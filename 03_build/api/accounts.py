"""
Accounts API — SFDC-backed account list and per-account health.

GET /accounts        → paginated list with composite health, risk, tier, RM, ARR
GET /accounts/{id}   → full health detail with signal vector + themes

Data sources (all read-only per §4.14):
  - Account (Segment__c → tier, Owner → RM)
  - RM_Outreach__c (Customer_Health__c, Churn_Probability__c, EBR_Date__c)
  - Associates__c (Stage='Active' count → active talent → ARR heuristic)
  - Case (risk-tagged → churn signals)

Health normalization:
  Customer_Health__c: Healthy→8.5, Neutral→6.0, At Risk→4.0, Escalated→2.0
  Churn_Probability__c ≥ 0.5 → overrides to churn-signal (score 5.2)
  No data → 5.0

Segment → tier (white-label, §6 rule 1):
  ENT → Strategic | MID-MKT → Growth | SMB / Insurance → Core
"""
from __future__ import annotations

import asyncio
import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.salesforce import SalesforceClient

router = APIRouter(prefix="/accounts", tags=["accounts"])

# ── types ─────────────────────────────────────────────────────────────────────

RiskLevel = Literal["Low", "Medium", "High"]
HealthState = Literal["healthy", "churn-signal", "at-risk"]

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

ARR_PER_TALENT = 10_000  # Phase-1 demo heuristic (§6 rule 31)


class AccountSummary(BaseModel):
    account_id: str
    name: str
    composite_health: float       # 0..10
    risk: RiskLevel
    meeting: str                  # next key event or "No meeting scheduled"
    tier: str                     # Core | Growth | Strategic
    rm_name: str
    active_talent: int
    arr_usd: int                  # active_talent × ARR_PER_TALENT


class SignalAxis(BaseModel):
    label: str
    pct: int  # 0..100


class AccountHealth(AccountSummary):
    positioning: str
    signal_vector: list[SignalAxis]
    themes: list[str]
    churn_probability: float | None
    last_ebr: str | None


class AccountList(BaseModel):
    accounts: list[AccountSummary]
    total: int
    page: int
    page_size: int


# ── helpers ───────────────────────────────────────────────────────────────────

AI_RM_POSITIONING = (
    "Pulse is prioritising evidence, next best action, and stakeholder context. "
    "No auto-send. Every customer-facing move waits for RM approval."
)

SIGNAL_AXES = ["Engagement", "Satisfaction", "Retention safety", "Growth orientation"]


def _vector(score: float) -> list[SignalAxis]:
    return [
        SignalAxis(label=l, pct=max(10, min(100, round(score * 10 - i * 7))))
        for i, l in enumerate(SIGNAL_AXES)
    ]


def _risk(score: float, churn_prob: float | None) -> RiskLevel:
    if churn_prob is not None and churn_prob >= 0.5:
        return "High"
    if score >= 7.0:
        return "Low"
    if score >= 4.5:
        return "Medium"
    return "High"


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


def _fmt_ebr(ebr_date: str | None) -> str:
    if not ebr_date:
        return "No meeting scheduled"
    return f"EBR scheduled {ebr_date}"


def _score_from_outreach(outreach: dict | None) -> tuple[float, float | None]:
    """Return (composite_score, churn_prob) from most recent RM_Outreach record."""
    if not outreach:
        return 5.0, None
    label = outreach.get("Customer_Health__c")
    churn = outreach.get("Churn_Probability__c")
    score = HEALTH_LABEL_TO_SCORE.get(label, 5.0)
    if churn is not None and float(churn) >= 0.5:
        score = min(score, 5.2)  # churn signal caps health
    return score, (float(churn) if churn is not None else None)


def _get_sf_client() -> SalesforceClient:
    return SalesforceClient()


# ── data fetchers ─────────────────────────────────────────────────────────────

async def _fetch_accounts_bulk(client: SalesforceClient) -> list[dict]:
    return await client.query_all(
        "SELECT Id, Name, Segment__c, Type, OwnerId, Owner.Name "
        "FROM Account WHERE Type = 'Client' ORDER BY Name"
    )


async def _fetch_outreach_by_account(client: SalesforceClient) -> dict[str, dict]:
    """Latest RM_Outreach__c per account, keyed by Account__c Id."""
    rows = await client.query_all(
        "SELECT Id, Account__c, Customer_Health__c, Churn_Probability__c, "
        "EBR_Date__c, LastModifiedDate "
        "FROM RM_Outreach__c WHERE Account__c != null "
        "ORDER BY LastModifiedDate DESC"
    )
    latest: dict[str, dict] = {}
    for row in rows:
        acct_id = row.get("Account__c")
        if acct_id and acct_id not in latest:
            latest[acct_id] = row
    return latest


