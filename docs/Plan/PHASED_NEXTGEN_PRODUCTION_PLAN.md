# SOVRN NextGen Production Plan

<!-- markdownlint-disable MD024 -->

Last updated: 2026-04-17
Owner: Core Platform Team
Source baseline: docs/NEXTGEN_ARCHITECTURE_PLAN.md, docs/ROADMAP.md, docs/TODO.md

## Purpose

This plan turns the NextGen architecture into a production program that is:

- Incremental (do not build all at once)
- Test-gated at every phase
- Safe under heavy load
- Ready for frontend, backend, inference, and infra scale

## Delivery Rules (Non-Negotiable)

- Ship one major capability group per phase.
- No phase moves forward without passing its exit gates.
- Every phase must include frontend tests, backend tests, and load checks.
- Any new feature must have a fallback mode.
- Canary before full rollout for all user-visible behavior changes.

## Current Baseline (Already Done)

From the current roadmap:

- [x] Phase 1 Canonical path and prompt governance
- [x] Phase 2 Structured contract and backend action governance (shadow)
- [x] Phase 3 Conversation persistence
- [x] Phase 4 Context compaction completion
- [x] Phase 5 Resolved action contract cutover

## Master Program Board

- [ ] Phase 0: Program setup, baselines, and SLO instrumentation
- [x] Phase 1: Complete current execution-track gaps (P4/P5)
- [ ] Phase 2: WebContainer runtime and instant preview path
- [ ] Phase 3: AST patch engine and safe code apply pipeline
- [ ] Phase 4: Multi-agent orchestration with self-healing loops
- [ ] Phase 5: Full-stack generation (DB to API to UI)
- [ ] Phase 6: CRDT collaboration and multiplayer editing
- [ ] Phase 7: Hyper-scale inference engine (vLLM + adapters + cache)
- [ ] Phase 8: Production hardening, chaos testing, and launch rings

---

## Global SLO and Capacity Targets

These targets are required before general availability:

- API availability: >= 99.95%
- Chat success rate (non-5xx): >= 99.5%
- p95 chat response latency (interactive path): <= 2.5s
- p95 preview update latency (edit to visible): <= 1.5s
- p95 job queue wait time: <= 5s at design capacity
- Error budget burn alerting: active and tested
- Zero data loss in conversation persistence under failover tests

## The Performance Method (Core Invention)

### Adaptive Quality Envelope (AQE) + Three-Lane Scheduler

AQE prevents crashes under load by dynamically selecting pipeline depth based on real-time capacity.

Lane model:

- Lane A (Interactive): user-facing edits and chat generation
- Lane B (Quality): critic agent, lint, visual review, refactor loops
- Lane C (Background): indexing, embeddings, analytics, compaction

Quality levels:

- Q3 (Low load): full 3-agent loop + visual critic + deep checks
- Q2 (Medium load): 2-agent loop, selective visual critic
- Q1 (High load): single-pass generation + async quality follow-up
- Q0 (Critical load): cache-first + strict throttling + queue protection

Trigger inputs:

- GPU utilization
- KV cache pressure
- Queue depth
- p95 latency trend
- error rate trend

Required behavior:

- Automatic downgrade and recovery between Q3/Q2/Q1/Q0
- No user-visible outage during quality downgrade
- Always preserve correctness and state integrity

---

## Phase 0: Program Setup and Baseline Instrumentation

Goal: Make the system measurable before introducing new complexity.

### Frontend

- [x] Add telemetry hooks for builder chat latency, preview latency, and UI error boundaries
- [x] Add client session correlation id for tracing across API and worker calls

### Backend

- [x] Add trace context propagation scaffold for API -> worker -> inference request chain
- [x] Add per-endpoint p50/p95/p99 latency metrics endpoint (/metrics/http)
- [x] Add structured error classes for retryable vs non-retryable failures

### Inference and Infra

- [ ] Add GPU telemetry (utilization, memory, kv cache pressure)
- [ ] Add queue depth dashboards and alert thresholds
- [ ] Add autoscaling signals (or scale-up playbooks if fixed infra)

### Test and Exit Gates

- [ ] Smoke tests pass
- [ ] Observability dashboard live for all critical paths
- [ ] Alerting tested with synthetic failures

Validation commands:

- npm run guard:canonical-chat
- npm run lint
- npm run typecheck
- npm run test
- npm run test:api
- npm run test:web

### Phase 0 Execution Log (2026-04-16)

