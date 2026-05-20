"""
SPEC-001 / ADR-001 — top-level request-timeout middleware.

ADR-001 Implementation Contract item 2: every FastAPI handler is async; the
top-level request timeout is 60 seconds. On timeout, return HTTP 504 with a
structured error payload and (once the event log exists, spec 008) emit an
`action-timeout` event. No silent failure (§6 rule 14).
"""

from __future__ import annotations

import asyncio

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_TIMEOUT_SECONDS = 60


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """Bound every request to REQUEST_TIMEOUT_SECONDS; 504 on overrun."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT_SECONDS)
        except TimeoutError:
            # TODO(spec-008): emit `action-timeout` event to the event log.
            return JSONResponse(
                status_code=504,
                content={
                    "error": "request_timeout",
                    "detail": f"Request exceeded {REQUEST_TIMEOUT_SECONDS}s budget.",
                    "path": request.url.path,
                },
            )
