"""
SPEC-017 — Signal Definition Library: shared types.

Each `core/signals/<signal_id>.py` module exports a `META` (must align with its
`02_planning/signals/<signal_id>.md` definition — CI enforces) and an async
`evaluate(ctx) -> SignalResult | None`. This is the §6-rule-8 answer: the
markdown is inspectable English, the module is the executable code, and they are
kept in lock-step.

Evaluators are pure w.r.t. I/O: they read pre-assembled `ctx.facts` (the owning
skill gathers these via the named retrievers / event log) and apply the
definition's documented threshold. LLM-based signals consume the extraction that
Skill 01 already performed (provided in `ctx.facts`), so the evaluator validates
and tiers it rather than calling the LLM itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

SignalCategory = Literal[
    "churn", "expansion", "talent-care", "escalation", "recognition", "account-context"
]
SeverityModel = Literal["binary", "tiered", "scored"]
DetectionType = Literal["rule-based", "llm-based", "hybrid"]
Severity = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class SignalMeta:
    signal_id: str
    category: SignalCategory
    severity_model: SeverityModel
    owning_skills: frozenset[int]
    detection_type: DetectionType


@dataclass
class EvaluationContext:
    """Inputs a signal evaluates against. `facts` is assembled by the owning
    skill from the retrievers / event log; `tier` drives tier-aware thresholds."""

    customer_id: str | None = None
    talent_id: str | None = None
    tier: str | None = None  # "SMB" | "Mid-Market" | "Enterprise"
    as_of: datetime | None = None
    facts: dict[str, Any] = field(default_factory=dict)


@dataclass
class SignalResult:
    signal_id: str
    fired: bool
    severity: str | None = None  # tiered: low/medium/high; scored: stringified 0-1
    score: float | None = None
    evidence: list[str] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)


def fire(
    meta: SignalMeta,
    severity: str | None = None,
    *,
    score: float | None = None,
    evidence: list[str] | None = None,
    **detail: Any,
) -> SignalResult:
    return SignalResult(
        signal_id=meta.signal_id,
        fired=True,
        severity=severity,
        score=score,
        evidence=evidence or [],
        detail=detail,
    )


def no_fire(meta: SignalMeta, **detail: Any) -> SignalResult:
    return SignalResult(signal_id=meta.signal_id, fired=False, detail=detail)


def extraction_signal(meta: SignalMeta, ext: dict[str, Any] | None) -> SignalResult:
    """Normalize a Skill-01 extraction ({fired, severity, evidence}) into a result.

    Used by LLM-based signals: Skill 01 extracts the tag during ingestion, the
    signal module tiers/validates it (the markdown says "Skill 01 emits the tag;
    this signal aggregates")."""
    ext = ext or {}
    if not ext.get("fired"):
        return no_fire(meta)
    return fire(meta, ext.get("severity", "medium"), evidence=list(ext.get("evidence", [])))
