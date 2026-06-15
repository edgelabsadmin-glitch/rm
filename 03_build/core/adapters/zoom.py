"""
Zoom Signal Source Adapter — Server-to-Server OAuth, polling via Zoom Reports API.

Fetches past meetings for every user in the account, normalises them into
canonical Episode envelopes, and fuzzy-matches the meeting topic against the
SF account index (same strategy as ChorusAdapter).

Zoom Reports API limits each request to a 30-day window, so list_recent_events
chunks the since→now range internally.  fetch_full is a no-op (report rows
already carry all fields we need).  receive_webhook is not used (SUPPORTS_WEBHOOKS=False).
"""

from __future__ import annotations

import base64
import logging
import os
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from core.adapters.base import SignalSourceAdapter
from core.adapters.chorus import _ACCOUNT_MATCH_THRESHOLD, fuzz_score, normalize_name
from core.adapters.episode import EntityRef, Episode, RawEvent

ZOOM_BASE = "https://api.zoom.us/v2"
ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"
_HTTP_TIMEOUT = 30.0
_REPORT_WINDOW_DAYS = 29  # Zoom Reports API hard limit: 1 month per request

log = logging.getLogger(__name__)


class ZoomAdapter(SignalSourceAdapter):
    SOURCE_NAME = "zoom"
    SUPPORTS_WEBHOOKS = False
    SUPPORTS_BACKFILL = True

    def __init__(
        self,
        account_id: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        account_index: list[dict] | None = None,
    ) -> None:
        self.account_id = account_id or os.environ.get("ZOOM_ACCOUNT_ID", "")
        self.client_id = client_id or os.environ.get("ZOOM_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("ZOOM_CLIENT_SECRET", "")
        self.account_index = account_index or []
        self._token: str | None = None
        self._token_expiry: float = 0.0

    # ── OAuth ─────────────────────────────────────────────────────────────────

    async def _get_token(self) -> str:
        if self._token and time.time() < self._token_expiry - 60:
            return self._token
        creds = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(
                ZOOM_TOKEN_URL,
                params={"grant_type": "account_credentials", "account_id": self.account_id},
                headers={"Authorization": f"Basic {creds}"},
            )
            resp.raise_for_status()
            data = resp.json()
        self._token = data["access_token"]
        self._token_expiry = time.time() + data.get("expires_in", 3600)
        return self._token

    # ── HTTP ──────────────────────────────────────────────────────────────────

    async def _get(self, path: str, params: dict | None = None) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(
                f"{ZOOM_BASE}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            return resp.json()

    # ── User list ─────────────────────────────────────────────────────────────

    async def _list_user_ids(self) -> list[str]:
        """Return IDs of licensed users only (type=2/3). Basic users can't access reporting."""
        ids: list[str] = []
        npt: str | None = None
        while True:
            params: dict = {"page_size": 300, "status": "active"}
            if npt:
                params["next_page_token"] = npt
            data = await self._get("/users", params)
            for u in data.get("users", []):
                if u.get("type", 1) != 1:  # skip basic (type=1) users
                    ids.append(u["id"])
            npt = data.get("next_page_token") or ""
            if not npt:
                break
        return ids

    # ── Adapter contract ──────────────────────────────────────────────────────

    async def list_recent_events(self, since: datetime, max_pages: int = 2000) -> list[RawEvent]:
        """Paginate Zoom Reports for all users in 30-day windows from `since` to now."""
        now = datetime.now(UTC)
        since = since.replace(tzinfo=UTC) if since.tzinfo is None else since

        # Build 29-day date windows
        windows: list[tuple[datetime, datetime]] = []
        cur = since
        while cur < now:
            end = min(cur + timedelta(days=_REPORT_WINDOW_DAYS), now)
            windows.append((cur, end))
            cur = end + timedelta(seconds=1)

        try:
            user_ids = await self._list_user_ids()
        except Exception as exc:
            log.error("Zoom: failed to list users: %s", exc)
            return []

        log.info("Zoom: %d users × %d date windows to fetch.", len(user_ids), len(windows))

        seen: set[str] = set()
        events: list[RawEvent] = []
        pages_used = 0

        for uid in user_ids:
            user_has_access = True  # set False on first 400 to skip remaining windows
            for from_dt, to_dt in windows:
                if not user_has_access or pages_used >= max_pages:
                    break
                npt: str | None = None
                while pages_used < max_pages:
                    params: dict = {
                        "page_size": 300,
                        "from": from_dt.strftime("%Y-%m-%d"),
                        "to": to_dt.strftime("%Y-%m-%d"),
                    }
                    if npt:
                        params["next_page_token"] = npt
                    try:
                        data = await self._get(f"/report/users/{uid}/meetings", params)
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code in (400, 404):
                            # Code 300 = date range outside retention window (not an access error)
                            # — skip this window only; other codes mean user lacks report access.
                            try:
                                err_code = exc.response.json().get("code")
                            except Exception:
                                err_code = None
                            if err_code != 300:
                                user_has_access = False
                            break  # stop fetching pages for this window
                        raise
                    pages_used += 1
                    for m in data.get("meetings", []):
                        if m.get("duration", 0) < 2:
                            continue  # skip instant/no-show calls
                        key = str(m.get("uuid") or m.get("id") or "")
                        if key and key not in seen:
                            seen.add(key)
                            events.append(self._raw(m))
                    npt = data.get("next_page_token") or ""
                    if not npt:
                        break

        return events

    async def receive_webhook(self, payload: dict, headers: dict) -> list[RawEvent]:
        raise NotImplementedError("Zoom adapter uses polling only.")

    async def fetch_full(self, event: RawEvent) -> RawEvent:
        return event  # report rows are already fully hydrated

    def normalize(self, raw: RawEvent) -> Episode:
        m = raw.get("payload", {}).get("meeting", {})
        mid = raw.get("source_event_id", "")
        topic = (m.get("topic") or "").strip()

        ts_str = m.get("start_time") or ""
        if ts_str:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        else:
            ts = datetime.now(UTC)

        duration = m.get("duration")  # minutes
        host_email = m.get("host_email") or m.get("host_id") or ""

        parts: list[str] = []
        if topic:
            parts.append(f"Meeting: {topic}")
        if host_email:
            parts.append(f"Host: {host_email}")
        if duration:
            parts.append(f"Duration: {duration} minutes")
        participants = m.get("participants_count")
        if participants:
            parts.append(f"Participants: {participants}")

        content: dict = {
            "text": "\n\n".join(parts) or f"Zoom meeting {mid}",
            "duration_mins": duration,
        }

        return Episode(
            episode_id=uuid4(),
            dedup_key=self.dedup_key(raw),
            source=self.SOURCE_NAME,
            source_event_id=mid,
            source_url=None,
            source_timestamp=ts,
            content_type="text",
            content=content,
            subject=topic or f"Zoom meeting {mid}",
            description=f"Zoom meeting — {topic}" if topic else "Zoom meeting",
            candidate_entities=self._resolve_account(topic),
            tags=["zoom", "meeting"],
            ingested_at=datetime.now(UTC),
            processing_state="normalized",
        )

    def dedup_key(self, raw: RawEvent) -> str:
        return f"zoom:meeting:{raw.get('source_event_id', '')}"

    # ── helpers ───────────────────────────────────────────────────────────────

    def _raw(self, m: dict) -> RawEvent:
        mid = str(m.get("uuid") or m.get("id") or "")
        return {
            "source": self.SOURCE_NAME,
            "source_event_id": mid,
            "source_url": None,
            "payload": {"meeting": m},
        }

    def _resolve_account(self, topic: str) -> list[EntityRef]:
        if not topic or not self.account_index:
            return []
        norm = normalize_name(topic)
        best, best_score = None, 0.0
        for acct in self.account_index:
            score = fuzz_score(norm, normalize_name(acct.get("name", "")))
            if score > best_score:
                best, best_score = acct, score
        if best and best_score >= _ACCOUNT_MATCH_THRESHOLD:
            return [{"type": "Customer", "sfdc_id": best["id"], "name": best.get("name", "")}]
        return [{"type": "Customer", "name": topic}]
