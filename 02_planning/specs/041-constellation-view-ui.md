# Spec 041 — Constellation view (galactic + agentic overlays)

**Maps to:** §14 UI surfaces (Constellation as dedicated nav surface; Decision 38); Session-18 visual + agentic lock; pre-spec-041 audit (`00_research/audits/pre_spec_041_constellation_audit.md`), 12 dispositions ratified PM_CONTEXT Session 19 §3.
**Depends on:** specs 030 (health), 034 (shell), 038 (Pulse Bar), 027 (Skill 10 cross-account patterns). **Soft:** 042 (RBAC — NOT a hard dependency; renders against the stubbed session for scope until 042 ships).
**Effort:** ~2.0–2.5 days (front-end galactic surface + back-end overlay composer).

> **This spec was rewritten (Session 19) to match the Session-18 lock + audit dispositions.** The prior spec 041 — a flat account-only force graph with signal overlays deferred to v1.5+ — is **superseded**. The audit's three corrections are absorbed: there is no standalone Constellation design doc; this rewrite is the canonical spec; Skill 10 is spec 027.

## Description

A dedicated `/constellation` nav surface: a **galactic map of the whole book of business** with an embedded **agentic overlay layer**. Built on **react-force-graph-2d** (Q151 locked; 2D canvas, not 3D — disposition D3).

**Visual vision (Session-18 lock):**
- **Center:** the EDGE Pulse **globe** — a custom-rendered node, the brand-mark `Zap` glyph on a solid `bg-brand` disc with a `--color-brand-primary-glow` halo (the §6 tinted-shadow signature), pinned at graph center (`fx/fy = 0`). The gravitational anchor. (A true 3D globe is v1.5+.)
- **Orbital hierarchy:** RM Managers (innermost orbit) → individual RMs (mid) → customer accounts (outermost, densest). Enforced via a per-tier **radial force** (`d3Force('radial', forceRadial(r_tier))`) + link forces — descendants trail their parent through physics, not bespoke transforms (disposition D11).
- **Link saturation = signal state** (disposition D2 tokens): active customer engagement → `--color-link-active` (saturated brand purple); inactive / no recent signal → `--color-link-inactive` (dimmed slate); silent-churn-signal detected → `--color-link-churn` (reddish, reuses risk-high). **Churn links get animated emphasis** (pulse / glow / animated flow) — red is reserved for the genuinely urgent state (a connection failing) and earns attention through motion, not by tinting nodes.
- **Force dynamics:** active accounts gain mass and pull outward; dormant accounts drift to the periphery.
- **Node color = brand purple across all health tiers** (Amendment 5) — the galaxy stays brand-cohesive at rest; scattered risk-colored nodes broke cohesion and fought the link encoding. **Node size = composite health × activity** (healthier + more active = larger; at-risk + dormant = smaller) — a single dimension encoding *both* health and activity. Health is NOT encoded as node color; the urgent signal lives on the links (churn-state, animated).
- **Node geometry = rounded squares** (Amendment 6) for managers / RMs / accounts / talent — corner radius ≈ 25% of side (soft, matching the brand-mark tile, Hero Card, and Action Queue cards). The **center globe is the only circle** (a singleton, not part of a cluster; the globe metaphor needs it). *Rationale:* a dense radial cluster of circles is a **trypophobia trigger** — a real accessibility concern (~15–20% of people to varying degrees); hero surfaces must not cause physical discomfort. Rounded squares are also Pulse's established vocabulary, bringing the Constellation into visual coherence. Pair with slightly increased node spacing (link-distance + charge tuning) for breathing room — only enough to fix density, not to break the galactic metaphor.
- **Talent (option c):** hidden by default; on **account click**, talent appears as small nodes **orbiting that account** (inline orbital expansion; added to the graph data, removed on collapse). Side-panel list is the documented perf fallback (disposition D10). Keeps the galactic view clean per §22 opt-in depth.

**Agentic overlay layer (3 types; the v1.5+→Phase-1 reversal, disposition 1f).** Overlays are HTML elements positioned over the canvas via `graph2ScreenCoords`, not graph nodes:
1. **Cluster-pattern alert** — when ≥3 accounts under one RM (or vertical) share a correlated signal pattern, surface a constellation-level proposed action with provenance, anchored in that RM's orbital region. Click → the existing cross-account pattern card (Overall view). Consumes **pre-computed Skill-10 cards** (spec 027), not re-computed (disposition D5).
2. **RM capacity imbalance** — when one RM's region shows many red/dim links + deep queue while another shows steady-purple with bandwidth, surface a reassignment thesis floating in inter-RM space. Click → reassignment-draft review surface. Proposal only; requires human approval (§6 rule 3).
3. **Escalation tier-jump** — when an account's health worsens past threshold within a window, surface an escalation proposal anchored to the node. Click → drafts an escalation email to the RM's manager (spec-032 dispatch + new template). Reuses the existing `health-tier-changed` event (disposition D7).

