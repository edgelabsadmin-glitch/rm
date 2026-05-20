# churn_signal_contact_disengagement_v1

**Version:** v1
**Category:** churn
**Severity model:** tiered (low / medium / high)
**Owning skill(s):** Skill 03 (renewal-watcher), Skill 05 (escalation-router), Skill 10 (cross-account-pattern-finder)
**Status:** active

## Plain-English definition

The customer's primary contact has gone quiet. "Quiet" means: the contact has not replied to RM outreach in the last 14+ days, OR the contact has missed two or more scheduled meetings (no-shows or last-minute reschedules), OR no Chorus call has been hosted involving this contact in the last 21 days when they were active in the prior period. This is one of the earliest reliable churn signals — disengagement precedes formal churn by 30-90 days on average.

## Detection mechanism

**Type:** hybrid

**Rule layer (cheap pre-filter):**
```
For each Customer where Account.Status != 'Churned':
  primary_contact = identify_champion(Customer)   # most-recent Chorus participant or RM-tagged champion
  days_since_last_reply = today - max(
    email_replies.received_at where contact = primary_contact,
    sfdc.activity.last_modified where activity_type IN ('Reply','Inbound'),
  )
  ebr_no_shows_last_60d = count(
    Calendar.events where attendees contains primary_contact
                       AND meeting_status IN ('no_show','last_minute_reschedule')
                       AND date >= today - 60
  )
  chorus_call_count_21d = count(
    Chorus.engagements where participants contains primary_contact
                            AND completed_at >= today - 21
  )
  chorus_call_count_prior_21d = count(
    Chorus.engagements where participants contains primary_contact
                            AND completed_at BETWEEN today - 42 AND today - 21
  )

  fire_rule_a = days_since_last_reply >= 14
  fire_rule_b = ebr_no_shows_last_60d >= 2
  fire_rule_c = chorus_call_count_21d == 0 AND chorus_call_count_prior_21d > 0

  if fire_rule_a OR fire_rule_b OR fire_rule_c:
    forward to LLM ambiguity-resolution layer
```

**LLM ambiguity-resolution prompt** (run when rule fires; resolves false-positive PTO / vacation cases):

```
You are evaluating whether a contact disengagement signal at <Customer> is genuine
or whether known context (PTO, parental leave, role change, vacation) explains
the silence.

Inputs:
  - Customer Per-Profile Markdown (Design 06) — read the "Open threads" and
    "Communication preferences" sections especially
  - Most recent 5 RM_Outreach__c records (last 90 days) — look for stated reasons
  - Account_Plan__c Open Threads section if present

Output JSON:
{
  "severity": "low" | "medium" | "high",
  "is_explained": true | false,
  "explanation": "<one sentence — e.g. 'Sarah is on parental leave per RM_Outreach 2026-05-01; not a disengagement signal'>",
  "evidence_quoted": ["<verbatim quote 1>", "<verbatim quote 2>"]
}

If is_explained=true, the signal does NOT fire downstream.
If is_explained=false, the signal fires with the assigned severity.
```

## Evidence shape

| Source | Field(s) | Time window |
|---|---|---|
| Chorus episodes | `participants`, `completed_at`, `meeting_outcome` | last 60 days |
| Calendar episodes | `attendees`, `meeting_status`, `date` | last 60 days |
| SFDC `RM_Outreach__c` | `LastModifiedDate`, `Description__c`, `Communication_Channel__c` | last 90 days |
| Email / Gmail (where wired) | replies received from primary_contact | last 30 days |
| Per-Profile Markdown (Customer) | "Open threads" + "Communication preferences" sections | current |
| Account_Plan__c | "Open Threads" section if present | current |

## Triggering threshold

**Fire if ANY of:**
- `days_since_last_reply >= 14` (the user-stated example)
- `ebr_no_shows_last_60d >= 2`
- `chorus_call_count_21d == 0 AND chorus_call_count_prior_21d > 0` (active → silent inflection)

**AND the LLM resolves `is_explained = false`.**

Severity:
- `low` if exactly one rule fires AND the customer is not in a renewal window (<90 days to renewal)
- `medium` if two rules fire, OR one rule fires AND the customer is in a renewal window
- `high` if all three rules fire, OR two rules fire AND the customer is in a renewal window <30 days

## Tier-aware variants

| Account tier | Variant |
|---|---|
| **SMB** | `silence_days=21` (less aggressive — SMB contacts naturally communicate less). Auto-approve recommended check-in actions at +2h. |
| **Mid-Market** | `silence_days=14` (the baseline). Human-required for resulting check-in. |
| **Enterprise** | `silence_days=10` AND ebr_no_show_threshold drops to 1. Human-required + cc VP-CS on resulting action. |

