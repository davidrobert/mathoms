# Mathoms AI — Arquitetura

> Documento técnico de referência. Atualizar quando stack ou modelo de dados mudar.
>
> **Última atualização:** 2026-04-19 (migração infra + domínio — fases 1-8 foundation)

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
- **jsonschema** — validação de artefatos pipeline (E2/E4/E5 schemas)

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
│  │   stage_spec.py (STAGE_REGISTRY)  stage_config.py        │  │
│  │   artifact_store.py (Protocol + Disk/InMemory impls)     │  │
│  │   domain/ (models + services — Money, Reconciliation…)   │  │
│  │   stages/ (wrappers) + llm/prompts/ + llm/validators/    │  │
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
    → build.py → CSS (frontend)

Report layout (report_layout.yaml)
    → codegen_report_layout.py → TypeScript + Pydantic
```

---

## 4. Modelo de dados (21 models)

> **Contagem real** (2026-04-24): `ls backend/app/models/*.py | grep -v __init__` → 21 arquivos. `DB_SCHEMA_REFERENCE.md` (auto-gerado) lista as tabelas expandidas incluindo associativas e partial indexes.

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

PipelineArtifact (ADR-082)
  id (INTEGER PK autoincrement)
  workspace_id (FK→Workspace, CASCADE, indexed)
  pipeline_run_id (FK→PipelineRun, CASCADE, indexed)
  stage (VARCHAR(50))           # "E2", "E3", "E5"... Fases 1-8
                                # "reconcile_transactions"... pós-Fase 9
  artifact_key (VARCHAR(255))   # stem do doc (E2) ou nome canônico (E3+)
  document_id (FK→Document, SET NULL)  # nullable, só preenchido em E2-*
  content_json (JSON/JSONB)
  schema_version, byte_size, created_at
  UNIQUE(pipeline_run_id, stage, artifact_key)
  INDEX(workspace_id, stage, artifact_key)
  INDEX(document_id)

Report
  id (UUID), workspace_id (FK), pipeline_run_id (FK→PipelineRun, SET NULL)
  title, period, analysis_artifact_id (FK→PipelineArtifact, SET NULL — ADR-131)
  tasks_snapshot_json (immutable snapshot, F8.3)
  score, patrimonio_liquido, created_at
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
  output_json, edited_output_json, reviewed_at

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

## 4.1. Domain glossary (rules-as-code)

Mathoms é um produto de **planejamento patrimonial** com taxonomias e
regras de domínio que vivem no código (rules-as-code, [ADR-143](DECISIONS.md#adr-143--docsmethodology-é-rules-as-code-sprint-a76)).
Esta seção é índice rápido — para o "porquê" + alternativas consideradas,
ler a ADR linkada; para o "como" + matching exato, ler o docstring do
módulo enforcer.

| Conceito | Source of truth (código) | ADR canônica |
| --- | --- | --- |
| Membros familiares (titular/cônjuge/dependente) | `backend/app/models/family_member.py::FamilyMember.role` + `family_members.json` workspace-specific | — |
| Contas bancárias + override de tier de fonte | `backend/app/models/family_member.py::BankAccount.source_tier` | [ADR-146](DECISIONS.md#adr-146--e3-source-hierarchy--bankaccountsource_tier-schema) |
| Instituições financeiras (catálogo + workspace overrides) | `backend/app/models/institution_catalog.py` + resolver | [ADR-137](DECISIONS.md#adr-137--catalog--override-resolver-para-categorization-e-institutions) |
| Categorias de receita/despesa (catálogo + workspace overrides) | `backend/app/models/category_template.py` + `workspace_category_override.py` + resolver | [ADR-137](DECISIONS.md#adr-137--catalog--override-resolver-para-categorization-e-institutions) |
| 7 categorias canonical da composição patrimonial | `pipeline/domain/services/patrimonio_calculator.py::PatrimonioCalculator` (módulo docstring) | [ADR-145](DECISIONS.md#adr-145--7-categorias-canonical-da-composição-patrimonial) |
| Hierarquia de fontes E3 + tie-breaking de reconciliação | `pipeline/domain/services/source_tier.py` + `reconciliation_service.py` (docstring) | [ADR-146](DECISIONS.md#adr-146--e3-source-hierarchy--bankaccountsource_tier-schema) |
| Programas de milhagem — método de valuation universal + storage workspace-scoped (`<workspace>/notes/milhas.md`, gitignored) | `scripts/e5_analyze.py::parse_milhas_md_content` (docstring) | [ADR-147](DECISIONS.md#adr-147--milhas-valuation-methodology-universal--storage-workspace-scoped) |
| Decisões de planejamento patrimonial (event-sourced) | `backend/app/models/decision.py::Decision` + `DecisionEvent` | [ADR-136](DECISIONS.md#adr-136--decision-aggregate-event-sourced-com-supersede-chain) |
| Parâmetros fiscais (IRPF, lucro presumido, PGBL) versionados por ano | `backend/app/models/fiscal_parameter.py::FiscalParameter` | [ADR-135](DECISIONS.md#adr-135--versionamento-temporal-de-séries-fiscais-e-câmbio) |
| IRPF completo (renda + imposto + dependentes + dedutíveis) — KPIs renda anual líquida, alíquota dual, capacidade PGBL, split trabalho×capital | `pipeline/llm/schemas/e16_irpf_full.py::IRPFFullOutput` + `pipeline/domain/services/irpf_analyzer.py::IRPFAnalyzer` | [ADR-157](DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full) |
| Câmbio + indexadores temporais | `backend/app/models/market_rate.py::MarketRate` | [ADR-135](DECISIONS.md#adr-135--versionamento-temporal-de-séries-fiscais-e-câmbio) |
| Códigos de tipo de documento + roteamento E0 | `scripts/e0_route.py::DOC_TYPE_PATTERNS` | — |
| Naming pattern de artefatos (`[entidade]_[tipo]_[periodo]-N_stage.ext`) | `CLAUDE.md §Convenções de naming de artefatos` | — |
| Money policy (`Decimal` string · `int64` cents · nunca float) | `pipeline/domain/models/transaction.py::Money` | [ADR-090](DECISIONS.md#adr-090--money-nunca-é-float) |
| Cenário de estresse "cônjuge sem trabalhar" — chave de payload `cenarios_conjuge` (universal estável, ADR-166) | `pipeline/domain/services/cenarios_conjuge_analyzer.py::CenariosConjugeAnalyzer` + `pipeline/domain/services/e5_serialization.py::build_e5_output` | [ADR-166](DECISIONS.md#adr-166--schema-estável-cenarios_conjuge-no-payload-e5) |
| Mês fechado / relatório publicado (invariante temporal de imutabilidade) | `backend/app/services/report_publication.py::is_month_closed` + `ReportPublication` model | [ADR-186](adr/186-relatorio-publicado-imutavel-mes-fechado.md) — ver também [REPORT_PUBLICATION.md](REPORT_PUBLICATION.md) |

**Regra geral:** nada de regras de produto em markdown editorial. Toda
regra que o código enforce vive no código (docstring) + ADR (porquê);
toda configuração workspace-specific vive em DB; toda nota livre
workspace-specific vai para `<workspace>/notes/` (gitignored). `docs/methodology/`
é um path **proibido** desde A7.6 — `dev/check_forbidden_paths.py`
bloqueia recriação acidental.

---

## 5. API Surface (20 routers, ~80 endpoints)

> **Contagem real** (2026-04-24): `ls backend/app/api/*.py | grep -v __init__` → 20 arquivos de router.

| Router | Endpoints-chave |
| --- | --- |
| **auth.py** | POST register/login, GET /me |
| **workspaces.py** | GET /me/workspaces, CRUD members, CRUD invitations |
| **invitations.py** | GET preview (public), POST accept |
| **documents.py** | POST upload (multipart batch), GET list, DELETE, POST retry-unlock |
| **pipeline.py** | POST run, GET runs, cancel, resume, reviews |
| **reports.py** | GET list/detail/download.pdf/data/tasks |
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

## 6. Services (42 top-level + `internal_ops/` submódulo)

> **Contagem real** (2026-04-24): `ls backend/app/services/*.py | grep -v __init__` → 42. Tabela abaixo é **parcial** (originalmente "26") e precisa de rodada de sync — entradas conhecidas faltantes: `artifact_reader`, `canonical_routing`, `classification_telemetry`, `config_defaults`, `document_classification`, `document_duplicates`, `document_extract_json_service`, `document_pipeline_sync`, `document_reclassify_bulk_service`, `document_retry_service`, `document_upload_service`, `password_vault_reader`, `pipeline_client`, `premissas_snapshot`, `report_lineage`, `stage_duration_estimator`, mais `internal_ops/` submódulo (F7F-Local, ADR-116). Não duplicar lista — fonte de verdade é o filesystem.

| Service | Responsabilidade |
| --- | --- |
| **pipeline_service** | Trigger, cancel, resume pipeline runs |
| **pipeline_adapter** | DB ↔ pipeline JSON format (goals, tasks, family_members) |
| **db_artifact_store** | Impl SQLAlchemy do `ArtifactStore` protocol (ADR-083) |
| **pipeline_artifact_repository** | Queries cross-run em `pipeline_artifacts` (ADR-082) |
| **document_processor** | Upload pipeline: unlock → classify → dedupe → route |
| **content_classifier** | Content-first classification (regex + LLM fallback) |
| **config_materializer** | Materializa 5 configs editáveis (DB → disco per-tenant) |
| **goal_service** | Goal computation (IF via FV anuidade, Aporte, Dolar, Alocação) + CRUD versionado append-only (`create_goal_version` genérica, helpers tipados) |
| **task_service** | Task CRUD + status transitions + dependencies + export MD |
| **task_suggestion_service** | TaskSuggestion (legado LLM): create/approve/reject/merge — distinto de `Suggestion` (ADR-153) |
| **task_notification_service** | Scan deadlines → notifications (overdue/upcoming) |
| **task_progress_service** | % executado (BRL parser + match transactions) |
| **task_attachment_service** | Upload/list/delete task attachments |
| **report_tasks_snapshot_service** | Snapshot imutável de tasks no momento do relatório |
| **suggestion_service** | `Suggestion` aggregate (ADR-153 · Direção E · Onda 5): proposal imutável + state machine accept/dismiss/modify; pipeline E5 gera via `SuggestionGenerator` (5 regras canônicas); aceitar cria Decision com `derived_from_suggestion_id` |
| **workspace_notes_service** | `WorkspaceNotes` aggregate (ADR-154 · Direção E · Onda 1): notas livres por workspace, multi-row com pin; substitui `report_notes` (deprecated) |
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
→ E3 → E4 → E5 → E5.N
→ E7-crossval → E7-review (LLM) → E7-apply
```

### Ordem determinística (`DETERMINISTIC_ORDER` — free)

```
E0-audit → E1.5c (skip se sem baseline)
→ E2-faturas → E2-extratos
→ E3 → E4 → E5 → E5.N
→ E7-crossval → E7-apply (skip)
```

> **Nota:** stages `E6` e `E6-final` foram removidos em
> [ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side) —
> o relatório não é mais artefato de pipeline. Render atual: ver §**Render do relatório**
> (logo após a tabela de stages abaixo).

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
| E7-crossval    | det.       | 14 checks automáticos de qualidade                               |
| E7-review      | **LLM**    | Review holístico (insights, recomendações, ajustes de score)     |
| E7-apply       | det.       | Aplica review ao E5 JSON                                         |

> **Render do relatório:** O relatório é renderizado como rota React
> nativa (`/reports/[id]`) consumindo `GET /reports/{id}/data`. O único
> export server-side é **PDF via Playwright** (backend/app/services/pdf_renderer.py)
> sobre essa mesma rota. O renderer HTML server-side (`e6_render.py`
> + stages `E6`/`E6-final`) foi descontinuado em
> [ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side).

### Modo incremental (ADR-080)

O pipeline suporta execução **incremental**: processar apenas documentos novos (upload após última execução) nas etapas de extração, mantendo consolidação full.

**Comportamento:**
- **E0→E2**: filtrado — só processa docs com `pipeline_last_run_at IS NULL`
- **E3→E7**: full — roda sobre todos os E2_extracts existentes (novos + anteriores)
- **Resultado**: relatório completo, mas com economia de tempo/custo nas etapas E0→E2

**Trigger:** `POST /pipeline/run { incremental: true }`. A API busca `stored_path` dos docs novos e passa ao Celery task via `WorkspaceContext.incremental_doc_paths`. O E2 wrapper filtra `find_all_files()` por stem matching.

**Contagem:** `GET /pipeline/new-doc-count` retorna quantos docs têm `pipeline_last_run_at IS NULL`.

**UI:** Quando há docs novos e já houve run anterior, a página Pipeline mostra botão primário "Processar N novo(s)" + secundário "Processar todos".

### Execução offline (dev)

O mesmo orquestrador usado pelo worker pode rodar localmente sobre um tenant materializado:

```bash
python -m pipeline.run_dev --root /path/to/storage/<workspace_id>
python -m pipeline.run_dev --root ./tenant --stages E3,E4,E5
```

Fronteiras do pacote `pipeline/` (sem imports de FastAPI/Celery/SQLAlchemy) são verificadas por `python dev/check_pipeline_boundaries.py`. Artefatos JSON e schemas: [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md), [CANONICAL_ENGINE_P0.md](CANONICAL_ENGINE_P0.md).

### Artefatos no banco + abstração de I/O (ADR-082, ADR-083)

Desde a migração `plano_migracao_artifacts_db.md` (Fases 1-8 foundation), artefatos
computacionais do pipeline (E2–E7) **são gravados em `pipeline_artifacts`** via a
abstração `ArtifactStore`, em vez de exclusivamente em `storage/<ws>/processed/*.json`.

**Tabela `pipeline_artifacts`** (ver ADR-082):

```
id                  INTEGER PK
workspace_id        FK workspaces (CASCADE)
pipeline_run_id     FK pipeline_runs (CASCADE)
stage               VARCHAR(50)        -- "E2", "E3"... pré-F9; "reconcile_transactions"... pós-F9
artifact_key        VARCHAR(255)        -- stem do doc (E2) ou nome canônico (E3+)
document_id         FK documents        -- nullable; preenchido só em E2-*; SET NULL
content_json        JSON (JSONB em PG)
schema_version, byte_size, created_at
UNIQUE(pipeline_run_id, stage, artifact_key)
```

**Protocolo `ArtifactStore`** (ADR-083) em `pipeline/artifact_store.py`:

```python
class ArtifactStore(Protocol):
    def read(stage, key)  -> dict | None
    def list_keys(stage)  -> list[str]
    def exists(stage, key) -> bool
    def write(stage, key, data, *, document_id=None) -> None
    def delete(stage, key) -> None
    def delete_stage(stage) -> int
```

Três implementações concretas:

| Classe | Onde | Uso |
|---|---|---|
| `DiskArtifactStore` | `pipeline/artifact_store.py` | CLI dev, backward compat com `processed/` |
| `InMemoryArtifactStore` | `pipeline/artifact_store.py` | **Obrigatória** em testes de domain services |
| `DBArtifactStore` | `backend/app/services/db_artifact_store.py` | Web/Celery — sessão SQLAlchemy injetada pelo chamador |

`DBArtifactStore` vive em `backend/` (não `pipeline/`) porque depende de SQLAlchemy —
`dev/check_pipeline_boundaries.py` proíbe SQLAlchemy dentro de `pipeline/`.
`PipelineArtifactRepository` em `backend/app/repositories/pipeline_artifact_repository.py`
encapsula queries cross-run (`get_latest_for_workspace`, `get_by_document`,
`delete_stages_for_run`).

**Feature flag** `MATHOMS_USE_DB_ARTIFACTS` (default `True` desde 2026-04-23 — ADR-118)
seleciona o store em produção. `False` é fallback de debug/rollback.

### Orquestrador declarativo (ADR-087)

`pipeline/stage_spec.py` substitui o `FROM_MAP` manual do orquestrador:

```python
@dataclass(frozen=True)
class StageSpec:
    name: str
    reads: tuple[str, ...]     # stages de input
    writes: tuple[str, ...]    # stages de output
    is_llm: bool = False
    tier: str = "free" | "premium"

STAGE_REGISTRY: dict[str, StageSpec] = { "E2-extratos": ..., "E3": ..., ... }
VIRTUAL_ARTIFACT_STAGES = frozenset({"E5-revised"})  # não executáveis
FULL_ORDER = [...]  # decisão intencional
```

- `build_from_map(FULL_ORDER)` deriva o `FROM_MAP` (antes manual).
- `validate_full_order()` chamado no import — falha rápido se uma dependência é
  consumida antes de ser produzida.
- `STAGE_RENAME_MAP`: fonte de verdade para o renaming descritivo pós-Fase 9
  (`"E3"` → `"reconcile_transactions"`, etc.). ADR-093 documenta o plano.

Durante a janela de transição (Fases 1-8), os identificadores permanecem
**legados** (`"E2"`, `"E3"`, `"E5"`). A Fase 9 aplica o rename em bloco.

### Configuração imutável: `StageConfig` (ADR-088)

`pipeline/stage_config.py` substitui `_init_config(base_dir)` com globals:

```python
class StageConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    family_members: dict = {}
    pipeline: dict = {}
    institutions: dict = {}
    categorization: dict = {}
    goals: dict = {}       # opcional
    scoring: dict = {}     # opcional
    fiscal: dict = {}      # opcional

    REQUIRED = frozenset({"family_members", "pipeline", "institutions", "categorization"})
```

`from_context(ctx)` **falha rápido** com `ConfigError` quando um config
obrigatório está ausente (vs. `or {}` silencioso).

### `MaterializationBridge` — removido em A6c (2026-04-24)

Adapter temporário (ADR-086) entre `DBArtifactStore` e scripts legados em
Caminho A. Removido após cutover Caminho B (A6a/b) + aprovação humana
A6-human. Wrappers `pipeline/stages/eN.py` chamam
`scripts.eN_*.main_with_store(ctx)` direto sobre `ArtifactStore`.

### Camada de domínio `pipeline/domain/` (ADR-089-091)

Value objects tipados e imutáveis + services puros (sem I/O de disco):

```
pipeline/domain/
  models/
    transaction.py       Money (Decimal, R4 precisão por moeda), Transaction
    document.py          BankStatement, Investment, InvestmentStatement, BaselinePatrimonial
    bank.py              BankCanonicalizer (display/code → canonical), canonicalize_bank
  services/
    reconciliation_service.py         ReconciliationService(ReconciliationConfig)
    reconciliation_validators.py      SaldoContinuityValidator(SaldoContinuityConfig),
                                      TemporalGapDetector(TemporalGapConfig) +
                                      warnings estruturados (SaldoGapWarning,
                                      TemporalGapWarning)
    baseline_validator.py             BaselineValidator(BaselineValidatorConfig,
                                      BankCanonicalizer); BaselineAccountSaldo
                                      (+ from_baseline_dict), BaselineDiffWarning
    account_grouper.py                AccountGrouper(AccountGrouperConfig); value
                                      object AccountKey (bank, account_type,
                                      currency) + should_skip (tipos inválidos /
                                      faturas não-permitidas)
    statement_preprocessor.py         StatementPeriodNormalizer (expande periodo
                                      string / sintetiza para faturas →
                                      NormalizationResult + PeriodDerivationWarning);
                                      AnachronicTransactionDropper(AnachronicGuardConfig)
                                      (drop tx > 180d pré-período →
                                      AnachronicFilterResult + AnachronicTransactionWarning)
    e3_reconciler_adapter.py          E3ReconcilerAdapter (orquestra normalize →
                                      drop → group → reconcile → validate →
                                      write via ArtifactStore);
                                      ReconciliationStoreResult (saída tipada
                                      com contagens + 5 tuplas de warnings)
    e3_serialization.py               serialize_to_e3_legacy_format,
                                      generate_legacy_filename,
                                      generate_legacy_artifact_key (conversão
                                      BankStatement → schema E3 legado)
    categorization_service.py         CategorizationService(CategorizationRules)
    calculators.py                    CashFlowAggregator, PatrimonioCalculator,
                                      EmergencyReserveCalculator, FinancialScoreCalculator
```

- **`Money`** usa `Decimal` com precisão por moeda (BRL=2, JPY=0). Rejeita
  `float` no construtor e em `Money.of()` — dev deve converter explicitamente
  via `Decimal(str(v))` para tornar o risco visível (ADR-090).
- **Frozen dataclasses** para objetos de campos primitivos; **Pydantic frozen**
  para `StageConfig` (campos dict — deep-copy na construção); **dataclass não-frozen**
  para `BankStatement` (campo `transactions: list` com invariante restrito a
  pipeline de reconciliação) — regra R11 consolidada em ADR-091.
- **Services seguem ISP** — recebem value objects de config tipados
  (`ReconciliationConfig`, `SaldoContinuityConfig`, `TemporalGapConfig`,
  `BaselineValidatorConfig`, `AccountGrouperConfig`, `AnachronicGuardConfig`,
  `CategorizationRules`), não `StageConfig` inteiro. Fixtures de teste têm 3
  linhas em vez de mock completo.
- **Pipeline E3 como composição de services** — o `E3ReconcilerAdapter` encadeia
  pré-processadores (`StatementPeriodNormalizer` → `AnachronicTransactionDropper`),
  grouper (`AccountGrouper`), reconciliador (`ReconciliationService`) e
  validadores (`SaldoContinuityValidator`, `TemporalGapDetector`,
  `BaselineValidator`) sobre `ArtifactStore`. Saída tipada em
  `ReconciliationStoreResult` com contagens e 5 tuplas de warnings
  estruturados (`PeriodDerivationWarning`, `AnachronicTransactionWarning`,
  `SaldoGapWarning`, `TemporalGapWarning`, `BaselineDiffWarning`). A
  conversão para o schema E3 legado (`fontes`, `transacoes_duplicadas_removidas`,
  etc.) vive em `e3_serialization.py` — o adapter aceita `serialize_fn` e
  `output_key_fn` injetáveis via DI para permitir esse formato sem acoplar
  o domínio ao schema legado.
- **E3 Caminho B (ADR-097)** — `scripts/e3_reconcile.main_with_store(ctx)`
  orquestra o `E3ReconcilerAdapter` sobre `ctx.get_artifact_store()`.
  [pipeline/stages/e3.py](../pipeline/stages/e3.py) é o único caller.
  Sidecar logs (`reconciliation.md` + `qa_log.md` E3 section) escritos em
  `ctx.logs_dir`.
- **Validadores de reconciliação** — `SaldoContinuityValidator` (continuidade de
  saldo entre extratos consecutivos da mesma conta), `TemporalGapDetector` (gaps
  em dias entre `period_end` e próximo `period_start`), `BaselineValidator`
  (saldo 31/12 do extrato vs. IRPF, via `BankCanonicalizer` para evitar falsos
  positivos de substring). Foundation extraído de `scripts/e3_reconcile.py`
  para destravar o refactor completo (Caminho B) num sprint subsequente.

### Fronteira `pipeline/` ↔ framework

`dev/check_pipeline_boundaries.py` garante via AST que `pipeline/**/*.py` não
importa `fastapi`, `celery`, nem `sqlalchemy`. Adaptadores DB (incluindo
`DBArtifactStore`) vivem em `backend/app/services/` / `backend/app/repositories/`.

### Auth e fronteiras de processo (A6f · ADR-102 · ADR-109)

O backend expõe contratos **portáveis** na fronteira entre processos
(browser, Celery worker, pipeline, clients hipotéticos Go/Rust). Princípios
R18-R20 (ADR-102):

**Contratos de rede**:
- Toda resposta JSON de endpoint tem schema declarado via `response_model`
  (Pydantic) ou `response_class` explícito (`FileResponse`,
  `StreamingResponse`, `HTMLResponse`, `PlainTextResponse`, `Response`).
- Snapshot completo em [`docs/reference/api/v1/openapi.json`](api/v1/openapi.json) —
  committed e validado por [`test_openapi_snapshot.py`](../backend/tests/test_openapi_snapshot.py)
  (A6f.2).
- Estrutural [`test_openapi_response_models.py`](../backend/tests/test_openapi_response_models.py)
  bloqueia merge de endpoint novo sem contrato.

**JWT**:
- Algoritmo HS256 (RFC 7519 padrão — qualquer lib Go/TS/Rust lê sem ajuste).
- Payload canônico `{sub: str, exp: int, tv: int}` — `tv` = token version
  para revogação bulk via incremento em `User.token_version`.
- Refresh tokens httpOnly (F7B.4) — estado pode viver em Redis (A6f.6)
  quando multi-worker for exigência.

**Fernet** (simétrica, `cryptography.fernet`):
- Usada para `LLMConfig.api_key_encrypted` e futuros vault entries.
- Spec público (version byte 0x80 + 8-byte timestamp + 16-byte IV +
  ciphertext + 32-byte HMAC-SHA256) — existe `fernet-go`, `fernet`
  (TS/Rust).
- `VaultService` é singleton process-wide com key de `settings.FERNET_KEY`
  (ADR-060 prevê dual-key para rotation).

**Teste de portabilidade**: [`test_auth_portability.py`](../backend/tests/test_auth_portability.py)
roda 12 parity tests — se algum falhar, a mudança é breaking e exige
nova ADR (A6f.5b para AES-GCM, A6f.5c para RS256).

**O que não é portátil hoje (ciente)**:
- Celery usa JSON para args/results (OK), mas o broker é Redis — compat Go
  via `redis/go-redis`. Broker neutro (gRPC/NATS) não está no escopo.
- Logs ainda em formato texto — A6f.3 migra para JSON Lines + OpenTelemetry.

---

## 8. Frontend — Rotas e componentes

### Rotas (25 `page.tsx` — 21 produto + 2 playgrounds `_dev` + 2 auth públicas extras)

> **Contagem real** (2026-04-24): `find frontend/src/app -name page.tsx` → 25 arquivos. Produto: dashboard, documents, pipeline, transactions, reports (list+[id]), plano (home), plano/meta-if (+wizard), plano/aportes (+wizard), plano/dolarizacao (+wizard), plano/alocacao (+wizard), plano-de-acao (+sugestoes), vault, config. Playgrounds: reports/_dev/charts, reports/_dev/ui. Públicas: /, /login, /register, /invite/[token]. A tabela abaixo cobre o caminho principal — wizards de Aporte/Dolarização/Alocação e playgrounds `_dev` existem mas não estão enumerados.

**Públicas:**
| Rota | Página |
| --- | --- |
| `/` | Redirect → `/plano` (autenticado) ou `/login` |
| `/login` | Login (email/password, suporta `?next=`) |
| `/register` | Registro |
| `/invite/[token]` | Aceite de convite (preview público, aceite com auth) |

**Protegidas (dentro de `(app)` com AppShell):**
| Rota | Página |
| --- | --- |
| `/dashboard` | Redirect 308 → `/plano` (absorvido em ADR-155 · Direção E consolidação) |
| `/documents` | Upload drag-and-drop, status badges, retry-unlock |
| `/pipeline` | Trigger + progress (PhaseStepper 4 fases) |
| `/transactions` | Filtros, busca, override de categoria, export CSV/XLSX |
| `/reports` | Lista de relatórios (metadata, score, tamanho) |
| `/reports/[id]` | **Render nativo React** — Estratégico (S1–S10 + plano_de_acao + APP_A-E) + USA (U1-U4). Modo Tático removido (ADR-151). `<SuggestionCallout/>` inline em seções com sugestões + agregador "§ Próximos passos" no fim (ADR-153 · Onda 5). |
| `/plano` | **Home única do app** (ADR-155 · Direção E consolidação). 3 seções verticais: (1) Estratégia — KPIs estratégicos · `SuggestionsBanner` · Hero IF · Metas de suporte; (2) Mês corrente (ex-/dashboard) — alertas · KPIs operacionais · ChartsGrid; (3) Plano de Ação — Decisões em vigor · UpcomingTasksWidget · Tarefas ligadas à IF |
| `/plano/meta-if` | Editor da meta IF com simulador live |
| `/plano/meta-if/wizard` | Wizard 4 passos (renda → TRS → horizonte → confirm) |
| `/acao` | **Superfície dinâmica** (Direção E · Onda 6, ADR-152): tabs Inbox · Tarefas · Timeline · Notas. **Inbox** consome `Suggestion` (ADR-153 · Onda 5) com fluxos Aceitar/Modificar/Descartar. **Notas** consome `WorkspaceNotes` (ADR-154 · Onda 1). |
| `/acao/sugestoes` | Fila de TaskSuggestion (LLM legacy) approve/reject 1-click — distinto de `Suggestion` (ADR-153) que vive na Inbox tab |
| `/plano-de-acao` | Redirect 308 → `/acao` (rota antiga, ADR-152) |
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
| `WorkspaceProvider.tsx` | **React Context** — resolve workspace uma vez no layout, compartilha via `useWorkspace()` |
| `useCurrentWorkspace.ts` | Workspace atual (standalone, legado) — preferir `useWorkspace()` em pages sob `(app)/` |
| `usePermissions.ts` | Derives permissions from role (isOwner, canWrite, etc.) |
| `usePipelineWS.ts` | WebSocket hook (auto-reconnect, terminal events) |
| `format.ts` | 9 formatters (currency BRL/USD, percent, delta, compact, doc/pipeline status) |
| `export.ts` | Export CSV (BOM UTF-8, `;`) + XLSX (auto-width) |
| `pipelinePhases.ts` | Backend stages → 4 user-facing phases. **Fonte de verdade de execução**: `pipeline.stage_spec.STAGE_REGISTRY` (18 entradas em 2026-04-24). O mapping UI agrupa (E2-extratos/E2-faturas/E2-llm → "Extração", etc.). |
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
  3. ``document_classification.classify_document()`` — classificador único (P2 / ADR-081); content-first:
     a. Extract text preview (pdfplumber/openpyxl/csv)
     b. Content regex (content_classifier.py) → institution + doc_type + period
     c. If confidence < 0.8 → LLM fallback (anthropic SDK, classify_by_llm)
     d. If confidence < 0.7 → needs_review=true (e possivelmente ``other``)
     ⚠ Filename is NOT used — bank exports have wrong/arbitrary names
     O mesmo módulo atende upload web, ``POST /documents/reclassify`` e ``e0_route.route_file`` (quando o backend está importável); o CLI sem backend cai em regex por nome + LLM.
  4. Dedupe:
     a. Exact: SHA-256 hash → rejeita se (workspace_id, content_hash) existe
     b. Fuzzy: se (doc_type, bank_code, period) já existe → possible_duplicate_of_id
  5. route_to_data_dir() → storage/{ws_id}/data/{dest_group}/
    ↓
Document.status = "ready", classification_confidence, needs_review
    ↓
**P2.5 (observabilidade):** após cada classificação (upload, retry-unlock, reclassify em lote), o backend emite log estruturado no logger `fin.classification_telemetry` — linha com JSON (`event`, `context`, `doc_type`, `confidence_bucket`, `type_changed_vs_prior`, etc.) **sem nome de arquivo**. Útil para medir volume de mismatch antes/depois de mudanças no classificador.

User clica "Gerar Relatório"
    ↓
POST /api/v1/pipeline/runs → prepare_pipeline_config_dir() → Celery task
    ↓
Pipeline stages rodam em ordem → PipelineStageLog por stage
    ↓
WebSocket /ws publica eventos via Redis Pub/Sub
    ↓
Celery task cria Report no DB (analysis_artifact_id FK + tasks_snapshot)
    ↓
Frontend renderiza nativamente via GET /reports/{id}/data (React)
```

