# Inbox & Suggested Reply Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an Inbox tab where each RM sees unreplied emails from their existing clients, each pre-loaded with an editable AI draft in the RM's voice, sent via Gmail as the RM.

**Architecture:** A background loop syncs every connected RM's Gmail, keeps only unreplied threads from contacts on accounts that RM owns, fetches the full body, drafts a reply with the RM's style profile, and stores both in a new `pulse.inbox_emails` table. A `/inbox` FastAPI router serves the pending list and handles draft-save / regenerate / send / dismiss. A React Inbox feature renders a list-plus-detail view with an account-context card, tone controls, and a Send button that dispatches through Gmail.

**Tech Stack:** Python 3.12 / FastAPI / psycopg3 / Aurora Postgres; Gmail REST API v1; Anthropic (Claude Sonnet); React 18 / Vite / TypeScript / TanStack Query.

**Working directory:** All paths are relative to `03_build/`. Work happens in the worktree at `.claude/worktrees/inbox-suggested-reply` on branch `worktree-inbox-suggested-reply`.

**Test conventions:** Pure unit tests live in `tests/` and must NOT need a DB or network (the `db`/`integration` pytest markers are excluded by default in CI). Mock Gmail HTTP with monkeypatch and mock Anthropic. Run backend tests with `python3 -m pytest tests/test_inbox_*.py -q`. Frontend is verified with `front/node_modules/.bin/tsc -b` (the same check CI runs); there is no JS unit-test runner.

**Identity facts (verified):**
- The frontend `user.id` equals `pulse.google_sessions.user_id` and is sent as `X-User-Id`.
- `pulse.rm_style_profiles.rm_pulse_user_id` is keyed by that same `user_id` (see `core/llm/rm_style.py`).
- RM↔account ownership link: `pulse.google_sessions.google_name` (case-insensitive) == `pulse.sf_accounts.rm_name`.
- `core/google/auth.py` exposes `get_valid_token(user_id)` and `list_connected_users()`.
- `core/google/account_matcher.py` exposes `build_email_index()` and `match_accounts(addresses, index)` returning `[{"type":"sf_account","sfdc_id": account_id}]`.
- Reuse `require_caller` from `api/actions.py` for the `/inbox` router's identity.
- Model constant: `ANTHROPIC_SONNET` from `core/llm/config.py`.

**Scope note (deviation from spec, intentional/YAGNI):** The spec mentions a proactive `gmail_send` capability flag. We instead handle missing send-consent **reactively**: `send_reply` raises a 403 with `detail="reconnect_required"` when Gmail rejects for scope, and the UI shows "Reconnect Google to send" on that response. No new scope-storage plumbing.

---

## File Structure

**Backend (create):**
- `core/inbox/__init__.py` — package marker.
- `core/inbox/threads.py` — pure Gmail-payload helpers: `extract_plain_body`, `latest_inbound_message`.
- `core/inbox/reply.py` — `build_reply_prompt` (pure) + `generate_reply` (Claude).
- `core/inbox/send.py` — `build_reply_raw` (pure MIME) + `send_reply` (Gmail + DB).
- `core/inbox/sync.py` — `owned_account_ids` (pure) + `sync_inbox` (orchestration).
- `core/inbox/loop.py` — `inbox_sync_loop` background task.
- `api/inbox.py` — FastAPI router.
- `tests/test_inbox_threads.py`, `tests/test_inbox_reply.py`, `tests/test_inbox_send.py`, `tests/test_inbox_sync.py` — pure unit tests.

**Backend (modify):**
- `api/main.py` — add `pulse.inbox_emails` to `_ensure_schema()`, register the router, start the loop in `lifespan`.
- `api/auth_google.py` — add `gmail.send` scope.

**Frontend (create):**
- `front/src/features/inbox/types.ts`
- `front/src/features/inbox/hooks.ts`
- `front/src/features/inbox/InboxPage.tsx`

**Frontend (modify):**
- `front/src/lib/api.ts` — inbox client methods.
- `front/src/components/Header.tsx` — nav item + unread badge.
- `front/src/App.tsx` — `/inbox` route.

---

## Task 1: Database schema — `pulse.inbox_emails`

**Files:**
- Modify: `api/main.py` (inside `_ensure_schema()`, before the final `await conn.commit()` at line ~324)

- [ ] **Step 1: Add the table + index creation**

In `api/main.py`, inside `_ensure_schema()`, immediately before `await conn.commit()`, add:

```python
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.inbox_emails (
                email_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                rm_user_id        TEXT        NOT NULL,
                gmail_message_id  TEXT        NOT NULL,
                gmail_thread_id   TEXT        NOT NULL,
                rfc_message_id    TEXT,
                account_id        TEXT,
                from_email        TEXT        NOT NULL,
                from_name         TEXT,
                subject           TEXT,
                body              TEXT,
                received_at       TIMESTAMPTZ NOT NULL,
                suggested_reply   TEXT,
                reply_rationale   TEXT,
                draft_reply       TEXT,
                reply_state       TEXT        NOT NULL DEFAULT 'pending',
                sent_at           TIMESTAMPTZ,
                sent_message_id   TEXT,
                created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (rm_user_id, gmail_message_id)
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_inbox_rm_state "
            "ON pulse.inbox_emails (rm_user_id, reply_state, received_at DESC);"
        )
```

> Note: `rfc_message_id` stores the inbound email's RFC-2822 `Message-Id` header, needed for threading the reply (`In-Reply-To`/`References`).

- [ ] **Step 2: Verify the file still imports**

Run: `python3 -c "import ast; ast.parse(open('api/main.py').read()); print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add api/main.py
git commit -m "feat(inbox): add pulse.inbox_emails table to schema bootstrap"
```

---

## Task 2: Add the `gmail.send` OAuth scope

**Files:**
- Modify: `api/auth_google.py:37-45` (the `_SCOPES` list)
- Test: `tests/test_inbox_scopes.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_inbox_scopes.py`:

```python
"""Inbox feature requires the gmail.send scope in the Google OAuth grant."""

from api.auth_google import _SCOPES


def test_gmail_send_scope_present():
    assert "https://www.googleapis.com/auth/gmail.send" in _SCOPES


def test_readonly_scope_still_present():
    # Send is additive; reading must keep working.
    assert "https://www.googleapis.com/auth/gmail.readonly" in _SCOPES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_inbox_scopes.py -q`
Expected: FAIL on `test_gmail_send_scope_present` (scope not yet added).

- [ ] **Step 3: Add the scope**

In `api/auth_google.py`, change the `_SCOPES` list to include the send scope:

```python
_SCOPES = " ".join(
    [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar.readonly",
    ]
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_inbox_scopes.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add api/auth_google.py tests/test_inbox_scopes.py
git commit -m "feat(inbox): add gmail.send OAuth scope"
```

---

## Task 3: Gmail payload helpers (`core/inbox/threads.py`)

**Files:**
- Create: `core/inbox/__init__.py`
- Create: `core/inbox/threads.py`
- Test: `tests/test_inbox_threads.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_inbox_threads.py`:

