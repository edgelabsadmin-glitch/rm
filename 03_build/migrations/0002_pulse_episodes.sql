-- SPEC-011 / Design 02 — the episodes audit table + idempotency gate.
-- One row per atomic source event. UNIQUE(dedup_key) is the idempotency
-- contract: re-ingesting the same event is a no-op (INSERT ... ON CONFLICT
-- DO NOTHING in core/ingest/pipeline.py). Episodes are immutable by intent
-- (no ON CONFLICT DO UPDATE). Idempotent migration.

CREATE SCHEMA IF NOT EXISTS pulse;

CREATE TABLE IF NOT EXISTS pulse.episodes (
    episode_id          UUID PRIMARY KEY,
    dedup_key           TEXT        NOT NULL UNIQUE,

    -- Provenance
    source              TEXT        NOT NULL,
    source_event_id     TEXT,
    source_url          TEXT,
    source_timestamp    TIMESTAMPTZ,

    -- Content (source shape preserved: text stored as a JSON string, dict as object)
    content_type        TEXT        NOT NULL,
    content             JSONB       NOT NULL,
    subject             TEXT,
    description         TEXT,

    -- Routing hints
    candidate_entities  JSONB       NOT NULL DEFAULT '[]'::jsonb,
    tags                TEXT[]      NOT NULL DEFAULT '{}',

    -- Pulse-internal lifecycle (Design 02 envelope)
    processing_state    TEXT        NOT NULL DEFAULT 'received',
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episodes_source_time ON pulse.episodes (source, source_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_episodes_state       ON pulse.episodes (processing_state);
