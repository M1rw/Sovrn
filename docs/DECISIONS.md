# SOVRN Architectural Decisions

Last updated: 2026-04-13

This file records active architecture decisions in effect for the current execution track.

## D-001 Canonical Endpoint Only

Decision:

- Use a single canonical conversation endpoint path for chat behavior.

Reason:

- Prevent behavior drift across duplicate handlers.
- Keep routing, persistence, and telemetry semantics consistent.

Consequence:

- Legacy routes may remain for compatibility but are not authoritative.

## D-002 Model Proposes, Backend Decides

Decision:

- Model proposals are advisory; backend computes authoritative resolved action.

Reason:

- Preserve deterministic policy control and safety checks.
- Avoid direct model control over workflow transitions.

Consequence:

- Proposed action mismatches are measured and logged before cutover.

## D-003 No String Triggers for State Transitions

Decision:

- Do not use raw response string heuristics as authoritative transition signals.

Reason:

- String triggers are brittle and hard to test deterministically.

Consequence:

- Contract-validated structures and backend gates are the transition basis.

## D-004 Summaries Are Non-Authoritative

Decision:

- Conversation summaries must never be treated as authoritative state.

Reason:

- Summaries are lossy and primarily for future context compaction.

Consequence:

- Authoritative state remains in thread/snapshot records with versioning.

## D-005 Backend Owns State and Actions

Decision:

- Backend owns state persistence, versioning, and action resolution.

Reason:

- Enables deterministic rollback, conflict detection, and safe rollout.

Consequence:

- Client-facing behavior changes are gated and introduced only after shadow validation.

## D-006 Fail-Open for Shadow and Persistence Side Paths

Decision:

- Shadow parse, telemetry, and persistence side paths must not break chat completion behavior.

Reason:

- Preserve user-facing availability while maturing internal controls.

Consequence:

- Failures in side paths are logged and monitored, not surfaced as hard chat failures.

## Legacy Decision Context (Historical)

The following documents include prior strategic framing and may conflict with current execution constraints:

- docs/legacy/planning/SOVRN_ROADMAP.md
- docs/legacy/planning/SOVRN_ARCHITECTURE_FLOW.md
- docs/SYSTEM_ARCHITECTURE.md
- docs/GAP_ANALYSIS.md

Treat this file plus docs/ARCHITECTURE.md as the current decision baseline.
