"""
Inbound webhook receivers — called by the Activepieces flow engine (ADR-002).

POST /webhooks/expansion-intent
    Receives a single row POSTed by the `expansion_intent_poll` Activepieces
    flow (30-min cron over pulse.expansion_intent_signals). Normalizes the row
    into an Episode, runs it through the ingest pipeline, and stamps the EIS
    row's processed_at / pulse_episode_id / processed_status.

    Idempotent: if the same posting_id is delivered twice, run_episode returns
    False (ON CONFLICT DO NOTHING) and the row is marked skipped:dup.

    Guarded by PULSE_INTERNAL_API_TOKEN (same header as dispatch.py). The
    Activepieces flow must inject this token via x-internal-token.

    Graphiti failures: run_episode writes the Episode to pulse.episodes before
    calling the memory layer. If Graphiti raises, the Episode is already in the
    DB with processing_state='normalized' for the retry cron — the EIS row is
    still marked processed (ingested) so Activepieces doesn't re-deliver it.
"""

from __future__ import annotations

import logging
import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from core.adapters.opportunity_tracker import OpportunityTrackerAdapter

log = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _require_internal_token(
    x_internal_token: str = Header(default=None),
) -> str:
    expected = os.environ.get("PULSE_INTERNAL_API_TOKEN")
    if not expected or x_internal_token != expected:
        raise HTTPException(status_code=403, detail="internal token required")
    return "internal"


@router.post("/expansion-intent")
async def expansion_intent_webhook(
    request: Request,
    _: Annotated[str, Depends(_require_internal_token)],
) -> dict[str, Any]:
    """Receive one EIS row from Activepieces, ingest it as an Episode."""
    from core.ingest.pipeline import run_episode

    payload = await request.json()
    adapter = OpportunityTrackerAdapter()

    try:
        raws = await adapter.receive_webhook(payload, dict(request.headers))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not raws:
        # off-scope row — receive_webhook already stamped it skipped:off-scope
        return {"ok": True, "ingested": 0, "skipped": 1}

    ingested = 0
    for raw in raws:
        posting_id = str(raw.get("source_event_id", ""))
        episode = adapter.normalize(raw)
        episode_id = episode["episode_id"]
        try:
            ok = await run_episode(episode)
            status = "ingested" if ok else "skipped:dup"
            await adapter.mark_processed(posting_id, episode_id, status)
            if ok:
                ingested += 1
        except Exception as exc:
            # Graphiti failure: Episode is already in pulse.episodes
            # (processing_state='normalized'); mark EIS processed so the
            # flow doesn't re-deliver the row. The retry cron handles
            # Graphiti re-ingestion via pulse.episodes.
            await adapter.mark_processed(posting_id, episode_id, "ingested")
            log.error(
                "Graphiti ingest failed for posting %s (episode saved, retry cron will pick it up): %s",
                posting_id,
                exc,
            )

    return {"ok": True, "ingested": ingested}
