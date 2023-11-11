from postgres import Postgres
import copy
import datetime
import decimal
import sys
import os
import pandas as pd
import numpy as np
from django.utils import timezone
from typing import Iterable, List, Optional, Tuple
from dotenv import load_dotenv

from b import models

from . import api_util
from . import db_tools
from . import tools
from . import tournament as trnmt
from .teams import TeamRating
from .players import PlayerRating
from .changes import calculate_hash

load_dotenv()

SCHEMA = 'b'
POSTGRES_URL = 'postgresql://{}:{}@{}:{}/{}?sslmode=disable'.format(
    os.environ['DJANGO_POSTGRES_DB_USER'],
    os.environ['DJANGO_POSTGRES_DB_PASSWORD'],
    os.environ['DJANGO_POSTGRES_DB_HOST'],
    os.environ['DJANGO_POSTGRES_DB_PORT'],
    os.environ['DJANGO_POSTGRES_DB_NAME']
)
os.environ['PGOPTIONS'] = '-c statement_timeout=300s'

decimal.getcontext().prec = 1
verbose = False

# Reads the teams rating for given release_id.
def get_team_rating(cursor, schema: str, release_id: int) -> TeamRating:
    teams_list = list(models.Team_rating.objects.filter(release_id=release_id).values('team_id', 'rating', 'trb', 'place').order_by('-rating'))
    return TeamRating(teams_list=teams_list)


# Calculates new teams and players rating based on old rating and provided set of tournaments.
def make_step_for_teams_and_players(cursor, initial_teams: TeamRating, initial_players: PlayerRating,
                 tournaments: Iterable[trnmt.Tournament],
                 new_release: models.Release) -> Tuple[TeamRating, PlayerRating]:
    existing_player_ids = set(initial_players.data.index)
    new_player_ids = set()
    for tournament in tournaments:
        if verbose:
            print(f'Tournament {tournament.id}...' + ('' if tournament.is_in_maii_rating else ' (not in MAII rating)'))
        initial_teams.add_new_teams(tournament, initial_players)
        tournament.add_ratings(initial_teams, initial_players)
        tournament.calc_bonuses(initial_teams)
        new_player_ids |= tournament.get_new_player_ids(existing_player_ids)

    final_teams = copy.deepcopy(initial_teams)
    final_players = copy.deepcopy(initial_players)
    if new_player_ids:
        new_players = pd.DataFrame(
            [{'player_id': player_id, 'rating': 0, 'top_bonuses': []} for player_id in
             new_player_ids]).set_index("player_id").join(
            db_tools.get_base_teams_for_players(new_release.date), how='left')
        final_players.data = pd.concat([final_players.data, new_players])

    # We need these columns to dump the difference between new and old rating.
    final_teams.data['prev_rating'] = final_teams.data['rating']
    final_players.data['prev_rating'] = final_players.data['rating']

    final_players.reduce_rating()
    for tournament in tournaments:
        if tournament.is_in_maii_rating:
            final_teams, final_players = tournament.apply_bonuses(final_teams, final_players)
    # Team rating cannot be negative.
    final_teams.data['rating'] = np.maximum(final_teams.data['rating'], 0)
    final_players.recalc_rating()
    return final_teams, final_players


# Reads the date for release at chgk.info with provided ID
def get_api_release_date(release_id: int) -> datetime.date:
    release_json = api_util.url2json(f'http://api.rating.chgk.net/releases/{release_id}')
    return datetime.datetime.fromisoformat(release_json['date']).date()


