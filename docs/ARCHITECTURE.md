# Fin — Arquitetura

> Documento técnico de referência. Atualizar quando stack ou modelo de dados mudar.

---

## 1. Stack tecnológica

### Backend
- **FastAPI** (Python 3.11+) — API server
- **SQLAlchemy 2.0** (async + sync engines) — ORM
- **Alembic** — DB migrations
- **Pydantic v2** — validação e serialização
- **Celery + Redis** — task queue + pub/sub para WebSocket
- **Fernet (cryptography)** — encryption at-rest (CPFs, API keys, senhas PDF)
- **LiteLLM + Instructor** — LLM orchestration (multi-provider)
- **pdfplumber, openpyxl, xlrd, pikepdf** — extração de documentos

### Frontend
- **Next.js 16** (App Router) + **React 19** + **TypeScript**
- **Tailwind CSS 4** com `@theme inline` (tokens oklch)
- **shadcn/ui** (Radix primitives)
- **Recharts** — visualizações
- **next-themes** — dark mode
- **Sonner** — toast notifications
- **Lucide React** — ícones

### Infraestrutura
- **Dev:** SQLite + Redis local + 3 processos locais (api, worker, frontend)
- **Prod (planejado F7):** PostgreSQL + Traefik (auto-SSL) + Docker Compose + VPS Hetzner

### Persistência
| Ambiente | DB          | Storage                   | Broker        |
| -------- | ----------- | ------------------------- | ------------- |
| Dev      | SQLite      | Filesystem local          | Redis local   |
| Prod     | PostgreSQL  | Docker volume (per-tenant)| Redis Docker  |

---

## 2. Diagrama de componentes

```
┌──────────────────────────────────────────────────────────────┐
│                    FRONTEND (SPA)                             │
│  Next.js 16 + TypeScript + Tailwind CSS 4 + Recharts          │
│  Login, Upload, Config, Dashboard, Reports, Pipeline          │
└────────────────────────┬─────────────────────────────────────┘
                         │ REST API (OpenAPI)
                         │ + WebSocket (progress, via Redis Pub/Sub)
┌────────────────────────┴─────────────────────────────────────┐
│                  BACKEND (API Server)                         │
│  FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2             │
│                                                               │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────┐  │
│  │ Auth Module  │  │ Pipeline      │  │ LLM Service        │  │
│  │ JWT + bcrypt │  │ Orchestrator  │  │ LiteLLM+Instructor │  │
│  │ Fernet vault │  │ (F0 wrappers) │  │ BYOK, auto-retry   │  │
│  └──────────────┘  └───────────────┘  └────────────────────┘  │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │         Pipeline Core (package Python)                   │  │
│  │   e0/ e2/ e3/ e4/ e5/ e5n/ e6/ e7/ models/              │  │
│  │   + llm/prompts/ + llm/validators/                       │  │
│  │   + materialize_config()                                 │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────┬────────────────┬────────────────┬─────────────────┘
           │                │                │
      ┌────┴─────┐   ┌─────┴──────┐   ┌─────┴──────────────┐
      │PostgreSQL│   │File Storage│   │Celery + Redis       │
      │(prod)    │   │Docker vol  │   │ broker, result,     │
      │SQLite    │   │per-tenant  │   │ Pub/Sub (WS events) │
      │(dev)     │   │            │   │                     │
      └──────────┘   └────────────┘   └─────────────────────┘
```

---

## 3. Type safety end-to-end

```
FastAPI (Pydantic models)
    → auto-generate OpenAPI schema (JSON)
        → openapi-typescript (build step)
            → TypeScript types (.d.ts)
                → Next.js consome com fetch type-safe
```

---

## 4. Modelo de dados

### Auth + Core

```
User
  id, email, hashed_password, name, tier, created_at
  llm_api_key (encrypted)

Workspace
  id, user_id, name, created_at
  → family_members[], categories[], pipeline_config, institution_config, report_layout
```

### Documents & Pipeline

