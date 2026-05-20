-- SPEC-012 (Q142) — observed Associates__c.Stage__c transitions.
-- The SFDC adapter records every observed (associate, stage, observed_at) so
-- downstream signals (e.g. client_termination_pattern_v1) can compute reliable
-- transition dates. UNIQUE on (associate_id, stage, observed_at) makes
-- re-polling idempotent. Idempotent migration.

CREATE SCHEMA IF NOT EXISTS pulse;

CREATE TABLE IF NOT EXISTS pulse.associate_stage_history (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    associate_id  TEXT        NOT NULL,
    account_id    TEXT,
    stage         TEXT        NOT NULL,
    observed_at   TIMESTAMPTZ NOT NULL,   -- the record's LastModifiedDate
    recorded_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (associate_id, stage, observed_at)
);

CREATE INDEX IF NOT EXISTS idx_assoc_stage_assoc ON pulse.associate_stage_history (associate_id, observed_at DESC);
