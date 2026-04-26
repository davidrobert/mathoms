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
# Dev stack — sobe os 6 serviços de desenvolvimento local em background
#
# Diferente de `smoke-*`, este preserva `.env` e `mathoms.db` reais.
# Targets:
#   make dev-bootstrap       First-run: venv, deps, .env, codegen
#   make dev-pull            git pull --ff-only + npm install
#   make dev-up              Sobe redis + api(8000) + worker + frontend(3000)
#                              + ops-api(8001) + frontend-ops(3100)
#   make dev-down            Mata todos os processos
#   make dev-restart         down && up
#   make dev-restart-worker  Restart só do worker (após mudar pipeline/)
#   make dev-status          ✅/❌ por serviço (PID + porta listening)
#   make dev-logs            tail -f de todos (SVC=api para um só)
#   make dev-kill-stale      Mata órfãos em 8000/8001/3000/3100 + limpa pids
#   make dev-reset-env       DESTRUTIVO: regenera .env (invalida Fernet)
#
# PIDs em _dev_pids/<svc>.pid · logs em _dev_pids/<svc>.log (no .gitignore)
# ---------------------------------------------------------------------------

DEV_DIR := _dev_pids

.PHONY: dev-bootstrap dev-pull dev-up dev-down dev-restart dev-restart-worker \
        dev-status dev-logs dev-reset-env dev-dirs dev-kill-stale \
        dev-redis-up dev-api-up dev-worker-up dev-frontend-up \
        dev-ops-api-up dev-frontend-ops-up

## dev-dirs: Cria _dev_pids/
dev-dirs:
	@mkdir -p $(DEV_DIR)

# Helper: aborta se a porta $(1) já está em uso por outro processo.
# Usado nos dev-X-up para detectar uvicorn/npm órfãos antes do bind.
define check_port_free
	@if lsof -nP -iTCP:$(1) -sTCP:LISTEN >/dev/null 2>&1; then \
	   pid=$$(lsof -ti tcp:$(1) 2>/dev/null | head -1); \
	   echo "   ❌ Porta $(1) já está em uso (pid=$$pid)."; \
	   echo "      Provavelmente uvicorn/npm órfão de uma sessão anterior."; \
	   echo "      Resolva com: 'make dev-kill-stale'  (mata tudo nas portas 8000/8001/3000/3100)"; \
	   echo "      Ou manual:   'kill $$pid'"; \
	   exit 1; \
	 fi
endef

## dev-bootstrap: Setup inicial — venv, deps, .env, codegen
dev-bootstrap:
	@echo "▶  Verificando .venv…"
	@if [ ! -d .venv ]; then \
	   python3 -m venv .venv; \
	   echo "   ✓ .venv criada"; \
	 else echo "   ✓ .venv presente"; fi
	@echo "▶  Instalando deps Python (pip install -e .[dev])…"
	@$(VENV)/pip install -q -e ".[dev]"
	@echo "▶  Instalando deps frontend…"
	@npm --prefix frontend install --silent
	@npm --prefix frontend-ops install --silent
	@echo "▶  Verificando .env…"
	@if [ ! -f .env ]; then \
	   ./scripts/gen-secrets.sh --init-env; \
	 else echo "   ✓ .env presente (preservado)"; fi
	@echo "▶  Verificando frontend-ops/.env.local…"
	@if [ ! -f frontend-ops/.env.local ] && [ -f frontend-ops/.env.local.example ]; then \
	   cp frontend-ops/.env.local.example frontend-ops/.env.local; \
	   echo "   ✓ frontend-ops/.env.local criado"; \
	 else echo "   ✓ frontend-ops/.env.local presente ou example ausente"; fi
	@echo "▶  Codegen (design-tokens + report-layout)…"
	@$(PYTHON) design-tokens/build.py
	@$(PYTHON) dev/codegen_report_layout.py
	@if [ ! -f config/internal_operators.yaml ]; then \
	   echo ""; \
	   echo "   ⚠️  config/internal_operators.yaml não existe."; \
	   echo "      Login no console interno (3100) falhará até criá-lo."; \
	   echo "      Gere senha: python3 scripts/hash_ops_pw.py"; \
	   echo "      Detalhes: docs/RUNBOOK.md §7.2."; \
	 fi
	@echo ""
	@echo "  ✅ Bootstrap completo. 'make dev-up' para subir o stack."

