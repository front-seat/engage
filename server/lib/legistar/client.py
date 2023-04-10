import datetime
import urllib.parse

import requests

from .errors import LegistarError
from .odata import AndFilter, ComparisonFilter, DateComparisonFilter, odata_queryparams
from .schema import Body, BodyDict, Event, EventDict, Matter, MatterDict

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
            raise LegistarError from e
        return response.json()

    def get_body_dicts(
        self, top: int | None = None, skip: int | None = None
    ) -> list[BodyDict]:
        """Get all bodies."""
        queryparams = odata_queryparams(top=top, skip=skip)
        data = self._get("Bodies", **queryparams)
        if not isinstance(data, list):
            raise LegistarError(f"get_bodies: expected list, got {type(data)}")
        return data

    def get_bodies(self, top: int | None = None, skip: int | None = None) -> list[Body]:
        """Get all bodies."""
        data = self.get_body_dicts(top=top, skip=skip)
        return [Body.from_dict(d) for d in data]

    def get_event_dicts(
        self,
        top: int | None = None,
        skip: int | None = None,
        event_start_date: datetime.date | None = None,
        event_end_date: datetime.date | None = None,
    ) -> list[EventDict]:
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
        return data

    def get_events(
        self,
        top: int | None = None,
        skip: int | None = None,
        event_start_date: datetime.date | None = None,
        event_end_date: datetime.date | None = None,
    ) -> list[Event]:
        """Get all events."""
        data = self.get_event_dicts(
            top=top,
            skip=skip,
            event_start_date=event_start_date,
            event_end_date=event_end_date,
        )
        return [Event.from_dict(d) for d in data]

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

    def get_matter_dicts(
        self,
        top: int | None = None,
        skip: int | None = None,
        # CONSIDER: add other Matter filters ()
        body_id: int | None = None,
        agenda_start_date: datetime.date | None = None,
        agenda_end_date: datetime.date | None = None,
    ) -> list[MatterDict]:
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
        return data

    def get_matters(
        self,
        top: int | None = None,
        skip: int | None = None,
        # CONSIDER: add other Matter filters ()
        body_id: int | None = None,
        agenda_start_date: datetime.date | None = None,
        agenda_end_date: datetime.date | None = None,
    ) -> list[Matter]:
        """Get all matters."""
        data = self.get_matter_dicts(
            top=top,
            skip=skip,
            body_id=body_id,
            agenda_start_date=agenda_start_date,
            agenda_end_date=agenda_end_date,
        )
        return [Matter.from_dict(d) for d in data]
