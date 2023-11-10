import unittest
from datetime import date

from dotenv import load_dotenv
load_dotenv()

import django
django.setup()

from scripts.main import calc_release
from b import models


class TestReleases(unittest.TestCase):
    def test_calc_single_release(self):
        release_date = date(2021, 9, 16)
        calc_release(release_date)

        team_at_first_place = models.Team_rating.objects.filter(release=2).order_by("place")[0]
        self.assertEqual(45556, team_at_first_place.team_id)
        self.assertEqual(10674, team_at_first_place.rating)
        self.assertEqual(21, team_at_first_place.rating_change)

        team_at_place_53 = models.Team_rating.objects.filter(release=2).order_by("place")[52]
        self.assertEqual(50186, team_at_place_53.team_id)
        self.assertEqual(7697, team_at_place_53.rating)
        self.assertEqual(-189, team_at_place_53.rating_change)

        team_at_place_400 = models.Team_rating.objects.filter(release=2).order_by("place")[399]
        self.assertEqual(46627, team_at_place_400.team_id)
        self.assertEqual(5288, team_at_place_400.rating)
        self.assertEqual(0, team_at_place_400.rating_change)
