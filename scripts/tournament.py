import pandas as pd
import numpy as np
from typing import Any, Tuple, Set
import numpy.typing as npt
from .constants import (D2_MULTIPLIER, D2_EXPONENT_DENOMINATOR, MIN_PLAYERS_FOR_HEREDITY,
                        MIN_PLAYERS_FOR_HEREDITY_OLD, MIN_PLAYERS_FOR_HEREDITY_WITH_NAME_OLD,
                        D1_NEGATIVE_LOWERING_COEFFICIENT, MIN_TOURNAMENT_TO_RELEASE_RATING_RATIO, TEAMS_COUNT_FOR_BP,
                        MAX_BONUS, MIN_LEGIONNAIRES_TO_REDUCE_BONUS, REGULAR_TOURNAMENT_COEFFICIENT,
                        STRICT_SYNCHRONOUS_TOURNAMENT_COEFFICIENT, SYNCHRONOUS_TOURNAMENT_COEFFICIENT)
from scripts import tools
from b import models


class EmptyTournamentException(Exception):
    pass


class Tournament:
    def __init__(self, cursor, trnmt_from_db: models.Tournament, release: models.Release, verbose: bool=False):
        self.coeff = self.tournament_type_to_coeff(trnmt_from_db.typeoft_id)
        self.id = trnmt_from_db.id
        self.release_id = release.id
        self.is_in_maii_rating = trnmt_from_db.maii_rating
        teams = {}
        if verbose:
            print(f'Loading tournament {self.id}...')
        for team_score in trnmt_from_db.team_score_set.select_related('team'):
            if team_score.position in (0, 9999):
                print(f'Tournament {self.id}: team {team_score.id} ({team_score.team.title}) has incorrect place {team_score.position}! Skipping this team.')
                continue
            teams[team_score.team_id] = {
                'team_id': team_score.team_id,
                'name': team_score.team.title,
                'current_name': team_score.title,
                'questionsTotal': team_score.total,
                'position': float(team_score.position), # it's of type Decimal (whatever it is) for some reason
                'n_base': 0,
                'n_legs': 0,
                'teamMembers': [],
                'baseTeamMembers': [],
            }
        if len(teams) == 0:
            raise EmptyTournamentException(f"There are no teams.")
        for team_player in trnmt_from_db.roster_set.all():
            if team_player.team_id not in teams:
                print(f'Tournament {self.id}, team {team_player.team_id}: player {team_player.player_id} is in roster but the team did not play there!')
                continue
            teams[team_player.team_id]['teamMembers'].append(team_player.player_id)
            if team_player.flag == 'Б':
                teams[team_player.team_id]['n_base'] += 1
                teams[team_player.team_id]['baseTeamMembers'].append(team_player.player_id)
            else:
                teams[team_player.team_id]['n_legs'] += 1

        teams_without_players = [team_id for team_id, team_data in teams.items() if len(team_data['teamMembers']) == 0]
        if teams_without_players:
            raise EmptyTournamentException(f'There are {len(teams_without_players)} teams without any players. First such team: {teams_without_players[0]}.')
        self.data = pd.DataFrame(teams.values())
        if release.date < tools.FIRST_NEW_RELEASE:
            self.data['heredity'] = (self.data.n_base >= MIN_PLAYERS_FOR_HEREDITY_OLD) | \
                                    (self.data.n_base == MIN_PLAYERS_FOR_HEREDITY_WITH_NAME_OLD) & (
                                                self.data.name == self.data.current_name)
        else:
            self.data['heredity'] = self.data.n_base >= MIN_PLAYERS_FOR_HEREDITY

    def add_ratings(self, team_rating, player_rating):
        self.data['rt'] = self.data.teamMembers.map(lambda x: player_rating.calc_rt(x, team_rating.q))
        self.data['r'] = np.where(self.data.heredity, self.data.team_id.map(team_rating.get_team_rating), 0)
        self.data['rb'] = np.where(self.data.heredity, self.data.team_id.map(team_rating.get_trb), 0)
        self.data['rg'] = np.where(self.data.rb, self.data.r * self.data.rt / self.data.rb, self.data.rt)
        self.data['rg'] = np.where(self.data.rt < self.data.rb,
                                   np.maximum(self.data.rg, MIN_TOURNAMENT_TO_RELEASE_RATING_RATIO * self.data.r),
                                   np.minimum(self.data.rg, np.maximum(self.data.r, self.data.rt)))
        self.data['expected_place'] = tools.calc_places(self.data['rg'].values)

    @staticmethod
    def calculate_bonus_predictions(tournament_ratings: npt.ArrayLike, c=1):
        """
        produces array of bonuses based on the array of game ratings of participants
        :parameter tournament_ratings - sorted descendingly game ratings (rg) of teams
        """
        raw_preds = np.round(tools.rolling_window(tournament_ratings, TEAMS_COUNT_FOR_BP).dot(
            2. ** np.arange(0, -TEAMS_COUNT_FOR_BP, -1)) * c)
        samesies = tournament_ratings[:-1] == tournament_ratings[1:]
        for ind in np.nonzero(samesies)[0]:
            raw_preds[ind + 1] = raw_preds[ind]
        return raw_preds

    def calc_d1(self):
        d_one = self.data.score_real - self.data.score_pred
        d_one[d_one < 0] *= D1_NEGATIVE_LOWERING_COEFFICIENT
        return d_one

    def calc_bonuses(self, team_rating):
        self.data.sort_values(by='rg', ascending=False, inplace=True)
        self.data['score_pred'] = self.calculate_bonus_predictions(self.data.rg.values, c=team_rating.c)
        self.data['score_real'] = tools.calc_score_real(self.data.score_pred.values, self.data.position.values)
        self.data['D1'] = self.calc_d1()
        self.data['D2'] = D2_MULTIPLIER * np.exp((self.data.score_real - MAX_BONUS) / D2_EXPONENT_DENOMINATOR)
        self.data['bonus_raw'] = (self.coeff * (self.data['D1'] + self.data['D2'])).astype('int')
        self.data['bonus'] = self.data.bonus_raw
        self.data.loc[self.data.heredity & (self.data.n_legs >= MIN_LEGIONNAIRES_TO_REDUCE_BONUS), 'bonus'] *= \
            (2 / self.data[self.data.heredity & (self.data.n_legs >= MIN_LEGIONNAIRES_TO_REDUCE_BONUS)]['n_legs'])
        self.data.sort_values(by=['position', 'name'], inplace=True)

    def apply_bonuses(self, team_rating, player_rating) -> Tuple[Any, Any]:
        for i, team in self.data.iterrows():
            if team['heredity']:
                team_rating.data.at[team['team_id'], 'rating'] += team['bonus']
            for player_id in team['teamMembers']:
                bonus = models.Player_rating_by_tournament(
                    release_id=self.release_id,
                    player_id=player_id,
                    weeks_since_tournament=0,
                    tournament_id=self.id,
                    initial_score=team['score_real'],
                    cur_score=team['score_real'],
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
        if ttype in {models.TRNMT_TYPE_REGULAR, models.TRNMT_TYPE_REGIONAL}:
            return REGULAR_TOURNAMENT_COEFFICIENT
        if ttype == models.TRNMT_TYPE_STRICT_SYNCHRONOUS:
            return STRICT_SYNCHRONOUS_TOURNAMENT_COEFFICIENT
        if ttype in models.TRNMT_TYPES:
            return SYNCHRONOUS_TOURNAMENT_COEFFICIENT
        raise Exception(f"tournament type {ttype} is not supported!")
