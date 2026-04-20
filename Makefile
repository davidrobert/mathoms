# Makefile — Mathoms AI dev tooling (A6b.5)
#
# Targets de smoke test: smoke-up, smoke-down, smoke-reset, smoke-seed, smoke-logs
# Prerequisite: pip install -e ".[dev]" + npm install em frontend/
#
# Todos os processos locais (backend, worker, frontend) escrevem logs em
# _smoke_pids/<service>.log e guardam PID em _smoke_pids/<service>.pid.
# _smoke_pids/ está no .gitignore.

SHELL := /bin/bash
VENV  := .venv/bin
PYTHON := $(VENV)/python

# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

SMOKE_DIR     := _smoke_pids
SMOKE_DB      := mathoms-smoke.db
SMOKE_STORAGE := _smoke_storage

.PHONY: smoke-up smoke-down smoke-reset smoke-seed smoke-logs smoke-api smoke-worker smoke-frontend smoke-dirs

## smoke-up: Sobe Redis + backend + Celery worker + frontend em background
smoke-up: smoke-dirs
	@echo "▶  Starting Redis…"
	docker compose -f docker-compose.smoke.yml up -d --wait
	@echo "▶  Starting backend API…"
	@MATHOMS_DATABASE_URL="sqlite+aiosqlite:///$(CURDIR)/$(SMOKE_DB)" \
	 MATHOMS_STORAGE_ROOT="$(CURDIR)/$(SMOKE_STORAGE)" \
	 MATHOMS_REDIS_URL="redis://localhost:6379/0" \
	 MATHOMS_FERNET_KEY="$$($(VENV)/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' 2>/dev/null || echo 'smoke-key-32bytes-placeholder-AA=')" \
	 nohup $(VENV)/uvicorn backend.app.main:app \
	   --host 0.0.0.0 --port 8000 --reload \
	   > $(CURDIR)/$(SMOKE_DIR)/api.log 2>&1 & echo $$! > $(CURDIR)/$(SMOKE_DIR)/api.pid
	@echo "▶  Starting Celery worker…"
	@MATHOMS_DATABASE_URL="sqlite+aiosqlite:///$(CURDIR)/$(SMOKE_DB)" \
	 MATHOMS_STORAGE_ROOT="$(CURDIR)/$(SMOKE_STORAGE)" \
	 MATHOMS_REDIS_URL="redis://localhost:6379/0" \
	 nohup $(VENV)/celery -A backend.app.worker worker \
	   --loglevel=info --concurrency=2 \
	   > $(CURDIR)/$(SMOKE_DIR)/worker.log 2>&1 & echo $$! > $(CURDIR)/$(SMOKE_DIR)/worker.pid
	@echo "▶  Starting frontend…"
	@nohup npm --prefix frontend run dev \
	  > $(CURDIR)/$(SMOKE_DIR)/frontend.log 2>&1 & echo $$! > $(CURDIR)/$(SMOKE_DIR)/frontend.pid
	@echo ""
	@echo "  ✅ Smoke stack started:"
	@echo "     API:      http://localhost:8000"
	@echo "     Frontend: http://localhost:3000"
	@echo "     Health:   http://localhost:8000/health"
	@echo ""
	@echo "  Next: make smoke-seed"

## smoke-seed: Cria usuários, workspace e copia fixtures para inbox
smoke-seed:
	@MATHOMS_DATABASE_URL="sqlite+aiosqlite:///$(CURDIR)/$(SMOKE_DB)" \
	 MATHOMS_STORAGE_ROOT="$(CURDIR)/$(SMOKE_STORAGE)" \
	 MATHOMS_FERNET_KEY="smoke-key-32bytes-placeholder-AA=" \
	 $(PYTHON) backend/app/scripts/seed_smoke.py

## smoke-down: Para todos os processos locais + Redis
smoke-down:
	@echo "▶  Stopping local processes…"
	@for svc in api worker frontend; do \
	  if [ -f $(CURDIR)/$(SMOKE_DIR)/$$svc.pid ]; then \
	    pid=$$(cat $(CURDIR)/$(SMOKE_DIR)/$$svc.pid); \
	    kill $$pid 2>/dev/null && echo "   Stopped $$svc (pid=$$pid)" || true; \
	    rm -f $(CURDIR)/$(SMOKE_DIR)/$$svc.pid; \
	  fi; \
	done
	@echo "▶  Stopping Redis…"
	docker compose -f docker-compose.smoke.yml down
	@echo "  ✅ Smoke stack stopped."

## smoke-reset: Para tudo, apaga DB e storage, reinicia
smoke-reset: smoke-down
	@echo "▶  Resetting smoke state…"
	rm -f $(SMOKE_DB)
	rm -rf $(SMOKE_STORAGE)
	rm -rf $(SMOKE_DIR)
	@echo "  ✅ Reset complete. Run 'make smoke-up && make smoke-seed' to restart."

## smoke-logs: Tail dos logs de todos os serviços em paralelo
smoke-logs:
	@tail -f $(CURDIR)/$(SMOKE_DIR)/api.log $(CURDIR)/$(SMOKE_DIR)/worker.log $(CURDIR)/$(SMOKE_DIR)/frontend.log 2>/dev/null || \
	 echo "No log files found. Run 'make smoke-up' first."

## smoke-dirs: Cria diretórios necessários
smoke-dirs:
	@mkdir -p $(SMOKE_DIR) $(SMOKE_STORAGE)

# ---------------------------------------------------------------------------
# Dev helpers
# ---------------------------------------------------------------------------

.PHONY: test lint format check-boundaries update-openapi-snapshot update-db-schema-reference

## test: Roda pytest com cobertura
test:
	$(PYTHON) -m pytest tests/ -q --deselect=tests/test_stage_wrappers.py::TestContextIntegration::test_default_has_processed_dirs

## lint: Roda ruff
lint:
	$(VENV)/ruff check .

## format: Aplica black + ruff --fix
format:
	$(VENV)/black .
	$(VENV)/ruff check --fix .

## check-boundaries: Verifica que pipeline/ não importa framework
check-boundaries:
	$(PYTHON) dev/check_pipeline_boundaries.py

## update-openapi-snapshot: Regenera docs/api/v1/openapi.json a partir do FastAPI app (A6f.2 · ADR-102)
update-openapi-snapshot:
	@mkdir -p docs/api/v1
	@MATHOMS_FERNET_KEY=$${MATHOMS_FERNET_KEY:-NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA=} \
	  $(PYTHON) -c 'import json; from backend.app.main import app; \
	    print(json.dumps(app.openapi(), indent=2, sort_keys=True))' \
	  > docs/api/v1/openapi.json
	@echo "✓ docs/api/v1/openapi.json regenerado. Comite o diff."

## update-db-schema-reference: Regenera docs/DB_SCHEMA_REFERENCE.md a partir de Base.metadata (A6f.4 · ADR-102 R20)
update-db-schema-reference:
	@MATHOMS_FERNET_KEY=$${MATHOMS_FERNET_KEY:-NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA=} \
	  $(PYTHON) dev/generate_db_schema_reference.py > docs/DB_SCHEMA_REFERENCE.md
	@echo "✓ docs/DB_SCHEMA_REFERENCE.md regenerado. Comite o diff."
