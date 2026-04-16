# SOVRN Architecture (Current System)

Last updated: 2026-04-13

This document describes the system as currently implemented in the active execution track.

## Canonical Chat Path

Authoritative chat path:

- POST /api/v1/ai/chat
- File: services/api/app/api/v1/endpoints/ai.py

Principle:

- Canonical endpoint path only for conversation behavior.
- Duplicate legacy handlers are not authoritative.

## Core Flow

1. Request enters canonical chat endpoint.
2. Prompt is assembled by server-side registry when feature flag is enabled.
3. Model output can be parsed against structured contract in shadow mode.
4. Backend computes resolved action (shadow mode) using deterministic gates.
5. Conversation persistence writes thread, turn, and state snapshot (feature-flagged).
6. Non-authoritative summary persistence can run on deterministic turn boundaries.

## Model Proposes, Backend Decides

Current decision model:

- Model output may propose action via structured payload.
- Backend resolves action independently in shadow mode.
- Action mismatch is logged as telemetry.
- Generation handoff behavior is not changed by shadow logic.

This enforces backend authority over actions and state transitions.

## Persistence Model

Conversation persistence entities:

- conversation_threads
- conversation_turns
- conversation_state_snapshots
- conversation_summaries

Authoritative state:

- Thread state_version and authoritative_state in thread/snapshot records.
- Optimistic version check enforced on snapshot writes.

Idempotency:

- thread_id + idempotency_key uniqueness prevents duplicate turn writes.

## Summaries and Resolved Action

Resolved action:

- Produced by backend logic in shadow mode.
- Used for telemetry and quality gating.

Summaries:

- Summary records are explicitly non-authoritative.
- Deterministic trigger: summary runs only on configured turn interval boundaries.
- Summary contract validation rejects invalid payloads safely.
- No context compaction is enabled yet.

## Safety and Compatibility Rules

- Fail-open behavior: persistence and shadow parsing never break chat fallback behavior.
- Client-visible chat response shape remains unchanged.
- No frontend dependency was introduced for these backend phases.

## Out of Scope for Current Architecture

The following are future/exploratory and not current behavior:

- Hyper-parallel multi-agent generation runtime
- CRDT live assembly pipeline
- Marketplace and monetization features

For these concepts, see exploratory docs listed in docs/ROADMAP.md.
