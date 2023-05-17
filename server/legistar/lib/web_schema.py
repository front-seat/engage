from __future__ import annotations

import datetime
import urllib.parse

from server.legistar.lib.base_schema import BaseSchema as BaseCrawlData


def _id_from_url(url: str) -> int:
    """Extract the ID from a Legistar URL."""
    parsed = urllib.parse.urlparse(url)
    return int(dict(urllib.parse.parse_qsl(parsed.query))["ID"])


def _guid_from_url(url: str) -> str:
    """Extract the GUID from a Legistar URL."""
    parsed = urllib.parse.urlparse(url)
    return dict(urllib.parse.parse_qsl(parsed.query))["GUID"]


class Link(BaseCrawlData):
    """A link to a page on the Legistar site. Potentially, an attachment."""

    name: str
    url: str

    @property
    def id(self) -> int:
        """The ID from the URL. If none is present, an exception is raised."""
        return _id_from_url(self.url)

    @property
    def guid(self) -> str:
        """The GUID from the URL. If none is present, an exception is raised."""
        return _guid_from_url(self.url)


class CalendarRowCrawlData(BaseCrawlData):
    """Single row in the /Calendar.aspx page's main table."""

    department: Link
    date: datetime.date
    time: datetime.time | None  # None implies "canceled"
    location: str
    details: Link  # /MeetingDetail.aspx...
    agenda: Link  # a PDF
    agenda_packet: Link | None  # a PDF
    minutes: Link | None  # a PDF
    video: Link | None  # for the city of Seattle, a seattlechannel.org URL

    @property
    def is_canceled(self) -> bool:
        """Whether the meeting has been canceled."""
        return self.time is None


class CalendarCrawlData(BaseCrawlData):
    """The /Calendar.aspx page."""

    kind: str = "calendar"
    rows: list[CalendarRowCrawlData]


class MeetingRowCrawlData(BaseCrawlData):
    """Single row in the /MeetingDetail.aspx page's main table."""

    # aka "Record No"; like "Appt 02510" or "CB 120537"; /LegislationDetail.aspx
    legislation: Link
    version: int
    agenda_sequence: int | None
    name: str | None = None
    type: str  # like "Appointment (Appt)" or "Council Bill (CB)"
    title: str  # like "Appointment of Lowell Deo as member, ..."
    action: str | None  # like "confirm", or "pass as amended"
    result: str | None  # like "Pass"
    action_details: Link | None  # /HistoryDetail.aspx
    video: Link | None  # for the city of Seattle, a seattlechannel.org URL


class MeetingCrawlData(BaseCrawlData):
    """The /MeetingDetail.aspx page."""

    kind: str = "meeting"
    url: str  # the absolute URL for the meeting
    # like "Economic Development, Technology, and City Light Committee"
    department: Link
    agenda_status: str | None = None  # like "Final" or "Pending"
    date: datetime.date
    time: datetime.time | None  # None implies "canceled"
    location: str  # like "Council Chambers, Seattle City Hall"
    agenda: Link  # a PDF
    agenda_packet: Link | None  # a PDF
    minutes: Link | None  # a PDF
    video: Link | None  # for the city of Seattle, a seattlechannel.org URL
    attachments: list[Link]

    rows: list[MeetingRowCrawlData]

    @property
    def is_canceled(self) -> bool:
        """Whether the meeting has been canceled."""
        return self.time is None

    @property
    def is_active(self) -> bool:
        """Whether the meeting is active."""
        return self.time is not None

    @property
    def id(self) -> int:
        """The ID from the URL. If none is present, an exception is raised."""
        return _id_from_url(self.url)

    @property
    def guid(self) -> str:
        """The GUID from the URL. If none is present, an exception is raised."""
        return _guid_from_url(self.url)


class LegislationRowCrawlData(BaseCrawlData):
    """Single row in the /Legislation.aspx page's main history table."""

    date: datetime.date
    version: int
    action_by: str  # like "City Clerk" or "Mayor" etc.
    action: str | None  # like "attested by City Clerk", "Signed", etc.
    result: str | None = None  # like "Pass", "Fail", etc.
    action_details: Link | None  # a link to a /HistoryDetail.aspx page
    meeting: Link | None  # a link to a /MeetingDetail.aspx page
    video: Link | None  # for the city of Seattle, a seattlechannel.org URL


class LegislationCrawlData(BaseCrawlData):
    """The /Legislation.aspx page."""

    kind: str = "legislation"
    url: str  # the absolute URL for the legislation
    record_no: str  # like "CB 120537"
    version: int | None
    council_bill_no: str | None = None  # like "120537"
    type: str  # like "Council Bill (CB)" or "Information Item (Inf)"
    status: str | None  # like "Heard in Committee"
    controlling_body: str
    on_agenda: datetime.date | None
    ordinance_no: str | None
    title: str
    sponsors: list[Link]
    attachments: list[Link]
    supporting_documents: list[Link]
    # for ordinances, etc, the full text of the legislation
    # (not always available; not always complete)
    full_text: str | None

    rows: list[LegislationRowCrawlData]

    @property
    def id(self) -> int:
        """The ID from the URL. If none is present, an exception is raised."""
        return _id_from_url(self.url)

    @property
    def guid(self) -> str:
        """The GUID from the URL. If none is present, an exception is raised."""
        return _guid_from_url(self.url)


class ActionRowCrawlData(BaseCrawlData):
    """Single row in the /HistoryDetail.aspx page's main table."""

    person: Link
    vote: str  # like "In Favor", "Absent", "Excused", etc.


class ActionCrawlData(BaseCrawlData):
    """The /HistoryDetail.aspx page."""

    kind: str = "action"
    url: str  # the absolute URL for the action
    record_no: str  # like "CB 120537" or "Inf 1960"
    version: int
    type: str  # like "Council Bill (CB)" or "Information Item (Inf)"
    title: str
    result: str | None
    agenda_note: str | None
    minutes_note: str | None
    action: str | None  # like "pass as amended", "confirm", "heard in committee", etc.
    action_text: str | None  # like "council minutes were approved"

    # AKA votes
    rows: list[ActionRowCrawlData]

    @property
    def id(self) -> int:
        """The ID from the URL. If none is present, an exception is raised."""
        return _id_from_url(self.url)

    @property
    def guid(self) -> str:
        """The GUID from the URL. If none is present, an exception is raised."""
        return _guid_from_url(self.url)
