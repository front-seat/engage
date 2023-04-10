import json
from functools import wraps

import djclick as click

from server.lib.legistar import LegistarClient


def _common_params(func):
    @click.option("--customer", default="seattle", help="Legistar customer")
    @click.option(
        "--api-url",
        default="https://webapi.legistar.com/v1",
        help="Legistar API base URL",
    )
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
@_common_params
def get_bodies(customer: str, api_url: str, lines: bool):
    """Get all legislative bodies."""
    client = LegistarClient(customer, api_url)
    response = client.get_bodies()
    _echo_jsonable(response, lines)


@main.command()
def events():
    """Import Legistar events."""
    click.secho("Importing Legistar events")
    click.secho("Importing Legistar events")
