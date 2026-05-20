# recognition_signal_advocacy_candidate_v1

**Version:** v1
**Category:** recognition
**Severity model:** scored (0-1)
**Owning skill(s):** Skill 06 (advocacy) — primary; Skill 07 (recognition) — coordination
**Status:** active

## Plain-English definition

A customer has shown clear positive patterns in recent episodes — direct positive quotes, expansion willingness, successful issue resolutions, high `Customer_Health__c` ratings — and qualifies as an advocacy candidate. The signal identifies *ambassadors*: customers worth asking for references, case studies, or further expansion.

## Detection mechanism

**Type:** rule-based + LLM-confirmed (Skill 01 already extracted positive-sentiment quotes; this signal aggregates)

```
For each Customer:
  positive_quotes_30d = retrieve(Graphiti.episodes
                                   where mentions(Customer)
                                   AND has(signal='positive_quote' OR signal='expansion_mention')
                                   AND date >= today - 30)

  customer_health = sfdc.RM_Outreach__c (latest).Customer_Health__c
  expansion_sentiment = sfdc.RM_Outreach__c (latest).Expansion_Sentiment__c
  open_risk_cases = count(sfdc.Case where AccountId=Customer AND IsClosed=False
                                       AND Categories__c LIKE 'Risk%')

  # Disqualifiers (per Skill 06 guardrails)
  if customer_health in ('At-Risk', 'Escalated', 'Watch'):
    return None
  if open_risk_cases > 0 with categories IN (
      'Risk - Talent Competency', 'Risk - Resignation',
      'Risk - Customer Payment Failure', 'Poor Experience with Edge', 'Competitor'):
    return None

  # Score the advocacy strength
  positive_signal_count = len(positive_quotes_30d)
  if positive_signal_count < 2:
    return None  # need at least 2 positive signals

  score = min(1.0, 0.3 + 0.2 * positive_signal_count
                       + (0.2 if expansion_sentiment in ('Strong', 'Likely') else 0)
                       + (0.2 if customer_health == 'Healthy' else 0))

  fire(score)
```

## Evidence shape

| Source | Field(s) | Time window |
|---|---|---|
| Graphiti episodes | `signal=positive_quote` or `signal=expansion_mention` | last 30 days |
| SFDC `RM_Outreach__c` | `Customer_Health__c`, `Expansion_Sentiment__c`, `Referral_Sentiment__c`, `Referral_Potential__c` | most recent |
| SFDC `Case` | `IsClosed`, `Categories__c` | last 60 days |
| SFDC `Account` custom field (if exists) | `Advocacy_Participation_History__c` (to track 12-month no-ask guardrail per Skill 06) | current |

## Triggering threshold

Fires when:
1. ≥2 positive signals in last 30 days, AND
2. Customer health not Watch / At-Risk / Escalated, AND
3. No open risk-tagged Cases in the disqualifier list (per Skill 06 guardrails).

Score 0.3 - 1.0 maps to:
- `0.3 - 0.5` → `low` advocacy strength (recognition note only)
- `0.5 - 0.75` → `medium` (reference-call ask appropriate)
- `0.75+` → `high` (case-study candidate; cc Sales)

## Tier-aware variants

| Customer tier | Variant |
|---|---|
| **SMB** | Recognition note only; no reference-call ask (per Skill 06 spec). |
| **Mid-Market** | Recognition + reference-call asks at `medium+`. |
| **Enterprise** | Recognition + reference-call + case-study suggestion at `high`; cc Sales lead. |

## False-positive failure modes

- **Polite-but-not-truly-positive customer.** Customer says "thanks, good work" generically — not a real advocate. Mitigation: Skill 01's `positive_quote` extraction looks for *specific* praise; generic thank-yous don't tag.
- **Recent good moment over recent bad moment.** A customer with 2 positive quotes and 1 open risk case shouldn't fire as advocate. The risk-case disqualifier handles this.

## False-negative failure modes

- **Quiet advocate.** Customer is happy but doesn't say so on calls. v1.5+: NPS / survey integration.

## Adjustability

| Parameter | Type | Default | Who | Effect |
|---|---|---|---|---|
| `min_positive_signals` | int | 2 | Admin | Higher = stricter advocacy gate |
| Disqualifier health-state list | list | Watch/At-Risk/Escalated | Admin | |
| Disqualifier case-category list | list | per Skill 06 | Admin | |
| 12-month no-ask guardrail | bool | True | Admin (per Skill 06) | |

## Performance metrics (populated by Layer 8 Mechanism 1)

- Fire rate: _TBD_
- Action-approval rate: _TBD_
- Outcome (customer-acceptance of advocacy motion within 14d): _TBD_  ← Skill 06 outcome
- Last tuned: never

## Examples

### Example 1 — Pinnacle
- **Evidence:** 4 positive quotes in last 30 days (CEO praise of medical coders; expansion mention for insurance coders; recognition of audit pass-through; ambassador-like reply to recent outreach). `Customer_Health__c=Healthy`. Zero open risk cases.
- **Score:** 0.3 + 0.2*4 + 0.2 + 0.2 = 1.1 → clamped to 1.0.
- **Signal fires at:** `0.75+` → `high`.
- **Action proposed:** Skill 06 — recognition note to CEO + reference-call ask drafted + case-study candidacy flag.

### Example 2 — Vertex Group — does NOT fire
- **Evidence:** 3 positive quotes but 1 open `Risk - Talent Competency` Case. Disqualified.

## Open questions

- **Q141:** `Advocacy_Participation_History__c` SFDC field. Does it exist? If not, Phase 1 tracks the 12-month no-ask guardrail in a Pulse-internal table. Filed for Q21 sandbox refresh confirmation.
