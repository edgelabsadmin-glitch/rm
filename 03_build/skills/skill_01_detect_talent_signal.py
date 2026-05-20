"""
SPEC-020 — Skill 01: detect-talent-signal (Design 05 /
01_design/skills/01-detect-talent-signal.md).

The upstream signal EXTRACTOR — the bridge between raw Episodes and the Signal
Definition Library. Runs (Haiku) on a newly-ingested text/json Episode that has a
candidate Customer/Talent, extracts structured tags (competitor mentions,
expansion mentions, talent-welfare signals, multi-axis sentiment vector, positive
quotes) with VERBATIM quotes, and maps them to the `facts` shape the signal
evaluators (spec 017) consume. Emits a reasoning-completed event. No SFDC writes.

Phase-1 note: extracted tags are returned as facts (consumed in-memory by signal
evaluators) rather than persisted as new Kuzu edges — was_in_sentiment_state is
not in the locked 10 edge types (spec 005); persisting tags as graph edges is a
v1.5+ candidate alongside was_in_stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any

from langfuse import observe

from core.llm import client
from core.llm.config import ANTHROPIC_HAIKU

SKILL_ID = "detect-talent-signal"
_PROMPT = Path(__file__).parent / "prompts" / "skill_01_extraction.txt"


@dataclass
class ExtractionResult:
    client_sentiment: str = "neutral"
    sentiment_vector: dict[str, float] = field(default_factory=dict)
    competitor_mentions: list[dict] = field(default_factory=list)
    expansion_signals: list[dict] = field(default_factory=list)
    talent_welfare: dict[str, dict] = field(default_factory=dict)
    positive_quotes: list[str] = field(default_factory=list)
    key_quote: str = ""
    topic: str = ""

    @property
    def fired(self) -> bool:
        return bool(
            self.competitor_mentions
            or self.expansion_signals
            or self.positive_quotes
            or any(v.get("fired") for v in self.talent_welfare.values())
        )

    def to_signal_facts(self) -> dict[str, Any]:
        """Map extracted tags into the facts the spec-017 evaluators read."""

        def welfare(key: str) -> dict:
            w = self.talent_welfare.get(key, {})
            return {
                "fired": bool(w.get("fired")),
                "severity": w.get("severity", "medium"),
                "evidence": [w["quote"]] if w.get("quote") else [],
            }

        exp = self.expansion_signals
        warmth = float(self.sentiment_vector.get("warmth", 0.0))
        frustration = float(self.sentiment_vector.get("frustration", 0.0))
        return {
            "competitor_mentions": [
                {
                    "competitor": m.get("competitor"),
                    "severity": m.get("severity", "low"),
                    "quote": m.get("quote", ""),
                }
                for m in self.competitor_mentions
            ],
            "expansion_mention": {
                "fired": bool(exp),
                "severity": (max((e.get("severity", "low") for e in exp), default="low")),
                "evidence": [e.get("quote", "") for e in exp if e.get("quote")],
            },
            "burnout": welfare("burnout"),
            "growth_concern": welfare("growth"),
            "pay_concern": welfare("pay"),
            "positive_quotes": list(self.positive_quotes),
            "advocacy_score": round(max(0.0, warmth - frustration), 3),
            # sentiment_now in 0-1 for churn_signal_sentiment_decline_v1
            "sentiment_now": round(max(0.0, min(1.0, 0.5 + (warmth - frustration) / 2)), 3),
        }


@observe(name="skill_01_detect_talent_signal")
async def run(
    content: str, *, subject: str = "", episode_id: str = "", customer_id: str | None = None
) -> ExtractionResult:
    """Extract signal tags from one Episode's content. Empty/scheduling-only
    inputs yield an empty (non-fired) result."""
    if not content.strip():
        return ExtractionResult(topic="no content")

    user = f"Subject: {subject}\n\nContent:\n{content}"
    t0 = perf_counter()
    text = await client.complete(ANTHROPIC_HAIKU, user, system=_PROMPT.read_text())
    latency_ms = int((perf_counter() - t0) * 1000)
    data = client.parse_json(text)

    result = ExtractionResult(
        client_sentiment=data.get("client_sentiment", "neutral"),
        sentiment_vector=data.get("sentiment_vector", {}) or {},
        competitor_mentions=data.get("competitor_mentions", []) or [],
        expansion_signals=data.get("expansion_signals", []) or [],
        talent_welfare=data.get("talent_welfare", {}) or {},
        positive_quotes=data.get("positive_quotes", []) or [],
        key_quote=data.get("key_quote", ""),
        topic=data.get("topic", ""),
    )

    from core.events import log

    summary = (
        f"extracted: topic={result.topic} sentiment={result.client_sentiment} fired={result.fired}"
    )
    await log.emit_reasoning_completed(
        model=ANTHROPIC_HAIKU,
        tokens_in=0,
        tokens_out=0,
        latency_ms=latency_ms,
        reasoning_summary=summary,
        skill_id=SKILL_ID,
        customer_id=customer_id,
        episode_id=episode_id or None,
    )
    return result
