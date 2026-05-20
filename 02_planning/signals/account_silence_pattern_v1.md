# account_silence_pattern_v1

**Version:** v1
**Category:** account-context
**Severity model:** binary fire (silence detected) + tier (low / medium / high)
**Owning skill(s):** Skill 03 (renewal-watcher), Skill 04 (talent-care) — consume as context; Layer 8 Mechanism 1 (Signal Performance) flags this as a data-gap indicator
**Status:** active

## Plain-English definition

No signals from this account in the last N days. The signal serves two purposes: (1) account-context for other skills (silence on an account means recent RM judgments / customer health are stale and proposed actions should be calibrated accordingly), and (2) **data-gap detection** for Layer 8 — if a customer goes silent for too long, the absence is itself informative.

## Detection mechanism

**Type:** rule-based (no LLM — silence is structural)

```
For each Customer (Account.Status='Active'):
  last_signal_date = max(
    last(Chorus.engagements where account=Customer).completed_at,
    last(sfdc.RM_Outreach__c where Account__c=Customer).LastModifiedDate,
    last(sfdc.Case where AccountId=Customer).CreatedDate,
    last(sfdc.Opportunity where AccountId=Customer).LastModifiedDate,
    last(sfdc.Associates__c stage change where Account__c=Customer).LastModifiedDate,
    last(opportunity-tracker match where account_id=Customer).first_seen_date,
  )

  days_silent = today - last_signal_date

  if days_silent < threshold_for_tier(Customer.Segment__c):
    return None

  if days_silent >= threshold_for_tier(...) * 2:
    severity = 'high'  # double the threshold — significant data gap
  elif days_silent >= threshold_for_tier(...) * 1.5:
    severity = 'medium'
  else:
    severity = 'low'

  emit_account_context(severity, days_silent)
  emit_layer8_data_gap(Customer, days_silent)   # feeds Mechanism 1
```

## Evidence shape

| Source | Field(s) | Time window |
|---|---|---|
| All Signal Source Adapter outputs | latest timestamp per source | up to lookback window |
| Pulse `events` table | last `episode-ingested` event referencing this customer | current |

## Triggering threshold

Per-tier thresholds (in days):

| Customer tier | Silence threshold |
|---|---|
| **SMB** | 30 days (less frequent contact is normal) |
| **Mid-Market** | 21 days |
| **Enterprise** | 14 days |

Severity multipliers: ×1 to ×1.5 → low; ×1.5 to ×2 → medium; ×2+ → high.

## Tier-aware variants

Built into the threshold table directly. No further variation.

## False-positive failure modes

- **Account on PTO / vacation / known closure.** Customer announced they'd be silent (holiday, sabbatical). Mitigation: cross-check Per-Profile Markdown "Open threads" for stated absence; if present, suppress for the stated window.
- **Recently onboarded account.** New customer (Phase 1 created in last 30 days) hasn't generated signals yet. Mitigation: require Account creation > 30 days before firing.
- **Customer who simply doesn't use Chorus / SFDC heavily.** Some customers run mostly through in-person / email channels Phase 1 doesn't ingest. Mitigation: per-customer baseline — if customer's *historical* silence rate is similar, don't fire. v1.5+ enhancement.

## False-negative failure modes

- **Apparent activity, no substance.** Customer has SFDC record updates but they're all RM-side notes ("touched base by email"); no inbound signals. Phase 1 doesn't distinguish. v1.5+: inbound-vs-outbound signal classification.

## Adjustability

| Parameter | Type | Default | Who | Effect |
|---|---|---|---|---|
| Tier thresholds | dict | per above | Admin | |
| Severity multipliers | floats | 1.5, 2.0 | Admin | |
| New-account exemption window | int days | 30 | Admin | |

## Performance metrics (populated by Layer 8 Mechanism 1)

- Fire rate: _TBD_
- Correlation with churn outcomes: _TBD_  ← validates the silence-as-churn-precursor thesis
- Data-gap detection rate (count of customers in `high` silence): _TBD_  ← the Layer 8 use
- Last tuned: never

## Examples

### Example 1 — Mendota Health (Mid-Market)
- **Evidence:** Last signal 24 days ago (Chorus call). Tier threshold 21 days; multiplier 24/21 = 1.14 ≈ low.
- **Severity:** `low`.
- **Surfaced as:** account context. Skill 03 (renewal-watcher) reads this when evaluating Mendota's renewal proximity; weights it as slight churn-risk factor.

### Example 2 — Vertex Group (Mid-Market)
- **Evidence:** Last signal 45 days ago. Multiplier 45/21 = 2.14 → `high`.
- **Severity:** `high`.
- **Surfaced as:** account context + Layer 8 data-gap event. Skill 03 flags the renewal-watcher as needing fresh outreach urgently. Per-Profile Markdown regenerator notes the data-gap in the Trajectory section.

## Open questions

- **Q144:** Per-customer baseline learning. Some accounts are intrinsically quiet. v1.5+ enhancement.
- **Q145:** Data-gap → Layer 8 wiring. Layer 8 Mechanism 1 (Signal Performance metrics) is the admin surface; data-gap events from this signal go there. Phase 4 spec for Layer 8 Mechanism 1 needs to consume `layer8_data_gap` events explicitly.
