"""
SPEC-019 integration — Skill 03 renewal-watcher end-to-end (markers integration+db).

Real Sonnet draft + Postgres event/policy. get_customer_context is faked (this
skill is facts-driven; no Graphiti needed), so this isolates the live draft +
action-suggested emission. Gated on LLM keys + a reachable DB.
"""

import importlib.util
import os
from pathlib import Path

import psycopg
import pytest

from core import db
from core.llm.config import load_env

load_env()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.db,
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="needs ANTHROPIC_API_KEY",
    ),
]


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


async def test_skill_03_end_to_end(monkeypatch):
    import skills.skill_03_renewal_watcher as skill
    from core.agent.context import SkillContext

    async def fake_bundle(customer_id, as_of=None, *, graphiti=None):
        return {"entity": {"uuid": "u1", "name": "Acrisure"}, "recent_episodes": []}

    monkeypatch.setattr("core.memory.retrievers.get_customer_context", fake_bundle)

    ctx = SkillContext(
        customer_id="001ACRISURE",
        tier="Mid-Market",
        trigger="scheduled",
        facts={"renewal_days": 45, "churn_signal_count_90d": 3, "open_risk_cases": 1},
    )
    actions = await skill.run(ctx)
    assert len(actions) == 1
    assert actions[0].action_type == "renewal-touch"
    assert "email_draft" in actions[0].body

    pool = await db.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM pulse.events "
                "WHERE event_type = 'action-suggested' AND action_id = %s;",
                (actions[0].action_id,),
            )
            (n,) = await cur.fetchone()
    assert n == 1
