# Skill 09 — coaching-signal-router

**Lifecycle stage:** escalation (talent coaching path; complements `04-talent-care`)
**Phase:** 1
**Tier-aware:** partial — same logic; Enterprise notifies a senior coach.

## Trigger
**Episode-driven.** Fires on:
1. A Skill 01 signal of talent welfare type (`burnout`, `growth concerns`, `AI-displacement`, `pay concerns`, `work-quality stress`) above medium severity.
2. A risk-tagged `Case` with `Categories__c = 'Performance'` or `'Risk - Talent Competency'` being created (`05-escalation-router` also fires; this skill is the *coaching* complement to that *routing* skill).
3. A talent quarterly check-in (Skill 04) surfacing a coaching-relevant theme in the outcome.

## Inputs
- Retrievers required: `get_talent_context()`.
- External calls (READ ONLY): Salesforce — full Associates record, related Cases.
- Per-Profile Markdown read: Associate profile.
- Policy inputs: tier of placed-at customer.

## Behavior
Routes the talent's coaching opportunity to **Talent Dev** (EDGE's internal talent development function) with a structured handoff packet. The packet contains:
- The triggering signal(s) with verbatim quotes where available.
- The talent's role, tenure at customer, and any historical coaching notes from the profile.
- A suggested coaching focus (e.g., "AI tooling adoption", "audit-process competency", "career pathing conversation").
- A proposed timeline (e.g., "within 2 weeks").

Distinguishes from Skill 05 (`escalation-router`): Skill 05 routes **issues to be resolved** (the talent has a problem to fix); Skill 09 routes **growth opportunities to be nurtured** (the talent has a developmental need). Both may fire on the same Case if the situation is dual-flavored, and that's fine — they propose different actions.

**Reasoning** highlights the developmental angle (not the deficit angle). Tone matters: this is not an escalation but a coaching handoff.

## Guardrails
- **Do not propose coaching for `Stage = Replaced` or `Terminated` talent.** Those have transitioned out of placement.
- **Do not loop with Skill 05.** A shared "this case already has an active proposed action" check (`case_id`-keyed) prevents two skills from generating overlapping action cards.
- **No customer-facing artifact.** Coaching is internal-only (talent ↔ Talent Dev ↔ RM).
- **Privacy posture:** pay-concern signals are sensitive. The action card mentions "pay concern raised in a check-in" but does not quote specific dollar figures even if the talent named them.

## Output / Proposed action shape
```yaml
action_type: coaching-handoff
delivery_channel: email + sfdc_task
body:
  email_draft:
    to: <talent_dev_team_alias>
    cc: <rm_email, associate_manager_email>
    subject: "Coaching opportunity: <talent_name>"
    body: <packet content, inline-tag-rendered>
  sfdc_task:
    subject: "Coaching handoff: <talent_name>"
    description: <full packet for SFDC record>
    related_to: <Associates__c.Id>
    assigned_to: <talent_dev_lead_user_id>
    due_date: <2 weeks>
modifiable_fields: [body.email_draft.body, body.sfdc_task.description,
                     body.sfdc_task.due_date]
```

## Tier variants
| Tier | Variant |
|---|---|
| **SMB** | Default routing to general Talent Dev queue |
| **Mid** | Same; possible escalation if the talent is high-impact (signal: customer ARR > threshold) |
| **Enterprise** | Route to senior coach; suggested 1-week timeline rather than 2 |

Approval mode: human-required (coaching is high-touch and tone-sensitive).

## Outcome detection
- New Chorus or `RM_Outreach__c` episode within 30 days showing a coaching conversation happened → `outcome-recorded` type `coaching-engaged`.
- No movement after 30 days → `outcome-missing` and re-queue.

## EDGE Coverage
- §13.5 row "Coach Talent for long-term success" — direct implementation.
- §13.5 row "Support partner for Talent issues" — paired with Skill 04.

## Open questions
- **Q74** — Talent Dev team structure. Does EDGE have named coaches, or a generic queue? Affects routing precision.
- **Q75** — Career-pathing data shape. Does the Associates record have a "career goals" field, or does it need to be captured in Per-Profile Markdown? PM proposes: Per-Profile Markdown.
- **Q76** — Skill 05 / Skill 09 deconfliction at trigger time. Both can fire on the same Case. PM proposes: shared rate-limit table keyed on (case_id, dispatch_week); see also Q67.

## Owned signals (Phase 3 cross-reference)

| Signal ID | Role |
|---|---|
| `talent_growth_concern_v1` | **Primary consumer.** The developmental-growth angle that distinguishes Skill 09 from Skill 04. |
| `talent_burnout_signal_v1` | **High-severity cascade consumer.** When burnout is severe enough to threaten retention, Skill 09 routes a coaching handoff alongside Skill 04's care touch. |
| `talent_pay_concern_v1` | **Read-only context.** Pay-concern signals route through Skill 05 to Finance; Skill 09 reads them as context but does not propose coaching for pay alone. |

Skill 09's golden-trace tests verify the **developmental-vs-deficit distinction** — given a synthetic Case + welfare-signal state, the resulting routing is to Talent Dev (coaching), Skill 05 (issue resolution), or both (with the shared rate-limit deduplicating).
