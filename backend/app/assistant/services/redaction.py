"""Redaction layer (ticket §8/§10/§15/§28).

Every piece of free text that could carry operational data — an admin's typed
question, text pulled from an uploaded screenshot/PDF, a technical error string —
passes through `redact()` before it is sent to DeepSeek or stored. We mask
emails, phone numbers, money amounts, tax/registration numbers, long digit runs
(IDs/account numbers) and secret-shaped tokens. Only the *kind* and *count* of
what was masked is recorded (never the value), satisfying "log what was redacted
without the value".

This is defence-in-depth: business data is already kept away from the assistant
architecturally (it has no operational-DB access). Redaction guards the one path
data can still arrive on — the admin's own keyboard / screenshots.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ...extensions import db
from ..models import RedactionLog

# order matters: tokens & emails before bare digit runs so we don't shred them
_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("token", re.compile(r"\b(?:sk|pk|rk|ghp|xox[bap]|AKIA|ASIA)[A-Za-z0-9_\-]{12,}\b"), "⟪token⟫"),
    ("token", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"), "⟪jwt⟫"),
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "⟪email⟫"),
    # Egyptian + international phone shapes
    ("phone", re.compile(r"(?<!\d)(?:\+?20|0)1[0-25]\d{8}(?!\d)"), "⟪phone⟫"),
    ("phone", re.compile(r"(?<!\d)\+?\d[\d\s\-]{8,15}\d(?!\d)"), "⟪phone⟫"),
    # money amounts with an EGP marker
    ("amount", re.compile(r"\b\d[\d,]*(?:\.\d+)?\s*(?:ج\.?م|جنيه|EGP|L\.?E)\b", re.IGNORECASE), "⟪amount⟫"),
    # tax card / commercial register (long 9–15 digit official numbers)
    ("tax_id", re.compile(r"(?<!\d)\d{9,15}(?!\d)"), "⟪id⟫"),
    # remaining medium digit runs (account/order numbers the admin might paste)
    ("number", re.compile(r"(?<!\d)\d{5,8}(?!\d)"), "⟪number⟫"),
]


@dataclass
class RedactionResult:
    text: str
    findings: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.findings.values())


def redact(text: str | None) -> RedactionResult:
    """Mask sensitive spans. Pure — no DB writes (use `log_findings` for that)."""
    if not text:
        return RedactionResult(text="")
    findings: dict[str, int] = {}
    out = text
    for kind, pattern, repl in _PATTERNS:
        out, n = pattern.subn(repl, out)
        if n:
            findings[kind] = findings.get(kind, 0) + n
    return RedactionResult(text=out, findings=findings)


def log_findings(scope: str, findings: dict[str, int]) -> None:
    """Record kind+count of what was masked (never the value). Caller commits."""
    for kind, count in findings.items():
        if count:
            db.session.add(RedactionLog(scope=scope, kind=kind, count=count))


def redact_and_log(text: str | None, *, scope: str) -> str:
    r = redact(text)
    if r.findings:
        log_findings(scope, r.findings)
    return r.text
