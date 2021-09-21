from postgres import Postgres
import copy
import datetime
import pandas as pd
from typing import Iterable, List, Tuple

import api_util
from teams import TeamRating
from players import PlayerRating
import private_data
from tournament import Tournament

from db_tools import get_release_id, fast_insert, get_base_teams_for_players


# Reads the teams rating for given release_details_id.
def get_team_rating(cursor, schema: str, release_details_id: int) -> TeamRating:
    cursor.execute('SELECT team_id, rating '
                   + f'FROM {schema}.releases '
                   + f'WHERE release_details_id={release_details_id};')
    teams_list = [{'team_id': team_id, 'rating': rating} for team_id, rating in cursor.fetchall()]
    return TeamRating(teams_list=teams_list)


# Calculates new teams and players rating based on old rating and provided set of tournaments.
def calc_release(cursor, initial_teams: TeamRating, initial_players: PlayerRating,
                 tournaments: Iterable[Tournament],
                 release_date_for_squads: datetime.date) -> Tuple[TeamRating, PlayerRating]:
    initial_teams.update_q(initial_players)
    initial_teams.calc_trb(initial_players)
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
        get_base_teams_for_players(cursor, release_date_for_squads), how='left')
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
def get_chgkinfo_release_date(release_id: int) -> datetime.date:
    release_json = api_util.url2json(f'http://api.rating.chgk.net/releases/{release_id}')
    return datetime.datetime.fromisoformat(release_json['date']).date()


# Saves provided teams and players ratings to our DB for provided release date
def dump_release(cursor, schema: str, release_date: datetime.date, team_rating: TeamRating,
                 player_rating: PlayerRating):
    release_details_id = get_release_id(cursor, release_date, schema)

    # TODO: We don't need to dump players with rating 0
    cursor.execute(
        f'DELETE FROM {schema}.player_rating WHERE release_details_id={release_details_id};')
    player_rows = [
        f'({player_id}, {release_details_id}, {player["rating"]}, {player["rating"] - player["prev_rating"]})'
        for player_id, player in player_rating.data.iterrows()]
    fast_insert(cursor, 'player_rating', 'player_id, release_details_id, rating, rating_change',
                player_rows, schema)

    cursor.execute(f'DELETE FROM {schema}.releases WHERE release_details_id={release_details_id};')
    team_rows = [
        f'({team_id}, {release_details_id}, {team["rating"]}, {team["rating"] - team["prev_rating"]})'
        for team_id, team in team_rating.data.iterrows()]
    fast_insert(cursor, 'releases', 'team_id, release_details_id, rating, rating_change', team_rows,
                schema)

    cursor.execute(
        f'DELETE FROM {schema}.player_top_bonuses WHERE release_details_id={release_details_id};')
    bonuses_rows = []
    for player_id, player in player_rating.data.iterrows():
        bonuses_rows += [
            f'({player_id}, {release_details_id}, {tournament_id}, {rating_now}, {rating_original})'
            for tournament_id, rating_now, rating_original in player['top_bonuses']]
    fast_insert(cursor, 'player_top_bonuses',
                'player_id, release_details_id, tournament_id, rating_now, rating_original',
                bonuses_rows, schema)


# Saves tournament bonuses that were already calculated.
def dump_team_bonuses_for_tournament(cursor, schema: str, trnmt: Tournament):
    cursor.execute(f'DELETE FROM {schema}.tournament_results WHERE tournament_id={trnmt.id};')
    rows = [f'({trnmt.id}, {team["team_id"]}, {team["bonus"]})' for _, team in
            trnmt.data.iterrows()]
    fast_insert(cursor, 'tournament_results', 'tournament_id, team_id, rating', rows, schema)


# Creates release row if it doesn't exist.
# Marks the release with provided date as just updated.
# Returns the ID of this release in 'release_details' table.
def mark_release_as_just_updated(cursor, schema: str, release_date: datetime.date) -> int:
    cursor.execute(
        f'UPDATE {schema}.release_details SET updated_at=NOW() WHERE date=\'{release_date.isoformat()}\';')
    if cursor.rowcount == 0:
        # This means that there is now row with provided release_date yet
        cursor.execute(
            f'INSERT INTO {schema}.release_details (date, updated_at, created_at) VALUES (\'{release_date.isoformat()}\', NOW(), NOW());')
    cursor.execute(
        f'SELECT id FROM {schema}.release_details WHERE date=\'{release_date.isoformat()}\';')
    release_details_id = cursor.fetchone()[0]
    if release_details_id <= 0:
        print(f'Wrong release_details.id for {release_date.isoformat()}: {release_details_id}!')
    return release_details_id


# Copies release (teams and players) with provided ID from chgk.info to provided schema in our DB
def import_release(cursor, schema: str, release_id: int):
    team_rating = TeamRating(release_id=release_id)
    player_rating = PlayerRating(api_release_id=release_id)

    release_date = get_chgkinfo_release_date(release_id)
    dump_release(cursor, schema, release_date, team_rating, player_rating)
    print(f'Loaded {len(team_rating.data)} teams and {len(player_rating.data)} players from '
          f'release {release_date} (ID {release_id}).')


# Loads tournaments from our DB that finish between given releases.
def get_tournaments_for_release(cursor, old_release_date: datetime.date,
                                new_release_date: datetime.date) -> List[Tournament]:
    cursor.execute(f'SELECT id FROM public.rating_tournament WHERE end_datetime::date >= '
                   f'\'{old_release_date.isoformat()}\' AND end_datetime::date < '
                   f'\'{new_release_date.isoformat()}\' AND "maiiRating";')
    tournaments = []
    # We want only tournaments with available results
    for row in cursor.fetchall():
        maybe_tournament = Tournament(cursor, row[0])
        if maybe_tournament is not None:
            tournaments.append(maybe_tournament)
    print(
        f'Tournaments between {old_release_date.isoformat()} and '
        f'{new_release_date.isoformat()}: {len(tournaments)}')
    return tournaments


# Reads teams and players for provided dates; finds tournaments for next release; calculates
# new ratings and writes them to our DB.
def make_step(cursor, schema: str, old_release_date: datetime.date):
    old_release_id = get_release_id(cursor, old_release_date, schema)
    initial_teams = get_team_rating(cursor, schema, old_release_id)

    if old_release_date == datetime.date(2020, 4, 3):
        new_release_date = datetime.date(2021, 9, 9)
    else:
        new_release_date = old_release_date + datetime.timedelta(days=7)
    initial_players = PlayerRating(release_date=old_release_date,
                                   release_date_for_squads=new_release_date, cursor=cursor,
                                   schema=schema)
    tournaments = get_tournaments_for_release(cursor, old_release_date, new_release_date)

    new_teams, new_players = calc_release(cursor, initial_teams, initial_players, tournaments,
                                          release_date_for_squads=new_release_date)
    for trnmt in tournaments:
        dump_team_bonuses_for_tournament(cursor, schema, trnmt)
    # We run this before dumping release to create corresponding row in `release_details` if needed.
    mark_release_as_just_updated(cursor, schema, new_release_date)
    dump_release(cursor, schema, new_release_date, new_teams, new_players)


db = Postgres(url=private_data.postgres_url)
with db.get_cursor() as cursor:
    make_step(cursor, 'b', datetime.date(2020, 4, 3))
# write_initial_release(cursor, 1020) # 2014-09-smth
# write_initial_release(cursor, 1443) # 2020-04-03
# import_release(cursor, 'b', release_id=1443)
