# Architecture Snapshot

Last updated: 2026-04-18

## Service Topology

- Web frontend: Next.js application for build, preview, and orchestration UX.
- API backend: FastAPI service for auth, projects, generation, orchestration, and contracts.
- Worker: async job processor handling queued generation workloads.
- Inference service: model runtime for generation stages and telemetry inputs.
- Data plane: PostgreSQL (source of record) and Redis (queue/cache).

## Runtime Characteristics

1. Generation requests are queued with lane-aware priority.
2. AQE level selection adapts quality depth under load signals.
3. Orchestration stage state is persisted and exposed to frontend timeline UI.
4. Cancellation and budget controls prevent runaway execution paths.

## Reliability Controls

- Queue depth and inference wait signals feed AQE decisions.
- Critic retry policy is bounded and configurable.
- Runtime budget controls enforce request and stage limits.
- Targeted backend tests validate orchestration contracts.

## Security Surface

- Environment-only secret handling.
- Explicit database URL bootstrap order.
- Dedicated security runbook and key rotation guidance.
