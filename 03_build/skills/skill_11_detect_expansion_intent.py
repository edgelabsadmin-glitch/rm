"""
SPEC-028 — Skill 11: detect-expansion-intent-from-job-posting (Design 05 /
01_design/skills/11-detect-expansion-intent-from-job-posting.md).

Fires on a hot/warm opportunity-tracker job-posting match
(expansion_signal_job_posting_match_v1). Drafts a light, well-timed expansion
outreach to the customer referencing the public posting + the matched role.
`general` matches are suppressed (no outreach) by default. LLM-drafted.
"""

from __future__ import annotations

from langfuse import observe

from core.agent.context import SkillContext, SuggestedAction, recently_actioned, submit_action
from core.llm import client
from core.llm.config import ANTHROPIC_SONNET

SKILL_ID = "detect-expansion-intent-from-job-posting"
_FIRE_TIERS = {"hottest": "high", "warm": "medium"}
_RATE_LIMIT_DAYS = 30
_SYSTEM = (
    "You are EDGE Pulse drafting a light, well-timed expansion outreach to a "
    "client who has publicly posted a role EDGE could staff. Reference the public "
    "posting tactfully (not intrusively); offer to help. Brief and warm; invent "
    'nothing. Return ONLY JSON: {"email_draft": {"subject": "", "body": ""}}'
)
MODIFIABLE_FIELDS = ["body.email_draft.body", "body.email_draft.subject"]


@observe(name="skill_11_detect_expansion_intent")
async def run(ctx: SkillContext) -> list[SuggestedAction]:
    f = ctx.facts
    tier = (f.get("match_tier") or "").lower()
    urgency = _FIRE_TIERS.get(tier)
    if urgency is None:  # general / off-scope / none → suppressed
        return []
    if ctx.customer_id and await recently_actioned(
        SKILL_ID, customer_id=ctx.customer_id, within_days=_RATE_LIMIT_DAYS
    ):
        return []

    role = f.get("matched_role", "a role")
    posting = f.get("posting_title") or role
    prompt = f"Customer: {ctx.customer_id}\nPosted role: {posting}\nMatched EDGE role: {role}"
    text = await client.complete(ANTHROPIC_SONNET, prompt, system=_SYSTEM)
    draft = client.parse_json(text)

    body = {
        "email_draft": draft.get("email_draft", {}),
        "posting": {"title": posting, "matched_role": role, "tier": tier},
    }
    action = SuggestedAction(
        skill_id=SKILL_ID,
        action_type="expansion-intent-outreach",
        body=body,
        why_oneline=f"Expansion signal ({tier}): {posting} @ {ctx.customer_id}",
        urgency=urgency,
        why_detail=f"[skill: {SKILL_ID}] {tier} job-posting match for {role}.",
        modifiable_fields=MODIFIABLE_FIELDS,
        customer_id=ctx.customer_id,
    )
    await submit_action(ctx, action)
    return [action]
