-- 0014 — Pre-computed RM communication style prompts
CREATE TABLE IF NOT EXISTS pulse.rm_style_profiles (
    rm_pulse_user_id  TEXT        PRIMARY KEY,
    style_prompt      TEXT        NOT NULL,
    email_count       INT         NOT NULL DEFAULT 0,
    analyzed_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
