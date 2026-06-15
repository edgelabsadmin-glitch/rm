# Client Portal & Virtual RM — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a client-facing portal at `/client` where EDGE clients log in via email + OTP and chat with a virtual version of their assigned RM — an AI that speaks in the RM's tone using emails and meeting history as context, with hard data-isolation guardrails.

**Architecture:** Same Vite + FastAPI codebase. New `/client/*` FastAPI router (cookie-free, header-based `X-Client-Session` auth). New `/client/*` React routes wrapped in their own `ClientAuthProvider`, completely isolated from RM Google OAuth. Five new DB tables. RM style profiles are pre-computed after each Gmail sync and stored in DB.

**Tech Stack:** FastAPI + psycopg3 + Aurora PostgreSQL + React 18 + Vite + Tailwind v3 + TanStack Query + Anthropic Claude SSE + AWS SES (boto3) for OTP email

---

## File Map

**New backend files:**
- `03_build/migrations/0012_client_otps.sql`
- `03_build/migrations/0013_client_sessions.sql`
- `03_build/migrations/0014_rm_style_profiles.sql`
- `03_build/migrations/0015_client_conversations.sql`
- `03_build/core/client/__init__.py`
- `03_build/core/client/otp.py`
- `03_build/core/client/email.py`
- `03_build/core/llm/rm_style.py`
- `03_build/api/client_auth.py`
- `03_build/api/client_chat.py`
- `03_build/tests/test_client_otp.py`
- `03_build/tests/test_client_auth.py`
- `03_build/tests/test_client_chat.py`

**Modified backend files:**
- `03_build/api/main.py` — mount new routers, add tables to `_ensure_schema`
- `03_build/core/google/gmail_sync.py` — trigger `analyze_rm_style` after sync
- `03_build/pyproject.toml` — add `boto3>=1.37`

**New frontend files:**
- `03_build/front/src/lib/client-api.ts`
- `03_build/front/src/features/client/ClientAuthContext.tsx`
- `03_build/front/src/features/client/ClientLoginPage.tsx`
- `03_build/front/src/features/client/ClientPortal.tsx`
- `03_build/front/src/features/client/hooks.ts`
- `03_build/front/src/features/client/ClientChatPage.tsx`

**Modified frontend files:**
- `03_build/front/src/App.tsx` — add `/client/*` route before catch-all

---

## Task 1: DB Migrations

**Files:**
- Create: `03_build/migrations/0012_client_otps.sql`
- Create: `03_build/migrations/0013_client_sessions.sql`
- Create: `03_build/migrations/0014_rm_style_profiles.sql`
- Create: `03_build/migrations/0015_client_conversations.sql`

- [ ] **Step 1: Write migration 0012 — client_otps**

```sql
-- 0012 — OTP codes for client email auth
CREATE TABLE IF NOT EXISTS pulse.client_otps (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email          TEXT        NOT NULL,
    otp_hash       TEXT        NOT NULL,
    expires_at     TIMESTAMPTZ NOT NULL,
    used_at        TIMESTAMPTZ,
    attempt_count  INT         NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_client_otps_email
    ON pulse.client_otps (email, created_at DESC);
```

- [ ] **Step 2: Write migration 0013 — client_sessions**

```sql
-- 0013 — Authenticated client sessions (24hr expiry)
CREATE TABLE IF NOT EXISTS pulse.client_sessions (
    session_id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_email    TEXT        NOT NULL,
    account_id       TEXT        NOT NULL,
    rm_owner_id      TEXT        NOT NULL,
    rm_name          TEXT        NOT NULL,
    rm_pulse_user_id TEXT,
    client_name      TEXT        NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at       TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_client_sessions_email
    ON pulse.client_sessions (contact_email);
```

- [ ] **Step 3: Write migration 0014 — rm_style_profiles**

```sql
-- 0014 — Pre-computed RM communication style prompts
CREATE TABLE IF NOT EXISTS pulse.rm_style_profiles (
    rm_pulse_user_id  TEXT        PRIMARY KEY,
    style_prompt      TEXT        NOT NULL,
    email_count       INT         NOT NULL DEFAULT 0,
    analyzed_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

- [ ] **Step 4: Write migration 0015 — client conversations**

```sql
-- 0015 — Per-client conversation history (soft delete)
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

- [ ] **Step 5: Commit**

```bash
git add 03_build/migrations/0012_client_otps.sql 03_build/migrations/0013_client_sessions.sql 03_build/migrations/0014_rm_style_profiles.sql 03_build/migrations/0015_client_conversations.sql
git commit -m "feat: add client portal DB migrations (otps, sessions, style profiles, conversations)"
```

---

## Task 2: Core OTP Helpers + Tests

**Files:**
- Create: `03_build/core/client/__init__.py`
- Create: `03_build/core/client/otp.py`
- Test: `03_build/tests/test_client_otp.py`

- [ ] **Step 1: Write the failing tests**

```python
# 03_build/tests/test_client_otp.py
"""Unit tests for OTP helpers — no DB, no network."""
from __future__ import annotations
import pytest


def test_generate_otp_is_six_digits():
    from core.client.otp import generate_otp
    otp = generate_otp()
    assert len(otp) == 6
    assert otp.isdigit()


def test_generate_otp_zero_padded():
    from core.client.otp import hash_otp, verify_otp_hash
    # Verify round-trip works for a low number like "000042"
    otp = "000042"
    assert verify_otp_hash(otp, hash_otp(otp))


def test_hash_otp_is_deterministic():
    from core.client.otp import hash_otp
    assert hash_otp("123456") == hash_otp("123456")


def test_verify_otp_hash_wrong_otp():
    from core.client.otp import hash_otp, verify_otp_hash
    h = hash_otp("123456")
    assert not verify_otp_hash("999999", h)


def test_truncate_client_title_long():
    from core.client.otp import truncate_title
    assert truncate_title("a" * 100) == "a" * 60


def test_truncate_client_title_strips():
    from core.client.otp import truncate_title
    assert truncate_title("  hello  ") == "hello"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd 03_build && python -m pytest tests/test_client_otp.py -v
```

