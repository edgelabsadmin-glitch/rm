# expansion_signal_verbal_capacity_mention_v1

**Version:** v1
**Category:** expansion
**Severity model:** tiered (low / medium / high)
**Owning skill(s):** Skill 01 (detect-talent-signal — emits the underlying `expansion_signal` tag); Skill 06 (advocacy — high-tier asks); Skill 11 (cross-walks with job-posting matches)
**Status:** active

## Plain-English definition

The customer verbally mentioned growth, hiring, or capacity needs during a Chorus call, an RM_Outreach note, or any ingested episode. The signal captures the *intent* before any external evidence (a posted job, an RFP) surfaces — it's the leading edge of expansion. Strongest when phrased as a direct ask ("can you give us a proposal for 5 more medical scribes?") and weakest when general ("we're growing").

## Detection mechanism

**Type:** LLM-based (extracted by Skill 01 during episode ingestion)

Skill 01's extraction prompt produces:
```json
{
  "expansion_mentions": [
    {
      "role_or_category": "<e.g. Medical Scribe>",
      "quantity_mentioned": "<e.g. 3-5>" | null,
      "context": "<verbatim quote>",
      "directness": "general" | "exploratory" | "direct_ask" | "active_negotiation"
    }
  ]
}
```

This signal fires when any `expansion_mention` exists in the last 60 days of episodes for the customer:

```
For each Customer:
  mentions_60d = retrieve(Graphiti.episodes
                            where mentions(Customer)
                            AND has(signal='expansion_mention')
                            AND date >= today - 60)
  if not mentions_60d:
    return None

  max_directness = max(m['directness'] for m in mentions_60d)
  severity = {
    'general':            'low',
    'exploratory':        'low',
    'direct_ask':         'medium',
    'active_negotiation': 'high',
  }[max_directness]

  # Escalate if quantity_mentioned is concrete (named number/range)
  if any(m['quantity_mentioned'] for m in mentions_60d) and severity == 'low':
    severity = 'medium'

  fire(severity)
```

## Evidence shape

| Source | Field(s) | Time window |
|---|---|---|
| Chorus episodes | `content.summary`, `content.action_items`, transcript (where ingested) | last 60 days |
| SFDC `RM_Outreach__c` | `Expansion_Sentiment__c`, `Expansion_Probability__c`, `Description__c` | most recent |
| Graphiti `mentions` edges with `signal=expansion_mention` | source episode, context, directness | last 60 days |

## Triggering threshold

Fire when any `expansion_mention` exists. Severity per directness ladder above. Quantity-mention bumps low → medium.

## Tier-aware variants

| Account tier | Variant |
|---|---|
| **SMB** | Same ladder; auto-approve at +2h for `low` and `medium`. |
| **Mid-Market** | Baseline. Human-required at all severities. |
| **Enterprise** | Severity floor raised by one tier (`general` → `medium`; `direct_ask` → `high`). cc Sales lead always; suggested EBR-tie-in copy attached at `high`. |

## False-positive failure modes

- **Wishful customer hypothesizing.** "If we ever expand to dental coding…" — speculative, not actual. Mitigation: Skill 01 prompt's `directness=general` captures this; severity stays `low`.
- **Customer mentions hiring for a role EDGE doesn't staff.** "We're hiring 3 software engineers" — irrelevant. Mitigation: cross-reference with EDGE role catalog; Skill 01 prompt instructs to set `role_or_category=null` for non-catalog roles, which suppresses fire.
- **Hiring at parent company, not this account.** "Our parent posted some roles" — wrong granularity. Mitigation: LLM prompt asks for the *account* doing the hiring.

## False-negative failure modes

- **Customer hires in non-call channels.** Email-only customers, Slack-only customers (Phase 1 boundary).
- **Customer posts the job without verbalizing first.** This signal misses it; `expansion_signal_job_posting_match_v1` (sibling signal) catches it via opportunity-tracker. The two signals are complementary by design.

## Adjustability

| Parameter | Type | Default | Who | Effect |
|---|---|---|---|---|
| `directness_ladder` map | dict | per above | Admin | Per-directness severity remap |
| `quantity_mention_bumps_severity` | bool | True | Admin | Off = treat all general mentions as low |
| Lookback window | int days | 60 | Admin | Wider catches slower-burn signals |

## Performance metrics (populated by Layer 8 Mechanism 1)

- Fire rate: _TBD_
- Action-approval rate: _TBD_
- Outcome (Opportunity created / amount-amount-added) within 60d: _TBD_  ← key Layer 8 outcome
- Last tuned: never

## Examples

### Example 1 — Pinnacle
- **Evidence:** Chorus call 2026-05-08 — Maria Lopez (CEO): *"The medical coding team you placed has been exceptional. We're thinking about expanding into insurance coding next quarter — can you give us a proposal for 3-5 insurance coders?"* Skill 01 extracts: `role='Insurance Coder'`, `quantity='3-5'`, `directness='direct_ask'`.
- **Signal fires at:** `medium` (direct_ask + quantity).
- **Action proposed:** Skill 06 (advocacy) drafts a proposal-prep email to RM with the verbatim quote + cross-references EDGE Insurance Coder catalog entry.

### Example 2 — Acrisure
- **Evidence:** RM_Outreach 2026-05-12 — `Expansion_Sentiment__c='Strong'`. Chorus call mentions: *"We're growing in the dental side; talent ramp-up has been slower than insurance"* — `directness='general'`, no quantity.
- **Signal fires at:** `low`.
- **Action proposed:** Skill 06 — soft outreach in Pulse-suggested cadence (not a heavy ask).

### Example 3 — Mendota — does NOT fire
- **Evidence:** No expansion mentions in last 60d.

## Open questions

- **Q134:** Cross-reference with `expansion_signal_job_posting_match_v1`. When both signals fire on the same Customer in the same window, do they compose into one action proposal or two? PM proposes: one (the job-posting match strengthens the verbal mention). Skill 11 detection logic handles this composition.