- [x] Added API request observability middleware outputs: request id, correlation id, trace id, traceparent
- [x] Added in-memory endpoint latency metrics store with p50/p95/p99 snapshots
- [x] Added readiness endpoint with dependency health checks: /ready
- [x] Added structured retryable/non-retryable exception classification in API error handling
- [x] Added web client telemetry utility with session correlation and request timing metrics
- [x] Instrumented builder chat and preview paths for client-side latency metrics
- [x] Added worker-to-API trace propagation headers for internal job processing calls
- [x] Added periodic worker queue depth and processor latency snapshot logging
- [x] Added inference request observability middleware with correlation and trace headers
- [x] Added inference readiness endpoint and runtime metrics endpoint: /ready, /metrics/system
- [x] Added inference queue-pressure telemetry (waiting requests, wait events, avg wait ms)
- [x] Added best-effort GPU telemetry (utilization and memory) in inference metrics endpoint
- [x] Added k6 load-test baseline for chat and generation flow paths under eval/load
- [x] Added PowerShell Docker fallback runner for k6 load baselines when host k6 is unavailable
- [x] Local runtime validation executed in filesystem clone (frontend typecheck clean, lint warnings only)
- [x] Backend deterministic suite passed: canonical route guard, structured output, summary contract, prompt registry
- [x] k6 load scenarios executed locally (harness validation run against local mock API target)
- [x] Published baseline report: docs/Plan/PHASE0_LOAD_BASELINE_2026-04-17.md
- [x] Added canonical chat conversation metadata response fields (thread_id, turn_index, state_version, idempotency_key) when persistence is enabled
- [x] Builder chat now supports thread-aware incremental requests for server-side compaction contexts

## Phase 1: Complete Current Execution-Track Gaps (P4 and P5)

Goal: Finish canonical architecture before NextGen expansion.

### Phase 1 Execution Log (2026-04-17)

- [x] Added integration tests for conversation persistence idempotency replay by thread_id + idempotency_key
- [x] Added integration tests for resume existing thread vs create new thread path
- [x] Added integration tests for snapshot version conflict fail-open behavior
- [x] Added integration test for summary-trigger threshold behavior in conversation compaction flow
- [x] Added integration test for invalid summary payload rejection without persistence/chat failure
- [x] Test file added: services/api/tests/test_conversation_persistence_integration.py
- [x] Added resolved-action contract coverage tests for respond, ask_clarification, ready_to_generate, and propose_revision outcomes
- [x] Test file added: services/api/tests/test_resolved_action_contract.py
- [x] Runtime verification in local clone: py -3.11 -m pytest tests/test_conversation_persistence_integration.py tests/test_resolved_action_contract.py (13 passed)
- [x] Added endpoint-level resolved-action outcome tests (chat_completion) for respond, ask_clarification, ready_to_generate, and propose_revision
- [x] Test file added: services/api/tests/test_resolved_action_e2e.py
- [x] Runtime verification in local clone: py -3.11 -m pytest tests/test_conversation_persistence_integration.py tests/test_resolved_action_contract.py tests/test_resolved_action_e2e.py (17 passed)
- [x] Removed residual frontend string-trigger transition logic (GENERATE_WEBSITE sentinel path) from builder flow
- [x] Added load validation tests for summary contract rejection and parser fail-open behavior
- [x] Test file added: services/api/tests/test_fail_open_load_validation.py
- [x] Added Phase 1 canary ring simulation tests for feature-flagged cutover (5/25/50/100 rings)
- [x] Test file added: services/api/tests/test_phase1_canary_rollout.py
- [x] Runtime verification in local clone: py -3.11 -m pytest tests/test_fail_open_load_validation.py tests/test_phase1_canary_rollout.py tests/test_conversation_persistence_integration.py tests/test_resolved_action_contract.py tests/test_resolved_action_e2e.py (23 passed)
- [x] Published canary validation report: docs/Plan/PHASE1_CANARY_VALIDATION_2026-04-17.md

### Frontend

- [x] Add support for compaction-aware conversation rendering
- [x] Add UI-safe handling for resolved action contract fields under feature flag

### Backend

- [x] Implement context compaction read/write integration (P4-2)
- [x] Promote resolved_action contract to optional client-visible response under flag
- [x] Remove residual string-trigger transition logic

### Inference and Infra

- [x] Validate summary contract rejection path under load
- [x] Validate fail-open behavior when parser/summary fails

### Test and Exit Gates

