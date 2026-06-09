# Support Chat History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist support chat conversations per user in PostgreSQL, with a sidebar showing multiple named sessions (auto-titled from first message) that persist across page refreshes.

**Architecture:** Backend owns all history — frontend sends only `{ conversation_id, message }`, backend loads prior messages from DB, streams the Claude response, saves both turns to DB. Frontend shows a conversation sidebar (new chat, switch, delete) and loads messages from the API when switching. The existing SSE streaming pattern is unchanged; only what's sent in the request body changes.

**Tech Stack:** PostgreSQL (psycopg, `pulse` schema), FastAPI (new router endpoints + modified `/support/chat`), React Query (new hooks), React useState for local streaming state.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `03_build/migrations/0011_support_chat.sql` | Create | Two new tables: `support_conversations`, `support_messages` |
| `03_build/tests/test_support_api.py` | Create | Unit tests for `_truncate_title`, `require_user_id` |
| `03_build/api/support.py` | Modify | `require_user_id` dep, 4 new endpoints, modified `/chat` |
| `03_build/front/src/lib/api.ts` | Modify | 4 new API calls, updated `chat` call signature |
| `03_build/front/src/features/support/hooks.ts` | Create | `useConversations()`, `useMessages()` React Query hooks |
| `03_build/front/src/features/support/SupportPage.tsx` | Modify | Sidebar layout, conversation switching, SSE title event |

---

## Task 1: DB Migration

**Files:**
- Create: `03_build/migrations/0011_support_chat.sql`

- [ ] **Step 1: Write the migration**

```sql
-- 03_build/migrations/0011_support_chat.sql
CREATE TABLE IF NOT EXISTS pulse.support_conversations (
    conversation_id  UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          TEXT    NOT NULL,
    title            TEXT    NOT NULL DEFAULT 'New conversation',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_support_conv_user
    ON pulse.support_conversations (user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS pulse.support_messages (
    message_id       UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID    NOT NULL
                             REFERENCES pulse.support_conversations (conversation_id)
                             ON DELETE CASCADE,
    role             TEXT    NOT NULL CHECK (role IN ('user', 'assistant')),
    content          TEXT    NOT NULL,
    tool_calls       JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_support_msg_conv
    ON pulse.support_messages (conversation_id, created_at ASC);
```

- [ ] **Step 2: Apply the migration locally**

Run from `03_build/`:
```bash
python3 -c "
import os, psycopg
from pathlib import Path

env = Path('../.env')
for line in env.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith('#') and '=' in line:
        k, _, v = line.partition('=')
        os.environ.setdefault(k.strip(), v.strip().strip('\'\"'))

sql = Path('migrations/0011_support_chat.sql').read_text()
conn = psycopg.connect(os.environ['DATABASE_URL'])
conn.execute(sql)
conn.commit()
print('Migration 0011 applied.')
conn.close()
"
```

Expected output: `Migration 0011 applied.`

- [ ] **Step 3: Commit**

```bash
git add 03_build/migrations/0011_support_chat.sql
git commit -m "feat: add support_conversations and support_messages tables"
```

---

## Task 2: Backend Unit Tests

**Files:**
- Create: `03_build/tests/test_support_api.py`

- [ ] **Step 1: Write the failing tests**

```python
# 03_build/tests/test_support_api.py
"""
Unit tests for support chat helpers — no DB, no network.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException


def test_truncate_title_long():
    from api.support import _truncate_title
    result = _truncate_title("a" * 100)
    assert result == "a" * 60


def test_truncate_title_short():
    from api.support import _truncate_title
    assert _truncate_title("Hello world") == "Hello world"


def test_truncate_title_strips_whitespace():
    from api.support import _truncate_title
    assert _truncate_title("  hello  ") == "hello"


def test_truncate_title_exactly_60():
    from api.support import _truncate_title
    assert _truncate_title("x" * 60) == "x" * 60


async def test_require_user_id_missing_raises_400():
    from api.support import require_user_id
    with pytest.raises(HTTPException) as exc:
        await require_user_id(x_user_id=None)
    assert exc.value.status_code == 400


async def test_require_user_id_present_returns_id():
    from api.support import require_user_id
    result = await require_user_id(x_user_id="user-123")
    assert result == "user-123"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd 03_build && python3 -m pytest tests/test_support_api.py -v
```

