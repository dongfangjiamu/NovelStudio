#!/usr/bin/env bash

set -euo pipefail

# shellcheck source=ops/common.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

if [[ $# -ne 1 ]]; then
    echo "usage: $0 /abs/path/to/backup.sql.gz" >&2
    exit 1
fi

backup_file="$1"
require_file "${backup_file}"
load_env_file
require_service_running postgres

if [[ "${backup_file}" == *.gz ]]; then
    gunzip -c "${backup_file}" | compose_cmd exec -T postgres psql \
        -v ON_ERROR_STOP=1 \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}"
else
    compose_cmd exec -T postgres psql \
        -v ON_ERROR_STOP=1 \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" < "${backup_file}"
fi

echo "restored backup into ${POSTGRES_DB}: ${backup_file}"
