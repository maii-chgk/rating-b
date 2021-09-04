from rating_api.release import get_players_release
from egor.tools import calc_tech_rating
import pandas as pd


class PlayerRating:
    def __init__(self, release_id=None, file_path=None):
        self.data = pd.DataFrame()
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