```python
"""Pure helpers over Gmail message payloads — no network."""

import base64

from core.inbox.threads import extract_plain_body, latest_inbound_message


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode()


def test_extract_plain_body_simple():
    payload = {"mimeType": "text/plain", "body": {"data": _b64("Hello there")}}
    assert extract_plain_body(payload) == "Hello there"


def test_extract_plain_body_multipart_prefers_plain():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/html", "body": {"data": _b64("<p>HTML</p>")}},
            {"mimeType": "text/plain", "body": {"data": _b64("Plain wins")}},
        ],
    }
    assert extract_plain_body(payload) == "Plain wins"


def test_extract_plain_body_nested_multipart():
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    {"mimeType": "text/plain", "body": {"data": _b64("Nested plain")}},
                ],
            }
        ],
    }
    assert extract_plain_body(payload) == "Nested plain"


def test_extract_plain_body_missing_returns_empty():
    assert extract_plain_body({"mimeType": "text/html", "body": {}}) == ""


def test_latest_inbound_message_returns_latest_when_client_last():
    msgs = [
        {"id": "m1", "from_email": "client@acme.com", "internal_date": 100},
        {"id": "m2", "from_email": "rm@onedge.co", "internal_date": 200},
        {"id": "m3", "from_email": "client@acme.com", "internal_date": 300},
    ]
    out = latest_inbound_message(msgs, "rm@onedge.co")
    assert out is not None
    assert out["id"] == "m3"


def test_latest_inbound_message_none_when_rm_replied_last():
    msgs = [
        {"id": "m1", "from_email": "client@acme.com", "internal_date": 100},
        {"id": "m2", "from_email": "rm@onedge.co", "internal_date": 200},
    ]
    assert latest_inbound_message(msgs, "rm@onedge.co") is None


def test_latest_inbound_message_case_insensitive_rm_match():
    msgs = [{"id": "m1", "from_email": "RM@OnEdge.co", "internal_date": 200},
            {"id": "m0", "from_email": "client@acme.com", "internal_date": 100}]
    assert latest_inbound_message(msgs, "rm@onedge.co") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_inbox_threads.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.inbox'`.

- [ ] **Step 3: Create the package + implementation**

Create `core/inbox/__init__.py`:

```python
"""Inbox feature — unreplied client emails with AI-drafted replies."""
```

Create `core/inbox/threads.py`:

```python
"""
Pure helpers over Gmail message payloads. No network, no DB — unit-testable.

extract_plain_body walks a Gmail `payload` MIME tree and returns the decoded
text/plain content (preferred over text/html). latest_inbound_message decides
whether a thread is unreplied and, if so, which message to surface.
"""

from __future__ import annotations

import base64


def _decode(data: str) -> str:
    """Decode Gmail's base64url body data (tolerant of missing padding)."""
    if not data:
        return ""
    padding = "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(data + padding).decode("utf-8", errors="replace")
    except Exception:
        return ""


def extract_plain_body(payload: dict) -> str:
    """Return the text/plain body from a Gmail message payload, or "".

    Prefers text/plain; recurses into multipart containers. Returns the first
    text/plain part found in a depth-first walk.
    """
    mime = payload.get("mimeType", "")
    if mime == "text/plain":
        return _decode(payload.get("body", {}).get("data", "")).strip()
    for part in payload.get("parts", []) or []:
        found = extract_plain_body(part)
        if found:
            return found
    return ""


def latest_inbound_message(messages: list[dict], rm_email: str) -> dict | None:
    """Return the latest message if the thread is unreplied, else None.

    `messages` is a list of dicts with at least `from_email` and `internal_date`
    (int, ms since epoch). A thread is "unreplied" when its newest message is
    NOT from the RM (i.e. the client spoke last). Returns that newest message.
    """
    if not messages:
        return None
    newest = max(messages, key=lambda m: m["internal_date"])
    if newest.get("from_email", "").lower() == rm_email.lower():
        return None
    return newest
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_inbox_threads.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add core/inbox/__init__.py core/inbox/threads.py tests/test_inbox_threads.py
git commit -m "feat(inbox): pure Gmail payload helpers (body extract + unreplied detection)"
```

---

## Task 4: Reply generation (`core/inbox/reply.py`)

**Files:**
- Create: `core/inbox/reply.py`
- Test: `tests/test_inbox_reply.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_inbox_reply.py`:

```python
"""Reply prompt construction + draft parsing — Claude is mocked."""

import json

from core.inbox import reply as reply_mod
from core.inbox.reply import build_reply_prompt, parse_reply_response


def test_prompt_includes_style_account_and_body():
    p = build_reply_prompt(
        style_prompt="Warm and concise.",
        account_name="Acme Health",
        from_name="Jane Client",
        subject="Renewal timing",
        body="When does our contract renew?",
    )
    assert "Warm and concise." in p
    assert "Acme Health" in p
    assert "Jane Client" in p
    assert "When does our contract renew?" in p


def test_prompt_tone_formal_adds_instruction():
    p = build_reply_prompt(
        style_prompt="x", account_name="A", from_name="B",
        subject="s", body="b", tone="formal",
    )
    assert "formal" in p.lower()


def test_prompt_tone_shorter_and_warmer():
    assert "short" in build_reply_prompt(
        style_prompt="x", account_name="A", from_name="B", subject="s", body="b", tone="shorter"
    ).lower()
    assert "warm" in build_reply_prompt(
        style_prompt="x", account_name="A", from_name="B", subject="s", body="b", tone="warmer"
    ).lower()


def test_parse_reply_response_valid_json():
    raw = json.dumps({"reply": "Hi Jane,\n\nHappy to help.", "rationale": "Confirms renewal date."})
    out = parse_reply_response(raw)
    assert out["reply"].startswith("Hi Jane,")
    assert out["rationale"] == "Confirms renewal date."


def test_parse_reply_response_json_in_codefence():
    raw = "```json\n" + json.dumps({"reply": "R", "rationale": "X"}) + "\n```"
    out = parse_reply_response(raw)
    assert out["reply"] == "R"
    assert out["rationale"] == "X"


def test_parse_reply_response_falls_back_to_plain_text():
    out = parse_reply_response("just a plain reply, no json")
    assert out["reply"] == "just a plain reply, no json"
    assert out["rationale"] == ""


async def test_generate_reply_uses_mocked_claude(monkeypatch):
    captured = {}

    def fake_call(prompt: str) -> str:
        captured["prompt"] = prompt
        return json.dumps({"reply": "Drafted reply", "rationale": "Because reasons."})

    monkeypatch.setattr(reply_mod, "_call_claude", fake_call)

    out = await reply_mod.generate_reply(
        style_prompt="Warm.", account_name="Acme", from_name="Jane",
        subject="Hi", body="Question?",
    )
    assert out == {"reply": "Drafted reply", "rationale": "Because reasons."}
    assert "Acme" in captured["prompt"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_inbox_reply.py -q`
Expected: FAIL with `ModuleNotFoundError` / missing functions.

- [ ] **Step 3: Implement `core/inbox/reply.py`**

