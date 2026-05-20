# Spec 038 — Pulse Bar (Breathing) implementation

**Maps to:** §14 Agent presence; Tier-0 §8.14 (LOCKED Session 10); §6 rule 24.
**Depends on:** spec 034 (shell). Implements on every screen including CEO View + Constellation.
**Effort:** 0.5 day.

## Description

Implement Tier-0 §8.14 exactly per the canonical render at `01_design/agent_presence_variants/04_pulse_bar_breathing.html`. Three states (idle / processing / action-ready). CSS keyframes per the spec. WebSocket or polling for state updates.

## Inputs

- Tier-0 §8.14 spec (motion, throttling, anti-patterns).
- Server-sent events or WebSocket from the back-end signaling agent state.

## Outputs

- `03_build/front/src/features/chrome/PulseBar.tsx`.
- A WebSocket or SSE endpoint (`GET /events/stream`) on the back-end (spec 001's FastAPI extended) that broadcasts: `agent_state_change` (idle/processing) + `action_suggested_count`.

## Definition of Done

- [ ] CSS keyframes match Tier-0 §8.14 exactly (breathe 2s; heartbeat 600ms; opacities 15%/40%/80%; heights 1px/1.5px/2px).
- [ ] Reduced-motion media-query support per Tier-0 §8.14 §"Reduced-motion handling."
- [ ] Throttling rules per Tier-0 enforced: heartbeats serialize at 600ms max cadence; processing state stacks; badge count is live.
- [ ] Bar lives on every screen including CEO View and Constellation.
- [ ] WebSocket/SSE auto-reconnects on disconnect (gracefully degrades to polling if not reconnectable).

## Tests

- **Unit:** state-transition logic.
- **Visual regression:** static screenshot per state (cannot animate; matches canonical HTML's static frames).
- **Manual:** open the canonical `04_pulse_bar_breathing.html` side-by-side and visually compare animation cadence.

## Signal definitions involved

None directly — the bar surfaces agent state, not signals.

## Open questions

None.

## What this is NOT

- Not the Action Queue badge — the badge lives on the Queue button (per spec 035 + Tier-0 §8.14 companion-badge spec).
- Not v3 Account-Card Ring (v1.5+ secondary indicator per Q117).
