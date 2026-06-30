"""Pure priority score + color from fired signals (tier-weighted highest severity)."""

from __future__ import annotations

_SEV = {"high": 3, "medium": 2, "low": 1}
_TIER = {"Strategic": 1.5, "Growth": 1.2, "Core": 1.0}


def compute_priority(fired_signals: list[dict], *, tier: str | None) -> dict:
    tw = _TIER.get(tier or "Core", 1.0)
    score = max((_SEV.get(s.get("severity") or "", 0) for s in fired_signals), default=0) * tw
    if score >= 4:
        pri, color = "critical", "red"
    elif score >= 3:
        pri, color = "high", "orange"
    elif score >= 2:
        pri, color = "medium", "amber"
    elif score > 0:
        pri, color = "low", "blue"
    else:
        pri, color = "healthy", "green"
    return {"priority": pri, "color": color, "score": round(score, 3)}
