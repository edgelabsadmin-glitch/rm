# Spec 039 — Submission UI (`/submit` web shell route)

**Maps to:** §14 UI surfaces (submission UI in v1); §13.2 row "Submit voice note or text summary (30 sec)."
**Depends on:** specs 001, 011, 020, 034, 043.
**Effort:** 0.75 day.

> **Reframed (pre-spec-034 audit, disposition D9 — Session 16).** This spec was
> originally scoped as a Slack slash command. **Slack is OUT for v1** — the locked
> surfaces are dashboard + email + SFDC tasks (`feedback_dont_flood_slack`). The
> submission UI is therefore a **`/submit` web route inside the Pulse app shell**
> (spec 034), not a Slack command. Slack-as-input may return as a v1.5+ secondary
> surface; it is not the Phase-1 mechanism.

## Description

A `/submit` route under the front-end shell (spec 034) where an RM types or pastes
a short free-text note (EDGE Workflow 1's "submit voice note or text summary, 30
sec" ask). On submit, the note POSTs to a Pulse FastAPI endpoint → is ingested as
an Episode → Skill 01 extracts signals → surfaces in the Action Queue. A small,
calm, single-textarea surface per Tier-0 voice (§10) — not a chat composer (§12 #11).

Voice capture (record → transcribe → same path) is **v1.5+**; Phase 1 ships the
text path only. The route is reachable from the shell nav and renders the Pulse
Bar like every other surface (§8.14).

## Inputs

- Authenticated RM identity from the session (spec 043; stubbed in spec 034 until 043 lands).
- Free-text note from the `/submit` form (react-hook-form; client-side length guard).

## Outputs

- A `/submit` route + `<SubmissionForm>` component in `03_build/front/` (consumes the shell from spec 034).
- FastAPI endpoint `POST /submit/note` (RM note → Episode via the spec-011 ingest pipeline).
- The submitted note becomes an Episode tagged `["web-submission", "rm-note"]`, with `rm_id` from the session.

## Definition of Done

- [ ] Submitting a note from `/submit` produces an Episode within 5s and clears the form with a calm confirmation ("Captured. Pulse will process and surface in your queue.").
- [ ] The endpoint requires an authenticated session; the `rm_id` is taken from the session, never from client input (no spoofing).
- [ ] Submitted notes flow through Skill 01 like any other Episode (no special-casing downstream).
- [ ] Empty / whitespace-only submissions are rejected client-side with inline validation; no network call.
- [ ] The route renders inside the shell (header + Pulse Bar) and matches Tier-0 voice/spacing.

## Tests

- **Unit:** form validation (empty/whitespace rejected); endpoint maps session `rm_id` → Episode `rm_id` (not client-supplied).
- **Integration:** POST `/submit/note` with a stubbed session → Episode emitted → assert visible in queue within 30s.
- **E2E (Playwright):** type a note on `/submit` → confirmation appears → form clears.

## Signal definitions involved

Skill 01 (signal extraction) consumes these Episodes the same as any other Episode source.

## Open questions

None new. Slack-as-input is deferred to v1.5+ (was the Phase-1 mechanism; reframed to the web route per audit D9). Slack-as-Pulse-output remains OUT per `feedback_dont_flood_slack`.

## What this is NOT

- **Not a Slack slash command** (reframed; Slack is out for v1).
- Not Slack notifications outbound (out per `feedback_dont_flood_slack`).
- Not voice capture in Phase 1 (record→transcribe is v1.5+; text path only now).
- Not a chat composer — single textarea + submit, per Tier-0 §12 #11.
