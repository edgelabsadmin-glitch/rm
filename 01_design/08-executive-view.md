# Design 08 — Executive View

**Status:** Locked Session 19 late stream (2026-05-21) per operator mockup approval. Closed Session 19 late-late stream (2026-05-22) with spec 040 reframe shipped and spec 041 Constellation closed.
**Supersedes:** `01_design/08-ceo-view.md` (renamed in place; this file replaces it). The prior file's "narrative not chart" weekly digest framing is partially superseded by the three-column agentic workspace direction adopted Session 19 late stream after operator pushback. Pattern that survives: hero card centered, calm whitespace, italic AI-RM voice. Pattern that's replaced: linear top-to-bottom weekly digest reading flow.
**Spec:** `02_planning/specs/040-executive-view.md` (renamed from `040-ceo-view.md` Session 19 late stream).
**Route:** `/executive` (renamed from `/ceo` Session 19 late stream per white-label discipline + audience accuracy).
**Component:** `src/features/executive/ExecutiveView.tsx` (renamed from `CeoView.tsx`).
**Recipients (Phase 1):** CEO Iffi Wahla, VP-Client-Success Eddy Chen. Phase 2+ extends to additional executive-tier roles as EDGE org grows.
**PM-drafted on `dz-001` branch.** Doc-only commit; no implementation changes. Lands at merge to main when operator authorizes `dz-001` sequence.

---

## 1. The reframe in one paragraph

The original Design 08 framed this surface as a **weekly narrative digest** for the CEO — long-form prose answering "what happened this week, in plain English, without charts." Session 19 late stream review surfaced a problem: the digest read as a static report. Operator response after seeing the first implementation pass was direct: "STOP. WHY IS THIS LINEAR." The reframe — operator-approved via mockup the same session — anchors the surface on a **central Hero Card** flanked by two action-oriented columns (Client Stickiness left, Upsell Opportunities right), with a "What I'd ask of you · 3 this week" middle band and a "Book in numbers" bottom strip. Every section now surfaces an agentic decision the executive can act on, not just information they can read about. This brings the surface in line with §4.20 — "every screen must surface an agentic decision, not just show information" — codified Session 19 and applied retroactively to all hero surfaces.

---

## 2. Recipients + naming rationale

### Why "Executive View" not "CEO View"

The renaming from `/ceo` to `/executive` (Session 19 late stream operator decision) is structural, not cosmetic. Three reasons:

