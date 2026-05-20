# Spec 047 — Demo HTML fallback verification

**Maps to:** §14 Demo deliverables; Decision 12 (rm-intelligence-agent's static HTML preserved); Design 08 §"Demo HTML fallback"; §13.6 #8.
**Depends on:** specs 040 (CEO View — shares the renderer).
**Effort:** 0.5 day.

## Description

Per Decision 12 + Design 08 §"Demo HTML fallback." Verify that the static-HTML renderer consumes the same JSON shape as the live CEO View renderer and produces a self-contained `data/demo.html` file consistent with rm-intelligence-agent's existing output. Brand-update to Tier-0 tokens (Edge purple #6B46C1; ring at 270°; Inter font).

## Inputs

- CEO View composer JSON (spec 040).
- rm-intelligence-agent's `src/render_demo.py` (the reference renderer; will be ported/adapted).

## Outputs

- `03_build/pulse/dispatch/static_html/render_demo.py` — ported renderer with Tier-0 tokens.
- A produced `data/demo.html` from a fixture-CEO-View-JSON.

## Definition of Done

- [ ] Renderer produces single self-contained HTML (no external assets; inline CSS).
- [ ] Output uses Tier-0 tokens (Edge Purple #6B46C1; Inter primary; 270° conic ring; tinted shadow on hero).
- [ ] Inline-tag voice rendered identically to the live UI's renderer.
- [ ] File opens correctly in Chrome / Safari / Firefox latest.
- [ ] Demo data + CEO View composer fire → fallback HTML produced + committed to `data/`.
- [ ] Fallback HTML's narrative anchors on the recon-verified accounts (**DHR Health Clinics + Mendota Insurance + Cirventis (HelixVM)** per Session 13) — inherited automatically from the CEO View composer JSON (spec 040), which sources from real production data. No Acrisure/Pinnacle references.

## Tests

- **Unit:** rendered HTML structure matches expected (snapshot test).
- **Parity:** the JSON CEO View renders the same content in live UI (spec 040) and static HTML; manual diff verification.
- **Visual:** open both side-by-side and confirm identical content.

## Signal definitions involved

None.

## Open questions

Q20 (Demo HTML preservation as fallback mode) — disposed; this spec is its implementation.

## What this is NOT

- Not the live CEO View page (spec 040).
- Not the demo storyboard (Design 12 — a script, not a build artifact).