Expected: `ImportError` — `_truncate_title` and `require_user_id` don't exist yet.

- [ ] **Step 3: Commit the test file**

```bash
git add 03_build/tests/test_support_api.py
git commit -m "test: add failing unit tests for support chat helpers"
```

---

## Task 3: Backend — `require_user_id` Dependency + 4 New Endpoints

**Files:**
- Modify: `03_build/api/support.py`

- [ ] **Step 1: Add imports and new models at the top of `support.py`**

Replace the existing imports block (lines 1–19) with:

```python
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

from core.db import get_pool
from core.llm.config import ANTHROPIC_SONNET, load_env
from core.salesforce import SalesforceClient
from psycopg.rows import dict_row
```

- [ ] **Step 2: Add `_truncate_title`, `require_user_id`, and new response models after `load_env()`**

Add after `load_env()` (before `SYSTEM_PROMPT`):

```python
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
```

- [ ] **Step 3: Add the 4 new endpoints after the existing `TOOL_DEF` block**

Add after the `_run_tool` function:

```python
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
        result = await conn.execute(
            """
            DELETE FROM pulse.support_conversations
            WHERE conversation_id = %s AND user_id = %s
            """,
            [conversation_id, user_id],
        )
        await conn.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: str,
    user_id: Annotated[str, Depends(require_user_id)],
) -> list[MessageOut]:
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        # Verify ownership
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
```

- [ ] **Step 4: Run unit tests — should pass now**

```bash
cd 03_build && python3 -m pytest tests/test_support_api.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add 03_build/api/support.py
git commit -m "feat: add support conversation CRUD endpoints and require_user_id dependency"
```

---

## Task 4: Backend — Modify `/support/chat`

**Files:**
- Modify: `03_build/api/support.py`

- [ ] **Step 1: Replace `ChatMessage` and `ChatRequest` models**

Find and replace the existing models block (currently around line 96–103):

```python
# Old — remove these:
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
```

Replace with:

```python
class ChatRequest(BaseModel):
    conversation_id: str
    message: str
```

- [ ] **Step 2: Replace the entire `chat` endpoint**

Find and replace the entire `@router.post("/chat")` function with:

```python
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

        # Count messages to detect first turn
        count_row = await (await conn.execute(
            "SELECT COUNT(*) AS n FROM pulse.support_messages WHERE conversation_id = %s",
            [body.conversation_id],
        )).fetchone()
        is_first_message = count_row["n"] == 1

        # Auto-title on first message
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

    # Build Claude messages list from DB history
    messages: list[dict[str, Any]] = []
    for row in history_rows[:-1]:  # exclude the user message we just saved (added below)
        messages.append({"role": row["role"], "content": row["content"]})
    messages.append({"role": "user", "content": body.message})

    conversation_id = body.conversation_id

    async def event_stream():
        # Emit title on first message
        if is_first_message:
            yield f"data: {json.dumps({'type': 'title', 'title': title})}\n\n"

        client = anthropic.Anthropic(api_key=api_key)
        final_text = ""
        collected_tool_calls: list[dict] = []

        # Agentic loop: Claude may call query_salesforce multiple times
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
                # Save assistant reply to DB
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
```

- [ ] **Step 3: Verify unit tests still pass**

```bash
cd 03_build && python3 -m pytest tests/test_support_api.py -v
```

Expected: all 6 PASS.

- [ ] **Step 4: Smoke-test the backend manually**

