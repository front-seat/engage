"""
Simple tools for managing OData query parameters.

Legistar's API uses these, but only in the simplest way; adopting the official
OData Python library would be (painful) overkill.
"""
from __future__ import annotations

import datetime
import typing as t


def odata_queryparams(
    top: int | None = None,
    skip: int | None = None,
    filter: Filter | None = None,
    orderby: str | None = None,
) -> dict[str, str]:
    """Form OData query parameters as a dictionary."""
    queryparams = {}
    if top is not None:
        queryparams["$top"] = str(top)
    if skip is not None:
        queryparams["$skip"] = str(skip)
    if filter is not None:
        queryparams["$filter"] = str(filter)
    if orderby is not None:
        queryparams["$orderby"] = orderby
    return queryparams


FilterOp = t.Literal["eq", "ne", "gt", "ge", "lt", "le"]


class Filter:
    """Base class for OData filters."""

    def __str__(self):
        raise NotImplementedError


class AndFilter(Filter):
    """Form a filter query value."""

    def __init__(self, *filters: Filter):
        self.filters = filters

    def __str__(self):
        return " and ".join(str(f) for f in self.filters)


class ComparisonFilter(Filter):
    """Form a filter query value."""

    def __init__(self, field: str, op: FilterOp, value: str):
        self.field = field
        self.op = op
        self.value = value

    def __str__(self):
        return f"{self.field} {self.op} {self.value}"


class DateComparisonFilter(ComparisonFilter):
    """Form a filter query value."""

    def __init__(self, field: str, op: FilterOp, value: datetime.date):
        super().__init__(field, op, f"datetime'{value.isoformat()}'")
        super().__init__(field, op, f"datetime'{value.isoformat()}'")
