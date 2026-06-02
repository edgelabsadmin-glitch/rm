# Salesforce Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `core/salesforce/` — a native Python REST connector for Salesforce with automatic OAuth token refresh, supporting arbitrary SOQL queries and record writes.

**Architecture:** A two-file module: `auth.py` holds `_SFAuth` which exchanges a stored refresh token for an access token on first use and re-exchanges on 401; `client.py` holds `SalesforceClient` which wraps `simple-salesforce` for sync calls via `asyncio.to_thread` and delegates all auth/retry to `_SFAuth`. A bootstrap script extracts the three required env vars from the local `~/.sfdx/` file once.

**Tech Stack:** Python 3.12+, `simple-salesforce>=1.12`, `httpx>=0.27` (already in deps), `asyncio`, `pytest-asyncio` (already in dev deps).

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `03_build/core/salesforce/__init__.py` | Re-export `SalesforceClient` |
| Create | `03_build/core/salesforce/auth.py` | `_SFAuth`: refresh token exchange, 401 invalidation, asyncio lock |
| Create | `03_build/core/salesforce/client.py` | `SalesforceClient`: query, query_all, update, create_record + system denylist |
| Create | `03_build/scripts/bootstrap_sf_creds.py` | One-time: read `~/.sfdx/` → print env block |
| Create | `03_build/tests/test_salesforce_auth.py` | Unit tests for `_SFAuth` |
| Create | `03_build/tests/test_salesforce_client.py` | Unit tests for `SalesforceClient` |
| Modify | `03_build/pyproject.toml` | Add `simple-salesforce>=1.12` to dependencies |
| Modify | `.env` | Add `SF_REFRESH_TOKEN`, `SF_CLIENT_ID`, `SF_INSTANCE_URL` |
| Modify | `.env.example` | Document the three new vars |

---

## Setup: Python environment

Before any task, you need a working Python 3.12+ environment with deps installed. The system Python is 3.9; use `python3.13` (available via Homebrew at `/opt/homebrew/bin/python3.13`).

- [ ] **Create virtualenv and install deps**

```bash
cd /Users/afnanhashmi/Documents/rm-cloned/03_build
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: `Successfully installed pulse-0.1.0 ...` (and all deps including pytest, pytest-asyncio, httpx).

---

## Task 1: Add `simple-salesforce` dependency

**Files:**
- Modify: `03_build/pyproject.toml`

- [ ] **Step 1: Add the dependency**

Open `03_build/pyproject.toml`. In the `dependencies` list, after the `httpx` line, add:

```toml
    "simple-salesforce>=1.12",
