-- SPEC-030 / Design 07 — dual-sided account-health cache.
-- Composite of customer-side + talent-side scores (tier-weighted α/β). Cached
-- per Account; recomputed on signal fan-out + nightly. Idempotent migration.

CREATE SCHEMA IF NOT EXISTS pulse;

CREATE TABLE IF NOT EXISTS pulse.account_health (
    account_id          TEXT PRIMARY KEY,            -- SFDC Account.Id
    tier                TEXT        NOT NULL,        -- Healthy|Stable|Watch|At-Risk|Escalated
    composite_score     DOUBLE PRECISION NOT NULL,  -- -100..+100
    customer_side_score DOUBLE PRECISION NOT NULL,
    talent_side_score   DOUBLE PRECISION NOT NULL,
    top_contributors    JSONB       NOT NULL DEFAULT '[]'::jsonb,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tier_changed_at     TIMESTAMPTZ                  -- last tier transition (24h debounce)
);

CREATE INDEX IF NOT EXISTS idx_account_health_tier ON pulse.account_health (tier);
