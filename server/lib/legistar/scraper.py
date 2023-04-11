import datetime
import typing as t
import urllib.parse

import requests
from bs4 import BeautifulSoup, Tag

from .errors import LegistarError
from .schema import CalendarEntry


class CalendarColumn:
    NAME = 0
    MEETING_DATE = 1
    MEETING_CALENDAR = 2
    MEETING_TIME = 3
    MEETING_LOCATION = 4
    MEETING_DETAILS = 5
    AGENDA = 6
    AGENDA_PACKET = 7
    MINUTES = 8
    SEATTLE_CHANNEL = 9


CALENDAR_EXPECTED_COLUMNS = [
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
        return BeautifulSoup(text)

    def _clean_text(self, text: str) -> str:
        return text.encode("ascii", errors="ignore").decode("ascii").strip()

    def _cell_link(
        self, cell: t.Any, required: bool = True
    ) -> tuple[str, str] | tuple[None, None]:
        if not isinstance(cell, Tag):
            if required:
                raise LegistarError(f"_cell_link: expected Tag, got {type(cell)}")
            return (None, None)
        link = cell.find("a")
        if not isinstance(link, Tag):
            if required:
                raise LegistarError(f"_cell_link: expected Tag, got {type(link)}")
            return (None, None)
        href = link.get("href")
        if not isinstance(href, str):
            if required:
                raise LegistarError(f"_cell_link: expected str, got {type(href)}")
            return (None, None)
        absolute_href = urllib.parse.urljoin(self.base_url, href)
        text = self._clean_text(cell.text)
        return (text, absolute_href)

    def _cell_text(self, cell: t.Any, required: bool = True) -> str | None:
        if not isinstance(cell, Tag):
            if required:
                raise LegistarError(f"_cell_text: expected Tag, got {type(cell)}")
            return None
        text = self._clean_text(cell.text)
        return text

    def _cell_date(self, cell: t.Any, required: bool = True) -> datetime.date | None:
        text = self._cell_text(cell, required=required)
        if text is None:
            return None
        try:
            return datetime.datetime.strptime(text, "%m/%d/%Y").date()
        except ValueError as e:
            raise LegistarError(f"_cell_date: could not parse {text}") from e

    def _cell_time(self, cell: t.Any, required: bool = True) -> datetime.time | None:
        text = self._cell_text(cell, required=required)
        if text is None:
            return None
        try:
            return datetime.datetime.strptime(text, "%H:%M %p").time()
        except ValueError as e:
            if text.lower() == "canceled":
                return None
            raise LegistarError(f"_cell_time: could not parse {text}") from e

    def get_calendar(self) -> list[CalendarEntry]:
        """Get the calendar."""
        soup = self._get_soup("/Calendar.aspx")
        table = soup.find("table", class_="rgMasterTable")
        if not isinstance(table, Tag):
            raise LegistarError("get_calendar: could not find calendar table")
        headers = table.find_all("th", class_="rgHeader")
        columns = [
            header.text.encode("ascii", errors="ignore")
            .decode("ascii")
            .lower()
            .replace(":", "")
            .strip()
            for header in headers
        ]
        if columns != CALENDAR_EXPECTED_COLUMNS:
            # FUTURE: for now, just raise an error; in the future, we may
            # want to support other Legistar customers & column names.
            raise LegistarError(
                f"get_calendar: expected: {CALENDAR_EXPECTED_COLUMNS}, got {columns}"
            )

        def make_calendar_entry(row) -> CalendarEntry:
            cells = row.find_all("td")
            body, body_url = self._cell_link(cells[CalendarColumn.NAME])
            assert body is not None
            assert body_url is not None
            date = self._cell_date(cells[CalendarColumn.MEETING_DATE])
            assert date is not None
            time = self._cell_time(cells[CalendarColumn.MEETING_TIME], required=False)
            location = self._cell_text(cells[CalendarColumn.MEETING_LOCATION])
            assert location is not None
            _, details_url = self._cell_link(cells[CalendarColumn.MEETING_DETAILS])
            assert details_url is not None
            _, agenda_url = self._cell_link(cells[CalendarColumn.AGENDA])
            assert agenda_url is not None
            _, agenda_packet_url = self._cell_link(
                cells[CalendarColumn.AGENDA_PACKET], required=False
            )
            _, minutes_url = self._cell_link(
                cells[CalendarColumn.MINUTES], required=False
            )
            _, video_url = self._cell_link(
                cells[CalendarColumn.SEATTLE_CHANNEL], required=False
            )
            return CalendarEntry(
                body=body,
                body_url=body_url,
                date=date,
                time=time,
                location=location,
                details_url=details_url,
                agenda_url=agenda_url,
                agenda_packet_url=agenda_packet_url,
                minutes_url=minutes_url,
                video_url=video_url,
            )

        rows = table.find_all("tr", class_="rgRow")
        entries = [make_calendar_entry(row) for row in rows]
        return entries
