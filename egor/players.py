from api_util import get_players_release
from egor.tools import calc_tech_rating
import pandas as pd
from typing import List, Tuple

J = 0.99
N_BEST_TOURNAMENTS = 7

class PlayerRating:
    def __init__(self, release_id=None, file_path=None, players_list=None):
        self.data = pd.DataFrame()
        if players_list:
            self.data = pd.DataFrame(players_list)
        if release_id:
            raw_rating = get_players_release(release_id)
            raw_rating = raw_rating[[' ИД', 'ИД базовой команды', 'Рейтинг']]
            raw_rating.columns = ['player_id', 'base_team_id', 'rating']
            raw_rating.drop_duplicates(subset='player_id', inplace=True)
            self.data = raw_rating.set_index('player_id')
        elif file_path:
            self.data = pd.DataFrame.from_csv(file_path, index_col=0)

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
            return sorted(v, lambda x: -x[1])[:N_BEST_TOURNAMENTS]
        self.data['top_bonuses'] = self.data['top_bonuses'].map(leave_top_N)

        def sum_ratings_now(v: List[Tuple[int, int, int]]) -> int:
            return sum(x[1] for x in v)
        self.data['rating'] = self.data['top_bonuses'].map(sum_ratings_now)
