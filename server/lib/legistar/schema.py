import datetime
import typing as t
import urllib.parse

from pydantic import BaseModel as PydanticBase
from pydantic import Field, validator


def _id_from_url(url: str) -> int:
    """Extract the ID from a Legistar URL."""
    parsed = urllib.parse.urlparse(url)
    return int(dict(urllib.parse.parse_qsl(parsed.query))["ID"])


def _guid_from_url(url: str) -> str:
    """Extract the GUID from a Legistar URL."""
    parsed = urllib.parse.urlparse(url)
    return dict(urllib.parse.parse_qsl(parsed.query))["GUID"]


class BaseSchema(PydanticBase):
    """Base schema type for all Legistar-returned data."""

    # def dict(self, *args, **kwargs):
    #     """Override dict() to ensure we remove None values from the output."""
    #     # Keep exclude_none=False if explicitly provided, though.
    #     final_kwargs = {"exclude_none": True, **kwargs}
    #     return super().dict(*args, **final_kwargs)

    # def json(self, *args, **kwargs):
    #     """Override json() to ensure we remove None values from the output."""
    #     # Keep exclude_none=False if explicitly provided, though.
    #     final_kwargs = {"exclude_none": True, **kwargs}
    #     return super().json(*args, **final_kwargs)

    class Config:
        allow_population_by_field_name = True


# -----------------------------------------------------------------------------
# API Models
# -----------------------------------------------------------------------------


class Body(BaseSchema):
    """Body data schema from the Legistar API."""

    id: int = Field(alias="BodyId")
    guid: str = Field(alias="BodyGuid")
    last_modified: datetime.datetime = Field(alias="BodyLastModifiedUtc")
    row_version: str = Field(alias="BodyRowVersion")
    name: str = Field(alias="BodyName")
    type_id: int = Field(alias="BodyTypeId")
    type_name: str = Field(alias="BodyTypeName")
    meet_flag: int = Field(alias="BodyMeetFlag")
    active_flag: int = Field(alias="BodyActiveFlag")
    sort: int = Field(alias="BodySort")
    description: str = Field(alias="BodyDescription")
    contact_name_id: t.Optional[int] = Field(alias="BodyContactNameId")
    contact_full_name: t.Optional[str] = Field(alias="BodyContactFullName")
    contact_phone: t.Optional[str] = Field(alias="BodyContactPhone")
    contact_email: t.Optional[str] = Field(alias="BodyContactEmail")
    used_control_flag: int = Field(alias="BodyUsedControlFlag")
    number_of_members: int = Field(alias="BodyNumberOfMembers")
    used_acting_flag: int = Field(alias="BodyUsedActingFlag")
    used_target_flag: int = Field(alias="BodyUsedTargetFlag")
    used_sponsor_flag: int = Field(alias="BodyUsedSponsorFlag")


class Event(BaseSchema):
    """Event data schema from the Legistar API."""

    id: int = Field(alias="EventId")
    guid: str = Field(alias="EventGuid")
    last_modified: datetime.datetime = Field(alias="EventLastModifiedUtc")
    row_version: str = Field(alias="EventRowVersion")
    body_id: int = Field(alias="EventBodyId")
    body_name: str = Field(alias="EventBodyName")
    date: datetime.date = Field(alias="EventDate")
    time: datetime.time | None = Field(alias="EventTime")
    video_status: str = Field(alias="EventVideoStatus")
    agenda_status_id: int = Field(alias="EventAgendaStatusId")
    agenda_status_name: str = Field(alias="EventAgendaStatusName")
    minutes_status_id: int = Field(alias="EventMinutesStatusId")
    minutes_status_name: str = Field(alias="EventMinutesStatusName")
    location: str = Field(alias="EventLocation")  # often contains an address
    agenda_file: str | None = Field(alias="EventAgendaFile")  # URL to the agenda PDF
    minutes_file: str | None = Field(alias="EventMinutesFile")  # URL to the minutes PDF
    agenda_last_published: datetime.datetime | None = Field(
        alias="EventAgendaLastPublishedUTC"
    )
    minutes_last_published: datetime.datetime | None = Field(
        alias="EventMinutesLastPublishedUTC"
    )
    comment: str | None = Field(alias="EventComment")
    video_path: str | None = Field(alias="EventVideoPath")
    media: str | None = Field(alias="EventMedia")
    in_site_url: str = Field(alias="EventInSiteURL")  # URL to the event page
    items: list[dict] = Field(alias="EventItems")  # TODO: flesh out

    @validator("date", pre=True)
    def parse_date(cls, value: str) -> datetime.date:
        return datetime.datetime.fromisoformat(value).date()

    @validator("time", pre=True)
    def parse_time(cls, value: str | None) -> datetime.time | None:
        return datetime.datetime.strptime(value, "%H:%M %p").time() if value else None


