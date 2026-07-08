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
# Usa o python do venv quando existe; senão cai para python3 do PATH (worktrees em
# .claude/worktrees/ e ambientes sem venv não têm .venv/bin/python).
PYTHON  := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || command -v python3)
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

# Token deste worktree/clone. Escopa os workers Celery a ESTE clone via
# --hostname, para que um down/off/recover aqui não mate o worker de outro
# worktree que compartilha o mesmo host (todos batem no mesmo broker e no
# mesmo pgrep). Sanitizado para caber num hostname Celery.
WT := $(shell basename "$(CURDIR)" | tr -c 'A-Za-z0-9' '-' | sed 's/-*$$//')-$(shell echo "$(CURDIR)" | shasum | cut -c1-6)

# Portas da stack nativa (uvicorn-local) + overlay Go (:8002). UMA fonte única
# consumida por check_port_free (launcher), recover (sweep) e status. Sem isso
# a :8002 fica de fora de um dos três e vira beco sem saída (o bug em que o
# erro de colisão manda rodar um sweep que não cobre a porta).
PORT_API           := 8000
PORT_OPS_API       := 8001
PORT_FRONTEND      := 3000
PORT_FRONTEND_OPS  := 3100
PORT_GO            := 8002
DEV_PORTS          := $(PORT_API) $(PORT_OPS_API) $(PORT_FRONTEND) $(PORT_FRONTEND_OPS)
ALL_LOCAL_PORTS    := $(DEV_PORTS) $(PORT_GO)

# Portas publicadas pela stack dev em Docker (docker-compose.dev.yml). Banda
# DELIBERADAMENTE distinta da legada acima para as duas coexistirem sem colisão.
# Overridáveis: `make dev-up-docker MATHOMS_DOCKER_API_PORT=9000`. Exportadas
# para o compose consumir os mesmos valores que o check_port_free abaixo.
MATHOMS_DOCKER_API_PORT      ?= 8010
MATHOMS_DOCKER_FRONTEND_PORT ?= 3010
MATHOMS_DOCKER_POSTGRES_PORT ?= 5433
MATHOMS_DOCKER_OPS_PORT      ?= 3110
export MATHOMS_DOCKER_API_PORT MATHOMS_DOCKER_FRONTEND_PORT MATHOMS_DOCKER_POSTGRES_PORT MATHOMS_DOCKER_OPS_PORT

# Porta HOST do redis do smoke (docker-compose.smoke.yml). DELIBERADAMENTE ≠ 6379:
# 6379 é a porta do redis NATIVO da stack dev (dev-redis-up), e o smoke roda
# backend/worker nativos que alcançam o broker por localhost. Isolar o smoke em
# 6380 elimina a colisão nos dois sentidos — (a) `smoke-down` derrubando um redis
# que a nativa "reusou"; (b) `smoke-up` falhando ao bindar 6379 quando a nativa já
# o ocupa. A porta INTERNA do container continua 6379 (consumidores da rede
# compose, ex. pipeline-service → redis-smoke:6379, não mudam). 6380 segue o
# precedente do segundo redis no CI (ci.yml). Override: `make smoke-up
# MATHOMS_SMOKE_REDIS_PORT=6399`.
MATHOMS_SMOKE_REDIS_PORT ?= 6380
export MATHOMS_SMOKE_REDIS_PORT

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
	   echo "      Provavelmente uvicorn/npm/go órfão de sessão anterior (talvez de outro clone)."; \
	   echo "      Resolva: make recover  (reset seguro deste clone)  ou  kill $$pid"; \
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

# Mata os celery workers DESTE worktree cujo --hostname casa o prefixo $(1),
# com escalação SIGTERM→SIGKILL. Idempotente. Como todo worker é lançado com
# --hostname="<role>-$(WT)@…", isto NÃO toca workers de outros worktrees/clones
# que compartilham o host (o pgrep genérico antigo matava todos — split-brain).
# Ex.: $(1)=celery-native-$(WT) (só o nativo) · celery-native.*-$(WT) (nativo +
# overlay go) · celery-(native|smoke)(-go)?-$(WT) (tudo deste worktree).
# Matar o master dispara o warm-shutdown dos filhos prefork do próprio Celery.
define kill_celery_scoped
	@pat='celery -A backend.app.worker worker.*--hostname=$(1)@'; \
	 pids="$$(pgrep -f "$$pat" 2>/dev/null || true)"; \
	 if [ -n "$$pids" ]; then \
	   echo "   ⚠ celery [$(1)] — matando $$(echo $$pids | tr '\n' ' ')…"; \
	   echo "$$pids" | xargs kill 2>/dev/null || true; \
	   for i in 1 2 3 4 5 6 7 8 9 10; do pgrep -f "$$pat" >/dev/null 2>&1 || break; sleep 0.2; done; \
	   strag="$$(pgrep -f "$$pat" 2>/dev/null || true)"; \
	   [ -n "$$strag" ] && echo "$$strag" | xargs kill -9 2>/dev/null || true; \
	   echo "   ✓ celery [$(1)] parado"; \
	 fi
endef

# Variante HOST-WIDE explícita: mata TODO worker celery do host, inclusive de
# outros worktrees. Só é chamada pelo recover com FORCE=host, e avisa alto.
define kill_celery_hostwide
	@pids="$$(pgrep -f 'celery -A backend.app.worker worker' 2>/dev/null || true)"; \
	 if [ -n "$$pids" ]; then \
	   echo "   ⚠ HOST-WIDE: matando TODOS os workers celery do host (inclui OUTROS worktrees): $$(echo $$pids | tr '\n' ' ')"; \
	   echo "$$pids" | xargs kill 2>/dev/null || true; \
	   for i in 1 2 3 4 5 6 7 8 9 10; do pgrep -f 'celery -A backend.app.worker worker' >/dev/null 2>&1 || break; sleep 0.2; done; \
	   strag="$$(pgrep -f 'celery -A backend.app.worker worker' 2>/dev/null || true)"; \
	   [ -n "$$strag" ] && echo "$$strag" | xargs kill -9 2>/dev/null || true; \
	   echo "   ✓ celery host-wide parado"; \
	 fi
endef

# Sweep de UMA porta $(1) — mata o listener SÓ se ele pertence a este clone
# (cwd sob $(CURDIR)) ou se FORCE=host. Porta é recurso global do host: sem o
# cwd-check, um recover num worktree derrubaria a stack de outro clone (ou do
# repo principal). Preserva-e-avisa o que for de fora. Idempotente, nunca aborta.
define sweep_port_clone
	@pid="$$(lsof -ti tcp:$(1) -sTCP:LISTEN 2>/dev/null | head -1 || true)"; \
	 if [ -n "$$pid" ]; then \
	   cwd="$$(lsof -a -p $$pid -d cwd -Fn 2>/dev/null | awk '/^n/{print substr($$0,2); exit}')"; \
	   cmd="$$(ps -p $$pid -o comm= 2>/dev/null | head -1 || echo '?')"; \
	   case "$$cwd/" in "$(CURDIR)/"*) mine=1 ;; *) mine=0 ;; esac; \
	   if [ "$$mine" = "1" ] || [ "$(FORCE)" = "host" ]; then \
	     echo "   ✓ porta $(1) → kill $$pid ($$cmd)"; \
	     kill $$pid 2>/dev/null || true; \
	     for i in 1 2 3 4 5; do kill -0 $$pid 2>/dev/null || break; sleep 0.2; done; \
	     kill -0 $$pid 2>/dev/null && kill -9 $$pid 2>/dev/null || true; \
	   else \
	     echo "   · porta $(1) ocupada por pid $$pid ($$cmd) de OUTRO clone (cwd=$${cwd:-?}) — preservado. FORCE=host p/ matar."; \
	   fi; \
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
# Atalhos e recuperação  ·  🆘 Travado? → make recover
#
# Atalhos de topo (sem prefixo) apontam para a stack nativa (o caminho padrão
# de dev). `status` e `recover` valem para QUALQUER stack deste clone.
# ---------------------------------------------------------------------------