# Saves provided teams and players ratings to our DB for provided release date
def dump_release(cursor, schema: str, release: models.Release, teams: pd.DataFrame,
                 player_rating: PlayerRating, tournaments: Iterable[trnmt.Tournament]):
    release.player_rating_set.all().delete()
    release.team_rating_set.all().delete()
    release.player_rating_by_tournament_set.all().delete()
    release.tournament_in_release_set.all().delete()

    if verbose:
        print(f'Dumping ratings for {len(player_rating.data.index)} players and {len(teams.index)} teams...')
    player_rows = [
        f'({player_id}, {release.id}, {player["rating"]}, {(player["rating"] - player["prev_rating"]) if player["prev_rating"] else "NULL"})'
        for player_id, player in player_rating.data.iterrows()
        if (player["rating"] > 0)]
    db_tools.fast_insert(cursor, 'player_rating', 'player_id, release_id, rating, rating_change',
                player_rows, schema)

    team_rows = [
        f'({team_id}, {release.id}, {team["rating"]}, {team["trb"]}, {(team["rating"] - team["prev_rating"]) if team["prev_rating"] else "NULL"}, '
        + f'{team["place"] if team["place"] else "NULL"}, {(decimal.Decimal(team["place"]) - team["prev_place"]) if team["prev_place"] else "NULL"})'
        for team_id, team in teams.iterrows()]
    db_tools.fast_insert(cursor, 'team_rating', 'team_id, release_id, rating, trb, rating_change, place, place_change', team_rows,
                schema)

    bonuses_rows = []
    i = 0
    for player_id, player in player_rating.data.iterrows():
        if player["rating"] == 0:
            continue
        i += 1
        for player_rating_by_trnmt in player['top_bonuses']:
            if player_rating_by_trnmt.cur_score > 0:
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
    if verbose:
        print(f'Dumping {len(bonuses_rows)} player bonuses...')
    db_tools.fast_insert(cursor, 'player_rating_by_tournament',
                'release_id, player_id, tournament_result_id, tournament_id, initial_score, weeks_since_tournament, cur_score',
                bonuses_rows, schema)

    tournament_in_release_rows = [f'({release.id}, {tournament.id})' for tournament in tournaments if tournament.is_in_maii_rating]
    db_tools.fast_insert(cursor, 'tournament_in_release', 'release_id, tournament_id', tournament_in_release_rows, schema)


# Saves tournament bonuses that were already calculated.
def dump_team_bonuses_for_tournament(cursor, schema: str, trnmt: trnmt.Tournament):
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
            team["r"],
            team["rt"],
            team["rb"],
            team["rg"],
            'TRUE' if team["heredity"] else 'FALSE',
        ]) + ')')
    db_tools.fast_insert(cursor, 'tournament_result', 'tournament_id, team_id, mp, bp, m, rating, d1, d2, rating_change, r, rt, rb, rg, is_in_maii_rating', rows, schema)

def dump_rating_for_next_release(old_release: models.Release, teams_with_updated_rating: List[Tuple[int, int]]):
    for team_id, new_rating in teams_with_updated_rating:
        n_changed = old_release.team_rating_set.filter(team_id=team_id).update(rating_for_next_release=new_rating)
        if n_changed != 1:
            print('dump_rating_for_next_release: there is problem with updating team_rating.rating_for_next_release for '
                + f'team_id {team_id}, new rating {new_rating}: {n_changed} rows are affected.')

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
    if verbose:
        print(f'Loaded {len(team_rating.data)} teams and {len(player_rating.data)} players from '
              f'release {release_date} (ID in API {api_release_id}).')


# Loads tournaments from our DB that finish between given releases.
def get_tournaments_for_release(cursor, old_release: models.Release,
                                new_release: models.Release) -> List[trnmt.Tournament]:
    tournaments = []
    n_counted_in_maii_rating = 0
    tournaments_qs = models.Tournament.objects.filter(
        end_datetime__date__gt=old_release.date,
        end_datetime__date__lte=new_release.date).prefetch_related('roster_set', 'team_score_set__team')
    if new_release.date <= tools.FIRST_NEW_RELEASE:
        tournaments_qs = tournaments_qs.filter(maii_rating=True)
    for trnmt_from_db in tournaments_qs.order_by('pk'):
        # We need only tournaments with available results of at lease some teams.
        try:
            tournament = trnmt.Tournament(cursor, trnmt_from_db=trnmt_from_db, release=new_release, verbose=verbose)
            tournaments.append(tournament)
            if trnmt_from_db.maii_rating:
                n_counted_in_maii_rating += 1
        except trnmt.EmptyTournamentException as e:
            if trnmt_from_db.maii_rating:
                print(f'Skipping tournament with id {trnmt_from_db.id}: {e}')
    if verbose:
        print(f'There are {len(tournaments)} tournaments ({n_counted_in_maii_rating} in MAII rating) with at least one result between {old_release.date} and {new_release.date}.')
    return tournaments

