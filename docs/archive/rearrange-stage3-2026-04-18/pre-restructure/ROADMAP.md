# SOVRN Roadmap

Last updated: 2026-04-13

This roadmap separates current execution-track delivery from future exploratory concepts.

## Status Legend

- Implemented: finished in codebase
- In progress: active next-phase work
- Future: planned, not implemented

## Phase 1 to Phase 5 (Current Execution Track)

## Phase 1: Canonical Path and Prompt Governance

Status: Implemented

Delivered:

- Canonical chat route governance checks
- Legacy duplicate chat path deprecation behavior
- Prompt registry modules and ordered assembly with checksum validation
- Canonical endpoint prompt assembly wiring behind feature flag

## Phase 2: Structured Contract and Backend Action Governance

Status: Implemented

Delivered:

- Structured output contract parser with single repair attempt (shadow)
- Backend-resolved action in shadow mode
- Proposed action vs resolved action mismatch telemetry
- Shadow quality-gate metrics and thresholds

## Phase 3: Conversation Persistence

Status: Implemented

Delivered:

- Conversation persistence schema and rollback migration
- ORM models and repository layer
- Canonical endpoint persistence writes (thread, turn, snapshot) behind feature flag
- Idempotency key handling and optimistic version conflict behavior

## Phase 4: Summarization and Compaction

Status: In progress

Delivered:

- Deterministic summary trigger rules
- Non-authoritative summary output contract
- Safe rejection path for invalid summary payloads

Remaining before Phase 4 completion:

- Context compaction read/write integration (P4-2)
- Compaction-specific integration tests and rollout gates

## Phase 5: Contract Cutover and Hardening

Status: Future

Planned:

- Production cutover from shadow action signals to client-visible resolved-action contract
- Elimination of residual string-trigger behavior from conversation state transitions
- Expanded end-to-end testing and release hardening for canonical path behavior

## Future Roadmap (Exploratory, Not Current Behavior)

The items below are strategic ideas from planning docs, not current committed implementation behavior.

- Specialist agent swarm and speculative parallel generation
- CRDT-based real-time merge/preview concepts
- Retention and marketplace concepts
- Optional managed deployment and cloud sync offerings

Primary exploratory references:

- docs/legacy/planning/SOVRN_ROADMAP.md
- docs/legacy/planning/SOVRN_ARCHITECTURE_FLOW.md
- docs/legacy/planning/SOVRN_RETENTION_AND_ARCH_ANALYSIS.md

## Legacy Docs with Conflicting Completion Claims

DEPRECATED status snapshots (historical references only):

- docs/legacy/status/ALL_COMPLETE.md
- docs/legacy/status/BUILD_COMPLETE.md
- docs/legacy/status/FINAL_VERIFICATION.md
- docs/legacy/status/PIPELINE_STATUS.md
- docs/README_PIPELINE.md
- docs/legacy/status/SESSION_SUMMARY.md

These are kept for historical traceability and are not the canonical roadmap source.
