"""Decimal money helpers + EGP currency guard.

Non-negotiable (per docs/00-stack-and-architecture.md §5):
- `float` is forbidden in any monetary code path.
- Every monetary amount is stored as NUMERIC(18,4) and manipulated as
  `decimal.Decimal` with the quantization defined here.
- Every monetary row carries `currency = 'EGP'`. Non-EGP values are
  rejected at the DB level AND here, both at the row level.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, getcontext
from typing import Final

# Four fractional digits — matches NUMERIC(18,4).
MONEY_SCALE: Final = Decimal("0.0001")
ZERO_MONEY: Final = Decimal("0")
CURRENCY: Final = "EGP"

# Prevent silent precision loss in intermediate ops.
getcontext().prec = 28


def to_money(value: Decimal | int | str) -> Decimal:
    """Quantize to the money scale with half-up rounding.

    Accepts int, str, or Decimal. Floats are rejected — passing a float
    anywhere near money is a bug.
    """
    if isinstance(value, float):
        raise TypeError(
            "float is forbidden for money; use Decimal or a numeric string"
        )
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    return d.quantize(MONEY_SCALE, rounding=ROUND_HALF_UP)


def ensure_egp(currency: str) -> None:
    if currency != CURRENCY:
        raise ValueError(
            f"Only {CURRENCY} is supported; got {currency!r} (US-11.2)"
        )
