# Design 07 — Dual-Sided Account Health

**Phase:** 2 (Design)
**Tier:** 2 — second-week lock
**Status:** Draft, Phase 2

---

## Purpose

Pulse's most differentiated architectural pattern: **account health is composed of both customer-side signals AND talent-side signals**, rolled up into a single per-account composite tier. PM_CONTEXT memory `project_rm_dual_sided` is unambiguous — RMs manage both, and no reference repo in the Phase 1 audit had this dual rollup as a first-class concept.

This spec defines: the customer-side input set, the talent-side input set, the composition formula, the output tier values, freshness semantics, and how skills consume the health value.

---

## Inputs

### Customer-side signals (per Account)

| Signal | Source | Polarity | Weight (Phase 1 default) |
|---|---|---|---|
| `RM_Outreach__c.Customer_Health__c` | RM-curated SFDC field | varies | high (RM judgment) |
| `RM_Outreach__c.Churn_Probability__c` | RM-curated SFDC field | negative | high |
| `RM_Outreach__c.Expansion_Probability__c` | RM-curated SFDC field | positive | medium |
| Open risk-tagged Cases on the Account (not on a placed talent) | `Case.AccountId` join | negative | high |
| Recent Chorus churn signals (Skill 01 output, last 60d) | Graph edges | negative | medium |
| Recent Chorus expansion signals (Skill 01 output, last 60d) | Graph edges | positive | medium |
| Multi-axis sentiment trajectory (last 60d) | Graph properties | varies | medium |
| Days since last RM-customer touchpoint | Computed from episodes | negative when stale | low |
| External news signals (where ingested) | News adapter (v1.5+) | varies | low |

### Talent-side signals (per Account, aggregated across all placed Associates)

| Signal | Source | Polarity | Weight (Phase 1 default) |
|---|---|---|---|
| Replacement rate among placed Associates (last 180d) | `Associates__c.Stage__c` aggregation | negative | high |
| Open risk-tagged Cases on placed talent | `Case.Associate__c` join | negative | high |
| Average talent-welfare signal severity (last 90d) | Graph edges from Skill 01 | negative | medium |
| Talent-care cadence compliance (Skill 04) | Computed from latest check-ins | negative when overdue | medium |
| Successful talent recognitions (Skill 07) | Graph edges | positive | low |
| Days since last talent-side touchpoint | Computed | negative when stale | low |

### Configuration inputs

- **Tier classification of the Account** (drives different thresholds — Enterprise tolerates fewer adverse signals before downgrading).
- **Customer's industry segment** (Insurance vs. Medical vs. Dental — some signals are vertical-weighted, e.g., audit-failure carries more weight in Dental).

## Outputs

- **A health tier** per Account, refreshed at most every 5 minutes (cached in Postgres `account_health` table; recomputed lazily on read or eagerly on event-log fan-out).
- **Component sub-scores** for explainability: `customer_side_score`, `talent_side_score`, plus the top 3 contributing signals on each side.
- **Health-tier-change events** in the event log (Design 04) when the tier transitions.

---

## Behavior

### The composition formula (Phase 1)

**Two-stage composition:**

```
Step 1: compute customer_side_score (range -100 to +100)
        - normalize each customer-side signal to a per-signal score
        - weighted sum
        - cap at ±100

Step 2: compute talent_side_score (range -100 to +100)
        - normalize each talent-side signal
        - weighted sum
        - cap at ±100

Step 3: composite_score = α * customer_side_score + β * talent_side_score
        - α and β are tier-dependent:
          - SMB:        α=0.6, β=0.4    (customer-side leads; SMB has fewer placements)
          - Mid:        α=0.5, β=0.5    (balanced)
          - Enterprise: α=0.4, β=0.6    (talent-side leads; Enterprise has more placements
                                          and talent-replacement risk is the dominant churn driver)

Step 4: composite_score → tier mapping
          composite_score >=  +40  → "Healthy"
          composite_score in [+10, +40)  → "Stable"
          composite_score in [-10, +10)  → "Watch"
          composite_score in [-40, -10)  → "At-Risk"
          composite_score <  -40  → "Escalated"
```

**Why a weighted sum, not a multiplicative model:**
- Linear models are easier to reason about, easier to explain in the action card's `why_detail`, and easier to tune.
- Multiplicative models hide which signal is driving the tier — the agent needs to *cite* the dominant contributor, which weighted-sum readily exposes.

**Why these tier values (Healthy / Stable / Watch / At-Risk / Escalated):**
- Five tiers give enough resolution for the CEO View and for the Action Queue ranking, without overwhelming the RM.
- The terminology aligns with the existing `RM_Outreach__c.Customer_Health__c` values where they're known (Phase 1 may map directly if the picklist enums match — pending Spike 1 follow-up).

### Why the dual rollup matters

A customer can be **"customer-side healthy but talent-side dying"** — the customer's stakeholders are friendly, but placed talent are quitting and being replaced at high rates. Single-axis health would miss this: the customer-side sentiment looks fine, so the system assumes no problem; in reality, the customer is one bad replacement chain from terminating the engagement. Dual rollup makes this visible.

Conversely, a customer can be **"customer-side hostile but talent-side healthy"** — the customer's contact is grumpy this quarter, but the placed talent are delivering excellent work and customers in similar situations historically retain. Single-axis health would over-react.

Both scenarios exist in EDGE's book of business (per `project_rm_dual_sided` memory and the rm-intelligence-agent prototype's observation that "supply-side replacement rate is a leading churn indicator").

### Freshness semantics

