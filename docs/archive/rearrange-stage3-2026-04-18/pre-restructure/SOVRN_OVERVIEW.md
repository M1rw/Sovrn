# SOVRN Overview

Last updated: 2026-04-13

This document is the canonical high-level explanation of what SOVRN is today.

## What SOVRN Is

SOVRN is a hosted AI website generation platform.

- It is not a downloadable desktop product.
- Users interact with hosted APIs and UI flows.
- AI inference is self-hosted inside SOVRN-controlled infrastructure.

## How It Works (High Level)

1. A user sends a request through the AI chat/generation flow.
2. The canonical backend endpoint processes conversation context.
3. The model returns output proposals.
4. The backend validates contracts and resolves actions.
5. Conversation state is persisted with deterministic versioning.
6. Non-authoritative summaries are stored when deterministic summary triggers fire.

## What Offline Means

In SOVRN documentation, offline means:

- No dependency on third-party AI APIs at runtime.
- No per-request external AI API cost.
- Inference is self-hosted by SOVRN backend services.

This does not mean users download and run a standalone local app.

## Core Value Proposition

- Predictable backend-governed behavior, not raw model output control.
- Cost control through self-hosted inference (no external AI API spend).
- Deterministic rollout using feature flags, schema contracts, and safe fail-open handling.
- Canonical endpoint governance to avoid behavior drift across duplicate routes.

## Current Reality Snapshot

Implemented in the current execution track:

- Canonical chat route governance and prompt assembly controls.
- Structured output shadow parsing and backend action resolution in shadow mode.
- Conversation persistence (thread, turn, snapshot) behind feature flags.
- Deterministic non-authoritative summary trigger and summary contract validation.

Not yet implemented in current track:

- Context compaction based on summaries.
- Full cutover to client-visible backend-resolved action contract.

## Legacy Documentation Notes

The repository keeps historical and planning documents. Some contain conflicting status claims.

DEPRECATED snapshot status claims (historical, not canonical):

- docs/legacy/status/ALL_COMPLETE.md
- docs/legacy/status/BUILD_COMPLETE.md
- docs/legacy/status/FINAL_VERIFICATION.md
- docs/legacy/status/PIPELINE_STATUS.md
- docs/README_PIPELINE.md
- docs/legacy/status/SESSION_SUMMARY.md

Exploratory strategy and future concepts (not current system behavior):

- docs/legacy/planning/SOVRN_ROADMAP.md
- docs/legacy/planning/SOVRN_ARCHITECTURE_FLOW.md
- docs/legacy/planning/SOVRN_RETENTION_AND_ARCH_ANALYSIS.md

Use this file plus docs/ARCHITECTURE.md and docs/ROADMAP.md as the current canonical narrative.
