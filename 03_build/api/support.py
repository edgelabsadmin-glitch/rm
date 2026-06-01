"""
Support chat API — AI assistant with Salesforce tool use.

POST /support/chat  → streams SSE text/event-stream
Body: { message: str, history: [{role, content}] }

The assistant has one tool: query_salesforce(soql) which runs any read-only
SOQL against the Edge org. All DML keywords are blocked at validation.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import anthropic
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.llm.config import ANTHROPIC_SONNET, load_env
from core.salesforce import SalesforceClient

router = APIRouter(prefix="/support", tags=["support"])

load_env()

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
        # Return compact JSON — Claude parses it well
        return json.dumps(rows[:50], default=str)  # cap at 50 rows
    except Exception as exc:
        return f"Query error: {exc}"


# ── Request model ─────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []


# ── Streaming route ───────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(body: ChatRequest) -> StreamingResponse:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    # Build message history
    messages: list[dict[str, Any]] = [
        {"role": m.role, "content": m.content}
        for m in body.history
        if m.role in ("user", "assistant")
    ]
    messages.append({"role": "user", "content": body.message})

    async def event_stream():
        client = anthropic.Anthropic(api_key=api_key)

        # Agentic loop: Claude may call query_salesforce multiple times
        while True:
            response = client.messages.create(
                model=ANTHROPIC_SONNET,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=[TOOL_DEF],
                messages=messages,
            )

            # Stream any text content back to the client immediately
            for block in response.content:
                if block.type == "text" and block.text:
                    # SSE format
                    yield f"data: {json.dumps({'type': 'text', 'text': block.text})}\n\n"

            # If the model wants to call a tool, execute it and continue
            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        # Stream a "thinking" status so UI shows activity
                        yield f"data: {json.dumps({'type': 'tool', 'name': block.name, 'input': block.input})}\n\n"

                        result = await _run_tool(block.input.get("soql", ""))
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                # Append assistant turn + tool results and loop
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                # end_turn — done
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")
