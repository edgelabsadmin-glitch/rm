"""
Orchestrator: analyze one entity through the full pipeline and run the batch modes.

  pack → analyst (Sonnet) → validate → [Opus fallback] → snapshot + priority + actions

Heavy/IO collaborators (evidence pack, store, action submission, SkillContext) are
imported lazily so this module — and its mocked unit tests — stay light.
"""

from __future__ import annotations

import asyncio
import hashlib
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
_BACKFILL_CONCURRENCY = 4


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


# ── run modes (incremental + backfill) ────────────────────────────────────────
#
# Scope is *active only*: accounts with active_talent>0 and talent in the Active
# stage. A run analyzes an entity only when its inputs changed since the last
# snapshot — `_data_version` hashes the relevant timestamps, compared against the
# `data_version` stored on the latest matrix row. That makes backfill resumable
# (re-running skips entities already at the current version) and the incremental
# loop cheap (it touches only what moved).


async def _active_entities() -> list[tuple[str, str]]:
    """(entity_type, entity_id) for every active account + active talent."""
    from psycopg.rows import dict_row

    from core.db import get_pool

    pool = await get_pool()
    out: list[tuple[str, str]] = []
    async with pool.connection() as conn:
        conn.row_factory = dict_row
        accs = await (
            await conn.execute(
                "SELECT account_id FROM pulse.sf_accounts "
                "WHERE COALESCE(active_talent, 0) > 0 ORDER BY account_id"
            )
        ).fetchall()
        out.extend(("account", r["account_id"]) for r in accs)
        tal = await (
            await conn.execute(
                "SELECT associate_id FROM pulse.sf_associates "
                "WHERE stage = 'Active' ORDER BY associate_id"
            )
        ).fetchall()
        out.extend(("talent", r["associate_id"]) for r in tal)
    return out


async def _data_version(entity_type: str, entity_id: str) -> str:
    """A stable hash of the entity's input freshness — changes iff its data moved."""
    from psycopg.rows import tuple_row

    from core.db import get_pool

    pool = await get_pool()
    async with pool.connection() as conn:
        # Pooled connections may carry a dict_row factory set by a prior caller
        # (build_*_pack / _active_entities); pin a tuple_row cursor so positional
        # access is correct regardless of the connection's ambient factory.
        cur = conn.cursor(row_factory=tuple_row)

        async def scalar(sql: str, params: list) -> Any:
            row = await (await cur.execute(sql, params)).fetchone()
            return row[0] if row else None

        if entity_type == "talent":
            parts = [
                await scalar(
                    "SELECT synced_at FROM pulse.sf_associates WHERE associate_id=%s",
                    [entity_id],
                ),
                await scalar(
                    "SELECT max(observed_at) FROM pulse.associate_stage_history "
                    "WHERE associate_id=%s",
                    [entity_id],
                ),
            ]
        else:
            parts = [
                await scalar(
                    "SELECT synced_at FROM pulse.sf_accounts WHERE account_id=%s",
                    [entity_id],
                ),
                await scalar(
                    "SELECT max(received_at) FROM pulse.inbox_emails WHERE account_id=%s",
                    [entity_id],
                ),
                await scalar(
                    "SELECT max(observed_at) FROM pulse.associate_stage_history "
                    "WHERE account_id=%s",
                    [entity_id],
                ),
            ]
    raw = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


async def _last_version(entity_type: str, entity_id: str) -> Any:
    from core.analysis import store

    return await store.last_data_version(entity_type, entity_id)


async def _status_set(**fields: Any) -> None:
    from core.analysis import store

    await store.set_status(**fields)


async def _analyze_if_changed(entity_type: str, entity_id: str) -> bool:
    """Analyze one entity iff its data_version moved. Returns True if analyzed."""
    version = await _data_version(entity_type, entity_id)
    if version == await _last_version(entity_type, entity_id):
        return False
    await analyze_entity(entity_type, entity_id, data_version=version)
    return True


async def run_incremental() -> dict:
    """Analyze only active entities whose inputs changed since their last snapshot."""
    entities = await _active_entities()
    analyzed = 0
    for entity_type, entity_id in entities:
        try:
            if await _analyze_if_changed(entity_type, entity_id):
                analyzed += 1
        except Exception as exc:  # noqa: BLE001 — isolate per-entity failures
            log.error("incremental analyze %s/%s failed: %s", entity_type, entity_id, exc)
    return {"scanned": len(entities), "analyzed": analyzed}


async def run_backfill() -> dict:
    """Analyze every active entity (resumable: skips those already at the current
    version), throttled by a concurrency cap, with progress in analysis_status."""
    from datetime import datetime, timezone

    utc = timezone.utc  # noqa: UP017 — datetime.UTC is 3.11+; keeps local 3.9 tests runnable
    entities = await _active_entities()
    total = len(entities)
    await _status_set(
        state="running",
        percent=0,
        phase="Analyzing entities",
        detail=f"0/{total}",
        started_at=datetime.now(utc),
        finished_at=None,
    )
    sem = asyncio.Semaphore(_BACKFILL_CONCURRENCY)
    done = 0
    analyzed = 0
    errors = 0
    lock = asyncio.Lock()

    async def worker(entity_type: str, entity_id: str) -> None:
        nonlocal done, analyzed, errors
        async with sem:
            try:
                if await _analyze_if_changed(entity_type, entity_id):
                    analyzed += 1
            except Exception as exc:  # noqa: BLE001 — isolate per-entity failures
                errors += 1
                log.error("backfill analyze %s/%s failed: %s", entity_type, entity_id, exc)
        async with lock:
            done += 1
            if done % 10 == 0 or done == total:
                await _status_set(
                    percent=round(done / total * 100) if total else 100, detail=f"{done}/{total}"
                )

    await asyncio.gather(*(worker(et, eid) for et, eid in entities))
    await _status_set(
        state="error" if errors else "done",
        percent=100,
        phase="Complete" if not errors else "Finished with errors",
        detail=f"{analyzed} analyzed, {errors} errors of {total}",
        finished_at=datetime.now(utc),
    )
    return {"total": total, "analyzed": analyzed, "errors": errors}
