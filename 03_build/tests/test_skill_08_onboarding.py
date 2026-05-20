"""SPEC-025 unit tests — Skill 08 onboarding."""

import pytest

import skills.skill_08_onboarding as skill
from core.agent.context import SkillContext


@pytest.fixture(autouse=True)
def _mock(monkeypatch):
    async def fake_recent(skill_id, *, talent_id=None, customer_id=None, within_days=30):
        return fake_recent.value

    fake_recent.value = False

    async def fake_submit(ctx, action):
        fake_submit.calls.append(action)

    fake_submit.calls = []
    monkeypatch.setattr(skill, "recently_actioned", fake_recent)
    monkeypatch.setattr(skill, "submit_action", fake_submit)
    return fake_recent, fake_submit


async def test_fires_on_new_active_placement(_mock):
    ctx = SkillContext(
        customer_id="001ACR",
        talent_id="a0X",
        facts={"new_placement": True, "stage": "Active", "talent_name": "Aisha"},
    )
    actions = await skill.run(ctx)
    assert actions[0].action_type == "onboarding"
    assert len(actions[0].body["checklist"]) == 4


async def test_no_fire_without_new_placement(_mock):
    assert await skill.run(SkillContext(talent_id="a0X", facts={"stage": "Active"})) == []


async def test_rate_limited(_mock):
    fake_recent, _ = _mock
    fake_recent.value = True
    ctx = SkillContext(talent_id="a0X", facts={"new_placement": True, "stage": "Active"})
    assert await skill.run(ctx) == []
