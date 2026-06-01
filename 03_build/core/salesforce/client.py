"""
SalesforceClient — async-friendly REST client for Salesforce.

Wraps simple-salesforce (sync) via asyncio.to_thread. All auth and 401
retry is delegated to _SFAuth. Writes are guarded by a system denylist;
all other objects are writable (Action Queue approval is the authorization
gate per §6 rule 6).
"""
from __future__ import annotations

import asyncio
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
            auth = _SFAuth.from_env()
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
