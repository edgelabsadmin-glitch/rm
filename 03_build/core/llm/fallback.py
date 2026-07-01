"""
Opus-primary → Sonnet-fallback for every LLM call site.

`call_with_fallback(fn)` runs `fn(model_id)` with the primary model (Opus); on any
exception it retries once with the fallback model (Sonnet), re-raising if both fail.
The callable receives the model ID already resolved for the active provider
(direct Anthropic ID or Bedrock inference-profile ID). Async variant included.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from core.llm.config import LLM_FALLBACK, LLM_PRIMARY, resolve_model

log = logging.getLogger(__name__)
T = TypeVar("T")


def call_with_fallback(  # noqa: UP047 — TypeVar (not PEP695) keeps local 3.9 tests runnable
    fn: Callable[[str], T],
    *,
    label: str = "llm",
    primary: str | None = None,
    fallback: str | None = None,
) -> T:
    prim = primary or LLM_PRIMARY
    fb = fallback or LLM_FALLBACK
    try:
        return fn(resolve_model(prim))
    except Exception as exc:  # noqa: BLE001 — any primary failure → try the fallback tier
        log.warning("%s primary (%s) failed: %s — falling back to %s", label, prim, exc, fb)
        return fn(resolve_model(fb))


async def acall_with_fallback(  # noqa: UP047 — TypeVar keeps local 3.9 tests runnable
    fn: Callable[[str], Awaitable[T]],
    *,
    label: str = "llm",
    primary: str | None = None,
    fallback: str | None = None,
) -> T:
    prim = primary or LLM_PRIMARY
    fb = fallback or LLM_FALLBACK
    try:
        return await fn(resolve_model(prim))
    except Exception as exc:  # noqa: BLE001 — any primary failure → try the fallback tier
        log.warning("%s primary (%s) failed: %s — falling back to %s", label, prim, exc, fb)
        return await fn(resolve_model(fb))
