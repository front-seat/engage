from __future__ import annotations

import datetime
import itertools
import typing as t
import urllib.parse

import requests
from bs4 import BeautifulSoup, Tag

from .errors import LegistarError
from .schema import (
    Action,
    ActionRow,
    Calendar,
    CalendarRow,
    Legislation,
    LegislationRow,
    Link,
    Meeting,
    MeetingRow,
)

# ---------------------------------------------------------------------
# Tools for /Calendar.aspx
# ---------------------------------------------------------------------

CALENDAR_ROW_HEADERS = [
    "name",
    "meeting date",
    "",  # the ics icon
    "meeting time",
    "meeting location",
    "meeting details",
    "agenda",
    "agenda packet",
    "minutes",
    "seattle channel",
]


def _make_calendar_row(row: RowScraper) -> CalendarRow:
    department = row.get_link("name")
    date = row.get_date("meeting date")
    time = row.get_optional_time("meeting time")
    location = row.get_text("meeting location")
    details = row.get_link("meeting details")
    agenda = row.get_link("agenda")
    agenda_packet = row.get_optional_link("agenda packet")
    minutes = row.get_optional_link("minutes")
    video = row.get_optional_link("seattle channel")

    return CalendarRow(
        department=department,
        date=date,
        time=time,
        location=location,
        details=details,
        agenda=agenda,
        agenda_packet=agenda_packet,
        minutes=minutes,
        video=video,
    )


# ---------------------------------------------------------------------
# Tools for /MeetingDetail.aspx
# ---------------------------------------------------------------------

MEETING_DETAIL_LABELS = {
    "meeting name",
    "agenda status",
    "meeting date/time",
    "meeting location",
    "published agenda",
    "published minutes",
    "agenda packet",
    "meeting video",
    "attachments",
}


def _make_meeting(details: DetailScraper, table: TableScraper) -> Meeting:
    """Extract the meeting details from the page."""
    department = details.get_link("meeting name")
    agenda_status = details.get_optional_text("agenda status")
    date, time = details.get_date_and_optional_time("meeting date/time")
    location = details.get_text("meeting location")
    agenda = details.get_link("published agenda")
    minutes = details.get_optional_link("published minutes")
    agenda_packet = details.get_optional_link("agenda packet")
    video = details.get_optional_link("meeting video")
    attachments = details.get_links("attachments")
    rows = [_make_meeting_row(row) for row in table]
    return Meeting(
        department=department,
        agenda_status=agenda_status,
        date=date,
        time=time,
        location=location,
        agenda=agenda,
        minutes=minutes,
        agenda_packet=agenda_packet,
        video=video,
        attachments=attachments,
        rows=rows,
    )


MEETING_ROW_HEADERS = [
    "record no",
    "ver",
    "agenda #",
    "name",
    "type",
    "title",
    "action",
    "result",
    "action details",
    "seattle channel",
]


def _make_meeting_row(row: RowScraper) -> MeetingRow:
    legislation = row.get_link("record no")
    version = row.get_int("ver")
    agenda_sequence = row.get_optional_int("agenda #")
    name = row.get_optional_text("name")
    type = row.get_text("type")
    title = row.get_text("title")
    action = row.get_optional_text("action")
    result = row.get_optional_text("result")
    action_details = row.get_optional_link("action details")
    video = row.get_optional_link("seattle channel")

    return MeetingRow(
        legislation=legislation,
        version=version,
        agenda_sequence=agenda_sequence,
        name=name,
        type=type,
        title=title,
        action=action,
        result=result,
        action_details=action_details,
        video=video,
    )


# ---------------------------------------------------------------------
# Tools for /LegislationDetail.aspx
# ---------------------------------------------------------------------

LEGISLATION_DETAIL_LABELS = {
    "record no",
    # "version",
    "council bill no",
    "type",
    "status",
    "current controlling legislative body",
    "on agenda",
    "ordinance no",
    "title",
    # "sponsors",
    # "attachments",
    # "supporting documents",
}


