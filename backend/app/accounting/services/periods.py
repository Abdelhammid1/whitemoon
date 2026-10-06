"""Period open / close / reopen (US-3.6).

Each state change is a sensitive action — the route layer gates with
`period.close` / `period.reopen` permissions and emits audit events.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import UTC, date, datetime

from sqlalchemy import select

from ...common.errors import BadRequest, Conflict, NotFound
from ...extensions import db
from ..models import Period


def ensure_period(*, year: int, month: int) -> Period:
    """Idempotent — returns the existing period, or creates it."""
    if not (1 <= month <= 12):  # noqa: PLR2004
        raise BadRequest("month must be 1..12", code="period_month_invalid")

    existing = db.session.execute(
        select(Period).where(Period.year == year, Period.month == month)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    last_day = monthrange(year, month)[1]
    period = Period(
        year=year,
        month=month,
        starts_on=date(year, month, 1),
        ends_on=date(year, month, last_day),
    )
    db.session.add(period)
    db.session.commit()  # persist — each request is its own transaction (T-25)
    return period


def close(*, year: int, month: int, closed_by: int) -> Period:
    period = db.session.execute(
        select(Period).where(Period.year == year, Period.month == month)
    ).scalar_one_or_none()
    if period is None:
        raise NotFound("Period not found", code="period_not_found")
    if period.is_closed:
        raise Conflict("Period already closed", code="period_already_closed")
    period.is_closed = True
    period.closed_by = closed_by
    period.closed_at = datetime.now(UTC)
    db.session.commit()  # T-25: persist the close
    return period


def reopen(*, year: int, month: int, reopened_by: int) -> Period:  # noqa: ARG001
    period = db.session.execute(
        select(Period).where(Period.year == year, Period.month == month)
    ).scalar_one_or_none()
    if period is None:
        raise NotFound("Period not found", code="period_not_found")
    if not period.is_closed:
        raise Conflict("Period is not closed", code="period_not_closed")
    period.is_closed = False
    period.closed_by = None
    period.closed_at = None
    db.session.commit()  # T-25: persist the reopen
    return period
