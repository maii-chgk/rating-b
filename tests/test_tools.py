import unittest
import datetime

from scripts import tools


class TestTools(unittest.TestCase):
    def test_get_releases_difference(self):
        self.assertEqual(1, tools.get_releases_difference(datetime.date(2020, 4, 3), datetime.date(2021, 9, 9)))
        self.assertEqual(2, tools.get_releases_difference(datetime.date(2020, 4, 3), datetime.date(2021, 9, 16)))
        self.assertEqual(4, tools.get_releases_difference(datetime.date(2020, 3, 20), datetime.date(2021, 9, 16)))
        with self.assertRaises(AssertionError) as _:
            tools.get_releases_difference(datetime.date(2020, 3, 21), datetime.date(2021, 9, 16))

    def test_get_age_in_weeks(self):
        self.assertEqual(0, tools.get_age_in_weeks(datetime.date(2021, 9, 3), datetime.date(2021, 9, 9)))
        self.assertEqual(1, tools.get_age_in_weeks(datetime.date(2021, 9, 3), datetime.date(2021, 9, 16)))
        self.assertEqual(2, tools.get_age_in_weeks(datetime.date(2020, 4, 1), datetime.date(2021, 9, 16)))
        with self.assertRaises(AssertionError) as _:
            tools.get_age_in_weeks(datetime.date(2021, 9, 13), datetime.date(2021, 9, 9))

    def test_get_prev_release_date(self):
        self.assertEqual(datetime.date(2020, 4, 3), tools.get_prev_release_date(datetime.date(2021, 9, 9)))
        self.assertEqual(datetime.date(2021, 9, 16), tools.get_prev_release_date(datetime.date(2021, 9, 23)))
        self.assertEqual(datetime.date(2020, 3, 27), tools.get_prev_release_date(datetime.date(2020, 4, 3)))
        with self.assertRaises(AssertionError) as _:
            tools.get_prev_release_date(datetime.date(2021, 9, 13))


if __name__ == '__main__':
    unittest.main()
