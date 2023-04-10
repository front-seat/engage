import datetime
import json
from functools import wraps

import djclick as click

from server.lib.legistar import LegistarClient


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


def _echo_jsonable(jsonable: list | dict, lines: bool = False, indent: int | None = 2):
    """
    Given an arbitrary json-serializable structure, echo it to stdout.

    If `lines` is True, then each item in a list is dumped on a separate line
    and `indent` is ignored.
    """
    if lines and isinstance(jsonable, list):
        for item in jsonable:
            click.echo(json.dumps(item))
    elif lines:
        click.echo(json.dumps(jsonable))
    else:
        click.echo(json.dumps(jsonable, indent=indent))


@click.group(invoke_without_command=True)
def main():
    """Work with data on the Legistar website."""
    context = click.get_current_context()
    if context.invoked_subcommand is None:
        click.echo(context.get_help())


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
    response = client.get_body_dicts(top=top, skip=skip)
    _echo_jsonable(response, lines)


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
    response = client.get_event_dicts(
        top=top,
        skip=skip,
        event_start_date=event_start_date,
        event_end_date=event_end_date,
    )
    _echo_jsonable(response, lines)


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
    _echo_jsonable([str(r) for r in response], lines)


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
    response = client.get_matter_dicts(
        top=top,
        skip=skip,
        body_id=body_id,
        agenda_start_date=agenda_start_date,
        agenda_end_date=agenda_end_date,
    )
    _echo_jsonable(response, lines)