## dev-pull: git pull --ff-only + npm install em ambos os frontends
dev-pull:
	@echo "▶  Verificando working tree…"
	@if ! git diff --quiet || ! git diff --cached --quiet; then \
	   echo "   ❌ Working tree sujo. Commit ou stash antes."; \
	   exit 1; \
	 fi
	@echo "▶  git fetch + git pull --ff-only…"
	@git fetch origin
	@git pull --ff-only
	@echo "▶  npm install (frontend + frontend-ops)…"
	@npm --prefix frontend install --silent
	@npm --prefix frontend-ops install --silent
	@echo "  ✅ Pull completo. 'make dev-restart' para reiniciar serviços."

## dev-up: Sobe os 6 serviços em background
dev-up: dev-dirs dev-redis-up dev-api-up dev-worker-up dev-frontend-up dev-ops-api-up dev-frontend-ops-up
	@echo ""
	@echo "  ✅ Dev stack subido (6 serviços):"
	@echo "     Redis:        redis://localhost:6379/0"
	@echo "     API:          http://localhost:8000"
	@echo "     Worker:       celery (concurrency=2)"
	@echo "     Frontend:     http://localhost:3000"
	@echo "     Ops API:      http://127.0.0.1:8001/admin/*"
	@echo "     Frontend-ops: http://127.0.0.1:3100/login"
	@echo ""
	@echo "  Logs em $(DEV_DIR)/<svc>.log · 'make dev-status' · 'make dev-logs'"

dev-redis-up: dev-dirs
	@if redis-cli ping >/dev/null 2>&1; then \
	   echo "▶  Redis já rodando (reusando, não controlado por dev-down)"; \
	 elif command -v redis-server >/dev/null 2>&1; then \
	   redis-server --daemonize yes \
	     --pidfile $(CURDIR)/$(DEV_DIR)/redis.pid \
	     --logfile $(CURDIR)/$(DEV_DIR)/redis.log; \
	   sleep 1; \
	   echo "▶  Redis subido (nativo)"; \
	 else \
	   echo "   ❌ redis-server não encontrado. Instale: brew install redis"; \
	   exit 1; \
	 fi

dev-api-up: dev-dirs
	@echo "▶  Subindo API principal (porta 8000)…"
	$(call check_port_free,8000)
	@nohup $(VENV)/uvicorn backend.app.main:app \
	   --host 127.0.0.1 --port 8000 --reload \
	   > $(CURDIR)/$(DEV_DIR)/api.log 2>&1 & echo $$! > $(CURDIR)/$(DEV_DIR)/api.pid

dev-worker-up: dev-dirs
	@echo "▶  Subindo Celery worker (concurrency=2)…"
	@nohup $(VENV)/celery -A backend.app.worker worker \
	   --loglevel=info --concurrency=2 \
	   > $(CURDIR)/$(DEV_DIR)/worker.log 2>&1 & echo $$! > $(CURDIR)/$(DEV_DIR)/worker.pid

dev-frontend-up: dev-dirs
	@echo "▶  Subindo frontend (porta 3000)…"
	$(call check_port_free,3000)
	@nohup npm --prefix frontend run dev \
	   > $(CURDIR)/$(DEV_DIR)/frontend.log 2>&1 & echo $$! > $(CURDIR)/$(DEV_DIR)/frontend.pid

