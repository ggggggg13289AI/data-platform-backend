# Project-level commands

.PHONY: refresh-context
refresh-context:
	@echo "[refresh-context] Scanning _tasks, docs, claudedocs and updating .cursor/rules/context-sync.mdc..."
	@python scripts/refresh_context.py

.PHONY: backup
backup:
	@echo "[backup] Creating database backup..."
	@python scripts/backup_database.py --compress --keep-last 30

.PHONY: backup-postgres
backup-postgres:
	@echo "[backup-postgres] Creating PostgreSQL backup..."
	@python scripts/backup_database.py --mode postgres --compress --keep-last 30

.PHONY: restore
restore:
	@echo "[restore] Restoring database from backup..."
	@echo "Usage: make restore FILE=backups/backup_YYYYMMDD_HHMMSS.json.gz"
	@python scripts/restore_database.py $(FILE)