```python
"""
Draft a reply to a client email in the RM's voice.

build_reply_prompt assembles the prompt (pure). generate_reply runs Claude
(off-thread) and returns {"reply", "rationale"}. parse_reply_response is the
tolerant JSON parser used to read the model's structured output.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re

from core.llm.config import ANTHROPIC_SONNET, load_env

log = logging.getLogger(__name__)

_TONE_INSTRUCTIONS = {
    "formal": "Make the reply more formal and polished.",
    "shorter": "Make the reply noticeably shorter and more to the point.",
    "warmer": "Make the reply warmer and more personable.",
}


def build_reply_prompt(
    *,
    style_prompt: str,
    account_name: str,
    from_name: str,
    subject: str,
    body: str,
    tone: str | None = None,
) -> str:
    """Build the LLM prompt for drafting a reply in the RM's voice."""
    tone_line = ""
    if tone and tone in _TONE_INSTRUCTIONS:
        tone_line = f"\nADJUSTMENT: {_TONE_INSTRUCTIONS[tone]}\n"

    return (
        "You are a Relationship Manager at EDGE Solutions, a healthcare staffing company, "
        "drafting a reply to an email from your client.\n\n"
        f"YOUR WRITING STYLE (impersonate this exactly):\n{style_prompt}\n\n"
        f"CLIENT ACCOUNT: {account_name}\n"
        f"FROM: {from_name}\n"
        f"SUBJECT: {subject}\n\n"
        f"THE EMAIL YOU ARE REPLYING TO:\n{body}\n"
        f"{tone_line}\n"
        "Write a complete, ready-to-send reply email body (no subject line, no placeholders "
        "like [Name] — use the real names). Then give a one-sentence rationale explaining what "
        "the reply does.\n\n"
        'Respond ONLY with a JSON object: {"reply": "<the email body>", '
        '"rationale": "<one sentence>"}'
    )


def parse_reply_response(raw: str) -> dict:
    """Parse the model output into {"reply", "rationale"}; tolerant of code fences.

    Falls back to treating the whole text as the reply with an empty rationale.
    """
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else text
    try:
        obj = json.loads(candidate)
        return {
            "reply": str(obj.get("reply", "")).strip(),
            "rationale": str(obj.get("rationale", "")).strip(),
        }
    except (json.JSONDecodeError, AttributeError):
        return {"reply": text, "rationale": ""}


def _call_claude(prompt: str) -> str:
    load_env()
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    response = client.messages.create(
        model=ANTHROPIC_SONNET,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    block = response.content[0]
    return block.text if hasattr(block, "text") else ""  # type: ignore[union-attr]


async def generate_reply(
    *,
    style_prompt: str,
    account_name: str,
    from_name: str,
    subject: str,
    body: str,
    tone: str | None = None,
) -> dict:
    """Draft a reply; returns {"reply", "rationale"}. Empty reply on failure."""
    prompt = build_reply_prompt(
        style_prompt=style_prompt,
        account_name=account_name,
        from_name=from_name,
        subject=subject,
        body=body,
        tone=tone,
    )
    try:
        raw = await asyncio.to_thread(_call_claude, prompt)
    except Exception as exc:
        log.error("inbox reply generation failed: %s", exc)
        return {"reply": "", "rationale": ""}
    return parse_reply_response(raw)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_inbox_reply.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add core/inbox/reply.py tests/test_inbox_reply.py
git commit -m "feat(inbox): RM-voice reply generation with tone variants"
```

---

## Task 5: Reply send / MIME (`core/inbox/send.py`)

**Files:**
- Create: `core/inbox/send.py`
- Test: `tests/test_inbox_send.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_inbox_send.py`:

```python
"""Pure MIME construction for a threaded Gmail reply."""

import base64
from email.message import Message

from core.inbox.send import build_reply_raw


def _decode_raw(raw: str) -> Message:
    from email import message_from_bytes

    padded = raw + "=" * (-len(raw) % 4)
    return message_from_bytes(base64.urlsafe_b64decode(padded))


def test_build_reply_raw_sets_recipients_and_subject():
    raw = build_reply_raw(
        to_email="client@acme.com",
        from_email="rm@onedge.co",
        subject="Re: Renewal",
        body="Happy to help.",
        in_reply_to="<abc@mail.gmail.com>",
    )
    msg = _decode_raw(raw)
    assert msg["To"] == "client@acme.com"
    assert msg["From"] == "rm@onedge.co"
    assert msg["Subject"] == "Re: Renewal"
    assert "Happy to help." in msg.get_payload()


def test_build_reply_raw_adds_threading_headers():
    raw = build_reply_raw(
        to_email="c@acme.com", from_email="rm@onedge.co", subject="Re: x",
        body="b", in_reply_to="<abc@mail.gmail.com>",
    )
    msg = _decode_raw(raw)
    assert msg["In-Reply-To"] == "<abc@mail.gmail.com>"
    assert msg["References"] == "<abc@mail.gmail.com>"


def test_build_reply_raw_prefixes_re_once():
    raw = build_reply_raw(
        to_email="c@acme.com", from_email="rm@onedge.co", subject="Renewal",
        body="b", in_reply_to=None,
    )
    msg = _decode_raw(raw)
    assert msg["Subject"] == "Re: Renewal"


def test_build_reply_raw_keeps_existing_re():
    raw = build_reply_raw(
        to_email="c@acme.com", from_email="rm@onedge.co", subject="Re: Renewal",
        body="b", in_reply_to=None,
    )
    msg = _decode_raw(raw)
    assert msg["Subject"] == "Re: Renewal"


def test_build_reply_raw_omits_threading_when_no_message_id():
    raw = build_reply_raw(
        to_email="c@acme.com", from_email="rm@onedge.co", subject="Re: x",
        body="b", in_reply_to=None,
    )
    msg = _decode_raw(raw)
    assert msg["In-Reply-To"] is None
    assert msg["References"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_inbox_send.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `core/inbox/send.py`**

```python
"""
Send a threaded reply through Gmail as the RM.

build_reply_raw constructs the RFC-2822 MIME message (pure, unit-tested).
send_reply loads the inbox row, calls Gmail users.messages.send with the raw
message + threadId, and flips the row to 'sent'. A missing send scope (Gmail
403) surfaces as a 403 with detail 'reconnect_required'.
"""

from __future__ import annotations

import base64
import logging
from email.message import EmailMessage

import httpx
from fastapi import HTTPException
from psycopg.rows import dict_row

from core.db import get_pool
from core.google.auth import get_valid_token

log = logging.getLogger(__name__)

_GMAIL_SEND = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def build_reply_raw(
    *,
    to_email: str,
    from_email: str,
    subject: str,
    body: str,
    in_reply_to: str | None,
) -> str:
    """Return a base64url-encoded RFC-2822 reply message (Gmail `raw` field)."""
    msg = EmailMessage()
    msg["To"] = to_email
    msg["From"] = from_email
    subj = subject.strip()
    if not subj.lower().startswith("re:"):
        subj = f"Re: {subj}"
    msg["Subject"] = subj
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.set_content(body)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


