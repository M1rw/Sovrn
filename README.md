# SOVRN

SOVRN is a production AI website platform with a hosted product surface and a self-managed inference stack.

## Canonical Documentation

Use these files first:

- docs/README.md
- docs/active/tracking/PROJECT_DASHBOARD.md
- docs/active/planning/MASTER_EXECUTION_PLAN.md
- docs/active/planning/ENGINEERING_BACKLOG.md
- docs/active/agent/CODEXX_AGENT_GUIDE.md

## Security Baseline

- Never commit secrets, tokens, or database passwords.
- Use local environment files or a managed secret store.
- Database bootstrap order in API: DATABASE_URL, then SUPABASE_DB_URL.

## Repository Hygiene

- Active documentation lives under docs/active/.
- Historical snapshots are preserved under docs/archive/rearrange-stage2-2026-04-18/ and docs/archive/rearrange-stage3-2026-04-18/.
- Prefer ORCHESTRATION_* naming for runtime controls.
