"""Audit log API enrichment: actor/target names, IP, OS (ticket)."""

from __future__ import annotations

from tests.helpers import auth_header, create_user


def test_audit_list_includes_names_ip_and_os(client) -> None:
    create_user(kind="admin", email="auditor@wm.eg", roles=("admin.high",))
    # Logging in emits a `user.login` audit event (actor + target = this user),
    # captured with the request IP / User-Agent.
    h = auth_header(client, email="auditor@wm.eg")

    data = client.get("/admin/audit", headers=h).get_json()
    assert data["items"], "expected at least the login event"
    sample = data["items"][0]
    # New fields are present on every row.
    assert {"actor_name", "target_name", "ip", "user_agent", "os"} <= set(sample)

    login = next((e for e in data["items"] if e["action"] == "user.login"), None)
    assert login is not None
    # Actor + target resolve to the admin's email (no profile → email fallback).
    assert login["actor_name"] == "auditor@wm.eg"
    assert login["target_name"] == "auditor@wm.eg"
    # IP captured from the (test) request.
    assert login["ip"]


def test_audit_requires_admin_high(client) -> None:
    create_user(kind="staff", email="plainstaff@wm.eg", roles=("staff",))
    h = auth_header(client, email="plainstaff@wm.eg")
    assert client.get("/admin/audit", headers=h).status_code == 403
