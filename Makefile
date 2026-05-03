# Makefile — Mathoms AI dev tooling
#
# Rode `make` ou `make help` para listar todos os targets disponíveis.
# `make info` mostra versões de Python, Node, Docker e Redis detectadas.
#
# Setup canônico: pip install -e . -r requirements-dev.txt + npm install em
# frontend/ + frontend-ops/. Logs e PIDs locais ficam em _smoke_pids/ e
# _dev_pids/ (ambos no .gitignore).
#
# Convenções:
#   - Targets públicos têm linha `## nome: descrição` consumida por `make help`
#   - Targets privados (chamados por outros targets) não têm `##`
#   - Variáveis em UPPER_SNAKE; macros reutilizáveis via `define ... endef`
#   - PYTEST_ARGS / RUFF_ARGS / GO_TEST_ARGS são pass-through em runtime

# ---------------------------------------------------------------------------
# Shell e flags globais
# ---------------------------------------------------------------------------

SHELL          := /bin/bash
.SHELLFLAGS    := -eu -o pipefail -c
MAKEFLAGS      += --no-print-directory
.DEFAULT_GOAL  := help

# ---------------------------------------------------------------------------
# Variáveis canônicas
# ---------------------------------------------------------------------------

VENV    := .venv/bin
PYTHON  := $(VENV)/python
PIP     := $(VENV)/pip

# Pass-through para CLIs externas. Ex.: `make test-pipeline PYTEST_ARGS="-x -k saldo"`
PYTEST_ARGS   ?=
RUFF_ARGS     ?=
GO_TEST_ARGS  ?= -race -count=1

# Stage selecionado em test-pipeline: o teste abaixo depende de um helper
# E1.6 que conflita com fixture default do contexto (ADR-097). Mantido como
# variável para facilitar revisão/expiração futura.
PYTEST_PIPELINE_DESELECT := tests/test_stage_wrappers.py::TestContextIntegration::test_default_has_processed_dirs

# Diretórios de runtime (gitignored)
SMOKE_DIR     := _smoke_pids
SMOKE_DB      := mathoms-smoke.db
SMOKE_STORAGE := _smoke_storage
DEV_DIR       := _dev_pids

# Portas dev (para checks e kill-stale)
PORT_API           := 8000
PORT_OPS_API       := 8001
PORT_FRONTEND      := 3000
PORT_FRONTEND_OPS  := 3100
DEV_PORTS          := $(PORT_API) $(PORT_OPS_API) $(PORT_FRONTEND) $(PORT_FRONTEND_OPS)

# ---------------------------------------------------------------------------
# Macros reutilizáveis
# ---------------------------------------------------------------------------

# Aborta se a porta $(1) já está em uso (LISTEN). Usado antes de bind de
# uvicorn/npm para detectar órfãos de sessão anterior com mensagem útil.
define check_port_free
	@if lsof -nP -iTCP:$(1) -sTCP:LISTEN >/dev/null 2>&1; then \
	   pid=$$(lsof -ti tcp:$(1) -sTCP:LISTEN 2>/dev/null | head -1); \
	   cmd=$$(ps -p $$pid -o comm= 2>/dev/null | head -1 || echo "?"); \
	   echo "   ❌ Porta $(1) já em uso (pid=$$pid, cmd=$$cmd)."; \
	   echo "      Provavelmente uvicorn/npm órfão de sessão anterior."; \
	   echo "      Resolva: make dev-kill-stale  ou  kill $$pid"; \
	   exit 1; \
	 fi
endef

# Mata um processo via PID file: SIGTERM com grace, escala para SIGKILL se
# resistir, sempre remove o pidfile. Idempotente.
# Args: $(1) = label, $(2) = pidfile path
define kill_pid_safe
	@if [ -f $(2) ]; then \
	   pid=$$(cat $(2) 2>/dev/null || true); \
	   if [ -n "$$pid" ] && kill -0 $$pid 2>/dev/null; then \
	     kill $$pid 2>/dev/null || true; \
	     for i in 1 2 3 4 5 6 7 8 9 10; do \
	       kill -0 $$pid 2>/dev/null || break; sleep 0.2; \
	     done; \
	     if kill -0 $$pid 2>/dev/null; then \
	       kill -9 $$pid 2>/dev/null || true; \
	       echo "   ✓ $(1) (pid=$$pid) parado (SIGKILL)"; \
	     else \
	       echo "   ✓ $(1) (pid=$$pid) parado"; \
	     fi; \
	   else \
	     echo "   · $(1) (pid=$${pid:-?}) já não estava rodando"; \
	   fi; \
	   rm -f $(2); \
	 fi
