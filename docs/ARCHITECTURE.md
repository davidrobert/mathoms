# Fin — Arquitetura

> Documento técnico de referência. Atualizar quando stack ou modelo de dados mudar.
>
> **Última atualização:** 2026-04-15

---

## 1. Stack tecnológica

### Backend
- **FastAPI** (Python 3.11+) — API server
- **SQLAlchemy 2.0** (async + sync engines) — ORM
- **Alembic** — DB migrations (17 revisions)
- **Pydantic v2** — validação e serialização
- **Celery + Redis** — task queue + pub/sub para WebSocket
- **Fernet (cryptography)** — encryption at-rest (CPFs, API keys, senhas PDF)
- **LiteLLM + Instructor** — LLM orchestration (multi-provider)
- **Playwright** — PDF server-side rendering (headless Chromium)
- **pdfplumber, openpyxl, xlrd, pikepdf** — extração de documentos

### Frontend
- **Next.js 16.2** (App Router) + **React 19** + **TypeScript 6**
- **Tailwind CSS 4.2** com design tokens gerados (`tokens.json` → CSS)
- **base-ui/react + shadcn** (18 primitivos UI)
- **Recharts 3.8** — visualizações (SVG, print-native)
- **next-themes** — dark mode
- **Sonner** — toast notifications
- **Lucide React** — ícones
- **date-fns** — formatação de datas
- **xlsx** — export CSV/XLSX

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
│  19 rotas (5 públicas + 14 protegidas)                        │
│  117 componentes (report: 50, tasks: 9, charts: 3, ui: 18)   │
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

Design tokens (tokens.json)
    → build.py → CSS (frontend + E6 standalone)

Report layout (report_layout.yaml)
    → codegen_report_layout.py → TypeScript + Pydantic
```

---

## 4. Modelo de dados (20 models)

### Auth + Core

```
User
  id (UUID), email (unique), hashed_password, full_name, is_active
  token_version (int — JWT invalidation on membership removal)
  created_at
  → workspaces, memberships

Workspace
  id (UUID), name, family_surname, owner_id (FK→User), created_at
  → owner, reports, documents, vault_passwords, pipeline_runs
  → family_members, categories, configs (pipeline/institution/layout)
  → llm_config, transaction_overrides, notifications
  → members, invitations

WorkspaceMember
  id (UUID), workspace_id (FK), user_id (FK), role (owner|member|viewer)
  invited_by, joined_at
  unique(workspace_id, user_id)

WorkspaceInvitation
  id (UUID), workspace_id (FK), email, role
  token_hash (SHA-256, indexed), status (pending|accepted|revoked|expired)
  invited_by, expires_at (TTL 72h), accepted_at, revoked_at, created_at
```

### Documents & Pipeline

```
Document
  id (UUID), workspace_id (FK, indexed), original_name, stored_path
  doc_type (enum: bank_statement|credit_card_bill|investment_report|irpf|
            e1_members_json|e1_5_baseline_json|other)
  bank_code, period
  status (enum: uploaded|unlocking|classifying|ready|needs_password|
          processing|processed|error)
  classification_meta (JSON), file_size_bytes, content_hash (indexed)
  content_type, error_message
  classification_confidence (Float, 0.0–1.0)
  needs_review (Bool, indexed)
  possible_duplicate_of_id (String, soft FK)
  uploaded_at

PasswordVault
  id (UUID), workspace_id (FK), label, encrypted_password (Fernet), created_at

PipelineRun
  id (UUID), workspace_id (FK, indexed)
  status (enum: pending|running|completed|partial_failure|failed|cancelled|
          needs_review|resuming)
  current_stage, failed_at_stage, config_snapshot (JSON)
  total_documents, reprocess_all
  started_at, completed_at, tier_at_run (free|premium)
  paused_at_stage, celery_task_id

PipelineStageLog
  id (UUID), pipeline_run_id (FK), stage_name
  status (enum: pending|running|completed|failed|skipped|skipped_free_tier|
          needs_review)
  started_at, completed_at, output_json, error_message

