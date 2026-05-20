"""
SPEC-009/010 DB-backed tests (marker `db`).

End-to-end against Postgres: policy_decide emits a policy-decision event; the
kill switch blocks and emits kill-switch-flipped; the admin endpoint round-trips.
Skips cleanly when the DB is unreachable. The global kill switch is reset in
finally so the shared singleton row isn't left flipped.
"""

import importlib.util
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from core import db
from core.policy import kill_switch
from core.policy.decide import policy_decide
from core.policy.types import ActionSuggested

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


async def _count_events(event_type: str, action_id: str) -> int:
    pool = await db.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM pulse.events WHERE event_type = %s AND action_id = %s;",
                (event_type, action_id),
            )
            (n,) = await cur.fetchone()
    return n


async def test_policy_decide_emits_event():
    aid = str(uuid4())
    decision = await policy_decide(
        ActionSuggested(
            skill_id="renewal-watcher", urgency="high", tier_class="Enterprise", action_id=aid
        )
    )
    assert decision.decision == "require-human"
    assert await _count_events("policy-decision", aid) == 1


async def test_kill_switch_blocks_and_emits():
    try:
        state = await kill_switch.set_kill_switch("global", True, "user:tester")
        assert state["global"] is True

        aid = str(uuid4())
        decision = await policy_decide(
            ActionSuggested(skill_id="recognition", urgency="low", tier_class="SMB", action_id=aid)
        )
        assert decision.decision == "block"
        assert await _count_events("policy-decision", aid) == 1

        # the toggle emitted a kill-switch-flipped event
        pool = await db.get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COUNT(*) FROM pulse.events "
                    "WHERE event_type = 'kill-switch-flipped' "
                    "AND payload->>'scope' = 'global' AND actor = 'user:user:tester';"
                )
                (n,) = await cur.fetchone()
                assert n >= 1
    finally:
        await kill_switch.set_kill_switch("global", False, "user:tester")


async def test_admin_endpoint_round_trip(monkeypatch):
    monkeypatch.setenv("PULSE_INTERNAL_API_TOKEN", "test-admin-token")
    from api.main import create_app

    try:
        with TestClient(create_app()) as client:
            headers = {"X-Admin-Token": "test-admin-token"}
            resp = client.post(
                "/admin/kill-switch",
                json={"scope": "skill:renewal-watcher", "on": True, "user_id": "admin"},
                headers=headers,
            )
            assert resp.status_code == 200
            assert resp.json()["kill_switch"]["by_skill"]["renewal-watcher"] is True

            get = client.get("/admin/kill-switch", headers=headers)
            assert get.status_code == 200
            assert get.json()["kill_switch"]["by_skill"]["renewal-watcher"] is True
    finally:
        await kill_switch.set_kill_switch("skill:renewal-watcher", False, "admin")
