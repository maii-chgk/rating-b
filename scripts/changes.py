import mmh3
import numpy as np


def calculate_hash(players, teams, tournaments):
    tournaments_to_concat = [t.data['score_real'].values for t in tournaments]
    if tournaments_to_concat:
        tournament_ratings = np.concatenate(tournaments_to_concat)
    else:
        tournament_ratings = np.array([])
    tournament_ratings.sort()

    player_ratings = players.data['rating'].values
    player_ratings.sort()

    team_ratings = teams.data['rating'].values
    team_ratings.sort()

    ratings_to_hash = np.concatenate((player_ratings, team_ratings, tournament_ratings))
    return mmh3.hash_from_buffer(ratings_to_hash)