def _make_legislation(details: DetailScraper, table: TableScraper) -> Legislation:
    """Extract the legislation details from the page."""
    record_no = details.get_text("record no")
    version = details.get_int("version") if details.has_label("version") else None
    council_bill_no = details.get_optional_text("council bill no")
    type = details.get_text("type")
    status = details.get_optional_text("status")
    controlling_body = details.get_text("current controlling legislative body")
    on_agenda = details.get_date("on agenda")
    ordinance_no = details.get_optional_text("ordinance no")
    title = details.get_text("title")
    sponsors = details.get_links("sponsors") if details.has_label("sponsors") else []
    attachments = (
        details.get_links("attachments") if details.has_label("attachments") else []
    )
    supporting_documents = (
        details.get_links("supporting documents")
        if details.has_label("supporting documents")
        else []
    )
    rows = [_make_legislation_row(row) for row in table]
    return Legislation(
        record_no=record_no,
        version=version,
        council_bill_no=council_bill_no,
        type=type,
        status=status,
        controlling_body=controlling_body,
        on_agenda=on_agenda,
        ordinance_no=ordinance_no,
        title=title,
        sponsors=sponsors,
        attachments=attachments,
        supporting_documents=supporting_documents,
        rows=rows,
    )


LEGISLATION_ROW_HEADERS = [
    "date",
    "ver",
    "action by",
    "action",
    "result",
    "action details",  # aka a /HistoryDetail page.
    "meeting details",
    "seattle channel",
]


def _make_legislation_row(row: RowScraper) -> LegislationRow:
    date = row.get_date("date")
    version = row.get_int("ver")
    action_by = row.get_text("action by")
    action = row.get_text("action")
    result = row.get_optional_text("result")
    action_details = row.get_link("action details")
    meeting = row.get_optional_link("meeting details")
    video = row.get_optional_link("seattle channel")

    return LegislationRow(
        date=date,
        version=version,
        action_by=action_by,
        action=action,
        result=result,
        action_details=action_details,
        meeting=meeting,
        video=video,
    )


# ---------------------------------------------------------------------
# Tools for /HistoryDetail.aspx (aka "action")
# ---------------------------------------------------------------------

ACTION_DETAIL_LABELS = {
    "record no",
    "version",
    "type",
    "title",
    "result",
    "agenda note",
    "minutes note",
    "action",
    "action text",
}


def _make_action(details: DetailScraper, table: TableScraper) -> Action:
    """Extract the action details from the page."""
    record_no = details.get_text("record no")
    version = details.get_int("version")
    type = details.get_text("type")
    title = details.get_text("title")
    result = details.get_optional_text("result")
    agenda_note = details.get_optional_text("agenda note")
    minutes_note = details.get_optional_text("minutes note")
    action = details.get_text("action")
    action_text = details.get_optional_text("action text")
    rows = [_make_action_row(row) for row in table]
    return Action(
        record_no=record_no,
        version=version,
        type=type,
        title=title,
        result=result,
        agenda_note=agenda_note,
        minutes_note=minutes_note,
        action=action,
        action_text=action_text,
        rows=rows,
    )


ACTION_ROW_HEADERS = ["person name", "vote"]


def _make_action_row(row: RowScraper) -> ActionRow:
    person = row.get_link("person name")
    vote = row.get_text("vote")

    return ActionRow(person=person, vote=vote)


# ---------------------------------------------------------------------
# Generic utilities
# ---------------------------------------------------------------------


def clean_text(text: str) -> str:
    """Clean up text from the Legistar website."""
    # Remove non-breaking spaces; replace em-dashes and en-dashes.
    return (
        text.replace("\xa0", " ").replace("\u2013", "-").replace("\u2014", "-").strip()
    )


def clean_header(header: str) -> str:
    """Clean up a header string."""
    return clean_text(header).replace(":", "").replace(".", "").lower().strip()


def get_href_from_a_tag(a: Tag) -> str:
    """Given an `a` tag, get the linked URL."""
    # If there's an href, and it's not empty, use that.
    maybe_href = a.attrs.get("href", "").replace("#", "").strip()
    if maybe_href:
        return maybe_href

    # There'd better be an onclick handler.
    maybe_onclick = a.attrs.get("onclick", "").strip()
    if not maybe_onclick:
        raise LegistarError(f"Could not find href or onclick for link: {a}")

    # Buried in this stupid onclick handler is the URL. In particular, it's
    # inside the invocation of radopen('url', ...) or radopen('url')
    try:
        maybe_url = maybe_onclick.split("radopen('")[1].split("'")[0].strip()
        if not maybe_url:
            raise LegistarError("Could not find href or onclick for link")
        return maybe_url
    except IndexError as e:
        raise LegistarError("Could not find href or onclick for link") from e


