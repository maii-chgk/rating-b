import unittest
from datetime import date

import django
django.setup()

from scripts.main import calc_release
from b import models


class TestReleases(unittest.TestCase):
    def test_calc_single_release(self):
        release_date = date(2021, 9, 16)
        calc_release(release_date)
        release = models.Release.objects.get(date=release_date)
        self.assertEqual(201835736, release.hash)
