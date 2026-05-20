"""
SPEC-020 integration — Skill 01 extractor end-to-end (markers integration+db).

Real Haiku extraction + Postgres reasoning-completed event. Gated on
ANTHROPIC_API_KEY + a reachable DB.
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
    pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="needs ANTHROPIC_API_KEY"),
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


async def test_skill_01_extracts_and_emits():
    import skills.skill_01_detect_talent_signal as skill

    transcript = (
        "QBR with Acrisure. Director Sarah Chen said: 'Honestly, we've started evaluating "
        "Globex for some of this work.' She added the dental coder 'has been overwhelmed and "
        "is burning out.' Overall she said 'your medical team has been great.'"
    )
    result = await skill.run(transcript, subject="Acrisure QBR", customer_id="001ACRTEST")

    assert isinstance(result.client_sentiment, str)
    facts = result.to_signal_facts()
    assert "competitor_mentions" in facts and "burnout" in facts and "sentiment_now" in facts

    pool = await db.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM pulse.events "
                "WHERE event_type = 'reasoning-completed' AND customer_id = '001ACRTEST' "
                "AND skill_id = 'detect-talent-signal';"
            )
            (n,) = await cur.fetchone()
    assert n >= 1
