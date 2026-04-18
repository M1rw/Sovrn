# Risks and Blockers

Last updated: 2026-04-18

| ID | Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- | --- |
| R1 | Staging credentials or environment mismatch delays latency gate | Blocks promotion decision | Validate env and tokens before benchmark run; keep fallback execution window | Open |
| R2 | Canary telemetry gaps hide regressions in preview stream behavior | Increases rollout risk | Define required telemetry fields and enforce gate check before go-live | Open |
| R3 | Mixed-workload load profile differs from production traffic mix | False confidence in AQE behavior | Run representative workload mix and capture queue-depth evidence | Open |
| R4 | Docs drift after cleanup cycle | Loss of operational clarity | Enforce update rules in agent guide and delivery log discipline | Managed |