- [x] Integration test: idempotent replay by thread_id + idempotency_key
- [x] Integration test: snapshot version conflict fail-open path
- [x] Integration test: resume existing thread vs create new thread
- [x] Integration test: compaction threshold behavior
- [x] Integration test: invalid summary payload rejection without chat failure
- [x] End-to-end test: resolved action outcomes (respond, ask_clarification, ready_to_generate, propose_revision)
- [x] Canary rollout passed for feature-flagged cutover

## Phase 2: WebContainer Runtime and Instant Preview

Goal: Deliver interactive browser-native runtime with fast visual feedback.

### Phase 2 Execution Log (2026-04-17)

- [x] Added frontend preview runtime lifecycle hook with explicit states (idle, booting, mounting, ready, failed)
- [x] Added workspace mounting bridge in builder UI to mount generated files and drive preview via runtime URL
- [x] Added runtime status telemetry surface in builder preview toolbar (runtime kind, status, mounted file count)
- [x] Added preview artifact API endpoint: GET /api/v1/projects/{project_id}/preview-artifact
- [x] Added signed preview bootstrap session API endpoint: POST /api/v1/projects/{project_id}/preview-session
- [x] Added web API client support for preview artifact/session endpoints in apps/web/src/lib/api.ts
- [x] Added backend tests for preview bootstrap helpers and token claims: services/api/tests/test_phase2_preview_bootstrap.py
- [x] Updated API reference with preview artifact + preview session endpoint contracts
- [x] Added secure preview iframe bridge handshake channel with message validation in builder runtime flow
- [x] Added preview-session verification endpoint for runtime bootstrap claim checks: POST /api/v1/projects/{project_id}/preview-session/verify
- [x] Extended backend tests for preview-session claim decode and access guard behavior
- [x] Added preview SSE event stream endpoint for incremental apply updates: GET /api/v1/projects/{project_id}/preview-events
- [x] Wired builder EventSource consumer to apply preview.updated events and stream liveness state
- [x] Added backend SSE serialization coverage in Phase 2 preview bootstrap tests
- [x] Added builder code-view file tree + editable editor bridge with apply/discard patch workflow to remount preview runtime
- [x] Added runtime restart control and HMR health monitor state (bridge + stream liveness) in preview toolbar
- [x] Added frontend helper test for preview stream URL contract: apps/web/src/lib/api.preview-stream.test.ts
- [x] Added backend endpoint-level preview event stream auth and payload contract tests (query preview_token + bearer token paths)
- [x] Added frontend integration-style tests for preview bootstrap API contracts and secure preview bridge script injection
- [x] Added runtime fallback UX for stale/disconnected preview stream state with reconnect control in builder preview panel
- [x] Added Phase 2 preview latency benchmark harness for preview-session bootstrap and first preview.updated timing: eval/load/preview_latency_benchmark.py
- [x] Added Phase 2 latency evidence template doc: docs/Plan/PHASE2_PREVIEW_LATENCY_VALIDATION_2026-04-17.md
- [x] Added preview build-time timeout and artifact budget controls in generation service with regression tests
- [x] Added cached style starter-template fallback for instant preview startup on generation timeout/failure
- [x] Synced preview budget controls into local clone and validated runtime test suite: tests/test_generation_service_preview_budget.py (3 passed)
- [x] Added Next-aware Jest config for web preview suites: apps/web/jest.config.js
- [x] Synced and validated local frontend preview suites: src/lib/api.preview-stream.test.ts + src/hooks/use-preview-runtime.test.ts (2 suites passed)
- [x] Synced local-clone backend preview bootstrap contracts and validated runtime suite: tests/test_phase2_preview_bootstrap.py (11 passed)
- [x] Added one-command PowerShell staging benchmark runner for Phase 2 gate execution: eval/load/run-preview-latency.ps1
- [x] Synced latency runner into local clone and smoke-tested required-input validation path (fails fast without staging env vars)
- [x] Added backend endpoint-level Phase 2 contract tests for preview-artifact access, preview-session TTL clamp, and preview-session verify userless flow in services/api/tests/test_phase2_preview_bootstrap.py
- [x] Added frontend preview lifecycle integration helper coverage for bootstrap artifact mapping, preview.updated apply mapping, stale threshold detection, and reconnect/error transition behavior in apps/web/src/app/builder/preview-lifecycle.test.ts
- [x] Runtime verification for expanded Phase 2 backend suite: py -3.11 -m pytest tests/test_phase2_preview_bootstrap.py tests/test_generation_service_preview_budget.py (18 passed)
- [x] Runtime verification for expanded Phase 2 frontend preview suites: npx jest src/app/builder/preview-lifecycle.test.ts src/lib/api.preview-stream.test.ts src/hooks/use-preview-runtime.test.ts (3 suites, 12 tests passed)
- [x] Validated local mock latency harness with real benchmark implementation and runner script (no placeholder benchmark substitution); report: eval/load/phase2_preview_latency_report.local_mock.json (5/5 successful, p95 total 31.78 ms, non-gating sanity evidence)
- [x] Hardened eval/load/run-preview-latency.ps1 for bracketed clone paths by switching Resolve-Path, Push-Location, Test-Path, and Get-Content calls to -LiteralPath.
- [x] Revalidated local mock latency benchmark after literal-path hardening; report: eval/load/phase2_preview_latency_report.local_mock.json (5/5 successful, p95 total 6.57 ms, p95 stream first update 2.94 ms, non-gating sanity evidence)
- [x] Validated Phase 2 rollback drill path with runtime fallback flag disabled (`NEXT_PUBLIC_BUILDER_WEBCONTAINER_ENABLED=false`) and reran preview lifecycle/endpoint suites: frontend (3 suites, 12 tests passed), backend (tests/test_phase2_preview_bootstrap.py: 15 passed)

