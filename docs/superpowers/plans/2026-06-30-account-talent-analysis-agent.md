# Account & Talent Analysis Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An agent that re-analyzes every active account + active talent after data refreshes, produces an LLM-generated signal matrix (29 signals) grounded in deterministic evidence, snapshots it dated, fires RM actions, and assigns a tier-weighted priority color — with hard anti-hallucination (evidence grounding + math override + Sonnet→Opus fallback).

**Architecture:** A deterministic **Evidence Pack** per entity → **LLM analyst** (Sonnet, Opus fallback) emits a structured matrix → a **validation gate** rejects hallucinations (fabricated evidence, math mismatch) → dated **snapshot** to `pulse.entity_matrices` → fired signals become **Action Queue** items + a **priority color**. Backfill (one-time, throttled, resumable) + incremental (changed-only) run modes.

**Tech Stack:** Python 3.12 / FastAPI / psycopg3 / Aurora Postgres; Anthropic (Sonnet `claude-sonnet-4-6`, Opus `claude-opus-4-7`) via tool-forced structured output; React 18 / Vite / TS / TanStack Query.

**Spec:** `docs/superpowers/specs/2026-06-30-account-talent-analysis-agent-design.md`

**Working dir:** all paths relative to `03_build/`. Build on a branch; **do not deploy**.

**Test conventions:** pure unit tests in `tests/` must not need DB/network (the `db`/`integration` markers are excluded by default in CI). Mock Anthropic; for DB-touching logic, keep the *pure* core in separate functions and unit-test those. Run: `python3 -m pytest tests/test_analysis_*.py -q`. Ruff: `python3 -m ruff check . && python3 -m ruff format --check .`. Frontend: `cd front && node_modules/.bin/tsc -b && node_modules/.bin/vite build`.

**Reuse (verified):**
- Signals: `core/signals/runtime.py` `evaluate(signal_id, ctx)`; `core/signals/base.py` `EvaluationContext(customer_id, talent_id, tier, as_of, facts)`, `SignalResult(signal_id, fired, severity, score, evidence, detail)`.
- Health: `core/health/dual_sided.py` `evaluate(account_id, tier_class, facts) -> AccountHealth` (pure) and async `compute(...)`.
- Actions: `core/agent/context.py` `SuggestedAction(skill_id, action_type, body, why_oneline, urgency, why_detail, source_episodes, customer_id, talent_id)` + `submit_action(ctx, action)`; `SkillContext(customer_id, talent_id, rm_id, tier, trigger, facts)`.
- LLM: `core/llm/config.py` `ANTHROPIC_SONNET`, `ANTHROPIC_OPUS`, `load_env()`. Anthropic client pattern as in `core/inbox/reply.py` (`anthropic.Anthropic(api_key=...).messages.create(...)` off-thread via `asyncio.to_thread`).
- Status pattern: `core/sync_runner.py` + `pulse.sync_status` (single-row progress); mirror for `analysis_status`.
- Schema bootstrap: `api/main.py` `_ensure_schema()`. Background loops: `api/main.py` lifespan.
- Accounts API/UI: `api/accounts.py`, `front/src/lib/api.ts`, `front/src/features/account/`, `front/src/components/RiskBadge.tsx` (risk color tokens `risk-high-*`, amber, etc.).

---

## File structure

**Backend (create):**
- `core/analysis/__init__.py`
- `core/analysis/quant_signals.py` — pure deterministic computations for the new quantitative signals. *(heavily unit-tested)*
- `core/analysis/priority.py` — pure priority score + color. *(unit-tested)*
- `core/analysis/validate.py` — pure validation gate. *(unit-tested)*
- `core/analysis/evidence_pack.py` — assemble the per-entity Evidence Pack (DB IO + pure shaping).
- `core/analysis/analyst.py` — LLM analyst (Sonnet→Opus, tool-forced JSON).
- `core/analysis/store.py` — snapshot write + latest/history reads + analysis state.
- `core/analysis/agent.py` — orchestrator: `analyze_entity`, `run_incremental`, `run_backfill`.
- `core/analysis/loop.py` — background incremental loop.
- `api/analysis.py` — admin + read endpoints.
- Tests: `tests/test_analysis_quant.py`, `tests/test_analysis_priority.py`, `tests/test_analysis_validate.py`, `tests/test_analysis_analyst.py`, `tests/test_analysis_agent.py`, `tests/test_analysis_evidence.py`.

**Backend (modify):** `api/main.py` (schema, router, loop).

**Frontend (create):** `front/src/features/analysis/types.ts`, `hooks.ts`, `MatrixPanel.tsx`, `PriorityDot.tsx`.
**Frontend (modify):** `front/src/lib/api.ts`, the account list row, account detail.

