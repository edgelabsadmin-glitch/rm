"""
SPEC-015 — opportunity-tracker Signal Source Adapter (Spike 4 §3).

opportunity-tracker mirror-writes job-posting matches into
pulse.expansion_intent_signals; this adapter polls unprocessed rows, normalizes
each into an Episode (Spike 4 §3.4 mapping), and stamps the row's
processed_at / pulse_episode_id / processed_status. `off-scope` rows (Q120) are
skipped — no Episode, status 'skipped:off-scope'.

Triggered in production by the Activepieces `expansion_intent_poll` flow (30-min
cron → /webhooks/expansion-intent). The opp-tracker mirror-write itself is a
coordinated PR against that repo (operator/Week-2).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from psycopg.rows import dict_row

from core.adapters.base import SignalSourceAdapter
from core.adapters.episode import Episode, RawEvent
from core.db import get_pool

OFF_SCOPE = "off-scope"


class OpportunityTrackerAdapter(SignalSourceAdapter):
    SOURCE_NAME = "opportunity-tracker"
    SUPPORTS_WEBHOOKS = True
    SUPPORTS_BACKFILL = True

    async def list_recent_events(self, since: datetime) -> list[RawEvent]:
        """Poll unprocessed rows. off-scope rows are marked skipped and excluded;
        every other row becomes a RawEvent."""
        pool = await get_pool()
        async with pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM pulse.expansion_intent_signals WHERE processed_at IS NULL "
                    "ORDER BY first_seen_date DESC;"
                )
                rows = await cur.fetchall()

        events: list[RawEvent] = []
        for row in rows:
            if (row.get("match_tier") or "").lower() == OFF_SCOPE:
                await self.mark_processed(row["posting_id"], None, "skipped:off-scope")
                continue
            events.append(self._raw(row))
        return events

    async def receive_webhook(self, payload: dict, headers: dict) -> list[RawEvent]:
        """The Activepieces fan-out posts one row."""
        row = payload.get("row") or payload
        if not row.get("posting_id"):
            raise ValueError("malformed expansion-intent webhook: missing posting_id")
        if (row.get("match_tier") or "").lower() == OFF_SCOPE:
            await self.mark_processed(row["posting_id"], None, "skipped:off-scope")
            return []
        return [self._raw(row)]

    async def fetch_full(self, event: RawEvent) -> RawEvent:
        return event  # the row is already complete

    def normalize(self, raw: RawEvent) -> Episode:
        row: dict = raw.get("payload", {})["row"]
        posting_id = row["posting_id"]
        tier = row.get("match_tier") or "general"
        matched_role = row.get("matched_role") or ""

        return Episode(
            episode_id=uuid4(),
            dedup_key=self.dedup_key(raw),
            source=self.SOURCE_NAME,
            source_event_id=posting_id,
            source_url=row.get("url"),
            source_timestamp=_parse_dt(row.get("first_seen_date")),
            content_type="json",
            content={
                "posting": {
                    "title": row.get("title"),
                    "company": row.get("company"),
                    "location": row.get("location"),
                    "source": row.get("source"),
                    "url": row.get("url"),
                    "date_posted": row.get("date_posted"),
                    "description": row.get("description"),
                },
                "match": {
                    "tier": tier,
                    "matched_role": matched_role,
                    "matched_industry": row.get("matched_industry"),
                    "score": row.get("match_score"),
                    "reasoning": row.get("reasoning"),
                    "outreach_suggestion": row.get("outreach_suggestion"),
                    "signals": row.get("signals") or [],
                    "work_arrangement": row.get("work_arrangement"),
                },
            },
            subject=f"Job posting: {row.get('title') or matched_role} @ {row.get('account_name')}"[
                :120
            ],
            description=f"opportunity-tracker {tier} match: {matched_role}",
            candidate_entities=[{"type": "Customer", "sfdc_id": row["account_id"]}],
            tags=["expansion-intent", tier, row.get("source") or "unknown"],
            ingested_at=datetime.now().astimezone(),
            processing_state="normalized",
        )

    def dedup_key(self, raw: RawEvent) -> str:
        return f"oppt:posting:{raw.get('payload', {})['row']['posting_id']}"

    # ── status bookkeeping ───────────────────────────────────────────────────
    async def mark_processed(
        self, posting_id: str, episode_id: UUID | str | None, status: str
    ) -> None:
        """Stamp a row processed. Only sets processed_at if still NULL so a
        re-delivery doesn't overwrite the first ingestion time (Spike 4 §3.5)."""
        pool = await get_pool()
        async with pool.connection() as conn:
            await conn.execute(
                "UPDATE pulse.expansion_intent_signals "
                "SET processed_at = COALESCE(processed_at, NOW()), "
                "    pulse_episode_id = COALESCE(pulse_episode_id, %s), "
                "    processed_status = %s "
                "WHERE posting_id = %s;",
                (str(episode_id) if episode_id else None, status, posting_id),
            )

    def _raw(self, row: dict) -> RawEvent:
        return {
            "source": self.SOURCE_NAME,
            "source_event_id": row["posting_id"],
            "source_url": row.get("url"),
            "payload": {"row": row},
        }


def _parse_dt(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.now().astimezone()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now().astimezone()
