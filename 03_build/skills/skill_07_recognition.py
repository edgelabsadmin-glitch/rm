"""
SPEC-024 — Skill 07: recognition (Design 05 / 01_design/skills/07-recognition.md).

Episode-driven. Drafts a short, warm recognition note for one of three audiences
(customer champion / placed talent / the RM, drafted as if from the VP). Fires on
positive quotes, milestones, or resolved Cases. Auto-approve at +1h (policy rule
3, low blast radius). Guardrails: no recognition while an active risk-Case burns
at the same customer; no talent recognition for placements <30 days old; no
internal RM recognition more than once per RM per week.
"""

from __future__ import annotations

from langfuse import observe

from core.agent.context import SkillContext, SuggestedAction, recently_actioned, submit_action
from core.llm import client
from core.llm.config import ANTHROPIC_SONNET

SKILL_ID = "recognition"
_RM_RATE_LIMIT_DAYS = 7
_MIN_PLACEMENT_DAYS = 30
_SYSTEM = (
    "You are EDGE Pulse drafting a short (2-4 sentence), warm recognition note. "
    "Ground it in one VERBATIM quote or one concrete milestone fact; never "
    'fabricate. Return ONLY JSON: {"email_draft": {"subject": "", "body": ""}}'
)
MODIFIABLE_FIELDS = ["body.email_draft.body", "body.email_draft.subject"]


def _has_moment(facts: dict) -> bool:
    return bool(facts.get("positive_quote") or facts.get("milestone") or facts.get("resolved_case"))


@observe(name="skill_07_recognition")
async def run(ctx: SkillContext) -> list[SuggestedAction]:
    f = ctx.facts
    if not _has_moment(f) or f.get("active_risk_case"):
        return []  # defer recognition while a fire burns at the customer

    audience = f.get("audience", "customer")  # customer | talent | rm
    if audience == "talent" and f.get("placement_days", 999) < _MIN_PLACEMENT_DAYS:
        return []
    if audience == "rm" and await recently_actioned(
        SKILL_ID, customer_id=ctx.rm_id, within_days=_RM_RATE_LIMIT_DAYS
    ):
        return []

    moment = f.get("positive_quote") or f.get("milestone") or "a recent positive moment"
    prompt = f"Audience: {audience}\nMoment: {moment}"
    text = await client.complete(ANTHROPIC_SONNET, prompt, system=_SYSTEM)
    draft = client.parse_json(text)

    action = SuggestedAction(
        skill_id=SKILL_ID,
        action_type="recognition-note",
        body={"audience": audience, "email_draft": draft.get("email_draft", {})},
        why_oneline=f"Recognition ({audience}): {str(moment)[:60]}",
        urgency="low",
        why_detail=f"[skill: {SKILL_ID}] audience={audience}; moment grounded in evidence.",
        modifiable_fields=MODIFIABLE_FIELDS,
        customer_id=ctx.customer_id,
        talent_id=ctx.talent_id if audience == "talent" else None,
    )
    await submit_action(ctx, action)
    return [action]