```
Document
  id, workspace_id, original_name, stored_path, doc_type, bank_code, period
  status (uploaded|unlocking|classifying|ready|needs_password|processing|processed|error)
  classification_meta (JSON), uploaded_at, content_hash

PasswordVault
  id, workspace_id, label, encrypted_password (Fernet), created_at

PipelineRun
  id, workspace_id, status (pending|running|completed|failed|cancelled|needs_review|resuming)
  current_stage, started_at, completed_at, config_snapshot (JSON)
  tier_at_run (free|premium), paused_at_stage
  celery_task_id

PipelineStageLog
  id, pipeline_run_id, stage
  status (pending|running|completed|failed|skipped|skipped_free_tier|needs_review)
  started_at, completed_at, output_summary, errors, duration_ms

Report
  id, pipeline_run_id, html_path, period_start, period_end
  created_at, score, patrimonio_liquido
```

### Config (por workspace)

```
FamilyMember
  id, workspace_id, key, full_name, short_name
  cpf_encrypted (Fernet), birth_date, role, order, extra (JSON)
  → accounts[]

BankAccount
  id, member_id (FK), institution_code, account_type, agency, account_number, label

Category
  id, workspace_id, code, name, category_type (receita|despesa)
  monthly_cap, order
  → keywords[]

CategoryKeyword
  id, category_id (FK), keyword

PipelineConfig      (id, workspace_id unique, config_json)
InstitutionConfig   (id, workspace_id unique, config_json)
ReportLayout        (id, workspace_id unique, config_json)
```

### LLM & Reviews

```
LLMConfig
  id, workspace_id (unique), provider (anthropic|openai|ollama|...)
  api_key_encrypted (Fernet), model_name, max_tokens, temperature

StageReview
  id, pipeline_run_id, stage, status (pending|approved|edited)
  original_output_json, edited_output_json
  validation_errors, reviewer_notes, created_at, reviewed_at
```

### Transactions & Notifications

```
TransactionOverride
  id, workspace_id, transaction_hash
  original_category, new_category, notes, reviewed, created_at

Notification
  id, workspace_id, severity (info|warning|critical)
  title, message, is_read, created_at
```

---

## 5. Pipeline stages

### Ordem completa (`FULL_ORDER` — premium)

```
E0-unlock → E0-audit → E0-route
→ E1 (LLM) → E1.5 (LLM) → E1.5c
→ E2-llm (LLM) → E2-faturas → E2-extratos
→ E3 → E4 → E5 → E5.N → E6
→ E7-crossval → E7-review (LLM) → E7-apply → E6-final
```

### Ordem determinística (`DETERMINISTIC_ORDER` — free)

```
E0-audit → E1.5c (skip se sem baseline)
→ E2-faturas → E2-extratos
→ E3 → E4 → E5 → E5.N → E6
→ E7-crossval → E7-apply (skip) → E6-final
```

### O que cada stage faz

| Stage          | Tipo       | Responsabilidade                                                 |
| -------------- | ---------- | ---------------------------------------------------------------- |
| E0-unlock      | det.       | Desbloqueia PDFs protegidos usando vault                         |
| E0-audit       | det.       | 9 checks de integridade (filename↔content, órfãos, duplicatas)   |
| E0-route       | det.       | Classifica docs por regex, move inbox/ → data/{dest_group}/      |
| E1             | **LLM**    | Extrai dados pessoais (nome, CPF, role) de IRPFs/IDs             |
| E1.5           | **LLM**    | Extrai baseline patrimonial (imóveis, veículos, investimentos)   |
| E1.5c          | det.       | Consolida baseline (soma imóveis, deduplica)                     |
| E2-llm         | **LLM**    | Extrai transações de docs sem parser determinístico              |
| E2-faturas     | det.       | Parse de faturas de cartão (11 parsers bancários)                |
| E2-extratos    | det.       | Parse de extratos de conta (11 parsers bancários)                |
| E3             | det.       | Reconciliação cross-banco, deduplicação, transferências internas |
| E4             | det.       | Categorização por keywords (300+ em 16 categorias)               |
| E5             | det.       | Análise: score, fluxo, patrimônio, goals, reserva emergência     |
| E5.N           | det.       | Narrativas automáticas (contexto para cada seção)                |
| E6             | det.       | Render HTML do relatório (Chart.js, dark mode)                   |
| E7-crossval    | det.       | 14 checks automáticos de qualidade                               |
| E7-review      | **LLM**    | Review holístico (insights, recomendações, ajustes de score)     |
| E7-apply       | det.       | Aplica review ao E5 JSON                                         |
| E6-final       | det.       | Re-render final com review incorporado                           |

