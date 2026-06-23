"""
Salesforce → Postgres account sync.

pull_and_upsert() fetches every Client account from the Edge SF org in parallel,
computes composite health + derived fields, then bulk-upserts into pulse.sf_accounts.

Called at:
  - FastAPI startup (first run, cold cache)
  - Every 12 hours via the background scheduler in api/main.py

Safe to call concurrently — Postgres ON CONFLICT DO UPDATE is atomic per row.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime

from core.db import get_pool
from core.salesforce import SalesforceClient

log = logging.getLogger(__name__)

# ── constants (mirrors api/accounts.py) ──────────────────────────────────────

SEGMENT_TO_TIER: dict[str | None, str] = {
    "ENT": "Strategic",
    "MID-MKT": "Growth",
    "SMB": "Core",
    "Insurance": "Core",
    None: "Core",
}

HEALTH_LABEL_TO_SCORE: dict[str | None, float] = {
    "Healthy": 8.5,
    "Neutral": 6.0,
    "At Risk": 4.0,
    "Escalated": 2.0,
    None: 5.0,
}

ARR_PER_TALENT = 10_000
SIGNAL_AXES = ["Engagement", "Satisfaction", "Retention safety", "Growth orientation"]


# ── derived field helpers ─────────────────────────────────────────────────────


def _score(outreach: dict | None) -> tuple[float, float | None]:
    if not outreach:
        return 5.0, None
    label = outreach.get("Customer_Health__c")
    churn = outreach.get("Churn_Probability__c")
    score = HEALTH_LABEL_TO_SCORE.get(label, 5.0)
    churn_f = float(churn) if churn is not None else None
    if churn_f is not None and churn_f >= 0.5:
        score = min(score, 5.2)
    return score, churn_f


def _risk(score: float, churn_prob: float | None) -> str:
    if churn_prob is not None and churn_prob >= 0.5:
        return "High"
    if score >= 7.0:
        return "Low"
    if score >= 4.5:
        return "Medium"
    return "High"


def _vector(score: float) -> list[dict]:
    return [
        {"label": label, "pct": max(10, min(100, round(score * 10 - i * 7)))}
        for i, label in enumerate(SIGNAL_AXES)
    ]


def _themes(score: float, churn_prob: float | None, has_open_case: bool) -> list[str]:
    if score >= 7.0:
        return [
            "Strong placement continuity",
            "Positive talent feedback trend",
            "Account engagement stable",
        ]
    if (churn_prob is not None and churn_prob >= 0.5) or score < 5.0:
        themes = ["Churn risk signal detected", "Engagement drop observed"]
        if has_open_case:
            themes.append("<bad>Open escalation case</bad>")
        return themes
    return [
        "<em>Renewal window approaching</em>" if has_open_case else "Account health stable",
        "Monitor engagement cadence",
    ]


# ── SF fetchers (same queries as api/accounts.py) ────────────────────────────


async def _fetch_all(
    client: SalesforceClient,
) -> tuple[list[dict], dict[str, dict], dict[str, int], set[str]]:
    accounts, outreach_rows, talent_rows, case_rows = await asyncio.gather(
        client.query_all(
            "SELECT Id, Name, Segment__c, Type, OwnerId, Owner.Name, "
            "Owner.IsActive, Owner.Manager.Name "
            "FROM Account WHERE Type = 'Client' ORDER BY Name"
        ),
        client.query_all(
            "SELECT Id, Account__c, Customer_Health__c, Churn_Probability__c, "
            "EBR_Date__c, LastModifiedDate "
            "FROM RM_Outreach__c WHERE Account__c != null "
            "ORDER BY LastModifiedDate DESC"
        ),
        client.query_all(
            "SELECT Account__c, COUNT(Id) cnt FROM Associates__c "
            "WHERE Stage__c = 'Active' AND Account__c != null "
            "GROUP BY Account__c"
        ),
        client.query_all(
            "SELECT AccountId FROM Case "
            "WHERE IsClosed = false AND AccountId != null AND Categories__c != null"
        ),
    )

    # Build lookup maps
    outreach_map: dict[str, dict] = {}
    for row in outreach_rows:
        aid = row.get("Account__c")
        if aid and aid not in outreach_map:
            outreach_map[aid] = row

    talent_map = {r["Account__c"]: int(r.get("cnt") or 0) for r in talent_rows}
    open_cases = {r["AccountId"] for r in case_rows}

    return accounts, outreach_map, talent_map, open_cases


# ── upsert ────────────────────────────────────────────────────────────────────

UPSERT_SQL = """
INSERT INTO pulse.sf_accounts (
    account_id, name, segment, tier, owner_id, rm_name,
    active_talent, arr_usd, composite_health, risk,
    customer_health, churn_probability, last_ebr, has_open_case,
    signal_vector, themes, synced_at, rm_is_active, rm_manager_name
) VALUES (
    %(account_id)s, %(name)s, %(segment)s, %(tier)s, %(owner_id)s, %(rm_name)s,
    %(active_talent)s, %(arr_usd)s, %(composite_health)s, %(risk)s,
    %(customer_health)s, %(churn_probability)s, %(last_ebr)s, %(has_open_case)s,
    %(signal_vector)s, %(themes)s, %(synced_at)s, %(rm_is_active)s, %(rm_manager_name)s
)
ON CONFLICT (account_id) DO UPDATE SET
    name              = EXCLUDED.name,
    segment           = EXCLUDED.segment,
    tier              = EXCLUDED.tier,
    owner_id          = EXCLUDED.owner_id,
    rm_name           = EXCLUDED.rm_name,
    active_talent     = EXCLUDED.active_talent,
    arr_usd           = EXCLUDED.arr_usd,
    composite_health  = EXCLUDED.composite_health,
    risk              = EXCLUDED.risk,
    customer_health   = EXCLUDED.customer_health,
    churn_probability = EXCLUDED.churn_probability,
    last_ebr          = EXCLUDED.last_ebr,
    has_open_case     = EXCLUDED.has_open_case,
    signal_vector     = EXCLUDED.signal_vector,
    themes            = EXCLUDED.themes,
    synced_at         = EXCLUDED.synced_at,
    rm_is_active      = EXCLUDED.rm_is_active,
    rm_manager_name   = EXCLUDED.rm_manager_name
