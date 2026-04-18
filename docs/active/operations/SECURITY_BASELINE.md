# Security Baseline

Last updated: 2026-04-18

## Secret Handling

1. Never commit passwords, API tokens, or service role keys.
2. Keep secrets in local env files or managed secret stores.
3. Rotate keys immediately if any exposure is suspected.

## Database Bootstrap Order

- Primary: DATABASE_URL
- Fallback: SUPABASE_DB_URL

## Supabase Variables

- SUPABASE_ENABLED
- SUPABASE_URL
- SUPABASE_PUBLISHABLE_KEY
- SUPABASE_SERVICE_ROLE_KEY
- SUPABASE_DB_URL

## Credential Hygiene

- Keep .env out of source control.
- Use redacted values in all docs and examples.
- Prefer short-lived credentials for automation where available.
