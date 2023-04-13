import sys
import typing as t

from .scraper import LegistarScraper
from .web_schema import (
    ActionSchema,
    CalendarRowSchema,
    CalendarSchema,
    LegislationRowSchema,
    LegislationSchema,
    MeetingRowSchema,
    MeetingSchema,
)


class LegistarCalendarCrawler:
    """
    Crawler for the Legistar Calendar API.
    """

    future_only: bool
    debug: bool
    _calendar: CalendarSchema | None
    _meetings: dict[str, MeetingSchema]
    _legislations: dict[str, LegislationSchema]
    _actions: dict[str, ActionSchema]

    def __init__(self, customer: str, future_only: bool = False, debug: bool = False):
        self.customer = customer
        self.future_only = future_only
        self.debug = debug
        self.scraper = LegistarScraper(customer)
        self._calendar = None
        self._meetings = {}
        self._legislations = {}
        self._actions = {}

    def get_calendar(self) -> CalendarSchema:
        if self._calendar is None:
            if self.debug:
                print(">>>> DEBUG: get_calendar()", file=sys.stderr)
            self._calendar = self.scraper.get_calendar(future_only=self.future_only)
        return self._calendar

    def get_meeting_for_calendar_row(self, row: CalendarRowSchema) -> MeetingSchema:
        id, guid = row.details.id, row.details.guid
        return self.get_meeting(id, guid)

    def get_meeting(self, id: int, guid: str) -> MeetingSchema:
        if guid not in self._meetings:
            if self.debug:
                url = self.scraper.get_meeting_url(id, guid)
                print(f">>>> DEBUG: get_meeting({url})", file=sys.stderr)
            self._meetings[guid] = self.scraper.get_meeting(id, guid)
        return self._meetings[guid]

    def get_legislation_for_meeting_row(
        self, row: MeetingRowSchema
    ) -> LegislationSchema:
        id, guid = row.legislation.id, row.legislation.guid
        return self.get_legislation(id, guid)

    def get_legislation(self, id: int, guid: str) -> LegislationSchema:
        if guid not in self._legislations:
            if self.debug:
                url = self.scraper.get_legislation_url(id, guid)
                print(f">>>> DEBUG: get_legislation({url})", file=sys.stderr)
            self._legislations[guid] = self.scraper.get_legislation(id, guid)
        return self._legislations[guid]

    def get_action_for_legislation_row(self, row: LegislationRowSchema) -> ActionSchema:
        id, guid = row.action_details.id, row.action_details.guid
        return self.get_action(id, guid)

    def get_action(self, id: int, guid: str) -> ActionSchema:
        if guid not in self._actions:
            if self.debug:
                url = self.scraper.get_action_url(id, guid)
                print(f">>>> DEBUG: get_action({url})", file=sys.stderr)
            self._actions[guid] = self.scraper.get_action(id, guid)
        return self._actions[guid]

    def iter_meetings(self) -> t.Iterator[MeetingSchema]:
        for row in self.get_calendar().rows:
            yield self.get_meeting_for_calendar_row(row)

    def iter_legislations(self) -> t.Iterator[LegislationSchema]:
        for meeting in self.iter_meetings():
            for row in meeting.rows:
                yield self.get_legislation_for_meeting_row(row)

    def iter_actions(self) -> t.Iterator[ActionSchema]:
        for legislation in self.iter_legislations():
            for row in legislation.rows:
                yield self.get_action_for_legislation_row(row)

    def crawl(
        self,
    ) -> t.Iterator[
        t.Union[CalendarSchema, MeetingSchema, LegislationSchema, ActionSchema]
    ]:
        yield self.get_calendar()
        for meeting in self.iter_meetings():
            yield meeting
        for legislation in self.iter_legislations():
            yield legislation
        for action in self.iter_actions():
            yield action
        for legislation in self.iter_legislations():
            yield legislation
        for action in self.iter_actions():
            yield action