# A.2.2: We only calculate rating for teams that have base roster in current season,
# or that had it in previous season and new season started <=3 months ago.
def teams_to_dump(release_date: datetime.date, teams: TeamRating) -> pd.DataFrame:
    cur_season = db_tools.get_season(release_date)
    teams_with_rosters = set(cur_season.season_roster_set.values_list('team_id', flat=True).distinct())
    if cur_season.start + datetime.timedelta(days=90) >= release_date:
        prev_season = db_tools.get_season(release_date - datetime.timedelta(days=180))
        teams_with_rosters |= set(prev_season.season_roster_set.values_list('team_id', flat=True).distinct())
    res = teams.data[teams.data.index.isin(teams_with_rosters)]
    n_skipped_teams = len(teams.data[~teams.data.index.isin(teams_with_rosters)])
    if n_skipped_teams and verbose:
        print(f'We exclude from the rating {n_skipped_teams} teams that have no roster for current season.')
    return teams.data[teams.data.index.isin(teams_with_rosters)]

# Reads teams and players for provided dates; finds tournaments for next release; calculates
# new ratings and writes them to our DB.
def calc_release(next_release_date: datetime.date, schema: str=SCHEMA, db: Optional[Postgres] = None, flag_verbose=None):
    if flag_verbose is not None:
        global verbose
        verbose = flag_verbose
    if db is None:
        db = Postgres(url=POSTGRES_URL)
    with db.get_cursor() as cursor:
        old_release_date = tools.get_prev_release_date(next_release_date)
        old_release = models.Release.objects.get(date=old_release_date)
        initial_teams = get_team_rating(cursor, schema, old_release.id)
        next_release, _ = models.Release.objects.get_or_create(date=next_release_date)

        print(f'Making a step from release {old_release_date} (id {old_release.id}) to release {next_release_date} (id {next_release.id})')
        initial_players = PlayerRating(release=old_release, release_for_squads=next_release)
        initial_teams.update_q(initial_players)
        if pd.isnull(initial_teams.q):
            sys.exit('Q is nan! We cannot continue.')
        initial_teams.calc_trb(initial_players)

        changed_teams = db_tools.get_teams_with_new_players(old_release_date, next_release_date)
        teams_with_updated_rating = initial_teams.update_ratings_for_changed_teams(changed_teams)
        dump_rating_for_next_release(old_release, teams_with_updated_rating)

        tournaments = get_tournaments_for_release(cursor, old_release, next_release)
        new_teams, new_players = make_step_for_teams_and_players(
            cursor, initial_teams, initial_players, tournaments, new_release=next_release)
        new_teams.data['place'] = tools.calc_places(new_teams.data['rating'].values)
        for tournament in tournaments:
            dump_team_bonuses_for_tournament(cursor, schema, tournament)
        dump_release(cursor, schema, next_release, teams_to_dump(next_release_date, new_teams), new_players,
                     tournaments)

        release_hash = calculate_hash(new_players, new_teams, tournaments)

        if release_hash != next_release.hash:
            print("hashes are different, updating release")
            next_release.updated_at = timezone.now()
            next_release.hash = release_hash
            next_release.save()


# Calculates all releases starting from FIRST_NEW_RELEASE until current date
def calc_all_releases(first_to_calc: datetime.date, flag_verbose=None):
    if flag_verbose is not None:
        global verbose
        verbose = flag_verbose
    next_release_date = first_to_calc
    time_started = datetime.datetime.now()
    db = Postgres(url=POSTGRES_URL)
    n_releases_calculated = 0
    last_day_to_calc = datetime.date.today() + datetime.timedelta(days=7)
    while next_release_date <= last_day_to_calc:
        calc_release(next_release_date=next_release_date, db=db, flag_verbose=flag_verbose)
        n_releases_calculated += 1
        next_release_date += datetime.timedelta(days=7)
    time_spent = datetime.datetime.now() - time_started
    print('Done! Releases calculated:', n_releases_calculated)
    print(f'Total time spent: {time_spent}, time per release: {time_spent / n_releases_calculated}')
