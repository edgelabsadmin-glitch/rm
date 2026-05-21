"""
SPEC-029 — Per-Profile regeneration (Design 06). Builds a fresh Markdown profile
from the graph context (Opus, premium synthesis) and merges it with any RM
override. Override semantics: a fresh auto-gen that has DIVERGED from the
baseline the RM edited (override_source_md) is held back and a re-merge action
surfaces; otherwise the RM's edit is preserved silently.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from langfuse.decorators import observe

from core.llm import client
from core.llm.config import ANTHROPIC_OPUS
from core.profiles.loader import get_profile, upsert_profile

_EPISODE_THRESHOLD = 5
_DAYS_THRESHOLD = 7
_DIVERGENCE_THRESHOLD = 0.85  # fresh vs baseline similarity below this = diverged

_SYSTEM = {
    "customer": "Write a concise Customer profile (500-1500 words) in Markdown from the evidence: "
    "current shape, open threads, stakeholders, risks, opportunities. Cite nothing you can't see.",
    "talent": "Write a concise Associate (talent) profile (300-800 words) in Markdown: role, "
    "placement context, recent welfare/sentiment, risks. Evidence only.",
    "rm": "Write a brief RM profile (200-500 words) in Markdown: book shape, active priorities. "
    "Evidence only.",
}


def should_regenerate(
    new_episode_count: int, had_high_urgency: bool, days_since_regen: int
) -> bool:
    """Regenerate on >=5 new episodes, a high-urgency event, or weekly fallback."""
    return (
        new_episode_count >= _EPISODE_THRESHOLD
        or had_high_urgency
        or days_since_regen >= _DAYS_THRESHOLD
    )


def diverged(fresh_md: str, baseline_md: str, threshold: float = _DIVERGENCE_THRESHOLD) -> bool:
    if not baseline_md:
        return bool(fresh_md)
    return SequenceMatcher(None, fresh_md, baseline_md).ratio() < threshold


def resolve_regeneration(
    override_active: bool,
    override_source_md: str | None,
    fresh_md: str,
    current_md: str,
    threshold: float = _DIVERGENCE_THRESHOLD,
) -> dict[str, Any]:
    """Pure merge decision (golden-trace tested)."""
    if not override_active:
        return {"content_md": fresh_md, "override_source_md": None, "remerge_needed": False}
    if diverged(fresh_md, override_source_md or "", threshold):
        # data moved materially since the RM's edit — keep the edit, flag a re-merge
        return {
            "content_md": current_md,
            "override_source_md": override_source_md,
            "remerge_needed": True,
            "pending_md": fresh_md,
        }
    return {
        "content_md": current_md,
        "override_source_md": override_source_md,
        "remerge_needed": False,
    }


def _context_blob(bundle: dict) -> str:
    parts = [f"Entity: {(bundle.get('entity') or {}).get('name', '?')}"]
    for f in (bundle.get("temporal_facts") or [])[:25]:
        parts.append(f"- [{f.get('edge_type')}] {f.get('fact')}")
    for e in (bundle.get("recent_episodes") or [])[:8]:
        parts.append(f"- ({e.get('name')}) {e.get('content', '')[:300]}")
    return "\n".join(parts)


async def _bundle_for(profile_type: str, entity_id: str, graphiti) -> dict:
    from core.memory import retrievers

    fn = {
        "customer": retrievers.get_customer_context,
        "talent": retrievers.get_talent_context,
        "rm": retrievers.get_rm_context,
    }[profile_type]
    return dict(await fn(entity_id, graphiti=graphiti))


@observe(name="profile_regenerate")
async def regenerate(profile_type: str, entity_id: str, *, graphiti=None) -> dict[str, Any]:
    """Regenerate (or first-generate) a profile, honoring any RM override."""
    bundle = await _bundle_for(profile_type, entity_id, graphiti)
    fresh_md = await client.complete(
        ANTHROPIC_OPUS,
        "Evidence:\n\n" + _context_blob(bundle),
        system=_SYSTEM.get(profile_type, _SYSTEM["customer"]),
    )

    current = await get_profile(profile_type, entity_id)
    if current is None:
        merged = {"content_md": fresh_md, "override_source_md": None, "remerge_needed": False}
        override_active = False
    else:
        merged = resolve_regeneration(
            current["override_active"],
            current.get("override_source_md"),
            fresh_md,
            current["content_md"],
        )
        override_active = current["override_active"]

    digest = await upsert_profile(
        profile_type,
        entity_id,
        merged["content_md"],
        override_active=override_active,
        override_source_md=merged["override_source_md"],
    )

    from core.events import log

    await log.emit_profile_regenerated(
        profile_type, entity_id, digest, remerge_needed=merged["remerge_needed"]
    )
    if merged["remerge_needed"]:
        await _surface_remerge(profile_type, entity_id, merged.get("pending_md", ""))
    return {"content_hash": digest, **merged}


async def _surface_remerge(profile_type: str, entity_id: str, pending_md: str) -> None:
    """Surface a 'profile re-merge needed' Action Queue card (Design 06)."""
    from core.agent.context import SkillContext, SuggestedAction, submit_action

    customer_id = entity_id if profile_type == "customer" else None
    talent_id = entity_id if profile_type == "talent" else None
    ctx = SkillContext(customer_id=customer_id, talent_id=talent_id)
    await submit_action(
        ctx,
        SuggestedAction(
            skill_id="profile-regenerator",
            action_type="profile-remerge",
            body={"profile_type": profile_type, "entity_id": entity_id, "pending_md": pending_md},
            why_oneline=f"Profile re-merge needed: {profile_type} {entity_id}",
            urgency="low",
            modifiable_fields=["body.pending_md"],
            customer_id=customer_id,
            talent_id=talent_id,
        ),
    )