.PHONY: up down logs status recover _recover-celery-hostwide

## up: Atalho → make native-up (sobe a stack nativa)
up: native-up

## down: Atalho → make native-down (para a stack nativa, inclui overlay Go :8002)
down: native-down

## logs: Atalho → make native-logs (SVC=<nome> para um só)
logs: native-logs

## status: 🔎 O que roda NESTE clone (read-only) — serviços nativos + overlay Go :8002 + smoke + órfãos de porta + celery
status:
	@printf "%-16s  %-7s  %-5s  %s\n" "Serviço" "PID" "Porta" "Status"
	@printf "%-16s  %-7s  %-5s  %s\n" "────────────────" "───────" "─────" "──────────────────────"
	@for row in "api:api:$(PORT_API):$(DEV_DIR)" "worker:worker::$(DEV_DIR)" "frontend:frontend:$(PORT_FRONTEND):$(DEV_DIR)" "ops-api:ops-api:$(PORT_OPS_API):$(DEV_DIR)" "frontend-ops:frontend-ops:$(PORT_FRONTEND_OPS):$(DEV_DIR)" "go-shell:go:$(PORT_GO):$(DEV_DIR)"; do \
	   label=$${row%%:*}; r1=$${row#*:}; pn=$${r1%%:*}; r2=$${r1#*:}; port=$${r2%%:*}; dir=$${r2#*:}; \
	   pidfile=$(CURDIR)/$$dir/$$pn.pid; \
	   if [ -f $$pidfile ]; then \
	     pid=$$(cat $$pidfile 2>/dev/null); \
	     if [ -n "$$pid" ] && kill -0 $$pid 2>/dev/null; then \
	       if [ -n "$$port" ]; then \
	         if lsof -nP -iTCP:$$port -sTCP:LISTEN >/dev/null 2>&1; then st="✅ OK"; else st="⏳ subindo (porta não listening)"; fi; \
	       else st="✅ OK (sem porta)"; fi; \
	       printf "%-16s  %-7s  %-5s  %s\n" "$$label" "$$pid" "$${port:-—}" "$$st"; \
	     else \
	       printf "%-16s  %-7s  %-5s  %s\n" "$$label" "$$pid" "$${port:-—}" "❌ PID morto (stale — make recover)"; \
	     fi; \
	   else \
	     printf "%-16s  %-7s  %-5s  %s\n" "$$label" "—" "$${port:-—}" "⚪ não subido"; \
	   fi; \
	 done
	@if [ -d $(CURDIR)/$(SMOKE_DIR) ] && ls $(CURDIR)/$(SMOKE_DIR)/*.pid >/dev/null 2>&1; then \
	   echo "  — smoke ($(SMOKE_DIR)):"; \
	   for pn in api worker frontend go; do \
	     pf=$(CURDIR)/$(SMOKE_DIR)/$$pn.pid; [ -f $$pf ] || continue; \
	     pid=$$(cat $$pf 2>/dev/null); \
	     if [ -n "$$pid" ] && kill -0 $$pid 2>/dev/null; then st="✅"; else st="❌ morto"; fi; \
	     printf "     %-12s %-7s %s\n" "$$pn" "$${pid:-—}" "$$st"; \
	   done; \
	 fi
	@echo "  — portas ($(ALL_LOCAL_PORTS)) · órfãos = listener sem pidfile deste clone:"; \
	 found=0; \
	 for p in $(ALL_LOCAL_PORTS); do \
	   pid=$$(lsof -ti tcp:$$p -sTCP:LISTEN 2>/dev/null | head -1 || true); \
	   [ -z "$$pid" ] && continue; \
	   tracked=0; \
	   for pf in $(CURDIR)/$(DEV_DIR)/*.pid $(CURDIR)/$(SMOKE_DIR)/*.pid; do \
	     [ -f "$$pf" ] || continue; [ "$$(cat $$pf 2>/dev/null)" = "$$pid" ] && tracked=1; \
	   done; \
	   [ $$tracked -eq 1 ] && continue; \
	   cwd=$$(lsof -a -p $$pid -d cwd -Fn 2>/dev/null | awk '/^n/{print substr($$0,2); exit}'); \
	   cmd=$$(ps -p $$pid -o comm= 2>/dev/null | head -1 || echo '?'); \
	   case "$$cwd/" in "$(CURDIR)/"*) echo "     ⚠ :$$p pid $$pid ($$cmd) órfão DESTE clone — make recover" ;; *) echo "     · :$$p pid $$pid ($$cmd) de OUTRO clone (cwd=$${cwd:-?})" ;; esac; \
	   found=1; \
	 done; \
	 [ $$found -eq 0 ] && echo "     · nenhum órfão" || true
	@mine=$$( { pgrep -f "celery -A backend.app.worker worker.*--hostname=celery-(native|smoke)(-go)?-$(WT)@" 2>/dev/null || true; } | tr '\n' ' '); \
	 total=$$( { pgrep -f 'celery -A backend.app.worker worker' 2>/dev/null || true; } | wc -l | tr -d ' '); \
	 echo "  — celery: deste worktree [$${mine:-nenhum}] · total no host: $$total"
	@if redis-cli ping >/dev/null 2>&1; then echo "  — redis: ✅ OK (6379)"; else echo "  — redis: ❌ não responde (6379)"; fi

## recover: 🆘 Destrava ESTE clone — para nativo+smoke+go, reap pids, varre portas, remove _*_pids. Idempotente, nunca crasha.
##          Só toca processos deste clone (cwd sob a raiz). FORCE=host mata de QUALQUER clone/worktree.
recover:
	@echo "▶  recover — destravando o clone '$(WT)'…"
	@[ "$(FORCE)" = "host" ] && echo "   ⚠ FORCE=host — vai matar processos de QUALQUER clone/worktree do host." || true
	$(call kill_pid_safe,go(dev) :8002,$(CURDIR)/$(DEV_DIR)/go.pid)
	$(call kill_pid_safe,go(smoke) :8002,$(CURDIR)/$(SMOKE_DIR)/go.pid)
	$(call kill_pid_safe,api(dev),$(CURDIR)/$(DEV_DIR)/api.pid)
	$(call kill_pid_safe,worker(dev),$(CURDIR)/$(DEV_DIR)/worker.pid)
	$(call kill_pid_safe,frontend(dev),$(CURDIR)/$(DEV_DIR)/frontend.pid)
	$(call kill_pid_safe,ops-api(dev),$(CURDIR)/$(DEV_DIR)/ops-api.pid)
	$(call kill_pid_safe,frontend-ops(dev),$(CURDIR)/$(DEV_DIR)/frontend-ops.pid)
	$(call kill_pid_safe,api(smoke),$(CURDIR)/$(SMOKE_DIR)/api.pid)
	$(call kill_pid_safe,worker(smoke),$(CURDIR)/$(SMOKE_DIR)/worker.pid)
	$(call kill_pid_safe,frontend(smoke),$(CURDIR)/$(SMOKE_DIR)/frontend.pid)
	$(call kill_celery_scoped,celery-(native|smoke)(-go)?-$(WT))
	@[ "$(FORCE)" = "host" ] && $(MAKE) -s _recover-celery-hostwide || true
	$(call sweep_port_clone,$(PORT_API))
	$(call sweep_port_clone,$(PORT_OPS_API))
	$(call sweep_port_clone,$(PORT_GO))
	$(call sweep_port_clone,$(PORT_FRONTEND))
	$(call sweep_port_clone,$(PORT_FRONTEND_OPS))
	@for d in frontend frontend-ops; do \
	   lock=$(CURDIR)/$$d/.next/dev/lock; \
	   if [ -f $$lock ]; then \
	     pid=$$(python3 -c "import json;print(json.load(open('$$lock')).get('pid',''))" 2>/dev/null || true); \
	     if [ -z "$$pid" ] || ! kill -0 $$pid 2>/dev/null; then rm -f $$lock && echo "   ✓ $$d/.next/dev/lock órfão removido" || true; fi; \
	   fi; \
	 done
	$(call kill_pid_safe,redis(dev),$(CURDIR)/$(DEV_DIR)/redis.pid)
	@rm -rf $(CURDIR)/$(DEV_DIR) $(CURDIR)/$(SMOKE_DIR)
	@echo "  ✅ recover completo — clone '$(WT)' limpo. 'make status' confirma."
	@echo "     Redis próprio (subido por native-up) parado; redis externo/compartilhado preservado. Dados intactos."
	@echo "     Subir de novo: make native-up  ·  make smoke-up"

.PHONY: _recover-celery-hostwide
_recover-celery-hostwide:
	$(call kill_celery_hostwide)

# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

.PHONY: smoke-up smoke-down smoke-restart smoke-status smoke-reset smoke-seed smoke-logs smoke-dirs smoke-pipeline-service smoke-pipeline-service-down

## smoke-pipeline-service: builda+sobe o container e roda o gate ADR-303 (requer 'make smoke-up' antes)
smoke-pipeline-service:
	@test -f $(CURDIR)/$(SMOKE_DIR)/fernet.key || { echo "❌ $(SMOKE_DIR)/fernet.key ausente. Rode 'make smoke-up' antes."; exit 1; }
	@SMOKE_FERNET_KEY="$$(cat $(CURDIR)/$(SMOKE_DIR)/fernet.key)" \
	 docker compose -f docker-compose.smoke.yml -f docker-compose.pipeline-service.yml up -d --build --wait pipeline-service
	@$(VENV)/python dev/smoke_pipeline_service_container.py

## smoke-pipeline-service-down: derruba só o container do pipeline-service
smoke-pipeline-service-down:
	@docker compose -f docker-compose.smoke.yml -f docker-compose.pipeline-service.yml rm -sf pipeline-service

## smoke-up: Sobe Redis + backend + Celery worker + frontend em background
smoke-up: smoke-dirs
	@echo "▶  Verificando portas…"
	$(call check_port_free,$(PORT_API))
	$(call check_port_free,$(PORT_FRONTEND))
	@echo "▶  Starting Redis (docker compose)…"
	@if docker container inspect mathoms-smoke-redis >/dev/null 2>&1 && \
	   [ "$$(docker container inspect -f '{{.State.Running}}' mathoms-smoke-redis)" = "false" ]; then \
	   echo "   ⚠ removendo container stale mathoms-smoke-redis (parado, de projeto compose anterior)"; \
	   docker rm mathoms-smoke-redis >/dev/null; \
	 fi
	@# --force-recreate garante que um container mathoms-smoke-redis pré-6380
	@# (rodando com o binding host 6379 antigo) seja recriado com a porta nova —
	@# sem isto o compose reusaria o container por nome e o fix não pegaria até
	@# um smoke-down. Redis do smoke é efêmero (sem volume), recriar não perde nada.
	@docker compose -f docker-compose.smoke.yml up -d --wait --force-recreate
	@echo "▶  Aplicando migrations no smoke DB…"
	@MATHOMS_DATABASE_URL="sqlite+aiosqlite:///$(CURDIR)/$(SMOKE_DB)" \
	 $(ALEMBIC) upgrade head
	@echo "▶  Starting backend API (porta $(PORT_API))…"
	@FERNET_KEY="$(ephemeral_fernet)"; \
	 MATHOMS_DATABASE_URL="sqlite+aiosqlite:///$(CURDIR)/$(SMOKE_DB)" \
	 MATHOMS_STORAGE_ROOT="$(CURDIR)/$(SMOKE_STORAGE)" \
	 MATHOMS_REDIS_URL="redis://localhost:$(MATHOMS_SMOKE_REDIS_PORT)/0" \
	 MATHOMS_FERNET_KEY="$$FERNET_KEY" \
	 nohup $(VENV)/uvicorn backend.app.main:app \
	   --host 0.0.0.0 --port $(PORT_API) --reload \
	   > $(CURDIR)/$(SMOKE_DIR)/api.log 2>&1 & echo $$! > $(CURDIR)/$(SMOKE_DIR)/api.pid; \
	 echo "$$FERNET_KEY" > $(CURDIR)/$(SMOKE_DIR)/fernet.key
	@echo "▶  Starting Celery worker…"
	$(call kill_celery_scoped,celery-smoke(-go)?-$(WT))
	@TS=$$(date +%s); \
	 FERNET_KEY="$$(cat $(CURDIR)/$(SMOKE_DIR)/fernet.key)"; \
	 MATHOMS_DATABASE_URL="sqlite+aiosqlite:///$(CURDIR)/$(SMOKE_DB)" \
	 MATHOMS_STORAGE_ROOT="$(CURDIR)/$(SMOKE_STORAGE)" \
	 MATHOMS_REDIS_URL="redis://localhost:$(MATHOMS_SMOKE_REDIS_PORT)/0" \
	 MATHOMS_FERNET_KEY="$$FERNET_KEY" \
	 nohup $(VENV)/celery -A backend.app.worker worker \
	   --hostname="celery-smoke-$(WT)@%h-$$TS" \
	   --max-tasks-per-child=200 \
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
	@echo "     Redis:    redis://localhost:$(MATHOMS_SMOKE_REDIS_PORT)/0  (isolado da stack nativa em 6379)"
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

## smoke-down: Para os processos do smoke + Redis do smoke (idempotente, inclui overlay Go :8002)
smoke-down:
	@echo "▶  Stopping smoke processes…"
	$(call kill_pid_safe,go-shell :8002,$(CURDIR)/$(SMOKE_DIR)/go.pid)
	$(call kill_pid_safe,api,$(CURDIR)/$(SMOKE_DIR)/api.pid)
	$(call kill_pid_safe,worker,$(CURDIR)/$(SMOKE_DIR)/worker.pid)
	$(call kill_celery_scoped,celery-smoke(-go)?-$(WT))
	$(call kill_pid_safe,frontend,$(CURDIR)/$(SMOKE_DIR)/frontend.pid)
	@echo "▶  Stopping Redis (smoke, porta $(MATHOMS_SMOKE_REDIS_PORT))…"
	@docker compose -f docker-compose.smoke.yml down 2>/dev/null || echo "   · redis do smoke já parado / compose indisponível"
	@echo "  ✅ Smoke stack stopped."
	@echo "     (Redis do smoke roda na porta $(MATHOMS_SMOKE_REDIS_PORT), isolada do redis"
	@echo "      nativo da stack dev em 6379 — este 'smoke-down' não afeta uma 'dev-up'.)"

## smoke-restart: smoke-down && smoke-up (reseed com make smoke-seed)
smoke-restart: smoke-down smoke-up

## smoke-status: Visão do que roda (alias de status — a visão unificada já cobre nativo + smoke + go)
smoke-status: status

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
# Stack Docker (docker-compose.dev.yml · A20.L6/L7 · ADR-252)
#
# Caminho RECOMENDADO de onboarding: um comando sobe a stack inteira em
# containers (postgres + 2 redis + api + worker + beat + frontend), com
# hot-reload e seed automático. Paridade dev↔prod. Não usa .venv local.
#
# Sufixo `-docker` distingue da stack uvicorn-local legada (dev-up/dev-down/
# dev-logs sem sufixo). As duas COEXISTEM: a stack Docker publica numa banda de
# portas distinta (8010/3010/5433/3110) da legada (8000/8001/3000/3100), então
# rodar ambas ao mesmo tempo não colide. Override via MATHOMS_DOCKER_*_PORT.
# ---------------------------------------------------------------------------

COMPOSE_DEV := docker-compose.dev.yml

.PHONY: docker-up docker-down docker-restart docker-status docker-reset docker-shell \
        docker-build docker-logs \
        dev-up-docker dev-down-docker dev-reset-docker dev-shell-docker \
        dev-rebuild-docker dev-logs-docker

## docker-up: Sobe a stack dev em Docker (API 8010/Front 3010/PG 5433 — coexiste com a nativa). Onboarding em 1 comando.
docker-up:
	@echo "▶  Verificando portas publicadas ($(MATHOMS_DOCKER_API_PORT), $(MATHOMS_DOCKER_FRONTEND_PORT))…"
	$(call check_port_free,$(MATHOMS_DOCKER_API_PORT))
	$(call check_port_free,$(MATHOMS_DOCKER_FRONTEND_PORT))
	@echo "▶  Subindo stack ($(COMPOSE_DEV))…"
	@docker compose -f $(COMPOSE_DEV) up -d --build
	@echo ""
	@echo "  ✅ Stack dev (Docker) subindo. Boot leva ~60s (build + migrate + seed):"
	@echo "     API:      http://localhost:$(MATHOMS_DOCKER_API_PORT)/health"
	@echo "     Frontend: http://localhost:$(MATHOMS_DOCKER_FRONTEND_PORT)"
	@echo "     Postgres: 127.0.0.1:$(MATHOMS_DOCKER_POSTGRES_PORT)  (coexiste com a stack nativa)"
	@echo "     Logs:     make docker-logs   (SVC=api para um só)"
	@echo "     Shell:    make docker-shell"

## docker-down: Para a stack Docker, PRESERVA volumes (DB/Redis/storage intactos)
docker-down:
	@echo "▶  Parando stack ($(COMPOSE_DEV)) — volumes preservados…"
	@docker compose -f $(COMPOSE_DEV) down
	@echo "  ✅ Stack parada. 'make docker-up' para subir de novo (dados mantidos)."

## docker-restart: docker-down && docker-up
docker-restart: docker-down docker-up

## docker-status: docker compose ps da stack Docker
docker-status:
	@docker compose -f $(COMPOSE_DEV) ps

## docker-reset: DESTRUTIVO — para a stack e APAGA volumes (wipe DB/Redis/storage)
docker-reset:
	@echo "⚠️  DESTRUTIVO: vai apagar DB, Redis e storage da stack dev Docker."
	@docker compose -f $(COMPOSE_DEV) down -v
	@echo "  ✅ Volumes apagados. 'make docker-up' reinicia do zero (re-seed)."

## docker-shell: Shell (bash) dentro do container api
docker-shell:
	@docker compose -f $(COMPOSE_DEV) exec api bash

## docker-build: Rebuild das imagens após mudança em deps/Dockerfile (sem subir)
docker-build:
	@echo "▶  Rebuild das imagens ($(COMPOSE_DEV))…"
	@docker compose -f $(COMPOSE_DEV) build
	@echo "  ✅ Imagens rebuildadas. 'make docker-up' aplica."

## docker-logs: tail -f dos logs da stack Docker (SVC=<nome> para um só)
docker-logs:
	@if [ -n "$(SVC)" ]; then \
	   docker compose -f $(COMPOSE_DEV) logs -f $(SVC); \
	 else \
	   docker compose -f $(COMPOSE_DEV) logs -f; \
	 fi

# ---------------------------------------------------------------------------
# Stack nativa (uvicorn-local)
#
# Sobe os 6 serviços de desenvolvimento local em background.
# Diferente de `smoke-*`, este preserva `.env` e `mathoms.db` reais.
# Verbo comum: native-<up|down|restart|status|logs>. Atalhos sem prefixo
# (make up/down/logs/status) apontam para cá. Nomes antigos dev-* seguem como
# aliases (ver seção "Aliases de compatibilidade" no fim do arquivo).
# Targets:
#   make dev-bootstrap        First-run: venv, deps, .env, codegen
#   make dev-pull             git pull --ff-only + npm install
#   make native-up            Sobe redis + api(8000) + worker + frontend(3000)
#                               + ops-api(8001) + frontend-ops(3100)
#   make native-down          Para todos os processos (inclui overlay Go :8002)
#   make native-restart       down && up
#   make native-restart-worker  Restart só do worker (após mudar pipeline/)
#   make native-fresh         Reset completo: recover + pull + clean + up + status
#   make status               ✅/❌ por serviço + órfãos de porta + celery (read-only)
#   make native-logs          tail -f de todos (SVC=api para um só)
#   make recover              🆘 destrava o clone (para tudo, reap pids, varre portas)
#   make native-reset-env     DESTRUTIVO: regenera .env (invalida Fernet)
#
# PIDs em _dev_pids/<svc>.pid · logs em _dev_pids/<svc>.log (no .gitignore)
# ---------------------------------------------------------------------------

.PHONY: dev-bootstrap dev-pull native-up native-down native-restart native-restart-worker \
        native-fresh status recover native-logs native-reset-env dev-dirs \
        dev-redis-up dev-api-up dev-worker-up dev-frontend-up \
        dev-ops-api-up dev-frontend-ops-up pipeline-run \
        up down logs panic reset-all dev-nuke kill-stale \
        dev-up dev-down dev-restart dev-restart-worker dev-fresh dev-status \
        dev-logs dev-reset-env dev-kill-stale

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
	   echo "      Detalhes: docs/reference/RUNBOOK.md §7.2."; \
	 fi
	@echo ""
	@echo "  ✅ Bootstrap completo. 'make up' (ou 'make native-up') para subir a stack."

## dev-pull: git pull --ff-only + npm install em ambos os frontends
dev-pull:
	@echo "▶  Verificando working tree…"
	@git update-index -q --refresh
	@if ! git diff --quiet || ! git diff --cached --quiet; then \
	   echo "   ❌ Working tree sujo. Commit ou stash antes."; \
	   exit 1; \
	 fi
	@echo "▶  git fetch --prune + git pull --ff-only…"
	@git fetch origin --prune
	@CURRENT_BRANCH=$$(git rev-parse --abbrev-ref HEAD); \
	 UPSTREAM_NAME=$$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true); \
	 if [ -z "$$UPSTREAM_NAME" ]; then \
	   case "$$CURRENT_BRANCH" in agent/*) \
	     echo "   ❌ Branch '$$CURRENT_BRANCH' sem upstream remoto."; \
	     echo "      Provavelmente uma branch agent/* cuja PR já foi mergeada e"; \
	     echo "      auto-deletada no GitHub. Limpe e volte para main:"; \
	     echo ""; \
	     echo "        git checkout main && git pull --ff-only \\"; \
	     echo "          && git branch -D $$CURRENT_BRANCH"; \
	     echo ""; \
	     exit 1 ;; \
	   esac; \
	   echo "   ⚠️  '$$CURRENT_BRANCH' sem upstream — pulando pull."; \
	 elif ! git rev-parse --verify --quiet "$$UPSTREAM_NAME" >/dev/null; then \
	   echo "   ❌ Upstream '$$UPSTREAM_NAME' não existe mais (branch deletada no remoto)."; \
	   echo "      Provavelmente PR mergeada (squash) e branch auto-deletada."; \
	   echo "      Limpe e volte para main:"; \
	   echo ""; \
	   echo "        git checkout main && git pull --ff-only \\"; \
	   echo "          && git branch -D $$CURRENT_BRANCH"; \
	   echo ""; \
	   exit 1; \
	 else \
	   git pull --ff-only; \
	 fi
	@echo "▶  npm install (frontend + frontend-ops)…"
	@npm --prefix frontend install --silent
	@npm --prefix frontend-ops install --silent
	@echo "  ✅ Pull completo. 'make native-restart' para reiniciar serviços."

## native-up: Sobe os 6 serviços nativos (uvicorn-local) em background — migrate roda antes p/ evitar drift
native-up: dev-dirs migrate dev-redis-up dev-api-up dev-worker-up dev-frontend-up dev-ops-api-up dev-frontend-ops-up
	@echo ""
	@echo "  ✅ Stack nativa subida (6 serviços):"
	@echo "     Redis:        redis://localhost:6379/0"
	@echo "     API:          http://localhost:$(PORT_API)"
	@echo "     Worker:       celery (concurrency=2)"
	@echo "     Frontend:     http://localhost:$(PORT_FRONTEND)"
	@echo "     Ops API:      http://127.0.0.1:$(PORT_OPS_API)/admin/*"
	@echo "     Frontend-ops: http://127.0.0.1:$(PORT_FRONTEND_OPS)/login"
	@echo ""
	@echo "  Logs em $(DEV_DIR)/<svc>.log · 'make status' · 'make native-logs'"

# Reusa qualquer redis já ouvindo em 6379 (idempotência do onboarding). O guard
# abaixo é um detector TRANSITÓRIO: avisa se o 6379 for o container do smoke
# pré-migração-6380 (que 'smoke-down' derrubaria, deixando o worker nativo sem
# broker em silêncio). Pode ser removido após 1-2 ciclos, quando não houver mais
# container smoke stale publicando 6379.
dev-redis-up: dev-dirs
	@if redis-cli ping >/dev/null 2>&1; then \
	   if command -v docker >/dev/null 2>&1 && \
	      [ -n "$$(docker ps --format '{{.Names}}' --filter name=mathoms-smoke-redis --filter publish=6379 2>/dev/null)" ]; then \
	     echo "   ⚠ 6379 está sendo servido pelo container do smoke (mathoms-smoke-redis)."; \
	     echo "     A stack nativa NÃO deve reusá-lo — 'make smoke-down' o derrubaria e o"; \
	     echo "     worker nativo perderia o broker em silêncio. O smoke agora usa a porta"; \
	     echo "     $(MATHOMS_SMOKE_REDIS_PORT); recrie-o com 'make smoke-down && make smoke-up'."; \
	   fi; \
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
	@echo "▶  Subindo Celery worker nativo (concurrency=2, max-tasks-per-child=200)…"
	$(call kill_celery_scoped,celery-native(-go)?-$(WT))
	@TS=$$(date +%s); \
	 nohup $(VENV)/celery -A backend.app.worker worker \
	   --hostname="celery-native-$(WT)@%h-$$TS" \
	   --max-tasks-per-child=200 \
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

## native-down: Para a stack nativa via PID files (SIGTERM→SIGKILL) — inclui o overlay Go :8002 e redis próprio
native-down:
	@echo "▶  Parando a stack nativa ($(WT))…"
	$(call kill_pid_safe,go-shell :8002,$(CURDIR)/$(DEV_DIR)/go.pid)
	$(call kill_pid_safe,api,$(CURDIR)/$(DEV_DIR)/api.pid)
	$(call kill_pid_safe,worker,$(CURDIR)/$(DEV_DIR)/worker.pid)
	$(call kill_celery_scoped,celery-native(-go)?-$(WT))
	$(call kill_pid_safe,frontend,$(CURDIR)/$(DEV_DIR)/frontend.pid)
	$(call kill_pid_safe,ops-api,$(CURDIR)/$(DEV_DIR)/ops-api.pid)
	$(call kill_pid_safe,frontend-ops,$(CURDIR)/$(DEV_DIR)/frontend-ops.pid)
	@if [ -f $(CURDIR)/$(DEV_DIR)/redis.pid ]; then \
	   $(MAKE) -s _kill_redis_pidfile; \
	 else \
	   echo "   · redis não foi subido por native-up (preservado)"; \
	 fi
	@echo "  ✅ Stack nativa parada."

# Privado: kill do redis nativo via pidfile, com a mesma escalação
.PHONY: _kill_redis_pidfile
_kill_redis_pidfile:
	$(call kill_pid_safe,redis,$(CURDIR)/$(DEV_DIR)/redis.pid)

## native-restart: native-down && native-up
native-restart: native-down native-up

## native-restart-worker: Restart só do worker nativo (após mudar pipeline/ ou tasks/)
native-restart-worker:
	$(call kill_pid_safe,worker,$(CURDIR)/$(DEV_DIR)/worker.pid)
	$(call kill_celery_scoped,celery-native(-go)?-$(WT))
	@$(MAKE) -s dev-worker-up
	@echo "  ✅ Worker nativo reiniciado."

## native-fresh: Reset completo — recover + pull + clean + up + status ("fecha tudo, atualiza, limpa, sobe limpo")
##             Requer working tree limpo (validado em pre-flight antes de matar nada).
native-fresh: _dev-fresh-preflight recover dev-pull clean-all native-up
	@$(MAKE) -s status

# Privado: valida working tree limpo ANTES do recover.
# Sem isso, tree sujo abortaria no dev-pull com a stack já morta.
.PHONY: _dev-fresh-preflight
_dev-fresh-preflight:
	@echo "▶  Pre-flight (native-fresh): working tree…"
	@git update-index -q --refresh
	@if ! git diff --quiet || ! git diff --cached --quiet; then \
	   echo "   ❌ Working tree sujo. Commit ou stash antes de rodar native-fresh."; \
	   echo "      (sem isso, recover derrubaria a stack e dev-pull abortaria,"; \
	   echo "       deixando você sem nada rodando.)"; \
	   exit 1; \
	 fi
	@echo "   ✓ Working tree limpo"
	@python3 dev/check_post_merge_cleanup.py

## stale-check: avisa se HEAD está em agent/* órfã (PR já mergeada / branch deletada)
.PHONY: stale-check
stale-check:
	@python3 dev/check_post_merge_cleanup.py

# status e recover são definidos na seção "Atalhos e recuperação" no topo do
# arquivo (para aparecerem cedo no `make help`). Os alvos native-* abaixo os
# consomem via prerequisite/$(MAKE).

## native-logs: tail -f de todos os logs da stack nativa (SVC=<nome> para um só)
native-logs:
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
	   echo "Nenhum log encontrado em $(DEV_DIR)/. Rode 'make native-up' primeiro."; \
	 else \
	   tail -f $$logs; \
	 fi
endif

## native-reset-env: DESTRUTIVO — regenera .env (INVALIDA Fernet → API keys LLM e dados encriptados quebram)
native-reset-env:
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

## pipeline-run: Reprocessa o pipeline de um workspace (WS=<uuid> [FROM=<stage>] [SKIP_LLM=0] [RESET=1] [YES=1]; sem WS lista)
pipeline-run:
	@ARGS=""; \
	 if [ -n "$(FROM)" ]; then ARGS="$$ARGS --from-stage $(FROM)"; fi; \
	 if [ "$(SKIP_LLM)" = "0" ]; then ARGS="$$ARGS --with-llm"; fi; \
	 if [ "$(RESET)" = "1" ]; then ARGS="$$ARGS --reset"; fi; \
	 if [ "$(YES)" = "1" ]; then ARGS="$$ARGS --yes"; fi; \
	 $(PYTHON) -m backend.app.scripts.run_workspace_pipeline $(WS) $$ARGS

# ---------------------------------------------------------------------------
# Tests, lint, format
#
# Pass-through: PYTEST_ARGS / RUFF_ARGS.
#   make test-pipeline PYTEST_ARGS="-x -k saldo"
#   make lint RUFF_ARGS="--statistics"
# ---------------------------------------------------------------------------

.PHONY: test test-all test-pipeline test-backend test-frontend test-e2e \
        lint lint-fix format precommit check-boundaries codex-check

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

## codex-check: Gate local para agentes antes de PR (sem E2E)
codex-check:
	@echo "▶  pre-commit — hooks locais e checks de docs/codegen"
	@$(MAKE) precommit
	@echo "▶  boundaries — pipeline sem imports de framework"
	@$(MAKE) check-boundaries
	@echo "▶  Python — pipeline + backend"
	@$(MAKE) test-all
	@echo "▶  Frontend — Vitest unit"
	@$(MAKE) test-frontend
	@echo "▶  Go — no-op enquanto não houver go.work/.go"
	@$(MAKE) go-test
	@echo "✅ codex-check verde."

# ---------------------------------------------------------------------------
# Codegen / snapshots (commitar diff após rodar)
# ---------------------------------------------------------------------------

.PHONY: update-openapi-snapshot update-pipeline-service-openapi update-db-schema-reference

## update-openapi-snapshot: Regenera docs/reference/api/v1/openapi.json (A6f.2 · ADR-102)
update-openapi-snapshot: update-pipeline-service-openapi
	@mkdir -p docs/reference/api/v1
	@FERNET_KEY="$${MATHOMS_FERNET_KEY:-$(ephemeral_fernet)}"; \
	 out=docs/reference/api/v1/openapi.json; tmp=$$(mktemp); \
	 MATHOMS_FERNET_KEY="$$FERNET_KEY" \
	 $(PYTHON) -c 'import json; from backend.app.main import app; \
	   print(json.dumps(app.openapi(), indent=2, sort_keys=True))' \
	 > "$$tmp" && mv "$$tmp" "$$out" || { rm -f "$$tmp"; exit 1; }
	@echo "✓ docs/reference/api/v1/openapi.json regenerado. Comite o diff."

## update-pipeline-service-openapi: Regenera docs/reference/api/v1/pipeline-service.openapi.json (A6f.1 · ADR-112)
update-pipeline-service-openapi:
	@mkdir -p docs/reference/api/v1
	@out=docs/reference/api/v1/pipeline-service.openapi.json; tmp=$$(mktemp); \
	 PYTHONPATH="$(CURDIR)/pipeline-service:$(CURDIR)" \
	 $(PYTHON) -c 'import json; from app.main import create_app; \
	   print(json.dumps(create_app().openapi(), indent=2, sort_keys=True))' \
	 > "$$tmp" && mv "$$tmp" "$$out" || { rm -f "$$tmp"; exit 1; }
	@echo "✓ docs/reference/api/v1/pipeline-service.openapi.json regenerado. Comite o diff."

## update-db-schema-reference: Regenera docs/reference/DB_SCHEMA_REFERENCE.md (A6f.4 · ADR-102 R20)
update-db-schema-reference:
	@FERNET_KEY="$${MATHOMS_FERNET_KEY:-$(ephemeral_fernet)}"; \
	 out=docs/reference/DB_SCHEMA_REFERENCE.md; tmp=$$(mktemp); \
	 MATHOMS_FERNET_KEY="$$FERNET_KEY" \
	 $(PYTHON) dev/generate_db_schema_reference.py > "$$tmp" \
	 && mv "$$tmp" "$$out" || { rm -f "$$tmp"; exit 1; }
	@echo "✓ docs/reference/DB_SCHEMA_REFERENCE.md regenerado. Comite o diff."

# ---------------------------------------------------------------------------
# Go (A6g.7 — ADR-113)
#
# No-op enquanto não há .go no repo. Quando o primeiro serviço entrar em
# services/<name>/ com go.mod próprio + use directive em go.work, os
# targets executam normalmente. CI (.github/workflows/go.yml) gatilha
# via hashFiles('**/*.go').
# ---------------------------------------------------------------------------

.PHONY: go-fmt go-lint go-test go-all

GO_FILES = $(shell find . \
	-path ./node_modules -prune -o \
	-path ./.git -prune -o \
	-path ./.claude -prune -o \
	-path ./.codex -prune -o \
	-path ./.venv -prune -o \
	-path './*/.venv' -prune -o \
	-path './*/node_modules' -prune -o \
	-path './*/.next' -prune -o \
	-path ./storage -prune -o \
	-path ./_scratch -prune -o \
	-path ./_archive -prune -o \
	-type f -name '*.go' -print 2>/dev/null)

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
	   for d in $$(go list -m -f '{{.Dir}}'); do \
	     (cd $$d && golangci-lint run --timeout=3m ./...) || exit 1; \
	   done; \
	 fi

## go-test: go test ./... (no-op se não houver .go) — pass-through GO_TEST_ARGS
go-test:
	@if [ ! -f go.work ] || [ -z "$(GO_FILES)" ]; then \
	   echo "go-test: sem go.work ou .go presentes (skip)"; \
	 else \
	   for d in $$(go list -m -f '{{.Dir}}'); do \
	     (cd $$d && go test ./... $(GO_TEST_ARGS)) || exit 1; \
	   done; \
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

## clean-all: recover (PARA os processos deste clone) + clean + remove storage smoke, _scratch e .next
##            Seguro: para tudo ANTES de apagar pids — nunca orfana (era o bug do clean-all antigo).
##            NÃO toca .venv, node_modules, .env, mathoms.db.
clean-all: recover clean
	@rm -rf $(SMOKE_STORAGE) _scratch
	@rm -rf frontend/.next frontend-ops/.next
	@echo "  ✅ Estado runtime local limpo — processos parados (recover) + caches + storage smoke + .next."
	@echo "     Preservados: .venv, node_modules, .env, mathoms.db."

# ---------------------------------------------------------------------------
# Overlay Go (dogfood do shell Go :8002 — F2 GO_SHELL, validação pré-cutover, ADR-150 §7)
#
# O shell Go NÃO é uma stack própria: é um OVERLAY de executor sobre uma stack
# já rodando (nativa OU smoke). Por isso a interface é go-on/go-off com ENV=
# OBRIGATÓRIO — sem default. O ambiente (que era o eixo confuso dos antigos
# dogfood-go vs dogfood-go-dev) fica explícito no call-site.
#
#   make go-on  ENV=smoke    (sobre a stack smoke — requer 'make smoke-up' antes)
#   make go-on  ENV=native   (sobre a stack nativa real — requer .env)
#   make go-off ENV=smoke | ENV=native
#
# Nota: :8002 é uma porta única compartilhada pelos dois ENV — rode o overlay
# em UM ambiente por vez. 'make recover' reapea o :8002 em qualquer caso.
# ---------------------------------------------------------------------------

.PHONY: go-on go-off _go-on-smoke _go-on-native _go-off-smoke _go-off-native \
        dogfood-go dogfood-go-off dogfood-go-dev dogfood-go-dev-off

## go-on: Liga o overlay Go (:8002) sobre a stack ENV — ENV=native|smoke (obrigatório)
go-on:
	@case "$(ENV)" in \
	   native) $(MAKE) -s _go-on-native ;; \
	   smoke)  $(MAKE) -s _go-on-smoke ;; \
	   "")     echo "❌ ENV= obrigatório. Uso: make go-on ENV=native  |  make go-on ENV=smoke"; exit 2 ;; \
	   *)      echo "❌ ENV='$(ENV)' inválido — use native ou smoke"; exit 2 ;; \
	 esac