## False-positive failure modes

- **PTO / parental leave / personal emergency.** The contact is genuinely away, not disengaged. Mitigation: LLM resolver checks Per-Profile Markdown "Open threads" + recent RM_Outreach for stated absence reasons.
- **Channel shift.** The contact moved from email to Slack or WhatsApp (not yet integrated). Mitigation: low-confidence resolution; the LLM can flag this case as `is_explained=true` with explanation "channel shift suspected — verify via RM."
- **Champion changed.** The original champion left the company; the new champion hasn't been re-tagged in Pulse. Mitigation: cross-check `Contact.IsActive` and `LastModifiedDate` of the champion's record; if recently inactive, re-evaluate champion identification.
- **Re-org silence.** Customer is in a re-org and "silent" is the new normal across all vendors. Mitigation: cross-account check — if multiple customers in the same parent org are silent, downgrade individual severity (parent-org context).

## False-negative failure modes

- **Pretend engagement.** Customer replies once per week with single-sentence non-answers ("got it", "looks good") that mimic engagement but indicate disengagement-by-politeness. v1.5+ enhancement: sentiment + response-length composite metric.
- **In-person-only customers.** A few EDGE customers prefer in-person meetings, not Chorus calls. Phase 1 doesn't see this. v1.5+ Zoom adapter + on-site visit log integration would catch it.
- **Slack-native customers.** Customer communicates primarily in Slack DMs. Phase 1 Slack-as-input is out per `feedback_dont_flood_slack`. v1.5+ Slack adapter.

## Adjustability

| Parameter | Type | Default | Who can adjust | Effect of increasing |
|---|---|---|---|---|
| `silence_days` (Mid-Market baseline) | int | 14 | Admin via policy module | Fewer false-positives, slower churn-risk detection |
| `ebr_no_show_threshold` | int | 2 | Admin | Tighter precision, lower recall |
| `chorus_active_window` | int days | 21 | Admin | Catches more "subtle disengagement" cases at higher false-positive cost |
| Renewal-window-multiplier (severity-amplifier) | float | 1.5x | Admin | Renewals get earlier alerts |

## Performance metrics (populated by Layer 8 Mechanism 1)

- Fire rate (instances/day per RM): _TBD post-launch_
- Action-approval rate when this signal contributes: _TBD_
- Outcome-recorded rate among approved actions: _TBD_
- Apparent false-positive rate (rejections coded as "wrong signal"): _TBD_
- Last tuned: never

## Examples

### Example 1 — Acrisure (Mid-Market)
- **Evidence:** Sarah Chen has not replied to RM email since 2026-04-30 (21 days). One Chorus call in the prior 21-day window (2026-04-12 EBR); zero Chorus calls in the last 21 days. No no-shows.
- **Signal fires at:** `medium` (two rules: silence_days, chorus active→silent inflection; not in renewal window <90)
- **Action proposed:** Skill 03 (renewal-watcher) drafts a check-in email referencing the April EBR's open items.

### Example 2 — Pinnacle (Enterprise)
- **Evidence:** Primary champion (CEO) hasn't replied in 12 days (>10 day Enterprise threshold). Hosted weekly Chorus calls until 3 weeks ago; none since.
- **Signal fires at:** `high` (Enterprise variant — both rules; cc VP-CS triggers)
- **Action proposed:** Skill 03 + Skill 05 (escalation-router) — drafted check-in to CEO + Salesforce Task to VP-CS for awareness.

### Example 3 — Mendota (SMB) — does NOT fire
- **Evidence:** 16 days since last reply (>14 baseline but <21 SMB threshold). No no-shows. Active Chorus calls in last 21 days.
- **Signal does not fire** at SMB threshold.

## Open questions

- **Q126:** Champion identification heuristic (cross-references Q56/Q65). Phase 1 fallback = most-recent Chorus customer-side participant. Need to confirm this works in practice; may surface as a tuning need in Layer 8 metrics.
- **Q127:** Email-reply ingestion mechanism. Pulse's adapter list (Design 02) covers Chorus, SFDC, Calendar, opportunity-tracker. Email-reply detection requires either Gmail/Outlook OAuth (Skill 03's outcome detection covers this) or scraping SFDC `Activity` records. PM proposes: SFDC `Activity` is sufficient for Phase 1 (the RM logs replies in CRM); pure-email-reply parsing is v1.5+.