Report
  id (UUID), workspace_id (FK), pipeline_run_id (FK→PipelineRun, SET NULL)
  title, period, html_path, analysis_json_path (E5 JSON snapshot, F9)
  tasks_snapshot_json (immutable snapshot, F8.3)
  size_bytes, score, patrimonio_liquido, created_at
```

### Goals & Tasks (F8)

```
Goal
  id (UUID), workspace_id (FK, indexed)
  type (INDEPENDENCIA_FINANCEIRA|APORTE_MENSAL|DOLARIZACAO|ALOCACAO_ALVO|
        PLANNING_CONTEXT)
  params_json, derived_json
  effective_from (Date), effective_to (Date, nullable — active when NULL)
  created_by (FK→User), notes, is_template, created_at, updated_at
  unique per (workspace, type, effective_to=NULL)

Task
  id (UUID), workspace_id (FK), number (unique per workspace)
  title, description
  priority (S|R|O), category
  status (pending|in_progress|done|cancelled|blocked)
  deadline_kind (HARD_DATE|MONTH|QUARTER|CONDITIONAL|UNSCHEDULED)
  deadline_date, deadline_label
  parent_task_id (soft FK), related_transaction_id, related_goal_id
  created_by (FK→User), created_from (manual|seed|llm_suggestion)
  created_at, updated_at, extra_json
  → attachments, suggestions

TaskSuggestion
  id (UUID), workspace_id (FK), task_id (optional FK)
  title, description, estimated_priority
  source (e5n_llm|cross_validation|system_rule)
  status (pending|approved|rejected|merged), confidence
  reviewed_by, reviewed_at, reason_rejected, created_at

TaskAttachment
  id (UUID), workspace_id (FK), task_id (FK)
  original_filename, stored_path, file_size_bytes, content_type
  uploaded_by (FK→User), uploaded_at
```

### Config (por workspace)

```
FamilyMember
  id (UUID), workspace_id (FK, indexed), key, full_name, short_name
  cpf_encrypted (Fernet), birth_date, role, order, extra (JSON)
  → accounts[]

BankAccount
  id (UUID), member_id (FK, indexed), institution_code, account_type
  agency, account_number, label

Category
  id (UUID), workspace_id (FK, indexed), code (unique per workspace)
  name, category_type (expense|income), monthly_cap, order
  → keywords[]

CategoryKeyword
  id (UUID), category_id (FK), keyword (indexed)

PipelineConfig      (id, workspace_id unique, config_json)
InstitutionConfig   (id, workspace_id unique, config_json)
ReportLayout        (id, workspace_id unique, config_json)
```

### LLM, Reviews & Observability

```
LLMConfig
  id (UUID), workspace_id (unique), provider (anthropic|openai|ollama|...)
  api_key_encrypted (Fernet), model_name, max_tokens, temperature

StageReview
  id (UUID), pipeline_run_id (FK), stage_name
  status (pending|approved|edited)
  output_json, edited_output_json, reviewer_notes, reviewed_at

TransactionOverride
  id (UUID), workspace_id (FK, indexed), transaction_hash (indexed)
  original_category, new_category, notes, reviewed, created_at

Notification
  id (UUID), workspace_id (FK, indexed), severity (info|warning|critical)
  title, message, source, is_read, created_at

AuditLog
  id (UUID), workspace_id (FK, indexed), action (indexed)
  resource_type, resource_id, actor_user_id (FK→User, SET NULL)
  details (JSON), ip_address, user_agent, created_at (indexed)

FeatureFlag
  id (UUID), workspace_id (FK, indexed), flag_name (indexed)
  enabled, created_at, updated_at
  unique(workspace_id, flag_name)
