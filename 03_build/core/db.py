"""
SPEC-008 — Postgres connection plumbing (also fulfils spec-001's deferred
"Postgres init"). A single lazily-opened async psycopg connection pool keyed off
DATABASE_URL (Supabase in Phase 1, ADR-002/ADR-008).

Async-everything per ADR-001: callers `async with (await get_pool()).connection()
as conn`. The pool is opened once on first use and closed at FastAPI shutdown
(api.main lifespan) or via close_pool() in tests.
"""

from __future__ import annotations

import os
from typing import Any

from psycopg_pool import AsyncConnectionPool

from core.llm.config import load_env

_pool: AsyncConnectionPool[Any] | None = None


def database_url() -> str:
    """Return DATABASE_URL from the environment (.env loaded with override=True)."""
    load_env()
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set (see .env / .env.example).")
    return url


async def get_pool() -> AsyncConnectionPool[Any]:
    """Return the process-wide async connection pool, opening it on first use."""
    global _pool
    if _pool is None:
        pool: AsyncConnectionPool[Any] = AsyncConnectionPool(
            conninfo=database_url(), min_size=1, max_size=10, open=False
        )
        await pool.open(wait=True, timeout=10)
        _pool = pool
    return _pool


async def close_pool() -> None:
    """Close the pool (FastAPI shutdown / test teardown). Safe to call when unopened."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
