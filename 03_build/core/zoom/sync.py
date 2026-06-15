"""
Zoom → pulse.episodes sync (poll-based, identical pattern to core/chorus/sync.py).

pull_and_ingest():
  1. Loads SF account index for fuzzy topic→account matching.
  2. Polls Zoom Reports API (all users, 30-day windows) since the last synced
     timestamp, or from 2020-01-01 on first run.
  3. Upserts into pulse.episodes with ON CONFLICT DO NOTHING.

Dedup key: zoom:meeting:{uuid} — stable across re-fetches.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from psycopg.types.json import Jsonb

from core.adapters.zoom import ZoomAdapter
from core.db import get_pool

log = logging.getLogger(__name__)
_ALL_TIME_SINCE = datetime(2025, 12, 1, tzinfo=UTC)  # Zoom reporting retention is 6 months

_INSERT_EPISODE = """
INSERT INTO pulse.episodes (
    episode_id, dedup_key, source, source_event_id, source_url, source_timestamp,
    content_type, content, subject, description, candidate_entities, tags,
    processing_state, ingested_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'received', NOW()
)
ON CONFLICT (dedup_key) DO NOTHING
RETURNING episode_id;
"""


async def _load_account_index() -> list[dict]:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT account_id, name FROM pulse.sf_accounts WHERE name IS NOT NULL;"
            )
            rows = await cur.fetchall()
    return [{"id": row[0], "name": row[1]} for row in rows]


async def _last_synced_at() -> datetime | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT MAX(source_timestamp) FROM pulse.episodes WHERE source = 'zoom';"
            )
            row = await cur.fetchone()
    return row[0] if row and row[0] else None


async def _upsert_episode(conn, episode) -> bool:
    content = episode["content"]
    candidate_entities = episode.get("candidate_entities", [])
    async with conn.cursor() as cur:
        await cur.execute(
            _INSERT_EPISODE,
            (
                str(episode["episode_id"]),
                episode["dedup_key"],
                episode["source"],
                episode.get("source_event_id"),
                episode.get("source_url"),
                episode.get("source_timestamp"),
                episode["content_type"],
                Jsonb(content) if isinstance(content, dict) else Jsonb({"text": content}),
                episode.get("subject"),
                episode.get("description"),
                Jsonb(candidate_entities),
                episode.get("tags", []),
            ),
        )
        row = await cur.fetchone()
    return row is not None


async def pull_and_ingest(since: datetime | None = None) -> dict:
    """
    Poll Zoom and upsert meetings into pulse.episodes.

    Returns:
        {"fetched": int, "ingested": int, "duplicates": int, "errors": int}
    """
    account_id = os.environ.get("ZOOM_ACCOUNT_ID", "")
    client_id = os.environ.get("ZOOM_CLIENT_ID", "")
    client_secret = os.environ.get("ZOOM_CLIENT_SECRET", "")

    if not all([account_id, client_id, client_secret]):
        log.warning("ZOOM credentials not set — skipping Zoom sync.")
        return {"fetched": 0, "ingested": 0, "duplicates": 0, "errors": 0}

    if since is None:
        last = await _last_synced_at()
        since = last if last else _ALL_TIME_SINCE
        log.info("Zoom sync since %s", since.isoformat())

    account_index = await _load_account_index()
    log.info("Zoom account index: %d SF accounts loaded.", len(account_index))

    adapter = ZoomAdapter(
        account_id=account_id,
        client_id=client_id,
        client_secret=client_secret,
        account_index=account_index,
    )

    try:
        raw_events = await adapter.list_recent_events(since=since)
    except Exception as exc:
        log.error("Zoom API error during list_recent_events: %s", exc)
        return {"fetched": 0, "ingested": 0, "duplicates": 0, "errors": 1}

    log.info("Zoom: fetched %d raw events.", len(raw_events))

    ingested = duplicates = errors = 0
    pool = await get_pool()

    for raw in raw_events:
        try:
            full = await adapter.fetch_full(raw)
            episode = adapter.normalize(full)
            episode["dedup_key"] = adapter.dedup_key(raw)

            async with pool.connection() as conn:
                new = await _upsert_episode(conn, episode)

            if new:
                ingested += 1
                sfdc_ids = [
                    e.get("sfdc_id")
                    for e in episode.get("candidate_entities", [])
                    if e.get("sfdc_id")
                ]
                log.info(
                    "Zoom episode ingested: %s | sfdc=%s",
                    episode.get("subject", "?")[:60],
                    sfdc_ids[0] if sfdc_ids else "no-match",
                )
            else:
                duplicates += 1

        except Exception as exc:
            log.error(
                "Zoom ingest error for event %s: %s",
                raw.get("source_event_id", "?"),
                exc,
            )
            errors += 1

    log.info(
        "Zoom sync complete — fetched=%d ingested=%d duplicates=%d errors=%d",
        len(raw_events),
        ingested,
        duplicates,
        errors,
    )
    return {
        "fetched": len(raw_events),
        "ingested": ingested,
        "duplicates": duplicates,
        "errors": errors,
    }
