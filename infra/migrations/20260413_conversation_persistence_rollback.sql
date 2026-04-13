-- Rollback for conversation persistence schema migration.
-- Drops conversation persistence objects in reverse dependency order.

DROP TRIGGER IF EXISTS conversation_threads_updated_at ON conversation_threads;

DROP TABLE IF EXISTS conversation_summaries;
DROP TABLE IF EXISTS conversation_state_snapshots;
DROP TABLE IF EXISTS conversation_turns;
DROP TABLE IF EXISTS conversation_threads;