### Carregamento de config (DB-first pós-Sprint A7)

Após Sprint A7 (Config DB Cutover, 2026-04-27), o pipeline lê configs **direto do DB via ConfigStore** ([ADR-134](DECISIONS.md#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend)). Materialização disco-side foi removida; bridges deletados em A7.5 (`materialize_config`, `FileConfigStore`).

```
User edita config via UI → DB (categories, family_members, transfer_configs, etc.)
    ↓
POST /api/v1/pipeline/runs
    ↓
backend.app.services.pipeline_service._prepare_run_context():
  1. prepare_pipeline_config_dir(ws_id, tenant_root, db):
     - Copia config/ global (assets de produto: schemas, prompts,
       templates, scoring.json, pipeline.json, report_layout.yaml)
       → storage/{ws_id}/config/
     - Sobrescreve apenas pipeline.json + llm_config.json com overrides DB
       (configs A7.1 NÃO são escritos em disco — fluem via DBConfigStore)
  2. build_config_overrides_from_db(ws_id, db):
     - Pré-serializa categorization, family_members, institutions,
       report_layout, transfer_configs em dict
     - Injetado em WorkspaceContext.config_overrides
  3. build_config_store(db, use_db_artifacts=True):
     - DBConfigStore lê DB via repositórios + cache Redis
     - Injetado em WorkspaceContext.config_store
    ↓
Pipeline stages consomem via ctx.load_config(name) (overrides → typed)
ou via ctx.config_store.get_X(workspace_id) (typed direto)
    ↓
Goldens E3/E4/E5/E5.N preservam paridade byte-a-byte vs pré-A7
```

**Assets de produto remanescentes em `config/`** ([ADR-149](DECISIONS.md#adr-149--configreport_layoutyaml-permanece-como-asset-de-produto-sprint-a80)): `report_layout.yaml`, `pipeline.json` (default), `scoring.json`, `schemas/`, `prompts/`, `templates/`. Editáveis pelo time Mathoms; **não** contêm dados cliente.

---

## 10. Estrutura de pastas

```
mathoms.ai/
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
│   ├── alembic/               # 32 DB migrations (2026-04-24; `ls backend/alembic/versions/*.py`)
│   ├── tests/                 # ~50 test files, ~450 tests
│   │   ├── factories/         # Type-safe builders
│   │   ├── fixtures/          # LLM mock, pipeline runs, PDF generator
│   │   └── regressions/       # Anti-regression bank (24 tests)
│   └── requirements.txt
│
├── pipeline/                  # Pipeline core (package Python — sem FastAPI/Celery/SQLAlchemy)
│   ├── __init__.py            # API pública v0.2.0
│   ├── context.py             # WorkspaceContext (+ get_artifact_store)
│   ├── config_loader.py
│   ├── orchestrator.py        # run_pipeline, run_from, run_stages (FROM_MAP derivado)
│   ├── stage_spec.py          # STAGE_REGISTRY + STAGE_RENAME_MAP + FULL_ORDER (ADR-087)
│   ├── stage_config.py        # StageConfig (Pydantic frozen, ADR-088)
│   ├── artifact_store.py      # Protocol + DiskArtifactStore + InMemoryArtifactStore (ADR-083)
│   ├── domain/                # Camada de domínio (ADR-089)
│   │   ├── models/            # Money, Transaction, BankStatement, Investment, Baseline
│   │   └── services/          # ReconciliationService, CategorizationService, calculators
│   ├── llm/                   # LLM infrastructure
│   │   ├── service.py         # LiteLLM + Instructor
│   │   ├── text_extractor.py
│   │   ├── validators.py
│   │   ├── prompts/
│   │   └── schemas/
│   └── stages/                # Thin wrappers (4-20 linhas cada)
│
├── scripts/                   # Pipeline scripts determinísticos (worker)
│   ├── e0_audit.py, e0_route.py, e0_unlock.py
│   ├── e15_consolidate.py, e2_extract.py
│   ├── e3_reconcile.py, e4_categorize.py
│   ├── e5_analyze.py, e5n_narrativas.py
│   ├── e7_review.py, e_reset.py
│   ├── e2/                    # Parsers por banco (registry, common, banks/)
│   └── pipeline_common.py     # Paths, config, JSON I/O (atomic writes), schema validation, structured logging
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
│   │   │   ├── report/        # Report Premium v1 (decomposto pós-Fase 10)
│   │   │   │   ├── ui/        # 14 primitivos (Kpi, Alert, Badge, Timeline, NotasCard, kanban/, badges/)
│   │   │   │   ├── charts/    # 8 Chart.js wrappers + primitives/ + _registry.ts
│   │   │   │   ├── sections/  # S1-S10 (estratégico) + UsaSections + ApendiceA-E (Modo Tático removido em ADR-151)
│   │   │   │   ├── shell/     # ReportCover, ReportTopNav, ExportToolbar, FloatingNav, FontScaleToggle, ModeToggle, SkipNav
│   │   │   │   ├── kpi/       # PatrimonioKpiRow (KPI rows reutilizáveis)
│   │   │   │   ├── cards/     # 15 cards de domínio (PerfilFamilia, Reserva, Equilíbrio, Endividamento, Investimentos, Previdência…)
│   │   │   │   ├── utils/     # conclusionUtils, kanbanAdapter, priorityMap, scoreUtils, timelineAdapter
│   │   │   │   ├── ReportShell.tsx, ReportHeader.tsx, ReportSection.tsx, ReportToc.tsx, ReportSourceStrip.tsx
│   │   │   │   ├── ReportModeProvider.tsx     # cliente, dinâmico (?mode= URL)
│   │   │   │   ├── StaticReportModeProvider.tsx  # SSR/standalone (ADR-124 §11.1)
│   │   │   │   └── report-print.css, MonetaryValue.tsx, ReportThemeToggle.tsx, useReportFontScale.ts
│   │   │   └── *.tsx          # Compositions (AppShell, KPICard, etc.)
│   │   ├── generated/         # Codegen (report-layout.ts from YAML)
│   │   ├── types/             # Tipos fortes do E5 (análise financeira)
│   │   ├── hooks/             # React hooks (useReportData, etc.)
│   │   ├── styles/            # tokens.css gerado pelo design-tokens build
│   │   └── lib/
│   │       ├── api.ts         # API client completo + types
│   │       ├── format.ts, export.ts
│   │       ├── WorkspaceProvider.tsx  # Context provider (useWorkspace hook)
│   │       ├── useCurrentUser.ts, useCurrentWorkspace.ts, usePermissions.ts
│   │       ├── usePipelineWS.ts
│   │       └── utils.ts       # cn()
│   └── package.json
│
├── design-tokens/
│   ├── tokens.json            # Fonte única de verdade (cores, tipografia, spacing)
│   └── build.py               # Gera CSS para frontend
│
├── config/                    # Configs globais (até A7.5; metodologia movida em A7.4 → docs/methodology/)
│   ├── pipeline.json          # Parâmetros operacionais + report_version
│   ├── family_members.json, categorization.json, institutions.json
│   ├── methodology.md, report_spec.md
│   ├── report_layout.yaml     # Codegen source → TS + Pydantic
│   ├── scoring.json, cenarios.json, taxas.json, parametros_fiscais.json
│   ├── schemas/               # 11 JSON schemas (baseline, E2/E3/E4/E5, 4 goals, pipeline, report_layout)
│   └── templates/             # 7 templates (HTML, MD, CSS)
│
├── docs/methodology/          # A7.4: documentação humana de produto (não-runtime)
│   ├── definitions.md, regras_composicao_patrimonial.md
│   ├── source_hierarchy.md, milhas.md
│   └── README.md
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
└── pyproject.toml             # Package mathoms-pipeline v0.2.0
```

**Sobre `frontend/src/components/report/`** (Report Premium v1, pós-Fase
10): shell decomposto em primitivos (`ui/`), Chart.js wrappers
(`charts/`), seções por modo (`sections/`), shell composicional
(`shell/`), KPIs reutilizáveis (`kpi/`), cards de domínio (`cards/`) e
utilitários (`utils/`). Provider de modo dual:
`ReportModeProvider` (cliente, dinâmico via `?mode=`) +
`StaticReportModeProvider` (SSR/standalone — ADR-124 §11.1, mantido
como provider mesmo após [ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side)
descontinuar o renderer HTML server-side; React em `/reports/[id]` é
único renderer; PDF via Playwright é único export server-side).

---

## 11. Onde moram os dados

### Mapa por tipo de dado

| Dado                                              | Onde vive                                                   | Persistido por                                                  |
| ------------------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------- |
| Código-fonte + docs                               | Git (`github.com/davidrobert/mathoms`)                      | Desenvolvedor via `git commit`                                  |
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
| Goals (metas financeiras)                         | `goals` (DB), `params_json` com `inputs` + `meta_version`, vigência `effective_from` / `effective_to` | `PUT /goals/...` (por tipo) · **UI F11.6a:** `GoalPremissasCard` em `/plano/*` |
| Tasks (backlog de ações)                          | `tasks`, `task_suggestions`, `task_attachments` (DB)        | CRUD via `/tasks` endpoints                                     |
| Feature flags                                     | `feature_flags` (DB) + defaults em código                   | `PUT /feature-flags/{flag}`                                     |
| Config materializada por tenant (assets de produto) | `storage/{ws_id}/config/*`                                  | `config_materializer.prepare_pipeline_config_dir()` (apenas pipeline.json + llm_config.json + assets globais; A7.1 configs fluem via `WorkspaceContext.config_overrides` from DB) |
| Artefatos intermediários (`-2_extract.json`, …)   | `storage/{ws_id}/processed/E2_extracts/` etc.               | Scripts E2–E5 executando dentro do tenant_root                  |
| Análise final (`analise_financeira-5_analysis.json`) | `storage/{ws_id}/processed/E5_analysis/`                 | Stage E5                                                        |
| Relatório (metadata)                              | row em `reports` (DB) — sem filesystem                      | Celery task registra `Report` após E5/E7-apply; render é React on-demand |
| Tasks snapshot no relatório                       | `reports.tasks_snapshot_json` (DB)                          | `build_snapshot_sync` na criação do Report                      |
| Audit log                                         | `audit_logs` (DB)                                           | `audit_service.log()` dentro da transação                       |
| Tasks queue state                                 | Redis (broker + result backend)                             | Celery                                                          |
| Eventos WebSocket                                 | Redis Pub/Sub                                               | `services/events.py`                                            |

### O que **não** é persistido no git

Todos os dados de utilizador estão fora do git por design. O destino **canónico**
de ficheiros por workspace é `storage/<workspace_id>/` (gitignored por completo).

`.gitignore` também cobre nomes de pastas de **workspace legado na raiz do
repo** (`data/`, `inbox/`, `inbox_processed/`, …) para quem corre o pipeline
CLI com `MATHOMS_WORKSPACE_ROOT` na raiz do projeto — essas pastas **não** são
obrigatórias no clone; criam-se só quando há esse uso local. Além disso:
`*.db`, `.env`, `config/passwords.txt`, `_scratch/`. O `pre-commit`
(`dev/check_forbidden_paths.py`) aplica regras alinhadas em nível de hook.

---

## 12. Padrões arquiteturais

### "Wrap, Don't Rewrite" (F0)
Scripts legados (E5=107KB — E6=197KB foi removido em ADR-129) têm lógica refinada. Em vez de reescrever:
1. Cada script ganha `_init_config(base_dir)` que (re)carrega globals de config
2. `main(root_dir=None)` aceita root injetado
3. Wrappers finos em `pipeline/stages/` (3-5 linhas)

### Materialize, Don't Inject (F3 → superseded por ConfigStore em Sprint A7)

**Histórico:** F3 introduziu `materialize_config()` que copiava `config/` global → tenant + sobrescrevia com DB; scripts lêem do disco via `_init_config`. **Sprint A7 (2026-04-27) substituiu este padrão** ([ADR-134](DECISIONS.md#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend)) pelo `ConfigStore` Protocol read-only. `materialize_config` foi deletado em A7.5; scripts continuam usando `ctx.load_config(name)` mas agora os dados fluem de DB via `WorkspaceContext.config_overrides` (populado por `build_config_overrides_from_db`). Para configs que ainda precisam de disco (assets de produto: `pipeline.json`, `llm_config.json` overrides), `prepare_pipeline_config_dir()` materializa apenas o subset necessário.

### Pipeline Adapter (F8)
`pipeline_adapter.py` é a fachada DB → JSON para entidades migradas (goals, tasks, family_members). Scripts recebem JSONs materializados no disco, sem saber que a fonte é o DB.

### Atomic Writes (pipeline hardening)
Artefatos intermediários (E3, E4, E5) são escritos atomicamente via `pipeline_common.write_json_atomic()` (temp file + `os.replace()`). O flag `fsync=True` é usado para artefatos críticos (E5 analysis). Previne arquivos truncados em caso de crash/OOM kill do worker.

### Consolidate, Don't Duplicate (pipeline hardening)
Scripts E3/E4/E5 delegam `read_json()`, `write_json()`, `log_progress()` para `pipeline_common.py`. Elimina divergência comportamental entre estágios (ex: error handling, encoding, indentation). `safe_float(locale=)` aceita BRL/USD/EUR para parsing correto de valores multi-moeda.

### Cancel Cooperativo (F5)
DB flag `PipelineRun.status = "cancelled"`. Task verifica entre stages. Celery `revoke()` adicional. Stages completos preservados.

### SystemExit Interception
Scripts legados usam `sys.exit(1)`. Em Celery fork worker, `_run_stage()` no orchestrator captura `SystemExit` → converte em `StageResult(success=False)`.

### Retorno `dict` e chave `success` (orchestrator)

Alguns runners (`pipeline/stages/*.py`) retornam um **dicionário** com metadados (tokens, arquivos processados, erros parciais). Para falhas **sem** exceção (ex.: E2-llm concluiu mas há erros; E5.N não gerou output), o runner deve incluir explicitamente:

```python
{"success": False, ...}  # ou True em caso de sucesso explícito
```

Regras em `_run_stage()` (`pipeline/orchestrator.py`):

| Retorno do runner | `StageResult.success` |
| ----------------- | ---------------------- |
| Exceção ou `SystemExit` com código ≠ 0 | `False` |
| Qualquer valor que **não** seja `dict` | `True` |
| `dict` **sem** chave `"success"` | `True` (compat.: skips como E1 sem docs) |
| `dict` **com** `"success"` | `bool(detail["success"])` |

O dicionário completo permanece em `StageResult.detail` para a UI, logs e persistência do run.

---

## 13. Segurança

### At-rest
- **Fernet** (symmetric encryption) para CPFs, API keys LLM, senhas PDF
- `MATHOMS_FERNET_KEY` persistida em `.env` (nunca commitar)

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

## 15. Observabilidade (F7)

- **Runbook + SLO + incidentes** — [RUNBOOK.md](RUNBOOK.md), [SLO.md](SLO.md), templates em [runbooks/incidents/](runbooks/incidents/); link público de status no app via `NEXT_PUBLIC_MATHOMS_STATUS_PAGE_URL` (rodapé).
- **Sentry** — backend + frontend (error tracking, performance 10%) — tarefa 7C.4
- **Structured logging + OpenTelemetry** (ADR-110 · A6f.3 · entregue 2026-04-20):
  - `backend/app/core/logging.py` — `MathomsJsonFormatter` (wraps `python-json-logger`). Formato JSON por linha, jq-compatível. Campos: `timestamp` (UTC ISO 8601 `Z`), `level`, `logger`, `message`, `trace_id`, `workspace_id`, `user_id`, `pipeline_run_id`, opcional `otelTraceID`/`otelSpanID`.
  - `backend/app/middleware/correlation.py` — `CorrelationIdMiddleware` gera/reflete `X-Trace-Id` por request. Contextvars tipados (`_trace_id`, `_workspace_id`, `_user_id`, `_pipeline_run_id`) propagam ID através de asyncio + Celery. Setters usados em `api.auth` (depois de authenticate), Celery task (antes de run).
  - `backend/app/core/otel.py` — `setup_otel(service_name)` idempotente. `LoggingInstrumentor` sempre liga (custo desprezível, popula trace context). `OTLPSpanExporter` opt-in via env `OTEL_EXPORTER_OTLP_ENDPOINT` — aponta para collector OTLP-compliant (Tempo, Jaeger, Honeycomb, DataDog). `instrument_fastapi(app)` liga no lifespan; `instrument_celery()` no `worker_process_init` signal (fork-safe).
  - **Env vars**: `MATHOMS_LOG_LEVEL` (default INFO), `MATHOMS_LOG_FORMAT` (default `json`; `text` volta para humano com `[trace=XXXXXXXX]`), `OTEL_EXPORTER_OTLP_ENDPOINT` (opt-in).
  - **Por que importa cross-service**: backend, worker e (futuro A6f.1) pipeline-service gravam no mesmo formato. Qualquer Go/TS/Rust service futuro exporta OTLP idêntico — sem vendor lock-in.
- **Uptime externo** — health check (UptimeRobot ou equivalente) — alinhado à status page
- **Custom telemetry** — UsageMetric (privacy-first) — 7D.9

Para decisões arquiteturais detalhadas com rationale, ver [DECISIONS.md](DECISIONS.md).

---

## 16. Console interno (operadores, planejado — F7F)

Aplicação **separada** do fluxo multi-tenant do cliente: autenticação própria, RBAC interno, APIs em prefixo dedicado (ex.: `/api/internal/...`), agregados privacy-first e ações mutadoras com audit obrigatório. O `/config` do workspace continua sendo **administração pelo cliente**.

- Plano por fases (IA-0 … IA-3): [INTERNAL_ADMIN_ROADMAP.md](INTERNAL_ADMIN_ROADMAP.md)
- Tasks: [BACKLOG.md — F7F](BACKLOG.md#f7f--console-interno-operadores)
- Primeira entrega de UI alinhada: **7E.7** (business metrics em `/admin/metrics`)

---

## 17. Arquitetura alvo pós-A6 (migração infra+domínio)

**ADRs formalizadoras**: 097-111 em [DECISIONS.md](DECISIONS.md) ·
**Status de execução + lanes abertas**: [BACKLOG §Sprint A6](BACKLOG.md#sprint-a6--migração-infradomínio-plano-transversal) ·
**Critérios de aceite por fase**: [TESTING §Critérios de aceite por fase](TESTING.md#critérios-de-aceite-por-fase-da-migração-a6) ·
**Runbook de cutover**: [runbooks/cutover.md](runbooks/cutover.md)

### 17.0 Motivação — por que migrar

A migração A6 resolve 2 classes de problemas acumuladas no sistema
legado, cada um já endereçado por ADR individual — esta §17 descreve o
**estado alvo**; cada ADR explica o porquê específico e a estratégia de
transição:

- **Infraestrutura (artefatos + orquestrador):** acoplamento frágil
  por nome de arquivo (regex em `document_pipeline_sync.py`), ambiguidade
  de modo incremental (stem matching que colide em re-extração), estado
  global mutável em `pipeline_common._init_config()` (bomba-relógio
  multi-worker), `FROM_MAP` manual em `FULL_ORDER`, `init_workspace_paths_from_env()`
  em nível de módulo que levanta `SystemExit` sem `FIN_WORKSPACE_ROOT`.
  → ADRs **082** (PipelineArtifact), **083** (ArtifactStore), **086**
  (MaterializationBridge), **087** (StageSpec declarativo), **093**
  (stage rename Fase 9), **096** (observabilidade de cutover).
- **Domínio (modelo + design):** ausência de modelo — tudo é `dict`
  genérico; `float` para dinheiro (drift binário acumula em relatórios);
  scripts god-object com 30+ globals (`e5_analyze.py` 108KB); lógica
  acoplada a disco, intestável em isolamento; nomes `eN_*.py`
  acoplados à ordem de execução (responsabilidade do orquestrador).
  → ADRs **089** (ISP services), **090** (Money value object),
  **097** (extract-then-refactor de domain services), **098** (Caminho
  B puro vs pragmático), **101** (backend DDD/SOLID R12-R17).
- **Language-neutral boundary (preparação Go):** backend importa
  `pipeline.*` por Python, prendendo stack de execução à linguagem.
  Structured logs + DB schema precisam ser legíveis fora de Python.
  → ADRs **102** (R18-R20 language-neutral), **109** (auth portability),
  **110** (JSON logs + OTel), **111** (stateless rigoroso).

O plano de execução histórico (v3.0→v3.6, 2026-04-02 a 2026-04-21)
viveu em `_scratch/plano_migracao_artifacts_db.md` e foi absorvido nas
fontes canônicas listadas no topo em 2026-04-21. Conteúdo único
(checklist de testes §7 → `TESTING.md`, LGPD D1-D5 §15 → `BACKLOG F7B`,
runbook de cutover §16 → `runbooks/cutover.md`) migrado; o resto estava
duplicado com ADRs, `BACKLOG` e o código real em `pipeline/**`.

Esta seção descreve o **estado alvo** após a conclusão das sessões A5f+A6
do plano transversal de migração. Reflete decisões arquiteturais já tomadas
mas **ainda não implementadas** em partes (A6e.3-.6 + A6f.1 pendentes).

### 17.1 Caminho B: puro vs pragmático (estado atual e alvo)

Pós-A5f, **7 de 7** stages determinísticos rodam em "Caminho B" (sem
`MaterializationBridge` no wrapper). Dois sabores convivem:

| Variante | Stages | I/O via store | Globals removidos | Domain services integrados |
|---|---|---|---|---|
| **Caminho B puro** | **E3** (A2), **E5** (A6d.3.3), **E5.N** (A6d.3.2) | ✅ | ✅ (A3b + A6d.1) | ✅ (ReconcilerAdapter, AnalyzerAdapter com 14+ services, NarrativasBuilder) |
| **Caminho B pragmático** | E4, E7, E1.5c | ✅ | ✅ (A6d.1) | ❌ (decisão consciente: E4 adapter já ativo; E7 LLM-bound; E1.5c trivial) |

**A6d fechou a diferença** (2026-04-20, ADR-100 + ADR-097): E5 e E5.N
migraram para Caminho B puro. E4, E7 e E1.5c permanecem pragmáticos
porque o refactor não entrega valor adicional relevante: E4 já roda via
`E4CategorizerAdapter` em `main_with_store` (auditoria A6d.3.1); E7 é
LLM-bound e não se beneficia de services puros; E1.5c é consolidação
trivial. Estado final: globals eliminados em 5 scripts (A6d.1), 1427 testes
passando, zero regressão nos goldens.

### 17.2 Arquitetura alvo de processos e comunicação (pós-A6f)

```
┌─────────────────────────────┐    HTTP/JSON     ┌──────────────────────────────┐
│ backend/app/ (hoje Python,  │ ───────────────▶ │ pipeline-service/            │
│ eventualmente Go — A6f.1)   │                  │ FastAPI standalone           │
│ · routers /api/v1/...       │                  │ · lê E2 via ArtifactStore    │
│ · repositories por aggregate│                  │ · invoca stages E0-E7         │
│ · use cases (application/)  │                  │ · chama LLM (pipeline/llm/)  │
│ · DTOs (schemas/dto/)       │                  │ · escreve via ArtifactStore  │
│ · eventos tipados (events/) │                  │                              │
└─────────────────────────────┘                  └──────────────────────────────┘
              │                                                 │
              │ SQLAlchemy / pgx                                │ SQLAlchemy
              ▼                                                 ▼
        ┌──────────────────────────────────────────────────────────┐
        │  Postgres                                                 │
        │  · pipeline_artifacts (language-neutral JSON)             │
        │  · workspaces, documents, goals, tasks, ...               │
        │  · UUIDs + UTC-aware timestamps + JSON camelCase (A6f.4)  │
        └──────────────────────────────────────────────────────────┘
              │
              │ pub/sub (Redis channels, A6f.6)
              ▼
        ┌──────────────────────────┐
        │  WebSocket clients       │
        │  (browser — live updates)│
        └──────────────────────────┘
```

**Pontos-chave**:

- **Backend fala com pipeline-service apenas via HTTP** (ADR-102 / R18).
  Mesmo sendo Python hoje, o acoplamento por `import` desaparece. Isso
  destrava escalar o pipeline independente do web tier e prepara
  migração de linguagem futura.
- **Repository pattern** em `backend/app/repositories/` (ADR-101 / R13)
  encapsula todo acesso a DB. Routers não importam SQLAlchemy.
- **Application layer** em `backend/app/application/` organiza use cases
  explícitos (R15). Cada endpoint chama exatamente 1 use case.
- **DTOs separados de models** (R12) — breaking changes no ORM não
  quebram UI silenciosamente.
- **Domain events** (R17) para side-effects desacoplados (notificações,
  audit, WebSocket push via `register_handler(Event, handler)`).
- **Stateless rigoroso** (R19) — WebSocket via Redis pub/sub; zero estado
  in-memory que impeça múltiplos workers concorrentes.

### 17.3 `ArtifactStore` como fronteira de storage (A6b ✅)

`USE_DB_ARTIFACTS=True` é o default (ADR-118, 2026-04-23) — todos os stages rodam
sobre `DBArtifactStore` por default. Workspace pode forçar disco para debug via
`workspaces.use_db_artifacts_override=FALSE` (ADR-106):
```sql
UPDATE workspaces SET use_db_artifacts_override = FALSE WHERE id = '<ws_id>';
```
`pipeline_task._resolve_use_db_artifacts(ws_id)` verifica override do workspace
> global `MATHOMS_USE_DB_ARTIFACTS`. Com default ativo, cria `DBArtifactStore` com
sessão longa e injeta em `ctx.artifact_store`. Gate de validação:
`python dev/compare_disk_vs_db.py <ws_id> --strict`.

```python
class ArtifactStore(Protocol):
    def read(self, stage: str, key: str) -> dict | None: ...
    def list_keys(self, stage: str) -> list[str]: ...
    def write(self, stage: str, key: str, payload: dict) -> None: ...
```

3 implementações:
- **`DiskArtifactStore`** — CLI, dev, smoke test
- **`InMemoryArtifactStore`** — testes unitários de domain services
- **`DBArtifactStore`** — produção pós-A6b, usa tabela `pipeline_artifacts`

A tabela `pipeline_artifacts` tem schema estável (`schema_version`), JSON
`content` com keys em camelCase (ADR-102 / R20), foreign keys explícitas
— legível por qualquer linguagem.

### 17.4 Fronteira `pipeline/` ↔ framework (preservada)

Regra original mantida e estendida:
- `pipeline/**/*.py` **não importa** `fastapi`, `celery`, `sqlalchemy`
  (enforçado por `dev/check_pipeline_boundaries.py`).
- `pipeline-service/` (novo, A6f.1) é o **único** com acesso a framework;
  `pipeline/` continua sendo lib pura.
- `backend/app/services/db_artifact_store.py` (SQLAlchemy) fica em
  `backend/`, não em `pipeline/` (preservando R1).

### 17.5 Resumo de princípios (R1-R20)

| ID | Princípio | ADR | Escopo |
|---|---|---|---|
| R1 | `pipeline/` sem framework | 083 | Estrutural |
| R2 | `Money` com `Decimal`, rejeita `float` | 090 | Domain |
| R3 | Value objects frozen | 089, 091 | Domain |
| R4 | `InMemoryArtifactStore` para testes | 083 | Testes |
| R5 | Stage rename via `STAGE_RENAME_MAP` | 093 | Stages |
| R6 | `StageConfig` Pydantic frozen | 088 | Config |
| R7 | `MaterializationBridge` temporário | 086 | Transição |
| R8 | `STAGE_REGISTRY` fonte de verdade | 087 | Stages |
| R9 | Services recebem value object de config (ISP) | 089 | Domain |
| R10 | E2 parsers adaptados por stage, não ad-hoc | 089 | Domain |
| R11 | Dataclass não-frozen para `BankStatement` com invariante documentado | 091 | Domain |
| **R12** | **Endpoints retornam DTO dedicado, não ORM model** | **101** | **Backend API** |
| **R13** | **Repositórios por aggregate; routers não importam SQLAlchemy** | **101** | **Backend API** |
| **R14** | **Routers ≤50 linhas (enforçado por teste estrutural)** | **101** | **Backend API** |
| **R15** | **Application layer por use case; 1 endpoint = 1 use case** | **101** | **Backend API** |
| **R16** | **Versionamento `/api/v1/`; breaking changes em `/v2/` coexistem** | **101** | **Backend API** |
| **R17** | **Domain events tipados; side-effects via `register_handler`** | **101** | **Backend API** |
| **R18** | **Wire formats explícitos; zero pickle cross-process** | **102** | **Fronteiras** |
| **R19** | **Stateless-ready; zero estado in-memory bloqueador de escala** | **102** | **Backend / pipeline-service** |
| **R20** | **DB schema + JSON artifacts language-neutral (UUIDs, UTC, camelCase)** | **102** | **Storage** |

Princípios **D1-D8** (domain-specific, restritos a domínio puro) em
ADR-097 e ADR-099.

---

## 18. Domínios e URLs públicas (F7A)

**Decisão:** [ADR-108](DECISIONS.md#adr-108--estratégia-de-subdomínios-mathomsai--cloudflare-dns) (2026-04-20).
**Domínio:** `mathoms.ai` (registrado em Cloudflare Domains).

### 18.1 Estrutura canônica de URLs

| Papel | Produção | Staging | Dev local |
|---|---|---|---|
| Landing marketing | `https://mathoms.ai` | `https://staging.mathoms.ai` | — |
| Produto (Next.js) | `https://app.mathoms.ai` | `https://app.staging.mathoms.ai` | `http://localhost:3000` |
| API (FastAPI + WS) | `https://api.mathoms.ai` | `https://api.staging.mathoms.ai` | `http://localhost:8000` |
| Console interno | `https://ops.mathoms.ai` | `https://ops.staging.mathoms.ai` | `http://localhost:3000/ops` |
| Docs do produto | `https://docs.mathoms.ai` | — | — |
| Status page | `https://status.mathoms.ai` | — | — |
| Sharing público | `https://share.mathoms.ai` (reservado, F10+) | — | — |
| Previews (opt) | `https://<branch>.preview.mathoms.ai` | — | — |

**Multi-tenancy via path**, não subdomain: `app.mathoms.ai/w/<workspace-slug>/reports/<id>`.
Subdomain-per-tenant (`<slug>.mathoms.ai`) reservado para enterprise tier futuro.

### 18.2 Versionamento de API

`api.mathoms.ai/v1/...` — sem `/api/` redundante (o subdomain já declara).
Breaking changes vão para `/v2/...` coexistindo, não sobrescrevendo. Alinha
com R16 (ADR-101).

**Implementação (A6e.5, 2026-04-22):** em dev e enquanto o reverse proxy
de F7A não separa host de path, a app expõe:

- **Canônico:** `/api/v1/*` — único registrado no OpenAPI (88 paths,
  `info.version = "1.0.0"`, `servers: [{url: "/api/v1"}]`).
- **Alias deprecated:** `/api/*` — mesmos handlers, `include_in_schema=False`.
  Cada response carrega `Deprecation: true` + `Sunset: TBD F7A` +
  `Link: </api/v1>; rel="successor-version"` via
  `LegacyApiDeprecationMiddleware` (RFC 8594 + IETF
  draft-dalal-deprecation-header + RFC 8288).
- **Remoção:** F7A, quando reverse proxy (`api.mathoms.ai → /v1/*`) +
  métricas de tráfego mostrando zero clientes legados estiverem prontos.

Frontend consome `${API_BASE}` = `"/api/v1"` em `frontend/src/lib/api/core.ts`.

### 18.3 Cookies e sessão

- Sempre com prefix `__Host-` (força `Secure`, `HttpOnly`, `Path=/`, sem `Domain`).
- `app.mathoms.ai` e `ops.mathoms.ai` **nunca** compartilham cookies —
  session scope estritamente por subdomain.
- Nenhum cookie com `Domain=mathoms.ai` (vazaria entre todos os subdomínios).

### 18.4 CORS e isolamento

`api.mathoms.ai` aceita apenas origins explícitos:
```
https://app.mathoms.ai
https://ops.mathoms.ai
https://app.staging.mathoms.ai
https://ops.staging.mathoms.ai
```
Nenhum `*`. Nenhum wildcard. Preflight obrigatório para mutações.

### 18.5 DNS e TLS (Cloudflare + Traefik)

**DNS provider:** Cloudflare (domínio registrado lá — zero fricção).

| Record | Tipo | Proxy Cloudflare | Destino |
|---|---|---|---|
| `mathoms.ai` (apex) | A | 🟠 ON (CDN + WAF) | VPS Hetzner |
| `www.mathoms.ai` | CNAME → apex | 🟠 ON | (redirect 301) |
| `docs.mathoms.ai` | CNAME → apex ou A | 🟠 ON (CDN) | VPS / Pages |
| `app.mathoms.ai` | A | ⚪ OFF | VPS Hetzner |
| `api.mathoms.ai` | A | ⚪ OFF | VPS Hetzner |
| `ops.mathoms.ai` | A | ⚪ OFF | VPS Hetzner |
| `status.mathoms.ai` | CNAME | — | BetterStack / Statuspage |
| `*.staging.mathoms.ai` | A | ⚪ OFF | VPS Hetzner (ou staging dedicado) |

**Proxy Cloudflare OFF para app/api/ops:** evita double-TLS, WebSocket
proxying issues e latência extra. Landing e docs ganham proxy ON para
CDN/WAF grátis.

**TLS:** Let's Encrypt via **DNS-01 challenge** (não HTTP-01) — permite
wildcard `*.mathoms.ai`. Traefik provider `cloudflare` com API token de
permissão `Zone:DNS:Edit` apenas para zona `mathoms.ai`.

### 18.6 Segurança do console interno (`ops.mathoms.ai`)

- **IP allowlist** via Traefik middleware `ipAllowList` — apenas IPs do
  time (VPN / escritório / IPs pessoais autorizados).
- **MFA obrigatório** (TOTP mínimo; evoluir para WebAuthn em F7E).
- **Rotas sensíveis do backend** sob `api.mathoms.ai/v1/internal/*`
  com middleware próprio de auth de ops (diferente do `get_current_user`
  de produto).
- **Session cookie separado** de `app.mathoms.ai` (zero-trust entre
  produto e ops).
- **Audit log obrigatório** para toda operação de ops (F7B.5 + F7F).

### 18.7 Emails institucionais

| Endereço | Uso |
|---|---|
| `noreply@mathoms.ai` | Transacionais (verify, reset, invite) |
| `support@mathoms.ai` | Suporte a usuários |
| `hello@mathoms.ai` | Marketing / comercial |
| `ops@mathoms.ai` | Operações internas |
| `security@mathoms.ai` | Disclosure responsável |

SPF + DKIM + DMARC obrigatórios antes do launch. Provider recomendado:
Postmark (transacionais) ou Resend. **Não self-hosted.**

### 18.8 Upgrade path para enterprise custom-domain

Backend já usa header `Host` como chave de tenancy. Para oferecer custom
domain por cliente (enterprise tier futuro):

1. Cliente configura CNAME `<customer-domain>` → `app.mathoms.ai`.
2. Cloudflare for SaaS (ou equivalente) emite cert para o domínio do cliente.
3. Traefik roteia por `Host` header para o workspace correto.

Nenhum refactor de código necessário.
