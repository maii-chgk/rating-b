from postgres import Postgres
import datetime

import private_data
import util

def get_tournament_and_teams(cursor, tournament_id: int) -> dict[int, list[int]]:
	cursor.execute(f'SELECT team_id, total, position FROM public.rating_result WHERE tournament_id={tournament_id};')
	teams_raw = cursor.fetchall()
	cursor.execute(f'SELECT rteam.r_id f1, rp.r_id f2, otr.inRating, rteam.title, rr.team_title, rr.total, rr.position, or.flag '
		+ 'FROM public.rating_result rr, public."rating_result_teamMembers" rrt, public.rating_tournament rt, public.rating_team rteam, '
		+ 'public.rating_player rp, public.rating_oldteamrating otr, public.rating_oldrating or '
		+ f'WHERE rr.id=rrt.result_id AND rt.r_id={tournament_id} AND rt.id=tournament_id AND rteam.id=rr.team_id AND rrt.player_id=rp.id AND otr.result_id=rr.id '
		+ f'AND rr.position!=9999 AND or.result_id=rr.id AND or.player_id=rp.id;')
	# cursor.execute(f'SELECT rr.team_id, rrt.player_id FROM public.rating_result rr, public."rating_result_teamMembers" rrt, public.rating_tournament WHERE rr.id=rrt.result_id AND tournament_id={tournament_id} ;')
	players_raw = cursor.fetchall()
	players: dict[int, list[int]] = {}
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
	print(len(players), players.get(56459))
	for k, v in list(players.items())[:10]:
		print(k, v, players_raw[0][2])
	return players

def calc_release(teams, tournaments):
	pass

def write_initial_release(release_id: int):
	release_json = util.url2json(f'http://api.rating.chgk.net/releases/{release_id}')
	release_date = datetime.fromisoformat(release_json['date']).date
	

db = Postgres(url=private_data.postgres_url)

with db.get_cursor() as cursor:
	get_tournament_and_teams(cursor, 4791)
