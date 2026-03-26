#!/usr/bin/env bash

set -euo pipefail

OPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${OPS_DIR}/backup_postgres.sh"
"${OPS_DIR}/prune_backups.sh"
