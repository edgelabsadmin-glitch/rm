# Spec 041 — Constellation view

**Maps to:** §14 UI surfaces (Constellation view as dedicated nav surface; locked Session 11, Decision 38).
**Depends on:** specs 030 (health for coloring), 034 (shell), 038 (Pulse Bar).
**Effort:** 2.0 days. **Largest single UI spec.**

## Description

Per Decision 38: dedicated nav surface; force-directed graph; sized by placements; colored by health; clickable to navigate to existing account view. Library pick at spec-author time — `react-force-graph` is the leading candidate. Graceful degradation per Risk 7: if the chosen library proves a bad fit, MVP = nodes + click navigation, no animated forces.

## Inputs

- All Customers + their placement counts (from SFDC ingestion + Graphiti).
- Per-Customer composite health (spec 030).
- Cross-account pattern cards (spec 027) for theme-overlay (v1.5+ feature; Phase 1 ships base view).

## Outputs

- `03_build/front/src/features/constellation/Constellation.tsx`.
- `03_build/front/src/features/constellation/ForceGraph.tsx` — library wrapper.
- New route `/constellation` under the front-end shell.

## Definition of Done

- [ ] All Customer accounts render as nodes; size proportional to placement count.
- [ ] Node colors map to health tier per Tier-0 risk colors.
- [ ] Click a node → navigate to that account's per-account view.
- [ ] At 530 accounts, performance: initial render <2s; pan/zoom interactive at 30fps minimum.
- [ ] RBAC scope per spec 042 — RM sees their own book; Manager sees direct reports; Admin sees all.
- [ ] Pulse Bar (Breathing) lives at the top of the constellation page same as every other screen (per §6 rule 24).
- [ ] Graceful degradation MVP: if force-directed performance fails, static positioning + clickable nodes still satisfies DoD.

## Tests

- **Unit:** node-to-color mapping; size formula.
- **Visual regression:** layout snapshot at 530 nodes.
- **Performance:** Lighthouse audit at the 530-node scale.

## Signal definitions involved

None directly — composite health drives colors; signal-level overlays are v1.5+.

## Open questions

- **Q151:** Force-graph library final pick (react-force-graph vs. d3-force vs. cytoscape). PM picks at spec-author time post-Week-4 exploration.

## What this is NOT

- Not where signal definitions surface — it's an account-level map; signal details live in the account view.
- Not v1.5+'s theme-overlay (Phase 1 ships base view only).