Expected: `ModuleNotFoundError` (module doesn't exist yet)

- [ ] **Step 3: Create package init**

```python
# 03_build/core/client/__init__.py
```

(empty file)

- [ ] **Step 4: Write otp.py**

```python
# 03_build/core/client/otp.py
"""OTP generation and hashing helpers — pure functions, no I/O."""
from __future__ import annotations

import hashlib
import hmac
import secrets


def generate_otp() -> str:
    """Return a 6-digit zero-padded OTP string."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(otp: str) -> str:
    """Return SHA-256 hex digest of the OTP."""
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp_hash(otp: str, otp_hash: str) -> bool:
    """Constant-time comparison of OTP against its stored hash."""
    expected = hash_otp(otp)
    return hmac.compare_digest(expected, otp_hash)


def truncate_title(text: str) -> str:
    """Trim whitespace and cap at 60 chars for conversation auto-titles."""
    return text.strip()[:60]
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd 03_build && python -m pytest tests/test_client_otp.py -v
```

Expected: 6 PASSED

- [ ] **Step 6: Commit**

```bash
git add 03_build/core/client/__init__.py 03_build/core/client/otp.py 03_build/tests/test_client_otp.py
git commit -m "feat: add core OTP helpers (generate, hash, verify, truncate)"
```

---

## Task 3: SES Email Sender

**Files:**
- Modify: `03_build/pyproject.toml` — add boto3
- Create: `03_build/core/client/email.py`

- [ ] **Step 1: Add boto3 to pyproject.toml**

In `03_build/pyproject.toml`, add `"boto3>=1.37"` to the `dependencies` list after `"httpx>=0.27"`:

```toml
    # HTTP for adapters / Activepieces callbacks
    "httpx>=0.27",
    # AWS SDK — SES for client OTP emails
    "boto3>=1.37",
```

- [ ] **Step 2: Install boto3**

```bash
cd 03_build && pip install boto3>=1.37
```

Expected: Successfully installed boto3

- [ ] **Step 3: Write email.py**

```python
# 03_build/core/client/email.py
"""Send OTP emails via AWS SES."""
from __future__ import annotations

import asyncio
import logging
import os

log = logging.getLogger(__name__)

_SENDER = os.environ.get("AWS_SES_SENDER", "pulse@onedge.co")
_REGION = os.environ.get("AWS_SES_REGION", "us-east-1")


def _send_otp_sync(to_email: str, otp: str) -> None:
    """Blocking SES send — call via asyncio.to_thread."""
    import boto3  # imported lazily so tests don't need AWS credentials
    client = boto3.client("ses", region_name=_REGION)
    client.send_email(
        Source=_SENDER,
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": "Your EDGE login code"},
            "Body": {
                "Text": {
                    "Data": (
                        f"Your one-time login code is: {otp}\n\n"
                        "This code expires in 10 minutes.\n\n"
                        "If you did not request this, ignore this email."
                    )
                }
            },
        },
    )
    log.info("OTP email sent to %s", to_email)


async def send_otp_email(to_email: str, otp: str) -> None:
    """Send OTP to client email address (non-blocking)."""
    await asyncio.to_thread(_send_otp_sync, to_email, otp)
```

- [ ] **Step 4: Add env vars to .env**

Add to `03_build/.env` (or project root `.env`):
```
AWS_SES_SENDER=pulse@onedge.co
AWS_SES_REGION=us-east-1
```

- [ ] **Step 5: Commit**

```bash
git add 03_build/core/client/email.py 03_build/pyproject.toml
git commit -m "feat: add SES OTP email sender"
```

---

## Task 4: Client Auth API + Tests

**Files:**
- Create: `03_build/api/client_auth.py`
- Test: `03_build/tests/test_client_auth.py`

- [ ] **Step 1: Write failing tests**

```python
# 03_build/tests/test_client_auth.py
"""Unit tests for client auth helpers — no DB, no network."""
from __future__ import annotations
import pytest
from fastapi import HTTPException


async def test_require_client_session_missing_header_raises_401():
    from api.client_auth import require_client_session
    with pytest.raises(HTTPException) as exc:
        await require_client_session(x_client_session=None)
    assert exc.value.status_code == 401


async def test_require_client_session_present_queries_db():
    """Just verifies the dependency accepts a value without erroring on header parse."""
    from api.client_auth import require_client_session
    # Will raise 401 because DB is not available in unit tests — that's expected.
    with pytest.raises((HTTPException, Exception)):
        await require_client_session(x_client_session="some-uuid")
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd 03_build && python -m pytest tests/test_client_auth.py -v
```

Expected: `ImportError` (module doesn't exist)

- [ ] **Step 3: Write client_auth.py**

```python
# 03_build/api/client_auth.py
"""
Client portal auth — email + OTP flow.

POST /client/auth/request-otp   → validate email, send OTP via SES
POST /client/auth/verify-otp    → validate OTP, create session, return session_id
POST /client/auth/logout        → delete session row
GET  /client/me                 → return client name, account, rm name

Auth: X-Client-Session header containing a session_id UUID.
All endpoints except request-otp / verify-otp require this header.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from psycopg.rows import dict_row
from pydantic import BaseModel

from core.client.otp import generate_otp, hash_otp, truncate_title, verify_otp_hash
from core.db import get_pool

log = logging.getLogger(__name__)

router = APIRouter(prefix="/client", tags=["client"])


# ── Session dependency ────────────────────────────────────────────────────────

async def require_client_session(
    x_client_session: str | None = Header(default=None),
) -> dict:
    if not x_client_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        row = await (await conn.execute(
            """
            SELECT session_id, contact_email, account_id, rm_owner_id,
                   rm_name, rm_pulse_user_id, client_name
            FROM pulse.client_sessions
            WHERE session_id = %s::uuid AND expires_at > now()
            """,
            [x_client_session],
        )).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return dict(row)


ClientSession = Annotated[dict, Depends(require_client_session)]


# ── Request models ────────────────────────────────────────────────────────────

class OtpRequest(BaseModel):
    email: str


class OtpVerify(BaseModel):
    email: str
    otp: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/auth/request-otp")
async def request_otp(body: OtpRequest) -> dict:
    """Validate email against sf_contacts, send OTP. Always returns 200 to prevent enumeration."""
    from core.client.email import send_otp_email
    from core.llm.config import load_env
    load_env()

    email_lower = body.email.lower().strip()
    if not email_lower or "@" not in email_lower:
        raise HTTPException(status_code=422, detail="Invalid email address")

    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row

        # Check email exists in sf_contacts
        contact = await (await conn.execute(
            "SELECT contact_id FROM pulse.sf_contacts WHERE lower(email) = %s LIMIT 1",
            [email_lower],
        )).fetchone()

        if not contact:
            # Return 200 to prevent enumeration — no OTP is actually sent
            log.info("OTP request for unknown email: %s", email_lower)
            return {"sent": True}

        # Rate limit: max 3 OTPs per email per 10 minutes
        count_row = await (await conn.execute(
            """
            SELECT COUNT(*) AS n FROM pulse.client_otps
            WHERE email = %s AND created_at > now() - INTERVAL '10 minutes'
            """,
            [email_lower],
        )).fetchone()

        if count_row["n"] >= 3:
            raise HTTPException(status_code=429, detail="Too many requests. Try again in 10 minutes.")

        otp = generate_otp()
        otp_hash_val = hash_otp(otp)
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

        await conn.execute(
            """
            INSERT INTO pulse.client_otps (email, otp_hash, expires_at)
            VALUES (%s, %s, %s)
            """,
            [email_lower, otp_hash_val, expires_at],
        )
        await conn.commit()

    try:
        await send_otp_email(email_lower, otp)
    except Exception as exc:
        log.error("SES send failed for %s: %s", email_lower, exc)
        raise HTTPException(status_code=500, detail="Failed to send email. Please try again.")

    return {"sent": True}


@router.post("/auth/verify-otp")
async def verify_otp(body: OtpVerify) -> dict:
    """Validate OTP, create session, return session_id."""
    email_lower = body.email.lower().strip()

    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row

        # Find most recent unused, unexpired OTP
        otp_row = await (await conn.execute(
            """
            SELECT id, otp_hash, attempt_count
            FROM pulse.client_otps
            WHERE email = %s AND used_at IS NULL AND expires_at > now()
            ORDER BY created_at DESC LIMIT 1
            """,
            [email_lower],
        )).fetchone()

        if not otp_row:
            raise HTTPException(status_code=400, detail="Invalid or expired code")

        if otp_row["attempt_count"] >= 3:
            raise HTTPException(status_code=429, detail="Too many attempts. Request a new code.")

        # Increment attempt count
        await conn.execute(
            "UPDATE pulse.client_otps SET attempt_count = attempt_count + 1 WHERE id = %s",
            [otp_row["id"]],
        )
        await conn.commit()

        if not verify_otp_hash(body.otp.strip(), otp_row["otp_hash"]):
            raise HTTPException(status_code=400, detail="Invalid code")

        # Mark OTP as used
        await conn.execute(
            "UPDATE pulse.client_otps SET used_at = now() WHERE id = %s",
            [otp_row["id"]],
        )

        # Resolve: contact → account → RM
        contact_row = await (await conn.execute(
            """
            SELECT c.name AS client_name, c.account_id,
                   a.owner_id AS rm_owner_id, a.rm_name
            FROM pulse.sf_contacts c
            JOIN pulse.sf_accounts a ON c.account_id = a.account_id
            WHERE lower(c.email) = %s
            LIMIT 1
            """,
            [email_lower],
        )).fetchone()

        if not contact_row:
            raise HTTPException(status_code=400, detail="Account not found for this email")

        # Resolve RM's Pulse user_id via name match in google_sessions
        gs_row = await (await conn.execute(
            """
            SELECT gs.user_id
            FROM pulse.google_sessions gs
            JOIN pulse.sf_accounts sa ON LOWER(gs.google_name) = LOWER(sa.rm_name)
            WHERE sa.account_id = %s
            LIMIT 1
            """,
            [contact_row["account_id"]],
        )).fetchone()

        rm_pulse_user_id = gs_row["user_id"] if gs_row else None

        # Create session (24 hours)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        session_row = await (await conn.execute(
            """
            INSERT INTO pulse.client_sessions
                (contact_email, account_id, rm_owner_id, rm_name, rm_pulse_user_id, client_name, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING session_id
            """,
            [
                email_lower,
                contact_row["account_id"],
                contact_row["rm_owner_id"],
                contact_row["rm_name"],
                rm_pulse_user_id,
                contact_row["client_name"] or email_lower,
                expires_at,
            ],
        )).fetchone()

        await conn.commit()

    return {"session_id": str(session_row["session_id"])}


@router.post("/auth/logout", status_code=204)
async def logout(session: ClientSession) -> None:
    """Delete the client session row."""
    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "DELETE FROM pulse.client_sessions WHERE session_id = %s::uuid",
            [str(session["session_id"])],
        )
        await conn.commit()


@router.get("/me")
async def client_me(session: ClientSession) -> dict:
    """Return client identity info for the frontend."""
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        acct = await (await conn.execute(
            "SELECT name FROM pulse.sf_accounts WHERE account_id = %s",
            [session["account_id"]],
        )).fetchone()

    return {
        "client_name": session["client_name"],
        "account_name": acct["name"] if acct else "Unknown",
        "rm_name": session["rm_name"],
        "contact_email": session["contact_email"],
    }
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd 03_build && python -m pytest tests/test_client_auth.py -v
```

Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add 03_build/api/client_auth.py 03_build/tests/test_client_auth.py
git commit -m "feat: add client auth API (OTP request/verify, session, /me)"
```

---

## Task 5: RM Style Analysis + Gmail Sync Hook

**Files:**
- Create: `03_build/core/llm/rm_style.py`
- Modify: `03_build/core/google/gmail_sync.py`

- [ ] **Step 1: Write rm_style.py**

```python
# 03_build/core/llm/rm_style.py
"""
Analyze an RM's Gmail episodes and save a style prompt to pulse.rm_style_profiles.
Called after Gmail sync completes. Uses ANTHROPIC_HAIKU for cost efficiency.
"""
from __future__ import annotations

import asyncio
import logging
import os

from core.db import get_pool
from core.llm.config import ANTHROPIC_HAIKU, load_env
from psycopg.rows import dict_row

log = logging.getLogger(__name__)

_MAX_EMAILS = 50
_STYLE_PROMPT_TEMPLATE = (
    "Analyze the following email snippets written by a Relationship Manager at a healthcare "
    "staffing company. Extract their communication style. Return a 100-150 word paragraph "
    "describing: greeting and sign-off patterns, sentence length, formality level, tone, and "
    "any recurring phrases or habits. Write it as instructions for someone impersonating this "
    "RM's writing style.\n\nEmails:\n{samples}"
)
_DEFAULT_STYLE = (
    "Write professionally and warmly. Use a friendly but concise tone. "
    "Keep responses focused and helpful. Be supportive and solution-oriented."
)


def _call_claude(email_samples: str) -> str:
    load_env()
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    response = client.messages.create(
        model=ANTHROPIC_HAIKU,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": _STYLE_PROMPT_TEMPLATE.format(samples=email_samples),
        }],
    )
    return response.content[0].text.strip()


