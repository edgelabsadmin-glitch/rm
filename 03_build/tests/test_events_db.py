"""
SPEC-008 DB-backed tests (marker `db`, excluded by default).

Gated on a reachable Postgres: if DATABASE_URL is unset or the host doesn't
resolve/connect, the whole module skips cleanly (Supabase free-tier pauses when
idle). Run with a live DB via:  pytest -m db

Each test isolates itself with a unique correlation_id so concurrent runs and a
shared Supabase instance don't interfere; no global truncation.
"""

import importlib.util
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from core import db
from core.events import log, queries

pytestmark = pytest.mark.db


def _load_db_migrate():
    path = Path(__file__).resolve().parents[1] / "scripts" / "db_migrate.py"
    spec = importlib.util.spec_from_file_location("db_migrate", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module", autouse=True)
def _require_db():
    """Skip the module unless the migration can be applied against a live DB."""
    try:
        url = db.database_url()
    except RuntimeError as e:
        pytest.skip(str(e))
    try:
        with psycopg.connect(url, connect_timeout=8) as conn:
            conn.execute("SELECT 1;")
    except Exception as e:  # unreachable / paused / auth
        pytest.skip(f"Postgres unreachable: {type(e).__name__}: {str(e)[:120]}")
    # Apply migrations once for the module.
    _load_db_migrate().migrate()
    yield


@pytest.fixture(autouse=True)
async def _close_pool():
    yield
    await db.close_pool()


async def test_emit_and_roundtrip():
    corr = uuid4()
    action_id = uuid4()
    await log.emit_action_suggested(
        action_card={"kind": "email", "to": "sarah@acrisure.test"},
        why_oneline="EBR in 3 days; risk signals fresh",
        urgency="medium-high",
        action_id=str(action_id),
        customer_id="001ACRISURE",
        skill_id="renewal-watcher",
        correlation_id=corr,
    )
    await log.emit_action_approved(
        action_id=str(action_id), approver_id="user:jordan", rm_id="005JORDAN", correlation_id=corr
    )
    hist = await queries.action_history(action_id)
    types_in_order = [r["event_type"] for r in hist]
    assert types_in_order == ["action-suggested", "action-approved"]


async def test_emit_event_rejects_unknown_type_before_insert():
    with pytest.raises(ValueError, match="unknown event_type"):
        await log.emit_event("nope", {})


async def test_named_queries_against_seeded_data():
    corr = uuid4()
    action_id = uuid4()
    cust = f"001CUST{corr.hex[:6]}"
    rm = f"005RM{corr.hex[:6]}"
    skill = f"renewal-watcher-{corr.hex[:6]}"
    since = datetime.now(UTC) - timedelta(minutes=5)

    await log.emit_action_suggested(
        action_card={},
        why_oneline="x",
        urgency="low",
        action_id=str(action_id),
        customer_id=cust,
        rm_id=rm,
        skill_id=skill,
        correlation_id=corr,
    )
    await log.emit_action_approved(
        action_id=str(action_id),
        approver_id="user:x",
        customer_id=cust,
        rm_id=rm,
        skill_id=skill,
        correlation_id=corr,
    )
    await log.emit_action_executed(
        action_id=str(action_id),
        handler="gmail",
        customer_id=cust,
        rm_id=rm,
        skill_id=skill,
        correlation_id=corr,
    )
    await log.emit_outcome_recorded(
        action_id=str(action_id),
        outcome_type="email-replied",
        customer_id=cust,
        rm_id=rm,
        skill_id=skill,
        correlation_id=corr,
    )

    funnel = await queries.skill_funnel(skill, since)
    assert funnel == {"suggested": 1, "approved": 1, "executed": 1, "outcome_recorded": 1}

    assert await queries.rm_throughput(rm, since) == 1

    recent = await queries.customer_recent_actions(cust, since)
    assert len(recent) == 4  # all four are action-* / outcome handled separately
    # newest-first ordering
    occurred = [r["occurred_at"] for r in recent]
    assert occurred == sorted(occurred, reverse=True)

    outcomes = await queries.recent_outcomes(since)
    assert any(str(o["action_id"]) == str(action_id) for o in outcomes)


async def test_burst_1000_events_under_2s():
    corr = uuid4()
    rm = f"005BURST{corr.hex[:6]}"
    rows = [
        {
            "event_type": "skill-fired",
            "payload": {"skill_id": "renewal-watcher"},
            "skill_id": "renewal-watcher",
            "rm_id": rm,
            "correlation_id": corr,
        }
        for _ in range(1000)
    ]
    t0 = time.perf_counter()
    ids = await log.emit_events_bulk(rows)
    elapsed = time.perf_counter() - t0
    assert len(ids) == 1000
    # Design 04 perf target: 1000 events < 2s (assumes a co-located Postgres).
    assert elapsed < 2.0, f"burst took {elapsed:.2f}s (>2s)"
