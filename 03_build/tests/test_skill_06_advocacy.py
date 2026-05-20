"""SPEC-023 unit tests — Skill 06 advocacy (eligibility, motion, guardrails)."""

import json

import pytest

import skills.skill_06_advocacy as skill
from core.agent.context import SkillContext
from skills.skill_06_advocacy import _eligible


@pytest.fixture
def _mock(monkeypatch):
    async def fake_recent(skill_id, *, talent_id=None, customer_id=None, within_days=30):
        return fake_recent.value

    fake_recent.value = False

    async def fake_complete(model, prompt, *, system="", max_tokens=None, temperature=0.0):
        return json.dumps({"email_draft": {"subject": "Thank you", "body": "..."}})

    async def fake_submit(ctx, action):
        fake_submit.calls.append(action)

    fake_submit.calls = []
    monkeypatch.setattr(skill, "recently_actioned", fake_recent)
    monkeypatch.setattr(skill.client, "complete", fake_complete)
    monkeypatch.setattr(skill, "submit_action", fake_submit)
    return fake_recent, fake_submit


def test_eligible_logic():
    assert _eligible({"advocacy_score": 0.7}) is True
    assert _eligible({"positive_quotes": ["great"]}) is True
    assert _eligible({"advocacy_score": 0.7, "active_risk_categories": ["Competitor"]}) is False
    assert _eligible({}) is False


async def test_run_proposes_reference_call(_mock):
    _, fake_submit = _mock
    ctx = SkillContext(
        customer_id="001ACR", facts={"advocacy_score": 0.8, "positive_quotes": ["q"]}
    )
    actions = await skill.run(ctx)
    assert actions[0].action_type == "advocacy-touch"
    assert actions[0].body["proposed_motion"] == "reference-call"


async def test_run_recognition_motion_when_reference_declined(_mock):
    ctx = SkillContext(
        customer_id="001ACR", facts={"advocacy_score": 0.8, "reference_declined_12mo": True}
    )
    actions = await skill.run(ctx)
    assert actions[0].body["proposed_motion"] == "recognition"


async def test_run_rate_limited(_mock):
    fake_recent, _ = _mock
    fake_recent.value = True
    ctx = SkillContext(customer_id="001ACR", facts={"advocacy_score": 0.9})
    assert await skill.run(ctx) == []


async def test_run_blocked_by_active_risk(_mock):
    ctx = SkillContext(
        customer_id="001ACR",
        facts={"advocacy_score": 0.9, "active_risk_categories": ["Risk - Resignation"]},
    )
    assert await skill.run(ctx) == []
