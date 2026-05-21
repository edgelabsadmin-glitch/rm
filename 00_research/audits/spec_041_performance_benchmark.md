# Spec 041 — 610-Node Performance Benchmark (Step-2 GATE)

**Date:** 2026-05-21
**Purpose:** the §4.16 perf GATE before spec-041 implementation (Step 3). Build the
locked-density fixture, render it with react-force-graph-2d (placeholder rendering),
and measure FPS / interaction latency / memory before locking implementation patterns.
**Harness (committed, live):** `/constellation` route — `Constellation.tsx` +
`ForceGraph.tsx` + `fixtures.ts`. On-screen counter + `window.__cstBench` (live FPS /
node / link / heap) + `window.__fg` (force-graph ref: `zoom` / `zoomToFit` / `centerAt`).

## Fixture (locked density)

- **612 nodes** = 1 center globe + 3 managers + 8 RMs + **600 accounts**.
- Account tier mix: **200 SMB / 280 Mid-Market / 120 Enterprise**; health varied 0–10 (seeded PRNG, deterministic).
- **611 links**: account→RM, RM→manager, manager→globe; link state varied (~50% active / 25% inactive / 25% churn).
- Rendering: **placeholder** (default circle nodes colored by type/health; links colored by state). NOTE: the Step-3 custom rendering (brand-glyph globe, avatar/label nodes, animated link recolor) will be **heavier** — these numbers are a **lower bound**.

## Results

| Metric | Result | vs. target | Notes |
|---|---|---|---|
| Nodes / links rendered | 612 / 611 | — | full density, canvas present |
| Force layout settles | ✅ | — | spread bbox ≈ 1810 × 1806 graph units; `cooldownTicks=100` |
| **JS heap (baseline)** | **16 MB** | ✅ ≪ 200 MB | right after settle |
| **JS heap (after zoom+pan)** | **14 MB** | ✅ ≪ 200 MB | stable/lower (GC) — strong anti-leak signal |
| Zoom / pan / zoomToFit controls | ✅ work | — | driven via `window.__fg` |
| Bundle size | **602 kB** (196 kB gz) | ⚠️ | +~200 kB gz from react-force-graph + d3 |
| **Interactive FPS** | **INCONCLUSIVE** | — | see limitation below |
| **5-min sustained-interaction memory** | **INCONCLUSIVE** | — | see limitation below |

## Measurement limitation (important)

The benchmark ran in the **headless preview tab**, which reports `document.visibilityState = "hidden"`. Browsers **throttle `requestAnimationFrame` to ~1–2 fps in hidden/background tabs** — so the harness's FPS counter read `2`, which is the **throttle, not the render cost**. The same throttle prevents a meaningful 5-minute sustained-interaction loop. (This is the same visibility-gating seen in the spec-038 polling verification.)

What this means: **FPS and the 5-min leak number cannot be obtained from the headless preview.** They require a **focused browser tab**, which the committed `/constellation` harness supports out of the box (open it focused; read the on-screen `fps` counter + `window.__cstBench.heapMB` over 5 minutes of pan/zoom).

What IS reliably established (visibility-independent):
- The 612-node graph **builds, renders, and settles** — galactic density is functionally feasible with react-force-graph-2d.
- **Memory is tiny and stable** (14–16 MB) — ≪ the 200 MB ceiling; baseline gives no indication of a leak (the 5-min confirmation still wants a focused run).
- **Bundle weight** is the one clear cost signal: /constellation should be **code-split** (lazy-loaded route) so the +200 kB gz doesn't burden the rest of the app.

## Documented fallbacks (ready if focused-tab FPS < 30)

In order of preference (per the pre-spec audit Dim 13):
1. `cooldownTicks` / `cooldownTime` to freeze the simulation after settle (already `cooldownTicks=100`).
2. Level-of-detail labels — render labels only above a zoom threshold.
3. Recolor/animate only links within the viewport.
4. Cluster accounts under their RM at low zoom; expand on zoom-in.
5. Graceful-degradation floor (spec-041 DoD): static positions + click nav, no animated forces.

## GATE recommendation (PM rules)

Feasibility ✅ and memory ✅ are green. The only open metric is **interactive FPS**, which the headless environment can't measure. Two ways forward — **PM rules**:

- **(A) Confirm-then-proceed:** the operator opens the committed `/constellation` harness in a **focused tab**, confirms ≥30 fps + <200 MB after 5 min, and reports back; Step 3 proceeds (applying fallbacks only if the focused number misses).
- **(B) Proceed-with-fallbacks-ready:** begin Step 3 now (feasibility + memory cleared), confirm FPS in the focused dev environment during Step-3 build, and apply the ranked fallbacks if it misses. The graceful-degradation floor guarantees a shippable surface regardless.

**Recommendation: (B)** — feasibility + memory are the load-bearing risks for a GATE and both passed; FPS is tunable via the ready fallbacks and confirmable continuously during focused-tab Step-3 dev. (A) is the more conservative choice if the PM wants a hard FPS number before any Step-3 code.

**HALT.** Per the execution sequence, spec-041 Step-3 implementation does **not** begin until the PM rules (A) or (B).
