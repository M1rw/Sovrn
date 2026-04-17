# Phase 0 Load Baseline - 2026-04-17

## Scope

This baseline validates the k6 load harness and scenario logic added under eval/load.

Target used for this run:

- Local mock API on [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Purpose: harness validation and scenario contract verification
- Not a production performance baseline for real API + worker + inference stack

## Environment

- k6: v1.7.1 portable binary
- Host: Windows (local shell)
- Scenarios:

  - eval/load/k6_chat.js
  - eval/load/k6_generation_flow.js

## Run 1: Chat Scenario

Command profile:

- K6_VUS=5
- K6_DURATION=15s
- SOVRN_BASE_URL=[http://127.0.0.1:8000](http://127.0.0.1:8000)

Result summary:

- Checks passed: 1125 / 1125 (100.00%)
- HTTP request failures: 0.00% (0/375)
- p95 http_req_duration: 3.09ms
- p99 http_req_duration: 9.19ms
- Requests: 375 total

Threshold status:

- checks rate > 0.99: pass
- http_req_failed rate < 0.01: pass
- http_req_duration p95 < 2500ms: pass
- http_req_duration p99 < 5000ms: pass

## Run 2: Generation Flow Scenario

Command profile:

- K6_VUS=2
- K6_DURATION=20s
- K6_JOB_MAX_POLLS=5
- K6_JOB_POLL_INTERVAL_MS=200
- SOVRN_BASE_URL=[http://127.0.0.1:8000](http://127.0.0.1:8000)
- SOVRN_TOKEN=mock-token

Result summary:

- Checks passed: 500 / 500 (100.00%)
- HTTP request failures: 0.00% (0/400)
- p95 http_req_duration: 1.69ms
- Requests: 400 total

Threshold status:

- checks rate > 0.95: pass
- http_req_failed rate < 0.03: pass
- http_req_duration p95 < 7000ms: pass

## Interpretation

- The load scripts are runnable and stable in this environment.
- Request/response expectations in both scenarios are valid.
- This report should be treated as a harness baseline only, because the target was a mock API.

## Next Baseline Required

To complete production-representative baseline capture:

- Run both scenarios against real canonical API + worker + inference stack
- Capture p50/p95/p99 from /metrics/http and inference /metrics/system during load
- Publish dashboard screenshots and alert behavior snapshots for Phase 0 exit gate evidence
