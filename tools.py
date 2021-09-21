import numpy as np
import pandas as pd
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
