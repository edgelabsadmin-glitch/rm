# Spec 037 — Per-Account view UI (opt-in depth)

**Maps to:** §14 UI surfaces (per-account view with opt-in depth); Tier-0 §8.9-8.10 (signal vector bar, verified-theme row); §6 rule 20 (calm whitespace + opt-in depth).
**Depends on:** specs 029 (profiles), 030 (health), 034 (shell), 036 (hero).
**Effort:** 0.75 day.

## Description

Below the hero, three click-to-expand panels (per React preview's middle column): signal vector (4 stacked bars), verified themes (slate-50 rows with check icons), meeting brief (purple-tinted blocks). Per §6 rule 20 — closed by default; click to expand.

## Inputs

- Per-Account composite health (spec 030).
- Verified-themes from Per-Profile Markdown (spec 029) + recent signal events.
- Meeting brief (when Skill 02 has emitted; spec 018).

## Outputs

- `03_build/front/src/features/account/SignalVectorPanel.tsx`, `VerifiedThemesPanel.tsx`, `MeetingBriefPanel.tsx`.

## Definition of Done

- [ ] Three panels closed by default; click expands each.
- [ ] Signal vector: 4 axes from the multi-axis sentiment vector (per Q51) as `--color-brand-primary` filled bars with `--color-surface-track` rails.
- [ ] Verified-themes: slate-50 background rows with `CheckCircle2` icon in `--color-brand-primary`.
- [ ] Meeting-brief panel: triggered by skill 02's emit; "Generate brief" button per Tier-0 button primary.
- [ ] All inline-tag content rendered with the spec 035 renderer.

## Tests

- **Unit:** panel state-machine (closed/open transition).
- **Visual regression:** snapshots of each panel state.

## Signal definitions involved

Consumes signal evaluations to render the signal vector + verified themes.

## Open questions

Q51 (sentiment vector axes) — disposed.

## What this is NOT

- Not the hero card (spec 036).
- Not where briefs are generated (spec 018).
