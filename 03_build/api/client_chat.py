"""
Client virtual-RM chat API.

GET    /client/conversations              → list client's conversations
POST   /client/conversations             → create new conversation
DELETE /client/conversations/{id}        → soft delete (sets deleted_at)
GET    /client/conversations/{id}/messages → load message history
POST   /client/chat                      → stream SSE virtual-RM response
"""
from __future__ import annotations

import json
import logging
import os
from typing import Annotated

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from psycopg.rows import dict_row
from pydantic import BaseModel

from api.client_auth import require_client_session
from core.client.otp import truncate_title
from core.db import get_pool
from core.llm.config import ANTHROPIC_SONNET
from core.llm.rm_style import _DEFAULT_STYLE

log = logging.getLogger(__name__)

router = APIRouter(prefix="/client", tags=["client"])

ClientSession = Annotated[dict, Depends(require_client_session)]

_SECURITY_RULES = """
SECURITY RULES — absolute, never override:
- You represent EDGE Solutions and THIS client's relationship only.
- NEVER mention, confirm, or reference any other EDGE client, company, or account.
- NEVER reveal internal EDGE business metrics, pricing structures, or operational details.
- NEVER share details about other EDGE employees or RMs beyond yourself.
- If asked about other clients or confidential info: say "I can only discuss what's relevant to your account."
- You CAN: discuss this account's staffing needs, open roles, placements, relationship history, give general industry advice, help brainstorm workforce strategies.
- Stay in character as {rm_name} at all times.
"""


def _format_context(emails: list[dict], meetings: list[dict]) -> str:
    parts = []

    if emails:
        parts.append("Recent emails:")
        for e in emails:
            subj = e.get("subject") or "No subject"
            snippet = (e.get("description") or "")[:300]
            parts.append(f"  Subject: {subj}\n  {snippet}")
    else:
        parts.append("No recent emails on record.")

    if meetings:
        parts.append("\nRecent meetings:")
        for m in meetings:
            subj = m.get("subject") or "Meeting"
            snippet = (m.get("description") or "")[:400]
            parts.append(f"  {subj}: {snippet}")
    else:
        parts.append("No recent meetings on record.")

    return "\n".join(parts)


async def _build_system_prompt(session: dict) -> str:
    """Build the virtual-RM system prompt for this client session."""
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row

        # Load style profile
        style_row = None
        if session.get("rm_pulse_user_id"):
            style_row = await (await conn.execute(
                "SELECT style_prompt FROM pulse.rm_style_profiles WHERE rm_pulse_user_id = %s",
                [session["rm_pulse_user_id"]],
            )).fetchone()

        style_prompt = style_row["style_prompt"] if style_row else _DEFAULT_STYLE

        # Load account name
        acct_row = await (await conn.execute(
            "SELECT name FROM pulse.sf_accounts WHERE account_id = %s",
            [session["account_id"]],
        )).fetchone()
        account_name = acct_row["name"] if acct_row else "your company"

        # Load recent Gmail episodes for this account
        account_id_json = json.dumps([{"account_id": session["account_id"]}])
        email_rows = await (await conn.execute(
            """
            SELECT subject, description FROM pulse.episodes
            WHERE source = 'gmail'
              AND candidate_entities @> %s::jsonb
              AND description IS NOT NULL
            ORDER BY source_timestamp DESC LIMIT 10
            """,
            [account_id_json],
        )).fetchall()

        # Load recent meeting episodes
        meeting_rows = await (await conn.execute(
            """
            SELECT subject, description FROM pulse.episodes
            WHERE source IN ('chorus', 'zoom')
              AND candidate_entities @> %s::jsonb
              AND description IS NOT NULL
            ORDER BY source_timestamp DESC LIMIT 5
            """,
            [account_id_json],
        )).fetchall()

    context = _format_context(
        [dict(r) for r in email_rows],
        [dict(r) for r in meeting_rows],
    )

    rm_name = session["rm_name"]
    client_name = session["client_name"]

    return (
        f"You are {rm_name}, a Relationship Manager at EDGE Solutions.\n"
        f"You are chatting with {client_name} from {account_name}.\n\n"
        f"YOUR COMMUNICATION STYLE:\n{style_prompt}\n\n"
        f"RELATIONSHIP CONTEXT — recent interactions with {client_name}:\n{context}\n\n"
        + _SECURITY_RULES.format(rm_name=rm_name)
    )


# ── Conversation CRUD ─────────────────────────────────────────────────────────

