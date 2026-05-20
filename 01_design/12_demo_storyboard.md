# Design 12 — Demo Storyboard

**Phase:** 2 (Design); refreshed Phase 2.5 against Tier-0
**Tier:** 3 — late Phase 2 / extending into Phase 3
**Status:** Locked on substance Phase 2; **visual references refreshed Phase 2.5** against `00_design_language.md`

---

## Purpose

The 4-week demo narrative — what the CEO sees, in what order, for how long. Maps directly to §13 EDGE Coverage and the Pulse-exceeds-EDGE additions (§13.6). This is the **visual spine for the live demo on 2026-06-30**, and the explicit checklist the Phase 4 Build phase races to satisfy.

> **Demo anchor accounts (recon-verified, Session 13 — `00_research/spikes/05_demo_data_recon.md`).** The storyboard's anchor accounts are real, production-verified EDGE accounts with rich data:
> - **DHR Health Clinics** (Enterprise / Medical; 76 active talent + 45 recent cases — densest in the org) — *primary churn-watch anchor; replaces the earlier "Acrisure" placeholder.*
> - **Mendota Insurance** (Enterprise / Insurance; 42 active talent) — *expansion + EBR anchor; replaces the earlier "Pinnacle" placeholder. Also a §13.4 query example.*
> - **Cirventis (HelixVM)** (Mid-Market / Medical; 23 active talent) — *the real account behind the React preview's "Helix Labs" display name; used in §13.4 AI-displacement query.*
> - **Vertex** — referenced in §13.4 ambassador query; data depth unverified at recon (Q154); verify Week 1 or swap.
> Contact names in scene narratives (e.g. "Sarah Chen") are **illustrative placeholders**; the live demo surfaces real champion contacts pulled from SFDC at runtime.

The demo is rendered against the **Tier-0 design language** (`01_design/00_design_language.md`) — Edge Purple on warm white, three-column shell, conic health rings, and the **Pulse Bar (Breathing)** agent-presence indicator (locked Session 10, Tier-0 §8.14; canonical render at `01_design/agent_presence_variants/04_pulse_bar_breathing.html`). The visual register is the user's React preview (`01_design/00_design_language_preview.tsx`).

The rm-intelligence-agent demo.html stays as the **deliberate fallback** (PM_CONTEXT Decision 12) — and **uses the same Tier-0 tokens + the same inline-tag voice renderer** as the live UI, so the fallback's tone matches the live demo's tone exactly.

---

## Inputs

- Design 01–11 (the architecture this demo exercises).
- PM_CONTEXT §13 (every row must be visible somewhere in the demo, or explicitly acknowledged as "not in the demo scope" with a v1.5+ note).
- rm-intelligence-agent's existing `data/demo.html` content as the **starting reference** for visual tone.

## Outputs

- A scripted demo flow lasting **~15 minutes live, ~30 minutes with Q&A**.
- A backup single-file HTML demo (rm-intelligence-agent variant) at `data/demo.html` updated for the demo-day context.
- A small list of pre-demo data-priming actions (which DHR-Health-Clinics-shaped scenarios to seed if live data is sparse).

---

## Behavior

### The 15-minute narrative arc

**Scene 0: Setup (1 min)** · *Visual register: the React preview's three-column shell at first paint.*
Open Pulse at the URL on the CEO's laptop. The page is the React-preview layout: `--color-surface-page` background (#FAFAFA), `--color-surface-chrome` shell (#F5F5F7) with `rounded-[2rem]` + `shadow-2xl shadow-slate-200/70`. The brand-mark tile in the header is solid Edge Purple with the `--color-brand-primary-glow` tinted shadow — the first brand moment. The **Pulse Bar (Breathing)** sits at the top of the chrome just below the header — at this moment in its idle state (1px line at 15% Edge-Purple opacity, no motion). Pulse is here, present, waiting.

*"This is the home screen — Pulse's only home. The hero card and the action queue. Nothing else."*

**Scene 1: The action queue + situational hero (3 min) — §13.3 + §13.6 #1** · *Visual register: middle column hero card + right rail queue, both fully rendered.*
Helix Labs is the selected account in the left rail (the white card with `--color-brand-primary-edge` border + slate shadow, per Tier-0 §8.12 "selected" state). The middle column shows the Helix hero card — solid `--color-brand-primary` background, the conic-gradient health ring at 6.4/10 (per Tier-0 §8.8 — outer ring `conic-gradient(white 173deg, rgba(255,255,255,.18) 0deg)`, inner ring `--color-brand-primary-deep`). The hero subtitle reads: *"Pulse is prioritizing evidence, next best action, and stakeholder context."* (Tier-0 §10 voice anchor.) The pulse-facts strip below shows: Temporal account memory · Evidence-backed signals · RM approval before action · Customer + talent health.

