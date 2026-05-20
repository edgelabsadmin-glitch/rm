# Design 04 — Event Log + Reasoning Capture

**Phase:** 2 (Design)
**Tier:** 1 — first-week lock
**Status:** Draft, Phase 2

---

## Purpose

The event log is **Pulse's audit spine**. Every signal received, every skill fired, every action proposed, every approval decision, every dispatch, every outcome — written to a single append-only Postgres table. It is the literal answer to §6 rule 12 ("no silent failure"), the implementation of the "AWS-only hosting + audit log on every action" standing rule (§6 rule 2), and the data substrate the policy module reads to enforce tier-aware approval thresholds.

This spec defines: the event schema, the lifecycle of an action from proposal to outcome, the reasoning-capture payload shape, the policy module's input/output contract, and the queries the system runs against the log.

The event vocabulary is **lifted from Multi-Agent-Enterprise-CRM** (`findings/Multi-Agent-Enterprise-CRM.md` — `productivity.action-suggested` / `action-approved` / `action-rejected`). Payloads are Pulse-specific.

---

## Inputs

- **Signal events** from the Signal Source Adapter pipeline (Design 02): `signal-received`, `signal-rejected`, `signal-normalized`, `episode-ingested`, `episode-deduped`, `ingestion-failed`.
- **Agent reasoning events** from the skill runtime (Design 05): `skill-fired`, `context-retrieved`, `reasoning-completed`, `action-suggested`.
- **Approval events** from the Action Queue (Design 03): `action-approved`, `action-modified-and-approved`, `action-rejected`, `action-expired`.
- **Dispatch events** from action handlers: `action-executed`, `dispatch-failed`.
- **Outcome events** from passive outcome capture: `outcome-recorded`, `outcome-missing` (when a watched signal didn't materialize within the window).

## Outputs

- **The audit log**: every event durably written, with stable ordering, queryable by entity / by skill / by RM / by time range.
- **The policy module's input substrate**: the policy module reads recent events to decide approval thresholds (e.g., if a skill has produced 5 rejected actions in a row, dampen its proposals).
- **The CEO View's data source** (Design 08): aggregated event throughput per RM / per skill / per outcome.
- **The Per-Profile Markdown Layer's regeneration trigger** (Design 06): when a customer's event log changes meaningfully, the markdown profile re-renders.

---

## Behavior

### Storage — single Postgres `events` table

```sql
-- Phase 4 schema sketch; not for production until Phase 4 build
CREATE TABLE events (
    event_id        UUID PRIMARY KEY,
    event_type      TEXT NOT NULL,       -- enum below
    event_version   INT NOT NULL DEFAULT 1,
    occurred_at     TIMESTAMPTZ NOT NULL,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Entity refs (nullable — not every event references each)
    customer_id     TEXT,                -- SFDC Account.Id
    talent_id       TEXT,                -- SFDC Associates__c.Id
    rm_id           TEXT,                -- SFDC User.Id
    case_id         TEXT,                -- SFDC Case.Id
    action_id       UUID,                -- ties suggested → approved → executed → outcome
    episode_id      UUID,                -- ties to ingested Episode (Design 02)
    skill_id        TEXT,                -- "renewal-watcher", "ebr-prep", ...

    -- Payload: structured per event_type (JSONB; schemas in §"Event types" below)
    payload         JSONB NOT NULL,

    -- Tier-aware policy substrate
    tier_class      TEXT,                -- "SMB" | "Mid" | "Enterprise" | NULL
    urgency         TEXT,                -- only for action-suggested

    -- Operational
    correlation_id  UUID,                -- ties bursts (one signal → one chain of events)
    actor           TEXT,                -- "agent" | "user:<user_id>" | "system" | "policy"

    -- Reasoning (only on agent events; bounded length)
    reasoning_text  TEXT,                -- the agent's prose explanation
    reasoning_tags  TEXT[],              -- structured tags ("urgency:high", "skill:renewal-watcher")

    INDEX (event_type, occurred_at DESC),
    INDEX (action_id),
    INDEX (customer_id, occurred_at DESC),
    INDEX (rm_id, occurred_at DESC),
    INDEX (skill_id, occurred_at DESC),
    INDEX (correlation_id)
);
```

**Why single table over event-type-per-table:**
- Single timeline. The history of an action_id is a `WHERE action_id = X ORDER BY occurred_at` query, full stop.
- Cross-event queries (e.g., "for skill renewal-watcher, what's the suggested → approved → outcome funnel?") are trivial.
- Schema migration cost is concentrated in `payload` JSONB validation, not in 12 tables.

**Append-only by intent.** No `UPDATE`. Corrections happen as new events (`action-rejected` after `action-approved` = a correction event, not an update).

**Retention:** Phase 1 keeps full history in Postgres (volume is low — thousands of events/day across 8 RMs). At Phase 2+ scale, cold events older than 90 days move to compressed S3 archive with a re-indexable manifest. Defer that to v1.5+.

### Event types (Phase 1 enum)

| Event type | Emitter | Payload sketch |
|---|---|---|
| `signal-received` | Signal Source Adapter receiver | `{source, source_event_id, headers_hash}` |
| `signal-rejected` | Adapter receiver | `{source, reason: "bad-signature" / "rate-limit" / "duplicate-dedup-key"}` |
| `signal-normalized` | Adapter | `{episode_id, dedup_key, content_size}` |
| `episode-ingested` | Memory layer | `{episode_id, entity_extractions: [...], edge_extractions: [...], extraction_model, latency_ms}` |
| `episode-deduped` | Memory layer | `{episode_id, duplicate_of}` |
| `ingestion-failed` | Adapter or memory layer | `{stage, error_class, error_message_summary}` |
| `skill-fired` | Skill runtime | `{skill_id, trigger_event_id, context_bundle_summary}` |
| `context-retrieved` | Skill runtime | `{retrievers_called: [...], entity_count, episode_count, retrieval_latency_ms}` |
| `reasoning-completed` | Skill runtime | `{model, tokens_in, tokens_out, latency_ms, reasoning_summary}` |
| `action-suggested` | Skill runtime | `{action_card, why_oneline, why_detail, urgency, source_episodes}` |
| `action-approved` | Action Queue | `{action_id, approver_id, decision_latency_ms}` |
| `action-modified-and-approved` | Action Queue | `{action_id, approver_id, diff, decision_latency_ms}` |
| `action-rejected` | Action Queue | `{action_id, approver_id, reason_picker, free_text}` |
| `action-expired` | Action Queue | `{action_id, expired_after_seconds}` |
| `action-executed` | Dispatch handler | `{action_id, handler, external_id, dispatch_latency_ms}` |
| `dispatch-failed` | Dispatch handler | `{action_id, handler, error_class, retry_attempt}` |
| `outcome-recorded` | Outcome watcher | `{action_id, outcome_type, evidence_episode_id}` |
| `outcome-missing` | Outcome watcher | `{action_id, outcome_window_closed_at, expected_outcome_type}` |
| `policy-decision` | Policy module | `{action_id, decision: "auto-approve"/"require-human"/"block", thresholds_applied}` |
| `kill-switch-flipped` | Admin UI | `{user_id, scope: "global"/"skill:X"/"customer:X", on_or_off}` |

### Reasoning capture — the agent prose layer

Every `reasoning-completed` and `action-suggested` event carries `reasoning_text` (bounded to ~2KB; longer reasoning gets a summary + S3 link in v1.5).

**Reasoning text structure (Phase 1):**

```
[skill: renewal-watcher]
[context: Customer=Acrisure, as_of=2026-05-20]

Signals consulted:
  - <num>2</num> open risk-tagged Cases (Risk - Talent Competency, Risk - Resignation)
  - <bad>Vendor-consolidation concern mentioned in 2 calls in the last 4 weeks</bad>
  - <good>Marcus Wells replacement plan delivered on time per RM_Outreach 2026-05-12</good>
  - EBR booked Thursday 2026-05-23 per Calendar

Reasoning:
  Account is in a watch state with rising churn risk but a recent positive
  signal on the replacement plan. The CFO mandate to cut vendor count by 20%
  is the dominant risk; the upcoming EBR is the natural moment to address
  it. RM should walk in with a tightened proposal.

Proposed action: draft EBR prep brief for Sarah Chen (Acrisure director)
Urgency: medium-high (EBR in 3 days; risk signals fresh)
```

**The inline-tag voice** (`<num>`, `<good>`, `<bad>`, `<quote>`, `<em>`) is **lifted verbatim from `rm-intelligence-agent/src/render_demo.py`**. Same renderer; same CSS classes. This means the same prose works in:
- The Action Queue card's `why_detail` panel (Design 03)
- The CEO View narrative (Design 08)
- The static-HTML fallback demo (Decision 12 — preserves rm-intelligence-agent's fallback)

**Reasoning structure invariants** (enforced by skill spec — Design 05):
- `Signals consulted:` always first
- `Reasoning:` always second
- `Proposed action:` always last
- Inline tags whitelisted; everything else escaped

### Action lifecycle — one action_id, many events

```
                  action-suggested
                        │
                        ▼
                  policy-decision
                ┌───────┴───────┐
                ▼               ▼
       auto-approve       require-human
                │               │
                ▼               ▼ (RM clicks Approve/Modify/Reject)
        action-approved   action-approved
                          / action-modified-and-approved
                          / action-rejected
                          / action-expired
                │               │
                └───────┬───────┘
                        ▼
                  action-executed (or dispatch-failed → retry → action-executed)
                        │
                        ▼
                  outcome-recorded (or outcome-missing after window)
```

One `action_id` threads the whole lifecycle. The CEO View's "throughput" chart is `COUNT(*) FILTER (WHERE event_type = 'action-executed') GROUP BY skill_id, week`. The "outcome rate" chart is `outcome-recorded / action-executed` over a window.

### Policy module — input/output contract

The policy module is the only consumer of `action-suggested` events with read-write authority over routing. **It is a code module in Phase 1**, not OPA (per `findings/Multi-Agent-Enterprise-CRM.md` recommendation and synthesis decision — defer real OPA to v1.5+ candidate #5+).

**Contract:**

```python
# Pseudocode — Phase 4 implementation
def policy_decide(suggestion: ActionSuggested) -> PolicyDecision:
    """
    Input: an action-suggested event payload.
    Output: a decision: auto-approve | require-human | block,
            with the thresholds that applied (for audit).
    Side effect: emits `policy-decision` event.
    """
```

**Phase 1 policy rules (code, not OPA):**
1. If `customer.tier_class == "Enterprise"` → always `require-human`.
2. If `urgency == "high"` → always `require-human` regardless of tier.
3. If `skill_id == "recognition"` → auto-approve at +1h delay across all tiers (low blast radius).
4. If `skill_id` has had ≥3 `action-rejected` in the last 14 days → require-human + flag for tuning.
5. If global kill switch is on → block (no actions dispatch at all).
6. If `customer.tier_class == "SMB"` AND `skill_id` is in the SMB auto-approve list → auto-approve at +1h.
7. Otherwise → require-human.

The auto-approve list is configuration, not code; Phase 1 default contains: `recognition`, `talent-care` (check-in only, not escalation), `onboarding` (kickoff sequence only).

**OPA migration trigger (v1.5+):** when the policy rule count exceeds ~15 or non-engineers need to tune them, migrate to OPA `.rego` files. Phase 1 keeps it simple.

### Querying the event log

Five named queries Pulse needs (Phase 4 implements these as named SQL views or repository functions):

1. **`action_history(action_id)`** — full lifecycle of a single action.
2. **`customer_recent_actions(customer_id, since)`** — every action proposed/dispatched/outcome'd for a customer.
3. **`skill_funnel(skill_id, since)`** — suggested → approved → dispatched → outcome-recorded counts.
4. **`rm_throughput(rm_id, since)`** — count of actions approved by this RM in a window.
5. **`recent_outcomes(since)`** — for the CEO View aggregation.

### Kill switch

The kill switch is a single boolean in the `pulse_settings` table plus per-scope overrides (`{global: false, by_skill: {renewal-watcher: false}, by_customer: {001A...: true}}`). When `global == true`, `policy_decide()` returns `block` for every suggestion. The block emits a `policy-decision` event so the audit trail records why nothing dispatched.

**Surface:** Admin UI has a single big toggle. RMs see a banner when the kill switch is on. Per §6 rule 12, no silent failure — the kill switch's *being on* is itself logged.

---

## EDGE Coverage references

- **§13.5 JD area "Issue Resolution & Escalation Management"** row "Track issues, resolutions, outcomes" — the event log is the substrate. Every escalation traceable end-to-end.
- **§13.5 JD area "Monitoring & Reporting"** row "Collect health metrics, renewal forecasts, churn, usage" — aggregations over the event log feed leadership reports (Design 08).
- **§13.5 JD area "Strategy & Operations"** row "Ensure compliance" — audit log + AWS-only standing rules (§6 rule 2) satisfy the compliance posture.
- **§6 rule 12** "No silent failure" — every agent action logs to the event log with reasoning attached. This artifact *is* the receipt.
- **§6 rule 2** "AWS-only hosting + audit log on every action" — same.
- **§13.6 #1** "Action Queue + agentic action proposals" — the event log is the spine that records every proposal and decision.

---

## Open questions

- **Q41** — Event log retention beyond 90 days. Cold archive to S3 with re-indexable manifest? Or full Postgres retention? PM proposes: full Postgres for Phase 1 (volume is low), cold archive in v1.5+.
- **Q42** — Reasoning text length cap. 2KB inline? S3-link-out for longer reasoning? PM proposes: 2KB inline with S3 link-out for longer (Phase 4 implementation detail).
- **Q43** — Cross-tenant analytics scope. If EDGE ever multi-tenants Pulse (different staffing firms on shared infra), per-tenant `events` schemas vs. shared table with tenant_id column? PM proposes: Phase 1 is single-tenant; revisit at multi-tenant time.
- **Q44** — Policy module rule format. Phase 1 = Python code; v1.5+ = OPA. PM proposes: write the Python rules as pure functions taking a typed `Suggestion` and returning a typed `Decision`, with the function names and signatures matching what OPA's input/output shape would be. Makes the migration mechanical.
- **Q45** — Outcome window per action type. How long does Pulse wait for an outcome before emitting `outcome-missing`? PM proposes: per-skill config; defaults: emails 7d, SFDC Tasks 14d, EBR briefs aligned with the meeting date.

---

## What this is NOT

- **Not a metrics database.** No aggregations are stored as nodes/columns; everything is computed from the event log. Prevents drift between aggregations and ground truth.
- **Not a search index over the agent's reasoning.** `reasoning_text` is queryable for audit/debugging, but the agent does not "search its past reasoning" as a runtime operation. (If it ever does, that's a v1.5+ feature.)
- **Not OPA in Phase 1.** Phase 1 ships Python policy code. OPA migration is v1.5+.
- **Not a queue.** Don't confuse this with a job queue. The workflow engine (Activepieces / n8n) has its own queues for retries; the event log is the *historical record*, not a work-dispatch primitive.
- **Not where Salesforce writes happen.** Writes happen via the dispatch handlers when an action is approved (§6 rule 6). The event log records that the write happened; it doesn't perform it.
- **Not user-facing.** RMs see the Action Queue (Design 03) and the CEO View (Design 08). Admins can drill into the event log via an admin console (Phase 2 design — Design 09).