dev-ops-api-up: dev-dirs
	@echo "▶  Subindo Ops API (porta 8001, /admin/*)…"
	$(call check_port_free,8001)
	@OPS_SECRET="$$(grep -E '^MATHOMS_INTERNAL_OPS_SESSION_SECRET=' .env 2>/dev/null | head -1 | cut -d= -f2-)"; \
	 if [ -z "$$OPS_SECRET" ]; then \
	   OPS_SECRET="$$(openssl rand -hex 32)"; \
	   echo "   ⚠️  MATHOMS_INTERNAL_OPS_SESSION_SECRET não está em .env — usando valor efêmero."; \
	   echo "      Persistir: echo MATHOMS_INTERNAL_OPS_SESSION_SECRET=$$OPS_SECRET >> .env"; \
	 fi; \
	 MATHOMS_INTERNAL_OPS_UI_ENABLED=1 \
	 MATHOMS_INTERNAL_OPS_SESSION_SECRET="$$OPS_SECRET" \
	 nohup $(VENV)/uvicorn backend.app.main:app \
	   --host 127.0.0.1 --port 8001 --reload \
	   > $(CURDIR)/$(DEV_DIR)/ops-api.log 2>&1 & echo $$! > $(CURDIR)/$(DEV_DIR)/ops-api.pid

dev-frontend-ops-up: dev-dirs
	@echo "▶  Subindo frontend-ops (porta 3100)…"
	$(call check_port_free,3100)
	@INTERNAL_OPS_API_BASE=http://127.0.0.1:8001 \
	 nohup npm --prefix frontend-ops run dev \
	   > $(CURDIR)/$(DEV_DIR)/frontend-ops.log 2>&1 & echo $$! > $(CURDIR)/$(DEV_DIR)/frontend-ops.pid

## dev-down: Mata todos os processos via PID files
dev-down:
	@echo "▶  Parando serviços de dev…"
	@for svc in api worker frontend ops-api frontend-ops; do \
	   if [ -f $(CURDIR)/$(DEV_DIR)/$$svc.pid ]; then \
	     pid=$$(cat $(CURDIR)/$(DEV_DIR)/$$svc.pid); \
	     if kill $$pid 2>/dev/null; then \
	       echo "   ✓ $$svc (pid=$$pid) parado"; \
	     else \
	       echo "   · $$svc (pid=$$pid) já não estava rodando"; \
	     fi; \
	     rm -f $(CURDIR)/$(DEV_DIR)/$$svc.pid; \
	   fi; \
	 done
	@if [ -f $(CURDIR)/$(DEV_DIR)/redis.pid ]; then \
	   pid=$$(cat $(CURDIR)/$(DEV_DIR)/redis.pid); \
	   kill $$pid 2>/dev/null && echo "   ✓ redis (pid=$$pid) parado" || true; \
	   rm -f $(CURDIR)/$(DEV_DIR)/redis.pid; \
	 else \
	   echo "   · redis não foi subido por dev-up (preservado)"; \
	 fi
	@echo "  ✅ Stack parado."

## dev-restart: down && up
dev-restart: dev-down dev-up

## dev-restart-worker: Restart só do worker (após mudar pipeline/ ou tasks/)
dev-restart-worker:
	@if [ -f $(CURDIR)/$(DEV_DIR)/worker.pid ]; then \
	   pid=$$(cat $(CURDIR)/$(DEV_DIR)/worker.pid); \
	   kill $$pid 2>/dev/null && echo "   ✓ Worker parado (pid=$$pid)" || true; \
	   rm -f $(CURDIR)/$(DEV_DIR)/worker.pid; \
	 fi
	@$(MAKE) -s dev-worker-up
	@echo "  ✅ Worker reiniciado."