- **Triggered recompute:** when any signal in §"Inputs" changes (event-log fan-out on `episode-ingested`, `Case` Stage change, `Associates__c` Stage change), the affected Account's health is invalidated and recomputed within 5 minutes.
- **Scheduled recompute:** all Accounts recompute nightly at 02:00 local as a safety net for any missed event-log fan-outs.
- **Read-time recompute:** if a skill requests an Account's health and the cached value is >5 minutes stale, recompute synchronously on read.

### Health-tier-change events

When `account_health.tier` transitions (e.g., from `Stable` to `Watch`), emit a `health-tier-changed` event to the event log:

```yaml
event_type: health-tier-changed
customer_id: <Account.Id>
payload:
  from_tier: "Stable"
  to_tier: "Watch"
  composite_score_from: 18.4
  composite_score_to: -3.2
  customer_side_delta: -8.0
  talent_side_delta: -13.6
  top_contributing_signals:
    - {side: "talent", signal: "replacement-rate", current_value: 0.35, delta: +0.15}
    - {side: "customer", signal: "open-cases-customer-side", current_value: 2, delta: +1}
    - {side: "customer", signal: "chorus-churn-signals-60d", current_value: 4, delta: +2}
```

**Why emit:** the event triggers skills that should act on the transition. Specifically:
- A drop into `Watch` or worse triggers Skill 03 `renewal-watcher` to reassess (if the customer is anywhere near a renewal window).
- A drop into `At-Risk` or `Escalated` triggers an Admin/VP-of-CS notification card in the Overall view of the Action Queue.

### Skill consumption pattern

Skills read health via the retriever:

```python
# Pseudocode
bundle = await ctx.retrievers.get_customer_context(customer_id)
bundle.account_health  # → AccountHealth dataclass with tier, component scores, contributors
```

Skills do **not** recompute health themselves. The composition logic lives in **one named module** (`03_build/health/dual_sided.py` in Phase 4) consumed by retrievers; this avoids the failure mode where 10 skills all reinvent the rollup with subtle differences.

### Tier-aware thresholds — where they apply

The same composite score produces a different tier at different customer tiers:

| Customer tier | Threshold adjustment |
|---|---|
| **SMB** | Default thresholds |
| **Mid-Market** | Thresholds tightened by 10 points each (e.g., Healthy starts at +30, not +40) |
| **Enterprise** | Thresholds tightened by 20 points (Enterprise should rarely be "Healthy" without active relationship work) |

This is a deliberate calibration choice: an Enterprise customer at composite +35 should not be classified the same as an SMB customer at composite +35, because the strategic stakes differ. PM_CONTEXT §6 rule 4 (tier-aware behavior) is satisfied via this calibration plus the per-tier α/β weights above.

### Audit & explainability

Every health value carries:
- The exact formula version used (Phase 1 = `v1.0`).
- The signal values at compute time.
- The α/β weights applied.
- The top-3 contributing signals on each side.

This payload is what the Action Queue's `why_detail` panel renders (Design 03), what the CEO View summarizes (Design 08), and what the Senior Developer reads during review. **There is no "black box health score"** — the RM and the auditor can always trace why an Account is at a given tier.

---

## EDGE Coverage references

- **§13.3 Workflow 2** row "Aggregate sentiment, identify red flags" — the dual-sided rollup *is* this aggregation, with talent-side as a first-class input.
- **§13.5 JD area "Talent Relationship & Engagement"** row "Cohesive customer + Talent experience" — direct implementation; the rollup makes the dual relationship visible.
- **§13.5 row "Owner of placed Talent"** — talent-side composition makes this ownership measurable.
- **§13.5 row "Proactive risk monitoring"** — health-tier-change events are the proactive trigger.
- **§13.5 row "Collect health metrics, renewal forecasts, churn, usage"** — the composite health value is the headline metric in the CEO View (Design 08).
- **§13.6 #4** "Talent-side workflows as first-class — EDGE focuses customer-side; JD makes clear half the value is talent-side" — this artifact *is* the receipt.

---

## Open questions

- **Q85** — α/β weight tuning. Phase 1 defaults are heuristic. v1.5+ may use historical churn outcomes to fit the weights. Filed.
- **Q86** — `Customer_Health__c` picklist enum values from SFDC. If they match `Healthy/Stable/Watch/At-Risk/Escalated`, Phase 1 can map directly; otherwise Pulse maintains its own enum and reports both side-by-side. Awaiting Spike 1 resolution.
- **Q87** — Per-industry-segment signal weighting. The spec hints at industry weighting (e.g., audit-failure heavier in Dental); Phase 1 default is no industry differential. Filed for v1.5.
- **Q88** — Health-tier-change notification fatigue. If an Account oscillates between Watch and Stable on small score changes, the change events become noise. PM proposes: emit `health-tier-changed` only on transitions that hold for ≥24h (debouncing layer). Filed for Phase 4 detail.
- **Q89** — Historical-trajectory display. Should the Account profile (Design 06) show a sparkline of the composite score over time? PM proposes: yes, in Phase 1 if cheap.

---

## What this is NOT

- **Not a churn-prediction model.** No ML training in Phase 1 (per §12 #1 v1.5+). The rollup is a *current-state composite*, not a *future prediction*. Phase 1 churn-watching uses Skill 03 rules + this health value.
- **Not a black-box score.** Every tier value cites its top contributors.
- **Not where signals are extracted.** Skill 01 `detect-talent-signal` extracts signals; this composition module *consumes* them.
- **Not user-facing per-component-score detail.** The RM sees the tier value and (on click) the top contributors. The full numeric breakdown is admin-only.
- **Not a replacement for the RM's `RM_Outreach__c.Customer_Health__c` field.** Pulse *consumes* that field as a high-weight input. RMs continue to author it. Pulse's composite is *additive* to RM judgment, not substitutive.
- **Not multi-tenant-aware in Phase 1.** Single-tenant assumption per Q43.
