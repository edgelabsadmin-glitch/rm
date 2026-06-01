"""
Accounts API — DB-backed account list and per-account health.

GET /accounts        → paginated list read from pulse.sf_accounts
GET /accounts/{id}   → full health detail from pulse.sf_accounts

Data is kept fresh by the 12-hour background sync (core/salesforce/sync.py).
Direct Salesforce calls are no longer made here; all reads hit Postgres.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from psycopg.rows import dict_row

from core.db import get_pool

router = APIRouter(prefix="/accounts", tags=["accounts"])

# ── types ─────────────────────────────────────────────────────────────────────

RiskLevel = Literal["Low", "Medium", "High"]

AI_RM_POSITIONING = (
    "Pulse is prioritising evidence, next best action, and stakeholder context. "
    "No auto-send. Every customer-facing move waits for RM approval."
)


class AccountSummary(BaseModel):
    account_id: str
    name: str
    composite_health: float
    risk: RiskLevel
    meeting: str
    tier: str
    rm_name: str
    active_talent: int
    arr_usd: int


class SignalAxis(BaseModel):
    label: str
    pct: int


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

def _fmt_ebr(last_ebr: str | None) -> str:
    if not last_ebr:
        return "No meeting scheduled"
    return f"EBR scheduled {last_ebr}"


def _row_to_summary(row: dict) -> AccountSummary:
    return AccountSummary(
        account_id=row["account_id"],
        name=row["name"],
        composite_health=float(row["composite_health"]),
        risk=row["risk"],
        meeting=_fmt_ebr(row.get("last_ebr")),
        tier=row["tier"],
        rm_name=row["rm_name"] or "",
        active_talent=row["active_talent"],
        arr_usd=row["arr_usd"],
    )


def _row_to_health(row: dict) -> AccountHealth:
    sv = row.get("signal_vector") or []
    themes = row.get("themes") or []
    return AccountHealth(
        account_id=row["account_id"],
        name=row["name"],
        composite_health=float(row["composite_health"]),
        risk=row["risk"],
        meeting=_fmt_ebr(row.get("last_ebr")),
        tier=row["tier"],
        rm_name=row["rm_name"] or "",
        active_talent=row["active_talent"],
        arr_usd=row["arr_usd"],
        positioning=AI_RM_POSITIONING,
        signal_vector=[SignalAxis(**s) for s in sv],
        themes=themes,
        churn_probability=float(row["churn_probability"]) if row.get("churn_probability") is not None else None,
        last_ebr=row.get("last_ebr"),
    )


# ── routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=AccountList)
async def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    tier: str | None = Query(None),
    rm_id: str | None = Query(None),
    rm_ids: str | None = Query(None),  # comma-separated SF user IDs (manager team scope)
) -> AccountList:
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row

        # Build WHERE clause using %s placeholders (psycopg3 style)
        conditions = []
        params: list = []
        if tier:
            conditions.append("tier = %s")
            params.append(tier)
        # rm_ids (manager team) takes precedence over rm_id (single RM)
        if rm_ids:
            ids = [i.strip() for i in rm_ids.split(",") if i.strip()]
            if ids:
                placeholders = ", ".join(["%s"] * len(ids))
                conditions.append(f"owner_id IN ({placeholders})")
                params.extend(ids)
        elif rm_id:
            conditions.append("owner_id = %s")
            params.append(rm_id)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        count_row = await (await conn.execute(
            f"SELECT COUNT(*) FROM pulse.sf_accounts {where}",
            params or None,
        )).fetchone()
        total = count_row["count"] if count_row else 0

        offset = (page - 1) * page_size
        rows = await (await conn.execute(
            f"SELECT account_id, name, composite_health, risk, last_ebr, tier, "
            f"rm_name, active_talent, arr_usd "
            f"FROM pulse.sf_accounts {where} "
            f"ORDER BY name "
            f"LIMIT %s OFFSET %s",
            [*params, page_size, offset],
        )).fetchall()

    return AccountList(
        accounts=[_row_to_summary(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{account_id}", response_model=AccountHealth)
async def get_account_health(account_id: str) -> AccountHealth:
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        row = await (await conn.execute(
            "SELECT * FROM pulse.sf_accounts WHERE account_id = %s",
            [account_id],
        )).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Account not found")

    return _row_to_health(row)


