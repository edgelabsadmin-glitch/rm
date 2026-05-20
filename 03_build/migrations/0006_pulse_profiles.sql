-- SPEC-029 / Design 06 — Per-Profile Markdown Layer.
-- One Markdown profile per Customer / Talent / RM entity, auto-regenerated from
-- the graph + event log, with an RM-edit override layer. Idempotent migration.

CREATE SCHEMA IF NOT EXISTS pulse;

CREATE TABLE IF NOT EXISTS pulse.profiles (
    profile_id          UUID PRIMARY KEY,
    profile_type        TEXT        NOT NULL,           -- 'customer' | 'talent' | 'rm'
    entity_id           TEXT        NOT NULL UNIQUE,    -- SFDC Id (Account / Associates__c / User)
    content_md          TEXT        NOT NULL,
    content_hash        TEXT        NOT NULL,           -- SHA256 of content_md
    last_regenerated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Override layer: the RM's edit is preserved across regenerations until the
    -- fresh auto-gen diverges from override_source_md (then a re-merge surfaces).
    override_active     BOOLEAN     NOT NULL DEFAULT FALSE,
    override_source_md  TEXT,                           -- auto-gen at the time the RM started editing
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profiles_entity ON pulse.profiles (entity_id);
CREATE INDEX IF NOT EXISTS idx_profiles_type_regen ON pulse.profiles (profile_type, last_regenerated_at);
