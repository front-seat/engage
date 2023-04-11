import datetime
import typing as t
import urllib.parse

from pydantic import BaseModel as PydanticBase
from pydantic import Field, validator


class BaseSchema(PydanticBase):
    """Base schema type for all Legistar-returned data."""

    # CONSIDER:

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


class CalendarEntry(BaseSchema):
    """Single row in the /Calendar.aspx page's main table."""

    body: str
    body_url: str
    date: datetime.date
    time: datetime.time | None  # None implies "cancelled"
    location: str
    details_url: str  # a page on the Legistar site
    agenda_url: str  # a PDF
    agenda_packet_url: str | None = None  # a PDF
    minutes_url: str | None = None  # a PDF
    video_url: str | None = None  # for the city of Seattle, a seattlechannel.org URL

    # FUTURE: use the Council Data Project to get a video transcript

    def _body_query_dict(self) -> dict[str, str]:
        """The query dict from the committee URL."""
        parsed = urllib.parse.urlparse(self.body_url)
        return dict(urllib.parse.parse_qsl(parsed.query))

    @property
    def body_id(self) -> int:
        """The Body ID from the committee URL."""
        return int(self._body_query_dict()["BodyID"])

    @property
    def body_guid(self) -> str:
        """The Body GUID from the committee URL."""
        return self._body_query_dict()["BodyGUID"]

    def _detail_query_dict(self) -> dict[str, str]:
        """The query dict from the details URL."""
        parsed = urllib.parse.urlparse(self.details_url)
        return dict(urllib.parse.parse_qsl(parsed.query))

    @property
    def matter_id(self) -> int:
        """The Matter ID from the details URL."""
        return int(self._detail_query_dict()["ID"])

    @property
    def matter_guid(self) -> str:
        """The Matter GUID from the details URL."""
        return self._detail_query_dict()["GUID"]
