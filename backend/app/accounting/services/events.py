"""Event → Journal posting engine.

Rules (docs/03-journal-map.md):
- Every operational event posts via `post(event_type, context, ...)`.
- The engine refuses any event without matching rows in
  `accounting.event_journal_map`.
- Account resolution is template-driven: static `account_code`, or
  `rule_json` for conditional selection (by category / by location / etc).
- Amounts come from the `context` dict under the key `amount_source`.
- `source='manual'` entries are a separate path (`post_manual`) that
  requires `high.manual_journal` and sets a session variable to override
  the period-close trigger when posting into a closed period.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text

from ...common.errors import BadRequest, Forbidden, NotFound
from ...common.money import CURRENCY, ensure_egp, to_money
from ...extensions import db
from ..models import (
    Account,
    EventJournalMap,
    JournalEntry,
    JournalLine,
    Period,
)

# ---------------------------------------------------------------- data types


@dataclass(frozen=True)
class LineInput:
    """One side of a manual journal entry (for `post_manual`)."""

    account_code: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    partner_type: str | None = None
    partner_id: int | None = None
    description: str | None = None


@dataclass(frozen=True)
class PostingResult:
    entry_id: int
    entry_no: str


# ---------------------------------------------------------------- public API


def post(
    *,
    event_type: str,
    entry_date: date,
    description: str,
    context: Mapping[str, Any],
    source_event_id: str | int | None = None,
    posted_by: int | None = None,
) -> PostingResult:
    """Create a balanced journal entry from the event→journal map.

    `context` must contain every `amount_source` key referenced by the
    map rows for this event, plus any inputs the rules reference
    (e.g. `category`, `location_type`).
    """
    rows = db.session.execute(
        select(EventJournalMap)
        .where(EventJournalMap.event_type == event_type)
        .order_by(EventJournalMap.step)
    ).scalars().all()
    if not rows:
        raise BadRequest(
            f"No journal map for event '{event_type}'",
            code="event_map_missing",
        )

    entry = _create_entry(
        entry_date=entry_date,
        description=description,
        source="system",
        source_event_type=event_type,
        source_event_id=str(source_event_id) if source_event_id is not None else None,
        posted_by=posted_by,
    )

    accounts_cache: dict[str, int] = {}
    for row in rows:
        account_code = _resolve_account_code(row, context)
        account_id = accounts_cache.get(account_code)
        if account_id is None:
            account_id = _account_id(account_code)
            accounts_cache[account_code] = account_id

        amount = _resolve_amount(row.amount_source, context)
        if amount <= 0:
            raise BadRequest(
                f"Amount source '{row.amount_source}' is non-positive",
                code="amount_non_positive",
            )

        line = JournalLine(
            entry_id=entry.id,
            account_id=account_id,
            debit=amount if row.side == "debit" else Decimal("0"),
            credit=amount if row.side == "credit" else Decimal("0"),
            currency=CURRENCY,
            partner_type=context.get("partner_type"),
            partner_id=context.get("partner_id"),
            description=row.description,
        )
        db.session.add(line)

    # Balance check fires at commit (deferred trigger); we flush now so a
    # map misconfiguration surfaces before we return.
    db.session.flush()
    return PostingResult(entry_id=entry.id, entry_no=entry.entry_no)


def post_manual(
    *,
    entry_date: date,
    description: str,
    lines: list[LineInput],
    posted_by: int,
    reason: str,
    allow_closed_period: bool = False,
) -> PostingResult:
    """Manual journal — high-privilege path.

    Caller is responsible for the permission check; this function
    assumes the ``high.manual_journal`` permission was already verified.
    If `allow_closed_period`, the DB session sets the override variable so
    the period-close trigger lets the insert through.
    """
    min_desc_len = 10
    min_reason_len = 10
    min_lines = 2
    if not description or len(description.strip()) < min_desc_len:
        raise BadRequest(
            "description must be ≥10 chars", code="description_required"
        )
    if not reason or len(reason.strip()) < min_reason_len:
        raise BadRequest("reason must be ≥10 chars", code="reason_required")
    if len(lines) < min_lines:
        raise BadRequest("≥2 lines required", code="too_few_lines")

    total_debit = sum((to_money(li.debit) for li in lines), start=Decimal("0"))
    total_credit = sum((to_money(li.credit) for li in lines), start=Decimal("0"))
    if total_debit != total_credit:
        raise BadRequest(
            f"debit {total_debit} ≠ credit {total_credit}",
            code="unbalanced",
        )

    if allow_closed_period:
        db.session.execute(text("SET LOCAL app.allow_closed_period = 'yes'"))

    entry = _create_entry(
        entry_date=entry_date,
        description=description.strip(),
        source="manual",
        source_event_type=None,
        source_event_id=None,
        posted_by=posted_by,
    )

    for li in lines:
        ensure_egp(CURRENCY)
        account_id = _account_id(li.account_code)
        db.session.add(
            JournalLine(
                entry_id=entry.id,
                account_id=account_id,
                debit=to_money(li.debit),
                credit=to_money(li.credit),
                currency=CURRENCY,
                partner_type=li.partner_type,
                partner_id=li.partner_id,
                description=li.description,
            )
        )

    db.session.flush()
    return PostingResult(entry_id=entry.id, entry_no=entry.entry_no)


# ---------------------------------------------------------------- helpers


def _create_entry(
    *,
    entry_date: date,
    description: str,
    source: str,
    source_event_type: str | None,
    source_event_id: str | None,
    posted_by: int | None,
) -> JournalEntry:
    period = _period_for(entry_date)
    # entry_no = YYYYMM-SEQ, filled after flush with the id
    tmp_no = f"{entry_date.strftime('%Y%m')}-TMP"
    entry = JournalEntry(
        entry_no=tmp_no,
        entry_date=entry_date,
        period_id=period.id if period else None,
        source=source,
        source_event_type=source_event_type,
        source_event_id=source_event_id,
        description=description,
        posted_by=posted_by,
    )
    db.session.add(entry)
    db.session.flush()
    entry.entry_no = f"{entry_date.strftime('%Y%m')}-{entry.id:08d}"
    db.session.flush()
    return entry


def _period_for(d: date) -> Period | None:
    return db.session.execute(
        select(Period).where(Period.starts_on <= d, Period.ends_on >= d)
    ).scalar_one_or_none()


def _account_id(code: str) -> int:
    row = db.session.execute(
        select(Account.id, Account.is_postable).where(Account.code == code)
    ).one_or_none()
    if row is None:
        raise NotFound(f"Unknown account code {code}", code="account_unknown")
    if not row.is_postable:
        raise Forbidden(
            f"Account {code} is not postable", code="account_not_postable"
        )
    return int(row.id)


def _resolve_account_code(row: EventJournalMap, context: Mapping[str, Any]) -> str:
    if row.account_code:
        return row.account_code
    rule = row.rule_json or {}
    if "by_category" in rule:
        mapping: dict[str, str] = rule["by_category"]
        key_cat = str(context.get("category") or "")
        if key_cat not in mapping:
            raise BadRequest(
                f"category '{key_cat}' has no mapping for event",
                code="category_mapping_missing",
            )
        return mapping[key_cat]
    if "by_location" in rule:
        mapping = rule["by_location"]
        key_loc = str(context.get("location_type") or "")
        if key_loc not in mapping:
            raise BadRequest(
                f"location_type '{key_loc}' has no mapping for event",
                code="location_mapping_missing",
            )
        value = mapping[key_loc]
        # "1151_or_1152" means further decide by category.
        if "_or_" in value:
            cat = context.get("category")
            alt = value.split("_or_")
            if cat == "food":
                return alt[0]
            if cat == "clothing":
                return alt[1]
            raise BadRequest(
                f"category '{cat}' needed to pick between {alt}",
                code="category_required_for_location",
            )
        return value
    raise BadRequest(
        f"map row {row.id} has no account_code and no supported rule",
        code="unresolvable_account",
    )


def _resolve_amount(amount_source: str, context: Mapping[str, Any]) -> Decimal:
    if amount_source not in context:
        raise BadRequest(
            f"amount source '{amount_source}' missing from context",
            code="amount_missing",
        )
    return to_money(context[amount_source])