async def _fetch_talent_counts(client: SalesforceClient) -> dict[str, int]:
    """Active Associates__c count per account, keyed by Account__c Id."""
    rows = await client.query_all(
        "SELECT Account__c, COUNT(Id) cnt FROM Associates__c "
        "WHERE Stage__c = 'Active' AND Account__c != null "
        "GROUP BY Account__c"
    )
    return {r["Account__c"]: int(r.get("cnt") or 0) for r in rows}


async def _fetch_open_cases(client: SalesforceClient) -> set[str]:
    """Account Ids with at least one open risk-tagged Case."""
    rows = await client.query_all(
        "SELECT AccountId FROM Case "
        "WHERE IsClosed = false AND AccountId != null AND Categories__c != null"
    )
    return {r["AccountId"] for r in rows}


# ── routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=AccountList)
async def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    tier: str | None = Query(None),
    rm_id: str | None = Query(None),
) -> AccountList:
    client = _get_sf_client()

    accounts, outreach_map, talent_counts, open_cases = await asyncio.gather(
        _fetch_accounts_bulk(client),
        _fetch_outreach_by_account(client),
        _fetch_talent_counts(client),
        _fetch_open_cases(client),
    )

    summaries: list[AccountSummary] = []
    for acct in accounts:
        acct_id = acct["Id"]
        outreach = outreach_map.get(acct_id)
        score, churn_prob = _score_from_outreach(outreach)
        active_talent = talent_counts.get(acct_id, 0)
        segment = acct.get("Segment__c")
        acct_tier = SEGMENT_TO_TIER.get(segment, "Core")
        owner = acct.get("Owner") or {}
        owner_name = owner.get("Name", "") if isinstance(owner, dict) else ""

        # Optional filters
        if tier and acct_tier != tier:
            continue
        if rm_id and acct.get("OwnerId") != rm_id:
            continue

        summaries.append(AccountSummary(
            account_id=acct_id,
            name=acct["Name"],
            composite_health=round(score, 1),
            risk=_risk(score, churn_prob),
            meeting=_fmt_ebr(outreach.get("EBR_Date__c") if outreach else None),
            tier=acct_tier,
            rm_name=owner_name,
            active_talent=active_talent,
            arr_usd=active_talent * ARR_PER_TALENT,
        ))

    total = len(summaries)
    start = (page - 1) * page_size
    page_items = summaries[start: start + page_size]

    return AccountList(accounts=page_items, total=total, page=page, page_size=page_size)


@router.get("/{account_id}", response_model=AccountHealth)
async def get_account_health(account_id: str) -> AccountHealth:
    client = _get_sf_client()

    acct_rows, outreach_rows, talent_count_rows, case_rows = await asyncio.gather(
        client.query(
            f"SELECT Id, Name, Segment__c, Type, OwnerId, Owner.Name "
            f"FROM Account WHERE Id = '{account_id}' LIMIT 1"
        ),
        client.query(
            f"SELECT Id, Customer_Health__c, Churn_Probability__c, EBR_Date__c "
            f"FROM RM_Outreach__c WHERE Account__c = '{account_id}' "
            f"ORDER BY LastModifiedDate DESC LIMIT 1"
        ),
        client.query(
            f"SELECT COUNT(Id) cnt FROM Associates__c "
            f"WHERE Stage__c = 'Active' AND Account__c = '{account_id}'"
        ),
        client.query(
            f"SELECT Id FROM Case "
            f"WHERE IsClosed = false AND AccountId = '{account_id}' LIMIT 1"
        ),
    )

    if not acct_rows:
        raise HTTPException(status_code=404, detail="Account not found")

    acct = acct_rows[0]
    outreach = outreach_rows[0] if outreach_rows else None
    active_talent = int((talent_count_rows[0].get("cnt") or 0) if talent_count_rows else 0)
    has_open_case = len(case_rows) > 0
    score, churn_prob = _score_from_outreach(outreach)
    segment = acct.get("Segment__c")
    acct_tier = SEGMENT_TO_TIER.get(segment, "Core")
    owner = acct.get("Owner") or {}
    owner_name = owner.get("Name", "") if isinstance(owner, dict) else ""

    return AccountHealth(
        account_id=acct["Id"],
        name=acct["Name"],
        composite_health=round(score, 1),
        risk=_risk(score, churn_prob),
        meeting=_fmt_ebr(outreach.get("EBR_Date__c") if outreach else None),
        tier=acct_tier,
        rm_name=owner_name,
        active_talent=active_talent,
        arr_usd=active_talent * ARR_PER_TALENT,
        positioning=AI_RM_POSITIONING,
        signal_vector=_vector(score),
        themes=_themes(score, churn_prob, has_open_case),
        churn_probability=churn_prob,
        last_ebr=outreach.get("EBR_Date__c") if outreach else None,
    )
