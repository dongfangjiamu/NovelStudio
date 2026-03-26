ENV_FILE ?= .env.compose
COMPOSE_PROJECT_NAME ?=
BACKUP ?=
CRON_LOG ?= /var/log/novelstudio-backup.log

.PHONY: up down logs ps backup-db restore-db prune-backups backup-cycle print-backup-cron health-check systemd-verify

up:
	COMPOSE_PROJECT_NAME=$(COMPOSE_PROJECT_NAME) docker compose --env-file $(ENV_FILE) up -d --build

down:
	COMPOSE_PROJECT_NAME=$(COMPOSE_PROJECT_NAME) docker compose --env-file $(ENV_FILE) down

logs:
	COMPOSE_PROJECT_NAME=$(COMPOSE_PROJECT_NAME) docker compose --env-file $(ENV_FILE) logs -f app

ps:
	COMPOSE_PROJECT_NAME=$(COMPOSE_PROJECT_NAME) docker compose --env-file $(ENV_FILE) ps

backup-db:
	ENV_FILE=$(abspath $(ENV_FILE)) COMPOSE_PROJECT_NAME=$(COMPOSE_PROJECT_NAME) ./ops/backup_postgres.sh

restore-db:
	test -n "$(BACKUP)" || (echo "usage: make restore-db BACKUP=/abs/path/to/backup.sql.gz" && exit 1)
	ENV_FILE=$(abspath $(ENV_FILE)) COMPOSE_PROJECT_NAME=$(COMPOSE_PROJECT_NAME) ./ops/restore_postgres.sh "$(BACKUP)"

prune-backups:
	ENV_FILE=$(abspath $(ENV_FILE)) COMPOSE_PROJECT_NAME=$(COMPOSE_PROJECT_NAME) ./ops/prune_backups.sh

backup-cycle:
	ENV_FILE=$(abspath $(ENV_FILE)) COMPOSE_PROJECT_NAME=$(COMPOSE_PROJECT_NAME) ./ops/run_backup_cycle.sh

print-backup-cron:
	ENV_FILE=$(abspath $(ENV_FILE)) COMPOSE_PROJECT_NAME=$(COMPOSE_PROJECT_NAME) CRON_LOG=$(CRON_LOG) ./ops/install_backup_cron.sh --print

health-check:
	ENV_FILE=$(abspath $(ENV_FILE)) COMPOSE_PROJECT_NAME=$(COMPOSE_PROJECT_NAME) ./ops/check_system_health.sh

systemd-verify:
	systemd-analyze verify deploy/systemd/novelstudio-compose.service deploy/systemd/novelstudio-backup.service deploy/systemd/novelstudio-backup.timer deploy/systemd/novelstudio-healthcheck.service deploy/systemd/novelstudio-healthcheck.timer