---

## 6. Fluxos-chave

### Upload → Classificação → Pipeline

```
User drag-and-drop PDF
    ↓
POST /api/documents/upload
    ↓
StorageService.save_to_inbox()  →  storage/{ws_id}/inbox/
    ↓
process_uploaded_document():
  1. PDF encrypted? → try vault passwords → unlock OR needs_password
  2. classify_document() via E0-route regex
  3. JSON? → detect E1/E1.5 type
  4. route_to_data_dir() → storage/{ws_id}/data/{dest_group}/
    ↓
Document.status = "ready"
    ↓
User clica "Gerar Relatório"
    ↓
POST /api/pipeline/run → materialize_config() → Celery task
    ↓
Pipeline stages rodam em ordem → PipelineStageLog por stage
    ↓
WebSocket /ws publica eventos via Redis Pub/Sub
    ↓
E6 produz HTML → Report criado no DB
```

### Materialização de config

```
User edita config via UI → DB
    ↓
POST /api/pipeline/run
    ↓
materialize_config(ws_id, tenant_root, db):
  1. Copia config/ global → storage/{ws_id}/config/
  2. Sobrescreve com serializers de configs editados no DB
  3. Decripta LLM api_key e inclui em llm_config.json
    ↓
Pipeline scripts lêem de storage/{ws_id}/config/ via _init_config(root_dir)
    ↓
Zero mudança na lógica interna dos scripts legados
```

### Tier detection + skip_llm

```
POST /api/pipeline/run
    ↓
Detect tier: LLMConfig exists → "premium", else "free"
    ↓
body.skip_llm == True → DETERMINISTIC_ORDER (sem LLM stages)
body.skip_llm == False → FULL_ORDER (com E1, E1.5, E2-llm, E7-review)
    ↓
Dentro da task Celery:
  - if stage in LLM_STAGES AND skip_llm → status = skipped
  - Stage runner individual pode retornar {skipped: true} se dados ausentes
```

---

## 7. Estrutura de pastas

