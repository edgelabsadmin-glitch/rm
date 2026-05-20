"""SPEC-030 DB tests — compute() caches + emits health-tier-changed, with debounce."""

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from core import db
from core.health import dual_sided

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


async def _count_tier_changes(account_id: str) -> int:
    pool = await db.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM pulse.events "
                "WHERE event_type = 'health-tier-changed' AND customer_id = %s;",
                (account_id,),
            )
            (n,) = await cur.fetchone()
    return n


async def _backdate_tier_change(account_id: str, hours: int) -> None:
    pool = await db.get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE pulse.account_health SET tier_changed_at = %s WHERE account_id = %s;",
            (datetime.now(UTC) - timedelta(hours=hours), account_id),
        )


async def test_first_compute_caches_and_emits():
    aid = f"001H{uuid4().hex[:8]}"
    h = await dual_sided.compute(aid, tier_class="Mid-Market", facts={"customer_health": "Healthy"})
    assert h.tier in {"Healthy", "Stable"}
    assert await _count_tier_changes(aid) == 1  # None -> tier is a transition


async def test_flip_within_debounce_is_suppressed():
    aid = f"001H{uuid4().hex[:8]}"
    await dual_sided.compute(aid, tier_class="Mid-Market", facts={"customer_health": "Healthy"})
    # immediate flip to a bad state — within 24h → suppressed (tier held, no new event)
    h2 = await dual_sided.compute(
        aid,
        tier_class="Mid-Market",
        facts={"churn_probability": 1.0, "replacement_rate": 1.0, "open_account_risk_cases": 3},
    )
    assert h2.tier in {"Healthy", "Stable"}  # held at the prior healthy tier
    assert await _count_tier_changes(aid) == 1  # no second event


async def test_flip_after_debounce_window_is_accepted():
    aid = f"001H{uuid4().hex[:8]}"
    await dual_sided.compute(aid, tier_class="Mid-Market", facts={"customer_health": "Healthy"})
    await _backdate_tier_change(aid, hours=25)  # last change > 24h ago
    h2 = await dual_sided.compute(
        aid,
        tier_class="Mid-Market",
        facts={"churn_probability": 1.0, "replacement_rate": 1.0, "open_account_risk_cases": 3},
    )
    assert h2.tier in {"At-Risk", "Escalated"}  # flip accepted
    assert await _count_tier_changes(aid) == 2
