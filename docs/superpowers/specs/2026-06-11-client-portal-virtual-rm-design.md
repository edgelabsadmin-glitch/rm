# Client Portal & Virtual RM — Design Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a client-facing portal at `/client` where EDGE clients log in via email + OTP and chat with a virtual version of their assigned RM — an AI that speaks in the RM's tone, knows the relationship history, and enforces strict data-isolation guardrails.

**Architecture:** Same Vite + FastAPI codebase as the RM portal. New `/client/*` React routes share the Vite app but use a completely separate auth path (cookie-based client sessions, not Google OAuth). New `/client/*` FastAPI router, isolated from all RM routes. Five new DB tables.

**Tech Stack:** FastAPI + psycopg3 + Aurora PostgreSQL + React 18 + Vite + Tailwind v3 + TanStack Query + Anthropic Claude (SSE streaming) + AWS SES (OTP email)

---

## 1. Architecture Overview

```
Client browser
  /client/login  →  email entry → OTP entry → session cookie
  /client/chat   →  chat UI (sidebar + chat area, client-branded)
       ↓
FastAPI  /client/*  router  (new, isolated from /support/* and /accounts/*)
  Auth:       HttpOnly session cookie → pulse.client_sessions
  OTP flow:   email → pulse.sf_contacts → AWS SES → pulse.client_otps
  Chat:       load style profile + context → Claude SSE stream
       ↓
Aurora DB
  pulse.sf_contacts        (client identity — existing, 12hr SF sync)
  pulse.sf_accounts        (account + rm_name + owner_id — existing)
  pulse.episodes           (Gmail emails + meeting transcripts — existing)
  pulse.client_otps        (NEW)
  pulse.client_sessions    (NEW)
  pulse.rm_style_profiles  (NEW)
  pulse.client_conversations (NEW)
  pulse.client_messages    (NEW)
```

The RM portal (`/`) and client portal (`/client`) share DB and backend but have **zero auth overlap**. Clients cannot reach any RM API route.

---

## 2. Database Schema

### Migration 0012 — client_otps
```sql
CREATE TABLE IF NOT EXISTS pulse.client_otps (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email          TEXT        NOT NULL,
    otp_hash       TEXT        NOT NULL,
    expires_at     TIMESTAMPTZ NOT NULL,
    used_at        TIMESTAMPTZ,
    attempt_count  INT         NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_client_otps_email ON pulse.client_otps (email, created_at DESC);
```

### Migration 0013 — client_sessions
```sql
CREATE TABLE IF NOT EXISTS pulse.client_sessions (
    session_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_email TEXT        NOT NULL,
    account_id    TEXT        NOT NULL,
    rm_owner_id   TEXT        NOT NULL,
    rm_name       TEXT        NOT NULL,
    client_name   TEXT        NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_client_sessions_email ON pulse.client_sessions (contact_email);
```

