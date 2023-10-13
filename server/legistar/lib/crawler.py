import datetime
import sys
import typing as t

from django.conf import settings

from .scraper import LegistarScraper
from .web_schema import (
    ActionCrawlData,
    CalendarCrawlData,
    CalendarRowCrawlData,
    LegislationCrawlData,
    LegislationRowCrawlData,
    MeetingCrawlData,
    MeetingRowCrawlData,
)


class LegistarCalendarCrawler:
    """
    Crawler for the Legistar Calendar API.
    """

    start_date: datetime.date | None
    _calendar: CalendarCrawlData | None
    _meetings: dict[str, MeetingCrawlData]
    _legislations: dict[str, LegislationCrawlData]
    _actions: dict[str, ActionCrawlData]

    def __init__(
        self,
        customer: str,
        start_date: datetime.date | None = None,
    ):
        self.customer = customer
        self.start_date = start_date
        self.scraper = LegistarScraper(customer)
        self._calendar = None
        self._meetings = {}
        self._legislations = {}
        self._actions = {}

    def get_calendar(self) -> CalendarCrawlData:
        if self._calendar is None:
            if settings.VERBOSE:
                print(">>>> CRAWL: get_calendar()", file=sys.stderr)
            self._calendar = self.scraper.get_calendar(start_date=self.start_date)
        return self._calendar

    def get_meeting_for_calendar_row(
        self, row: CalendarRowCrawlData
    ) -> MeetingCrawlData:
        id, guid = row.details.id, row.details.guid
        return self.get_meeting(id, guid)

    def get_meeting(self, id: int, guid: str) -> MeetingCrawlData:
        if guid not in self._meetings:
            if settings.VERBOSE:
                url = self.scraper.get_meeting_url(id, guid)
                print(f">>>> CRAWL: get_meeting({url})", file=sys.stderr)
            self._meetings[guid] = self.scraper.get_meeting(id, guid)
        return self._meetings[guid]

    def get_legislation_for_meeting_row(
        self, row: MeetingRowCrawlData
    ) -> LegislationCrawlData:
        id, guid = row.legislation.id, row.legislation.guid
        return self.get_legislation(id, guid)

    def get_legislation(self, id: int, guid: str) -> LegislationCrawlData:
        if guid not in self._legislations:
            if settings.VERBOSE:
                url = self.scraper.get_legislation_url(id, guid)
                print(f">>>> CRAWL: get_legislation({url})", file=sys.stderr)
            self._legislations[guid] = self.scraper.get_legislation(id, guid)
        return self._legislations[guid]

    def get_action_for_legislation_row(
        self, row: LegislationRowCrawlData
    ) -> ActionCrawlData | None:
        if row.action_details is None:
            return None
        id, guid = row.action_details.id, row.action_details.guid
        try:
            return self.get_action(id, guid)
        except Exception as e:
            print(f"Error getting action {id}, {guid}: {e}")
            return None

    def get_action(self, id: int, guid: str) -> ActionCrawlData:
        if guid not in self._actions:
            if settings.VERBOSE:
                url = self.scraper.get_action_url(id, guid)
                print(f">>>> CRAWL: get_action({url})", file=sys.stderr)
            self._actions[guid] = self.scraper.get_action(id, guid)
        return self._actions[guid]

    def iter_meetings(self) -> t.Iterator[MeetingCrawlData]:
        for row in self.get_calendar().rows:
            yield self.get_meeting_for_calendar_row(row)

    def iter_legislations(self) -> t.Iterator[LegislationCrawlData]:
        for meeting in self.iter_meetings():
            for row in meeting.rows:
                yield self.get_legislation_for_meeting_row(row)

    def iter_actions(self) -> t.Iterator[ActionCrawlData]:
        for legislation in self.iter_legislations():
            for row in legislation.rows:
                maybe_action = self.get_action_for_legislation_row(row)
                if maybe_action is not None:
                    yield maybe_action

    def crawl(
        self,
    ) -> t.Iterator[
        t.Union[
            CalendarCrawlData, MeetingCrawlData, LegislationCrawlData, ActionCrawlData
        ]
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
