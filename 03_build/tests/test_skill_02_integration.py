"""
SPEC-018 integration — Skill 02 end-to-end (markers `integration` + `db`).

Real Graphiti fixture + real Sonnet brief + Postgres event/policy. Gated on LLM
keys and a reachable DB; skips otherwise.
"""

import importlib.util
import os
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
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
        not os.environ.get("ANTHROPIC_API_KEY") or not os.environ.get("OPENAI_API_KEY"),
        reason="needs ANTHROPIC_API_KEY + OPENAI_API_KEY",
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


async def test_skill_02_end_to_end():
    import skills.skill_02_prepare_customer_meeting_brief as skill
    from core.agent.context import SkillContext
    from core.memory.graph import add_pulse_episode, make_graphiti

    g = make_graphiti(":memory:")
    await g.build_indices_and_constraints()
    try:
        await add_pulse_episode(
            g,
            name="Chorus call Acrisure EBR",
            episode_body=(
                "QBR with Acrisure. Director Sarah Chen praised the medical coders but flagged "
                "CFO vendor-consolidation pressure. Dental ramp is slower."
            ),
            reference_time=datetime.now(UTC) - timedelta(days=5),
        )
        ctx = SkillContext(
            customer_id="Acrisure", tier="Mid-Market", trigger="calendar", graphiti=g
        )
        actions = await skill.run(ctx)
    finally:
        await g.close()

    assert len(actions) == 1
    body = actions[0].body
    assert "headline" in body and "talking_points" in body

    # the action-suggested event was recorded
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