def get_optional_href_from_a_tag(a: Tag) -> str | None:
    try:
        return get_href_from_a_tag(a)
    except LegistarError:
        return None


def get_link_from_a_tag(a: Tag, base_url: str) -> Link:
    """Given an `a` tag, get the attachment structure."""
    href = get_href_from_a_tag(a)
    absolute_href = urllib.parse.urljoin(base_url, href)
    return Link(name=clean_text(a.text), url=absolute_href)


def get_optional_link_from_a_tag(a: Tag, base_url: str) -> Link | None:
    try:
        return get_link_from_a_tag(a, base_url)
    except LegistarError:
        return None


def children_of_type_before(tag: Tag, of_type: str, before: str) -> t.Iterator[Tag]:
    """Yield all children of the given tag of the given type before the stop tag."""
    # Sadly, this turns out to be pretty handy when dealing with a whole bunch
    # of Legistar's anti-semantic HTML. :-/
    for child in tag.children:
        if not isinstance(child, Tag):
            continue
        if child.name == before:
            break
        if child.name == of_type:
            yield child


def find_in_sequence(
    tags: t.Iterable[Tag],
    of_types: set[str],
    filter: t.Optional[t.Callable[[Tag], bool]] = None,
) -> t.Iterator[Tag]:
    """Given a sequence of tags, and desired types, return each matching tag."""
    # This is another weird generic-ish method that turns out to be handy when
    # dealing with Legistar's anti-semantic HTML. :-/
    for tag in tags:
        for found_tag in tag.find_all(of_types):
            if filter and not filter(found_tag):
                continue
            yield found_tag


def is_label_predicate(tag: Tag) -> bool:
    """
    Return True if a given tag *appears* to be a detail label.
    """
    ends_with_colon = tag.text.strip().endswith(":")
    is_special_case = tag.text.strip().lower() in {
        "current controlling legislative body"
    }
    return ends_with_colon or is_special_case


# ---------------------------------------------------------------------
# Table & row scraping
# ---------------------------------------------------------------------


class RowScraper:
    """
    Utilities to cull structured data from an arbitrary Legistar website table row.
    """

    table_scraper: TableScraper
    row: Tag

    def __init__(self, table_scraper: TableScraper, row: Tag):
        self.table_scraper = table_scraper
        self.row = row

    def get_text(self, header: str) -> str:
        """Get the text of the cell in the given column."""
        maybe_text = self.row.find_all("td")[
            self.table_scraper.get_header_index(header)
        ].text
        if not isinstance(maybe_text, str):
            raise LegistarError(f"Could not find text for header {header}")
        cleaned = clean_text(maybe_text)
        if not cleaned:
            raise LegistarError(f"Could not find text for header {header}")
        return cleaned

    def get_optional_text(self, header: str) -> str | None:
        """Get the text of the cell in the given column, if it exists."""
        maybe_text = self.row.find_all("td")[
            self.table_scraper.get_header_index(header)
        ].text
        if not isinstance(maybe_text, str):
            return None
        cleaned = clean_text(maybe_text)
        return cleaned if cleaned else None

    def get_int(self, header: str) -> int:
        """Get the integer of the cell in the given column."""
        text = self.get_text(header)
        if text.endswith("."):
            text = text[:-1]
        try:
            return int(text)
        except ValueError as e:
            raise LegistarError(f"Could not parse int {text}") from e

    def get_optional_int(self, header: str) -> int | None:
        """Get the integer of the cell in the given column, if it exists."""
        text = self.get_optional_text(header)
        if text is None:
            return None
        if text.endswith("."):
            text = text[:-1]
        try:
            return int(text)
        except ValueError as e:
            raise LegistarError(f"Could not parse int {text}") from e

    def get_date(self, header: str) -> datetime.date:
        """Get the date of the cell in the given column."""
        text = self.get_text(header)
        try:
            return datetime.datetime.strptime(text, "%m/%d/%Y").date()
        except ValueError as e:
            raise LegistarError(f"Could not parse date {text}") from e

    def get_optional_date(self, header: str) -> datetime.date | None:
        """Get the date of the cell in the given column, if it exists."""
        text = self.get_optional_text(header)
        if text is None:
            return None
        try:
            return datetime.datetime.strptime(text, "%m/%d/%Y").date()
        except ValueError as e:
            raise LegistarError(f"Could not parse date {text}") from e

    def get_time(self, header: str) -> datetime.time:
        """Get the time of the cell in the given column."""
        text = self.get_text(header)
        try:
            return datetime.datetime.strptime(text, "%I:%M %p").time()
        except ValueError as e:
            raise LegistarError(f"Could not parse time {text}") from e

    def get_optional_time(self, header: str) -> datetime.time | None:
        """Get the time of the cell in the given column, if it exists."""
        text = self.get_optional_text(header)
        if text is None:
            return None
        try:
            return datetime.datetime.strptime(text, "%I:%M %p").time()
        except ValueError as e:
            if text.lower() == "canceled":
                return None
            raise LegistarError(f"Could not parse time {text}") from e

    def get_link(self, header: str) -> Link:
        """Get the link and text of the cell in the given column."""
        maybe_link = self.row.find_all("td")[
            self.table_scraper.get_header_index(header)
        ].find("a")
        if not isinstance(maybe_link, Tag):
            raise LegistarError(f"Could not find link for header {header}")
        return get_link_from_a_tag(
            maybe_link, base_url=self.table_scraper.scraper.base_url
        )

    def get_optional_link(self, header: str) -> Link | None:
        """Get the link and text of the cell in the given column, if it exists."""
        maybe_link = self.row.find_all("td")[
            self.table_scraper.get_header_index(header)
        ].find("a")
        if not isinstance(maybe_link, Tag):
            return None
        return get_optional_link_from_a_tag(
            maybe_link, base_url=self.table_scraper.scraper.base_url
        )


