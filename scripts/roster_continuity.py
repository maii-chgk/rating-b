import datetime
from abc import ABC, abstractmethod

FIRST_DATE_OF_2021_RULES = datetime.date(2021, 8, 28)
FIRST_DATE_OF_2022_RULES = datetime.date(2022, 10, 29)


class RosterContinuity(ABC):
    @abstractmethod
    def counts(self, base_players: int, legionnaires: int, base_name_used: bool = True):
        pass


class Pre2021Rule(RosterContinuity):
    def counts(self, base_players: int, legionnaires: int, base_name_used: bool = True):
        return (base_players >= 4) | (base_players == 3 & base_name_used)


class MAIIRule2021to2022(RosterContinuity):
    def counts(self, base_players: int, legionnaires: int, base_name_used: bool = True):
        return base_players >= 4


class MAIIRuleFrom2022(RosterContinuity):
    def counts(self, base_players: int, legionnaires: int, base_name_used: bool = True):
        return (base_players >= 3) & (legionnaires < base_players) & (legionnaires <= 3)


def select_rule(date: datetime.date) -> RosterContinuity:
    if date < FIRST_DATE_OF_2021_RULES:
        return Pre2021Rule()
    if date < FIRST_DATE_OF_2022_RULES:
        return MAIIRule2021to2022()
    return MAIIRuleFrom2022()
