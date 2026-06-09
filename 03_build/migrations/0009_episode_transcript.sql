-- SPEC backfill — add transcript storage to pulse.episodes.
-- transcript: raw speaker-labeled text (Zoom VTT parsed to plain text,
--             Chorus transcript when available).
-- source_url: already exists; backfill populates it for zoom (share_url)
--             and chorus (https://chorus.ai/meeting/{source_event_id}).
-- Idempotent: ADD COLUMN IF NOT EXISTS.

ALTER TABLE pulse.episodes
    ADD COLUMN IF NOT EXISTS transcript TEXT;