class Matter(BaseSchema):
    """Matter data schema from the Legistar API."""

    id: int = Field(alias="MatterId")
    guid: str = Field(alias="MatterGuid")
    last_modified: datetime.datetime = Field(alias="MatterLastModifiedUtc")
    row_version: str = Field(alias="MatterRowVersion")
    file: str | None = Field(alias="MatterFile")  # like "Min 43"
    name: str | None = Field(alias="MatterName")  # like "Ordinance 2020-1234"
    title: str | None = Field(alias="MatterTitle")  # often, but not always, a date
    type_id: int = Field(alias="MatterTypeId")
    type_name: str = Field(
        alias="MatterTypeName"
    )  # like "Ordinance", "Resolution", etc.  # noqa: E501
    status_id: int = Field(alias="MatterStatusId")
    status_name: str = Field(
        alias="MatterStatusName"
    )  # like "Passed", "Failed", "Adopted", etc.  # noqa: E501
    body_id: int = Field(alias="MatterBodyId")
    body_name: str = Field(alias="MatterBodyName")
    intro_date: datetime.datetime | None = Field(alias="MatterIntroDate")
    agenda_date: datetime.datetime | None = Field(alias="MatterAgendaDate")
    passed_date: datetime.datetime | None = Field(alias="MatterPassedDate")
    enactment_date: datetime.datetime | None = Field(alias="MatterEnactmentDate")
    enactment_number: str | None = Field(alias="MatterEnactmentNumber")
    requester: str | None = Field(alias="MatterRequester")
    notes: str | None = Field(alias="MatterNotes")
    version: str = Field(alias="MatterVersion")  # like "1"
    cost: str | None = Field(alias="MatterCost")
    # This is no fun! For texts, see self.text and self.ex_text.
    text_1: str | None = Field(alias="MatterText1")
    text_2: str | None = Field(alias="MatterText2")
    text_3: str | None = Field(alias="MatterText3")
    text_4: str | None = Field(alias="MatterText4")
    text_5: str | None = Field(alias="MatterText5")
    date_1: datetime.datetime | None = Field(alias="MatterDate1")
    date_2: datetime.datetime | None = Field(alias="MatterDate2")
    date_3: datetime.datetime | None = Field(alias="MatterDate3")
    date_4: datetime.datetime | None = Field(alias="MatterDate4")
    date_5: datetime.datetime | None = Field(alias="MatterDate5")
    ex_text_1: str | None = Field(alias="MatterExText1")
    ex_text_2: str | None = Field(alias="MatterExText2")
    ex_text_3: str | None = Field(alias="MatterExText3")
    ex_text_4: str | None = Field(alias="MatterExText4")
    ex_text_5: str | None = Field(alias="MatterExText5")
    ex_text_6: str | None = Field(alias="MatterExText6")
    ex_text_7: str | None = Field(alias="MatterExText7")
    ex_text_8: str | None = Field(alias="MatterExText8")
    ex_text_9: str | None = Field(alias="MatterExText9")
    ex_text_10: str | None = Field(alias="MatterExText10")
    ex_text_11: str | None = Field(alias="MatterExText11")
    ex_date_1: datetime.datetime | None = Field(alias="MatterExDate1")
    ex_date_2: datetime.datetime | None = Field(alias="MatterExDate2")
    ex_date_3: datetime.datetime | None = Field(alias="MatterExDate3")
    ex_date_4: datetime.datetime | None = Field(alias="MatterExDate4")
    ex_date_5: datetime.datetime | None = Field(alias="MatterExDate5")
    ex_date_6: datetime.datetime | None = Field(alias="MatterExDate6")
    ex_date_7: datetime.datetime | None = Field(alias="MatterExDate7")
    ex_date_8: datetime.datetime | None = Field(alias="MatterExDate8")
    ex_date_9: datetime.datetime | None = Field(alias="MatterExDate9")
    ex_date_10: datetime.datetime | None = Field(alias="MatterExDate10")
    agiloft_id: str | None = Field(alias="MatterAgiloftId")
    restrict_view_via_web: bool = Field(alias="MatterRestrictViewViaWeb")
    reports: list[dict] = Field(alias="MatterReports")

    @property
    def text(self) -> str | None:
        """The Matter's text, if any."""
        return "\n".join([getattr(self, f"text_{i}") or "" for i in range(1, 6)])

    @property
    def ex_text(self) -> str | None:
        """The Matter's extended text, if any."""
        return "\n".join([getattr(self, f"ex_text_{i}") or "" for i in range(1, 12)])


