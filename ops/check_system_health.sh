#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${REPO_ROOT}/.env.compose}"
APP_PORT="${APP_PORT:-18080}"
APP_URL="${APP_URL:-}"
DISK_CHECK_PATH="${DISK_CHECK_PATH:-${REPO_ROOT}}"
DISK_WARN_PERCENT="${DISK_WARN_PERCENT:-85}"
MEMORY_WARN_PERCENT="${MEMORY_WARN_PERCENT:-90}"
LOAD_WARN_PER_CPU="${LOAD_WARN_PER_CPU:-1.5}"

if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    . "${ENV_FILE}"
    set +a
fi

APP_PORT="${APP_PORT:-18080}"
APP_URL="${APP_URL:-http://127.0.0.1:${APP_PORT}/healthz}"

if ! health_json="$(curl -fsS "${APP_URL}")"; then
    echo "health check failed: cannot reach ${APP_URL}" >&2
    exit 1
fi

read -r app_status db_status <<<"$(HEALTH_JSON="${health_json}" python3 - <<'PY'
import json
import os
payload = json.loads(os.environ["HEALTH_JSON"])
print(payload.get("status", "unknown"), payload.get("database", {}).get("status", "unknown"))
PY
)"

if [[ "${app_status}" != "ok" || "${db_status}" != "ready" ]]; then
    echo "application unhealthy: status=${app_status} database=${db_status}" >&2
    exit 1
fi

disk_used_percent="$(df -P "${DISK_CHECK_PATH}" | awk 'NR==2 {gsub(/%/, "", $5); print $5}')"
mem_total_kb="$(awk '/MemTotal/ {print $2}' /proc/meminfo)"
mem_available_kb="$(awk '/MemAvailable/ {print $2}' /proc/meminfo)"
mem_used_percent="$(( (100 * (mem_total_kb - mem_available_kb)) / mem_total_kb ))"

read -r load_one cpu_count load_threshold <<<"$(python3 - <<'PY'
import os
load_one = os.getloadavg()[0]
cpu_count = os.cpu_count() or 1
threshold = cpu_count * float(os.environ.get("LOAD_WARN_PER_CPU", "1.5"))
print(f"{load_one:.2f} {cpu_count} {threshold:.2f}")
PY
)"

if (( disk_used_percent >= DISK_WARN_PERCENT )); then
    echo "disk usage too high: ${disk_used_percent}% >= ${DISK_WARN_PERCENT}%" >&2
    exit 1
fi

if (( mem_used_percent >= MEMORY_WARN_PERCENT )); then
    echo "memory usage too high: ${mem_used_percent}% >= ${MEMORY_WARN_PERCENT}%" >&2
    exit 1
fi

LOAD_ONE="${load_one}" LOAD_THRESHOLD="${load_threshold}" python3 - <<'PY'
import os
import sys
load_one = float(os.environ["LOAD_ONE"])
load_threshold = float(os.environ["LOAD_THRESHOLD"])
if load_one >= load_threshold:
    print(f"load too high: {load_one:.2f} >= {load_threshold:.2f}", file=sys.stderr)
    raise SystemExit(1)
PY

echo "app=ok database=ready disk=${disk_used_percent}% memory=${mem_used_percent}% load1=${load_one}/${load_threshold} cpus=${cpu_count}"
