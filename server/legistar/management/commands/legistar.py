import datetime
import json
import sys
from functools import wraps

import djclick as click
from pydantic import BaseModel as PydanticBase

from server.legistar.lib import (
    ActionSchema,
    CalendarSchema,
    LegislationSchema,
    LegistarCalendarCrawler,
    LegistarClient,
    LegistarScraper,
    MeetingSchema,
)
from server.legistar.models import Action, Legislation, Meeting


def _common_params(func):
    """Define common parameters for all commands."""

    @click.option("--customer", default="seattle", help="Legistar customer")
    @click.option(
        "--lines",
        is_flag=True,
        default=False,
        help="If set, each item in a list is dumped on a separate line.",
    )
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def _common_api_params(func):
    """Define common parameters for all LegistarClient commands."""

    @click.option(
        "--api-url",
        default="https://webapi.legistar.com/v1",
        help="Legistar API base URL",
    )
    @click.option(
        "--top",
        type=int,
        default=None,
        help="If set, only the first `top` items are returned.",
    )
    @click.option(
        "--skip",
        type=int,
        default=None,
        help="If set, the first `skip` items are skipped.",
    )
    @_common_params
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


# For now...
_common_scraper_params = _common_params


def _echo_response(
    data: list | dict | PydanticBase, lines: bool = False, indent: int | None = 2
):
    """
    Given an arbitrary json-serializable structure, echo it to stdout.

    If `lines` is True, then each item in a list is dumped on a separate line
    and `indent` is ignored.
    """
    if isinstance(data, list):
        for item in data:
            _echo_response(item, lines=lines, indent=indent)
    elif isinstance(data, PydanticBase):
        click.echo(data.json(indent=None if lines else indent))
    else:
        click.echo(json.dumps(data, indent=None if lines else indent))


@click.group(invoke_without_command=True)
def main():
    """Work with data on the Legistar website."""
    context = click.get_current_context()
    if context.invoked_subcommand is None:
        click.echo(context.get_help())


@main.command()
@click.option("--body-id", type=int, help="Legistar body ID", required=True)
@_common_api_params
def get_body(
    customer: str,
    api_url: str,
    lines: bool,
    body_id: int,
    top: int | None = None,
    skip: int | None = None,
):
    """Get a legislative body."""
    client = LegistarClient(customer, api_url)
    response = client.get_body(body_id)
    _echo_response(response, lines)


@main.command()
@_common_api_params
def get_bodies(
    customer: str,
    api_url: str,
    lines: bool,
    top: int | None = None,
    skip: int | None = None,
):
    """Get all legislative bodies."""
    client = LegistarClient(customer, api_url)
    response = client.get_bodies(top=top, skip=skip)
    _echo_response(response, lines)


@main.command()
@click.option(
    "--event-start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Only return events on or after this date (YYYY-MM-DD).",
)
@click.option(
    "--event-end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Only return events on or before this date (YYYY-MM-DD).",
)
@_common_api_params
def get_events(
    customer: str,
    api_url: str,
    lines: bool,
    top: int | None = None,
    skip: int | None = None,
    event_start_date: datetime.datetime | None = None,
    event_end_date: datetime.datetime | None = None,
):
    """Get all events."""
    client = LegistarClient(customer, api_url)
    response = client.get_events(
        top=top,
        skip=skip,
        event_start_date=event_start_date,
        event_end_date=event_end_date,
    )
    _echo_response(response, lines)


@main.command()
@click.option("--body-id", type=int, help="Legistar body ID", required=True)
@_common_api_params
def get_event_dates_for_body(
    customer: str,
    api_url: str,
    body_id: int,
    lines: bool,
    top: int | None = None,
    skip: int | None = None,
):
    """Get all event dates for the given body."""
    client = LegistarClient(customer, api_url)
    response = client.get_event_dates_for_body(
        body_id,
        top=top,
        skip=skip,
    )
    _echo_response([str(r) for r in response], lines)


@main.command()
@click.option("--matter-id", type=int, help="Legistar matter ID", required=True)
@_common_api_params
def get_matter(
    customer: str,
    api_url: str,
    matter_id: int,
    lines: bool,
    top: int | None = None,
    skip: int | None = None,
):
    """Get a single matter."""
    client = LegistarClient(customer, api_url)
    response = client.get_matter(matter_id)
    _echo_response(response, lines)


@main.command()
@click.option("--body-id", type=int, help="Legistar body ID", default=None)
@click.option(
    "--agenda-start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Only return events on or after this date (YYYY-MM-DD).",
)
@click.option(
    "--agenda-end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=None,
    help="Only return events on or before this date (YYYY-MM-DD).",
)
@_common_api_params
def get_matters(
    customer: str,
    api_url: str,
    lines: bool,
    body_id: int | None = None,
    top: int | None = None,
    skip: int | None = None,
    agenda_start_date: datetime.datetime | None = None,
    agenda_end_date: datetime.datetime | None = None,
):
    """Get all matters."""
    client = LegistarClient(customer, api_url)
    response = client.get_matters(
        top=top,
        skip=skip,
        body_id=body_id,
        agenda_start_date=agenda_start_date,
        agenda_end_date=agenda_end_date,
    )
    _echo_response(response, lines)


@main.command()
@_common_api_params
def get_upcoming_matters(
    customer: str,
    api_url: str,
    lines: bool,
    top: int | None = None,
    skip: int | None = None,
):
    """Get all upcoming matters."""
    client = LegistarClient(customer, api_url)
    response = client.get_matters(
        top=top,
        skip=skip,
        agenda_start_date=datetime.datetime.now(),
    )
    _echo_response(response, lines)


