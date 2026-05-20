"""
SPEC-001 — FastAPI app factory + /health.

ADR-001: async-everything. The 60s request-timeout middleware is mounted here.
Env is loaded with override=True at startup (Q116, via core.llm.config.load_env).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.middleware.timeout import RequestTimeoutMiddleware
from core.llm.config import load_env

__version__ = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load env with override=True (Q116). Later specs add:
    #   - Graphiti × PulseKuzuDriver init (spec 005)
    #   - Langfuse client (ADR-003)
    # The Postgres pool (spec 008) opens lazily on first use; close it here.
    load_env()
    yield
    # Shutdown: close the Postgres pool (spec 008); later specs flush traces.
    from core.db import close_pool

    await close_pool()


def create_app() -> FastAPI:
    app = FastAPI(title="EDGE Pulse", version=__version__, lifespan=lifespan)
    app.add_middleware(RequestTimeoutMiddleware)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    from api.admin.kill_switch import router as kill_switch_router

    app.include_router(kill_switch_router)

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
