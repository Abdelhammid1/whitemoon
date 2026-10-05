"""Export accounting reports to Excel (.xlsx) and PDF (US-3.5).

Each report service returns a shaped dict; `build_doc` normalises any of the
five into a ReportDoc (title + sections of columns/rows), which the Excel
(openpyxl) and PDF (WeasyPrint) renderers consume.

WeasyPrint needs native libs (GTK/Pango/Cairo) present on the Linux server;
it is imported lazily so this module loads everywhere and PDF simply reports
`pdf_engine_unavailable` where the libs are missing (e.g. a Windows dev box).
Arabic PDF rendering relies on an Arabic font being installed on the server
(e.g. Noto Sans Arabic) — see the deploy notes.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

# ---------------------------------------------------------------- normalised doc


@dataclass
class Section:
    columns: list[str]
    rows: list[list[str]]
    heading: str | None = None


@dataclass
class ReportDoc:
    title: str
    subtitle: str
    sections: list[Section]


def _m(s: Any) -> str:
    """Format a money string/number with thousands separators, 2 decimals."""
    try:
        return f"{Decimal(str(s)):,.2f}"
    except Exception:
        return str(s)


def _safe(v: Any) -> str:
    """Neutralise spreadsheet formula injection: a cell whose text begins with
    =,+,-,@ or a control char is interpreted as a formula by Excel. Prefix such
    TEXT with an apostrophe, but let genuine numbers (incl. negatives / grouped)
    through so money columns stay numeric."""
    s = str(v)
    if s[:1] in ("=", "+", "-", "@", "\t", "\r"):
        try:
            float(s.replace(",", ""))
        except ValueError:
            return "'" + s
    return s


def build_doc(report: str, data: dict[str, Any]) -> ReportDoc:
    """Normalise a report dict into a ReportDoc. `report` is the report key."""
    if report == "trial-balance":
        f = data["filter"]
        rows = [
            [r["code"], r["name_ar"], _m(r["debit"]), _m(r["credit"]), _m(r["balance"])]
            for r in data["rows"]
        ]
        t = data["totals"]
        rows.append(["", "الإجمالي", _m(t["debit"]), _m(t["credit"]), "متوازن" if t["balanced"] else "غير متوازن"])
        return ReportDoc(
            title="ميزان المراجعة",
            subtitle=f"من {f['date_from']} إلى {f['date_to']}",
            sections=[Section(["الكود", "الحساب", "مدين", "دائن", "الرصيد"], rows)],
        )

    if report == "income-statement":
        f = data["filter"]
        cols = ["الكود", "الحساب", "المبلغ"]
        rev = [[r["code"], r["name_ar"], _m(r["amount"])] for r in data["revenues"]]
        exp = [[r["code"], r["name_ar"], _m(r["amount"])] for r in data["expenses"]]
        t = data["totals"]
        return ReportDoc(
            title="قائمة الدخل",
            subtitle=f"من {f['date_from']} إلى {f['date_to']}",
            sections=[
                Section(cols, [*rev, ["", "إجمالي الإيرادات", _m(t["revenue"])]], "الإيرادات"),
                Section(cols, [*exp, ["", "إجمالي المصروفات", _m(t["expense"])]], "المصروفات"),
                Section(["", "صافي الدخل"], [["", _m(t["net_income"])]], "النتيجة"),
            ],
        )

    if report == "balance-sheet":
        cols = ["الكود", "الحساب", "المبلغ"]
        t = data["totals"]

        def _rows(items: list[dict[str, Any]], total_label: str, total_val: str) -> list[list[str]]:
            return [[r["code"], r["name_ar"], _m(r["amount"])] for r in items] + [
                ["", total_label, _m(total_val)]
            ]

        return ReportDoc(
            title="المركز المالي",
            subtitle=f"كما في {data['as_of']}",
            sections=[
                Section(cols, _rows(data["assets"], "إجمالي الأصول", t["assets"]), "الأصول"),
                Section(cols, _rows(data["liabilities"], "إجمالي الالتزامات", t["liabilities"]), "الالتزامات"),
                Section(cols, _rows(data["equity"], "إجمالي حقوق الملكية", t["equity"]), "حقوق الملكية"),
            ],
        )

    if report == "cash-flow":
        f = data["filter"]
        cols = ["الكود", "الحساب", "المبلغ"]
        src = [[r["code"], r["name_ar"], _m(r["amount"])] for r in data["sources"]]
        use = [[r["code"], r["name_ar"], _m(r["amount"])] for r in data["uses"]]
        return ReportDoc(
            title="التدفقات النقدية",
            subtitle=f"من {f['date_from']} إلى {f['date_to']}",
            sections=[
                Section(cols, src, "مصادر نقدية (داخل)"),
                Section(cols, use, "استخدامات نقدية (خارج)"),
                Section(["", "صافي التغير النقدي"], [["", _m(data["net_cash_change"])]], "الصافي"),
            ],
        )

    if report == "general-ledger":
        acc = data["account"]
        rows = [
            [
                r["entry_date"], str(r["entry_no"]), r["description"],
                _m(r["debit"]), _m(r["credit"]), _m(r["running_balance"]),
            ]
            for r in data["rows"]
        ]
        return ReportDoc(
            title=f"الأستاذ العام — {acc['code']} {acc['name_ar']}",
            subtitle=f"من {data['date_from']} إلى {data['date_to']}",
            sections=[Section(["التاريخ", "رقم القيد", "البيان", "مدين", "دائن", "الرصيد الجاري"], rows)],
        )

    raise ValueError(f"unknown report: {report}")


# ---------------------------------------------------------------- Excel


def to_xlsx(doc: ReportDoc) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Report"
    ws.sheet_view.rightToLeft = True  # RTL for Arabic

    bold = Font(bold=True)
    head_fill = PatternFill("solid", fgColor="F5F3F3")
    right = Alignment(horizontal="right")

    r = 1
    ws.cell(r, 1, doc.title).font = Font(bold=True, size=14)
    r += 1
    ws.cell(r, 1, doc.subtitle).font = Font(italic=True, color="666666")
    r += 2

    max_cols = 1
    for sec in doc.sections:
        max_cols = max(max_cols, len(sec.columns))
        if sec.heading:
            ws.cell(r, 1, sec.heading).font = Font(bold=True, size=12)
            r += 1
        for ci, col in enumerate(sec.columns, start=1):
            cell = ws.cell(r, ci, col)
            cell.font = bold
            cell.fill = head_fill
            cell.alignment = right
        r += 1
        for row in sec.rows:
            for ci, val in enumerate(row, start=1):
                ws.cell(r, ci, _safe(val)).alignment = right
            r += 1
        r += 1  # blank line between sections

    for ci in range(1, max_cols + 1):
        ws.column_dimensions[get_column_letter(ci)].width = 22

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- PDF


def _render_html(doc: ReportDoc) -> str:
    def esc(s: str) -> str:
        return (
            str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

    parts = [
        "<!doctype html><html dir='rtl' lang='ar'><head><meta charset='utf-8'>",
        "<style>",
        "@page{size:A4;margin:1.5cm}",
        "body{font-family:'Noto Sans Arabic','Amiri','DejaVu Sans',sans-serif;color:#1b1c1c;font-size:12px}",
        "h1{font-size:18px;margin:0 0 2px}.sub{color:#666;margin:0 0 14px;font-size:11px}",
        "h2{font-size:13px;margin:14px 0 4px}",
        "table{width:100%;border-collapse:collapse;margin-bottom:8px}",
        "th,td{border:1px solid #e9e8e7;padding:4px 6px;text-align:right}",
        "th{background:#f5f3f3}",
        "</style></head><body>",
        f"<h1>{esc(doc.title)}</h1><p class='sub'>{esc(doc.subtitle)}</p>",
    ]
    for sec in doc.sections:
        if sec.heading:
            parts.append(f"<h2>{esc(sec.heading)}</h2>")
        parts.append("<table><thead><tr>")
        parts.extend(f"<th>{esc(c)}</th>" for c in sec.columns)
        parts.append("</tr></thead><tbody>")
        for row in sec.rows:
            parts.append("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>")
        parts.append("</tbody></table>")
    parts.append("</body></html>")
    return "".join(parts)


def to_pdf(doc: ReportDoc) -> bytes:
    try:
        from weasyprint import HTML  # type: ignore[reportMissingTypeStubs]
    except Exception as e:  # native libs missing (e.g. Windows dev)
        raise RuntimeError("pdf_engine_unavailable") from e
    pdf = HTML(string=_render_html(doc)).write_pdf()  # type: ignore[reportUnknownMemberType]
    return pdf if pdf is not None else b""
