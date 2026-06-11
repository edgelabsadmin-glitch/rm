-- 0015 — Per-client conversation history (soft delete)
CREATE TABLE IF NOT EXISTS pulse.client_conversations (
    conversation_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_email   TEXT        NOT NULL,
    account_id      TEXT        NOT NULL,
    title           TEXT        NOT NULL DEFAULT 'New conversation',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_client_conv_email
    ON pulse.client_conversations (contact_email, updated_at DESC);

CREATE TABLE IF NOT EXISTS pulse.client_messages (
    message_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID        NOT NULL
                                REFERENCES pulse.client_conversations (conversation_id)
                                ON DELETE CASCADE,
    role            TEXT        NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT        NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_client_msg_conv
    ON pulse.client_messages (conversation_id, created_at ASC);