async def send_reply(rm_user_id: str, email_id: str, text: str) -> str:
    """Send `text` as a threaded reply to the given inbox email. Returns Gmail id.

    Raises HTTPException(404) if the row isn't found/owned, 403 'reconnect_required'
    if Gmail rejects for missing scope, 502 on other Gmail errors.
    """
    token = await get_valid_token(rm_user_id)
    if not token:
        raise HTTPException(status_code=403, detail="reconnect_required")

    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        row = await (
            await conn.execute(
                "SELECT gmail_thread_id, rfc_message_id, from_email, subject "
                "FROM pulse.inbox_emails WHERE email_id = %s::uuid AND rm_user_id = %s",
                [email_id, rm_user_id],
            )
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="email not found")

    sess = None
    pool2 = await get_pool()
    async with pool2.connection() as conn:
        conn.row_factory = dict_row
        sess = await (
            await conn.execute(
                "SELECT email FROM pulse.google_sessions WHERE user_id = %s",
                [rm_user_id],
            )
        ).fetchone()
    from_email = sess["email"] if sess else rm_user_id

    raw = build_reply_raw(
        to_email=row["from_email"],
        from_email=from_email,
        subject=row["subject"] or "",
        body=text,
        in_reply_to=row["rfc_message_id"],
    )

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            _GMAIL_SEND,
            headers={"Authorization": f"Bearer {token}"},
            json={"raw": raw, "threadId": row["gmail_thread_id"]},
        )
    if res.status_code in (401, 403):
        log.warning("Gmail send rejected for %s: %s", rm_user_id, res.text)
        raise HTTPException(status_code=403, detail="reconnect_required")
    if not res.is_success:
        log.error("Gmail send error for %s: %s", rm_user_id, res.text)
        raise HTTPException(status_code=502, detail="send failed")

    sent_id = res.json().get("id", "")
    pool3 = await get_pool()
    async with pool3.connection() as conn:
        await conn.execute(
            "UPDATE pulse.inbox_emails SET reply_state='sent', sent_at=now(), "
            "sent_message_id=%s WHERE email_id=%s::uuid AND rm_user_id=%s",
            [sent_id, email_id, rm_user_id],
        )
        await conn.commit()
    return sent_id
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_inbox_send.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add core/inbox/send.py tests/test_inbox_send.py
git commit -m "feat(inbox): threaded Gmail reply send + MIME builder"
```

---

## Task 6: Inbox sync (`core/inbox/sync.py`)

**Files:**
- Create: `core/inbox/sync.py`
- Test: `tests/test_inbox_sync.py`

- [ ] **Step 1: Write the failing tests** (pure ownership filter)

Create `tests/test_inbox_sync.py`:

```python
"""Ownership filter for inbox sync — pure, no network."""

from core.inbox.sync import owned_account_ids


def _idx():
    return {
        "001": {"rm_name": "Eddy Chen", "name": "Acme", "tier": "Strategic", "risk": "High"},
        "002": {"rm_name": "Other RM", "name": "Beta", "tier": "Core", "risk": "Low"},
    }


def test_owned_account_ids_keeps_only_this_rms_accounts():
    entities = [{"type": "sf_account", "sfdc_id": "001"},
                {"type": "sf_account", "sfdc_id": "002"}]
    assert owned_account_ids(entities, _idx(), "Eddy Chen") == ["001"]


def test_owned_account_ids_case_insensitive():
    entities = [{"type": "sf_account", "sfdc_id": "001"}]
    assert owned_account_ids(entities, _idx(), "eddy chen") == ["001"]


def test_owned_account_ids_unknown_account_excluded():
    entities = [{"type": "sf_account", "sfdc_id": "999"}]
    assert owned_account_ids(entities, _idx(), "Eddy Chen") == []


def test_owned_account_ids_empty():
    assert owned_account_ids([], _idx(), "Eddy Chen") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_inbox_sync.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `core/inbox/sync.py`**

