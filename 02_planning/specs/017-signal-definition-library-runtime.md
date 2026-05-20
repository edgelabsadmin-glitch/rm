# Spec 017 — Signal Definition Library runtime

**Maps to:** §14 Signal Definition Library; §6 rule 8 (no black-box detection).
**Depends on:** specs 005, 006, 008.
**Effort:** 1.0 day.

## Description

Build the runtime that loads `02_planning/signals/*.md` definitions at startup, exposes them as queryable Signal objects, and provides the `evaluate(signal_id, context)` API that skills call. The runtime parses each markdown file's structured sections (template per `02_planning/signal_definition_template.md`), validates required sections, and constructs a Python object per signal with the detection logic compiled from the spec's `Detection mechanism` section.

For rule-based signals, the runtime extracts the pseudocode and translates to a Python evaluator (Phase 4 implementation pattern — each signal has a corresponding `pulse/core/signals/<signal_id>.py` module with the actual code; the markdown is authority but the Python is invoked at runtime). For LLM-based signals, the runtime stores the prompt and invokes via the LLM client.

This is the architectural answer to §6 rule 8: signal definitions are inspectable in plain English (the markdown) AND executable as code (the matching Python). The two must align — CI enforces.

## Inputs

- The 14 signal definitions in `02_planning/signals/*.md`.
- `pulse.core.signals.<signal_id>` Python modules (one per signal — co-authored with this spec).
- The named retrievers (spec 006).
- The cross-account retriever (spec 007).
- The event log (spec 008).

## Outputs

- `03_build/pulse/core/signals/runtime.py` exporting:
  - `load_signal_library() -> dict[signal_id, Signal]` — called at startup.
  - `async def evaluate(signal_id: str, context: EvaluationContext) -> SignalResult | None`.
- `03_build/pulse/core/signals/<signal_id>.py` — 14 Python modules, one per signal definition.
- A CI check that asserts every `02_planning/signals/*.md` has a corresponding `pulse/core/signals/<signal_id>.py` and vice versa (no orphaned definitions; no orphaned code).
- Validation: parsed markdown + Python signature must agree on signal category, severity model, owning skill.

## Definition of Done

- [ ] All 14 signal definitions load at startup without error.
- [ ] CI check enforces 1:1 markdown:code correspondence.
- [ ] `evaluate('churn_signal_contact_disengagement_v1', ctx)` returns a `SignalResult` with severity + evidence for fixture inputs.
- [ ] Every `evaluate` call emits a structured event to the log so signal-evaluation history is auditable (Layer 8 Mechanism 1 reads from these events).
- [ ] Langfuse-instrumented; each evaluate call becomes a span in the parent skill's trace.

## Tests

- **Unit:** each signal's `evaluate()` runs against its fixture set (positive + negative examples from its definition file's "Examples" section).
- **Integration:** load library + evaluate one signal per category end-to-end with real Graphiti.
- **CI meta-test:** `test_signal_markdown_and_python_align` — for each md+py pair, verify category/severity/owning-skill match.

## Signal definitions involved

All 14.

## Open questions

- **Q150:** Signal versioning at runtime — when `v2` of a signal lands, does the runtime support both `v1` (deprecated) and `v2` simultaneously? PM proposes: yes, controlled by a `pulse_settings.active_signal_versions` config; deprecated versions still evaluate but emit `signal-deprecated-evaluation` event.

## What this is NOT

- Not the signal definitions themselves (those are `02_planning/signals/*.md`).
- Not Skill 01 (signal *extractor* — different from signal *evaluator*).
- Not Layer 8 (which reads the runtime's evaluation history, not the runtime itself).
