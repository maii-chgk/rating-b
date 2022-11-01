import unittest
from scripts.roster_continuity import *


class TestRosterContinuity(unittest.TestCase):
    def test_rule_selection(self):
        old_rule = select_rule(datetime.date(2019, 1, 1))
        self.assertIs(old_rule, Pre2021Rule)


if __name__ == '__main__':
    unittest.main()
