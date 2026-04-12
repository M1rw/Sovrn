#!/usr/bin/env bash
set -euo pipefail

DB_USER="${POSTGRES_USER:-sovrn}"
DB_NAME="${POSTGRES_DB:-sovrn}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_PASS="${POSTGRES_PASSWORD:-}"

declare -a DB_PASS_CANDIDATES=()

add_candidate() {
  local candidate="${1:-}"
  if [[ -z "$candidate" ]]; then
    return
  fi
  for existing in "${DB_PASS_CANDIDATES[@]}"; do
    if [[ "$existing" == "$candidate" ]]; then
      return
    fi
  done
  DB_PASS_CANDIDATES+=("$candidate")
}

can_connect_db() {
  local candidate_pass="$1"
  if ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  timeout 5 docker run --rm --network host \
    -e PGPASSWORD="$candidate_pass" \
    postgres:16-alpine \
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc "select 1" \
    >/dev/null 2>&1
}

add_candidate "$DB_PASS"

if [[ -f .env ]]; then
  ENV_DB_PASS="$(awk -F= '/^POSTGRES_PASSWORD=/{print substr($0, index($0,$2)); exit}' .env)"
  add_candidate "$ENV_DB_PASS"
fi

if command -v docker >/dev/null 2>&1; then
  if docker ps --format '{{.Names}}' | grep -qx 'sovrn-db'; then
    LIVE_DB_PASS="$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' sovrn-db | awk -F= '/^POSTGRES_PASSWORD=/{print $2; exit}')"
    add_candidate "$LIVE_DB_PASS"
  fi
fi

add_candidate "devpassword"

for candidate in "${DB_PASS_CANDIDATES[@]}"; do
  if can_connect_db "$candidate"; then
    DB_PASS="$candidate"
    break
  fi
done

if [[ -z "$DB_PASS" ]]; then
  DB_PASS="devpassword"
fi

export NODE_ENV="${NODE_ENV:-development}"

# Local uvicorn cannot resolve Docker service aliases like "db".
# If DATABASE_URL points to a Docker-only host, rewrite to localhost.
DEFAULT_DB_URL="postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME"
RESOLVED_DB_URL="${DATABASE_URL:-$DEFAULT_DB_URL}"
if [[ "$RESOLVED_DB_URL" == *"@db:"* ]] || [[ "$RESOLVED_DB_URL" == *"@postgres:"* ]]; then
  RESOLVED_DB_URL="$DEFAULT_DB_URL"
fi

export DATABASE_URL="$RESOLVED_DB_URL"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export INFERENCE_URL="${INFERENCE_URL:-http://localhost:8080}"

cd services/api
exec python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
