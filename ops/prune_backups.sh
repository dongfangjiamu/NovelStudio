#!/usr/bin/env bash

set -euo pipefail

OPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$(cd "${OPS_DIR}/.." && pwd)/backups}"
KEEP_DAILY_DAYS="${KEEP_DAILY_DAYS:-7}"
KEEP_WEEKLY_WEEKS="${KEEP_WEEKLY_WEEKS:-4}"
DRY_RUN="${DRY_RUN:-false}"

if [[ ! -d "${BACKUP_DIR}" ]]; then
    echo "backup directory does not exist: ${BACKUP_DIR}"
    exit 0
fi

mapfile -t to_delete < <(
    BACKUP_DIR="${BACKUP_DIR}" \
    KEEP_DAILY_DAYS="${KEEP_DAILY_DAYS}" \
    KEEP_WEEKLY_WEEKS="${KEEP_WEEKLY_WEEKS}" \
    python3 - <<'PY'
import datetime as dt
import os
import re
from pathlib import Path

backup_dir = Path(os.environ["BACKUP_DIR"])
keep_daily_days = int(os.environ["KEEP_DAILY_DAYS"])
keep_weekly_weeks = int(os.environ["KEEP_WEEKLY_WEEKS"])
pattern = re.compile(r"^postgres_.+_(\d{8}T\d{6}Z)\.sql\.gz$")
now = dt.datetime.now(dt.timezone.utc)

files = []
for path in sorted(backup_dir.glob("postgres_*.sql.gz")):
    match = pattern.match(path.name)
    if not match:
        continue
    stamp = dt.datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
    age_days = (now - stamp).days
    iso_year, iso_week, _ = stamp.isocalendar()
    files.append(
        {
            "path": path,
            "stamp": stamp,
            "age_days": age_days,
            "week_key": f"{iso_year}-W{iso_week:02d}",
        }
    )

keep = set()
weekly_kept = set()
for item in sorted(files, key=lambda entry: entry["stamp"], reverse=True):
    if item["age_days"] <= keep_daily_days:
        keep.add(item["path"])
        continue
    if item["age_days"] <= keep_weekly_weeks * 7 and item["week_key"] not in weekly_kept:
        keep.add(item["path"])
        weekly_kept.add(item["week_key"])

for item in files:
    if item["path"] not in keep:
        print(item["path"])
PY
)

if [[ "${#to_delete[@]}" -eq 0 ]]; then
    echo "no backups to prune in ${BACKUP_DIR}"
    exit 0
fi

for file_path in "${to_delete[@]}"; do
    meta_path="${file_path%.sql.gz}.meta"
    if [[ "${DRY_RUN}" == "true" ]]; then
        echo "would delete ${file_path}"
        if [[ -f "${meta_path}" ]]; then
            echo "would delete ${meta_path}"
        fi
        continue
    fi
    rm -f "${file_path}"
    echo "deleted ${file_path}"
    if [[ -f "${meta_path}" ]]; then
        rm -f "${meta_path}"
        echo "deleted ${meta_path}"
    fi
done
