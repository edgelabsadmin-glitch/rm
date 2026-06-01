# Salesforce Connector — Design Spec
**Date:** 2026-05-22  
**Status:** Approved  
**Scope:** `core/salesforce/` — standalone connector only. Adapter rewiring and dispatch integration are separate follow-on tasks.

---

## Problem

The existing SFDC code (`core/adapters/sfdc.py`, `core/dispatch/sfdc_task.py`) spawns a `sf` CLI subprocess for every query and write. This works locally but breaks on AWS (no `~/.sfdx/` credential file in containers) and has subprocess overhead per call. There is also no native write path beyond Task creation.

---

## Solution

A standalone `core/salesforce/` Python module — a native REST client using `simple-salesforce` with automatic OAuth token refresh. Takes three env vars (`SF_REFRESH_TOKEN`, `SF_CLIENT_ID`, `SF_INSTANCE_URL`), works in any container, and exposes a clean async-friendly interface for querying and writing any Salesforce object.

---

## Module layout

```
core/salesforce/
  __init__.py        # re-exports SalesforceClient
  auth.py            # _SFAuth: refresh_token → access_token exchange, 401 auto-retry
  client.py          # SalesforceClient: query, query_all, update, create_record
scripts/
  bootstrap_sf_creds.py   # one-time: extracts creds from ~/.sfdx/ → prints env block
```

---

## Auth (`auth.py`)

### Env vars required

| Var | Source | Description |
|---|---|---|
| `SF_REFRESH_TOKEN` | `~/.sfdx/edgelabs.admin@onedge.co.json` | OAuth refresh token |
| `SF_CLIENT_ID` | same file | `PlatformCLI` |
| `SF_INSTANCE_URL` | same file | `https://edgesolutions.my.salesforce.com` |

### Token lifecycle

- `_SFAuth` holds the current `access_token` in memory.
- On first use (lazy init): POSTs to `{instance_url}/services/oauth2/token` with `grant_type=refresh_token`.
- Response: new `access_token` (valid ~2h). Stored in memory, never written to disk.
- On 401 from any API call: re-exchanges once, updates cached token, retries the call.
- Thread/async safe: `asyncio.Lock` guards the exchange.
- `refresh_token` does not expire as long as it is used within the org's refresh token policy (default 90 days; Salesforce resets the clock on each use, so normal operation keeps it alive indefinitely).

### AWS deployment

`SF_REFRESH_TOKEN`, `SF_CLIENT_ID`, `SF_INSTANCE_URL` go into AWS Secrets Manager / ECS task definition environment. No credential files on disk.

---

## Client (`client.py`)

### Interface

```python
class SalesforceClient:
    async def query(self, soql: str) -> list[dict]:
        """Single-page SOQL query. Strips 'attributes' keys from records."""

    async def query_all(self, soql: str) -> list[dict]:
        """Auto-paginating SOQL query. Follows nextRecordsUrl until done.
        Use for bulk pulls (accounts, associates, etc.)."""

    async def update(self, object_name: str, record_id: str, fields: dict) -> None:
        """PATCH /sobjects/{object_name}/{record_id}. 
        Raises ValueError if object_name is in SYSTEM_DENYLIST."""

    async def create_record(self, object_name: str, fields: dict) -> str:
        """POST /sobjects/{object_name}. Returns new record Id.
        Raises ValueError if object_name is in SYSTEM_DENYLIST."""
```

### System denylist

Objects that must never be written to programmatically:

```python
SYSTEM_DENYLIST = frozenset({
    "User", "Profile", "PermissionSet", "PermissionSetAssignment",
    "SetupAuditTrail", "LoginHistory", "AuthSession",
})
```

Read operations (`query`, `query_all`) are unrestricted — any object can be queried.

### Implementation details

- `simple-salesforce` `Salesforce(instance_url=..., session_id=...)` is initialised with the current access token from `_SFAuth`.
- All methods run in `asyncio.to_thread` (simple-salesforce is synchronous) to stay compatible with FastAPI's async model (ADR-001).
- On `SalesforceExpiredSession` (401): `_SFAuth.refresh()` → rebuild the `Salesforce` instance → retry once.
- API version: `v62.0` (§6 rule 17).

---

## Bootstrap script (`scripts/bootstrap_sf_creds.py`)

One-time local utility. Reads `~/.sfdx/edgelabs.admin@onedge.co.json`, prints the three env var values to stdout as an `.env` block. Operator pastes into `.env` (and into AWS Secrets Manager before deployment). Script is never run in production.

---

## New dependency

```toml
# pyproject.toml
"simple-salesforce>=1.12"
```

---

## Tests (`tests/test_salesforce_client.py`)

| Test | What it verifies |
|---|---|
| `test_query_returns_records` | Happy path query, strips `attributes` |
| `test_query_all_paginates` | Follows `nextRecordsUrl` across two pages |
| `test_update_happy_path` | Calls PATCH with correct object + fields |
| `test_update_denylist_raises` | `ValueError` on `User`, `Profile`, etc. |
| `test_create_record_returns_id` | POST returns new record Id |
| `test_401_triggers_refresh_and_retry` | On expired session: refreshes token, retries once, succeeds |
| `test_401_double_failure_raises` | If retry also 401s, raises — no infinite loop |
| `test_auth_lock_prevents_concurrent_refresh` | Two concurrent 401s only trigger one exchange |

All tests mock `simple_salesforce.Salesforce` and `httpx.post` — no real org touched.

---

## Out of scope (follow-on tasks)

- Rewiring `SFDCAdapter` to use `SalesforceClient.query()` instead of `sf` CLI subprocess
- Rewiring `sfdc_task.py` to use `SalesforceClient.create_record()`
- New `sfdc_update.py` dispatch handler for field updates via Action Queue
