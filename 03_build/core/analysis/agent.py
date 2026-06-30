"""
Orchestrator: analyze one entity through the full pipeline and run the batch modes.

  pack → analyst (Sonnet) → validate → [Opus fallback] → snapshot + priority + actions

Heavy/IO collaborators (evidence pack, store, action submission, SkillContext) are
imported lazily so this module — and its mocked unit tests — stay light.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from core.analysis.analyst import run_analyst
from core.analysis.priority import compute_priority
from core.analysis.quant_signals import QUANT_SIGNALS
from core.analysis.signal_catalog import signal_defs_for
from core.analysis.validate import validate_matrix

log = logging.getLogger(__name__)

_ACTION_NS = uuid.UUID("00000000-0000-0000-0000-0000000000aa")


# ── patchable IO seams (wrappers keep heavy imports lazy + tests simple) ──────


async def _load_pack(entity_type: str, entity_id: str) -> dict | None:
    if entity_type == "talent":
        from core.analysis.evidence_pack import build_talent_pack

        return await build_talent_pack(entity_id)
    from core.analysis.evidence_pack import build_account_pack

    return await build_account_pack(entity_id)


async def save_snapshot(**kw: Any) -> None:
    from core.analysis import store

    await store.save_snapshot(**kw)


async def submit_action(ctx: Any, action: Any) -> Any:
    from core.agent.context import submit_action as _sa

    return await _sa(ctx, action)


def _build_ctx_action(pack: dict, sig: dict, narrative: str) -> tuple[Any, Any]:
    from core.agent.context import SkillContext, SuggestedAction

    et, eid = pack["entity_type"], pack["entity_id"]
    is_acct = et == "account"
    ctx = SkillContext(
        customer_id=eid if is_acct else None,
        talent_id=eid if not is_acct else None,
        rm_id=pack.get("rm_id"),
        tier=pack.get("tier"),
        trigger="scheduled",
    )
    action = SuggestedAction(
        skill_id="analysis_agent",
        action_type=f"signal:{sig['signal_id']}",
        body={"signal_id": sig["signal_id"], "severity": sig.get("severity")},
        why_oneline=f"{sig['signal_id']} ({sig.get('severity')})",
        urgency=sig.get("severity") or "medium",
        why_detail=narrative,
        customer_id=eid if is_acct else None,
        talent_id=eid if not is_acct else None,
        # Stable id per (entity, signal) → re-analysis dedups instead of duplicating.
        action_id=str(uuid.uuid5(_ACTION_NS, f"{eid}:{sig['signal_id']}")),
    )
    return ctx, action


async def _emit_actions(pack: dict, fired: list[dict], narrative: str) -> None:
    for sig in fired:
        if sig.get("severity") in ("high", "medium"):
            ctx, action = _build_ctx_action(pack, sig, narrative)
            await submit_action(ctx, action)


# ── the pipeline ──────────────────────────────────────────────────────────────


async def analyze_entity(
    entity_type: str, entity_id: str, *, data_version: str | None = None
) -> dict | None:
    pack = await _load_pack(entity_type, entity_id)
    if pack is None:
        return None
    facts = pack["facts"]
    quant = {sid: fn(facts) for sid, fn in QUANT_SIGNALS.items()}
    defs = signal_defs_for(entity_type)

    out, model = await run_analyst(pack, defs, model="sonnet")
    ok, cleaned, reasons = validate_matrix(out, pack, quant=quant)
    if not ok:
        log.warning("analysis %s/%s sonnet failed gate: %s", entity_type, entity_id, reasons)
        out, model = await run_analyst(pack, defs, model="opus")
        ok, cleaned, reasons = validate_matrix(out, pack, quant=quant)

    if not ok:
        await save_snapshot(
            entity_type=entity_type,
            entity_id=entity_id,
            priority="healthy",
            color="green",
            score=0,
            fired_signals=[],
            scores={},
            narrative="; ".join(reasons)[:1000],
            model_used=model,
            data_version=data_version,
            state="needs_review",
        )
        return {"state": "needs_review"}

    # Merge in quant signals the analyst omitted entirely (the math is authoritative).
    present = {s["signal_id"] for s in cleaned["signals"]}
    for sid, q in quant.items():
        if q.fired and sid not in present:
            cleaned["signals"].append(
                {
                    "signal_id": sid,
                    "fired": True,
                    "severity": q.severity,
                    "confidence": 1.0,
                    "evidence": [f"deterministic:{q.detail}"],
                }
            )

    fired = [s for s in cleaned["signals"] if s.get("fired")]
    pri = compute_priority(fired, tier=pack.get("tier"))
    await save_snapshot(
        entity_type=entity_type,
        entity_id=entity_id,
        priority=pri["priority"],
        color=pri["color"],
        score=pri["score"],
        fired_signals=fired,
        scores={},
        narrative=cleaned["narrative"],
        model_used=model,
        data_version=data_version,
        state="ok",
    )
    await _emit_actions(pack, fired, cleaned["narrative"])
    return {"state": "ok", "priority": pri["priority"], "fired": len(fired)}