Walk through three queue cards in the right rail, top-to-bottom. Each card uses the Tier-0 §8.3 Card primitive (white `--color-surface-card`, `rounded-3xl`, `shadow-sm`, `--color-border-subtle` border).

1. **High-urgency: Helix renewal-risk note to sponsor.** Click "Review." The card expands in place (no modal — Tier-0 §7 motion: fade-and-lift 250ms). The inline-tag reasoning unfurls (Tier-0 §10 inline-tag voice): `<num>3 verified signals</num>`, `<bad>AI displacement concern raised</bad>`, `<good>Champion still warm</good>`, verbatim quote in `<quote>"…"</quote>` Inter italic. Source episodes are clickable Chorus / SFDC / Calendar links.

   *"Pulse drafted this in the 8 seconds after the calendar adapter spotted the renewal sync."*

2. **Medium-high: Mendota EBR brief.** Already prepared (the "Prepared" pill state). Click "Review." Expand. *"Brief is ready. RM can ship-as-is or modify."* Show the Modify flow: change one sentence inline, save, Approve. The Approve button is `--color-brand-primary` solid, hover `--color-brand-primary-hover` (Tier-0 §8.4). On approve: the card dispatches; an `action-executed` event lands; the card animates (Tier-0 §7 fade) to the "Dispatched" group.

3. **Low: Coaching handoff for Vertex talent.** Show the auto-approval countdown (the small purple-tinted countdown chip per Tier-0 §8.1 active-pill variant). *"Most low-blast-radius actions get out of the way automatically. RM stays in control via a single click."*

During this scene, a **new card lands in the queue mid-walkthrough**. The Pulse Bar (Breathing) fires its single 600ms heartbeat (1px → 2px height, 15% → 80% → 15% opacity) and the numbered badge on the Queue header button increments. The card itself fade-and-lifts into the queue per Tier-0 §7. The CEO's eye follows the chrome heartbeat → the queue badge → the new card — no toast, no popup, no verbal cue from the demo presenter. This is the action-ready moment the indicator was designed for.

**Scene 2: The "why" — explainability (2 min) — §6 rule 12 + §13.5 audit** · *Visual register: expanded card detail with full reasoning prose.*
Stay on the Helix card. Read the full reasoning prose aloud — the inline-tag voice gives the prose its texture: numbers in `--font-mono`, bad-signals in `--color-risk-high-fg`, good-signals in `--color-risk-low-fg`, quotes in Inter italic. Switch to admin mode (visible only to Admin/VP role per Design 09) and reveal the audit log query showing the full event chain: `signal-received → episode-ingested → skill-fired → context-retrieved → reasoning-completed → action-suggested → policy-decision → action-approved → action-executed`.

*"Every action Pulse ever proposes leaves an audit trail. The Senior Developer can answer 'why did Pulse do that' for any decision, ever."*

**Scene 3: The graph and cross-account intelligence (3 min) — §13.4 + §13.6 #1** · *Visual register: Overall view; pattern card uses Tier-0 Card primitive.*

When the search query fires in this scene, **the Pulse Bar (Breathing) transitions from idle to its breathing state** — 2-second sine cycle, opacity 15% ↔ 40%, height 1px ↔ 1.5px (Tier-0 §8.14). The CEO sees Pulse reasoning across the book without any "thinking…" affordance. When the result list materializes, the bar returns to idle.

Switch to the Overall view. The cross-account pattern card sits at the top of the right rail:

```
Pattern: vendor consolidation
3 customers · 30 days · 4 verbatim quotes
- DHR Health Clinics (2x)
- ClientX
- ClientY

Proposed motion: Sales / messaging play.
```

The pattern card itself uses the standard `--color-surface-card` + `--color-border-subtle` + `rounded-3xl` + `shadow-sm`. The "vendor consolidation" headline is `text-lg font-semibold`. The "3 customers · 30 days · 4 verbatim quotes" line is metadata typography (`text-xs text-slate-500`, Tier-0 §3). The verbatim quotes use `<quote>` styling.

*"Single-customer view never catches this. Pulse watches across the whole book."*

