# Phase 2 Preview Latency Validation - 2026-04-17

## Objective

Validate Phase 2 preview runtime responsiveness against the gate:

- p95 edit-to-preview latency <= 1.5s in staging

## Harness

Benchmark script:

- eval/load/preview_latency_benchmark.py

The harness measures these stages per iteration:

1. POST /api/v1/projects/{project_id}/preview-session
2. POST /api/v1/projects/{project_id}/preview-session/verify
3. GET preview-artifact endpoint returned by verify
4. GET /api/v1/projects/{project_id}/preview-events and wait for first preview.updated event

## Staging Run Inputs

Required:

- SOVRN_BASE_URL
- SOVRN_TOKEN
- SOVRN_PROJECT_ID

Optional:

- SOVRN_GENERATION_ID
- SOVRN_ENTRYPOINT (default index.html)
- SOVRN_PREVIEW_BENCH_ITERATIONS (default 30)
- SOVRN_PREVIEW_BENCH_WARMUP (default 3)
- SOVRN_PREVIEW_TARGET_P95_MS (default 1500)

## Runtime Evidence

Command used:

```powershell
$env:SOVRN_BASE_URL='https://<staging-api-host>'
$env:SOVRN_TOKEN='<staging-bearer-token>'
$env:SOVRN_PROJECT_ID='<project-id-with-generation>'
py -3.11 eval/load/preview_latency_benchmark.py
```

Alternative one-command runner:

```powershell
powershell -ExecutionPolicy Bypass -File eval/load/run-preview-latency.ps1 \
  -BaseUrl 'https://<staging-api-host>' \
  -Token '<staging-bearer-token>' \
  -ProjectId '<project-id-with-generation>'
```

Optional prerequisite check before benchmark execution:

```powershell
powershell -ExecutionPolicy Bypass -File eval/load/check-preview-latency-prereqs.ps1
```

Report output:

- eval/load/preview_latency_report.json

Latest precheck attempt (2026-04-17):

- `SOVRN_BASE_URL`, `SOVRN_TOKEN`, and `SOVRN_PROJECT_ID` were not present in shell environment.
- `http://localhost:8000/health` and `http://localhost/health` were unreachable from host.
- Benchmark runner was not executed because required staging inputs and reachable API target were unavailable.

Latest local mock dry-run (2026-04-17, non-gating sanity check):

- Command: `powershell -ExecutionPolicy Bypass -File eval/load/run-preview-latency.ps1 -BaseUrl http://127.0.0.1:8000 -Token mock-token -ProjectId mock-project -Iterations 5 -Warmup 1 -OutputPath eval/load/preview_latency_report.local_mock.json`
- Report: `eval/load/preview_latency_report.local_mock.json`
- successful iterations: 5/5
- p50 total latency: 5.06 ms
- p95 total latency: 6.57 ms
- p99 total latency: 6.80 ms
- p95 stream first update latency: 2.94 ms
- gate status in mock run: PASS
- Note: this validates harness wiring only and does not satisfy the staging gate.
- Note: `run-preview-latency.ps1` was hardened to use `-LiteralPath` operations so it runs correctly from bracketed clone paths such as `E:\Synthos\[Sovrn]`.

## Result

Staging gate status: pending execution in staging shell with required credentials.

- successful iterations: not yet executed in staging
- p50 total latency: pending staging run
- p95 total latency: pending staging run
- p99 total latency: pending staging run
- p95 stream first update latency: pending staging run
- gate (p95 <= 1500ms and zero failed iterations): pending staging run

## Notes

- If p95 exceeds target, keep Phase 2 open and stabilize preview runtime path before progressing.
- If local clone is out of sync with workspace changes, sync first before recording runtime evidence.

## Current Blocker Snapshot (Local Host)

- SOVRN_BASE_URL, SOVRN_TOKEN, and SOVRN_PROJECT_ID are not set in the active shell.
- Local API target is not running on localhost:8000.
- Docker is not available on host, so docker-compose local stack startup is unavailable.
- Local Postgres is not reachable on localhost:5432.
- Result: staging benchmark execution is pending valid staging credentials and reachable staging API.
