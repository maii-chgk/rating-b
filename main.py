from postgres import Postgres
import datetime

import private_data
import util
from egor import tournament


def get_tournament_and_teams(cursor, tournament_id: int) -> dict[int, list[int]]:
	cursor.execute(f'SELECT team_id, total, position FROM public.rating_result WHERE tournament_id={tournament_id};')
	teams_raw = cursor.fetchall()
	cursor.execute(f'SELECT rteam.r_id f1, rp.r_id f2, otr.inRating, rteam.title, rr.team_title, rr.total, rr.position, or.flag '
		+ 'FROM public.rating_result rr, public."rating_result_teamMembers" rrt, public.rating_tournament rt, public.rating_team rteam, '
		+ 'public.rating_player rp, public.rating_oldteamrating otr, public.rating_oldrating or '
		+ f'WHERE rr.id=rrt.result_id AND rt.r_id={tournament_id} AND rt.id=tournament_id AND rteam.id=rr.team_id AND rrt.player_id=rp.id AND otr.result_id=rr.id '
		+ f'AND rr.position!=9999 AND or.result_id=rr.id AND or.player_id=rp.id;')
	# cursor.execute(f'SELECT rr.team_id, rrt.player_id FROM public.rating_result rr, public."rating_result_teamMembers" rrt, public.rating_tournament WHERE rr.id=rrt.result_id AND tournament_id={tournament_id} ;')
	teams = {}
	print(tournament_id, len(teams_raw), len(players_raw))
	for team_id, player_id, in_rating, team_name, cur_title, total, position, flag in players_raw:
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

def calc_release(teams, tournaments, players):
	teams.update(players)
	for tournament in tournaments:
		tournament.add_ratings(t_r, p_r)
		tournament.calc_bonuses(t_r)

def write_initial_release(cursor):
	release_id = 1020
	release_json = util.url2json(f'http://api.rating.chgk.net/releases/{release_id}')
	release_date = datetime.datetime.fromisoformat(release_json['date']).date()
	cursor.execute(f'UPDATE ratingb.release_details SET updated_at=NOW() WHERE date=\'{release_date.isoformat()}\';')
	if cursor.rowcount == 0:
		cursor.execute(f'INSERT INTO ratingb.release_details (date, updated_at, created_at) VALUES (\'{release_date.isoformat()}\', NOW(), NOW());')
	cursor.execute(f'SELECT id FROM ratingb.release_details WHERE date=\'{release_date.isoformat()}\';')
	release_details_id = cursor.fetchone()[0]
	if release_details_id <= 0:
		print(f'Wrong release_details.id for {release_date.isoformat()}: {release_id}!')
		return

	# teams_pd = util.get_teams_release(release_id)
	# cursor.execute(f'DELETE FROM ratingb.releases WHERE release_details_id={release_details_id}')
	# for i, team in teams_pd.iterrows():
	# 	cursor.execute(f'INSERT INTO ratingb.releases (team_id, release_details_id, rating, rating_change) VALUES ({team["Ид"]}, {release_details_id}, {team["Рейтинг"]}, 0);')
	# print(f'Initial release is loaded: {len(teams_pd)} teams found.')

	players_pd = util.get_players_release(release_id)
	print(f'Loaded {len(players_pd)} players.')
	cursor.execute(f'DELETE FROM ratingb.player_rating WHERE release_details_id={release_details_id}')
	for i, player in players_pd.iterrows():
		cursor.execute(f'INSERT INTO ratingb.player_rating (player_id, release_details_id, rating, rating_change) VALUES ({player[" ИД"]}, {release_details_id}, {player["Рейтинг"]}, 0);')
		if (i % 100) == 0:
			print(i, f'INSERT INTO ratingb.player_rating (player_id, release_details_id, rating, rating_change) VALUES ({player[" ИД"]}, {release_details_id}, {player["Рейтинг"]}, 0);')
		# if i >= 10:
		# 	break
	print(f'Initial release is loaded: {len(players_pd)} found.')

db = Postgres(url=private_data.postgres_url)

with db.get_cursor() as cursor:
	write_initial_release(cursor)
