# Supabase Setup

Use environment variables only. Do not commit credentials.

## Required Variables

- SUPABASE_ENABLED=true
- SUPABASE_URL=https://<project-ref>.supabase.co
- SUPABASE_PUBLISHABLE_KEY=sb_publishable_<redacted>
- SUPABASE_SERVICE_ROLE_KEY=<redacted>
- SUPABASE_DB_URL=postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres

## Runtime Resolution

- API uses DATABASE_URL when present.
- If DATABASE_URL is not set, API falls back to SUPABASE_DB_URL.

## Rotation Guidance

- Rotate publishable and service role keys if exposed.
- Rotate database password if exposure is suspected.