## dev-status: Health check de cada serviço (PID alive + porta listening)
dev-status:
	@printf "%-14s  %-6s  %-5s  %s\n" "Serviço" "PID" "Porta" "Status"
	@printf "%-14s  %-6s  %-5s  %s\n" "──────────────" "──────" "─────" "──────────────────────"
	@for svc in api worker frontend ops-api frontend-ops; do \
	   case $$svc in \
	     api)          port=8000 ;; \
	     ops-api)      port=8001 ;; \
	     frontend)     port=3000 ;; \
	     frontend-ops) port=3100 ;; \
	     *)            port="" ;; \
	   esac; \
	   pidfile=$(CURDIR)/$(DEV_DIR)/$$svc.pid; \
	   if [ -f $$pidfile ]; then \
	     pid=$$(cat $$pidfile); \
	     if kill -0 $$pid 2>/dev/null; then \
	       if [ -n "$$port" ]; then \
	         if lsof -nP -iTCP:$$port -sTCP:LISTEN >/dev/null 2>&1; then \
	           printf "%-14s  %-6s  %-5s  %s\n" $$svc $$pid $$port "✅ OK"; \
	         else \
	           printf "%-14s  %-6s  %-5s  %s\n" $$svc $$pid $$port "⏳ subindo (porta ainda não listening)"; \
	         fi; \
	       else \
	         printf "%-14s  %-6s  %-5s  %s\n" $$svc $$pid "—" "✅ OK (sem porta)"; \
	       fi; \
	     else \
	       printf "%-14s  %-6s  %-5s  %s\n" $$svc $$pid "$${port:-—}" "❌ PID morto (ver $(DEV_DIR)/$$svc.log)"; \
	     fi; \
	   else \
	     printf "%-14s  %-6s  %-5s  %s\n" $$svc "—" "$${port:-—}" "⚪ não subido"; \
	   fi; \
	 done
	@if redis-cli ping >/dev/null 2>&1; then \
	   printf "%-14s  %-6s  %-5s  %s\n" redis "—" 6379 "✅ OK"; \
	 else \
	   printf "%-14s  %-6s  %-5s  %s\n" redis "—" 6379 "❌ não responde"; \
	 fi

## dev-kill-stale: Mata QUALQUER processo nas portas dev (8000/8001/3000/3100) + limpa _dev_pids/
##                 Use quando dev-up reclama de "Porta X já em uso" (uvicorn/npm órfão).
dev-kill-stale:
	@echo "▶  Matando processos órfãos nas portas dev…"
	@killed=0; \
	 for port in 8000 8001 3000 3100; do \
	   pids=$$(lsof -ti tcp:$$port 2>/dev/null); \
	   if [ -n "$$pids" ]; then \
	     for pid in $$pids; do \
	       cmd=$$(ps -p $$pid -o comm= 2>/dev/null | head -1); \
	       echo "   ✓ porta $$port → kill $$pid ($$cmd)"; \
	       kill $$pid 2>/dev/null || kill -9 $$pid 2>/dev/null; \
	       killed=$$((killed+1)); \
	     done; \
	   fi; \
	 done; \
	 if [ $$killed -eq 0 ]; then echo "   · nenhum órfão encontrado"; fi
	@rm -rf $(CURDIR)/$(DEV_DIR)
	@echo "  ✅ Stale kill completo. 'make dev-up' para subir novamente."

## dev-logs: tail -f de todos os logs (SVC=<nome> para um só)
dev-logs:
ifdef SVC
	@tail -f $(CURDIR)/$(DEV_DIR)/$(SVC).log
