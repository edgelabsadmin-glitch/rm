"""
SPEC-030 — Dual-Sided account health (Design 07).

Composite = α·customer_side + β·talent_side, with tier-dependent α/β. A customer
can be "customer-side healthy but talent-side dying" (high replacement rate) —
single-axis health misses it; the dual rollup makes it visible. Scoring is a
weighted sum of normalized signals (pure, golden-trace tested); the per-signal
normalization is the Phase-1 default (tunable). compute() caches the result and
emits health-tier-changed on a debounced (>=24h) tier transition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from typing import Any

from langfuse.decorators import observe

# Tier-dependent composition weights (Design 07).
ALPHA_BETA = {
    "SMB": (0.6, 0.4),
    "Mid-Market": (0.5, 0.5),
    "Enterprise": (0.4, 0.6),
}
_W = {"high": 3.0, "medium": 2.0, "low": 1.0}
_TIER_DEBOUNCE = timedelta(hours=24)
_CUSTOMER_HEALTH_MAP = {
    "Healthy": 1.0,
    "Stable": 0.5,
    "Watch": -0.3,
    "At-Risk": -0.7,
    "Escalated": -1.0,
    "Churned": -1.0,
}


@dataclass
class AccountHealth:
    account_id: str
    tier: str
    composite_score: float
    customer_side_score: float
    talent_side_score: float
    top_contributors: list[dict] = field(default_factory=list)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _weighted(terms: list[tuple[str, float, float]]) -> tuple[float, list[dict]]:
    """terms = [(name, value[-1..1], weight)] → (score[-100..100], contributors)."""
    total_w = sum(w for _, _, w in terms) or 1.0
    score = _clamp(100 * sum(v * w for _, v, w in terms) / total_w, -100, 100)
    ranked = sorted(terms, key=lambda t: abs(t[1] * t[2]), reverse=True)
    contributors = [{"signal": n, "contribution": round(v * w, 2)} for n, v, w in ranked]
    return score, contributors


def _stale(days: float) -> float:
    """Touchpoint staleness penalty: 0 at <=30d, ramps to 1 by 90d."""
    return -_clamp((days - 30) / 60, 0, 1)


def _count(n: float) -> float:
    """Normalize a small count to [0,1] (saturates at 3)."""
    return _clamp(n / 3, 0, 1)


def score_customer_side(f: dict[str, Any]) -> tuple[float, list[dict]]:
    """Weighted sum over the customer-side signals PRESENT in `f` (absent signals
    don't penalize — missing data is neutral, not negative)."""
    terms: list[tuple[str, float, float]] = []
    add = terms.append
    if "churn_probability" in f:
        add(("churn_probability", -_clamp(f["churn_probability"], 0, 1), _W["high"]))
    if "expansion_probability" in f:
        add(("expansion_probability", _clamp(f["expansion_probability"], 0, 1), _W["medium"]))
    if "open_account_risk_cases" in f:
        add(("open_account_risk_cases", -_count(f["open_account_risk_cases"]), _W["high"]))
    if "churn_signal_count_60d" in f:
        add(("churn_signals_60d", -_count(f["churn_signal_count_60d"]), _W["medium"]))
    if "expansion_signal_count_60d" in f:
        add(("expansion_signals_60d", _count(f["expansion_signal_count_60d"]), _W["medium"]))
    if "days_since_touchpoint" in f:
        add(("touchpoint_staleness", _stale(f["days_since_touchpoint"]), _W["low"]))
    if f.get("customer_health") in _CUSTOMER_HEALTH_MAP:
        add(("customer_health", _CUSTOMER_HEALTH_MAP[f["customer_health"]], _W["high"]))
    if "sentiment_now" in f:
        add(("sentiment", 2 * _clamp(f["sentiment_now"], 0, 1) - 1, _W["medium"]))
    return _weighted(terms)


def score_talent_side(f: dict[str, Any]) -> tuple[float, list[dict]]:
    """Weighted sum over the talent-side signals PRESENT in `f`."""
    terms: list[tuple[str, float, float]] = []
    add = terms.append
    if "replacement_rate" in f:
        add(("replacement_rate", -_clamp(f["replacement_rate"], 0, 1), _W["high"]))
    if "open_talent_risk_cases" in f:
        add(("open_talent_risk_cases", -_count(f["open_talent_risk_cases"]), _W["high"]))
    if "avg_welfare_severity" in f:
        add(("avg_welfare_severity", -_clamp(f["avg_welfare_severity"], 0, 1), _W["medium"]))
    if "cadence_overdue" in f:
        add(("cadence_overdue", -(1.0 if f["cadence_overdue"] else 0.0), _W["medium"]))
    if "recognition_count" in f:
        add(("recognitions", _count(f["recognition_count"]), _W["low"]))
    if "days_since_talent_touchpoint" in f:
        add(("talent_touchpoint_staleness", _stale(f["days_since_talent_touchpoint"]), _W["low"]))
    return _weighted(terms)


def tier_for(composite: float) -> str:
    if composite >= 40:
        return "Healthy"
    if composite >= 10:
        return "Stable"
    if composite >= -10:
        return "Watch"
    if composite >= -40:
        return "At-Risk"
    return "Escalated"


def evaluate(account_id: str, tier_class: str | None, facts: dict[str, Any]) -> AccountHealth:
    """Pure composite-health computation (Design 07 §"composition formula")."""
    alpha, beta = ALPHA_BETA.get(tier_class or "Mid-Market", (0.5, 0.5))
    cust, cust_contrib = score_customer_side(facts)
    tal, tal_contrib = score_talent_side(facts)
    composite = round(alpha * cust + beta * tal, 2)
    top = sorted(cust_contrib + tal_contrib, key=lambda c: abs(c["contribution"]), reverse=True)[:3]
    return AccountHealth(
        account_id, tier_for(composite), composite, round(cust, 2), round(tal, 2), top
    )


@observe(name="health_compute")
async def compute(
    account_id: str, *, tier_class: str | None = None, facts: dict[str, Any] | None = None
) -> AccountHealth:
    """Compute, cache, and (on a debounced tier change) emit health-tier-changed."""
    health = evaluate(account_id, tier_class, facts or {})

    from core.db import get_pool

    pool = await get_pool()
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT tier, tier_changed_at FROM pulse.account_health WHERE account_id = %s;",
                (account_id,),
            )
            row = await cur.fetchone()
    prior_tier = row[0] if row else None
    prior_change_at = row[1] if row else None

    now = datetime.now(UTC)
    first_time = prior_tier is None
    tier_changed = (not first_time) and prior_tier != health.tier
    # A flip is only accepted (and emitted) when >= 24h since the last change,
    # so transient oscillation doesn't take effect (Design 07 / Q88).
    debounced = tier_changed and (
        prior_change_at is None or (now - prior_change_at) >= _TIER_DEBOUNCE
    )

    if first_time or not tier_changed or debounced:
        effective_tier = health.tier
        new_change_at = now if (first_time or debounced) else prior_change_at
    else:
        effective_tier = prior_tier  # suppress the flip within the debounce window
        new_change_at = prior_change_at
    emit = first_time or debounced
    health.tier = effective_tier  # authoritative (debounced) tier

    from psycopg.types.json import Jsonb

    pool = await get_pool()
    async with pool.connection() as conn:
        await conn.execute(
            "INSERT INTO pulse.account_health "
            "(account_id, tier, composite_score, customer_side_score, talent_side_score, "
            " top_contributors, computed_at, tier_changed_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s) "
            "ON CONFLICT (account_id) DO UPDATE SET "
            "tier = EXCLUDED.tier, composite_score = EXCLUDED.composite_score, "
            "customer_side_score = EXCLUDED.customer_side_score, "
            "talent_side_score = EXCLUDED.talent_side_score, "
            "top_contributors = EXCLUDED.top_contributors, computed_at = NOW(), "
            "tier_changed_at = EXCLUDED.tier_changed_at;",
            (
                account_id,
                health.tier,
                health.composite_score,
                health.customer_side_score,
                health.talent_side_score,
                Jsonb(health.top_contributors),
                new_change_at,
            ),
        )

    if emit:
        from core.events import log

        await log.emit_health_tier_changed(
            prior_tier, health.tier, health.composite_score, customer_id=account_id
        )
    return health
