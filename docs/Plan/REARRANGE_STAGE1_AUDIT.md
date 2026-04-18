# Rearrange Stage 1 Audit

Generated at: 2026-04-18T13:16:00+00:00
Repository root: E:\Synthos\[Sovrn]

## Coverage

- Files scanned: 239
- Folders scanned: 60
- Files with findings: 27
- Total findings: 74

## Pattern Summary

| Pattern | Hits | Files |
| --- | ---: | ---: |
| Phase-Prefixed Naming | 42 | 9 |
| MVP/Prototype Language | 10 | 9 |
| Placeholder Secret Markers | 2 | 2 |
| TODO/FIXME Markers | 20 | 13 |
| Supabase Typo Markers | 0 | 0 |

## Top Files By Finding Count

- services/api/app/core/config.py: 22
- docs/Plan/PHASED_NEXTGEN_PRODUCTION_PLAN.md: 10
- docs/Plan/PHASE2_PREVIEW_LATENCY_VALIDATION_2026-04-17.md: 9
- docs/TODO.md: 5
- scripts/rearrange_audit.py: 3
- docs/GAP_ANALYSIS.md: 2
- eval/benchmark.py: 2
- eval/load/preview_latency_benchmark.py: 2
- docs/API.md: 1
- docs/BUILD_DOCUMENTATION_INDEX.md: 1
- docs/COMPETITIVE_ANALYSIS.md: 1
- docs/DOCUMENTATION_INDEX.md: 1
- docs/IMPLEMENTATION_SUMMARY.md: 1
- docs/INDEX.md: 1
- docs/legacy/planning/SOVRN_ROADMAP.md: 1
- docs/legacy/README.md: 1
- docs/legacy/status/FINAL_REPORT.md: 1
- docs/legacy/status/PHASE_1_COMPLETE.md: 1
- docs/legacy/status/README.md: 1
- docs/QUICK_REFERENCE.md: 1
- docs/README.md: 1
- docs/README_PIPELINE.md: 1
- eval/load/phase2_preview_latency_report.local_mock.json: 1
- eval/load/README.md: 1
- eval/load/run-preview-latency.ps1: 1
- README.md: 1
- services/api/app/api/v1/endpoints/internal.py: 1

## Findings (Sampled)

### services/api/app/core/config.py
- [Phase-Prefixed Naming] L170: validation_alias=AliasChoices("ORCHESTRATION_RUNTIME_ENABLED", "PHASE4_ORCHESTRATION_ENABLED"),
- [Phase-Prefixed Naming] L174: validation_alias=AliasChoices("ORCHESTRATION_AQE_ENABLED", "PHASE4_AQE_ENABLED"),
- [Phase-Prefixed Naming] L182: "PHASE4_AQE_INFER_STATS_TIMEOUT_SECONDS",
- [Phase-Prefixed Naming] L190: validation_alias=AliasChoices("ORCHESTRATION_REQUEST_TIME_BUDGET_SECONDS", "PHASE4_REQUEST_TIME_BUDGET_SECONDS"),
- [Phase-Prefixed Naming] L196: validation_alias=AliasChoices("ORCHESTRATION_STAGE_TIMEOUT_SECONDS", "PHASE4_STAGE_TIMEOUT_SECONDS"),
- [Phase-Prefixed Naming] L203: validation_alias=AliasChoices("ORCHESTRATION_CRITIC_MAX_ATTEMPTS", "PHASE4_CRITIC_MAX_ATTEMPTS"),
- [Phase-Prefixed Naming] L207: validation_alias=AliasChoices("ORCHESTRATION_CRITIC_STRICT_FAIL", "PHASE4_CRITIC_STRICT_FAIL"),
- [Phase-Prefixed Naming] L214: validation_alias=AliasChoices("ORCHESTRATION_LANE_PRIORITY_INTERACTIVE", "PHASE4_LANE_PRIORITY_INTERACTIVE"),
- [Phase-Prefixed Naming] L220: validation_alias=AliasChoices("ORCHESTRATION_LANE_PRIORITY_QUALITY", "PHASE4_LANE_PRIORITY_QUALITY"),
- [Phase-Prefixed Naming] L226: validation_alias=AliasChoices("ORCHESTRATION_LANE_PRIORITY_BACKGROUND", "PHASE4_LANE_PRIORITY_BACKGROUND"),

