# Spec 036 — Situational Hero card UI

**Maps to:** §14 UI surfaces (situational hero card); Tier-0 §8.7 (hero card), §8.8 (composite health ring).
**Depends on:** specs 030 (dual-sided health), 034 (shell).
**Effort:** 1.0 day.

## Description

The middle-column hero per the React preview. Purple-rich; conic-gradient 270° health ring; pulse-facts strip; AI-RM voice subtitle. Renders per-account state.

## Inputs

- Selected account from left rail (state hook).
- `GET /accounts/{id}/health` (returns dual-sided health from spec 030).
- AI-RM voice paragraph from the active per-account context.

## Outputs

- `03_build/front/src/features/hero/SituationalHero.tsx`.
- `03_build/front/src/components/CompositeHealthRing.tsx` — the 270° conic-gradient component.

## Definition of Done

- [ ] Hero card matches React preview exactly: `--color-brand-primary` background, `rounded-[2rem]`, `--color-brand-primary-glow` tinted shadow.
- [ ] Conic ring uses 270° math per Tier-0 §8.8 (LOCKED Session 10).
- [ ] Account-switch motion: fade-and-lift 250ms ease-out (Tier-0 §7).
- [ ] AI-RM voice subtitle reads per Tier-0 §10 anchor: *"Pulse is prioritizing evidence, next best action, and stakeholder context. No auto-send. Every customer-facing move waits for RM approval."*
- [ ] Pulse-facts strip: 4 cards with `--color-text-on-brand-strip`.

## Tests

- **Unit:** conic-ring math (score → degrees).
- **Visual regression:** snapshots at score 0/5/10.
- **E2E:** account switch transitions correctly.

## Signal definitions involved

None directly — consumes composite health from spec 030.

## Open questions

None.

## What this is NOT

- Not the per-account view's opt-in depth panels (signal vector / themes / brief) — that's spec 037.
- Not where health is computed (spec 030).