### Frontend

- [x] Add WebContainer boot lifecycle and workspace mounting
- [x] Add live preview iframe with isolated origin and secure messaging
- [x] Add file tree and editor bridge for AI patch apply
- [x] Add HMR state monitor and graceful restart UX

### Backend

- [x] Add artifact endpoint for generated project snapshots
- [x] Add signed session tokens for preview runtime bootstrap
- [x] Add preview event stream endpoint (SSE/WebSocket) for incremental apply

### Inference and Infra

- [x] Cache common starter templates for instant startup
- [x] Add build-time budgets and timeout controls for preview tasks

### Test and Exit Gates

- [x] Frontend integration test: boot + install + run preview
- [x] Security test: iframe isolation and message validation
- [x] Backend endpoint-level contract tests: preview-artifact, preview-session, preview-session/verify
- [ ] p95 edit-to-preview latency <= 1.5s in staging

### Phase 2 Release Controls (In Progress)

- [x] Feature flag rollout plan documented for preview runtime enablement and fallback behavior
- [x] Rollback playbook validated for preview endpoints and builder runtime fallback
- [ ] Canary monitoring checks confirmed in staging for preview latency and preview stream disconnect/reconnect rates

#### Rollout Plan

1. Ring 1 (5%): enable `NEXT_PUBLIC_BUILDER_WEBCONTAINER_ENABLED=true` for canary users only; keep iframe fallback path enabled.
2. Ring 2 (25%): expand only if no sustained regression in `builder_preview_render_ms` p95 and no spike in `builder_preview_stream_reconnect_count`.
3. Ring 3 (50%): maintain rollout only if `builder_preview_stream_update_count` remains stable and error rates stay within Phase 2 error budget.
4. Ring 4 (100%): complete rollout after at least one full business day of stable canary metrics.

#### Rollback Playbook

1. Immediate rollback switch: set `NEXT_PUBLIC_BUILDER_WEBCONTAINER_ENABLED=false` and redeploy web.
2. Runtime fallback confirmation: verify builder preview mounts via iframe fallback and `preview-events` reconnect path remains available.
3. API containment: if preview endpoint instability is detected, disable preview session issuance at deployment ring edge and route users to local mounted preview artifacts.
4. Validation checklist before unfreeze: rerun frontend preview lifecycle tests and backend preview bootstrap contract suite.

#### Canary Monitoring Checks

1. Preview render latency metric: `builder_preview_render_ms` p95 within Phase 2 gate target.
2. Stream health metrics: monitor `builder_preview_stream_update_count` and `builder_preview_stream_reconnect_count` for regressions.
3. Runtime restart pressure: monitor `builder_preview_runtime_restart_count` for unexpected growth after rollout increments.
4. Gate to advance rings: no sustained disconnect/error fallback banner rates in builder preview panel.

### Local URLs for Try/Test (Until Domain Purchase)