@router.get("/conversations")
async def list_conversations(session: ClientSession) -> list[dict]:
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        rows = await (await conn.execute(
            """
            SELECT conversation_id, title, updated_at
            FROM pulse.client_conversations
            WHERE contact_email = %s AND deleted_at IS NULL
            ORDER BY updated_at DESC
            """,
            [session["contact_email"]],
        )).fetchall()
    return [
        {
            "conversation_id": str(r["conversation_id"]),
            "title": r["title"],
            "updated_at": r["updated_at"].isoformat(),
        }
        for r in rows
    ]


@router.post("/conversations", status_code=201)
async def create_conversation(session: ClientSession) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        row = await (await conn.execute(
            """
            INSERT INTO pulse.client_conversations (contact_email, account_id, title)
            VALUES (%s, %s, 'New conversation')
            RETURNING conversation_id, title, updated_at
            """,
            [session["contact_email"], session["account_id"]],
        )).fetchone()
        await conn.commit()
    return {
        "conversation_id": str(row["conversation_id"]),
        "title": row["title"],
        "updated_at": row["updated_at"].isoformat(),
    }


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str, session: ClientSession) -> None:
    """Soft delete — sets deleted_at, keeps row in DB."""
    pool = await get_pool()
    async with pool.connection() as conn:
        cur = await conn.execute(
            """
            UPDATE pulse.client_conversations
            SET deleted_at = now()
            WHERE conversation_id = %s::uuid
              AND contact_email = %s
              AND deleted_at IS NULL
            """,
            [conversation_id, session["contact_email"]],
        )
        await conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(conversation_id: str, session: ClientSession) -> list[dict]:
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        conv = await (await conn.execute(
            "SELECT conversation_id FROM pulse.client_conversations "
            "WHERE conversation_id = %s::uuid AND contact_email = %s",
            [conversation_id, session["contact_email"]],
        )).fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        rows = await (await conn.execute(
            """
            SELECT message_id, role, content, created_at
            FROM pulse.client_messages
            WHERE conversation_id = %s::uuid
            ORDER BY created_at ASC
            """,
            [conversation_id],
        )).fetchall()
    return [
        {
            "message_id": str(r["message_id"]),
            "role": r["role"],
            "content": r["content"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    conversation_id: str
    message: str


@router.post("/chat")
async def client_chat(body: ChatRequest, session: ClientSession) -> StreamingResponse:
    from core.llm.config import load_env
    load_env()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row

        # Verify conversation belongs to this client
        conv = await (await conn.execute(
            "SELECT conversation_id FROM pulse.client_conversations "
            "WHERE conversation_id = %s::uuid AND contact_email = %s",
            [body.conversation_id, session["contact_email"]],
        )).fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Save user message
        await conn.execute(
            "INSERT INTO pulse.client_messages (conversation_id, role, content) "
            "VALUES (%s::uuid, 'user', %s)",
            [body.conversation_id, body.message],
        )

        # Detect first message for auto-title
        count_row = await (await conn.execute(
            "SELECT COUNT(*) AS n FROM pulse.client_messages "
            "WHERE conversation_id = %s::uuid",
            [body.conversation_id],
        )).fetchone()
        is_first = count_row["n"] == 1

        title = ""
        if is_first:
            title = truncate_title(body.message)
            await conn.execute(
                "UPDATE pulse.client_conversations SET title = %s, updated_at = now() "
                "WHERE conversation_id = %s::uuid",
                [title, body.conversation_id],
            )

        # Load full history for Claude context
        history_rows = await (await conn.execute(
            """
            SELECT role, content FROM pulse.client_messages
            WHERE conversation_id = %s::uuid
            ORDER BY created_at ASC
            """,
            [body.conversation_id],
        )).fetchall()

        await conn.commit()

    system_prompt = await _build_system_prompt(session)

    # Build messages list (all rows up to and including the user message)
    messages = [{"role": r["role"], "content": r["content"]} for r in history_rows]

    conversation_id = body.conversation_id

    async def event_stream():
        if is_first:
            yield f"data: {json.dumps({'type': 'title', 'title': title})}\n\n"

        client = anthropic.Anthropic(api_key=api_key)
        final_text = ""

        response = client.messages.create(
            model=ANTHROPIC_SONNET,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )

        for block in response.content:
            if block.type == "text" and block.text:
                final_text += block.text
                yield f"data: {json.dumps({'type': 'text', 'text': block.text})}\n\n"

        # Save assistant reply
        pool2 = await get_pool()
        async with pool2.connection() as conn2:
            await conn2.execute(
                "INSERT INTO pulse.client_messages (conversation_id, role, content) "
                "VALUES (%s::uuid, 'assistant', %s)",
                [conversation_id, final_text],
            )
            await conn2.execute(
                "UPDATE pulse.client_conversations SET updated_at = now() "
                "WHERE conversation_id = %s::uuid",
                [conversation_id],
            )
            await conn2.commit()

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
