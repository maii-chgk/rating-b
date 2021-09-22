import numpy as np
import pandas as pd
import datetime
import decimal


def rolling_window(a, window):
    a = np.append(a, np.zeros(window - 1))
    shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
    strides = a.strides + (a.strides[-1],)
    return np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)


def calc_tech_rating(players_ratings, q=None):
    pr_sorted = np.sort(players_ratings)[::-1]
    coeffs = np.zeros(pr_sorted.size)
    coeffs[:6] = (np.arange(6, 0, -1) / 6)[:coeffs.size]
    tech_rating = np.round(pr_sorted.dot(coeffs))
    if q is not None:
        tech_rating *= q
    return tech_rating


def calc_score_real(predicted_scores, positions):
    positions = positions - 1
    pos_counts = pd.Series(positions).value_counts().reset_index()
    pos_counts.columns = ['pos', 'n_teams']
    pos_counts['bonus'] = pos_counts.apply(
        lambda x: np.mean(predicted_scores[
                          int(x.pos - (x.n_teams - 1) / 2): int(x.pos + (x.n_teams - 1) / 2) + 1]),
        axis=1)
    return np.round(pos_counts.set_index('pos').loc[positions, 'bonus'].values)

# Find the gap between two releases in weeks.
# There are no releases between 2020-04-03 and 2021-09-09; the gap between them is 1.
# Releases before 2020-04-03 must be on Friday; releases after 2021-09-09 must be on Thursday.
LAST_OLD_RELEASE = datetime.date(2020, 4, 3)
FIRST_NEW_RELEASE = datetime.date(2021, 9, 9)
THURSDAY = 3
FRIDAY = 4
def get_releases_difference(release1: datetime.date, release2: datetime.date) -> int:
    if release1 > release2:
        raise AssertionError(f'First release must be before second release but {release1} > {release2}.')
    for release in [release1, release2]:
        if LAST_OLD_RELEASE < release < FIRST_NEW_RELEASE:
            raise AssertionError(f'{release} is between old releases and new releases.')
        if (release <= LAST_OLD_RELEASE) and (release.weekday() != FRIDAY):
            raise AssertionError(f'{release} is before {LAST_OLD_RELEASE} and is not on Friday.')
        if (release >= FIRST_NEW_RELEASE) and (release.weekday() != THURSDAY):
            raise AssertionError(f'{release} is before {FIRST_NEW_RELEASE} and is not on Thursday.')
    if  release1 <= LAST_OLD_RELEASE < FIRST_NEW_RELEASE <= release2:
        return ((release2 - FIRST_NEW_RELEASE).days // 7) + 1 + ((LAST_OLD_RELEASE - release1).days // 7)
    return (release2 - release1).days // 7


def next_weekday(d, weekday):
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)


def get_release_date(tournament_end: datetime.date) -> datetime.date:
    if LAST_OLD_RELEASE < tournament_end < (FIRST_NEW_RELEASE - datetime.timedelta(days=7)):
        raise AssertionError(f'{release} is between old releases and new releases.')
    return next_weekday(tournament_end, FRIDAY if (tournament_end <= LAST_OLD_RELEASE) else THURSDAY)


# Find such n that we should multiply bonus for given tournament when calculating players bonuses for given release by 0.99^n.
# Old tournaments that end from from Friday till Thursday belong
def get_age_in_weeks(tournament_end: datetime.date, release_date: datetime.date) -> int:
    tournament_release_date = get_release_date(tournament_end)
    if tournament_release_date > release_date:
        raise AssertionError(f'Tournament date {tournament_end} is for future release compared with {release_date}.')
    return get_releases_difference(tournament_release_date, release_date)
