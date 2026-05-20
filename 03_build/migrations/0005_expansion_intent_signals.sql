-- SPEC-015 / Spike 4 §3.3 — the opportunity-tracker ↔ Pulse contract table.
-- opportunity-tracker mirror-writes job-posting matches here (one row per
-- posting); Pulse polls rows with processed_at IS NULL, ingests each as an
-- Episode, and stamps processed_at / pulse_episode_id / processed_status.
-- Idempotent migration.

CREATE SCHEMA IF NOT EXISTS pulse;

CREATE TABLE IF NOT EXISTS pulse.expansion_intent_signals (
    posting_id           TEXT PRIMARY KEY,          -- opp-tracker's deterministic hash
    account_id           TEXT        NOT NULL,      -- SFDC Account.Id
    account_name         TEXT        NOT NULL,
    title                TEXT        NOT NULL,
    company              TEXT,
    location             TEXT,
    source               TEXT        NOT NULL,      -- linkedin | indeed | career_page | greenhouse | lever
    url                  TEXT,
    date_posted          TEXT,
    description          TEXT,
    first_seen_date      TIMESTAMPTZ NOT NULL,

    -- match output
    match_tier           TEXT,                      -- hottest | warm | general | off-scope
    matched_role         TEXT,
    matched_industry     TEXT,
    match_score          INTEGER,
    reasoning            TEXT,
    outreach_suggestion  TEXT,
    signals              TEXT[],
    work_arrangement     TEXT,                      -- remote | hybrid | on-site | unspecified (Change B)

    -- ingestion bookkeeping
    ingested_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- when opp-tracker wrote the row
    processed_at         TIMESTAMPTZ,                          -- when Pulse ingested it; NULL until then
    pulse_episode_id     UUID,                                 -- Pulse Episode UUID after ingestion
    processed_status     TEXT                                  -- ingested | skipped:off-scope | skipped:dup | failed
);

CREATE INDEX IF NOT EXISTS idx_eis_unprocessed ON pulse.expansion_intent_signals (account_id) WHERE processed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_eis_account     ON pulse.expansion_intent_signals (account_id, first_seen_date DESC);
CREATE INDEX IF NOT EXISTS idx_eis_tier        ON pulse.expansion_intent_signals (match_tier);
