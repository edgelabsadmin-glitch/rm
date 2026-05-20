# Spec 012 — SFDC Signal Source Adapter

**Maps to:** §14 Signal sources (Salesforce); Design 02; §13.2 row "Pull all talent profiles from Salesforce" + multiple §13.4 rows; §6 rule 7 (SFDC system-of-record).
**Depends on:** specs 011, 008.
**Effort:** 2.0 days. **Largest single adapter spec.**

## Description

Implement the Salesforce Signal Source Adapter. Read-only ingestion of: Account, Contact, Opportunity, RM_Outreach__c, Associates__c, Account_Plan__c, Case (including descriptions per Decision 35), affectlayer__Engagement__c. Uses `sf` CLI subprocess (per PM_CONTEXT `reference_sfdc_access` memory and Decision log entry 14 — `--target-org production`). Lifts the SOQL query patterns from `rm-intelligence-agent/src/sfdc_pull.py` verbatim and extends to cover Case descriptions + Account_Plan__c.

Triggered by Activepieces flow `sfdc_poll_changes` (cron every 5 minutes per ADR-002 §"Phase 1 flow inventory"). The flow queries SFDC for records modified since `last_synced_at`, fans out a per-record POST to `/webhooks/sfdc`. The adapter's `receive_webhook` validates + normalizes each record into an Episode.

Per Decision 35 (Case-description ingestion ~0.5 day): Case `Description` and `Details__c` are first-class Episode content fields, not just metadata. The risk-tagged Cases narrative is what makes this signal source qualitatively richer than `rm-intelligence-agent`'s prior pull.

## Inputs

- `sf` CLI installed (Spike 1 confirmed).
- SFDC `production` alias authenticated (Q21 — must be confirmed Day-1).
- The known-validated schema from Spike 1 §B + Q22 resolution (`Segment__c` is the tier field).
- Episode envelope from spec 011.

## Outputs

- `03_build/pulse/core/adapters/sfdc.py` exporting `SFDCAdapter(SignalSourceAdapter)`.
- Activepieces flow `sfdc_poll_changes` (in `pulse_workflows/sfdc_poll_changes.json`).
- One Episode emitted per SFDC record change. `content_type='json'`; `content={object_type, record_id, fields}`. Tags include `["sfdc", object_type.lower()]`.

## Definition of Done

- [ ] Adapter ingests all 8 in-scope object types successfully (verified by polling a known sandbox state and counting Episodes emitted).
- [ ] Case `Description` + `Details__c` populated as Episode `content.description_text` + `content.details_text` (not truncated; full text preserved).
- [ ] Risk-tagged Case filtering applied: `Categories__c IN (...)` per the existing 14-value EDGE taxonomy lifted from `rm-intelligence-agent/src/sfdc_pull.py:109-115`.
- [ ] `Account.Segment__c` ingested onto the Customer entity in Graphiti (drives tier-aware behavior in policy module).
- [ ] `dedup_key` formula: `f"sfdc:{object_api_name}:{record_id}:{last_modified_iso}"` per Design 02 §"Idempotency contract."
- [ ] Per-record latency P95 <500ms (lightweight SOQL + Episode emission; no LLM call in the adapter).
- [ ] `Associates__c.Stage__c` transitions trigger a separate edge update (`was_in_stage` bi-temporal edge per Design 01).
- [ ] Q142 (associate_stage_history sub-spec from `client_termination_pattern_v1`): a `pulse.associate_stage_history` table records every observed Stage transition (allowing reliable transition-date computation downstream).

## Tests

- **Unit:** mocked `sf` CLI invocations; verify SOQL query strings + record normalization.
- **Integration:** real `sf` CLI against `production` (read-only); ingest one record from each of 8 object types; verify Episode and event log.
- **Idempotency:** re-poll same window → zero new Episodes.

## Signal definitions involved

This adapter is upstream of *every* signal that reads SFDC data. Direct dependents:
- `churn_signal_contact_disengagement_v1` (RM_Outreach + Case data)
- `churn_signal_renewal_period_silence_v1` (Opportunity + Account_Plan__c)
- `escalation_signal_case_pattern_v1`, `escalation_signal_severity_jump_v1` (Case)
- `client_termination_pattern_v1` (Associates__c stage transitions)
- `account_silence_pattern_v1` (any SFDC activity)
- `recognition_signal_advocacy_candidate_v1` (RM_Outreach Customer_Health__c)

## Open questions

- Q21 — SFDC sandbox refresh (blocking schema describe completeness; doesn't block this spec because rm-intelligence-agent's schema is sufficient floor).
- Q58 (Opportunity.Type enum), Q61 (Talent contact email source), Q71 (Account stage enum), Q72 (placement Start_Date semantics), Q86 (Customer_Health__c enum) — all pending Q21; spec 012 ships with assumed values from Spike 1 §B; tunes after Q21.

## What this is NOT

- Not SFDC write-back (that's spec 032 dispatch handlers, and only via approved Actions per §6 rule 6).
- Not Chorus (spec 013 — separate adapter despite Chorus's SFDC integration via affectlayer__Engagement__c).
- Not where the schema is enumerated — schema lives in spec 005's Pydantic models.
