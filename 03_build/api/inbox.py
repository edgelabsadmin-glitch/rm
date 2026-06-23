"""
Inbox API — the logged-in RM's unreplied client emails + reply actions.

GET  /inbox                  → pending rows (summaries) + count
POST /inbox/sync             → force an immediate sync, return refreshed list
GET  /inbox/{id}             → full body + suggested/draft reply
POST /inbox/{id}/draft       → persist the RM's edited draft
POST /inbox/{id}/regenerate  → re-draft with an optional tone
POST /inbox/{id}/reply       → send via Gmail as the RM
POST /inbox/{id}/dismiss     → drop from the queue

Identity comes from the shared require_caller header guard; every query is
scoped to rm_user_id = caller.user_id.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from psycopg.rows import dict_row
from pydantic import BaseModel

from api.actions import Caller, require_caller
from core.db import get_pool
from core.inbox.send import send_reply

router = APIRouter(prefix="/inbox", tags=["inbox"])


class InboxEmailSummary(BaseModel):
    email_id: str
    from_email: str
    from_name: str | None
    subject: str | None
    snippet: str
    received_at: str
    account_id: str | None
    tier: str | None
    risk: str | None
    sender_kind: str
    has_draft: bool


class InboxList(BaseModel):
    emails: list[InboxEmailSummary]
    count: int


class InboxEmailDetail(InboxEmailSummary):
    body: str
    suggested_reply: str | None
    reply_rationale: str | None
    draft_reply: str | None


class DraftBody(BaseModel):
    text: str


class RegenerateBody(BaseModel):
    tone: Literal["formal", "shorter", "warmer"] | None = None


async def _pending_list(rm_user_id: str) -> InboxList:
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        rows = await (
            await conn.execute(
                """
                SELECT i.email_id, i.from_email, i.from_name, i.subject, i.body,
                       i.received_at, i.account_id, i.suggested_reply, i.draft_reply,
                       i.sender_kind, a.tier, a.risk
                FROM pulse.inbox_emails i
                LEFT JOIN pulse.sf_accounts a ON a.account_id = i.account_id
                WHERE i.rm_user_id = %s AND i.reply_state = 'pending'
                ORDER BY
                    CASE a.risk WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END,
                    i.received_at DESC
                """,
                [rm_user_id],
            )
        ).fetchall()
    emails = [
        InboxEmailSummary(
            email_id=str(r["email_id"]),
            from_email=r["from_email"],
            from_name=r["from_name"],
            subject=r["subject"],
            snippet=(r["body"] or "")[:140],
            received_at=r["received_at"].isoformat(),
            account_id=r["account_id"],
            tier=r["tier"],
            risk=r["risk"],
            sender_kind=r["sender_kind"],
            has_draft=bool(r["draft_reply"] or r["suggested_reply"]),
        )
        for r in rows
    ]
    return InboxList(emails=emails, count=len(emails))


@router.get("")
async def list_inbox(caller: Annotated[Caller, Depends(require_caller)]) -> InboxList:
    return await _pending_list(caller.user_id)


@router.post("/sync")
async def force_sync(caller: Annotated[Caller, Depends(require_caller)]) -> InboxList:
    from core.inbox.sync import sync_inbox

    await sync_inbox(caller.user_id)
    return await _pending_list(caller.user_id)


@router.get("/{email_id}")
async def get_inbox_email(
    email_id: str, caller: Annotated[Caller, Depends(require_caller)]
) -> InboxEmailDetail:
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        r = await (
            await conn.execute(
                """
                SELECT i.email_id, i.from_email, i.from_name, i.subject, i.body,
                       i.received_at, i.account_id, i.suggested_reply, i.reply_rationale,
                       i.draft_reply, i.sender_kind, a.tier, a.risk
                FROM pulse.inbox_emails i
                LEFT JOIN pulse.sf_accounts a ON a.account_id = i.account_id
                WHERE i.email_id = %s::uuid AND i.rm_user_id = %s
                """,
                [email_id, caller.user_id],
            )
        ).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="email not found")
    return InboxEmailDetail(
        email_id=str(r["email_id"]),
        from_email=r["from_email"],
        from_name=r["from_name"],
        subject=r["subject"],
        snippet=(r["body"] or "")[:140],
        received_at=r["received_at"].isoformat(),
        account_id=r["account_id"],
        tier=r["tier"],
        risk=r["risk"],
        sender_kind=r["sender_kind"],
        has_draft=bool(r["draft_reply"] or r["suggested_reply"]),
        body=r["body"] or "",
        suggested_reply=r["suggested_reply"],
        reply_rationale=r["reply_rationale"],
        draft_reply=r["draft_reply"],
    )


@router.post("/{email_id}/draft")
async def save_draft(
    email_id: str, body: DraftBody, caller: Annotated[Caller, Depends(require_caller)]
) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        cur = await conn.execute(
            "UPDATE pulse.inbox_emails SET draft_reply = %s "
            "WHERE email_id = %s::uuid AND rm_user_id = %s",
            [body.text, email_id, caller.user_id],
        )
        await conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="email not found")
    return {"saved": True}


@router.post("/{email_id}/regenerate")
async def regenerate(
    email_id: str, body: RegenerateBody, caller: Annotated[Caller, Depends(require_caller)]
) -> dict:
    from core.inbox.reply import generate_reply
    from core.inbox.sync import _load_style

    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        r = await (
            await conn.execute(
                "SELECT i.from_name, i.subject, i.body, a.name AS account_name "
                "FROM pulse.inbox_emails i "
                "LEFT JOIN pulse.sf_accounts a ON a.account_id = i.account_id "
                "WHERE i.email_id = %s::uuid AND i.rm_user_id = %s",
                [email_id, caller.user_id],
            )
        ).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="email not found")

    style = await _load_style(caller.user_id)
    drafted = await generate_reply(
        style_prompt=style,
        account_name=r["account_name"] or "your client",
        from_name=r["from_name"] or "",
        subject=r["subject"] or "",
        body=r["body"] or "",
        tone=body.tone,
    )
    pool2 = await get_pool()
    async with pool2.connection() as conn:
        await conn.execute(
            "UPDATE pulse.inbox_emails SET suggested_reply=%s, reply_rationale=%s, draft_reply=NULL "
            "WHERE email_id=%s::uuid AND rm_user_id=%s",
            [drafted["reply"], drafted["rationale"], email_id, caller.user_id],
        )
        await conn.commit()
    return {"reply": drafted["reply"], "rationale": drafted["rationale"]}


@router.post("/{email_id}/reply")
async def send_inbox_reply(
    email_id: str, body: DraftBody, caller: Annotated[Caller, Depends(require_caller)]
) -> dict:
    sent_id = await send_reply(caller.user_id, email_id, body.text)
    return {"sent_message_id": sent_id}


@router.post("/{email_id}/dismiss")
async def dismiss(email_id: str, caller: Annotated[Caller, Depends(require_caller)]) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        cur = await conn.execute(
            "UPDATE pulse.inbox_emails SET reply_state = 'dismissed' "
            "WHERE email_id = %s::uuid AND rm_user_id = %s",
            [email_id, caller.user_id],
        )
        await conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="email not found")
    return {"dismissed": True}
