#!/usr/bin/env bash

set -euo pipefail

OPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${OPS_DIR}/.." && pwd)"
ENV_FILE="${ENV_FILE:-${REPO_ROOT}/.env.compose}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-}"

require_file() {
    local file_path="$1"
    if [[ ! -f "${file_path}" ]]; then
        echo "missing file: ${file_path}" >&2
        exit 1
    fi
}

load_env_file() {
    require_file "${ENV_FILE}"
    set -a
    # shellcheck disable=SC1090
    . "${ENV_FILE}"
    set +a
}

compose_cmd() {
    if [[ -n "${COMPOSE_PROJECT_NAME}" ]]; then
        docker compose -p "${COMPOSE_PROJECT_NAME}" --env-file "${ENV_FILE}" "$@"
        return
    fi
    docker compose --env-file "${ENV_FILE}" "$@"
}

require_service_running() {
    local service_name="$1"
    local container_id
    container_id="$(compose_cmd ps -q "${service_name}")"
    if [[ -z "${container_id}" ]]; then
        echo "service '${service_name}' is not running for env file ${ENV_FILE}" >&2
        exit 1
    fi
}

timestamp_utc() {
    date -u +"%Y%m%dT%H%M%SZ"
}