```

---

## 5. API Surface (17 routers, ~80 endpoints)

| Router | Endpoints-chave |
| --- | --- |
| **auth.py** | POST register/login, GET /me |
| **workspaces.py** | GET /me/workspaces, CRUD members, CRUD invitations |
| **invitations.py** | GET preview (public), POST accept |
| **documents.py** | POST upload (multipart batch), GET list, DELETE, POST retry-unlock |
| **pipeline.py** | POST run, GET runs, cancel, resume, reviews |
| **reports.py** | GET list/detail/html/download.html/download.pdf/data/tasks |
| **transactions.py** | GET list/export, POST override, DELETE override |
| **config.py** | CRUD members/accounts/categories, GET/PUT pipeline/institutions/layout, import/export |
| **goals.py** | POST compute IF, GET/PUT IF, history, goal↔tasks |
| **tasks.py** | CRUD tasks, status transitions, upcoming, export.md, progress, scan-deadlines, attachments, suggestions (approve/reject/merge) |
| **vault.py** | CRUD passwords |
| **llm.py** | CRUD LLM config, test, tier |
| **dashboard.py** | GET dashboard, alerts |
| **notifications.py** | GET list, PATCH read, DELETE |
| **audit.py** | GET audit logs |
| **feature_flags.py** | GET/PUT workspace flags |
| **ws.py** | WebSocket /pipeline/runs/{id}/ws (JWT auth, Redis Pub/Sub) |

---

## 6. Services (26)

| Service | Responsabilidade |
| --- | --- |
| **pipeline_service** | Trigger, cancel, resume pipeline runs |
| **pipeline_adapter** | DB ↔ pipeline JSON format (goals, tasks, family_members) |
| **document_processor** | Upload pipeline: unlock → classify → dedupe → route |
| **content_classifier** | Content-first classification (regex + LLM fallback) |
| **config_materializer** | Materializa 5 configs editáveis (DB → disco per-tenant) |
| **goal_service** | IF goal computation (FV anuidade), CRUD versionado append-only |
| **task_service** | Task CRUD + status transitions + dependencies + export MD |
| **task_suggestion_service** | Suggestion queue: create/approve/reject/merge |
| **task_notification_service** | Scan deadlines → notifications (overdue/upcoming) |
| **task_progress_service** | % executado (BRL parser + match transactions) |
| **task_attachment_service** | Upload/list/delete task attachments |
| **report_tasks_snapshot_service** | Snapshot imutável de tasks no momento do relatório |
| **dashboard_service** | KPIs, charts, alerts, data freshness |
| **transaction_service** | Load transactions E4 JSON + overrides + filtering |
| **audit_service** | Log audit events (action, resource, actor, IP) |
| **membership_service** | Workspace members: list, update role, remove |
| **invitation_service** | Create/accept/revoke/list invitations (token SHA-256) |
| **feature_flags_service** | Defaults + workspace overrides, fail-safe |
| **storage** | File I/O: quota, validation, save to inbox/attachments |
| **vault** | Encrypt/decrypt passwords at-rest (Fernet) |
| **pdf_renderer** | Server-side PDF via Playwright headless Chromium |
| **events** | Redis Pub/Sub publisher para WebSocket |
| **retry_config** | Retry strategies & backoff |
| **seed** | Populate initial workspace data (demo/template) |
| **tarefas_md_parser** | Parse legacy tarefas.md → task objects |

---

## 7. Pipeline stages

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
| E0-unlock      | det.       | Desbloqueia PDFs/ZIPs protegidos usando vault                    |
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
| E6             | det.       | Exporta HTML standalone (render primário é React nativo, F9)     |
| E7-crossval    | det.       | 14 checks automáticos de qualidade                               |
| E7-review      | **LLM**    | Review holístico (insights, recomendações, ajustes de score)     |
| E7-apply       | det.       | Aplica review ao E5 JSON                                         |
| E6-final       | det.       | Re-render final com review incorporado                           |

> **Render do relatório (F9):** Desde F9, o relatório é renderizado como rota React nativa (`/reports/[id]`) consumindo `GET /reports/{id}/data`. O E6 gera HTML standalone para exportação (email, backup, impressão offline). PDF server-side via Playwright.

---

## 8. Frontend — Rotas e componentes

### Rotas (19 total)

**Públicas:**
| Rota | Página |
| --- | --- |
| `/` | Redirect → dashboard ou login |
| `/login` | Login (email/password, suporta `?next=`) |
| `/register` | Registro |
| `/invite/[token]` | Aceite de convite (preview público, aceite com auth) |

**Protegidas (dentro de `(app)` com AppShell):**
| Rota | Página |
| --- | --- |
| `/dashboard` | KPIs, charts, alertas, UpcomingTasksWidget |
| `/documents` | Upload drag-and-drop, status badges, retry-unlock |
| `/pipeline` | Trigger + progress (PhaseStepper 4 fases) |
| `/transactions` | Filtros, busca, override de categoria, export CSV/XLSX |
| `/reports` | Lista de relatórios (metadata, score, tamanho) |
| `/reports/[id]` | **Render nativo React** (18 seções, 13 cards, 8 charts Recharts) |
| `/plano` | Overview meta IF (3 KPI cards + parâmetros) |
| `/plano/meta-if` | Editor da meta IF com simulador live |
| `/plano/meta-if/wizard` | Wizard 4 passos (renda → TRS → horizonte → confirm) |
| `/plano-de-acao` | Tasks: 3 views (priority/deadline/category) + CRUD + drawer |
| `/plano-de-acao/sugestoes` | Fila de sugestões approve/reject 1-click |
| `/vault` | CRUD senhas (encrypted at-rest) |
| `/config` | Settings: workspace, membros, acessos, categorias, pipeline, layout |

### Componentes (117 total)

- **Report:** ReportShell, ReportHeader, ReportToc, ReportSection, 13 cards, 8 charts, 9 section components
- **Tasks:** TaskCard, TaskDrawer, TaskFormDialog, TaskStatusPill, TaskPriorityChip, TaskDeadlineBadge, TaskAttachments, UpcomingTasksWidget, TaskProgressCard
- **Shell:** AppShell, AuthBootstrap, ErrorBoundary, WorkspaceSwitcher, ViewerBanner
- **Data:** DataTable, DateRangePicker, ConfirmDialog, PhaseStepper
- **Display:** KPICard, StatusBadge, Delta, EmptyState, Spinner, NotificationCenter, ThemeToggle
- **Charts:** FinAreaChart, FinBarChart, FinPieChart (wrappers Recharts)
- **UI base (shadcn):** 18 primitivos (button, card, input, label, table, dialog, alert-dialog, select, sheet, badge, tabs, separator, skeleton, switch, textarea, tooltip, sonner)

### Hooks e utils

| Arquivo | Propósito |
| --- | --- |
| `api.ts` | API client completo (todos os endpoints, types, token management) |
| `useCurrentUser.ts` | User autenticado (cache module-level) |
| `useCurrentWorkspace.ts` | Workspace atual (localStorage + /me/workspaces) |
| `usePermissions.ts` | Derives permissions from role (isOwner, canWrite, etc.) |
| `usePipelineWS.ts` | WebSocket hook (auto-reconnect, terminal events) |
| `format.ts` | 9 formatters (currency BRL/USD, percent, delta, compact, doc/pipeline status) |
| `export.ts` | Export CSV (BOM UTF-8, `;`) + XLSX (auto-width) |
| `pipelinePhases.ts` | 14 backend stages → 4 user-facing phases |
| `roleLabels.ts` | PT-BR labels (Responsável/Coadministrador/Acompanha) |

---

## 9. Fluxos-chave

### Upload → Classificação → Pipeline

```
User drag-and-drop PDF
    ↓
