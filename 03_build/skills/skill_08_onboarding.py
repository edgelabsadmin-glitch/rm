"""
SPEC-025 — Skill 08: onboarding (Design 05 / 01_design/skills/08-onboarding.md).

Episode-driven on a new Active placement. Proposes an onboarding kickoff
(checklist + RM Salesforce Task). Deterministic template (no LLM). One onboarding
action per placed Talent (rate-limit via the event log).
"""

from __future__ import annotations

from langfuse import observe

from core.agent.context import SkillContext, SuggestedAction, recently_actioned, submit_action

SKILL_ID = "onboarding"
_KICKOFF_CHECKLIST = [
    "Confirm start date + first-day logistics with the client manager",
    "Schedule the 7-day check-in with the placed associate",
    "Verify access/credentials provisioned by the client",
    "Set the 30-day talent-care cadence anchor",
]
MODIFIABLE_FIELDS = ["body.checklist", "body.sfdc_task.description"]


@observe(name="skill_08_onboarding")
async def run(ctx: SkillContext) -> list[SuggestedAction]:
    f = ctx.facts
    if not (f.get("new_placement") and (f.get("stage") or "Active") == "Active"):
        return []
    if ctx.talent_id and await recently_actioned(
        SKILL_ID, talent_id=ctx.talent_id, within_days=365
    ):
        return []  # one onboarding per placement

    name = f.get("talent_name") or ctx.talent_id or "the new associate"
    body = {
        "checklist": list(_KICKOFF_CHECKLIST),
        "sfdc_task": {
            "subject": f"Onboarding kickoff: {name}",
            "description": f"New placement at {ctx.customer_id or 'client'} — run checklist.",
            "due_date_days": 2,
        },
    }
    action = SuggestedAction(
        skill_id=SKILL_ID,
        action_type="onboarding",
        body=body,
        why_oneline=f"Onboarding kickoff for {name}",
        urgency="low",
        why_detail=f"[skill: {SKILL_ID}] new Active placement; kickoff checklist proposed.",
        modifiable_fields=MODIFIABLE_FIELDS,
        customer_id=ctx.customer_id,
        talent_id=ctx.talent_id,
    )
    await submit_action(ctx, action)
    return [action]