### docs/Plan/PHASED_NEXTGEN_PRODUCTION_PLAN.md
- [TODO/FIXME Markers] L7: Source baseline: docs/NEXTGEN_ARCHITECTURE_PLAN.md, docs/ROADMAP.md, docs/TODO.md
- [Phase-Prefixed Naming] L105: - [x] Renamed generation orchestration metadata payload from `phase4` to `orchestration_profile` while preserving legacy fallback reads
- [MVP/Prototype Language] L114: - [ ] Replace remaining MVP/prototype language in active docs and implementation comments
- [TODO/FIXME Markers] L115: - [ ] Close TODO/FIXME markers in runtime-critical files first (API, worker, orchestration, preview pipeline)
- [Phase-Prefixed Naming] L174: - [x] Published baseline report: docs/Plan/PHASE0_LOAD_BASELINE_2026-04-17.md
- [Phase-Prefixed Naming] L202: - [x] Published canary validation report: docs/Plan/PHASE1_CANARY_VALIDATION_2026-04-17.md
- [Phase-Prefixed Naming] L257: - [x] Added Phase 2 latency evidence template doc: docs/Plan/PHASE2_PREVIEW_LATENCY_VALIDATION_2026-04-17.md
- [Phase-Prefixed Naming] L270: - [x] Validated local mock latency harness with real benchmark implementation and runner script (no placeholder benchmark substitution); report: eval/load/phase2_preview_latency...
- [Phase-Prefixed Naming] L272: - [x] Revalidated local mock latency benchmark after literal-path hardening; report: eval/load/phase2_preview_latency_report.local_mock.json (5/5 successful, p95 total 6.57 ms, ...
- [Phase-Prefixed Naming] L612: - [ ] Run `eval/load/run-preview-latency.ps1` (or `eval/load/preview_latency_benchmark.py`) in staging and validate `summary.p95_total_ms <= 1500` in `eval/load/phase2_preview_l...

### docs/Plan/PHASE2_PREVIEW_LATENCY_VALIDATION_2026-04-17.md
- [Phase-Prefixed Naming] L66: - eval/load/phase2_preview_latency_report.json
- [Phase-Prefixed Naming] L76: - Command: `powershell -ExecutionPolicy Bypass -File eval/load/run-preview-latency.ps1 -BaseUrl http://127.0.0.1:8000 -Token mock-token -ProjectId mock-project -Iterations 5 -Wa...
- [Phase-Prefixed Naming] L77: - Report: `eval/load/phase2_preview_latency_report.local_mock.json`
- [TODO/FIXME Markers] L91: - successful iterations: TODO
- [TODO/FIXME Markers] L92: - p50 total latency: TODO ms
- [TODO/FIXME Markers] L93: - p95 total latency: TODO ms
- [TODO/FIXME Markers] L94: - p99 total latency: TODO ms
- [TODO/FIXME Markers] L95: - p95 stream first update latency: TODO ms
- [TODO/FIXME Markers] L96: - gate (p95 <= 1500ms and zero failed iterations): TODO PASS/FAIL

### docs/TODO.md
- [TODO/FIXME Markers] L1: # SOVRN Engineering TODO
- [Phase-Prefixed Naming] L13: 5. Canary ring simulation and load fail-open validations completed (see docs/Plan/PHASE1_CANARY_VALIDATION_2026-04-17.md).
- [Phase-Prefixed Naming] L18: 2. Run staging preview latency benchmark (preferred: `eval/load/run-preview-latency.ps1`; fallback: `eval/load/preview_latency_benchmark.py`) and verify p95 total <= 1.5s in `ev...
- [Phase-Prefixed Naming] L19: 3. Capture benchmark evidence in `docs/Plan/PHASE2_PREVIEW_LATENCY_VALIDATION_2026-04-17.md` after the staging run completes.
- [Phase-Prefixed Naming] L27: 4. Revalidated localhost mock latency harness with the hardened runner (`eval/load/phase2_preview_latency_report.local_mock.json`: 5/5 successful, p95 total 6.57 ms, p95 stream ...

### scripts/rearrange_audit.py
- [MVP/Prototype Language] L71: title="MVP/Prototype Language",
- [Placeholder Secret Markers] L77: regex=re.compile(r"change_me|your-password|your_password|replace_me", re.IGNORECASE),
- [TODO/FIXME Markers] L81: title="TODO/FIXME Markers",

### docs/GAP_ANALYSIS.md
- [MVP/Prototype Language] L83: **Impact**: 🟡 Medium - Works for MVP but not scalable
- [MVP/Prototype Language] L241: **Gap Score**: 2/10 (works for MVP only)

### eval/benchmark.py
- [TODO/FIXME Markers] L311: result.correct_date_format or True,  # TODO: implement
- [TODO/FIXME Markers] L312: result.correct_payment_methods or True,  # TODO: implement

### eval/load/preview_latency_benchmark.py
- [Phase-Prefixed Naming] L71: default=os.getenv("SOVRN_PREVIEW_BENCH_OUTPUT", "eval/load/phase2_preview_latency_report.json"),
- [Phase-Prefixed Naming] L364: "benchmark": "phase2_preview_latency",

### docs/API.md
- [Placeholder Secret Markers] L17: "password": "your-password"

### docs/BUILD_DOCUMENTATION_INDEX.md
- [TODO/FIXME Markers] L10: - [TODO.md](TODO.md)

### docs/COMPETITIVE_ANALYSIS.md
- [MVP/Prototype Language] L462: #### **Phase 1: MVP Parity** (Weeks 1-4)

### docs/DOCUMENTATION_INDEX.md
- [TODO/FIXME Markers] L10: - [TODO.md](TODO.md)

### docs/IMPLEMENTATION_SUMMARY.md
- [MVP/Prototype Language] L660: **Estimated time to MVP**: 4-6 weeks with 2 developers

### docs/INDEX.md
- [TODO/FIXME Markers] L11: - [TODO.md](TODO.md)

### docs/legacy/planning/SOVRN_ROADMAP.md
- [MVP/Prototype Language] L50: ### Summary Checklist for MVP Launch

### docs/legacy/README.md
- [TODO/FIXME Markers] L28: - Use docs/SOVRN_OVERVIEW.md, docs/ARCHITECTURE.md, docs/ROADMAP.md, docs/TODO.md, and docs/DECISIONS.md for current understanding.

### docs/legacy/status/FINAL_REPORT.md
- [MVP/Prototype Language] L527: - **Estimated Time to MVP**: 4-6 weeks

### docs/legacy/status/PHASE_1_COMPLETE.md
- [MVP/Prototype Language] L512: **Progress**: 80% of MVP

### docs/legacy/status/README.md
- [TODO/FIXME Markers] L12: - ../../TODO.md

### docs/QUICK_REFERENCE.md
- [MVP/Prototype Language] L437: 4. **Clear roadmap to launch** (4-6 weeks to MVP)

### docs/README.md
- [TODO/FIXME Markers] L10: - [TODO.md](TODO.md)

### docs/README_PIPELINE.md
- [TODO/FIXME Markers] L10: - [TODO.md](TODO.md)

### eval/load/phase2_preview_latency_report.local_mock.json
- [Phase-Prefixed Naming] L3: "benchmark": "phase2_preview_latency",

### eval/load/README.md
- [Phase-Prefixed Naming] L135: - `eval/load/phase2_preview_latency_report.json`

### eval/load/run-preview-latency.ps1
- [Phase-Prefixed Naming] L13: [string]$OutputPath = $(if ([string]::IsNullOrWhiteSpace($env:SOVRN_PREVIEW_BENCH_OUTPUT)) { 'eval/load/phase2_preview_latency_report.json' } else { $env:SOVRN_PREVIEW_BENCH_OUT...

### README.md
- [TODO/FIXME Markers] L16: - [docs/TODO.md](docs/TODO.md)

### services/api/app/api/v1/endpoints/internal.py
- [Phase-Prefixed Naming] L179: legacy_orchestration_input = job_input.get("phase4")

