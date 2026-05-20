"""
SPEC-013 — Chorus Signal Source Adapter.

Ports rm-intelligence-agent/src/chorus_pull.py into the Design 02 adapter
contract. Chorus v3 API (raw `Authorization: <token>` header, continuation_key
pagination) per the reference_chorus_api memory. Produces one text Episode per
completed engagement: meeting summary + action items + participant context
(the input shape extract_signals.py / Skill 01 consumes).

Triggered in production by the Activepieces `chorus_engagement_completed` flow
(HTTP webhook → /webhooks/chorus). receive_webhook validates the signature;
fetch_full hydrates the conversation detail; normalize emits the Episode.
Read-only.
"""

from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import re
from datetime import datetime
from difflib import SequenceMatcher
from uuid import uuid4

import httpx

from core.adapters.base import SignalSourceAdapter
from core.adapters.episode import EntityRef, Episode, RawEvent

CHORUS_BASE = "https://chorus.ai"
_ACCOUNT_MATCH_THRESHOLD = 85.0  # fuzz score required to bind a Customer sfdc_id
_HTTP_TIMEOUT = 30.0


# ── Lifted verbatim from rm-intelligence-agent (DoD requirement) ─────────────
def strip_html(s: str | None) -> str:
    """rm-intelligence-agent/src/extract_signals.py::strip_html()."""
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return s.strip()


def normalize_name(s: str | None) -> str:
    """rm-intelligence-agent/src/rank_accounts.py::normalize_name()."""
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def fuzz_score(a: str, b: str) -> float:
    """rm-intelligence-agent/src/rank_accounts.py::fuzz_score() (stdlib difflib)."""
    if not a or not b:
        return 0
    ta = " ".join(sorted(set(a.split())))
    tb = " ".join(sorted(set(b.split())))
    if not ta or not tb:
        return 0
    direct = SequenceMatcher(None, a, b).ratio() * 100
    tokenset = SequenceMatcher(None, ta, tb).ratio() * 100
    short, long = (ta, tb) if len(ta) < len(tb) else (tb, ta)
    contain = 100 if short and short in long else 0
    return max(direct, tokenset, contain * 0.95)


