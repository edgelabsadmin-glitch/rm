# Tier-0 Design Language System

**Phase:** 2.5 — Brand Alignment + Agent Presence Pass
**Status:** Locked Session 8 (visual direction) → codified Phase 2.5
**Source of truth:** This file. All visual artifacts in `01_design/` reference tokens by name from here.

---

## 1. Brand anchor

Pulse looks like a first-party Edge surface. Reference: [onedge.co](https://onedge.co) + `01_design/00_design_language_preview.tsx`. The design language below is the source of truth for every visual decision in Pulse.

Pulse's visual identity rests on three principles, extracted from the user-provided React preview and confirmed by onedge.co:

1. **Restrained purple, generous greyish-white.** Edge Purple appears as accent + hero brand moment + iconography color. Surfaces are warm-neutral (`#FAFAFA` / `#F5F5F7` / white), never grey-cold. Purple is *the highlight*, not the wallpaper.
2. **Calm, confident, human-centered tone.** From onedge.co: "Stop searching for talent. *Start building your team.*" — assured, conversational, comfortable with italics for emphasis. Pulse inherits this tone in microcopy.
3. **Evidence-led, opt-in depth.** The hero communicates situation. The Action Queue communicates next-best-action. Deeper context (signal vector, themes, briefs) reveals on click. No information firehose.

Anything below that conflicts with the React preview should be reconciled toward the preview; anything not in the preview is documented here for the first time.

---

## 2. Color tokens

Tokens are declared as CSS custom properties, Phase-4-build-ready. Each token has a single source of truth here. Tailwind utility classes in the preview map to these tokens; Phase 4 generates a `tailwind.config.ts` from this file.

```css
:root {
  /* ─── Brand: Edge Purple ─────────────────────────────────────── */
  --color-brand-primary:        #6B46C1;                /* primary brand moment — hero card, brand mark, CTA bg, signal-vector fill, icon accents */
  --color-brand-primary-hover:  #5B35B1;                /* button hover state (preview: bg-[#6B46C1] hover:bg-[#5B35B1]) */
  --color-brand-primary-muted:  rgba(107, 70, 193, 0.10); /* icon-container backgrounds, ghost-button hover, brief-card tinted blocks */
  --color-brand-primary-ghost:  rgba(107, 70, 193, 0.07); /* used for tinted block backgrounds (brief cards) and ghost-button hover states — LOCKED Session 10 (Decision 32); two literal occurrences in the React preview promoted to a named token to prevent drift */
  --color-brand-primary-soft:   rgba(107, 70, 193, 0.15); /* trust-layer callout border */
  --color-brand-primary-edge:   rgba(107, 70, 193, 0.25); /* outline-button border, selected-account border, active-pill border */
  --color-brand-primary-glow:   rgba(107, 70, 193, 0.20); /* tinted shadow on hero card — Edge brand-shadow signature */
  --color-brand-primary-deep:   #4B2E91;                /* inner ring of the conic health gauge */

  /* ─── Surfaces ───────────────────────────────────────────────── */
  --color-surface-page:         #FAFAFA;                /* page background (outermost) */
  --color-surface-chrome:       #F5F5F7;                /* outer-shell background; rounded-[2rem] card containing the whole app */
  --color-surface-card:         #FFFFFF;                /* cards, panels, white-card-on-tinted-rail */
  --color-surface-sidebar:      rgba(248, 250, 252, 0.80); /* tinted sidebar background — slate-50/80 from preview */
  --color-surface-sidebar-soft: rgba(248, 250, 252, 0.70); /* right-rail variant — slate-50/70 from preview */
  --color-surface-tinted-row:   rgb(248, 250, 252);     /* verified-themes row background — slate-50 */
  --color-surface-track:        rgb(241, 245, 249);     /* progress/composite bar track — slate-100 */
  --color-surface-glass-light:  rgba(255, 255, 255, 0.12); /* inner pulse-facts card on hero (against purple) */
  --color-surface-glass-border: rgba(255, 255, 255, 0.15); /* border of pulse-facts cards on hero */

  /* ─── Text ───────────────────────────────────────────────────── */
  --color-text-primary:         rgb(2, 6, 23);          /* slate-950 — body, h1, h2, account names */
  --color-text-secondary:       rgb(100, 116, 139);     /* slate-500 — eyebrows, metadata, supporting copy */
  --color-text-muted:           rgb(148, 163, 184);     /* slate-400 — chevrons, faint icons */
  --color-text-on-brand:        #FFFFFF;                /* white text on purple — hero, primary buttons */
  --color-text-on-brand-soft:   rgba(255, 255, 255, 0.85); /* hero subtitle */
  --color-text-on-brand-faint:  rgba(255, 255, 255, 0.65); /* tiny eyebrow on hero — "HEALTH" inside ring */
  --color-text-on-brand-strip:  rgba(255, 255, 255, 0.80); /* pulse-facts strip text — white/80 */

  /* ─── Borders ────────────────────────────────────────────────── */
  --color-border-subtle:        rgb(241, 245, 249);     /* slate-100 — header divider, between aside + main */
  --color-border-strong:        rgb(226, 232, 240);     /* slate-200 — outer shell, search field, neutral pills */
  --color-border-transparent:   transparent;            /* unselected account-list cards */
  --color-border-brand:         rgba(107, 70, 193, 0.35); /* selected account card border — purple/35 */

  /* ─── Tier risk colors (rose / amber / emerald) ──────────────── */
  --color-risk-high-bg:         rgb(255, 241, 242);     /* rose-50 */
  --color-risk-high-fg:         rgb(225, 29, 72);       /* rose-700 (the preview says rose-700; rose-50 bg + rose-700 fg + rose-200 border) */
  --color-risk-high-border:     rgb(254, 205, 211);     /* rose-200 */

  --color-risk-medium-bg:       rgb(255, 251, 235);     /* amber-50 */
  --color-risk-medium-fg:       rgb(180, 83, 9);        /* amber-700 */
  --color-risk-medium-border:   rgb(253, 230, 138);     /* amber-200 */

  --color-risk-low-bg:          rgb(236, 253, 245);     /* emerald-50 */
  --color-risk-low-fg:          rgb(4, 120, 87);        /* emerald-700 */
  --color-risk-low-border:      rgb(167, 243, 208);     /* emerald-200 */
}
```

**Justifications for tokens beyond the literal preview:**
- `--color-brand-primary-ghost` (purple/7) is observed in the preview at *two* locations — the brief-card tinted block (`bg-[#6B46C1]/7`) and the ghost-button hover (`hover:bg-[#6B46C1]/7`). Pulling it out as a named token prevents drift.
- `--color-brand-primary-edge` (purple/25) is the outline-button + selected-account border. Two locations, one token.
- `--color-brand-primary-glow` (purple/20) is the *tinted shadow* on the hero card and the brand mark. This is **Pulse's signature shadow** and gets a dedicated token.
- `--color-text-on-brand-strip` (white/80) is the pulse-facts strip text inside the hero. Distinct from `--color-text-on-brand-soft` (white/85, hero subtitle).
- Tier-risk borders are inferred from Tailwind's `border-rose-200` / `border-amber-200` / `border-emerald-200` classes in the preview's `RiskBadge` component.

---

## 3. Typography

### Family

```css
:root {
  --font-sans:  "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  --font-mono:  "JetBrains Mono", "SF Mono", Menlo, Monaco, "Cascadia Mono", Consolas, monospace;
}
```

**Primary type family (LOCKED Session 10, Decision log entry 32 + §6 design rule 17): Inter** (https://rsms.me/inter/). Fallback stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif`. The single `--font-sans` declaration above is the only line that needs to change if the user later prefers a different humanist face (Söhne, Geist, GT Walsheim, IBM Plex Sans, etc.) — the rest of Pulse references the token. Phase 4 ships Inter via `@fontsource-variable/inter` for predictable rendering; the system humanist stack remains the fallback. `font-mono` is reserved for inline-tag voice elements (`<num>`, dates, IDs) per Design 04 reasoning-capture spec — lifted from rm-intelligence-agent's JetBrains Mono pairing.

**Rationale.** The React preview does not declare a font-family explicitly — it relies on Tailwind's `font-sans` default (system humanist stack). onedge.co's marketing site appears to use Inter or a near-equivalent (confirmed via Phase 2.5 onedge.co cross-reference). Inter as primary + system fallback gives Pulse predictable rendering across platforms while leaving the swap path open.

**Weights used:** 400 (regular), 500 (medium), 600 (semibold), 700 (bold). The preview uses 600 (`font-semibold`) most heavily; 700 reserved for the conic-ring center number.

### Type scale

Concrete values for Phase 4 reference. Tailwind utility names listed for cross-walk.

| Role | Tailwind class | Size | Line-height | Weight | Letter-spacing | Used for |
|---|---|---|---|---|---|---|
| **Display** | `text-3xl font-semibold tracking-tight` | 1.875rem / 30px | 2.25rem / 36px | 600 | -0.025em | Hero account name (e.g. "Helix Labs") |
| **Display-on-brand-ring** | (custom) | 1.5rem / 24px | 1.75rem / 28px | 700 | normal | The health-score number inside the conic ring |
| **h2 / card header** | `text-lg font-semibold` | 1.125rem / 18px | 1.75rem / 28px | 600 | normal | "Signal vector", "Verified themes", "Meeting brief", "Action Queue" |
| **Body** | `text-sm` | 0.875rem / 14px | 1.25rem / 20px | 400 | normal | Card body copy, action-card titles (semibold variant), trust-layer copy |
| **Body-leading-5** | `text-sm leading-5` | 0.875rem / 14px | 1.25rem / 20px | 400 | normal | Verified-theme rows, hero subtitle, action-card detail |
| **Body-on-brand** | `text-sm leading-6 text-white/85` | 0.875rem / 14px | 1.5rem / 24px | 400 | normal | Hero subtitle paragraph |
| **Metadata** | `text-xs text-slate-500` | 0.75rem / 12px | 1rem / 16px | 400 | normal | Card metadata, account-list meeting line, pulse-facts strip |
| **Metadata-semibold** | `text-xs font-medium` | 0.75rem / 12px | 1rem / 16px | 500 | normal | Pill body, RiskBadge body, button labels in pills |
| **Eyebrow** | `text-sm font-semibold uppercase tracking-[0.18em] text-slate-500` | 0.875rem / 14px | 1.25rem / 20px | 600 | 0.18em | Sidebar headers — "Accounts", "Action Queue" |
| **Eyebrow-tiny** | `text-[10px] uppercase tracking-widest text-white/65` | 0.625rem / 10px | 1 | 400 | 0.1em | The "HEALTH" label inside the conic ring |

**Tracking discipline.** The preview uses `tracking-tight` on the display + account-list account names (-0.025em), default tracking on body, `tracking-widest` on tiny eyebrows, and a custom `tracking-[0.18em]` on the sidebar header eyebrows. These three levels — tight / default / wide / extra-wide — are the only tracking values Pulse uses. Don't introduce a fifth.

---

## 4. Spacing system

Tailwind's 4px base (`spacing-1 = 0.25rem = 4px`). Pulse's observed scale:

| Token | Value | Used for |
|---|---|---|
| `space-2` | 0.5rem / 8px | Inline icon-to-text gaps |
| `space-3` | 0.75rem / 12px | Tight gaps; eyebrow → content |
| `space-4` | 1rem / 16px | Section spacing inside cards (`mb-4`), card grid gaps (`gap-4`) |
| `space-5` | 1.25rem / 20px | Default card padding (`p-5`) — the most-used padding |
| `space-6` | 1.5rem / 24px | Hero card padding (`p-6`); main column padding |
| `space-7` | 1.75rem / 28px | Header horizontal padding (`px-7`) |
| `space-10` | 2.5rem / 40px | Lg-only header center-search padding (`px-10`) |

**The breathing-room rule.** Cards have generous internal padding (`p-5` is the floor). Outer-shell chrome breathes (`p-6` on the page; `rounded-[2rem]` on the shell). Pulse never crams a card.

---

## 5. Border radius

The bigger the container, the bigger the radius. This is a deliberate visual rhythm — small things tight, big things soft.

| Token | Value | Used for |
|---|---|---|
| `rounded-md` | 0.375rem / 6px | (reserved; not currently used) |
| `rounded-xl` | 0.75rem / 12px | (reserved; not currently used) |
| `rounded-2xl` | 1rem / 16px | Icon-container squares; brief-card tinted blocks; pulse-facts strip cards; brand-mark tile |
| `rounded-3xl` | 1.5rem / 24px | Standard cards (signal vector, verified themes, meeting brief, action items, account list items, trust layer) |
| `rounded-[2rem]` | 2rem / 32px | Hero card; outer shell |
| `rounded-full` | 9999px | Pills, buttons, search field, conic health ring, progress-bar tracks, avatar, RiskBadges, queue-button badges, action-card icon-containers (when inside actions) |

**Note on the conic ring.** The outer ring is `rounded-full` with a conic-gradient background. The inner ring is also `rounded-full`, sized `h-20 w-20` against the outer `h-28 w-28`. Both must be `rounded-full` — squared corners on a conic gradient look broken.

---

## 6. Shadows / elevation

Pulse's elevation language. Note: shadows that carry Edge Purple tinting at lower opacity are a **Pulse identity moment** — never seen on plain shadcn defaults.

| Token | Tailwind | Used for |
|---|---|---|
| `shadow-sm` | `0 1px 2px 0 rgb(0 0 0 / 0.05)` | Quiet cards — signal vector, verified themes, meeting brief, action items |
| `shadow-lg-slate` | `shadow-lg shadow-slate-200` | Selected account card (left rail) |
| `shadow-xl-brand` | `shadow-xl shadow-[#6B46C1]/20` | **Hero card** + **brand-mark tile** — purple-tinted shadow, the Edge brand signature |
| `shadow-2xl-shell` | `shadow-2xl shadow-slate-200/70` | Outer shell — gentle, broad, no color |

**The tinted-shadow rule (LOCKED Session 10, Decision log entry 32 + §6 design rule 23).** The Edge-Purple-tinted shadow (`shadow-xl shadow-[#6B46C1]/20`, token `--color-brand-primary-glow`) is **restricted to exactly two elements**:

1. **The hero card** (the rich purple-on-purple Edge brand moment — `--color-brand-primary` background + tinted shadow). This is Pulse's most-brand moment per screen.
2. **The brand-mark tile** in the header (the purple Zap tile, top-left).

**Do NOT apply this tinted shadow anywhere else.** Not on selected account-list cards, not on the Action Queue cards, not on the conic ring, not on the trust-layer callout, not on the Pulse Bar's heartbeat moment. Diffusing the tinted shadow weakens the signal — the restriction is what gives the signature its meaning. Other elevated elements use the neutral `shadow-lg shadow-slate-200` (selected account card) or `shadow-sm` (standard cards) treatments instead. The tinted-shadow rule is a **brand-identity invariant**, not a stylistic suggestion.

---

## 7. Motion

Pulse's motion principles, codified from the React preview's framer-motion usage:

### Tokens

```css
:root {
  --motion-fast:      200ms;
  --motion-base:      250ms;
  --motion-slow:      400ms;
  --motion-ease:      cubic-bezier(0.16, 1, 0.3, 1);   /* ease-out — default */
  --motion-ease-in:   cubic-bezier(0.4, 0, 1, 1);
}
```

### The single motion pattern in the preview

Account switch:
```tsx
<motion.div
  key={selected.name}
  initial={{ opacity: 0, y: 10 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.25 }}
/>
```

A **fade-and-lift**, 250ms, ease-out (framer-motion default). This is the only state-transition motion in Pulse Phase 1 + 2.5. New cards / new content does this; everything else is static.

### Motion rules

1. **State transitions are 200–300ms.** Below 200ms feels twitchy; above 300ms feels slow on a working surface.
2. **Default to ease-out.** Things enter quickly, settle softly. Never use ease-in-out for state transitions (it makes them feel mushy).
3. **No spinning wheels.** Loading states use the alive-presence indicator (Phase 2.5 variant) — never a spinner.
4. **No "AI thinking…" dots.** Pulse's reasoning is invisible by default; presence is conveyed by ambient motion (see Section 8 → "Alive-presence indicator placeholder").
5. **No auto-playing motion on page load.** First render is static. Motion happens *in response to interaction*.
6. **Reduced-motion media-query support** is a Phase 4 task — every motion declaration falls back to instant if `prefers-reduced-motion: reduce` is set.

---

## 8. Component primitives

Copy-pasteable component compositions, observed from the React preview. Phase 4 implements these as React components; Phase 2.5 freezes the visual contract.

### 8.1 Pill

Used for tiny status chips and metadata tags. Two variants.

**Active (purple-tinted):**
```html
<span class="rounded-full border border-[--color-brand-primary-edge] bg-[--color-brand-primary-muted] px-3 py-1 text-xs font-medium text-[--color-brand-primary]">
  Today
</span>
```

**Neutral:**
```html
<span class="rounded-full border border-[--color-border-strong] bg-white px-3 py-1 text-xs font-medium text-slate-600">
  RM approval
</span>
```

- Padding: `px-3 py-1` (12px / 4px)
- Border: 1px
- Text: 12px / 500
- Radius: pill (rounded-full)

### 8.2 RiskBadge

Tier-colored risk indicator. Three variants — High (rose), Medium (amber), Low (emerald).

```html
<span class="rounded-full border px-2.5 py-1 text-xs font-semibold
             bg-[--color-risk-high-bg] text-[--color-risk-high-fg] border-[--color-risk-high-border]">
  High
</span>
```

(Substitute `medium` or `low` for Medium / Low variants.)

- Padding: `px-2.5 py-1` (10px / 4px) — slightly tighter than Pill on x-axis
- Border: 1px tier-color
- Text: 12px / 600 (heavier than Pill — RiskBadge is a status, Pill is a label)

### 8.3 Card

The Pulse card. Crisp white, slate-100 border, soft shadow, generous radius.

```html
<div class="rounded-3xl border border-[--color-border-subtle] bg-[--color-surface-card] shadow-sm">
  <div class="p-5">
    ... content ...
  </div>
</div>
```

- Radius: `rounded-3xl` (24px)
- Border: 1px slate-100
- Padding: `p-5` (20px) — the floor
- Shadow: `shadow-sm`

**Selected-state variant** (for account-list items):
```html
<div class="rounded-3xl border border-[--color-border-brand] bg-white shadow-lg shadow-slate-200 p-4">
  ...
</div>
```

(Note: account-list cards use `p-4` not `p-5` because their density is higher.)

### 8.4 Button — primary

```html
<button class="rounded-full bg-[--color-brand-primary] px-4 py-2 text-sm font-medium text-white
               hover:bg-[--color-brand-primary-hover] transition">
  Generate brief
</button>
```

- Default background: `--color-brand-primary`
- Hover: `--color-brand-primary-hover` (#5B35B1 — the named hover state from the preview)
- Radius: `rounded-full`
- No gradient. No drop shadow. Solid purple, white text, hover-darken.

### 8.5 Button — outline

```html
<button class="rounded-full border border-[--color-brand-primary-edge] bg-transparent px-4 py-2
               text-sm font-medium text-[--color-brand-primary]
               hover:bg-[--color-brand-primary-ghost] transition">
  Queue
</button>
```

### 8.6 Button — ghost

```html
<button class="rounded-full bg-transparent px-3 py-2 text-sm font-medium text-[--color-brand-primary]
               hover:bg-[--color-brand-primary-ghost] transition">
  Review
</button>
```

(Note: hover background is `--color-brand-primary-ghost` (purple/7) — observed twice in the preview, named here.)

### 8.7 Hero card

The richest brand moment. Solid Edge Purple, white text, purple-tinted shadow.

```html
<div class="rounded-[2rem] bg-[--color-brand-primary] p-6 text-white shadow-xl shadow-[--color-brand-primary-glow]">
  ... hero content ...
</div>
```

- Background: solid `--color-brand-primary`
- Padding: `p-6` (24px)
- Radius: `rounded-[2rem]` (32px)
- Shadow: `shadow-xl shadow-[--color-brand-primary-glow]` — the tinted shadow signature

### 8.8 Composite health ring

The conic-gradient signature. Phase 4 implements as a React component.

**Outer ring (conic):**
```html
<div class="grid h-28 w-28 place-items-center rounded-full"
     style="background: conic-gradient(white {angle}deg, rgba(255,255,255,.18) 0deg);">
  ... inner ring ...
</div>
```

Where `{angle}` is `(score / 10) * 270` — the score-to-arc-degrees math:
- Score 10 → 270° (3/4 of the full circle)
- Score 5 → 135°
- Score 0 → 0° (empty)

The unfilled arc is `rgba(255,255,255,.18)` (translucent white over the purple hero).

**Inner ring (solid purple-deep):**
```html
<div class="grid h-20 w-20 place-items-center rounded-full bg-[--color-brand-primary-deep]">
  <div class="text-center">
    <div class="text-2xl font-bold text-white">{score}</div>
    <div class="text-[10px] uppercase tracking-widest text-white/65">Health</div>
  </div>
</div>
```

**The 270° decision (LOCKED Session 10, Decision log entry 32).** The conic gradient spans **270° (a 3/4 arc), not 360° (a closed loop)**. This is deliberate, not an artifact of the preview: a closed 360° loop reads as a fixed verdict ("this account scored a 6.4 and that's the answer"); a 270° 3/4 arc reads as continuously evaluated ("Pulse is reasoning, this is the current score, it moves"). Pulse is reasoning, not delivering a final score. **Score-to-angle math: `angle = (score / 10) * 270deg`** — score 10 → 270°, score 5 → 135°, score 0 → 0°. Do not change to 360°. See §6 design rule 24.

### 8.9 Signal vector bar

Linear progress bar with slate-100 track and Edge Purple fill.

```html
<div class="h-2 rounded-full bg-[--color-surface-track]">
  <div class="h-2 rounded-full bg-[--color-brand-primary]" style="width: {pct}%"></div>
</div>
```

- Height: 8px (`h-2`)
- Both track and fill are `rounded-full`
- Used in: signal vector (4 stacked bars), account-list composite-health bar

### 8.10 Verified-theme row

Soft slate-50 row with check icon + body text.

```html
<div class="flex items-start gap-3 rounded-2xl bg-[--color-surface-tinted-row] p-3">
  <CheckCircle2 class="mt-0.5 h-4 w-4 text-[--color-brand-primary]" />
  <div class="text-sm leading-5 text-slate-700">
    Burnout mentions easing
  </div>
</div>
```

- Background: slate-50 (named `--color-surface-tinted-row`)
- Icon: `CheckCircle2`, purple, 16px
- Body text: 14px / 400 / slate-700
- Radius: `rounded-2xl` (16px — smaller than card radius)

### 8.11 Search field

Pill-shaped, slate-50, slate-200 border, slate-500 placeholder.

```html
<div class="flex w-full max-w-xl items-center gap-2 rounded-full border border-[--color-border-strong]
            bg-[--color-surface-tinted-row] px-4 py-2.5 text-sm text-slate-500">
  <Search class="h-4 w-4" />
  Ask: "Prep me for Helix renewal" or "Who raised pay concerns?"
</div>
```

- Radius: pill
- Padding: `px-4 py-2.5` (16px / 10px)
- Icon: `Search`, slate-500
- Placeholder text in slate-500

### 8.12 Account-list item

Selectable card, two states.

**Unselected:**
```html
<button class="w-full rounded-3xl border border-transparent bg-white/70 p-4 text-left transition
               hover:border-[--color-brand-primary-soft] hover:bg-white">
  ...
</button>
```

**Selected:**
```html
<button class="w-full rounded-3xl border border-[--color-border-brand] bg-white shadow-lg shadow-slate-200 p-4 text-left">
  ...
</button>
```

- Selected = white-card-on-tinted-rail, purple-edged border, slate shadow
- Unselected = transparent border, semi-transparent white background
- Both: `rounded-3xl`, `p-4`

### 8.13 Trust-layer callout

The Action Queue footer card.

```html
<div class="rounded-3xl border border-[--color-brand-primary-soft] bg-white p-4">
  <div class="flex items-center gap-2 text-sm font-semibold text-slate-900">
    <ShieldCheck class="h-4 w-4 text-[--color-brand-primary]" />
    Trust layer
  </div>
  <p class="mt-2 text-xs leading-5 text-slate-500">
    Show the source, date, confidence, and owner for every insight. Keep the RM in control of outreach.
  </p>
</div>
```

- Border: `--color-brand-primary-soft` (purple/15) — softer than selected-account-card's purple/35
- Icon: `ShieldCheck`, purple
- Body: slate-500 secondary copy

### 8.14 Agent Presence Indicator — Pulse Bar (Breathing) **[LOCKED Session 10]**

Pulse's single, canonical agent-presence indicator. Locked Session 10 per Decision log entry 31 and §6 design rule 22. Canonical render: `01_design/agent_presence_variants/04_pulse_bar_breathing.html`.

**Structure.** A thin horizontal bar, 1–2px tall, full app-shell width, positioned at the top of the chrome — immediately below the header bar (the seam between header and body). The bar is part of the chrome, not the content; it does not scroll, does not resize with content, and is identical across every screen (hero view, Action Queue, CEO View, profile views, admin console).

**Color token.** `--color-brand-primary` (#6B46C1) with variable opacity per state. No gradient. No additional colors.

```html
<div class="pulse-bar" data-state="idle | processing | ready"></div>
```

```css
.pulse-bar {
  position: relative;
  width: 100%;
  background: var(--color-brand-primary);

  /* Idle defaults */
  height: 1px;
  opacity: 0.15;
}

/* Idle: no animation; literal defaults above. */

/* Processing: gentle 2-second sine breathing */
.pulse-bar[data-state="processing"] {
  animation: pb-breathe 2s ease-in-out infinite;
}
@keyframes pb-breathe {
  0%, 100% { opacity: 0.15; height: 1px;   }
  50%      { opacity: 0.40; height: 1.5px; }
}

/* Action ready: single 600ms heartbeat; returns to idle. */
.pulse-bar[data-state="ready"] {
  animation: pb-heartbeat 600ms ease-out 1 forwards;
}
@keyframes pb-heartbeat {
  0%   { opacity: 0.15; height: 1px; }
  40%  { opacity: 0.80; height: 2px; }
  100% { opacity: 0.15; height: 1px; }
}
```

**Three states.**

| State | Visual | Behavior | Meaning |
|---|---|---|---|
| **Idle** | 1px line at 15% opacity | No motion | Pulse is here, not currently reasoning. Calm baseline. |
| **Processing** | Breathing pulse — 2s ease-in-out cycle; 15% ↔ 40% opacity; 1px ↔ 1.5px height | Continuous animation while ≥1 agent reasoning op is in flight | Pulse is reasoning on something. Organic, attentive — not mechanical, not a progress bar. |
| **Action ready** | Single 600ms ease-out heartbeat; peak 80% opacity / 2px height; returns to idle | One-shot per `action-suggested` event; companion badge increments on Action Queue button | A new action has landed. The heartbeat is the announcement; the badge is the persistence. |

**Companion: numbered queue badge.** When the bar fires its action-ready heartbeat, the Queue button in the header receives a small numbered badge (the integer count of pending Action Queue items). The badge uses `--color-brand-primary` background, white text, `rounded-full`, 12px ×12px, with a soft `--color-brand-primary-glow` drop shadow. The badge **persists** until the user handles the items (approves, modifies-and-approves, rejects, or expires). The badge count is live — it decrements when items leave the queue.

**Throttling rules.**

1. **One indicator at a time.** A single global bar exists per app shell — there is no concurrency to throttle at the indicator level. Multiple processing events stack invisibly on the same breathing animation.
2. **Processing state stacks.** If multiple agent-reasoning operations are in flight concurrently, the bar continues breathing until **all** of them complete. The bar reverts to idle only when zero reasoning operations remain in flight.
3. **Action-ready heartbeats serialize.** If a second `action-suggested` event lands while the first 600ms heartbeat is mid-flight, the second heartbeat **queues** to fire immediately after the first completes. Heartbeats never overlap or visually superimpose; the cadence is one-at-a-time even under burst load.
4. **Badge count is live.** The badge updates immediately on every queue mutation (`action-approved`, `action-rejected`, `action-modified-and-approved`, `action-expired`). No latency, no animation on increment — the number simply changes. The companion badge can decrement to zero, at which point it disappears.
5. **Burst-load cadence.** During a heartbeat backlog, the bar fires heartbeats at maximum cadence of one per 600ms (no compression below 600ms). If the queue grows faster than heartbeats can announce, the badge integer leads the visual cadence — this is acceptable.

**Where it lives.** Every screen in the app. The bar is part of the chrome, not the content:
- Hero view (the situational hero + Action Queue surface) — yes.
- Action Queue dedicated view — yes.
- CEO View — yes (this is the variant's primary advantage over V3; CEO View has no left rail, so a rail-local indicator would go silent there).
- Per-Profile views (Customer / Talent / RM profiles) — yes.
- Admin console — yes.
- Login / auth screens — no (no agent reasoning yet at that point; pre-shell).

**Anti-patterns — do NOT.**
- Do NOT use a horizontal sweep (mechanical-feeling, reads as a progress bar — the V1-original sweep was rejected for this reason).
- Do NOT use a sharp blink or strobe (jarring, reads as an alert; Pulse never alarms).
- Do NOT increase the processing-state amplitude beyond 40% opacity / 1.5px height (anything brighter starts demanding attention; "alive presence" stops being calm).
- Do NOT sustain the action-ready brightness (the single 600ms pulse is the announcement; sustained brightness crosses from ambient to insistent — that's what the persistent badge is for).
- Do NOT apply the breathing animation to anything else in Pulse (the brand mark, the search field, the avatar, etc.). The bar's breathing is the **single** alive-presence signal — diffusing it weakens the signal.
- Do NOT change the color to anything other than `--color-brand-primary`. No red on errors, no green on success — those signals belong elsewhere (toasts, inline error states).
- Do NOT auto-play the heartbeat at page load. The bar starts in idle; transitions to processing/ready are response, not introduction.
- Do NOT remove the badge on heartbeat completion. The heartbeat is ephemeral; the badge is durable.

**Reduced-motion handling (Phase 4).** Under `prefers-reduced-motion: reduce`, the bar holds at a constant 30% opacity during processing (no breathing cycle) and the action-ready heartbeat is replaced with an instantaneous opacity step from 15% → 80% → 15% over 200ms (still visible, no oscillation).

---

## 9. Layout primitives

### 9.1 Outer shell

```
<page bg=#FAFAFA, padding=24px>
  <shell rounded-[2rem], bg=#F5F5F7, border=slate-200, shadow-2xl shadow-slate-200/70, max-width=80rem (max-w-7xl), overflow=hidden>
    <header>
    <main grid-cols-12>
  </shell>
</page>
```

The shell is the anchor. Everything inside lives within the rounded-[2rem] frame. Page background and shell background are distinct (one is `#FAFAFA`, the other `#F5F5F7`) — this two-layer chrome is part of the Edge brand surface.

### 9.2 Header

```
<header flex items-center justify-between border-b border-slate-100 px-7 py-5>
  Left:    [brand-mark + name + tagline]
  Center:  [search field — lg+ only]
  Right:   [Queue outline button] [avatar]
</header>
```

- Padding: `px-7 py-5` (28px / 20px)
- Border-bottom: slate-100 divider
- Center search collapses on md and below

### 9.3 Three-column main grid

```
<main grid grid-cols-12 gap-0>
  <aside col-span-12 lg:col-span-3 left-rail>     Account list (sidebar tint)
  <section col-span-12 lg:col-span-6 main>        Deep account view (primary content)
  <aside col-span-12 lg:col-span-3 right-rail>    Action Queue (sidebar tint)
</main>
```

- On `lg+` (≥1024px): side-by-side three columns (25% / 50% / 25%).
- On `md` and below: stacks vertically — sidebar → main → queue.
- Borders between columns: `lg:border-r` (left rail), `lg:border-l` (right rail), slate-100.

### 9.4 Spacing within columns

| Column | Padding | Vertical spacing between cards |
|---|---|---|
| Left rail | `p-5` | `space-y-3` (12px) |
| Main | `p-6` | `space-y-5` (20px) |
| Right rail | `p-5` | `space-y-3` (12px) |

Main column has more padding *and* larger vertical spacing — it's the primary read surface and earns the breathing room.

---

## 10. Voice & micro-copy guidance

Pulse's voice, codified from the preview's existing copy and onedge.co's tone.

### Voice attributes

| Attribute | Means | Doesn't mean |
|---|---|---|
| **Calm** | Doesn't shout. No exclamation marks except where genuinely warranted. | Boring. Distant. |
| **Confident** | States findings; cites sources; doesn't hedge. | Overclaims. "AI says…" framing. |
| **Conversational** | Reads like a thoughtful colleague. Comfortable with em-dashes, italics for emphasis. | Casual. Jokey. Emoji-heavy. |
| **Human-centered** | Keeps the RM in control. Names the human (the RM, the customer, the talent). | Persona-driven. "Hi, I'm Pulse 👋" |
| **Evidence-led** | Every claim cites a source. | Verbose citations. Inline footnotes mid-sentence. |

### Specific copy patterns from the preview (cite-and-extend)

**Hero subtitle (the core voice example):**
> "Pulse is prioritizing evidence, next best action, and stakeholder context. No auto-send. Every customer-facing move waits for RM approval."

Calm, explanatory, confident. Names what Pulse is doing right now ("prioritizing"), what it isn't doing ("auto-send"), and who is in control ("RM approval"). This is the voice tier-0 reference.

**Card eyebrows** (brief, metadata-style, no verbs):
- "Composite health"
- "Verified themes"
- "Signal vector"
- "Meeting brief"
- "Action Queue"
- "Accounts"

Rule: card eyebrows are noun phrases, never imperative. They label *what's in the card*, not what to do with it.

**Pulse Facts strip** (anchoring nouns):
- "Temporal account memory"
- "Evidence-backed signals"
- "RM approval before action"
- "Customer + talent health"

Rule: pulse-facts are short noun phrases — 2–4 words each — anchoring the elevator pitch on the hero card. They are *what Pulse is*, not *what Pulse does*.

**Sample query placeholders** (conversational, EDGE-flavored):
- "Ask: 'Prep me for Helix renewal'"
- "Ask: 'Who raised pay concerns?'"

Rule: placeholders reflect actual EDGE Workflow 2 + §13.4 Customer Intelligence Hub query examples. Never generic ("Ask anything…").

**Trust-layer callout copy:**
> "Show the source, date, confidence, and owner for every insight. Keep the RM in control of outreach."

Rule: imperative is OK on operational copy that explains a system behavior. Still calm.

### Inline-tag voice (operational reasoning)

For the agent's reasoning prose — surfaced inside Action Queue cards' `why_detail` panels and the CEO View narrative — Pulse uses the inline-tag voice lifted from `rm-intelligence-agent/src/render_demo.py`:

| Tag | Rendered as | Used for |
|---|---|---|
| `<num>2 risk-tagged Cases</num>` | JetBrains Mono, slate-900 | Numbers, counts, IDs |
| `<bad>vendor-consolidation mandate</bad>` | Inline color: `--color-risk-high-fg` | Negative signals worth highlighting |
| `<good>replacement plan delivered</good>` | Inline color: `--color-risk-low-fg` | Positive signals |
| `<quote>"Our CFO is asking us to cut vendor count by 20%"</quote>` | Inter italic, slate-700 | Verbatim quotes from calls / notes |
| `<em>EBR is Thursday</em>` | Inter italic, slate-900 | Emphasis on facts (no italic-quote conflation) |

**The tag whitelist is exact.** Anything not on the whitelist gets escaped (per `rm-intelligence-agent/src/render_demo.py`). No `<b>`, `<i>`, `<strong>`, `<em>` raw HTML in reasoning prose — only the five Pulse tags.

### Voice rules — what Pulse never does

1. **Never apologizes.** No "Sorry, I couldn't…" — describe what's available instead.
2. **Never threatens.** No "ALERT: RENEWAL RISK" — use the urgency dimension on the action card.
3. **Never performs personality.** No "Hey there! 👋", no agent jokes, no "Let me think about that…".
4. **Never name-drops underlying tech.** White-label rule (§6 product rule 1).
5. **Never hedges with disclaimers.** "Based on the data, it seems possible that…" — cut. State the finding with its citation.
6. **Never speculates beyond evidence.** If the data is thin, the brief is short. Better short than confabulated.

---

## 11. What this design language is NOT

Explicit non-goals — drawn from PM_CONTEXT §6 design rules + Session 6 reversals + Session 8 locks.

1. **Not dark-mode-first.** Session 6 reversed. Default surface is `#FAFAFA` page on `#F5F5F7` chrome on white cards. A dark-mode variant may ship in v1.5+ but is not the design surface Pulse launches with.
2. **Not Linear-inspired.** The original Linear+Granola direction was reversed Session 6 in favor of Edge brand alignment. Linear is a beautifully-engineered surface; it is not Edge.
3. **Not Granola-inspired.** Same — beautifully neutral, not Edge.
4. **Not playful or whimsical.** No mascots, no rounded cartoon iconography, no emoji in interface chrome.
5. **Not corporate-stale.** No stock photography, no business-suit imagery, no Helvetica-flavored type, no faux-3D buttons.
6. **Not workflow-builder-aesthetic.** Pulse is not Zapier; not n8n; not Activepieces. The agent orchestration is buried; the outcomes lead.
7. **Not chat-ified.** No chat box hero. No agent-with-name. No floating message bubbles. The query box exists (preview shows it) but it is *secondary* — small, centered in the header, hidden on small screens.
8. **Not persona-heavy.** No avatar named "Pulse" with a face. No anthropomorphism. Pulse is *present* (Section 7 motion + Phase 2.5 alive-presence variant), not *personified*.
9. **Not gradient-heavy.** Solid Edge Purple on the hero. Solid purple on CTA buttons. The conic-gradient health ring is the *only* multi-stop color treatment in the product.

---

## 12. Anti-patterns to actively avoid

Concrete things to refuse in Phase 4 build:

1. **Generic shadcn defaults.** Pulse uses shadcn components as substrate, but always customizes tokens. Never ship the default white-bg + slate-200-border + black-text shadcn look — it isn't Edge.
2. **Material Design.** No FAB buttons, no ripple effects, no elevation-shadow ladders beyond Section 6. No floating action buttons.
3. **Gradient CTAs.** Buttons are solid Edge Purple. No purple-to-pink gradients, no purple-to-blue, no rainbow strips.
4. **Spinning loaders.** Use the alive-presence indicator (Phase 2.5 variant). Spinners are out.
5. **"AI thinking…" three-dot animations.** Out. Same reason.
6. **Heavy chrome, decorative borders, faux-3D.** Pulse has flat surfaces, soft shadows, no embossing.
7. **Bootstrap-flavored sans-serifs.** No "Open Sans", no "Roboto", no "Source Sans Pro". Inter or the system humanist stack.
8. **Auto-playing motion on page load.** First paint is static. Motion is response, not introduction.
9. **Iconography mismatched to the lucide-react family.** The preview uses `lucide-react`; Phase 4 sticks with it. No FontAwesome, no Material Icons, no heroicons. Single iconography family.
10. **Confidence-implying widgets that aren't graded.** Don't show a "94% confident" tag unless you have a calibrated confidence value. The preview doesn't show one — Pulse doesn't introduce one in Phase 1.
11. **Chat input that looks like primary UI.** The search field exists but is centered in header and pill-shaped; it isn't a chat composer. No multi-line text area, no Enter-to-send affordance ribbon, no autosuggest dropdown.
12. **Emoji in chrome.** Action cards, eyebrows, button labels — never emoji. (Microcopy *inside* a customer-facing email draft is the RM's call.)

---

## Appendix A — Tailwind config preview (Phase 4 reference)

Phase 4 generates a `tailwind.config.ts` reflecting these tokens. Sketch:

```ts
// Sketch — Phase 4 generates the real one from this file
export default {
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#6B46C1',
          hover:   '#5B35B1',
          deep:    '#4B2E91',
          muted:   'rgba(107, 70, 193, 0.10)',
          ghost:   'rgba(107, 70, 193, 0.07)',
          soft:    'rgba(107, 70, 193, 0.15)',
          edge:    'rgba(107, 70, 193, 0.25)',
          glow:    'rgba(107, 70, 193, 0.20)',
        },
        surface: {
          page:    '#FAFAFA',
          chrome:  '#F5F5F7',
          card:    '#FFFFFF',
        },
      },
      borderRadius: {
        '2.5xl': '1.25rem',
        '4xl':   '2rem',
      },
      boxShadow: {
        'xl-brand':  '0 20px 25px -5px rgba(107, 70, 193, 0.20), 0 8px 10px -6px rgba(107, 70, 193, 0.10)',
        '2xl-shell': '0 25px 50px -12px rgba(226, 232, 240, 0.70)',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Helvetica Neue', 'Arial', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Menlo', 'Monaco', 'monospace'],
      },
    },
  },
};
```

## Appendix B — Iconography reference

The React preview uses `lucide-react`. Mapping for Phase 4:

| Icon | Used at |
|---|---|
| `Zap` | Brand mark (header top-left, in purple tile) |
| `Search` | Header search field |
| `Bell` | Queue button |
| `Sparkles` | Hero card eyebrow ("AI briefing, grounded in account memory") |
| `CalendarDays` | Account-list meeting line |
| `ShieldCheck` | Verified-themes header + Trust-layer callout |
| `CheckCircle2` | Verified-theme rows |
| `FileText` | Brief — Top 3 issues |
| `UsersRound` | Brief — At-risk talent |
| `MessageSquareText` | Brief — Talk tracks |
| `Clock3` | Action Queue card — pending |
| `UserRoundCheck` | Action Queue card — care action |
| `ChevronRight` | Action Queue card — go-into-detail affordance |

Icon size is `h-4 w-4` (16px) for inline / `h-5 w-5` (20px) for emphasis (header brand-mark, verified-themes header, brief tiles).

---

## Appendix C — Cross-walk to Phase 2 visual artifacts

These Phase 2 artifacts re-render against this Tier-0 doc:

- `01_design/03_action_queue.md` — updated to opt-in depth + Tier-0 references (Phase 2.5)
- `01_design/08_ceo_view.md` — updated to Tier-0 references (Phase 2.5); purple-rich since it's the highest brand-moment surface (the weekly Pulse-to-CEO narrative)
- `01_design/12_demo_storyboard.md` — each scene re-described against Tier-0 + the three-column layout (Phase 2.5)

Non-visual designs (01, 02, 04, 05, 06, 07, 09, 10, 11) are unchanged.

---

*End of Tier-0 Design Language System. Token additions/changes go through PM review per §4.10.*
