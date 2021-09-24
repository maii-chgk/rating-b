import pandas as pd
import numpy as np
from typing import Any, Tuple, Set
import numpy.typing as npt

from scripts.tools import rolling_window, calc_score_real
from b import models

class EmptyTournamentException(Exception):
    pass

class Tournament:
    def __init__(self, cursor, tournament_id: int, release: models.Release):
        cursor.execute(f'SELECT typeoft_id FROM rating_tournament WHERE id = {tournament_id}')
        self.type = cursor.fetchone()[0]
        self.coeff = self.tournament_type_to_coeff(self.type)
        self.id = tournament_id
        self.release_id = release.id
        cursor.execute(f'SELECT rteam.id f1, rp.id f2, otr."inRating", rteam.title, rr.team_title, rr.total, rr.position, o_r.flag '
                       + 'FROM public.rating_result rr, public."rating_result_teamMembers" rrt, public.rating_tournament rt, public.rating_team rteam, '
                       + 'public.rating_player rp, public.rating_oldteamrating otr, public.rating_oldrating o_r '
                       + f'WHERE rt.id={tournament_id} AND rr.tournament_id=rt.id AND rrt.result_id=rr.id AND rteam.id=rr.team_id AND rrt.player_id=rp.id AND otr.result_id=rr.id '
                       + f'AND rr.position!=9999 AND o_r.result_id=rr.id AND o_r.player_id=rp.id AND rr.position != 0;')
        teams = {}
        for team_id, player_id, in_rating, team_name, cur_title, total, position, flag in cursor.fetchall():
            if team_id not in teams:
                teams[team_id] = {
                    'team_id': team_id,
                    'name': team_name,
                    'current_name': cur_title,
                    'questionsTotal': total,
                    'position': float(position), # it's of type Decimal (whatever it is) for some reason
                    'n_base': 0,
                    'n_legs': 0,
                    'teamMembers': [],
                    'baseTeamMembers': []
                }
            teams[team_id]['teamMembers'].append(player_id)
            if flag in {'Б', 'К'}:
                teams[team_id]['n_base'] += 1
                teams[team_id]['baseTeamMembers'].append(player_id)
            else:
                teams[team_id]['n_legs'] += 1
        print(f'Tournament id: {tournament_id}. teams: {len(teams)}')
        if len(teams) == 0:
            raise EmptyTournamentException(f"Tournament {tournament_id} is empty!")
        self.data = pd.DataFrame(teams.values())
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
    def calculate_bonus_predictions(tournament_ratings: npt.ArrayLike, c=1):
        """
        produces array of bonuses based on the array of game ratings of participants
        :parameter tournament_ratings - sorted descendingly game ratings (rg) of teams
        """
        raw_preds = np.round(rolling_window(tournament_ratings, 15).dot(2.**np.arange(0, -15, -1)) * c)
        samesies = tournament_ratings[:-1] == tournament_ratings[1:]
        for ind in np.nonzero(samesies)[0]:
            raw_preds[ind + 1] = raw_preds[ind]
        return raw_preds

    def calc_d1(self):
        d_one = self.data.score_real - self.data.score_pred
        d_one[d_one < 0] *= 0.5
        return d_one

    def calc_bonuses(self, team_rating):
        self.data.sort_values(by='rg', ascending=False, inplace=True)
        self.data['score_pred'] = self.calculate_bonus_predictions(self.data.rg.values, c=team_rating.c)
        self.data['score_real'] = calc_score_real(self.data.score_pred.values, self.data.position.values)
        self.data['D1'] = self.calc_d1()
        self.data['D2'] = 300 * np.exp((self.data.score_real - 2300) / 350)
        self.data['bonus_raw'] = (self.coeff * (self.data['D1'] + self.data['D2'])).astype('int')
        self.data['bonus'] = self.data.bonus_raw
        self.data.loc[self.data.heredity & (self.data.n_legs > 2), 'bonus'] *= \
            (2 / self.data[self.data.heredity & (self.data.n_legs > 2)]['n_legs'])
        self.data.sort_values(by=['position', 'name'], inplace=True)

    def apply_bonuses(self, team_rating, player_rating) -> Tuple[Any, Any]:
        for i, team in self.data.iterrows():
            if team['heredity']:
                team_rating.data.loc[team['team_id']]['rating'] += team['bonus']
            for player_id in team['teamMembers']:
                bonus = models.Player_rating_by_tournament(
                    release_id=self.release_id,
                    player_id=player_id,
                    weeks_since_tournament=0,
                    tournament_id=self.id,
                    initial_score=team['bonus'],
                    cur_score=team['bonus'],
                )
                bonus.raw_cur_score = bonus.cur_score
                player_rating.data.loc[player_id]['top_bonuses'].append(bonus)
        return team_rating, player_rating

    def get_new_player_ids(self, existing_players: Set[int]) -> Set[int]:
        res = set()
        for i, team in self.data.iterrows():
            for player_id in team['teamMembers']:
                if player_id not in existing_players:
                    res.add(player_id)
        return res

    @staticmethod
    def tournament_type_to_coeff(ttype: int) -> float:
        if ttype in {2, 4}:
            return 1.0
        if ttype == 6:
            return 2./3.
        if ttype == 3:
            return 0.5
        else:
            raise Exception(f"tournament type {ttype} is not supported!")


