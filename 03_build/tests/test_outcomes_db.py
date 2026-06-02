"""
SPEC-033 DB tests — run_outcome_watch emits outcome-recorded / -missing / follow-up.

Seeds executed actions directly (action-suggested + action-executed), backdating
the dispatch time to control the window, then runs the sweep with a fixed `now`
and injected evidence checkers.
"""

import importlib.util
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from core import db
from core.events import log
from core.outcomes.watchers import EvidenceCheckers, run_outcome_watch

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


async def _seed_executed(action_type: str, *, dispatched_at: datetime, external_id="X1") -> str:
    aid = str(uuid4())
    cust = f"001{uuid4().hex[:6]}"
    await log.emit_action_suggested(
        action_card={"action_type": action_type, "subject": "S", "body": "B"},
        why_oneline="why",
        urgency="high",
        action_id=aid,
        customer_id=cust,
        rm_id=f"rm{uuid4().hex[:5]}",
        skill_id="renewal-watcher",
    )
    await log.emit_action_executed(
        action_id=aid,
        handler="email",
        external_id=external_id,
        customer_id=cust,
        occurred_at=dispatched_at,
    )
    return aid


async def _count(aid: str, event_type: str) -> int:
    pool = await db.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM pulse.events WHERE action_id = %s AND event_type = %s;",
                (aid, event_type),
            )
            (n,) = await cur.fetchone()
    return n


async def test_email_reply_evidence_records_outcome():
    now = datetime.now(UTC)
    aid = await _seed_executed("renewal-touch", dispatched_at=now - timedelta(days=2))

    async def found_reply(external_id, customer_id, since):
        return "episode-reply-1"

    tally = await run_outcome_watch(now=now, evidence=EvidenceCheckers(email_reply=found_reply))
    assert tally["recorded"] >= 1
    assert await _count(aid, "outcome-recorded") == 1
    assert await _count(aid, "outcome-missing") == 0


async def test_open_window_stays_pending():
    now = datetime.now(UTC)
    aid = await _seed_executed("renewal-touch", dispatched_at=now - timedelta(days=1))
    # No evidence, window (7d) still open → no outcome event yet.
    await run_outcome_watch(now=now, evidence=EvidenceCheckers())
    assert await _count(aid, "outcome-recorded") == 0
    assert await _count(aid, "outcome-missing") == 0


async def test_closed_window_without_evidence_emits_missing():
    now = datetime.now(UTC)
    aid = await _seed_executed("renewal-touch", dispatched_at=now - timedelta(days=10))
    await run_outcome_watch(now=now, evidence=EvidenceCheckers())  # 7d window closed, no reply
    assert await _count(aid, "outcome-missing") == 1
    assert await _count(aid, "outcome-recorded") == 0


async def test_task_completed_evidence_records_outcome():
    now = datetime.now(UTC)
    aid = await _seed_executed("escalation-routed", dispatched_at=now - timedelta(days=3))

    async def task_done(external_id):
        return True

    await run_outcome_watch(now=now, evidence=EvidenceCheckers(task_completed=task_done))
    assert await _count(aid, "outcome-recorded") == 1


async def test_unwatched_type_emits_single_followup_after_grace():
    now = datetime.now(UTC)
    # Unwatched type, past 14d window + 7d grace.
    aid = await _seed_executed("brand-new-thing", dispatched_at=now - timedelta(days=22))

    async def followups() -> int:
        pool = await db.get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT COUNT(*) FROM pulse.events WHERE event_type = 'action-suggested' "
                    "AND skill_id = 'outcome-watcher' "
                    "AND payload->'action_card'->>'followup_for' = %s;",
                    (aid,),
                )
                (n,) = await cur.fetchone()
        return n

    await run_outcome_watch(now=now, evidence=EvidenceCheckers())
    assert await followups() == 1
    # Idempotent: a second sweep does not double-emit.
    await run_outcome_watch(now=now, evidence=EvidenceCheckers())
    assert await followups() == 1
    assert await _count(aid, "outcome-missing") == 0  # unwatched → no missing event
