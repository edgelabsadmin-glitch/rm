# churn_signal_renewal_period_silence_v1

**Version:** v1
**Category:** churn
**Severity model:** tiered (low / medium / high)
**Owning skill(s):** Skill 03 (renewal-watcher) — primary; Skill 05 (escalation-router) — high-severity cascade
**Status:** active

## Plain-English definition

A renewal is approaching, and the customer is unusually quiet about it. Renewal-window silence is a stronger churn signal than general silence: the customer should be *more* engaged as renewal approaches, not less. This signal composes general disengagement (see `churn_signal_contact_disengagement_v1`) with renewal proximity — the proximity is the amplifier.

## Detection mechanism

**Type:** rule-based (no LLM step needed — the renewal date is structured, the silence is measurable)

**Rule layer:**
```
For each Customer:
  next_renewal = identify_renewal(Customer)   # Opportunity.CloseDate or Account_Plan__c.Plan_End_Date
  if next_renewal is None or next_renewal > today + 120:
    return None  # too far out

  days_to_renewal = next_renewal - today

  silence = churn_signal_contact_disengagement_v1.evaluate(Customer)
  rm_outreach_recent = count(
    sfdc.RM_Outreach__c where Account__c = Customer
                           AND LastModifiedDate >= today - 30
                           AND EBR_Date__c is not null
  )

  fire_rule_a = days_to_renewal <= 60 AND silence.fires
  fire_rule_b = days_to_renewal <= 90 AND rm_outreach_recent == 0
  fire_rule_c = days_to_renewal <= 30 AND silence.severity >= 'medium'

  severity = 'low' if days_to_renewal > 60
           else 'medium' if days_to_renewal > 30
           else 'high'

  if fire_rule_a OR fire_rule_b OR fire_rule_c:
    fire(severity)
```

No LLM call — this signal is purely structural. The component `churn_signal_contact_disengagement_v1` does include an LLM resolver; this signal inherits that resolution.

## Evidence shape

| Source | Field(s) | Time window |
|---|---|---|
| SFDC `Opportunity` | `CloseDate`, `Type`, `StageName`, `Probability` | next 120 days |
| SFDC `Account_Plan__c` | `Plan_End_Date__c` (TBD field name per Q21) | next 120 days |
| SFDC `RM_Outreach__c` | `LastModifiedDate`, `EBR_Date__c`, `Description__c` | last 30 days |
| Outputs of `churn_signal_contact_disengagement_v1` | severity, evidence | current |

## Triggering threshold

**Fire if ANY of:**
- `days_to_renewal <= 60` AND `contact_disengagement` signal fires
- `days_to_renewal <= 90` AND zero RM_Outreach records in last 30 days
- `days_to_renewal <= 30` AND `contact_disengagement.severity >= medium`

**Severity escalation:**
- `low` — renewal 60-90 days out
- `medium` — renewal 30-60 days out
- `high` — renewal 0-30 days out

## Tier-aware variants

| Account tier | Variant |
|---|---|
| **SMB** | Renewal-watch window starts at 60 days (later — SMB renewals are smaller, less escalation cost). `low` severity not fired (only `medium`/`high`). |
| **Mid-Market** | Baseline 90-day window. |
| **Enterprise** | Renewal-watch window starts at 120 days (earlier — Enterprise renewals are larger, the recovery window is longer). All severities fire. cc VP-CS on `medium+` per §6 rule 4. |

## False-positive failure modes

- **Renewal already locked verbally.** Customer agreed to renew in conversation but it's not yet in SFDC. Mitigation: cross-check Per-Profile Markdown "Open threads" for renewal commitments; LLM resolver via the composed `contact_disengagement` step often catches this.
- **Long sales cycle.** Some Enterprise renewals start engagement 120+ days out by design; "silence at 90 days" isn't unusual. Mitigation: Enterprise variant uses different baseline thresholds.
- **Opportunity stage misread.** If `Opportunity.Type = 'Renewal'` is not consistently used, the signal may fire on net-new opportunities. Mitigation: validate Opportunity.Type values against Q58 after sandbox refresh (Q21).

## False-negative failure modes

- **Renewal not in Opportunity yet.** RM hasn't created the renewal Opportunity record yet; only `Account_Plan__c.Plan_End_Date` is the source. Mitigation: fall back to `Plan_End_Date` as the renewal proxy.
- **Customer with no formal renewal date.** Pay-as-you-go or month-to-month customers. v1.5+ enhancement: detect non-formal-renewal customers differently.
- **Renewal cadence < 60 days.** Some customers renew quarterly or monthly. Phase 1 thresholds assume annual-ish renewals. v1.5+ enhancement: per-Customer renewal-cadence learning.

## Adjustability

| Parameter | Type | Default (Mid) | Who can adjust | Effect |
|---|---|---|---|---|
| `low_severity_window` | int days | 90 | Admin | Earlier alerts |
| `medium_severity_window` | int days | 60 | Admin | Earlier escalation |
| `high_severity_window` | int days | 30 | Admin | Earlier-stage urgency |
| Renewal source priority | enum | `Opportunity` > `Account_Plan__c` | Admin | Per-org preference |

## Performance metrics (populated by Layer 8 Mechanism 1)

- Fire rate: _TBD_
- Action-approval rate: _TBD_
- Renewal outcome (Closed Won) within 30d of action approval: _TBD_  ← critical Layer 8 outcome metric
- Renewal outcome (Closed Lost) within 60d of signal first fire: _TBD_  ← the failure case
- Last tuned: never

## Examples

### Example 1 — Acrisure (Mid-Market)
- **Evidence:** `Opportunity.CloseDate = 2026-07-15` (56 days out). `contact_disengagement` fires at `medium` severity (18 days silence + EBR no-show). Zero RM_Outreach updates in last 30 days.
- **Signal fires at:** `medium` (rule_a + rule_b both trigger; renewal 30-60 days)
- **Action proposed:** Skill 03 (renewal-watcher) — draft renewal-touch email to Sarah Chen + SFDC Task for the RM with full evidence citation.

### Example 2 — Pinnacle (Enterprise, no signal)
- **Evidence:** Renewal 110 days out (within Enterprise 120-day window). Last RM_Outreach 12 days ago; active Chorus calls weekly. `contact_disengagement` does not fire.
- **Signal does NOT fire** — engagement is healthy despite renewal proximity.

### Example 3 — Mendota (SMB, high severity)
- **Evidence:** Renewal 25 days out. `contact_disengagement` fires at `medium`. SMB variant: 60-day window, medium+ severities only.
- **Signal fires at:** `high` (renewal <30 days, contact disengagement medium).
- **Action proposed:** Skill 03 + Skill 05 cascade. Email draft + SFDC Task + (SMB tier) auto-approve at +2h.

## Open questions

- **Q130:** Renewal source priority. Opportunity-first vs. Account_Plan__c-first vs. both. PM proposes: Opportunity first (when present); Account_Plan__c as fallback. User confirmation pending Q21 sandbox refresh which clarifies which is more reliably populated.
- **Q131:** Non-renewal customers (PAYG / month-to-month). Phase 1 silently excludes them. Filed v1.5+.
