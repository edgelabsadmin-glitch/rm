"""
SPEC-011 — the central ingestion pipeline (Design 02 §"The ingestion pipeline").

`ingest_raw(adapter, raw)` runs the full sequence for one source event:
    dedup-key → fetch_full → normalize → run_episode
`run_episode(episode)` is the authoritative gate + writer:
    INSERT into pulse.episodes (UNIQUE(dedup_key) = idempotency) →
    Graphiti.add_episode (memory layer) → event-log emission.

Idempotency is enforced by the UNIQUE(dedup_key) constraint via
INSERT ... ON CONFLICT DO NOTHING: a re-delivered event inserts zero rows and is
a clean no-op (emits `episode-deduped`, returns False). Per Design 02's error
table, a memory-ingest failure leaves the row in `processing_state='normalized'`
for the retry cron and emits `ingestion-failed` (no silent failure, §6 rule 14).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
UTC = timezone.utc
from time import perf_counter
from typing import TYPE_CHECKING

from graphiti_core.nodes import EpisodeType
from psycopg.types.json import Jsonb

from core.adapters.base import SignalSourceAdapter
from core.adapters.episode import Episode, RawEvent
from core.db import get_pool
from core.events import log
from core.llm.config import ANTHROPIC_HAIKU
from core.memory.graph import DEFAULT_NAMESPACE, add_pulse_episode

if TYPE_CHECKING:
    from graphiti_core import Graphiti

_INSERT_EPISODE = """
INSERT INTO pulse.episodes (
    episode_id, dedup_key, source, source_event_id, source_url, source_timestamp,
    content_type, content, subject, description, candidate_entities, tags, processing_state
) VALUES (
    %(episode_id)s, %(dedup_key)s, %(source)s, %(source_event_id)s, %(source_url)s,
    %(source_timestamp)s, %(content_type)s, %(content)s, %(subject)s, %(description)s,
    %(candidate_entities)s, %(tags)s, 'received'
)
ON CONFLICT (dedup_key) DO NOTHING
RETURNING episode_id;
"""


def _content_size(content: str | dict) -> int:
    return len(content if isinstance(content, str) else json.dumps(content))


def _episode_body(episode: Episode) -> tuple[str, EpisodeType]:
    content = episode["content"]
    if episode["content_type"] == "text" and isinstance(content, str):
        return content, EpisodeType.text
    body = content if isinstance(content, str) else json.dumps(content)
    return body, EpisodeType.json


async def _existing_episode_id(conn, dedup_key: str) -> str | None:
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT episode_id FROM pulse.episodes WHERE dedup_key = %s;", (dedup_key,)
        )
        row = await cur.fetchone()
    return str(row[0]) if row else None


async def _set_state(conn, episode_id, state: str) -> None:
    async with conn.cursor() as cur:
        await cur.execute(
            "UPDATE pulse.episodes SET processing_state = %s WHERE episode_id = %s;",
            (state, str(episode_id)),
        )


async def run_episode(episode: Episode, *, graphiti: Graphiti | None = None) -> bool:
    """Idempotently ingest one normalized Episode. Returns True if newly ingested,
    False if it was a duplicate (already seen). Raises (after emitting
    `ingestion-failed`) if the memory-layer write fails."""
    dedup_key = episode["dedup_key"]
    episode_id = episode["episode_id"]
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _INSERT_EPISODE,
                {
                    "episode_id": str(episode_id),
                    "dedup_key": dedup_key,
                    "source": episode["source"],
                    "source_event_id": episode.get("source_event_id"),
                    "source_url": episode.get("source_url"),
                    "source_timestamp": episode.get("source_timestamp"),
                    "content_type": episode["content_type"],
                    "content": Jsonb(episode["content"]),
                    "subject": episode.get("subject"),
                    "description": episode.get("description"),
                    "candidate_entities": Jsonb(episode.get("candidate_entities", [])),
                    "tags": episode.get("tags", []),
                },
            )
            inserted = await cur.fetchone()

        if inserted is None:
            duplicate_of = await _existing_episode_id(conn, dedup_key)
            await log.emit_episode_deduped(
                episode_id=str(episode_id), duplicate_of=duplicate_of or dedup_key
            )
            return False

    await log.emit_signal_normalized(
        episode_id=str(episode_id),
        dedup_key=dedup_key,
        content_size=_content_size(episode["content"]),
    )

    body, ep_type = _episode_body(episode)
    if graphiti is None:
        from core.memory.graph import get_shared_graphiti

        graphiti = await get_shared_graphiti()

    t0 = perf_counter()
    try:
        result = await add_pulse_episode(
            graphiti,
            name=episode.get("subject") or str(episode_id),
            episode_body=body,
            reference_time=episode.get("source_timestamp") or datetime.now(UTC),
            source=ep_type,
            source_description=episode.get("description") or episode["source"],
            namespace=DEFAULT_NAMESPACE,
        )
    except Exception as e:
        async with pool.connection() as conn:
            await _set_state(conn, episode_id, "normalized")  # hold for retry cron
        await log.emit_ingestion_failed(
            stage="memory-ingest",
            error_class=type(e).__name__,
            error_message_summary=str(e)[:300],
            episode_id=str(episode_id),
        )
        raise

    latency_ms = int((perf_counter() - t0) * 1000)
    nodes = getattr(result, "nodes", []) or []
    edges = getattr(result, "edges", []) or []
    async with pool.connection() as conn:
        await _set_state(conn, episode_id, "ingested")
    await log.emit_episode_ingested(
        episode_id=str(episode_id),
        extraction_model=ANTHROPIC_HAIKU,
        latency_ms=latency_ms,
        entity_extractions=[getattr(n, "name", str(n)) for n in nodes],
        edge_extractions=[getattr(e, "name", str(e)) for e in edges],
    )
    return True


async def ingest_raw(
    adapter: SignalSourceAdapter, raw: RawEvent, *, graphiti: Graphiti | None = None
) -> bool:
    """Full per-event sequence: dedup-key → fetch_full → normalize → run_episode.

    Emits `signal-received` up front; `fetch_full` hydrates thin webhook events.
    The Episode's dedup_key is forced to the adapter's deterministic key so the
    Postgres idempotency gate is authoritative.
    """
    dedup_key = adapter.dedup_key(raw)
    await log.emit_signal_received(
        source=adapter.SOURCE_NAME,
        source_event_id=str(raw.get("source_event_id", "")),
    )
    full = await adapter.fetch_full(raw)
    episode = adapter.normalize(full)
    episode["dedup_key"] = dedup_key
    return await run_episode(episode, graphiti=graphiti)
