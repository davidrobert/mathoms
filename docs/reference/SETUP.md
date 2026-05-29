# Mathoms AI — Setup Local

> Guia para rodar o projeto em desenvolvimento local.

## Onboarding em <5min (Docker — caminho recomendado · ADR-252)

Clone fresh → stack inteira rodando em **um comando**:

```bash
make dev-up-docker
```

Sobe 7 containers (Postgres + 2 Redis + API + worker + beat + frontend) com
**migração + seed automáticos** e **hot-reload** do `backend/`. A stack Docker
publica numa **banda de portas distinta** da nativa (8010/3010/5433) — assim
as duas coexistem sem colisão. Quando o boot terminar (~60s: build + migrate +
seed):

- API: http://localhost:8010/health → `{"api":"ok", ...}`
- Frontend: http://localhost:3010
- Postgres: 127.0.0.1:5433 (coexiste com a stack nativa)

Operação diária (todos os targets em `make help`):

```bash
make dev-logs-docker          # tail -f dos logs (SVC=api para um só)
make dev-shell-docker         # bash dentro do container api
make dev-down-docker          # para tudo, PRESERVA volumes (DB/Redis/storage)
make dev-reset-docker         # DESTRUTIVO: para + apaga volumes (wipe + re-seed)
make dev-rebuild-docker       # rebuild das imagens após mudar deps/Dockerfile
```

Passo a passo e troubleshooting no runbook
[Dev environment em Docker](runbooks/dev_environment.md). Vars locais
(LLM key real, secrets próprios) via override gitignored — ver §4 do runbook.

> O setup nativo abaixo (uvicorn no host, targets `make dev-up`/`dev-down`
> sem sufixo) segue suportado como **fallback** e publica na banda
> 8000/8001/3000/3100. A stack Docker publica em 8010/3010/5433/3110, então
> **as duas rodam ao mesmo tempo** sem colidir. Portas overridáveis via
> `MATHOMS_DOCKER_*_PORT` (ex.: `make dev-up-docker MATHOMS_DOCKER_API_PORT=9000`).

## URLs por ambiente (ADR-108)

| Ambiente | Produto | API | Console interno |
|---|---|---|---|
| **Dev local** | http://localhost:3000 | http://localhost:8000 | http://127.0.0.1:3100 (F7F-Local; app `frontend-ops/`, flag `MATHOMS_INTERNAL_OPS_UI_ENABLED=1` · [RUNBOOK §7](RUNBOOK.md)) |
| **Staging** | https://app.staging.mathoms.ai | https://api.staging.mathoms.ai | https://ops.staging.mathoms.ai |
| **Produção** | https://app.mathoms.ai | https://api.mathoms.ai/v1/ | https://ops.mathoms.ai |

