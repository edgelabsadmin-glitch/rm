"""
SPEC-019 unit tests — Skill 03 renewal-watcher (scoring + run, mocked LLM/IO).
"""

import json

import pytest

import skills.skill_03_renewal_watcher as skill
from core.agent.context import SkillContext
from skills.skill_03_renewal_watcher import score_renewal_risk

_DRAFT = {
    "email_draft": {
        "subject": "Quick check-in ahead of renewal",
        "body": "Hi — wanted to connect...",
    },
    "sfdc_task": {
        "subject": "Renewal at risk: Acrisure",
        "description": "churn signals + silence",
        "due_date_days": 2,
    },
}


# ── composite risk scoring (golden-trace) ────────────────────────────────────
def test_score_high_on_churn_signal_count():
    level, factors = score_renewal_risk({"churn_signal_count_90d": 3})
    assert level == "high" and "churn_signals>=3" in factors["high"]


def test_score_high_on_open_case_or_replacement_or_churn_prob():
    assert score_renewal_risk({"open_risk_cases": 1})[0] == "high"
    assert score_renewal_risk({"replacement_rate": 0.4})[0] == "high"
    assert score_renewal_risk({"churn_probability": 0.6})[0] == "high"


def test_score_medium_on_single_medium_factor():
    assert score_renewal_risk({"no_rm_outreach_60d": True})[0] == "medium"
    assert score_renewal_risk({"negative_sentiment_trajectory": True})[0] == "medium"


def test_mitigating_downgrades():
    # one high + mitigating, no mediums → medium
    assert (
        score_renewal_risk({"open_risk_cases": 1, "positive_expansion_signal": True})[0] == "medium"
    )
    # medium + mitigating → low
    assert (
        score_renewal_risk({"no_rm_outreach_60d": True, "positive_expansion_signal": True})[0]
        == "low"
    )


def test_score_low_when_clean():
    assert score_renewal_risk({})[0] == "low"


# ── run() ────────────────────────────────────────────────────────────────────
@pytest.fixture
def _mock_io(monkeypatch):
    async def fake_get_customer_context(customer_id, as_of=None, *, graphiti=None):
        return {"entity": {"uuid": "u-1", "name": "Acrisure"}, "recent_episodes": []}

    async def fake_complete(model, prompt, *, system="", max_tokens=None, temperature=0.0):
        fake_complete.captured = {"prompt": prompt, "system": system}
        return json.dumps(_DRAFT)

    async def fake_submit(ctx, action):
        fake_submit.calls.append(action)

    fake_submit.calls = []
    monkeypatch.setattr("core.memory.retrievers.get_customer_context", fake_get_customer_context)
    monkeypatch.setattr(skill.client, "complete", fake_complete)
    monkeypatch.setattr(skill, "submit_action", fake_submit)
    return fake_complete, fake_submit


async def test_run_drafts_renewal_touch_when_at_risk(_mock_io):
    fake_complete, fake_submit = _mock_io
    ctx = SkillContext(
        customer_id="001ACRISURE",
        tier="Mid-Market",
        trigger="scheduled",
        facts={"renewal_days": 45, "churn_signal_count_90d": 3},
    )
    actions = await skill.run(ctx)
    assert len(actions) == 1
    a = actions[0]
    assert a.action_type == "renewal-touch"
    assert a.urgency == "high"
    assert "email_draft" in a.body and "sfdc_task" in a.body
    assert a.modifiable_fields == skill.MODIFIABLE_FIELDS
    assert len(fake_submit.calls) == 1
    # guardrail instruction reached the model
    assert (
        "no specific placed talent" in fake_complete.captured["system"].lower()
        or "never an individual" in fake_complete.captured["system"].lower()
    )


async def test_run_renewal_window_guard(_mock_io):
    # renewal 200d out (> Mid 90 and > 120 cap) → no fire
    ctx = SkillContext(
        customer_id="x", tier="Mid-Market", facts={"renewal_days": 200, "churn_signal_count_90d": 5}
    )
    assert await skill.run(ctx) == []


async def test_run_no_fire_when_low_risk(_mock_io):
    ctx = SkillContext(customer_id="x", tier="SMB", facts={"renewal_days": 30})
    assert await skill.run(ctx) == []
