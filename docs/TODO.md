# SOVRN Engineering TODO

Last updated: 2026-04-13

Only actionable pending engineering work is listed below.

## Phase 3 Residual Hardening

1. Add canonical endpoint integration test for idempotent replay on thread_id + idempotency_key.
2. Add integration test for snapshot version conflict path and fail-open logging behavior.
3. Add integration test for thread resume path when thread_id exists vs missing.

## Phase 4 Remaining Work

1. Implement P4-2 context compaction behind feature flag using non-authoritative summaries.
2. Add deterministic compaction boundary tests (no compaction before threshold, compaction at threshold).
3. Add integration test for invalid summary contract payload rejection without chat-path failure.
4. Add telemetry coverage for summary-triggered, summary-skipped, and summary-rejected outcomes.

## Phase 5 Planned Work

1. Promote backend resolved_action contract from shadow-only to production response behavior under flag.
2. Remove residual string-trigger based transition logic from canonical conversation flow.
3. Add end-to-end tests for canonical action resolution outcomes (respond, ask_clarification, ready_to_generate, propose_revision).
4. Define and run canary rollout with measurable quality gates before full cutover.

## Documentation Follow-Up (No Behavioral Change)

1. Add a top-level pointer from historical docs to docs/SOVRN_OVERVIEW.md as canonical status source.
2. Mark conflicting completion-claim sections in legacy docs with explicit DEPRECATED notes in a future doc-only pass.
