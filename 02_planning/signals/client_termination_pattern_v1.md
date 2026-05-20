# client_termination_pattern_v1

**Version:** v1
**Category:** account-context
**Severity model:** tiered (low / medium / high) — surfaced as account-context, not as real-time alert
**Owning skill(s):** Skill 10 (cross-account-pattern-finder) — primary; Skill 03 (renewal-watcher) consumes as context
**Status:** active

## Plain-English definition

A customer has terminated or replaced N or more placed Talent in the last M months. This is a leading indicator of churn that is structurally hidden in the per-Talent view — RMs see "Marcus was replaced" as one event; they may not see that this is the *fourth* talent the customer has terminated this quarter. The signal aggregates termination/replacement events at the Customer level and surfaces the pattern as **account context** (informs other actions) rather than firing a real-time alert.

Locked Session 11 (PM_CONTEXT Decision log entry 36).

## Detection mechanism

**Type:** rule-based (no LLM — terminations are structured SFDC events)

```
For each Customer:
  associates = retrieve(sfdc.Associates__c where Account__c = Customer)
  termination_events_in_window = []
  for assoc in associates:
    if assoc.Stage__c in ('Replaced', 'Terminated'):
      # When did the transition happen?
      transition_date = assoc.LastModifiedDate  # proxy; Phase 1 doesn't track full Stage history
      if transition_date >= today - 180:
        termination_events_in_window.append(assoc)

  if len(termination_events_in_window) < 2:
    return None

  # Compute rate
  customer_active_count = count(assoc where Stage__c == 'Active')
  termination_rate = len(termination_events_in_window) / max(1, customer_active_count + len(termination_events_in_window))

  # Tier severity
  if len(termination_events_in_window) >= 4 OR termination_rate >= 0.4:
    severity = 'high'
  elif len(termination_events_in_window) >= 3 OR termination_rate >= 0.25:
    severity = 'medium'
  else:
    severity = 'low'

  # Surface as account-context, not as Action Queue card directly
  emit_account_context(severity, evidence=termination_events_in_window)
```

**Note on surfacing.** This signal does *not* directly drive an Action Queue card. Instead, it emits an `account_context` event the other skills consume:
- Skill 03 (renewal-watcher) weights this as a churn-risk factor when evaluating renewal proximity.
- Skill 10 (cross-account-pattern-finder) aggregates `client_termination_pattern` across multiple Customers to detect industry-wide patterns ("3 dental customers each terminated 3+ talent this quarter").
- The Per-Profile Markdown (Design 06) Customer profile's "Trajectory" section embeds the termination rate as durable context.

## Evidence shape

| Source | Field(s) | Time window |
|---|---|---|
| SFDC `Associates__c` | `Stage__c`, `LastModifiedDate`, `Risk_level__c`, `Risk_Details__c`, `Prior_Associate_Replaced__c` | last 180 days |
| SFDC `Case` linked via `Associate__c` | `Description`, `Details__c`, `Categories__c` (for termination *reason*) | last 180 days |
| Graphiti `replaced_by` edges | chain of replacements | historical |

## Triggering threshold

- `low` — 2 terminations in 180 days OR rate ≥10%
- `medium` — 3 terminations OR rate ≥25%
- `high` — 4+ terminations OR rate ≥40%

## Tier-aware variants

| Customer tier | Variant |
|---|---|
| **SMB** | SMB customers naturally have fewer placements; threshold relative to active count is more meaningful than absolute count. Use rate-based threshold primarily. |
| **Mid-Market** | Standard. |
| **Enterprise** | Severity floor raised by one tier (Enterprise customers with 2 terminations in 180d already warrant attention). |

## False-positive failure modes

- **Customer-side downsizing.** Customer terminated talent due to their own restructure, not EDGE-side issues. Mitigation: cross-reference Case descriptions for termination reasons; if reason is `Customer-side capacity reduction` or `Role no longer needed`, downweight (the data is signal but for different reasons — Skill 11 may also find expansion patterns elsewhere).
- **Conversion to permanent placement.** Some "terminations" are conversions of EDGE talent to client direct-hire. This is a *positive* outcome but looks like a termination event. Mitigation: cross-check `Risk_Details__c` for "converted to permanent" language; suppress.
- **Project completion.** Some placements are time-bounded (project-based). Stage transition to `Terminated` is expected. Mitigation: check `Type__c` and `End_Date__c` — if planned, suppress.

## False-negative failure modes

- **Slow attrition.** 2 terminations every 6 months over 2 years is severe trajectory but never crosses 180-day threshold. v1.5+: longer-window cumulative tracking.
- **Missed Stage history.** Phase 1 uses `LastModifiedDate` as transition-date proxy. If a record's Stage was set then re-set, we see only the latest. SFDC field-history tracking is the proper source; v1.5+.

## Adjustability

| Parameter | Type | Default | Who | Effect |
|---|---|---|---|---|
| Lookback window | int days | 180 | Admin | |
| Absolute thresholds (low/medium/high) | int | 2/3/4 | Admin | |
| Rate thresholds | float | 0.10/0.25/0.40 | Admin | |
| Conversion-to-permanent suppression | bool | True | Admin | |
| Project-completion suppression | bool | True | Admin | |

## Performance metrics (populated by Layer 8 Mechanism 1)

- Fire rate: _TBD_
- Outcome (customer churns within 180d of `high` fire): _TBD_  ← the validation signal
- Outcome (renewal closed-won within 180d of `high` fire after intervention): _TBD_  ← success case
- Last tuned: never

## Examples

### Example 1 — Acrisure (Mid-Market)
- **Evidence:** Last 180 days — 3 Associates transitioned to `Replaced` (Marcus Wells dental, two others medical). Active placement count = 18. Rate = 3/(3+18) = 14%.
- **Severity:** `medium` (3 terminations; rate <25%).
- **Surfaced as:** account context for Skill 03's renewal-watcher (renewal in 56 days; the termination pattern raises composite churn risk). Per-Profile Markdown Trajectory section embeds the pattern.

### Example 2 — Cross-account pattern (Skill 10 consumes)
- **Evidence:** 3 dental-vertical customers each have `client_termination_pattern_v1` firing at `medium+` in last 90 days.
- **Skill 10 surface:** "Cohort pattern: dental-vertical termination rate elevated across 3 customers; investigate whether EDGE's dental-coding placement training is sufficient."

## Open questions

- **Q142:** Stage-history tracking. Phase 1 uses `LastModifiedDate` as a proxy; this misses prior transitions. Should Phase 1 add a Pulse-side `associate_stage_history` table to track transitions? PM proposes: yes, written by the SFDC Signal Source Adapter on every `Associates__c` ingestion. Adds ~0.25 days. Filed as a sub-spec for SFDC adapter.
- **Q143:** Conversion-to-permanent suppression heuristic. Phase 1 looks for "converted to permanent" in `Risk_Details__c`. v1.5+: explicit `Conversion_Date__c` field if EDGE wants to track these distinctly.
