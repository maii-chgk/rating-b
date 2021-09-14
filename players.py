from tools import calc_tech_rating
from api_util import get_players_release
from db_tools import get_release_id, get_base_teams_for_players
import pandas as pd
from typing import List, Tuple

J = 0.99
N_BEST_TOURNAMENTS = 7


class PlayerRating:
    def __init__(self, release_date=None, file_path=None,
                 cursor=None, schema='b', api_release_id=None):
        self.data = pd.DataFrame()
        if api_release_id:
            print(f'Creating PlayerRating by old API from release_id {api_release_id}')
            raw_rating = get_players_release(api_release_id)
            raw_rating = raw_rating[[' ИД', 'ИД базовой команды', 'Рейтинг']]
            raw_rating.columns = ['player_id', 'base_team_id', 'rating']
            raw_rating.drop_duplicates(subset='player_id', inplace=True)
            self.data = raw_rating.set_index('player_id')
            self.data['prev_rating'] = 0
            self.data['top_bonuses'] = [[] for _ in range(len(self.data))]
            return
        if file_path:
            self.data = pd.DataFrame.from_csv(file_path, index_col=0)
            return
        if cursor is None:
            raise Exception("no file_path or cursor is passed")
        if release_date is None:
            raise Exception("no release_date is passed")
        release_id = get_release_id(cursor, release_date, schema)
        cursor.execute('SELECT player_id, rating '
                       + f'FROM {schema}.player_rating '
                       + f'WHERE release_details_id={release_id};')
        players_dict = {player_id: {'player_id': player_id, 'rating': rating, 'top_bonuses': []}
                        for player_id, rating in cursor.fetchall()}
        cursor.execute('SELECT player_id, tournament_id, rating_now, rating_original '
                       + f'FROM public.rating_individual_old_details ORDER BY rating_now;')
        for player_id, tournament_id, rating_now, rating_original in cursor.fetchall():
            if player_id in players_dict:
                players_dict[player_id]['top_bonuses'].append((tournament_id, rating_now, rating_original))
        # adding base_team_ids
        self.data = pd.DataFrame(players_dict.values()).set_index("player_id").join(
            get_base_teams_for_players(cursor, release_date), how='left')

    def calc_rt(self, player_ids, q=None):
        """
        вычисляет тех рейтинг по списку id игроков
        """
        prs = self.data.rating.reindex(player_ids).fillna(0).values
        return calc_tech_rating(prs, q)

    # Multiplies all existing bonuses by J_i constant
    def reduce_rating(self):
        def reduce_vector(v: List[Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
            return [(tournament_id, int(round(rating_now * J)), rating_original) for tournament_id, rating_now, rating_original in v]
        self.data['top_bonuses'] = self.data['top_bonuses'].map(reduce_vector)

    # Removes all bonuses except top 7 and updates rating for each player
    def recalc_rating(self):
        def leave_top_N(v: List[Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
            return sorted(v, key=lambda x: -x[1])[:N_BEST_TOURNAMENTS]
        self.data['top_bonuses'] = self.data['top_bonuses'].map(leave_top_N)

        def sum_ratings_now(v: List[Tuple[int, int, int]]) -> int:
            return sum(x[1] for x in v)
        self.data['rating'] = self.data['top_bonuses'].map(sum_ratings_now)
