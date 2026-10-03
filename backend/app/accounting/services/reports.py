"""Accounting reports (US-3.5).

v1 returns structured JSON. PDF (WeasyPrint) and Excel (openpyxl)
templates are a Phase 2.5 ops task — the data layer is here and locked.

Reports:
- Trial Balance (TB)
- Income Statement (P&L)
- Balance Sheet (BS)
- Cash Flow (CF) — single-section v1 (operations only; investing/financing
  activities land when 1200 fixed assets have movements)
- General Ledger (GL) — paginated per-account view

All totals are `Decimal`, computed server-side with Postgres SUM to avoid
Python-side rounding on large ledgers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select

from ...common.money import to_money
from ...extensions import db
from ..models import Account, JournalEntry, JournalLine


@dataclass(frozen=True)
class ReportFilter:
    date_from: date
    date_to: date
    account_prefix: str | None = None  # e.g. "11" to limit to current assets
    partner_type: str | None = None
    partner_id: int | None = None


# ---------------------------------------------------------------- helpers


def _apply_filter(stmt: Any, f: ReportFilter) -> Any:
    stmt = stmt.where(
        and_(JournalEntry.entry_date >= f.date_from, JournalEntry.entry_date <= f.date_to)
    )
    if f.account_prefix:
        stmt = stmt.where(Account.code.like(f"{f.account_prefix}%"))
    if f.partner_type:
        stmt = stmt.where(JournalLine.partner_type == f.partner_type)
    if f.partner_id is not None:
        stmt = stmt.where(JournalLine.partner_id == f.partner_id)
    return stmt


# ---------------------------------------------------------------- 1. Trial Balance


def trial_balance(f: ReportFilter) -> dict[str, Any]:
    stmt = (
        select(
            Account.code,
            Account.name_ar,
            Account.name_en,
            Account.type,
            func.coalesce(func.sum(JournalLine.debit), 0).label("total_debit"),
            func.coalesce(func.sum(JournalLine.credit), 0).label("total_credit"),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .group_by(Account.id, Account.code, Account.name_ar, Account.name_en, Account.type)
        .order_by(Account.code)
    )
    stmt = _apply_filter(stmt, f)

    rows: list[dict[str, Any]] = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for row in db.session.execute(stmt):
        d = to_money(row.total_debit)
        c = to_money(row.total_credit)
        total_debit += d
        total_credit += c
        rows.append(
            {
                "code": row.code,
                "name_ar": row.name_ar,
                "name_en": row.name_en,
                "type": row.type,
                "debit": str(d),
                "credit": str(c),
                "balance": str(d - c),
            }
        )
    return {
        "filter": {
            "date_from": f.date_from.isoformat(),
            "date_to": f.date_to.isoformat(),
            "account_prefix": f.account_prefix,
            "partner_type": f.partner_type,
            "partner_id": f.partner_id,
        },
        "rows": rows,
        "totals": {
            "debit": str(total_debit),
            "credit": str(total_credit),
            "balanced": total_debit == total_credit,
        },
    }


# ---------------------------------------------------------------- 2. Income Statement (P&L)


def income_statement(f: ReportFilter) -> dict[str, Any]:
    stmt = (
        select(
            Account.type,
            Account.code,
            Account.name_ar,
            func.coalesce(func.sum(JournalLine.credit) - func.sum(JournalLine.debit), 0).label(
                "net"
            ),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(Account.type.in_(("revenue", "expense", "contra")))
        .group_by(Account.id, Account.type, Account.code, Account.name_ar)
        .order_by(Account.code)
    )
    stmt = _apply_filter(stmt, f)

    revenues: list[dict[str, Any]] = []
    expenses: list[dict[str, Any]] = []
    total_revenue = Decimal("0")
    total_expense = Decimal("0")

    for row in db.session.execute(stmt):
        amount = to_money(row.net)
        item = {"code": row.code, "name_ar": row.name_ar, "amount": str(amount)}
        if row.type == "revenue":
            revenues.append(item)
            total_revenue += amount
        else:  # expense OR contra (contra-revenue nets against revenue)
            # Expense accounts naturally net to debit (we flipped sign above
            # with credit-debit) — invert so expense amounts are positive.
            flipped = -amount
            item["amount"] = str(flipped)
            expenses.append(item)
            total_expense += flipped

    return {
        "filter": {"date_from": f.date_from.isoformat(), "date_to": f.date_to.isoformat()},
        "revenues": revenues,
        "expenses": expenses,
        "totals": {
            "revenue": str(total_revenue),
            "expense": str(total_expense),
            "net_income": str(total_revenue - total_expense),
        },
    }


# ---------------------------------------------------------------- 3. Balance Sheet


def balance_sheet(f: ReportFilter) -> dict[str, Any]:
    """As-of date = `f.date_to`. `date_from` is ignored (cumulative to date)."""

    stmt = (
        select(
            Account.type,
            Account.code,
            Account.name_ar,
            func.coalesce(func.sum(JournalLine.debit) - func.sum(JournalLine.credit), 0).label(
                "balance"
            ),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            Account.type.in_(("asset", "liability", "equity")),
            JournalEntry.entry_date <= f.date_to,
        )
        .group_by(Account.id, Account.type, Account.code, Account.name_ar)
        .order_by(Account.code)
    )

    assets: list[dict[str, Any]] = []
    liabilities: list[dict[str, Any]] = []
    equity: list[dict[str, Any]] = []
    total_assets = Decimal("0")
    total_liabilities = Decimal("0")
    total_equity = Decimal("0")

    for row in db.session.execute(stmt):
        bal = to_money(row.balance)
        if row.type == "asset":
            total_assets += bal
            assets.append({"code": row.code, "name_ar": row.name_ar, "amount": str(bal)})
        elif row.type == "liability":
            amt = -bal  # liability natural balance is credit
            total_liabilities += amt
            liabilities.append({"code": row.code, "name_ar": row.name_ar, "amount": str(amt)})
        else:  # equity
            amt = -bal
            total_equity += amt
            equity.append({"code": row.code, "name_ar": row.name_ar, "amount": str(amt)})

    return {
        "as_of": f.date_to.isoformat(),
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "totals": {
            "assets": str(total_assets),
            "liabilities": str(total_liabilities),
            "equity": str(total_equity),
            "balances": total_assets == (total_liabilities + total_equity),
        },
    }


# ---------------------------------------------------------------- 4. Cash Flow


def cash_flow(f: ReportFilter) -> dict[str, Any]:
    """Cash flow — simplified operations view for v1.

    Takes net movement on all cash/bank accounts (`11xx` with type=asset)
    broken down by the counter-party account type.
    """

    cash_accounts = db.session.execute(
        select(Account).where(Account.code.in_(("1111", "1112")))
    ).scalars().all()
    cash_ids = [a.id for a in cash_accounts]

    stmt = (
        select(
            Account.code,
            Account.name_ar,
            Account.type,
            func.coalesce(func.sum(JournalLine.debit) - func.sum(JournalLine.credit), 0).label(
                "net"
            ),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .join(Account, Account.id == JournalLine.account_id)
        .where(
            JournalEntry.id.in_(
                select(JournalLine.entry_id).where(JournalLine.account_id.in_(cash_ids))
            ),
            ~JournalLine.account_id.in_(cash_ids),
            JournalEntry.entry_date >= f.date_from,
            JournalEntry.entry_date <= f.date_to,
        )
        .group_by(Account.id, Account.code, Account.name_ar, Account.type)
        .order_by(Account.code)
    )

    sources: list[dict[str, Any]] = []
    uses: list[dict[str, Any]] = []
    net_change = Decimal("0")
    for row in db.session.execute(stmt):
        # If the counter leg DEBITED, cash went down. If it CREDITED, cash
        # came in. We stored `debit - credit`; invert sign so "+" is cash in.
        amount = -to_money(row.net)
        net_change += amount
        bucket = sources if amount > 0 else uses
        bucket.append(
            {"code": row.code, "name_ar": row.name_ar, "amount": str(amount)}
        )

    return {
        "filter": {"date_from": f.date_from.isoformat(), "date_to": f.date_to.isoformat()},
        "sources": sources,
        "uses": uses,
        "net_cash_change": str(net_change),
    }


# ---------------------------------------------------------------- 5. General Ledger


def general_ledger(
    *, account_code: str, date_from: date, date_to: date, limit: int = 500
) -> dict[str, Any]:
    account = db.session.execute(
        select(Account).where(Account.code == account_code)
    ).scalar_one_or_none()
    if account is None:
        return {"error": "account_unknown", "account_code": account_code}

    stmt = (
        select(
            JournalEntry.entry_no,
            JournalEntry.entry_date,
            JournalEntry.description,
            JournalLine.debit,
            JournalLine.credit,
            JournalLine.partner_type,
            JournalLine.partner_id,
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalLine.account_id == account.id,
            JournalEntry.entry_date >= date_from,
            JournalEntry.entry_date <= date_to,
        )
        .order_by(JournalEntry.entry_date, JournalEntry.id)
        .limit(limit)
    )

    rows: list[dict[str, Any]] = []
    running = Decimal("0")
    for r in db.session.execute(stmt):
        d = to_money(r.debit)
        c = to_money(r.credit)
        running += d - c
        rows.append(
            {
                "entry_no": r.entry_no,
                "entry_date": r.entry_date.isoformat(),
                "description": r.description,
                "debit": str(d),
                "credit": str(c),
                "running_balance": str(running),
                "partner_type": r.partner_type,
                "partner_id": r.partner_id,
            }
        )

    return {
        "account": {
            "code": account.code,
            "name_ar": account.name_ar,
            "type": account.type,
        },
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "rows": rows,
        "closing_balance": str(running),
    }
