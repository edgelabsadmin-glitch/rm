"""
Salesforce auth via the `sf` CLI.

_SFAuth retrieves a fresh, decrypted access token by running
`sf org display --json --target-org <alias>` in a subprocess. The sf CLI
owns token rotation and re-authentication — this module just reads the
current valid token from it.

Token is cached in memory; invalidate() clears it so the next call fetches
a fresh one (used on 401 responses). asyncio.Lock prevents concurrent
subprocesses when multiple coroutines need a refresh at the same time.

For AWS deployment: the `sf` CLI must be installed and authenticated in
the container via `sf org login jwt` with a Connected App + certificate,
or the SF_ACCESS_TOKEN env var can be set directly to bypass CLI entirely.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass, field


@dataclass
class _SFAuth:
    instance_url: str
    target_org: str = "edge-prod"
    sf_bin: str = "sf"
    _access_token: str = field(default="", init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    @classmethod
    def from_env(cls) -> "_SFAuth":
        """Build from environment variables (SF_INSTANCE_URL, SF_TARGET_ORG)."""
        # If a raw token is provided (e.g. in CI/AWS without sf CLI), use it directly.
        token = os.environ.get("SF_ACCESS_TOKEN", "")
        instance_url = os.environ.get("SF_INSTANCE_URL", "https://edgesolutions.my.salesforce.com")
        target_org = os.environ.get("SF_TARGET_ORG", "edge-prod")
        auth = cls(instance_url=instance_url, target_org=target_org)
        if token:
            auth._access_token = token
        return auth

    async def token(self) -> str:
        """Return current access token, fetching from sf CLI if empty."""
        if not self._access_token:
            await self._fetch()
        return self._access_token

    async def _fetch(self) -> None:
        async with self._lock:
            if self._access_token:  # another coroutine fetched while we waited
                return
            self._access_token = await asyncio.to_thread(self._fetch_sync)

    def _fetch_sync(self) -> str:
        """Run sf org display and extract the access token (blocking)."""
        cmd = [
            self.sf_bin,
            "org",
            "display",
            "--target-org",
            self.target_org,
            "--json",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"sf org display failed: {result.stderr[:200]}")
        data = json.loads(result.stdout)
        token = data.get("result", {}).get("accessToken", "")
        if not token:
            raise RuntimeError("sf org display returned no accessToken")
        return token

    def invalidate(self) -> None:
        """Clear cached token so next call fetches a fresh one."""
        self._access_token = ""
