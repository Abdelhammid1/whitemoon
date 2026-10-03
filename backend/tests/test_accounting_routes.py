"""End-to-end routes — permissions and the happy-path."""

from __future__ import annotations

from flask.testing import FlaskClient

from tests.helpers import auth_header, create_user


def test_customer_cannot_close_period(client: FlaskClient) -> None:
    create_user(kind="customer", phone="+201000000100", roles=("customer",))
    headers = auth_header(client, phone="+201000000100")
    r = client.post(
        "/accounting/periods/close", headers=headers, json={"year": 2026, "month": 10}
    )
    assert r.status_code == 403


def test_admin_high_closes_period_and_posts_manual_entry(client: FlaskClient) -> None:
    create_user(kind="admin", email="fin@example.com", roles=("admin.high",))
    headers = auth_header(client, email="fin@example.com")

    # ensure
    r = client.post(
        "/accounting/periods/ensure",
        headers=headers,
        json={"year": 2026, "month": 10},
    )
    assert r.status_code == 200

    # post a manual entry
    r = client.post(
        "/accounting/journal/manual",
        headers=headers,
        json={
            "entry_date": "2026-10-10",
            "description": "manual correction for test",
            "reason": "test reason exceeding ten chars",
            "lines": [
                {"account_code": "1111", "debit": "25"},
                {"account_code": "4400", "credit": "25"},
            ],
        },
    )
    assert r.status_code == 201, r.get_json()

    # close
    r = client.post(
        "/accounting/periods/close",
        headers=headers,
        json={"year": 2026, "month": 10},
    )
    assert r.status_code == 200
    assert r.get_json()["is_closed"] is True


def test_trial_balance_endpoint_returns_balanced(client: FlaskClient) -> None:
    create_user(kind="admin", email="rep@example.com", roles=("admin.high",))
    headers = auth_header(client, email="rep@example.com")
    client.post(
        "/accounting/periods/ensure",
        headers=headers,
        json={"year": 2026, "month": 10},
    )
    client.post(
        "/accounting/journal/manual",
        headers=headers,
        json={
            "entry_date": "2026-10-05",
            "description": "seed for TB test",
            "reason": "seed-for-tb-test",
            "lines": [
                {"account_code": "1111", "debit": "40"},
                {"account_code": "4400", "credit": "40"},
            ],
        },
    )
    r = client.post(
        "/accounting/reports/trial-balance",
        headers=headers,
        json={"date_from": "2026-10-01", "date_to": "2026-10-31"},
    )
    assert r.status_code == 200
    assert r.get_json()["totals"]["balanced"] is True
