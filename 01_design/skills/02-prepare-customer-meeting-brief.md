# Skill 02 — prepare-customer-meeting-brief

**Lifecycle stage:** operations
**Phase:** 1
**Tier-aware:** yes — Enterprise briefs are longer and include stakeholder org-chart context; SMB briefs are tight.

## Trigger
**Schedule-driven (24h ahead of meeting) + RM-initiated.** Fires when:
1. Calendar adapter ingests a `calendar.upcoming-customer-meeting` Episode that resolves to a known Customer (24h before start time per §13.3 Workflow 2), OR
2. An RM types a Pulse query like *"prep me for my Pinnacle meeting at 2pm"* (RM-initiated).

EBRs follow this same skill (no separate `ebr-prep` skill in Phase 1; see Design 05).

## Inputs
- Retrievers required: `get_customer_context(customer_id, as_of=now)`; if any specific talent or contact is named, also `get_talent_context()`.
- External calls (READ ONLY): Salesforce — current `RM_Outreach__c` state, `Account_Plan__c` if it exists, recent `Opportunity` rows.
- Per-Profile Markdown read: the Customer profile (Design 06).
- Policy inputs: tier (drives brief length/depth).

## Behavior
Produces a structured brief (the action card's `recommended_action.body`) that the RM walks into the meeting with. Lifts the prompt structure from `rm-intelligence-agent/src/generate_narratives.py` but reshapes the output for a **forward-looking** brief rather than a CEO retrospective narrative.

Brief structure:
- **Headline** (2 sentences). What's true now, what the RM should focus on.
- **Top 3 issues at this customer** (talent-side + customer-side mixed). Each cites the source Episode.
- **At-risk talent** (placed Associates with `Risk_level__c >= Medium` or recent risk-tagged Cases). Phase 1: read directly from SFDC, paired with any concern signals from Skill 01.
- **Positive performers** (placed Associates with no risks + positive Chorus mentions). Counter-balance for tone.
- **Talking points** (3 bullets the RM can raise). Inline-tag voice for direct quotes.
- **Recent activity recap** (last 30 days, condensed).

**Reasoning structure:**
```
[skill: prepare-customer-meeting-brief]
[context: Customer=<name>, meeting_at=<ts>, tier=<class>]

Signals consulted:
  - <num>N</num> RM_Outreach__c records last 90 days
  - <num>M</num> Chorus episodes last 90 days
  - <num>K</num> at-risk talent at this customer
  - <num>J</num> risk-tagged Cases open

Reasoning:
  [Synthesize current health + outstanding issues + recent signals
   into a forward-looking brief for the RM's meeting. Cite verbatim
   client quotes where they exist. Flag any acute issues.]

Proposed action: brief delivered as an Action Queue card with the
                 structured payload above.
```

## Guardrails
- **No invented facts.** Every bullet cites a source Episode or SFDC record. If the source is sparse, the brief is short — better than confabulated.
- **No competitor speculation.** Only mention competitors if a verbatim quote or risk-tagged Case names them.
- **Talent privacy in customer-facing surface.** The brief is *for the RM*, not for the customer. RM can share fragments; the skill does not draft customer-facing content here. Customer-facing emails are a separate skill output (typically `03-renewal-watcher` or `06-advocacy`).
- **Recency cap.** Default 90-day window for signal aggregation; EBRs widen to 180.

## Output / Proposed action shape
`ActionPayload`:
```yaml
action_type: meeting-brief
delivery_channel: action_queue + email_to_rm
body:
  headline: <2-sentence summary>
  top_issues: [..., ..., ...]      # 3 items, each with source citation
  at_risk_talent: [{name, role, risk_summary, source}, ...]
  positive_performers: [{name, role, highlight, source}, ...]
  talking_points: [..., ..., ...]
  recent_activity: <condensed paragraph>
  meeting_meta: {customer, attendees, time, agenda_hint}
modifiable_fields: [body.top_issues, body.talking_points]  # RM can tighten/edit before send
```

**Delivery:** Action Queue card (primary). Optional: also emailed to the RM's inbox 4h before meeting if `urgency >= medium`. No Slack delivery v1 (`feedback_dont_flood_slack`).

## Tier variants
| Tier | Variant |
|---|---|
| **SMB** | Brief capped at ~400 words; no Opportunity pipeline depth; default delivery = Action Queue only |
| **Mid-Market** | Standard brief (~700 words); Opportunity pipeline summary included |
| **Enterprise** | Extended brief (~1000 words); includes stakeholder org-chart context from Per-Profile Markdown Layer; Account Plan summary required |

Approval mode per Design 03: Enterprise = human-approval-required regardless; SMB = auto-approve at +30min for delivery; Mid = human-approval-required.

## Outcome detection
Outcome signal: the RM's *next* Chorus call with that customer happens within 7 days, and the brief's talking points appear in the call (LLM compares post-call summary to brief). If yes, `outcome-recorded` with type `brief-utilized`. If no, `outcome-missing`.

## EDGE Coverage
- §13.3 Workflow 2 — **entire row table**. This is the direct implementation of EDGE Workflow 2.
- §13.4 example "Prep me for my Pinnacle meeting" — RM-initiated trigger path.
- §13.5 row "Conduct EBRs" — same skill, schedule-driven on EBR-tagged meetings.
- §13.5 row "Trust-based stakeholder relationships" — stakeholder org-chart context (Per-Profile Markdown).

## Open questions
- **Q53** — RM-initiated trigger UX. A small query box on the dashboard ("ask Pulse anything about your book") is the natural surface, but §6 rule 17 says "the hero is the action queue, not the chat box." PM proposes: keep the query box deliberately small and secondary. User to confirm.
- **Q54** — Calendar attendee → Customer resolution failure mode. If the calendar event's attendee emails don't resolve to a known SFDC Customer (e.g., new prospect on the calendar), what does the skill do? PM proposes: emit a low-urgency "unknown attendee" notification rather than a brief.
- **Q55** — EBR detection. Phase 1 detects EBRs via `EBR_Date__c` on `RM_Outreach__c`. What if the EBR is on the calendar but not yet in SFDC? PM proposes: title-keyword detection ("EBR", "QBR", "quarterly review") as a fallback.

## Owned signals (Phase 3 cross-reference)

Skill 02 is a **consumer-only skill** — it does not own any single signal definition. Instead, it consumes the *full* signal state of a customer at brief-generation time:

| Signal ID | How Skill 02 uses it |
|---|---|
| `churn_signal_contact_disengagement_v1` | If fires, brief's "top issues" includes contact-disengagement context |
| `churn_signal_sentiment_decline_v1` | Trajectory data feeds the brief's "current shape" paragraph |
| `churn_signal_renewal_period_silence_v1` | If fires AND renewal proximate, brief leads with renewal context |
| `churn_signal_competitor_mention_v1` | If recent, brief includes "competitor watch" talking point |
| `expansion_signal_verbal_capacity_mention_v1` | If recent, brief includes "expansion opportunity" talking point |
| `expansion_signal_job_posting_match_v1` | Hot opportunity-tracker matches → "anchor moment" in the brief |
| `talent_burnout_signal_v1`, `talent_growth_concern_v1`, `talent_pay_concern_v1` | Talent-side context section of the brief |
| `escalation_signal_case_pattern_v1`, `escalation_signal_severity_jump_v1` | If active, brief flags "open escalations" as discussion items |
| `recognition_signal_advocacy_candidate_v1` | If fires, brief includes "moments of strength" celebration |
| `client_termination_pattern_v1` | Account-context — informs brief's churn-trajectory framing |
| `account_silence_pattern_v1` | Account-context — informs brief's freshness disclaimers ("most recent signal is N days old") |

Skill 02 does not have golden-trace tests for *signal detection* — those tests live with each signal definition. Skill 02's own golden-trace tests verify that, given a synthetic signal state, the resulting brief has the right structure, citations, and tone.