@main.command()
@_common_scraper_params
def get_calendar_rows(
    customer: str,
    lines: bool,
):
    """Get a legislative body's calendar rows via scraping."""
    scaper = LegistarScraper(customer)
    response = scaper.get_calendar_rows()
    _echo_response(response, lines)


@main.command()
@_common_scraper_params
def get_calendar(
    customer: str,
    lines: bool,
):
    """Get a legislative body's calendar details + rows via scraping."""
    scaper = LegistarScraper(customer)
    response = scaper.get_calendar()
    _echo_response(response, lines)


@main.command()
@click.argument("meeting_id", type=int, required=True)
@click.argument("meeting_guid", type=str, required=True)
@_common_scraper_params
def get_meeting_rows(
    customer: str,
    lines: bool,
    meeting_id: int,
    meeting_guid: str,
):
    """Get a legislative body's meeting rows via scraping."""
    scaper = LegistarScraper(customer)
    response = scaper.get_meeting_rows(meeting_id, meeting_guid)
    _echo_response(response, lines)


@main.command()
@click.argument("meeting_id", type=int, required=True)
@click.argument("meeting_guid", type=str, required=True)
@_common_scraper_params
def get_meeting(
    customer: str,
    lines: bool,
    meeting_id: int,
    meeting_guid: str,
):
    """Get a legislative body's meeting details + rows via scraping."""
    scaper = LegistarScraper(customer)
    response = scaper.get_meeting(meeting_id, meeting_guid)
    _echo_response(response, lines)


@main.command()
@click.argument("legislation_id", type=int, required=True)
@click.argument("legislation_guid", type=str, required=True)
@_common_scraper_params
def get_legislation_rows(
    customer: str,
    lines: bool,
    legislation_id: int,
    legislation_guid: str,
):
    """Get a legislative body's legislation items via scraping."""
    scaper = LegistarScraper(customer)
    response = scaper.get_legislation_rows(legislation_id, legislation_guid)
    _echo_response(response, lines)


@main.command()
@click.argument("legislation_id", type=int, required=True)
@click.argument("legislation_guid", type=str, required=True)
@_common_scraper_params
def get_legislation(
    customer: str,
    lines: bool,
    legislation_id: int,
    legislation_guid: str,
):
    """Get a legislative body's legislation details + rows via scraping."""
    scaper = LegistarScraper(customer)
    response = scaper.get_legislation(legislation_id, legislation_guid)
    _echo_response(response, lines)


@main.command()
@click.argument("action_id", type=int, required=True)
@click.argument("action_guid", type=str, required=True)
@_common_scraper_params
def get_action_rows(
    customer: str,
    lines: bool,
    action_id: int,
    action_guid: str,
):
    """Get a legislative body's action items via scraping."""
    scaper = LegistarScraper(customer)
    response = scaper.get_action_rows(action_id, action_guid)
    _echo_response(response, lines)


@main.command()
@click.argument("action_id", type=int, required=True)
@click.argument("action_guid", type=str, required=True)
@_common_scraper_params
def get_action(
    customer: str,
    lines: bool,
    action_id: int,
    action_guid: str,
):
    """Get a legislative body's action details + rows via scraping."""
    scraper = LegistarScraper(customer)
    response = scraper.get_action(action_id, action_guid)
    _echo_response(response, lines)


@main.command()
@click.option(
    "--future-only", is_flag=True, help="Only return future events.", default=False
)
@click.option("--debug", is_flag=True, help="Print debug info.", default=False)
@click.option(
    "--db", is_flag=True, help="Update database, including attachments.", default=False
)
@_common_scraper_params
def crawl_calendar(
    customer: str,
    lines: bool,
    future_only: bool,
    db: bool,
    debug: bool,
):
    """Get all events."""

    def _update_meeting_db(schema: MeetingSchema) -> None:
        """Create or update meeting in database."""
        meeting, created = Meeting.objects.update_or_create_from_schema(schema)
        if debug:
            verb = "created" if created else "updated"
            print(
                f">>>> DEBUG: Meeting {meeting.pk} ({meeting.legistar_id}) {verb}.",
                file=sys.stderr,
            )

    def _update_legislation_db(schema: LegislationSchema) -> None:
        """Create or update legislation in database."""
        legislation, created = Legislation.objects.update_or_create_from_schema(schema)
        if debug:
            verb = "created" if created else "updated"
            print(
                f"Legislation {legislation.pk} ({legislation.legistar_id}) {verb}.",
                file=sys.stderr,
            )

    def _update_action_db(schema: ActionSchema) -> None:
        """Create or update action in database."""
        action, created = Action.objects.update_or_create_from_schema(schema)
        if debug:
            verb = "created" if created else "updated"
            print(f"Action {action.pk} ({action.legistar_id}) {verb}.", file=sys.stderr)

    def _update_db(
        item: CalendarSchema | MeetingSchema | LegislationSchema | ActionSchema,
    ) -> None:
        """Update the database."""
        if isinstance(item, MeetingSchema):
            _update_meeting_db(item)
        elif isinstance(item, LegislationSchema):
            _update_legislation_db(item)
        elif isinstance(item, ActionSchema):
            _update_action_db(item)
        elif not isinstance(item, CalendarSchema):
            raise ValueError(f"Unexpected item type: {type(item)}")

    crawler = LegistarCalendarCrawler(customer, future_only=future_only, debug=debug)
    for item in crawler.crawl():
        _echo_response(item, lines)
        if db:
            _update_db(item)