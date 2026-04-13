-- Conversation persistence schema for existing databases.
-- Authoritative state is stored in conversation_threads and conversation_state_snapshots.
-- Summaries are non-authoritative and stored in conversation_summaries.

CREATE TABLE IF NOT EXISTS conversation_threads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    state_version BIGINT NOT NULL DEFAULT 1,
    authoritative_state JSONB NOT NULL DEFAULT '{}',
    locked_constraints JSONB NOT NULL DEFAULT '[]',
    last_turn_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversation_threads_user ON conversation_threads(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_threads_project ON conversation_threads(project_id);
CREATE INDEX IF NOT EXISTS idx_conversation_threads_created ON conversation_threads(created_at);

CREATE TABLE IF NOT EXISTS conversation_turns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id UUID NOT NULL REFERENCES conversation_threads(id) ON DELETE CASCADE,
    turn_index INTEGER NOT NULL,
    user_message TEXT NOT NULL,
    model_raw_output JSONB,
    server_response JSONB NOT NULL DEFAULT '{}',
    parse_status VARCHAR(30) NOT NULL DEFAULT 'not_attempted',
    provider VARCHAR(50),
    model VARCHAR(100),
    latency_ms INTEGER,
    tokens_used INTEGER,
    idempotency_key VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_conversation_turns_thread_turn UNIQUE(thread_id, turn_index),
    CONSTRAINT uq_conversation_turns_thread_idempotency UNIQUE(thread_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_conversation_turns_thread ON conversation_turns(thread_id);
CREATE INDEX IF NOT EXISTS idx_conversation_turns_created ON conversation_turns(created_at);
CREATE INDEX IF NOT EXISTS idx_conversation_turns_parse_status ON conversation_turns(parse_status);

CREATE TABLE IF NOT EXISTS conversation_state_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id UUID NOT NULL REFERENCES conversation_threads(id) ON DELETE CASCADE,
    turn_id UUID REFERENCES conversation_turns(id) ON DELETE SET NULL,
    state_version BIGINT NOT NULL,
    authoritative_state JSONB NOT NULL DEFAULT '{}',
    locked_constraints JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_conversation_state_snapshots_thread_version UNIQUE(thread_id, state_version)
);

CREATE INDEX IF NOT EXISTS idx_conversation_state_snapshots_thread ON conversation_state_snapshots(thread_id);
CREATE INDEX IF NOT EXISTS idx_conversation_state_snapshots_turn ON conversation_state_snapshots(turn_id);

CREATE TABLE IF NOT EXISTS conversation_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id UUID NOT NULL REFERENCES conversation_threads(id) ON DELETE CASCADE,
    from_turn_index INTEGER NOT NULL,
    to_turn_index INTEGER NOT NULL,
    summary_json JSONB NOT NULL DEFAULT '{}',
    summarizer_version VARCHAR(50),
    quality_score NUMERIC(5,4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_conversation_summary_turn_range CHECK (to_turn_index >= from_turn_index)
);

CREATE INDEX IF NOT EXISTS idx_conversation_summaries_thread ON conversation_summaries(thread_id);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_to_turn ON conversation_summaries(thread_id, to_turn_index);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'conversation_threads_updated_at'
    ) THEN
        CREATE TRIGGER conversation_threads_updated_at BEFORE UPDATE ON conversation_threads
            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    END IF;
END;
$$;
