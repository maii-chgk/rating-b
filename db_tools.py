import datetime
from typing import Optional, List, Dict

import pandas as pd


def get_release_id(cursor, release_date: datetime.date, schema: str = 'b') -> Optional[int]:
    """
    Reads the ID for release in given schema with provided date
    :param cursor:
    :param schema:
    :param release_date:
    :return:
    """
    cursor.execute(f'SELECT id FROM {schema}.release_details WHERE date::date=\'{release_date.isoformat()}\'')
    print(f'SELECT id FROM {schema}.release_details WHERE date::date=\'{release_date.isoformat()}\'')
    res = cursor.fetchall()[0]
    if not res:
        print(f'No release with date {release_date} found in {schema}.release_details!')
        return None
    print(f'Release id with date {release_date}: {res[0]}')
    return res[0]


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
    for i in range(0, len(rows), 100):
        cursor.execute(f'INSERT INTO {schema}.{table} ({columns}) VALUES ' + ', '.join(rows[i:i + 100]) + ';')


def get_season_id(cursor, release_date: datetime.date) -> int:
    cursor.execute(f'SELECT id FROM public.rating_season WHERE start::date <= \'{release_date.isoformat()}\' AND "end"::date >= \'{release_date.isoformat()}\';')
    return cursor.fetchone()[0]


def get_base_teams_for_players(cursor, release_date: datetime.date) -> pd.Series:
    season_id = get_season_id(cursor, release_date)
    cursor.execute(f'SELECT player_id, team_id base_team_id , start FROM public.rating_basesquad '
        + f'WHERE season_id={season_id} AND start::date <= \'{release_date.isoformat()}\';')
    bs_pd = pd.DataFrame(cursor.fetchall())
    return bs_pd.sort_values("start").groupby("player_id").last().base_team_id
