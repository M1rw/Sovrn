# SOVRN Load Test Baseline (Phase 0)

This folder contains baseline k6 scenarios for Phase 0 observability and capacity validation.

## Prerequisites

- k6 installed locally: [k6 installation guide](https://k6.io/docs/get-started/installation/)
- API stack running and reachable

## Environment Variables

- SOVRN_BASE_URL (optional): API URL, default `http://localhost:8000`
- K6_VUS (optional): virtual users
- K6_DURATION (optional): test duration, e.g. 2m

Generation flow only:

- SOVRN_TOKEN (required): bearer token for authenticated API calls
- SOVRN_LOCALE (optional): default en
- K6_JOB_MAX_POLLS (optional): default 20
- K6_JOB_POLL_INTERVAL_MS (optional): default 1500

Preview latency benchmark only:

- SOVRN_PROJECT_ID (required): existing project id with at least one completed generation
- SOVRN_GENERATION_ID (optional): explicit generation id; defaults to latest project generation
- SOVRN_ENTRYPOINT (optional): preview entrypoint path, default `index.html`
- SOVRN_PREVIEW_BENCH_ITERATIONS (optional): measured iterations, default 30
- SOVRN_PREVIEW_BENCH_WARMUP (optional): warmup iterations, default 3
- SOVRN_PREVIEW_TARGET_P95_MS (optional): gate threshold, default 1500

## Scenarios

- k6_chat.js
  - Stresses /api/v1/ai/chat interactive path
  - Validates response headers and p95 latency threshold

- k6_generation_flow.js
  - Creates project, enqueues generation, polls /api/v1/jobs/:jobId
  - Measures queue and worker path behavior under concurrent generation traffic

- preview_latency_benchmark.py
  - Measures preview bootstrap + first preview.updated stream event latency
  - Emits p50/p95/p99 and writes JSON report for Phase 2 p95 <= 1.5s gate

## Run Commands

Chat baseline:

```bash
k6 run eval/load/k6_chat.js
```

Generation baseline:

```bash
SOVRN_TOKEN=<token> k6 run eval/load/k6_generation_flow.js
```

Preview latency benchmark:

```bash
SOVRN_BASE_URL=http://localhost:8000 \
SOVRN_TOKEN=<token> \
SOVRN_PROJECT_ID=<project_id> \
python eval/load/preview_latency_benchmark.py
```

Prerequisite check (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File eval/load/check-preview-latency-prereqs.ps1
```

This prints presence of required `SOVRN_*` environment variables and probes `/health` reachability before running the benchmark.

Canary metric check (PowerShell):

```powershell
powershell -ExecutionPolicy Bypass -File eval/load/check-preview-canary-metrics.ps1 -WebBaseUrl 'https://<staging-web-host>'
```

This validates preview canary metrics from the web telemetry snapshot endpoint (`/api/v1/telemetry/client-metrics`) including:

- `builder_preview_render_ms` p95 threshold
- `builder_preview_stream_update_count` minimum activity
- `builder_preview_stream_reconnect_count` maximum threshold
- `builder_preview_runtime_restart_count` maximum threshold

PowerShell example:

```powershell
$env:SOVRN_BASE_URL='http://localhost:8000'
$env:SOVRN_TOKEN='<token>'
$env:SOVRN_PROJECT_ID='<project-id>'
py -3.11 eval/load/preview_latency_benchmark.py
```

PowerShell one-command runner:

```powershell
powershell -ExecutionPolicy Bypass -File eval/load/run-preview-latency.ps1 \
  -BaseUrl 'https://<staging-api-host>' \
  -Token '<staging-bearer-token>' \
  -ProjectId '<project-id-with-generation>'
```

The runner validates required inputs, executes the Python benchmark, and prints the parsed summary from the JSON report.

PowerShell + Docker fallback (no host k6 install required):

```powershell
powershell -ExecutionPolicy Bypass -File eval/load/run-k6-docker.ps1 -Scenario chat
powershell -ExecutionPolicy Bypass -File eval/load/run-k6-docker.ps1 -Scenario generation -Token <token>
```

## Suggested First Pass

- Chat: K6_VUS=10, K6_DURATION=2m
- Generation: K6_VUS=2, K6_DURATION=5m

## Output Correlation

Requests include:

- X-Correlation-ID
- X-Client-Session-ID

Use these IDs in API and inference logs to trace saturation and failure points.

## Phase 2 Gate Output

The benchmark writes a machine-readable report by default to:

- `eval/load/preview_latency_report.json`

Gate expectation:

- `summary.p95_total_ms <= 1500`
- zero failed iterations
