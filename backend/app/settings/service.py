"""Read/write access to tunable business constants (T-37).

`get_int` / `get_decimal` are called at the point of use (never at import), so
an override takes effect without a restart. `set_value` validates against the
registry, appends a change-log row, and emits an audit event.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select

from ..common.errors import BadRequest, NotFound
from ..extensions import db
from ..identity.services import audit
from .models import SystemSetting, SystemSettingChange
from .registry import BY_KEY, REGISTRY, SettingDef, cast


def _raw(key: str) -> str:
    """Current raw string value: the override if present, else the default."""
    defn = BY_KEY.get(key)
    if defn is None:
        raise NotFound(f"Unknown setting: {key}", code="unknown_setting")
    row = db.session.get(SystemSetting, key)
    return row.value if row is not None else defn.default


def get_int(key: str) -> int:
    return int(_raw(key))


def get_decimal(key: str) -> Decimal:
    return Decimal(_raw(key))


def _validate(defn: SettingDef, raw: str) -> str:
    """Normalise + bounds-check a candidate value, returning the stored form."""
    raw = raw.strip()
    try:
        val = cast(defn, raw)
    except (ValueError, InvalidOperation):
        kind = "عددًا صحيحًا" if defn.value_type == "int" else "رقمًا"
        raise BadRequest(f"القيمة يجب أن تكون {kind}.", code="invalid_value")
    if defn.minimum is not None and val < cast(defn, defn.minimum):
        raise BadRequest(f"القيمة أقل من الحد الأدنى ({defn.minimum}).", code="below_min")
    if defn.maximum is not None and val > cast(defn, defn.maximum):
        raise BadRequest(f"القيمة أكبر من الحد الأقصى ({defn.maximum}).", code="above_max")
    # Canonical string form (e.g. Decimal normalises "0.5" / "0.50" consistently).
    return str(val)


def set_value(*, key: str, raw: str, actor_user_id: int | None) -> dict[str, Any]:
    defn = BY_KEY.get(key)
    if defn is None:
        raise NotFound(f"Unknown setting: {key}", code="unknown_setting")
    new_value = _validate(defn, raw)
    old_value = _raw(key)
    if new_value == old_value:
        return _view(defn)  # no-op, nothing logged

    row = db.session.get(SystemSetting, key)
    if row is None:
        row = SystemSetting(key=key, value=new_value, updated_by_id=actor_user_id)
        db.session.add(row)
    else:
        row.value = new_value
        row.updated_by_id = actor_user_id
    db.session.add(
        SystemSettingChange(
            key=key, old_value=old_value, new_value=new_value, changed_by_id=actor_user_id
        )
    )
    audit.emit(
        "system_setting.update",
        actor_user_id=actor_user_id,
        target_type="system_setting",
        target_id=key,
        before={"value": old_value},
        after={"value": new_value},
    )
    db.session.commit()
    return _view(defn)


def _view(defn: SettingDef) -> dict[str, Any]:
    row = db.session.get(SystemSetting, defn.key)
    return {
        "key": defn.key,
        "group": defn.group,
        "label": defn.label,
        "description": defn.description,
        "example": defn.example,
        "value_type": defn.value_type,
        "unit": defn.unit,
        "minimum": defn.minimum,
        "maximum": defn.maximum,
        "default": defn.default,
        "value": row.value if row is not None else defn.default,
        "overridden": row is not None,
        "source": defn.source,
    }


def list_settings() -> list[dict[str, Any]]:
    """Every registered setting with its current value — doubles as the report
    of «الثوابت التجارية المنقولة» (acceptance: a report listing the constants)."""
    return [_view(d) for d in REGISTRY]


def changes_for(key: str, limit: int = 50) -> list[dict[str, Any]]:
    if key not in BY_KEY:
        raise NotFound(f"Unknown setting: {key}", code="unknown_setting")
    rows = db.session.execute(
        select(SystemSettingChange)
        .where(SystemSettingChange.key == key)
        .order_by(SystemSettingChange.changed_at.desc(), SystemSettingChange.id.desc())
        .limit(limit)
    ).scalars().all()
    return [
        {
            "id": r.id,
            "old_value": r.old_value,
            "new_value": r.new_value,
            "changed_by_id": r.changed_by_id,
            "changed_at": r.changed_at.isoformat() if r.changed_at else None,
        }
        for r in rows
    ]
