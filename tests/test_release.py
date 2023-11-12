import unittest
from datetime import date

from dotenv import load_dotenv
load_dotenv('../.env.test')

import django
django.setup()

from scripts.main import calc_release
from b.models import Team_rating, Tournament_in_release, Player_rating_by_tournament


class TestReleases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        release_date = date(2021, 9, 16)
        calc_release(release_date)

    def test_team_rating_values(self):
        team_at_first_place = Team_rating.objects.filter(release=3).order_by("place")[0]
        self.assertEqual(45556, team_at_first_place.team_id)
        self.assertEqual(10737, team_at_first_place.rating)
        self.assertEqual(63, team_at_first_place.rating_change)

        team_at_place_57 = Team_rating.objects.filter(release=3).order_by("place")[56]
        self.assertEqual(65268, team_at_place_57.team_id)
        self.assertEqual(7653, team_at_place_57.rating)
        self.assertEqual(-82, team_at_place_57.rating_change)

        team_at_place_400 = Team_rating.objects.filter(release=3).order_by("place")[399]
        self.assertEqual(46627, team_at_place_400.team_id)
        self.assertEqual(5288, team_at_place_400.rating)
        self.assertEqual(0, team_at_place_400.rating_change)

    def test_tournaments_in_release_values(self):
        tournaments_in_release = Tournament_in_release.objects.filter(release=3)
        self.assertEqual([6044, 6114, 7225, 7325],
                         list(tournaments_in_release.values_list('tournament_id', flat=True)))

    def test_player_rating_by_tournament_values(self):
        players_in_release = Player_rating_by_tournament.objects.filter(release=3)
        self.assertEqual(1794, players_in_release.get(player_id=77673, tournament_id=7225).cur_score)
        self.assertEqual(1794, players_in_release.get(player_id=77673, tournament_id=7225).initial_score)
        self.assertEqual(1933, players_in_release.get(player_id=77673, tournament_id=5923).cur_score)
        self.assertEqual(2053, players_in_release.get(player_id=77673, tournament_id=5923).initial_score)
        self.assertEqual(6, players_in_release.get(player_id=77673, tournament_id=5923).weeks_since_tournament)
