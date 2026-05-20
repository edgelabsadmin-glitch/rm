"""
SPEC-018 — Skill 02: prepare-customer-meeting-brief (Design 05 /
01_design/skills/02-prepare-customer-meeting-brief.md).

Consumer-only skill: reads the full customer context (get_customer_context) +
any pre-evaluated signal state in ctx.facts, asks Sonnet to compose a
forward-looking, evidence-cited brief, captures inline-tag-voice reasoning,
emits an action-suggested event, and routes through the policy module. Brief
length is tier-aware (SMB ~400w / Mid ~700w / Enterprise ~1000w).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from langfuse import observe

from core.agent.context import SkillContext, SuggestedAction, submit_action
from core.llm import client
from core.llm.config import ANTHROPIC_SONNET

SKILL_ID = "prepare-customer-meeting-brief"
_PROMPT_DIR = Path(__file__).parent / "prompts"
_WORD_CAP = {"SMB": 400, "Mid-Market": 700, "Enterprise": 1000}
_URGENCY_DEFAULT = "medium"
MODIFIABLE_FIELDS = ["body.top_issues", "body.talking_points"]


def _system_prompt(tier: str | None) -> str:
    cap = _WORD_CAP.get(tier or "Mid-Market", 700)
    return (_PROMPT_DIR / "skill_02_system.txt").read_text().replace("{word_cap}", str(cap))


def _context_blob(bundle: dict) -> str:
    """Render the ContextBundle + signals into the user prompt evidence section."""
    parts: list[str] = []
    entity = bundle.get("entity") or {}
    parts.append(f"Customer: {entity.get('name', 'Unknown')}")
    facts = bundle.get("temporal_facts") or []
    if facts:
        parts.append("Temporal facts:")
        parts += [f"  - [{f.get('edge_type')}] {f.get('fact')}" for f in facts[:20]]
    rels = bundle.get("relationships") or []
    if rels:
        parts.append("Relationships (1-hop):")
        parts += [
            f"  - {r.get('edge_type')} → {r.get('other')}: {r.get('fact')}" for r in rels[:20]
        ]
    eps = bundle.get("recent_episodes") or []
    if eps:
        parts.append("Recent episodes (cite by name):")
        parts += [f"  - ({e.get('name')}) {e.get('content', '')[:400]}" for e in eps[:8]]
    return "\n".join(parts)


def _reasoning(bundle: dict, ctx: SkillContext, body: dict) -> str:
    """Inline-tag-voice reasoning capture (Design 04)."""
    entity = (bundle.get("entity") or {}).get("name", ctx.customer_id or "?")
    n_facts = len(bundle.get("temporal_facts") or [])
    n_eps = len(bundle.get("recent_episodes") or [])
    n_risk = len(body.get("at_risk_talent") or [])
    return (
        f"[skill: {SKILL_ID}]\n"
        f"[context: Customer={entity}, meeting_at={ctx.as_of or 'TBD'}, tier={ctx.tier}]\n\n"
        "Signals consulted:\n"
        f"  - <num>{n_facts}</num> temporal facts in context\n"
        f"  - <num>{n_eps}</num> recent episodes\n"
        f"  - <num>{n_risk}</num> at-risk talent flagged\n\n"
        "Reasoning:\n"
        "  Synthesized current health + outstanding issues + recent signals into a\n"
        "  forward-looking brief; every claim cites a source episode or SFDC record.\n\n"
        "Proposed action: brief delivered as an Action Queue card."
    )


def _build_action(ctx: SkillContext, bundle: dict, body: dict) -> SuggestedAction:
    source_episodes = [e.get("uuid", "") for e in (bundle.get("recent_episodes") or [])]
    return SuggestedAction(
        skill_id=SKILL_ID,
        action_type="meeting-brief",
        body=body,
        why_oneline=(body.get("headline") or "Meeting brief")[:200],
        urgency=_URGENCY_DEFAULT,
        why_detail=_reasoning(bundle, ctx, body),
        modifiable_fields=MODIFIABLE_FIELDS,
        source_episodes=[s for s in source_episodes if s],
        customer_id=ctx.customer_id,
    )


@observe(name="skill_02_prepare_customer_meeting_brief")
async def run(ctx: SkillContext) -> list[SuggestedAction]:
    """Compose a meeting brief, emit it, route through policy. Returns the action(s)."""
    from core.memory.retrievers import get_customer_context

    if not ctx.customer_id:
        return []  # unknown attendee (Q54) — no brief; caller emits the notification

    bundle = await get_customer_context(
        ctx.customer_id, as_of=ctx.as_of or datetime.now(UTC), graphiti=ctx.graphiti
    )
    user_prompt = "Evidence available:\n\n" + _context_blob(dict(bundle))
    if ctx.facts:
        user_prompt += "\n\nActive signals:\n" + json.dumps(ctx.facts, default=str)[:2000]

    text = await client.complete(ANTHROPIC_SONNET, user_prompt, system=_system_prompt(ctx.tier))
    body = client.parse_json(text)

    action = _build_action(ctx, dict(bundle), body)
    await submit_action(ctx, action)
    return [action]
