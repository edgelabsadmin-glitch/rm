# Spec 033 — Outcome detection watchers

**Maps to:** §14; Design 03 §"After-action outcome capture"; Layer 8 Mechanism 3 (spec 045 reads outputs).
**Depends on:** specs 012, 013, 014, 031, 032.
**Effort:** 0.75 day.

## Description

Per Design 03 §"After-action outcome capture." Three Phase 1 outcome types wired (email reply / SFDC Task done / Chorus EBR detection); the rest emit a manual "did this work?" follow-up card a week post-dispatch.

## Inputs

- `action-executed` events.
- Adapter Episodes (Chorus / SFDC / Calendar / email reply via IMAP scan if wired Phase 1).

## Outputs

- `03_build/pulse/core/outcomes/watchers.py` exporting per-outcome-type watchers.
- Activepieces flow `outcome_watch_daily` (cron daily) scanning recently-executed actions for outcome evidence.
- `outcome-recorded` / `outcome-missing` events.

## Definition of Done

- [ ] Email-reply watcher: matches reply messages to action `external_id` (SFDC Activity reply or Gmail thread reply).
- [ ] SFDC Task watcher: detects `Task.Status='Completed'` for actions with `external_id` = task ID.
- [ ] Chorus EBR watcher: detects engagements matching dispatched-action attendees + customer.
- [ ] Outcome-window per action type per Q45 (emails 7d; Tasks 14d; EBRs aligned to meeting date).
- [ ] `outcome-missing` event emits after window closes without evidence.
- [ ] Manual-follow-up card emitted at window+7d for unwatched action types.

## Tests

- **Unit:** matcher logic per outcome type.
- **Integration:** dispatch action → seed evidence → outcome-recorded fires.
- **Negative:** dispatch action → no evidence → outcome-missing fires at window-close.

## Signal definitions involved

Outcome events power Layer 8 Mechanism 3 metrics (spec 045).

## Open questions

Q45 disposed.

## What this is NOT

- Not Layer 8 admin surface (spec 045 — reads outcome events).
- Not where outcomes are *defined* — Design 03 owns the canonical type list.
