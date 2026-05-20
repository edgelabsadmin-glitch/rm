"""
SPEC-031 DB tests — suggest → list → approve/modify/reject chain + RBAC scope.

Seeds the queue by emitting action-suggested events directly (the skill path), then
drives the lifecycle through the FastAPI router with TestClient + identity headers.
"""

import importlib.util
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from core import db
from core.events import log

pytestmark = pytest.mark.db


def _load(name: str):
    path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module", autouse=True)
def _require_db():
    try:
        url = db.database_url()
    except RuntimeError as e:
        pytest.skip(str(e))
    try:
        with psycopg.connect(url, connect_timeout=8) as conn:
            conn.execute("SELECT 1;")
    except Exception as e:
        pytest.skip(f"Postgres unreachable: {type(e).__name__}: {str(e)[:120]}")
    _load("db_migrate").migrate()
    yield


@pytest.fixture(autouse=True)
async def _close_pool():
    yield
    await db.close_pool()


async def _suggest(
    *, rm_id: str, customer_id: str, urgency="high", tier="Enterprise", modifiable=None
) -> str:
    action_id = str(uuid4())
    await log.emit_action_suggested(
        action_card={"action_type": "email", "subject": "Hi", "body": "draft"},
        why_oneline="because reasons",
        urgency=urgency,
        modifiable_fields=modifiable or ["subject", "body"],
        action_id=action_id,
        customer_id=customer_id,
        rm_id=rm_id,
        skill_id="renewal-watcher",
        tier_class=tier,
    )
    return action_id


def _client() -> TestClient:
    from api.main import create_app

    return TestClient(create_app())


def _hdr(user_id: str, role: str, reports: str = "") -> dict[str, str]:
    h = {"X-User-Id": user_id, "X-User-Role": role}
    if reports:
        h["X-Report-Ids"] = reports
    return h


async def test_suggest_list_approve_chain():
    rm = f"rm{uuid4().hex[:6]}"
    cust = f"001{uuid4().hex[:6]}"
    aid = await _suggest(rm_id=rm, customer_id=cust)
    await db.close_pool()  # hand the pool to the app lifespan

    with _client() as client:
        listed = client.get("/actions", headers=_hdr(rm, "rm"))
        assert listed.status_code == 200
        ids = [a["action_id"] for a in listed.json()["actions"]]
        assert aid in ids

        approved = client.post(f"/actions/{aid}/approve", headers=_hdr(rm, "rm"))
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"

        # Approved action no longer pending → drops out of the list.
        listed2 = client.get("/actions", headers=_hdr(rm, "rm"))
        assert aid not in [a["action_id"] for a in listed2.json()["actions"]]

        # Second approve is a 409 (already left the queue).
        assert client.post(f"/actions/{aid}/approve", headers=_hdr(rm, "rm")).status_code == 409


async def test_modify_rejects_non_modifiable_field():
    rm = f"rm{uuid4().hex[:6]}"
    aid = await _suggest(rm_id=rm, customer_id=f"001{uuid4().hex[:6]}", modifiable=["subject"])
    await db.close_pool()

    with _client() as client:
        bad = client.post(
            f"/actions/{aid}/modify",
            json={"diff": {"recipient": "x@y.com"}},
            headers=_hdr(rm, "rm"),
        )
        assert bad.status_code == 400

        ok = client.post(
            f"/actions/{aid}/modify", json={"diff": {"subject": "New"}}, headers=_hdr(rm, "rm")
        )
        assert ok.status_code == 200 and ok.json()["status"] == "modified-approved"


async def test_reject_with_reason():
    rm = f"rm{uuid4().hex[:6]}"
    aid = await _suggest(rm_id=rm, customer_id=f"001{uuid4().hex[:6]}")
    await db.close_pool()

    with _client() as client:
        r = client.post(
            f"/actions/{aid}/reject",
            json={"reason_picker": "not-relevant", "free_text": "off base"},
            headers=_hdr(rm, "rm"),
        )
        assert r.status_code == 200 and r.json()["status"] == "rejected"


async def test_rbac_rm_cannot_act_on_another_rms_action():
    owner = f"rm{uuid4().hex[:6]}"
    other = f"rm{uuid4().hex[:6]}"
    aid = await _suggest(rm_id=owner, customer_id=f"001{uuid4().hex[:6]}")
    await db.close_pool()

    with _client() as client:
        # Not visible in the other RM's list…
        listed = client.get("/actions", headers=_hdr(other, "rm"))
        assert aid not in [a["action_id"] for a in listed.json()["actions"]]
        # …and acting on it is 403.
        assert client.post(f"/actions/{aid}/approve", headers=_hdr(other, "rm")).status_code == 403
        # Owner can; admin can.
        assert client.get(f"/actions/{aid}", headers=_hdr(owner, "rm")).status_code == 200
        assert client.get(f"/actions/{aid}", headers=_hdr("boss", "admin")).status_code == 200


async def test_manager_sees_reports_and_skill_hidden_from_non_admin():
    rm = f"rm{uuid4().hex[:6]}"
    mgr = f"mgr{uuid4().hex[:6]}"
    aid = await _suggest(rm_id=rm, customer_id=f"001{uuid4().hex[:6]}")
    await db.close_pool()

    with _client() as client:
        detail = client.get(f"/actions/{aid}", headers=_hdr(mgr, "manager", reports=rm))
        assert detail.status_code == 200
        assert "skill_id" not in detail.json()  # hidden from non-admin

        admin_detail = client.get(f"/actions/{aid}", headers=_hdr("boss", "admin"))
        assert admin_detail.json()["skill_id"] == "renewal-watcher"


async def test_auth_required():
    await db.close_pool()
    with _client() as client:
        assert client.get("/actions").status_code == 403
        assert (
            client.get("/actions", headers={"X-User-Id": "x", "X-User-Role": "bogus"}).status_code
            == 403
        )
