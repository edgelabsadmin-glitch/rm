"""
Pure helpers over Gmail message payloads. No network, no DB — unit-testable.

extract_plain_body walks a Gmail `payload` MIME tree and returns the decoded
text/plain content (preferred over text/html). latest_inbound_message decides
whether a thread is unreplied and, if so, which message to surface.
"""

from __future__ import annotations

import base64


def _decode(data: str) -> str:
    """Decode Gmail's base64url body data (tolerant of missing padding)."""
    if not data:
        return ""
    padding = "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(data + padding).decode("utf-8", errors="replace")
    except Exception:
        return ""


def extract_plain_body(payload: dict) -> str:
    """Return the text/plain body from a Gmail message payload, or "".

    Prefers text/plain; recurses into multipart containers. Returns the first
    text/plain part found in a depth-first walk.
    """
    mime = payload.get("mimeType", "")
    if mime == "text/plain":
        return _decode(payload.get("body", {}).get("data", "")).strip()
    for part in payload.get("parts", []) or []:
        found = extract_plain_body(part)
        if found:
            return found
    return ""


def latest_inbound_message(messages: list[dict], rm_email: str) -> dict | None:
    """Return the latest message if the thread is unreplied, else None.

    `messages` is a list of dicts with at least `from_email` and `internal_date`
    (int, ms since epoch). A thread is "unreplied" when its newest message is
    NOT from the RM (i.e. the client spoke last). Returns that newest message.
    """
    if not messages:
        return None
    newest = max(messages, key=lambda m: m["internal_date"])
    if newest.get("from_email", "").lower() == rm_email.lower():
        return None
    return newest
