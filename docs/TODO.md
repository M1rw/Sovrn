# SOVRN Engineering TODO

Last updated: 2026-04-17

Only actionable pending engineering work is listed below.

## Phase 1 Closure Status (Completed 2026-04-17)

1. Conversation persistence hardening tests completed (idempotent replay, thread resume, snapshot conflict fail-open).
2. Context compaction integration and summary contract rejection coverage completed.
3. Resolved-action contract promotion and endpoint-level outcome coverage completed.
4. Residual string-trigger transition logic removed from canonical builder flow.
5. Canary ring simulation and load fail-open validations completed (see docs/Plan/PHASE1_CANARY_VALIDATION_2026-04-17.md).

## Phase 2 Next Work (WebContainer Runtime)

1. Run staging preview latency benchmark (preferred: `eval/load/run-preview-latency.ps1`; fallback: `eval/load/preview_latency_benchmark.py`) and verify p95 total <= 1.5s in `eval/load/phase2_preview_latency_report.json`.
2. Capture benchmark evidence in `docs/Plan/PHASE2_PREVIEW_LATENCY_VALIDATION_2026-04-17.md` after the staging run completes.

## Documentation Follow-Up (No Behavioral Change)

1. Add a top-level pointer from historical docs to docs/SOVRN_OVERVIEW.md as canonical status source.
2. Mark conflicting completion-claim sections in legacy docs with explicit DEPRECATED notes in a future doc-only pass.