Then: focus the search field in the header (the pill-shaped slate-50 field per Tier-0 §8.11). Type *"Which talent across all accounts have raised pay concerns this quarter?"* (verbatim §13.4 example placeholder text). Results appear inline as a small list with verbatim quotes. Click one — the layout transitions (Tier-0 §7 fade-and-lift) to the Talent Profile view.

*"This is what an institutional memory feels like. Every signal is somewhere; finding it is one question away."*

**Scene 4: The Per-Profile narrative (2 min) — §13.5 stakeholder relationships + §13.6 #2** · *Visual register: profile view; Card primitives stacked.*
Open DHR Health Clinics' Customer profile (Design 06 schema). The profile sections — Relationship origin · Current shape · Stakeholders · Strategic context · Communication preferences · History · Open threads — each render as Tier-0 Card primitives. Section headers use h2 typography (`text-lg font-semibold`); section bodies use Body (`text-sm`). Verified-theme rows inside Stakeholders use the Tier-0 §8.10 primitive — `--color-surface-tinted-row` background, `--color-brand-primary` check icon, slate-700 body.

*"This is what an RM knows about their customer, codified. Editable by the RM, auto-regenerated when meaningful new info arrives. Backed by the temporal graph; not a Claude-conversation-per-customer."*

Show one edited paragraph. Show the diff. Click into one Stakeholder.

*"Sarah Chen prefers structured agendas. We wrote that down once. It's there every time."*

**Scene 5: The CEO View (3 min) — §13.6 #7** · *Visual register: Pulse's most-brand-moment surface. Purple-rich.*
Switch to the CEO View. The **Pulse Bar (Breathing) is still there at the top of the chrome** — same indicator, same calm baseline. This is the V1+V2 hybrid's primary advantage: the leadership-facing read does not lose Pulse's presence, the way a rail-local indicator would. The AI-RM voice hero block is a full-width version of the Tier-0 §8.7 hero card — solid `--color-brand-primary`, white text, `rounded-[2rem]` radius, `--color-brand-primary-glow` tinted shadow. Read the first AI-RM voice paragraph aloud. The Account health pulse below uses Tier-0 §8.9 signal-vector bars — slate-100 track, Edge Purple fill, one bar per tier (Healthy / Stable / Watch / At-Risk / Escalated). Top 3 stories use standard Card primitives. "What I'd ask of you" uses the Tier-0 §8.13 trust-layer callout — white card + `--color-brand-primary-soft` border + ShieldCheck icon.

*"This is what arrives in your inbox every Friday. Five minutes of reading. Pulse, on behalf of the book of business."*

**Scene 6: The fallback (30 sec) — Decision 12** · *Visual register: same renderer, same tokens, no server.*
Open `data/demo.html` in a new tab — the single-file HTML demo. Same inline-tag voice. Same Edge Purple. Same renderer (lifted from rm-intelligence-agent and now token-bound to Tier-0).

*"And when the wifi fails right before a board meeting, this — same content, no server, no infrastructure — is the safety net."*

**Q&A (15 min)**
Expected questions:
- "What does this cost?" — answer from PM_CONTEXT §5 budget posture.
- "When is it production-ready?" — Phase 3 + Phase 4 timeline; production-ready = post-demo + AWS migration.
- "Can we add Zoom?" — Yes, via the Signal Source Adapter (Design 02). 1-week build per Spike 2 verdict.
- "What about HIPAA?" — Answered by §6 rule 2 + Decision 17 (no PHI in RM calls; AWS-only + audit log are the posture).
- "Who built this?" — *(answer per user; PM proposes "Pulse is built on EDGE's own data with white-labeled agentic infrastructure under the hood.")*

---

### EDGE coverage — what the demo exercises