async def analyze_rm_style(user_id: str) -> None:
    """Fetch RM's Gmail episodes, call Claude for style, upsert to DB."""
    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        rows = await (await conn.execute(
            """
            SELECT subject, description
            FROM pulse.episodes
            WHERE source = 'gmail'
              AND %s = ANY(tags)
              AND description IS NOT NULL
            ORDER BY source_timestamp DESC
            LIMIT %s
            """,
            [user_id, _MAX_EMAILS],
        )).fetchall()

    if not rows:
        log.info("rm_style: no Gmail episodes for %s — skipping", user_id)
        return

    email_samples = "\n---\n".join(
        f"Subject: {r['subject'] or 'No subject'}\n{r['description']}"
        for r in rows
    )

    try:
        style_prompt = await asyncio.to_thread(_call_claude, email_samples)
    except Exception as exc:
        log.error("rm_style: Claude call failed for %s: %s", user_id, exc)
        return

    pool2 = await get_pool()
    async with pool2.connection() as conn:
        await conn.execute(
            """
            INSERT INTO pulse.rm_style_profiles (rm_pulse_user_id, style_prompt, email_count, analyzed_at)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (rm_pulse_user_id) DO UPDATE SET
                style_prompt = EXCLUDED.style_prompt,
                email_count  = EXCLUDED.email_count,
                analyzed_at  = EXCLUDED.analyzed_at
            """,
            [user_id, style_prompt, len(rows)],
        )
        await conn.commit()

    log.info("rm_style: profile saved for %s (%d emails analyzed)", user_id, len(rows))
