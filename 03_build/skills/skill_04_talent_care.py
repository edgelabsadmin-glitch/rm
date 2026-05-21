"""
SPEC-021 — Skill 04: talent-care (Design 05 / 01_design/skills/04-talent-care.md).

Schedule-driven (hourly). Fires for an Active placed Associate that is overdue
against the 90-day check-in cadence (75d for Mid/Enterprise placements) OR when a
welfare signal (burnout / growth / pay) fires. Drafts a warm talent check-in
(email + RM Salesforce Task). Guardrails: never surfaces customer-side concerns
to talent; skips Replaced/Terminated stages; one action per Talent per 30 days
(rate-limit via the event log); sparse profile → an "RM check-in needed" card
rather than a templated email.
"""

from __future__ import annotations

from pathlib import Path

from langfuse.decorators import observe

from core.agent.context import SkillContext, SuggestedAction, recently_actioned, submit_action
from core.llm import client
from core.llm.config import ANTHROPIC_SONNET

SKILL_ID = "talent-care"
_PROMPT = Path(__file__).parent / "prompts" / "skill_04_system.txt"
_SKIP_STAGES = {"Replaced", "Terminated"}
_RATE_LIMIT_DAYS = 30
_WELFARE_KEYS = ("burnout", "growth_concern", "pay_concern")
_SEV_RANK = {"low": 1, "medium": 2, "high": 3}
MODIFIABLE_FIELDS = [
    "body.email_draft.body",
    "body.email_draft.subject",
    "body.sfdc_task.description",
]


def is_overdue(days_since_checkin: int, tier: str | None) -> bool:
    threshold = 75 if tier in {"Mid-Market", "Enterprise"} else 90
    return days_since_checkin > threshold


def _welfare_severity(facts: dict) -> str | None:
    """Highest-severity welfare signal that fired, else None."""
    sev = 0
    for key in _WELFARE_KEYS:
        w = facts.get(key) or {}
        if w.get("fired"):
            sev = max(sev, _SEV_RANK.get(w.get("severity", "low"), 1))
    return {1: "low", 2: "medium", 3: "high"}.get(sev)


def should_fire(facts: dict, tier: str | None) -> tuple[bool, str | None]:
    """(fire?, urgency). Fires on cadence-overdue OR a welfare signal."""
    welfare = _welfare_severity(facts)
    overdue = is_overdue(facts.get("days_since_last_checkin", 0), tier)
    if welfare:
        return True, welfare
    if overdue:
        return True, "low"
    return False, None


@observe(name="skill_04_talent_care")
async def run(ctx: SkillContext) -> list[SuggestedAction]:
    if not ctx.talent_id:
        return []
    if (ctx.facts.get("stage") or "") in _SKIP_STAGES:
        return []  # Replaced/Terminated → different lifecycle (Skill 09)

    fire, urgency = should_fire(ctx.facts, ctx.tier)
    if not fire:
        return []
    if await recently_actioned(SKILL_ID, talent_id=ctx.talent_id, within_days=_RATE_LIMIT_DAYS):
        return []  # one talent-care action per Talent per 30 days

    days = ctx.facts.get("days_since_last_checkin", 0)
    reasoning = (
        f"[skill: {SKILL_ID}]\n[context: Talent={ctx.talent_id}, tier={ctx.tier}]\n\n"
        f"Signals consulted:\n  - <num>{days}</num> days since last check-in\n"
        f"  - welfare severity: {urgency}\n\n"
        "Proposed action: warm talent check-in (email + RM Task)."
    )

    if ctx.facts.get("profile_sparse"):
        action = SuggestedAction(
            skill_id=SKILL_ID,
            action_type="talent-checkin-sparse",
            body={
                "note": "RM check-in needed; Per-Profile is sparse — "
                "draft skipped to avoid a generic template."
            },
            why_oneline=f"Talent check-in needed ({ctx.talent_id}); profile sparse",
            urgency=urgency or "low",
            why_detail=reasoning,
            talent_id=ctx.talent_id,
        )
        await submit_action(ctx, action)
        return [action]

    from core.memory.retrievers import get_talent_context

    bundle: dict = dict(await get_talent_context(ctx.talent_id, graphiti=ctx.graphiti))
    name = (bundle.get("entity") or {}).get("name", ctx.talent_id)
    prompt = (
        f"Talent: {name}\nDays since last check-in: {days}\nWelfare severity: {urgency}\n"
        "Draft the talent check-in JSON. Never mention any customer-side concern."
    )
    text = await client.complete(ANTHROPIC_SONNET, prompt, system=_PROMPT.read_text())
    body = client.parse_json(text)

    action = SuggestedAction(
        skill_id=SKILL_ID,
        action_type="talent-checkin",
        body=body,
        why_oneline=f"Talent check-in for {name} ({urgency})",
        urgency=urgency or "low",
        why_detail=reasoning,
        modifiable_fields=MODIFIABLE_FIELDS,
        talent_id=ctx.talent_id,
    )
    await submit_action(ctx, action)
    return [action]
