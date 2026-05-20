"""
SPEC-032 — Email dispatch (Gmail / Outlook OAuth, Q60).

Phase 1 sends FROM the RM's own mailbox via OAuth so the reply lands in the RM's
inbox, not Pulse (Design 03 / Q60). The actual OAuth send is spec 043; here we
define the transport seam and a not-yet-configured default. Unit tests inject a
fake transport to assert the composed message; the integration test uses a real
test mailbox.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from core.actions.queue import ActionRecord


@dataclass
class EmailMessage:
    to: list[str]
    subject: str
    body: str
    from_rm_id: str | None = None
    cc: list[str] | None = None
    calendar_link: str | None = None  # set by the calendar-hold handler


class EmailTransport(Protocol):
    async def send(self, msg: EmailMessage) -> str:
        """Send and return the provider message id."""
        ...


class NotConfiguredTransport:
    """Default transport until OAuth (spec 043) lands — raises on send so a
    dispatch attempt fails loudly (retry → dead-letter) rather than silently
    dropping. Never used when a real transport is injected."""

    async def send(self, msg: EmailMessage) -> str:
        raise RuntimeError(
            "no email OAuth transport configured (spec 043); inject EmailTransport to send"
        )


def _default_transport() -> EmailTransport:
    return NotConfiguredTransport()


def compose(action: ActionRecord) -> EmailMessage:
    """Build the outbound message from the approved action_card (best-effort over
    the LLM-authored body; tolerant of missing keys)."""
    card = action.action_card
    to = card.get("to") or card.get("recipient") or card.get("recipients") or []
    if isinstance(to, str):
        to = [to]
    subject = card.get("subject") or card.get("headline") or action.why_oneline
    body = card.get("body") or card.get("draft") or card.get("note") or ""
    return EmailMessage(
        to=list(to),
        subject=subject,
        body=body,
        from_rm_id=action.rm_id,
        cc=card.get("cc"),
        calendar_link=card.get("calendar_link"),
    )


async def send(action: ActionRecord, *, transport: EmailTransport | None = None) -> str:
    """Compose + send the email; returns the provider message id."""
    transport = transport or _default_transport()
    msg = compose(action)
    if os.environ.get("PULSE_DISPATCH_DRY_RUN") == "1":
        return "dry-run"
    return await transport.send(msg)
