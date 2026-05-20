"""
SPEC-001 stub — agent reasoning entry point (ADR-001).

This is the central abstraction ADR-001 names: the API → runner → reasoning-call
sequence. It runs synchronously in-process for Phase 1 (Option A). The clean
boundary here is what makes the eventual Option-B (queue + worker) migration a
swap rather than a redesign.

Filled in by later specs (skills 018-028 route through here; ADR-003 wraps it
with Langfuse @observe). Day-1: stub raises NotImplementedError so nothing
silently no-ops (§6 rule 14).
"""

from __future__ import annotations


async def run_skill(skill_id: str, *args, cancellation_token=None, **kwargs):  # noqa: D401
    """Run a skill by id. Implemented per-skill in specs 018-028."""
    raise NotImplementedError(
        f"run_skill({skill_id!r}) not implemented yet — wired by the skill specs."
    )
