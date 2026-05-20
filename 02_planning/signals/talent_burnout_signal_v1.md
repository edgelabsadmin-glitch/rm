# talent_burnout_signal_v1

**Version:** v1
**Category:** talent-care
**Severity model:** tiered (low / medium / high)
**Owning skill(s):** Skill 01 (detect-talent-signal — emits the underlying tag); Skill 04 (talent-care — primary consumer); Skill 09 (coaching-signal-router — high-tier cascade); Skill 10 (cross-account-pattern-finder — cohort burnout patterns)
**Status:** active

## Plain-English definition

A placed Talent (Associate) has expressed burnout, exhaustion, or unsustainable-workload concerns in a Chorus call, RM_Outreach note, Case description, or any ingested episode about them. Burnout precedes resignation by weeks-to-months on average and is one of the highest-leverage early-detection moments for talent retention.

## Detection mechanism

**Type:** LLM-based (Skill 01 extraction)

Skill 01's prompt includes burnout as a recognized welfare-signal category:
```json
{
  "talent_welfare_signals": [
    {
      "type": "burnout",
      "severity_hint": "low" | "medium" | "high",
      "speaker_role": "talent_self" | "rm_observation" | "third_party",
      "context": "<verbatim quote or paraphrase if not direct>",
      "indicators": ["exhaustion mention", "workload complaint", "sleep concern", ...]
    }
  ]
}
```

This signal fires when any `talent_welfare_signal` of type `burnout` exists in the last 30 days for the Talent:

```
For each Talent (Associates__c with Stage='Active'):
  burnout_signals_30d = retrieve(Graphiti.episodes
                                   where mentions(Talent)
                                   AND has(signal='talent_welfare', type='burnout')
                                   AND date >= today - 30)
  if not burnout_signals_30d:
    return None

  # Direct quotes from the talent themselves weight heavier
  has_self_report = any(s.speaker_role == 'talent_self' for s in burnout_signals_30d)
  max_severity_hint = max(s.severity_hint for s in burnout_signals_30d)

  severity = max_severity_hint
  if has_self_report and severity == 'low':
    severity = 'medium'  # self-report bumps severity

  fire(severity)
```

## Evidence shape

| Source | Field(s) | Time window |
|---|---|---|
| Chorus episodes | `content.summary`, transcript (where ingested) | last 30 days |
| SFDC `RM_Outreach__c` where `Associate__c = Talent` | `Description__c`, `Satisfaction_with_Talent__c` (if RM annotated) | last 30 days |
| SFDC `Case` where `Associate__c = Talent` | `Description`, `Details__c`, `Categories__c` | last 90 days (broader window for cases) |
| Graphiti `raised_concern_about` edges | source episode, indicators, severity_hint | last 30 days |

## Triggering threshold

Fire on any burnout signal in last 30 days. Severity per Skill 01's hint, escalated by one tier if `speaker_role=talent_self`.

## Tier-aware variants

Tier-aware here refers to **the placed-at Customer's tier**, not Talent's tier.

| Customer tier | Variant |
|---|---|
| **SMB** | Standard threshold; resulting talent-care action auto-approve at +1h. |
| **Mid-Market** | Standard. Human-required. |
| **Enterprise** | Threshold sensitivity raised by one — Enterprise customers carry higher replacement-cost, so earlier intervention; cc Talent Dev on `medium+`. |

## False-positive failure modes

- **"Crunch week" venting.** Talent is exhausted this week but stable. Mitigation: the 30-day rolling window damps single-instance fires; severity stays low.
- **Mention without attribution.** RM says "they seem tired" but Talent didn't say so. Mitigation: `speaker_role=rm_observation` weights lower than `talent_self`.
- **Sarcasm / hyperbole.** "I'm dying" said in jest. Mitigation: Skill 01's prompt has explicit tone-context detection per Q133.

## False-negative failure modes

- **Burnout expressed in non-call channels.** Phase 1 boundary.
- **Quiet quitting / disengagement without burnout language.** Different signal pattern; not covered by this definition. v1.5+ may add a separate signal.

## Adjustability

| Parameter | Type | Default | Who | Effect |
|---|---|---|---|---|
| Lookback window | int days | 30 | Admin | Wider = more catches, more old-news fires |
| Self-report severity bump | bool | True | Admin | Off = no bump |
| Min indicator count for `high` | int | 3 | Admin | Tighter threshold |

## Performance metrics (populated by Layer 8 Mechanism 1)

- Fire rate: _TBD_
- Action-approval rate: _TBD_
- Outcome (RM check-in within 14d): _TBD_
- Outcome (talent stage = `Resigned` within 90d of `high` fire): _TBD_  ← the failure case
- Last tuned: never

## Examples

### Example 1 — Marcus Wells @ Acrisure
- **Evidence:** Chorus check-in 2026-05-10. Marcus: *"I'm running on fumes; the dental side workload tripled this month."* Skill 01 extracts: `type=burnout`, `speaker_role=talent_self`, `severity_hint=medium`, indicators=["exhaustion mention", "workload spike"].
- **Signal fires at:** `medium` (self-report).
- **Action proposed:** Skill 04 (talent-care) — checkin email + suggested 1:1; Skill 09 evaluates whether coaching handoff is appropriate.

### Example 2 — Aisha Patel @ Pinnacle (Enterprise)
- **Evidence:** RM_Outreach 2026-05-15 — RM noted "Aisha seems stretched; missed two 1:1s." `speaker_role=rm_observation`. `severity_hint=low`.
- **Signal fires at:** `low` (Enterprise sensitivity bumps to `medium`).
- **Action proposed:** Skill 04 talent check-in + cc Talent Dev (Enterprise variant).

## Open questions

- **Q136:** Talent welfare signal taxonomy completeness. Phase 1 covers burnout, growth concern, pay concern, AI-displacement (the user's example list). Are there other categories EDGE wants surfaced? Filed for week-1 review with VP-CS.
