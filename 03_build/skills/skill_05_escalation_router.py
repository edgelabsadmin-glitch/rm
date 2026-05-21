"""
SPEC-022 — Skill 05: escalation-router (Design 05 / 01_design/skills/05-escalation-router.md).

Episode-driven. Classifies a risk-tagged Case (or high-urgency concern / talent
stage transition) by category and routes it to the right internal team via the
Phase-1 routing table, proposing an escalation-routed action (team email + SFDC
Task; Jira is v1.5+). Deterministic — no LLM. Guardrails: skip self-healed
replacements, skip if already routed for this case, Payment-Failure never to
Sales (the table owns this), Enterprise always cc VP-CS.
"""

from __future__ import annotations

from langfuse.decorators import observe

from core.agent.context import SkillContext, SuggestedAction, submit_action

SKILL_ID = "escalation-router"

# Risk category → internal team (Design 05 routing table).
ROUTING_TABLE = {
    "Risk - Talent Competency": "Talent Dev",
    "Risk - Resignation": "Talent Ops",
    "Risk - Talent Professionalism": "Talent Dev + HR",
    "Risk - Customer Payment Failure": "Finance",  # hard rule: never Sales
    "Risk - ADP": "Payroll",
    "Risk – Role Change": "Sales",
    "Risk – Emergency Leaves": "HR",
    "Poor Experience with Edge": "CS leadership",
    "Competitor": "Sales",
    "Performance": "Talent Dev",
    "Relationship Management": "CS leadership",
    "Business Performance": "Finance + CS leadership",
    "Business Needs": "Sales",
}
_DEFAULT_TEAM = "CS leadership"
MODIFIABLE_FIELDS = [
    "body.email_draft.body",
    "body.email_draft.cc",
    "body.sfdc_task.description",
    "body.sfdc_task.due_date",
]


def route(category: str | None) -> str:
    return ROUTING_TABLE.get(category or "", _DEFAULT_TEAM)


@observe(name="skill_05_escalation_router")
async def run(ctx: SkillContext) -> list[SuggestedAction]:
    f = ctx.facts
    category = f.get("risk_category")
    case_id = f.get("case_id")
    # Fire only on a real escalation trigger.
    if not (category or f.get("stage_transition") or f.get("high_urgency_concern")):
        return []
    if f.get("self_healed") or f.get("already_routed"):
        return []  # successor placement within 7d / existing open escalation

    team = route(category)
    urgency = f.get("urgency", "high")
    cc = [e for e in [ctx.rm_id and f"rm:{ctx.rm_id}"] if e]
    if ctx.tier == "Enterprise":
        cc.append("vp-cs")
    due_days = 1 if urgency == "high" else 3

    customer = f.get("customer_name") or ctx.customer_id or "the customer"
    trigger = category or f.get("stage_transition") or "high-urgency concern"
    reasoning = (
        f"[skill: {SKILL_ID}]\n[context: Customer={customer}, case={case_id}, tier={ctx.tier}]\n\n"
        f"Signals consulted:\n  - <bad>{trigger}</bad>\n\n"
        f"Reasoning:\n  Routed to <em>{team}</em> per the category routing table.\n\n"
        "Proposed action: escalation routed (team email + SFDC Task)."
    )
    body = {
        "email_draft": {
            "to": f"{team.lower().replace(' ', '-')}@onedge.co",
            "cc": cc,
            "subject": f"Escalation: {category or 'risk'} @ {customer}",
            "body": f"Routing a {category or 'risk'} escalation at {customer} to {team}. "
            "RM is cc'd. See the linked Case for full context.",
        },
        "sfdc_task": {
            "subject": f"Escalation routed: {category or 'risk'}",
            "description": f"Routed to {team}. Trigger: {category or f.get('stage_transition')}.",
            "related_to": case_id,
            "due_date_days": due_days,
        },
        "routed_team": team,
    }
    action = SuggestedAction(
        skill_id=SKILL_ID,
        action_type="escalation-routed",
        body=body,
        why_oneline=f"Escalation @ {customer} → {team}",
        urgency=urgency,
        why_detail=reasoning,
        modifiable_fields=MODIFIABLE_FIELDS,
        customer_id=ctx.customer_id,
        talent_id=ctx.talent_id,
    )
    await submit_action(ctx, action)
    return [action]
