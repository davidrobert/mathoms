# Fin — Setup Local

> Guia para rodar o projeto em desenvolvimento local.

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
git clone <repo> fin-current
cd fin-current

# Python virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Instalar pipeline + backend (modo editable)
pip install -e ".[dev]"

# Instalar dependências que não estão no pyproject
pip install pytz pikepdf openpyxl xlrd

# Frontend
cd frontend && npm install && cd ..
```

---

## 1.1. Build steps (codegen e tokens)

```bash
# Design tokens (gera CSS para Next.js e E6)
python3 design-tokens/build.py

# Codegen do layout (gera TS e Pydantic a partir do YAML)
python3 dev/codegen_report_layout.py

# Playwright chromium (para PDF server-side — opcional em dev)
pip install playwright && playwright install chromium
```

---

## 2. Variáveis de ambiente

Na raiz do repositório existe **`.env.example`** com todas as variáveis documentadas (valores seguros para commit).

**Fluxo recomendado:**

```bash
# Na raiz, com dependências Python do backend instaladas (cryptography).
# Cria .env a partir de .env.example e preenche FIN_FERNET_KEY + FIN_SECRET_KEY (falha se .env já existir).
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
FIN_FERNET_KEY=sua-chave-fernet-aqui

# JWT secret (dev pode ser qualquer string, prod tem que ser forte)
FIN_SECRET_KEY=dev-secret-change-in-production

# Redis (default local)
FIN_REDIS_URL=redis://localhost:6379/0

# Storage (default: ./storage/)
FIN_STORAGE_ROOT=./storage

# DB (default: SQLite)
FIN_DATABASE_URL=sqlite+aiosqlite:///./fin.db

# CORS (default: localhost:3000)
FIN_CORS_ORIGINS=["http://localhost:3000"]
```

> **⚠️ Fernet key:** Se você perder essa chave ou gerá-la novamente, **todos os CPFs, API keys LLM e senhas PDF encriptadas ficam irrecuperáveis**. O user precisaria re-cadastrar.

---

## 3. Inicializar banco de dados

```bash
cd backend
python seed_db.py
```

Isso cria:
- Usuário dev: `admin@fin.app` / `admin123`
- Workspace default para esse usuário
- Importa relatórios HTML existentes em `output/` (se houver)

### Migrations (Alembic)

> **F6.5E.4 — cwd safety:** o `backend/alembic.ini` usa `%(here)s/../fin.db` (caminho absoluto resolvido a partir do diretório do .ini), e `env.py` tem um guard que **rejeita** SQLite com path relativo. Resultado: você pode rodar `alembic` de qualquer pasta sem risco de aplicar a migration na DB errada.

```bash
# Da raiz do repo:
alembic -c backend/alembic.ini current      # estado atual
alembic -c backend/alembic.ini upgrade head # aplica migrations pendentes

# Ou de dentro de backend/ (atalho):
cd backend && alembic current
cd backend && alembic upgrade head
```

Em **CI/produção** sempre setar `FIN_DATABASE_URL` com path absoluto (ou URL Postgres). O guard só permite SQLite relativo se você setar `FIN_ALEMBIC_ALLOW_RELATIVE_SQLITE=1` — use **apenas** em testes do próprio guard.

---

## 4. Rodar os 4 serviços

Precisa de **4 terminais** abertos simultaneamente:

### Terminal 1 — Redis
```bash
redis-server
# ou como serviço: brew services start redis
```

### Terminal 2 — Backend (FastAPI)
```bash
cd fin-current
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --port 8000
```

Acessar: http://localhost:8000/docs (OpenAPI) ou http://localhost:8000/health

### Terminal 3 — Celery worker
```bash
cd fin-current
source .venv/bin/activate
celery -A backend.app.worker worker -l info -c 2
```

### Terminal 4 — Frontend (Next.js)
```bash
cd fin-current/frontend
npm run dev
```

Acessar: http://localhost:3000

**Status page (opcional, 7E.6):** crie `frontend/.env.local` com `NEXT_PUBLIC_FIN_STATUS_PAGE_URL=https://…` para exibir o link **Status e incidentes** no rodapé (login, cadastro, convite e área logada). Ver [RUNBOOK.md](RUNBOOK.md).

---

## 5. Primeiro login

1. Abrir http://localhost:3000
2. Login: `admin@fin.app` / `admin123`
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
6. Se verde → rodar pipeline novamente. Agora E1, E1.5, E2-llm e E7-review executam.

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

O pipeline continua funcionando via CLI para debug:

```bash
source .venv/bin/activate

# Extração de faturas
python scripts/e2_extract.py --faturas-only

# Reconciliação
python scripts/e3_reconcile.py

# Relatório completo (usa config/ global)
python scripts/e_reset.py

# Mesmo orquestrador do worker, sobre tenant materializado (storage/<workspace_id>/)
python -m pipeline.run_dev --root /caminho/para/tenant
```

Após cada run, artefatos JSON críticos são validados contra schemas (`warn` por padrão; ver `FIN_PIPELINE_SCHEMA_MODE` e [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md)).

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

Provavelmente a `FIN_FERNET_KEY` mudou entre o save e o pipeline run. Re-salvar a API key em **Configurações → LLM** resolve. Para evitar no futuro: persistir `FIN_FERNET_KEY` no `.env` (nunca gerar uma nova).

### "openpyxl does not support old .xls format"

Instale `xlrd`: `pip install xlrd`

### "No module named 'pytz'" / "pikepdf"

Dependências faltando. Instalar:
```bash
pip install pytz pikepdf openpyxl xlrd
```

### Frontend build quebrando com erro TypeScript

```bash
cd frontend
rm -rf .next node_modules
npm install
npm run build
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

Para o fluxo de trabalho atual e tarefas em andamento, ver **[ROADMAP.md](ROADMAP.md)** e **[BACKLOG.md](BACKLOG.md)**.
