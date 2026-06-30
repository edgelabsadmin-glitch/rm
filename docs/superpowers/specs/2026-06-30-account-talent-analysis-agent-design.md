# Account & Talent Analysis Agent — Design

**Date:** 2026-06-30 · **Status:** Draft for review

## Goal

After each data refresh, an agent re-analyzes every **active account** and every **active associate (talent)**, produces an **LLM-generated signal matrix** (which of the 29 signals fire, with severity + cited evidence), **snapshots it dated** for trend analysis, fires the fired signals as **RM actions**, and assigns each entity a **priority color** (red = highest). Robust against hallucination by construction.

## Scope

- **Accounts:** active only = `pulse.sf_accounts.active_talent > 0` (~601). (`status` is unpopulated, so `active_talent` is the active-customer definition.)
- **Talent:** Active-stage only = `pulse.sf_associates.stage = 'Active'` (~1,326).
- **Out of scope (v1):** churned/dormant accounts; non-active talent stages; the RM-facing "explain this matrix" chat (future).

## Architecture — one entity-agnostic pipeline, run for accounts *and* talent

```
Evidence Pack (deterministic)  →  LLM Analyst (Sonnet→Opus)  →  Validation gate  →  Snapshot (dated)  →  Actions + Color
```

Each stage is a focused, independently-testable unit. The same pipeline processes both entity types; the only differences are which evidence and which signals apply.

### Stage 1 — Evidence Pack (deterministic, no LLM) — the anti-hallucination foundation
A curated, labeled, timestamped fact sheet per entity. The LLM **only ever sees this** — never raw data. Built in code from durable sources:

**Account pack:** tier, segment, `active_talent` + 90-day baseline, `churn_probability`, `last_ebr` + days-since, `has_open_case` + open case count/severity (from cases), days-since-last-touchpoint, email response-latency trend + inbound-volume trend (from `inbox_emails` timestamps), associate attrition counts & velocity (from `associate_stage_history`), distinct engaged contacts count, plus **curated text snippets** (recent email subjects/snippets, meeting-summary excerpts, case categories) — each labeled with source + date, capped in count/length.

**Talent pack:** stage + stage history, days-in-current-stage, account it serves, welfare/burnout/pay/growth extraction tags (from Skill-01 episode extractions / event log), recent talent-side email snippets, recognition count.

