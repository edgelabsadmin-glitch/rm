-- SPEC-009 / SPEC-010 — operational settings (Design 04 §"Kill switch" / §"Policy").
-- Singleton row (id=1) holding the kill-switch state + the per-tier auto-approve
-- skill list. Idempotent. Rejection counters are NOT stored here — they are
-- computed from the event log (Design 04 §"What this is NOT": no stored
-- aggregations, everything derived from pulse.events).

CREATE SCHEMA IF NOT EXISTS pulse;

CREATE TABLE IF NOT EXISTS pulse.settings (
    id                  INT         PRIMARY KEY DEFAULT 1,
    kill_switch         JSONB       NOT NULL DEFAULT '{"global": false, "by_skill": {}, "by_customer": {}}'::jsonb,
    auto_approve_skills JSONB       NOT NULL DEFAULT '["recognition", "talent-care", "onboarding"]'::jsonb,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT settings_singleton CHECK (id = 1)
);

INSERT INTO pulse.settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
