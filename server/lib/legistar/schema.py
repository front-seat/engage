import datetime
import typing as t

import requests


class BodyDict(t.TypedDict):
    """Raw body data from Legistar API."""

    BodyId: int
    BodyGuid: str
    BodyLastModifiedUtc: str
    BodyRowVersion: str
    BodyName: str
    BodyTypeId: int
    BodyTypeName: str
    BodyMeetFlag: int  # 1 if body meets, 0 if not
    BodyActiveFlag: int  # 1 if body is active, 0 if not
    BodySort: int
    BodyDescription: str
    BodyContactNameId: int | None
    BodyContactFullName: str | None
    BodyContactPhone: str | None
    BodyContactEmail: str | None
    BodyUsedControlFlag: int  # 1 if body uses control, 0 if not
    BodyNumberOfMembers: int
    BodyUsedActingFlag: int  # 1 if body uses acting, 0 if not
    BodyUsedTargetFlag: int  # 1 if body uses target, 0 if not
    BodyUsedSponsorFlag: int  # 1 if body uses sponsor, 0 if not


class Body:
    """Well-typed body data from Legistar API."""

    def __init__(self, data: BodyDict):
        self.data = data

    @classmethod
    def from_dict(cls, data: dict | BodyDict) -> "Body":
        return cls(t.cast(BodyDict, data))

    def to_dict(self) -> dict:
        return dict(self.data)

    @property
    def id(self) -> int:
        return self.data["BodyId"]

    @property
    def guid(self) -> str:
        return self.data["BodyGuid"]

    @property
    def last_modified(self) -> datetime.datetime:
        return datetime.datetime.fromisoformat(self.data["BodyLastModifiedUtc"])

    @property
    def name(self) -> str:
        return self.data["BodyName"]

    @property
    def type_name(self) -> str:
        return self.data["BodyTypeName"]

    @property
    def description(self) -> str:
        return self.data["BodyDescription"]

    @property
    def contact_full_name(self) -> str | None:
        return self.data["BodyContactFullName"]

    @property
    def contact_phone(self) -> str | None:
        return self.data["BodyContactPhone"]

    @property
    def contact_email(self) -> str | None:
        return self.data["BodyContactEmail"]

    @property
    def number_of_members(self) -> int:
        return self.data["BodyNumberOfMembers"]


class EventDict(t.TypedDict):
    """Raw event data from Legistar API."""

    EventId: int
    EventGuid: str
    EventLastModifiedUtc: str
    EventRowVersion: str
    EventBodyId: int
    EventBodyName: str
    EventDate: str
    EventTime: str
    EventVideoStatus: str  # like Public, Private, etc.
    EventAgendaStatusId: int
    EventAgendaStatusName: str  # like Cancelled, etc.
    EventMinutesStatusId: int
    EventMinutesStatusName: str  # like Cancelled, etc.
    EventLocation: str  # like City Hall, etc. Often contains an address.
    EventAgendaFile: str | None  # if present, a URL to the agenda PDF
    EventMinutesFile: str | None  # if present, a URL to the minutes PDF
    EventAgendaLastPublishedUTC: str | None
    EventMinutesLastPublishedUTC: str | None
    EventComment: str
    EventVideoPath: str | None
    EventMedia: str | None
    EventInSiteURL: str  # like https://chicago.legistar.com/MeetingDetail.aspx
    EventItems: list[dict]  # TODO: flesh out


class Event:
    """Well-typed event data from Legistar API."""

    def __init__(self, data: EventDict):
        self.data = data

    @classmethod
    def from_dict(cls, data: dict | EventDict) -> "Event":
        return cls(t.cast(EventDict, data))

    def to_dict(self) -> dict:
        return dict(self.data)

    @property
    def id(self) -> int:
        return self.data["EventId"]

    @property
    def guid(self) -> str:
        return self.data["EventGuid"]

    @property
    def last_modified(self) -> datetime.datetime:
        return datetime.datetime.fromisoformat(self.data["EventLastModifiedUtc"])

    @property
    def body_id(self) -> int:
        return self.data["EventBodyId"]

    @property
    def body_name(self) -> str:
        return self.data["EventBodyName"]

    @property
    def date(self) -> datetime.date:
        return datetime.datetime.fromisoformat(self.data["EventDate"]).date()

    @property
    def time(self) -> datetime.time:
        return datetime.datetime.strptime(self.data["EventTime"], "%H:%M %p").time()

    @property
    def video_status(self) -> str:
        return self.data["EventVideoStatus"]

    @property
    def agenda_status_id(self) -> int:
        return self.data["EventAgendaStatusId"]

    @property
    def agenda_status_name(self) -> str:
        return self.data["EventAgendaStatusName"]

    @property
    def minutes_status_id(self) -> int:
        return self.data["EventMinutesStatusId"]

    @property
    def minutes_status_name(self) -> str:
        return self.data["EventMinutesStatusName"]

    @property
    def location(self) -> str:
        return self.data["EventLocation"]

    @property
    def agenda_file_url(self) -> str | None:
        return self.data["EventAgendaFile"]

    def get_agenda_file(self) -> requests.Response | None:
        if self.agenda_file_url is None:
            return None
        response = requests.get(self.agenda_file_url)
        response.raise_for_status()
        return response

    @property
    def minutes_file_url(self) -> str | None:
        return self.data["EventMinutesFile"]

    def get_minutes_file(self) -> requests.Response | None:
        if self.minutes_file_url is None:
            return None
        response = requests.get(self.minutes_file_url)
        response.raise_for_status()
        return response

    @property
    def agenda_last_published(self) -> datetime.datetime | None:
        if self.data["EventAgendaLastPublishedUTC"] is None:
            return None
        return datetime.datetime.fromisoformat(self.data["EventAgendaLastPublishedUTC"])

    @property
    def minutes_last_published(self) -> datetime.datetime | None:
        if self.data["EventMinutesLastPublishedUTC"] is None:
            return None
        return datetime.datetime.fromisoformat(
            self.data["EventMinutesLastPublishedUTC"]
        )

    @property
    def comment(self) -> str:
        return self.data["EventComment"]

    @property
    def video_path(self) -> str | None:
        return self.data["EventVideoPath"]

    @property
    def media(self) -> str | None:
        return self.data["EventMedia"]

    @property
    def in_site_url(self) -> str:
        return self.data["EventInSiteURL"]

    @property
    def items(self) -> list[dict]:
        return self.data["EventItems"]


