# Skill 04 — talent-care

**Lifecycle stage:** escalation (talent welfare; quarterly cadence)
**Phase:** 1
**Tier-aware:** partial — cadence is the same, but Enterprise placements include an extra "stakeholder sync" prompt.

## Trigger
**Schedule-driven (hourly).** Scans all `Associates__c` records in `Stage = Active` and finds those whose last check-in is **overdue against cadence**. Phase 1 cadence rule: **quarterly (90-day) per JD ("Quarterly check-ins, no slippage")**.

Last-check-in source (priority order):
1. Most recent `RM_Outreach__c` record where `Associate__c = <talent_id>`.
2. Most recent Chorus call where the talent or their RM Manager was a participant.
3. Fallback: 90 days since `Associates__c.LastModifiedDate`.

A talent is **overdue** if last check-in > 90 days ago, OR > 75 days ago AND the talent is at a Mid/Enterprise customer.

## Inputs
- Retrievers required: `get_talent_context(talent_id)`.
- External calls (READ ONLY): Salesforce — `Associates__c`, `RM_Outreach__c`, `User` (for RM ownership).
- Per-Profile Markdown read: Associate profile (Design 06).
- Policy inputs: tier of the placed-at customer.

## Behavior
For each overdue talent, propose a check-in action:
1. A draft message to the talent (email if email is the canonical channel; Slack DM is OUT for v1 per `feedback_dont_flood_slack`).
2. A Salesforce Task for the RM to call/meet the talent.

The message is **warm, low-pressure, and personalized** to the talent's profile — Per-Profile Markdown context is load-bearing here. Example anchor lines: *"It's been a couple months — wanted to check in on how the audit ramp is going at Acrisure"*.

**Reasoning** captures signal context: any recent risk-tagged Case on this talent (Design 01 `escalated_via` edge), any recent concern signals from Skill 01 (`raised_concern_about` edges), and the placement context (role, customer tier, time since placement).

## Guardrails
- **Do not mention customer-side concerns to the talent unless explicitly safe** (e.g., never tell a placed Associate that their customer is at churn risk — that's an RM judgment to convey verbally, not an email to draft).
- **Do not propose check-in actions for talent in `Replaced` or `Terminated` stage.** Those are different lifecycle paths (Skill 09 `coaching-signal-router` may catch the coaching aspect).
- **Avoid generic templates.** If the Per-Profile Markdown is empty or stale, the skill emits a "RM check-in needed; profile sparse" card rather than a templated email.
- **Do not propose more than one talent-care action per Talent per 30 days.** Rate-limit to prevent alert fatigue.

## Output / Proposed action shape
```yaml
action_type: talent-checkin
delivery_channel: email + sfdc_task
body:
  email_draft:
    to: <talent_email>
    subject: "Quick check-in"
    body: <personalized draft, inline-tag-rendered>
  sfdc_task:
    subject: "Talent check-in: <talent_name>"
    description: <last-check-in date + any signals worth raising>
    related_to: <Associates__c.Id>
    due_date: <5_business_days>
modifiable_fields: [body.email_draft.body, body.email_draft.subject,
                     body.sfdc_task.description]
```

## Tier variants
| Tier (of placed-at customer) | Variant |
|---|---|
| **SMB** | Email-only; SFDC Task optional |
| **Mid** | Email + SFDC Task |
| **Enterprise** | Email + SFDC Task + suggested 30-min Zoom hold on RM's calendar |

Approval mode: auto-approve at +1h for SMB and Mid (low blast radius); Enterprise = human-required.

## Outcome detection
- Talent reply received within 14 days → `outcome-recorded` type `talent-engaged`.
- New `RM_Outreach__c` record created within 30 days referencing this talent → `outcome-recorded` type `checkin-completed`.
- No movement after 30 days → `outcome-missing` (and Talent is re-queued for the next cycle).

## EDGE Coverage
- §13.5 row "Quarterly check-ins, no slippage" — direct implementation.
- §13.5 row "Support partner for Talent issues" — related; complements `05-escalation-router`.
- §13.5 row "Cohesive customer + Talent experience" — talent-side of the dual-sided experience.

## Open questions
- **Q59** — Cadence per role-type. Phase 1 = 90 days for all. v1.5+ may want shorter cadence for at-risk roles. Filed.
- **Q60** — Email channel ownership. Does Pulse send from the RM's mailbox (OAuth) or from a Pulse alias? PM proposes: from RM's mailbox via OAuth so replies land in the RM's inbox. Implementation detail for Phase 4.
- **Q61** — Talent contact email source. Is it on `Associates__c` directly, on a linked `Contact`, or elsewhere? Spike 1 follow-up.

## Owned signals (Phase 3 cross-reference)

| Signal ID | Role |
|---|---|
| `talent_burnout_signal_v1` | **Primary consumer.** Fires a talent-care check-in at the resolved severity. |
| `talent_growth_concern_v1` | **Co-consumer.** Triggers a check-in; coordinates with Skill 09 for coaching handoff at `medium+`. |
| `talent_pay_concern_v1` | **Co-consumer.** Triggers a check-in; Skill 05 cascades on `high` severity (competing-offer auto-elevation). |

Skill 04's golden-trace tests verify the **cadence rule** (90-day Phase 1 default; talent-care fires when last check-in > threshold AND welfare-signals fire concurrently OR independently) and the **rate-limit** (one talent-care action per Talent per 30 days).
