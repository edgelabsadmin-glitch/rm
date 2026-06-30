"""
Talent (associate) detail API.

GET /talent/{id}         → profile: stage, account, email, latest analysis priority
GET /talent/{id}/emails  → the associate's own emails (matched by from_email)

(`GET /talent/{id}/matrix` lives in api/analysis.py.) Reads hit Postgres; data is
kept fresh by the Salesforce + inbox background syncs.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from psycopg.rows import dict_row
from pydantic import BaseModel

from core.db import get_pool

router = APIRouter(prefix="/talent", tags=["talent"])


class TalentDetail(BaseModel):
    associate_id: str
    name: str | None
    email: str | None
    stage: str | None
    account_id: str | None
    account_name: str | None
    tier: str | None
    priority: str | None
    priority_color: str | None


@router.get("/{associate_id}", response_model=TalentDetail)
async def get_talent(associate_id: str) -> TalentDetail:
    pool = await get_pool()
    async with pool.connection() as conn:
        cur = conn.cursor(row_factory=dict_row)  # per-cursor only (no pooled-conn leak)
        row = await (
            await cur.execute(
                """
                SELECT a.associate_id, a.name, a.email, a.stage, a.account_id,
                       acc.name AS account_name, acc.tier,
                       m.priority, m.priority_color
                FROM pulse.sf_associates a
                LEFT JOIN pulse.sf_accounts acc ON acc.account_id = a.account_id
                LEFT JOIN LATERAL (
                    SELECT priority, priority_color FROM pulse.entity_matrices
                    WHERE entity_type = 'talent' AND entity_id = a.associate_id
                    ORDER BY analyzed_at DESC LIMIT 1
                ) m ON true
                WHERE a.associate_id = %s
                """,
                [associate_id],
            )
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Talent not found")
    return TalentDetail(
        associate_id=row["associate_id"],
        name=row["name"],
        email=row["email"],
        stage=row["stage"],
        account_id=row["account_id"],
        account_name=row["account_name"],
        tier=row["tier"],
        priority=row["priority"],
        priority_color=row["priority_color"],
    )


class TalentEmail(BaseModel):
    email_id: str
    subject: str | None
    body: str | None
    received_at: str | None


@router.get("/{associate_id}/emails", response_model=list[TalentEmail])
async def list_talent_emails(
    associate_id: str,
    limit: int = Query(25, ge=1, le=100),
) -> list[TalentEmail]:
    """Emails authored by this associate (their own voice), matched on email address."""
    pool = await get_pool()
    async with pool.connection() as conn:
        cur = conn.cursor(row_factory=dict_row)  # per-cursor only (no pooled-conn leak)
        assoc = await (
            await cur.execute(
                "SELECT email FROM pulse.sf_associates WHERE associate_id = %s",
                [associate_id],
            )
        ).fetchone()
        if not assoc or not assoc["email"]:
            return []
        rows = await (
            await cur.execute(
                "SELECT email_id, subject, body, received_at FROM pulse.inbox_emails "
                "WHERE lower(from_email) = lower(%s) ORDER BY received_at DESC LIMIT %s",
                [assoc["email"], limit],
            )
        ).fetchall()
    return [
        TalentEmail(
            email_id=str(r["email_id"]),
            subject=r["subject"],
            body=r["body"],
            received_at=r["received_at"].isoformat() if r["received_at"] else None,
        )
        for r in rows
    ]
