from django.db.models import F, Q
import datetime
from typing import Optional, List, Dict

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
    BATCH_SIZE = 200000
    for i in range(0, len(rows), BATCH_SIZE):
        cursor.execute(f'INSERT INTO {schema}.{table} ({columns}) VALUES ' + ', '.join(rows[i:i + BATCH_SIZE]) + ';')


def get_season(cursor, release_date: datetime.date) -> models.Season:
    return models.Season.objects.get(start__date__lte=release_date, end__date__gte=release_date)


def get_base_teams_for_players(cursor, release_date: datetime.date) -> pd.Series:
    season = get_season(cursor, release_date)
    base_teams = season.season_roster_set.filter(
        Q(start_date=None) | Q(start__date__lte=release_date),
        Q(end_date=None) | Q(end_date__lte=release_date)
    ).annotate(base_team_id=F('team_id')).values('player_id', 'base_team_id')
    bs_pd = pd.DataFrame(base_teams)
    return bs_pd.sort_values("start_date").groupby("player_id").last().base_team_id.astype("Int64")


def get_teams_with_new_players(cursor, old_release: datetime.date, new_release: datetime.date):
    old_string = old_release.isoformat()
    new_string = new_release.isoformat()
    query = f"SELECT DISTINCT team_id FROM public.base_rosters " \
            f"WHERE start_date <= \'{new_string}\' AND start_date > \'{old_string}\';"
    cursor.execute(query)
    return [entry.team_id for entry in cursor.fetchall()]


def get_tournament_end_date(cursor, tournament_id: int) -> datetime.date:
    cursor.execute(f'SELECT end_datetime FROM public.rating_tournament WHERE id={tournament_id};')
    return cursor.fetchone()[0].date()

def get_tournament_end_dates(cursor) -> Dict[int, datetime.date]:
    cursor.execute(f'SELECT id, end_datetime FROM public.rating_tournament;')
    res = {}
    for t_id, dt in cursor.fetchall():
        res[t_id] = dt.date()
    return res