class TableScraper:
    """
    Utilities to cull structured data from an arbitrary Legistar website table.
    """

    scraper: LegistarScraper
    table: Tag
    headers: list[str]
    _indexes: dict[str, int]

    def __init__(
        self,
        scraper: LegistarScraper,
        table: Tag,
        header_class: str = "rgHeader",
        row_class: str = "rgRow",
    ):
        self.scraper = scraper
        self.table = table
        self.headers = self._build_headers(header_class)
        self._indexes = {header: i for i, header in enumerate(self.headers)}

    def _build_headers(self, header_class: str) -> list[str]:
        """Populate the headers list."""
        return [
            clean_header(header.text)
            for header in self.table.find_all("th", class_=header_class)
        ]

    def get_header_index(self, header: str) -> int:
        """Get the index of the given header."""
        maybe_index = self._indexes.get(clean_header(header))
        if maybe_index is None:
            raise LegistarError(f"Could not find header {header}")
        return maybe_index

    def __iter__(self) -> t.Iterator[RowScraper]:
        """Iterate over the rows of the table."""
        for row in self.table.find_all("tr", class_="rgRow"):
            if not isinstance(row, Tag):
                raise LegistarError(f"Invalid row: {row}")
            yield RowScraper(self, row)

    @classmethod
    def from_soup(
        cls,
        scraper: LegistarScraper,
        soup: BeautifulSoup,
        table_class: str = "rgMasterTable",
        header_class: str = "rgHeader",
        row_class: str = "rgRow",
    ) -> "TableScraper":
        """Construct a TableScraper from a BeautifulSoup object."""
        table = soup.find("table", class_=table_class)
        if not isinstance(table, Tag):
            raise LegistarError(f"Could not find table with class {table_class}")
        return cls(scraper, table, header_class=header_class, row_class=row_class)


# ---------------------------------------------------------------------
# Details tab scraper
# ---------------------------------------------------------------------


