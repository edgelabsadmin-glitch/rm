-- 0012 — OTP codes for client email auth
CREATE TABLE IF NOT EXISTS pulse.client_otps (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email          TEXT        NOT NULL,
    otp_hash       TEXT        NOT NULL,
    expires_at     TIMESTAMPTZ NOT NULL,
    used_at        TIMESTAMPTZ,
    attempt_count  INT         NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_client_otps_email
    ON pulse.client_otps (email, created_at DESC);
