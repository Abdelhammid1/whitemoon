"""Read endpoints that connect the frontend accounting/admin/inventory screens."""

from __future__ import annotations

from tests.helpers import auth_header, create_user


def _admin(client):
    # admin.high holds '*' — the accounting reads are gated like the existing
    # reports (period.close), which only admin.high has; this matches the
    # bootstrap/finance admin the UI logs in as.
    create_user(kind="admin", email="reader@example.com", roles=("admin.high",))
    return auth_header(client, email="reader@example.com")


def test_chart_of_accounts_list(client) -> None:
    h = _admin(client)
    r = client.get("/accounting/accounts", headers=h)
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert len(items) > 0
    codes = {a["code"] for a in items}
    assert "1111" in codes  # seeded cash account
    sample = next(a for a in items if a["code"] == "1111")
    assert {"code", "name_ar", "type", "is_postable", "parent_code"} <= sample.keys()


def test_periods_list(client) -> None:
    h = _admin(client)
    client.post("/accounting/periods/ensure", json={"year": 2026, "month": 3}, headers=h)
    r = client.get("/accounting/periods", headers=h)
    assert r.status_code == 200
    items = r.get_json()["items"]
    assert any(p["year"] == 2026 and p["month"] == 3 for p in items)


def test_receipts_and_deferred_lists(client) -> None:
    h = _admin(client)
    assert client.get("/accounting/receipts", headers=h).status_code == 200
    assert client.get("/accounting/deferred-terms", headers=h).status_code == 200


def test_audit_list_and_user_detail(client) -> None:
    h = _admin(client)
    # recompute something audited? just assert the endpoints shape.
    r = client.get("/admin/audit", headers=h)
    assert r.status_code == 200
    assert "items" in r.get_json()

    me = create_user(kind="customer", email="detail@example.com", roles=("customer",))
    r2 = client.get(f"/admin/users/{me.id}", headers=h)
    assert r2.status_code == 200
    body = r2.get_json()
    assert body["id"] == me.id
    assert body["roles"] == ["customer"]

    assert client.get("/admin/users/99999", headers=h).status_code == 404


def test_transfers_list(client) -> None:
    h = _admin(client)
    r = client.get("/inventory/transfers", headers=h)
    assert r.status_code == 200
    assert "items" in r.get_json()
