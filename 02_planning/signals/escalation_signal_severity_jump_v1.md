# escalation_signal_severity_jump_v1

**Version:** v1
**Category:** escalation
**Severity model:** tiered (low / medium / high)
**Owning skill(s):** Skill 05 (escalation-router) — primary
**Status:** active

## Plain-English definition

A new Case at a customer is materially more severe than recent Cases at that customer, OR a Case's status / severity transitions upward (e.g. opened with low priority then escalated to high). The signal captures the *delta* — Cases that look more serious than the customer's recent norm warrant earlier RM attention than the standard escalation-router would give them.

## Detection mechanism

**Type:** rule-based (no LLM call — severity is structured)

```
For each Customer:
  cases_90d = retrieve(sfdc.Case where AccountId=Customer
                                  AND CreatedDate >= today - 90)

  # Baseline severity = max recent severity (excluding the case being evaluated)
  for new_case in cases_90d where IsNewSinceLastScan(new_case):
    other_cases = [c for c in cases_90d if c.Id != new_case.Id]
    if not other_cases:
      baseline_severity = 'low'  # first case ever for this customer
    else:
      baseline_severity = max(severity_of(c.Categories__c, c.Priority) for c in other_cases)

    new_severity = severity_of(new_case.Categories__c, new_case.Priority)

    if severity_rank(new_severity) - severity_rank(baseline_severity) >= 2:
      fire(severity='high', evidence=(new_case, baseline_severity))
    elif severity_rank(new_severity) - severity_rank(baseline_severity) == 1:
      fire(severity='medium', evidence=(new_case, baseline_severity))

  # Also detect mid-case severity transitions
  for case in cases_90d:
    if case.severity_history shows jump in last 7 days:
      fire(severity='medium', evidence=case)
```

`severity_of(category, priority)` maps EDGE's risk taxonomy + Salesforce `Priority` to an ordinal:
- `Risk - Customer Payment Failure` → `critical`
- `Risk - Talent Resignation` → `high`
- `Risk - Talent Competency`, `Risk - Talent Professionalism` → `high`
- `Performance`, `Relationship Management` → `medium`
- `Risk – Emergency Leaves`, `Risk – Role Change` → `medium`
- `Business Performance`, `Business Needs` → `low`
- Plus `Case.Priority` field (Critical/High/Normal/Low) layered on top.

## Evidence shape

| Source | Field(s) | Time window |
|---|---|---|
| SFDC `Case` | `CaseNumber`, `Categories__c`, `Priority`, `Status`, `CreatedDate`, `Description`, `Details__c` | last 90 days |
| Graphiti episodes referencing the Case | content, source | current + historical |

## Triggering threshold

- Severity rank delta = 2+ → `high`
- Severity rank delta = 1 → `medium`
- Mid-case priority jump (within 7 days) → `medium`

## Tier-aware variants

| Customer tier | Variant |
|---|---|
| **SMB** | Standard ladder. |
| **Mid-Market** | Standard. |
| **Enterprise** | Any non-zero delta fires `medium+`. cc VP-CS at all severities. |

## False-positive failure modes

- **First-ever case is high-severity.** No baseline; the signal would default `baseline='low'` and over-fire. Mitigation: if `len(other_cases) == 0`, do not fire (let `escalation_signal_case_pattern_v1` or direct case-trigger handle it).
- **Stale baseline.** A 90-day-old `high` baseline may be irrelevant. Mitigation: weight more recent cases — within-last-30-days cases count more toward baseline.

## False-negative failure modes

- **Slow severity drift.** Each case slightly higher than the last, but no single jump triggers the rule. v1.5+ enhancement: trend-detection across 90+ days.

## Adjustability

| Parameter | Type | Default | Who | Effect |
|---|---|---|---|---|
| `severity_rank_map` | dict | per above | Admin | Re-map category → ordinal |
| Lookback baseline | int days | 90 | Admin | Wider = more stable baseline |
| Recent-weight multiplier | float | 2x last 30d | Admin | Recent cases weigh more |

## Performance metrics (populated by Layer 8 Mechanism 1)

- Fire rate: _TBD_
- Action-approval rate: _TBD_
- Outcome (Case resolved within SLA): _TBD_
- Last tuned: never

## Examples

### Example 1 — Acrisure
- **Evidence:** Acrisure's recent cases (last 90d) max severity = `medium` (Risk-Talent-Competency, Performance). New case 2026-05-18 opens with category `Risk - Customer Payment Failure` (critical rank).
- **Delta:** critical - medium = 2 ranks.
- **Signal fires at:** `high`.
- **Action proposed:** Skill 05 immediate escalation to Finance + cc VP-CS (Mid-Market+); SFDC Task with 1-business-day SLA.

## Open questions

- **Q140:** Severity-rank map confirmation. The map above is PM-proposed based on EDGE's existing risk taxonomy + standard SFDC priorities. User to confirm or revise — particularly the relative ranking of `Risk - Talent Competency` vs `Risk - Talent Resignation` (both currently `high`; one may warrant `critical`).