class MatterDict(t.TypedDict):
    """Raw matter data from Legistar API."""

    MatterId: int
    MatterGuid: str
    MatterLastModifiedUtc: str
    MatterRowVersion: str
    MatterFile: str  # like "Min 43"
    MatterName: str | None  # like "Ordinance 2020-1234"
    MatterTitle: str | None  # often, but not always, a date in Seattle.
    MatterTypeId: int
    MatterTypeName: str  # like "Ordinance", "Resolution", etc.
    MatterStatusId: int
    MatterStatusName: str  # like "Passed", "Failed", "Adopted", etc.
    MatterBodyId: int
    MatterBodyName: str
    MatterIntroDate: str | None
    MatterAgendaDate: str | None
    MatterPassedDate: str | None
    MatterEnactmentDate: str | None
    MatterEnactmentNumber: int | None
    MatterRequester: str | None
    MatterNotes: str | None
    MatterVersion: str  # like "1"
    MatterCost: str | None
    MatterText1: str | None
    MatterText2: str | None
    MatterText3: str | None
    MatterText4: str | None
    MatterText5: str | None
    MatterDate1: str | None
    MatterDate2: str | None
    MatterEXText1: str | None
    MatterEXText2: str | None
    MatterEXText3: str | None
    MatterEXText4: str | None
    MatterEXText5: str | None
    MatterEXText6: str | None
    MatterEXText7: str | None
    MatterEXText8: str | None
    MatterEXText9: str | None
    MatterEXText10: str | None
    MatterEXText11: str | None
    MatterEXDate1: str | None
    MatterEXDate2: str | None
    MatterEXDate3: str | None
    MatterEXDate4: str | None
    MatterEXDate5: str | None
    MatterEXDate6: str | None
    MatterEXDate7: str | None
    MatterEXDate8: str | None
    MatterEXDate9: str | None
    MatterEXDate10: str | None
    MatterAgiloftId: int | None
    MatterReference: str | None
    MatterRestrictViewViaWeb: bool
    MatterReports: list[dict]


class Matter:
    """Well-typed matter data from Legistar API."""

    def __init__(self, data: MatterDict):
        self.data = data

    @classmethod
    def from_dict(cls, data: dict | MatterDict) -> "Matter":
        return cls(t.cast(MatterDict, data))

    def to_dict(self) -> dict:
        return dict(self.data)

    @property
    def id(self) -> int:
        return self.data["MatterId"]

    @property
    def guid(self) -> str:
        return self.data["MatterGuid"]

    @property
    def last_modified(self) -> datetime.datetime:
        return datetime.datetime.fromisoformat(self.data["MatterLastModifiedUtc"])

    @property
    def file(self) -> str:
        return self.data["MatterFile"]

    @property
    def name(self) -> str | None:
        return self.data["MatterName"]

    @property
    def title(self) -> str | None:
        return self.data["MatterTitle"]

    @property
    def type_name(self) -> str:
        return self.data["MatterTypeName"]

    @property
    def status_name(self) -> str:
        return self.data["MatterStatusName"]

    @property
    def body_id(self) -> int:
        return self.data["MatterBodyId"]

    @property
    def body_name(self) -> str:
        return self.data["MatterBodyName"]

    @property
    def intro_date(self) -> datetime.datetime | None:
        if self.data["MatterIntroDate"] is None:
            return None
        return datetime.datetime.fromisoformat(self.data["MatterIntroDate"])

    @property
    def agenda_date(self) -> datetime.datetime | None:
        if self.data["MatterAgendaDate"] is None:
            return None
        return datetime.datetime.fromisoformat(self.data["MatterAgendaDate"])

    @property
    def passed_date(self) -> datetime.datetime | None:
        if self.data["MatterPassedDate"] is None:
            return None
        return datetime.datetime.fromisoformat(self.data["MatterPassedDate"])

    @property
    def enactment_date(self) -> datetime.datetime | None:
        if self.data["MatterEnactmentDate"] is None:
            return None
        return datetime.datetime.fromisoformat(self.data["MatterEnactmentDate"])

    @property
    def enactment_number(self) -> int | None:
        return self.data["MatterEnactmentNumber"]

    @property
    def notes(self) -> str | None:
        return self.data["MatterNotes"]

    @property
    def text(self) -> str:
        # Merge all MatterText* fields into one string; if they're None,
        # replace with empty string.
        return "\n".join([self.data.get(f"MatterText{i}") or "" for i in range(1, 6)])

    @property
    def ex_text(self) -> str:
        # Merge all MatterEXText* fields into one string; if they're None,
        # replace with empty string.
        return "\n".join(
            [self.data.get(f"MatterEXText{i}") or "" for i in range(1, 12)]
        )

    @property
    def reports(self) -> list[dict]:
        return self.data["MatterReports"]
