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

1. Sync current `vscode-vfs://github/Miljte/Sovrn` edits into local clone before runtime execution (`C:\Miljte\Sovrn` currently does not include latest workspace changes).
2. Run staging preview latency benchmark (preferred: `eval/load/run-preview-latency.ps1`; fallback: `eval/load/preview_latency_benchmark.py`) and verify p95 total <= 1.5s in `eval/load/phase2_preview_latency_report.json`.
3. Capture benchmark evidence in `docs/Plan/PHASE2_PREVIEW_LATENCY_VALIDATION_2026-04-17.md` after the staging run completes.
4. Confirm canary monitoring checks in staging after rollout ring activation (preview latency and stream reconnect metrics).

Completed in current implementation slice:

1. Added frontend preview lifecycle integration helper coverage and validated suites (`src/app/builder/preview-lifecycle.test.ts`, `src/lib/api.preview-stream.test.ts`, `src/hooks/use-preview-runtime.test.ts`) with `npx jest` (3 suites, 12 tests passed).
2. Added backend endpoint-level Phase 2 contract tests and validated expanded backend suite with `py -3.11 -m pytest tests/test_phase2_preview_bootstrap.py tests/test_generation_service_preview_budget.py` (18 passed).

## Documentation Follow-Up (No Behavioral Change)

1. Add a top-level pointer from historical docs to docs/SOVRN_OVERVIEW.md as canonical status source.
2. Mark conflicting completion-claim sections in legacy docs with explicit DEPRECATED notes in a future doc-only pass.
