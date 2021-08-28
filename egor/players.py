from rating_api.release import get_players_release
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
