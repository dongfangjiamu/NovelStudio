#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_SOURCE_DIR="${REPO_ROOT}/deploy/systemd"
UNIT_TARGET_DIR="${UNIT_TARGET_DIR:-/etc/systemd/system}"

units=(
    novelstudio-compose.service
    novelstudio-backup.service
    novelstudio-backup.timer
    novelstudio-healthcheck.service
    novelstudio-healthcheck.timer
)

for unit_name in "${units[@]}"; do
    install -m 0644 "${UNIT_SOURCE_DIR}/${unit_name}" "${UNIT_TARGET_DIR}/${unit_name}"
    echo "installed ${UNIT_TARGET_DIR}/${unit_name}"
done

systemctl daemon-reload

if [[ "${1:-}" == "--enable" ]]; then
    systemctl enable --now novelstudio-compose.service
    systemctl enable --now novelstudio-backup.timer
    systemctl enable --now novelstudio-healthcheck.timer
    echo "enabled compose service and timers"
    exit 0
fi

echo "copied unit files. run with --enable to start them."
