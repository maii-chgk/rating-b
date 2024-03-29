import urllib.request
import json
import pandas as pd


def url2json(url):
    response = urllib.request.urlopen(url)
    return json.load(response)


def get_players_release(release_id):
    """
    https://rating.chgk.info/players.php?release=1425&download_data=export_release
    :return:
    """
    players_pd = pd.read_csv(
        f"https://rating.chgk.info/players.php"
        f"?release={release_id}&download_data=export_release"
    )
    return players_pd


def get_teams_release(release_id):
    teams_pd = pd.read_csv(
        f"https://rating.chgk.info/teams.php"
        f"?release={release_id}&download_data=export_release"
    )
    return teams_pd
