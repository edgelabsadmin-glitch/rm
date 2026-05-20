"""SPEC-022 unit tests — Skill 05 escalation-router (routing + guardrails)."""

import pytest

import skills.skill_05_escalation_router as skill
from core.agent.context import SkillContext
from skills.skill_05_escalation_router import route


@pytest.fixture(autouse=True)
def _mock(monkeypatch):
    async def fake_submit(ctx, action):
        fake_submit.calls.append(action)

    fake_submit.calls = []
    monkeypatch.setattr(skill, "submit_action", fake_submit)
    return fake_submit


def test_routing_table_payment_failure_to_finance_never_sales():
    assert route("Risk - Customer Payment Failure") == "Finance"
    assert route("Competitor") == "Sales"
    assert route("Risk - Resignation") == "Talent Ops"
    assert route("unknown category") == "CS leadership"  # default


async def test_run_routes_case(_mock):
    ctx = SkillContext(
        customer_id="001ACR",
        tier="Mid-Market",
        trigger="episode",
        facts={
            "risk_category": "Risk - Resignation",
            "case_id": "500X",
            "customer_name": "Acrisure",
        },
    )
    actions = await skill.run(ctx)
    assert len(actions) == 1
    assert actions[0].action_type == "escalation-routed"
    assert actions[0].body["routed_team"] == "Talent Ops"
    assert actions[0].body["sfdc_task"]["due_date_days"] == 1  # default urgency high


async def test_enterprise_ccs_vp_cs(_mock):
    ctx = SkillContext(
        customer_id="001ENT",
        tier="Enterprise",
        facts={"risk_category": "Competitor", "case_id": "c1"},
    )
    actions = await skill.run(ctx)
    assert "vp-cs" in actions[0].body["email_draft"]["cc"]


async def test_self_healed_skip(_mock):
    ctx = SkillContext(customer_id="x", facts={"stage_transition": "Replaced", "self_healed": True})
    assert await skill.run(ctx) == []


async def test_already_routed_skip(_mock):
    ctx = SkillContext(
        customer_id="x", facts={"risk_category": "Competitor", "already_routed": True}
    )
    assert await skill.run(ctx) == []


async def test_no_trigger_no_fire(_mock):
    assert await skill.run(SkillContext(customer_id="x", facts={})) == []
