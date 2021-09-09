# from rating_api.tournaments import get_tournament_results
from egor.tools import calc_tech_rating, rolling_window, calc_score_real, calc_bonus_raw
import pandas as pd
import numpy as np


class Tournament:
    def __init__(self, tournament_id, teams_dict=None):
        if teams_dict:
            self.data = pd.DataFrame(teams_dict.values())
        else:
            # raw_results = get_tournament_results(tournament_id, recaps=True)
            self.data = pd.DataFrame([
                {
                    'team_id': t['team']['id'],
                    'name': t['team']['name'],
                    'current_name': t['current']['name'],
                    'questionsTotal': t['questionsTotal'],
                    'position': t['position'],
                    'n_base': sum(player['flag'] in {'Б', 'К'} for player in t['teamMembers']),
                    'n_legs': sum(player['flag'] not in {'Б', 'К'} for player in t['teamMembers']),
                    'teamMembers': [x['player']['id'] for x in t['teamMembers']]
                } for t in raw_results if t['position'] != 9999
            ])
        self.data['heredity'] = (self.data.n_base > 3) | (self.data.n_base == 3) & \
                                (self.data.name == self.data.current_name)

    @staticmethod
    def calc_rt(player_ids, player_rating, q):
        """
        вычисляет тех рейтинг по фактическому составу команды
        """
        prs = player_rating.data.rating.reindex(player_ids).fillna(0).values
        return calc_tech_rating(prs, q)

    def add_ratings(self, team_rating, player_rating):
        self.data['rt'] = self.data.teamMembers.map(lambda x: self.calc_rt(x, player_rating, team_rating.q))
        self.data['r'] = np.where(self.data.heredity, self.data.team_id.map(team_rating.get_team_rating), 0)
        self.data['rb'] = np.where(self.data.heredity, self.data.team_id.map(team_rating.get_trb), 0)
        self.data['rg'] = np.where(self.data.rb, self.data.r * self.data.rt / self.data.rb, self.data.rt)
        self.data['rg'] = np.where(self.data.rt < self.data.rb, np.maximum(self.data.rg, 0.5 * self.data.r),
                                   np.minimum(self.data.rg, np.maximum(self.data.r, self.data.rt)))

    @staticmethod
    def calculate_bonus_predictions(tournament_ratings, c=1):
        """
        produces array of bonuses based on the array of rating of participants
        """
        tournament_ratings[::-1].sort()
        raw_preds = np.round(rolling_window(tournament_ratings, 15).dot(2.**np.arange(0, -15, -1)) * c)
        samesies = tournament_ratings[:-1] == tournament_ratings[1:]
        for ind in np.nonzero(samesies)[0]:
            raw_preds[ind + 1] = raw_preds[ind]
        return raw_preds

    def calc_bonuses(self, team_rating):
        self.data.sort_values(by='rg', ascending=False, inplace=True)
        self.data['score_pred'] = self.calculate_bonus_predictions(self.data.rg.values, c=team_rating.c)
        self.data['score_real'] = calc_score_real(self.data.score_pred.values, self.data.position.values)
        self.data['bonus_raw'] = calc_bonus_raw(self.data.score_real, self.data.score_pred)
        self.data['bonus'] = self.data.bonus_raw
        self.data.loc[self.data.heredity & (self.data.n_legs > 2), 'bonus'] *= \
            (2 / self.data[self.data.heredity & (self.data.n_legs > 2)]['n_legs'])
        self.data.sort_values(by=['position', 'name'], inplace=True)