```

The dependencies block should look like:
```toml
dependencies = [
    # Web
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "pydantic>=2.11",
    "pydantic-settings>=2.5",
    # Memory layer
    "graphiti-core[kuzu,anthropic]>=0.29",
    # LLM
    "anthropic>=0.49",
    "openai>=1.91",
    # Data
    "psycopg[binary,pool]>=3.2",
    # Observability
    "langfuse>=2.0,<3",
    # Env
    "python-dotenv>=1.0",
    # HTTP
    "httpx>=0.27",
    # Salesforce
    "simple-salesforce>=1.12",
]
```

- [ ] **Step 2: Install into venv**

```bash
cd /Users/afnanhashmi/Documents/rm-cloned/03_build
source .venv/bin/activate
pip install "simple-salesforce>=1.12"
```

Expected: `Successfully installed simple-salesforce-...`

- [ ] **Step 3: Verify import**

```bash
python3 -c "from simple_salesforce import Salesforce, SalesforceExpiredSession; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
cd /Users/afnanhashmi/Documents/rm-cloned
git add 03_build/pyproject.toml
git commit -m "[SPEC-SFDC-CONN] add simple-salesforce>=1.12 dependency"
```

---

## Task 2: Auth module — tests first, then implementation

**Files:**
- Create: `03_build/core/salesforce/__init__.py`
- Create: `03_build/core/salesforce/auth.py`
- Create: `03_build/tests/test_salesforce_auth.py`

- [ ] **Step 1: Create the package directory**

```bash
mkdir -p /Users/afnanhashmi/Documents/rm-cloned/03_build/core/salesforce
touch /Users/afnanhashmi/Documents/rm-cloned/03_build/core/salesforce/__init__.py
```

- [ ] **Step 2: Write the failing auth tests**

Create `03_build/tests/test_salesforce_auth.py`:

```python
"""Tests for _SFAuth — OAuth refresh token exchange and token caching."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.salesforce.auth import _SFAuth


def make_auth(access_token: str = "") -> _SFAuth:
    auth = _SFAuth(
        instance_url="https://test.salesforce.com",
        client_id="PlatformCLI",
        refresh_token="rt-abc",
    )
    auth._access_token = access_token
    return auth


async def test_token_exchanges_on_first_call():
    auth = make_auth()  # empty access token

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "new-tok"}
    mock_resp.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)

    with patch("core.salesforce.auth.httpx.AsyncClient", return_value=mock_http):
        token = await auth.token()

    assert token == "new-tok"
    assert auth._access_token == "new-tok"


async def test_token_returns_cached_without_exchange():
    auth = make_auth(access_token="cached-tok")

    # No HTTP mock needed — exchange must not be called
    token = await auth.token()

    assert token == "cached-tok"


async def test_exchange_posts_correct_payload():
    auth = make_auth()

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "tok-xyz"}
    mock_resp.raise_for_status = MagicMock()

    mock_post = AsyncMock(return_value=mock_resp)
    mock_http = AsyncMock()
    mock_http.__aenter__.return_value.post = mock_post

    with patch("core.salesforce.auth.httpx.AsyncClient", return_value=mock_http):
        await auth.token()

    mock_post.assert_called_once_with(
        "https://test.salesforce.com/services/oauth2/token",
        data={
            "grant_type": "refresh_token",
            "client_id": "PlatformCLI",
            "refresh_token": "rt-abc",
        },
    )


async def test_invalidate_clears_token():
    auth = make_auth(access_token="tok-123")
    auth.invalidate()
    assert auth._access_token == ""


async def test_concurrent_calls_only_exchange_once():
    """Two concurrent token() calls on empty auth must only call _exchange once."""
    import asyncio

    auth = make_auth()
    exchange_count = {"n": 0}

    original_exchange = auth._exchange

    async def counted_exchange():
        exchange_count["n"] += 1
        auth._access_token = "fresh-tok"

    with patch.object(auth, "_exchange", side_effect=counted_exchange):
        # Fire two concurrent token() calls
        t1, t2 = await asyncio.gather(auth.token(), auth.token())

    assert t1 == "fresh-tok"
    assert t2 == "fresh-tok"
    assert exchange_count["n"] == 1
```

- [ ] **Step 3: Run tests — expect failure (module not found)**

```bash
cd /Users/afnanhashmi/Documents/rm-cloned/03_build
source .venv/bin/activate
python -m pytest tests/test_salesforce_auth.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.salesforce.auth'`

- [ ] **Step 4: Implement `core/salesforce/auth.py`**

Create `03_build/core/salesforce/auth.py`:

```python
"""
Salesforce OAuth refresh token exchange.

_SFAuth holds the current access_token in memory and exchanges the stored
refresh_token for a new one on first use or after a 401. Thread/async safe:
asyncio.Lock prevents concurrent exchanges from firing duplicate HTTP calls.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import httpx


