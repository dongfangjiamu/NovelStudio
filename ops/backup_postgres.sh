#!/usr/bin/env bash

set -euo pipefail

# shellcheck source=ops/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

load_env_file
require_service_running postgres

BACKUP_DIR="${BACKUP_DIR:-${REPO_ROOT}/backups}"
mkdir -p "${BACKUP_DIR}"

timestamp="$(timestamp_utc)"
dump_file="${BACKUP_DIR}/postgres_${POSTGRES_DB}_${timestamp}.sql.gz"
meta_file="${dump_file%.sql.gz}.meta"

compose_cmd exec -T postgres pg_dump \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" | gzip -c > "${dump_file}"

{
    printf "timestamp=%s\n" "${timestamp}"
    printf "database=%s\n" "${POSTGRES_DB}"
    printf "user=%s\n" "${POSTGRES_USER}"
    printf "env_file=%s\n" "${ENV_FILE}"
    printf "compose_project=%s\n" "${COMPOSE_PROJECT_NAME:-default}"
    printf "backup_file=%s\n" "${dump_file}"
} > "${meta_file}"

echo "created backup: ${dump_file}"
echo "metadata: ${meta_file}"