POST /api/documents/upload
    ↓
StorageService.save_to_inbox()  →  storage/{ws_id}/inbox/
    ↓
process_uploaded_document():
  1. JSON? → detect E1/E1.5 type (structure-based, bypasses classifier)
  2. PDF encrypted? → try vault passwords → unlock OR needs_password
  3. classify_document() — content-first pipeline:
     a. Extract text preview (pdfplumber/openpyxl/csv)
     b. Content regex (content_classifier.py) → institution + doc_type + period
     c. If confidence < 0.8 → LLM fallback (anthropic SDK, classify_by_llm)
     d. If confidence < 0.7 → doc_type=other, needs_review=true
     ⚠ Filename is NOT used — bank exports have wrong/arbitrary names
  4. Dedupe:
     a. Exact: SHA-256 hash → rejeita se (workspace_id, content_hash) existe
     b. Fuzzy: se (doc_type, bank_code, period) já existe → possible_duplicate_of_id
  5. route_to_data_dir() → storage/{ws_id}/data/{dest_group}/
    ↓
Document.status = "ready", classification_confidence, needs_review
    ↓
User clica "Gerar Relatório"
    ↓
POST /api/pipeline/run → materialize_config() → Celery task
    ↓
Pipeline stages rodam em ordem → PipelineStageLog por stage
    ↓
