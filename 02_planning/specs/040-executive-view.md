# Spec 040 — Executive View page

**Renamed from `040-ceo-view-page.md` Session 19 late stream per the Executive View reframe** (route `/ceo`→`/executive`, component `CeoView.tsx`→`ExecutiveView.tsx`, Design 08 → `08-executive-view.md` all landed prior; this is the spec-doc filename catch-up). Recipients are CEO Iffi Wahla + VP-CS Eddy Chen, hence "Executive" not "CEO" (white-label discipline + audience accuracy). NOTE: this doc still describes the original weekly-digest framing; the shipped surface is the three-column agentic workspace per the revised Design 08 — a content revision is a separate follow-up, not this naming rename.

**Maps to:** §14 UI surfaces (Executive View); Design 08; §13.5 row "Regular leadership reports"; §13.6 #7.
**Depends on:** specs 030 (health), 008 (events for throughput), 029 (per-account narratives), 034 (shell), 038 (Pulse Bar).
**Effort:** 1.5 days.

## Description

Per Design 08. Purple-rich (most-brand-moment surface). Weekly composer skill triggered Friday 16:00 (Activepieces flow `weekly_ceo_view`). Renders the same JSON via two renderers: the live React UI AND the static-HTML fallback (per Decision 12; spec 047 verifies parity).

## Inputs

- Aggregated event log throughput (Design 04 named query: `recent_outcomes`, etc.).
- Health rollups (spec 030).
- Per-account narratives (Skill aggregator output; Phase 4 work).
- Cross-account pattern cards (Skill 10 — spec 027).
- Outcome stories from spec 033.

## Outputs

- Weekly composer skill at `03_build/pulse/skills/ceo_view_composer.py` (runs Friday 16:00 from Activepieces).
- Page at `03_build/front/src/features/executive/ExecutiveView.tsx`.
- Email digest HTML template at `03_build/pulse/dispatch/email_templates/ceo_view_weekly.html`.
- Static-HTML renderer extension that consumes the same JSON.

## Definition of Done

- [ ] Composer produces JSON matching the Design 08 §"Layout" structure.
- [ ] React UI page renders the JSON purple-rich per Tier-0 §8.7 hero (full-width).
- [ ] AI-RM voice prose uses inline-tag rendering.
- [ ] Account health pulse uses signal-vector-bar primitive (Tier-0 §8.9).
- [ ] "What I'd ask of you" uses trust-layer callout primitive (Tier-0 §8.13).
- [ ] Email digest renders the same content in inline-CSS HTML (mobile-readable per Q92).
- [ ] Static-HTML fallback consumes same JSON, renders to `data/demo.html`.

## Tests

- **Unit:** composer JSON schema validation.
- **Integration:** Friday-evening cron triggers composer → page renders → email sent to CEO test address.
- **Parity:** UI page and static HTML render the same content (Q47 verification).

## Signal definitions involved

The Executive View aggregates outcomes across all signals; no signal-specific role.

## Open questions

Q90-Q94 disposed.

## What this is NOT

- Not the live demo (spec 047 + Demo storyboard).
- Not the per-RM Action Queue.