| §13 row | Demo scene |
|---|---|
| §13.2 Workflow 1 (Automated Post-Meeting Note Capture) | Scene 1 (Action Queue showing actions surfaced from a Chorus call) + Scene 2 (audit chain back to the signal) |
| §13.3 Workflow 2 (Pre-Meeting Briefing) | Scene 1, card #2 (Mendota Insurance EBR prep brief — the explicit Workflow 2 implementation) |
| §13.4 (Customer Intelligence Hub queries) | Scene 3 (cross-account pattern + query box exercises EDGE-doc-named queries verbatim) |
| §13.5 (six RM JD areas) | Scenes 1, 4, 5 (Action Queue covers most; Profile covers stakeholder relationships; CEO View covers leadership reporting) |
| §13.6 #1 Agentic upgrade | Scenes 1, 3 (propose/approve/execute is the demo's spine) |
| §13.6 #2 Three-graph (vs. EDGE's mistaken Claude-conversation framing) | Scene 4 (Per-Profile + graph-backed) |
| §13.6 #3 Multi-axis sentiment | Scene 2 (admin reveal can show the multi-axis vector) |
| §13.6 #4 Talent-side first-class | Scene 4 (profile structure has parallel Customer + Talent surfaces) |
| §13.6 #5 Renewal Watcher | Scene 1 if a renewal-watcher card is in the queue; otherwise Scene 4 sidebar mention |
| §13.6 #6 Escalation Router | Scene 1 if an escalation-router card is in the queue |
| §13.6 #7 Auto-generated leadership reports | Scene 5 (CEO View is the implementation) |
| §13.6 #8 Demo HTML fallback | Scene 6 |
| §13.6 #9 Signal Source Adapter pattern | Q&A response ("Can we add Zoom?") |

### Demo-day data priming

Pulse should walk into the demo with:
- DHR Health Clinics and Mendota Insurance both populated with realistic signal histories (production-verified per Session 13 recon; DHR has 76 active talent + 45 recent cases, Mendota 42 active talent).
- At least one cross-account pattern in the Overall view (vendor-consolidation pattern works if 3+ customers actually have it; if not, prime a Mendota-style burnout pattern).
- 3–5 actions in the demo RM's queue, mixing urgencies and skill types.
- A CEO View page ready for the most recent complete week ending before demo day.

**Demo-day priming script:** a small `scripts/demo_prime.py` (built in Phase 4) that seeds enough action variety to ensure each scene has a relevant card to walk through. The script writes to the live system; demo-day "Approves" execute real dispatches.

### What's NOT in the demo

- The Admin console policy-tuning surface (Scene 2 admin reveal is brief; full policy console is internal).
- The full event-log explorer (Scene 2 shows one chain; the explorer is admin-only).
- Skill 10 if no cross-account pattern surfaces from real data and priming fails (substitute: query-box demo).
- Mobile responsive view (out of Phase 1 per Q40).
- Multi-language anything.
- v1.5+ surfaces: Zoom inputs, Slack inputs, Jira ticketing, daily CEO View cadence.

### Roles in the room

- **CEO** — primary audience. Visual-first; impatient with linearity (per PM_CONTEXT §5 stakeholder context). The demo's pacing and visual rhythm is for them.
- **VP of Client Success** — secondary audience. Operational lens. The Q&A about cost, rollout, and operations is theirs.
- **Senior Developer** — tertiary audience. Will scrutinize the audit chain and architecture overview at the deep-dive. Scene 2 + a follow-up Design 10 + 11 review handles this.
- **EDGE doc owner (Eddy)** — checks that the original requirements are visibly satisfied. The §13 Coverage Map walk handles this offline post-demo.

---

## EDGE Coverage references

This artifact ties together every §13 row visible in the demo. See "EDGE coverage — what the demo exercises" table above.

---

## Open questions

- **Q109** — Demo-day environment. Live data in production org or live data in a staging clone? PM proposes: production (per Decision 16, live data demo). If production access is fragile, fall back to the static HTML demo (Scene 6 elevated to primary).
- **Q110** — Demo-day rehearsal cadence. PM proposes: full rehearsal 48h before; data-priming check 24h before.
- **Q111** — Recorded video backup. PM proposes: yes — record a 15-min screencast 24h before demo day as a third-tier fallback (after live + static HTML).
- **Q112** — Branding on the demo URL. `pulse.onedge.co`? `pulse.edge.lab`? User-decisive.
- **Q113** — Demo audience size. Just the four named stakeholders? Or open invite within EDGE? Affects pacing and Q&A management.

---

## What this is NOT

- **Not a marketing demo.** Internal stakeholders; speak shop. The demo is a working tool with a working narrative, not a sales reel.
- **Not a feature-tour.** The arc shows three workflows end-to-end. Comprehensive feature surface is the §13 Coverage walk, not the demo.
- **Not the rm-intelligence-agent demo.html.** That is the fallback; the live demo is the Pulse Phase 1 product.
- **Not Slack-delivered.** Per `feedback_dont_flood_slack`.
- **Not pre-recorded as the primary.** Live demo is primary; recording is third-tier fallback (Q111).
- **Not where the v1.5+ roadmap is presented.** A separate "what's next" slide can follow Q&A; the demo itself is Phase 1 only.
