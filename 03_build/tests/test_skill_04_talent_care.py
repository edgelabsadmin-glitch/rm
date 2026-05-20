"""SPEC-021 unit tests — Skill 04 talent-care (cadence, welfare, rate-limit, guards)."""

import json

import pytest

import skills.skill_04_talent_care as skill
from core.agent.context import SkillContext
from skills.skill_04_talent_care import is_overdue, should_fire

_DRAFT = {
    "email_draft": {"subject": "Quick check-in", "body": "Hi — how's the ramp going?"},
    "sfdc_task": {
        "subject": "Talent check-in: Marcus",
        "description": "overdue 95d",
        "due_date_days": 5,
    },
}


def test_is_overdue_tier_thresholds():
    assert is_overdue(91, "SMB") is True
    assert is_overdue(80, "SMB") is False
    assert is_overdue(80, "Enterprise") is True  # 75d threshold for Mid/Ent
    assert is_overdue(70, "Mid-Market") is False


def test_should_fire_welfare_and_cadence():
    assert should_fire({"burnout": {"fired": True, "severity": "high"}}, "SMB") == (True, "high")
    assert should_fire({"days_since_last_checkin": 100}, "SMB") == (True, "low")
    assert should_fire({"days_since_last_checkin": 10}, "SMB") == (False, None)


@pytest.fixture
def _mock(monkeypatch):
    async def fake_recent(skill_id, *, talent_id=None, customer_id=None, within_days=30):
        return fake_recent.value

    fake_recent.value = False

    async def fake_get_talent_context(talent_id, as_of=None, *, graphiti=None):
        return {"entity": {"uuid": "t1", "name": "Marcus Wells"}}

    async def fake_complete(model, prompt, *, system="", max_tokens=None, temperature=0.0):
        fake_complete.captured = {"prompt": prompt, "system": system}
        return json.dumps(_DRAFT)

    async def fake_submit(ctx, action):
        fake_submit.calls.append(action)

    fake_submit.calls = []
    monkeypatch.setattr(skill, "recently_actioned", fake_recent)
    monkeypatch.setattr("core.memory.retrievers.get_talent_context", fake_get_talent_context)
    monkeypatch.setattr(skill.client, "complete", fake_complete)
    monkeypatch.setattr(skill, "submit_action", fake_submit)
    return fake_recent, fake_submit, fake_complete


async def test_run_drafts_checkin_when_overdue(_mock):
    _, fake_submit, fake_complete = _mock
    ctx = SkillContext(
        talent_id="a0X", tier="Mid-Market", facts={"stage": "Active", "days_since_last_checkin": 95}
    )
    actions = await skill.run(ctx)
    assert len(actions) == 1 and actions[0].action_type == "talent-checkin"
    assert actions[0].talent_id == "a0X"
    assert "email_draft" in actions[0].body
    assert len(fake_submit.calls) == 1
    assert "never mention" in fake_complete.captured["system"].lower()


async def test_run_skips_replaced_stage(_mock):
    ctx = SkillContext(
        talent_id="a0X", tier="SMB", facts={"stage": "Replaced", "days_since_last_checkin": 200}
    )
    assert await skill.run(ctx) == []


async def test_run_rate_limited(_mock):
    fake_recent, _, _ = _mock
    fake_recent.value = True
    ctx = SkillContext(
        talent_id="a0X", tier="SMB", facts={"stage": "Active", "days_since_last_checkin": 200}
    )
    assert await skill.run(ctx) == []


async def test_run_sparse_profile_emits_card(_mock):
    _, fake_submit, _ = _mock
    ctx = SkillContext(
        talent_id="a0X",
        tier="SMB",
        facts={"stage": "Active", "days_since_last_checkin": 200, "profile_sparse": True},
    )
    actions = await skill.run(ctx)
    assert actions[0].action_type == "talent-checkin-sparse"


async def test_run_no_fire_when_current(_mock):
    ctx = SkillContext(
        talent_id="a0X", tier="SMB", facts={"stage": "Active", "days_since_last_checkin": 10}
    )
    assert await skill.run(ctx) == []
