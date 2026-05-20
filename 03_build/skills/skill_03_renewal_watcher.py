"""
SPEC-019 — Skill 03: renewal-watcher (Design 05 /
01_design/skills/03-renewal-watcher.md).

Schedule-driven (daily heartbeat). For a Customer with a renewal in the
tier-aware window (SMB 60d / Mid 90d / Enterprise 120d), scores composite renewal
risk from the assembled signal facts; if risk >= medium, drafts a renewal-touch
(customer-facing check-in email + RM-facing Salesforce Task) via Sonnet, captures
inline-tag reasoning, emits the action, and routes through policy.

Composite-risk scoring (the Behavior table) is a pure function — golden-trace
tested. The signal evaluations that populate ctx.facts are the heartbeat's job
(upstream), keeping this skill deterministic + unit-testable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langfuse import observe

from core.agent.context import SkillContext, SuggestedAction, submit_action
from core.llm import client
from core.llm.config import ANTHROPIC_SONNET

SKILL_ID = "renewal-watcher"
_PROMPT_DIR = Path(__file__).parent / "prompts"
_LOOKAHEAD_DAYS = {"SMB": 60, "Mid-Market": 90, "Enterprise": 120}
_MAX_LOOKAHEAD = 120  # renewal-window guard: never fire beyond this
MODIFIABLE_FIELDS = [
    "body.email_draft.body",
    "body.email_draft.subject",
    "body.sfdc_task.description",
    "body.sfdc_task.due_date",
]


def score_renewal_risk(facts: dict[str, Any]) -> tuple[str, dict]:
    """Composite renewal risk (Skill 03 Behavior table). Returns (level, factors).

    high factors: ≥3 churn signals / ≥1 open risk Case / ≥30% replacement rate /
    Churn_Probability__c ≥ 0.5. medium: negative sentiment trajectory / RM silent
    60d. mitigating: a positive expansion signal downgrades one level.
    """
    high: list[str] = []
    med: list[str] = []
    if facts.get("churn_signal_count_90d", 0) >= 3:
        high.append("churn_signals>=3")
    if facts.get("open_risk_cases", 0) >= 1:
        high.append("open_risk_case")
    if facts.get("replacement_rate", 0.0) >= 0.30:
        high.append("replacement_rate>=30%")
    if facts.get("churn_probability", 0.0) >= 0.5:
        high.append("churn_probability>=0.5")
    if facts.get("negative_sentiment_trajectory", False):
        med.append("negative_sentiment")
    if facts.get("no_rm_outreach_60d", False):
        med.append("rm_silent_60d")
    mitigating = bool(facts.get("positive_expansion_signal", False))

    if high:
        level = "medium" if (mitigating and len(high) == 1 and not med) else "high"
    elif med:
        level = "low" if mitigating else "medium"
    else:
        level = "low"
    return level, {"high": high, "medium": med, "mitigating": mitigating}


def _reasoning(ctx: SkillContext, level: str, factors: dict, renewal_days: int) -> str:
    cited = factors["high"] + factors["medium"]
    lines = "\n".join(f"  - <bad>{c}</bad>" for c in cited) or "  - (no acute factors)"
    mit = (
        "\n  - <good>positive expansion signal (mitigating)</good>" if factors["mitigating"] else ""
    )
    return (
        f"[skill: {SKILL_ID}]\n"
        f"[context: Customer={ctx.customer_id}, renewal_in={renewal_days}d, tier={ctx.tier}]\n\n"
        "Signals consulted:\n"
        f"{lines}{mit}\n\n"
        f"Reasoning:\n  Composite renewal risk = <em>{level}</em> within the renewal window;\n"
        "  proposing a renewal-touch (check-in email + RM Task).\n\n"
        "Proposed action: renewal-touch card (email draft + Salesforce Task)."
    )


@observe(name="skill_03_renewal_watcher")
async def run(ctx: SkillContext) -> list[SuggestedAction]:
    """Evaluate one Customer's renewal risk; draft a renewal-touch if >= medium."""
    window = _LOOKAHEAD_DAYS.get(ctx.tier or "Mid-Market", 90)
    renewal_days = ctx.facts.get("renewal_days")
    if renewal_days is None or renewal_days > min(window, _MAX_LOOKAHEAD):
        return []  # renewal-window guard (no alert fatigue)

    level, factors = score_renewal_risk(ctx.facts)
    if level == "low":
        return []

    from core.memory.retrievers import get_customer_context

    bundle: dict[str, Any] = (
        dict(await get_customer_context(ctx.customer_id, graphiti=ctx.graphiti))
        if ctx.customer_id
        else {}
    )
    entity = (bundle.get("entity") or {}).get("name", ctx.customer_id or "the customer")
    prompt = (
        f"Customer: {entity}\nRenewal in: {renewal_days} days\nComposite risk: {level}\n"
        f"Risk factors: {factors['high'] + factors['medium']}\n"
        f"Mitigating: {factors['mitigating']}\n\n"
        "Draft the renewal-touch JSON. Remember: the email names no specific talent."
    )
    text = await client.complete(
        ANTHROPIC_SONNET, prompt, system=(_PROMPT_DIR / "skill_03_system.txt").read_text()
    )
    body = client.parse_json(text)

    action = SuggestedAction(
        skill_id=SKILL_ID,
        action_type="renewal-touch",
        body=body,
        why_oneline=f"Renewal at risk ({level}) for {entity} — {renewal_days}d out",
        urgency=level,
        why_detail=_reasoning(ctx, level, factors, renewal_days),
        modifiable_fields=MODIFIABLE_FIELDS,
        customer_id=ctx.customer_id,
    )
    await submit_action(ctx, action)
    return [action]
