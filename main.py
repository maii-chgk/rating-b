from postgres import Postgres
import datetime
from typing import Optional, Tuple

import private_data
import api_util
from egor import players, teams, tournament

# TODO: We should read this from our public.* tables instead
def import_release_from_chgkinfo(release_id: int) -> Tuple[teams.TeamRating, players.PlayerRating]:
	return api_util.get_players_release(release_id), api_util.get_teams_release(release_id)

# Reads the data for given tournament including each team's players from 'public' schema.
def get_tournament(cursor, tournament_id: int) -> tournament.Tournament:
	cursor.execute(f'SELECT rteam.id f1, rp.id f2, otr.inRating, rteam.title, rr.team_title, rr.total, rr.position, o_r.flag '
		+ 'FROM public.rating_result rr, public."rating_result_teamMembers" rrt, public.rating_tournament rt, public.rating_team rteam, '
		+ 'public.rating_player rp, public.rating_oldteamrating otr, public.rating_oldrating o_r '
		+ f'WHERE rt.id={tournament_id} AND rr.tournament_id=rt.id AND rrt.result_id=rr.id AND rteam.id=rr.team_id AND rrt.player_id=rp.id AND otr.result_id=rr.id '
		+ f'AND rr.position!=9999 AND o_r.result_id=rr.id AND o_r.player_id=rp.id;')
	teams = {}
	for team_id, player_id, in_rating, team_name, cur_title, total, position, flag in cursor.fetchall():
		if team_id not in teams:
			teams[team_id] = {
				'team_id': team_id,
				'name': team_name,
				'current_name': cur_title,
				'questionsTotal': total,
				'position': position,
				'n_base': 0,
				'n_legs': 0,
				'teamMembers': [],
			}
		teams[team_id]['teamMembers'].append(player_id)
		if flag in {'Б', 'К'}:
			teams[team_id]['n_base'] += 1
		else:
			teams[team_id]['n_legs'] += 1
	return tournament.Tournament(teams_dict=teams)

# Reads the teams rating for given release_details_id.
def get_team_rating(cursor, schema: str, release_details_id: int) -> teams.TeamRating:
	cursor.execute('SELECT team_id, rating '
		+ f'FROM {schema}.releases'
		+ f'WHERE release_details_id={release_details_id};')
	# TODO: fill trb with "ТРК по БС"
	teams_list = [{'team_id': team_id, 'rating': rating, 'trb': rating} for team_id, rating in cursor.fetchall()]
	return teams.TeamRating(teams_list=teams_list)

# Reads the players rating for given release_details_id.
def get_player_rating(cursor, schema: str, release_details_id: int) -> players.PlayerRating:
	cursor.execute('SELECT player_id, rating '
		+ f'FROM {schema}.player_rating'
		+ f'WHERE release_details_id={release_details_id};')
	players_list = [{'player_id': player_id, 'rating': rating} for player_id, rating in cursor.fetchall()]
	return players.PlayerRating(players_list=players_list)

# Calculates new teams and players rating based on old rating and provided set of tournaments.
def calc_release(initial_teams: teams.TeamRating, initial_players: players.PlayerRating, tournaments: tournament.Tournament) -> Tuple[teams.TeamRating, players.PlayerRating]:
	initial_teams.update_q(players_rating)
	for tournament in tournaments:
		initial_teams.add_new_teams(tournament, initial_players)
		tournament.add_ratings(initial_teams, initial_players)
		tournament.calc_bonuses(initial_teams)
	new_teams = initial_teams.copy()
	new_players = initial_players.copy()
	for tournament in tournaments:
		for i, team in tournament.data.iterrows():
			new_teams, new_players = tournament.apply_bonuses(new_teams, new_players)
	return new_teams, new_players

# Reads the date for release at chgk.info with provided ID
def get_chgkinfo_release_date(release_id: int) -> datetime.date:
	release_json = api_util.url2json(f'http://api.rating.chgk.net/releases/{release_id}')
	return datetime.datetime.fromisoformat(release_json['date']).date()

# Reads the ID for release in given schema with provided date
def get_release_id(cursor, schema: str, release_date: datetime.date) -> Optional[int]:
	cursor.execute(f'SELECT id FROM {schema}.release_details WHERE date="{release_date.isoformat()}"')
	res = cursor.fetchall()
	if not res:
		print(f'No release with date {release_date} found in {schema}.release_details!')
		return None
	return res['id']

# Saves provided teams and players ratings to our DB for provided release date
def dump_release(cursor, schema: str, release_date: datetime.date, team_rating: teams.TeamRating, player_rating: players.PlayerRating):
	cursor.execute(f'DELETE FROM {schema}.player_rating WHERE release_details_id={release_details_id}')
	values = []
	for i, player in player_rating.iterrows():
		values.append(f'({player[" ИД"]}, {release_details_id}, {player["Рейтинг"]}, 0)')
		if ((i % 100) == 0) and values:
			cursor.execute(f'INSERT INTO {schema}.player_rating (player_id, release_details_id, rating, rating_change) VALUES ' + ', '.join(values) + ';')
			print(i)
			values = []
	if values:
		cursor.execute(f'INSERT INTO {schema}.player_rating (player_id, release_details_id, rating, rating_change) VALUES ' + ', '.join(values) + ';')

# Marks the release with provided date as just updated.
# Returns the ID of this release in 'release_details' table.
def mark_release_as_just_updated(cursor, schema: str, release_date: datetime.date) -> int:
	cursor.execute(f'UPDATE {schema}.release_details SET updated_at=NOW() WHERE date=\'{release_date.isoformat()}\';')
	if cursor.rowcount == 0:
		# This means that there is now row with provided release_date yet
		cursor.execute(f'INSERT INTO {schema}.release_details (date, updated_at, created_at) VALUES (\'{release_date.isoformat()}\', NOW(), NOW());')
	cursor.execute(f'SELECT id FROM {schema}.release_details WHERE date=\'{release_date.isoformat()}\';')
	release_details_id = cursor.fetchone()[0]
	if release_details_id <= 0:
		print(f'Wrong release_details.id for {release_date.isoformat()}: {release_id}!')
	return release_details_id

# Copies release (teams and players) with provided ID from chgk.info to provided schema in our DB
def import_release(cursor, schema: str, release_id: int):
	release_date = get_release_date(release_id)
	release_details_id = mark_release_as_just_updated(cursor, schema, release_date)

	team_rating, player_rating = import_release_from_chgkinfo(release_id)
	dump_release(cursor, schema, release_date, team_rating, player_rating)
	print(f'Loaded {len(team_rating.data)} teams and {len(player_rating.data)} players from release {release_date} (ID {release_id}).')

# Reads teams and players for provided dates; finds tournaments for next release; calculates new ratings and writes them to our DB.
def make_step(cursor, schema: str, old_release_date: datetime.date):
	old_release_id = get_release_id(cursor, schema, old_release_date)
	initial_teams = get_team_rating(cursor, schema, old_release_id)
	initial_playerss = get_player_rating(cursor, schema, old_release_id)
	tournaments = None # TODO
	new_teams, new_players = calc_release(initial_teams, initial_players, tournaments)
	if old_release_date < datetime.date.date(2020, 3, 4):
		new_release_date = old_release_date.datetime.timedelta(days=7)
	else:
		new_release_date = datetime.date.date(2021, 9, 9)
	dump_release(cursor, schema, new_release_date, new_teams, new_players)

db = Postgres(url=private_data.postgres_url)
with db.get_cursor() as cursor:
	pass
	# write_initial_release(cursor, 1020) # 2014-09-smth
	# write_initial_release(cursor, 1443) # 2021-04-03

