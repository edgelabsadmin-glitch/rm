"""
SPEC-032 DB tests — approve → dispatch chain, §6 rule-6 refusal, retry/dead-letter.

Dispatch handlers are injected (fake sf runner / email transport) so no real org
or mailbox is touched. The lifecycle (action-executed / dispatch-failed events +
dead-letter row) is asserted against the real event log.
"""

import importlib.util
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from core import db
from core.actions import service
from core.dispatch.base import DispatchNotAllowed, dispatch_approved_action
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


async def _suggest(action_card: dict, *, urgency="high") -> str:
    aid = str(uuid4())
    await log.emit_action_suggested(
        action_card=action_card,
        why_oneline="because",
        urgency=urgency,
        action_id=aid,
        customer_id=f"001{uuid4().hex[:6]}",
        rm_id=f"rm{uuid4().hex[:5]}",
        skill_id="renewal-watcher",
        tier_class="Enterprise",
    )
    return aid


async def _events_of(aid: str, event_type: str) -> int:
    pool = await db.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM pulse.events WHERE action_id = %s AND event_type = %s;",
                (aid, event_type),
            )
            (n,) = await cur.fetchone()
    return n


async def test_dispatch_refused_for_unapproved_action():
    # A merely-suggested (un-approved) action must not dispatch (§6 rule 6).
    aid = await _suggest({"action_type": "escalation-routed", "subject": "X"})
    with pytest.raises(DispatchNotAllowed):
        await dispatch_approved_action(aid)
    assert await _events_of(aid, "action-executed") == 0


async def test_dispatch_missing_action_refused():
    with pytest.raises(DispatchNotAllowed):
        await dispatch_approved_action(str(uuid4()))


async def test_approve_then_dispatch_sfdc_task():
    aid = await _suggest({"action_type": "escalation-routed", "subject": "Escalate", "body": "now"})
    await service.approve_action(aid, "rmBoss")

    calls = {}

    def fake_sf(values, *, target_org):
        calls["values"] = values
        calls["org"] = target_org
        return "00T000000000001"

    result = await dispatch_approved_action(aid, sf_runner=fake_sf)
    assert result.ok and result.handler == "sfdc_task"
    assert result.external_id == "00T000000000001"
    assert calls["values"]["Subject"] == "Escalate"
    assert await _events_of(aid, "action-executed") == 1


async def test_approve_then_dispatch_email():
    aid = await _suggest({"action_type": "renewal-touch", "to": "cfo@x.com", "subject": "Renew"})
    await service.approve_action(aid, "rmBoss")

    captured = {}

    class FakeTransport:
        async def send(self, msg):
            captured["to"] = msg.to
            return "gmail-abc"

    result = await dispatch_approved_action(aid, email_transport=FakeTransport())
    assert result.ok and result.handler == "email" and result.external_id == "gmail-abc"
    assert captured["to"] == ["cfo@x.com"]


async def test_retry_then_dead_letter():
    aid = await _suggest({"action_type": "escalation-routed", "subject": "Boom"})
    await service.approve_action(aid, "rmBoss")

    attempts = {"n": 0}

    def always_fail(values, *, target_org):
        attempts["n"] += 1
        raise RuntimeError("sf exploded")

    result = await dispatch_approved_action(
        aid, sf_runner=always_fail, max_attempts=3, base_delay=0.0
    )
    assert result.ok is False and result.attempts == 3 and attempts["n"] == 3
    assert await _events_of(aid, "dispatch-failed") == 3
    assert await _events_of(aid, "action-executed") == 0

    pool = await db.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT handler, attempts FROM pulse.dispatch_failed WHERE action_id = %s;", (aid,)
            )
            row = await cur.fetchone()
    assert row == ("sfdc_task", 3)


async def test_trigger_endpoint_403_without_token_and_for_unapproved():
    import os

    os.environ["PULSE_INTERNAL_API_TOKEN"] = "tok-test"
    aid = await _suggest({"action_type": "escalation-routed", "subject": "X"})
    await db.close_pool()

    from api.main import create_app

    with TestClient(create_app()) as client:
        # No token → 403.
        assert client.post(f"/internal/dispatch/{aid}").status_code == 403
        # Valid token but action is un-approved → 403 (§6 rule 6).
        r = client.post(f"/internal/dispatch/{aid}", headers={"X-Internal-Token": "tok-test"})
        assert r.status_code == 403
