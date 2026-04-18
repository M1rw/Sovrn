# Quality Gates

Last updated: 2026-04-18

## Required Before Promotion

1. Backend orchestration tests pass.
2. Preview latency gate passes in staging.
3. Canary telemetry checks pass in staging.
4. Mixed-workload AQE behavior is validated.
5. Repository hygiene audit has no active-surface production-marker findings.

## Recommended Validation Commands

- py -3.11 -m pytest services/api/tests/test_phase4_orchestration.py -q
- py -3.11 -m pytest services/api/tests/test_phase3_patch_contract.py -q
- E:/Synthos/.venv/Scripts/python.exe scripts/rearrange_audit.py

## Evidence Requirements

- Record command context and outcome in tracking/DELIVERY_LOG.md.
- Link report files used for go/no-go decisions.
- Document failures and remediation attempts explicitly.
