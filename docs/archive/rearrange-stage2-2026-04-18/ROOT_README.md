# SOVRN

SOVRN is a hosted AI website-building platform.

Users access SOVRN through a hosted domain with account login and subscription-based access.

In SOVRN documentation, offline means the core stack does not require paid third-party AI APIs for inference. The platform runs its own inference stack rather than depending on external per-request AI API billing.

## Canonical Documentation

Use these files first:

- [docs/SOVRN_OVERVIEW.md](docs/SOVRN_OVERVIEW.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/ROADMAP.md](docs/ROADMAP.md)
- [docs/TODO.md](docs/TODO.md)
- [docs/DECISIONS.md](docs/DECISIONS.md)

## Legacy Documentation Note

Some older documents in this repository are retained for historical traceability and may include deprecated planning or outdated status claims.

## Supabase Integration

SOVRN supports Supabase as a managed backend path.

- Configure `SUPABASE_ENABLED=true` and set Supabase environment variables in local secret files.
- API database bootstrap resolves in this order: `DATABASE_URL` first, then `SUPABASE_DB_URL` fallback.
- Never commit publishable keys, service role keys, or direct DB passwords to source control.
