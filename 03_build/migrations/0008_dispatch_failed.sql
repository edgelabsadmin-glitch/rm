-- SPEC-032 / Design 03 — dispatch dead-letter table.
-- After the retry budget (3 attempts, exponential backoff) is exhausted, a
-- failed dispatch lands here for operator follow-up. The authoritative failure
-- signal is still the `dispatch-failed` event; this table is the actionable
-- queue of un-dispatched approved actions. Idempotent migration.

CREATE SCHEMA IF NOT EXISTS pulse;

CREATE TABLE IF NOT EXISTS pulse.dispatch_failed (
    action_id       UUID PRIMARY KEY,           -- the approved action that could not dispatch
    handler         TEXT        NOT NULL,        -- "email" | "sfdc_task" | "calendar_hold"
    attempts        INT         NOT NULL,        -- attempts made before dead-lettering
    error_class     TEXT        NOT NULL,
    error_message   TEXT,
    failed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ                  -- set when an operator clears it
);

CREATE INDEX IF NOT EXISTS idx_dispatch_failed_unresolved
    ON pulse.dispatch_failed (failed_at DESC)
    WHERE resolved_at IS NULL;