WebSocket /ws publica eventos via Redis Pub/Sub
    ↓
E6 produz HTML → Report criado no DB (com analysis_json_path + tasks_snapshot)
    ↓
Frontend renderiza nativamente via GET /reports/{id}/data (React, F9)
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
  4. pipeline_adapter: materializa goals.json + tarefas.md do DB
    ↓
Pipeline scripts lêem de storage/{ws_id}/config/ via _init_config(root_dir)
    ↓
Zero mudança na lógica interna dos scripts legados
```

---

## 10. Estrutura de pastas

```
fin-current/
├── backend/
│   ├── app/
│   │   ├── api/               # 17 routers REST + WebSocket
│   │   │   ├── auth.py, workspaces.py, invitations.py
│   │   │   ├── documents.py, vault.py, pipeline.py
│   │   │   ├── config.py, llm.py, reports.py
│   │   │   ├── transactions.py, dashboard.py, notifications.py
│   │   │   ├── goals.py, tasks.py, audit.py, feature_flags.py
│   │   │   └── ws.py          # WebSocket (JWT auth, Redis Pub/Sub)
│   │   ├── core/              # Settings, database, security, deps
│   │   ├── models/            # 20 SQLAlchemy models
│   │   ├── schemas/           # Pydantic request/response
│   │   ├── services/          # 26 services (business logic)
│   │   ├── scripts/           # Operational scripts (seed, reclassify, cutover)
│   │   ├── generated/         # Codegen (report_layout.py from YAML)
│   │   ├── tasks/
│   │   │   └── pipeline_task.py  # Celery @task principal
│   │   ├── worker.py          # Celery app config
│   │   └── main.py            # FastAPI app
│   ├── alembic/               # 17 DB migrations
│   ├── tests/                 # ~50 test files, ~450 tests
│   │   ├── factories/         # Type-safe builders
│   │   ├── fixtures/          # LLM mock, pipeline runs, PDF generator
│   │   └── regressions/       # Anti-regression bank (24 tests)
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
├── scripts/                   # Pipeline scripts determinísticos (CLI + worker)
│   ├── e0_audit.py, e0_route.py, e0_unlock.py
│   ├── e15_consolidate.py, e2_extract.py
│   ├── e3_reconcile.py, e4_categorize.py
│   ├── e5_analyze.py, e5n_narrativas.py
│   ├── e6_render.py, e7_review.py, e_reset.py
│   └── pipeline_common.py
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── login/, register/, invite/[token]/
│   │   │   └── (app)/         # Route group com AppShell
│   │   │       ├── dashboard/, documents/, pipeline/
│   │   │       ├── transactions/, reports/, reports/[id]/
│   │   │       ├── plano/, plano/meta-if/, plano/meta-if/wizard/
│   │   │       ├── plano-de-acao/, plano-de-acao/sugestoes/
│   │   │       └── vault/, config/
│   │   ├── components/
│   │   │   ├── ui/            # 18 shadcn/base-ui primitives
│   │   │   ├── charts/        # 3 Recharts wrappers
│   │   │   ├── tasks/         # 9 task components
│   │   │   ├── report/        # 50 report components (shell, cards, charts, sections)
│   │   │   └── *.tsx          # Compositions (AppShell, KPICard, etc.)
│   │   ├── generated/         # Codegen (report-layout.ts from YAML)
│   │   ├── types/             # Tipos fortes do E5 (análise financeira)
│   │   ├── hooks/             # React hooks (useReportData, etc.)
│   │   ├── styles/            # tokens.css gerado pelo design-tokens build
│   │   └── lib/
│   │       ├── api.ts         # API client completo + types
│   │       ├── format.ts, export.ts
│   │       ├── useCurrentUser.ts, useCurrentWorkspace.ts, usePermissions.ts
│   │       ├── usePipelineWS.ts
│   │       └── utils.ts       # cn()
│   └── package.json
│
├── design-tokens/
│   ├── tokens.json            # Fonte única de verdade (cores, tipografia, spacing)
│   └── build.py               # Gera CSS para frontend + E6 standalone
│
├── config/                    # Configs globais (18 arquivos + schemas + templates)
│   ├── pipeline.json          # Parâmetros operacionais + report_version
│   ├── family_members.json, categorization.json, institutions.json
│   ├── definitions.md, methodology.md, report_spec.md
│   ├── report_layout.yaml     # Codegen source → TS + Pydantic
│   ├── scoring.json, cenarios.json, taxas.json, parametros_fiscais.json
│   ├── schemas/               # 6 JSON schemas (baseline, goals, report_layout)
│   └── templates/             # 7 templates (HTML, MD, CSS)
│
├── dev/                       # Dev tooling
│   ├── commit.py, check_forbidden_paths.py, validate_commit_msg.py
│   └── codegen_report_layout.py
│
├── storage/                   # Per-tenant (gitignored)
│   └── {workspace_id}/
│       ├── inbox/, data/, processed/, output/, members/, config/
│
├── _archive/                  # Arquivos legados preservados
├── docs/                      # Documentação técnica
├── tests/                     # Pipeline tests (~270)
├── docker-compose.yml         # Redis (dev)
├── docker-compose.test.yml    # PG 5433 + Redis 6380 (test isolation)
├── .github/workflows/ci.yml   # 7 CI jobs + all-green gate
└── pyproject.toml             # Package fin-pipeline v0.2.0
```

---

## 11. Onde moram os dados

### Mapa por tipo de dado

| Dado                                              | Onde vive                                                   | Persistido por                                                  |
| ------------------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------- |
| Código-fonte + docs                               | Git (`github.com/.../fin-current`)                          | Desenvolvedor via `git commit`                                  |
| Schema do banco                                   | Migrations Alembic (`backend/alembic/versions/`)            | Desenvolvedor (`alembic revision`)                              |
| Config global (fallback de todo tenant)           | `config/*.{json,yaml,md}`                                   | Versionado no repo                                              |
| **Usuário** (email, senha hash)                   | `users` (DB)                                                | `POST /auth/register`                                           |
| **Workspace** (tenant)                            | `workspaces` (DB)                                           | Criado no primeiro login do owner                               |
| **Workspace members**                             | `workspace_members` (DB)                                    | `POST /invitations/{token}/accept`                              |
| **Documento uploadado** (metadata)                | `documents` (DB)                                            | `POST /documents/upload`                                        |
| **Documento uploadado** (bytes)                   | `storage/{workspace_id}/inbox/{safe_name}`                  | `StorageService.save_to_inbox`                                  |
| Documento classificado (após E0)                  | `storage/{workspace_id}/data/<subdir>/`                     | `document_processor` → `StorageService.move_to_data`            |
| Senhas de PDF (vault)                             | `password_vault` (DB), `encrypted_password` Fernet          | `POST /vault/passwords`                                         |
| Chaves API LLM do usuário (BYOK)                  | `llm_configs` (DB), `api_key_encrypted` Fernet              | `POST /llm/config`                                              |
| CPFs dos membros                                  | `family_members.cpf_encrypted` (DB), Fernet                 | `POST /config/family-members` (ou E1 LLM)                       |
| Goals (metas financeiras)                         | `goals` (DB), versionado append-only                        | `PUT /goals/if`                                                 |
| Tasks (backlog de ações)                          | `tasks`, `task_suggestions`, `task_attachments` (DB)        | CRUD via `/tasks` endpoints                                     |
| Feature flags                                     | `feature_flags` (DB) + defaults em código                   | `PUT /feature-flags/{flag}`                                     |
| Config materializada por tenant (input do E2–E7)  | `storage/{ws_id}/config/*`                                  | `config_materializer.materialize_config()`                      |
| Artefatos intermediários (`-2_extract.json`, …)   | `storage/{ws_id}/processed/E2_extracts/` etc.               | Scripts E2–E5 executando dentro do tenant_root                  |
| Análise final (`analise_financeira-5_analysis.json`) | `storage/{ws_id}/processed/E5_analysis/`                 | Stage E5                                                        |
| Relatório HTML final                              | `storage/{ws_id}/output/` e row em `reports` (DB)           | Stage E6 + handler que registra `Report`                        |
| Tasks snapshot no relatório                       | `reports.tasks_snapshot_json` (DB)                          | `build_snapshot_sync` na criação do Report                      |
| Audit log                                         | `audit_logs` (DB)                                           | `audit_service.log()` dentro da transação                       |
| Tasks queue state                                 | Redis (broker + result backend)                             | Celery                                                          |
| Eventos WebSocket                                 | Redis Pub/Sub                                               | `services/events.py`                                            |

### O que **não** é persistido no git

Todos os dados de usuário estão fora do git por design. `.gitignore`
bloqueia `storage/`, `*.db`, `.env`, `config/passwords.txt`,
`data/`, `inbox/`, `inbox_processed/`, `_scratch/`. O `pre-commit`
(`dev/check_forbidden_paths.py`) aplica a mesma regra em nível de hook.

---

## 12. Padrões arquiteturais

### "Wrap, Don't Rewrite" (F0)
Scripts legados (E5=107KB, E6=197KB) têm lógica refinada. Em vez de reescrever:
1. Cada script ganha `_init_config(base_dir)` que (re)carrega globals de config
2. `main(root_dir=None)` aceita root injetado
3. Wrappers finos em `pipeline/stages/` (3-5 linhas)

### Materialize, Don't Inject (F3)
Scripts lêem config do disco via `_init_config`. `materialize_config()` copia `config/` global → tenant, sobrescreve com DB. Scripts continuam lendo de `tenant_root/config/` sem mudança.

### Pipeline Adapter (F8)
`pipeline_adapter.py` é a fachada DB → JSON para entidades migradas (goals, tasks, family_members). Scripts recebem JSONs materializados no disco, sem saber que a fonte é o DB.

### Cancel Cooperativo (F5)
DB flag `PipelineRun.status = "cancelled"`. Task verifica entre stages. Celery `revoke()` adicional. Stages completos preservados.

### SystemExit Interception
Scripts legados usam `sys.exit(1)`. Em Celery fork worker, `_run_stage()` no orchestrator captura `SystemExit` → converte em `StageResult(success=False)`.

---

## 13. Segurança

### At-rest
- **Fernet** (symmetric encryption) para CPFs, API keys LLM, senhas PDF
- `FIN_FERNET_KEY` persistida em `.env` (nunca commitar)

### In-transit
- HTTPS via Traefik (prod) — Let's Encrypt auto-SSL
- CORS restritivo. JWT access tokens (15min prod / 24h dev)
- `User.token_version` invalida tokens stale ao remover membro

### Multi-tenant isolation
- `workspace_id` FK + filtro em toda query
- `StorageService.resolve_path` rejeita path traversal
- 27 tests paramétricos (F6.5) — 0 vazamentos confirmados
- AST-based tenancy lint em CI

### LGPD (F7, planejado)
- DELETE /api/account com cascade completo
- Export ZIP com dados pessoais
- Audit log imutável (ON DELETE SET NULL em actor_user_id)

---

## 14. Testes

| Camada | Framework | Contagem | Foco |
| --- | --- | --- | --- |
| Backend pytest | pytest | ~450 | Models, services, endpoints, isolation, regression |
| Frontend Vitest | Vitest + RTL + MSW | ~350 | Components, hooks, formatters, API client |
| E2E | Playwright | ~25 specs | Golden Path, fluxos críticos cross-browser |
| Pipeline | pytest | ~270 | Parsers, E2-E7, golden files |

CI: `.github/workflows/ci.yml` com 7 jobs (lint, PII lint, pipeline, backend+Redis, frontend, E2E condicional, all-green gate).

---

## 15. Observabilidade (F7, planejado)

- **Sentry** — backend + frontend (error tracking, performance 10%)
- **Structured logging** — structlog JSON em prod, `request_id` UUID
- **UptimeRobot** — health check
- **Custom telemetry** — UsageMetric (privacy-first)

Para decisões arquiteturais detalhadas com rationale, ver [DECISIONS.md](DECISIONS.md).
