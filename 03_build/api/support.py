"""
Support chat API — AI assistant with Salesforce tool use.

POST /support/chat                         → streams SSE text/event-stream
GET  /support/conversations                → list user's conversations
POST /support/conversations                → create a new conversation
DELETE /support/conversations/{id}         → delete conversation + messages
GET  /support/conversations/{id}/messages  → load messages for a conversation

Body for /support/chat: { conversation_id: str, message: str }
"""
from __future__ import annotations

import json
import os
import re
from typing import Annotated, Any

import anthropic
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from psycopg.rows import dict_row

from core.db import get_pool
from core.llm.config import ANTHROPIC_SONNET, load_env
from core.salesforce import SalesforceClient

router = APIRouter(prefix="/support", tags=["support"])

load_env()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _truncate_title(text: str) -> str:
    return text.strip()[:60]


# ── Auth dependency ───────────────────────────────────────────────────────────

async def require_user_id(
    x_user_id: str | None = Header(default=None),
) -> str:
    if not x_user_id:
        raise HTTPException(status_code=400, detail="X-User-Id header required")
    return x_user_id


# ── Response models ───────────────────────────────────────────────────────────

class ConversationOut(BaseModel):
    conversation_id: str
    title: str
    updated_at: str


class MessageOut(BaseModel):
    message_id: str
    role: str
    content: str
    tool_calls: list[dict] | None
    created_at: str


# ── Salesforce schema context ─────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the Edge Pulse Support AI — a helpful assistant for the Edge Solutions team.
You have live read-only access to Edge's Salesforce org and can answer questions about accounts, associates, health data, outreach records, and opportunities.

KEY SALESFORCE OBJECTS (use exact API names in SOQL):
- Account           Id, Name, Segment__c (ENT/MID-MKT/SMB/Insurance), OwnerId, Owner.Name, Type
- Associates__c     Id, Name, Account__c, Stage__c ('Active'|'Inactive'|others)
- RM_Outreach__c    Id, Account__c, Customer_Health__c, Churn_Probability__c, EBR_Date__c, Description__c, LastModifiedDate
- Opportunity       Id, Name, AccountId, StageName, CloseDate, Amount, IsClosed, Type
- Case              Id, AccountId, IsClosed, Categories__c, Subject, CreatedDate

SEGMENT → TIER MAPPING: ENT=Strategic, MID-MKT=Growth, SMB/Insurance=Core