**Interaction (click → destination; audit Dim 9 + Session-19 amendments):**
- **Center globe** → routes to **`/ceo`** (CEO View). Center node = org-level; CEO View = org-level narrative — a natural drill from visual org survey to strategic org narrative (and keeps the globe non-decorative per §4.20).
- **Manager node** → **single-click = zoom-to-cluster** (primary; visual survey). **Modifier-click (cmd/ctrl)**, or a small "View N pending actions" overlay link shown after zoom, → **queue-filter `/actions?manager=<id>`** (secondary; navigation). Both workflows matter: survey first, then filtered access.
- **RM node** → `/actions` filtered to that RM (`rm_id`).
- **Account node** → set `selectedAccountId` (spec-036 context) + per-account view; spawns inline talent orbit.
- **Link** → tooltip (state + last-signal date); no navigation.
- **Overlays** → cluster→pattern card (Overall view); capacity→reassignment-draft review; escalation→escalation-email draft.

## Inputs

- **Graph:** all in-scope managers/RMs/accounts + placement counts (SFDC + Graphiti), per-account composite health (spec 030, normalized `(score+100)/20` → 0..10), link signal-state per account.
- **Overlays:** Skill-10 pattern cards (spec 027, extended with `support_account_ids` + `owning_rm_id`); per-RM capacity inputs (event-log queue depth + signal velocity + `account_health` rollup); `health-tier-changed` events (worsening + window).
- **Scope:** `derive_scope` (spec 042) server-side; stubbed-session scope until 042 ships.

## Outputs

**Front-end (`03_build/front/`):**
- `src/features/constellation/Constellation.tsx` — the page.
- `src/features/constellation/ForceGraph.tsx` — react-force-graph-2d wrapper (custom node/link rendering, radial force).
- `src/features/constellation/overlays/` — ClusterAlert / CapacityImbalance / EscalationJump overlay components.
- `src/features/constellation/fixtures.ts` — 610-node fixture (Step-2 benchmark + dev).
- Link-state tokens added to `src/styles/tokens.css` (`--color-link-active/inactive/churn`, §22-justified).

**Back-end (overlay composer — absorbed into spec 041, no 041.1; disposition D15):**
- `03_build/<composer module>` — composes the 3 overlay types from Skill-10 cards + capacity query + health-tier-changed.
- `GET /constellation` → `{ nodes:[{id,type,label,tier?,health?,size,rm_id?,manager_id?}], links:[{source,target,state,last_signal_at?}] }`.
- `GET /constellation/overlays` → `{ cluster_alerts[], capacity_imbalances[], escalation_jumps[] }`. Both RBAC-scoped (disposition D8/D12). Week-4 pulse-api wiring.
- RM capacity imbalance emitted as `action-suggested(action_type="capacity-imbalance")` (disposition D6).

## Definition of Done

- [ ] Center globe + 3-tier orbital hierarchy render via radial force; managers inner → RMs mid → accounts outer.
- [ ] Nodes render **brand-purple across all tiers**; **node size = composite-health × activity** (Amendment 5). Health is NOT a node color.
- [ ] Node geometry = **rounded squares** (corner radius ≈ 25% of side) for managers/RMs/accounts/talent; the **center globe stays circular** (Amendment 6). Node spacing tuned for breathing room without breaking the galactic structure.
- [ ] Link state colors per the 3 link-state tokens; **churn links carry animated emphasis** (pulse/glow/flow) — red reserved for the failing connection, not for nodes.
- [ ] Account click → sets `selectedAccountId` (spec-036 context) + navigates to the per-account view; full click→destination matrix per audit Dim 9.
- [ ] Talent inline orbital expansion on account click (or side-panel fallback if perf gate requires).
- [ ] All 3 overlays render + route correctly (cluster→pattern card; capacity→reassignment draft; escalation→email draft).
- [ ] Performance per Step-2 gate: initial render <2s, pan/zoom ≥30fps at ~610 nodes, **memory footprint <200MB after 5 min of typical pan/zoom** (RMs leave Pulse open all day; canvas leaks possible) — or PM-approved mitigations applied if exceeded.
- [ ] RBAC scope (stubbed session Phase 1; spec-042 server-side when it ships): RM own book / Manager reports / Admin all.
- [ ] Pulse Bar lives at the top, same as every screen (§6 rule 24).
- [ ] Empty / loading / error / RBAC-subset states per audit Dim 14.
- [ ] Graceful-degradation floor: if force perf fails, static positioning + click nav still satisfies the navigation DoD.
- [ ] Tokens-only; no arbitrary Tailwind color values. Build + vitest green.

## Tests

- **Unit:** node→color + size mapping; link-state→token mapping; tier→radial-ring assignment; overlay anchor positioning.
- **Visual regression:** layout snapshot at the 610-node fixture.
- **Performance:** the Step-2 benchmark (`00_research/audits/spec_041_performance_benchmark.md`) is the gate.

## Implementation order (9-step audit sequence — disposition D15)

