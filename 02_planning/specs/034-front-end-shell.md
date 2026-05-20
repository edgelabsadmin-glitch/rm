# Spec 034 — Front-end shell

**Maps to:** §14 UI surfaces; Design 11 ADR-005; Tier-0 §9 (layout primitives).
**Depends on:** specs 001, 031, 043.
**Effort:** 0.75 day.

## Description

React + Vite + Tailwind project skeleton with Tier-0 tokens plumbed through. Three-column app shell per Tier-0 §9.3 (account list / deep view / Action Queue). Authentication flow + protected routes.

## Inputs

- Tier-0 design language doc.
- Spec 031 Action Queue API.
- Spec 043 OAuth.

## Outputs

- `03_build/front/` Vite project.
- `tailwind.config.ts` generated from `01_design/00_design_language.md` §"Appendix A."
- Top-level `<App>` with three-column layout + protected routes.
- Auth state hook + login redirect.

## Definition of Done

- [ ] `npm run dev` serves the shell at localhost; the empty three-column layout renders with Tier-0 tokens.
- [ ] Inter font loaded + system fallback verified on Safari/Chrome.
- [ ] Login redirects unauthed users; Google Workspace OAuth completes.
- [ ] All Tier-0 §2 color tokens accessible as Tailwind utilities (e.g., `bg-brand`, `text-brand-glow`).
- [ ] Lint + type-check green.

## Tests

- **Unit:** Vitest setup + one shell-rendering snapshot test.
- **E2E:** Playwright login flow.

## Signal definitions involved

None.

## Open questions

None.

## What this is NOT

- Not any feature UI — that's specs 035-041.
- Not where production build artifacts ship — Vercel deploy is per Design 11 ADR-005.
