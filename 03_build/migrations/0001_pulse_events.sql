-- SPEC-008 / Design 04 — Event Log + Reasoning Capture.
-- Single append-only events table in the `pulse` schema. Idempotent: safe to
-- re-run (IF NOT EXISTS throughout). Applied by scripts/db_migrate.py.

CREATE SCHEMA IF NOT EXISTS pulse;

CREATE TABLE IF NOT EXISTS pulse.events (
    event_id        UUID PRIMARY KEY,
    event_type      TEXT        NOT NULL,
    event_version   INT         NOT NULL DEFAULT 1,
    occurred_at     TIMESTAMPTZ NOT NULL,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Entity refs (nullable — not every event references each)
    customer_id     TEXT,   -- SFDC Account.Id
    talent_id       TEXT,   -- SFDC Associates__c.Id
    rm_id           TEXT,   -- SFDC User.Id
    case_id         TEXT,   -- SFDC Case.Id
    action_id       UUID,   -- ties suggested -> approved -> executed -> outcome
    episode_id      UUID,   -- ties to ingested Episode (Design 02)
    skill_id        TEXT,   -- "renewal-watcher", "ebr-prep", ...

    -- Structured per event_type (schemas in core/events/types.py)
    payload         JSONB       NOT NULL,

    -- Tier-aware policy substrate
    tier_class      TEXT,   -- "SMB" | "Mid" | "Enterprise" | NULL
    urgency         TEXT,   -- only for action-suggested

    -- Operational
    correlation_id  UUID,   -- ties bursts (one signal -> one chain of events)
    actor           TEXT,   -- "agent" | "user:<user_id>" | "system" | "policy"

    -- Reasoning (only on agent events; bounded length)
    reasoning_text  TEXT,
    reasoning_tags  TEXT[],

    -- ADR-003 cross-link to the Langfuse trace tree
    trace_id        UUID
);

-- Index strategy (Design 04 §"Storage").
CREATE INDEX IF NOT EXISTS idx_events_type_time     ON pulse.events (event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_action        ON pulse.events (action_id);
CREATE INDEX IF NOT EXISTS idx_events_customer_time ON pulse.events (customer_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_rm_time       ON pulse.events (rm_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_skill_time    ON pulse.events (skill_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_correlation   ON pulse.events (correlation_id);