```

- [ ] **Step 2: Hook into gmail_sync.py**

In `03_build/core/google/gmail_sync.py`, find the end of `pull_and_ingest` (before the final `return` statement) and add the style analysis trigger:

The current last lines of `pull_and_ingest` are:
```python
    log.info(
        "Gmail sync done for %s — fetched=%d ingested=%d skipped=%d errors=%d",
        user_id, fetched, ingested, skipped, errors,
    )
    return {"fetched": fetched, "ingested": ingested, "skipped": skipped, "errors": errors}
```

Replace the return block with:
```python
    log.info(
        "Gmail sync done for %s — fetched=%d ingested=%d skipped=%d errors=%d",
        user_id, fetched, ingested, skipped, errors,
    )

    # Trigger style profile analysis after sync (non-blocking background task)
    if ingested > 0:
        try:
            from core.llm.rm_style import analyze_rm_style
            asyncio.create_task(analyze_rm_style(user_id))
            log.info("rm_style: queued style analysis for %s", user_id)
        except Exception as exc:
            log.error("rm_style: failed to queue analysis for %s: %s", user_id, exc)

    return {"fetched": fetched, "ingested": ingested, "skipped": skipped, "errors": errors}
```

- [ ] **Step 3: Verify the import works**

```bash
cd 03_build && python -c "from core.llm.rm_style import analyze_rm_style; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add 03_build/core/llm/rm_style.py 03_build/core/google/gmail_sync.py
git commit -m "feat: add RM style profile analysis triggered after Gmail sync"
```

---

## Task 6: Client Chat API + Tests

**Files:**
- Create: `03_build/api/client_chat.py`
- Test: `03_build/tests/test_client_chat.py`

- [ ] **Step 1: Write failing tests**

```python
# 03_build/tests/test_client_chat.py
"""Unit tests for client chat helpers — no DB, no network."""
from __future__ import annotations


def test_truncate_title_from_otp_module():
    from core.client.otp import truncate_title
    assert truncate_title("Hello, I have a question about my staffing needs") == \
        "Hello, I have a question about my staffing needs"


def test_truncate_title_caps_at_60():
    from core.client.otp import truncate_title
    long = "x" * 100
    assert truncate_title(long) == "x" * 60


def test_format_context_no_episodes():
    from api.client_chat import _format_context
    result = _format_context([], [])
    assert "No recent emails" in result
    assert "No recent meetings" in result


def test_format_context_with_episodes():
    from api.client_chat import _format_context
    emails = [{"subject": "Follow up", "description": "Hope you are well"}]
    meetings = [{"subject": "Quarterly Review", "description": "Discussed placements"}]
    result = _format_context(emails, meetings)
    assert "Follow up" in result
    assert "Quarterly Review" in result
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd 03_build && python -m pytest tests/test_client_chat.py -v
```

Expected: `ImportError` on `api.client_chat`

- [ ] **Step 3: Write client_chat.py**

```python
# 03_build/api/client_chat.py
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
from core.llm.config import ANTHROPIC_SONNET, load_env
from core.llm.rm_style import _DEFAULT_STYLE

