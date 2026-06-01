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


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_env()
    # Start background SF sync — runs immediately then every 12 hours.
    sync_task = asyncio.create_task(_sf_sync_loop())
    yield
    sync_task.cancel()
    try:
        await sync_task
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

    app.include_router(kill_switch_router)
    app.include_router(profiles_router)
    app.include_router(actions_router)
    app.include_router(dispatch_router)
    app.include_router(accounts_router)
    app.include_router(submit_router)
    app.include_router(support_router)

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
