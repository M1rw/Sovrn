# API Surface

Last updated: 2026-04-18

## Core Domains

- Auth and user session management.
- Project lifecycle and generation requests.
- Job polling and generation timeline state.
- Internal orchestration processing and regression checks.
- Patch contract validation and resolution flows.

## Operational Contract Notes

1. Generation requests include quality_mode values: fast, balanced, high.
2. Queue priority is derived from orchestration lane and quality mode.
3. Job output may include orchestration timeline metadata for UI rendering.
4. Internal processing supports cooperative cancellation handling.

## Source of Truth

- OpenAPI endpoint in running API environment.
- Backend schemas and endpoint modules in services/api.
- Targeted endpoint tests in services/api/tests.
