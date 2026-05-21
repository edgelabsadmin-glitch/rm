# Pre-Spec-034 Front-End Shell Audit

**Date:** 2026-05-21
**Type:** Read-only audit session (NOT implementation). Pulled forward ahead of the Gate-2 review per PM direction.
**Scope:** 9 dimensions of front-end-shell readiness, plus halt-trigger evaluation (§6 rule 35, permissive thresholds).
**Artifacts read:** `01_design/00_design_language.md`, `01_design/00_design_language_preview.tsx`, `01_design/agent_presence_variants/04_pulse_bar_breathing.html` (+ siblings), `01_design/11_tech_stack_decisions.md` (ADR-005/006/008), specs 034–045, `PM_CONTEXT.md §6/§14`.
**Build state confirmed:** No front-end exists yet (`03_build/` has no `package.json`, `vite.config`, or `tailwind.config`). Spec 034 has not started. Nothing was created or modified in the build tree by this audit.

---

## ⛔ HALT TRIGGERS — 1 FIRED

Per §6 rule 35 (permissive thresholds):

| Threshold | Limit | Observed | Status |
|---|---|---|---|
| Files touched outside spec scope | >5 | 0 (read-only) | ✅ clear |
| **Design artifacts requiring revision** | **>1** | **2 frontend-relevant (+2 incidental)** | **⛔ FIRED** |
| Locked schema additions | >0 | 0 proposed | ✅ clear |
| Unplanned debugging | >3 h | 0 (no code run) | ✅ clear |

**The "design artifacts requiring revision" trigger fired.** Two frontend-relevant artifacts contain stale guidance that would mislead a spec-034 implementer, plus two incidental (non-frontend) staleness items. This is exactly the class of issue the pulled-forward audit was meant to surface; per the directive I am halting on it and flagging for PM adjudication rather than editing any design artifact. **No spec-034 implementation begun.** Details in dimensions 1 / 6 / 9 and the Incidental Findings section. Recommended dispositions are per-item below; PM adjudicates each before Gate 2 closes.

---

## Dimension 1 — Tier-0 token plumbing (CSS custom properties + Tailwind config)

