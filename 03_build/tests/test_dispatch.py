"""SPEC-032 unit tests — channel routing + message composition (no DB)."""

from datetime import UTC, datetime

import pytest

from core.actions.queue import ActionRecord
from core.dispatch import calendar_hold, email, sfdc_task
from core.dispatch.base import channel_for


def _rec(action_card: dict, *, urgency="medium", rm_id="rmX", customer_id="001A") -> ActionRecord:
    return ActionRecord(
        action_id="a1",
        skill_id="renewal-watcher",
        customer_id=customer_id,
        talent_id=None,
        rm_id=rm_id,
        tier_class="Enterprise",
        urgency=urgency,
        action_card=action_card,
        why_oneline="why",
        why_detail=None,
        modifiable_fields=[],
        source_episodes=[],
        proposed_at=datetime(2026, 5, 20, tzinfo=UTC),
    )


def test_channel_explicit_overrides_action_type():
    rec = _rec({"action_type": "escalation-routed", "channel": "email"})
    assert channel_for(rec) == "email"


def test_channel_by_action_type_map():
    assert channel_for(_rec({"action_type": "renewal-touch"})) == "email"
    assert channel_for(_rec({"action_type": "escalation-routed"})) == "sfdc_task"


def test_channel_unknown_action_type_defaults_to_sfdc_task():
    assert channel_for(_rec({"action_type": "brand-new-thing"})) == "sfdc_task"


def test_email_compose_pulls_fields_with_fallbacks():
    msg = email.compose(_rec({"to": "cfo@acme.com", "subject": "Renewal", "body": "Hi"}))
    assert msg.to == ["cfo@acme.com"] and msg.subject == "Renewal" and msg.body == "Hi"
    assert msg.from_rm_id == "rmX"
    # subject falls back to why_oneline when absent
    assert email.compose(_rec({"recipient": "x@y.com"})).subject == "why"


def test_sfdc_task_values_shape():
    vals = sfdc_task._compose_values(
        _rec({"subject": "Follow up", "body": "details"}, urgency="high")
    )
    assert vals["Subject"] == "Follow up"
    assert vals["Description"] == "details"
    assert vals["Priority"] == "High"
    assert vals["OwnerId"] == "rmX"
    assert vals["WhatId"] == "001A"


def test_calendar_hold_synthesizes_link():
    rec = _rec({"action_type": "meeting-brief", "proposed_time": "2026-06-01T15:00"})
    calendar_hold._ensure_calendar_link(rec)
    assert rec.action_card["calendar_link"].startswith("calendar-hold://a1")


async def test_email_send_uses_injected_transport():
    sent = {}

    class FakeTransport:
        async def send(self, msg):
            sent["msg"] = msg
            return "msg-123"

    mid = await email.send(
        _rec({"to": "a@b.com", "subject": "S", "body": "B"}), transport=FakeTransport()
    )
    assert mid == "msg-123"
    assert sent["msg"].subject == "S"


async def test_not_configured_transport_raises():
    with pytest.raises(RuntimeError, match="no email OAuth transport"):
        await email.send(_rec({"to": "a@b.com"}))
