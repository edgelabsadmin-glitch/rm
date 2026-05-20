# Spec 013 — Chorus Signal Source Adapter

**Maps to:** §14 Signal sources (Chorus); Design 02; §13.2 row "Workflow captures meeting transcript"; PM_CONTEXT `reference_chorus_api` memory.
**Depends on:** specs 011, 008.
**Effort:** 0.75 day.

## Description

Lift the Chorus integration from `rm-intelligence-agent/src/chorus_pull.py` and port it into the Signal Source Adapter contract. The Chorus v3 API integration (auth header shape, pagination, conversation-detail join) is already validated; this spec is mostly re-shaping into the adapter pattern.

Triggered by Activepieces flow `chorus_engagement_completed` (HTTP webhook from Chorus when an engagement ends). The flow POSTs to `/webhooks/chorus`; the adapter validates webhook signature, calls Chorus v3 API to fetch the conversation detail, normalizes to Episode.

## Inputs

- `CHORUS_API_TOKEN` from `.env`.
- Chorus webhook payload (engagement-completed event).
- Episode envelope from spec 011.

## Outputs

- `03_build/pulse/core/adapters/chorus.py` exporting `ChorusAdapter(SignalSourceAdapter)`.
- Activepieces flow `chorus_engagement_completed` (in `pulse_workflows/`).
- One Episode emitted per completed engagement. `content_type='text'`; `content` is the meeting summary + action_items + participant context (matching `rm-intelligence-agent/src/extract_signals.py:67`'s input).

## Definition of Done

- [ ] Webhook signature validated; bad signatures emit `signal-rejected` + return 401.
- [ ] Conversation detail fetched via Chorus v3 API; HTML stripping applied per `rm-intelligence-agent/src/extract_signals.py::strip_html()`.
- [ ] `dedup_key` formula: `f"chorus:conv:{conversation_id}"` per Design 02 §"Idempotency contract."
- [ ] Fuzzy account-name → SFDC Account.Id join lifted from `rm-intelligence-agent/src/rank_accounts.py::fuzz_score()` verbatim; sets `candidate_entities` in Episode.
- [ ] Backfill path: `list_recent_events(since)` calls Chorus v3 `/v3/engagements?since=...`.

## Tests

- **Unit:** mocked Chorus API; verify auth headers + pagination + HTML stripping.
- **Integration:** real Chorus API (Phase 1 demo-data ingestion); ingest 1 engagement end-to-end.
- **Idempotency:** re-fire webhook with same engagement → second call returns `False`.

## Signal definitions involved

Direct consumer signals (via Skill 01's downstream extraction):
- `churn_signal_competitor_mention_v1`
- `expansion_signal_verbal_capacity_mention_v1`
- `talent_burnout_signal_v1`, `talent_growth_concern_v1`, `talent_pay_concern_v1`
- `churn_signal_sentiment_decline_v1` (via Skill 01's sentiment_vector)
- `recognition_signal_advocacy_candidate_v1` (via Skill 01's positive_quote tagging)

## Open questions

None new — `reference_chorus_api` memory and `rm-intelligence-agent/src/chorus_pull.py` cover the API mechanics.

## What this is NOT

- Not Skill 01 (signal extraction) — that's spec 020. Chorus adapter produces Episodes; Skill 01 reads them and extracts.
- Not the affectlayer__Engagement__c join (SFDC adapter's responsibility — spec 012).
