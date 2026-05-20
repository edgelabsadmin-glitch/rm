# Spec 008 — Event Log + Reasoning Capture schema + emitter

**Maps to:** §14 Infrastructure ("Event Log + Reasoning Capture schema"); Design 04; §6 rule 14 (no silent failure); §13.5 row "Track issues, resolutions, outcomes."
**Depends on:** spec 001.
**Effort:** 1.0 day.

## Description

Implement the event log per Design 04. Single Postgres `events` table (schema `pulse`) per Design 04 §"Storage." Append-only by design. An emitter API (`pulse/core/events/log.py::emit_event(...)`) that every skill, retriever, adapter, and dispatch handler calls to record significant moments. Cross-linked to Langfuse via a `trace_id` column on every event.

The 19 event types from Design 04 §"Event types (Phase 1 enum)" are enumerated as Python literal types; the emitter validates incoming events against the appropriate payload schema per type.

## Inputs

- Supabase Postgres connection from spec 001.
- Design 04's full event-type enum and payload schemas.

## Outputs

- A Postgres migration creating the `pulse.events` table per Design 04 §"Storage" — verbatim schema with the addition of a `trace_id UUID NULL` column (ADR-003 cross-link).
- `03_build/pulse/core/events/log.py` exporting:
  - `async def emit_event(event_type: str, payload: dict, **kwargs) -> UUID`
  - Per-event-type helper functions: `emit_signal_received(...)`, `emit_action_suggested(...)`, etc. (one per Design 04 enum).
- `03_build/pulse/core/events/queries.py` exporting the 5 named queries from Design 04 §"Querying the event log."

## Definition of Done

- [ ] Postgres migration applied; `\d pulse.events` shows the expected schema.
- [ ] `emit_event` is async; validates `event_type` against the enum; raises on unknown types.
- [ ] Per-event-type payload validation via Pydantic — bad payloads raise at emit time, not at read time.
- [ ] `trace_id` populated from `langfuse.get_current_trace_id()` when called from inside an `@observe()`-decorated function.
- [ ] All 5 named queries from Design 04 work; pytest verifies each against a seeded events fixture.
- [ ] Index strategy from Design 04 §"Storage" implemented.

## Tests

- **Unit:** Pydantic validation per event type; emit + immediate query roundtrip.
- **Integration:** emit 100 events; assert ordering preserved (occurred_at DESC); assert each named query returns expected counts.
- **Performance:** burst test — 1000 events emitted in <2s.

## Signal definitions involved

The event log is the canonical record of *every* signal-firing event, action-suggested event, etc. Each signal definition records its `signal_id` in the relevant event's payload.

## Open questions

- Q41 disposition (event log retention beyond 90 days) is documented in `99_open_questions.md`; Phase 1 keeps full history, v1.5+ adds cold-archive.

## What this is NOT

- Not Langfuse (ADR-003) — the event log is the structured audit log; Langfuse is the LLM-call trace tree. They cross-link, they don't merge.
- Not the policy module (spec 009).
- Not the kill switch (spec 010).
