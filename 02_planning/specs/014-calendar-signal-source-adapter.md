# Spec 014 — Calendar Signal Source Adapter

**Maps to:** §14 Signal sources (Calendar); Design 02; §13.3 row "Detect customer meeting on calendar 24h ahead."
**Depends on:** specs 011, 008, 012 (Account lookup for attendee resolution).
**Effort:** 0.75 day.

## Description

Implement the Calendar Signal Source Adapter. Phase 1 scope (per Design 02): detect customer meetings on RM calendars 24h ahead; resolve attendee emails to SFDC Account.Id via the existing salesforce_client; emit one `calendar.upcoming-customer-meeting` Episode per qualifying event.

Provider choice (Google Calendar vs. MS Graph) pending Q23/Q33 resolution. Day-1 of Phase 4 confirms provider with user; this spec writes against the chosen provider's webhook + read API. Both providers have similar shape; the adapter abstracts.

Out of Phase 1 scope (per Design 02 §"Calendar adapter scope"): meeting-conflict detection, automatic calendar holds, past-meeting reconciliation.

## Inputs

- OAuth credentials for the chosen provider (Google or MS).
- Calendar webhook payload (push notification for upcoming meetings).
- SFDC `Account` records ingested via spec 012 (for attendee-email → Account.Id resolution).
- Episode envelope from spec 011.

## Outputs

- `03_build/pulse/core/adapters/calendar.py` exporting `CalendarAdapter(SignalSourceAdapter)`.
- Activepieces flow `calendar_24h_ahead` (in `pulse_workflows/`).
- One Episode emitted per qualifying upcoming meeting. `content_type='json'`; `content={meeting_id, attendees, start_time, agenda, meeting_provider}`. Tags include `["calendar", "upcoming-customer-meeting"]`.

## Definition of Done

- [ ] Webhook signature validated.
- [ ] Attendee emails resolved to `Account.Id` via SQL on `pulse.episodes` table filtering for SFDC Contact records matching attendee email; if no match, emit a low-urgency `unknown-attendee` Episode (per Q54 disposition).
- [ ] 24h-ahead filter applied; meetings further out or already started are skipped.
- [ ] EBR detection fallback per Q55: meeting title contains "EBR" / "QBR" / "quarterly review" → Episode tagged `["calendar", "ebr-candidate"]`.
- [ ] `dedup_key` formula: `f"calendar:{event_id}:{etag}"` per Design 02.
- [ ] Recurring-meeting handling: each instance gets its own Episode (recurring meeting series do not deduplicate across occurrences).

## Tests

- **Unit:** mocked Google Calendar webhook + API; resolve attendee → Account.Id; verify Episode shape.
- **Integration:** real Google Calendar (test account); fire one meeting webhook; verify Episode + event log.

## Signal definitions involved

Direct triggers:
- `churn_signal_contact_disengagement_v1` (`ebr_no_shows_last_60d` counter depends on Calendar Episodes for the participation history).
- Skill 02 (briefing) — fires on `calendar.upcoming-customer-meeting` Episodes (this isn't a Signal Definition but a direct skill trigger).

## Open questions

- Q23 / Q33 — Google vs. MS Graph confirmation (Day-1 task).
- Q54 — unknown-attendee disposition (decided: emit low-urgency notification per Skill 02).
- Q73 — calendar hold mechanism (Phase 1 = manual suggestion; auto-booking v1.5+).

## What this is NOT

- Not Skill 02 (the briefing skill consumes Calendar Episodes — that's spec 018).
- Not where calendar holds are *placed* — that's spec 032 dispatch handlers, only on approval.
- Not Zoom (v1.5+ per §12 #8; Spike 2 questionnaire pending).
