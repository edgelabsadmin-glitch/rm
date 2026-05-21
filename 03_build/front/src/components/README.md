# Pulse front-end — component library boundary

**Spec 034 deliverable.** Defines what we take from **shadcn/ui** (substrate) vs. what
we build **custom** (Pulse brand-signature). Ratified in the pre-spec-034 audit
(disposition D6) and reconciled into ADR-005 (Design 11 §"Component library").

## The rule

> shadcn/ui for **generic interactive primitives**; **custom** for every
> brand-signature component. Even the shadcn ones are **re-tokened** to Tier-0 —
> we never ship the default shadcn look (Tier-0 §12 #1).

shadcn here is **copy-in, not a runtime dependency**: the CLI writes component
source into `src/components/ui/` and we own/edit it. That is still "in-house code"
in the ADR-005 sense — we just don't hand-roll accessible primitives from scratch.

## Substrate — shadcn/ui (`src/components/ui/`)

Generic primitives. Install on demand via `npx shadcn@latest add <name>`, then
re-token to Tier-0 (§2 colors, §5 radius, §6 shadows). Start set:

| Component | Used for | Tier-0 re-token |
|---|---|---|
| `button` | all buttons | §8.4/8.5/8.6 — solid Edge Purple / purple-edged outline / ghost (✅ in repo) |
| `card` | card containers | §8.3 — white, `line-subtle` border, `shadow-sm`, `rounded-3xl`, `p-5` (✅ in repo) |
| `dialog` | modals (modify-action, confirmations) | rounded-3xl, brand focus ring |
| `dropdown-menu` | filter chips, row actions | brand-muted active state |
| `input` | search field, form fields | §8.11 — pill, `surface-tinted-row`, `line-strong` |
| `select` | filter selects | match input tokens |
| `badge` | → re-skinned into Pill / RiskBadge | §8.1/8.2 |

> Anything shadcn provides that we need later (tabs, tooltip, avatar, sheet,
> sonner/toast) is added the same way. Toasts (sonner) are the **non-bar**
> notification channel — the Pulse Bar never carries error/success color (§8.14).

## Custom — Pulse brand-signature (`src/components/`)

No shadcn equivalent; the Tier-0 §8 visual contract is the spec. Build these by hand.

| Component | Spec / lock | Status |
|---|---|---|
| `PulseBar` | §8.14 LOCKED — chrome breathing bar, **CSS keyframes** (not framer-motion) | ✅ shipped (034) |
| `AppShell` / `AppShellChrome` | §9.1 two-layer Edge surface; owns the Pulse Bar singleton | ✅ shipped (034) |
| `Header` | §9.2 — brand-mark tinted-shadow tile (§6 #2), nav, Queue badge | ✅ shipped (034) |
| `FadeLift` | §7 — the single fade-and-lift motion wrapper | ✅ shipped (034) |
| `HealthRing` | §8.8 + §6 #27 — 270° conic-gradient ring (`angle = score/10 * 270`) | spec 036 |
| `HeroCard` | §8.7 + §6 #26 — purple-on-purple brand moment, tinted shadow | spec 036 |
| `SignalVectorBar` | §8.9 — linear track+fill | spec 037 |
| `VerifiedThemeRow` | §8.10 | spec 037 |
| `QueueCard` | preview right-rail — icon-container + chevron + pill + ghost Review | spec 035 |
| `AccountCard` | §8.12 — selectable, two states | spec 035/036 |
| `VerdictPill` | §8.1 — active/neutral pill | spec 035 |
| `RoleBadge` | tier chip (Admin/Manager/RM) | spec 042 surface |
| `TrustLayerCallout` | §8.13 | spec 035 |
| `ConstellationNode` | force-graph node (lib per Q151) | spec 041 (placeholder until then) |
| `TagRenderer` | §10 — the 5-tag inline-voice whitelist (`<num>/<bad>/<good>/<quote>/<em>`); **escapes** anything off-whitelist (security-sensitive) | spec 035 |

## Tinted-shadow invariant (§6)

`shadow-xl-brand` (the Edge-Purple-tinted shadow) is restricted to **exactly two
elements**: the **hero card** and the **brand-mark tile**. Do not apply it
anywhere else — diffusing it weakens the signature. All other elevation uses
`shadow-sm` / `shadow-lg shadow-slate-200` / `shadow-2xl-shell`.

## Iconography

`lucide-react` only (Tier-0 Appendix B / §12 #9). No FontAwesome, Material, heroicons.