**Signal definitions (create):** `02_planning/signals/<id>.md` for the 13 new signals.

---

## Phase 1 — Deterministic core (pure, exhaustively tested)

### Task 1: Schema — `entity_matrices` + `analysis_status`

**Files:** Modify `api/main.py` `_ensure_schema()` (before final `await conn.commit()`).

- [ ] **Step 1: Add tables**

In `_ensure_schema()` add:

```python
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.entity_matrices (
                id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                entity_type    TEXT        NOT NULL,
                entity_id      TEXT        NOT NULL,
                analyzed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
                priority       TEXT        NOT NULL,
                priority_color TEXT        NOT NULL,
                priority_score NUMERIC     NOT NULL DEFAULT 0,
                fired_signals  JSONB       NOT NULL DEFAULT '[]',
                scores         JSONB       NOT NULL DEFAULT '{}',
                narrative      TEXT,
                model_used     TEXT,
                data_version   TEXT,
                state          TEXT        NOT NULL DEFAULT 'ok',
                created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entity_matrices_latest "
            "ON pulse.entity_matrices (entity_type, entity_id, analyzed_at DESC);"
        )
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pulse.analysis_status (
                id           INT         PRIMARY KEY,
                state        TEXT        NOT NULL DEFAULT 'idle',
                percent      INT         NOT NULL DEFAULT 0,
                phase        TEXT,
                detail       TEXT,
                started_at   TIMESTAMPTZ,
                finished_at  TIMESTAMPTZ
            )
        """)
        await conn.execute(
            "INSERT INTO pulse.analysis_status (id, state) VALUES (1, 'idle') "
            "ON CONFLICT (id) DO NOTHING"
        )
```

- [ ] **Step 2: Verify import** — `python3 -c "import ast; ast.parse(open('api/main.py').read()); print('ok')"` → `ok`
- [ ] **Step 3: Commit** — `git add api/main.py && git commit -m "feat(analysis): entity_matrices + analysis_status schema"`

### Task 2: `quant_signals.py` — deterministic signal computations (pure, TDD)

These produce authoritative `{signal_id, fired, severity}` results the analyst is later checked against. Each takes a plain facts dict (assembled in Task 5) — pure, no IO.

**Files:** Create `core/analysis/__init__.py`, `core/analysis/quant_signals.py`; Test `tests/test_analysis_quant.py`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_analysis_quant.py
"""Deterministic quantitative signal computations — pure, no IO."""
from core.analysis.quant_signals import (
    ebr_overdue, attrition_velocity, response_time_degradation,
    ramp_stall, coverage_gap, single_threaded, inbound_volume_drop,
    QuantResult,
)

# EBR cadence (days) by tier; overdue if days_since_ebr exceeds it.
def test_ebr_overdue_recent_not_fired():
    assert ebr_overdue({"days_since_ebr": 20, "tier": "Strategic"}).fired is False

def test_ebr_overdue_just_past_low():
    r = ebr_overdue({"days_since_ebr": 100, "tier": "Strategic"})  # cadence 90
    assert r.fired and r.severity == "low"

def test_ebr_overdue_far_past_high():
    r = ebr_overdue({"days_since_ebr": 200, "tier": "Strategic"})
    assert r.fired and r.severity == "high"

def test_ebr_overdue_null_not_fired():
    assert ebr_overdue({"days_since_ebr": None, "tier": "Core"}).fired is False

def test_attrition_velocity_none():
    assert attrition_velocity({"departures_30d": 0, "active_talent": 10}).fired is False

def test_attrition_velocity_cluster_high():
    r = attrition_velocity({"departures_30d": 4, "active_talent": 8})  # 50% in 30d
    assert r.fired and r.severity == "high"

def test_attrition_velocity_backfilled_not_fired():
    # 2 left but 2 onboarding to replace → net stable, don't false-fire
    assert attrition_velocity({"departures_30d": 2, "active_talent": 10, "onboarding_30d": 2}).fired is False

def test_response_time_stable_not_fired():
    assert response_time_degradation({"reply_latency_now_h": 6, "reply_latency_prior_h": 5}).fired is False

def test_response_time_degraded_fired():
    r = response_time_degradation({"reply_latency_now_h": 72, "reply_latency_prior_h": 8})
    assert r.fired and r.severity in ("medium", "high")

def test_response_time_insufficient_history():
    assert response_time_degradation({"reply_latency_now_h": 50, "reply_latency_prior_h": None}).fired is False

