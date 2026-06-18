# Inbox & Suggested Reply — Design

**Date:** 2026-06-15
**Status:** Approved

## Goal

Give each RM an **Inbox** tab in Pulse that surfaces unreplied emails from their existing
clients, each pre-loaded with an AI-drafted reply written in the RM's own voice. The RM
edits the draft if they wish and clicks **Send**; the reply goes out through Gmail as the
RM, threaded into the original conversation.

## Background — what already exists

- **Gmail sync** (`core/google/gmail_sync.py`) pulls the last 6 months of a user's Gmail
  into `pulse.episodes`, matching sender/recipient addresses to SF accounts via
  `core/google/account_matcher.py`. **Limitations this feature must overcome:** it requests
  `format=metadata` (snippet only, no full body) and the OAuth grant is **read-only**
  (`gmail.readonly`).
- **RM writing-style profiles** (`pulse.rm_style_profiles`, keyed by `rm_pulse_user_id`)
  are produced by `core/llm/rm_style.py` and already consumed by the client-chat feature
  (`api/client_chat.py`) to write in the RM's voice. The Inbox reuses this verbatim.
- **No send capability exists.** `core/dispatch/email.py` defines an `EmailTransport`
  Protocol but its default implementation raises "not configured".
- **Identity:** the frontend `user.id` (e.g. `eddy-chen`) equals
  `pulse.google_sessions.user_id`, and the API auth shim sends it as `X-User-Id`. So the
  inbox scopes to the logged-in RM's own mailbox with no new auth plumbing.
- **Frontend patterns:** `Header.tsx` holds a static role-gated `NAV` array; `App.tsx`
  registers routes under `RoleGuard`; `features/support/SupportPage.tsx` is the canonical
  list-plus-detail layout; `features/*/hooks.ts` wrap TanStack Query; `lib/api.ts` holds
  typed client methods.

## Decisions (locked)

1. **Send mechanism:** Gmail `users.messages.send` as the RM (requires adding the
   `gmail.send` scope; RMs re-consent once at next login). The reply lands in the RM's
   Gmail Sent and threads correctly.
2. **Inbox scope:** unreplied client emails only — inbound emails from contacts that
   resolve to an SF account **owned by this RM**, where the email is the latest message in
   its Gmail thread.
3. **Reply flow:** the suggested reply is **pre-generated at ingest time** so it is already
   present when the email appears in the Pulse inbox, and is **editable** before the RM
   sends it.

## Out of scope (v1)

Attachments; HTML-formatted replies (plain text only); CC / multi-recipient replies;
real-time Gmail push notifications (poll-on-open + 60s frontend refetch instead).

## Data model

New table `pulse.inbox_emails`:

```sql
CREATE TABLE IF NOT EXISTS pulse.inbox_emails (
    email_id          UUID PRIMARY KEY,
    rm_user_id        TEXT NOT NULL,          -- google_sessions.user_id (mailbox owner)
    gmail_message_id  TEXT NOT NULL,          -- Gmail message id of the inbound email
    gmail_thread_id   TEXT NOT NULL,          -- Gmail thread id (for threading the reply)
    account_id        TEXT,                   -- matched SF account
    from_email        TEXT NOT NULL,
    from_name         TEXT,
    subject           TEXT,
    body              TEXT,                   -- full plain-text body
    received_at       TIMESTAMPTZ NOT NULL,
    suggested_reply   TEXT,                   -- pre-generated AI draft (NULL if generation failed)
    reply_rationale   TEXT,                   -- one-line "why this draft" explanation
    draft_reply       TEXT,                   -- RM's edited draft (NULL until they edit); survives refresh
    reply_state       TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'sent' | 'dismissed'
    sent_at           TIMESTAMPTZ,
    sent_message_id   TEXT,                   -- Gmail id of the sent reply
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (rm_user_id, gmail_message_id)
);
CREATE INDEX IF NOT EXISTS idx_inbox_rm_state
    ON pulse.inbox_emails (rm_user_id, reply_state, received_at DESC);
```

The table is created in `_ensure_schema()` in `api/main.py`, consistent with how other
Pulse tables are provisioned.

## Components

### Backend

**OAuth scope (`api/auth_google.py`)** — add
`https://www.googleapis.com/auth/gmail.send` to `_SCOPES`. Existing sessions keep working
for read; sending requires re-consent. A `gmail_send` boolean is exposed on the
session/me endpoint so the UI can show a "Reconnect Google" prompt when the granted scopes
don't yet include send.

