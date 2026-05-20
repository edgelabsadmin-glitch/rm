# Spike 2 — Zoom Feasibility (no-build investigation)

**Date:** 2026-05-20
**Goal:** Confirm what's accessible in EDGE's Zoom environment without building integration code. Surfaces nasty surprises before Pulse plans a Zoom Signal Source Adapter implementation (Phase 2+).
**Scope per Session 5 decision:** Zoom is deferred to Phase 2+; Phase 1 ships Chorus + SFDC + Calendar only. This spike confirms the realistic effort estimate for the future Zoom adapter without committing engineering time.

---

## Preamble — what I'm about to do

Zoom feasibility is a yes/no/conditional inventory across four dimensions: plan tier, recording capability, transcript capability, and webhook subscription state. I cannot run live API calls against EDGE's Zoom because credentials are user-managed and the spike is explicitly no-build. I structure this memo as a **questionnaire the user can answer in 10 minutes by checking the Zoom Admin console**, plus my best-effort inference of what each answer implies for Pulse's Zoom adapter cost.

---

## A. The questions to answer

Each question is paired with **where to look** (Zoom Admin console path or equivalent) and **what the answer implies** for Pulse.

### A.1 Plan tier
- **Q:** What is EDGE's Zoom plan? (Pro / Business / Business Plus / Enterprise / One)
- **Where to look:** Zoom Admin → Account Management → Account Profile → "Account Type"
- **Implication:**
  - *Pro:* Cloud Recording yes, basic. Transcript add-on may require AI Companion or Business+. Limited webhook breadth.
  - *Business / Business Plus:* Recording + transcripts native. AI Companion typically available.
  - *Enterprise / One:* Full webhook breadth, native AI Companion, recording compliance features.

### A.2 Cloud Recording — default on for RM accounts?
- **Q:** Is Cloud Recording enabled at the account level? Is it on by default for individual users (Group settings)?
- **Where to look:** Zoom Admin → Account Management → Recording Management → Cloud Recording settings. Also Group settings if RMs are in their own group.
- **Implication:** If off by default per-user, a separate change-management step is required (admin must enable group-wide or RMs must self-enable). Without it, no recordings exist for Pulse to ingest.

### A.3 Audio Transcript — separate setting from Cloud Recording
- **Q:** Is "Create audio transcript" (also called "Audio transcript for cloud recordings") enabled?
- **Where to look:** Zoom Admin → Account Settings → Recording → "Audio transcript" toggle.
- **Implication:** Audio transcripts are the *primary* text artifact Pulse needs. Without them, Pulse would have to run its own ASR pass on the audio file — a meaningful additional dependency and cost. **If audio transcripts are off, this is the #1 thing to flip on** before Phase 2+ Zoom work.

### A.4 Zoom AI Companion
- **Q:** Is AI Companion enabled? (Meeting Summary / Smart Recording / Action Items / Next Steps features.)
- **Where to look:** Zoom Admin → Account Settings → AI Companion section.
- **Implication:** AI Companion is **a high-value Pulse input** — Zoom natively produces meeting summaries, action items, and next steps. If on, Pulse can consume AI Companion outputs *instead of* running its own LLM extraction on raw transcripts. Meaningful cost reduction. If off, Pulse can still ingest raw transcripts but does extraction itself.

### A.5 Webhook event subscriptions
- **Q:** Which Zoom webhook events are subscribed by EDGE's existing apps? Specifically:
  - `meeting.ended`
  - `recording.completed`
  - `recording.transcript_completed`
  - `meeting.summary_completed` (AI Companion)
- **Where to look:** Zoom Marketplace → "Manage" → look at each installed app's "Event Subscriptions" tab. Check the Marketplace developer console for any custom OAuth/Server-to-Server apps.
- **Implication:** Pulse needs these webhooks to ingest meetings without polling. If none are subscribed, the Zoom Signal Source Adapter must include its own webhook-receiving app (Server-to-Server OAuth, ~1 day of work). If already subscribed for Chorus or another integration, Pulse may piggy-back via a fanout from the existing receiver.