```python
"""
Sync one RM's unreplied client emails into pulse.inbox_emails, drafting a reply
for each newly-ingested message.

Flow per RM:
  1. resolve the RM's google_name + email,
  2. list recent INBOX threads,
  3. for each thread: keep only those whose newest message is from a client
     (unreplied) on an account this RM owns,
  4. fetch the full body, upsert the row, and generate a reply for new rows.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from email.utils import parseaddr

import httpx
from psycopg.rows import dict_row

from core.db import get_pool
from core.google.account_matcher import build_email_index, match_accounts
from core.google.auth import get_valid_token
from core.inbox.reply import generate_reply
from core.inbox.threads import extract_plain_body, latest_inbound_message

log = logging.getLogger(__name__)

_GMAIL = "https://gmail.googleapis.com/gmail/v1/users/me"
_LOOKBACK_DAYS = 14
_DEFAULT_STYLE = (
    "Write professionally and warmly. Use a friendly but concise tone. "
    "Keep responses focused and helpful."
)


def owned_account_ids(entities: list[dict], account_index: dict, rm_name: str) -> list[str]:
    """Account ids from `entities` that resolve to an account owned by `rm_name`."""
    out: list[str] = []
    target = rm_name.lower().strip()
    for e in entities:
        aid = e.get("sfdc_id")
        meta = account_index.get(aid)
        if meta and (meta.get("rm_name") or "").lower().strip() == target:
            out.append(aid)
    return out


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


async def _rm_identity(rm_user_id: str) -> dict | None:
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        return await (
            await conn.execute(
                "SELECT email, google_name FROM pulse.google_sessions WHERE user_id = %s",
                [rm_user_id],
            )
        ).fetchone()


async def _account_meta(account_ids: list[str]) -> dict:
    """Return {account_id: {rm_name, name, tier, risk}} for the given ids."""
    if not account_ids:
        return {}
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        rows = await (
            await conn.execute(
                "SELECT account_id, rm_name, name, tier, risk FROM pulse.sf_accounts "
                "WHERE account_id = ANY(%s)",
                [account_ids],
            )
        ).fetchall()
    return {r["account_id"]: dict(r) for r in rows}


async def sync_inbox(rm_user_id: str) -> dict:
    """Sync unreplied client emails for one RM. Returns counts."""
    token = await get_valid_token(rm_user_id)
    if not token:
        return {"threads": 0, "ingested": 0, "skipped": 0, "errors": 0}

    identity = await _rm_identity(rm_user_id)
    if not identity:
        return {"threads": 0, "ingested": 0, "skipped": 0, "errors": 0}
    rm_email = (identity["email"] or "").lower()
    rm_name = identity["google_name"] or ""

    email_index = await build_email_index()
    headers = {"Authorization": f"Bearer {token}"}
    since = (datetime.now(UTC) - timedelta(days=_LOOKBACK_DAYS)).strftime("%Y/%m/%d")
    query = f"in:inbox after:{since}"

    threads = ingested = skipped = errors = 0

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.get(
            f"{_GMAIL}/threads", headers=headers, params={"q": query, "maxResults": 100}
        )
        if not res.is_success:
            log.warning("inbox: thread list failed for %s: %s", rm_user_id, res.text)
            return {"threads": 0, "ingested": 0, "skipped": 0, "errors": 1}
        thread_stubs = res.json().get("threads", [])
        threads = len(thread_stubs)

        for stub in thread_stubs:
            try:
                tres = await client.get(
                    f"{_GMAIL}/threads/{stub['id']}", headers=headers, params={"format": "full"}
                )
                if not tres.is_success:
                    errors += 1
                    continue
                tmsgs = tres.json().get("messages", [])

                # Normalize messages for unreplied detection
                norm = []
                for m in tmsgs:
                    mh = m.get("payload", {}).get("headers", [])
                    _, from_addr = parseaddr(_header(mh, "From"))
                    norm.append(
                        {
                            "id": m["id"],
                            "from_email": from_addr.lower(),
                            "internal_date": int(m.get("internalDate", "0")),
                            "raw": m,
                        }
                    )

                newest = latest_inbound_message(norm, rm_email)
                if newest is None:
                    skipped += 1
                    continue

                msg = newest["raw"]
                mh = msg.get("payload", {}).get("headers", [])
                from_name, from_addr = parseaddr(_header(mh, "From"))
                entities = match_accounts([from_addr.lower()], email_index)
                meta_index = await _account_meta([e["sfdc_id"] for e in entities])
                owned = owned_account_ids(entities, meta_index, rm_name)
                if not owned:
                    skipped += 1
                    continue

                account_id = owned[0]
                body = extract_plain_body(msg.get("payload", {})) or msg.get("snippet", "")
                subject = _header(mh, "Subject") or None
                rfc_id = _header(mh, "Message-Id") or _header(mh, "Message-ID") or None
                received = datetime.fromtimestamp(int(msg.get("internalDate", "0")) / 1000, tz=UTC)

                inserted = await _upsert_email(
                    rm_user_id=rm_user_id,
                    gmail_message_id=msg["id"],
                    gmail_thread_id=stub["id"],
                    rfc_message_id=rfc_id,
                    account_id=account_id,
                    from_email=from_addr.lower(),
                    from_name=from_name or from_addr,
                    subject=subject,
                    body=body,
                    received_at=received,
                )
                if not inserted:
                    skipped += 1
                    continue

                # Generate a reply for the newly-inserted row
                acct = meta_index.get(account_id, {})
                style = await _load_style(rm_user_id)
                drafted = await generate_reply(
                    style_prompt=style,
                    account_name=acct.get("name", "your client"),
                    from_name=from_name or from_addr,
                    subject=subject or "",
                    body=body,
                )
                await _save_suggestion(
                    rm_user_id, msg["id"], drafted["reply"], drafted["rationale"]
                )
                ingested += 1
            except Exception as exc:
                log.error("inbox: thread %s error for %s: %s", stub.get("id"), rm_user_id, exc)
                errors += 1

    log.info(
        "inbox sync %s — threads=%d ingested=%d skipped=%d errors=%d",
        rm_user_id, threads, ingested, skipped, errors,
    )
    return {"threads": threads, "ingested": ingested, "skipped": skipped, "errors": errors}


async def _load_style(rm_user_id: str) -> str:
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        row = await (
            await conn.execute(
                "SELECT style_prompt FROM pulse.rm_style_profiles WHERE rm_pulse_user_id = %s",
                [rm_user_id],
            )
        ).fetchone()
    return row["style_prompt"] if row else _DEFAULT_STYLE


async def _upsert_email(**kw) -> bool:
    """Insert an inbox row; return True if newly inserted, False if it existed."""
    pool = await get_pool()
    async with pool.connection() as conn:
        row = await (
            await conn.execute(
                """
                INSERT INTO pulse.inbox_emails (
                    rm_user_id, gmail_message_id, gmail_thread_id, rfc_message_id,
                    account_id, from_email, from_name, subject, body, received_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (rm_user_id, gmail_message_id) DO NOTHING
                RETURNING email_id
                """,
                [
                    kw["rm_user_id"], kw["gmail_message_id"], kw["gmail_thread_id"],
                    kw["rfc_message_id"], kw["account_id"], kw["from_email"],
                    kw["from_name"], kw["subject"], kw["body"], kw["received_at"],
                ],
            )
        ).fetchone()
        await conn.commit()
    return row is not None


async def _save_suggestion(rm_user_id: str, gmail_message_id: str, reply: str, rationale: str) -> None:
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE pulse.inbox_emails SET suggested_reply=%s, reply_rationale=%s "
            "WHERE rm_user_id=%s AND gmail_message_id=%s",
            [reply, rationale, rm_user_id, gmail_message_id],
        )
        await conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_inbox_sync.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Run the full inbox suite + lint**

Run: `python3 -m pytest tests/test_inbox_*.py -q && python3 -m ruff check core/inbox api/inbox.py tests/test_inbox_*.py 2>/dev/null; python3 -m ruff check core/inbox`
Expected: tests PASS; ruff clean on `core/inbox`.

- [ ] **Step 6: Commit**

```bash
git add core/inbox/sync.py tests/test_inbox_sync.py
git commit -m "feat(inbox): sync unreplied client emails + draft replies"
```

---

## Task 7: Background sync loop + lifespan wiring

**Files:**
- Create: `core/inbox/loop.py`
- Modify: `api/main.py` (lifespan)

- [ ] **Step 1: Implement `core/inbox/loop.py`**

```python
"""
Background loop: sync every connected RM's inbox on an interval.

Enabled only when PULSE_INBOX_SYNC=1 so CI/local can opt out. Errors are isolated
per-user and logged; one user's failure never aborts the round.
"""

from __future__ import annotations

import asyncio
import logging
import os

log = logging.getLogger(__name__)

_INTERVAL_S = int(os.environ.get("PULSE_INBOX_SYNC_INTERVAL", "180"))


async def inbox_sync_loop() -> None:
    """Sync all connected RMs' inboxes every _INTERVAL_S seconds.

    Waits 200s at startup so SF contacts + google sessions are ready first.
    No-op unless PULSE_INBOX_SYNC=1.
    """
    if os.environ.get("PULSE_INBOX_SYNC") != "1":
        log.info("inbox sync loop disabled (set PULSE_INBOX_SYNC=1 to enable)")
        return
    await asyncio.sleep(200)
    from core.google.auth import list_connected_users
    from core.inbox.sync import sync_inbox

    while True:
        try:
            users = await list_connected_users()
            for u in users:
                try:
                    await sync_inbox(u["user_id"])
                except Exception as exc:
                    log.error("inbox sync failed for %s: %s", u["user_id"], exc)
        except Exception as exc:
            log.error("inbox sync loop error: %s", exc)
        await asyncio.sleep(_INTERVAL_S)
```

- [ ] **Step 2: Wire into `api/main.py` lifespan**

In `api/main.py`, in `lifespan`, after `eis_task = asyncio.create_task(_expansion_intent_poll_loop())`, add:

```python
    from core.inbox.loop import inbox_sync_loop

    inbox_task = asyncio.create_task(inbox_sync_loop())
```

Then add `inbox_task` to BOTH cleanup tuples (the `.cancel()` loop and the `await task` loop), so they read:

```python
    for task in (sf_task, sf_contacts_task, chorus_task, zoom_task, google_task, eis_task, inbox_task):
        task.cancel()
    for task in (sf_task, sf_contacts_task, chorus_task, zoom_task, google_task, eis_task, inbox_task):
        try:
            await task
        except asyncio.CancelledError:
            pass