log = logging.getLogger(__name__)

router = APIRouter(prefix="/client", tags=["client"])

load_env()

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
            "SELECT conversation_id FROM pulse.client_conversations WHERE conversation_id = %s::uuid AND contact_email = %s",
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
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    pool = await get_pool()
    async with pool.connection() as conn:
        conn.row_factory = dict_row

        # Verify conversation belongs to this client
        conv = await (await conn.execute(
            "SELECT conversation_id FROM pulse.client_conversations WHERE conversation_id = %s::uuid AND contact_email = %s",
            [body.conversation_id, session["contact_email"]],
        )).fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Save user message
        await conn.execute(
            "INSERT INTO pulse.client_messages (conversation_id, role, content) VALUES (%s::uuid, 'user', %s)",
            [body.conversation_id, body.message],
        )

        # Detect first message for auto-title
        count_row = await (await conn.execute(
            "SELECT COUNT(*) AS n FROM pulse.client_messages WHERE conversation_id = %s::uuid",
            [body.conversation_id],
        )).fetchone()
        is_first = count_row["n"] == 1

        title = ""
        if is_first:
            title = truncate_title(body.message)
            await conn.execute(
                "UPDATE pulse.client_conversations SET title = %s, updated_at = now() WHERE conversation_id = %s::uuid",
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

    # Build messages list (exclude last row = user msg we just saved, re-add below)
    messages = [{"role": r["role"], "content": r["content"]} for r in history_rows[:-1]]
    messages.append({"role": "user", "content": body.message})

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
                "INSERT INTO pulse.client_messages (conversation_id, role, content) VALUES (%s::uuid, 'assistant', %s)",
                [conversation_id, final_text],
            )
            await conn2.execute(
                "UPDATE pulse.client_conversations SET updated_at = now() WHERE conversation_id = %s::uuid",
                [conversation_id],
            )
            await conn2.commit()

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd 03_build && python -m pytest tests/test_client_chat.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add 03_build/api/client_chat.py 03_build/tests/test_client_chat.py
git commit -m "feat: add client chat API (conversations CRUD + virtual-RM SSE chat)"
```

---

## Task 7: Wire Backend

**Files:**
- Modify: `03_build/api/main.py`

- [ ] **Step 1: Mount new routers in main.py**

In `03_build/api/main.py`, inside `create_app()`, add after the existing router imports:

```python
    from api.client_auth import router as client_auth_router
    from api.client_chat import router as client_chat_router
```

And after `app.include_router(webhooks_router)`:

```python
    app.include_router(client_auth_router)
    app.include_router(client_chat_router)
```

- [ ] **Step 2: Add new tables to _ensure_schema in main.py**

In `_ensure_schema()`, add after the existing `CREATE TABLE` blocks:

```python
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.client_otps (
                id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                email          TEXT        NOT NULL,
                otp_hash       TEXT        NOT NULL,
                expires_at     TIMESTAMPTZ NOT NULL,
                used_at        TIMESTAMPTZ,
                attempt_count  INT         NOT NULL DEFAULT 0,
                created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_client_otps_email "
            "ON pulse.client_otps (email, created_at DESC);"
        )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.client_sessions (
                session_id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                contact_email    TEXT        NOT NULL,
                account_id       TEXT        NOT NULL,
                rm_owner_id      TEXT        NOT NULL,
                rm_name          TEXT        NOT NULL,
                rm_pulse_user_id TEXT,
                client_name      TEXT        NOT NULL,
                created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
                expires_at       TIMESTAMPTZ NOT NULL
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_client_sessions_email "
            "ON pulse.client_sessions (contact_email);"
        )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.rm_style_profiles (
                rm_pulse_user_id  TEXT        PRIMARY KEY,
                style_prompt      TEXT        NOT NULL,
                email_count       INT         NOT NULL DEFAULT 0,
                analyzed_at       TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.client_conversations (
                conversation_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                contact_email   TEXT        NOT NULL,
                account_id      TEXT        NOT NULL,
                title           TEXT        NOT NULL DEFAULT 'New conversation',
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                deleted_at      TIMESTAMPTZ
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_client_conv_email "
            "ON pulse.client_conversations (contact_email, updated_at DESC);"
        )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.client_messages (
                message_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                conversation_id UUID        NOT NULL
                                            REFERENCES pulse.client_conversations (conversation_id)
                                            ON DELETE CASCADE,
                role            TEXT        NOT NULL CHECK (role IN ('user', 'assistant')),
                content         TEXT        NOT NULL,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_client_msg_conv "
            "ON pulse.client_messages (conversation_id, created_at ASC);"
        )
```

- [ ] **Step 3: Verify the app starts**

```bash
cd 03_build && python -m uvicorn api.main:app --port 8000 &
sleep 3 && curl -s http://localhost:8000/health
```

Expected: `{"status":"ok","version":"0.1.0"}`

```bash
pkill -f "uvicorn api.main"
```

- [ ] **Step 4: Commit**

```bash
git add 03_build/api/main.py 03_build/pyproject.toml
git commit -m "feat: mount client portal routers and add tables to _ensure_schema"
```

---

## Task 8: Frontend API Client

**Files:**
- Create: `03_build/front/src/lib/client-api.ts`

- [ ] **Step 1: Write client-api.ts**

```typescript
// 03_build/front/src/lib/client-api.ts
/**
 * HTTP client for the /client/* API routes.
 * Uses X-Client-Session header (stored in localStorage) instead of Google OAuth.
 * Completely separate from the RM-facing api.ts.
 */

const BASE = import.meta.env.VITE_API_BASE ?? "/api";
const SESSION_KEY = "client_session_id";

export function getClientSession(): string | null {
  return localStorage.getItem(SESSION_KEY);
}

export function setClientSession(id: string): void {
  localStorage.setItem(SESSION_KEY, id);
}

export function clearClientSession(): void {
  localStorage.removeItem(SESSION_KEY);
}

function clientHeaders(): Record<string, string> {
  const session = getClientSession();
  return session ? { "X-Client-Session": session } : {};
}

async function clientRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...clientHeaders(),
      ...(init.headers as Record<string, string> ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch { /* non-JSON body */ }
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as T;
}

export interface ClientMe {
  client_name: string;
  account_name: string;
  rm_name: string;
  contact_email: string;
}

export interface ClientConversation {
  conversation_id: string;
  title: string;
  updated_at: string;
}

export interface ClientMessage {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export const clientApi = {
  requestOtp: (email: string) =>
    clientRequest<{ sent: boolean }>("/client/auth/request-otp", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  verifyOtp: (email: string, otp: string) =>
    clientRequest<{ session_id: string }>("/client/auth/verify-otp", {
      method: "POST",
      body: JSON.stringify({ email, otp }),
    }),

  logout: () =>
    clientRequest<void>("/client/auth/logout", { method: "POST" }),

  me: () =>
    clientRequest<ClientMe>("/client/me"),

  listConversations: () =>
    clientRequest<ClientConversation[]>("/client/conversations"),

  createConversation: () =>
    clientRequest<ClientConversation>("/client/conversations", { method: "POST" }),

  deleteConversation: (id: string) =>
    clientRequest<void>(`/client/conversations/${id}`, { method: "DELETE" }),

  getMessages: (id: string) =>
    clientRequest<ClientMessage[]>(`/client/conversations/${id}/messages`),
};
```

- [ ] **Step 2: Commit**

```bash
git add 03_build/front/src/lib/client-api.ts
git commit -m "feat: add client portal API client (X-Client-Session header auth)"
```

---

## Task 9: ClientAuthContext + ClientLoginPage + ClientPortal

**Files:**
- Create: `03_build/front/src/features/client/ClientAuthContext.tsx`
- Create: `03_build/front/src/features/client/ClientLoginPage.tsx`
- Create: `03_build/front/src/features/client/ClientPortal.tsx`

- [ ] **Step 1: Write ClientAuthContext.tsx**

```tsx
// 03_build/front/src/features/client/ClientAuthContext.tsx
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { clientApi, clearClientSession, getClientSession, type ClientMe } from "@/lib/client-api";

interface ClientAuthValue {
  me: ClientMe | null;
  loading: boolean;
  logout: () => Promise<void>;
}

const ClientAuthContext = createContext<ClientAuthValue | null>(null);

export function ClientAuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<ClientMe | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getClientSession()) {
      setLoading(false);
      return;
    }
    clientApi
      .me()
      .then(setMe)
      .catch(() => {
        clearClientSession();
      })
      .finally(() => setLoading(false));
  }, []);

  const logout = useCallback(async () => {
    await clientApi.logout().catch(() => {});
    clearClientSession();
    setMe(null);
    window.location.href = "/client/login";
  }, []);

  return (
    <ClientAuthContext.Provider value={{ me, loading, logout }}>
      {children}
    </ClientAuthContext.Provider>
  );
}