### A.6 Recording / transcript retention policy
- **Q:** What is the retention window for cloud recordings and transcripts? (Default is 0 = forever; many compliance setups are 30 / 60 / 90 days.)
- **Where to look:** Zoom Admin → Account Settings → Recording → "Auto delete cloud recordings after" / similar setting.
- **Implication:** Short retention means Pulse must ingest the moment a recording completes — no batch backfill is possible. Long retention gives Pulse more flexibility, including periodic re-ingestion for missed episodes.

### A.7 RM hosting coverage (validation against PM_CONTEXT `project_chorus_coverage_gap`)
- **Q:** Do most RM check-in calls actually run through Zoom (vs. Chorus-only, vs. customer's own platform like Teams)?
- **Where to look:** spot-check the last 30 days of meeting recordings by attendee email. Estimate the percentage of RM-with-customer meetings that have Zoom recordings.
- **Implication:** If <30% of RM calls are on Zoom, the Zoom adapter delivers less marginal signal than expected. Chorus may remain the primary call-signal source even after Zoom ships.

### A.8 PII / PHI considerations (sanity check)
- **Q:** Are Zoom recordings subject to any data-residency or BAA constraints in EDGE's plan?
- **Where to look:** Zoom Admin → Account Profile → Compliance section; or vendor contract.
- **Implication:** PM_CONTEXT Session 5 confirmed no PHI in RM calls and AWS-only as the hosting standard. Zoom recordings are stored in Zoom's cloud first; if EDGE has a BAA with Zoom, fine. If not, the recordings should at minimum stay encrypted in Zoom and be ingested through AWS-hosted infrastructure only. Re-verify per §6 rule 2.

---

## B. Effort estimate per outcome

| Scenario | Likelihood (PM guess) | Pulse Zoom-adapter effort |
|---|---|---|
| Pro/Business plan + Recording on + Transcript on + AI Companion on + webhooks already subscribed | possible | **3–5 days** — webhook receiver + adapter + transcript ingestion |
| Same plan tier + Recording on + Transcript on + AI Companion on + webhooks NOT subscribed | most likely | **1 week** — add Server-to-Server OAuth app + 3–5 day adapter |
| Recording on but **Transcript off** | possible | **1.5–2 weeks** — adapter + either an ASR pass (extra cost) or admin-flip + backfill workflow |
| **AI Companion off** | possible | adds **2–3 days** in the adapter (Pulse does its own summarization) — not a blocker |
| Plan tier **doesn't expose transcripts at all** (unlikely on Business+) | low | **blocked-until-plan-upgrade** — Zoom adapter deferred indefinitely |
| Webhook surface lacks `meeting.summary_completed` (AI Companion event) | possible | adds **1 day** in the adapter (poll vs. webhook) — not a blocker |

**Median outcome estimate:** ~1 week of focused work for the Zoom Signal Source Adapter, assuming Business+ plan with Recording + Transcript both on. **Worst case:** 2 weeks if Transcript needs to be flipped on and historical sessions need backfill.

---

## C. Verdict for Phase 2 design

**No blocker for Phase 1.** Zoom is deferred per Session 5; the Signal Source Adapter pattern (Phase 2 Tier 1 design) is the architectural commitment, not the Zoom implementation. The adapter spec must be permissive enough to accept:

1. Webhook-pushed events (meeting.ended, recording.completed, transcript_completed, summary_completed)
2. Polled events (when webhooks aren't available)
3. Both **AI-Companion-summarized inputs** (high-quality, already-extracted) and **raw transcripts** (Pulse extracts itself)

If the user answers the §A questions before Phase 2 design closes, the Zoom-adapter sub-spec (deferred to v1.5+ per `02_signal_source_adapter.md`) can be drafted in parallel with no risk to Phase 1 scope.

---

## D. Open questions raised

- **Q24** — Answers to §A.1–A.8 above. **Not blocking** Phase 1 demo (Zoom out of scope), but needed before Zoom adapter implementation in Phase 2+.

---

## E. What this spike did NOT do

- Did not run live Zoom API calls — explicitly no-build.
- Did not build a Zoom webhook receiver.
- Did not build a Zoom transcript ingestion pipeline.
- Did not commit Pulse to a specific Zoom plan tier or recommend a plan upgrade.
- Did not test the AI Companion output shape — that happens in the Phase 2+ Zoom adapter sub-spec.