```
fin-current/
├── backend/
│   ├── app/
│   │   ├── api/               # 9 routers REST
│   │   │   ├── auth.py, reports.py
│   │   │   ├── documents.py, vault.py
│   │   │   ├── pipeline.py, config.py, llm.py
│   │   │   ├── transactions.py, dashboard.py, notifications.py
│   │   │   └── ws.py          # WebSocket (JWT auth, Redis Pub/Sub)
│   │   ├── core/              # Settings, database, security, deps
│   │   ├── models/            # 17 SQLAlchemy models
│   │   ├── schemas/           # Pydantic request/response
│   │   ├── services/          # Business logic
│   │   │   ├── storage.py, vault.py
│   │   │   ├── document_processor.py
│   │   │   ├── pipeline_service.py
│   │   │   ├── config_materializer.py
│   │   │   ├── events.py      # Redis Pub/Sub publisher
│   │   │   └── retry_config.py
│   │   ├── tasks/
│   │   │   └── pipeline_task.py  # Celery @task principal
│   │   ├── worker.py          # Celery app config
│   │   └── main.py            # FastAPI app
│   ├── alembic/               # DB migrations
│   ├── tests/                 # ~320 tests
│   └── requirements.txt
│
├── pipeline/                  # Pipeline core (package Python)
│   ├── __init__.py            # API pública v0.2.0
│   ├── context.py             # WorkspaceContext
│   ├── config_loader.py
│   ├── orchestrator.py        # run_pipeline, run_from, run_stages
│   ├── llm/                   # LLM infrastructure
│   │   ├── service.py         # LiteLLM + Instructor
│   │   ├── text_extractor.py
│   │   ├── validators.py
│   │   ├── prompts/
│   │   └── schemas/
│   └── stages/                # Thin wrappers (4-15 lines cada)
│
├── scripts/                   # Pipeline scripts legados (CLI mode)
│   ├── e0_audit.py, e0_route.py, e0_unlock.py
│   ├── e15_consolidate.py, e2_extract.py
│   ├── e2/banks/              # 11 parsers bancários
│   ├── e3_reconcile.py, e4_categorize.py
│   ├── e5_analyze.py, e5n_narrativas.py
│   ├── e6_render.py, e7_review.py
│   └── pipeline_common.py
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── login/, register/
│   │   │   └── (app)/         # Route group com AppShell
│   │   │       ├── dashboard/, documents/, pipeline/
│   │   │       ├── transactions/, reports/, vault/, config/
│   │   ├── components/
│   │   │   ├── ui/            # 16+ shadcn/ui primitives
│   │   │   └── *.tsx          # Compositions (AppShell, KPICard, etc.)
│   │   └── lib/
│   │       ├── api.ts         # 50+ API functions + types
│   │       ├── format.ts      # Formatters + status maps
│   │       ├── usePipelineWS.ts
│   │       └── utils.ts       # cn()
│   └── package.json
│
├── config/                    # Configs globais (22 arquivos)
│   ├── family_members.json (fallback)
│   ├── categorization.json (300+ keywords)
│   ├── institutions.json, pipeline.json, scoring.json
│   ├── llm_config.json, report_layout.yaml
│   └── schemas/               # JSON schemas
│
├── storage/                   # Per-tenant (gitignored)
│   └── {workspace_id}/
│       ├── inbox/             # Uploads landing
│       ├── data/              # Arquivos classificados
│       ├── processed/         # E2/E3/E4/E5 outputs
│       ├── output/            # Relatório HTML
│       ├── members/           # JSONs E1
│       └── config/            # Config materializada
│
├── tests/                     # Pipeline tests (~270)
├── docs/                      # Este diretório
├── dev/                       # Dev tooling (commit helper, pre-commit hooks)
├── docker-compose.yml         # Redis (dev)
└── pyproject.toml             # Package fin-pipeline
```

---

## 8. Onde moram os dados

A pergunta "onde está tal dado?" aparece toda hora. Essa seção é a fonte de
verdade curta. Vale para o produto web multi-tenant atual; não descreve o
estado do pipeline legado single-tenant em `data/`/`inbox/` (que persiste
apenas no repo do dono original e não é usado pela API).

### 8.1 Mapa por tipo de dado