"""


async def pull_and_upsert() -> int:
    """Fetch all SF accounts and upsert to pulse.sf_accounts. Returns row count."""
    log.info("SF account sync starting…")
    client = SalesforceClient()

    try:
        accounts, outreach_map, talent_map, open_cases = await _fetch_all(client)
    except Exception as exc:
        log.error("SF fetch failed: %s", exc)
        raise

    now = datetime.now(UTC)
    rows = []
    for acct in accounts:
        acct_id = acct["Id"]
        outreach = outreach_map.get(acct_id)
        score, churn_prob = _score(outreach)
        active_talent = talent_map.get(acct_id, 0)
        has_open_case = acct_id in open_cases
        segment = acct.get("Segment__c")
        tier = SEGMENT_TO_TIER.get(segment, "Core")
        owner = acct.get("Owner") or {}
        rm_name = owner.get("Name", "") if isinstance(owner, dict) else ""
        rm_is_active = owner.get("IsActive") if isinstance(owner, dict) else None
        owner_manager = (owner.get("Manager") or {}) if isinstance(owner, dict) else {}
        rm_manager_name = owner_manager.get("Name") if isinstance(owner_manager, dict) else None

        rows.append(
            {
                "account_id": acct_id,
                "name": acct["Name"],
                "segment": segment,
                "tier": tier,
                "owner_id": acct.get("OwnerId"),
                "rm_name": rm_name,
                "active_talent": active_talent,
                "arr_usd": active_talent * ARR_PER_TALENT,
                "composite_health": round(score, 1),
                "risk": _risk(score, churn_prob),
                "customer_health": outreach.get("Customer_Health__c") if outreach else None,
                "churn_probability": churn_prob,
                "last_ebr": outreach.get("EBR_Date__c") if outreach else None,
                "has_open_case": has_open_case,
                "signal_vector": json.dumps(_vector(score)),
                "themes": json.dumps(_themes(score, churn_prob, has_open_case)),
                "synced_at": now,
                "rm_is_active": rm_is_active,
                "rm_manager_name": rm_manager_name,
            }
        )

    if not rows:
        log.warning("SF sync: no accounts returned from Salesforce.")
        return 0

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(UPSERT_SQL, rows)
        await conn.commit()

    log.info("SF account sync complete — %d accounts upserted.", len(rows))
    return len(rows)


# ── Contacts sync ─────────────────────────────────────────────────────────────

_CONTACTS_SOQL = """
    SELECT Id, AccountId, Name, Email, Phone, Title
    FROM Contact
    WHERE AccountId != null AND Email != null
