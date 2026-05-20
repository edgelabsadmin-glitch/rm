"""SPEC-028 unit tests — Skill 11 detect-expansion-intent-from-job-posting."""

import json

import pytest

import skills.skill_11_detect_expansion_intent as skill
from core.agent.context import SkillContext


@pytest.fixture(autouse=True)
def _mock(monkeypatch):
    async def fake_recent(skill_id, *, talent_id=None, customer_id=None, within_days=30):
        return fake_recent.value

    fake_recent.value = False

    async def fake_complete(model, prompt, *, system="", max_tokens=None, temperature=0.0):
        return json.dumps({"email_draft": {"subject": "Saw your posting", "body": "..."}})

    async def fake_submit(ctx, action):
        fake_submit.calls.append(action)

    fake_submit.calls = []
    monkeypatch.setattr(skill, "recently_actioned", fake_recent)
    monkeypatch.setattr(skill.client, "complete", fake_complete)
    monkeypatch.setattr(skill, "submit_action", fake_submit)
    return fake_recent, fake_submit


@pytest.mark.parametrize("tier,urgency", [("hottest", "high"), ("warm", "medium")])
async def test_fires_on_hot_or_warm(_mock, tier, urgency):
    ctx = SkillContext(
        customer_id="001ACR", facts={"match_tier": tier, "matched_role": "medical-coder-ii"}
    )
    actions = await skill.run(ctx)
    assert actions[0].action_type == "expansion-intent-outreach"
    assert actions[0].urgency == urgency
    assert actions[0].body["posting"]["tier"] == tier


async def test_general_suppressed(_mock):
    assert (
        await skill.run(SkillContext(customer_id="001ACR", facts={"match_tier": "general"})) == []
    )


async def test_rate_limited(_mock):
    fake_recent, _ = _mock
    fake_recent.value = True
    ctx = SkillContext(customer_id="001ACR", facts={"match_tier": "hottest"})
    assert await skill.run(ctx) == []