## go-off: Desliga o overlay Go e volta o worker ENV ao executor Python — ENV=native|smoke (obrigatório)
##         Sem sessão/overlay ativo: diz "nada a desligar" e sai 0 (idempotente, nunca crasha).
go-off:
	@case "$(ENV)" in \
	   native) if [ -f "$(CURDIR)/$(DEV_DIR)/go.pid" ]; then $(MAKE) -s _go-off-native; else echo "  · overlay Go não está ligado no nativo — nada a desligar."; fi ;; \
	   smoke)  if [ -f "$(CURDIR)/$(SMOKE_DIR)/go.pid" ]; then $(MAKE) -s _go-off-smoke; else echo "  · overlay Go não está ligado no smoke — nada a desligar."; fi ;; \
	   "")     echo "❌ ENV= obrigatório. Uso: make go-off ENV=native  |  make go-off ENV=smoke"; exit 2 ;; \
	   *)      echo "❌ ENV='$(ENV)' inválido — use native ou smoke"; exit 2 ;; \
	 esac

_go-on-smoke:
	@test -f $(CURDIR)/$(SMOKE_DIR)/fernet.key || { echo "❌ Sessão smoke ausente. Rode 'make smoke-up' antes (fernet key + DB + worker)."; exit 1; }
	@echo "▶  Buildando o shell Go…"
	@mkdir -p $(CURDIR)/$(SMOKE_DIR)
	@cd services/pipeline-service-go && go build -o $(CURDIR)/$(SMOKE_DIR)/pipeline-service-go ./cmd/pipeline-service
	$(call kill_pid_safe,go-shell :8002,$(CURDIR)/$(SMOKE_DIR)/go.pid)
	$(call check_port_free,$(PORT_GO))
	@echo "▶  Subindo shell Go na :$(PORT_GO)…"
	@FERNET_KEY="$$(cat $(CURDIR)/$(SMOKE_DIR)/fernet.key)"; \
	 [ -n "$${ANTHROPIC_API_KEY:-}" ] || echo "   ⚠ ANTHROPIC_API_KEY ausente — stages LLM vão falhar (export antes, ou rode com skip de LLM)"; \
	 MATHOMS_DATABASE_URL="sqlite+aiosqlite:///$(CURDIR)/$(SMOKE_DB)" \
	 MATHOMS_STORAGE_ROOT="$(CURDIR)/$(SMOKE_STORAGE)" \
	 MATHOMS_REDIS_URL="redis://localhost:$(MATHOMS_SMOKE_REDIS_PORT)/0" \
	 MATHOMS_FERNET_KEY="$$FERNET_KEY" \
	 MATHOMS_REPO_ROOT="$(CURDIR)" \
	 MATHOMS_PYTHON="$(PYTHON)" \
	 REDIS_URL="redis://localhost:$(MATHOMS_SMOKE_REDIS_PORT)/0" \
	 PIPELINE_SERVICE_PORT=$(PORT_GO) \
	 nohup $(CURDIR)/$(SMOKE_DIR)/pipeline-service-go \
	   > $(CURDIR)/$(SMOKE_DIR)/go.log 2>&1 & echo $$! > $(CURDIR)/$(SMOKE_DIR)/go.pid
	@sleep 1; curl -sf --max-time 5 http://localhost:$(PORT_GO)/health > /dev/null \
	  && echo "   ✓ shell Go saudável em http://localhost:$(PORT_GO)" \
	  || { echo "   ❌ /health falhou — veja $(SMOKE_DIR)/go.log"; exit 1; }
	@echo "▶  Re-apontando o worker Celery (smoke) para o shell Go…"
	$(call kill_pid_safe,worker,$(CURDIR)/$(SMOKE_DIR)/worker.pid)
	$(call kill_celery_scoped,celery-smoke(-go)?-$(WT))
	@TS=$$(date +%s); \
	 FERNET_KEY="$$(cat $(CURDIR)/$(SMOKE_DIR)/fernet.key)"; \
	 MATHOMS_DATABASE_URL="sqlite+aiosqlite:///$(CURDIR)/$(SMOKE_DB)" \
	 MATHOMS_STORAGE_ROOT="$(CURDIR)/$(SMOKE_STORAGE)" \
	 MATHOMS_REDIS_URL="redis://localhost:$(MATHOMS_SMOKE_REDIS_PORT)/0" \
	 MATHOMS_FERNET_KEY="$$FERNET_KEY" \
	 MATHOMS_PIPELINE_SERVICE_URL="http://localhost:$(PORT_GO)" \
	 nohup $(VENV)/celery -A backend.app.worker worker \
	   --hostname="celery-smoke-go-$(WT)@%h-$$TS" \
	   --max-tasks-per-child=200 \
	   --loglevel=info --concurrency=2 \
	   > $(CURDIR)/$(SMOKE_DIR)/worker.log 2>&1 & echo $$! > $(CURDIR)/$(SMOKE_DIR)/worker.pid
	@echo ""
	@echo "  ✅ Overlay Go LIGADO no SMOKE — cada stage executa via shell Go (:$(PORT_GO))."
	@echo "     Rode o pipeline pela UI. Logs: $(SMOKE_DIR)/go.log + worker.log"
	@echo "     Voltar ao Python: make go-off ENV=smoke"

