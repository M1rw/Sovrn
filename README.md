# SOVRN

SOVRN is a production AI website platform with a hosted product surface and a self-managed inference stack.

## Canonical Documentation

Use these files first:

- docs/SOVRN_OVERVIEW.md
- docs/ARCHITECTURE.md
- docs/ROADMAP.md
- docs/ENGINEERING_BACKLOG.md
- docs/DECISIONS.md
- docs/Plan/PHASED_NEXTGEN_PRODUCTION_PLAN.md

## Security Baseline

- Never commit secrets, tokens, or database passwords.
- Use local environment files or a managed secret store.
- Database bootstrap order in API: DATABASE_URL, then SUPABASE_DB_URL.

## Repository Hygiene

- Active documentation lives under docs/.
- Historical snapshots are preserved under docs/archive/rearrange-stage2-2026-04-18/.
- Prefer ORCHESTRATION_* naming for runtime controls.
