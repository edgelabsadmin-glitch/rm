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


async def _sf_contacts_sync_loop() -> None:
    """Sync SF contacts at startup (after accounts) then every 12 hours.
    Waits 120s so the SF account sync has completed first."""
    await asyncio.sleep(120)
    from core.salesforce.sync import pull_and_upsert_contacts
    while True:
        try:
            count = await pull_and_upsert_contacts()
            log.info("SF contact sync done: %d contacts in DB.", count)
        except Exception as exc:
            log.error("SF contact sync error (will retry in %dh): %s", SYNC_INTERVAL_HOURS, exc)
        await asyncio.sleep(SYNC_INTERVAL_HOURS * 3600)


_GOOGLE_SYNC_INTERVAL_HOURS = 6
_GOOGLE_SYNC_CONCURRENCY = 3  # max users synced in parallel

_EIS_POLL_INTERVAL_SECONDS = 1800  # 30 min — mirrors Activepieces cron cadence


async def _expansion_intent_poll_loop() -> None:
    """Poll pulse.expansion_intent_signals every 30 min for unprocessed rows.

    This runs alongside the Activepieces `expansion_intent_poll` flow (ADR-002).
    When Activepieces is deployed it will drive ingestion via the webhook endpoint;
    this loop acts as a fallback and fills any gaps (e.g. Activepieces downtime,
    rows written before Activepieces was wired up).

    Waits 90s at startup so SF contacts and other adapters are ready first.
    """
    await asyncio.sleep(90)
    from core.adapters.opportunity_tracker import OpportunityTrackerAdapter
    from core.ingest.pipeline import run_episode
    from datetime import datetime, timezone

    adapter = OpportunityTrackerAdapter()
    while True:
        try:
            raws = await adapter.list_recent_events(since=datetime.now(timezone.utc))
            if raws:
                log.info("Expansion intent: processing %d unprocessed EIS rows", len(raws))
            for raw in raws:
                posting_id = str(raw.get("source_event_id", ""))
                episode = adapter.normalize(raw)
                episode_id = episode["episode_id"]
                try:
                    ok = await run_episode(episode)
                    status = "ingested" if ok else "skipped:dup"
                    await adapter.mark_processed(posting_id, episode_id, status)
                except Exception as exc:
                    await adapter.mark_processed(posting_id, episode_id, "ingested")
                    log.error(
                        "EIS Graphiti ingest failed for %s (episode saved): %s",
                        posting_id, exc,
                    )
        except Exception as exc:
            log.error("Expansion intent poll loop error: %s", exc)
        await asyncio.sleep(_EIS_POLL_INTERVAL_SECONDS)


