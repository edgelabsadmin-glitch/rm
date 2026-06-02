"""
SPEC-031 — Action Queue read model (Design 03).

There is no separate "actions" table: an action's state is reconstructed by
folding its events (keyed on `action_id`) in the append-only `pulse.events`
log. `action-suggested` is the genesis; a decision event
(approved / modified-and-approved / rejected / expired) or `action-executed`
takes the item out of the *pending* queue. This module derives the queue the
Action Queue UI consumes: pending list (scoped, filtered, ranked, paginated) and
single-action detail (full reasoning + lifecycle history).

Ranking is a pure, tunable composite score computed at retrieval time (Design 03
§"Ranking logic") — no manual reordering in Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

UTC = timezone.utc
from typing import Any

# Events that take an action OUT of the pending queue (Design 03 approval_state).
_TERMINAL = (
    "action-approved",
    "action-modified-and-approved",
    "action-rejected",
    "action-expired",
    "action-executed",
)

# Urgency → weight (Design 03 §"Ranking logic" Phase-1 defaults; tunable).
_URGENCY_WEIGHT = {
    "high": 100.0,
    "medium-high": 60.0,
    "medium": 30.0,
    "medium-low": 10.0,
    "low": 1.0,
}
# Tier signal bonus: Enterprise > Mid > SMB. Accepts both "Mid" and "Mid-Market".
_TIER_BONUS = {"Enterprise": 20.0, "Mid-Market": 10.0, "Mid": 10.0, "SMB": 5.0}
_RECENCY_MAX_BONUS = 5.0  # newer surfaces above older, ceteris paribus
_RECENCY_HALF_LIFE_H = 48.0


def ranking_score(
    urgency: str | None, tier_class: str | None, proposed_at: datetime, now: datetime | None = None
) -> float:
    """Composite ranking score (Design 03). Higher = surfaced higher in the queue.

    score = urgency_weight + tier_signal_bonus + recency_bonus. Deadline-proximity
    and acknowledged-penalty terms from Design 03 are deferred (no expires_at /
    ack state captured in Phase-1 events) — additive when those land.
    """
    now = now or datetime.now(UTC)
    score = _URGENCY_WEIGHT.get((urgency or "medium").lower(), 30.0)
    score += _TIER_BONUS.get(tier_class or "", 0.0)
    age_h = max(0.0, (now - proposed_at).total_seconds() / 3600.0)
    score += _RECENCY_MAX_BONUS * max(0.0, 1.0 - age_h / _RECENCY_HALF_LIFE_H)
    return round(score, 4)


@dataclass
class ActionRecord:
    """A pending/decided action folded from the event log (Design 03 ActionCard)."""

    action_id: str
    skill_id: str | None
    customer_id: str | None
    talent_id: str | None
    rm_id: str | None
    tier_class: str | None
    urgency: str | None
    action_card: dict[str, Any]
    why_oneline: str
    why_detail: str | None
    modifiable_fields: list[str]
    source_episodes: list[str]
    proposed_at: datetime
    status: str = "pending"  # pending|approved|modified-approved|rejected|expired|dispatched
    rank_score: float = 0.0
    history: list[dict[str, Any]] = field(default_factory=list)

    def public_dict(self, *, include_skill: bool = True) -> dict[str, Any]:
        """JSON-serializable view. `include_skill=False` hides the firing skill
        from non-admins (Design 03 §"why" — skill visible to admins for tuning)."""
        d: dict[str, Any] = {
            "action_id": self.action_id,
            "customer_id": self.customer_id,
            "talent_id": self.talent_id,
            "rm_id": self.rm_id,
            "tier_class": self.tier_class,
            "urgency": self.urgency,
            "action_card": self.action_card,
            "why_oneline": self.why_oneline,
            "why_detail": self.why_detail,
            "modifiable_fields": self.modifiable_fields,
            "source_episodes": self.source_episodes,
            "proposed_at": self.proposed_at.isoformat(),
            "status": self.status,
            "rank_score": self.rank_score,
        }
        if include_skill:
            d["skill_id"] = self.skill_id
        return d


def _record_from_suggested(row: dict[str, Any]) -> ActionRecord:
    p = row["payload"] or {}
    return ActionRecord(
        action_id=str(row["action_id"]),
        skill_id=row.get("skill_id"),
        customer_id=row.get("customer_id"),
        talent_id=row.get("talent_id"),
        rm_id=row.get("rm_id"),
        tier_class=row.get("tier_class"),
        urgency=row.get("urgency") or p.get("urgency"),
        action_card=p.get("action_card", {}),
        why_oneline=p.get("why_oneline", ""),
        why_detail=p.get("why_detail"),
        modifiable_fields=list(p.get("modifiable_fields", [])),
        source_episodes=list(p.get("source_episodes", [])),
        proposed_at=row["occurred_at"],
    )


async def list_pending_actions(
    *,
    visible_rm_ids: list[str] | None = None,
    tier_class: str | None = None,
    customer_id: str | None = None,
    skill_id: str | None = None,
    rm_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    now: datetime | None = None,
) -> list[ActionRecord]:
    """Pending actions in the caller's scope, ranked (Design 03), paginated.

    `visible_rm_ids=None` means unrestricted (admin); an empty list means the
    caller can see nothing. Additional args are the filter chips (tier / customer
    / skill / owner) — applied as SQL predicates so the DB does the filtering.
    """
    from psycopg.rows import dict_row

    from core.db import get_pool

    where = ["e.event_type = 'action-suggested'"]
    params: dict[str, Any] = {}
    if visible_rm_ids is not None:
        if not visible_rm_ids:
            return []
        where.append("e.rm_id = ANY(%(visible_rm_ids)s)")
        params["visible_rm_ids"] = visible_rm_ids
    if tier_class:
        where.append("e.tier_class = %(tier_class)s")
        params["tier_class"] = tier_class
    if customer_id:
        where.append("e.customer_id = %(customer_id)s")
        params["customer_id"] = customer_id
    if skill_id:
        where.append("e.skill_id = %(skill_id)s")
        params["skill_id"] = skill_id
    if rm_id:
        where.append("e.rm_id = %(rm_id)s")
        params["rm_id"] = rm_id

    sql = (
        "SELECT e.action_id, e.occurred_at, e.customer_id, e.talent_id, e.rm_id, "
        "e.tier_class, e.urgency, e.skill_id, e.payload FROM pulse.events e WHERE "
        + " AND ".join(where)
        + " AND NOT EXISTS (SELECT 1 FROM pulse.events d WHERE d.action_id = e.action_id "
        "AND d.event_type = ANY(%(terminal)s)) AND e.action_id IS NOT NULL"
    )
    params["terminal"] = list(_TERMINAL)

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(sql, params)  # type: ignore[arg-type]
            rows = await cur.fetchall()

    now = now or datetime.now(UTC)
    records = [_record_from_suggested(r) for r in rows]
    for rec in records:
        rec.rank_score = ranking_score(rec.urgency, rec.tier_class, rec.proposed_at, now)
    # Rank DESC, tie-break proposed_at DESC (Design 03).
    records.sort(key=lambda r: (r.rank_score, r.proposed_at), reverse=True)
    return records[offset : offset + limit]


def _status_from_history(history: list[dict[str, Any]]) -> str:
    """Latest lifecycle state from the (oldest→newest) event history."""
    state = "pending"
    for ev in history:
        et = ev["event_type"]
        if et == "action-approved":
            state = "approved"
        elif et == "action-modified-and-approved":
            state = "modified-approved"
        elif et == "action-rejected":
            state = "rejected"
        elif et == "action-expired":
            state = "expired"
        elif et == "action-executed":
            state = "dispatched"
    return state


async def get_action(action_id: str, *, now: datetime | None = None) -> ActionRecord | None:
    """Single action with full lifecycle history, or None if no such action."""
    from psycopg.rows import dict_row

    from core.db import get_pool

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT event_type, occurred_at, customer_id, talent_id, rm_id, "
                "tier_class, urgency, skill_id, actor, payload FROM pulse.events "
                "WHERE action_id = %(aid)s ORDER BY occurred_at ASC;",
                {"aid": action_id},
            )
            rows = await cur.fetchall()
    if not rows:
        return None
    suggested = next((r for r in rows if r["event_type"] == "action-suggested"), None)
    if suggested is None:
        return None  # orphan lifecycle event without a genesis — not a real card
    suggested["action_id"] = action_id
    rec = _record_from_suggested(suggested)
    rec.history = [
        {
            "event_type": r["event_type"],
            "occurred_at": r["occurred_at"].isoformat(),
            "actor": r["actor"],
            "payload": r["payload"],
        }
        for r in rows
    ]
    rec.status = _status_from_history(rec.history)
    rec.rank_score = ranking_score(rec.urgency, rec.tier_class, rec.proposed_at, now)
    return rec
