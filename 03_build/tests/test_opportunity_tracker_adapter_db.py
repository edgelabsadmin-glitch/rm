"""
SPEC-015 DB tests (marker `db`) — poll, off-scope skip, mark_processed,
idempotency against pulse.expansion_intent_signals.
"""

import importlib.util
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from core import db
from core.adapters.opportunity_tracker import OpportunityTrackerAdapter

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


async def _seed(posting_id: str, tier: str) -> None:
    pool = await db.get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO pulse.expansion_intent_signals "
            "(posting_id, account_id, account_name, title, source, first_seen_date, match_tier) "
            "VALUES (%s, %s, %s, %s, %s, NOW(), %s) ON CONFLICT (posting_id) DO NOTHING;",
            (posting_id, "001ACR", "Acrisure", "Remote Coder", "linkedin", tier),
        )


async def _status(posting_id: str):
    pool = await db.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT processed_at, processed_status FROM pulse.expansion_intent_signals "
                "WHERE posting_id = %s;",
                (posting_id,),
            )
            return await cur.fetchone()


async def test_poll_returns_unprocessed_and_skips_off_scope():
    hot = f"hot_{uuid4().hex[:8]}"
    off = f"off_{uuid4().hex[:8]}"
    await _seed(hot, "hottest")
    await _seed(off, "off-scope")

    events = await OpportunityTrackerAdapter().list_recent_events(
        __import__("datetime").datetime.now()
    )
    ids = {e["source_event_id"] for e in events}
    assert hot in ids
    assert off not in ids  # off-scope skipped

    # off-scope row was marked skipped
    processed_at, status = await _status(off)
    assert processed_at is not None and status == "skipped:off-scope"


async def test_mark_processed_idempotent_processed_at():
    pid = f"p_{uuid4().hex[:8]}"
    await _seed(pid, "hottest")
    a = OpportunityTrackerAdapter()
    eid = uuid4()
    await a.mark_processed(pid, eid, "ingested")
    first_at, status = await _status(pid)
    assert status == "ingested"
    # second mark must not overwrite the original processed_at
    await a.mark_processed(pid, uuid4(), "ingested")
    second_at, _ = await _status(pid)
    assert first_at == second_at
