from postgres import Postgres
import copy
import datetime
import pandas as pd
from django.utils import timezone
from typing import Iterable, List, Optional, Tuple

from b import models
from dj import private_settings

from . import api_util
from . import tools
from .teams import TeamRating
from .players import PlayerRating
from .tournament import EmptyTournamentException, Tournament
from .db_tools import get_teams_with_new_players, fast_insert, get_base_teams_for_players

SCHEMA = 'b'
POSTGRES_URL = 'postgresql://{}:{}@{}:{}/{}'.format(
    private_settings.DJANGO_POSTRGES_DB_USER,
    private_settings.DJANGO_POSTRGES_DB_PASSWORD,
    private_settings.DJANGO_POSTRGES_DB_HOST,
    private_settings.DJANGO_POSTRGES_DB_PORT,
    private_settings.DJANGO_POSTRGES_DB_NAME,
)

# Reads the teams rating for given release_id.
def get_team_rating(cursor, schema: str, release_id: int) -> TeamRating:
    teams_list = list(models.Team_rating.objects.filter(release_id=release_id).values('team_id', 'rating', 'trb'))
    return TeamRating(teams_list=teams_list)


# Calculates new teams and players rating based on old rating and provided set of tournaments.
def make_step_for_teams_and_players(cursor, initial_teams: TeamRating, initial_players: PlayerRating,
                 tournaments: Iterable[Tournament],
                 new_release: models.Release) -> Tuple[TeamRating, PlayerRating]:
    existing_player_ids = set(initial_players.data.index)
    new_player_ids = set()
    for tournament in tournaments:
        initial_teams.add_new_teams(tournament, initial_players)
        tournament.add_ratings(initial_teams, initial_players)
        tournament.calc_bonuses(initial_teams)
        new_player_ids |= tournament.get_new_player_ids(existing_player_ids)

    final_teams = copy.deepcopy(initial_teams)
    final_players = copy.deepcopy(initial_players)
    new_players = pd.DataFrame(
        [{'player_id': player_id, 'rating': 0, 'top_bonuses': []} for player_id in
         new_player_ids]).set_index("player_id").join(
        get_base_teams_for_players(cursor, new_release.date), how='left')
    final_players.data = final_players.data.append(new_players)

    # We need these columns to dump the difference between new and old rating.
    final_teams.data['prev_rating'] = final_teams.data['rating']
    final_players.data['prev_rating'] = final_players.data['rating']

    final_players.reduce_rating()
    for tournament in tournaments:
        final_teams, final_players = tournament.apply_bonuses(final_teams, final_players)
    final_players.recalc_rating()
    return final_teams, final_players


# Reads the date for release at chgk.info with provided ID
def get_api_release_date(release_id: int) -> datetime.date:
    release_json = api_util.url2json(f'http://api.rating.chgk.net/releases/{release_id}')
    return datetime.datetime.fromisoformat(release_json['date']).date()


# Saves provided teams and players ratings to our DB for provided release date
def dump_release(cursor, schema: str, release: models.Release, team_rating: TeamRating,
                 player_rating: PlayerRating):
    # TODO: We don't need to dump players with rating 0
    release.player_rating_set.all().delete()
    release.team_rating_set.all().delete()
    release.player_rating_by_tournament_set.all().delete()

    print(f'Dumping ratings for {len(player_rating.data.index)} players and {len(team_rating.data.index)} teams...')
    player_rows = [
        f'({player_id}, {release.id}, {player["rating"]}, {(player["rating"] - player["prev_rating"]) if player["prev_rating"] else "NULL"})'
        for player_id, player in player_rating.data.iterrows()]
    fast_insert(cursor, 'player_rating', 'player_id, release_id, rating, rating_change',
                player_rows, schema)

    team_rows = [
        f'({team_id}, {release.id}, {team["rating"]}, {team["trb"]}, {(team["rating"] - team["prev_rating"]) if team["prev_rating"] else "NULL"})'
        for team_id, team in team_rating.data.iterrows()]
    fast_insert(cursor, 'team_rating', 'team_id, release_id, rating, trb, rating_change', team_rows,
                schema)

    bonuses_rows = []
    i = 0
    for player_id, player in player_rating.data.iterrows():
        i += 1
        for player_rating_by_trnmt in player['top_bonuses']:
            bonuses_rows.append('(' + ', '.join(str(x) for x in [
                release.id,
                player_id,
                player_rating_by_trnmt.tournament_result_id if player_rating_by_trnmt.tournament_result_id else 'NULL',
                player_rating_by_trnmt.tournament_id if player_rating_by_trnmt.tournament_id else 'NULL',
                # player_rating_by_trnmt.tournament_result.rating if player_rating_by_trnmt.tournament_result else player_rating_by_trnmt.initial_score,
                player_rating_by_trnmt.initial_score,
                player_rating_by_trnmt.weeks_since_tournament,
                player_rating_by_trnmt.cur_score,
            ]) + ')')
    print(f'Dumping {len(bonuses_rows)} player bonuses...')
    fast_insert(cursor, 'player_rating_by_tournament',
                'release_id, player_id, tournament_result_id, tournament_id, initial_score, weeks_since_tournament, cur_score',
                bonuses_rows, schema)


