"""
Per-entity Evidence Pack — the deterministic, curated input the LLM analyst
reasons over (and *only* this). No raw dumps: hard facts + a bounded set of
labeled, timestamped snippets, each with a stable evidence id so the validation
gate can reject fabricated citations.

`shape_account_facts` is pure (unit-tested). `build_account_pack` /
`build_talent_pack` do the DB IO and call the shaper.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from psycopg.rows import dict_row

from core.db import get_pool

_SNIPPET_CAP = 12  # max curated text snippets per entity


def shape_account_facts(row: dict, **derived: Any) -> dict:
    """Build the account facts dict + the evidence-id set (pure)."""
    facts: dict[str, Any] = {
        "account_id": row["account_id"],
        "tier": row.get("tier"),
        "active_talent": row.get("active_talent"),
        "churn_probability": row.get("churn_probability"),
        "days_since_ebr": derived.get("days_since_ebr"),
        "talent_baseline": derived.get("talent_baseline"),
        "departures_30d": derived.get("departures_30d"),
        "onboarding_30d": derived.get("onboarding_30d"),
        "max_days_in_onboarding": derived.get("max_days_in_onboarding"),
        "reply_latency_now_h": derived.get("reply_latency_now_h"),
        "reply_latency_prior_h": derived.get("reply_latency_prior_h"),
        "inbound_now_30d": derived.get("inbound_now_30d"),
        "inbound_prior_30d": derived.get("inbound_prior_30d"),
        "distinct_engaged_contacts": derived.get("distinct_engaged_contacts"),
    }
    # explicit per-signal input bundles (also handed to the analyst prompt)
    facts["coverage_gap_input"] = {
        "active_talent": facts["active_talent"],
        "talent_baseline": facts["talent_baseline"],
    }
    facts["evidence_ids"] = {
        f"fact:{k}" for k, v in facts.items() if not isinstance(v, dict) and v is not None
    }
    return facts


def _days_since(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    if isinstance(value, datetime):
        ref = value if value.tzinfo else value.replace(tzinfo=UTC)
        return (datetime.now(UTC) - ref).days
    # plain date
    try:
        return (datetime.now(UTC).date() - value).days
    except TypeError:
        return None


async def _account_derived(conn, account_id: str) -> dict:
    """Compute the deterministic derived inputs for an account (DB)."""
    cur = conn.cursor(row_factory=dict_row)

    async def scalar(sql: str, params: list) -> Any:
        row = await (await cur.execute(sql, params)).fetchone()
        return next(iter(row.values())) if row else None

    inbound_now = await scalar(
        "SELECT count(*) n FROM pulse.inbox_emails WHERE account_id=%s "
        "AND received_at > now() - interval '30 days'",
        [account_id],
    )
    inbound_prior = await scalar(
        "SELECT count(*) n FROM pulse.inbox_emails WHERE account_id=%s "
        "AND received_at BETWEEN now() - interval '60 days' AND now() - interval '30 days'",
        [account_id],
    )
    distinct_contacts = await scalar(
        "SELECT count(DISTINCT from_email) n FROM pulse.inbox_emails WHERE account_id=%s "
        "AND received_at > now() - interval '90 days'",
        [account_id],
    )
    departures_30d = await scalar(
        "SELECT count(*) n FROM pulse.associate_stage_history WHERE account_id=%s "
        "AND stage IN ('Terminated','Replaced','Downsell') "
        "AND observed_at > now() - interval '30 days'",
        [account_id],
    )
    onboarding_30d = await scalar(
        "SELECT count(*) n FROM pulse.associate_stage_history WHERE account_id=%s "
        "AND stage IN ('Onboarding','Selected') "
        "AND observed_at > now() - interval '30 days'",
        [account_id],
    )
    baseline = await scalar(
        "SELECT count(*) n FROM pulse.sf_associates WHERE account_id=%s "
        "AND stage IN ('Active','Onboarding','Selected')",
        [account_id],
    )
    return {
        "inbound_now_30d": inbound_now or 0,
        "inbound_prior_30d": inbound_prior or 0,
        "distinct_engaged_contacts": distinct_contacts,
        "departures_30d": departures_30d or 0,
        "onboarding_30d": onboarding_30d or 0,
        "talent_baseline": baseline or 0,
    }


async def _account_snippets(conn, account_id: str) -> list[dict]:
    """A bounded set of labeled, timestamped snippets (recent emails)."""
    cur = conn.cursor(row_factory=dict_row)
    rows = await (
        await cur.execute(
            "SELECT email_id, subject, body, received_at, sender_kind "
            "FROM pulse.inbox_emails WHERE account_id=%s "
            "ORDER BY received_at DESC LIMIT %s",
            [account_id, _SNIPPET_CAP],
        )
    ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": f"email:{r['email_id']}",
                "source": f"{r['sender_kind']} email",
                "date": r["received_at"].isoformat() if r["received_at"] else None,
                "text": f"{r['subject'] or ''} — {(r['body'] or '')[:300]}",
            }
        )
    return out


async def build_account_pack(account_id: str) -> dict | None:
    """Assemble the full Evidence Pack for one account."""
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        row = await (
            await conn.execute(
                "SELECT account_id, name, tier, active_talent, churn_probability, "
                "last_ebr, rm_name, owner_id FROM pulse.sf_accounts WHERE account_id=%s",
                [account_id],
            )
        ).fetchone()
        if not row:
            return None
        derived = await _account_derived(conn, account_id)
        derived["days_since_ebr"] = _days_since(row.get("last_ebr"))
        derived["max_days_in_onboarding"] = None  # needs stage-entry history (sparse)
        derived["reply_latency_now_h"] = None  # populated once reply data accrues
        derived["reply_latency_prior_h"] = None
        snippets = await _account_snippets(conn, account_id)

    facts = shape_account_facts(dict(row), **derived)
    evidence_ids = set(facts["evidence_ids"]) | {s["id"] for s in snippets}
    return {
        "entity_type": "account",
        "entity_id": account_id,
        "tier": row.get("tier"),
        "rm_id": row.get("owner_id"),
        "facts": facts,
        "evidence_ids": evidence_ids,
        "snippets": snippets,
    }
