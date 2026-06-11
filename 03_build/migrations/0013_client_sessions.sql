-- 0013 — Authenticated client sessions (24hr expiry)
CREATE TABLE IF NOT EXISTS pulse.client_sessions (
    session_id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_email    TEXT        NOT NULL,
    account_id       TEXT        NOT NULL,
    rm_owner_id      TEXT        NOT NULL,
    rm_name          TEXT        NOT NULL,
    rm_pulse_user_id TEXT,
    client_name      TEXT        NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at       TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_client_sessions_email
    ON pulse.client_sessions (contact_email);
