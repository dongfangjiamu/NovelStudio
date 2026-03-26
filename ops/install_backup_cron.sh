#!/usr/bin/env bash

set -euo pipefail

OPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${OPS_DIR}/.." && pwd)"
ENV_FILE="${ENV_FILE:-${REPO_ROOT}/.env.compose}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-}"
CRON_SCHEDULE="${CRON_SCHEDULE:-17 3 * * *}"
CRON_LOG="${CRON_LOG:-/var/log/novelstudio-backup.log}"
CRON_FILE="${CRON_FILE:-/etc/cron.d/novelstudio-backup}"

cron_line="${CRON_SCHEDULE} root cd ${REPO_ROOT} && ENV_FILE=${ENV_FILE} COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME} ${REPO_ROOT}/ops/run_backup_cycle.sh >> ${CRON_LOG} 2>&1"

if [[ "${1:-}" == "--print" ]]; then
    printf '%s\n' "${cron_line}"
    exit 0
fi

printf '%s\n' "SHELL=/bin/bash" > "${CRON_FILE}"
printf '%s\n' "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" >> "${CRON_FILE}"
printf '%s\n' "${cron_line}" >> "${CRON_FILE}"

echo "installed cron file: ${CRON_FILE}"
echo "schedule: ${CRON_SCHEDULE}"
