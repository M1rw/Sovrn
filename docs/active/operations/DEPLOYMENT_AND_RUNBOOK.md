# Deployment and Runbook

Last updated: 2026-04-18

## Local Validation

1. Start services and dependencies.
2. Run targeted backend orchestration tests.
3. Run frontend test and type-check suites for touched surfaces.
4. Run repository audit for non-production markers.

## Staging Gate Sequence

1. Preview latency benchmark with staging credentials.
2. Canary telemetry checks for preview and stream reconnect metrics.
3. Mixed-workload load run to validate AQE transitions under pressure.
4. Record all outcomes in tracking docs before promotion decision.

## Promotion Preconditions

- All required tests are green.
- Quality gates are satisfied.
- Rollback path is documented and validated.
- Risks are reviewed and accepted.

## Rollback Rule

If any gate fails after rollout start, halt promotion and roll back to the last verified release immediately.