async def _google_sync_loop() -> None:
    """Poll Gmail + Calendar for all connected users every 6 hours.
    Waits 180s for SF contacts to be populated so email matching works."""
    await asyncio.sleep(180)
    from core.google.auth import list_connected_users
    from core.google.account_matcher import build_email_index
    from core.google.gmail_sync import pull_and_ingest as gmail_ingest
    from core.google.calendar_sync import pull_and_ingest as cal_ingest

    sem = asyncio.Semaphore(_GOOGLE_SYNC_CONCURRENCY)

    async def _sync_user(user_id: str) -> None:
        async with sem:
            try:
                # Shared index per sync run — avoids N DB round-trips
                index = await build_email_index()
                g = await gmail_ingest(user_id, index)
                c = await cal_ingest(user_id, index)
                log.info(
                    "Google sync for %s done — gmail ingested=%d, calendar ingested=%d",
                    user_id, g["ingested"], c["ingested"],
                )
            except Exception as exc:
                log.error("Google sync error for %s: %s", user_id, exc)

    while True:
        try:
            users = await list_connected_users()
            if users:
                log.info("Google sync starting for %d users", len(users))
                await asyncio.gather(*[_sync_user(u["user_id"]) for u in users])
                log.info("Google sync round complete")
            else:
                log.debug("Google sync: no connected users yet")
        except Exception as exc:
            log.error("Google sync loop error: %s", exc)
        await asyncio.sleep(_GOOGLE_SYNC_INTERVAL_HOURS * 3600)


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
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.sf_contacts (
                contact_id  TEXT PRIMARY KEY,
                account_id  TEXT NOT NULL,
                name        TEXT,
                email       TEXT,
                phone       TEXT,
                title       TEXT,
                synced_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sf_contacts_email "
            "ON pulse.sf_contacts (LOWER(email)) WHERE email IS NOT NULL;"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sf_contacts_account "
            "ON pulse.sf_contacts (account_id);"
        )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.client_otps (
                id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                email          TEXT        NOT NULL,
                otp_hash       TEXT        NOT NULL,
                expires_at     TIMESTAMPTZ NOT NULL,
                used_at        TIMESTAMPTZ,
                attempt_count  INT         NOT NULL DEFAULT 0,
                created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_client_otps_email "
            "ON pulse.client_otps (email, created_at DESC);"
        )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.client_sessions (
                session_id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                contact_email    TEXT        NOT NULL,
                account_id       TEXT        NOT NULL,
                rm_owner_id      TEXT        NOT NULL,
                rm_name          TEXT        NOT NULL,
                rm_pulse_user_id TEXT,
                client_name      TEXT        NOT NULL,
                created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
                expires_at       TIMESTAMPTZ NOT NULL
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_client_sessions_email "
            "ON pulse.client_sessions (contact_email);"
        )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.rm_style_profiles (
                rm_pulse_user_id  TEXT        PRIMARY KEY,
                style_prompt      TEXT        NOT NULL,
                email_count       INT         NOT NULL DEFAULT 0,
                analyzed_at       TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.client_conversations (
                conversation_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                contact_email   TEXT        NOT NULL,
                account_id      TEXT        NOT NULL,
                title           TEXT        NOT NULL DEFAULT 'New conversation',
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                deleted_at      TIMESTAMPTZ
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_client_conv_email "
            "ON pulse.client_conversations (contact_email, updated_at DESC);"
        )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.client_messages (
                message_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                conversation_id UUID        NOT NULL
                                            REFERENCES pulse.client_conversations (conversation_id)
                                            ON DELETE CASCADE,
                role            TEXT        NOT NULL CHECK (role IN ('user', 'assistant')),
                content         TEXT        NOT NULL,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_client_msg_conv "
            "ON pulse.client_messages (conversation_id, created_at ASC);"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_env()
    await _ensure_schema()
    # SF runs immediately; contacts waits 120s for accounts; Chorus/Zoom/Google stagger after that.
    sf_task = asyncio.create_task(_sf_sync_loop())
    sf_contacts_task = asyncio.create_task(_sf_contacts_sync_loop())
    chorus_task = asyncio.create_task(_chorus_sync_loop())
    zoom_task = asyncio.create_task(_zoom_sync_loop())
    google_task = asyncio.create_task(_google_sync_loop())
    eis_task = asyncio.create_task(_expansion_intent_poll_loop())
    yield
    for task in (sf_task, sf_contacts_task, chorus_task, zoom_task, google_task, eis_task):
        task.cancel()
    for task in (sf_task, sf_contacts_task, chorus_task, zoom_task, google_task, eis_task):
        try:
            await task
        except asyncio.CancelledError:
            pass
    from core.db import close_pool
    await close_pool()


def create_app() -> FastAPI:
    app = FastAPI(title="EDGE Pulse", version=__version__, lifespan=lifespan)
    import os
    _frontend = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000", _frontend],
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
    from api.webhooks import router as webhooks_router
    from api.client_auth import router as client_auth_router
    from api.client_chat import router as client_chat_router

    app.include_router(kill_switch_router)
    app.include_router(profiles_router)
    app.include_router(actions_router)
    app.include_router(dispatch_router)
    app.include_router(accounts_router)
    app.include_router(submit_router)
    app.include_router(support_router)
    app.include_router(auth_google_router)
    app.include_router(webhooks_router)
    app.include_router(client_auth_router)
    app.include_router(client_chat_router)

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
