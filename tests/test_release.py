import unittest
from datetime import date

from dotenv import load_dotenv
load_dotenv('../.env.test')

import django
django.setup()

from scripts.main import calc_release
from b.models import Team_rating, Tournament_in_release, Player_rating_by_tournament


class TestReleases(unittest.TestCase):
    def test_calc_single_release(self):
        release_date = date(2021, 9, 16)
        calc_release(release_date)

        team_at_first_place = Team_rating.objects.filter(release=2).order_by("place")[0]
        self.assertEqual(45556, team_at_first_place.team_id)
        self.assertEqual(10674, team_at_first_place.rating)
        self.assertEqual(21, team_at_first_place.rating_change)

        team_at_place_53 = Team_rating.objects.filter(release=2).order_by("place")[52]
        self.assertEqual(50186, team_at_place_53.team_id)
        self.assertEqual(7697, team_at_place_53.rating)
        self.assertEqual(-189, team_at_place_53.rating_change)

        team_at_place_400 = Team_rating.objects.filter(release=2).order_by("place")[399]
        self.assertEqual(46627, team_at_place_400.team_id)
        self.assertEqual(5288, team_at_place_400.rating)
        self.assertEqual(0, team_at_place_400.rating_change)

        tournaments_in_release = Tournament_in_release.objects.filter(release=2)
        self.assertEqual([6560, 6639, 7086, 7182, 7513],
                         list(tournaments_in_release.values_list('tournament_id', flat=True)))

        players_in_release = Player_rating_by_tournament.objects.filter(release=2)
        self.assertEqual(2264, players_in_release.get(player_id=80897, tournament_id=6639).cur_score)
        self.assertEqual(2264, players_in_release.get(player_id=80897, tournament_id=6639).initial_score)
        self.assertEqual(1767, players_in_release.get(player_id=80897, tournament_id=6076).cur_score)
        self.assertEqual(1934, players_in_release.get(player_id=80897, tournament_id=6076).initial_score)
        self.assertEqual(9, players_in_release.get(player_id=80897, tournament_id=6076).weeks_since_tournament)
