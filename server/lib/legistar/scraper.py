from __future__ import annotations

import datetime
import typing as t
import urllib.parse

import requests
from bs4 import BeautifulSoup, Tag

from .errors import LegistarError
from .schema import CalendarEntry

CALENDAR_HEADERS = [
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


def clean_text(text: str) -> str:
    """Clean up text from the Legistar website."""
    return text.replace("\xa0", " ").strip()


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
        return clean_text(maybe_text)

    def get_optional_text(self, header: str) -> str | None:
        """Get the text of the cell in the given column, if it exists."""
        maybe_text = self.row.find_all("td")[
            self.table_scraper.get_header_index(header)
        ].text
        if not isinstance(maybe_text, str):
            return None
        return clean_text(maybe_text)

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

    def get_link_and_text(self, header: str) -> tuple[str, str]:
        """Get the link and text of the cell in the given column."""
        maybe_link = self.row.find_all("td")[
            self.table_scraper.get_header_index(header)
        ].find("a")
        if not isinstance(maybe_link, Tag):
            raise LegistarError(f"Could not find link for header {header}")
        href = maybe_link.get("href")
        if not isinstance(href, str):
            raise LegistarError(f"Could not find href for header {header}")
        absolute_href = urllib.parse.urljoin(self.table_scraper.scraper.base_url, href)
        return clean_text(maybe_link.text), absolute_href

    def get_optional_link_and_text(
        self, header: str
    ) -> tuple[str, str] | tuple[None, None]:
        """Get the link and text of the cell in the given column, if it exists."""
        maybe_link = self.row.find_all("td")[
            self.table_scraper.get_header_index(header)
        ].find("a")
        if not isinstance(maybe_link, Tag):
            return None, None
        href = maybe_link.get("href")
        if not isinstance(href, str):
            return None, None
        absolute_href = urllib.parse.urljoin(self.table_scraper.scraper.base_url, href)
        return clean_text(maybe_link.text), absolute_href


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

    def _clean_header(self, header: str) -> str:
        """Clean up a header string."""
        return header.replace(":", "").lower().strip()

    def _build_headers(self, header_class: str) -> list[str]:
        """Populate the headers list."""
        return [
            self._clean_header(header.text)
            for header in self.table.find_all("th", class_=header_class)
        ]

    def get_header_index(self, header: str) -> int:
        """Get the index of the given header."""
        maybe_index = self._indexes.get(self._clean_header(header))
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

    def _get_table_scraper(
        self, path: str, expected_headers: list[str], **queryparams
    ) -> TableScraper:
        """Perform a GET request and return a TableScraper object."""
        soup = self._get_soup(path, **queryparams)
        table_scraper = TableScraper.from_soup(self, soup)
        if table_scraper.headers != expected_headers:
            raise LegistarError(f"Unexpected headers: {table_scraper.headers}")
        return table_scraper

    def get_calendar(self) -> list[CalendarEntry]:
        """Get the calendar."""
        table_scraper = self._get_table_scraper("/Calendar.aspx", CALENDAR_HEADERS)

        def _make_entry(row: RowScraper) -> CalendarEntry:
            body, body_url = row.get_link_and_text("name")
            date = row.get_date("meeting date")
            time = row.get_optional_time("meeting time")
            location = row.get_text("meeting location")
            _, details_url = row.get_link_and_text("meeting details")
            _, agenda_url = row.get_link_and_text("agenda")
            _, agenda_packet_url = row.get_optional_link_and_text("agenda packet")
            _, minutes_url = row.get_optional_link_and_text("minutes")
            _, video_url = row.get_optional_link_and_text("seattle channel")

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

        return [_make_entry(row) for row in table_scraper]
