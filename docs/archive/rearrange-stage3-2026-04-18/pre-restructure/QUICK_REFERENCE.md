# SOVRN Quick Reference

## Core Commands

- npm run lint
- npm run typecheck
- npm run test
- npm run test:web
- npm run test:api

## Backend Targeted Validation

- py -3.11 -m pytest services/api/tests/test_phase4_orchestration.py -q
- py -3.11 -m pytest services/api/tests/test_phase3_patch_contract.py -q

## Audit and Plan

- e:/Synthos/.venv/Scripts/python.exe scripts/rearrange_audit.py
- docs/Plan/PHASED_NEXTGEN_PRODUCTION_PLAN.md

## Security

- Keep .env files out of source control.
- Use docs/security/SUPABASE_SETUP.md for Supabase configuration.
