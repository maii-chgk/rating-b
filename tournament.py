# from rating_api.tournaments import get_tournament_results
from tools import rolling_window, calc_score_real, calc_bonus_raw
import pandas as pd
import numpy as np
from typing import Any, Tuple


class Tournament:
    def __init__(self, tournament_id, teams_dict=None):
        self.id = tournament_id
        if teams_dict is not None:
            self.data = pd.DataFrame(teams_dict.values())
        # else:
        #     raw_results = get_tournament_results(tournament_id, recaps=True)
        #     self.data = pd.DataFrame([
        #         {
        #             'team_id': t['team']['id'],
        #             'name': t['team']['name'],
        #             'current_name': t['current']['name'],
        #             'questionsTotal': t['questionsTotal'],
        #             'position': t['position'],
        #             'n_base': sum(player['flag'] in {'Б', 'К'} for player in t['teamMembers']),
        #             'n_legs': sum(player['flag'] not in {'Б', 'К'} for player in t['teamMembers']),
        #             'teamMembers': [x['player']['id'] for x in t['teamMembers']],
        #             'baseTeamMembers': [x['player']['id'] for x in t['teamMembers'] if x['flag'] in {'Б', 'К'}]
        #         } for t in raw_results if t['position'] != 9999
        #     ])
        self.data['heredity'] = (self.data.n_base > 3) | (self.data.n_base == 3) & \
                                (self.data.name == self.data.current_name)

    def add_ratings(self, team_rating, player_rating):
        self.data['rt'] = self.data.teamMembers.map(lambda x: player_rating.calc_rt(x, team_rating.q))
        self.data['r'] = np.where(self.data.heredity, self.data.team_id.map(team_rating.get_team_rating), 0)
        self.data['rb'] = np.where(self.data.heredity, self.data.team_id.map(team_rating.get_trb), 0)
        self.data['rg'] = np.where(self.data.rb, self.data.r * self.data.rt / self.data.rb, self.data.rt)
        self.data['rg'] = np.where(self.data.rt < self.data.rb, np.maximum(self.data.rg, 0.5 * self.data.r),
                                   np.minimum(self.data.rg, np.maximum(self.data.r, self.data.rt)))

    @staticmethod
    def calculate_bonus_predictions(tournament_ratings, c=1):
        """
        produces array of bonuses based on the array of game ratings of participants
        :parameter tournament_ratings - sorted descendingly game ratings (rg) of teams
        """
        raw_preds = np.round(rolling_window(tournament_ratings, 15).dot(2.**np.arange(0, -15, -1)) * c)
        samesies = tournament_ratings[:-1] == tournament_ratings[1:]
        for ind in np.nonzero(samesies)[0]:
            raw_preds[ind + 1] = raw_preds[ind]
        return raw_preds

    def calc_bonuses(self, team_rating):
        self.data.sort_values(by='rg', ascending=False, inplace=True)
        self.data['score_pred'] = self.calculate_bonus_predictions(list(self.data.rg.values), c=team_rating.c)
        self.data['score_real'] = calc_score_real(self.data.score_pred.values, self.data.position.values)
        self.data['bonus_raw'] = calc_bonus_raw(self.data.score_real, self.data.score_pred)
        self.data['bonus'] = self.data.bonus_raw
        self.data.loc[self.data.heredity & (self.data.n_legs > 2), 'bonus'] *= \
            (2 / self.data[self.data.heredity & (self.data.n_legs > 2)]['n_legs'])
        self.data.sort_values(by=['position', 'name'], inplace=True)

    def apply_bonuses(self, team_rating, player_rating) -> Tuple[Any, Any]:
        for i, team in self.data.iterrows():
            if team['heredity']:
                team_rating.data.loc[team['team_id']]['rating'] += team['bonus']
            for player_id in team['teamMembers']:
                player_rating.data.loc[player_id]['top_bonuses'].append((self.id, team['bonus'], team['bonus']))
        return team_rating, player_rating

    def get_new_player_ids(self, existing_players: set[int]) -> set[int]:
        res = set()
        for i, team in self.data.iterrows():
            for player_id in team['teamMembers']:
                if player_id not in existing_players:
                    res.add(player_id)
        return res
