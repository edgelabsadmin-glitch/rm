# talent_pay_concern_v1

**Version:** v1
**Category:** talent-care
**Severity model:** tiered (low / medium / high)
**Owning skill(s):** Skill 01; Skill 04 (talent-care); Skill 05 (escalation-router — high-severity routes to HR/Finance); Skill 09 (coaching-signal-router); Skill 10 (cross-account-pattern-finder — cohort pay concerns)
**Status:** active

## Plain-English definition

A placed Talent has raised pay concerns — explicit dissatisfaction with current compensation, comparison to market rates, mention of competing offers, or hints that pay-driven attrition is imminent. The highest-stakes talent-welfare signal because resolution often requires Finance / HR involvement and the window between signal and resignation is short.

## Detection mechanism

**Type:** LLM-based (Skill 01 extraction)

Skill 01 output schema:
```json
{
  "talent_welfare_signals": [
    {
      "type": "pay_concern",
      "severity_hint": "low" | "medium" | "high",
      "speaker_role": "talent_self" | "rm_observation" | "third_party",
      "context": "<verbatim quote or paraphrase>",
      "indicators": ["market-rate comparison", "competing offer mention", "stipend ask", "raise request", "cost-of-living mention"]
    }
  ]
}
```

Fires on any `pay_concern` signal in last 45 days:

```
For each Talent (Active):
  pay_signals_45d = retrieve(... type='pay_concern' ... last 45 days)
  if not pay_signals_45d:
    return None

  has_self_report = any(s.speaker_role == 'talent_self' ...)
  has_competing_offer = any('competing offer' in s.indicators ...)
  max_severity = max(s.severity_hint ...)
  severity = max_severity

  if has_self_report and severity == 'low':
    severity = 'medium'
  if has_competing_offer:
    severity = 'high'  # competing offer always elevates

  fire(severity)
```

**Privacy guardrail (per Skill 09's privacy posture):** the signal *fires*, but the action card surfaces "pay concern raised in check-in" without quoting specific dollar figures even if the talent named them. The verbatim quote is available in the why_detail but the why_oneline summarizes generically.

## Evidence shape

| Source | Field(s) | Time window |
|---|---|---|
| Chorus check-in episodes | content + transcript | last 45 days |
| SFDC `RM_Outreach__c` where Associate__c=Talent | `Description__c` | last 45 days |
| SFDC `Case` where Associate__c=Talent | `Description`, `Details__c`, `Categories__c IN ('Risk - Resignation', 'Business Performance')` | last 90 days |
| SFDC `Associates__c.Salary__c`, `Annual_Recurring_Revenue__c` | numeric context for the action card | current |

## Triggering threshold

Any pay_concern signal in last 45 days. Severity per Skill 01 hint, +1 tier on self-report, **always high** if competing-offer indicator is present.

## Tier-aware variants

| Customer tier | Variant |
|---|---|
| **SMB** | Standard ladder; resulting check-in human-required (sensitive). |
| **Mid-Market** | Same. |
| **Enterprise** | Severity floor raised by one tier (any pay_concern → `medium`+); cc Finance lead + HR on `high`. |

## False-positive failure modes

- **Casual market-rate curiosity.** "I saw a friend got X at another firm" — interest, not threat. Mitigation: `severity_hint=low` + non-self-report stays low; the privacy guardrail also means the resulting card is non-urgent in tone.
- **Cost-of-living mention.** "Rent went up this year" is a context comment, not a pay demand. Mitigation: Skill 01 prompt distinguishes contextual mention from grievance.

## False-negative failure modes

- **Silent comparison.** Talent is interviewing externally but hasn't said anything to EDGE. Phase 1 can't see this.
- **Indirect mentions.** "I'm worried about finances generally" without pay-vs-EDGE framing. v1.5+: extend Skill 01 to flag financial-stress signals separately.

## Adjustability

| Parameter | Type | Default | Who | Effect |
|---|---|---|---|---|
| Lookback | int days | 45 | Admin | |
| Competing-offer auto-high | bool | True | Admin | Off = competing offer respects ladder |
| Privacy guardrail (no $ in why_oneline) | bool | True | Admin | Off violates privacy posture — strongly defaulted on |

## Performance metrics (populated by Layer 8 Mechanism 1)

- Fire rate: _TBD_
- Action-approval rate: _TBD_
- Outcome (RM follow-up within 7d): _TBD_
- Outcome (Talent stage transitions to Resigned within 60d of fire): _TBD_  ← failure case
- Outcome (raise / placement change executed within 90d): _TBD_  ← success case
- Last tuned: never

## Examples

### Example 1 — Marcus Wells @ Acrisure
- **Evidence:** Chorus check-in. Marcus: *"I've gotten reaches from two other firms paying more for similar dental coding roles."* `type=pay_concern`, `severity_hint=medium`, `speaker_role=talent_self`, indicators=["competing offer mention", "market-rate comparison"].
- **Signal fires at:** `high` (competing-offer auto-high rule).
- **Action proposed:** Skill 04 + Skill 05 — immediate RM 1:1 + escalation to Finance/HR for placement-rate review. Privacy guardrail ensures why_oneline reads "pay concern raised; competing offers mentioned" without dollar figures.

## Open questions

- See Q136 (welfare taxonomy completeness).
- **Q137:** Privacy guardrail behavior on internal admin views. The Admin/VP-CS surface may legitimately need the dollar context for resolution. PM proposes: privacy guardrail strips $ from RM-tier why_oneline only; Admin view shows full context. Filed for Design 09 RBAC review at Phase 4 spec-write time.
