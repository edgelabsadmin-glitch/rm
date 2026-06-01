"""
SPEC-042 Step-6 — executive role on the Action Queue API.

The `executive` role is a valid identity (full org scope via visible_rm_ids → None) but is
BLOCKED from the Action Queue endpoints (spec §3 permission matrix; defense in depth matching
the front-end RoleGuard). These tests don't need Postgres: the 403 fires in the
require_queue_caller dependency BEFORE any DB access, and the unit checks touch only the
Caller model — so no `db` marker (they run in the default `pytest`).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.actions import Caller


def _client() -> TestClient:
    from api.main import create_app

    return TestClient(create_app())


def _hdr(user_id: str, role: str) -> dict[str, str]:
    return {"X-User-Id": user_id, "X-User-Role": role}


# --- Caller model unit checks (no app, no DB) -------------------------------------------


def test_caller_role_accepts_executive() -> None:
    caller = Caller("iffi-wahla", "executive", [])
    assert caller.role == "executive"


def test_visible_rm_ids_executive_returns_none() -> None:
    # Executive = full org scope, same sentinel as admin.
    assert Caller("iffi-wahla", "executive", []).visible_rm_ids() is None
    assert Caller("boss", "admin", []).visible_rm_ids() is None


# --- Endpoint enforcement (403 fires in the dependency, before DB) ----------------------


def test_executive_blocked_from_list_actions() -> None:
    with _client() as client:
        resp = client.get("/actions", headers=_hdr("iffi-wahla", "executive"))
        assert resp.status_code == 403
        body = resp.json()
        assert body["detail"]["error"] == "insufficient_role"
        assert body["detail"]["user_role"] == "executive"


def test_executive_blocked_from_approve() -> None:
    with _client() as client:
        resp = client.post(
            "/actions/any-action-id/approve", headers=_hdr("iffi-wahla", "executive")
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["error"] == "insufficient_role"


def test_executive_blocked_from_reject() -> None:
    with _client() as client:
        resp = client.post(
            "/actions/any-action-id/reject",
            json={"reason_picker": "not-now"},
            headers=_hdr("iffi-wahla", "executive"),
        )
        assert resp.status_code == 403


def test_executive_is_a_valid_identity_not_a_bad_role() -> None:
    # require_caller accepts executive (valid role); the block is the specific queue 403,
    # NOT the generic "valid X-User-Id and X-User-Role required" rejection.
    with _client() as client:
        resp = client.get("/actions", headers=_hdr("iffi-wahla", "executive"))
        assert resp.status_code == 403
        assert isinstance(
            resp.json()["detail"], dict
        )  # structured queue-block, not the string guard

    with _client() as client:
        bogus = client.get("/actions", headers=_hdr("x", "bogus"))
        assert bogus.status_code == 403
        assert isinstance(bogus.json()["detail"], str)  # generic invalid-role guard (string)