else
	@tail -f $(CURDIR)/$(DEV_DIR)/*.log 2>/dev/null || \
	 echo "Nenhum log encontrado. Rode 'make dev-up' primeiro."
endif

## dev-reset-env: DESTRUTIVO — regenera .env (INVALIDA Fernet → API keys LLM e dados encriptados quebram)
dev-reset-env:
	@echo "⚠️  ATENÇÃO: regenerar .env vai invalidar:"
	@echo "    - API keys LLM salvas (precisará re-cadastrar)"
	@echo "    - Senhas PDF criptografadas"
	@echo "    - CPFs/dados sensíveis encriptados no DB"
	@echo ""
	@printf "Confirmar regeneração? (digite 'sim' para prosseguir): "
	@read CONFIRM; \
	 if [ "$$CONFIRM" = "sim" ]; then \
	   rm -f .env; \
	   ./scripts/gen-secrets.sh --init-env; \
	   echo "  ✅ .env regenerado."; \
	 else \
	   echo "  · Abortado, .env preservado."; \
	 fi

# ---------------------------------------------------------------------------
# Dev helpers
# ---------------------------------------------------------------------------

.PHONY: test lint format check-boundaries update-openapi-snapshot update-pipeline-service-openapi update-db-schema-reference

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
update-openapi-snapshot: update-pipeline-service-openapi
	@mkdir -p docs/api/v1
	@MATHOMS_FERNET_KEY=$${MATHOMS_FERNET_KEY:-NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA=} \
	  $(PYTHON) -c 'import json; from backend.app.main import app; \
	    print(json.dumps(app.openapi(), indent=2, sort_keys=True))' \
	  > docs/api/v1/openapi.json
	@echo "✓ docs/api/v1/openapi.json regenerado. Comite o diff."

## update-pipeline-service-openapi: Regenera docs/api/v1/pipeline-service.openapi.json (A6f.1 · ADR-112)
update-pipeline-service-openapi:
	@mkdir -p docs/api/v1
	@cd pipeline-service && $(CURDIR)/$(PYTHON) -c 'import json, sys; sys.path.insert(0, "."); sys.path.insert(0, ".."); from app.main import create_app; \
	    print(json.dumps(create_app().openapi(), indent=2, sort_keys=True))' \
	  > $(CURDIR)/docs/api/v1/pipeline-service.openapi.json
	@echo "✓ docs/api/v1/pipeline-service.openapi.json regenerado. Comite o diff."

## update-db-schema-reference: Regenera docs/DB_SCHEMA_REFERENCE.md a partir de Base.metadata (A6f.4 · ADR-102 R20)
update-db-schema-reference:
	@MATHOMS_FERNET_KEY=$${MATHOMS_FERNET_KEY:-NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA=} \
	  $(PYTHON) dev/generate_db_schema_reference.py > docs/DB_SCHEMA_REFERENCE.md
	@echo "✓ docs/DB_SCHEMA_REFERENCE.md regenerado. Comite o diff."

# ---------------------------------------------------------------------------
# Go (A6g.7 — ADR-113)
#
# No-op enquanto não há .go no repo. Quando o primeiro serviço entrar em
# services/<name>/ com go.mod próprio + use directive em go.work, os
# targets executam normalmente. CI (.github/workflows/go.yml) gatilha
# via hashFiles('**/*.go').
# ---------------------------------------------------------------------------

.PHONY: go-fmt go-lint go-test go-all

GO_FILES := $(shell find . -type f -name "*.go" -not -path "./node_modules/*" -not -path "./.git/*" 2>/dev/null)

## go-fmt: gofmt -s -w em todos os .go (no-op se não houver)
go-fmt:
	@if [ -z "$(GO_FILES)" ]; then \
	  echo "go-fmt: nenhum arquivo .go encontrado (skip)"; \
	else \
	  gofmt -s -w $(GO_FILES); \
	  echo "✓ gofmt aplicado"; \
	fi

## go-lint: golangci-lint run (no-op se não houver go.work ativo)
go-lint:
	@if [ ! -f go.work ] || [ -z "$(GO_FILES)" ]; then \
	  echo "go-lint: sem go.work ou .go presentes (skip)"; \
	else \
	  golangci-lint run --timeout=3m ./...; \
	fi

## go-test: go test ./... -race -count=1 (no-op se não houver .go)
go-test:
	@if [ ! -f go.work ] || [ -z "$(GO_FILES)" ]; then \
	  echo "go-test: sem go.work ou .go presentes (skip)"; \
	else \
	  go test ./... -race -count=1; \
	fi

## go-all: fmt + lint + test Go
go-all: go-fmt go-lint go-test