```

- [ ] **Step 3: Verify import + lint**

Run: `python3 -c "import ast; ast.parse(open('api/main.py').read()); print('ok')" && python3 -m ruff check core/inbox/loop.py api/main.py`
Expected: `ok` and ruff clean.

- [ ] **Step 4: Commit**

```bash
git add core/inbox/loop.py api/main.py
git commit -m "feat(inbox): background sync loop wired into app lifespan (env-gated)"
```

---

## Task 8: Inbox API router (`api/inbox.py`)

**Files:**
- Create: `api/inbox.py`
- Modify: `api/main.py` (register router)

- [ ] **Step 1: Implement `api/inbox.py`**

```python
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
                       a.tier, a.risk
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
                       i.draft_reply, a.tier, a.risk
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
async def dismiss(
    email_id: str, caller: Annotated[Caller, Depends(require_caller)]
) -> dict:
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
```

- [ ] **Step 2: Register the router in `api/main.py`**

In `create_app()`, add the import alongside the others:

```python
    from api.inbox import router as inbox_router
```

and register it (after `app.include_router(accounts_router)`):

```python
    app.include_router(inbox_router)
```

- [ ] **Step 3: Verify import + lint**

Run: `python3 -c "import ast; ast.parse(open('api/inbox.py').read()); print('ok')" && python3 -m ruff check api/inbox.py api/main.py`
Expected: `ok` and ruff clean.

- [ ] **Step 4: Commit**

```bash
git add api/inbox.py api/main.py
git commit -m "feat(inbox): /inbox API router (list, detail, draft, regenerate, reply, dismiss)"
```

---

## Task 9: Frontend API client methods + types

**Files:**
- Modify: `front/src/lib/api.ts`
- Create: `front/src/features/inbox/types.ts`

- [ ] **Step 1: Create `front/src/features/inbox/types.ts`**

```typescript
export interface InboxEmailDTO {
  email_id: string;
  from_email: string;
  from_name: string | null;
  subject: string | null;
  snippet: string;
  received_at: string;
  account_id: string | null;
  tier: string | null;
  risk: "Low" | "Medium" | "High" | null;
  has_draft: boolean;
}

export interface InboxEmailDetailDTO extends InboxEmailDTO {
  body: string;
  suggested_reply: string | null;
  reply_rationale: string | null;
  draft_reply: string | null;
}

export interface InboxListDTO {
  emails: InboxEmailDTO[];
  count: number;
}

