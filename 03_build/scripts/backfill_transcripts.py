"""
Backfill transcript + recording URL for existing Zoom and Chorus episodes.

Zoom  — calls /meetings/{id}/recordings, stores share_url + parsed VTT transcript.
Chorus — source_url is constructable from source_event_id (no API call needed).
         Raw transcript is not accessible via our current API token; AI summary
         is already in the content field.

Run from 03_build/ with DATABASE_URL set (or .env present):
    python3 scripts/backfill_transcripts.py            # both sources
    python3 scripts/backfill_transcripts.py --zoom     # zoom only
    python3 scripts/backfill_transcripts.py --chorus   # chorus only
    python3 scripts/backfill_transcripts.py --dry-run  # print stats, no writes
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import psycopg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Load .env if present
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
_CHORUS_MEETING_URL = "https://chorus.ai/meeting/{eid}"

# Zoom rate-limit: ~30 req/s on Pro plan; stay well under it.
_ZOOM_SLEEP = 0.5  # seconds between recording API calls
_BATCH_COMMIT = 50  # commit every N rows


# ── VTT parser ────────────────────────────────────────────────────────────────


def _parse_vtt(vtt: str) -> str:
    """Convert WebVTT to plain speaker-labeled text.

    Input:
        WEBVTT
        1
        00:00:16.059 --> 00:00:17.030
        Rihan Javid: Are you sure?

    Output:
        Rihan Javid: Are you sure?
        ...
    """
    lines = vtt.splitlines()
    out: list[str] = []
    _ts_re = re.compile(r"^\d{2}:\d{2}:\d{2}[.,]\d{3}\s+-->\s+")
    _cue_re = re.compile(r"^\d+$")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.upper().startswith("WEBVTT"):
            continue
        if _ts_re.match(line):
            continue
        if _cue_re.match(line):
            continue
        out.append(line)
    return "\n".join(out)


# ── Zoom OAuth ────────────────────────────────────────────────────────────────

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


# ── Zoom backfill ─────────────────────────────────────────────────────────────


async def backfill_zoom(dry_run: bool = False) -> dict:
    conn = await psycopg.AsyncConnection.connect(DB_URL)
    async with conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT episode_id, source_event_id
                FROM pulse.episodes
                WHERE source = 'zoom'
                  AND (transcript IS NULL OR source_url IS NULL)
                ORDER BY source_timestamp DESC
            """)
            rows = await cur.fetchall()

    log.info("Zoom: %d episodes need transcript / recording URL.", len(rows))
    if dry_run:
        return {"total": len(rows), "updated": 0, "no_recording": 0, "errors": 0}

    updated = no_recording = errors = 0

    conn = await psycopg.AsyncConnection.connect(DB_URL)
    async with conn:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for _i, (episode_id, meeting_id) in enumerate(rows):
                try:
                    token = await _zoom_access_token(client)
                    resp = await client.get(
                        f"{_ZOOM_BASE}/meetings/{meeting_id}/recordings",
                        headers={"Authorization": f"Bearer {token}"},
                    )

                    if resp.status_code == 404:
                        # No cloud recording for this meeting — mark source_url as N/A
                        # so we don't retry it on every run.
                        async with conn.cursor() as cur:
                            await cur.execute(
                                "UPDATE pulse.episodes SET source_url = 'no-recording' WHERE episode_id = %s",
                                (str(episode_id),),
                            )
                        no_recording += 1
                        await asyncio.sleep(_ZOOM_SLEEP)
                        continue

                    resp.raise_for_status()
                    data = resp.json()

                    share_url = data.get("share_url") or data.get("recording_url") or ""
                    transcript_text: str = ""

                    for f in data.get("recording_files", []):
                        if f.get("file_type") == "TRANSCRIPT" and f.get("download_url"):
                            dl_url = f["download_url"] + f"?access_token={token}"
                            vtt_resp = await client.get(dl_url)
                            if vtt_resp.status_code == 200:
                                transcript_text = _parse_vtt(vtt_resp.text)
                            break

                    async with conn.cursor() as cur:
                        await cur.execute(
                            """
                            UPDATE pulse.episodes
                               SET source_url  = COALESCE(NULLIF(%s,''), source_url),
                                   transcript  = COALESCE(NULLIF(%s,''), transcript)
                             WHERE episode_id  = %s
                            """,
                            (share_url, transcript_text or None, str(episode_id)),
                        )
                    updated += 1

                    if updated % _BATCH_COMMIT == 0:
                        await conn.commit()
                        log.info("Zoom: committed %d/%d updates so far.", updated, len(rows))

                except Exception as exc:
                    log.error("Zoom episode %s error: %s", episode_id, exc)
                    errors += 1

                await asyncio.sleep(_ZOOM_SLEEP)

        await conn.commit()

    log.info(
        "Zoom backfill done — updated=%d no_recording=%d errors=%d",
        updated,
        no_recording,
        errors,
    )
    return {"total": len(rows), "updated": updated, "no_recording": no_recording, "errors": errors}


# ── Chorus backfill ───────────────────────────────────────────────────────────


async def backfill_chorus(dry_run: bool = False) -> dict:
    """Populate source_url for all Chorus episodes using the known URL pattern."""
    conn = await psycopg.AsyncConnection.connect(DB_URL)
    async with conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT episode_id, source_event_id
                FROM pulse.episodes
                WHERE source = 'chorus'
                  AND source_url IS NULL
                  AND source_event_id IS NOT NULL
            """)
            rows = await cur.fetchall()

    log.info("Chorus: %d episodes need recording URL.", len(rows))
    if dry_run or not rows:
        return {"total": len(rows), "updated": 0}

    conn = await psycopg.AsyncConnection.connect(DB_URL)
    async with conn:
        async with conn.cursor() as cur:
            for i, (episode_id, eid) in enumerate(rows):
                url = _CHORUS_MEETING_URL.format(eid=eid)
                await cur.execute(
                    "UPDATE pulse.episodes SET source_url = %s WHERE episode_id = %s",
                    (url, str(episode_id)),
                )
                if (i + 1) % _BATCH_COMMIT == 0:
                    await conn.commit()
                    log.info("Chorus: committed %d/%d", i + 1, len(rows))
        await conn.commit()

    log.info("Chorus backfill done — updated=%d", len(rows))
    return {"total": len(rows), "updated": len(rows)}


# ── Entry point ───────────────────────────────────────────────────────────────


async def main() -> None:
    args = set(sys.argv[1:])
    dry_run = "--dry-run" in args
    do_zoom = "--zoom" in args or not ({"--zoom", "--chorus"} & args)
    do_chorus = "--chorus" in args or not ({"--zoom", "--chorus"} & args)

    if dry_run:
        log.info("DRY RUN — no writes.")

    if do_chorus:
        log.info("=== Chorus ===")
        result = await backfill_chorus(dry_run=dry_run)
        log.info("Chorus result: %s", result)

    if do_zoom:
        if not all([ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET]):
            log.error("Zoom credentials not set — skipping Zoom backfill.")
        else:
            log.info("=== Zoom ===")
            result = await backfill_zoom(dry_run=dry_run)
            log.info("Zoom result: %s", result)


if __name__ == "__main__":
    asyncio.run(main())
