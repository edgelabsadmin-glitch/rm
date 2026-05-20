"""
SPEC-029 — Per-Profile RM edit/override (Design 06 §"Edit semantics"). An RM edit
sets override_active and records the auto-gen baseline the RM edited from
(override_source_md) so a later regeneration can detect divergence.
"""

from __future__ import annotations

from typing import Any

from core.profiles.loader import get_profile, upsert_profile


async def edit_profile(
    profile_type: str, entity_id: str, new_md: str, editor_id: str | None = None
) -> dict[str, Any]:
    """Apply an RM edit: preserve it across regenerations until divergence."""
    current = await get_profile(profile_type, entity_id)
    # Baseline = the auto-gen content the RM is editing from. If already
    # overriding, keep the original baseline (don't reset it to the edited text).
    if current and current["override_active"]:
        baseline = current.get("override_source_md")
    elif current:
        baseline = current["content_md"]
    else:
        baseline = new_md  # editing a not-yet-generated profile

    digest = await upsert_profile(
        profile_type,
        entity_id,
        new_md,
        override_active=True,
        override_source_md=baseline,
    )

    from core.events import log

    await log.emit_profile_edited(profile_type, entity_id, editor_id)
    return {"content_hash": digest, "override_active": True}