export type ReplyTone = "formal" | "shorter" | "warmer";
```

- [ ] **Step 2: Add client methods to `front/src/lib/api.ts`**

Inside the `export const api = { ... }` object (before the closing `};` at line ~286), add:

```typescript
  listInbox: (caller: ApiCaller) =>
    request<import("@/features/inbox/types").InboxListDTO>("/inbox", caller),

  syncInbox: (caller: ApiCaller) =>
    request<import("@/features/inbox/types").InboxListDTO>("/inbox/sync", caller, {
      method: "POST",
    }),

  getInboxEmail: (caller: ApiCaller, emailId: string) =>
    request<import("@/features/inbox/types").InboxEmailDetailDTO>(`/inbox/${emailId}`, caller),

  saveInboxDraft: (caller: ApiCaller, emailId: string, text: string) =>
    request<{ saved: boolean }>(`/inbox/${emailId}/draft`, caller, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  regenerateInboxReply: (
    caller: ApiCaller,
    emailId: string,
    tone?: import("@/features/inbox/types").ReplyTone,
  ) =>
    request<{ reply: string; rationale: string }>(`/inbox/${emailId}/regenerate`, caller, {
      method: "POST",
      body: JSON.stringify({ tone: tone ?? null }),
    }),

  sendInboxReply: (caller: ApiCaller, emailId: string, text: string) =>
    request<{ sent_message_id: string }>(`/inbox/${emailId}/reply`, caller, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  dismissInboxEmail: (caller: ApiCaller, emailId: string) =>
    request<{ dismissed: boolean }>(`/inbox/${emailId}/dismiss`, caller, {
      method: "POST",
    }),
```

- [ ] **Step 3: Verify type-check**

Run: `cd front && node_modules/.bin/tsc -b && cd ..`
Expected: no errors (note: `types.ts` is referenced by the dynamic imports; this compiles even before `hooks.ts` exists).

- [ ] **Step 4: Commit**

```bash
git add front/src/lib/api.ts front/src/features/inbox/types.ts
git commit -m "feat(inbox): frontend API client methods + DTO types"
```

---

## Task 10: Frontend hooks (`features/inbox/hooks.ts`)

**Files:**
- Create: `front/src/features/inbox/hooks.ts`

- [ ] **Step 1: Implement `front/src/features/inbox/hooks.ts`**

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useUser } from "@/lib/auth/AuthContext";
import type { InboxListDTO, InboxEmailDetailDTO, ReplyTone } from "./types";

const INBOX_KEY = ["inbox"] as const;

export function useInbox() {
  const user = useUser();
  return useQuery({
    queryKey: [...INBOX_KEY, "list"],
    queryFn: () => api.listInbox(user) as Promise<InboxListDTO>,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useInboxEmail(emailId: string | null) {
  const user = useUser();
  return useQuery({
    queryKey: [...INBOX_KEY, "detail", emailId],
    queryFn: () => api.getInboxEmail(user, emailId!) as Promise<InboxEmailDetailDTO>,
    enabled: !!emailId,
    staleTime: 0,
  });
}

export function useSaveDraft() {
  const user = useUser();
  return useMutation({
    mutationFn: ({ emailId, text }: { emailId: string; text: string }) =>
      api.saveInboxDraft(user, emailId, text),
  });
}

export function useRegenerate() {
  const user = useUser();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ emailId, tone }: { emailId: string; tone?: ReplyTone }) =>
      api.regenerateInboxReply(user, emailId, tone),
    onSuccess: (_d, vars) =>
      qc.invalidateQueries({ queryKey: [...INBOX_KEY, "detail", vars.emailId] }),
  });
}

export function useSendReply() {
  const user = useUser();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ emailId, text }: { emailId: string; text: string }) =>
      api.sendInboxReply(user, emailId, text),
    onSuccess: () => qc.invalidateQueries({ queryKey: INBOX_KEY }),
  });
}

export function useDismiss() {
  const user = useUser();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (emailId: string) => api.dismissInboxEmail(user, emailId),
    onSuccess: () => qc.invalidateQueries({ queryKey: INBOX_KEY }),
  });
}
```

- [ ] **Step 2: Verify type-check**

Run: `cd front && node_modules/.bin/tsc -b && cd ..`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add front/src/features/inbox/hooks.ts
git commit -m "feat(inbox): TanStack Query hooks for inbox list/detail/actions"
```

---

## Task 11: Inbox page UI (`features/inbox/InboxPage.tsx`)

**Files:**
- Create: `front/src/features/inbox/InboxPage.tsx`

This is the showcase surface: a list-plus-detail layout (mirroring `SupportPage`) with risk-sorted rows, an account-context card (reusing `useAccountHealth`), an editable draft pre-filled with `draft_reply ?? suggested_reply`, tone chips, a "Why this draft" line, and a Send button (⌘/Ctrl+Enter), plus reconnect handling on a 403.

- [ ] **Step 1: Implement `front/src/features/inbox/InboxPage.tsx`**

```tsx
import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Sparkles, Send, RefreshCw, X } from "lucide-react";
import { Link } from "react-router-dom";
import { ApiError } from "@/lib/api";
import { useAccountHealth } from "@/features/account/hooks";
import {
  useInbox,
  useInboxEmail,
  useSaveDraft,
  useRegenerate,
  useSendReply,
  useDismiss,
} from "./hooks";
import type { InboxEmailDTO, ReplyTone } from "./types";

const RISK_ACCENT: Record<string, string> = {
  High: "border-l-risk-high-fg",
  Medium: "border-l-amber-500",
  Low: "border-l-line-strong",
};

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 60) return `${Math.max(mins, 1)}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

function initials(name: string | null, email: string): string {
  const src = (name || email).trim();
  const parts = src.split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || email[0]?.toUpperCase() || "?";
}

export function InboxPage() {
  const { data, isLoading } = useInbox();
  const emails = useMemo(() => data?.emails ?? [], [data]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedId && emails.length) setSelectedId(emails[0].email_id);
    if (selectedId && !emails.some((e) => e.email_id === selectedId)) {
      setSelectedId(emails[0]?.email_id ?? null);
    }
  }, [emails, selectedId]);

  return (
    <div className="grid h-[calc(100vh-64px)] grid-cols-12 overflow-hidden">
      <aside className="col-span-12 overflow-y-auto border-r border-line-subtle lg:col-span-4">
        <div className="flex items-center justify-between p-6 pb-3">
          <h1 className="text-lg font-semibold uppercase tracking-[0.18em]">Inbox</h1>
          <span className="text-xs text-ink-secondary">{emails.length} to reply</span>
        </div>
        {isLoading && <p className="px-6 text-sm text-ink-secondary">Loading…</p>}
        {!isLoading && emails.length === 0 && (
          <div className="mx-6 flex items-center gap-2 rounded-3xl bg-surface-tinted-row p-4 text-sm">
            <Sparkles className="h-4 w-4 text-brand" />
            You're all caught up — new client emails will appear here.
          </div>
        )}
        <div className="space-y-1 px-3 pb-6">
          <AnimatePresence initial={false}>
            {emails.map((e) => (
              <motion.button
                key={e.email_id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -20 }}
                onClick={() => setSelectedId(e.email_id)}
                className={`flex w-full gap-3 rounded-2xl border-l-2 ${
                  RISK_ACCENT[e.risk ?? "Low"]
                } p-3 text-left transition ${
                  selectedId === e.email_id ? "bg-brand-muted" : "hover:bg-brand-ghost"
                }`}
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-card text-xs font-semibold text-ink-secondary">
                  {initials(e.from_name, e.from_email)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium">{e.from_name ?? e.from_email}</span>
                    <span className="shrink-0 text-[10px] text-ink-secondary">{relativeTime(e.received_at)}</span>
                  </span>
                  <span className="block truncate text-xs font-medium text-ink-primary">{e.subject ?? "(no subject)"}</span>
                  <span className="block truncate text-xs text-ink-secondary">{e.snippet}</span>
                  {e.has_draft && (
                    <span className="mt-1 inline-block rounded-full bg-brand-ghost px-2 py-0.5 text-[10px] text-brand">
                      AI reply ready
                    </span>
                  )}
                </span>
              </motion.button>
            ))}
          </AnimatePresence>
        </div>
      </aside>

      <section className="col-span-12 overflow-y-auto lg:col-span-8">
        {selectedId ? (
          <EmailDetail key={selectedId} emailId={selectedId} summary={emails.find((e) => e.email_id === selectedId)} />
        ) : (
          <p className="p-6 text-sm text-ink-secondary">Select an email to view.</p>
        )}
      </section>
    </div>
  );
}

function AccountContextCard({ accountId }: { accountId: string | null }) {
  const { data } = useAccountHealth(accountId);
  if (!accountId || !data) return null;
  return (
    <div className="mb-5 flex flex-wrap items-center gap-3 rounded-2xl bg-surface-tinted-row p-4 text-xs">
      <span className="text-sm font-semibold">{data.name}</span>
      <span className="rounded-full bg-surface-card px-2 py-0.5">{data.tier}</span>
      <span
        className={`rounded-full px-2 py-0.5 ${
          data.risk === "High" ? "bg-risk-high-bg text-risk-high-fg" : "bg-surface-card"
        }`}
      >
        {data.risk} risk
      </span>
      <span className="text-ink-secondary">Health {Math.round(data.composite_health)}/10</span>
      <span className="text-ink-secondary">${(data.arr_usd / 1000).toFixed(0)}k ARR</span>
      <Link to="/accounts" className="ml-auto text-brand hover:underline">
        View account →
      </Link>
    </div>
  );
}

function EmailDetail({ emailId, summary }: { emailId: string; summary?: InboxEmailDTO }) {
  const { data: email, isLoading } = useInboxEmail(emailId);
  const saveDraft = useSaveDraft();
  const regenerate = useRegenerate();
  const sendReply = useSendReply();
  const dismiss = useDismiss();

  const [text, setText] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const [reconnect, setReconnect] = useState(false);

  useEffect(() => {
    if (email) setText(email.draft_reply ?? email.suggested_reply ?? "");
  }, [email]);

  if (isLoading || !email) return <p className="p-6 text-sm text-ink-secondary">Loading…</p>;

  const onBlurSave = () => {
    if (text && text !== (email.draft_reply ?? email.suggested_reply ?? "")) {
      saveDraft.mutate({ emailId, text });
    }
  };

  const onRegenerate = (tone?: ReplyTone) =>
    regenerate.mutate(
      { emailId, tone },
      { onSuccess: (d) => setText(d.reply) },
    );

  const onSend = () => {
    setReconnect(false);
    sendReply.mutate(
      { emailId, text },
      {
        onSuccess: () => setToast(`Reply sent to ${summary?.from_name ?? email.from_email}`),
        onError: (err) => {
          if (err instanceof ApiError && err.status === 403) setReconnect(true);
          else setToast("Send failed — try again.");
        },
      },
    );
  };

  return (
    <div className="p-6">
      <AccountContextCard accountId={email.account_id} />

      <div className="mb-4">
        <h2 className="text-base font-semibold">{email.subject ?? "(no subject)"}</h2>
        <p className="text-xs text-ink-secondary">
          From {email.from_name ?? email.from_email} &lt;{email.from_email}&gt;
        </p>
      </div>

      <div className="mb-6 whitespace-pre-wrap rounded-2xl border border-line-subtle bg-surface-card p-4 text-sm leading-relaxed">
        {email.body}
      </div>

      <div className="rounded-2xl border border-line-strong bg-surface-card p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-ink-secondary">
            Re: {email.subject ?? ""} · To: {email.from_email}
          </span>
          <div className="flex gap-1">
            {(["formal", "shorter", "warmer"] as ReplyTone[]).map((t) => (
              <button
                key={t}
                onClick={() => onRegenerate(t)}
                disabled={regenerate.isPending}
                className="rounded-full bg-brand-ghost px-2 py-0.5 text-[11px] capitalize text-brand hover:bg-brand-muted disabled:opacity-50"
              >
                {t}
              </button>
            ))}
            <button
              onClick={() => onRegenerate()}
              disabled={regenerate.isPending}
              className="flex items-center gap-1 rounded-full bg-brand-ghost px-2 py-0.5 text-[11px] text-brand hover:bg-brand-muted disabled:opacity-50"
            >
              <RefreshCw className={`h-3 w-3 ${regenerate.isPending ? "animate-spin" : ""}`} />
              Regenerate
            </button>
          </div>
        </div>

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onBlur={onBlurSave}
          onKeyDown={(e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === "Enter") onSend();
          }}
          rows={8}
          placeholder={regenerate.isPending ? "Drafting…" : "Write your reply…"}
          className="w-full resize-none rounded-xl border border-line-subtle bg-surface-base p-3 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
        />

        {email.reply_rationale && (
          <p className="mt-2 text-[11px] italic text-ink-secondary">Why this draft: {email.reply_rationale}</p>
        )}

        <div className="mt-3 flex items-center gap-2">
          {reconnect ? (
            <button
              onClick={() => {
                const apiBase = import.meta.env.VITE_API_BASE ?? "/api";
                window.location.href = `${apiBase}/auth/google/start`;
              }}
              className="rounded-full bg-brand px-4 py-1.5 text-sm font-medium text-white"
            >
              Reconnect Google to send
            </button>
          ) : (
            <button
              onClick={onSend}
              disabled={sendReply.isPending || !text.trim()}
              className="flex items-center gap-2 rounded-full bg-brand px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              {sendReply.isPending ? "Sending…" : "Send"}
            </button>
          )}
          <button
            onClick={() => dismiss.mutate(emailId)}
            disabled={dismiss.isPending}
            className="flex items-center gap-1 rounded-full px-3 py-1.5 text-sm text-ink-secondary hover:bg-brand-ghost"
          >
            <X className="h-4 w-4" />
            Dismiss
          </button>
          <span className="ml-auto text-[11px] text-ink-secondary">⌘/Ctrl+Enter to send</span>
        </div>
      </div>

      {toast && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 rounded-xl bg-surface-tinted-row p-3 text-sm text-ink-primary"
        >
          {toast}
        </motion.div>
      )}
    </div>
  );
}
```