```bash
# Start backend if not running
cd 03_build && python3 -m uvicorn api.main:app --port 8000 &

# Create a conversation
curl -s -X POST http://localhost:8000/support/conversations \
  -H "X-User-Id: test-user" | python3 -m json.tool

# Note the conversation_id from the response, e.g. "abc-123"
# Send a message
curl -s -X POST http://localhost:8000/support/chat \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test-user" \
  -d '{"conversation_id": "<id-from-above>", "message": "How many active associates are there?"}' \
  --no-buffer | head -5
```

Expected: first curl returns `{"conversation_id": "...", "title": "New conversation", "updated_at": "..."}`. Second curl streams SSE lines starting with `data: {"type": "title", ...}`.

- [ ] **Step 5: Commit**

```bash
git add 03_build/api/support.py
git commit -m "feat: persist chat history per user, backend owns conversation state"
```

---

## Task 5: Frontend — API Client

**Files:**
- Modify: `03_build/front/src/lib/api.ts`

- [ ] **Step 1: Add the `ConversationItem` and `SupportMessageItem` interfaces and 4 new API calls**

Add after the `getMeetings` function (before `getAction`):

```typescript
  listConversations: async (caller: ApiCaller) => {
    interface ConversationItem {
      conversation_id: string;
      title: string;
      updated_at: string;
    }
    return request<ConversationItem[]>("/support/conversations", caller);
  },

  createConversation: async (caller: ApiCaller) => {
    interface ConversationItem {
      conversation_id: string;
      title: string;
      updated_at: string;
    }
    return request<ConversationItem>("/support/conversations", caller, {
      method: "POST",
    });
  },

  deleteConversation: async (caller: ApiCaller, conversationId: string) =>
    request<void>(`/support/conversations/${conversationId}`, caller, {
      method: "DELETE",
    }),

  getConversationMessages: async (caller: ApiCaller, conversationId: string) => {
    interface SupportMessageItem {
      message_id: string;
      role: "user" | "assistant";
      content: string;
      tool_calls: Record<string, unknown>[] | null;
      created_at: string;
    }
    return request<SupportMessageItem[]>(
      `/support/conversations/${conversationId}/messages`,
      caller,
    );
  },
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd 03_build/front && npx tsc --noEmit 2>&1 | grep -v "npm notice"
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add 03_build/front/src/lib/api.ts
git commit -m "feat: add support conversation API calls to client"
```

---

## Task 6: Frontend — Hooks

**Files:**
- Create: `03_build/front/src/features/support/hooks.ts`

- [ ] **Step 1: Create the hooks file**

```typescript
// 03_build/front/src/features/support/hooks.ts
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useUser } from "@/lib/auth/AuthContext";

export interface ConversationItem {
  conversation_id: string;
  title: string;
  updated_at: string;
}

export interface SupportMessageItem {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  tool_calls: Record<string, unknown>[] | null;
  created_at: string;
}

export function useConversations() {
  const user = useUser();
  return useQuery({
    queryKey: ["support", "conversations"],
    queryFn: () => api.listConversations(user) as Promise<ConversationItem[]>,
    staleTime: 0,
  });
}

export function useMessages(conversationId: string | null) {
  const user = useUser();
  return useQuery({
    queryKey: ["support", "messages", conversationId],
    queryFn: () =>
      api.getConversationMessages(user, conversationId!) as Promise<SupportMessageItem[]>,
    enabled: !!conversationId,
    staleTime: 0,
  });
}

export function useInvalidateConversations() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["support", "conversations"] });
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd 03_build/front && npx tsc --noEmit 2>&1 | grep -v "npm notice"
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add 03_build/front/src/features/support/hooks.ts
git commit -m "feat: add useConversations and useMessages hooks"
```

---

## Task 7: Frontend — SupportPage Sidebar + Conversation Management

**Files:**
- Modify: `03_build/front/src/features/support/SupportPage.tsx`

This task rewrites `SupportPage.tsx` to add the sidebar and conversation management. The existing message bubble UI, tool chip, and streaming logic are preserved; only what wraps them changes.

- [ ] **Step 1: Replace the entire file with the new implementation**