class DetailScraper:
    """
    Utilities to cull structured data from an arbitrary Legistar website detail tab.
    """

    view: Tag
    _details: list[Tag]
    _is_label: t.Callable[[Tag], bool]
    labels: list[str]

    def __init__(
        self,
        scraper: LegistarScraper,
        soup: BeautifulSoup,
        view_class: str = "rmpView",
        view_index: int = 0,
        is_label: t.Callable[[Tag], bool] = is_label_predicate,
    ):
        self.scraper = scraper

        self.view = self._build_view(soup, view_class, view_index)
        self._details = self._build_details(self.view)
        self._is_label = is_label
        self.labels = self._build_labels()

    def _build_view(
        self,
        soup: BeautifulSoup,
        view_class: str,
        view_index: int,
    ) -> Tag:
        """Figure out where the details are stored."""
        all_views = soup.find_all("div", class_=view_class)
        if len(all_views) <= view_index:
            raise LegistarError(f"Could not find view with index {view_index}")
        maybe_view = all_views[view_index]
        if not isinstance(maybe_view, Tag):
            raise LegistarError(f"Unexpected view: {maybe_view}")
        return maybe_view

    def _build_details(
        self,
        view: Tag,
    ) -> list[Tag]:
        """
        Return an ordered list of labels and values.

        There may be 0 or more values for each label.
        """
        view_children = children_of_type_before(view, of_type="table", before="div")

        def _is_selected_option(tag: Tag) -> bool:
            return tag.name == "option" and tag.has_attr("selected")

        def _is_span_with_nested_a(tag: Tag) -> bool:
            return tag.name == "span" and len(tag.find_all("a")) > 0

        def _child_filter(tag: Tag) -> bool:
            if tag.name == "span" and _is_span_with_nested_a(tag):
                return False
            if tag.name == "option" and not _is_selected_option(tag):
                return False
            return True

        return list(
            find_in_sequence(
                view_children,
                {"span", "a", "option"},
                filter=_child_filter,
            )
        )

    def _build_labels(self) -> list[str]:
        """Return a list of all labels in the view."""
        return [
            clean_header(detail.text)
            for detail in self._details
            if self._is_label(detail)
        ]

    def has_label(self, label: str) -> bool:
        """Return True if the label exists in the view."""
        return label in self.labels

    def get_label_detail_index(self, label: str) -> int:
        """Get the index of the given label in the details list."""
        clean_label = clean_header(label)
        maybe_index = next(
            (
                i
                for i, detail in enumerate(self._details)
                if self._is_label(detail) and clean_header(detail.text) == clean_label
            ),
            None,
        )
        if maybe_index is None:
            raise LegistarError(f"Could not find label {label}")
        return maybe_index

    def get_text(self, label: str, join_with: str = " ") -> str:
        """
        Get the text value for a given label.

        If there are multiple values for the label, they will be joined with
        `join_with`.
        """
        label_index = self.get_label_detail_index(label)
        maybe_values = self._details[label_index + 1 :]
        values = list(
            itertools.takewhile(lambda detail: not self._is_label(detail), maybe_values)
        )
        final = join_with.join(clean_text(value.text) for value in values).strip()
        if not final:
            raise LegistarError(f"Could not find text for {label}")
        return final

    def get_optional_text(self, label: str, join_with: str = " ") -> str | None:
        """
        Get the text value for a given label.

        If there are multiple values for the label, they will be joined with
        `join_with`.
        """
        try:
            return self.get_text(label, join_with)
        except LegistarError:
            return None

    def get_int(self, label: str) -> int:
        """Get the integer value for a given label."""
        text = self.get_text(label)
        try:
            return int(text)
        except ValueError:
            raise LegistarError(f"Could not parse {text} as an integer")

    def get_optional_int(self, label: str) -> int | None:
        """Get the integer value for a given label."""
        try:
            return self.get_int(label)
        except LegistarError:
            return None

    def get_datetime(self, label: str) -> datetime.datetime:
        """Get the datetime value for a given label."""
        text = self.get_text(label)
        return datetime.datetime.strptime(text, "%m/%d/%Y %I:%M %p")

    def get_optional_datetime(self, label: str) -> datetime.datetime | None:
        """Get the datetime value for a given label."""
        try:
            return self.get_datetime(label)
        except LegistarError:
            return None

    def get_date_and_time(self, label: str) -> tuple[datetime.date, datetime.time]:
        """Get the date and time value for a given label."""
        text = self.get_text(label)
        date, time = text.split(" ", maxsplit=1)
        return (
            datetime.datetime.strptime(date, "%m/%d/%Y").date(),
            datetime.datetime.strptime(time, "%I:%M %p").time(),
        )

    def get_date_and_optional_time(
        self, label: str
    ) -> tuple[datetime.date, datetime.time | None]:
        """Get the date and time value for a given label."""
        text = self.get_text(label)
        date, time = text.split(" ", maxsplit=1)
        return (
            datetime.datetime.strptime(date, "%m/%d/%Y").date(),
            datetime.datetime.strptime(time, "%I:%M %p").time()
            if time and time.lower().strip() != "canceled"
            else None,
        )

    def get_date(self, label: str) -> datetime.date:
        """Get the date value for a given label."""
        text = self.get_text(label)
        return datetime.datetime.strptime(text, "%m/%d/%Y").date()

    def get_optional_date(self, label: str) -> datetime.date | None:
        """Get the date value for a given label."""
        try:
            return self.get_date(label)
        except LegistarError:
            return None

    def get_time(self, label: str) -> datetime.time:
        """Get the time value for a given label."""
        text = self.get_text(label)
        return datetime.datetime.strptime(text, "%I:%M %p").time()

    def get_optional_time(self, label: str) -> datetime.time | None:
        """Get the time value for a given label."""
        try:
            return self.get_time(label)
        except LegistarError:
            return None

    def get_link(self, label: str) -> Link:
        """Get the link and text value for a given label."""
        label_index = self.get_label_detail_index(label)
        maybe_values = self._details[label_index + 1 :]
        values = list(
            itertools.takewhile(lambda detail: not self._is_label(detail), maybe_values)
        )
        if len(values) != 1:
            raise LegistarError(f"Expected 1 value for {label}, got {len(values)}")
        value = values[0]
        if not isinstance(value, Tag):
            raise LegistarError(f"Unexpected value: {value}")
        return get_link_from_a_tag(value, base_url=self.scraper.base_url)

    def get_optional_link(self, label: str) -> Link | None:
        """Get the link and text value for a given label, if it exists."""
        try:
            return self.get_link(label)
        except LegistarError:
            return None

    def get_links(self, label: str) -> list[Link]:
        """Get a collection of link and text values for a given label."""
        label_index = self.get_label_detail_index(label)
        maybe_values = self._details[label_index + 1 :]
        values = list(
            itertools.takewhile(lambda detail: not self._is_label(detail), maybe_values)
        )
        maybe_links = [
            get_optional_link_from_a_tag(value, base_url=self.scraper.base_url)
            for value in values
        ]
        return [link for link in maybe_links if link is not None]