@dataclass
class _SFAuth:
    instance_url: str
    client_id: str
    refresh_token: str
    _access_token: str = field(default="", init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    async def token(self) -> str:
        """Return current access token, exchanging if empty."""
        if not self._access_token:
            await self._exchange()
        return self._access_token

    async def _exchange(self) -> None:
        async with self._lock:
            if self._access_token:  # another coroutine refreshed while we waited
                return
            async with httpx.AsyncClient() as http:
                resp = await http.post(
                    f"{self.instance_url}/services/oauth2/token",
                    data={
                        "grant_type": "refresh_token",
                        "client_id": self.client_id,
                        "refresh_token": self.refresh_token,
                    },
                )
                resp.raise_for_status()
                self._access_token = resp.json()["access_token"]

    def invalidate(self) -> None:
        """Clear cached token so next call triggers a fresh exchange."""
        self._access_token = ""
```

- [ ] **Step 5: Run auth tests — expect all pass**

```bash
python -m pytest tests/test_salesforce_auth.py -v
```

Expected:
```
tests/test_salesforce_auth.py::test_token_exchanges_on_first_call PASSED
tests/test_salesforce_auth.py::test_token_returns_cached_without_exchange PASSED
tests/test_salesforce_auth.py::test_exchange_posts_correct_payload PASSED
tests/test_salesforce_auth.py::test_invalidate_clears_token PASSED
tests/test_salesforce_auth.py::test_concurrent_calls_only_exchange_once PASSED
5 passed
```

- [ ] **Step 6: Commit**

```bash
cd /Users/afnanhashmi/Documents/rm-cloned
git add 03_build/core/salesforce/__init__.py 03_build/core/salesforce/auth.py 03_build/tests/test_salesforce_auth.py
git commit -m "[SPEC-SFDC-CONN] _SFAuth: refresh token exchange with async lock"
```

---

## Task 3: Client module — tests first, then implementation

**Files:**
- Modify: `03_build/core/salesforce/__init__.py`
- Create: `03_build/core/salesforce/client.py`
- Create: `03_build/tests/test_salesforce_client.py`

- [ ] **Step 1: Write failing client tests**

Create `03_build/tests/test_salesforce_client.py`:

```python
"""Tests for SalesforceClient — SOQL query, pagination, update, create, 401 retry."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from simple_salesforce import SalesforceExpiredSession

from core.salesforce.auth import _SFAuth
from core.salesforce.client import SYSTEM_DENYLIST, SalesforceClient


# ── helpers ───────────────────────────────────────────────────────────────────

def make_client(access_token: str = "tok-123") -> SalesforceClient:
    auth = _SFAuth(
        instance_url="https://test.salesforce.com",
        client_id="PlatformCLI",
        refresh_token="rt-abc",
    )
    auth._access_token = access_token
    return SalesforceClient(auth=auth)


# ── query ─────────────────────────────────────────────────────────────────────

async def test_query_returns_records_strips_attributes():
    client = make_client()
    mock_sf = MagicMock()
    mock_sf.query.return_value = {
        "records": [
            {"attributes": {"type": "Account", "url": "/..."}, "Id": "001", "Name": "ACME"},
        ]
    }
    with patch("core.salesforce.client._make_sf", return_value=mock_sf):
        result = await client.query("SELECT Id, Name FROM Account LIMIT 1")

    assert result == [{"Id": "001", "Name": "ACME"}]
    mock_sf.query.assert_called_once_with("SELECT Id, Name FROM Account LIMIT 1")


async def test_query_empty_result():
    client = make_client()
    mock_sf = MagicMock()
    mock_sf.query.return_value = {"records": []}
    with patch("core.salesforce.client._make_sf", return_value=mock_sf):
        result = await client.query("SELECT Id FROM Account WHERE Id = 'nonexistent'")
    assert result == []


# ── query_all ─────────────────────────────────────────────────────────────────

async def test_query_all_returns_all_records():
    client = make_client()
    mock_sf = MagicMock()
    mock_sf.query_all.return_value = {
        "records": [
            {"attributes": {}, "Id": "001"},
            {"attributes": {}, "Id": "002"},
            {"attributes": {}, "Id": "003"},
        ]
    }
    with patch("core.salesforce.client._make_sf", return_value=mock_sf):
        result = await client.query_all("SELECT Id FROM Account")

    assert len(result) == 3
    assert result[0] == {"Id": "001"}
    assert result[2] == {"Id": "003"}
    mock_sf.query_all.assert_called_once_with("SELECT Id FROM Account")


# ── update ────────────────────────────────────────────────────────────────────

async def test_update_calls_patch_on_correct_object():
    client = make_client()
    mock_sf = MagicMock()
    with patch("core.salesforce.client._make_sf", return_value=mock_sf):
        await client.update("Account", "001abc", {"Customer_Health__c": "Green"})

    mock_sf.Account.update.assert_called_once_with("001abc", {"Customer_Health__c": "Green"})


async def test_update_works_for_opportunity():
    client = make_client()
    mock_sf = MagicMock()
    with patch("core.salesforce.client._make_sf", return_value=mock_sf):
        await client.update("Opportunity", "006xyz", {"StageName": "Closed Won"})

    mock_sf.Opportunity.update.assert_called_once_with("006xyz", {"StageName": "Closed Won"})


async def test_update_denylist_raises_for_all_blocked_objects():
    client = make_client()
    for obj in SYSTEM_DENYLIST:
        with pytest.raises(ValueError, match=obj):
            await client.update(obj, "some-id", {"field": "value"})


# ── create_record ─────────────────────────────────────────────────────────────

async def test_create_record_returns_new_id():
    client = make_client()
    mock_sf = MagicMock()
    mock_sf.Task.create.return_value = {"id": "new-task-001", "success": True, "errors": []}
    with patch("core.salesforce.client._make_sf", return_value=mock_sf):
        result = await client.create_record("Task", {"Subject": "Follow up", "Status": "Not Started"})

    assert result == "new-task-001"
    mock_sf.Task.create.assert_called_once_with({"Subject": "Follow up", "Status": "Not Started"})


async def test_create_record_denylist_raises():
    client = make_client()
    with pytest.raises(ValueError, match="User"):
        await client.create_record("User", {"Username": "x@y.com"})


# ── 401 auto-retry ────────────────────────────────────────────────────────────

async def test_401_on_query_triggers_refresh_and_retry():
    client = make_client("expired-tok")

    expired_sf = MagicMock()
    expired_sf.query.side_effect = SalesforceExpiredSession(
        "https://test.salesforce.com/query", "401", "Session expired"
    )

    fresh_sf = MagicMock()
    fresh_sf.query.return_value = {"records": [{"attributes": {}, "Id": "001"}]}

    call_count = {"n": 0}

    def make_sf_side_effect(instance_url: str, access_token: str) -> MagicMock:
        call_count["n"] += 1
        return expired_sf if call_count["n"] == 1 else fresh_sf

    async def fake_exchange() -> None:
        client._auth._access_token = "fresh-tok"

    with patch("core.salesforce.client._make_sf", side_effect=make_sf_side_effect):
        with patch.object(client._auth, "_exchange", new_callable=AsyncMock) as mock_ex:
            mock_ex.side_effect = fake_exchange
            result = await client.query("SELECT Id FROM Account")

    assert result == [{"Id": "001"}]
    assert call_count["n"] == 2  # expired_sf + fresh_sf


async def test_401_double_failure_propagates_exception():
    """If retry also returns 401, the exception bubbles up — no infinite loop."""
    client = make_client("expired-tok")

    expired_sf = MagicMock()
    expired_sf.query.side_effect = SalesforceExpiredSession(
        "https://test.salesforce.com/query", "401", "Session expired"
    )

    async def fake_exchange() -> None:
        client._auth._access_token = "still-bad"

    with patch("core.salesforce.client._make_sf", return_value=expired_sf):
        with patch.object(client._auth, "_exchange", new_callable=AsyncMock) as mock_ex:
            mock_ex.side_effect = fake_exchange
            with pytest.raises(SalesforceExpiredSession):
                await client.query("SELECT Id FROM Account")
```

- [ ] **Step 2: Run tests — expect failure (module not found)**

```bash
cd /Users/afnanhashmi/Documents/rm-cloned/03_build
source .venv/bin/activate
python -m pytest tests/test_salesforce_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.salesforce.client'`

- [ ] **Step 3: Implement `core/salesforce/client.py`**

Create `03_build/core/salesforce/client.py`:

```python
"""
SalesforceClient — async-friendly REST client for Salesforce.

Wraps simple-salesforce (sync) via asyncio.to_thread. All auth and 401
retry is delegated to _SFAuth. Writes are guarded by a system denylist;
all other objects are writable (Action Queue approval is the authorization
gate per §6 rule 6).
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

from simple_salesforce import Salesforce, SalesforceExpiredSession

from core.salesforce.auth import _SFAuth

SF_API_VERSION = "62.0"

SYSTEM_DENYLIST: frozenset[str] = frozenset({
    "User",
    "Profile",
    "PermissionSet",
    "PermissionSetAssignment",
    "SetupAuditTrail",
    "LoginHistory",
    "AuthSession",
})


def _make_sf(instance_url: str, access_token: str) -> Salesforce:
    return Salesforce(
        instance_url=instance_url,
        session_id=access_token,
        version=SF_API_VERSION,
    )


class SalesforceClient:
    def __init__(self, auth: _SFAuth | None = None) -> None:
        if auth is None:
            auth = _SFAuth(
                instance_url=os.environ["SF_INSTANCE_URL"],
                client_id=os.environ["SF_CLIENT_ID"],
                refresh_token=os.environ["SF_REFRESH_TOKEN"],
            )
        self._auth = auth

    async def _sf(self) -> Salesforce:
        token = await self._auth.token()
        return _make_sf(self._auth.instance_url, token)

    async def _run(self, fn: Any) -> Any:
        """Run a synchronous simple-salesforce call in a thread, retry once on 401."""
        sf = await self._sf()
        try:
            return await asyncio.to_thread(fn, sf)
        except SalesforceExpiredSession:
            self._auth.invalidate()
            sf = await self._sf()
            return await asyncio.to_thread(fn, sf)

    async def query(self, soql: str) -> list[dict]:
        """Single-page SOQL query. Strips 'attributes' metadata from records."""
        def _fn(sf: Salesforce) -> list[dict]:
            records = sf.query(soql).get("records", [])
            for r in records:
                r.pop("attributes", None)
            return records

        return await self._run(_fn)

    async def query_all(self, soql: str) -> list[dict]:
        """Auto-paginating SOQL query — follows nextRecordsUrl until exhausted."""
        def _fn(sf: Salesforce) -> list[dict]:
            records = sf.query_all(soql).get("records", [])
            for r in records:
                r.pop("attributes", None)
            return records

        return await self._run(_fn)

    async def update(self, object_name: str, record_id: str, fields: dict) -> None:
        """PATCH an existing record. Raises ValueError for system objects."""
        if object_name in SYSTEM_DENYLIST:
            raise ValueError(f"writes to {object_name} are not permitted")

        def _fn(sf: Salesforce) -> None:
            getattr(sf, object_name).update(record_id, fields)

        await self._run(_fn)

    async def create_record(self, object_name: str, fields: dict) -> str:
        """POST a new record; returns the new record Id."""
        if object_name in SYSTEM_DENYLIST:
            raise ValueError(f"writes to {object_name} are not permitted")

        def _fn(sf: Salesforce) -> str:
            return getattr(sf, object_name).create(fields)["id"]

        return await self._run(_fn)
```

- [ ] **Step 4: Update `core/salesforce/__init__.py`**

```python
from core.salesforce.client import SalesforceClient

__all__ = ["SalesforceClient"]
```

- [ ] **Step 5: Run client tests — expect all pass**

```bash
cd /Users/afnanhashmi/Documents/rm-cloned/03_build
source .venv/bin/activate
python -m pytest tests/test_salesforce_client.py -v
```

Expected:
```
tests/test_salesforce_client.py::test_query_returns_records_strips_attributes PASSED
tests/test_salesforce_client.py::test_query_empty_result PASSED
tests/test_salesforce_client.py::test_query_all_returns_all_records PASSED
tests/test_salesforce_client.py::test_update_calls_patch_on_correct_object PASSED
tests/test_salesforce_client.py::test_update_works_for_opportunity PASSED
tests/test_salesforce_client.py::test_update_denylist_raises_for_all_blocked_objects PASSED
tests/test_salesforce_client.py::test_create_record_returns_new_id PASSED
tests/test_salesforce_client.py::test_create_record_denylist_raises PASSED
tests/test_salesforce_client.py::test_401_on_query_triggers_refresh_and_retry PASSED
tests/test_salesforce_client.py::test_401_double_failure_propagates_exception PASSED
10 passed
```

- [ ] **Step 6: Run full auth + client test suite together**

```bash
python -m pytest tests/test_salesforce_auth.py tests/test_salesforce_client.py -v
```

Expected: `15 passed`

- [ ] **Step 7: Commit**

```bash
cd /Users/afnanhashmi/Documents/rm-cloned
git add 03_build/core/salesforce/client.py 03_build/core/salesforce/__init__.py 03_build/tests/test_salesforce_client.py
git commit -m "[SPEC-SFDC-CONN] SalesforceClient: query, update, create_record with 401 auto-retry"
```

---

## Task 4: Bootstrap script + env wiring

**Files:**
- Create: `03_build/scripts/bootstrap_sf_creds.py`
- Modify: `.env`
- Modify: `.env.example`

- [ ] **Step 1: Write `scripts/bootstrap_sf_creds.py`**

Create `03_build/scripts/bootstrap_sf_creds.py`:

```python
"""
One-time utility: read ~/.sfdx/edgelabs.admin@onedge.co.json and print
the three SF_ env vars required by SalesforceClient.

Usage (local only — never run in production):
    python scripts/bootstrap_sf_creds.py

Paste the output into .env and into AWS Secrets Manager before deployment.
"""
from __future__ import annotations

import json
import pathlib
import sys

SFDX_FILE = pathlib.Path.home() / ".sfdx" / "edgelabs.admin@onedge.co.json"


def main() -> None:
    if not SFDX_FILE.exists():
        print(f"ERROR: {SFDX_FILE} not found. Run `sf org login web` first.", file=sys.stderr)
        sys.exit(1)
    with SFDX_FILE.open() as f:
        creds = json.load(f)
    print(f"SF_REFRESH_TOKEN={creds['refreshToken']}")
    print(f"SF_CLIENT_ID={creds['clientId']}")
    print(f"SF_INSTANCE_URL={creds['instanceUrl']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the bootstrap script and capture output**

```bash
cd /Users/afnanhashmi/Documents/rm-cloned/03_build
source .venv/bin/activate
python scripts/bootstrap_sf_creds.py
```

Expected output (values will be real credentials):
```
SF_REFRESH_TOKEN=5Aep861...
SF_CLIENT_ID=PlatformCLI
SF_INSTANCE_URL=https://edgesolutions.my.salesforce.com
```

- [ ] **Step 3: Add the three vars to `.env`**

Open `/Users/afnanhashmi/Documents/rm-cloned/.env` and add under the `# ── Salesforce` section:

```
SF_REFRESH_TOKEN=<value from bootstrap script>
SF_CLIENT_ID=PlatformCLI
SF_INSTANCE_URL=https://edgesolutions.my.salesforce.com
```

- [ ] **Step 4: Add the three vars to `.env.example`**

Open `/Users/afnanhashmi/Documents/rm-cloned/.env.example`. Under the `# ── Salesforce` section add:

```
# Native Python REST connector (SalesforceClient — no sf CLI needed at runtime)
# Run `python scripts/bootstrap_sf_creds.py` locally to extract from ~/.sfdx/
# On AWS: put these three in Secrets Manager.
SF_REFRESH_TOKEN=
SF_CLIENT_ID=PlatformCLI
SF_INSTANCE_URL=https://edgesolutions.my.salesforce.com
```

- [ ] **Step 5: Smoke-test the connector against the real org**

```bash
cd /Users/afnanhashmi/Documents/rm-cloned/03_build
source .venv/bin/activate
python3 - <<'EOF'
import asyncio, os
from dotenv import load_dotenv
load_dotenv("../.env", override=True)
from core.salesforce import SalesforceClient

async def main():
    client = SalesforceClient()
    rows = await client.query("SELECT Id, Name, Type FROM Account LIMIT 3")
    for r in rows:
        print(r)

asyncio.run(main())
EOF
```

Expected: 3 Account records printed (same ones seen earlier via `sf data query`):
```
{'Id': '0013h000006K123AAC', 'Name': 'Acrisure LLC - West Region', 'Type': 'Client'}
...
```

- [ ] **Step 6: Commit**

```bash
cd /Users/afnanhashmi/Documents/rm-cloned
git add 03_build/scripts/bootstrap_sf_creds.py .env.example
git commit -m "[SPEC-SFDC-CONN] bootstrap script + env vars documented"
```

Note: `.env` is gitignored — do not add it.

---

## Task 5: Run the full existing test suite to confirm no regressions

- [ ] **Step 1: Run all non-DB, non-integration tests**

```bash
cd /Users/afnanhashmi/Documents/rm-cloned/03_build
source .venv/bin/activate
python -m pytest tests/ -v --ignore=tests/test_salesforce_auth.py --ignore=tests/test_salesforce_client.py 2>&1 | tail -20
```

Expected: existing tests all pass (or skip on missing DB/LLM secrets — that is normal). No new failures introduced.

- [ ] **Step 2: Run the connector tests one final time**

```bash
python -m pytest tests/test_salesforce_auth.py tests/test_salesforce_client.py -v
```

Expected: `15 passed`

- [ ] **Step 3: Final commit**

```bash
cd /Users/afnanhashmi/Documents/rm-cloned
git add 03_build/pyproject.toml
git commit -m "[SPEC-SFDC-CONN] connector complete: SalesforceClient with auto-refresh, 15 tests green"
```

---

## Self-Review

**Spec coverage check:**
- ✅ `core/salesforce/auth.py` — `_SFAuth` with refresh exchange + async lock
- ✅ `core/salesforce/client.py` — `query`, `query_all`, `update`, `create_record`
- ✅ System denylist on writes
- ✅ 401 auto-retry (single retry, no infinite loop)
- ✅ `asyncio.to_thread` wrapping for FastAPI async compat
- ✅ `SF_REFRESH_TOKEN` / `SF_CLIENT_ID` / `SF_INSTANCE_URL` env vars
- ✅ Bootstrap script
- ✅ `.env.example` documented
- ✅ `simple-salesforce>=1.12` in `pyproject.toml`
- ✅ All 8 test cases from spec covered (query, query_all, update, denylist, create, 401 retry, 401 double fail, concurrent lock)

**Out of scope (confirmed):** adapter rewiring, dispatch handler, AWS Secrets Manager setup.