def test_ramp_stall_fired():
    assert ramp_stall({"max_days_in_onboarding": 45}).fired is True

def test_ramp_stall_ok():
    assert ramp_stall({"max_days_in_onboarding": 7}).fired is False

def test_coverage_gap_fired():
    r = coverage_gap({"active_talent": 6, "talent_baseline": 10})  # -40%
    assert r.fired and r.severity == "high"

def test_coverage_gap_ok():
    assert coverage_gap({"active_talent": 10, "talent_baseline": 10}).fired is False

def test_single_threaded_fired():
    assert single_threaded({"distinct_engaged_contacts": 1}).fired is True

def test_single_threaded_ok():
    assert single_threaded({"distinct_engaged_contacts": 4}).fired is False

def test_inbound_drop_fired():
    r = inbound_volume_drop({"inbound_now_30d": 1, "inbound_prior_30d": 12})
    assert r.fired

def test_inbound_drop_insufficient():
    assert inbound_volume_drop({"inbound_now_30d": 1, "inbound_prior_30d": 2}).fired is False
```

- [ ] **Step 2: Run → fail** — `python3 -m pytest tests/test_analysis_quant.py -q` → ModuleNotFound.

- [ ] **Step 3: Implement**

```python
# core/analysis/__init__.py
"""Account & Talent analysis agent."""
```

```python
# core/analysis/quant_signals.py
"""
Deterministic, pure computations for the quantitative signals. No IO.

Each returns a QuantResult the analyst's claims are later validated against
(core/analysis/validate.py): if the LLM disagrees with these, the math wins.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QuantResult:
    signal_id: str
    fired: bool
    severity: str | None = None  # 'low'|'medium'|'high'
    detail: str = ""


_EBR_CADENCE = {"Strategic": 90, "Growth": 120, "Core": 180}


def ebr_overdue(f: dict) -> QuantResult:
    sid = "ebr_overdue_v1"
    days = f.get("days_since_ebr")
    cadence = _EBR_CADENCE.get(f.get("tier") or "Core", 180)
    if days is None or days <= cadence:
        return QuantResult(sid, False)
    over = days - cadence
    sev = "high" if over >= cadence else ("medium" if over >= cadence * 0.3 else "low")
    return QuantResult(sid, True, sev, f"{days}d since EBR vs {cadence}d cadence")


def attrition_velocity(f: dict) -> QuantResult:
    sid = "talent_attrition_velocity_v1"
    dep = f.get("departures_30d", 0) or 0
    base = f.get("active_talent", 0) or 0
    onb = f.get("onboarding_30d", 0) or 0
    net = dep - onb  # backfill nets out
    if base <= 0 or net <= 0:
        return QuantResult(sid, False)
    rate = net / base
    if rate < 0.15:
        return QuantResult(sid, False)
    sev = "high" if rate >= 0.4 else ("medium" if rate >= 0.25 else "low")
    return QuantResult(sid, True, sev, f"net {net} departures / {base} ({rate:.0%})")


def response_time_degradation(f: dict) -> QuantResult:
    sid = "response_time_degradation_v1"
    now = f.get("reply_latency_now_h")
    prior = f.get("reply_latency_prior_h")
    if now is None or prior is None or prior <= 0:
        return QuantResult(sid, False)
    ratio = now / prior
    if ratio < 2 or now < 24:
        return QuantResult(sid, False)
    sev = "high" if ratio >= 5 else "medium"
    return QuantResult(sid, True, sev, f"reply latency {prior:.0f}h→{now:.0f}h")


def ramp_stall(f: dict) -> QuantResult:
    sid = "ramp_stall_v1"
    d = f.get("max_days_in_onboarding")
    if d is None or d < 30:
        return QuantResult(sid, False)
    sev = "high" if d >= 60 else "medium"
    return QuantResult(sid, True, sev, f"{d}d in onboarding")


def coverage_gap(f: dict) -> QuantResult:
    sid = "coverage_gap_v1"
    cur = f.get("active_talent", 0) or 0
    base = f.get("talent_baseline", 0) or 0
    if base <= 0 or cur >= base:
        return QuantResult(sid, False)
    drop = (base - cur) / base
    if drop < 0.25:
        return QuantResult(sid, False)
    sev = "high" if drop >= 0.4 else "medium"
    return QuantResult(sid, True, sev, f"{cur} vs baseline {base} (-{drop:.0%})")


def single_threaded(f: dict) -> QuantResult:
    sid = "single_threaded_account_v1"
    n = f.get("distinct_engaged_contacts")
    if n is None or n > 1:
        return QuantResult(sid, False)
    return QuantResult(sid, True, "medium", "only 1 engaged contact")


def inbound_volume_drop(f: dict) -> QuantResult:
    sid = "inbound_volume_drop_v1"
    now = f.get("inbound_now_30d", 0) or 0
    prior = f.get("inbound_prior_30d", 0) or 0
    if prior < 4 or now >= prior * 0.4:
        return QuantResult(sid, False)
    sev = "high" if now == 0 else "medium"
    return QuantResult(sid, True, sev, f"inbound {prior}→{now} (30d)")


# Registry: signal_id → computation. Used by validate.py + agent.py.
QUANT_SIGNALS = {
    "ebr_overdue_v1": ebr_overdue,
    "talent_attrition_velocity_v1": attrition_velocity,
    "response_time_degradation_v1": response_time_degradation,
    "ramp_stall_v1": ramp_stall,
    "coverage_gap_v1": coverage_gap,
    "single_threaded_account_v1": single_threaded,
    "inbound_volume_drop_v1": inbound_volume_drop,
}
```

- [ ] **Step 4: Run → pass** — `python3 -m pytest tests/test_analysis_quant.py -q` → all pass.
- [ ] **Step 5: Commit** — `git add core/analysis/__init__.py core/analysis/quant_signals.py tests/test_analysis_quant.py && git commit -m "feat(analysis): deterministic quantitative signal computations"`

### Task 3: `priority.py` — priority score + color (pure, TDD)

**Files:** Create `core/analysis/priority.py`; Test `tests/test_analysis_priority.py`.

- [ ] **Step 1: Failing tests**

```python
# tests/test_analysis_priority.py
from core.analysis.priority import compute_priority

def test_no_fired_is_healthy():
    p = compute_priority([], tier="Strategic")
    assert p["priority"] == "healthy" and p["color"] == "green" and p["score"] == 0

def test_high_on_strategic_is_critical():
    p = compute_priority([{"signal_id":"x","severity":"high"}], tier="Strategic")
    assert p["priority"] == "critical" and p["color"] == "red"

def test_high_on_core_is_high():
    p = compute_priority([{"signal_id":"x","severity":"high"}], tier="Core")
    assert p["priority"] == "high" and p["color"] == "orange"

def test_max_signal_wins():
    p = compute_priority(
        [{"signal_id":"a","severity":"low"},{"signal_id":"b","severity":"high"}], tier="Growth")
    assert p["score"] == 3 * 1.2

def test_medium_core_is_medium():
    p = compute_priority([{"signal_id":"x","severity":"medium"}], tier="Core")
    assert p["priority"] == "medium" and p["color"] == "amber"
```

- [ ] **Step 2: Run → fail.**
- [ ] **Step 3: Implement**

```python
# core/analysis/priority.py
"""Pure priority score + color from fired signals (tier-weighted highest severity)."""
from __future__ import annotations

_SEV = {"high": 3, "medium": 2, "low": 1}
_TIER = {"Strategic": 1.5, "Growth": 1.2, "Core": 1.0}


def compute_priority(fired_signals: list[dict], *, tier: str | None) -> dict:
    tw = _TIER.get(tier or "Core", 1.0)
    score = max((_SEV.get(s.get("severity"), 0) for s in fired_signals), default=0) * tw
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
```

- [ ] **Step 4: Run → pass.**
- [ ] **Step 5: Commit** — `git commit -am "feat(analysis): tier-weighted priority + color"`

### Task 4: `validate.py` — the anti-hallucination gate (pure, TDD)

Validates one analyst result against the Evidence Pack + the deterministic quant results. Returns `(ok: bool, cleaned: dict, reasons: list[str])`.

**Files:** Create `core/analysis/validate.py`; Test `tests/test_analysis_validate.py`.

- [ ] **Step 1: Failing tests**

```python
# tests/test_analysis_validate.py
from core.analysis.validate import validate_matrix
from core.analysis.quant_signals import QuantResult

def _pack():
    return {"evidence_ids": {"ev1", "ev2"}}  # ids the pack legitimately contains

def test_fabricated_evidence_rejected():
    out = {"signals":[{"signal_id":"churn_x","fired":True,"severity":"high",
                       "confidence":0.9,"evidence":["ev_FAKE"]}], "priority":"high","narrative":"n"}
    ok, cleaned, reasons = validate_matrix(out, _pack(), quant={})
    assert not ok and any("evidence" in r for r in reasons)

def test_grounded_evidence_passes():
    out = {"signals":[{"signal_id":"churn_x","fired":True,"severity":"high",
                       "confidence":0.9,"evidence":["ev1"]}], "priority":"high","narrative":"n"}
    ok, cleaned, reasons = validate_matrix(out, _pack(), quant={})
    assert ok

def test_low_confidence_demoted():
    out = {"signals":[{"signal_id":"churn_x","fired":True,"severity":"high",
                       "confidence":0.2,"evidence":["ev1"]}], "priority":"high","narrative":"n"}
    ok, cleaned, reasons = validate_matrix(out, _pack(), quant={})
    assert ok and cleaned["signals"][0]["fired"] is False

def test_math_override_demotes_false_positive():
    # LLM fired ebr_overdue but the math says not overdue → override to not-fired
    out = {"signals":[{"signal_id":"ebr_overdue_v1","fired":True,"severity":"high",
                       "confidence":0.9,"evidence":["ev1"]}], "priority":"high","narrative":"n"}
    quant = {"ebr_overdue_v1": QuantResult("ebr_overdue_v1", False)}
    ok, cleaned, reasons = validate_matrix(out, _pack(), quant=quant)
    sig = next(s for s in cleaned["signals"] if s["signal_id"]=="ebr_overdue_v1")
    assert sig["fired"] is False and any("override" in r for r in reasons)

def test_math_override_corrects_severity():
    out = {"signals":[{"signal_id":"ebr_overdue_v1","fired":True,"severity":"low",
                       "confidence":0.9,"evidence":["ev1"]}], "priority":"low","narrative":"n"}
    quant = {"ebr_overdue_v1": QuantResult("ebr_overdue_v1", True, "high")}
    ok, cleaned, reasons = validate_matrix(out, _pack(), quant=quant)
    sig = next(s for s in cleaned["signals"] if s["signal_id"]=="ebr_overdue_v1")
    assert sig["fired"] is True and sig["severity"] == "high"

def test_malformed_rejected():
    ok, cleaned, reasons = validate_matrix({"bad":1}, _pack(), quant={})
    assert not ok
```

- [ ] **Step 2: Run → fail.**
- [ ] **Step 3: Implement**

```python
# core/analysis/validate.py
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
                reasons.append(f"{sig['signal_id']}: no evidence → demoted")
            else:
                bogus = [e for e in sig["evidence"] if e not in evidence_ids]
                if bogus:
                    return False, {}, [f"{sig['signal_id']}: fabricated evidence {bogus}"]
        # 2. confidence floor
        if sig["fired"] and sig["confidence"] < _CONF_FLOOR:
            sig["fired"] = False
            reasons.append(f"{sig['signal_id']}: confidence<{_CONF_FLOOR} → demoted")
        # 3. math override for quantitative signals
        q = quant.get(sig["signal_id"])
        if q is not None:
            if q.fired != sig["fired"] or (q.fired and q.severity != sig["severity"]):
                reasons.append(
                    f"{sig['signal_id']}: math override (llm fired={sig['fired']}/{sig['severity']}"
                    f" → {q.fired}/{q.severity})"
                )
            sig["fired"] = q.fired
            sig["severity"] = q.severity if q.fired else None
        cleaned_signals.append(sig)

    cleaned = {
        "signals": cleaned_signals,
        "narrative": str(out.get("narrative") or ""),
    }
    return True, cleaned, reasons
```

- [ ] **Step 4: Run → pass.**
- [ ] **Step 5: Commit** — `git commit -am "feat(analysis): anti-hallucination validation gate"`

---

## Phase 2 — Evidence pack, analyst, store

### Task 5: `evidence_pack.py` — per-entity deterministic pack

Assembles facts + curated snippets + pre-computed quant facts. DB IO; the pure *shaping* is tested with fake rows.

**Files:** Create `core/analysis/evidence_pack.py`; Test `tests/test_analysis_evidence.py`.

- [ ] **Step 1: Failing test (pure shaping)**

```python
# tests/test_analysis_evidence.py
from core.analysis.evidence_pack import shape_account_facts

def test_shape_account_facts_computes_quant_inputs():
    row = {"account_id":"A1","tier":"Strategic","active_talent":6,"churn_probability":0.7,
           "last_ebr":None,"rm_name":"R","owner_id":"O"}
    facts = shape_account_facts(row, days_since_ebr=200, talent_baseline=10,
                                departures_30d=3, onboarding_30d=0, max_days_in_onboarding=0,
                                reply_latency_now_h=80, reply_latency_prior_h=8,
                                inbound_now_30d=1, inbound_prior_30d=10,
                                distinct_engaged_contacts=1)
    assert facts["tier"] == "Strategic"
    assert facts["days_since_ebr"] == 200
    assert facts["coverage_gap_input"]["active_talent"] == 6
    # the pack exposes a stable set of evidence ids
    assert "evidence_ids" in facts and isinstance(facts["evidence_ids"], set)
```

- [ ] **Step 2: Run → fail.**
- [ ] **Step 3: Implement** — `shape_account_facts` (pure) builds the facts dict + `evidence_ids` (stable ids for every fact/snippet, e.g. `"fact:days_since_ebr"`, `"email:<id>"`). Add async `build_account_pack(account_id)` / `build_talent_pack(associate_id)` that query `sf_accounts`, `sf_associates`/`associate_stage_history`, `inbox_emails` (latency/volume), `episodes` (recent snippets), `events` (Skill-01 extraction tags), compute the derived inputs, and call the pure shaper. Each returns `{facts, evidence_ids, snippets, quant_inputs}`.

```python
# core/analysis/evidence_pack.py  (shape function shown; build_* do the queries)
from __future__ import annotations

def shape_account_facts(row: dict, **derived) -> dict:
    facts = {
        "account_id": row["account_id"],
        "tier": row.get("tier"),
        "active_talent": row.get("active_talent"),
        "churn_probability": row.get("churn_probability"),
        "days_since_ebr": derived.get("days_since_ebr"),
        "talent_baseline": derived.get("talent_baseline"),
        "departures_30d": derived.get("departures_30d"),
        "onboarding_30d": derived.get("onboarding_30d"),
        "max_days_in_onboarding": derived.get("max_days_in_onboarding"),
        "reply_latency_now_h": derived.get("reply_latency_now_h"),
        "reply_latency_prior_h": derived.get("reply_latency_prior_h"),
        "inbound_now_30d": derived.get("inbound_now_30d"),
        "inbound_prior_30d": derived.get("inbound_prior_30d"),
        "distinct_engaged_contacts": derived.get("distinct_engaged_contacts"),
    }
    # explicit per-signal input bundles (used by quant_signals + analyst prompt)
    facts["coverage_gap_input"] = {"active_talent": facts["active_talent"],
                                   "talent_baseline": facts["talent_baseline"]}
    ids = {f"fact:{k}" for k, v in facts.items() if not isinstance(v, dict) and v is not None}
    facts["evidence_ids"] = ids
    return facts
```

> `build_account_pack`/`build_talent_pack` are the DB layer — write them with `get_pool()` + `dict_row`, mirroring `core/inbox/sync.py` query style. Keep all derivations in helper functions so they stay unit-testable; the heavy SQL itself is covered by the integration smoke in Task 16.

- [ ] **Step 4: Run → pass.** **Step 5: Commit** — `git commit -am "feat(analysis): per-entity evidence pack (deterministic)"`

### Task 6: `analyst.py` — LLM analyst with Sonnet→Opus, tool-forced JSON

**Files:** Create `core/analysis/analyst.py`; Test `tests/test_analysis_analyst.py`.

- [ ] **Step 1: Failing tests (mocked Anthropic)**

```python
# tests/test_analysis_analyst.py
from core.analysis import analyst as A

def test_build_prompt_includes_facts_and_signal_defs():
    p = A.build_analyst_prompt({"tier":"Core","facts":{"x":1}}, ["sig_a: fires when X"])
    assert "sig_a" in p and "tier" in p.lower()

async def test_analyze_uses_sonnet_then_returns_parsed(monkeypatch):
    calls = []
    def fake_call(model, prompt):
        calls.append(model)
        return {"signals":[{"signal_id":"a","fired":False,"severity":None,
                            "confidence":0.9,"evidence":[]}], "narrative":"ok"}
    monkeypatch.setattr(A, "_call_tool", fake_call)
    out, model = await A.run_analyst("acc pack", ["a: x"])
    assert model == "sonnet" and out["narrative"] == "ok"
```

- [ ] **Step 2: Run → fail.**
- [ ] **Step 3: Implement** — `build_analyst_prompt(pack, signal_defs)`; `_call_tool(model, prompt)` does `anthropic.Anthropic(...).messages.create(model=..., tools=[MATRIX_TOOL], tool_choice={"type":"tool","name":"emit_matrix"}, ...)` and returns the tool `input` (forced JSON); `run_analyst(pack, signal_defs, *, model="sonnet")` calls Sonnet, returns `(out_dict, "sonnet")`. The Opus fallback is orchestrated in Task 8 (analyst exposes both via a `model` param so the agent can re-call with Opus). Use `ANTHROPIC_SONNET`/`ANTHROPIC_OPUS`; run the blocking call via `asyncio.to_thread` (pattern from `core/inbox/reply.py`).

```python
MATRIX_TOOL = {
  "name": "emit_matrix",
  "description": "Emit the per-entity signal matrix. Only fire a signal with cited evidence.",
  "input_schema": {
    "type": "object",
    "properties": {
      "signals": {"type":"array","items":{"type":"object","properties":{
        "signal_id":{"type":"string"},"fired":{"type":"boolean"},
        "severity":{"type":["string","null"],"enum":["low","medium","high",None]},
        "confidence":{"type":"number"},
        "evidence":{"type":"array","items":{"type":"string"}}},
        "required":["signal_id","fired","confidence","evidence"]}},
      "narrative":{"type":"string"}},
    "required":["signals","narrative"]}
}
```

- [ ] **Step 4: Run → pass.** **Step 5: Commit** — `git commit -am "feat(analysis): LLM analyst (tool-forced matrix, sonnet)"`

### Task 7: `store.py` — dated snapshots + reads

**Files:** Create `core/analysis/store.py`. (Covered by agent tests in Task 8; smoke in Task 16.)

- [ ] **Step 1: Implement** — `save_snapshot(entity_type, entity_id, priority, fired_signals, scores, narrative, model_used, data_version, state)` inserts one `entity_matrices` row; `latest(entity_type, entity_id)` returns newest; `history(entity_type, entity_id, limit)` returns the ordered series; `last_data_version(entity_type, entity_id)` reads the newest row's `data_version` (incremental skip key). Use `get_pool()` + `dict_row`.
- [ ] **Step 2: Verify import** — `python3 -c "import ast; ast.parse(open('core/analysis/store.py').read()); print('ok')"`.
- [ ] **Step 3: Commit** — `git commit -am "feat(analysis): matrix snapshot store + history"`

---

## Phase 3 — Orchestrator + run modes + API

### Task 8: `agent.py` — `analyze_entity` (full pipeline) + Opus fallback (TDD, mocked LLM)

**Files:** Create `core/analysis/agent.py`; Test `tests/test_analysis_agent.py`.

- [ ] **Step 1: Failing tests** — assert the pipeline: pack → analyst → validate → (Opus on failure) → snapshot + priority + actions. Mock `build_*_pack`, `run_analyst`, `save_snapshot`, `submit_action`.

```python
# tests/test_analysis_agent.py
from core.analysis import agent as G

async def test_sonnet_pass_saves_no_opus(monkeypatch):
    monkeypatch.setattr(G, "_load_pack", lambda et, eid: {"facts":{"tier":"Core"}, "evidence_ids":set(), "quant":{}})
    monkeypatch.setattr(G, "run_analyst", _fake_analyst(fail=False, model="sonnet"))
    saved = {}
    monkeypatch.setattr(G, "save_snapshot", lambda **k: saved.update(k))
    r = await G.analyze_entity("account", "A1")
    assert saved["model_used"] == "sonnet" and saved["state"] == "ok"

async def test_sonnet_fail_then_opus(monkeypatch):
    # first call (sonnet) returns fabricated evidence → gate fails → opus called → passes
    ...

async def test_both_fail_marks_needs_review(monkeypatch):
    ...
```

- [ ] **Step 2: Run → fail.**
- [ ] **Step 3: Implement** — `analyze_entity(entity_type, entity_id)`:
  1. `pack = await _load_pack(...)`; compute quant results from `pack["facts"]` via `QUANT_SIGNALS`.
  2. `out, model = await run_analyst(pack, defs, model="sonnet")`; `ok, cleaned, reasons = validate_matrix(out, pack, quant=quant)`.
  3. If not ok → re-run with Opus; validate again. If still not ok → `save_snapshot(..., state="needs_review", narrative=reasons)` and return.
  4. Merge quant-only-fired signals into `cleaned["signals"]` (quant signals the LLM omitted but math fired).
  5. `pri = compute_priority(fired, tier=...)`; `save_snapshot(...)`; for each fired high/medium → `submit_action(...)` (deduped against pending).
- [ ] **Step 4: Run → pass.** **Step 5: Commit** — `git commit -am "feat(analysis): analyze_entity pipeline + opus fallback"`

### Task 9: `run_incremental` + `run_backfill` (changed-only, resumable, throttled)

**Files:** Modify `core/analysis/agent.py`; Test add to `tests/test_analysis_agent.py`.

- [ ] **Step 1: Failing tests** — unchanged `data_version` → skipped (no analyze call); changed → analyzed; backfill resumes (already-analyzed skipped); active-scope filter excludes inactive accounts / non-Active talent; per-entity error isolated.
- [ ] **Step 2: Run → fail.**
- [ ] **Step 3: Implement** — `_active_entities()` yields active accounts (`active_talent>0`) + Active talent. `_data_version(entity)` = hash of inputs (max episode ts, inbox ts, stage changes, sf synced_at). `run_incremental()` analyzes only entities whose version changed since `last_data_version`; `run_backfill()` analyzes all active entities with concurrency cap (`asyncio.Semaphore(4)`) + progress via `analysis_status` (mirror `core/sync_runner.py`), skipping entities already at the current version (resumable).
- [ ] **Step 4: Run → pass.** **Step 5: Commit** — `git commit -am "feat(analysis): incremental + resumable throttled backfill"`

### Task 10: `api/analysis.py` + wiring

**Files:** Create `api/analysis.py`; create `core/analysis/loop.py`; Modify `api/main.py`.

- [ ] **Step 1: Implement endpoints** — `POST /admin/analysis/backfill` (admin-gated via `require_caller`+`is_admin`, fire-and-forget `run_backfill`, returns status), `GET /admin/analysis/status`, `GET /accounts/{id}/matrix` (latest), `GET /accounts/{id}/matrix/history`, `GET /talent/{id}/matrix`. `core/analysis/loop.py` `analysis_loop()` (waits ~300s post-startup, runs `run_incremental` every 1–2h + a daily full pass; env-gated `PULSE_ANALYSIS=0` to disable). Wire into `api/main.py` lifespan + register router.
- [ ] **Step 2: Verify** — `python3 -m ruff check api/analysis.py core/analysis/loop.py api/main.py` + ast parse.
- [ ] **Step 3: Commit** — `git commit -am "feat(analysis): admin/read API + incremental loop wiring"`

---

## Phase 4 — Talent path

### Task 11: talent evidence pack + signal routing
- [ ] Implement `build_talent_pack` (stage history, days-in-stage, welfare tags, talent emails) and the talent signal set (talent-care + attrition/ramp). `analyze_entity("talent", id)` already routes through the shared pipeline. Add talent tests mirroring the account ones. Commit.

---

## Phase 5 — Signal definitions (all 29 visible to the analyst)

### Task 12: author the 13 new signal definitions
- [ ] Create `02_planning/signals/<id>.md` for each new signal (the analyst is handed these definitions per entity type; the quantitative ones also have code in `quant_signals.py`). Include: category, severity model, detection type, entity types, fire criteria, evidence required. Build a `core/analysis/signal_catalog.py` that returns the applicable signal definitions (existing 16 META + 13 new) for a given entity_type, fed to `build_analyst_prompt`. Commit.

---

## Phase 6 — Frontend (priority color + matrix panel)

### Task 13: API client + types + hooks
- [ ] `front/src/lib/api.ts`: `getAccountMatrix`, `getAccountMatrixHistory`, `getTalentMatrix`, `startAnalysisBackfill`, `getAnalysisStatus`. `features/analysis/types.ts` (`MatrixDTO {entity_id, priority, priority_color, fired_signals[], narrative, analyzed_at}`), `hooks.ts` (`useAccountMatrix`, etc.). Verify `tsc -b`. Commit.

### Task 14: account-list priority color + matrix panel
- [ ] `features/analysis/PriorityDot.tsx` (maps color → token, red/orange/amber/blue/green). Add the dot to the account-list rows + make priority sortable. `MatrixPanel.tsx` on the account detail (fired signals + narrative + a priority-over-time sparkline from history). Verify `tsc -b && vite build`. Commit.

### Task 15: talent color
- [ ] Color talent nodes in the constellation drill-down + the account talent panel from the talent matrix. Verify build. Commit.

---

## Phase 7 — Verification

### Task 16: full verification (no deploy)
- [ ] `python3 -m pytest tests/test_analysis_*.py -q` (all pass) · `python3 -m ruff check . && python3 -m ruff format --check .` · `cd front && node_modules/.bin/tsc -b && node_modules/.bin/vite build`.
- [ ] Push the branch → confirm `pulse-ci` green (Python 3.12 pytest + pyright). **Do not merge / deploy.**
- [ ] Commit any fixes.

## Done criteria
- `analyze_entity` produces a validated, non-hallucinated matrix (evidence-grounded, math-overridden, Sonnet→Opus→needs_review) and snapshots it dated for accounts + talent.
- Backfill (throttled, resumable) + incremental (changed-only + daily) run modes work; admin endpoints drive/observe them.
- Fired High/Medium signals appear as RM actions; account list + talent show a tier-weighted priority color; account detail shows the matrix + history.
- All `tests/test_analysis_*` pass; ruff/pyright/tsc/vite green; branch CI green. Not deployed.
