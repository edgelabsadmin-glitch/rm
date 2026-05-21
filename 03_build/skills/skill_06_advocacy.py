"""
SPEC-023 — Skill 06: advocacy (Design 05 / 01_design/skills/06-advocacy.md).

Weekly. Surfaces ambassador candidates from strong positive signals and proposes
one higher-quality motion (recognition / reference-call / case-study). Drafts the
champion email via Sonnet, opening with the strongest verbatim quote. Guardrails:
no advocacy while an override risk-Case is active; reference-call → recognition
if the customer declined a reference in the last 12 months; one advocacy action
per customer per quarter (90-day rate-limit).
"""

from __future__ import annotations

from langfuse.decorators import observe

from core.agent.context import SkillContext, SuggestedAction, recently_actioned, submit_action
from core.llm import client
from core.llm.config import ANTHROPIC_SONNET

SKILL_ID = "advocacy"
_RATE_LIMIT_DAYS = 90  # one per customer per quarter
_RISK_OVERRIDE = {
    "Risk – Talent Competency",
    "Risk - Talent Competency",
    "Risk - Resignation",
    "Risk - Customer Payment Failure",
    "Poor Experience with Edge",
    "Competitor",
}
_SYSTEM = (
    "You are EDGE Pulse drafting a warm advocacy outreach to a happy customer's "
    "champion. Open with their strongest VERBATIM positive quote. Be brief and "
    "genuine; never fabricate. Return ONLY JSON: "
    '{"email_draft": {"subject": "", "body": ""}}'
)
MODIFIABLE_FIELDS = ["body.email_draft.body", "body.proposed_motion"]


def _eligible(facts: dict) -> bool:
    strong = facts.get("advocacy_score", 0.0) >= 0.6 or bool(facts.get("positive_quotes"))
    blocked = bool(set(facts.get("active_risk_categories", [])) & _RISK_OVERRIDE)
    return strong and not blocked


@observe(name="skill_06_advocacy")
async def run(ctx: SkillContext) -> list[SuggestedAction]:
    if not ctx.customer_id or not _eligible(ctx.facts):
        return []
    if await recently_actioned(SKILL_ID, customer_id=ctx.customer_id, within_days=_RATE_LIMIT_DAYS):
        return []

    motion = "recognition" if ctx.facts.get("reference_declined_12mo") else "reference-call"
    quotes = ctx.facts.get("positive_quotes") or []
    prompt = f"Customer: {ctx.customer_id}\nProposed motion: {motion}\nPositive quotes: {quotes}"
    text = await client.complete(ANTHROPIC_SONNET, prompt, system=_SYSTEM)
    draft = client.parse_json(text)

    body = {
        "email_draft": draft.get("email_draft", {}),
        "sfdc_task": {
            "subject": f"Advocacy candidate: {ctx.customer_id}",
            "description": f"Proposed motion: {motion}. Positive signals present.",
        },
        "proposed_motion": motion,
    }
    action = SuggestedAction(
        skill_id=SKILL_ID,
        action_type="advocacy-touch",
        body=body,
        why_oneline=f"Advocacy candidate: {ctx.customer_id} ({motion})",
        urgency="low",
        why_detail=f"[skill: {SKILL_ID}] strong positive signals; motion={motion}.",
        modifiable_fields=MODIFIABLE_FIELDS,
        customer_id=ctx.customer_id,
    )
    await submit_action(ctx, action)
    return [action]
