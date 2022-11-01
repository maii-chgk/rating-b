import unittest
from scripts.roster_continuity import *


class TestRosterContinuity(unittest.TestCase):
    def test_rule_selection_before_maii(self):
        old_rule = select_rule(datetime.date(2019, 1, 1))
        self.assertIsInstance(old_rule, Pre2021Rule)

    def test_rule_selection_first_maii_rule(self):
        late_2021_rule = select_rule(datetime.date(2021, 12, 1))
        self.assertIsInstance(late_2021_rule, MAIIRule2021to2022)

    def test_rule_selection_second_maii_rule(self):
        late_2021_rule = select_rule(datetime.date(2022, 12, 1))
        self.assertIsInstance(late_2021_rule, MAIIRuleFrom2022)


if __name__ == '__main__':
    unittest.main()