_go-on-native:
	@test -f $(CURDIR)/.env || { echo "❌ .env ausente na raiz — a stack nativa depende dele."; exit 1; }
	@echo "▶  Buildando o shell Go…"
	@mkdir -p $(CURDIR)/$(DEV_DIR)
	@cd services/pipeline-service-go && go build -o $(CURDIR)/$(DEV_DIR)/pipeline-service-go ./cmd/pipeline-service
	$(call kill_pid_safe,go-shell :8002,$(CURDIR)/$(DEV_DIR)/go.pid)
	$(call check_port_free,$(PORT_GO))
	@echo "▶  Subindo shell Go na :$(PORT_GO) (env mínimo — subprocess lê o .env sozinho)…"
	@# NÃO sourcear o .env pelo shell: aspas de valores JSON (ex. CORS_ORIGINS)
	@# são stripadas e o import do backend explode no subprocess (SettingsError).
	@# O CLI lê o .env via pydantic-settings; só vai explícito o que é lido de
	@# os.environ: DATABASE_URL (fail-fast ADR-303 D4), ANTHROPIC_API_KEY (SDK)
	@# e REDIS_URL (publisher de eventos do próprio shell Go).
	@getv() { sed -n "s/^$$1=//p" $(CURDIR)/.env | tail -1 | sed -e 's/^"//' -e 's/"$$//' -e "s/^'//" -e "s/'$$//"; }; \
	 DBURL=$$(getv MATHOMS_DATABASE_URL); \
	 AKEY=$$(getv ANTHROPIC_API_KEY); AKEY="$${AKEY:-$${ANTHROPIC_API_KEY:-}}"; \
	 RURL=$$(getv MATHOMS_REDIS_URL); RURL="$${RURL:-redis://localhost:6379/0}"; \
	 [ -n "$$AKEY" ] || echo "   ⚠ ANTHROPIC_API_KEY ausente (.env/shell) — stages LLM vão falhar"; \
	 [ -n "$$DBURL" ] || echo "   ⚠ MATHOMS_DATABASE_URL ausente no .env — caindo para sqlite mathoms.db (pode DIFERIR do DB da stack nativa!)"; \
	 MATHOMS_DATABASE_URL="$${DBURL:-sqlite+aiosqlite:///$(CURDIR)/mathoms.db}" \
	 ANTHROPIC_API_KEY="$$AKEY" \
	 MATHOMS_REDIS_URL="$$RURL" \
	 REDIS_URL="$$RURL" \
	 MATHOMS_REPO_ROOT="$(CURDIR)" \
	 MATHOMS_PYTHON="$(PYTHON)" \
	 PIPELINE_SERVICE_PORT=$(PORT_GO) \
	 nohup $(CURDIR)/$(DEV_DIR)/pipeline-service-go \
	   > $(CURDIR)/$(DEV_DIR)/go.log 2>&1 & echo $$! > $(CURDIR)/$(DEV_DIR)/go.pid
	@sleep 1; curl -sf --max-time 5 http://localhost:$(PORT_GO)/health > /dev/null \
	  && echo "   ✓ shell Go saudável em http://localhost:$(PORT_GO)" \
	  || { echo "   ❌ /health falhou — veja $(DEV_DIR)/go.log"; exit 1; }
	@echo "▶  Re-apontando o worker nativo para o shell Go…"
	$(call kill_pid_safe,worker,$(CURDIR)/$(DEV_DIR)/worker.pid)
	$(call kill_celery_scoped,celery-native(-go)?-$(WT))
	@TS=$$(date +%s); \
	 MATHOMS_PIPELINE_SERVICE_URL="http://localhost:$(PORT_GO)" \
	 nohup $(VENV)/celery -A backend.app.worker worker \
	   --hostname="celery-native-go-$(WT)@%h-$$TS" \
	   --max-tasks-per-child=200 \
	   --loglevel=info --concurrency=2 \
	   > $(CURDIR)/$(DEV_DIR)/worker.log 2>&1 & echo $$! > $(CURDIR)/$(DEV_DIR)/worker.pid
	@echo ""
	@echo "  ✅ Overlay Go LIGADO no NATIVO — stages executam via shell Go (:$(PORT_GO))."
	@echo "     Use a UI normal (localhost:3000). Logs: $(DEV_DIR)/go.log + worker.log"
	@echo "     Rollback: make go-off ENV=native"

