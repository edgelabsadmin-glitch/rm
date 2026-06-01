"""
Chorus → pulse.episodes sync (poll-based, no Graphiti dependency for Phase 1).

pull_and_ingest():
  1. Loads the SF account index from pulse.sf_accounts (id + name) so the
     ChorusAdapter can fuzzy-match meeting account names to SFDC IDs.
  2. Polls the Chorus v3 /engagements API for meetings since `since` (default:
     90 days on first run, last 12 h on subsequent runs via the sync loop).
  3. Normalizes each meeting into the canonical Episode envelope and upserts
     into pulse.episodes with ON CONFLICT DO NOTHING (idempotency gate).

Linking strategy: ChorusAdapter._resolve_account() does token-set fuzzy match
(threshold 85) against the SF account name index.  The best-match SFDC account_id
is stored in episode.candidate_entities[0].sfdc_id — the same field the memory
layer (Graphiti) will consume when it is wired in later.  This is intentional:
no separate join table needed; the episodes row carries the binding.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone

from psycopg.types.json import Jsonb

from core.adapters.chorus import ChorusAdapter
from core.db import get_pool

log = logging.getLogger(__name__)

UTC = timezone.utc
_BACKFILL_DAYS = 90  # how far back the very first run fetches


async def _load_account_index() -> list[dict]:
    """Return [{id, name}] from pulse.sf_accounts for the fuzzy matcher."""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT account_id, name FROM pulse.sf_accounts WHERE name IS NOT NULL;"
            )
            rows = await cur.fetchall()
    return [{"id": row[0], "name": row[1]} for row in rows]


async def _last_synced_at() -> datetime | None:
    """Return the most recent source_timestamp from Chorus episodes, or None."""
    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT MAX(source_timestamp) FROM pulse.episodes WHERE source = 'chorus';"
            )
            row = await cur.fetchone()
    return row[0] if row and row[0] else None


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


async def _upsert_episode(conn, episode) -> bool:
    """Insert one Episode; returns True if newly written, False if duplicate."""
    content = episode["content"]
    content_val = Jsonb(content) if isinstance(content, str) else Jsonb(content)
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
                Jsonb(content) if not isinstance(content, str) else Jsonb({"text": content}),
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
    Poll Chorus and upsert meetings into pulse.episodes.

    Args:
        since: fetch meetings after this datetime. If None, auto-detects:
               uses last synced timestamp or falls back to 90-day backfill.

    Returns:
        {"fetched": int, "ingested": int, "duplicates": int, "errors": int}
    """
    token = os.environ.get("CHORUS_API_TOKEN", "")
    if not token:
        log.warning("CHORUS_API_TOKEN not set — skipping Chorus sync.")
        return {"fetched": 0, "ingested": 0, "duplicates": 0, "errors": 0}

    # Determine cutoff — use last sync watermark or backfill 90 days
    if since is None:
        last = await _last_synced_at()
        since = last if last else datetime.now(UTC) - timedelta(days=_BACKFILL_DAYS)
        log.info("Chorus sync since %s", since.isoformat())

    account_index = await _load_account_index()
    log.info("Chorus account index: %d SF accounts loaded for fuzzy match.", len(account_index))

    adapter = ChorusAdapter(token=token, account_index=account_index)

    try:
        raw_events = await adapter.list_recent_events(since=since)
    except Exception as exc:
        log.error("Chorus API error during list_recent_events: %s", exc)
        return {"fetched": 0, "ingested": 0, "duplicates": 0, "errors": 1}

    log.info("Chorus: fetched %d raw events.", len(raw_events))

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
                    "Chorus episode ingested: %s | account=%s | sfdc=%s",
                    episode.get("subject", "?")[:60],
                    next(
                        (e.get("name") for e in episode.get("candidate_entities", []) if e.get("name")),
                        "unknown",
                    ),
                    sfdc_ids[0] if sfdc_ids else "no-match",
                )
            else:
                duplicates += 1

        except Exception as exc:
            log.error(
                "Chorus ingest error for event %s: %s",
                raw.get("source_event_id", "?"),
                exc,
            )
            errors += 1

    log.info(
        "Chorus sync complete — fetched=%d ingested=%d duplicates=%d errors=%d",
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
