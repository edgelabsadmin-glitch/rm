-- Add recording_password column for Zoom meetings (backfilled via backfill_passwords.py).
ALTER TABLE pulse.episodes
    ADD COLUMN IF NOT EXISTS recording_password TEXT;