_go-off-smoke:
	$(call kill_pid_safe,go-shell :8002,$(CURDIR)/$(SMOKE_DIR)/go.pid)
	$(call kill_pid_safe,worker,$(CURDIR)/$(SMOKE_DIR)/worker.pid)
	$(call kill_celery_scoped,celery-smoke(-go)?-$(WT))
	@TS=$$(date +%s); \
	 FERNET_KEY="$$(cat $(CURDIR)/$(SMOKE_DIR)/fernet.key)"; \
	 MATHOMS_DATABASE_URL="sqlite+aiosqlite:///$(CURDIR)/$(SMOKE_DB)" \
	 MATHOMS_STORAGE_ROOT="$(CURDIR)/$(SMOKE_STORAGE)" \
	 MATHOMS_REDIS_URL="redis://localhost:$(MATHOMS_SMOKE_REDIS_PORT)/0" \
	 MATHOMS_FERNET_KEY="$$FERNET_KEY" \
	 nohup $(VENV)/celery -A backend.app.worker worker \
	   --hostname="celery-smoke-$(WT)@%h-$$TS" \
	   --max-tasks-per-child=200 \
	   --loglevel=info --concurrency=2 \
	   > $(CURDIR)/$(SMOKE_DIR)/worker.log 2>&1 & echo $$! > $(CURDIR)/$(SMOKE_DIR)/worker.pid
	@echo "  ✅ Overlay Go desligado (smoke) — worker de volta ao executor Python in-process."