class ChorusAdapter(SignalSourceAdapter):
    SOURCE_NAME = "chorus"
    SUPPORTS_WEBHOOKS = True
    SUPPORTS_BACKFILL = True

    def __init__(self, token: str | None = None, account_index: list[dict] | None = None) -> None:
        self.token = token or os.environ.get("CHORUS_API_TOKEN", "")
        # account_index: [{"id": "001...", "name": "Acrisure"}], for the fuzzy join.
        self.account_index = account_index or []

    # ── HTTP ─────────────────────────────────────────────────────────────────
    async def _http_get(self, url: str) -> dict:
        headers = {"Authorization": self.token, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()

    # ── Adapter contract ─────────────────────────────────────────────────────
    async def list_recent_events(self, since: datetime, max_pages: int = 200) -> list[RawEvent]:
        """Backfill/poll: paginate /v3/engagements (meetings) back to `since`."""
        since_epoch = since.timestamp()
        base = f"{CHORUS_BASE}/v3/engagements?engagement_type=meeting"
        url = base
        events: list[RawEvent] = []
        last_first_id = None
        for _ in range(max_pages):
            data = await self._http_get(url)
            eng = data.get("engagements", [])
            if not eng:
                break
            first_id = eng[0].get("engagement_id")
            if first_id == last_first_id:
                break  # pagination stalled
            last_first_id = first_id
            for e in eng:
                if e.get("no_show"):
                    continue
                if (e.get("date_time") or 0) < since_epoch:
                    continue
                events.append(self._raw_from_engagement(e))
            ck = data.get("continuation_key")
            oldest_ts = min((e.get("date_time") or 0) for e in eng)
            if not ck or oldest_ts < since_epoch:
                break
            from urllib.parse import quote

            url = f"{base}&continuation_key={quote(ck)}"
        return events

    def _verify_signature(self, payload: dict, headers: dict) -> bool:
        """HMAC-SHA256 over the canonical JSON body. No secret configured → accept
        (dev). Production should additionally verify the raw request body."""
        secret = os.environ.get("CHORUS_WEBHOOK_SECRET")
        if not secret:
            return True
        signature = headers.get("X-Chorus-Signature") or headers.get("x-chorus-signature") or ""
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def receive_webhook(self, payload: dict, headers: dict) -> list[RawEvent]:
        """Validate the Chorus webhook signature and return a thin RawEvent
        (fetch_full hydrates it). Raises on a forged signature."""
        if not self._verify_signature(payload, headers):
            raise ValueError("bad-signature")
        engagement_id = payload.get("engagement_id") or payload.get("conversation_id")
        if not engagement_id:
            raise ValueError("malformed chorus webhook: missing engagement_id")
        return [self._raw_from_engagement(payload, engagement_id=str(engagement_id))]

    async def fetch_full(self, event: RawEvent) -> RawEvent:
        """Hydrate a thin webhook event into a full engagement (summary/action
        items). Idempotent; a poll event already carrying a summary is returned
        as-is."""
        eng = event.get("payload", {}).get("engagement", {})
        if eng.get("meeting_summary") or eng.get("action_items"):
            return event
        eid = event.get("source_event_id")
        if not eid:
            return event
        detail = await self._http_get(f"{CHORUS_BASE}/v3/engagements/{eid}")
        full = detail.get("engagement", detail)
        return self._raw_from_engagement(full, engagement_id=str(eid))

    def normalize(self, raw: RawEvent) -> Episode:
        eng = raw.get("payload", {}).get("engagement", {})
        eid = raw.get("source_event_id", "")
        account_name = (eng.get("account_name") or "").strip()
        ts = eng.get("date_time") or 0

        return Episode(
            episode_id=uuid4(),
            dedup_key=self.dedup_key(raw),
            source=self.SOURCE_NAME,
            source_event_id=eid,
            source_url=eng.get("recording_url") or eng.get("call_url"),
            source_timestamp=datetime.fromtimestamp(ts).astimezone()
            if ts
            else datetime.now().astimezone(),
            content_type="text",
            content=self._compose_content(eng),
            subject=(eng.get("subject") or f"Chorus engagement {eid}")[:120],
            description=f"Chorus meeting — {account_name}" if account_name else "Chorus meeting",
            candidate_entities=self._resolve_account(account_name),
            tags=["chorus", "meeting"],
            ingested_at=datetime.now().astimezone(),
            processing_state="normalized",
        )

    def dedup_key(self, raw: RawEvent) -> str:
        return f"chorus:conv:{raw.get('source_event_id', '')}"

    # ── helpers ──────────────────────────────────────────────────────────────
    def _raw_from_engagement(self, eng: dict, engagement_id: str | None = None) -> RawEvent:
        eid = engagement_id or str(eng.get("engagement_id") or eng.get("conversation_id") or "")
        return {
            "source": self.SOURCE_NAME,
            "source_event_id": eid,
            "source_url": None,
            "payload": {"engagement": eng},
        }

    @staticmethod
    def _compose_content(eng: dict) -> str:
        parts: list[str] = []
        if eng.get("subject"):
            parts.append(f"Meeting: {eng['subject']}")
        if eng.get("account_name"):
            parts.append(f"Account: {eng['account_name']}")
        summary = strip_html(eng.get("meeting_summary"))
        if summary:
            parts.append("Summary:\n" + summary)
        action_items = eng.get("action_items")
        if isinstance(action_items, list):
            ai_text = "\n".join(strip_html(str(a)) for a in action_items if a)
        else:
            ai_text = strip_html(action_items)
        if ai_text:
            parts.append("Action items:\n" + ai_text)
        prospects = [
            p.get("name") or p.get("email")
            for p in (eng.get("participants") or [])
            if p.get("type") == "prospect"
        ]
        if prospects:
            parts.append("Client participants: " + ", ".join(p for p in prospects if p))
        return "\n\n".join(parts)

    def _resolve_account(self, account_name: str) -> list[EntityRef]:
        if not account_name:
            return []
        norm = normalize_name(account_name)
        best, best_score = None, 0.0
        for acct in self.account_index:
            score = fuzz_score(norm, normalize_name(acct.get("name", "")))
            if score > best_score:
                best, best_score = acct, score
        if best and best_score >= _ACCOUNT_MATCH_THRESHOLD:
            return [{"type": "Customer", "sfdc_id": best["id"], "name": best.get("name", "")}]
        # No confident SFDC match — keep the name as a hint for the LLM extractor.
        return [{"type": "Customer", "name": account_name}]
