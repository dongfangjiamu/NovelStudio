PYTHON := .venv/bin/python
PIP := .venv/bin/pip
PYTEST := .venv/bin/pytest
LANGGRAPH := .venv/bin/langgraph
HOST ?= 0.0.0.0
PORT ?= 8000

.PHONY: install env-check test smoke dev serve db-init

install:
	python3 -m venv .venv
	$(PIP) install -e ".[dev]"
	$(PIP) install -U "langgraph-cli[inmem]"

env-check:
	$(PYTHON) scripts/check_env.py

test:
	$(PYTEST) -q

smoke:
	$(PYTHON) scripts/smoke_run.py

dev:
	$(LANGGRAPH) dev

serve:
	.venv/bin/uvicorn novel_app.api.app:app --host $(HOST) --port $(PORT)

db-init:
	$(PYTHON) scripts/init_db.py
