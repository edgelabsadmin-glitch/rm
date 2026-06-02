"""
SPEC-011 pipeline tests against Postgres.

- Idempotency / event-log behavior needs only Postgres (marker `db`): a fake
  Graphiti is injected so no LLM is required.
- The real end-to-end ingest (marker `integration` + `db`) drives make_graphiti
  with live Anthropic+OpenAI.

All skip cleanly when their dependencies are unavailable (Supabase paused / no
LLM keys).
"""

import importlib.util
from datetime import datetime, timezone
UTC = timezone.utc
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest

from core import db
from core.adapters.episode import Episode
from core.ingest import pipeline


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


class _FakeGraphiti:
    """Stub: records add_episode calls, returns a result with nodes/edges."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def add_episode(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            nodes=[SimpleNamespace(name="Acrisure")],
            edges=[SimpleNamespace(name="placed_at")],
        )


def _episode(dedup_key: str) -> Episode:
    return Episode(
        episode_id=uuid4(),
        dedup_key=dedup_key,
        source="fake",
        source_event_id="evt-1",
        source_url=None,
        source_timestamp=datetime(2026, 5, 5, tzinfo=UTC),
        content_type="text",
        content="Quarterly business review with Acrisure.",
        subject="Acrisure EBR",
        description="QBR",
        candidate_entities=[{"type": "Customer", "sfdc_id": "001ACRISURE"}],
        tags=["ebr"],
        ingested_at=datetime.now(UTC),
        processing_state="normalized",
    )


@pytest.mark.db
async def test_double_ingest_is_idempotent():
    fake = _FakeGraphiti()
    ep = _episode(f"fake:conv:{uuid4().hex}")

    first = await pipeline.run_episode(ep, graphiti=fake)
    second = await pipeline.run_episode(ep, graphiti=fake)

    assert first is True
    assert second is False  # UNIQUE(dedup_key) → no-op
    assert len(fake.calls) == 1  # Graphiti only touched on the first ingest

    pool = await db.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT processing_state FROM pulse.episodes WHERE episode_id = %s;",
                (str(ep["episode_id"]),),
            )
            (state,) = await cur.fetchone()
            assert state == "ingested"

            await cur.execute(
                "SELECT COUNT(*) FROM pulse.events "
                "WHERE event_type = 'episode-deduped' AND payload->>'episode_id' = %s;",
                (str(ep["episode_id"]),),
            )
            (deduped_events,) = await cur.fetchone()
            assert deduped_events == 1


@pytest.mark.db
@pytest.mark.integration
async def test_real_graphiti_end_to_end():
    """Ingest one Episode through the real memory stack; verify state + events."""
    import os

    from core.llm.config import load_env
    from core.memory.graph import make_graphiti

    load_env()
    if not (os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("OPENAI_API_KEY")):
        pytest.skip("needs ANTHROPIC_API_KEY + OPENAI_API_KEY")

    graphiti = make_graphiti(":memory:")
    await graphiti.build_indices_and_constraints()
    try:
        ep = _episode(f"fake:conv:{uuid4().hex}")
        assert await pipeline.run_episode(ep, graphiti=graphiti) is True
    finally:
        await graphiti.close()

    pool = await db.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM pulse.events "
                "WHERE event_type = 'episode-ingested' AND payload->>'episode_id' = %s;",
                (str(ep["episode_id"]),),
            )
            (ingested_events,) = await cur.fetchone()
            assert ingested_events == 1