"""

_CONTACTS_UPSERT_SQL = """
INSERT INTO pulse.sf_contacts (contact_id, account_id, name, email, phone, title, synced_at)
VALUES (%(contact_id)s, %(account_id)s, %(name)s, %(email)s, %(phone)s, %(title)s, %(synced_at)s)
ON CONFLICT (contact_id) DO UPDATE SET
    account_id = EXCLUDED.account_id,
    name       = EXCLUDED.name,
    email      = EXCLUDED.email,
    phone      = EXCLUDED.phone,
    title      = EXCLUDED.title,
    synced_at  = EXCLUDED.synced_at
"""


async def pull_and_upsert_contacts() -> int:
    """Fetch all SF contacts with emails and upsert to pulse.sf_contacts. Returns row count."""
    log.info("SF contact sync starting…")
    client = SalesforceClient()
    try:
        contacts = await client.query_all(_CONTACTS_SOQL)
    except Exception as exc:
        log.error("SF contact fetch failed: %s", exc)
        raise

    if not contacts:
        log.warning("SF contact sync: no contacts returned.")
        return 0

    now = datetime.now(UTC)
    rows = [
        {
            "contact_id": c["Id"],
            "account_id": c["AccountId"],
            "name": c.get("Name"),
            "email": (c.get("Email") or "").lower().strip() or None,
            "phone": c.get("Phone"),
            "title": c.get("Title"),
            "synced_at": now,
        }
        for c in contacts
        if c.get("AccountId") and c.get("Email")
    ]

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(_CONTACTS_UPSERT_SQL, rows)
        await conn.commit()

    log.info("SF contact sync complete — %d contacts upserted.", len(rows))
    return len(rows)


# ── Associates (talent) sync ──────────────────────────────────────────────────

_ASSOCIATES_SOQL = """
    SELECT Id, Name, Account__c, Email__c, Stage__c
    FROM Associates__c
    WHERE Account__c != null AND Email__c != null
"""

_ASSOCIATES_UPSERT_SQL = """
INSERT INTO pulse.sf_associates (associate_id, account_id, name, email, stage, synced_at)
VALUES (%(associate_id)s, %(account_id)s, %(name)s, %(email)s, %(stage)s, %(synced_at)s)
ON CONFLICT (associate_id) DO UPDATE SET
    account_id = EXCLUDED.account_id,
    name       = EXCLUDED.name,
    email      = EXCLUDED.email,
    stage      = EXCLUDED.stage,
    synced_at  = EXCLUDED.synced_at
"""


async def pull_and_upsert_associates() -> int:
    """Fetch all SF associates (talent) with emails and upsert to pulse.sf_associates.

    These power the inbox's talent-email detection: an email from a talent maps to
    their Account__c, and thence to the RM who owns that account.
    """
    log.info("SF associate sync starting…")
    client = SalesforceClient()
    try:
        associates = await client.query_all(_ASSOCIATES_SOQL)
    except Exception as exc:
        log.error("SF associate fetch failed: %s", exc)
        raise

    if not associates:
        log.warning("SF associate sync: no associates returned.")
        return 0

    now = datetime.now(UTC)
    rows = [
        {
            "associate_id": a["Id"],
            "account_id": a["Account__c"],
            "name": a.get("Name"),
            "email": (a.get("Email__c") or "").lower().strip() or None,
            "stage": a.get("Stage__c"),
            "synced_at": now,
        }
        for a in associates
        if a.get("Account__c") and a.get("Email__c")
    ]

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(_ASSOCIATES_UPSERT_SQL, rows)
        await conn.commit()

    log.info("SF associate sync complete — %d associates upserted.", len(rows))
    return len(rows)