1. Library + `ForceGraph` wrapper + 610-node fixture + **perf benchmark (GATE)** — FPS at fit/mid/max zoom, pan/zoom interaction latency, and **memory footprint <200MB after 5 min interaction**.
2. Visual scaffold: center globe + 3-tier radial hierarchy (mock).
3. Encodings: health→color/size, link-state coloring, active-mass/dormant-drift forces.
4. Interaction: click→destination matrix + talent drill-down.
5. Overlay #1 — cluster-pattern (consumes Skill-10 cards; needs the spec-027 extension).
6. Overlay #2 — RM capacity imbalance (composer module).
7. Overlay #3 — escalation tier-jump (health-tier-changed).
8. Empty/loading/error + RBAC scope.
9. Polish + DoD verification.

## Open questions

- **Q151:** RESOLVED — react-force-graph (Session 19).
- Manager-node click = zoom-to-cluster vs queue-filter (audit Dim 9 sub-choice) — ratified to **zoom-to-cluster** single-click per Session 19 §3 disposition (confirm at impl).

## What this is NOT

- Not a 3D globe in Phase 1 (v1.5+).
- Not where signal *definitions* surface (account-level map; signal detail lives in the account view).
- Not auto-acting on capacity reassignments or escalations — both are proposals requiring approval (§6 rule 3).
- Not on the demo critical path (disposition D4 — teaser only for 2026-06-30; revisit Scene-3 upgrade post-perf). The Constellation demo storyboard scene is drafted as part of **specs 046/047 (demo prep)**, not in spec 041 itself.
- Not a separate 041.1 — the overlay composer is a back-end section of this spec.

## Step-9 close-out — SPEC 041 CLOSED (2026-05-22)

Steps 0–9 complete. Built on branch `dz-001` (operator branch discipline, Session 19 late
stream). Build green, **65/65 vitest**, perf gate passed (Step 2). Closure does NOT trigger
merge to `main` — that needs explicit two-step operator authorization.

### DoD verification
- [x] Center globe + 3-tier radial hierarchy (managers inner / RMs mid / accounts outer). *Accounts free-float beyond the RM ring rather than pinned to a fixed ring — by Amendment-5 force design.*
- [x] Brand-purple all tiers; node size = composite-health × activity (Amendment 5).
- [x] Rounded squares for managers/RMs/accounts/talent; center globe circular (Amendment 6); spacing tuned (charge −55 / link 36).
- [x] Link-state token colors; churn links animated (directional particles).
- [x] Account click → `selectedAccountId` + per-account nav; full click→destination matrix (Dim 9).
- [x] Inline orbital talent drill-down (cap 30; side-panel documented as fallback).
- [x] All 3 overlays render + route. ⚠️ **Deviation:** overlays route to existing surfaces (cluster→`/actions?pattern=`, capacity→`/actions?rm=`, escalation→`/accounts/<id>`) rather than pre-filled reassignment/email *drafts*. Drafts require the pulse-api composers — Week-4 wiring. Phase-1 routing is the honest proxy.
- [x] Performance: Step-2 gate passed (≥30fps at ~610 nodes, <200MB/5min). 
- [~] RBAC scope: **stubbed Phase-1** (all accounts visible) + `accountScope` prop interface ready. Server-side RM/Manager/Admin enforcement is **spec-042 (Week 4)**.
- [x] Pulse Bar at top (AppShell singleton, present on `/constellation`).
- [x] Empty / loading / error / RBAC-subset states (Step 8).
- [~] Graceful-degradation floor: **not separately implemented** — the perf gate passed at 610 nodes so the floor was never triggered; manager/RM nodes are pinned (fx/fy) and click-nav works independent of the force sim, so navigation survives a force failure in practice. Explicit static-fallback toggle deferred (no trigger).
- [x] Tokens-only (canvas reads Tier-0 vars via getComputedStyle, with hex fallbacks only when a var is unavailable). Build + vitest green.

### Watched concerns carried forward
- **#24** — capacity-imbalance threshold is marginal on demo data (Sajjal 2.76 vs 2× median 2.71); re-evaluate the heuristic at Phase-2 production scale.
- **#25** — tier-jump overlay uses a live 48h window; bump `demo_tier_jump_events.ts` `occurredAt` on the morning of the 2026-06-30 demo (PM follow-up).
- **#26** — overlay composers read full `DEMO_ACCOUNTS`, not `accountScope`; spec-042 (Week 4) must extend the composers to honor RBAC scope.
- **#27** — dev instrumentation chip ("N nodes · N fps") is visible on `/constellation`; gate behind `import.meta.env.DEV` or remove before the demo (low-priority polish).

### Storyboard alignment (Amendment 4)
The built Constellation (interactive graph + 3 overlays + hover ARR) can support the Session-13
storyboard "Scene 6/7 (cuttable)" Constellation teaser. Scene drafting remains in specs 046/047
per Amendment 4 — nothing here precludes it.

### Pending coordination
Spec-042 RBAC (Week 4): extend `buildConstellationGraph` consumers + overlay composers to honor
`accountScope`; wire server-side scope. Awaits operator authorization.
