"""
Submit API — RM Outreach creation.

POST /submit/outreach      → creates RM_Outreach__c in Salesforce
GET  /submit/opportunities → lists open Opportunities for a given account
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.salesforce import SalesforceClient

router = APIRouter(prefix="/submit", tags=["submit"])


# ── models ────────────────────────────────────────────────────────────────────


class OpportunityItem(BaseModel):
    opportunity_id: str
    name: str
    stage: str
    close_date: str | None
    amount: float | None


class OutreachCreate(BaseModel):
    # Required
    account_id: str

    # Optional Salesforce lookups
    associate_id: str | None = None

    # Health & risk
    customer_health: str | None = None  # Customer_Health__c picklist
    churn_probability: float | None = None  # 0–100
    expansion_probability: float | None = None  # 0–100
    customer_priority_level: str | None = None  # Customer_Priority_level__c

    # Meeting / EBR
    ebr_date: str | None = None  # YYYY-MM-DD
    description: str | None = None
    ebr_description: str | None = None
    recording_link: str | None = None
    transcript_link: str | None = None

    # Sentiment
    expansion_sentiment: str | None = None
    satisfaction_with_talent: str | None = None
    referral_sentiment: str | None = None
    referral_potential: float | None = None

    # Intelligence
    competitor_analysis: str | None = None
    feedback_primary_category: str | None = None
    structured_feedback_shared: str | None = None  # Structured_feedback_Shared_with_Talent__c


class OutreachCreated(BaseModel):
    record_id: str
    message: str


# ── helpers ───────────────────────────────────────────────────────────────────


def _build_fields(body: OutreachCreate) -> dict[str, Any]:
    """Map request body to Salesforce field names, dropping None values."""
    mapping: dict[str, Any] = {
        "Account__c": body.account_id,
    }
    if body.associate_id:
        mapping["Associate__c"] = body.associate_id
    if body.customer_health is not None:
        mapping["Customer_Health__c"] = body.customer_health
    if body.churn_probability is not None:
        # Salesforce percent field stores 0–100
        mapping["Churn_Probability__c"] = body.churn_probability
    if body.expansion_probability is not None:
        mapping["Expansion_Probability__c"] = body.expansion_probability
    if body.customer_priority_level is not None:
        mapping["Customer_Priority_level__c"] = body.customer_priority_level
    if body.ebr_date is not None:
        mapping["EBR_Date__c"] = body.ebr_date
    if body.description is not None:
        mapping["Description__c"] = body.description
    if body.ebr_description is not None:
        mapping["EBR_Description__c"] = body.ebr_description
    if body.recording_link is not None:
        mapping["Recording_link__c"] = body.recording_link
    if body.transcript_link is not None:
        mapping["Transcript_link__c"] = body.transcript_link
    if body.expansion_sentiment is not None:
        mapping["Expansion_Sentiment__c"] = body.expansion_sentiment
    if body.satisfaction_with_talent is not None:
        mapping["Satisfaction_with_Talent__c"] = body.satisfaction_with_talent
    if body.referral_sentiment is not None:
        mapping["Referral_Sentiment__c"] = body.referral_sentiment
    if body.referral_potential is not None:
        mapping["Referral_Potential__c"] = body.referral_potential
    if body.competitor_analysis is not None:
        mapping["Competitor_Analysis__c"] = body.competitor_analysis
    if body.feedback_primary_category is not None:
        mapping["Feedback_Primary_Category__c"] = body.feedback_primary_category
    if body.structured_feedback_shared is not None:
        mapping["Structured_feedback_Shared_with_Talent__c"] = body.structured_feedback_shared
    return mapping


# ── routes ────────────────────────────────────────────────────────────────────


@router.get("/opportunities", response_model=list[OpportunityItem])
async def list_opportunities(
    q: str | None = Query(default=None, description="Name search"),
    account_id: str | None = Query(default=None, description="Optional account filter"),
) -> list[OpportunityItem]:
    client = SalesforceClient()
    where = "IsClosed = false"
    if account_id:
        where += f" AND AccountId = '{account_id}'"
    if q:
        safe_q = q.replace("'", "\\'")
        where += f" AND Name LIKE '%{safe_q}%'"
    rows = await client.query(
        f"SELECT Id, Name, StageName, CloseDate, Amount, Account.Name "
        f"FROM Opportunity WHERE {where} "
        f"ORDER BY CloseDate ASC NULLS LAST LIMIT 50"
    )
    return [
        OpportunityItem(
            opportunity_id=r["Id"],
            name=r["Name"],
            stage=r.get("StageName", ""),
            close_date=r.get("CloseDate"),
            amount=float(r["Amount"]) if r.get("Amount") is not None else None,
        )
        for r in rows
    ]


@router.post("/outreach", response_model=OutreachCreated, status_code=201)
async def create_outreach(body: OutreachCreate) -> OutreachCreated:
    client = SalesforceClient()

    # Verify account exists
    acct = await client.query(
        f"SELECT Id, Name FROM Account WHERE Id = '{body.account_id}' LIMIT 1"
    )
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")

    fields = _build_fields(body)
    try:
        record_id = await client.create_record("RM_Outreach__c", fields)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return OutreachCreated(
        record_id=record_id,
        message=f"RM Outreach created for {acct[0]['Name']}",
    )