```tsx
// 03_build/front/src/features/support/SupportPage.tsx
import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Bot, User, Database, Loader2, Sparkles, Plus, Trash2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { api, authHeaders } from "@/lib/api";
import { useUser } from "@/lib/auth/AuthContext";
import {
  useConversations,
  useMessages,
  useInvalidateConversations,
  ConversationItem,
  SupportMessageItem,
} from "./hooks";

// ── Types ──────────────────────────────────────────────────────────────────

type Role = "user" | "assistant";

interface TextPart {
  type: "text";
  text: string;
}

interface ToolPart {
  type: "tool";
  name: string;
  input: Record<string, unknown>;
}

type MessagePart = TextPart | ToolPart;

interface Message {
  id: string;
  role: Role;
  parts: MessagePart[];
  pending?: boolean;
}

// ── Helpers ────────────────────────────────────────────────────────────────

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

/** Convert a DB message row to the local Message display format. */
function dbMsgToLocal(m: SupportMessageItem, idx: number): Message {
  const parts: MessagePart[] = [];
  if (m.tool_calls) {
    for (const tc of m.tool_calls) {
      parts.push({
        type: "tool",
        name: tc.name as string,
        input: tc.input as Record<string, unknown>,
      });
    }
  }
  if (m.content.trim()) {
    parts.push({ type: "text", text: m.content });
  }
  return { id: m.message_id ?? String(idx), role: m.role, parts };
}

// ── Suggested starters ─────────────────────────────────────────────────────

const SUGGESTIONS = [
  "How many active associates are there across all accounts?",
  "Which accounts have the highest churn probability?",
  "Show me accounts with no outreach in the last 30 days.",
  "How many open opportunities are closing this quarter?",
  "What are the top 5 accounts by active associate count?",
  "Which Strategic-tier accounts are at churn risk?",
];

// ── Components ─────────────────────────────────────────────────────────────

function ToolCallChip({ name, input }: { name: string; input: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  const soql = typeof input.soql === "string" ? input.soql : JSON.stringify(input);
  return (
    <div className="mt-1.5 inline-block">
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 rounded-full bg-brand-muted px-2.5 py-1 text-xs font-medium text-brand transition hover:bg-brand/10"
      >
        <Database className="h-3 w-3" />
        {name}
        <span className="text-brand/60">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <pre className="mt-1.5 w-full max-w-lg overflow-x-auto rounded-xl bg-surface-sidebar p-3 text-xs text-ink-secondary">
          {soql}
        </pre>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      <div
        className={cn(
          "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-ink-primary text-ink-on-brand" : "bg-brand text-ink-on-brand shadow-xl-brand",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div className={cn("flex max-w-[75%] flex-col gap-1", isUser ? "items-end" : "items-start")}>
        {message.pending ? (
          <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm bg-surface-sidebar px-4 py-3 text-sm text-ink-secondary">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Thinking…
          </div>
        ) : (
          message.parts.map((part, i) => {
            if (part.type === "tool") return <ToolCallChip key={i} name={part.name} input={part.input} />;
            if (!part.text.trim()) return null;
            return (
              <div
                key={i}
                className={cn(
                  "rounded-2xl px-4 py-3 text-sm leading-relaxed",
                  isUser
                    ? "rounded-tr-sm bg-brand text-ink-on-brand"
                    : "rounded-tl-sm bg-surface-sidebar text-ink-primary",
                )}
              >
                {part.text.split("\n").map((line, j) => (
                  <span key={j}>
                    {line}
                    {j < part.text.split("\n").length - 1 && <br />}
                  </span>
                ))}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function ConversationRow({
  conv,
  active,
  onSelect,
  onDelete,
}: {
  conv: ConversationItem;
  active: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      className={cn(
        "group flex cursor-pointer items-center justify-between rounded-lg px-3 py-2 text-sm transition",
        active
          ? "bg-brand/10 text-brand"
          : "text-ink-secondary hover:bg-surface-sidebar hover:text-ink-primary",
      )}
      onClick={onSelect}
    >
      <span className="truncate flex-1">{conv.title}</span>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="ml-1 shrink-0 opacity-0 group-hover:opacity-100 text-ink-muted hover:text-red-500 transition"
        aria-label="Delete conversation"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export function SupportPage() {
  const user = useUser();
  const qc = useQueryClient();
  const invalidateConversations = useInvalidateConversations();

  const { data: conversations = [] } = useConversations();
  const [activeId, setActiveId] = useState<string | null>(null);
  const { data: dbMessages } = useMessages(activeId);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const idCounter = useRef(0);
  const nextId = () => String(++idCounter.current);

  // Auto-select most recent conversation on first load
  useEffect(() => {
    if (!activeId && conversations.length > 0) {
      setActiveId(conversations[0].conversation_id);
    }
  }, [conversations, activeId]);

  // Load messages from DB when conversation changes
  useEffect(() => {
    if (!dbMessages) return;
    setMessages(dbMessages.map(dbMsgToLocal));
  }, [dbMessages]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleNewChat = useCallback(async () => {
    const conv = await api.createConversation(user) as ConversationItem;
    await invalidateConversations();
    setActiveId(conv.conversation_id);
    setMessages([]);
  }, [user, invalidateConversations]);

  const handleDeleteConversation = useCallback(async (conversationId: string) => {
    await api.deleteConversation(user, conversationId);
    await invalidateConversations();
    if (activeId === conversationId) {
      const remaining = conversations.filter((c) => c.conversation_id !== conversationId);
      setActiveId(remaining[0]?.conversation_id ?? null);
      setMessages([]);
    }
  }, [user, invalidateConversations, activeId, conversations]);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || streaming || !activeId) return;

      const userMsg: Message = {
        id: nextId(),
        role: "user",
        parts: [{ type: "text", text: text.trim() }],
      };
      const pendingId = nextId();
      const pendingMsg: Message = { id: pendingId, role: "assistant", parts: [], pending: true };

      setMessages((prev) => [...prev, userMsg, pendingMsg]);
      setInput("");
      setStreaming(true);

      try {
        const resp = await fetch(`${BASE}/support/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...authHeaders(user),
          },
          body: JSON.stringify({ conversation_id: activeId, message: text.trim() }),
        });

        if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        const assistantId = nextId();
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId ? { id: assistantId, role: "assistant", parts: [], pending: false } : m,
          ),
        );

        const appendPart = (part: MessagePart) => {
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== assistantId) return m;
              const last = m.parts[m.parts.length - 1];
              if (part.type === "text" && last?.type === "text") {
                return { ...m, parts: [...m.parts.slice(0, -1), { type: "text", text: last.text + part.text }] };
              }
              return { ...m, parts: [...m.parts, part] };
            }),
          );
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            try {
              const event = JSON.parse(line.slice(6));
              if (event.type === "text") {
                appendPart({ type: "text", text: event.text });
              } else if (event.type === "tool") {
                appendPart({ type: "tool", name: event.name, input: event.input });
              } else if (event.type === "title") {
                // Update conversation title in the sidebar
                qc.setQueryData<ConversationItem[]>(["support", "conversations"], (old = []) =>
                  old.map((c) =>
                    c.conversation_id === activeId ? { ...c, title: event.title } : c,
                  ),
                );
              }
            } catch {
              // ignore malformed SSE lines
            }
          }
        }
      } catch {
        setMessages((prev) =>
          prev.map((m) =>
            m.pending
              ? { ...m, pending: false, parts: [{ type: "text", text: "Sorry, something went wrong." }] }
              : m,
          ),
        );
      } finally {
        setStreaming(false);
      }
    },
    [streaming, activeId, user, qc],
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const empty = messages.length === 0;

  return (
    <div className="flex h-[calc(100vh-10rem)]">
      {/* Sidebar */}
      <aside className="flex w-64 shrink-0 flex-col border-r border-line-subtle bg-surface-sidebar">
        <div className="p-3">
          <button
            onClick={handleNewChat}
            className="flex w-full items-center gap-2 rounded-lg border border-line-subtle bg-white px-3 py-2 text-sm font-medium text-ink-primary transition hover:border-brand/30 hover:bg-brand-ghost hover:text-brand"
          >
            <Plus className="h-4 w-4" />
            New chat
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-2 pb-3 space-y-0.5">
          {conversations.map((conv) => (
            <ConversationRow
              key={conv.conversation_id}
              conv={conv}
              active={activeId === conv.conversation_id}
              onSelect={() => {
                setActiveId(conv.conversation_id);
                setMessages([]);
              }}
              onDelete={() => handleDeleteConversation(conv.conversation_id)}
            />
          ))}
        </div>
      </aside>

      {/* Chat area */}
      <div className="flex flex-1 flex-col">
        {/* Header */}
        <div className="border-b border-line-subtle px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-brand text-ink-on-brand shadow-xl-brand">
              <Sparkles className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-ink-primary">Edge Pulse Support AI</h1>
              <p className="text-xs text-ink-muted">
                Ask anything about Edge accounts, associates, outreach, or opportunities — live Salesforce data.
              </p>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {empty ? (
            <div className="flex h-full flex-col items-center justify-center gap-6">
              <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-brand/10">
                <Bot className="h-8 w-8 text-brand" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-ink-primary">Ask me anything about Edge data</p>
                <p className="mt-1 text-xs text-ink-muted">
                  {activeId
                    ? "I have live read-only access to the Edge Salesforce org."
                    : "Create a new chat or select a conversation to start."}
                </p>
              </div>
              {activeId && (
                <div className="grid max-w-xl grid-cols-1 gap-2 sm:grid-cols-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => sendMessage(s)}
                      className="rounded-2xl border border-line-subtle bg-white px-4 py-3 text-left text-xs text-ink-secondary transition hover:border-brand/30 hover:bg-brand-ghost hover:text-brand"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((m) => (
                <MessageBubble key={m.id} message={m} />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-line-subtle px-6 py-4">
          <div className="flex items-end gap-3 rounded-2xl border border-line-strong bg-white px-4 py-3 focus-within:border-brand/40 focus-within:ring-2 focus-within:ring-brand/10">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                activeId
                  ? "Ask about accounts, associates, churn risk, opportunities…"
                  : "Select or create a conversation to start chatting"
              }
              rows={1}
              disabled={streaming || !activeId}
              className="flex-1 resize-none bg-transparent text-sm text-ink-primary placeholder:text-ink-muted focus:outline-none disabled:opacity-60"
              style={{ maxHeight: "120px" }}
              onInput={(e) => {
                const el = e.currentTarget;
                el.style.height = "auto";
                el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
              }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || streaming || !activeId}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-brand text-ink-on-brand shadow-xl-brand transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {streaming ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
            </button>
          </div>
          <p className="mt-2 text-center text-xs text-ink-muted">
            Powered by Claude · Read-only Salesforce access · Press Enter to send
          </p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd 03_build/front && npx tsc --noEmit 2>&1 | grep -v "npm notice"
```

Expected: no errors.

- [ ] **Step 3: Test in browser**

With both servers running (`python3 -m uvicorn api.main:app --port 8000` and `npm run dev`), open `http://localhost:5173` and navigate to Support.

Verify:
1. Sidebar shows "New chat" button
2. If no conversations exist, clicking "New chat" creates one and shows suggestions
3. Typing a message and pressing Enter streams the response
4. After first message, sidebar title updates from "New conversation" to the first message text
5. Clicking "New chat" again creates a second conversation
6. Clicking between conversations switches the message history
7. Hovering over a conversation shows a trash icon; clicking it deletes it
8. Refreshing the page restores the conversation list and re-selects the most recent

- [ ] **Step 4: Commit**

```bash
git add 03_build/front/src/features/support/SupportPage.tsx
git commit -m "feat: support chat sidebar with persistent per-user conversation history"
```
