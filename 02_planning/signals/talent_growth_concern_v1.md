# talent_growth_concern_v1

**Version:** v1
**Category:** talent-care
**Severity model:** tiered (low / medium / high)
**Owning skill(s):** Skill 01; Skill 04 (talent-care); Skill 09 (coaching-signal-router — primary consumer)
**Status:** active

## Plain-English definition

A placed Talent has expressed concerns about career growth, skill stagnation, or limited advancement at the current placement. Distinct from burnout: growth-concern surfaces when the talent is *bored* or *plateauing*, not *overwhelmed*. Often a precursor to voluntary departure when an external opportunity arises.

## Detection mechanism

**Type:** LLM-based (Skill 01 extraction)

Skill 01 output schema:
```json
{
  "talent_welfare_signals": [
    {
      "type": "growth_concern",
      "severity_hint": "low" | "medium" | "high",
      "speaker_role": "talent_self" | "rm_observation" | "third_party",
      "context": "<verbatim quote or paraphrase>",
      "indicators": ["career stagnation", "wants new responsibilities", "asks about promotion path", ...]
    }
  ]
}
```

Fires on any `growth_concern` signal in last 60-day window (longer than burnout — growth concerns build slowly):

```
For each Talent (Active):
  growth_signals_60d = retrieve(... type='growth_concern' ... last 60 days)
  if not growth_signals_60d:
    return None
  has_self_report = any(s.speaker_role == 'talent_self' for s in growth_signals_60d)
  max_severity = max(s.severity_hint for s in growth_signals_60d)
  severity = max_severity
  if has_self_report and severity == 'low':
    severity = 'medium'
  fire(severity)
```

## Evidence shape

| Source | Field(s) | Time window |
|---|---|---|
| Chorus check-in episodes | content + transcript | last 60 days |
| SFDC `RM_Outreach__c` where Associate__c=Talent | `Description__c` | last 60 days |
| SFDC `Case` where Associate__c=Talent | `Description`, `Details__c` (if growth-related) | last 90 days |

## Triggering threshold

Any growth_concern signal in last 60 days. Severity per Skill 01 hint, +1 tier if self-report.

## Tier-aware variants

| Customer tier | Variant |
|---|---|
| **SMB** | Standard; coaching handoff via Skill 09 auto-approve at +2h. |
| **Mid-Market** | Standard. Human-required. |
| **Enterprise** | Standard; cc Talent Dev senior lead on `medium+`. |

## False-positive failure modes

- **Aspirational career planning.** Talent describes long-term goals without dissatisfaction. Mitigation: Skill 01 prompt distinguishes future-aspiration from current-frustration.
- **Conversation about promotion as a positive moment.** "I'd love to grow into X eventually" is healthy. `severity_hint=low` + non-self-report stays low.

## False-negative failure modes

- **Silent frustration.** Talent is plateauing but doesn't mention it. v1.5+ enhancement: tenure-based trigger (talent >18 months in same role gets a Skill 09 check-in regardless of explicit signal).

## Adjustability

| Parameter | Type | Default | Who | Effect |
|---|---|---|---|---|
| Lookback | int days | 60 | Admin | |
| Tenure-trigger fallback | bool | False | Admin | v1.5+ candidate |

## Performance metrics (populated by Layer 8 Mechanism 1)

- Fire rate: _TBD_
- Action-approval rate: _TBD_
- Outcome (coaching session booked within 21d): _TBD_
- Outcome (talent voluntarily leaves within 180d of fire): _TBD_  ← failure case
- Last tuned: never

## Examples

### Example 1 — Aisha Patel @ Pinnacle
- **Evidence:** Chorus check-in. Aisha: *"I've been doing the same coding work for a year; I want to learn the quality-audit side too."* `type=growth_concern`, `severity_hint=medium`, `speaker_role=talent_self`.
- **Signal fires at:** `medium`.
- **Action proposed:** Skill 09 routes to Talent Dev for a coaching conversation about cross-training paths.

## Open questions

- See Q136 (welfare taxonomy completeness).
