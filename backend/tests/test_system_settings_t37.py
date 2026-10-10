"""T-37 — generic system-settings registry: defaults, overrides, change log,
validation, the admin API, and its permission gate."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.common.errors import BadRequest, NotFound
from app.settings import service as settings
from tests.helpers import auth_header, create_user


def test_get_defaults_from_registry(client) -> None:
    # No override yet → the registry default applies.
    assert settings.get_int("credit.payment_reminder_days_before") == 3
    assert settings.get_int("cart.price_lock_minutes") == 60
    assert settings.get_decimal("orders.early_discount_fraction") == Decimal("0.50")


def test_set_value_overrides_and_logs(client) -> None:
    admin = create_user(kind="admin", email="t37a@example.com", roles=("admin.high",))
    view = settings.set_value(
        key="credit.payment_reminder_days_before", raw="5", actor_user_id=admin.id
    )
    assert view["value"] == "5"
    assert view["overridden"] is True
    assert settings.get_int("credit.payment_reminder_days_before") == 5

    changes = settings.changes_for("credit.payment_reminder_days_before")
    assert len(changes) == 1
    assert changes[0]["old_value"] == "3"
    assert changes[0]["new_value"] == "5"
    assert changes[0]["changed_by_id"] == admin.id


def test_no_op_set_is_not_logged(client) -> None:
    settings.set_value(key="cart.price_lock_minutes", raw="60", actor_user_id=None)
    assert settings.changes_for("cart.price_lock_minutes") == []


def test_validation_rejects_out_of_bounds_and_bad_type(client) -> None:
    with pytest.raises(BadRequest):
        settings.set_value(key="cart.price_lock_minutes", raw="0", actor_user_id=None)  # < min 1
    with pytest.raises(BadRequest):
        settings.set_value(key="cart.price_lock_minutes", raw="99999", actor_user_id=None)  # > max
    with pytest.raises(BadRequest):
        settings.set_value(key="cart.price_lock_minutes", raw="abc", actor_user_id=None)  # not int
    with pytest.raises(NotFound):
        settings.set_value(key="does.not.exist", raw="1", actor_user_id=None)


def test_admin_api_list_update_and_changes(client) -> None:
    create_user(kind="admin", email="t37b@example.com", roles=("admin.high",))
    h = auth_header(client, email="t37b@example.com")

    r = client.get("/admin/system-settings", headers=h)
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert any(i["key"] == "credit.rating_window_days" for i in items)
    # Every item carries its metadata for the screen/report.
    sample = next(i for i in items if i["key"] == "credit.rating_window_days")
    assert {"label", "description", "example", "default", "unit", "source"} <= sample.keys()

    r = client.patch(
        "/admin/system-settings/credit.rating_window_days", headers=h, json={"value": "400"}
    )
    assert r.status_code == 200
    assert r.get_json()["value"] == "400"
    assert settings.get_int("credit.rating_window_days") == 400

    r = client.get("/admin/system-settings/credit.rating_window_days/changes", headers=h)
    assert r.status_code == 200
    assert len(r.get_json()["items"]) == 1


def test_api_rejects_out_of_bounds_and_requires_permission(client) -> None:
    create_user(kind="admin", email="t37d@example.com", roles=("admin.high",))
    create_user(kind="customer", email="t37e@example.com", roles=("customer",))
    h = auth_header(client, email="t37d@example.com")

    r = client.patch(
        "/admin/system-settings/credit.green_score", headers=h, json={"value": "101"}
    )
    assert r.status_code == 400  # above max 100

    # A user without system.settings.manage is forbidden.
    hc = auth_header(client, email="t37e@example.com")
    assert client.get("/admin/system-settings", headers=hc).status_code == 403