1. **Audience accuracy.** Phase 1 has two named recipients — CEO Iffi Wahla and VP-CS Eddy Chen. Eddy is not the CEO; calling the surface "CEO View" was wrong by Session 19 late stream. Both avatars appear on the Hero Card; both stakeholders are surfaced as co-owners of the executive frame.
2. **White-label discipline (§6 #1).** EDGE Pulse is white-labeled. Other deployments may have different executive titles (CRO, COO, President, MD). "Executive View" is title-agnostic and survives the rename to "Acme Pulse" without surface-name changes.
3. **Future-proofing.** Phase 2+ may extend executive access to other senior roles (CRO, Head of Operations). The naming accommodates that without further surface renaming.

The mechanical rename ripples: route, component, spec filename, design doc filename. No content layer hardcoded "CEO" remained after Session 19 late stream sweep.

### Recipient framing on the surface itself

Both recipients appear on the Hero Card avatar pair (IW + EC stacked). This is not decorative — it signals that the agentic frame is shared between the operational lead (Eddy) and the strategic lead (Iffi). The italic AI-RM voice addresses both as "you" implicitly; specific asks in the middle band may be tagged to one or the other when context warrants (Phase 1B once LLM composer wires Week 4).

---

## 3. Composition lock — three-column agentic workspace

The locked layout (per Session 19 mockup):

```
┌─────────────────────────────────────────────────────────────────────┐
│  Pulse Bar (AppShell singleton, breathing amplitude calibrated)     │
├──────────────┬────────────────────────┬─────────────────────────────┤
│              │                        │                             │
│  CLIENT      │      HERO CARD         │   UPSELL                    │
│  STICKINESS  │   ┌──────────────┐     │   OPPORTUNITIES             │
│              │   │  IW EC       │     │                             │
│  • Account   │   │  Book Health │     │   • Account at signal      │
│  • Account   │   │     7.2      │     │   • Account at signal      │
│  • Account   │   │  ┌────────┐  │     │   • Account at signal      │
│              │   │  │ Italic │  │     │                             │
│  (chip-risk  │   │  │ AI-RM  │  │     │   (chip-opportunity         │
│   stat hue)  │   │  │ voice  │  │     │    stat hue)                │
│              │   │  └────────┘  │     │                             │
│              │   │  2×2 pulse-  │     │                             │
│              │   │  facts grid  │     │                             │
│              │   └──────────────┘     │                             │
├──────────────┴────────────────────────┴─────────────────────────────┤
│                                                                     │
│           "What I'd ask of you · 3 this week"                       │
│           (middle band — three discrete asks, each with action)     │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Book in numbers ($2.69M book · 269 active talent · 14 accounts)   │
└─────────────────────────────────────────────────────────────────────┘
```

### Why three columns, not two or four

- **Two columns** (Stickiness | Hero | nothing) would underweight the upsell narrative. EDGE's strategic posture explicitly treats upsell opportunities as equal-weight to retention risk; a one-sided risk-focus view misrepresents the book.
- **Four columns** would crowd the Hero Card and lose the visual hierarchy. The Hero needs to *anchor* the surface; flanking columns are subordinate by composition.
- **Three columns with Hero centered** mirrors the storyboard Scene 5 narrative pivot and matches the operator-driven mental model: "what's at risk · what matters most right now · where's the upside."

### Why the asks band in the middle, not above/below

The middle band is the *call to action* — the part the executive should leave the surface having decided about. Placing it visually between the Hero (which sets context) and the "Book in numbers" strip (which provides backdrop) makes it the natural reading destination. The three discrete asks each include an inline action (approve / read / discuss-with-RM type buttons in Phase 1B). The "3 this week" cap is deliberate — executive attention is finite; surfacing more than three asks weekly trains the surface as noise.

### Why "Book in numbers" at the bottom, not in the Hero

The Hero is for narrative and agentic posture (the italic AI-RM voice, the Book Health ring, the 2×2 pulse-facts). Raw aggregate numbers like total ARR, total accounts, total talent are *context*, not *story*. Placing them at the bottom strip honors the "calm whitespace + opt-in depth" design rule (#22): the executive can glance at the strip for grounding when they want grounding, without the numbers competing with the agentic narrative for attention above.

---

## 4. Hero Card composition rationale

The Hero Card is the visual anchor of the surface. Its composition was locked across Session 18-19:

### Brand purple anchor (`#4a0f70`)

The Hero Card uses saturated brand purple as background — the only surface in Pulse besides the brand-mark tile that does so. This is deliberate visual privilege: the Hero is THE most important thing on the screen, and brand saturation signals "this is Pulse speaking to you." Design rule #25 explicitly lists the Hero Card as one of the four heroes (Action Queue, Hero Card, Executive View, Constellation) that get visual privilege.

The brand purple value (`#4a0f70`) was corrected Session 19 late stream from the prior `#6B46C1` (Tailwind default placeholder) to the real Edge purple. Six surfaces verified clean ripple at that change. The Executive View Hero inherits the correction.

### IW + EC avatar pair

Two stacked avatars: Iffi Wahla (CEO) and Eddy Chen (VP-CS). Per §2 recipient framing. Hardcoded in `demo_characters.ts` per Path A canonicalization (Session 19 late stream). When the surface migrates to multi-tenant (post-Phase-1), the avatars become dynamic per tenant's executive recipient list — but the *pattern* of "two named recipients side-by-side" persists.

### Book Health Ring (7.2 default, 270° conic gradient)

The ring shows composite Book Health on a 0-10 scale, rendered as a 270° conic gradient (per design rule #28 — never 360° to avoid the "fully closed" cognitive trap). Default Phase 1 value 7.2 is derived from canonical `demo_characters.ts` aggregate health-state distribution; Phase 1B will derive from real Composite Health Score (pulse-api Week 4 cutover).

White ring fill on brand-purple background with faint-white track. Tinted shadow (design rule #27 — Hero Card is one of three surfaces that gets the tinted-shadow treatment).

### Italic AI-RM voice with on-brand inline tags

A single paragraph of italic prose in AI-RM voice — the agentic Pulse-as-RM persona speaking directly to the executive. Tone: confident, specific where verifiable, generalized where not. Phase 1A (now through Week 4) uses generalized framing per real-data principle codified Session 19 late stream — no fabricated specifics ("vendor consolidation talk," "Thursday slot," "+12 nurses") because pulse-api hasn't deployed the LLM composer that would extract those from real signals. Phase 1B (Week 4 forward) wires the LLM composer to Skills 01-10 outputs; specifics become real.

On-brand inline-tag variants (`--color-risk-on-brand`, `--color-good-on-brand`, `--color-em-on-brand`, `--color-num-on-brand`) are used inside the prose to highlight risk language, positive signals, emphasis, and key numbers. These tokens were added Session 19 late stream specifically because the standard chip palette doesn't read against saturated brand purple — the on-brand variants are calibrated for legibility on `#4a0f70`.

### 2×2 pulse-facts grid

Below the italic voice paragraph, four pulse-facts in a 2×2 grid. Each fact is a label + value pair (e.g., "Book value · $2.69M" / "At-risk exposure · $1.52M" / "Active conversations · N" / "Approvals this week · N"). The 2×2 layout is deliberate: it's the densest information layout that still reads as a glance, not a table. Five facts would force a 1+4 or 2+3 layout that loses visual rhythm; three facts would leave one cell empty.

The four facts are derived from canonical fixture data (Phase 1A) and will swap to real-signal-derived values at pulse-api Week 4 cutover (Phase 1B) without UI changes — same getters, different data source.

---

## 5. Every section surfaces an agentic decision (§4.20)

This is the operative principle of the reframe. Each surface element earns its place by surfacing a decision, not just information:

| Section | Decision the executive can make |
|---|---|
| **Hero Card italic voice** | Trust the AI-RM read on the book this week (or push back to the RM team for a different framing) |
| **Hero Book Health ring** | Recognize the composite trajectory; decide if it warrants a deeper Constellation visit |
| **2×2 pulse-facts** | Spot any value that's moved meaningfully; decide if any warrants follow-up |
| **Client Stickiness column** | Pick an at-risk account to ask the RM about, or to escalate to direct outreach |
| **Upsell Opportunities column** | Pick an upside lead to push the RM toward, or to bring up in CEO-level conversation |
| **"What I'd ask of you · 3" band** | Approve / read / route each ask; clear them by end-of-week |
| **"Book in numbers" strip** | Background context; doesn't demand a decision but anchors the others |

The "Book in numbers" strip is the only section that doesn't demand a decision — and that's deliberate. Calm whitespace plus opt-in depth (design rule #22) requires that not every pixel be a CTA. The strip is the grounding floor; everything above earns attention with action.

Pre-reframe Design 08 had multiple sections (the weekly narrative paragraphs, the chart-less prose summary) that informed without asking for action. §4.20 retired that pattern. If a future section is added to the Executive View, it must pass the "what decision does this surface?" test before it lands in the composition lock.

---

## 6. Real-data principle on the Executive View specifically

The Executive View was the surface where the real-data principle (§7 rules 25 + 26 + 27, §6 posture rule #42) got its hardest test Session 19 late stream. Three rounds of operator review caught fabricated specifics:

**Round 1** — Initial italic AI-RM voice contained "vendor consolidation talk happening at DHR" and similar specifics that were inferred from industry plausibility, not extracted from real signals. Operator caught: "we cannot make up data." PM generalized to honest data-only framing.

**Round 2** — Asks band and 2×2 pulse-facts had residual fabrication (specific seat counts, specific meeting times, specific named contacts). PM caught the residuals in a second sweep; generalized further.

**Round 3** — Spec 041 work; PM specified an account-tier count in a Claude Code prompt that conflicted with canonical fixture. Claude Code edited the fixture to match the PM count (data-edit) rather than ask. PM caught and reverted. Codified §7 rule 27: PM-specified counts in prompts must verify against canonical before send; Claude Code halts on conflict.

The Executive View is therefore the surface most tested against real-data discipline. The italic AI-RM voice as currently shipped on `main` is Phase 1A — generalized prose without fabricated specifics. When pulse-api deploys Week 4, the LLM composer reads real Skill outputs (call summaries, engagement signals, opportunity changes) and the prose becomes specific *with* real provenance. Phase 1A → 1B transition is data-source only; the UI is unchanged.

This is the most important takeaway from the Executive View design arc: **the surface was built to accommodate either generalized or specific prose without re-design.** Phase 1A doesn't apologize for being generalized; Phase 1B doesn't restructure when specifics arrive. The composition is data-shape-agnostic.

---

## 7. Mockup reference

The canonical visual reference for the locked composition is the Session 19 late stream operator-approved mockup. The mockup is preserved in the conversation transcript for that session and should be retrieved if any future implementation question arises about column proportions, vertical rhythm, type sizing, or the asks-band visual treatment.

When the mockup and a written description in this doc disagree, **the mockup wins** for visual/layout questions; this doc wins for naming, routing, and architectural questions.

---

## 8. Phase 1A → 1B framing

The Executive View ships in two content phases:

### Phase 1A — Now through Week 4 pulse-api deploy

- Real structural data: book ARR, account counts, talent counts, health-state aggregates all from canonical `demo_characters.ts`
- Generalized narratives: italic AI-RM voice uses honest data-only framing without fabricated specifics
- Static asks band: three asks composed by PM from the real account set, generalized in language
- Cross-surface revenue enrichment shipped via `accountARR/bookARR/rmBookARR/managerBookARR/churnExposureARR/formatARR` helpers (Session 19 late stream)

### Phase 1B — Week 4 forward (post pulse-api deploy)

- LLM composer wires real signal extraction (Skills 01-10) into italic AI-RM voice
- Specifics return with real provenance (named contacts, real meeting outcomes, actual seat counts derived from active placements)
- Asks band populated dynamically from Skill 10 pattern outputs + composer-generated narratives
- Revenue derivation swaps from `$10K × active_talent` heuristic to real Opportunity > Account roll-up; consumer surfaces unchanged (single getter swap in `demo_characters.ts`)

The composition lock survives both phases. Phase 1B is a data-source upgrade, not a redesign.

---

## 9. What this doc does not cover

This is a design composition lock + supersession notice + recipient framing doc. It deliberately does not duplicate content that lives elsewhere:

- **Spec 040 implementation detail** — lives in `02_planning/specs/040-executive-view.md`
- **Spec 041 Constellation surface** — separate hero surface; documented in `02_planning/specs/041-constellation-view-ui.md` (closed Session 19 late-late stream)
- **Tier-0 token specifications** — live in `01_design/00_design_language.md` (chip + stat + on-brand inline-tag tokens added Session 19 late stream)
- **Brand purple correction history** — lives in PM_CONTEXT decision log
- **Real-data principle full codification** — lives in PM_CONTEXT §6 posture rule #42 + §7 rules 25-27
- **§4.20 every-section-agentic principle** — lives in PM_CONTEXT working agreements
- **Pulse Bar animation calibration** — lives in `01_design/agent_presence_variants/` notes

This doc points to those rather than duplicating them.

---

## 10. Decision log (Executive View specifically)

| Date | Decision | Made by |
|---|---|---|
| 2026-05-20 | Spec 040 first draft (`CeoView.tsx`, route `/ceo`, linear weekly narrative digest per original Design 08) | PM Session 18 |
| 2026-05-21 | Spec 040 additive fix Session 19 — PM-prompt-vs-locked-design divergence corrected (Design 08 narrative arc restored: health-pulse tier bars, top-3 stories, book-in-numbers strip) | PM Session 19 |
| 2026-05-21 | **Operator pushback Session 19 late stream**: "STOP. WHY IS THIS LINEAR." | Operator review |
| 2026-05-21 | **Reframe direction approved Session 19 late stream** via operator-supplied mockup: three-column agentic workspace anchored on Hero Card center | Operator + PM Session 19 late stream |
| 2026-05-21 | **Route + naming rename**: `/ceo` → `/executive`; `CeoView.tsx` → `ExecutiveView.tsx`; spec filename + design doc filename rename to follow | Operator decision Session 19 late stream |
| 2026-05-21 | **Hero Card composition lock**: brand purple anchor, IW+EC avatars, Book Health ring (7.2 default), italic AI-RM voice with on-brand inline tags, 2×2 pulse-facts grid | PM Session 19 late stream per mockup |
| 2026-05-21 | **Three-column layout lock**: Client Stickiness left, Hero Card center, Upsell Opportunities right, asks band middle, book-in-numbers bottom strip | PM Session 19 late stream per mockup |
| 2026-05-21 | **§4.20 codified**: every screen must surface an agentic decision, not just show information. Applied retroactively; supersedes Design 08 "narrative not chart" partially | PM declared Session 19 |
| 2026-05-21 | **On-brand inline-tag variants added** to Tier-0 tokens (`--color-risk-on-brand`, `--color-good-on-brand`, `--color-em-on-brand`, `--color-num-on-brand`) specifically for Hero Card italic AI-RM voice legibility on saturated brand purple | PM Session 19 late stream |
| 2026-05-21 | **Real-data integrity round 1** on Executive View: italic AI-RM voice generalized; fabricated specifics removed | Operator catch + PM Session 19 late stream |
| 2026-05-21 | **Real-data integrity round 2** on Executive View: asks band + 2×2 pulse-facts generalized; residual fabrication cleaned | PM Session 19 late stream |
| 2026-05-21 | **Pulse Bar amplitude tuned + Hero donut centered** (post-content-fill calibration) | Operator catch + PM Session 19 late stream |
| 2026-05-22 | **Real-data integrity round 3** (cross-spec Mendota tier-revert): PM-specified count vs canonical fixture conflict; canonical wins; PM count corrected. §7 rule 27 codified | Operator catch + PM Session 19 late-late stream |
| 2026-05-22 | **Design 08 supersession declared**: this revision lands on `dz-001`; old file (`08-ceo-view.md`) renamed in place to `08-executive-view.md` per Option A | PM Session 19 late-late stream |

---

## 11. Status: locked

The composition described in this doc is **locked Session 19 late stream + late-late stream**. Future changes to the Executive View require:

1. Operator pushback or PM-identified need
2. PM proposal (typically PM-drafted mockup or written reframe)
3. Operator approval before implementation
4. Doc revision lands on a working branch (currently `dz-001`) before main merge
5. Decision log entry added to §10

Phase 1B (Week 4 forward) is a data-source change, not a composition change — does not require steps 1-5; lands as part of pulse-api Week 4 deploy under spec 042 / 043 scope.

---

*End of Design 08 — Executive View revision.*
*PM-drafted Session 19 late-late stream (2026-05-22). Lands on `dz-001`. Supersedes `08-ceo-view.md` (renamed in place).*