# -----------------------------------------------------------------------------
# Scraper models
# -----------------------------------------------------------------------------


class Link(BaseSchema):
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


class CalendarRow(BaseSchema):
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


class Calendar(BaseSchema):
    """The /Calendar.aspx page."""

    rows: list[CalendarRow]


class MeetingRow(BaseSchema):
    """Single row in the /MeetingDetail.aspx page's main table."""

    # aka "Record No"; like "Appt 02510" or "CB 120537"; /LegislationDetail.aspx
    legislation: Link
    version: int
    agenda_sequence: int
    name: str | None = None
    type: str  # like "Appointment (Appt)" or "Council Bill (CB)"
    title: str  # like "Appointment of Lowell Deo as member, ..."
    action: str | None  # like "confirm", or "pass as amended"
    result: str | None  # like "Pass"
    action_details: Link | None  # /HistoryDetail.aspx
    video: Link | None  # for the city of Seattle, a seattlechannel.org URL


class Meeting(BaseSchema):
    """The /MeetingDetail.aspx page."""

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

    rows: list[MeetingRow]

    @property
    def is_canceled(self) -> bool:
        """Whether the meeting has been canceled."""
        return self.time is None


class LegislationRow(BaseSchema):
    """Single row in the /Legislation.aspx page's main history table."""

    date: datetime.date
    version: int
    action_by: str  # like "City Clerk" or "Mayor" etc.
    action: str  # like "attested by City Clerk", "Signed", etc.
    result: str | None = None  # like "Pass", "Fail", etc.
    action_details: Link  # a link to a /HistoryDetail.aspx page
    meeting: Link | None  # a link to a /MeetingDetail.aspx page
    video: Link | None  # for the city of Seattle, a seattlechannel.org URL


class Legislation(BaseSchema):
    """The /Legislation.aspx page."""

    record_no: str  # like "CB 120537"
    version: int
    council_bill_no: str | None = None  # like "120537"
    type: str  # like "Council Bill (CB)" or "Information Item (Inf)"
    status: str | None  # like "Heard in Committee"
    department: Link
    on_agenda: datetime.date
    ordinance_no: str | None
    title: str
    sponsors: list[Link]
    attachments: list[Link]
    supporting_documents: list[Link]

    rows: list[LegislationRow]


class ActionRow(BaseSchema):
    """Single row in the /HistoryDetail.aspx page's main table."""

    person: Link
    vote: str  # like "In Favor", "Absent", "Excused", etc.


class Action(BaseSchema):
    """The /HistoryDetail.aspx page."""

    record_no: str  # like "CB 120537" or "Inf 1960"
    version: int
    type: str  # like "Council Bill (CB)" or "Information Item (Inf)"
    title: str
    result: str | None
    agenda_note: str | None
    minutes_note: str | None
    action: str  # like "pass as amended", "confirm", "heard in committee", etc.
    action_text: str | None  # like "council minutes were approved"

    # AKA votes
    rows: list[ActionRow]
