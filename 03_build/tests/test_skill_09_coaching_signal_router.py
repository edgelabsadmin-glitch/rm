"""SPEC-026 unit tests — Skill 09 coaching-signal-router."""

import pytest

import skills.skill_09_coaching_signal_router as skill
from core.agent.context import SkillContext
from skills.skill_09_coaching_signal_router import _routable


@pytest.fixture(autouse=True)
def _mock(monkeypatch):
    async def fake_submit(ctx, action):
        fake_submit.calls.append(action)

    fake_submit.calls = []
    monkeypatch.setattr(skill, "submit_action", fake_submit)
    return fake_submit


def test_routable_only_medium_plus():
    assert _routable({"growth_concern": {"fired": True, "severity": "low"}}) == []
    assert _routable({"pay_concern": {"fired": True, "severity": "high"}}) == [
        ("pay_concern", "high")
    ]


async def test_routes_highest_severity(_mock):
    ctx = SkillContext(
        talent_id="a0X",
        facts={
            "growth_concern": {"fired": True, "severity": "medium"},
            "burnout": {"fired": True, "severity": "high"},
            "talent_name": "Marcus",
        },
    )
    actions = await skill.run(ctx)
    assert actions[0].action_type == "coaching-handoff"
    assert actions[0].body["to_team"] == "Talent Wellbeing"  # burnout high wins
    assert actions[0].urgency == "high"


async def test_no_welfare_no_fire(_mock):
    assert await skill.run(SkillContext(talent_id="a0X", facts={})) == []
