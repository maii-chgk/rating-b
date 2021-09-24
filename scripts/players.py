import pandas as pd
from typing import List, Tuple

from .tools import calc_tech_rating, get_age_in_weeks
from .api_util import get_players_release
from .db_tools import get_release_id, get_base_teams_for_players, get_tournament_end_date
from scripts import constants
from scripts import db_tools
from b import models


class PlayerRating:
    def __init__(self, release=None, release_for_squads=None, file_path=None,
                 cursor=None, schema='b', api_release_id=None):
        self.data = pd.DataFrame()
        if api_release_id:
            print(f'Creating PlayerRating by old API from release_id {api_release_id}')
            raw_rating = get_players_release(api_release_id)
            raw_rating = raw_rating[[' ИД', 'ИД базовой команды', 'Рейтинг']]
            raw_rating.columns = ['player_id', 'base_team_id', 'rating']
            raw_rating.drop_duplicates(subset='player_id', inplace=True)
            self.data = raw_rating.set_index('player_id')
            self.data['prev_rating'] = None
            self.data['top_bonuses'] = [[] for _ in range(len(self.data))]
            return
        if file_path:
            self.data = pd.DataFrame.from_csv(file_path, index_col=0)
            return
        if cursor is None:
            raise Exception("no file_path or cursor is passed")
        if release is None:
            raise Exception("no release is passed")
        if release_for_squads is None:
            raise Exception("no release for squads is passed")
        cursor.execute('SELECT player_id, rating '
                       + f'FROM {schema}.player_rating '
                       + f'WHERE release_id={release.id};')
        players_dict = {player_id: {'player_id': player_id, 'rating': rating, 'top_bonuses': []}
                        for player_id, rating in cursor.fetchall()}

        tournament_end_dates = db_tools.get_tournament_end_dates(cursor)
        cursor.execute('SELECT player_id, tournament_id, rating_now, rating_original '
                       + f'FROM public.rating_individual_old_details ORDER BY rating_now;')
        n_weeks_by_tournament_id = {}
        i = 0
        for player_id, tournament_id, rating_now, rating_original in cursor.fetchall():
            i += 1
            if (i % 10000) == 0:
                print (i, len(n_weeks_by_tournament_id))
            if player_id in players_dict:
                if tournament_id not in n_weeks_by_tournament_id:
                    n_weeks_by_tournament_id[tournament_id] = get_age_in_weeks(tournament_end_dates[tournament_id], release_for_squads.date)
                bonus = models.Player_rating_by_tournament(
                    release_id=release.id,
                    player_id=player_id,
                    weeks_since_tournament=n_weeks_by_tournament_id[tournament_id],
                    tournament_id=tournament_id,
                    initial_score=rating_original,
                    cur_score=rating_now,
                )
                players_dict[player_id]['top_bonuses'].append(bonus)
        # adding base_team_ids
        self.data = pd.DataFrame(players_dict.values()).set_index("player_id").join(
            get_base_teams_for_players(cursor, release_for_squads.date), how='left')

    def calc_rt(self, player_ids, q=None):
        """
        вычисляет тех рейтинг по списку id игроков
        """
        prs = self.data.rating.reindex(player_ids).fillna(0).values
        return calc_tech_rating(prs, q)

    def calc_tech_rating_all_teams(self, q=None) -> pd.Series:
        """
        Рассчитывает технический рейтинг по базовому составу для всех команд, у которых есть
        хотя бы один приписанный к ним игрок
        :return: pd.Series, name: rating, index: base_team_id, values: техрейтинги
        """
        res = self.data.groupby('base_team_id')['rating'].apply(
            lambda x: calc_tech_rating(x.values, q))
        res.name = "trb"
        return res

    # Multiplies all existing bonuses by J_i constant
    def reduce_rating(self):
        def reduce_vector(player_ratings: List[models.Player_rating_by_tournament]) -> List[models.Player_rating_by_tournament]:
            for player_rating in player_ratings:
                player_rating.recalc_cur_score()
            return player_ratings
        self.data['top_bonuses'] = self.data['top_bonuses'].map(reduce_vector)

    # Removes all bonuses except top 7 and updates rating for each player
    def recalc_rating(self):
        def leave_top_N(v: List[models.Player_rating_by_tournament]) -> List[models.Player_rating_by_tournament]:
            return sorted(v, key=lambda x: -x.raw_cur_score)[:constants.N_BEST_TOURNAMENTS_FOR_PLAYER_RATING]
        self.data['top_bonuses'] = self.data['top_bonuses'].map(leave_top_N)

        def sum_ratings_now(v: List[models.Player_rating_by_tournament]) -> int:
            return sum(x.cur_score for x in v)
        self.data['rating'] = self.data['top_bonuses'].map(sum_ratings_now)
