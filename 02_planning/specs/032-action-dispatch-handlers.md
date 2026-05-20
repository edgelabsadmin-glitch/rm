# Spec 032 — Action dispatch handlers

**Maps to:** §14 (Email + SFDC + Calendar dispatch); Design 03 §"Approval flow" + §"After-action outcome capture"; §13.5 "Effective communication channels"; §6 rule 6 (SFDC write only via Action Queue).
**Depends on:** specs 008, 031, 043 (OAuth for RM mailbox sends).
**Effort:** 1.0 day.

## Description

Per-dispatch-type handlers triggered by `action-approved` / `action-modified-and-approved` events. Phase 1 channels: Email (Gmail / Outlook OAuth, sending from RM's mailbox per Q60); SFDC Task create (the canonical Pulse → SFDC write path per §6 rule 6); Calendar hold suggestion (Phase 1 = email with calendar link; auto-booking v1.5+).

## Inputs

- Approved action payloads.
- RM OAuth tokens for outbound email.

## Outputs

- `03_build/pulse/core/dispatch/email.py`, `sfdc_task.py`, `calendar_hold.py`.
- Per dispatch: `action-executed` event.
- Per failure: `dispatch-failed` event + retry-with-backoff schedule.

## Definition of Done

- [ ] Email handler sends from RM mailbox via OAuth (Q60); reply lands in RM inbox (not Pulse).
- [ ] SFDC Task handler uses `sf` CLI (per `reference_sfdc_access` memory); writes `OwnerId` = action's assigned RM/team-lead.
- [ ] Calendar hold handler emits the calendar invite as part of email (Phase 1 minimum).
- [ ] Retry semantics: 3 attempts exponential backoff; dead-letter to `dispatch_failed` table.
- [ ] No SFDC writes occur for un-approved actions (verified by unit test).
- [ ] Langfuse-traced.

## Tests

- **Unit:** mocked Gmail OAuth + mocked sf CLI; verify call shapes.
- **Integration:** approve a fixture action → email sent (test mailbox) + SFDC Task created (sandbox).
- **§6 rule 6 enforcement:** attempt direct dispatch without action_id → 403.

## Signal definitions involved

None.

## Open questions

Q60 (RM mailbox via OAuth), Q73 (calendar hold mechanism) — disposed.

## What this is NOT

- Not opportunity-tracker's `sf_tasks.push_to_salesforce` (that's spec 004 — separate write path, dormant).
- Not Skill-level templating — skills compose action payloads; handlers just dispatch.
