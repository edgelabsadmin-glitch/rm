# Spec 035 — Action Queue UI

**Maps to:** §14 UI surfaces (Action Queue, two-layer explainability, tier-aware approval matrix, modify/approve/reject); Design 03; §13.2 / §13.5 multiple rows.
**Depends on:** specs 031 (API), 034 (shell), 038 (Pulse Bar).
**Effort:** 1.5 days. **Largest single front-end spec.**

## Description

Implement the Action Queue UI per Design 03 + React preview. Cards with two-layer explainability (why_oneline + why_detail expand-in-place), modify/approve/reject flow, tier-aware approval visuals (countdown for auto-approve; lock for human-required), filter chips, inline-tag voice rendering (Tier-0 §10), Pulse Bar integration.

## Inputs

- Spec 031 API.
- Tier-0 design system (cards per §8.3, pills per §8.1, buttons per §8.4-8.6).
- The inline-tag renderer lifted from `rm-intelligence-agent/src/render_demo.py`.

## Outputs

- `03_build/front/src/features/queue/` — `QueueList.tsx`, `QueueCard.tsx`, `WhyDetailPanel.tsx`, `ModifyEditor.tsx`, `RejectModal.tsx`.
- The inline-tag renderer ported to TypeScript: `03_build/front/src/lib/inline_tags.tsx`.

## Definition of Done

- [ ] Queue renders cards from `GET /actions` with correct ranking per Design 03.
- [ ] Card design exactly matches React preview's right-rail (card structure, pill states, icon-container, chevron).
- [ ] "Review" click expands the card in place (no modal) showing the inline-tag-rendered reasoning.
- [ ] Approve / Modify / Reject all functional; emit the expected API calls.
- [ ] Tier-aware visuals: auto-approve countdown for SMB pending; Enterprise badge for cc-VP-CS cards.
- [ ] Inline-tag rendering: `<num>` → mono, `<bad>` → risk-high color, `<good>` → risk-low color, `<quote>` → Inter italic, `<em>` → italic.
- [ ] Fade-and-lift entrance animation on new cards (Tier-0 §7).
- [ ] Pulse Bar (Breathing) integration: badge increments on new card.
- [ ] No dark-mode default (per §6 rule 17 / Session 6 reversal).
- [ ] Accessibility: keyboard navigation; ARIA labels on cards.

## Tests

- **Unit:** inline-tag renderer (all 5 tags + escape behavior); card-state-machine.
- **E2E:** Playwright — list → click Review → click Approve → card moves to Dispatched bucket.
- **Visual regression:** snapshot of card in each approval-state.

## Signal definitions involved

None directly — the UI displays signal-attributed actions; signals live server-side.

## Open questions

Q40 (mobile responsive) v1.5+; Q39 (history depth) disposed at API level.

## What this is NOT

- Not the situational hero card (spec 036).
- Not the CEO View (spec 040).
- Not where dispatch happens (spec 032).
