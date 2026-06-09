CREATE TABLE IF NOT EXISTS pulse.support_conversations (
    conversation_id  UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          TEXT    NOT NULL,
    title            TEXT    NOT NULL DEFAULT 'New conversation',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_support_conv_user
    ON pulse.support_conversations (user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS pulse.support_messages (
    message_id       UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID    NOT NULL
                             REFERENCES pulse.support_conversations (conversation_id)
                             ON DELETE CASCADE,
    role             TEXT    NOT NULL CHECK (role IN ('user', 'assistant')),
    content          TEXT    NOT NULL,
    tool_calls       JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_support_msg_conv
    ON pulse.support_messages (conversation_id, created_at ASC);
