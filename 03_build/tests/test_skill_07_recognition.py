"""SPEC-024 unit tests — Skill 07 recognition (moment, audiences, guardrails)."""

import json

import pytest

import skills.skill_07_recognition as skill
from core.agent.context import SkillContext
from skills.skill_07_recognition import _has_moment


@pytest.fixture
def _mock(monkeypatch):
    async def fake_recent(skill_id, *, talent_id=None, customer_id=None, within_days=30):
        return fake_recent.value

    fake_recent.value = False

    async def fake_complete(model, prompt, *, system="", max_tokens=None, temperature=0.0):
        return json.dumps({"email_draft": {"subject": "Thanks", "body": "..."}})

    async def fake_submit(ctx, action):
        fake_submit.calls.append(action)

    fake_submit.calls = []
    monkeypatch.setattr(skill, "recently_actioned", fake_recent)
    monkeypatch.setattr(skill.client, "complete", fake_complete)
    monkeypatch.setattr(skill, "submit_action", fake_submit)
    return fake_recent, fake_submit


def test_has_moment():
    assert _has_moment({"positive_quote": "great"}) is True
    assert _has_moment({"milestone": "1yr"}) is True
    assert _has_moment({}) is False


async def test_run_customer_recognition(_mock):
    ctx = SkillContext(
        customer_id="001ACR", facts={"positive_quote": "your team is great", "audience": "customer"}
    )
    actions = await skill.run(ctx)
    assert actions[0].action_type == "recognition-note"
    assert actions[0].body["audience"] == "customer"


async def test_run_defers_during_active_risk(_mock):
    ctx = SkillContext(
        customer_id="001ACR", facts={"positive_quote": "q", "active_risk_case": True}
    )
    assert await skill.run(ctx) == []


async def test_run_talent_recognition_needs_30d_placement(_mock):
    young = SkillContext(
        talent_id="a0X",
        facts={"milestone": "first month", "audience": "talent", "placement_days": 10},
    )
    assert await skill.run(young) == []
    mature = SkillContext(
        talent_id="a0X", facts={"milestone": "1 year", "audience": "talent", "placement_days": 365}
    )
    actions = await skill.run(mature)
    assert actions[0].talent_id == "a0X"


async def test_run_rm_recognition_rate_limited(_mock):
    fake_recent, _ = _mock
    fake_recent.value = True
    ctx = SkillContext(rm_id="005RM", facts={"milestone": "closed renewal", "audience": "rm"})
    assert await skill.run(ctx) == []
