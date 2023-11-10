from django.db.models import F, Q
import datetime
from typing import Dict, List, Optional

from b import models
import pandas as pd


def fast_insert(cursor, table: str, columns: str, rows: List[str], schema: str = 'b'):
    """
    Insert provided list of rows to provided table, 100 items for query
    :param cursor:
    :param schema:
    :param table:
    :param columns:
    :param rows:
    :return:
    """
    BATCH_SIZE = 5000
    for i in range(0, len(rows), BATCH_SIZE):
        cursor.execute(f'INSERT INTO {schema}.{table} ({columns}) VALUES ' + ', '.join(rows[i:i + BATCH_SIZE]) + ';')


def get_season(release_date: datetime.date) -> models.Season:
    return models.Season.objects.get(start__lte=release_date, end__gte=release_date)


def get_base_teams_for_players(release_date: datetime.date) -> pd.Series:
    season = get_season(release_date)
    base_teams = season.season_roster_set.filter(
        Q(start_date=None) | Q(start_date__lte=release_date),
        Q(end_date=None) | Q(end_date__lte=release_date)
    ).annotate(base_team_id=F('team_id')).values('player_id', 'base_team_id', 'start_date')
    bs_pd = pd.DataFrame(base_teams)
    return bs_pd.sort_values("start_date").groupby("player_id").last().base_team_id.astype("Int64")


def get_teams_with_new_players(old_release: datetime.date, new_release: datetime.date) -> List[int]:
    return list(models.Season_roster.objects.filter(
        start_date__gt=old_release, start_date__lte=new_release).values_list(
        'team_id', flat=True).distinct())


def get_tournament_end_dates() -> Dict[int, datetime.date]:
    res = {}
    for tournament in models.Tournament.objects.all().values('pk', 'end_datetime'):
        res[tournament['pk']] = tournament['end_datetime'].date()
    return res