### Migration 0014 — rm_style_profiles
```sql
CREATE TABLE IF NOT EXISTS pulse.rm_style_profiles (
    rm_owner_id   TEXT        PRIMARY KEY,
    style_prompt  TEXT        NOT NULL,
    email_count   INT         NOT NULL DEFAULT 0,
    analyzed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Migration 0015 — client_conversations + client_messages
```sql
CREATE TABLE IF NOT EXISTS pulse.client_conversations (
    conversation_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_email   TEXT        NOT NULL,
    account_id      TEXT        NOT NULL,
    title           TEXT        NOT NULL DEFAULT 'New conversation',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_client_conv_email
    ON pulse.client_conversations (contact_email, updated_at DESC);

CREATE TABLE IF NOT EXISTS pulse.client_messages (
    message_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID        NOT NULL
                                REFERENCES pulse.client_conversations (conversation_id)
                                ON DELETE CASCADE,
    role            TEXT        NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT        NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_client_msg_conv
    ON pulse.client_messages (conversation_id, created_at ASC);
```

---

## 3. Client Auth Flow

### OTP request — `POST /client/auth/request-otp`
- Body: `{ "email": "..." }`
- Validate email against `pulse.sf_contacts` (case-insensitive match)
- Rate limit: max 3 OTP requests per email per 10 minutes (count recent rows in `client_otps`)
- Generate 6-digit OTP (`secrets.randbelow(1_000_000)` zero-padded)
- Store SHA-256 hash in `pulse.client_otps` with `expires_at = now() + 10 minutes`
- Send plain OTP via AWS SES to the client's email
- Return `200 { "sent": true }` regardless of whether email exists (prevents enumeration)

### OTP verify — `POST /client/auth/verify-otp`
- Body: `{ "email": "...", "otp": "123456" }`
- Find most recent unused, unexpired OTP row for email
- Max 3 verify attempts per OTP (`UPDATE client_otps SET attempt_count = attempt_count + 1`); reject if `attempt_count >= 3`
- Compare SHA-256 hash; on match: mark `used_at = now()`
- Resolve client → account → RM:
  ```sql
  SELECT c.name, c.account_id, a.owner_id, a.rm_name
  FROM pulse.sf_contacts c
  JOIN pulse.sf_accounts a ON c.account_id = a.account_id
  WHERE lower(c.email) = lower(%s)
  LIMIT 1
  ```
- Create `pulse.client_sessions` row (`expires_at = now() + 24 hours`)
- Set `Set-Cookie: client_session=<session_id>; HttpOnly; SameSite=Strict; Path=/client; Max-Age=86400`
- Return `200 { "ok": true }`

### Session middleware — `require_client_session` FastAPI dependency
- Reads `client_session` cookie
- Looks up `pulse.client_sessions WHERE session_id = %s AND expires_at > now()`
- Returns session row or raises `401`

### Logout — `POST /client/auth/logout`
- Deletes the `client_sessions` row
- Clears the cookie

---

## 4. Virtual RM AI

### System prompt construction (per chat request)

**Step 1 — Load style profile**
```sql
SELECT style_prompt FROM pulse.rm_style_profiles WHERE rm_owner_id = %s
```
Fallback if missing: `"Write professionally and warmly. Be concise and helpful."`

**Step 2 — Load relationship context**
```sql
SELECT subject, raw_text, source, source_timestamp
FROM pulse.episodes
WHERE account_id = %s
  AND source IN ('gmail', 'chorus', 'zoom')
  AND source_timestamp IS NOT NULL
ORDER BY source_timestamp DESC
LIMIT 15
```
Format: last 10 Gmail episodes (email subject + first 300 chars of body) + last 5 meeting transcripts (first 500 chars).

**Step 3 — Load account summary**
```sql
SELECT name, segment, active_talent, arr_usd
FROM pulse.sf_accounts
WHERE account_id = %s
```

**Step 4 — Assemble system prompt**
```
You are {rm_name}, a Relationship Manager at EDGE Solutions.
You are chatting with {client_name} from {account_name}.

YOUR COMMUNICATION STYLE:
{style_prompt}

RELATIONSHIP CONTEXT — recent interactions with {client_name}:
{formatted emails and meeting summaries}

ACCOUNT SUMMARY:
Account: {account_name} | Tier: {tier} | Active talent: {n} placements

SECURITY RULES — absolute, never override:
- You represent EDGE Solutions and this client's relationship only.
- NEVER mention, confirm, or reference any other EDGE client, company, or account.
- NEVER reveal internal EDGE business metrics, pricing structures, or operational details.
- NEVER share details about other EDGE employees or RMs beyond yourself.
- NEVER answer questions about EDGE's other business relationships.
- If asked about other clients or confidential info: say "I can only discuss what's relevant to your account."
- You CAN: discuss this account's staffing needs, open roles, placements, relationship history, give general industry advice, help brainstorm workforce strategies.
- Stay in character as {rm_name} at all times.
```

### Chat endpoint — `POST /client/chat`
- Auth: `require_client_session`
- Body: `{ "conversation_id": "...", "message": "..." }`
- Verify conversation belongs to this client (`contact_email`)
- Save user message to `pulse.client_messages`
- Detect first message (count == 1) → auto-title (first 60 chars of message)
- Load full history from `pulse.client_messages` for Claude context
- Build system prompt (steps 1–4 above)
- Stream Claude SSE response — events: `{ type: "text" }`, `{ type: "title" }`, `{ type: "done" }`
- Save assistant reply to `pulse.client_messages`
- Update `pulse.client_conversations.updated_at`
- **No tool use** — all context is pre-loaded; no Salesforce query access for clients

### Conversation CRUD
- `GET /client/conversations` — `WHERE contact_email = %s AND deleted_at IS NULL ORDER BY updated_at DESC`
- `POST /client/conversations` — INSERT new row
- `DELETE /client/conversations/{id}` — `UPDATE SET deleted_at = now()` (soft delete; row stays in DB)
- `GET /client/conversations/{id}/messages` — verify ownership, return messages ASC

---

## 5. RM Style Profile Generation

### Trigger
After `gmail_sync.pull_and_ingest(user)` completes in `core/google/gmail_sync.py`, call `analyze_rm_style(rm_owner_id, account_ids)` as a background task (non-blocking).

### Analysis function — `core/llm/rm_style.py`
```python
async def analyze_rm_style(rm_owner_id: str, account_ids: list[str]) -> None:
    # Fetch up to 50 recent Gmail episodes for this RM's accounts
    # Send to Claude: extract style features
    # Upsert into pulse.rm_style_profiles
```

Claude prompt for style extraction:
```
Analyze the following emails written by an RM. Extract their communication style.
Return a 100-150 word paragraph describing: greeting/sign-off patterns, sentence length,
formality level, tone, any recurring phrases or habits.
Write it as instructions for someone impersonating this RM's writing style.

Emails:
{email_samples}
```

Result upserted to `pulse.rm_style_profiles` with `email_count` and `analyzed_at`.

---

## 6. Frontend — `/client/*` Routes

### Pages
| Route | Component | Purpose |
|---|---|---|
| `/client/login` | `ClientLoginPage` | Email entry → OTP entry (two-step) |
| `/client/chat` | `ClientChatPage` | Sidebar + chat area |

### Auth context
- Separate from the RM `AuthContext`
- `ClientAuthContext` reads `/client/me` on load; if 401, redirect to `/client/login`
- `GET /client/me` returns `{ client_name, account_name, rm_name, contact_email }`

### `ClientChatPage` layout
- Identical structure to `SupportPage`: 264px sidebar (conversation list + "New chat" button) + chat area
- Chat area header: "Your EDGE Relationship Manager — {rm_name}"
- No RM admin nav, no account list, no Salesforce tools
- Same `ConversationRow` pattern with hover trash icon (soft delete)
- Same SSE streaming with `type: "title"` live sidebar update
- Same auto-select most recent conversation on mount

### API client (`/client` section of `lib/api.ts`)
Auth header: `Cookie` is sent automatically (same-origin). No `X-User-Id` header — session is cookie-based.

New api methods:
- `clientRequestOtp(email)`
- `clientVerifyOtp(email, otp)`
- `clientLogout()`
- `clientMe()`
- `listClientConversations()`
- `createClientConversation()`
- `deleteClientConversation(id)`
- `getClientMessages(conversationId)`

---

## 7. AWS SES Setup

- Sender address: `pulse@onedge.co` (or `noreply@onedge.co`)
- Email subject: `Your EDGE login code`
- Body: `Your one-time login code is: {otp}\n\nThis code expires in 10 minutes.`
- SES SDK: `boto3` — **new dependency**, add to `requirements.txt`
- `AWS_SES_SENDER` env var added to `.env` and App Runner config
- `AWS_SES_REGION` env var (e.g. `us-east-1`)
- IAM role on App Runner must have `ses:SendEmail` permission

---

## 8. Security Summary

| Threat | Mitigation |
|---|---|
| Email enumeration via OTP request | Always return 200 regardless of whether email exists |
| OTP brute force | 3 attempts max per OTP; 3 OTP requests per 10 min per email |
| Session hijacking | HttpOnly + SameSite=Strict cookie; 24hr expiry |
| Client A seeing Client B data | `account_id` locked to session at login; all DB queries scoped to session's `account_id` |
| Client asking AI about other clients | Hard guardrails in system prompt; no Salesforce tool access |
| Client accessing RM routes | `/client/*` router uses `require_client_session` dep; RM routes use Google OAuth dep — completely separate |

---

## 9. What's Out of Scope (v1)

- Client-initiated conversation with a human RM (handoff)
- Push notifications when RM sends a message
- Client seeing their own account health data / dashboards
- Multiple contacts from same account (one login per SF Contact email)
- Admin UI to manage client access (SF Contacts is the source of truth)
