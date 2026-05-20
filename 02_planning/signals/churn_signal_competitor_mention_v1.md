# churn_signal_competitor_mention_v1

**Version:** v1
**Category:** churn
**Severity model:** tiered (low / medium / high)
**Owning skill(s):** Skill 01 (detect-talent-signal — emits as a `competitor_mention` tag); Skill 05 (escalation-router); Skill 10 (cross-account-pattern-finder — for cross-account competitor patterns)
**Status:** active

## Plain-English definition

A competitor was named in a Chorus call, an RM_Outreach note, a risk-tagged Case description, or any other ingested episode about this customer. Competitor mentions vary in weight: a casual reference is `low`; "we're evaluating them" is `medium`; "they offered us a better rate" is `high`. The risk-tagged Case category `Competitor` (existing EDGE taxonomy from `rm-intelligence-agent/src/sfdc_pull.py`) is the strongest single signal — case existence alone fires `high`.

## Detection mechanism

**Type:** hybrid (rule for the Case-category trigger; LLM for free-text mentions)

**Rule layer (fast Case-based trigger):**
```
For each Customer:
  competitor_cases_90d = count(
    sfdc.Case where AccountId = Customer
                AND Categories__c = 'Competitor'
                AND CreatedDate >= today - 90
  )
  if competitor_cases_90d >= 1:
    fire(severity='high', evidence=case_record)
```

**LLM layer (free-text scan, runs episode-driven via Skill 01 during ingestion):**

Skill 01's extraction prompt already includes "competitor mentions" as a signal type. The output of Skill 01 includes:
```json
{
  "competitor_mentions": [
    {
      "competitor_name": "<name>",
      "context": "<verbatim quote>",
      "tone": "casual" | "evaluating" | "active_compare" | "switching_intent"
    }
  ]
}
```

This signal then fires when ANY `competitor_mention` exists in the last 90 days of episodes for the customer:

```
For each Customer:
  competitor_mentions_90d = retrieve(
    Graphiti.episodes where mentions(Customer)
                       AND has(signal='competitor_mention')
                       AND date >= today - 90
  )
  if not competitor_mentions_90d:
    return None

  max_tone = max(m['tone'] for m in competitor_mentions_90d)
  severity = {
    'casual':         'low',
    'evaluating':     'medium',
    'active_compare': 'medium',
    'switching_intent': 'high',
  }[max_tone]

  # Escalate severity if multiple distinct mentions
  if len(competitor_mentions_90d) >= 3 AND severity == 'low':
    severity = 'medium'

  fire(severity)
```

## Evidence shape

| Source | Field(s) | Time window |
|---|---|---|
| SFDC `Case` | `Categories__c = 'Competitor'`, `Description`, `Details__c` | last 90 days |
| Chorus episodes | `content.summary`, `content.action_items` (parsed by Skill 01 → `competitor_mention` signal) | last 90 days |
| Graphiti `mentions` edges | source episode, `competitor_name`, `tone`, `context` | last 90 days |
| SFDC `RM_Outreach__c` | `Competitor_Analysis__c` field (existing) | most recent |

## Triggering threshold

**Fire if EITHER:**
- One or more risk-tagged Case with `Categories__c = 'Competitor'` in last 90 days → `high` severity always.
- One or more `competitor_mention` signals extracted by Skill 01 from any episode in last 90 days → severity derived from the strongest `tone`.

**Severity ladder (LLM-derived tone):**
- `casual` mention ("they have a similar product") → `low`
- `evaluating` ("we're evaluating them") → `medium`
- `active_compare` ("they sent us a pitch", "we ran a side-by-side") → `medium`
- `switching_intent` ("they offered us a better rate", "we may switch") → `high`

## Tier-aware variants

| Account tier | Variant |
|---|---|
| **SMB** | Same severity ladder; resulting action defaults to auto-approve at +2h for `low`. |
| **Mid-Market** | Baseline. Human-required at all severities. |
| **Enterprise** | Severity floor raised by one tier (`casual` → `medium`; `evaluating` → `high`). cc VP-CS always. The downside of Enterprise customer-loss is large enough that any competitor whiff warrants escalation. |

## False-positive failure modes

- **Competitor named as a partner.** "We use [competitor] for their dental network, not their placements." The competitor is not actually a competitor in this context. Mitigation: Skill 01's prompt distinguishes context; the `tone` value carries this nuance.
- **Competitor named as a benchmark.** "Their pricing is reasonable for what they do; we'd like that here." Customer is using the competitor as a benchmark, not threatening to switch. Mitigation: `tone=casual` captures this; resulting severity is `low`.
- **Competitor named historically.** "We worked with [competitor] before Edge." Past tense — no current risk. Mitigation: Skill 01's prompt includes temporal-tense detection.

## False-negative failure modes

- **Indirect references.** "We're shopping around" without naming a specific competitor. v1.5+ enhancement: extend Skill 01 prompt to detect generic competitive intent.
- **Competitor named in non-ingested channels.** Slack, internal email, PIN-only RM_Outreach private notes. Phase 1 boundary.
- **Encrypted / private-channel discussion.** Out of scope by definition.

## Adjustability

| Parameter | Type | Default | Who can adjust | Effect |
|---|---|---|---|---|
| `case_severity_floor` | enum | `high` | Admin | Lowering disables auto-high; risky |
| `tone_ladder` mapping | dict | per above | Admin | Per-tone severity remapping |
| `escalate_multiple_mentions` | int | 3 | Admin | Adjust burst-detection threshold |
| EDGE competitor watch-list | list | (admin-curated) | Admin | Pre-populated list of known competitors — Skill 01 weights matches against it |

## Performance metrics (populated by Layer 8 Mechanism 1)

- Fire rate: _TBD_
- Action-approval rate: _TBD_
- Outcome (renewal closed-won) within 90d of fire: _TBD_  ← the key counter-signal
- False-positive code rate from RM rejections: _TBD_
- Last tuned: never

## Examples

### Example 1 — Acrisure
- **Evidence:** Chorus call 2026-05-08 — Sarah Chen said *"Our CFO is mandating we cut vendor count by 20% this year; we'll need to compare you against [Competitor X] and [Competitor Y]."* Skill 01 extracted `competitor_mention` with `tone=evaluating` for both.
- **Signal fires at:** `medium` (Mid-Market; tone=evaluating; 2 mentions doesn't trigger burst).
- **Action proposed:** Skill 03 (renewal-watcher) — drafted retention email + Skill 05 escalation to VP-CS for awareness.

### Example 2 — Helix Labs
- **Evidence:** Case opened 2026-05-15 — `Categories__c='Competitor'`, Description references active poaching of placed talent.
- **Signal fires at:** `high` (case-category rule trumps tone).
- **Action proposed:** Skill 05 (escalation-router) — immediate VP-CS + Sales lead notification.

### Example 3 — Vertex Group — does NOT fire
- **Evidence:** Last 90 days of episodes contain zero competitor mentions; no Competitor-category Cases.
- **Signal does not fire.**

## Open questions

- **Q132:** Competitor watch-list. Should EDGE pre-populate a list of known competitors (and have Skill 01 weight those matches more heavily)? PM proposes yes; list maintained by Admin in policy config. User to confirm.
- **Q133:** Past-tense detection robustness. Skill 01's prompt should handle "we used [competitor] before Edge" as non-firing. Add to Skill 01's golden-trace tests (per §6 rule 10).
