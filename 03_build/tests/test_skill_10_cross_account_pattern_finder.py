"""SPEC-027 unit tests — Skill 10 cross-account-pattern-finder (mocked retriever)."""

import pytest

import skills.skill_10_cross_account_pattern_finder as skill
from core.agent.context import SkillContext
from core.memory.retrievers import CrossAccountMatch


@pytest.fixture
def _mock(monkeypatch):
    async def fake_find(
        theme, time_window_days=30, min_support=3, *, graphiti=None, namespace="pulse"
    ):
        return fake_find.matches

    fake_find.matches = []

    async def fake_submit(ctx, action):
        fake_submit.calls.append(action)

    fake_submit.calls = []
    monkeypatch.setattr("core.memory.retrievers.find_pattern_across_customers", fake_find)
    monkeypatch.setattr(skill, "submit_action", fake_submit)
    return fake_find, fake_submit


def _match(name):
    return CrossAccountMatch(
        customer_id=name, customer_name=name, episode_id="e", quote="q", date=None
    )


async def test_surfaces_when_min_support_met(_mock):
    fake_find, _ = _mock
    fake_find.matches = [_match("Acrisure"), _match("Mendota"), _match("DHR")]
    ctx = SkillContext(facts={"theme": "vendor consolidation"})
    actions = await skill.run(ctx)
    assert actions[0].action_type == "pattern-surface"
    assert len(actions[0].body["customers"]) == 3


async def test_no_pattern_below_min_support(_mock):
    fake_find, _ = _mock
    fake_find.matches = [_match("Acrisure")]
    assert await skill.run(SkillContext(facts={"theme": "vendor consolidation"})) == []


async def test_no_theme_no_fire(_mock):
    assert await skill.run(SkillContext(facts={})) == []