> If `lucide-react` lacks any named icon above, substitute one that exists (the codebase already imports `Send` and `Sparkles`). The reconnect button reuses the verified login pattern from `LoginPage.tsx` (`${VITE_API_BASE}/auth/google/start`).

- [ ] **Step 2: Verify type-check**

Run: `cd front && node_modules/.bin/tsc -b && cd ..`
Expected: no errors. Fix any type mismatches (e.g. `AccountHealthDTO` field names) against `front/src/lib/api.ts`.

- [ ] **Step 3: Commit**

```bash
git add front/src/features/inbox/InboxPage.tsx
git commit -m "feat(inbox): Inbox page UI — risk-sorted list, account card, tone controls, send"
```

---

## Task 12: Nav item, unread badge, and route

**Files:**
- Modify: `front/src/components/Header.tsx`
- Modify: `front/src/App.tsx`

- [ ] **Step 1: Add the nav entry in `Header.tsx`**

In the `NAV` array (line ~24), add after the Constellation entry:

```typescript
  { to: "/inbox", label: "Inbox", roles: ["rm", "manager", "executive", "admin"] },
```

- [ ] **Step 2: Add an unread badge to the nav label**

At the top of `Header.tsx`, add the hook import:

```typescript
import { useInbox } from "@/features/inbox/hooks";
```

Inside the `Header` component body, before the `return`, read the count:

```typescript
  const { data: inboxData } = useInbox();
  const inboxCount = inboxData?.count ?? 0;
```

In the nav-rendering `.map((item) => ...)` (around line 75-88), replace the `{item.label}` line with a version that appends a badge for the Inbox item:

```tsx
              {item.label}
              {item.to === "/inbox" && inboxCount > 0 && (
                <span className="ml-1.5 rounded-full bg-brand px-1.5 py-0.5 text-[10px] font-semibold text-white">
                  {inboxCount}
                </span>
              )}
```

> Note: `useInbox` calls `useUser()`, which is valid here because `Header` only renders inside the authenticated `AppShell`. If `tsc` or runtime complains about user context, guard with the existing `user` already available in `Header`.

- [ ] **Step 3: Add the route in `App.tsx`**

Add the import near the other feature imports (line ~19):

```typescript
import { InboxPage } from "@/features/inbox/InboxPage";
```

Add the route inside the authenticated `<Route element={<AppShell />}>` block, following the Constellation/Actions pattern:

```tsx
          <Route
            path="/inbox"
            element={
              <RoleGuard allowedRoles={["rm", "manager", "executive", "admin"]}>
                <InboxPage />
              </RoleGuard>
            }
          />
```

- [ ] **Step 4: Verify type-check**

Run: `cd front && node_modules/.bin/tsc -b && cd ..`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add front/src/components/Header.tsx front/src/App.tsx
git commit -m "feat(inbox): add Inbox nav item with unread badge + /inbox route"
```

---

## Task 13: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Backend — tests, lint, format**

Run:
```bash
python3 -m pytest tests/test_inbox_*.py -q
python3 -m ruff check .
python3 -m ruff format --check .
```
Expected: all inbox tests PASS; ruff check "All checks passed!"; format clean. If format flags files, run `python3 -m ruff format .` and re-commit.

- [ ] **Step 2: Frontend — full build (matches CI)**

Run:
```bash
cd front && node_modules/.bin/tsc -b && node_modules/.bin/vite build && cd ..
```
Expected: tsc no errors; vite build succeeds.

- [ ] **Step 3: Full backend test suite (no regressions)**

Run: `python3 -m pytest -q`
Expected: same pass/skip profile as the pre-change baseline (no new failures).

- [ ] **Step 4: Commit any format fixes**

```bash
git add -A
git commit -m "chore(inbox): formatting + verification fixes" || echo "nothing to commit"
```

---

## Done criteria

- `/inbox` returns the caller's pending unreplied client emails, risk-sorted, with pre-generated drafts and rationale.
- The Inbox tab renders list + detail with account-context card, editable draft, tone chips, draft autosave, Send (⌘/Ctrl+Enter), Dismiss, and unread badge.
- Send dispatches a threaded Gmail reply as the RM and removes the row from the pending list; a missing send scope shows "Reconnect Google to send".
- The background loop syncs all connected RMs when `PULSE_INBOX_SYNC=1`.
- `ruff check`, `ruff format --check`, `pyright`/`tsc`, and `pytest` all pass.
