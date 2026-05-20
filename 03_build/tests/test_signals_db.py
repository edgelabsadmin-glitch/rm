"""
SPEC-017 DB test — runtime.evaluate emits a signal-evaluated event (marker `db`).
"""

import importlib.util
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from core import db
from core.signals import runtime
from core.signals.base import EvaluationContext

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


async def test_evaluate_emits_signal_evaluated_event():
    customer = f"001SIG{uuid4().hex[:8]}"
    result = await runtime.evaluate(
        "churn_signal_contact_disengagement_v1",
        EvaluationContext(
            customer_id=customer,
            tier="Mid-Market",
            facts={
                "days_since_last_reply": 21,
                "chorus_call_count_21d": 0,
                "chorus_call_count_prior_21d": 1,
            },
        ),
    )
    assert result is not None and result.fired

    pool = await db.get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM pulse.events "
                "WHERE event_type = 'signal-evaluated' AND customer_id = %s "
                "AND payload->>'signal_id' = 'churn_signal_contact_disengagement_v1';",
                (customer,),
            )
            (n,) = await cur.fetchone()
    assert n == 1