Docs públicas: `docs.mathoms.ai` · Status page: `status.mathoms.ai` · Landing: `mathoms.ai`. Ver [ARCHITECTURE.md §18](ARCHITECTURE.md#18-domínios-e-urls-públicas-f7a) para a arquitetura completa.

---

## Pré-requisitos

| Ferramenta     | Versão mínima | Como instalar                                     |
| -------------- | ------------- | ------------------------------------------------- |
| Python         | 3.11+         | `brew install python@3.13`                        |
| Node.js        | 18+           | `brew install node`                               |
| Redis          | 7+            | `brew install redis`                              |
| Git            | 2.x           | `brew install git`                                |

Verificar:

```bash
python3 --version   # >= 3.11
node --version      # >= 18
redis-cli --version # >= 7
```

---

## 1. Clone e instalação

```bash
git clone <repo> mathoms.ai
cd mathoms.ai

# Python virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Instalar pipeline + backend + deps de dev/test (canônico)
# requirements-dev.txt puxa requirements.txt + backend/requirements.txt
# + pytest-asyncio/cov + reportlab. Em conjunto com `-e .` deixa a suíte
# `pytest tests` e `pytest backend/tests` prontas.
pip install -e . -r requirements-dev.txt

# Frontend
cd frontend && npm install && cd ..
```

---

## 1.1. Build steps (codegen e tokens)

```bash
# Design tokens (gera CSS para Next.js)
python3 design-tokens/build.py

# Codegen do layout (gera TS e Pydantic a partir do YAML)
python3 dev/codegen_report_layout.py

# Playwright chromium (para PDF server-side — opcional em dev)
pip install playwright && playwright install chromium
```

---

## 1.2. Pre-commit hooks

```bash
pip install pre-commit
pre-commit install --install-hooks
pre-commit install --hook-type commit-msg
```

Os hooks rodam `dev/check_forbidden_paths.py`, `dev/validate_commit_msg.py`,
ruff, lint anti-PII, etc. — mesma lógica que `dev/commit.py` aplica.

**Se aparecer `Cowardly refusing to install hooks with core.hooksPath set`:**
algum clone antigo (ex.: `fin-current`) deixou `core.hooksPath` apontando para
fora deste repo. Confirme onde está setado:

```bash
git config --show-origin --get core.hooksPath
```

Se o origin for `~/.gitconfig` ou o `.git/config` deste repo, e não há outra
ferramenta dependendo dele, remova:

```bash
git config --unset-all core.hooksPath          # local
git config --global --unset-all core.hooksPath # global (se foi de lá)
```

Depois rode `pre-commit install --install-hooks` de novo.

---

## 1.3. Configuração git recomendada (anti-branch-órfã)

Agentes criam branches `agent/<slug>/<ts>` que viram squash-merge → branch
remota auto-deletada → checkout local fica parado em ref morta. Sintoma:
`make dev-fresh` quebra com `no such ref was fetched`.

**Configure uma vez, vale para sempre:**

```bash
# Auto-prune das refs deletadas no remoto a cada `git fetch`.
# Sem isso, origin/agent/<slug>/<ts> fica como zumbi local mesmo após
# o GitHub deletar a branch remota.
git config --local fetch.prune true

# Alias `git sweep`: deleta locais cuja upstream sumiu (post-merge).
# É destrutivo (-D), por isso fica como comando explícito, não automático.
git config --local alias.sweep '!git fetch -p && \
  git for-each-ref --format="%(refname:short) %(upstream:track)" refs/heads \
  | awk "/\\[gone\\]/ {print \$1}" \
  | xargs -r -n1 git branch -D'
```

**Uso após merge de PR:**

```bash
git checkout main && git pull --ff-only && git sweep
```

**Detecção proativa** (já wired no `make dev-fresh`):

```bash
make stale-check     # avisa se HEAD está em agent/* órfã + mostra one-liner
```

Se você ignorou o aviso e caiu na quebra do `dev-pull`, o próprio target
agora detecta o caso e te dá a one-liner de correção (ver
`Makefile:dev-pull`).

---

## 2. Variáveis de ambiente

Na raiz do repositório existe **`.env.example`** com todas as variáveis documentadas (valores seguros para commit).

**Fluxo recomendado:**

```bash
# Na raiz, com dependências Python do backend instaladas (cryptography).
# Cria .env a partir de .env.example e preenche MATHOMS_FERNET_KEY + MATHOMS_SECRET_KEY (falha se .env já existir).
./scripts/gen-secrets.sh --init-env
```

Alternativa manual: `cp .env.example .env` e rode `./scripts/gen-secrets.sh` (sem flags) para imprimir chaves e colá-las no `.env`.

Se `.env` já existir e você só precisar rotacionar segredos, edite o arquivo à mão ou gere novas linhas com:

```bash
./scripts/gen-secrets.sh
```

Bloco equivalente (trecho mínimo — ver `.env.example` para o restante):

```bash
# Fernet key — CRÍTICO. Gerar uma vez, NUNCA mudar sem re-encriptar dados.
# Preferência: ./scripts/gen-secrets.sh
MATHOMS_FERNET_KEY=sua-chave-fernet-aqui

# JWT secret (dev pode ser qualquer string, prod tem que ser forte)
MATHOMS_SECRET_KEY=dev-secret-change-in-production

# Redis (default local)
MATHOMS_REDIS_URL=redis://localhost:6379/0

# Storage (default: ./storage/)
MATHOMS_STORAGE_ROOT=./storage

# DB (default: SQLite)
MATHOMS_DATABASE_URL=sqlite+aiosqlite:///./mathoms.db

# CORS (default: localhost:3000)
MATHOMS_CORS_ORIGINS=["http://localhost:3000"]
```

> **`MATHOMS_USE_DB_ARTIFACTS` removido em [[ADR-212]] (2026-05-14):** pipeline grava artefatos exclusivamente em `pipeline_artifacts` via `DBArtifactStore`. Se você tem essa env var num `.env` antigo, pode deletar — ela é ignorada.

> **⚠️ Fernet key:** Se você perder essa chave ou gerá-la novamente, **todos os CPFs, API keys LLM e senhas PDF encriptadas ficam irrecuperáveis**. O user precisaria re-cadastrar.

---

## 3. Inicializar banco de dados

```bash
cd backend
python seed_db.py
```

Isso cria:
- Usuário dev: `admin@mathoms.ai` / `admin123`
- Workspace default para esse usuário

### Migrations (Alembic)

> **F6.5E.4 — cwd safety:** o `backend/alembic.ini` usa `%(here)s/../mathoms.db` (caminho absoluto resolvido a partir do diretório do .ini), e `env.py` tem um guard que **rejeita** SQLite com path relativo. Resultado: você pode rodar `alembic` de qualquer pasta sem risco de aplicar a migration na DB errada.

```bash
# Da raiz do repo:
alembic -c backend/alembic.ini current      # estado atual
alembic -c backend/alembic.ini upgrade head # aplica migrations pendentes

# Ou de dentro de backend/ (atalho):
cd backend && alembic current
cd backend && alembic upgrade head
```

Em **CI/produção** sempre setar `MATHOMS_DATABASE_URL` com path absoluto (ou URL Postgres). O guard só permite SQLite relativo se você setar `MATHOMS_ALEMBIC_ALLOW_RELATIVE_SQLITE=1` — use **apenas** em testes do próprio guard.

### Reset completo da plataforma (CLI)

Use **apenas em dev/staging** (ou base descartável). Apaga **todos** os utilizadores e dados em cascata no SQL, remove o conteúdo de `MATHOMS_STORAGE_ROOT` (ex.: `./storage/`) e, por defeito, executa `FLUSHDB` no Redis de `MATHOMS_REDIS_URL`.

| Comando | Efeito |
| --- | --- |
| `python -m backend.app.scripts.reset_platform --dry-run` | Mostra URL da DB (password mascarada), contagens e tamanho de storage; **não altera nada**. |
| `python -m backend.app.scripts.reset_platform --apply` | Após **duas confirmações interactivas** (frases exactas abaixo), executa o reset. |
| `… --apply --skip-redis` | Igual, mas **não** limpa o Redis (útil se não tiver Redis a correr). |

Confirmações exigidas com `--apply` (sem aspas, uma por linha):

1. `DELETE ALL DATA`
2. `RESET PLATFORM IRREVERSIBLE`

**Recomendação:** parar API, worker Celery e qualquer processo que escreva na mesma DB/storage antes de `--apply`.

Depois do reset, o “primeiro login” deixa de ser o seed de `seed_db.py` até voltar a correr esse script ou registar um novo utilizador na UI.

Relacionado: reset **só** de documentos e pastas de dados por tenant (preserva `config/` em cada tenant) — `python -m backend.app.scripts.reset_documents --dry-run` / `--apply`.

---

## 4. Rodar o stack local

### Caminho rápido — `make dev-*`

Uma aba de terminal sobe os **6 serviços** (Redis, API 8000, Celery worker,
frontend 3000, Ops API 8001, frontend-ops 3100) em background:

```bash
make dev-bootstrap   # primeira vez: venv, deps, .env, codegen
make dev-up          # sobe tudo
make dev-status      # checa PIDs e portas (✅/❌)
make dev-logs        # tail -f de todos os logs (SVC=api para um só)
make dev-down        # mata tudo (preserva Redis se já estava rodando antes)
```

| Target | O que faz |
| --- | --- |
| `make dev-bootstrap` | Cria `.venv`, instala deps Python e npm (frontend + frontend-ops), gera `.env` via `gen-secrets.sh --init-env` se ausente, gera `frontend-ops/.env.local`, roda codegen (design-tokens + report-layout). Avisa se `config/internal_operators.yaml` falta. |
| `make dev-pull` | `git pull --ff-only` na raiz + `npm install` em ambos os frontends. Aborta se working tree sujo. |
| `make dev-up` | Sobe os 6 serviços. **Não toca `.env` nem `mathoms.db`** (preserva Fernet e dados encriptados). |
| `make dev-down` | Mata todos os processos via PID files. Só mata Redis se foi `dev-up` quem subiu. |
| `make dev-restart` | `dev-down && dev-up`. |
| `make dev-restart-worker` | Restart só do Celery worker — útil ao mexer em `pipeline/` ou `tasks/` (worker não tem hot reload). |
| `make dev-status` | Tabela com PID + porta listening de cada serviço (via `lsof`). |
| `make dev-logs` | `tail -f` de todos os logs em `_dev_pids/`. `SVC=api` para um só. |
| `make dev-kill-stale` | Mata processos órfãos em 8000/8001/3000/3100 + limpa `_dev_pids/`. Use quando `dev-up` reclamar de "Porta X já em uso" (uvicorn/npm de sessão antiga). |
| `make dev-reset-env` | **Destrutivo.** Regenera `.env` (apaga `MATHOMS_FERNET_KEY` → invalida API keys LLM, senhas PDF, CPFs encriptados). Pede confirmação. |

PIDs e logs ficam em `_dev_pids/<svc>.{pid,log}` (no `.gitignore`).

URLs após `make dev-up`:
- API: http://localhost:8000/docs · http://localhost:8000/health
- Frontend: http://localhost:3000
- Ops API: http://127.0.0.1:8001/admin/* (requer `config/internal_operators.yaml` — ver [RUNBOOK §7.2](RUNBOOK.md))
- Frontend-ops: http://127.0.0.1:3100/login

### Caminho manual — 4 terminais (fallback)

Útil se você precisa ver os logs ao vivo ou usar `--reload` interativamente.

| Terminal | Comando |
| --- | --- |
| Redis | `redis-server` (ou `brew services start redis`) |
| Backend (8000) | `source .venv/bin/activate && uvicorn backend.app.main:app --reload --port 8000` |
| Celery | `source .venv/bin/activate && celery -A backend.app.worker worker -l info -c 2` |
| Frontend | `cd frontend && npm run dev` |

Para ops API (8001) e frontend-ops (3100), ver [RUNBOOK §7.2](RUNBOOK.md) —
exige envs extras (`MATHOMS_INTERNAL_OPS_UI_ENABLED=1` etc.) que `make dev-up`
já configura automaticamente.

**Status page (opcional, 7E.6):** crie `frontend/.env.local` com `NEXT_PUBLIC_MATHOMS_STATUS_PAGE_URL=https://…` para exibir o link **Status e incidentes** no rodapé (login, cadastro, convite e área logada). Ver [RUNBOOK.md](RUNBOOK.md).

---

## 5. Primeiro login

1. Abrir http://localhost:3000
2. Login: `admin@mathoms.ai` / `admin123`
3. Navegar para **Documentos** → arrastar PDFs/XLSX/CSVs
4. Navegar para **Pipeline** → clicar **Processar documentos**
5. Aguardar conclusão (~3-15min dependendo da quantidade de docs e se LLM está habilitado)
6. Ver relatório em **Relatórios**

---

## 6. Habilitar LLM (Premium)

1. Obter API key de um provedor suportado (Anthropic, OpenAI, etc.)
2. Ir em **Configurações → LLM**
3. Selecionar provider + modelo
4. Colar API key
5. Salvar → clicar **Testar Conexão**
6. Se verde → rodar pipeline novamente. Agora E1, E1.5, E2-llm e E6-parecer executam.

---

## 7. Rodar testes

### Pipeline (Python)
```bash
pytest tests/ -v        # Pipeline core (~270 tests)
```

### Backend
```bash
cd backend
pytest tests/ -v        # API, models, services (~320 tests)
```

### Coverage
```bash
pytest --cov=backend/app --cov=pipeline --cov-report=html
open htmlcov/index.html
```

---

## 8. Pipeline CLI (sem web)

> **[[ADR-212]] (2026-05-14):** CLI standalone do pipeline foi descontinuada.
> Entrypoints `python scripts/e0_route.py`, `python scripts/e0_unlock.py`,
> `python scripts/e2_extract.py`, `python scripts/e3_reconcile.py`,
> `python scripts/e4_categorize.py`, `python scripts/e5_analyze.py`,
> `python scripts/e7_review.py`, `python scripts/e_reset.py` **não existem
> mais**. Pipeline roda exclusivamente via backend (Celery worker); use
> `make dev-up` + `POST /pipeline/run` para debug local. Reset destrutivo
> de pipeline virou service-layer (`backend/app/services/internal_ops/pipeline_reset.py`),
> consumido pelo console interno.
>
> **Única CLI sobrevivente:**
> - `scripts/e0_audit.py` — inspeção read-only do filesystem do workspace
>   (detecta duplicatas + arquivos órfãos no inbox). Não toca
>   `pipeline_artifacts`; consome apenas `MATHOMS_WORKSPACE_ROOT`.

```bash
source .venv/bin/activate
export MATHOMS_WORKSPACE_ROOT="$PWD/storage/<workspace_id>"

# Inspeção read-only do inbox + duplicatas
python scripts/e0_audit.py
python scripts/e0_audit.py --json   # output JSON para scripts
```

Em produção (API + Celery worker), paths vêm via `WorkspaceContext` por-run; testes injetam `InMemoryArtifactStore` explícito ([[ADR-212]] PR2 removeu `MATHOMS_WORKSPACE_ROOT setdefault` global).

**Directórios na raiz do repo:** não é obrigatório existir `data/`, `inbox/`,
`inbox_processed/`, `logs/`, `members/` ou `life_plan/` na raiz do clone. Esses
nomes são **subpastas do workspace** (por defeito `storage/<workspace_id>/…`)
quando ainda existem em disco — pós-[[ADR-212]], artefatos do pipeline vivem
em `pipeline_artifacts` no DB, não em `processed/`/`output/`. A app web não
depende dessas pastas na raiz.

Após cada run, artefatos JSON críticos são validados contra schemas (`warn` por padrão; ver `MATHOMS_PIPELINE_SCHEMA_MODE` e [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md)).

---

## 9. Troubleshooting

### "ModuleNotFoundError: No module named 'pipeline'" no Celery worker

O `sys.path` do fork pool worker não herda o path do main process.
- **Fix já aplicado:** `backend/app/worker.py` adiciona `sys.path.insert(0, project_root)` no module load.
- Se o erro voltar, verifique se o worker está rodando do diretório raiz do projeto.

### "Celery worker não registra task 'pipeline.run'"

`autodiscover_tasks` procura por `tasks.py`, mas o arquivo é `pipeline_task.py`.
- **Fix aplicado:** `worker.py` usa `include=["backend.app.tasks.pipeline_task"]` explicitamente.

### Pipeline fica em "pending" indefinidamente

O worker Celery não está rodando. Verifique:
```bash
curl http://localhost:8000/health | python3 -m json.tool
# celery deve estar "ok", não "no_workers"
```

### "FATAL: Config file not found" / "Baseline não encontrado"

O pipeline está rodando sem docs em `data/`. Possíveis causas:
1. Upload não completou a classificação (docs ainda no `inbox/`)
2. Docs foram classificados como `other` e não roteados
3. Workspace vazio

Verifique com:
```bash
ls storage/{workspace_id}/data/*/
```

### LLM stages são skippados mesmo com API key configurada

Provavelmente a `MATHOMS_FERNET_KEY` mudou entre o save e o pipeline run. Re-salvar a API key em **Configurações → LLM** resolve. Para evitar no futuro: persistir `MATHOMS_FERNET_KEY` no `.env` (nunca gerar uma nova).

### "openpyxl does not support old .xls format"

Instale `xlrd`: `pip install xlrd`

### "No module named 'pytz'" / "pikepdf" / "pydantic" / "reportlab"

Dependências de dev/test faltando — você provavelmente rodou `pip install -e ".[dev]"` (extra mínimo). Use o caminho canônico:

```bash
pip install -e . -r requirements-dev.txt
```

### Frontend build quebrando com erro TypeScript

```bash
cd frontend
rm -rf .next node_modules
npm install
npm run build
```

### `MATHOMS_FERNET_KEY não configurada` ao subir o uvicorn

`.env` existe mas o valor está vazio (`MATHOMS_FERNET_KEY=`). Geralmente
significa que `.env` é cópia crua do `.env.example` e `gen-secrets.sh
--init-env` foi abortado porque o arquivo já existia.

```bash
rm .env
./scripts/gen-secrets.sh --init-env
```

### `seed_db.py` falha com "table X has no column named Y"

DB local (`mathoms.db`) é de uma sessão anterior e está com schema
desatualizado. `init_db()` só cria tabelas **faltando** — não aplica
migrações Alembic em tabelas pré-existentes.

Duas saídas:

```bash
# A) Wipe (começa zerado — recomendado para smoke)
rm -f mathoms.db mathoms.db-shm mathoms.db-wal mathoms-smoke.db*
cd backend && python seed_db.py

# B) Migrar (preserva dados)
cd backend && alembic upgrade head && python seed_db.py
```

### Worker Celery não reflete mudanças de código

O worker precisa ser **reiniciado** manualmente após mudanças em:
- `backend/app/tasks/*`
- `backend/app/worker.py`
- `pipeline/**/*`
- `scripts/*`

O backend FastAPI tem hot reload com `--reload`, mas o worker não.

---

## 10. Arquitetura em desenvolvimento

Para entender a arquitetura completa antes de contribuir, ler **[ARCHITECTURE.md](ARCHITECTURE.md)**.

Para o fluxo de trabalho atual e tarefas em andamento, ver **[PHASES.md](PHASES.md)** (roadmap macro) + **[../_MOC/SPRINTS-active.md](../_MOC/SPRINTS-active.md)** (sprint atual + lanes ready).

### Estado pós-A6 — infra + domínio consolidados

Arquitetura alvo em [ARCHITECTURE §17](ARCHITECTURE.md). Principais marcos:

- **Artefatos do pipeline em DB** (tabela `pipeline_artifacts`, [[ADR-082]]) — cutover final em [[ADR-212]] (2026-05-14): `DBArtifactStore` é caminho único, `DiskArtifactStore` deletado, flag `MATHOMS_USE_DB_ARTIFACTS` removida, validação JSON-schema universal via hook pós-write.
- **Abstração `ArtifactStore`** em [`pipeline/artifact_store.py`](../../pipeline/artifact_store.py) ([[ADR-083]]) — `InMemoryArtifactStore` (testes) + `DBArtifactStore` (web/Celery).
- **Orquestrador declarativo** via [`pipeline/stage_spec.py`](../../pipeline/stage_spec.py) (`STAGE_REGISTRY`, `STAGE_RENAME_MAP`, [[ADR-087]]).
- **Camada de domínio** em [`pipeline/domain/`](../../pipeline/domain/) ([[ADR-089]]/[[ADR-090]]/[[ADR-091]]) — `Money`, `Transaction`, `BankStatement`, services puros testáveis em memória.
- **Reset destrutivo** virou service-layer: `backend/app/services/internal_ops/pipeline_reset.py::reset_workspace_from_stage` (consumido pelo console interno, [[ADR-116]]).

Rollback do cutover [[ADR-212]] em [runbooks/pipeline_rollback.md](runbooks/pipeline_rollback.md) (~30min RTO via snapshot DB + revert PR + downgrade migration).

**Auditoria de identificadores legados (Fase 9):**

```bash
.venv/bin/python dev/audit_stage_references.py          # lista ocorrências
.venv/bin/python dev/audit_stage_references.py --strict # exit 1 se houver leak
```
