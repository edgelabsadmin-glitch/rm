"""
Anti-hallucination gate. Validates an analyst matrix against the Evidence Pack
and the deterministic quant results before it can be persisted.

Returns (ok, cleaned, reasons). `cleaned` has demotions/overrides applied.
"""

from __future__ import annotations

from typing import Any

_CONF_FLOOR = 0.4
_VALID_SEV = {"low", "medium", "high"}


def validate_matrix(out: Any, pack: dict, *, quant: dict) -> tuple[bool, dict, list[str]]:
    reasons: list[str] = []
    if not isinstance(out, dict) or not isinstance(out.get("signals"), list):
        return False, {}, ["malformed: missing signals[]"]

    evidence_ids = pack.get("evidence_ids", set())
    cleaned_signals: list[dict] = []
    for s in out["signals"]:
        if not isinstance(s, dict) or "signal_id" not in s:
            return False, {}, ["malformed: signal entry"]
        sig = {
            "signal_id": s["signal_id"],
            "fired": bool(s.get("fired")),
            "severity": s.get("severity") if s.get("severity") in _VALID_SEV else None,
            "confidence": float(s.get("confidence", 0) or 0),
            "evidence": [e for e in (s.get("evidence") or []) if isinstance(e, str)],
        }
        # 1. evidence grounding (only matters for fired)
        if sig["fired"]:
            if not sig["evidence"]:
                sig["fired"] = False
                reasons.append(f"{sig['signal_id']}: no evidence -> demoted")
            else:
                bogus = [e for e in sig["evidence"] if e not in evidence_ids]
                if bogus:
                    return False, {}, [f"{sig['signal_id']}: fabricated evidence {bogus}"]
        # 2. confidence floor
        if sig["fired"] and sig["confidence"] < _CONF_FLOOR:
            sig["fired"] = False
            reasons.append(f"{sig['signal_id']}: confidence<{_CONF_FLOOR} -> demoted")
        # 3. math override for quantitative signals
        q = quant.get(sig["signal_id"])
        if q is not None:
            if q.fired != sig["fired"] or (q.fired and q.severity != sig["severity"]):
                reasons.append(
                    f"{sig['signal_id']}: math override "
                    f"(llm {sig['fired']}/{sig['severity']} -> {q.fired}/{q.severity})"
                )
            sig["fired"] = q.fired
            sig["severity"] = q.severity if q.fired else None
        cleaned_signals.append(sig)

    cleaned = {
        "signals": cleaned_signals,
        "narrative": str(out.get("narrative") or ""),
    }
    return True, cleaned, reasons