RULES:
- Always use query_salesforce to get real data before answering quantitative questions.
- For counts use COUNT(Id) with GROUP BY or aggregate queries.
- Keep answers concise — 2–4 sentences max unless the user asks for detail.
- Format numbers with commas. Use $ for currency. Use % for percentages.
- If a query returns no data, say so honestly.
- Never fabricate numbers — only report what Salesforce returns.
- You only know about Edge Solutions data. Politely decline off-topic requests."""

TOOL_DEF = {
    "name": "query_salesforce",
    "description": "Run a read-only SOQL query against the Edge Solutions Salesforce org and return the results.",
    "input_schema": {
        "type": "object",
        "properties": {
            "soql": {
                "type": "string",
                "description": "A valid SOQL SELECT statement. Only SELECT queries are permitted.",
            }
        },
        "required": ["soql"],
    },
}

# ── Safety ────────────────────────────────────────────────────────────────────

_DML = re.compile(r"\b(INSERT|UPDATE|DELETE|UPSERT|MERGE|UNDELETE|CREATE|DROP|ALTER)\b", re.I)


def _validate_soql(soql: str) -> None:
    if _DML.search(soql):
        raise ValueError("Only SELECT queries are permitted.")
    if not soql.strip().upper().startswith("SELECT"):
        raise ValueError("Query must start with SELECT.")


# ── Salesforce tool execution ─────────────────────────────────────────────────

async def _run_tool(soql: str) -> str:
    try:
        _validate_soql(soql)
        client = SalesforceClient()
        rows = await client.query(soql)
        if not rows:
            return "No records found."
        return json.dumps(rows[:50], default=str)
    except Exception as exc:
        return f"Query error: {exc}"


# ── Conversation endpoints ────────────────────────────────────────────────────

@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    user_id: Annotated[str, Depends(require_user_id)],
) -> list[ConversationOut]:
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        rows = await (await conn.execute(
            """
            SELECT conversation_id, title, updated_at
            FROM pulse.support_conversations
            WHERE user_id = %s
            ORDER BY updated_at DESC
            """,
            [user_id],
        )).fetchall()
    return [
        ConversationOut(
            conversation_id=str(r["conversation_id"]),
            title=r["title"],
            updated_at=r["updated_at"].isoformat(),
        )
        for r in rows
    ]


@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(
    user_id: Annotated[str, Depends(require_user_id)],
) -> ConversationOut:
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        row = await (await conn.execute(
            """
            INSERT INTO pulse.support_conversations (user_id, title)
            VALUES (%s, 'New conversation')
            RETURNING conversation_id, title, updated_at
            """,
            [user_id],
        )).fetchone()
        await conn.commit()
    return ConversationOut(
        conversation_id=str(row["conversation_id"]),
        title=row["title"],
        updated_at=row["updated_at"].isoformat(),
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    user_id: Annotated[str, Depends(require_user_id)],
) -> None:
    pool = await get_pool()
    async with pool.connection() as conn:
        cur = await conn.execute(
            """
            DELETE FROM pulse.support_conversations
            WHERE conversation_id = %s AND user_id = %s
            """,
            [conversation_id, user_id],
        )
        await conn.commit()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: str,
    user_id: Annotated[str, Depends(require_user_id)],
) -> list[MessageOut]:
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        conv = await (await conn.execute(
            "SELECT conversation_id FROM pulse.support_conversations WHERE conversation_id = %s AND user_id = %s",
            [conversation_id, user_id],
        )).fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        rows = await (await conn.execute(
            """
            SELECT message_id, role, content, tool_calls, created_at
            FROM pulse.support_messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
            """,
            [conversation_id],
        )).fetchall()
    return [
        MessageOut(
            message_id=str(r["message_id"]),
            role=r["role"],
            content=r["content"],
            tool_calls=r["tool_calls"],
            created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


# ── Chat request model ────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    conversation_id: str
    message: str


# ── Streaming chat route ──────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    body: ChatRequest,
    user_id: Annotated[str, Depends(require_user_id)],
) -> StreamingResponse:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        # Verify conversation belongs to this user
        conv = await (await conn.execute(
            "SELECT conversation_id FROM pulse.support_conversations WHERE conversation_id = %s AND user_id = %s",
            [body.conversation_id, user_id],
        )).fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Save user message
        await conn.execute(
            "INSERT INTO pulse.support_messages (conversation_id, role, content) VALUES (%s, 'user', %s)",
            [body.conversation_id, body.message],
        )

        # Detect first turn (count after saving)
        count_row = await (await conn.execute(
            "SELECT COUNT(*) AS n FROM pulse.support_messages WHERE conversation_id = %s",
            [body.conversation_id],
        )).fetchone()
        is_first_message = count_row["n"] == 1

        title = ""
        if is_first_message:
            title = _truncate_title(body.message)
            await conn.execute(
                "UPDATE pulse.support_conversations SET title = %s, updated_at = now() WHERE conversation_id = %s",
                [title, body.conversation_id],
            )

        # Load full history for Claude context
        history_rows = await (await conn.execute(
            """
            SELECT role, content, tool_calls
            FROM pulse.support_messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
            """,
            [body.conversation_id],
        )).fetchall()
        await conn.commit()

    # Build Claude messages list (exclude the last row = user msg we just saved, re-add below)
    messages: list[dict[str, Any]] = []
    for row in history_rows[:-1]:
        messages.append({"role": row["role"], "content": row["content"]})
    messages.append({"role": "user", "content": body.message})

    conversation_id = body.conversation_id

    async def event_stream():
        if is_first_message:
            yield f"data: {json.dumps({'type': 'title', 'title': title})}\n\n"

        client = anthropic.Anthropic(api_key=api_key)
        final_text = ""
        collected_tool_calls: list[dict] = []

        while True:
            response = client.messages.create(
                model=ANTHROPIC_SONNET,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=[TOOL_DEF],
                messages=messages,
            )

            for block in response.content:
                if block.type == "text" and block.text:
                    final_text += block.text
                    yield f"data: {json.dumps({'type': 'text', 'text': block.text})}\n\n"

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        collected_tool_calls.append({"name": block.name, "input": block.input})
                        yield f"data: {json.dumps({'type': 'tool', 'name': block.name, 'input': block.input})}\n\n"
                        result = await _run_tool(block.input.get("soql", ""))
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                # Save completed assistant reply to DB
                pool2 = await get_pool()
                async with pool2.connection() as conn2:
                    await conn2.execute(
                        """
                        INSERT INTO pulse.support_messages (conversation_id, role, content, tool_calls)
                        VALUES (%s, 'assistant', %s, %s)
                        """,
                        [
                            conversation_id,
                            final_text,
                            json.dumps(collected_tool_calls) if collected_tool_calls else None,
                        ],
                    )
                    await conn2.execute(
                        "UPDATE pulse.support_conversations SET updated_at = now() WHERE conversation_id = %s",
                        [conversation_id],
                    )
                    await conn2.commit()

                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")
