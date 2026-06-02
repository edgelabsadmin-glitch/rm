"""
SPEC-012 DB + live-SFDC tests.

- record_associate_stage idempotency: marker `db` (Postgres only).
- real-org poll: marker `integration`, gated on PULSE_SFDC_LIVE=1 (needs an
  authenticated `sf` CLI; read-only).
"""

import importlib.util
import os
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from core import db
from core.adapters import sfdc


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


@pytest.mark.db
async def test_record_associate_stage_idempotent():
    aid = f"a0{uuid4().hex[:8]}"
    observed = "2026-05-05T10:00:00.000+0000"
    await sfdc.record_associate_stage(aid, "001X", "Replaced", observed)
    await sfdc.record_associate_stage(aid, "001X", "Replaced", observed)  # dupe → no-op

    pool = await db.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM pulse.associate_stage_history WHERE associate_id = %s;",
                (aid,),
            )
            (n,) = await cur.fetchone()
    assert n == 1


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("PULSE_SFDC_LIVE") != "1",
    reason="set PULSE_SFDC_LIVE=1 to run the read-only live SFDC poll",
)
def test_live_account_poll_normalizes():
    a = sfdc.SFDCAdapter()
    records = a._run_soql(a.build_query("Account", datetime.now(UTC) - timedelta(days=365)))
    assert isinstance(records, list)
    if records:
        rec = records[0]
        rec.pop("attributes", None)
        ep = a.normalize(
            {
                "source": "salesforce",
                "source_event_id": rec.get("Id", ""),
                "payload": {"object_type": "Account", "record": rec},
            }
        )
        assert ep["content"]["object_type"] == "Account"
        assert ep["dedup_key"].startswith("sfdc:Account:")