_go-off-native:
	$(call kill_pid_safe,go-shell :8002,$(CURDIR)/$(DEV_DIR)/go.pid)
	$(call kill_pid_safe,worker,$(CURDIR)/$(DEV_DIR)/worker.pid)
	$(call kill_celery_scoped,celery-native(-go)?-$(WT))
	@$(MAKE) -s dev-worker-up
	@echo "  ✅ Overlay Go desligado (nativo) — worker de volta ao executor Python in-process."

# ---------------------------------------------------------------------------
# Aliases de compatibilidade (nomes antigos → canônicos)
#
# Sem `##` → não poluem `make help`. Cada um delega ao alvo canônico e imprime
# um aviso de renomeação, para migrar muscle-memory sem quebrar nada. Podem ser
# aposentados numa sprint futura quando o help + os avisos já ensinaram o novo
# vocabulário.
# ---------------------------------------------------------------------------

# Synonyms neutros do botão de pânico (não deprecados — use à vontade).
panic reset-all kill-stale: recover

# Stack nativa (antigo dev-*).
dev-up: native-up
	@echo "ℹ  'dev-up' → 'native-up' (alias mantido)"
dev-down: native-down
	@echo "ℹ  'dev-down' → 'native-down' (alias mantido)"
dev-restart: native-restart
	@echo "ℹ  'dev-restart' → 'native-restart' (alias mantido)"
