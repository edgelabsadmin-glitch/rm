"""
Salesforce auth via OAuth username-password flow.

Fetches a fresh access token from the Salesforce token endpoint using
SF_USERNAME / SF_PASSWORD / SF_SECURITY_TOKEN / SF_CLIENT_ID env vars.
No sf CLI required — works in Docker / AWS App Runner out of the box.

Token is cached in-process. invalidate() clears it so the next call
re-authenticates (called automatically by SalesforceClient on 401).
asyncio.Lock prevents concurrent fetches.

Env vars:
  SF_INSTANCE_URL   — org URL (default: https://edgesolutions.my.salesforce.com)
  SF_CLIENT_ID      — Connected App consumer key
  SF_USERNAME       — Salesforce username
  SF_PASSWORD       — Salesforce password
  SF_SECURITY_TOKEN — Salesforce security token (appended to password)
  SF_ACCESS_TOKEN   — optional hard-coded token; skips OAuth entirely
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field

import httpx

_SF_TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"


@dataclass
class _SFAuth:
    instance_url: str
    _access_token: str = field(default="", init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    @classmethod
    def from_env(cls) -> "_SFAuth":
        instance_url = os.environ.get(
            "SF_INSTANCE_URL", "https://edgesolutions.my.salesforce.com"
        )
        auth = cls(instance_url=instance_url)
        # Direct token bypass (e.g. short-lived manual token in dev)
        if token := os.environ.get("SF_ACCESS_TOKEN", ""):
            auth._access_token = token
        return auth

    async def token(self) -> str:
        """Return cached access token, fetching a fresh one via OAuth if empty."""
        if not self._access_token:
            await self._fetch()
        return self._access_token

    async def _fetch(self) -> None:
        async with self._lock:
            if self._access_token:  # another coroutine fetched while we waited
                return
            self._access_token = await asyncio.to_thread(self._fetch_sync)

    def _fetch_sync(self) -> str:
        """Fetch a fresh access token from Salesforce OAuth (username-password flow)."""
        client_id = os.environ.get("SF_CLIENT_ID", "")
        username = os.environ.get("SF_USERNAME", "")
        password = os.environ.get("SF_PASSWORD", "")
        security_token = os.environ.get("SF_SECURITY_TOKEN", "")

        if not all([client_id, username, password]):
            raise RuntimeError(
                "SF_CLIENT_ID, SF_USERNAME, and SF_PASSWORD must be set for Salesforce auth"
            )

        resp = httpx.post(
            _SF_TOKEN_URL,
            data={
                "grant_type": "password",
                "client_id": client_id,
                "username": username,
                "password": password + security_token,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("access_token", "")
        if not token:
            raise RuntimeError(f"Salesforce OAuth returned no access_token: {data}")
        # OAuth response may return a different instance_url — keep in sync
        if instance_url := data.get("instance_url"):
            self.instance_url = instance_url
        return token

    def invalidate(self) -> None:
        """Clear cached token — next call to token() will re-authenticate."""
        self._access_token = ""
