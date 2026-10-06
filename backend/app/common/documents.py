"""Arabic (RTL) printable documents — invoices and account statements.

Rendering strategy: we build a self-contained RTL HTML document, then convert
it to PDF with WeasyPrint **when it is importable** (the Linux production path,
where its Pango/Cairo system libraries are installed). WeasyPrint shapes Arabic
and lays out RTL correctly, so no manual reshaping is needed.

When WeasyPrint cannot load — notably on a Windows dev box without the GTK
native stack — `pdf_response` degrades to serving the same HTML inline, which
the browser renders perfectly and the user can print to PDF (Ctrl/Cmd-P). The
caller never has to branch on the environment.
"""

from __future__ import annotations

from decimal import Decimal
from html import escape
from typing import Any

from flask import Response

_BASE_CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body {
  font-family: 'IBM Plex Sans Arabic', 'Segoe UI', Tahoma, sans-serif;
  direction: rtl; text-align: right; color: #1b2440; margin: 0;
  font-size: 13px; line-height: 1.6;
}
.doc { max-width: 760px; margin: 0 auto; padding: 8px; }
.head { display: flex; justify-content: space-between; align-items: flex-start;
  border-bottom: 3px solid #A8812B; padding-bottom: 14px; margin-bottom: 18px; }
.brand { font-size: 22px; font-weight: 700; color: #2B3A67; }
.brand small { display: block; font-size: 12px; font-weight: 400; color: #6b7280; }
.meta { text-align: left; font-size: 12px; color: #374151; }
.meta b { color: #2B3A67; }
h1 { font-size: 18px; color: #2B3A67; margin: 0 0 4px; }
table { width: 100%; border-collapse: collapse; margin: 14px 0; }
th, td { padding: 9px 10px; border-bottom: 1px solid #e5e7eb; }
th { background: #f3f4f6; color: #2B3A67; font-weight: 700; text-align: right; }
td.num, th.num { text-align: left; font-variant-numeric: tabular-nums; white-space: nowrap; }
tfoot td { font-weight: 700; border-top: 2px solid #2B3A67; border-bottom: none; }
.totals { margin-top: 10px; width: 320px; margin-left: auto; margin-right: 0; }
.chip { display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 12px; background: #eef2ff; color: #2B3A67; }
.foot { margin-top: 26px; font-size: 11px; color: #9ca3af; text-align: center;
  border-top: 1px solid #e5e7eb; padding-top: 10px; }
@media print { .noprint { display: none; } body { font-size: 12px; } }
"""

_PRINT_HINT = (
    '<div class="noprint" style="background:#fff7ed;border:1px solid #fed7aa;'
    'color:#9a3412;padding:10px 14px;border-radius:10px;margin-bottom:14px;'
    'font-size:13px">للحفظ كملف PDF اضغط Ctrl+P ثم اختر «حفظ بصيغة PDF».</div>'
)


def fmt_money(v: Any) -> str:
    """EGP amount with thousands separators and exactly two decimals."""
    try:
        d = Decimal(str(v))
    except (ArithmeticError, ValueError):
        d = Decimal("0")
    return f"{d:,.2f} ج.م"


def document(title: str, body_html: str) -> str:
    """Wrap a document body in the full RTL HTML skeleton."""
    return (
        "<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'>"
        f"<title>{escape(title)}</title><style>{_BASE_CSS}</style></head>"
        f"<body><div class='doc'>{body_html}"
        "<div class='foot'>White Moon · وايت مون — سوق الجملة الذكي</div>"
        "</div></body></html>"
    )


def to_pdf(html: str) -> bytes | None:
    """Render HTML → PDF bytes, or None when WeasyPrint is unavailable."""
    try:
        from weasyprint import HTML  # type: ignore[import-untyped]
    except Exception:
        return None
    try:
        return HTML(string=html).write_pdf()
    except Exception:
        return None


def pdf_response(html: str, *, filename: str) -> Response:
    """Return the document as a PDF download when possible, else printable HTML.

    `filename` should end in `.pdf`; the HTML fallback is served inline so the
    browser displays it for printing rather than downloading raw markup."""
    pdf = to_pdf(html)
    if pdf is not None:
        return Response(
            pdf,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )
    # Fallback: inject the print hint just after <body>'s container.
    printable = html.replace("<div class='doc'>", "<div class='doc'>" + _PRINT_HINT, 1)
    return Response(printable, mimetype="text/html; charset=utf-8")
