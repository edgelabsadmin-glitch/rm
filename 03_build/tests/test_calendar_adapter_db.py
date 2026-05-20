"""
SPEC-014 DB test — attendee email → Account.Id resolution against the
spec-012 Contact episodes in pulse.episodes (marker `db`).
"""

import importlib.util
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg.types.json import Jsonb

from core import db
from core.adapters.calendar import CalendarAdapter

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


async def _seed_contact(email: str, account_id: str) -> None:
    pool = await db.get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO pulse.episodes "
            "(episode_id, dedup_key, source, content_type, content) "
            "VALUES (%s, %s, 'salesforce', 'json', %s) ON CONFLICT (dedup_key) DO NOTHING;",
            (
                str(uuid4()),
                f"sfdc:Contact:{uuid4().hex}",
                Jsonb(
                    {
                        "object_type": "Contact",
                        "record_id": "003X",
                        "fields": {"Email": email, "AccountId": account_id, "Name": "Sarah Chen"},
                    }
                ),
            ),
        )


async def test_resolve_attendees_finds_account():
    email = f"sarah_{uuid4().hex[:8]}@acrisure.test"
    await _seed_contact(email, "001ACRISURE")

    ents = await CalendarAdapter()._resolve_attendees([email, "rm@onedge.co"])
    assert {"type": "Customer", "sfdc_id": "001ACRISURE"} in ents


async def test_resolve_attendees_empty_when_no_match():
    ents = await CalendarAdapter()._resolve_attendees([f"nobody_{uuid4().hex}@nowhere.test"])
    assert ents == []