**Pre-computed quantitative signals** (computed in code, included as hard facts so the LLM can't invent numbers): EBR overdue, attrition velocity, response-time degradation, inbound-volume drop, coverage gap, ramp stall, single-threaded account, case severity jump.

### Stage 2 — LLM Analyst (structured output)
Input: the Evidence Pack + the applicable signal definitions. Output: **forced-schema JSON** —
`{ signals: [{signal_id, fired, severity, confidence(0-1), evidence:[string]}], priority, narrative }`.
Prompt rules: fire a signal **only** if the pack contains supporting evidence; **cite** the exact evidence item(s); ambiguous/insufficient → `fired:false` with a reason; low temperature.

### Stage 3 — Validation gate (hard anti-hallucination)
Before anything is saved, every analyst result must pass:
1. **Schema valid** (StructuredOutput enforced).
2. **Evidence grounding** — each fired signal's `evidence[]` must reference items that **actually exist** in the pack (string/id match). Fabricated evidence → fail.
3. **Math agreement** — for quantitative signals, the analyst's `fired`/`severity` must match the deterministic pre-computation; on disagreement the **deterministic value wins** (override, logged).
4. **Confidence floor** — fired signals below a confidence threshold are demoted to not-fired.

### Stage 4 — Model strategy: Sonnet → Opus fallback
- **Primary:** Claude **Sonnet** (`ANTHROPIC_SONNET`).
- **Fallback:** if Sonnet's result **fails the validation gate** (schema/evidence/math) or returns low confidence, re-run that single entity with **Opus**.
- **If Opus also fails:** do **not** save a matrix; record the entity as `state='needs_review'` with the failure reason (no hallucination ever persists). Surfaced to admins, retried next cycle.

### Stage 5 — Snapshot (dated history)
Append a row to `pulse.entity_matrices` (below). Latest row per entity = current state; all rows = trend history.

### Stage 6 — Actions + Color
- Fired **High/Medium** signals → `submit_action()` → existing Action Queue (the analyst `narrative` becomes the action's `why_detail`; `evidence` → `source` lines). Deduped against the entity's currently-pending actions for the same signal.
- **Priority color** computed (below), stored on the snapshot, surfaced in the UI.

## Data model — `pulse.entity_matrices`

```sql
CREATE TABLE IF NOT EXISTS pulse.entity_matrices (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type    TEXT        NOT NULL,             -- 'account' | 'talent'
    entity_id      TEXT        NOT NULL,             -- account_id | associate_id
    analyzed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    priority       TEXT        NOT NULL,             -- 'critical'|'high'|'medium'|'low'|'healthy'
    priority_color TEXT        NOT NULL,             -- 'red'|'orange'|'amber'|'blue'|'green'
    priority_score NUMERIC     NOT NULL,             -- numeric for sorting
    fired_signals  JSONB       NOT NULL DEFAULT '[]',-- [{signal_id,severity,confidence,evidence[]}]
    scores         JSONB       NOT NULL DEFAULT '{}',-- composite/customer/talent health etc.
    narrative      TEXT,
    model_used     TEXT,                             -- 'sonnet'|'opus'
    data_version   TEXT,                             -- hash of inputs (incremental skip key)
    state          TEXT        NOT NULL DEFAULT 'ok',-- 'ok'|'needs_review'
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_entity_matrices_latest
    ON pulse.entity_matrices (entity_type, entity_id, analyzed_at DESC);
```

A small `pulse.entity_analysis_state (entity_type, entity_id, last_analyzed_at, data_version)` (or reuse the latest matrix row) drives incremental skipping.

## Signals (all 29)

- **16 existing** keep their deterministic evaluators (`core/signals/`); their results feed the Evidence Pack as facts.
- **13 new** (from the prioritization matrix): quantitative ones (EBR overdue, talent attrition velocity, response-time degradation, ramp stall, coverage gap, single-threaded account, inbound-volume drop, EBR no-show) computed deterministically; judgment ones (champion departure, new decision-maker, dual-sided divergence, talent silence, renewal+healthy upsell) LLM-assessed.
- **Routing:** account-category signals (churn/expansion/account-context/escalation) on accounts; talent-care signals on talent. Each signal definition declares which entity type(s) it applies to.

## Priority & color

`priority_score = max over fired signals of ( severity_weight × tier_weight )`
- severity_weight: high=3, medium=2, low=1; tier_weight: Strategic=1.5, Growth=1.2, Core=1.0 (talent uses its account's tier).
- Bands → color: ≥4 🔴 critical · 3–3.9 🟠 high · 2–2.9 🟡 medium · 1–1.9 🔵 low · 0 🟢 healthy.

## Run modes

**Backfill (one-time, on-demand, throttled, resumable):** analyze ALL active accounts + talent once. Triggered by an admin endpoint/button (not auto-run at deploy). Concurrency-capped (e.g. 3–5 parallel), rate-limited to respect Anthropic limits, progress tracked (reuse the `sync_status` pattern → `analysis_status`), and **resumable** (skips entities already analyzed at the current `data_version`). This is the "run it in parallel to seed signals" step.

**Incremental (steady-state loop):** a background loop (after syncs settle, e.g. every 1–2h) that analyzes only entities whose `data_version` changed since their last snapshot (new email/meeting/case/stage change), plus a **full daily pass** as a safety net. Bounds ongoing cost — most cycles touch only a handful of entities.

## RM surfacing & UI

- **Actions:** fired High/Medium signals appear in the existing Action Queue, scoped to the owning RM.
- **Account list:** a priority-color dot/bar per row (reuses risk color tokens); sortable by priority.
- **Talent:** color on talent nodes in the constellation drill-down and on the account's talent panel.
- **Account/talent detail:** the latest matrix (fired signals + narrative) shown; optional sparkline of `priority_score` over time from the dated history.

## Components (files)

- `core/analysis/evidence_pack.py` — build the deterministic pack per entity (+ quantitative signal pre-compute).
- `core/analysis/quant_signals.py` — pure deterministic computations for the quantitative signals (heavily unit-tested).
- `core/analysis/analyst.py` — LLM call (Sonnet→Opus), structured output, prompt.
- `core/analysis/validate.py` — the validation gate (schema/evidence/math/confidence).
- `core/analysis/priority.py` — priority_score + color (pure).
- `core/analysis/agent.py` — orchestrator: `analyze_entity()`, `run_backfill()`, `run_incremental()`.
- `core/analysis/store.py` — snapshot write + latest/ history reads + state.
- `api/analysis.py` — admin endpoints: `POST /admin/analysis/backfill`, `GET /admin/analysis/status`, `GET /accounts/{id}/matrix`, `GET /accounts/{id}/matrix/history`.
- `api/main.py` — schema + register router + start incremental loop.
- Frontend: matrix DTOs/hooks; priority color on account list + talent; matrix panel on detail.

## Error handling

- Per-entity isolation: one entity's failure never aborts the batch (logged, `needs_review`).
- Anthropic errors: retry with backoff; Sonnet→Opus on validation failure; persist nothing on double-failure.
- Backfill resumable across restarts via `data_version` skip.
- Rate-limit aware (concurrency cap + pacing).

## Test cases (must pass before deploy)

**Deterministic quant signals (`quant_signals.py`) — pure unit tests, exhaustive:**
- EBR overdue: recent EBR → not fired; just past cadence → low; far past → high; null `last_ebr` → handled (not fired / unknown), per tier cadence.
- Attrition velocity: no churn → not fired; cluster within window → fired with correct tier; backfill/replacement netting (don't false-fire on churn-and-backfill).
- Response-time degradation: stable latency → not fired; latency trending up beyond threshold → fired; insufficient history → not fired.
- Inbound-volume drop, coverage gap, ramp stall, single-threaded, EBR no-show, case severity jump: boundary + insufficient-data cases each.

**Validation gate (`validate.py`):**
- Fabricated evidence (cites an item not in pack) → rejected.
- Math mismatch (LLM fires EBR-overdue but `last_ebr` recent) → deterministic override, logged.
- Below-confidence fired signal → demoted to not-fired.
- Malformed/schema-invalid output → rejected → triggers fallback.

**Model fallback (`agent.py`, mocked LLM):**
- Sonnet passes → Opus not called, `model_used='sonnet'`.
- Sonnet fails gate → Opus called; Opus passes → saved `model_used='opus'`.
- Both fail → no snapshot saved; `state='needs_review'` recorded with reason.

**Priority/color (`priority.py`):** high-on-Strategic = critical/red; same on Core = high/orange; no fired = healthy/green; multiple fired → max wins.

**Pipeline / orchestrator (mocked LLM + test DB or fakes):**
- `analyze_entity` writes exactly one snapshot, dedups actions, emits the right action for High signals.
- Incremental: unchanged `data_version` → skipped (no LLM call); changed → re-analyzed.
- Backfill: resumable (already-analyzed entities skipped); progress reported; per-entity error isolation.
- Active-scope: inactive accounts / non-Active talent are excluded.

**Snapshot/history (`store.py`):** append-only; latest read returns newest; history returns ordered series.

**API (`api/analysis.py`):** admin-gated; backfill triggers; status reports; matrix + history endpoints return correct shape, caller-scoped.

## Phasing (the plan will sequence; design targets the whole)

1. Pipeline end-to-end on a **subset of signals** (a few deterministic + a few existing) for accounts → snapshot + color + actions working.
2. Add talent entity path.
3. Fill in all 29 signals (deterministic computations + definitions).
4. Backfill mode + incremental loop.
5. Frontend color + matrix panel.

Each phase is independently testable and leaves the system working.
