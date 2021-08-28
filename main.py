from postgres import Postgres
import private_data

def get_tournament_and_teams(cursor, tournament_id: int) -> dict[int, list[int]]:
	cursor.execute(f'SELECT team_id, total, position FROM public.rating_result WHERE tournament_id={tournament_id};')
	teams_raw = cursor.fetchall()
	cursor.execute(f'SELECT rteam.r_id f1, rp.r_id f2, rt.title FROM public.rating_result rr, public."rating_result_teamMembers" rrt, public.rating_tournament rt, public.rating_team rteam, public.rating_player rp '
		+ f'WHERE rr.id=rrt.result_id AND rt.r_id={tournament_id} AND rt.id=tournament_id AND rteam.id=rr.team_id AND rrt.player_id=rp.id;')
	# cursor.execute(f'SELECT rr.team_id, rrt.player_id FROM public.rating_result rr, public."rating_result_teamMembers" rrt, public.rating_tournament WHERE rr.id=rrt.result_id AND tournament_id={tournament_id} ;')
	players_raw = cursor.fetchall()
	players: dict[int, list[int]] = {}
	print(tournament_id, len(teams_raw), len(players_raw))
	for team_id, player_id, _ in players_raw:
		if team_id not in players:
			players[team_id] = []
		players[team_id].append(player_id)
	print(len(players), players.get(56459))
	for k, v in list(players.items())[:10]:
		print(k, v, players_raw[0][2])
	return players

def calc_release(teams, tournaments):
	pass

db = Postgres(url=private_data.postgres_url)

with db.get_cursor() as cursor:
	get_tournament_and_teams(cursor, 4791)
