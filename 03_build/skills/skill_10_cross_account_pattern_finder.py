"""
SPEC-027 — Skill 10: cross-account-pattern-finder (Design 05 /
01_design/skills/10-cross-account-pattern-finder.md).

Weekly. For a candidate theme, uses the cross-account retriever (spec 007) to
find customers connected to it; if at least `min_support` distinct customers
share the theme, surfaces a pattern card. The retriever enforces the
protected-class denylist (defense in depth). Includes the client_termination
pattern variant (Decision 36) by accepting that theme like any other.
"""

from __future__ import annotations

from langfuse import observe

from core.agent.context import SkillContext, SuggestedAction, submit_action

SKILL_ID = "cross-account-pattern-finder"
_DEFAULT_MIN_SUPPORT = 3
MODIFIABLE_FIELDS = ["body.headline"]


@observe(name="skill_10_cross_account_pattern_finder")
async def run(ctx: SkillContext) -> list[SuggestedAction]:
    theme = ctx.facts.get("theme")
    if not theme:
        return []
    min_support = ctx.facts.get("min_support", _DEFAULT_MIN_SUPPORT)

    from core.memory.retrievers import find_pattern_across_customers

    matches = await find_pattern_across_customers(
        theme, time_window_days=ctx.facts.get("time_window_days", 30), graphiti=ctx.graphiti
    )
    customers = sorted({m.customer_name for m in matches if m.customer_name})
    if len(customers) < min_support:
        return []  # not a pattern (Skill 10 makes this call, not the retriever)

    body = {
        "theme": theme,
        "headline": f"'{theme}' surfaced across {len(customers)} customers in the window.",
        "customers": customers,
        "match_count": len(matches),
        "examples": [{"customer": m.customer_name, "quote": m.quote[:200]} for m in matches[:5]],
    }
    action = SuggestedAction(
        skill_id=SKILL_ID,
        action_type="pattern-surface",
        body=body,
        why_oneline=f"Cross-account pattern: '{theme}' @ {len(customers)} customers",
        urgency="medium",
        why_detail=(
            f"[skill: {SKILL_ID}] theme=<em>{theme}</em> across "
            f"<num>{len(customers)}</num> customers (>= min_support {min_support})."
        ),
        modifiable_fields=MODIFIABLE_FIELDS,
    )
    await submit_action(ctx, action)
    return [action]
