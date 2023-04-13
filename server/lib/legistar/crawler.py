import typing as t

from .schema import (
    Action,
    Calendar,
    CalendarRow,
    Legislation,
    LegislationRow,
    Meeting,
    MeetingRow,
)
from .scraper import LegistarScraper


class LegistarCalendarCrawler:
    """
    Crawler for the Legistar Calendar API.
    """

    future_only: bool
    _calendar: Calendar | None
    _meetings: dict[str, Meeting]
    _legislations: dict[str, Legislation]
    _actions: dict[str, Action]

    def __init__(self, customer: str, future_only: bool = False):
        self.customer = customer
        self.future_only = future_only
        self.scraper = LegistarScraper(customer)
        self._calendar = None
        self._meetings = {}
        self._legislations = {}
        self._actions = {}

    def get_calendar(self) -> Calendar:
        if self._calendar is None:
            self._calendar = self.scraper.get_calendar(future_only=self.future_only)
        return self._calendar

    def get_meeting_for_calendar_row(self, row: CalendarRow) -> Meeting:
        id, guid = row.details.id, row.details.guid
        return self.get_meeting(id, guid)

    def get_meeting(self, id: int, guid: str) -> Meeting:
        if id not in self._meetings:
            self._meetings[guid] = self.scraper.get_meeting(id, guid)
        return self._meetings[guid]

    def get_legislation_for_meeting_row(self, row: MeetingRow) -> Legislation:
        id, guid = row.legislation.id, row.legislation.guid
        return self.get_legislation(id, guid)

    def get_legislation(self, id: int, guid: str) -> Legislation:
        if id not in self._legislations:
            self._legislations[guid] = self.scraper.get_legislation(id, guid)
        return self._legislations[guid]

    def get_action_for_legislation_row(self, row: LegislationRow) -> Action:
        id, guid = row.action_details.id, row.action_details.guid
        return self.get_action(id, guid)

    def get_action(self, id: int, guid: str) -> Action:
        if id not in self._actions:
            self._actions[guid] = self.scraper.get_action(id, guid)
        return self._actions[guid]

    def iter_meetings(self) -> t.Iterator[Meeting]:
        for row in self.get_calendar().rows:
            yield self.get_meeting_for_calendar_row(row)

    def iter_legislations(self) -> t.Iterator[Legislation]:
        for meeting in self.iter_meetings():
            for row in meeting.rows:
                yield self.get_legislation_for_meeting_row(row)

    def iter_actions(self) -> t.Iterator[Action]:
        for legislation in self.iter_legislations():
            for row in legislation.rows:
                yield self.get_action_for_legislation_row(row)

    def crawl(self) -> t.Iterator[t.Union[Calendar, Meeting, Legislation, Action]]:
        yield self.get_calendar()
        for meeting in self.iter_meetings():
            yield meeting
        for legislation in self.iter_legislations():
            yield legislation
        for action in self.iter_actions():
            yield action
