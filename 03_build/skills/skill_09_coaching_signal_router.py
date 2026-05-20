"""
SPEC-026 — Skill 09: coaching-signal-router (Design 05 /
01_design/skills/09-coaching-signal-router.md).

Episode-driven. When a talent-welfare signal (growth / pay / burnout) fires at
medium+ severity, routes a coaching/HR handoff to the right internal owner.
Deterministic (no LLM). Can fire concurrently with Skill 04 (talent-care).
"""

from __future__ import annotations

from langfuse import observe

from core.agent.context import SkillContext, SuggestedAction, submit_action

SKILL_ID = "coaching-signal-router"
_SEV_RANK = {"low": 1, "medium": 2, "high": 3}
# welfare signal → handoff owner
_HANDOFF = {
    "growth_concern": "Talent Development",
    "pay_concern": "Compensation / Finance",
    "burnout": "Talent Wellbeing",
}
MODIFIABLE_FIELDS = ["body.handoff_note", "body.sfdc_task.description"]


def _routable(facts: dict) -> list[tuple[str, str]]:
    """(welfare_key, severity) pairs that fired at medium+."""
    out = []
    for key in _HANDOFF:
        w = facts.get(key) or {}
        if w.get("fired") and _SEV_RANK.get(w.get("severity", "low"), 1) >= 2:
            out.append((key, w.get("severity", "medium")))
    return out


@observe(name="skill_09_coaching_signal_router")
async def run(ctx: SkillContext) -> list[SuggestedAction]:
    routable = _routable(ctx.facts)
    if not routable:
        return []
    # Highest-severity welfare signal drives the primary handoff.
    key, severity = max(routable, key=lambda kv: _SEV_RANK[kv[1]])
    owner = _HANDOFF[key]
    name = ctx.facts.get("talent_name") or ctx.talent_id or "the associate"

    body = {
        "handoff_note": f"{key.replace('_', ' ')} signal ({severity}) for {name} → {owner}.",
        "to_team": owner,
        "sfdc_task": {
            "subject": f"Coaching handoff: {name} ({key})",
            "description": f"Routed to {owner}; severity {severity}. Coordinate with talent-care.",
            "due_date_days": 3,
        },
    }
    action = SuggestedAction(
        skill_id=SKILL_ID,
        action_type="coaching-handoff",
        body=body,
        why_oneline=f"Coaching handoff: {name} → {owner}",
        urgency=severity,
        why_detail=f"[skill: {SKILL_ID}] {key}={severity}; routed to {owner}.",
        modifiable_fields=MODIFIABLE_FIELDS,
        customer_id=ctx.customer_id,
        talent_id=ctx.talent_id,
    )
    await submit_action(ctx, action)
    return [action]
