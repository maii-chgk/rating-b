from rating_api.release import get_teams_release
from rating.tools import calc_tech_rating
import pandas as pd
import numpy as np


class TeamRating:
    def __init__(self, release_id=None, filename=None):
        if not (release_id or filename):
            raise Exception('provide release id or file with rating!')
        self.q = 1
        if release_id:
            raw_rating = get_teams_release(release_id)
        else:
            raw_rating = pd.read_csv(filename)
        raw_rating = raw_rating[['Ид', 'Рейтинг', 'ТРК по БС']]
        raw_rating.columns = ['team_id', 'rating', 'trb']
        self.data = raw_rating.set_index('team_id')
        self.c = self.calc_c()

    def update_q(self, players_release):
        """
            Коэффициент Q вычисляется при релизе как среднее значение отношения рейтинга R к техническому
            рейтингу по базовому составу RB для команд, входящих в 100 лучших по последнему релизу
            (исключая те, которые получают в этом релизе стартовые рейтинги) и имеющих не менее шести
            игроков в базовом составе.
            """
        top_h = self.data.iloc[:100]
        top_h_ids = set(top_h.index)
        rb_raws = players_release.data[players_release.data['base_team_id'].isin(top_h_ids)].groupby(
            'base_team_id')['rating'].apply(lambda x: calc_tech_rating(x.values))
        top_h = top_h.join(rb_raws, rsuffix='_raw')
        self.q = (top_h['rating'] / top_h['rating_raw']).mean()

    def calc_c(self):
        ratings = self.data.rating.values
        ratings[::-1].sort()
        return 2300 / ratings[:15].dot(2. ** np.arange(0, -15, -1))

    def get_team_rating(self, team_id):
        return self.data.rating.get(team_id, 0)

    def get_trb(self, team_id):
        return self.data.trb.get(team_id, 0)