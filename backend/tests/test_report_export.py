"""Report export to Excel/PDF (US-3.5). The exporter is pure (no DB)."""

from __future__ import annotations

import pytest

from app.accounting.services import report_export as rx


def _weasy_ok() -> bool:
    try:
        import weasyprint  # noqa: F401
        return True
    except Exception:
        return False


_FILTER = {"date_from": "2026-01-01", "date_to": "2026-01-31", "account_prefix": None, "partner_type": None, "partner_id": None}

_DATA = {
    "trial-balance": {
        "filter": _FILTER,
        "rows": [{"code": "1111", "name_ar": "نقدية", "name_en": "Cash", "type": "asset", "debit": "1000.0000", "credit": "0.0000", "balance": "1000.0000"}],
        "totals": {"debit": "1000.0000", "credit": "1000.0000", "balanced": True},
    },
    "income-statement": {
        "filter": {"date_from": "2026-01-01", "date_to": "2026-01-31"},
        "revenues": [{"code": "4100", "name_ar": "مبيعات", "amount": "5000.0000"}],
        "expenses": [{"code": "5100", "name_ar": "مصروفات", "amount": "2000.0000"}],
        "totals": {"revenue": "5000.0000", "expense": "2000.0000", "net_income": "3000.0000"},
    },
    "balance-sheet": {
        "as_of": "2026-01-31",
        "assets": [{"code": "1111", "name_ar": "نقدية", "amount": "1000.0000"}],
        "liabilities": [{"code": "2110", "name_ar": "دائنون", "amount": "400.0000"}],
        "equity": [{"code": "3100", "name_ar": "رأس المال", "amount": "600.0000"}],
        "totals": {"assets": "1000.0000", "liabilities": "400.0000", "equity": "600.0000", "balances": True},
    },
    "cash-flow": {
        "filter": {"date_from": "2026-01-01", "date_to": "2026-01-31"},
        "sources": [{"code": "4100", "name_ar": "تحصيل", "amount": "1500.0000"}],
        "uses": [{"code": "5100", "name_ar": "مدفوعات", "amount": "-500.0000"}],
        "net_cash_change": "1000.0000",
    },
    "general-ledger": {
        "account": {"code": "1111", "name_ar": "نقدية", "type": "asset"},
        "date_from": "2026-01-01",
        "date_to": "2026-01-31",
        "rows": [{"entry_no": 7, "entry_date": "2026-01-10", "description": "تحصيل", "debit": "1000.0000", "credit": "0.0000", "running_balance": "1000.0000", "partner_type": None, "partner_id": None}],
    },
}


@pytest.mark.parametrize("report", list(_DATA))
def test_build_doc_and_xlsx(report: str) -> None:
    doc = rx.build_doc(report, _DATA[report])
    assert doc.title and doc.sections
    assert all(s.columns for s in doc.sections)
    blob = rx.to_xlsx(doc)
    assert blob[:2] == b"PK"  # .xlsx is a zip container
    assert len(blob) > 100


def test_unknown_report_raises() -> None:
    with pytest.raises(ValueError):
        rx.build_doc("nope", {})


def test_xlsx_neutralises_formula_injection() -> None:
    import io

    from openpyxl import load_workbook

    data = {**_DATA["general-ledger"]}
    data["rows"] = [{**data["rows"][0], "description": "=cmd|'/c calc'!A1"}]
    wb = load_workbook(io.BytesIO(rx.to_xlsx(rx.build_doc("general-ledger", data))))
    ws = wb.active
    assert ws is not None
    vals = [c.value for rc in ws.iter_rows() for c in rc if isinstance(c.value, str)]
    # The injected text is present but defused with a leading apostrophe,
    # never as a live formula.
    assert any(v.startswith("'=cmd") for v in vals)
    assert not any(v == "=cmd|'/c calc'!A1" for v in vals)


@pytest.mark.skipif(not _weasy_ok(), reason="WeasyPrint native libs unavailable (e.g. Windows dev)")
def test_to_pdf_when_available() -> None:
    blob = rx.to_pdf(rx.build_doc("trial-balance", _DATA["trial-balance"]))
    assert blob[:4] == b"%PDF"


@pytest.mark.skipif(_weasy_ok(), reason="only asserts the graceful failure path")
def test_to_pdf_unavailable_is_clean() -> None:
    with pytest.raises(RuntimeError, match="pdf_engine_unavailable"):
        rx.to_pdf(rx.build_doc("trial-balance", _DATA["trial-balance"]))
