# Support Chat History Design

## Goal

Persist support chat conversations per user in PostgreSQL, with each user able to maintain multiple named sessions (auto-titled from first message), switchable via a sidebar — replacing the current stateless, in-memory-only chat.

## Architecture

Backend becomes the single source of truth for chat history. The frontend sends only `{ conversation_id, message }` on each turn — no history payload. The backend loads history from the DB, builds the Claude context window, streams the response, and saves both turns to the DB. The frontend manages no history state beyond what it receives from the API.

## Tech Stack

- PostgreSQL (Aurora, `pulse` schema) — two new tables
- FastAPI (`api/support.py`) — three new REST endpoints + modified `/support/chat`
- React Query (`front/src/features/support/hooks.ts`) — two new hooks
- Existing SSE streaming pattern in `SupportPage.tsx`

---

## DB Schema

Migration: `03_build/migrations/0011_support_chat.sql`

```sql
CREATE TABLE IF NOT EXISTS pulse.support_conversations (
    conversation_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          TEXT NOT NULL,
    title            TEXT NOT NULL DEFAULT 'New conversation',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_support_conv_user
    ON pulse.support_conversations (user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS pulse.support_messages (
    message_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID NOT NULL
                         REFERENCES pulse.support_conversations (conversation_id)
                         ON DELETE CASCADE,
    role             TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content          TEXT NOT NULL,
    tool_calls       JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_support_msg_conv
    ON pulse.support_messages (conversation_id, created_at ASC);
```

---

## API Endpoints

All endpoints read `X-User-Id` from request headers for user identity. All live in `api/support.py`.

### `GET /support/conversations`
Returns the authenticated user's conversations ordered by `updated_at DESC`.

Response:
```json
[
  { "conversation_id": "uuid", "title": "How many active associates...", "updated_at": "2026-06-10T00:00:00Z" }
]
```

### `POST /support/conversations`
Creates a new conversation for the user with title `"New conversation"`.

Response:
```json
{ "conversation_id": "uuid", "title": "New conversation" }
```

### `DELETE /support/conversations/{conversation_id}`
Deletes the conversation and all its messages (CASCADE). Returns 204. Returns 404 if not found or not owned by user.

### `POST /support/chat` (modified)

**Old body:** `{ message: str, history: [...] }`
**New body:** `{ conversation_id: str, message: str }`

Behaviour:
1. Verify `conversation_id` belongs to `user_id` — 404 if not.
2. Save the user message to `pulse.support_messages`.
3. Load all prior messages for the conversation from DB — build Claude `messages` list.
4. If this is the first message (no prior messages before this one):
   - Set `title = message[:60].strip()` on the conversation.
   - Emit `data: {"type": "title", "title": "<title>"}` as the **first** SSE event.
5. Run the existing Claude agentic loop (tool use, streaming).
6. After streaming completes, save the full assistant reply text + tool_calls JSONB to `pulse.support_messages`.
7. Update `updated_at` on the conversation.
8. Emit `data: {"type": "done"}`.

---

## Frontend

### New file: `front/src/features/support/hooks.ts`

```ts
useConversations()                          // React Query: GET /support/conversations, staleTime 0
useMessages(conversationId: string | null)  // React Query: GET /support/conversations/{id}/messages, enabled when id is set
```

### New endpoint (backend): `GET /support/conversations/{id}/messages`
Returns all messages for a conversation in order.

```json
[
  { "message_id": "uuid", "role": "user", "content": "...", "tool_calls": null, "created_at": "..." },
  { "message_id": "uuid", "role": "assistant", "content": "...", "tool_calls": [...], "created_at": "..." }
]
```

### `SupportPage.tsx` layout

Two-column layout:

```
┌─────────────────┬────────────────────────────────────┐
│  Conversations  │                                    │
│  ─────────────  │         Chat area                  │
│  + New chat     │      (existing UI, unchanged)      │
│                 │                                    │
│  Meeting Q...   │                                    │
│  Churn risk...  │                                    │
│  Active assoc.. │                                    │
└─────────────────┴────────────────────────────────────┘
```

Sidebar (left, ~260px):
- "New chat" button at top
- List of conversations sorted newest first, each showing truncated title
- Active conversation highlighted
- Hover shows trash icon → DELETE

Chat area (right):
- Existing message bubbles, input, suggestions — unchanged
- On mount: fetch conversation list → auto-select most recent → load its messages
- On "New chat": POST conversation → select it → show empty state
- On send: POST `/support/chat` with `{ conversation_id, message }` (no history)
- On `type: "title"` SSE event: update conversation title in sidebar list

### State managed in `SupportPage.tsx`

```ts
const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
const [messages, setMessages] = useState<Message[]>([])   // local display state, loaded from API
```

`messages` is local display state only — loaded from DB on conversation switch, appended optimistically during streaming. On next conversation switch it's replaced by the DB-loaded messages.

### `front/src/lib/api.ts` additions

```ts
api.listConversations(caller)
api.createConversation(caller)
api.deleteConversation(caller, conversationId)
api.getConversationMessages(caller, conversationId)
// api.chat() signature changes: { conversationId, message } — no history
```

---

## Files Changed / Created

| File | Action |
|------|--------|
| `03_build/migrations/0011_support_chat.sql` | Create |
| `03_build/api/support.py` | Modify — 4 new endpoints, chat endpoint updated |
| `03_build/front/src/features/support/hooks.ts` | Create |
| `03_build/front/src/features/support/SupportPage.tsx` | Modify — sidebar + state changes |
| `03_build/front/src/lib/api.ts` | Modify — 4 new API calls, chat signature change |

---

## Error Handling

- `conversation_id` not found or not owned by user → 404
- `X-User-Id` header missing → 400
- Anthropic API key missing → 500 (existing behaviour)
- DB errors → 500, logged server-side
- Frontend: streaming error shows existing "Sorry, something went wrong" bubble

## Out of Scope

- Conversation search
- Message editing or regeneration
- Sharing conversations between users
- Context window summarization for very long conversations (load all messages as-is)