| Dado                                              | Onde vive                                                   | Persistido por                                                  | Quando                                  |
| ------------------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------- | --------------------------------------- |
| Código-fonte + docs                               | Git (`github.com/.../fin-current`)                          | Desenvolvedor via `git commit`                                  | Manual, em PRs                          |
| Schema do banco                                   | Migrations Alembic (`backend/alembic/versions/`)            | Desenvolvedor (`alembic revision`)                              | Ao mudar modelo                         |
| Config global (fallback de todo tenant)           | `config/*.{json,yaml,md}`                                   | Versionado no repo                                              | Só muda via PR                          |
| **Usuário** (email, senha hash, MFA)              | `users` (DB)                                                | `POST /auth/register`, `/auth/login`                            | Síncrono no request                     |
| **Workspace** (tenant)                            | `workspaces` (DB)                                           | Criado no primeiro login do owner                               | Síncrono                                |
| **Documento uploadado** (metadata)                | `documents` (DB)                                            | `POST /documents/upload`                                        | Síncrono no request                     |
| **Documento uploadado** (bytes)                   | `storage/{workspace_id}/inbox/{safe_name}`                  | `StorageService.save_to_inbox`                                  | Síncrono no upload                      |
| Documento classificado (após E0)                  | `storage/{workspace_id}/data/<subdir>/`                     | `document_processor` → `StorageService.move_to_data`            | Síncrono no upload                      |
| Senhas de PDF (vault)                             | `password_vault` (DB), `encrypted_password` Fernet          | `POST /vault/passwords`                                         | Síncrono                                |
| Chaves API LLM do usuário (BYOK)                  | `llm_configs` (DB), `api_key_encrypted` Fernet              | `POST /llm/config`                                              | Síncrono                                |
| CPFs dos membros                                  | `family_members.cpf_encrypted` (DB), Fernet                 | `POST /config/family-members` (ou E1 LLM)                       | Síncrono / durante pipeline             |
| Config materializada por tenant (input do E2–E7)  | `storage/{ws_id}/config/*`                                  | `config_materializer.materialize_config()`                      | Antes de cada `PipelineRun`             |
| Artefatos intermediários (`-2_extract.json`, …)   | `storage/{ws_id}/processed/E2_extracts/` etc.               | Scripts E2–E5 executando dentro do tenant_root                  | Durante job Celery do pipeline          |
| Análise final (`analise_financeira-5_analysis.json`) | `storage/{ws_id}/processed/E5_analysis/`                 | Stage E5                                                        | Durante job Celery                      |
| Relatório HTML final                              | `storage/{ws_id}/output/` e row em `reports` (DB)           | Stage E6 + handler que registra `Report`                        | Ao final do `PipelineRun`               |
| Logs do pipeline                                  | `pipeline_runs`, `pipeline_stage_logs` (DB) + stdout stages | `orchestrator` + `storage/{ws_id}/logs/` (texto bruto)          | Durante o job                           |
| Transações extraídas (após reconcile)             | `transactions` (DB)                                         | Serializer no fim do E3/E4                                      | Durante o job                           |
| Override de categoria pelo usuário                | `transaction_overrides` (DB)                                | `PATCH /transactions/{hash}`                                    | Síncrono                                |
| Notificações UI                                   | `notifications` (DB)                                        | Vários serviços                                                 | Síncrono / por job                      |
| **Audit log** (uploads, deletes, purges…)         | `audit_logs` (DB)                                           | `services/audit.py::audit_log` dentro da transação do endpoint  | Síncrono com a ação auditada            |
| Tasks queue state                                 | Redis (broker + result backend)                             | Celery                                                          | Efêmero                                 |
| Eventos WebSocket (progresso live)                | Redis Pub/Sub                                               | `services/events.py`                                            | Efêmero                                 |

### 8.2 O que **não** é persistido no git

Todos os dados de usuário estão fora do git por design. `.gitignore`
bloqueia `storage/`, `*.db`, `.env`, `config/passwords.txt`,
`data/`, `inbox/`, `inbox_processed/`, `_scratch/`. O `pre-commit`
(`dev/check_forbidden_paths.py`) aplica a mesma regra em nível de hook
para defense-in-depth.

### 8.3 Fluxo "onde está o documento do usuário X?"

Tomando o upload como exemplo canônico:

```
Frontend (Next.js)
   │  multipart/form-data
   ▼
POST /api/documents/upload
   │  1. resolve Workspace do user autenticado (JWT → user.id → workspace)
   │  2. StorageService.validate_file (extensão, tamanho)
   │  3. StorageService.check_workspace_quota (MAX_STORAGE_PER_WORKSPACE_MB)
   │  4. SHA-256 → dedup em documents.content_hash
   │  5. StorageService.save_to_inbox → storage/{ws_id}/inbox/{safe_name}
   │  6. INSERT documents (stored_path, status=classifying, content_hash…)
   │  7. document_processor: unlock PDF + classifica banco/período/tipo
   │  8. UPDATE documents com resultado
   │  9. audit_log('document.upload', resource_id=doc.id, ip, ua)  ← novo
   │  10. db.commit()
   │
   ▼
Resposta 201 (DocumentUploadResponse)
```

