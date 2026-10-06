"""Onboarding checklist (T-18)."""

from __future__ import annotations

from tests.helpers import auth_header, create_user


def test_checklist_is_role_based_and_data_driven(client) -> None:
    create_user(kind="admin", email="onbadmin@example.com", roles=("admin",))
    h = auth_header(client, email="onbadmin@example.com")
    r = client.get("/onboarding/checklist", headers=h)
    assert r.status_code == 200
    data = r.get_json()
    assert data["role"] == "admin"
    assert data["total"] == len(data["tasks"]) > 0
    keys = {t["key"] for t in data["tasks"]}
    assert {"secure", "categories", "suppliers", "slots"} <= keys
    # 2FA not enrolled yet → the secure task is not done.
    secure = next(t for t in data["tasks"] if t["key"] == "secure")
    assert secure["done"] is False
    assert all("to" in t and "done" in t and "kind" in t for t in data["tasks"])


def test_checklist_customer_role(client) -> None:
    create_user(kind="customer", email="onbcust@example.com", roles=("customer",))
    h = auth_header(client, email="onbcust@example.com")
    data = client.get("/onboarding/checklist", headers=h).get_json()
    assert data["role"] == "customer"
    assert {"phone", "browse", "slot"} <= {t["key"] for t in data["tasks"]}