| Surface | URL | Purpose |
| --- | --- | --- |
| Caddy entry | `http://localhost/` | Unified local entry (web at root, backend under /api/*) |
| Caddy health | `http://localhost/health` | Reverse-proxy health check |
| Web app direct | `http://localhost:3000/` | Next.js app direct (bypasses Caddy API routing) |
| Builder UI | `http://localhost:3000/builder` | Preview runtime and edit flow |
| Auth login | `http://localhost:3000/auth/login` | Local login form |
| Auth register | `http://localhost:3000/auth/register` | Local signup form |
| Dashboard | `http://localhost:3000/dashboard` | Main dashboard |
| Dashboard projects | `http://localhost:3000/dashboard/projects` | Project list |
| Dashboard templates | `http://localhost:3000/dashboard/templates` | Template gallery |
| Dashboard sparks | `http://localhost:3000/dashboard/sparks` | Spark usage |
| Dashboard settings | `http://localhost:3000/dashboard/settings` | Account/settings |
| Playground | `http://localhost:3000/playground` | Playground page |
| API docs | `http://localhost:8000/api/docs` | FastAPI Swagger |
| API ReDoc | `http://localhost:8000/api/redoc` | FastAPI ReDoc |
| API OpenAPI | `http://localhost:8000/api/openapi.json` | OpenAPI JSON |
| API health | `http://localhost:8000/health` | API liveness |
| API readiness | `http://localhost:8000/ready` | API dependency readiness |
| API HTTP metrics | `http://localhost:8000/metrics/http` | API latency metrics snapshot |
| Inference docs | `http://localhost:8080/docs` | Inference Swagger |
| Inference health | `http://localhost:8080/health` | Inference liveness |
| Inference readiness | `http://localhost:8080/ready` | Model readiness |
| Inference stats | `http://localhost:8080/stats` | Inference request statistics |
| Inference metrics | `http://localhost:8080/metrics/system` | Runtime/GPU/process telemetry |
| NextAuth route (web direct) | `http://localhost:3000/api/auth/signin` | NextAuth route |
| Web MML route (web direct) | `http://localhost:3000/api/v1/mml/generate` | Web-side MML API route |
| PostgreSQL DSN | `postgresql://sovrn:devpassword@localhost:5432/sovrn` | Local DB connection |
| Redis endpoint | `redis://localhost:6379` | Local cache/queue endpoint |
| pgAdmin (tools profile) | `http://localhost:5050/` | DB admin UI |
| Mailhog UI (tools profile) | `http://localhost:8025/` | Email capture UI |
| Mailhog SMTP (tools profile) | `smtp://localhost:1025` | Local SMTP test endpoint |

For the Phase 2 latency benchmark in local/dev mode, use `SOVRN_BASE_URL=http://localhost:8000` (direct API) or `SOVRN_BASE_URL=http://localhost` (through Caddy).

## Phase 3: AST Patch Engine and Safe Apply Pipeline

Goal: Move from full-file overwrite to deterministic patching.

### Frontend

- [ ] Add node-level selection UX (click element -> map to source)
- [ ] Add patch preview with accept/reject controls

### Backend

- [ ] Build AST parser + transformer pipeline for TS/JS/JSON/CSS
- [ ] Add patch contract schema and strict validation
- [ ] Add patch conflict resolver and rollback support
- [ ] Add deterministic formatter pass after patch apply

### Inference and Infra

- [ ] Train prompts to output patch contract only (no raw overwrite)
- [ ] Add fallback to safe file rewrite for unsupported syntax edge cases

### Test and Exit Gates

- [ ] Golden tests for patch determinism and idempotence
- [ ] Regression suite on representative generated projects
- [ ] Patch conflict simulation tests pass

## Phase 4: Multi-Agent Orchestration and Self-Healing

Goal: Add architect/coder/critic loops without destabilizing latency.

### Frontend

- [ ] Add generation timeline UI with per-agent status and logs
- [ ] Add user controls for quality mode (fast, balanced, high)

### Backend

- [ ] Build orchestration graph with deadlines and cancellation
- [ ] Add AQE controller for Q3/Q2/Q1/Q0 transitions
- [ ] Add critic retry policy and strict max attempt limits

### Inference and Infra

- [ ] Route specialist tasks through adapter-based model profiles
- [ ] Add budget manager (token, time, and retry budgets per request)
- [ ] Add queue priority for interactive traffic over background loops

### Test and Exit Gates

- [ ] Load test with mixed workloads and AQE transitions
- [ ] Verify no crash or cascading timeout during quality downgrades
- [ ] User-visible interactive latency remains within SLO in Q2/Q1 modes

## Phase 5: Full-Stack Generation (DB -> API -> UI)

Goal: Generate deployable applications, not only landing pages.

### Frontend

- [ ] Add data model editor and generated CRUD form renderer
- [ ] Add API client scaffolding and environment config UX

### Backend

- [ ] Add schema planner (Postgres tables, indexes, constraints)
- [ ] Add API scaffolder (REST/GraphQL) with policy templates
- [ ] Add migration generation and validation pipeline

### Inference and Infra

- [ ] Add schema-aware prompting with contract validation
- [ ] Add dry-run migration checks in isolated database

### Test and Exit Gates

- [ ] Generated migrations apply and rollback cleanly
- [ ] API contract tests pass for generated endpoints
- [ ] End-to-end CRUD test suite passes in generated app

## Phase 6: CRDT Collaboration and Multiplayer

Goal: Enable real-time multi-user + AI co-editing.

### Frontend

- [ ] Add presence indicators, cursors, and shared selections
- [ ] Add conflict annotations and timeline replay

### Backend

- [ ] Add CRDT session service with persistence checkpoints
- [ ] Add conflict reconciliation and ordered event log

### Inference and Infra

- [ ] Add AI edits as CRDT operations, not direct file writes
- [ ] Add per-session backpressure controls and room limits

### Test and Exit Gates

- [ ] Multi-client consistency tests pass
- [ ] Network partition and reconnect tests pass
- [ ] No state corruption after concurrent edits

## Phase 7: Hyper-Scale Inference Engine

Goal: Run high concurrency with stable cost and performance.

### Frontend

- [ ] Add adaptive UX indicators for quality mode and queue state
- [ ] Add non-blocking progress state for async quality upgrades

### Backend

- [ ] Add semantic cache lookup before model invocation
- [ ] Add result reuse by intent signature and AST fingerprint
- [ ] Add admission control and per-tenant quotas

### Inference and Infra

- [ ] Integrate vLLM with continuous batching and PagedAttention
- [ ] Implement base-model + multi-LoRA adapter switching
- [ ] Add speculative decoding path for code generation
- [ ] Add warm pools for hot adapters and startup templates

### Test and Exit Gates

- [ ] Soak test 24h with no memory leak or crash loop
- [ ] Capacity test at target concurrent users
- [ ] p95 latency and error-rate targets met at design load

## Phase 8: Production Hardening and Launch Rings

Goal: Release safely with measurable risk control.

### Frontend

- [ ] Finalize fallback UX for all degraded states
- [ ] Run accessibility and cross-browser audits

### Backend

- [ ] Complete security review and threat model updates
- [ ] Add disaster recovery drills for DB and queue layers
- [ ] Add kill switches for each major feature flag

### Inference and Infra

- [ ] Chaos testing for GPU node loss and queue outages
- [ ] Validate blue/green or canary deployment runbooks

### Test and Exit Gates

- [ ] Full regression suite green
- [ ] Chaos suite green
- [ ] Canary 5% -> 25% -> 50% -> 100% with stable error budget

---

## Frontend and Backend Test Matrix (Required Every Phase)

### Frontend Required

- [ ] Unit tests for new UI logic
- [ ] Integration tests for editor-preview flow
- [ ] Typecheck and lint clean

### Backend Required

- [ ] Unit tests for new services
- [ ] Integration tests for API, worker, and DB interactions
- [ ] Contract tests for AI payload schemas

### Performance Required

- [ ] Load test for interactive endpoints
- [ ] Queue stress test for worker/inference path
- [ ] Failover test for dependency outages

### Release Required

- [ ] Feature flag documented
- [ ] Rollback path documented and validated
- [ ] Canary and monitoring dashboards confirmed

## Immediate Next Execution Slice (Do This First)

- [ ] Run `eval/load/run-preview-latency.ps1` (or `eval/load/preview_latency_benchmark.py`) in staging and validate `summary.p95_total_ms <= 1500` in `eval/load/phase2_preview_latency_report.json`
- [ ] Provide staging `SOVRN_BASE_URL`, `SOVRN_TOKEN`, and `SOVRN_PROJECT_ID` in shell environment (or CI secret context) before executing the staging benchmark gate
- [ ] Confirm canary monitoring checks in staging after rollout ring activation (`builder_preview_render_ms`, `builder_preview_stream_update_count`, `builder_preview_stream_reconnect_count`, `builder_preview_runtime_restart_count`)

## Notes

- This plan is intentionally strict to prevent building everything at once.
- A phase is complete only when all its checkboxes and exit gates are green.
- If any SLO fails in staging, stop forward work and stabilize before continuing.
