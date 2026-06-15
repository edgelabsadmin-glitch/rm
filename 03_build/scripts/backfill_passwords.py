"""
Backfill recording_password for Zoom episodes that already have a share_url.

Calls /meetings/{id}/recordings for each meeting, stores the password field.
Only processes rows where recording_password IS NULL and source_url is a real URL.

Run from 03_build/ with DATABASE_URL set (or .env present):
    python3 scripts/backfill_passwords.py
    python3 scripts/backfill_passwords.py --dry-run
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import psycopg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

_env = Path(__file__).resolve().parents[2] / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            k, _, v = _line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))

DB_URL = os.environ["DATABASE_URL"]
ZOOM_ACCOUNT_ID = os.environ.get("ZOOM_ACCOUNT_ID", "")
ZOOM_CLIENT_ID = os.environ.get("ZOOM_CLIENT_ID", "")
ZOOM_CLIENT_SECRET = os.environ.get("ZOOM_CLIENT_SECRET", "")

_ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"
_ZOOM_BASE = "https://api.zoom.us/v2"
_SLEEP = 0.3  # seconds between API calls
_BATCH_COMMIT = 100


_zoom_token: str = ""
_zoom_token_expiry: float = 0.0


async def _zoom_access_token(client: httpx.AsyncClient) -> str:
    global _zoom_token, _zoom_token_expiry
    if _zoom_token and time.time() < _zoom_token_expiry - 60:
        return _zoom_token
    creds = base64.b64encode(f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}".encode()).decode()
    resp = await client.post(
        _ZOOM_TOKEN_URL,
        params={"grant_type": "account_credentials", "account_id": ZOOM_ACCOUNT_ID},
        headers={"Authorization": f"Basic {creds}"},
    )
    resp.raise_for_status()
    data = resp.json()
    _zoom_token = data["access_token"]
    _zoom_token_expiry = time.time() + data.get("expires_in", 3600)
    return _zoom_token


async def main(dry_run: bool = False) -> None:
    conn = await psycopg.AsyncConnection.connect(DB_URL)
    async with conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT episode_id, source_event_id
                FROM pulse.episodes
                WHERE source = 'zoom'
                  AND source_url IS NOT NULL
                  AND source_url != 'no-recording'
                  AND recording_password IS NULL
                ORDER BY source_timestamp DESC
            """)
            rows = await cur.fetchall()

    total = len(rows)
    log.info("Found %d Zoom episodes needing password.", total)

    if dry_run or not total:
        log.info("Dry run — no writes. Exiting.")
        return

    updated = errors = 0

    conn = await psycopg.AsyncConnection.connect(DB_URL)
    async with conn:
        async with httpx.AsyncClient(timeout=30) as client:
            for _i, (episode_id, meeting_id) in enumerate(rows):
                try:
                    token = await _zoom_access_token(client)
                    resp = await client.get(
                        f"{_ZOOM_BASE}/meetings/{meeting_id}/recordings",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if resp.status_code == 404:
                        # Recording deleted — mark with empty string so we skip next time
                        async with conn.cursor() as cur:
                            await cur.execute(
                                "UPDATE pulse.episodes SET recording_password = '' WHERE episode_id = %s",
                                (str(episode_id),),
                            )
                        await asyncio.sleep(_SLEEP)
                        continue

                    resp.raise_for_status()
                    data = resp.json()
                    password = data.get("password") or data.get("recording_password") or ""

                    async with conn.cursor() as cur:
                        await cur.execute(
                            "UPDATE pulse.episodes SET recording_password = %s WHERE episode_id = %s",
                            (password, str(episode_id)),
                        )
                    updated += 1

                    if updated % _BATCH_COMMIT == 0:
                        await conn.commit()
                        log.info("Committed %d/%d (errors: %d)", updated, total, errors)

                except Exception as exc:
                    log.error("Episode %s error: %s", episode_id, exc)
                    errors += 1

                await asyncio.sleep(_SLEEP)

        await conn.commit()

    log.info("Done — updated=%d errors=%d total=%d", updated, errors, total)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(main(dry_run=dry_run))
