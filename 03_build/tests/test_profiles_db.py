"""
SPEC-029 DB tests — loader/editor roundtrip + GET/PUT API (marker `db`); plus a
gated Opus regeneration (markers db+integration).
"""

import importlib.util
import os
from datetime import UTC
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient

from core import db
from core.llm.config import load_env
from core.profiles import editor, loader

# Load .env at import so the integration test's skipif sees the LLM keys.
load_env()

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


async def test_upsert_and_get():
    eid = f"001PROF{uuid4().hex[:8]}"
    await loader.upsert_profile("customer", eid, "# Acrisure\n\nProfile body.")
    row = await loader.get_profile("customer", eid)
    assert row["content_md"].startswith("# Acrisure")
    assert row["override_active"] is False


async def test_edit_sets_override_with_baseline():
    eid = f"001PROF{uuid4().hex[:8]}"
    await loader.upsert_profile("customer", eid, "AUTO baseline")
    await editor.edit_profile("customer", eid, "RM edited content", editor_id="user:rm")
    row = await loader.get_profile("customer", eid)
    assert row["override_active"] is True
    assert row["content_md"] == "RM edited content"
    assert row["override_source_md"] == "AUTO baseline"  # baseline preserved


async def test_api_get_and_put():
    from api.main import create_app

    eid = f"001PROF{uuid4().hex[:8]}"
    await loader.upsert_profile("customer", eid, "AUTO content")
    await db.close_pool()  # let the app's lifespan own the pool

    with TestClient(create_app()) as client:
        got = client.get(f"/profiles/customer/{eid}")
        assert got.status_code == 200 and got.json()["content_md"] == "AUTO content"

        put = client.put(
            f"/profiles/customer/{eid}", json={"content_md": "edited via API", "editor_id": "u"}
        )
        assert put.status_code == 200 and put.json()["override_active"] is True

        assert client.get("/profiles/customer/nonexistent").status_code == 404
        assert client.get("/profiles/bogus/x").status_code == 400


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY") or not os.environ.get("OPENAI_API_KEY"),
    reason="needs ANTHROPIC_API_KEY + OPENAI_API_KEY",
)
async def test_regenerate_real_opus():
    from datetime import datetime, timedelta

    from core.memory.graph import add_pulse_episode, make_graphiti
    from core.profiles import regenerator

    g = make_graphiti(":memory:")
    await g.build_indices_and_constraints()
    try:
        await add_pulse_episode(
            g,
            name="Chorus call Acrisure EBR",
            episode_body="QBR with Acrisure. Sarah Chen flagged vendor-consolidation pressure.",
            reference_time=datetime.now(UTC) - timedelta(days=3),
        )
        result = await regenerator.regenerate("customer", "Acrisure", graphiti=g)
    finally:
        await g.close()
    assert result["content_hash"]
    row = await loader.get_profile("customer", "Acrisure")
    assert row is not None and len(row["content_md"]) > 50
