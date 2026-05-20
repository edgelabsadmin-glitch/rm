"""
SPEC-018 unit tests — Skill 02 meeting-brief composition (mocked LLM/retriever/submit).

No live LLM/DB: get_customer_context, client.complete, and submit_action are
monkeypatched. A gated integration test (real Graphiti + LLM) is in
tests/test_skill_02_integration.py.
"""

import json

import pytest

import skills.skill_02_prepare_customer_meeting_brief as skill
from core.agent.context import SkillContext

_FAKE_BUNDLE = {
    "entity": {"uuid": "u-1", "name": "Acrisure"},
    "temporal_facts": [{"edge_type": "raised_concern_about", "fact": "vendor consolidation"}],
    "relationships": [
        {"edge_type": "placed_at", "other": "Marcus Wells", "fact": "Dental Coder II"}
    ],
    "recent_episodes": [{"uuid": "ep-1", "name": "Acrisure EBR", "content": "QBR notes"}],
    "skills": [],
    "as_of": None,
}

_FAKE_BRIEF = {
    "headline": "Acrisure is in a watch state; lead with the dental ramp plan.",
    "top_issues": [
        "Vendor consolidation pressure (source: Acrisure EBR)",
        "Dental ramp",
        "Renewal",
    ],
    "at_risk_talent": [
        {
            "name": "Marcus Wells",
            "role": "Dental Coder II",
            "risk_summary": "audits",
            "source": "Case",
        }
    ],
    "positive_performers": [],
    "talking_points": ["Address CFO mandate", "Show ramp plan", "Confirm renewal timing"],
    "recent_activity": "EBR held; replacement plan delivered.",
}


@pytest.fixture(autouse=True)
def _mock_io(monkeypatch):
    async def fake_get_customer_context(customer_id, as_of=None, *, graphiti=None):
        return dict(_FAKE_BUNDLE)

    async def fake_complete(model, prompt, *, system="", max_tokens=None, temperature=0.0):
        fake_complete.captured = {"model": model, "system": system, "prompt": prompt}
        return "```json\n" + json.dumps(_FAKE_BRIEF) + "\n```"

    async def fake_submit(ctx, action):
        fake_submit.calls.append(action)
        return None

    fake_submit.calls = []
    monkeypatch.setattr("core.memory.retrievers.get_customer_context", fake_get_customer_context)
    monkeypatch.setattr(skill.client, "complete", fake_complete)
    monkeypatch.setattr(skill, "submit_action", fake_submit)
    return fake_complete, fake_submit


def test_system_prompt_word_cap_is_tier_aware():
    assert "400" in skill._system_prompt("SMB")
    assert "1000" in skill._system_prompt("Enterprise")
    assert "700" in skill._system_prompt("Mid-Market")


async def test_run_composes_brief_action(_mock_io):
    fake_complete, fake_submit = _mock_io
    ctx = SkillContext(customer_id="001ACRISURE", tier="Mid-Market", trigger="calendar")
    actions = await skill.run(ctx)

    assert len(actions) == 1
    a = actions[0]
    assert a.action_type == "meeting-brief"
    assert a.skill_id == "prepare-customer-meeting-brief"
    assert a.body["headline"].startswith("Acrisure")
    assert len(a.body["top_issues"]) == 3
    assert a.modifiable_fields == ["body.top_issues", "body.talking_points"]
    assert a.source_episodes == ["ep-1"]
    # reasoning capture uses the inline-tag voice
    assert "<num>" in a.why_detail and "[skill: prepare-customer-meeting-brief]" in a.why_detail
    # routed through submit_action exactly once
    assert len(fake_submit.calls) == 1
    # Sonnet model + tier cap reached the LLM
    assert "sonnet" in fake_complete.captured["model"]
    assert "700" in fake_complete.captured["system"]


async def test_unknown_customer_emits_no_brief():
    actions = await skill.run(SkillContext(customer_id=None, trigger="calendar"))
    assert actions == []