Quem: `backend/app/api/documents.py::upload_documents`.
Onde (bytes): `storage/{workspace_id}/inbox/`.
Onde (metadata): tabela `documents`, scoped por `workspace_id`.
Quando: síncrono, dentro do próprio request HTTP.

Isolamento: `StorageService.resolve_path` rejeita qualquer path que escape
de `storage/{ws_id}/` (evita path traversal). FK `documents.workspace_id`
+ filtro em toda query impedem vazamento entre tenants.

### 8.4 Deleção e purge

- `DELETE /documents/{id}` — remove row no DB + unlink do arquivo em `storage/{ws_id}/inbox/` ou subdir. Emite `audit.document_delete`.
- `StorageService.delete_tenant(ws_id)` — apaga `storage/{ws_id}/` inteiro. Usado quando workspace é removido (cascade no DB cuida das tabelas).
- Não há soft-delete por padrão; auditoria preserva o histórico mesmo após hard-delete (FK usa `ON DELETE CASCADE` com `workspace_id`, mas `audit_logs` sobrevive ao usuário via `ON DELETE SET NULL` em `actor_user_id`).

### 8.5 Backups (F7, ainda não implementado)

- DB: `pg_dump` diário → S3/B2 (criptografado).
- `storage/`: snapshot incremental (restic/borg) → mesmo destino.
- Restore drill trimestral (runbook em `docs/` — a criar).

---

## 9. Padrões arquiteturais importantes

### "Wrap, Don't Rewrite" (Fase 0)

Scripts legados (E5=107KB, E6=197KB) têm lógica refinada. Em vez de reescrever:

1. Cada script ganha `_init_config(base_dir)` que (re)carrega globals de config
2. `main(root_dir=None)` aceita root injetado
3. Wrappers finos em `pipeline/stages/` (3-5 linhas)

Thread-safe, CLI-compatível, zero mudança na lógica interna.

### Materialize, Don't Inject (Fase 3)

Scripts lêem config do disco via `_init_config`. Em vez de modificar todos para aceitar dict:
- `materialize_config()` copia `config/` global → tenant, sobrescreve com DB
- Scripts continuam lendo de `tenant_root/config/` sem mudança

### Cancel Cooperativo (Fase 2→5)

- DB flag em `PipelineRun.status = "cancelled"`
- Task verifica entre stages (stage-boundary)
- Celery `revoke()` adicional
- Stages completos são preservados

### SystemExit Interception

Scripts legados usam `sys.exit(1)` para erros. Em Celery fork worker, isso mata o processo inteiro. O `_run_stage()` no orchestrator captura `SystemExit` e converte em `StageResult(success=False)`.

---

## 10. Segurança

### At-rest
- **Fernet** (symmetric encryption) para:
  - CPFs (FamilyMember.cpf_encrypted)
  - API keys LLM (LLMConfig.api_key_encrypted)
  - Senhas PDF (PasswordVault.encrypted_password)
- `FIN_FERNET_KEY` persistida em `.env` (nunca commitar)

### In-transit
- HTTPS via Traefik (prod) — Let's Encrypt auto-SSL
- CORS restritivo (só DOMAIN env var)
- JWT access tokens (15min prod / 24h dev) + refresh tokens (7d, httpOnly cookie)

### LGPD (F7)
- Termos aceitos no registro
- DELETE /api/account com cascade completo
- Export ZIP com dados pessoais
- **Audit log** — tabela `audit_logs` + `services/audit.py` registra upload/delete/retry-unlock de documentos (implementado F6.5 hardening). Expansão para auth/config/pipeline planejada em F7. Endpoint read-only: `GET /api/audit`.

---

## 11. Observabilidade (F7)

- **Sentry** — backend + frontend (error tracking, performance sampling 10%)
- **Structured logging** — structlog JSON em prod, `request_id` UUID por request
- **UptimeRobot** — health check monitoring
- **Custom telemetry** — tabela UsageMetric (privacy-first, sem third-party)

Para decisões arquiteturais detalhadas com rationale, ver [DECISIONS.md](DECISIONS.md).
