# Project-level commands

.PHONY: refresh-context
refresh-context:
	@echo "[refresh-context] Scanning _tasks, docs, claudedocs and updating .cursor/rules/context-sync.mdc..."
	@python scripts/refresh_context.py
