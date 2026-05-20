# Skill 08 — onboarding

**Lifecycle stage:** onboarding
**Phase:** 1
**Tier-aware:** yes — Enterprise onboarding includes more touch-points; SMB is condensed.

## Trigger
**Episode-driven.** Two distinct sub-triggers:
1. **New Customer onboarding** — a new `Account` is created in SFDC (Stage transitions to "Customer" / "Active" — exact stage value TBD via Spike 1).
2. **New Talent placement onboarding** — an `Associates__c` record transitions to `Stage = Active` for the first time at a Customer.

## Inputs
- Retrievers required: `get_customer_context()` or `get_talent_context()` depending on sub-trigger.
- External calls (READ ONLY): Salesforce — `Account`, `Contact` (decision-makers), `Associates__c`, role-catalog match.
- Per-Profile Markdown read: profile for the entity (may be sparse for net-new entities; that's expected).
- Policy inputs: tier of the customer.

## Behavior

### Sub-trigger 1: new Customer
Propose a **kickoff-call action**:
- Draft email to the customer's primary contact(s) proposing kickoff agenda.
- SFDC Task for the RM to send + follow up.
- Calendar hold suggestion (RM 60 min + customer time slot).

Kickoff agenda (Phase 1 default; tier-aware variants below):
- Introduce EDGE team
- Review placement plan / role catalog
- Confirm communication channels, cadence (quarterly check-ins per JD)
- Set 30/60/90-day success criteria

### Sub-trigger 2: new Talent placement
Propose a **placement-launch action**:
- Welcome email to the talent.
- SFDC Task for the Associate Manager to schedule a 1:1 in week 1.
- Heartbeat enqueue: 30/60/90-day check-ins scheduled (which feeds Skill 04 `talent-care` cadence).
- Recognition seed: talent's start date is logged for the 1-year milestone (Skill 07).

**Reasoning** is brief; onboarding is more procedural than analytical. The Per-Profile Markdown for a net-new entity will be sparse — the skill explicitly notes this and proposes that the RM populate the profile after the kickoff call.

## Guardrails
- **Fires once per entity.** A second `Stage = Active` transition on the same Associates record (e.g., after a temporary leave) does not re-trigger onboarding.
- **Does not draft contractual content.** No SOW language, no pricing, no commitments. Procedural and relationship-building only.
- **Calendar hold suggestion is a proposal, not a unilateral booking.** RM approves the time slot before any calendar API call.
- **Cross-skill coordination:** if Skill 03 `renewal-watcher` is firing on the same Customer (rare on a brand-new customer; possible if Pulse activates mid-relationship), defer to renewal-watcher.

## Output / Proposed action shape

```yaml
action_type: onboarding
sub_type: <new-customer | new-talent>
delivery_channel: email + sfdc_task + calendar_hold_suggestion
body:
  email_draft:
    to: <champion_or_talent_email>
    cc: <relevant_contacts>
    subject: <kickoff-relevant>
    body: <agenda + warm intro, inline-tag-rendered>
  sfdc_task:
    subject: "<Customer/Talent> onboarding kickoff"
    description: <RM-facing checklist>
    related_to: <Account.Id or Associates__c.Id>
  calendar_hold:                       # not booked; just suggested
    suggested_times: [<ts>, <ts>, <ts>]
    duration_min: <60 for customer, 30 for talent>
modifiable_fields: [body.email_draft.body, body.email_draft.subject,
                     body.sfdc_task.description, body.calendar_hold.suggested_times]
```

## Tier variants
| Tier | Variant |
|---|---|
| **SMB** | Single email + SFDC Task; no calendar hold suggestion |
| **Mid** | Email + SFDC Task + calendar hold suggestion |
| **Enterprise** | Email + SFDC Task + calendar hold + cc VP of Client Success; agenda includes governance-cadence discussion |

Approval mode: human-required across tiers (onboarding is a first-impression surface).

## Outcome detection
- Kickoff call detected (Chorus episode within 30 days with relevant participants) → `outcome-recorded` type `onboarding-kickoff-completed`.
- Talent 1:1 episode within 14 days → `outcome-recorded` type `talent-onboarding-engaged`.
- No movement after 30 days → `outcome-missing` and escalate via Skill 05.

## EDGE Coverage
- §13.5 row "Kickoff calls with new customers" — direct implementation.
- §13.5 row "Coach Talent for long-term success" — placement onboarding seeds the coaching cadence.

## Open questions
- **Q71** — Stage values that count as "new customer." Spike 1 needed for exact Account stage enum.
- **Q72** — First-day-of-placement vs. first-day-of-contract. Phase 1 uses `Associates__c.Start_Date__c`; confirm this maps to actual placement start.
- **Q73** — Calendar hold mechanism. RMs use Google or Outlook? Adapter choice per Q33. Phase 1 = manual suggestion in the action card; auto-booking is v1.5+.

## Owned signals (Phase 3 cross-reference)

Skill 08 is **structural-event-driven** — it fires on SFDC stage transitions (new Account creation; first-time `Associates__c.Stage = 'Active'`), not on LLM-detected signals. The Phase 1 signal library does not include a dedicated `onboarding_trigger_v1` definition; the trigger conditions are documented in this skill spec's "Trigger" section.

This is acceptable under §6 rule 8 (no black-box detection) because **structural events are inherently inspectable** — the SFDC record's stage transition is the evidence. The standing rule applies to *detection mechanisms that could be opaque* (LLM-based, heuristic, multi-signal aggregations); structural triggers don't carry that risk.

**v1.5+ candidate:** consolidate Skill 08's structural triggers into a formal `onboarding_signal_new_customer_v1` / `onboarding_signal_new_placement_v1` pair for symmetry with the rest of the library. Filed in `99_open_questions.md` as Q147.