dev-restart-worker: native-restart-worker
	@echo "ℹ  'dev-restart-worker' → 'native-restart-worker' (alias mantido)"
dev-fresh: native-fresh
	@echo "ℹ  'dev-fresh' → 'native-fresh' (alias mantido)"
dev-status: status
	@echo "ℹ  'dev-status' → 'status' (alias mantido)"
dev-logs: native-logs
	@echo "ℹ  'dev-logs' → 'native-logs' (alias mantido)"
dev-reset-env: native-reset-env
	@echo "ℹ  'dev-reset-env' → 'native-reset-env' (alias mantido)"
dev-kill-stale dev-nuke: recover
	@echo "ℹ  'dev-kill-stale'/'dev-nuke' → 'recover' (alias mantido)"

# Stack Docker (antigo dev-*-docker).
dev-up-docker: docker-up
	@echo "ℹ  'dev-up-docker' → 'docker-up' (alias mantido)"
dev-down-docker: docker-down
	@echo "ℹ  'dev-down-docker' → 'docker-down' (alias mantido)"
dev-reset-docker: docker-reset
	@echo "ℹ  'dev-reset-docker' → 'docker-reset' (alias mantido)"
dev-shell-docker: docker-shell
	@echo "ℹ  'dev-shell-docker' → 'docker-shell' (alias mantido)"
dev-rebuild-docker: docker-build
	@echo "ℹ  'dev-rebuild-docker' → 'docker-build' (alias mantido)"
dev-logs-docker: docker-logs
	@echo "ℹ  'dev-logs-docker' → 'docker-logs' (alias mantido)"

# Overlay Go (antigo dogfood-go*). Passam ENV= ao alvo canônico.
dogfood-go:
	@echo "ℹ  'dogfood-go' → 'make go-on ENV=smoke'"
	@$(MAKE) go-on ENV=smoke
dogfood-go-off:
	@echo "ℹ  'dogfood-go-off' → 'make go-off ENV=smoke'"
	@$(MAKE) go-off ENV=smoke
dogfood-go-dev:
	@echo "ℹ  'dogfood-go-dev' → 'make go-on ENV=native'"
	@$(MAKE) go-on ENV=native
dogfood-go-dev-off:
	@echo "ℹ  'dogfood-go-dev-off' → 'make go-off ENV=native'"
	@$(MAKE) go-off ENV=native