**Findings.**
- The Tier-0 doc (`00_design_language.md §2`) already declares the **full token set** as CSS custom properties under `:root` — brand (8 purple variants), surfaces (9), text (8), borders (4), tier-risk (9). Plus motion tokens (§7) and a font stack (§3). This is the single source of truth and is build-ready as a `tokens.css` `@layer base` file.
- **Appendix A** sketches the `tailwind.config.ts` `theme.extend` (colors.brand.*, colors.surface.*, borderRadius 2.5xl/4xl, boxShadow xl-brand/2xl-shell, fontFamily). Spec 034 DoD line "all §2 tokens accessible as `bg-brand`, `text-brand-glow`" maps directly to this.
- **GAP — the preview does NOT use tokens.** `00_design_language_preview.tsx` is written entirely in **literal arbitrary Tailwind values**: `bg-[#6B46C1]`, `bg-[#6B46C1]/10`, `border-[#6B46C1]/25`, `shadow-[#6B46C1]/20`, `bg-[#6B46C1]/7`, `bg-[#4B2E91]`, `rounded-[2rem]`, `bg-slate-50/80`. It cannot be lifted verbatim into a token-driven build — every literal must be migrated to the named Tailwind token (`bg-brand`, `bg-brand-muted`, `border-brand-edge`, `shadow-xl-brand`, `bg-brand-ghost`, `bg-brand-deep`) or it defeats the token layer and reintroduces the drift §2 explicitly calls out.
- **Decision needed — two valid plumbing approaches, and they overlap:**
  - **(A) Tailwind theme tokens** (Appendix A): semantic utility classes (`bg-brand`). Best for the ~90% of static styling.
  - **(B) CSS custom properties** (`§2 :root`): required for the *dynamic* values Tailwind can't express statically — the conic-gradient angle (`conic-gradient(white {angle}deg, …)`), the signal-vector bar width (`width: {pct}%`), and any runtime-themed value. These stay inline-style/CSS-var driven.
  - Recommended: ship **both** — generate `tailwind.config.ts` from Appendix A for static utilities, AND emit a `tokens.css` of the `§2 :root` variables so dynamic/inline styles and any `bg-[--color-…]` arbitrary references (the doc's own §8 primitives use `bg-[--color-brand-primary]` syntax) resolve. The two are complementary, not either/or.

**Disposition recommendation (D1):** Approve the dual approach (Tailwind theme config + `tokens.css` custom properties). Spec 034 generates `tailwind.config.ts` from Appendix A and a `tokens.css`; **mandate token migration of the preview** (literals → named utilities) as part of 034's shell scaffold, not a later cleanup. **PM adjudicates.**

---

## Dimension 2 — Inter font loading (no `next/font`; we're on Vite)

**Findings.**
- **Already decided in Tier-0 §3** (and §6 design rule 17): "Phase 4 ships Inter via `@fontsource-variable/inter` for predictable rendering; the system humanist stack remains the fallback." So the audit question is effectively pre-answered: **npm `@fontsource-variable/inter`**, not Google Fonts CDN, not hand-rolled self-host.
- This is the most performant + brand-aligned choice for a Vite SPA: it self-hosts the variable font as a build asset (no third-party CDN round-trip, no FOUT from an external request, no privacy/GDPR concern of Google Fonts), tree-shakes to the weights used (400/500/600/700 per §3), and is imported in `main.tsx` (`import '@fontsource-variable/inter'`). `next/font` is N/A (Vite, not Next).
- `--font-mono` (JetBrains Mono, for inline-tag voice) similarly → `@fontsource-variable/jetbrains-mono`, loaded only where the `<num>`/date/ID renderer mounts.

**Disposition recommendation (D2):** Confirm `@fontsource-variable/inter` (+ `@fontsource-variable/jetbrains-mono`), self-hosted via Vite, system stack as fallback. No open decision — Tier-0 §3 already locks it. **PM confirms (low-risk ratification).**

---

## Dimension 3 — framer-motion wiring (per-component vs root AnimatePresence)

**Findings.**
- Tier-0 §7 establishes **exactly one** state-transition motion for Phase 1/2.5: the **fade-and-lift** (`initial={{opacity:0,y:10}} → animate={{opacity:1,y:0}}`, 250ms, ease-out). The preview applies it as a **per-component** `<motion.div key={selected.name}>` keyed on the selected account — a re-mount transition, no `AnimatePresence` needed (no exit animation).
- The **Pulse Bar breathing** (§8.14) is **NOT framer-motion** — it is pure **CSS `@keyframes`** (`pb-breathe` 2s, `pb-heartbeat` 600ms) toggled by a `data-state` attribute. The canonical render `04_pulse_bar_breathing.html` confirms CSS-only. These two motion systems do not compose or conflict: framer-motion handles content-card entrances; CSS keyframes handle the chrome-level bar.
- **Canonical pattern:** per-component `motion.*` for card/content entrances (keyed re-mounts); **no** root `AnimatePresence` is required in Phase 1 because the only motions are enter-on-mount, not exit-on-unmount. `AnimatePresence` becomes warranted only if/when a surface needs **exit** animation (e.g., an Action Queue card animating *out* on approve/reject — §35's "card leaves the queue"). Spec 035 may introduce that; if so, wrap *that list* in a local `AnimatePresence`, not the app root.
- The fade-and-lift §22 reference and the Pulse Bar §8.14 motion therefore live in different layers and need no shared orchestration.

**Disposition recommendation (D3):** Spec 034 installs `framer-motion`, ships the fade-and-lift as a small reusable `<FadeLift>` wrapper, and keeps the Pulse Bar on CSS keyframes. Defer `AnimatePresence` to the first surface that needs exit motion (likely spec 035), scoped locally. Respect §7 rule 6 (reduced-motion fallback) at the wrapper level. **PM adjudicates (low-risk).**

---

## Dimension 4 — Routing structure (React Router v6 route tree + role-gating)

**Findings — §14 nav surfaces (locked):** Three-column hero, Action Queue, Per-account view (opt-in depth), CEO View, Constellation view (dedicated nav surface), Submission UI, Signal Performance admin (Layer 8 M1), Outcome tracking admin (Layer 8 M3). Plus auth/login (pre-shell).

**Proposed React Router v6 tree (nested layouts):**
```
<RouterProvider>
  /login                       → <LoginPage>            (pre-shell; no Pulse Bar)
  /  (element=<AppShell>)      → chrome: header + Pulse Bar + 3-col grid
     index → /accounts (redirect)
     /accounts                 → <HeroDeepView>         (left rail + hero + Action Queue rail; the preview layout)
     /accounts/:accountId      → same shell, selected account driven by URL param
     /queue                    → <ActionQueuePage>      (dedicated full Action Queue; spec 035)
     /constellation            → <ConstellationView>    (spec 041; route confirmed in 041)
     /ceo                      → <CEOViewPage>           (spec 040; role-gated)
     /submit                   → <SubmissionUI>          (spec 039 — SEE HALT / dim 9: Slack-vs-route)
     /admin (element=<AdminLayout>)  role-gated: admin only
        /admin/signals         → <SignalPerformance>    (spec 044)
        /admin/outcomes        → <OutcomeTracking>      (spec 045)
        /admin/settings        → <Settings> (kill switch UI — spec 010 surface)
  *                            → <NotFound>
```
**Role-gating (per spec 042 `derive_scope` + Design 09 three tiers):**
- `/admin/*` — **Admin only** (Signal Performance, Outcome tracking, Settings/kill-switch).
- `/ceo` — **CEO/Admin** (Design 08 is the leadership surface; Manager may get a scoped view — Q to confirm).
- `/accounts`, `/queue`, `/constellation`, `/submit` — all authed roles, but **data is scope-filtered** server-side by `derive_scope` (RM = own book; Manager = reports + own; Admin = all). The front-end gates *visibility of admin routes*; the back-end gates *data*. Front-end must not be the security boundary (§6 rule 7).
- Spec 034 builds a `<ProtectedRoute>` + `<RoleGate role="admin">` wrapper; the **real** enforcement is spec 042/043 server-side. The shell's gating is UX (hide what you can't use), not security.

**Note:** Spec 042's `derive_scope` is the canonical role source; my spec-031 Action Queue API currently uses a **placeholder header `Caller`** (X-User-Id/X-User-Role) — the front-end must not hard-code roles; it reads them from the authed session (spec 043) which 042 maps to scope.

**Disposition recommendation (D4):** Approve the route tree above with React Router v6 nested layouts (`<AppShell>` as the chrome layout owning the Pulse Bar; `<AdminLayout>` nested for admin surfaces). Confirm `/ceo` role-gating (CEO/Admin, Manager-scoped?) — minor open question. Resolve the `/submit` ambiguity per dim 9. **PM adjudicates.**

---

## Dimension 5 — Pulse Bar (Breathing) cross-surface implementation

**Findings.** Tier-0 §8.14 is unambiguous and **LOCKED Session 10**: the bar is **"part of the chrome, not the content … does not scroll, does not resize with content, and is identical across every screen"** and **"lives on every screen"** (hero, Action Queue, CEO View, Per-Profile, admin) — **except** login/auth (pre-shell). The canonical `04_pulse_bar_breathing.html` renders it as a single fixed element below the header.

**This decisively answers the question: top-level layout component, NOT per-page.** It mounts **once** in `<AppShell>` (the chrome layout that wraps every authed route), immediately below the header, above the `<Outlet/>`. A per-page composition would (a) violate "identical across every screen," (b) risk the bar going silent on surfaces with no left rail (CEO View — §8.14 explicitly cites this as the variant's advantage over the rejected rail-local V3 indicator), and (c) duplicate the singleton state.

**Dependency surfaced (→ dim 9):** Spec 038 (the bar's behavior) requires a back-end **`GET /events/stream` (SSE or WebSocket)** broadcasting `agent_state_change` + `action_suggested_count`, with graceful degradation to polling. That endpoint **does not exist yet** (spec 001's FastAPI has no streaming route). Spec 034 should mount the **bar element + a state context provider** in `<AppShell>` now (idle default), leaving the live transport to spec 038 — but 034's shell must reserve the mount point and the `PulseStateProvider` so 038 is a drop-in.

**Disposition recommendation (D5):** Approve top-level `<AppShell>`-level singleton (CSS-keyframes bar + `PulseStateProvider` context, idle by default in 034). Live SSE/WebSocket wiring stays in spec 038. Flag the `/events/stream` back-end endpoint as a spec-038 prerequisite (new FastAPI route) — note in Gate-2 report. **PM adjudicates.**

---

## Dimension 6 — Component library scope (shadcn vs custom boundary)

**Findings — a genuine tension to resolve:**
- The preview imports shadcn aliases: `@/components/ui/card`, `@/components/ui/button`. Tier-0 §12 #1 says **"Pulse uses shadcn components as substrate, but always customizes tokens"** — i.e., shadcn-as-copy-in (you own the code), not shadcn-as-dependency.
- **BUT ADR-005 (Design 11) says "Component library: build small in-house (no MUI/Antd; the design language is too specific)"** and does **not mention shadcn at all.** These are reconcilable (shadcn is copy-in, so it *is* "in-house" code you own — unlike MUI/Antd which are runtime deps), but ADR-005's wording predates the Tier-0 shadcn assumption and reads as "don't use a component library." **This is one of the artifacts the halt trigger flags** (dim 6 / ADR-005).
- **shadcn provides (use as substrate, re-tokenized):** Button, Card, Dialog/Sheet (modals, filter panel), DropdownMenu (filter chips), Badge (→ re-skin to Pill/RiskBadge), Input (search field), Tabs, Tooltip, Avatar, Toast (Sonner) for non-bar notifications.
- **Custom components (no shadcn equivalent; Tier-0 §8 freezes their contract):**
  - **CompositeHealthRing** — 270° conic-gradient ring (§8.8; spec 036 names `CompositeHealthRing.tsx`). Pure custom.
  - **PulseBar** — chrome breathing bar (§8.14; spec 038). Pure custom (CSS keyframes).
  - **Action Queue card** — the specific icon-container + chevron + pill + ghost-Review composition (§ preview right-rail; spec 035 "exactly matches preview"). Custom composition over shadcn Card.
  - **Hero card** — purple-on-purple brand moment + pulse-facts strip (§8.7). Custom.
  - **Signal vector bar** — linear track+fill (§8.9). Custom (trivial).
  - **Verified-theme row, Trust-layer callout, Pill, RiskBadge** — custom token-skinned primitives (§8.1/8.2/8.10/8.13).
  - **Constellation node/graph** — force-graph library (Q151), fully custom.
  - **Inline-tag voice renderer** — the 5-tag (`<num>/<bad>/<good>/<quote>/<em>`) whitelist parser (§10; spec 035). Custom, security-sensitive (escape non-whitelist).
- **Boundary statement:** shadcn for generic interactive primitives (buttons, menus, dialogs, inputs, toasts); **everything brand-signature is custom** (ring, bar, hero, cards, pills, badges, signal bars, constellation, tag renderer). The §12 "never ship default shadcn look" rule means even the shadcn ones get full token re-skin.

**Disposition recommendation (D6):** **Reconcile ADR-005 with Tier-0 §12** — confirm "shadcn-as-copy-in substrate + custom brand components," and update ADR-005's "build small in-house" wording so it doesn't read as "no shadcn." Adopt the custom-vs-shadcn boundary above. **PM adjudicates (artifact revision: ADR-005).**

---

## Dimension 7 — State management

**Findings.**
- **Server state: React Query (TanStack Query)** — confirmed direction; covers Action Queue list/detail, profiles, health, CEO aggregates, signal/outcome admin. Handles caching, refetch, optimistic updates (approve/reject), and the polling fallback for the Pulse Bar count.
- **Selected-account state (shared, cross-column):** the hero (036), per-account view (037), and left rail all key off the selected account. Two clean options: **(A) URL state** via `/accounts/:accountId` (react-router param) — recommended, makes selection bookmarkable/shareable and is the natural router idiom; or (B) a small context. Recommend **URL param as source of truth** + a thin `useSelectedAccount()` hook reading the param.
- **Pulse Bar state (global, ephemeral):** idle/processing/`action_suggested_count` — a small **React context** (`PulseStateProvider` in `<AppShell>`), fed by spec-038's SSE. Not server state, not URL state → context is correct. This is the one genuine *global* state need.
- **Local form state:** the modify-action form (spec 035), submission UI (039), settings (010). **`react-hook-form`** for the modify form (field-level validation against `modifiable_fields`); plain `useState` for trivial toggles. No need for Redux/Zustand in Phase 1.
- **Persistent client state:** Tier-0/Design 03 Q36 — **filter-chip selections persisted in `localStorage`** (tier/customer/skill/owner filters on the Action Queue). That is the only localStorage need. **No IndexedDB** need in Phase 1 (no offline, no large client cache — React Query holds server cache in memory).
- **Auth/session state:** from spec 043 (Supabase Auth client) — a session context; React Query reads the token for API calls.

**Disposition recommendation (D7):** Approve: React Query (server) + URL param (selected account) + small contexts (PulseState, auth/session) + react-hook-form (modify/submit forms) + localStorage (filter persistence, Q36). No global store library, no IndexedDB. **PM adjudicates (low-risk).**

---

## Dimension 8 — Vercel deploy domain

**Findings.** ADR-005 + Q108 confirm **Vercel free tier**. The repo is `github.com/edgelabsadmin-glitch/rm`, so the Vercel default would be `rm.vercel.app` (or a Vercel-suffixed variant if taken). Considerations: (a) the product is **white-labeled** (§6 product rule 1 / §11) — "rm" is an internal repo name, not the product name "Pulse", and a `rm.vercel.app` URL leaks nothing but is off-brand; (b) Phase 1 is an internal demo for ~8–10 RMs + CEO, not public; (c) a custom domain (e.g., `pulse.onedge.co` or `pulse-internal.onedge.co`) is the brand-aligned end state but requires DNS the operator controls.

**Disposition recommendation (D8):** **Phase 1: rename the Vercel project to `pulse` (→ `pulse.vercel.app`) rather than keep `rm.vercel.app`** — trivial, brand-aligned, avoids the internal "rm" name in any shared demo URL. **Defer a custom `*.onedge.co` domain to post-demo** (needs operator DNS; not on the critical path). Low-stakes; PM picks. **PM adjudicates.**

---

## Dimension 9 — Cross-spec dependencies inheriting from 034

**Findings — downstream specs and what they inherit/assume:**
| Spec | Depends on 034 | Inherited assumption / risk |
|---|---|---|
| 035 Action Queue UI | ✅ (+031, 038) | Card "exactly matches preview"; needs the inline-tag renderer; consumes 031 API (built); needs selected-account + queue state. Likely first to need `AnimatePresence` (card exit on approve/reject). |
| 036 Hero card UI | ✅ (+030) | "Selected account from left rail (**state hook**)" — assumes the dim-7 selected-account mechanism exists in 034. Names `CompositeHealthRing.tsx`. |
| 037 Per-account view | ✅ (+029,030,036) | Panel open/close state machine; opt-in depth; assumes 034 shell + 036 hero. |
| 038 Pulse Bar | ✅ | **Assumes a back-end `GET /events/stream` SSE/WebSocket that does NOT yet exist** (new FastAPI route). Assumes 034 reserves the chrome mount point + state context (dim 5). |
| 039 Submission UI | ❌ (001,011,012,020) | **CONFLICT:** titled "Slack slash command" but **Slack is OUT for v1** (locked: surfaces = dashboard + email + SFDC tasks). §14 line 473 still labels it "(Slack slash command)". It does **not** depend on 034 — so it's currently scoped as a non-shell ingestion path, contradicting §14 listing it as a UI surface. Needs re-scoping to a dashboard route (`/submit`) under the shell. **Halt-flagged artifact.** |
| 040 CEO View | ✅ (+030,008,029,038) | Role-gated route `/ceo`; assumes shell + Pulse Bar; purple-rich brand surface. |
| 041 Constellation | ✅ (+030,038) | New route `/constellation`; force-graph lib (Q151 — already filed); graceful-degradation MVP. Assumes shell + Pulse Bar. |
| 042 RBAC | (001,008,012) | Provides `derive_scope` — the canonical role source the shell's route-gating reads. 034's gating is UX only; 042 is the security boundary. |
| 043 OAuth | (— ) | **034's auth flow DoD ("Google Workspace OAuth completes") depends on 043, which is NOT built.** 034 can scaffold `<ProtectedRoute>` + a session hook, but the live OAuth handshake needs 043. Sequencing risk: 034 DoD line 28 cannot fully pass without 043. |

**Two unstated/at-risk assumptions worth PM attention:**
1. **038 ⇒ a new back-end streaming endpoint** (`/events/stream`) — not in any built spec; not in 034's scope. Must be slotted (likely a 038 sub-task on the FastAPI side) or the bar degrades to polling-only from day one.
2. **034 ⇄ 043 ordering** — 034's auth DoD presumes 043. Either build 043 first/concurrently, or explicitly de-scope 034's auth DoD to "scaffold + stub session" and move "OAuth completes" to a 043-gated checkpoint.

**Disposition recommendation (D9):** (a) Re-scope spec 039 to a shell route `/submit` (drop "Slack slash command"; align to no-Slack lock + §14) — **artifact revision**. (b) Decide 034↔043 sequencing (recommend: 034 ships shell + stubbed session; "OAuth completes" DoD moves to a 043 checkpoint). (c) File the `/events/stream` endpoint as an explicit 038 back-end prerequisite. **PM adjudicates each.**

---

## Incidental findings (outside the 9 dimensions; surfaced in passing)

1. **ADR-008 + ADR roll-up table say "self-hosted n8n"** — superseded by **Activepieces** (ADR-002). Stale; non-frontend. *(2nd of the design-artifact-revision items; informational — recommend a sweep of Design 11 for n8n→Activepieces.)*
2. **§14 vs spec-012 object count discrepancy:** §14 line 450 says `affectlayer__Engagement__c` was **REMOVED Session 13** (SFDC list shows 7 objects), but the spec-012 adapter (`core/adapters/sfdc.py`) and my own Spike-6 verification treat it as the **8th in-scope object**. The Spike-6 "0 rows in 7-day window" result is consistent with the object being deprecated. **Recommend PM reconcile** — either re-confirm Engagement in scope (update §14) or drop it from the adapter (update spec 012 + the Spike-6 memo's framing). Non-frontend; flagged for completeness.

---

## Disposition summary (PM adjudicates each before Gate 2 closes)

| # | Dimension | Recommendation | Type |
|---|---|---|---|
| D1 | Token plumbing | Dual: Tailwind theme (Appendix A) + `tokens.css` `:root`; migrate preview literals → named utilities in 034 | Approve |
| D2 | Inter font | `@fontsource-variable/inter` (self-host) + JetBrains Mono; already locked §3 | Ratify |
| D3 | framer-motion | Per-component `<FadeLift>`; CSS keyframes for bar; defer `AnimatePresence` to first exit-motion surface | Approve |
| D4 | Routing | React Router v6 nested `<AppShell>`/`<AdminLayout>` tree as drawn; admin-only `/admin/*`; data scoped server-side | Approve + confirm `/ceo` gating |
| D5 | Pulse Bar | Top-level `<AppShell>` singleton + `PulseStateProvider` (idle in 034); live SSE in 038 | Approve |
| D6 | Component lib | shadcn-as-copy-in substrate + custom brand components (boundary listed); **reconcile ADR-005 wording** | Approve + **revise ADR-005** |
| D7 | State mgmt | React Query + URL param (selected account) + small contexts + react-hook-form + localStorage (Q36) | Approve |
| D8 | Vercel domain | Rename project → `pulse.vercel.app`; defer custom `*.onedge.co` to post-demo | PM pick |
| D9 | Cross-spec | **Re-scope 039 off Slack → `/submit` route**; decide 034↔043 sequencing; file `/events/stream` as 038 prereq | **Revise 039** + sequence |

**Halt status:** 1 trigger fired (>1 design artifact requiring revision: **ADR-005** wording + **spec 039 / §14 Slack framing**; +2 incidental: ADR-008 n8n, §14 Engagement). **No spec-034 implementation has begun and none will until Gate-2 review closes and PM adjudicates these dispositions.** Holding for the Gate-2 report (Friday June 6).
