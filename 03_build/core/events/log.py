"""
SPEC-008 — Event Log emitter (Design 04).

`emit_event(...)` is the single write path into the append-only `pulse.events`
table. Every skill, retriever, adapter, and dispatch handler calls it (directly
or via the per-type helpers below) to record a significant moment. The payload
is validated against the per-type Pydantic model (core/events/types.py) BEFORE
the insert, so a malformed payload raises at emit time — never a silent write
of garbage (§6 rule 14).

`trace_id` cross-links the event to its Langfuse trace tree (ADR-003): when the
caller is inside an `@observe()`-decorated function and does not pass trace_id
explicitly, the emitter resolves it best-effort from the active Langfuse context.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from core.db import get_pool
from core.events.types import PAYLOAD_MODELS

_INSERT = """
INSERT INTO pulse.events (
    event_id, event_type, event_version, occurred_at,
    customer_id, talent_id, rm_id, case_id, action_id, episode_id, skill_id,
    payload, tier_class, urgency, correlation_id, actor,
    reasoning_text, reasoning_tags, trace_id
) VALUES (
    %(event_id)s, %(event_type)s, %(event_version)s, %(occurred_at)s,
    %(customer_id)s, %(talent_id)s, %(rm_id)s, %(case_id)s,
    %(action_id)s, %(episode_id)s, %(skill_id)s,
    %(payload)s, %(tier_class)s, %(urgency)s, %(correlation_id)s, %(actor)s,
    %(reasoning_text)s, %(reasoning_tags)s, %(trace_id)s
);
"""


def _current_trace_id() -> str | None:
    """Best-effort Langfuse trace id; None when not inside an @observe() context."""
    try:  # langfuse 3.x
        from langfuse import get_client

        return get_client().get_current_trace_id()
    except Exception:
        pass
    try:  # langfuse 2.x
        from langfuse.decorators import langfuse_context  # type: ignore[import-not-found]

        return langfuse_context.get_current_trace_id()
    except Exception:
        return None


def validate_payload(event_type: str, payload: dict) -> dict:
    """Validate `payload` against the model for `event_type`; return the clean dict.

    Raises ValueError on an unknown event_type and pydantic.ValidationError on a
    payload that does not match the schema.
    """
    model = PAYLOAD_MODELS.get(event_type)
    if model is None:
        raise ValueError(
            f"unknown event_type {event_type!r}; must be one of {sorted(PAYLOAD_MODELS)}"
        )
    return model.model_validate(payload).model_dump()


async def emit_event(
    event_type: str,
    payload: dict,
    *,
    occurred_at: datetime | None = None,
    event_version: int = 1,
    customer_id: str | None = None,
    talent_id: str | None = None,
    rm_id: str | None = None,
    case_id: str | None = None,
    action_id: str | UUID | None = None,
    episode_id: str | UUID | None = None,
    skill_id: str | None = None,
    tier_class: str | None = None,
    urgency: str | None = None,
    correlation_id: str | UUID | None = None,
    actor: str = "system",
    reasoning_text: str | None = None,
    reasoning_tags: list[str] | None = None,
    trace_id: str | UUID | None = None,
) -> UUID:
    """Validate and append one event; return its event_id.

    Append-only: corrections are new events, never UPDATEs (Design 04).
    """
    clean = validate_payload(event_type, payload)
    event_id = uuid4()
    params = {
        "event_id": event_id,
        "event_type": event_type,
        "event_version": event_version,
        "occurred_at": occurred_at or datetime.now(UTC),
        "customer_id": customer_id,
        "talent_id": talent_id,
        "rm_id": rm_id,
        "case_id": case_id,
        "action_id": str(action_id) if action_id else None,
        "episode_id": str(episode_id) if episode_id else None,
        "skill_id": skill_id,
        "payload": Jsonb(clean),
        "tier_class": tier_class,
        "urgency": urgency,
        "correlation_id": str(correlation_id) if correlation_id else None,
        "actor": actor,
        "reasoning_text": reasoning_text,
        "reasoning_tags": reasoning_tags,
        "trace_id": str(trace_id) if trace_id else _current_trace_id(),
    }
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(_INSERT, params)
    return event_id


# ── Per-event-type helpers (Design 04 enum) ──────────────────────────────────
# Thin, typed wrappers so callers don't pass raw event-type strings. Each builds
# the payload dict and forwards structured column kwargs via **cols.


async def emit_signal_received(
    source: str, source_event_id: str, headers_hash=None, **cols
) -> UUID:
    return await emit_event(
        "signal-received",
        {"source": source, "source_event_id": source_event_id, "headers_hash": headers_hash},
        **cols,
    )


async def emit_signal_rejected(source: str, reason: str, **cols) -> UUID:
    return await emit_event("signal-rejected", {"source": source, "reason": reason}, **cols)


async def emit_signal_normalized(
    episode_id: str, dedup_key: str, content_size: int, **cols
) -> UUID:
    return await emit_event(
        "signal-normalized",
        {"episode_id": episode_id, "dedup_key": dedup_key, "content_size": content_size},
        **cols,
    )


async def emit_episode_ingested(
    episode_id: str,
    extraction_model: str,
    latency_ms: int,
    entity_extractions: list[str] | None = None,
    edge_extractions: list[str] | None = None,
    **cols,
) -> UUID:
    return await emit_event(
        "episode-ingested",
        {
            "episode_id": episode_id,
            "entity_extractions": entity_extractions or [],
            "edge_extractions": edge_extractions or [],
            "extraction_model": extraction_model,
            "latency_ms": latency_ms,
        },
        **cols,
    )


async def emit_episode_deduped(episode_id: str, duplicate_of: str, **cols) -> UUID:
    return await emit_event(
        "episode-deduped", {"episode_id": episode_id, "duplicate_of": duplicate_of}, **cols
    )


async def emit_ingestion_failed(
    stage: str, error_class: str, error_message_summary: str, **cols
) -> UUID:
    return await emit_event(
        "ingestion-failed",
        {
            "stage": stage,
            "error_class": error_class,
            "error_message_summary": error_message_summary,
        },
        **cols,
    )


async def emit_skill_fired(
    skill_id: str, trigger_event_id=None, context_bundle_summary=None, **cols
) -> UUID:
    return await emit_event(
        "skill-fired",
        {
            "skill_id": skill_id,
            "trigger_event_id": trigger_event_id,
            "context_bundle_summary": context_bundle_summary,
        },
        skill_id=skill_id,
        **cols,
    )


async def emit_context_retrieved(
    retrievers_called: list[str],
    entity_count: int,
    episode_count: int,
    retrieval_latency_ms: int,
    **cols,
) -> UUID:
    return await emit_event(
        "context-retrieved",
        {
            "retrievers_called": retrievers_called,
            "entity_count": entity_count,
            "episode_count": episode_count,
            "retrieval_latency_ms": retrieval_latency_ms,
        },
        **cols,
    )


async def emit_reasoning_completed(
    model: str, tokens_in: int, tokens_out: int, latency_ms: int, reasoning_summary=None, **cols
) -> UUID:
    return await emit_event(
        "reasoning-completed",
        {
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
            "reasoning_summary": reasoning_summary,
        },
        **cols,
    )


async def emit_action_suggested(
    action_card: dict, why_oneline: str, urgency: str, why_detail=None, source_episodes=None, **cols
) -> UUID:
    return await emit_event(
        "action-suggested",
        {
            "action_card": action_card,
            "why_oneline": why_oneline,
            "why_detail": why_detail,
            "urgency": urgency,
            "source_episodes": source_episodes or [],
        },
        urgency=urgency,
        **cols,
    )


async def emit_action_approved(
    action_id: str, approver_id: str, decision_latency_ms=None, **cols
) -> UUID:
    return await emit_event(
        "action-approved",
        {
            "action_id": action_id,
            "approver_id": approver_id,
            "decision_latency_ms": decision_latency_ms,
        },
        action_id=action_id,
        **cols,
    )


async def emit_action_modified_and_approved(
    action_id: str, approver_id: str, diff: dict, decision_latency_ms=None, **cols
) -> UUID:
    return await emit_event(
        "action-modified-and-approved",
        {
            "action_id": action_id,
            "approver_id": approver_id,
            "diff": diff,
            "decision_latency_ms": decision_latency_ms,
        },
        action_id=action_id,
        **cols,
    )


async def emit_action_rejected(
    action_id: str, approver_id: str, reason_picker: str, free_text=None, **cols
) -> UUID:
    return await emit_event(
        "action-rejected",
        {
            "action_id": action_id,
            "approver_id": approver_id,
            "reason_picker": reason_picker,
            "free_text": free_text,
        },
        action_id=action_id,
        **cols,
    )


async def emit_action_expired(action_id: str, expired_after_seconds: int, **cols) -> UUID:
    return await emit_event(
        "action-expired",
        {"action_id": action_id, "expired_after_seconds": expired_after_seconds},
        action_id=action_id,
        **cols,
    )


async def emit_action_executed(
    action_id: str, handler: str, external_id=None, dispatch_latency_ms=None, **cols
) -> UUID:
    return await emit_event(
        "action-executed",
        {
            "action_id": action_id,
            "handler": handler,
            "external_id": external_id,
            "dispatch_latency_ms": dispatch_latency_ms,
        },
        action_id=action_id,
        **cols,
    )


async def emit_dispatch_failed(
    action_id: str, handler: str, error_class: str, retry_attempt: int, **cols
) -> UUID:
    return await emit_event(
        "dispatch-failed",
        {
            "action_id": action_id,
            "handler": handler,
            "error_class": error_class,
            "retry_attempt": retry_attempt,
        },
        action_id=action_id,
        **cols,
    )


async def emit_outcome_recorded(
    action_id: str, outcome_type: str, evidence_episode_id=None, **cols
) -> UUID:
    return await emit_event(
        "outcome-recorded",
        {
            "action_id": action_id,
            "outcome_type": outcome_type,
            "evidence_episode_id": evidence_episode_id,
        },
        action_id=action_id,
        **cols,
    )


async def emit_outcome_missing(
    action_id: str, outcome_window_closed_at: str, expected_outcome_type: str, **cols
) -> UUID:
    return await emit_event(
        "outcome-missing",
        {
            "action_id": action_id,
            "outcome_window_closed_at": outcome_window_closed_at,
            "expected_outcome_type": expected_outcome_type,
        },
        action_id=action_id,
        **cols,
    )


async def emit_policy_decision(
    action_id: str, decision: str, thresholds_applied: dict | None = None, **cols
) -> UUID:
    return await emit_event(
        "policy-decision",
        {
            "action_id": action_id,
            "decision": decision,
            "thresholds_applied": thresholds_applied or {},
        },
        action_id=action_id,
        actor="policy",
        **cols,
    )


async def emit_kill_switch_flipped(user_id: str, scope: str, on_or_off: bool, **cols) -> UUID:
    return await emit_event(
        "kill-switch-flipped",
        {"user_id": user_id, "scope": scope, "on_or_off": on_or_off},
        actor=f"user:{user_id}",
        **cols,
    )


async def emit_events_bulk(events: list[dict]) -> list[UUID]:
    """Validate and append many events in one round trip (executemany).

    Each item is a kwargs dict accepted by emit_event ({"event_type", "payload",
    ...}). Used by adapters/backfills and the burst path; payloads are validated
    up front so a single bad item raises before any insert.
    """
    rows: list[dict] = []
    ids: list[UUID] = []
    now = datetime.now(UTC)
    for ev in events:
        et = ev["event_type"]
        clean = validate_payload(et, ev["payload"])
        eid = uuid4()
        ids.append(eid)
        rows.append(
            {
                "event_id": eid,
                "event_type": et,
                "event_version": ev.get("event_version", 1),
                "occurred_at": ev.get("occurred_at") or now,
                "customer_id": ev.get("customer_id"),
                "talent_id": ev.get("talent_id"),
                "rm_id": ev.get("rm_id"),
                "case_id": ev.get("case_id"),
                "action_id": str(ev["action_id"]) if ev.get("action_id") else None,
                "episode_id": str(ev["episode_id"]) if ev.get("episode_id") else None,
                "skill_id": ev.get("skill_id"),
                "payload": Jsonb(clean),
                "tier_class": ev.get("tier_class"),
                "urgency": ev.get("urgency"),
                "correlation_id": str(ev["correlation_id"]) if ev.get("correlation_id") else None,
                "actor": ev.get("actor", "system"),
                "reasoning_text": ev.get("reasoning_text"),
                "reasoning_tags": ev.get("reasoning_tags"),
                "trace_id": str(ev["trace_id"]) if ev.get("trace_id") else None,
            }
        )
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(_INSERT, rows)
    return ids


def _payload_json(payload: dict) -> str:
    """Helper for tests/tools: stable JSON string of a validated payload."""
    return json.dumps(payload, sort_keys=True, default=str)
