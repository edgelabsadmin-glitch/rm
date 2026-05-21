# Pre-Spec-041 Constellation Audit

**Date:** 2026-05-21
**Type:** Read-only audit (§4.16). NO spec-041 implementation begun; no code/spec files modified. PM ratifies dispositions before any code.
**Locked inputs treated as PM-given (not re-litigated):** the Session-18 visual vision (central EDGE Pulse globe; orbital hierarchy Managers→RMs→accounts; link-saturation = signal state; force dynamics; talent drill-down option-c), the 3-overlay agentic layer (cluster-pattern / RM-capacity / escalation-tier-jump), the scope trade (OUT: spec 039 → v1.5+ #26; IN: expanded 041 + overlay composer), and **Q151 = react-force-graph** (validated, not re-picked).
**Artifacts read:** spec 041, spec 027 (Skill 10), `12_demo_storyboard.md`, `core/events/types.py` (HealthTierChanged), `skills/skill_10_cross_account_pattern_finder.py`, `core/health/dual_sided.py`, front-end tokens + RBAC context (spec 042).

---

## ⚠️ Three cross-cutting findings up front

1. **There is no standalone "Design 12 = Constellation" design doc.** `12_demo_storyboard.md` is Design 12 (the demo storyboard). The Constellation's only documentation is: the *written* spec 041, PM_CONTEXT Decision 38 / §14 (promoted as a dedicated nav surface, Session 11), and now the Session-18 lock. **The Session-18 vision is by far the most detailed Constellation spec that exists** — the audit treats spec 041 (written) as the baseline to reconcile against it.
2. **The written spec 041 is a small fraction of the Session-18 lock.** Spec 041 = a flat force graph of *account* nodes, sized by placements, colored by health, click→account view, with **signal overlays explicitly deferred to v1.5+**. Session-18 adds: a 3-tier orbital hierarchy, a central globe, link-state signal coloring, talent drill-down, and **three agentic overlays** — i.e., spec 041 needs a substantial rewrite + new back-end work. This is the audit's spine (Dimension 1).
3. **Spec-number correction:** Skill 10 (cross-account-pattern-finder) is **spec 027**, not spec 026 (which is Skill 09, coaching-router). The prompt said 026; this audit read the correct file (027). No action beyond noting it.

---

# VISUAL / DESIGN

## Dimension 1 — Design 12 / spec 041 delta (line-by-line vs the locked vision)

**Finding.** Reconciling the *written* spec 041 against the Session-18 lock, each line conflicts or is silent:

| # | spec 041 (written) | Session-18 lock | Delta type |
|---|---|---|---|
| 1a | Nodes = **accounts only** (~530) | **3-tier**: Managers (inner) → RMs → accounts (outer); ~610 nodes | **Expansion** (new node model) |
| 1b | Node **size = placement count** | Active accounts **gain mass / pull outward**; dormant drift to periphery | **Change** (size/force semantics) |
| 1c | Node **color = health tier** (risk colors) | Node color still health; **links** carry signal state (purple/grey/red) | **Addition** (link encoding is new) |
| 1d | **No links described** | Links are first-class: active=purple, inactive=grey, churn=red | **Addition** |
| 1e | **No center node** | Central EDGE Pulse **globe** = gravitational anchor | **Addition** |
| 1f | Signal overlays = **v1.5+; Phase-1 base view only** | **3 agentic overlays are IN Phase 1** | **Direct conflict** (v1.5+ → IN) |
| 1g | No talent representation | Talent **drill-down on account click** (option c) | **Addition** |
| 1h | Perf target **530 nodes** | ~610 nodes + custom render + animated links + overlays | **Change** (heavier) |
| 1i | "click → account view" only | Full **click→destination matrix** incl. overlay routing | **Expansion** (Dim 9) |

**Recommendation.** Rewrite spec 041 to the Session-18 lock as the canonical spec (the written one is superseded). Treat 1f (the v1.5+→IN reversal of overlays) as the headline change — it pulls real back-end work (Dims 5-8) into Phase 1. Keep spec 041's **graceful-degradation MVP** (static positioning + click nav if force perf fails) as the floor.
**PM adjudication needed: YES.** Proposed disposition: *"Ratify the Session-18 vision as the spec-041 rewrite; the written spec 041 is superseded. Overlays move v1.5+→Phase-1 (1f). Graceful-degradation floor retained."* PM rules per-row if any delta should NOT carry.

## Dimension 2 — Tier-0 token coverage for link states

**Finding.** Active link = `--color-brand-primary` ✅ exists. Churn/red = `--color-risk-high-fg` exists (but it's a *text* foreground token; semantically fine for a link stroke). **Dimmed/inactive link has no token** — the §2 palette has no neutral-grey-line meant for "no recent signal." Link-saturation-as-signal-state is a **new visual encoding** not in §2.
**Recommendation.** Add a small, §22-justified token set in `tokens.css` (mirrors how spec-035 added `--color-text-quote` and spec-036 added `--color-ring-track`):
- `--color-link-active: var(--color-brand-primary)` (alias for intent clarity),
- `--color-link-inactive: rgba(148,163,184,0.35)` (slate-400 @ low alpha — dimmed),
- `--color-link-churn: var(--color-risk-high-fg)` (reuse rose-700).
§22 justification: the Constellation introduces link-state as a first-class signal channel that no prior surface used; three named tokens prevent per-render literal drift.
**PM adjudication needed: YES (token addition).** Proposed disposition: *"Approve the 3 link-state tokens (active alias / inactive / churn-reuse). No other palette changes."*

## Dimension 3 — Center node ("EDGE Pulse globe") design

**Finding.** react-force-graph offers a 2D (canvas) and a 3D (Three.js) variant. A literal "globe" implies 3D; but 3D adds bundle weight (three.js ~600kb), perf cost at 610 nodes + custom rendering, and a second rendering mental model inconsistent with the rest of the (2D, token-driven) app.
**Recommendation.** **Phase 1: `react-force-graph-2d` with a custom-rendered center node** — the brand-mark `Zap` glyph scaled up on a solid `bg-brand` disc with a `--color-brand-primary-glow` halo (the §6 tinted-shadow signature, reused), pinned at the graph center (`fx/fy = 0`). This reads as "the gravitational anchor" without a 3D engine. A true 3D rotating globe is a **v1.5+ flair** candidate. (Validated: 2d `nodeCanvasObject` supports arbitrary custom drawing.)
**PM adjudication needed: YES.** Proposed disposition: *"2D canvas + custom brand-glyph center node for Phase 1; 3D globe → v1.5+."* (If PM wants 3D now, re-scope perf budget in Dim 13.)

## Dimension 4 — Demo storyboard alignment

**Finding.** **The storyboard (Design 12) has NO Constellation scene.** Scenes are 0 (setup), 1 (Action Queue+hero), 2 (explainability), 3 ("the graph and cross-account intelligence" — but the text is *"Switch to the Overall view; the cross-account pattern **card** sits at the top of the right rail"* → this is the Action-Queue Overall view + a pattern Card, **not** the force-directed Constellation), 4 (Per-Profile), 5 (CEO View), 6 (fallback). So the galactic Constellation is **not currently in the demo** at all.
**Recommendation.** Flag for PM: the Session-18 galactic vision is the richest unbuilt surface yet is **absent from the demo storyboard**. Either (a) upgrade Scene 3 to feature the live Constellation (high wow-factor, but raises demo risk if perf/overlays aren't solid), or (b) keep Constellation as a post-demo nav surface and leave Scene 3 as the Overall-view pattern card. Recommend **(b) for the 2026-06-30 demo** (de-risk) with Constellation as a "and there's a galactic map of the whole book" teaser, promoting to a full scene only if Dim-13 perf clears comfortably.
**PM adjudication needed: YES.** Proposed disposition: *"Constellation stays out of the demo critical path (teaser only); revisit Scene-3 upgrade post-perf-benchmark."*

---

# FUNCTIONAL / AGENTIC

## Dimension 5 — Cluster-pattern alert wiring (Skill 10 / spec 027)

**Finding.** Skill 10 (`skill_10_cross_account_pattern_finder.py`) runs weekly, uses the cross-account retriever, and on ≥`min_support` (≥3) customers emits an `action-suggested` with a **pattern_card = {theme, headline, ...}** + `why_oneline`/`why_detail`. **Gap:** the pattern_card stores the *theme and the count* but **not the supporting `account_id`s nor their owning RM** — which the Constellation needs to anchor the alert in the correct RM's orbital region (and to draw the "3+ correlated accounts" cluster). The skill computes the `customers` list internally but discards the ids in the card.
**Recommendation.** (a) **Extend the pattern_card additively** with `support_account_ids: list[str]` (+ optionally derive owning RM via `Account.OwnerId`, already ingested per spec 012). Small `[SPEC-027]` change, back-compatible. (b) The Constellation **renders from pre-computed cards** — it queries existing `action-suggested` events where the payload is a pattern_card (cheap; no re-computation; matches the weekly cadence). It does **not** re-run Skill 10. Click → the existing cross-account pattern card surface (Overall view).
**PM adjudication needed: YES.** Proposed disposition: *"Approve additive pattern_card.support_account_ids ([SPEC-027]); Constellation reads pre-computed cards, no re-compute."*

## Dimension 6 — RM capacity imbalance (new mini-skill)

**Finding.** Nothing today computes per-RM load balance. Required inputs all exist: **per-RM queue depth** (count `action-suggested` not yet decided, by `rm_id` — event log), **per-RM aggregate health** (`pulse.account_health` rows for that RM's accounts — spec 030), **per-RM signal velocity** (events/week by `rm_id` — event log). Output: a proposal pairing an overloaded RM (many red/dim, deep queue) with a steady RM (purple, bandwidth) + a reassignment thesis.
**Recommendation.** This is **surface-specific synthesis, not a reusable signal-library skill** → build it as a **Constellation-overlay composer module** (back-end), a query over event log + `account_health`, NOT a new entry in the signal catalog (it evaluates no signal definition). Emit as `action-suggested` with a new `action_type: "capacity-imbalance"` (reuses the whole Action Queue + audit chain; no new event type). **Effort ≈ 0.5–0.75d** (query + thesis assembly + payload). Note: a reassignment is **org-sensitive** — it must be a *proposal* requiring human approval (§6 rule 3), never auto-acted.
**PM adjudication needed: YES.** Proposed disposition: *"Capacity imbalance = Constellation composer module emitting action-suggested(action_type=capacity-imbalance); not a signal-library skill. ~0.5–0.75d."*

## Dimension 7 — Escalation tier-jump detector

**Finding.** Spec 030 **already emits `health-tier-changed`** with payload `{from_tier, to_tier, composite_score}` + `customer_id`, debounced ≥24h. "Link state worsened past threshold (dim→red, red→critical)" maps directly to a worsening tier transition.
**Recommendation.** **No new threshold logic.** Rank tiers (Healthy>Stable>Watch>At-Risk>Escalated); the escalation overlay = a query over `health-tier-changed` events within a time window where `to_tier` is worse than `from_tier` (optionally ≥2-step jumps for "critical"). Compose into an `action-suggested(action_type="escalation")` anchored to the account node; click → drafts an escalation email to the RM's manager (dispatch handler — spec 032 email path, new template).
**PM adjudication needed: YES.** Proposed disposition: *"Reuse health-tier-changed (worsening filter + window); no new detector. Escalation email uses spec-032 email dispatch + a new template."*

## Dimension 8 — Overlay composer architecture

**Finding.** Three overlay types, three different data origins (Skill-10 cards / capacity module / health-tier-changed), three cadences (weekly / on-demand / event-driven).
**Recommendation.** **Single back-end "Constellation overlay" composer** exposed as one endpoint `GET /constellation/overlays` returning `{cluster_alerts[], capacity_imbalances[], escalation_jumps[]}`, each item carrying the anchor (node id or inter-RM region) + the `action_id` to route to. Rationale vs client-side compose: keeps the RBAC scope filtering + the (non-trivial) aggregation logic server-side and testable; one round-trip; the client stays a thin renderer. Trade-off accepted: the client can't independently refresh one overlay type — acceptable at Phase-1 cadence (overlays poll at the same 10s as the queue, or slower).
**PM adjudication needed: YES.** Proposed disposition: *"Single server-side overlay composer → GET /constellation/overlays (3 arrays). Client renders, does not compose."*

---

# INTERACTION / NAVIGATION

## Dimension 9 — Click → destination matrix

**Finding/Recommendation.** Full matrix (recommended behaviors):

| Target | Click action |
|---|---|
| **Center globe** | Reset/recenter the view (zoom-to-fit). No navigation. |
| **Manager node** | Filter Action Queue to the manager's reports (route `/actions` view=Overall scoped) **or** zoom to that manager's cluster — recommend **zoom-to-cluster** (stays in-surface); double-click → queue filter. |
| **RM node** | Navigate to `/actions` filtered to that RM (`rm_id`); reuses spec-035 My-Queue mechanism. |
| **Account node** | Set `selectedAccountId` (spec-036 context) + navigate to `/` (per-account view). |
| **Link (any state)** | Tooltip with the signal summary (active/inactive/churn + last-signal date). No navigation. |
| **Cluster-pattern overlay** | Route to the cross-account pattern card (Overall view), keyed by the overlay's `action_id`. |
| **Capacity-imbalance overlay** | Route to the **reassignment-draft surface** (new mini-surface — a modal/panel showing the thesis + the proposed move, approve/reject like an action card). |
| **Escalation overlay** | Open the **escalation-email draft** (prefilled to the RM's manager) in a review modal → approve routes through spec-032 dispatch. |

**PM adjudication needed: YES** (one open sub-choice). Proposed disposition: *"Approve matrix as written; confirm manager-node = zoom-to-cluster (single-click) vs queue-filter."*

## Dimension 10 — Talent drill-down (option c)

**Finding.** Locked option-c = talent appears only on account click. react-force-graph supports mutating the node/link set at runtime (add child nodes + links, the simulation re-settles).
**Recommendation.** **Inline orbital expansion**: clicking an account spawns its talent as small nodes orbiting that account (added to the graph data; removed on collapse/deselect). This preserves the "galactic" metaphor and §22 opt-in depth (clean by default, depth on demand). **Fallback** if perf/complexity bites: a side panel listing talent (no graph mutation). Recommend inline-orbit as primary, side-panel as the documented degradation.
**PM adjudication needed: YES.** Proposed disposition: *"Inline orbital talent expansion primary; side-panel as perf fallback."*

## Dimension 11 — Hierarchy enforcement mechanics

**Finding.** Two options: (a) custom **radial force** per tier (managers on inner ring, RMs mid, accounts outer) via `d3Force('radial', forceRadial(r_tier))` + link forces; (b) manual coordinated rigid cluster movement (move a manager → programmatically translate all descendants).
**Recommendation.** **(a) Radial-force constraint** — react-force-graph exposes `d3Force(...)`; add a `forceRadial` keyed to node tier + tune `linkStrength`/`charge` so descendants trail their parent via physics, not bespoke code. (b) is materially more complex (manual transform bookkeeping, fights the simulation) for marginal benefit. **Complexity: medium** for (a), high for (b).
**PM adjudication needed: NO** (engineering call within the spec; recorded for transparency). Default: radial force.

---

# PERFORMANCE / DATA

## Dimension 12 — Data shape / endpoint contracts

**Finding.** No constellation endpoints exist; pulse-api isn't deployed (Week-4). Front-end needs graph + overlays + RBAC scoping.
**Recommendation.** Two endpoints (graph is stable; overlays refresh):
```
GET /constellation            → {
  nodes: [{ id, type: "manager"|"rm"|"account", label, tier?, health?(0..10),
            size, rm_id?, manager_id? }],
  links: [{ source, target, state: "active"|"inactive"|"churn",
            last_signal_at? }]
}
GET /constellation/overlays   → {
  cluster_alerts:        [{ action_id, anchor_rm_id|vertical, theme, support_account_ids }],
  capacity_imbalances:   [{ action_id, overloaded_rm_id, candidate_rm_id, thesis }],
  escalation_jumps:      [{ action_id, account_id, from_tier, to_tier, at }]
}
```
Both **RBAC-scoped server-side** (spec 042 `derive_scope`): RM → own accounts; Manager → reports' accounts; Admin → all. Health 0..10 uses the ratified `(score+100)/20` normalization from spec 030's −100..100. **All of this is Week-4 pulse-api wiring** — Phase-1 front-end builds against fixtures.
**PM adjudication needed: YES.** Proposed disposition: *"Approve the two-endpoint contract (graph + overlays), both RBAC-scoped; Week-4 wiring."*

## Dimension 13 — Performance benchmark plan

**Finding.** ~610 nodes (≈6 managers + ≈18 RMs + ≈585 accounts) with custom node rendering, animated link recoloring, and 3 overlay layers is well beyond spec 041's original 530-flat-node target.
**Recommendation.** **Build a 610-node fixture FIRST and benchmark before locking patterns** (this is implementation step 1, Dim 15). Targets: initial render <2s, pan/zoom ≥30fps (spec-041 DoD). Use **`react-force-graph-2d`** (canvas is far cheaper than SVG/3D at this density). Documented fallbacks, in order: (1) `cooldownTicks`/`warmupTicks` to freeze the sim after settle; (2) level-of-detail labels (render labels only above a zoom threshold); (3) recolor/animate only links in the viewport; (4) cluster accounts under their RM at low zoom, expand on zoom-in; (5) the spec-041 **graceful-degradation MVP** (static positions + click nav) as the floor. Benchmark gates the animated-force decision.
**PM adjudication needed: NO** (plan; gate is internal). Recorded; the benchmark result may surface a PM decision if it forces fallback (4)/(5).

## Dimension 14 — Empty / loading / error / RBAC-subset states

**Finding/Recommendation.**
- **Loading:** the Pulse Bar already breathes (spec 038); show a calm centered "Charting the constellation…" — no spinner (§7).
- **Empty (zero accounts in scope):** "No accounts in your book yet — the constellation fills in as Pulse ingests your customers." (RM with empty book, or fresh org.)
- **RBAC subset (Manager/RM):** render only the in-scope sub-graph (Manager → their RMs + those RMs' accounts, centered on their own sub-tree; the global globe still anchors). Show a quiet scope chip: "Showing your team's book." Server enforces (Dim 12); the front-end never receives out-of-scope nodes.
- **Error:** calm message + retry; fall back to the last good snapshot if cached.
**PM adjudication needed: NO** (standard; recorded). Default as written.

---

# SEQUENCING

## Dimension 15 — Implementation order within spec 041

**Finding/Recommendation.** Build sequence (each a checkpoint):
1. **Library + perf gate** — install `react-force-graph-2d`, `ForceGraph.tsx` wrapper, a **610-node fixture**, benchmark (Dim 13). *Gate: if perf fails, invoke fallback before building further.*
2. **Visual scaffold** — center globe + 3-tier radial hierarchy + node rendering (mock data).
3. **Encodings** — health→node color/size, link-state coloring (Dim 2 tokens), active-mass/dormant-drift forces.
4. **Interaction** — click→destination matrix (Dim 9) + talent drill-down (Dim 10).
5. **Overlay #1** — cluster-pattern (consumes Skill-10 cards; needs Dim-5 pattern_card extension).
6. **Overlay #2** — RM capacity imbalance (composer module, Dim 6).
7. **Overlay #3** — escalation tier-jump (health-tier-changed, Dim 7).
8. **States + RBAC scope + polish** (Dim 14) + DoD verification.

**Structure recommendation (the scope-trade question):** **Do NOT create a separate 041.1 spec.** Absorb the overlay composer + capacity module + the two endpoints into spec 041 as an explicit **"back-end (overlay composer)" section**, since there is exactly one consumer (the Constellation) and the coupling is tight. Spec 041 becomes a front-end section (steps 1-4, 8) + a back-end section (steps 5-7 data + endpoints). This keeps the audit chain single-spec and avoids a thin sub-spec.
**PM adjudication needed: YES.** Proposed disposition: *"Single spec 041 with delineated front-end + back-end(overlay-composer) sections; no 041.1. Build sequence as listed; step 1 is a perf gate."*

---

## Summary — dispositions PM must rule on before implementation

| # | Dimension | PM adj.? | Proposed disposition |
|---|---|---|---|
| 1 | spec-041 rewrite vs Session-18 | **YES** | Ratify Session-18 as the rewrite; written 041 superseded; overlays v1.5+→Phase-1; keep degradation floor |
| 2 | Link-state tokens | **YES** | Approve `--color-link-active/inactive/churn` (§22-justified); no other palette change |
| 3 | Center node | **YES** | 2D canvas + custom brand-glyph globe (Phase 1); 3D globe → v1.5+ |
| 4 | Storyboard alignment | **YES** | Constellation out of demo critical path (teaser); revisit Scene-3 upgrade post-perf |
| 5 | Cluster-pattern wiring | **YES** | Additive `pattern_card.support_account_ids` ([SPEC-027]); render pre-computed cards |
| 6 | RM capacity (mini-skill) | **YES** | Composer module → `action-suggested(action_type=capacity-imbalance)`; not a signal skill; ~0.5–0.75d |
| 7 | Escalation tier-jump | **YES** | Reuse `health-tier-changed` (worsening+window); email via spec-032 + new template |
| 8 | Overlay composer arch | **YES** | Single server-side composer → `GET /constellation/overlays`; client renders only |
| 9 | Click→destination matrix | **YES** | Approve matrix; confirm manager-node = zoom-to-cluster vs queue-filter |
| 10 | Talent drill-down | **YES** | Inline orbital expansion primary; side-panel fallback |
| 11 | Hierarchy mechanics | no | Radial force (engineering default) |
| 12 | Endpoint contracts | **YES** | Two endpoints (graph + overlays), RBAC-scoped; Week-4 wiring |
| 13 | Perf benchmark | no | 610-node fixture-first benchmark; documented fallbacks; gate |
| 14 | Empty/loading/error/RBAC | no | As specified |
| 15 | Build order + structure | **YES** | Single spec 041 (FE + BE sections), no 041.1; sequence w/ step-1 perf gate |

**10 of 15 dimensions need PM rulings** (1-10, 12, 15). Dims 11, 13, 14 are engineering defaults recorded for transparency.

**Halt status:** No halt triggered (read-only; 0 files modified beyond this memo). One item that would warrant a PM design-level conversation rather than a unilateral pick is **Dimension 1 (1f)** — moving the three agentic overlays from v1.5+ into Phase 1 is a genuine scope reversal of the written spec; flagged, not assumed. **Spec 041 implementation does NOT begin until PM ratifies these dispositions in a PM_CONTEXT update.**
