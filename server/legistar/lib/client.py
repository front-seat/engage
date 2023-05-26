import datetime
import urllib.parse

import requests

from .api_schema import BodyAPIData, EventAPIData, MatterAPIData
from .errors import LegistarError
from .odata import AndFilter, ComparisonFilter, DateComparisonFilter, odata_queryparams

LEGISTAR_API_BASE_URL = "https://webapi.legistar.com/v1"


class LegistarClient:
    """
    A simple API client for the Legistar API.

    See documentation at https://webapi.legistar.com/Home/Examples
    """

    def __init__(self, customer: str, base_url: str = LEGISTAR_API_BASE_URL):
        self.base_url = base_url
        self.customer = customer

    def _url(self, path: str, **queryparams):
        """Form a URL for the given path and query parameters."""
        url = urllib.parse.urljoin(f"{self.base_url}/{self.customer}/", path)
        query_str = urllib.parse.urlencode(queryparams)
        return f"{url}?{query_str}" if query_str else url

    def _get(self, path: str, **queryparams) -> list | dict:
        """Perform a GET request for the given path and query parameters."""
        url = self._url(path, **queryparams)
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise LegistarError(str(e)) from e
        return response.json()

    def get_body(self, body_id: int) -> BodyAPIData:
        """Get a body by ID."""
        data = self._get(f"Bodies/{body_id}")
        return BodyAPIData.parse_obj(data)

    def get_bodies(
        self, top: int | None = None, skip: int | None = None
    ) -> list[BodyAPIData]:
        """Get all bodies."""
        queryparams = odata_queryparams(top=top, skip=skip)
        data = self._get("Bodies", **queryparams)
        if not isinstance(data, list):
            raise LegistarError(f"get_bodies: expected list, got {type(data)}")
        return [BodyAPIData.parse_obj(d) for d in data]

    def get_events(
        self,
        top: int | None = None,
        skip: int | None = None,
        event_start_date: datetime.date | None = None,
        event_end_date: datetime.date | None = None,
    ) -> list[EventAPIData]:
        """Get all events."""
        filter = None
        if event_start_date is not None:
            filter = DateComparisonFilter("EventDate", "ge", event_start_date)
        if event_end_date is not None:
            end_filter = DateComparisonFilter("EventDate", "le", event_end_date)
            filter = AndFilter(filter, end_filter) if filter else end_filter
        queryparams = odata_queryparams(top=top, skip=skip, filter=filter)
        data = self._get("events", **queryparams)
        if not isinstance(data, list):
            raise LegistarError(f"get_events: expected list, got {type(data)}")
        return [EventAPIData.parse_obj(d) for d in data]

    def get_event_dates_for_body(
        self,
        body: int | dict,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[datetime.date]:
        """Get all events for the given body."""
        queryparams = odata_queryparams(top=top, skip=skip)
        body_id = body["BodyId"] if isinstance(body, dict) else body
        data = self._get(
            f"EventDates/{body_id}",
            **queryparams,
        )
        if not isinstance(data, list):
            raise LegistarError(f"get_event_dates: expected list, got {type(data)}")
        return [datetime.datetime.fromisoformat(d).date() for d in data]

    def get_matter(self, matter_id: int) -> MatterAPIData:
        """Get a matter by ID."""
        data = self._get(f"Matters/{matter_id}")
        if not isinstance(data, dict):
            raise LegistarError(f"get_matter: expected dict, got {type(data)}")
        return MatterAPIData.parse_obj(data)

    def get_matters(
        self,
        top: int | None = None,
        skip: int | None = None,
        # CONSIDER: add other Matter filters ()
        body_id: int | None = None,
        agenda_start_date: datetime.date | None = None,
        agenda_end_date: datetime.date | None = None,
    ) -> list[MatterAPIData]:
        """Get all matters."""
        filter = None
        if body_id is not None:
            filter = ComparisonFilter("MatterBodyId", "eq", str(body_id))
        if agenda_start_date is not None:
            start_filter = DateComparisonFilter(
                "MatterAgendaDate", "ge", agenda_start_date
            )
            filter = AndFilter(filter, start_filter) if filter else start_filter
        if agenda_end_date is not None:
            end_filter = DateComparisonFilter("MatterAgendaDate", "le", agenda_end_date)
            filter = AndFilter(filter, end_filter) if filter else end_filter
        queryparams = odata_queryparams(top=top, skip=skip, filter=filter)
        data = self._get("Matters", **queryparams)
        if not isinstance(data, list):
            raise LegistarError(f"get_matters: expected list, got {type(data)}")
        return [MatterAPIData.parse_obj(d) for d in data]