**`core/inbox/sync.py`** — `async def sync_inbox(rm_user_id: str) -> dict`:
1. `get_valid_token(rm_user_id)`; build the contact→account index (`account_matcher`).
2. List recent INBOX threads (default last 14 days) via Gmail `messages.list`.
3. For each thread, fetch the message list; keep the thread only if its **latest** message
   is inbound (the RM has not already replied).
4. Resolve the inbound sender to an SF account; keep only accounts **owned by this RM**
   (map `rm_user_id` → `google_name` → `sf_accounts.rm_name`, the existing link).
5. Fetch the full body (`format=full`, walk MIME parts, prefer `text/plain`).
6. Upsert into `pulse.inbox_emails` (`ON CONFLICT (rm_user_id, gmail_message_id)`).
7. For each newly inserted row, call `generate_reply` and store the result.

**`core/inbox/reply.py`** — `async def generate_reply(email: dict, tone: str | None = None)
-> dict`: load the RM's `rm_style_profiles.style_prompt` (fall back to a default voice),
assemble a prompt with the account name, the account's recent themes/health context, and the
inbound email body, call Claude Sonnet, and return `{reply, rationale}` — the draft plus a
one-line explanation of what it keyed on (e.g. "Client asked about renewal timing — draft
confirms the Q3 EBR date"). An optional `tone` (`"formal" | "shorter" | "warmer"`) adjusts
the prompt for the regenerate controls.

**`core/inbox/send.py`** — `async def send_reply(rm_user_id, email_id, body) -> str`: load
the row, build an RFC-2822 MIME message (`To`, `Subject: Re: …`, `In-Reply-To` and
`References` set to the inbound `Message-Id`), base64url-encode, POST to Gmail
`users.messages.send` with `{raw, threadId}`. On success, update the row to
`reply_state='sent'`, `sent_at`, `sent_message_id`. Returns the sent Gmail message id.

**`api/inbox.py`** — FastAPI router mounted under `/inbox`:
- `GET /inbox` → runs `sync_inbox` for the caller, then returns the caller's `pending`
  rows (newest first) as summaries, plus a `count` for the nav badge. Each summary carries
  the matched account's `tier`/`risk` so the list can prioritize and color rows.
- `GET /inbox/{email_id}` → full body, suggested reply, rationale, and any saved
  `draft_reply` for one row (caller-scoped).
- `POST /inbox/{email_id}/reply` (body `{text}`) → `send_reply`, returns the sent id.
- `POST /inbox/{email_id}/draft` (body `{text}`) → persists the RM's edited `draft_reply`
  so edits survive a refresh or tab switch (called on textarea blur / debounced).
- `POST /inbox/{email_id}/regenerate` (body `{tone}`) → re-runs `generate_reply` with the
  given tone, stores and returns the new `{reply, rationale}`.
- `POST /inbox/{email_id}/dismiss` → sets `reply_state='dismissed'`.

All endpoints resolve the caller from `X-User-Id` and filter every query by
`rm_user_id = caller`, so one RM can never read or send from another's mailbox.

### Frontend (`front/src/features/inbox/`)

- `types.ts` — `InboxEmailDTO` (summary: sender, subject, snippet, `received_at`,
  `account_id`, `tier`, `risk`, `has_draft`), `InboxEmailDetailDTO` (adds `body`,
  `suggested_reply`, `reply_rationale`, `draft_reply`), `InboxListDTO` (`emails`, `count`).
- `hooks.ts` — `useInbox()` (list, `refetchInterval: 60_000`), `useInboxEmail(id)`,
  `useSendReply()`, `useSaveDraft()`, `useRegenerate()`, `useDismiss()` (mutations
  invalidate the inbox key).
- `InboxPage.tsx` — list-plus-detail mirroring `SupportPage`: left = pending email rows
  (from, subject, snippet, relative time); right = full body + an editable textarea
  pre-filled with `suggested_reply` + a **Send** button (and a secondary Dismiss).
- API methods in `lib/api.ts`: `listInbox`, `getInboxEmail`, `sendInboxReply`,
  `dismissInboxEmail`.
- `Header.tsx`: add `{ to: "/inbox", label: "Inbox", roles: ["rm","manager","executive","admin"] }`,
  with a small unread-count badge on the label driven by `useInbox().data.count`.
- `App.tsx`: add a `/inbox` route under `RoleGuard` with the same roles.

## Inbox UI/UX (the polish layer)

The Inbox window is the showcase surface, so it gets first-class treatment rather than a
bare list. All of the following reuse data Pulse already has.

**List column (left):**
- Each row shows a sender initials avatar, sender name, subject, a one-line body snippet,
  and a relative timestamp ("2h ago").
- A left accent bar colors the row by the client's **risk** (high = red, medium = amber),
  and rows are **sorted by risk then recency** so churn-risk clients float to the top.
- A subtle "AI reply ready" pill appears when `suggested_reply` is populated, so the RM
  knows a draft is waiting before they even open it.
- Inbox-zero **empty state**: a calm "You're all caught up" panel with a Sparkles motif
  (matches the Action Queue's existing empty state).

**Detail pane (right):**
- **Account context card** at the top — client/account name, tier badge, risk badge, ARR,
  composite health, and last-meeting date, pulled from the existing account-health endpoint
  via the current `useAccountHealth(account_id)` hook (no new backend). Includes a
  "View account →" link that routes to `/accounts` for that client.
- Full inbound email body in a clean reading block with a `Re: <subject> · To: <client>`
  thread-preview header so the RM sees how the reply will thread.
- **Editable draft** textarea pre-filled with `draft_reply ?? suggested_reply`. Below it:
  - a one-line **"Why this draft"** rationale (`reply_rationale`) for trust,
  - **regenerate chips** — `More formal` · `Shorter` · `Warmer` · `↻ Regenerate` — each
    calling `POST /regenerate` and swapping in the new draft with a soft fade,
  - a **Reset to suggestion** affordance once the RM has edited.
- Edits autosave to `draft_reply` on blur (debounced) so nothing is lost on refresh.

**Send experience:**
- Primary **Send** button plus **⌘/Ctrl+Enter** to send from the textarea.
- Optimistic UI: Send shows a spinner, then the row animates out of the list with a slide,
  a success toast confirms ("Reply sent to <client>"), and the next pending email
  auto-selects so the RM can keep flowing.
- **Dismiss** as a secondary action removes the email from the queue without sending.
- If the RM hasn't granted `gmail.send` yet, the Send button is replaced by a
  **"Reconnect Google to send"** prompt that launches the OAuth re-consent.

**Motion & states:** loading skeletons for the list and detail, framer-motion
enter/exit on rows (consistent with `QueueList`), and disabled/spinner states on every
async action. Plain-text replies only in v1, but the reading block renders the inbound
body with preserved line breaks.

## Data flow

RM opens Inbox → `GET /inbox` syncs the newest unreplied client emails and generates drafts
→ the list renders (sorted by risk then recency) with drafts and rationale already
populated → RM optionally regenerates with a tone chip or edits inline (edits autosave to
`draft_reply`) → **Send** (button or ⌘/Ctrl+Enter) → Gmail sends as the RM, the row flips
to `sent`, animates out, a toast confirms, and the next pending email auto-selects. The
frontend re-polls every 60s, so newly arrived client emails surface on their own.

## Error handling

- **No `gmail.send` consent yet:** `send_reply` detects the missing scope (or Gmail returns
  403) → API responds 403 with a `reconnect_required` detail → UI shows "Reconnect Google".
- **Token expiry:** handled by the existing `get_valid_token` refresh path.
- **Send failure:** the row stays `pending`; the error is surfaced to the RM.
- **Reply-generation failure:** `suggested_reply` is stored `NULL`; the UI shows an empty
  editable box so the RM can write their own.
- **Sync failure for one thread:** logged and skipped; never aborts the whole sync.

## Testing

Unit tests with mocked Gmail API and Anthropic client:
- client-ownership filter (sender → account owned by this RM; non-clients excluded),
- unreplied-thread detection (latest message inbound vs. RM already replied),
- full-body MIME parsing (prefer `text/plain`, walk nested parts),
- reply generation returns `{reply, rationale}`; tone variants alter the prompt,
- MIME construction and threading headers (`In-Reply-To`/`References`/`threadId`),
- draft autosave persists `draft_reply` and detail returns `draft_reply ?? suggested_reply`,
- reply-state transitions (`pending` → `sent`, `pending` → `dismissed`),
- caller scoping (RM A cannot fetch, draft, regenerate, or send RM B's rows).
