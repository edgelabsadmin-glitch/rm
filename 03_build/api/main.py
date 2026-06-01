"""
SPEC-001 — FastAPI app factory + /health.

ADR-001: async-everything. The 60s request-timeout middleware is mounted here.
Env is loaded with override=True at startup (Q116, via core.llm.config.load_env).
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.middleware.timeout import RequestTimeoutMiddleware
from core.llm.config import load_env

log = logging.getLogger(__name__)

__version__ = "0.1.0"

SYNC_INTERVAL_HOURS = 12


async def _sf_sync_loop() -> None:
    """Run SF→DB account sync at startup then every 12 hours."""
    from core.salesforce.sync import pull_and_upsert
    while True:
        try:
            count = await pull_and_upsert()
            log.info("SF sync done: %d accounts in DB.", count)
        except Exception as exc:
            log.error("SF sync error (will retry in %dh): %s", SYNC_INTERVAL_HOURS, exc)
        await asyncio.sleep(SYNC_INTERVAL_HOURS * 3600)


async def _chorus_sync_loop() -> None:
    """Poll Chorus for completed meetings at startup then every 12 hours.
    Waits 30s after startup so the SF sync can populate the account index first."""
    await asyncio.sleep(30)
    from core.chorus.sync import pull_and_ingest
    while True:
        try:
            result = await pull_and_ingest()
            log.info(
                "Chorus sync done — fetched=%d ingested=%d duplicates=%d errors=%d",
                result["fetched"], result["ingested"], result["duplicates"], result["errors"],
            )
        except Exception as exc:
            log.error("Chorus sync error (will retry in %dh): %s", SYNC_INTERVAL_HOURS, exc)
        await asyncio.sleep(SYNC_INTERVAL_HOURS * 3600)


async def _zoom_sync_loop() -> None:
    """Poll Zoom Reports for past meetings at startup then every 12 hours.
    Waits 60s after startup so SF sync has time to populate the account index."""
    await asyncio.sleep(60)
    from core.zoom.sync import pull_and_ingest as zoom_ingest
    while True:
        try:
            result = await zoom_ingest()
            log.info(
                "Zoom sync done — fetched=%d ingested=%d duplicates=%d errors=%d",
                result["fetched"], result["ingested"], result["duplicates"], result["errors"],
            )
        except Exception as exc:
            log.error("Zoom sync error (will retry in %dh): %s", SYNC_INTERVAL_HOURS, exc)
        await asyncio.sleep(SYNC_INTERVAL_HOURS * 3600)


async def _ensure_schema() -> None:
    """Create tables that may not exist yet (idempotent)."""
    from core.db import get_pool
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.google_sessions (
                user_id              TEXT PRIMARY KEY,
                email                TEXT NOT NULL,
                google_access_token  TEXT,
                google_refresh_token TEXT,
                google_token_expiry  TIMESTAMPTZ,
                google_name          TEXT,
                google_picture       TEXT,
                connected_at         TIMESTAMPTZ DEFAULT NOW(),
                updated_at           TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.episodes (
                episode_id          UUID PRIMARY KEY,
                dedup_key           TEXT        NOT NULL UNIQUE,
                source              TEXT        NOT NULL,
                source_event_id     TEXT,
                source_url          TEXT,
                source_timestamp    TIMESTAMPTZ,
                content_type        TEXT        NOT NULL,
                content             JSONB       NOT NULL,
                subject             TEXT,
                description         TEXT,
                candidate_entities  JSONB       NOT NULL DEFAULT '[]'::jsonb,
                tags                TEXT[]      NOT NULL DEFAULT '{}',
                processing_state    TEXT        NOT NULL DEFAULT 'received',
                ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_episodes_source_time "
            "ON pulse.episodes (source, source_timestamp DESC);"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_episodes_state "
            "ON pulse.episodes (processing_state);"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_env()
    await _ensure_schema()
    # Start background syncs — SF runs immediately; Chorus waits 30s for SF index.
    sf_task = asyncio.create_task(_sf_sync_loop())
    chorus_task = asyncio.create_task(_chorus_sync_loop())
    zoom_task = asyncio.create_task(_zoom_sync_loop())
    yield
    sf_task.cancel()
    chorus_task.cancel()
    zoom_task.cancel()
    for task in (sf_task, chorus_task, zoom_task):
        try:
            await task
        except asyncio.CancelledError:
            pass
    from core.db import close_pool
    await close_pool()


def create_app() -> FastAPI:
    app = FastAPI(title="EDGE Pulse", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestTimeoutMiddleware)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    from api.accounts import router as accounts_router
    from api.submit import router as submit_router
    from api.actions import router as actions_router
    from api.admin.kill_switch import router as kill_switch_router
    from api.dispatch import router as dispatch_router
    from api.profiles import router as profiles_router
    from api.support import router as support_router
    from api.auth_google import router as auth_google_router

    app.include_router(kill_switch_router)
    app.include_router(profiles_router)
    app.include_router(actions_router)
    app.include_router(dispatch_router)
    app.include_router(accounts_router)
    app.include_router(submit_router)
    app.include_router(support_router)
    app.include_router(auth_google_router)

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