endef

# Gera Fernet key efêmera válida via venv. Ecoa para stdout. Aborta com
# mensagem clara se cryptography não está instalado (sem fallback inválido,
# que mascarava bug em produção do smoke).
define ephemeral_fernet
$$($(PYTHON) -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' 2>/dev/null || { \
  echo "ERRO: cryptography não instalado em $(VENV). Rode 'make dev-bootstrap'." >&2; exit 1; \
})
endef

# ---------------------------------------------------------------------------
# Help / info
# ---------------------------------------------------------------------------

.PHONY: help info version

## help: Lista todos os targets disponíveis (default)
help:
	@awk ' \
	BEGIN { \
	  printf "\n\033[1mMathoms AI — make targets\033[0m\n"; \
	  printf "Uso: \033[36mmake <target>\033[0m  (pass-through: PYTEST_ARGS, RUFF_ARGS, SVC, M)\n"; \
	} \
	/^# -+ *$$/ { in_box = !in_box; if (in_box) { sect_name = ""; sect_printed = 0; } next; } \
	in_box && sect_name == "" && /^# [A-Z]/ { \
	  sect_name = $$0; sub(/^# /, "", sect_name); next; \
	} \
	/^## [a-zA-Z][a-zA-Z0-9_-]+:/ { \
	  if (sect_name != "" && !sect_printed) { \
	    printf "\n\033[33m%s\033[0m\n", sect_name; sect_printed = 1; \
	  } \
	  line = $$0; sub(/^## /, "", line); \
	  c = index(line, ":"); \
	  printf "  \033[36m%-32s\033[0m %s\n", substr(line, 1, c-1), substr(line, c+2); \
	} \
	END { print ""; } \
	' $(MAKEFILE_LIST)

## info: Mostra versões detectadas de Python/Node/Docker/Redis (debug de ambiente)
info:
	@echo "Mathoms AI — environment"
	@printf "  %-14s " "venv:";       [ -d .venv ] && echo "$(CURDIR)/.venv" || echo "(ausente — rode make dev-bootstrap)"
	@printf "  %-14s " "python:";     $(PYTHON) --version 2>/dev/null || echo "(não encontrado em $(VENV))"
	@printf "  %-14s " "node:";       node --version 2>/dev/null || echo "(não encontrado)"
	@printf "  %-14s " "npm:";        npm --version 2>/dev/null || echo "(não encontrado)"
	@printf "  %-14s " "docker:";     docker --version 2>/dev/null | head -1 || echo "(não encontrado)"
	@printf "  %-14s " "redis-cli:";  redis-cli --version 2>/dev/null || echo "(não encontrado)"
	@printf "  %-14s " "go:";         go version 2>/dev/null || echo "(não encontrado — ok até A6g.7)"
	@printf "  %-14s " "git branch:"; git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "(não é repo git)"
	@printf "  %-14s " "git head:";   git log -1 --format='%h %s' 2>/dev/null || true

## version: Sinônimo de info
version: info

# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

.PHONY: smoke-up smoke-down smoke-reset smoke-seed smoke-logs smoke-dirs

## smoke-up: Sobe Redis + backend + Celery worker + frontend em background
smoke-up: smoke-dirs
	@echo "▶  Verificando portas…"
	$(call check_port_free,$(PORT_API))
	$(call check_port_free,$(PORT_FRONTEND))
	@echo "▶  Starting Redis (docker compose)…"
	@docker compose -f docker-compose.smoke.yml up -d --wait
	@echo "▶  Starting backend API (porta $(PORT_API))…"
	@FERNET_KEY="$(ephemeral_fernet)"; \
	 MATHOMS_DATABASE_URL="sqlite+aiosqlite:///$(CURDIR)/$(SMOKE_DB)" \
	 MATHOMS_STORAGE_ROOT="$(CURDIR)/$(SMOKE_STORAGE)" \
	 MATHOMS_REDIS_URL="redis://localhost:6379/0" \
	 MATHOMS_FERNET_KEY="$$FERNET_KEY" \
	 nohup $(VENV)/uvicorn backend.app.main:app \
	   --host 0.0.0.0 --port $(PORT_API) --reload \
	   > $(CURDIR)/$(SMOKE_DIR)/api.log 2>&1 & echo $$! > $(CURDIR)/$(SMOKE_DIR)/api.pid; \
	 echo "$$FERNET_KEY" > $(CURDIR)/$(SMOKE_DIR)/fernet.key
	@echo "▶  Starting Celery worker…"
	@FERNET_KEY="$$(cat $(CURDIR)/$(SMOKE_DIR)/fernet.key)"; \
	 MATHOMS_DATABASE_URL="sqlite+aiosqlite:///$(CURDIR)/$(SMOKE_DB)" \
	 MATHOMS_STORAGE_ROOT="$(CURDIR)/$(SMOKE_STORAGE)" \
	 MATHOMS_REDIS_URL="redis://localhost:6379/0" \
	 MATHOMS_FERNET_KEY="$$FERNET_KEY" \
	 nohup $(VENV)/celery -A backend.app.worker worker \
	   --loglevel=info --concurrency=2 \
	   > $(CURDIR)/$(SMOKE_DIR)/worker.log 2>&1 & echo $$! > $(CURDIR)/$(SMOKE_DIR)/worker.pid
	@echo "▶  Starting frontend (porta $(PORT_FRONTEND))…"
	@nohup npm --prefix frontend run dev \
	   > $(CURDIR)/$(SMOKE_DIR)/frontend.log 2>&1 & echo $$! > $(CURDIR)/$(SMOKE_DIR)/frontend.pid
	@echo ""
	@echo "  ✅ Smoke stack started:"
	@echo "     API:      http://localhost:$(PORT_API)"
	@echo "     Frontend: http://localhost:$(PORT_FRONTEND)"
	@echo "     Health:   http://localhost:$(PORT_API)/health"
	@echo ""
	@echo "  Next: make smoke-seed"

## smoke-seed: Cria usuários, workspace e copia fixtures para inbox
smoke-seed:
	@if [ ! -f $(CURDIR)/$(SMOKE_DIR)/fernet.key ]; then \
	   echo "❌ $(SMOKE_DIR)/fernet.key ausente. Rode 'make smoke-up' antes."; exit 1; \
	 fi
	@FERNET_KEY="$$(cat $(CURDIR)/$(SMOKE_DIR)/fernet.key)"; \
	 MATHOMS_DATABASE_URL="sqlite+aiosqlite:///$(CURDIR)/$(SMOKE_DB)" \
	 MATHOMS_STORAGE_ROOT="$(CURDIR)/$(SMOKE_STORAGE)" \
	 MATHOMS_FERNET_KEY="$$FERNET_KEY" \
	 $(PYTHON) backend/app/scripts/seed_smoke.py

## smoke-down: Para todos os processos locais + Redis (idempotente)
smoke-down:
	@echo "▶  Stopping local processes…"
	$(call kill_pid_safe,api,$(CURDIR)/$(SMOKE_DIR)/api.pid)
	$(call kill_pid_safe,worker,$(CURDIR)/$(SMOKE_DIR)/worker.pid)
	$(call kill_pid_safe,frontend,$(CURDIR)/$(SMOKE_DIR)/frontend.pid)
	@echo "▶  Stopping Redis…"
	@docker compose -f docker-compose.smoke.yml down
	@echo "  ✅ Smoke stack stopped."

## smoke-reset: Para tudo, apaga DB + storage + pids, reinicia do zero
smoke-reset: smoke-down
	@echo "▶  Resetting smoke state…"
	@rm -f $(SMOKE_DB)
	@rm -rf $(SMOKE_STORAGE) $(SMOKE_DIR)
	@echo "  ✅ Reset completo. Rode 'make smoke-up && make smoke-seed' para reiniciar."

## smoke-logs: tail -f dos logs api/worker/frontend (em paralelo)
smoke-logs:
	@logs=$$(ls $(CURDIR)/$(SMOKE_DIR)/*.log 2>/dev/null); \
	 if [ -z "$$logs" ]; then \
	   echo "Nenhum log encontrado em $(SMOKE_DIR)/. Rode 'make smoke-up' primeiro."; \
	 else \
	   tail -f $$logs; \
	 fi

smoke-dirs:
	@mkdir -p $(SMOKE_DIR) $(SMOKE_STORAGE)

# ---------------------------------------------------------------------------
# Dev stack
#
# Sobe os 6 serviços de desenvolvimento local em background.
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

.PHONY: dev-bootstrap dev-pull dev-up dev-down dev-restart dev-restart-worker \
        dev-status dev-logs dev-reset-env dev-dirs dev-kill-stale \
        dev-redis-up dev-api-up dev-worker-up dev-frontend-up \
        dev-ops-api-up dev-frontend-ops-up

dev-dirs:
	@mkdir -p $(DEV_DIR)

## dev-bootstrap: Setup inicial — venv, deps, .env, codegen
dev-bootstrap:
	@echo "▶  Verificando .venv…"
	@if [ ! -d .venv ]; then \
	   python3 -m venv .venv; \
	   echo "   ✓ .venv criada"; \
	 else echo "   ✓ .venv presente"; fi
	@echo "▶  Instalando deps Python (pip install -e . -r requirements-dev.txt)…"
	@$(PIP) install -q -e . -r requirements-dev.txt
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
	@echo "     API:          http://localhost:$(PORT_API)"
	@echo "     Worker:       celery (concurrency=2)"
	@echo "     Frontend:     http://localhost:$(PORT_FRONTEND)"
	@echo "     Ops API:      http://127.0.0.1:$(PORT_OPS_API)/admin/*"
	@echo "     Frontend-ops: http://127.0.0.1:$(PORT_FRONTEND_OPS)/login"
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
	@echo "▶  Subindo API principal (porta $(PORT_API))…"
	$(call check_port_free,$(PORT_API))
	@nohup $(VENV)/uvicorn backend.app.main:app \
	   --host 127.0.0.1 --port $(PORT_API) --reload \
	   > $(CURDIR)/$(DEV_DIR)/api.log 2>&1 & echo $$! > $(CURDIR)/$(DEV_DIR)/api.pid

dev-worker-up: dev-dirs
	@echo "▶  Subindo Celery worker (concurrency=2)…"
	@nohup $(VENV)/celery -A backend.app.worker worker \
	   --loglevel=info --concurrency=2 \
	   > $(CURDIR)/$(DEV_DIR)/worker.log 2>&1 & echo $$! > $(CURDIR)/$(DEV_DIR)/worker.pid

dev-frontend-up: dev-dirs
	@echo "▶  Subindo frontend (porta $(PORT_FRONTEND))…"
	$(call check_port_free,$(PORT_FRONTEND))
	@nohup npm --prefix frontend run dev \
	   > $(CURDIR)/$(DEV_DIR)/frontend.log 2>&1 & echo $$! > $(CURDIR)/$(DEV_DIR)/frontend.pid

dev-ops-api-up: dev-dirs
	@echo "▶  Subindo Ops API (porta $(PORT_OPS_API), /admin/*)…"
	$(call check_port_free,$(PORT_OPS_API))
	@OPS_SECRET="$$(grep -E '^MATHOMS_INTERNAL_OPS_SESSION_SECRET=' .env 2>/dev/null | head -1 | cut -d= -f2-)"; \
	 if [ -z "$$OPS_SECRET" ]; then \
	   OPS_SECRET="$$(openssl rand -hex 32)"; \
	   echo "   ⚠️  MATHOMS_INTERNAL_OPS_SESSION_SECRET não está em .env — usando valor efêmero."; \
	   echo "      Persistir: echo MATHOMS_INTERNAL_OPS_SESSION_SECRET=$$OPS_SECRET >> .env"; \
	 fi; \
	 MATHOMS_INTERNAL_OPS_UI_ENABLED=1 \
	 MATHOMS_INTERNAL_OPS_SESSION_SECRET="$$OPS_SECRET" \
	 nohup $(VENV)/uvicorn backend.app.main:app \
	   --host 127.0.0.1 --port $(PORT_OPS_API) --reload \
	   > $(CURDIR)/$(DEV_DIR)/ops-api.log 2>&1 & echo $$! > $(CURDIR)/$(DEV_DIR)/ops-api.pid

dev-frontend-ops-up: dev-dirs
	@echo "▶  Subindo frontend-ops (porta $(PORT_FRONTEND_OPS))…"
	$(call check_port_free,$(PORT_FRONTEND_OPS))
	@INTERNAL_OPS_API_BASE=http://127.0.0.1:$(PORT_OPS_API) \
	 nohup npm --prefix frontend-ops run dev \
	   > $(CURDIR)/$(DEV_DIR)/frontend-ops.log 2>&1 & echo $$! > $(CURDIR)/$(DEV_DIR)/frontend-ops.pid

## dev-down: Mata todos os processos via PID files (com escalação SIGTERM→SIGKILL)
dev-down:
	@echo "▶  Parando serviços de dev…"
	$(call kill_pid_safe,api,$(CURDIR)/$(DEV_DIR)/api.pid)
	$(call kill_pid_safe,worker,$(CURDIR)/$(DEV_DIR)/worker.pid)
	$(call kill_pid_safe,frontend,$(CURDIR)/$(DEV_DIR)/frontend.pid)
	$(call kill_pid_safe,ops-api,$(CURDIR)/$(DEV_DIR)/ops-api.pid)
	$(call kill_pid_safe,frontend-ops,$(CURDIR)/$(DEV_DIR)/frontend-ops.pid)
	@if [ -f $(CURDIR)/$(DEV_DIR)/redis.pid ]; then \
	   $(MAKE) -s _kill_redis_pidfile; \
	 else \
	   echo "   · redis não foi subido por dev-up (preservado)"; \
	 fi
	@echo "  ✅ Stack parado."

# Privado: kill do redis nativo via pidfile, com a mesma escalação
.PHONY: _kill_redis_pidfile
_kill_redis_pidfile:
	$(call kill_pid_safe,redis,$(CURDIR)/$(DEV_DIR)/redis.pid)

## dev-restart: down && up
dev-restart: dev-down dev-up

## dev-restart-worker: Restart só do worker (após mudar pipeline/ ou tasks/)
dev-restart-worker:
	$(call kill_pid_safe,worker,$(CURDIR)/$(DEV_DIR)/worker.pid)
	@$(MAKE) -s dev-worker-up
	@echo "  ✅ Worker reiniciado."

## dev-status: Health check de cada serviço (PID alive + porta listening)
dev-status:
	@printf "%-14s  %-6s  %-5s  %s\n" "Serviço" "PID" "Porta" "Status"
	@printf "%-14s  %-6s  %-5s  %s\n" "──────────────" "──────" "─────" "──────────────────────"
	@for svc in api worker frontend ops-api frontend-ops; do \
	   case $$svc in \
	     api)          port=$(PORT_API) ;; \
	     ops-api)      port=$(PORT_OPS_API) ;; \
	     frontend)     port=$(PORT_FRONTEND) ;; \
	     frontend-ops) port=$(PORT_FRONTEND_OPS) ;; \
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

## dev-kill-stale: Mata QUALQUER processo nas portas dev + limpa _dev_pids/
##                 Use quando dev-up reclama de "Porta X já em uso".
dev-kill-stale:
	@echo "▶  Matando processos órfãos nas portas dev…"
	@killed=0; \
	 for port in $(DEV_PORTS); do \
	   pids=$$(lsof -ti tcp:$$port -sTCP:LISTEN 2>/dev/null || true); \
	   if [ -n "$$pids" ]; then \
	     for pid in $$pids; do \
	       cmd=$$(ps -p $$pid -o comm= 2>/dev/null | head -1 || echo "?"); \
	       echo "   ✓ porta $$port → kill $$pid ($$cmd)"; \
	       kill $$pid 2>/dev/null || true; \
	       for i in 1 2 3 4 5; do kill -0 $$pid 2>/dev/null || break; sleep 0.2; done; \
	       if kill -0 $$pid 2>/dev/null; then \
	         echo "      · SIGTERM ignorado, escalando para SIGKILL"; \
	         kill -9 $$pid 2>/dev/null || true; \
	       fi; \
	       killed=$$((killed+1)); \
	     done; \
	   fi; \
	 done; \
	 if [ $$killed -eq 0 ]; then echo "   · nenhum órfão encontrado"; fi
	@for d in frontend frontend-ops; do \
	   lock=$(CURDIR)/$$d/.next/dev/lock; \
	   if [ -f $$lock ]; then \
	     pid=$$(python3 -c "import json,sys; print(json.load(open('$$lock')).get('pid',''))" 2>/dev/null || true); \
	     if [ -n "$$pid" ] && ! kill -0 $$pid 2>/dev/null; then \
	       echo "   ✓ $$d/.next/dev/lock órfão (pid=$$pid morto) → removido"; \
	       rm -f $$lock; \
	     fi; \
	   fi; \
	 done
	@rm -rf $(CURDIR)/$(DEV_DIR)
	@echo "  ✅ Stale kill completo. 'make dev-up' para subir novamente."

## dev-logs: tail -f de todos os logs (SVC=<nome> para um só)
dev-logs:
ifdef SVC
	@if [ ! -f $(CURDIR)/$(DEV_DIR)/$(SVC).log ]; then \
	   echo "❌ $(DEV_DIR)/$(SVC).log não existe. Disponíveis:"; \
	   ls $(CURDIR)/$(DEV_DIR)/*.log 2>/dev/null | xargs -n1 basename | sed 's/\.log//;s/^/   /'; \
	   exit 1; \
	 fi
	@tail -f $(CURDIR)/$(DEV_DIR)/$(SVC).log
else
	@logs=$$(ls $(CURDIR)/$(DEV_DIR)/*.log 2>/dev/null); \
	 if [ -z "$$logs" ]; then \
	   echo "Nenhum log encontrado em $(DEV_DIR)/. Rode 'make dev-up' primeiro."; \
	 else \
	   tail -f $$logs; \
	 fi
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
# Tests, lint, format
#
# Pass-through: PYTEST_ARGS / RUFF_ARGS.
#   make test-pipeline PYTEST_ARGS="-x -k saldo"
#   make lint RUFF_ARGS="--statistics"
# ---------------------------------------------------------------------------

.PHONY: test test-all test-pipeline test-backend test-frontend test-e2e \
        lint lint-fix format precommit check-boundaries

## test: Alias de test-all (pipeline + backend)
test: test-all

## test-all: Roda suíte Python completa — pipeline + backend
test-all: test-pipeline test-backend

## test-pipeline: pytest tests/ -q (pipeline determinístico, ADR-097/E1.6)
test-pipeline:
	$(PYTHON) -m pytest tests/ -q \
	  --deselect=$(PYTEST_PIPELINE_DESELECT) $(PYTEST_ARGS)

## test-backend: pytest backend/tests/ -q (FastAPI + repos + integration)
test-backend:
	$(PYTHON) -m pytest backend/tests/ -q $(PYTEST_ARGS)

## test-frontend: Vitest unit (frontend/)
test-frontend:
	@npm --prefix frontend test -- --run

## test-e2e: Playwright @critical (frontend/)
test-e2e:
	@npm --prefix frontend run test:e2e

## lint: ruff check . (gate bloqueante — selectores E/F/I/W)
lint:
	$(VENV)/ruff check . $(RUFF_ARGS)

## lint-fix: ruff check --fix . (auto-fix de lint, sem tocar formatação)
lint-fix:
	$(VENV)/ruff check --fix . $(RUFF_ARGS)

## format: ruff format . + ruff check --fix . (formatter canônico, ADR-114)
format:
	$(VENV)/ruff format .
	$(VENV)/ruff check --fix .

## precommit: pre-commit run --all-files (mesmos hooks aplicados no git)
precommit:
	$(VENV)/pre-commit run --all-files

## check-boundaries: Verifica que pipeline/ não importa fastapi/celery/sqlalchemy
check-boundaries:
	$(PYTHON) dev/check_pipeline_boundaries.py

# ---------------------------------------------------------------------------
# Codegen / snapshots (commitar diff após rodar)
# ---------------------------------------------------------------------------

.PHONY: update-openapi-snapshot update-pipeline-service-openapi update-db-schema-reference

## update-openapi-snapshot: Regenera docs/api/v1/openapi.json (A6f.2 · ADR-102)
update-openapi-snapshot: update-pipeline-service-openapi
	@mkdir -p docs/api/v1
	@FERNET_KEY="$${MATHOMS_FERNET_KEY:-$(ephemeral_fernet)}"; \
	 MATHOMS_FERNET_KEY="$$FERNET_KEY" \
	 $(PYTHON) -c 'import json; from backend.app.main import app; \
	   print(json.dumps(app.openapi(), indent=2, sort_keys=True))' \
	 > docs/api/v1/openapi.json
	@echo "✓ docs/api/v1/openapi.json regenerado. Comite o diff."

## update-pipeline-service-openapi: Regenera docs/api/v1/pipeline-service.openapi.json (A6f.1 · ADR-112)
update-pipeline-service-openapi:
	@mkdir -p docs/api/v1
	@PYTHONPATH="$(CURDIR)/pipeline-service:$(CURDIR)" \
	 $(PYTHON) -c 'import json; from app.main import create_app; \
	   print(json.dumps(create_app().openapi(), indent=2, sort_keys=True))' \
	 > docs/api/v1/pipeline-service.openapi.json
	@echo "✓ docs/api/v1/pipeline-service.openapi.json regenerado. Comite o diff."

## update-db-schema-reference: Regenera docs/DB_SCHEMA_REFERENCE.md (A6f.4 · ADR-102 R20)
update-db-schema-reference:
	@FERNET_KEY="$${MATHOMS_FERNET_KEY:-$(ephemeral_fernet)}"; \
	 MATHOMS_FERNET_KEY="$$FERNET_KEY" \
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

## go-test: go test ./... (no-op se não houver .go) — pass-through GO_TEST_ARGS
go-test:
	@if [ ! -f go.work ] || [ -z "$(GO_FILES)" ]; then \
	   echo "go-test: sem go.work ou .go presentes (skip)"; \
	 else \
	   go test ./... $(GO_TEST_ARGS); \
	 fi

## go-all: fmt + lint + test Go
go-all: go-fmt go-lint go-test

# ---------------------------------------------------------------------------
# Alembic — DB migrations
#
# Usa backend/alembic.ini com paths absolutos (%(here)s) — pode rodar de
# qualquer cwd. F6.5E.4: env.py rejeita SQLite com path relativo.
# ---------------------------------------------------------------------------

ALEMBIC := $(VENV)/alembic -c backend/alembic.ini

.PHONY: migrate migrate-current migrate-history migrate-revision

## migrate: alembic upgrade head (aplica migrations pendentes)
migrate:
	$(ALEMBIC) upgrade head

## migrate-current: Mostra revisão atual do DB
migrate-current:
	$(ALEMBIC) current

## migrate-history: Histórico de revisões com detalhes
migrate-history:
	$(ALEMBIC) history --verbose

## migrate-revision: Cria nova revisão autogenerate (uso: make migrate-revision M="msg")
migrate-revision:
	@if [ -z "$(M)" ]; then \
	   echo "❌ Faltou mensagem. Uso: make migrate-revision M=\"descrição da migration\""; \
	   exit 1; \
	 fi
	$(ALEMBIC) revision --autogenerate -m "$(M)"

# ---------------------------------------------------------------------------
# Clean / housekeeping
# ---------------------------------------------------------------------------

.PHONY: clean clean-pyc clean-caches clean-all

## clean: Remove caches Python (pyc/pycache/.pytest_cache/.ruff_cache/.mypy_cache)
clean: clean-pyc clean-caches

clean-pyc:
	@find . -type d -name "__pycache__" -not -path "./.venv/*" -not -path "./node_modules/*" -prune -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -not -path "./.venv/*" -delete 2>/dev/null || true

clean-caches:
	@rm -rf .pytest_cache .ruff_cache .mypy_cache build dist *.egg-info
	@rm -rf backend/.pytest_cache pipeline/.pytest_cache 2>/dev/null || true
	@echo "  ✅ Caches Python removidos."

## clean-all: clean + remove _smoke_pids/, _dev_pids/, _scratch/, frontend/.next/
##            (NÃO toca em .venv, node_modules, .env, mathoms.db)
clean-all: clean
	@rm -rf $(SMOKE_DIR) $(SMOKE_STORAGE) $(DEV_DIR) _scratch
	@rm -rf frontend/.next frontend-ops/.next
	@echo "  ✅ Estado runtime local limpo (preservados: .venv, node_modules, .env, DB)."