# Saves tournament bonuses that were already calculated.
def dump_team_bonuses_for_tournament(cursor, schema: str, trnmt: Tournament):
    models.Tournament_result.objects.filter(tournament_id=trnmt.id).delete()
    rows = []
    for _, team in trnmt.data.iterrows():
        rows.append('(' + ', '.join(str(x) for x in [
            trnmt.id,
            team["team_id"],
            team["expected_place"],
            team["score_pred"],
            team["position"],
            team["score_real"],
            team["D1"],
            team["D2"],
            team["bonus"],
            'TRUE' if team["heredity"] else 'FALSE',
        ]) + ')')
    fast_insert(cursor, 'tournament_result', 'tournament_id, team_id, mp, bp, m, rating, d1, d2, rating_change, is_in_maii_rating', rows, schema)


# Copies release (teams and players) with provided ID from API to provided schema in our DB
def import_release(api_release_id: int, schema: str=SCHEMA):
    team_rating = TeamRating(api_release_id=api_release_id)
    player_rating = PlayerRating(api_release_id=api_release_id)
    # TODO: Also read top_bonuses for players

    release_date = get_api_release_date(api_release_id)
    release, _ = models.Release.objects.get_or_create(date=release_date)
    db = Postgres(url=POSTGRES_URL)
    with db.get_cursor() as cursor:
        dump_release(cursor, schema, release, team_rating, player_rating)
    print(f'Loaded {len(team_rating.data)} teams and {len(player_rating.data)} players from '
          f'release {release_date} (ID in API {api_release_id}).')


# Loads tournaments from our DB that finish between given releases.
def get_tournaments_for_release(cursor, old_release: models.Release,
                                new_release: models.Release) -> List[Tournament]:
    tournaments = []
    for tournament_id in models.Tournament.objects.filter(
            end_datetime__date__gt=old_release.date,
            end_datetime__date__lte=new_release.date,
            maii_rating=True).values_list('pk', flat=True):
        # We need only tournaments with available results of at lease some teams.
        try:
            tournament = Tournament(cursor, tournament_id=tournament_id, release=new_release)
            tournaments.append(tournament)
        except EmptyTournamentException:
            print(f'Tournament with id {tournament_id} has no results. Skipping')
    print(f'There are {len(tournaments)} tournaments with at least one result between {old_release.date} and {new_release.date}.')
    return tournaments


# Reads teams and players for provided dates; finds tournaments for next release; calculates
# new ratings and writes them to our DB.
def calc_release(next_release_date: datetime.date, schema: str=SCHEMA, db: Optional[Postgres] = None):
    if db is None:
        db = Postgres(url=POSTGRES_URL)
    with db.get_cursor() as cursor:
        old_release_date = tools.get_prev_release_date(next_release_date)
        old_release = models.Release.objects.get(date=old_release_date)
        initial_teams = get_team_rating(cursor, schema, old_release.id)
        next_release, _ = models.Release.objects.get_or_create(date=next_release_date)

        print(f'Making a step from release {old_release_date} (id {old_release.id}) to release {next_release_date} (id {next_release.id})')
        initial_players = PlayerRating(release=old_release,
                                       release_for_squads=next_release,
                                       cursor=cursor,
                                       schema=schema,
                                       take_top_bonuses_from_api=(old_release_date == tools.LAST_OLD_RELEASE) # TODO: Remove
                                       )
        initial_teams.update_q(initial_players)
        initial_teams.calc_trb(initial_players)
        changed_teams = get_teams_with_new_players(cursor, old_release_date, next_release_date)
        initial_teams.update_ratings_for_changed_teams(changed_teams)
        tournaments = get_tournaments_for_release(cursor, old_release, next_release)
        new_teams, new_players = make_step_for_teams_and_players(
            cursor, initial_teams, initial_players, tournaments, new_release=next_release)
        for tournament in tournaments:
            dump_team_bonuses_for_tournament(cursor, schema, tournament)
        dump_release(cursor, schema, next_release, new_teams, new_players)
        next_release.updated_at = timezone.now()
        next_release.save()

# Calculates all releases starting from FIRST_NEW_RELEASE until current date
def calc_all_releases():
    next_release_date = tools.FIRST_NEW_RELEASE
    today = datetime.date.today()
    time_started = datetime.datetime.now()
    db = Postgres(url=POSTGRES_URL)
    n_releases_calculated = 0
    while next_release_date <= today:
        calc_release(next_release_date=next_release_date, db=db)
        n_releases_calculated += 1
        next_release_date += datetime.timedelta(days=7)
    time_spent = datetime.datetime.now() - time_started
    print('Done! Releases calculated:', n_releases_calculated)
    print(f'Total time spent: {time_spent}, time per release: {time_spent / n_releases_calculated}')
