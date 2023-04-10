import enum
import requests
import urllib.parse

from .errors import LegistarError
from .schema import Body, Event, EventDate, Matter


class LegistarCustomer(enum.StrEnum):
    SEATTLE = "seattle"


LEGISTAR_API_BASE_URL = "https://webapi.legistar.com/v1"


class LegistarClient:
    """
    A simple API client for the Legistar API.

    See documentation at https://webapi.legistar.com/Home/Examples
    """

    def __init__(
        self, customer: LegistarCustomer, base_url: str = LEGISTAR_API_BASE_URL
    ):
        self.base_url = base_url
        self.customer = customer.value

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

    def get_bodies(self) -> list[Body]:
        """Get all bodies."""
        data = self._get("Bodies")
        if not isinstance(data, list):
            raise LegistarError(f"get_bodies: expected list, got {type(data)}")
        return data

    def get_events(self) -> list[Event]:
        """Get all events."""
        data = self._get("events")
        if not isinstance(data, list):
            raise LegistarError(f"get_events: expected list, got {type(data)}")
        return data

    def get_event_dates_for_body(
        self, body: int | dict, future_dates_only: bool = False
    ) -> list[EventDate]:
        """Get all events for the given body."""
        body_id = body["BodyId"] if isinstance(body, dict) else body
        data = self._get(
            f"EventDates/{body_id}",
            FutureDatesOnly="true" if future_dates_only else "false",
        )
        if not isinstance(data, list):
            raise LegistarError(f"get_events_for_body: expected list, got {type(data)}")
        return data

    def get_matters(self) -> list[Matter]:
        """Get all matters."""
        data = self._get("Matters")
        if not isinstance(data, list):
            raise LegistarError(f"get_matters: expected list, got {type(data)}")
        return data
