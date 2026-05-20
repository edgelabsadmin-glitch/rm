"""
SPEC-032 — Calendar hold dispatch (Q73).

Phase 1 minimum: a calendar hold is delivered AS an email carrying the invite
link / .ics (auto-booking against the RM's calendar is a v1.5+ candidate). So
this handler composes the email (adding the calendar link) and sends it through
the same email transport — keeping a single outbound path.
"""

from __future__ import annotations

from core.actions.queue import ActionRecord
from core.dispatch import email
from core.dispatch.email import EmailTransport


def _ensure_calendar_link(action: ActionRecord) -> None:
    """Surface a calendar link into the card so compose() carries it. If the
    skill already provided one, keep it; else synthesize a placeholder hold."""
    card = action.action_card
    if not card.get("calendar_link"):
        slot = card.get("proposed_time") or card.get("when") or "TBD"
        card["calendar_link"] = f"calendar-hold://{action.action_id}?slot={slot}"


async def send(action: ActionRecord, *, transport: EmailTransport | None = None) -> str:
    """Send the calendar hold as an email invite; returns the provider message id."""
    _ensure_calendar_link(action)
    return await email.send(action, transport=transport)