# ---------------------------------------------------------------------
# Top level scraper API (this is probably what you're looking for!)
# ---------------------------------------------------------------------


class LegistarScraper:
    """
    A simple scraper for specific pages on the Legistar website.

    This is intended to complement the Legistar API client. Alas, the API
    only provides a subset of the data available on the website.
    """

    def __init__(self, customer: str):
        self.customer = customer
        self.base_url = f"https://{customer}.legistar.com"

    def _url(self, path: str, **queryparams):
        """Form a URL for the given path and query parameters."""
        url = urllib.parse.urljoin(f"{self.base_url}/", path)
        query_str = urllib.parse.urlencode(queryparams)
        return f"{url}?{query_str}" if query_str else url

    def _get(self, path: str, **queryparams) -> str:
        """Perform a GET request for the given path and query parameters."""
        url = self._url(path, **queryparams)
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise LegistarError(str(e)) from e
        return response.text

    def _get_soup(self, path: str, **queryparams) -> BeautifulSoup:
        """Perform a GET request and return a BeautifulSoup object."""
        text = self._get(path, **queryparams)
        return BeautifulSoup(text, features="lxml")

    def _get_table_scraper(
        self, path: str, exact_headers: list[str], **queryparams
    ) -> TableScraper:
        """Perform a GET request and return a TableScraper object."""
        soup = self._get_soup(path, **queryparams)
        table_scraper = TableScraper.from_soup(self, soup)
        if table_scraper.headers != exact_headers:
            raise LegistarError(f"Unexpected headers: {table_scraper.headers}")
        return table_scraper

    def _get_detail_scraper(
        self, path: str, required_labels: set[str], **queryparams
    ) -> DetailScraper:
        """Perform a GET request and return a DetailScraper object."""
        soup = self._get_soup(path, **queryparams)
        detail_scraper = DetailScraper(self, soup)
        if set(detail_scraper.labels) < required_labels:
            raise LegistarError(f"Unexpected labels: {detail_scraper.labels}")
        return detail_scraper

    def _get_detail_and_table_scraper(
        self,
        path: str,
        exact_table_headers: list[str],
        required_detail_labels: set[str],
        **queryparams,
    ) -> tuple[DetailScraper, TableScraper]:
        """Perform a GET request and return a TableScraper and DetailScraper object."""
        soup = self._get_soup(path, **queryparams)
        table_scraper = TableScraper.from_soup(self, soup)
        if table_scraper.headers != exact_table_headers:
            raise LegistarError(f"Unexpected headers: {table_scraper.headers}")
        detail_scraper = DetailScraper(self, soup)
        if set(detail_scraper.labels) < set(required_detail_labels):
            raise LegistarError(f"Unexpected labels: {detail_scraper.labels}")
        return detail_scraper, table_scraper

    def get_calendar_rows(self, future_only: bool = False) -> list[CalendarRow]:
        """Get rows from the calendar page."""
        table_scraper = self._get_table_scraper("/Calendar.aspx", CALENDAR_ROW_HEADERS)
        rows = [_make_calendar_row(row) for row in table_scraper]
        if future_only:
            rows = [row for row in rows if row.date >= datetime.date.today()]
        return rows

    def get_calendar(self, future_only: bool = False) -> Calendar:
        """Get the calendar."""
        # CONSIDER: this mostly exists for symmetry/completeness.
        # Unlike /MeetingDetail.aspx, /LegislationDetail.aspx,
        # and /HistoryDetail.aspx, /Calendar.aspx does not have top-level
        # details.
        return Calendar(rows=self.get_calendar_rows(future_only=future_only))

    def get_meeting_rows(self, meeting_id: int, meeting_guid: str) -> list[MeetingRow]:
        """Get rows from a single meeting detail page."""
        table_scraper = self._get_table_scraper(
            "/MeetingDetail.aspx",
            MEETING_ROW_HEADERS,
            ID=meeting_id,
            GUID=meeting_guid,
        )
        return [_make_meeting_row(row) for row in table_scraper]

    def get_meeting(self, meeting_id: int, meeting_guid: str) -> Meeting:
        """Get details + rows from a single meeting detail page."""
        detail_scraper, table_scraper = self._get_detail_and_table_scraper(
            "/MeetingDetail.aspx",
            MEETING_ROW_HEADERS,
            MEETING_DETAIL_LABELS,
            ID=meeting_id,
            GUID=meeting_guid,
        )
        return _make_meeting(detail_scraper, table_scraper)

    def get_legislation_rows(
        self, legislation_id: int, legislation_guid: str
    ) -> list[LegislationRow]:
        """Get the legislation detail for a given calendar entry."""
        table_scraper = self._get_table_scraper(
            "/LegislationDetail.aspx",
            LEGISLATION_ROW_HEADERS,
            ID=legislation_id,
            GUID=legislation_guid,
        )
        return [_make_legislation_row(row) for row in table_scraper]

    def get_legislation(
        self, legislation_id: int, legislation_guid: str
    ) -> Legislation:
        """Get the legislation detail for a given calendar entry."""
        detail_scraper, table_scraper = self._get_detail_and_table_scraper(
            "/LegislationDetail.aspx",
            LEGISLATION_ROW_HEADERS,
            LEGISLATION_DETAIL_LABELS,
            ID=legislation_id,
            GUID=legislation_guid,
        )
        return _make_legislation(detail_scraper, table_scraper)

    def get_action_rows(self, action_id: int, action_guid: str) -> list[ActionRow]:
        """Get the action detail for a given calendar entry."""
        table_scraper = self._get_table_scraper(
            "/HistoryDetail.aspx",
            ACTION_ROW_HEADERS,
            ID=action_id,
            GUID=action_guid,
        )
        return [_make_action_row(row) for row in table_scraper]

    def get_action(self, action_id: int, action_guid: str) -> Action:
        """Get the action detail for a given calendar entry."""
        detail_scraper, table_scraper = self._get_detail_and_table_scraper(
            "/HistoryDetail.aspx",
            ACTION_ROW_HEADERS,
            ACTION_DETAIL_LABELS,
            ID=action_id,
            GUID=action_guid,
        )
        return _make_action(detail_scraper, table_scraper)