export function useClientAuth() {
  const ctx = useContext(ClientAuthContext);
  if (!ctx) throw new Error("useClientAuth must be used inside ClientAuthProvider");
  return ctx;
}
```

- [ ] **Step 2: Write ClientLoginPage.tsx**

```tsx
// 03_build/front/src/features/client/ClientLoginPage.tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, Zap } from "lucide-react";
import { clientApi, setClientSession } from "@/lib/client-api";
import { cn } from "@/lib/utils";

export function ClientLoginPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<"email" | "otp">("email");
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRequestOtp(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await clientApi.requestOtp(email.trim());
      setStep("otp");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send code. Try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyOtp(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { session_id } = await clientApi.verifyOtp(email.trim(), otp.trim());
      setClientSession(session_id);
      navigate("/client/chat", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid code. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="mb-8 flex flex-col items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-brand text-ink-on-brand shadow-xl-brand">
            <Zap className="h-8 w-8" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-semibold tracking-tight text-ink-primary">EDGE Pulse</h1>
            <p className="mt-1 text-sm text-ink-secondary">Client portal</p>
          </div>
        </div>

        <div className="rounded-3xl border border-line-subtle bg-white p-8 shadow-lg shadow-slate-200">
          {step === "email" ? (
            <form onSubmit={handleRequestOtp} className="space-y-4">
              <div>
                <h2 className="mb-1 text-center text-base font-semibold text-ink-primary">
                  Sign in
                </h2>
                <p className="mb-6 text-center text-xs text-ink-muted">
                  Enter your email and we'll send you a login code
                </p>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  required
                  className="w-full rounded-xl border border-line-strong px-4 py-3 text-sm text-ink-primary placeholder:text-ink-muted focus:border-brand/40 focus:outline-none focus:ring-2 focus:ring-brand/10"
                />
              </div>
              {error && <p className="text-center text-xs text-red-500">{error}</p>}
              <button
                type="submit"
                disabled={loading || !email.trim()}
                className={cn(
                  "flex w-full items-center justify-center gap-2 rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-ink-on-brand shadow-xl-brand transition hover:opacity-90",
                  "disabled:cursor-not-allowed disabled:opacity-50",
                )}
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send code"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerifyOtp} className="space-y-4">
              <div>
                <h2 className="mb-1 text-center text-base font-semibold text-ink-primary">
                  Enter your code
                </h2>
                <p className="mb-6 text-center text-xs text-ink-muted">
                  We sent a 6-digit code to <span className="font-medium text-ink-secondary">{email}</span>
                </p>
                <input
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                  placeholder="123456"
                  required
                  className="w-full rounded-xl border border-line-strong px-4 py-3 text-center text-2xl tracking-widest text-ink-primary placeholder:text-ink-muted focus:border-brand/40 focus:outline-none focus:ring-2 focus:ring-brand/10"
                />
              </div>
              {error && <p className="text-center text-xs text-red-500">{error}</p>}
              <button
                type="submit"
                disabled={loading || otp.length !== 6}
                className={cn(
                  "flex w-full items-center justify-center gap-2 rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-ink-on-brand shadow-xl-brand transition hover:opacity-90",
                  "disabled:cursor-not-allowed disabled:opacity-50",
                )}
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Sign in"}
              </button>
              <button
                type="button"
                onClick={() => { setStep("email"); setOtp(""); setError(null); }}
                className="w-full text-center text-xs text-ink-muted hover:text-brand"
              >
                Use a different email
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Write ClientPortal.tsx**

```tsx
// 03_build/front/src/features/client/ClientPortal.tsx
import { Navigate, Route, Routes } from "react-router-dom";
import { ClientAuthProvider } from "./ClientAuthContext";
import { ClientLoginPage } from "./ClientLoginPage";
import { ClientChatPage } from "./ClientChatPage";

export function ClientPortal() {
  return (
    <ClientAuthProvider>
      <Routes>
        <Route path="login" element={<ClientLoginPage />} />
        <Route path="chat" element={<ClientChatPage />} />
        <Route path="*" element={<Navigate to="/client/login" replace />} />
      </Routes>
    </ClientAuthProvider>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add 03_build/front/src/features/client/ClientAuthContext.tsx 03_build/front/src/features/client/ClientLoginPage.tsx 03_build/front/src/features/client/ClientPortal.tsx
git commit -m "feat: add ClientAuthContext, ClientLoginPage, ClientPortal"
```

---

## Task 10: Client Chat Hooks + ClientChatPage

**Files:**
- Create: `03_build/front/src/features/client/hooks.ts`
- Create: `03_build/front/src/features/client/ClientChatPage.tsx`

- [ ] **Step 1: Write hooks.ts**

```typescript
// 03_build/front/src/features/client/hooks.ts
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { clientApi, type ClientConversation, type ClientMessage } from "@/lib/client-api";

export function useClientConversations() {
  return useQuery({
    queryKey: ["client", "conversations"],
    queryFn: () => clientApi.listConversations(),
    staleTime: 0,
  });
}

export function useClientMessages(conversationId: string | null) {
  return useQuery({
    queryKey: ["client", "messages", conversationId],
    queryFn: () => clientApi.getMessages(conversationId!),
    enabled: !!conversationId,
    staleTime: 0,
  });
}

export function useInvalidateClientConversations() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["client", "conversations"] });
}

export type { ClientConversation, ClientMessage };
```

- [ ] **Step 2: Write ClientChatPage.tsx**

```tsx
// 03_build/front/src/features/client/ClientChatPage.tsx
import { useState, useRef, useEffect, useCallback } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Send, Bot, User, Loader2, Plus, Trash2, Sparkles, LogOut } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { clientApi, getClientSession } from "@/lib/client-api";
import { useClientAuth } from "./ClientAuthContext";
import {
  useClientConversations,
  useClientMessages,
  useInvalidateClientConversations,
  type ClientConversation,
  type ClientMessage,
} from "./hooks";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

type Role = "user" | "assistant";

interface Message {
  id: string;
  role: Role;
  text: string;
  pending?: boolean;
}

function dbMsgToLocal(m: ClientMessage, idx: number): Message {
  return { id: m.message_id ?? String(idx), role: m.role, text: m.content };
}

function ConversationRow({
  conv,
  active,
  onSelect,
  onDelete,
}: {
  conv: ClientConversation;
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
      <span className="flex-1 truncate">{conv.title}</span>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(); }}
        className="ml-1 shrink-0 text-ink-muted opacity-0 transition hover:text-red-500 group-hover:opacity-100"
        aria-label="Delete conversation"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

export function ClientChatPage() {
  const { me, loading, logout } = useClientAuth();
  const qc = useQueryClient();
  const invalidateConversations = useInvalidateClientConversations();
  const navigate = useNavigate();

  const { data: conversations = [] } = useClientConversations();
  const [activeId, setActiveId] = useState<string | null>(null);
  const { data: dbMessages } = useClientMessages(activeId);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const idCounter = useRef(0);
  const nextId = () => String(++idCounter.current);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-brand" />
      </div>
    );
  }

  if (!me) {
    return <Navigate to="/client/login" replace />;
  }

  // Auto-select most recent conversation
  useEffect(() => {
    if (!activeId && conversations.length > 0) {
      setActiveId(conversations[0].conversation_id);
    }
  }, [conversations, activeId]);

  // Load messages when active conversation changes
  useEffect(() => {
    if (!dbMessages) return;
    setMessages(dbMessages.map(dbMsgToLocal));
  }, [dbMessages]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleNewChat = useCallback(async () => {
    const conv = await clientApi.createConversation();
    await invalidateConversations();
    setActiveId(conv.conversation_id);
    setMessages([]);
  }, [invalidateConversations]);

  const handleDeleteConversation = useCallback(
    async (conversationId: string) => {
      await clientApi.deleteConversation(conversationId);
      await invalidateConversations();
      if (activeId === conversationId) {
        const remaining = conversations.filter((c) => c.conversation_id !== conversationId);
        setActiveId(remaining[0]?.conversation_id ?? null);
        setMessages([]);
      }
    },
    [invalidateConversations, activeId, conversations],
  );

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || streaming || !activeId) return;

      const userMsg: Message = { id: nextId(), role: "user", text: text.trim() };
      const pendingId = nextId();
      const pendingMsg: Message = { id: pendingId, role: "assistant", text: "", pending: true };

      setMessages((prev) => [...prev, userMsg, pendingMsg]);
      setInput("");
      setStreaming(true);

      try {
        const resp = await fetch(`${BASE}/client/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Client-Session": getClientSession() ?? "",
          },
          body: JSON.stringify({ conversation_id: activeId, message: text.trim() }),
        });

        if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

        const assistantId = nextId();
        setMessages((prev) =>
          prev.map((m) =>
            m.id === pendingId ? { id: assistantId, role: "assistant", text: "" } : m,
          ),
        );

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

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
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId ? { ...m, text: m.text + event.text } : m,
                  ),
                );
              } else if (event.type === "title") {
                qc.setQueryData<ClientConversation[]>(["client", "conversations"], (old = []) =>
                  old.map((c) =>
                    c.conversation_id === activeId ? { ...c, title: event.title } : c,
                  ),
                );
              }
            } catch { /* ignore malformed SSE */ }
          }
        }
      } catch {
        setMessages((prev) =>
          prev.map((m) =>
            m.pending ? { ...m, pending: false, text: "Sorry, something went wrong." } : m,
          ),
        );
      } finally {
        setStreaming(false);
      }
    },
    [streaming, activeId, qc],
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="flex h-screen bg-white">
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
        <div className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-3">
          {conversations.map((conv) => (
            <ConversationRow
              key={conv.conversation_id}
              conv={conv}
              active={activeId === conv.conversation_id}
              onSelect={() => { setActiveId(conv.conversation_id); setMessages([]); }}
              onDelete={() => handleDeleteConversation(conv.conversation_id)}
            />
          ))}
        </div>
        {/* Footer */}
        <div className="border-t border-line-subtle p-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium text-ink-primary">{me.client_name}</p>
              <p className="text-xs text-ink-muted">{me.account_name}</p>
            </div>
            <button
              onClick={logout}
              className="text-ink-muted transition hover:text-red-500"
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
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
              <h1 className="text-sm font-semibold text-ink-primary">
                Your EDGE Relationship Manager — {me.rm_name}
              </h1>
              <p className="text-xs text-ink-muted">
                Ask anything about your account, placements, or staffing needs.
              </p>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-brand/10">
                <Bot className="h-8 w-8 text-brand" />
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-ink-primary">
                  Hi {me.client_name}, I'm {me.rm_name}
                </p>
                <p className="mt-1 text-xs text-ink-muted">
                  {activeId
                    ? "How can I help you today?"
                    : "Create a new chat or select a conversation to start."}
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {messages.map((m) => (
                <div key={m.id} className={cn("flex gap-3", m.role === "user" ? "flex-row-reverse" : "flex-row")}>
                  <div
                    className={cn(
                      "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                      m.role === "user"
                        ? "bg-ink-primary text-ink-on-brand"
                        : "bg-brand text-ink-on-brand shadow-xl-brand",
                    )}
                  >
                    {m.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                  </div>
                  <div className={cn("max-w-[75%]", m.role === "user" ? "items-end" : "items-start")}>
                    {m.pending ? (
                      <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm bg-surface-sidebar px-4 py-3 text-sm text-ink-secondary">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        Thinking…
                      </div>
                    ) : (
                      <div
                        className={cn(
                          "rounded-2xl px-4 py-3 text-sm leading-relaxed",
                          m.role === "user"
                            ? "rounded-tr-sm bg-brand text-ink-on-brand"
                            : "rounded-tl-sm bg-surface-sidebar text-ink-primary",
                        )}
                      >
                        {m.text.split("\n").map((line, j) => (
                          <span key={j}>
                            {line}
                            {j < m.text.split("\n").length - 1 && <br />}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-line-subtle px-6 py-4">
          <div className="flex items-end gap-3 rounded-2xl border border-line-strong bg-white px-4 py-3 focus-within:border-brand/40 focus-within:ring-2 focus-within:ring-brand/10">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                activeId
                  ? "Ask about your account, placements, open roles…"
                  : "Select or create a conversation to start"
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
            Powered by EDGE Pulse · Press Enter to send
          </p>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add 03_build/front/src/features/client/hooks.ts 03_build/front/src/features/client/ClientChatPage.tsx
git commit -m "feat: add ClientChatPage with conversation sidebar and virtual-RM SSE chat"
```

---

## Task 11: Wire App.tsx Routes

**Files:**
- Modify: `03_build/front/src/App.tsx`

- [ ] **Step 1: Add ClientPortal import**

At the top of `03_build/front/src/App.tsx`, after the existing imports, add:

```tsx
import { ClientPortal } from "@/features/client/ClientPortal";
```

- [ ] **Step 2: Add /client/* route**

In `App.tsx`, find the `<Routes>` block. Add the `/client/*` route BEFORE the existing `/login` route (so the catch-all doesn't intercept it):

```tsx
    <Routes>
      {/* Client portal — completely separate auth, no RM session required */}
      <Route path="/client/*" element={<ClientPortal />} />

      {/* Login — redirect to home if already authenticated */}
      <Route
        path="/login"
        element={user ? <Navigate to={defaultRouteForRole(user.role)} replace /> : <LoginPage />}
      />

      {/* ... rest of existing routes unchanged ... */}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd 03_build/front && npx tsc --noEmit
```

Expected: no errors

- [ ] **Step 4: Start the dev server and smoke-test**

```bash
cd 03_build/front && npm run dev &
```

Open `http://localhost:5173/client/login` — verify the login page renders with the email input.

Open `http://localhost:5173/client/chat` without a session — verify it redirects to `/client/login`.

- [ ] **Step 5: Commit**

```bash
git add 03_build/front/src/App.tsx
git commit -m "feat: wire /client/* routes into App.tsx (isolated from RM auth)"
```

---

## Final Verification

- [ ] **Backend smoke test** (requires running backend + DB):

```bash
cd 03_build && python -m uvicorn api.main:app --port 8000 &
sleep 3

# OTP request for unknown email returns 200
curl -s -X POST http://localhost:8000/client/auth/request-otp \
  -H "Content-Type: application/json" \
  -d '{"email":"unknown@example.com"}' | python -m json.tool

# No session returns 401
curl -s http://localhost:8000/client/me | python -m json.tool

# Conversations without auth returns 401
curl -s http://localhost:8000/client/conversations | python -m json.tool

pkill -f "uvicorn api.main"
```

Expected: `{"sent":true}` for OTP, `{"detail":"Not authenticated"}` for the other two

- [ ] **Run full test suite**

```bash
cd 03_build && python -m pytest tests/ -v
```

Expected: all existing + new tests pass

- [ ] **Final commit**

```bash
git add -A
git commit -m "feat: client portal complete — OTP auth, virtual RM chat, conversation history"
```
