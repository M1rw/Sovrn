#!/usr/bin/env bash
set -euo pipefail

COMPOSE_ARGS=(-f docker-compose.yml -f docker-compose.dev.yml)

docker compose "${COMPOSE_ARGS[@]}" up -d db redis

# Ensure local API credentials remain consistent across reused Postgres volumes.
DB_USER="${POSTGRES_USER:-sovrn}"
DB_PASS="${POSTGRES_PASSWORD:-devpassword}"
DB_NAME="${POSTGRES_DB:-sovrn}"

if docker ps --format '{{.Names}}' | grep -qx 'sovrn-db'; then
  docker exec sovrn-db psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<SQL
DO
\$do\$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    EXECUTE format('ALTER ROLE %I WITH LOGIN PASSWORD %L', '${DB_USER}', '${DB_PASS}');
  END IF;
END
\$do\$;
SQL
fi
