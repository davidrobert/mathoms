# PRODUCT PLAN — Fin: Planejamento Financeiro Inteligente

> **Documento vivo.** Atualizado a cada sprint. Fonte de verdade para visão, arquitetura, fases e backlog.
>
> **Última atualização:** 2026-04-14
> **Status global:** Fase 6 completa ✅ (6A-6D) — Próxima: Fase 6.5 (Frontend Testing & QA) → Fase 7 (Produção + Dogfood)

---

## Índice

1. [Visão do Produto](#1-visão-do-produto)
2. [Decisões Estratégicas](#2-decisões-estratégicas)
3. [Arquitetura Alvo](#3-arquitetura-alvo)
4. [Estado Atual do Projeto](#4-estado-atual-do-projeto)
5. [Fases de Migração](#5-fases-de-migração)
  - [Fase 0 — Desacoplar Core](#fase-0--desacoplar-core-em-package-python)
  - [Fase 1 — Backend API + Auth](#fase-1--backend-fastapi--auth--db)
  - [Fase 2 — Upload + Pipeline Web](#fase-2--upload-de-arquivos--pipeline-trigger)
  - [Fase 3 — Configuração via UI](#fase-3--configuração-via-ui)
  - [Fase 4 — Automação LLM](#fase-4--automação-llm-premium)
  - [Fase 4.5 — Design System Foundation](#fase-45--design-system-foundation)
  - [Fase 5 — Task Queue + Async](#fase-5--task-queue--real-time-progress)
  - [Fase 6 — Frontend Profissional](#fase-6--frontend-profissional-core-data-experience)
  - [Fase 6.5 — Frontend Testing & QA](#fase-65--frontend-testing--quality-assurance)
  - [Fase 7 — Produção + Security + LGPD](#fase-7--infraestrutura-de-produção--security--lgpd)
6. [Backlog Priorizado](#6-backlog-priorizado)
7. [Sprints](#7-sprints)
8. [Decisões Técnicas Pendentes](#8-decisões-técnicas-pendentes)
9. [Métricas de Sucesso](#9-métricas-de-sucesso)
10. [Riscos e Mitigações](#10-riscos-e-mitigações)
11. [Log de Progresso](#11-log-de-progresso)
12. [Apêndice C: Como Rodar (Setup Local)](#apêndice-c-como-rodar-setup-local)

---

## 1. Visão do Produto

### O que é

**Fin** é um planejador financeiro pessoal inteligente que consolida automaticamente extratos, faturas, investimentos e declarações de IRPF de múltiplos bancos brasileiros, gerando um relatório profissional unificado com score financeiro, análise patrimonial, fluxo de caixa e recomendações.

### Proposta de valor

> "Envie seus PDFs bancários. Receba um retrato financeiro completo da sua família em minutos — não em semanas de planilha."

### Diferenciais competitivos

1. **Parsers nativos para bancos BR** — não depende de Open Banking (ainda limitado no Brasil)
2. **Consolidação multi-banco, multi-membro** — visão família, não indivíduo
3. **IRPF-aware** — cruza dados fiscais com patrimoniais
4. **LLM-augmented** — extrai documentos sem parser determinístico via fallback inteligente
5. **Relatório com narrativa** — não é só número, é contexto e recomendação

### Público-alvo


| Segmento           | Perfil                                                          | Dor                                               |
| ------------------ | --------------------------------------------------------------- | ------------------------------------------------- |
| **Primário**       | Profissionais PJ/CLT alta renda, múltiplas contas               | Não conseguem ver o retrato completo das finanças |
| **Secundário**     | Famílias com patrimônio diversificado (imóveis + investimentos) | Consolidação manual em planilha demora dias       |
| **Futuro (B2B2C)** | Planejadores financeiros independentes                          | Ferramenta white-label para atender clientes      |


---

## 2. Decisões Estratégicas


| Decisão                | Escolha                                  | Data       | Rationale                                                                              |
| ---------------------- | ---------------------------------------- | ---------- | -------------------------------------------------------------------------------------- |
| Modelo de negócio      | **Freemium**                             | 2026-04-13 | Free = pipeline determinístico. Premium = LLM + features avançadas                     |
| Primeiro cliente       | **Dogfood (David)**                      | 2026-04-13 | Refinar até estar perfeito antes de abrir                                              |
| LLM strategy           | **BYOK (Bring Your Own Key)**            | 2026-04-14 | ✅ Implementado F4. Free sem LLM. Premium: user traz sua API key via LiteLLM+Instructor |
| Task queue             | **Celery + Redis**                       | 2026-04-14 | ✅ Implementado F5. Sync-native, maduro, Pub/Sub para WS events, fallback Thread        |
| Real-time progress     | **WebSocket + Polling fallback**         | 2026-04-14 | ✅ Implementado F5. WS via Redis Pub/Sub, polling backward-compat Fase 2                |
| Frontend               | **Next.js + TypeScript**                 | 2026-04-13 | Performático, tipagem estática, ecossistema maduro                                     |
| Backend                | **FastAPI (Python)**                     | 2026-04-13 | Mesma linguagem dos scripts, async, Pydantic nativo                                    |
| Banco de dados         | **PostgreSQL** (prod) / **SQLite** (dev) | 2026-04-13 | Robusto, JSON support, full-text search                                                |
| Type safety end-to-end | **openapi-typescript**                   | 2026-04-13 | FastAPI OpenAPI → TS types auto-gerados                                                |


---

## 3. Arquitetura Alvo

### Diagrama de componentes

```
┌──────────────────────────────────────────────────────────────┐
│                    FRONTEND (SPA)                              │
│  Next.js 16 + TypeScript + Tailwind CSS 4 + Recharts          │
│  Upload, Config, Dashboard, Reports, Onboarding, Landing      │
└────────────────────────┬─────────────────────────────────────┘
                         │ REST API (OpenAPI)
                         │ + WebSocket (progress, via Redis Pub/Sub)
┌────────────────────────┴─────────────────────────────────────┐
│                  BACKEND (API Server)                           │
│  FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2              │
│                                                                │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────┐  │
│  │ Auth Module   │  │ Pipeline      │  │ LLM Service        │  │
│  │ JWT + bcrypt  │  │ Orchestrator  │  │ LiteLLM+Instructor │  │
│  │ Fernet vault  │  │ (F0 wrappers) │  │ BYOK, auto-retry   │  │
│  └──────────────┘  └───────────────┘  └────────────────────┘  │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │         Pipeline Core (package Python)                    │  │
│  │   e0/ e2/ e3/ e4/ e5/ e5n/ e6/ e7/ models/               │  │
│  │   + llm/prompts/ + llm/validators/ (F4)                   │  │
│  │   + materialize_config() (F3)                             │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────┬────────────────┬────────────────┬─────────────────┘
           │                │                │
      ┌────┴─────┐   ┌─────┴──────┐   ┌─────┴──────────────┐
      │PostgreSQL │   │File Storage│   │Celery + Redis       │
      │(prod)     │   │Docker vol  │   │ broker, result,     │
      │SQLite     │   │per-tenant  │   │ Pub/Sub (WS events) │
      │(dev)      │   │            │   │                     │
      └──────────┘   └────────────┘   └─────────────────────┘
                                            │
                              ┌──────────────┘
                              │ (produção)
                      ┌───────┴──────────┐
                      │ Traefik v3        │
                      │ Reverse proxy     │
                      │ Auto-SSL (LE)     │
                      │ Docker labels     │
                      └──────────────────┘
```

### Type safety ponta-a-ponta

```
FastAPI (Pydantic models)
    → auto-generate OpenAPI schema (JSON)
        → openapi-typescript (build step)
            → TypeScript types (.d.ts)
                → Next.js consome com fetch type-safe
```

### Modelo de dados (implementado)

```
# --- Fase 1: Auth + Core ---

User                                                            # ✅ Implementado
  id, email, hashed_password, name, tier, created_at
  llm_api_key (encrypted)

Workspace                                                       # ✅ Implementado (+ relationships Fase 3)
  id, user_id, name, created_at
  → family_members[], categories[], pipeline_config, institution_config, report_layout

# --- Fase 2: Upload + Pipeline ---

Document                                                        # ✅ Implementado
  id, workspace_id, original_name, stored_path, doc_type, bank_code, period
  status (uploaded|unlocking|classifying|ready|needs_password|processing|processed|error)
  classification_meta (JSON), uploaded_at

PasswordVault                                                   # ✅ Implementado
  id, workspace_id, label, encrypted_password (Fernet), created_at

PipelineRun                                                     # ✅ Implementado (+ Fase 4: tier, review, resume + Fase 5: celery)
  id, workspace_id, status (pending|running|completed|failed|cancelled|needs_review|resuming)
  current_stage, started_at, completed_at, config_snapshot (JSON)
  tier_at_run (free|premium), paused_at_stage
  celery_task_id (String, nullable — Fase 5)

PipelineStageLog                                                # ✅ Implementado (+ Fase 4: skipped_free_tier, needs_review)
  id, pipeline_run_id, stage
  status (pending|running|completed|failed|skipped|skipped_free_tier|needs_review)
  started_at, completed_at, output_summary, errors

Report                                                          # ✅ Implementado
  id, pipeline_run_id, html_path, period_start, period_end
  created_at, score, patrimonio_liquido

# --- Fase 3: Config via UI (normalizados) ---

FamilyMember                                                    # ✅ Implementado
  id, workspace_id, key, full_name, short_name
  cpf_encrypted (Fernet), birth_date, role, order, extra (JSON)
  → accounts[]

BankAccount                                                     # ✅ Implementado
  id, member_id (FK), institution_code, account_type, agency, account_number

Category                                                        # ✅ Implementado
  id, workspace_id, code, name, category_type (receita|despesa)
  monthly_cap, order
  → keywords[]

CategoryKeyword                                                 # ✅ Implementado
  id, category_id (FK), keyword

# --- Fase 3: Config via UI (JSON blobs) ---

PipelineConfig                                                  # ✅ Implementado
  id, workspace_id (unique), config_json (JSON — tolerances, thresholds, formatting)

InstitutionConfig                                               # ✅ Implementado
  id, workspace_id (unique), config_json (JSON — patterns por banco)

ReportLayout                                                    # ✅ Implementado
  id, workspace_id (unique), config_json (JSON — YAML convertido para JSON)

# --- Fase 4: Automação LLM ---

LLMConfig                                                   # ✅ Implementado
  id, workspace_id (unique), provider (anthropic|openai|ollama|...)
  api_key_encrypted (Fernet), model_name, max_tokens, temperature
  created_at, updated_at

StageReview                                                 # ✅ Implementado
  id, pipeline_run_id, stage, status (pending|approved|edited)
  original_output_json, edited_output_json
  validation_errors, reviewer_notes, created_at, reviewed_at

# --- Fase 7: Produção + Security + LGPD ---

AuditEntry
  id, user_id, action (enum), resource_type, resource_id, ip, user_agent, timestamp, details_json

User (expandido Fase 7)
  + accepted_terms_at, refresh_token_hash, refresh_token_expires_at
```

### Estrutura de pastas atual (pós-Fase 5 completa)

```
fin-current/
├── backend/                     # ← Fases 1-5 backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py                    # Fase 1: register/login/me
│   │   │   ├── reports.py                 # Fase 1: list/get/html
│   │   │   ├── vault.py                   # Fase 2A: CRUD senhas encriptadas
│   │   │   ├── documents.py               # Fase 2B: upload/list/delete/retry-unlock
│   │   │   ├── pipeline.py                # Fase 2C + 4D + 5C: run/list/status/cancel/resume/reviews
│   │   │   ├── config.py                  # Fase 3B: 18 endpoints config
│   │   │   ├── llm.py                     # Fase 4A: LLM config CRUD, test, tier
│   │   │   └── ws.py                      # Fase 5B: WebSocket /pipeline/runs/{id}/ws (JWT auth, Redis Pub/Sub)
│   │   ├── core/
│   │   │   ├── config.py                  # Settings (+ REDIS_URL Fase 5)
│   │   │   ├── database.py                # Async + sync engines, Alembic-ready
│   │   │   ├── deps.py                    # get_current_user dependency
│   │   │   └── security.py                # JWT + bcrypt
│   │   ├── models/
│   │   │   ├── __init__.py                # Exporta todos os modelos (16 modelos total)
│   │   │   ├── user.py, workspace.py      # Fase 1 (workspace expandido com relationships)
│   │   │   ├── report.py                  # Fase 1 + pipeline_run_id (Fase 2)
│   │   │   ├── document.py                # Fase 2A: DocumentStatus/Type enums
│   │   │   ├── password_vault.py          # Fase 2A: Fernet-encrypted passwords
│   │   │   ├── pipeline_run.py            # Fase 2A + 4 + 5: PipelineRun (+ celery_task_id) + StageLog
│   │   │   ├── family_member.py           # Fase 3A: FamilyMember + BankAccount (normalizados)
│   │   │   ├── category.py                # Fase 3A: Category + CategoryKeyword (normalizados)
│   │   │   ├── config_blob.py             # Fase 3A: PipelineConfig, InstitutionConfig, ReportLayout (JSON blobs)
│   │   │   ├── llm_config.py              # Fase 4A: LLMConfig (provider, encrypted API key, model, params)
│   │   │   └── stage_review.py            # Fase 4A: StageReview (pending/approved/edited, original/edited output)
│   │   ├── schemas/
│   │   │   ├── auth.py, report.py         # Fase 1
│   │   │   ├── document.py                # Fase 2B
│   │   │   ├── vault.py                   # Fase 2A
│   │   │   ├── pipeline.py                # Fase 2C + 4D + 5: tier, paused, celery_task_id, StageReview
│   │   │   ├── config.py                  # Fase 3A: 17 Pydantic schemas
│   │   │   ├── llm.py                     # Fase 4A: LLM config schemas
│   │   │   └── events.py                  # Fase 5B: PipelineEvent, StageEvent, RunEvent, ErrorEvent
│   │   ├── services/
│   │   │   ├── seed.py                    # Fase 1
│   │   │   ├── storage.py                 # Fase 2A: StorageService (tenant dirs, quotas)
│   │   │   ├── vault.py                   # Fase 2A: VaultService (Fernet encrypt/decrypt)
│   │   │   ├── document_processor.py      # Fase 2B: unlock + classify + JSON detect
│   │   │   ├── pipeline_service.py        # Fase 2C + 4D + 5A: Celery dispatch, fallback thread, cancel via DB
│   │   │   ├── config_materializer.py     # Fase 3C + 4A: materialize_config()
│   │   │   ├── events.py                  # Fase 5A: Redis Pub/Sub event publisher (stage/run events)
│   │   │   └── retry_config.py            # Fase 5C: per-stage retry config (max_retries, retryable errors)
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   └── pipeline_task.py           # Fase 5A: Celery @task — pipeline execution with events + retry
│   │   ├── worker.py                      # Fase 5A: Celery app config (broker, backend, concurrency)
│   │   └── main.py                        # FastAPI app (8 routers incl. WS)
│   ├── alembic/                           # Database migrations
│   │   ├── env.py, script.py.mako
│   │   └── versions/                      # 4 migrations (F2 + F3 + F4 + F5 celery_task_id)
│   ├── tests/                             # ~300 testes backend
│   │   ├── conftest.py                    # StaticPool + FERNET_KEY fixture
│   │   ├── test_auth.py, test_reports.py  # Fase 1
│   │   ├── test_models.py                 # Fase 2A: 6 modelos
│   │   ├── test_storage.py               # Fase 2A: StorageService + VaultService
│   │   ├── test_vault.py                  # Fase 2A: vault API
│   │   ├── test_documents.py             # Fase 2B: upload/list/delete/retry
│   │   ├── test_document_processor.py    # Fase 2B: processor unit tests
│   │   ├── test_pipeline_api.py          # Fase 2C: trigger/status/cancel
│   │   ├── test_config_models.py         # Fase 3A: 7 modelos config + Pydantic schemas (30 testes)
│   │   ├── test_config_materializer.py   # Fase 3C + 4A: serializers + materialize_config + llm_config
│   │   ├── test_config_api.py            # Fase 3B: config API integration
│   │   ├── test_llm_config.py            # Fase 4A: LLMConfig/StageReview models + LLM API endpoints (52 testes)
│   │   ├── test_llm_service.py           # Fase 4A: LLMService + DocumentTextExtractor (mock tests)
│   │   ├── test_pipeline_review.py       # Fase 4D: tier detection, reviews CRUD, resume workflow (14 testes)
│   │   ├── test_events.py               # Fase 5A: Redis Pub/Sub events (14 testes)
│   │   ├── test_pipeline_task.py        # Fase 5A: Celery task, cancellation, event schemas (10 testes)
│   │   ├── test_pipeline_phase5.py      # Fase 5C: concurrency, cancel, resume, polling, health (12 testes)
│   │   └── test_retry_config.py         # Fase 5C: stage retry config (8 testes)
│   ├── alembic.ini
│   ├── requirements.txt                   # + celery[redis], redis, websockets (F5)
│   └── seed_db.py
├── docker-compose.yml             # ← Fase 5: Redis service (redis:7-alpine)
├── frontend/                    # ← Fase 1 + Fase 2D + Fase 3D + Fase 5B
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx, page.tsx, globals.css
│   │   │   ├── login/page.tsx, register/page.tsx
│   │   │   └── (app)/               # Route group com AppShell (sidebar nav)
│   │   │       ├── layout.tsx        # AppShell wrapper
│   │   │       ├── documents/page.tsx  # Upload drag-and-drop + documents table
│   │   │       ├── pipeline/page.tsx   # Trigger + WS real-time progress + polling fallback + stage bar + needs_review
│   │   │       ├── vault/page.tsx      # Password vault CRUD + retry unlock
│   │   │       ├── config/             # Fase 3D: 6 config tabs
│   │   │       │   ├── page.tsx, MembersTab.tsx, CategoriesTab.tsx
│   │   │       │   ├── PipelineTab.tsx, InstitutionsTab.tsx
│   │   │       │   ├── ReportLayoutTab.tsx, ImportExportTab.tsx
│   │   │       └── reports/
│   │   │           ├── page.tsx        # Reports list
│   │   │           └── [id]/page.tsx   # Report viewer (iframe)
│   │   ├── components/
│   │   │   └── AppShell.tsx          # Sidebar + mobile nav + user info
│   │   └── lib/
│   │       ├── api.ts                # 30+ API functions + types (+ PipelineEvent, needs_review/resuming statuses)
│   │       ├── format.ts             # Status labels (+ needs_review, skipped_free_tier), bank names, formatters
│   │       └── usePipelineWS.ts      # Fase 5B: WebSocket hook (auto-connect, reconnect, polling fallback)
│   ├── next.config.ts
│   └── package.json
├── pipeline/                    # ← Fase 0 + Fase 4 (LLM stages + service)
│   ├── __init__.py              # API pública v0.2.0
│   ├── context.py               # WorkspaceContext (+ config_dir override, Fase 2)
│   ├── config_loader.py         # Loader unificado
│   ├── orchestrator.py          # run_pipeline, run_from, run_stages — todos LLM stages registrados (Fase 4)
│   ├── llm/                     # Fase 4A: LLM infrastructure
│   │   ├── __init__.py
│   │   ├── service.py           # LLMService: LiteLLM + Instructor, retry, token tracking, cost estimation
│   │   ├── text_extractor.py    # DocumentTextExtractor: PDF/XLSX/CSV → text para prompts
│   │   ├── validators.py        # Fase 4B: validadores de compatibilidade (E1→members, E1.5→E3, E2-llm→E3)
│   │   ├── prompts/             # Prompt templates por LLM stage
│   │   │   ├── e1_members.py, e15_baseline.py
│   │   │   ├── e2_llm.py, e7_review.py
│   │   │   └── __init__.py
│   │   └── schemas/             # Pydantic output schemas (Instructor enforcement)
│   │       ├── e1_members.py, e15_baseline.py
│   │       ├── e2_llm_extract.py, e7_review.py
│   │       └── __init__.py
│   └── stages/                  # Wrappers por etapa — 4 novos LLM stages (Fase 4)
│       ├── e0_audit.py, e0_route.py, e0_unlock.py
│       ├── e1.py                # Fase 4B: E1 LLM member extraction
│       ├── e15.py               # Fase 4B: E1.5 LLM baseline patrimonial
│       ├── e15c.py, e2.py
│       ├── e2_llm.py            # Fase 4B: E2-llm extraction for docs without det. parser
│       ├── e3.py, e4.py, e5.py, e5n.py, e6.py
│       ├── e7.py                # E7-crossval + E7-apply (determinísticos)
│       ├── e7_review_llm.py     # Fase 4C: E7-review LLM holistic financial review
│       └── __init__.py
├── scripts/                     # CLI (inalterado, com _init_config adicionado)
│   ├── e0_audit.py, e0_route.py, e0_unlock.py
│   ├── e15_consolidate.py, e2_extract.py
│   ├── e2/banks/               # 11 parsers bancários
│   ├── e3_reconcile.py, e4_categorize.py
│   ├── e5_analyze.py, e5n_narrativas.py
│   ├── e6_render.py, e7_review.py
│   ├── e_reset.py, e_save.py
│   └── pipeline_common.py
├── storage/                     # ← Fase 2: per-tenant file storage (.gitignore)
├── config/                      # Configurações (22 arquivos)
├── tests/                       # Testes do pipeline (204 tests)
│   ├── fixtures/llm_golden/     # Fase 4B: golden files para snapshot tests
│   │   ├── e1_members_output.json, e15_baseline_output.json
│   │   ├── e2_llm_extract_output.json, e7_review_output.json
│   ├── test_llm_stages.py       # Fase 4B: LLM stages, validators, converters (48 testes)
│   ├── test_llm_golden.py       # Fase 4B: golden file snapshot tests (19 testes)
│   ├── test_orchestrator.py, test_stage_wrappers.py  # atualizados para LLM stages
│   └── ... (demais testes pipeline)
├── docs/PRODUCT_PLAN.md         # ← este documento
└── pyproject.toml               # Package fin-pipeline v0.2.0
```

### Estrutura de pastas alvo (pós-migração completa)

```
fin/
├── backend/
│   ├── alembic/                  # DB migrations (4 migrations: F2, F3, F4, F5)
│   ├── app/
│   │   ├── api/                  # FastAPI routers (8 routers incl. WS)
│   │   │   ├── auth.py           # F1: register/login/me
│   │   │   ├── documents.py      # F2B: upload/list/delete/retry-unlock
│   │   │   ├── pipeline.py       # F2C+4D+5C: run/list/status/cancel/resume/reviews
│   │   │   ├── reports.py        # F1: list/get/html
│   │   │   ├── config.py         # F3B: 18 endpoints config
│   │   │   ├── vault.py          # F2A: CRUD senhas encriptadas
│   │   │   ├── llm.py            # F4A: LLM config CRUD, test, tier
│   │   │   └── ws.py             # F5B: WebSocket /pipeline/runs/{id}/ws
│   │   ├── core/                 # Auth, security, settings (+ REDIS_URL F5)
│   │   ├── models/               # SQLAlchemy models (16 modelos)
│   │   ├── schemas/              # Pydantic request/response (+ events.py F5)
│   │   ├── services/             # Business logic (+ events.py, retry_config.py F5)
│   │   ├── tasks/                # F5A: Celery tasks
│   │   │   └── pipeline_task.py  # run_pipeline_task (events + retry + cancel)
│   │   ├── worker.py             # F5A: Celery app config (broker, backend, concurrency)
│   │   └── main.py               # FastAPI app (8 routers incl. WS)
│   ├── pipeline/                 # Pipeline core (refatorado)
│   │   ├── core/                 # E0-E7 como módulos
│   │   ├── llm/                  # LLM service (F4: LiteLLM + Instructor) ✅
│   │   │   ├── service.py, text_extractor.py, validators.py
│   │   │   ├── prompts/          # Templates por stage (e1, e15, e2_llm, e7_review)
│   │   │   └── schemas/          # Pydantic output schemas (Instructor enforcement)
│   │   ├── models/               # Pydantic models dos artefatos (futuro)
│   │   └── orchestrator.py       # Substitui e_reset.py
│   ├── scripts/                  # CLIs thin wrappers (retrocompat)
│   ├── storage/                  # File storage por tenant (.gitignore)
│   ├── tests/                    # ~284 testes backend
│   ├── requirements.txt          # + celery[redis], redis, websockets (F5)
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js App Router
│   │   │   ├── login/, register/ # Auth pages
│   │   │   └── (app)/            # Route group com AppShell
│   │   │       ├── documents/, pipeline/, vault/, config/, reports/
│   │   │       └── layout.tsx    # AppShell wrapper + Toaster
│   │   ├── components/
│   │   │   ├── ui/               # 16 shadcn/ui primitivos
│   │   │   └── *.tsx             # 7 compostos + AppShell
│   │   └── lib/
│   │       ├── api.ts            # 30+ API functions + types
│   │       ├── format.ts         # Status labels + financial formatters
│   │       ├── usePipelineWS.ts  # F5B: WS hook (auto-connect, reconnect, fallback)
│   │       └── utils.ts          # cn() utility
│   ├── package.json
│   └── tsconfig.json
│
├── docker-compose.yml            # F5: Redis 7-alpine service
├── docs/
│   └── PRODUCT_PLAN.md           # ← este documento
└── README.md
```

---

## 4. Estado Atual do Projeto

### O que já existe e funciona


| Asset                    | Detalhes                                                                                          | Valor                                  |
| ------------------------ | ------------------------------------------------------------------------------------------------- | -------------------------------------- |
| **11 parsers bancários** | C6, Itaú, Santander, Bradesco, BTG, Rico, PicPay, Wise, BoA, QuintoAndar, Binance                 | Alto — difícil de replicar             |
| **Pipeline E0→E7**       | 14 etapas, 31 scripts Python, ~860KB de código                                                    | Alto — lógica de domínio refinada      |
| **Categorização**        | 300+ keywords em 16 categorias                                                                    | Médio — expansível                     |
| **Relatório HTML**       | ~411KB, Chart.js, dark mode, narrativas                                                           | Médio — precisa virar componente       |
| **Reconciliação**        | Deduplicação cross-banco, transferências internas                                                 | Alto — lógica complexa                 |
| **Cross-validation**     | 14 checks automáticos no E7                                                                       | Médio — qualidade do output            |
| **Config estruturada**   | 22 arquivos em config/ (JSON, YAML, MD). 5 editáveis via DB + UI (Fase 3 ✅)                       | Médio — completo                       |
| **LLM Integration**      | LiteLLM+Instructor, 4 LLM stages, BYOK, validators, tier detection (Fase 4 ✅)                     | Alto — pipeline premium end-to-end     |
| **Design System**        | shadcn/ui v4 + 30+ tokens oklch + 7 compostos + Lucide + Geist fonts (Fase 4.5 ✅)                 | Alto — fundação para Fases 6-7         |
| **Task Queue**           | Celery + Redis, WS real-time, polling fallback, stage-boundary cancel, per-stage retry (Fase 5 ✅) | Alto — infra assíncrona robusta        |
| **Frontend**             | ~5.800 linhas, 47 arquivos, 25 componentes + WS hook + toast notifications                        | Alto — design system profissional      |
| **Testes**               | ~488 tests (204 pipeline + ~284 backend) em tests/ e backend/tests/                               | Alto — cobertura crescendo a cada fase |


### O que foi adicionado (Fases 0–5)

- ✅ **Web framework:** FastAPI (backend) + Next.js 16 (frontend)
- ✅ **Banco de dados:** SQLAlchemy 2.0 async + SQLite (dev) + Alembic migrations (4 migrations)
- ✅ **Autenticação:** JWT + bcrypt (register/login/me)
- ✅ **UI web:** Login, registro, relatórios, viewer, config (6 tabs), upload, pipeline (WS + polling), vault
- ✅ **Pipeline como package:** `from pipeline import run_pipeline` funciona
- ✅ **Contexto injetável:** `WorkspaceContext` permite multi-tenant
- ✅ **Storage por tenant:** `StorageService` com isolamento, sanitização, quotas
- ✅ **Vault de senhas:** Fernet encryption, CRUD API para senhas de PDFs
- ✅ **Upload de documentos:** Multipart batch (até 20 arquivos), validação, classificação automática
- ✅ **E0 processing no upload:** PDF unlock via vault + classify via E0-route regex
- ✅ **Pipeline execution API:** Celery task (com fallback Thread), tracking por stage, cancel stage-boundary, from_stage, resume, reviews CRUD
- ✅ **Document processor:** JSON E1/E1.5 detection, PDF unlock, E0-route classification
- ✅ **6 modelos Fase 2:** User, Workspace, Report, Document, PasswordVault, PipelineRun/StageLog
- ✅ **5 modelos Fase 3:** FamilyMember+BankAccount, Category+CategoryKeyword, PipelineConfig/InstitutionConfig/ReportLayout
- ✅ **2 modelos Fase 4:** LLMConfig (API key encrypted at-rest), StageReview (pending/approved/edited)
- ✅ **18 endpoints Config API:** CRUD membros/contas/categorias, GET/PUT pipeline/institutions/report-layout, import/export JSON
- ✅ **7 endpoints LLM/Review API (Fase 4):** LLM config CRUD, test connectivity, tier, reviews list/approve/edit, resume
- ✅ **Materialização de config:** `materialize_config()` copia config/ global → tenant, sobrescreve com DB — inclui LLM config
- ✅ **Fallback seletivo:** GET retorna defaults do disco se DB vazio — sem seed obrigatório
- ✅ **CPF criptografado at-rest:** Fernet via VaultService, validação de 11 dígitos no schema
- ✅ **LLM Service (4A):** LiteLLM + Instructor, multi-provider (6 provedores), structured output, retry exponencial, error classification, token tracking + cost estimation
- ✅ **4 LLM Stage Runners (4B/4C):** E1 (members), E1.5 (baseline patrimonial), E2-llm (docs sem parser det.), E7-review (holistic review). Cada um com prompt, schema Pydantic, e validador de compatibilidade downstream
- ✅ **Tier Detection (4D):** Free → LLM stages auto-skipados (`skipped_free_tier`). Premium → pipeline completo end-to-end
- ✅ **needs_review workflow (4D):** Validação falha → pipeline pausa → user edita JSON via API → resume do stage seguinte
- ✅ **Frontend Upload (2D):** Drag-and-drop batch upload com XHR progress, documents table, vault CRUD
- ✅ **Frontend Pipeline (2D → 5B):** Trigger com opções, WS real-time progress + polling 2s fallback, stage bar animada, toast Sonner, cancel com confirmação, auto-redirect
- ✅ **AppShell (2D):** Sidebar navigation (5 seções), mobile responsive, user info + logout
- ✅ **Design System (4.5A):** Tailwind v4 `@theme inline` com 30+ tokens oklch, Geist Sans + Geist Mono via `next/font/google`, paleta financeira semântica (gain/loss/alert/info/neutral), 12 chart colors
- ✅ **Financial Formatting (4.5A):** `format.ts` com 9 formatters (`formatCurrency`, `formatPercent`, `formatDelta`, `formatCompact`, `formatNumber`, `formatPeriod`, `formatMonth`, `formatRange`) + 3 status maps retornando `{ label, variant }` semântico
- ✅ **shadcn/ui (4.5B):** 16 primitivos (base-ui/react + radix), 7 compostos (`StatusBadge`, `Spinner`, `EmptyState`, `Delta`, `KPICard`, `PageHeader`, `ConfirmDialog`), `cn()` utility
- ✅ **Page Migration (4.5C):** 10 pages + AppShell migradas para design system. Lucide icons. Zero spinner duplicado, zero `confirm()` nativo, tabs ARIA, toggles `Switch`
- ✅ **Task Queue (5A):** Celery + Redis. `run_pipeline_task` como `@celery_app.task`. `pipeline_service.py` usa `task.delay()` com fallback Thread se Redis indisponível
- ✅ **Redis Pub/Sub Events (5A):** `events.py` publica `stage_started/completed/failed/skipped`, `needs_review`, `run_completed/failed/cancelled` no channel `pipeline:{run_id}`
- ✅ **WebSocket (5B):** `WS /api/pipeline/runs/{id}/ws` com JWT auth, subscribe Redis Pub/Sub, forward JSON, heartbeat 15s. `usePipelineWS` React hook com auto-reconnect exponential backoff
- ✅ **Stage-boundary Cancel (5C):** `cancel_pipeline_run` seta status DB + revoke Celery task + publica `run_cancelled`. Stages completos mantidos
- ✅ **Per-stage Retry (5C):** `retry_config.py` com `StageRetryConfig(max_retries, retryable_errors, delay, backoff)`. LLM stages: 1-2 retries. Det. stages: 0
- ✅ **Health Check (5A):** `GET /api/health` reporta status de Redis, Celery worker, e DB
- ✅ **Docker Compose (5A):** Redis 7-alpine (appendonly, healthcheck, maxmemory 256mb)

### O que NÃO existe ainda

- ~~Nenhum web framework~~ → FastAPI + Next.js (Fase 1)
- ~~Nenhum banco de dados~~ → SQLAlchemy + SQLite (Fase 1)
- ~~Nenhuma autenticação~~ → JWT + bcrypt (Fase 1)
- ~~Nenhuma UI~~ → Next.js com login, relatórios, viewer (Fase 1)
- ~~Multi-tenancy sem isolamento~~ → StorageService + workspace scoping (Fase 2)
- ~~Sem upload de documentos~~ → Upload + E0 processing (Fase 2)
- ~~Sem configuração via API~~ → 18 endpoints Config API + materialização (Fase 3)
- ~~Frontend de upload/documents/pipeline~~ → ✅ Completo (Fase 2D)
- ~~Frontend de configuração~~ → ✅ Config page com 6 tabs (Fase 3D)
- ~~LLM calls manuais~~ → ✅ LLM stages automatizados via LiteLLM + Instructor (Fase 4)
- ~~Sem design system / componentes visuais padronizados~~ → ✅ shadcn/ui + design tokens + 7 compostos + 10 pages migradas (Fase 4.5)
- ~~Sem task queue / processamento assíncrono~~ → ✅ Celery + Redis + WebSocket real-time (Fase 5)
- ~~Sem progresso em tempo real~~ → ✅ WebSocket + polling fallback (Fase 5)
- ~~Sem retry automático~~ → ✅ Per-stage retry config com backoff exponencial (Fase 5)
- Sem dashboard com alertas / report React components / Transaction Explorer — Fase 6
- Sem PWA / command palette / notification center — Fase 6

---

## 5. Fases de Migração

> **Regra de ouro:** Após cada fase, o pipeline continua funcionando e gerando relatórios corretos.

### Visão geral


| Fase    | Nome                     | Duração est. | Pré-requisito | Entrega principal                                                                            | Status                  |
| ------- | ------------------------ | ------------ | ------------- | -------------------------------------------------------------------------------------------- | ----------------------- |
| **0**   | Desacoplar Core          | 3-4 sem      | —             | Pipeline como package Python importável + contexto injetável                                 | ✅ Concluída             |
| **1**   | Backend API + Auth       | 2-3 sem      | Fase 0        | Login/registro + API de relatórios + Frontend MVP                                            | ✅ Concluída             |
| **2**   | Upload + Pipeline Web    | 3-4 sem      | Fase 1        | Upload + unlock/classify auto + pipeline pseudo-async                                        | ✅ Concluída (2A-2D)     |
| **3**   | Configuração via UI      | 3-4 sem      | Fase 2        | Config editável via UI + materialização + import/export JSON                                 | ✅ Concluída (3A-3D)     |
| **4**   | Automação LLM            | 3-4 sem      | Fase 3        | LiteLLM+Instructor, BYOK, Premium E2E, review manual, tier                                   | ✅ Concluída (4A-4D)     |
| **4.5** | Design System Foundation | 2 sem        | Fase 4        | Tailwind v4 @theme tokens, Geist fonts, shadcn/ui, 7 componentes financeiros, page migration | ✅ Concluída (4.5A-4.5C) |
| **5**   | Task Queue + Async       | 2-3 sem      | Fase 4.5      | Celery+Redis, WS+polling, cancel stage-boundary, concurrency                                 | ✅ Concluída (5A-5C)     |
| **6**   | Frontend Profissional    | 6-8 sem      | Fase 5        | Dashboard, Transaction Explorer, Report React interativo, Dark mode, Notifications, Export    | ✅ Concluída (6A-6D)     |
| **6.5** | Frontend Testing & QA    | 2 sem        | Fase 6        | Vitest + RTL + MSW + Playwright. Unit, integration, E2E. Smoke test checklist. CI gates      | ☐                       |
| **7**   | Produção + LGPD          | 6-8 sem      | Fase 6.5      | VPS+Docker+Traefik, LGPD, CI/CD, coverage gate, dogfood                                      | ☐                       |


**Timeline total estimada: ~11 meses / 21 sprints** (com entregas funcionais a cada 2-3 semanas).

---

### Política de Testes e Cobertura

> **Meta final: 100% line coverage + 90% branch coverage de todo o Python do backend (API + services + pipeline scripts).**

#### Princípios

1. **Testes começam na Fase 2.** A partir desta fase, nenhum merge é aceito se o código novo não tiver 100% de line coverage.
2. **Cobertura global cresce progressivamente** fase a fase, com metas explícitas por fase.
3. **Fase 7 tem sprint dedicado** para atingir 100% global backend + adicionar testes de frontend.
4. **Exclusões mínimas:** apenas migrations Alembic auto-geradas e arquivos `__init__.py` vazios.

#### Escopo da cobertura

- **Inclui:** todo código Python — `backend/app/`, `pipeline/`, `scripts/` (lógica interna dos parsers, reconciliação, categorização, análise, renderização)
- **Inclui:** edge cases, error paths, branches de validação
- **Exclui:** migrations Alembic, `__init__.py` vazios
- **Frontend:** testes adicionados na Fase 6.5 (Vitest + React Testing Library + Playwright). Meta separada: ≥80% lib/, ≥70% pages/.

#### Tooling

```
pytest + pytest-cov + coverage.py   → execução e medição
GitHub Actions CI gate              → bloqueia merge se coverage de código novo < 100%
codecov (ou similar)                → dashboard de cobertura, trends, diffs por PR
```

#### Metas progressivas de cobertura global


| Fase     | Meta line | Meta branch | Foco de testes                                                                                                                   |
| -------- | --------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **F0**   | ~30%      | —           | ✅ 136 tests. Regressão golden files. Wrappers. Orchestrator.                                                                     |
| **F1**   | ~40%      | —           | ✅ +13 tests (149 total). Auth endpoints, JWT, API de relatórios.                                                                 |
| **F2**   | ~55%      | ~40%        | ✅ Upload, vault, E0 processing, pipeline execution, E2E. **CI gate ativado**                                                     |
| **F3**   | ~65%      | ~50%        | ✅ CRUD config, config injection, serialização DB→pipeline                                                                        |
| **F4**   | ~75%      | ~60%        | ✅ 444 tests (204 pipeline + 240 backend). LLM service (mocks), validators, retry, tier detection, reviews, golden file snapshots |
| **F4.5** | ~75%      | ~60%        | Frontend-only (design system, shadcn/ui, page migration). Nenhum código Python novo. Zero testes Python adicionados              |
| **F5**   | ~85%      | ~70%        | Task queue, async execution, WebSocket, cancelamento                                                                             |
| **F6**   | ~90%      | ~80%        | Edge cases restantes, error paths, integration gaps                                                                              |
| **F6.5** | ~90%      | ~80%        | **Frontend tests:** ~240 tests (60 unit + 150 integration + 30 E2E). ≥80% lib/, ≥70% pages/. Zero testes Python adicionados     |
| **F7**   | **≥95%**  | **≥85%**    | Gap-fill scripts legados, error paths exaustivos, CI coverage gate                                                               |


#### O desafio dos scripts legados

Os scripts de pipeline totalizam ~14.000 linhas de código com lógica de domínio complexa. Atingir 100% de line coverage neles requer:

1. **Testes de integração** (rodar pipeline com dados de teste) cobrem ~60-70% naturalmente (happy path)
2. **Unit tests por módulo** (E3, E4, E5 etc.) cobrem edge cases e error paths
3. **Golden file tests** garantem não-regressão mas não cobrem todos os branches
4. **Sprint dedicado na Fase 7** para gap-fill sistemático dos scripts maiores (E5=107KB, E6=197KB)

Estratégia: cobertura cresce organicamente nas Fases 0-6 via testes de integração e unit tests do código novo. Fase 7 faz o push final nos scripts legados.

---

### FASE 0 — Desacoplar Core em Package Python ✅ CONCLUÍDA

**Objetivo:** Tornar os scripts chamáveis programaticamente com paths e configs injetáveis, sem reescrever a lógica interna.

**Resultado:** 136 testes passando. Pipeline 100% importável via `from pipeline import run_pipeline`. Commits: `a4b1c3e` (0B), `f50b954` (0C+0D).

**Estratégia: "Wrap, Don't Rewrite"**

Os scripts são grandes (E6=197KB, E5=107KB) e têm lógica de domínio refinada. Reescrevê-los é arriscado. Em vez disso:

1. Criar uma camada de **contexto** (`WorkspaceContext`) que fornece paths e configs
2. **Envolver** cada script com uma função que aceita esse contexto
3. O código interno dos scripts permanece **inalterado** inicialmente
4. CLIs continuam funcionando exatamente como antes

**Duração estimada:** 3-4 semanas (4 sub-fases)

#### Diagnóstico técnico dos acoplamentos atuais


| Acoplamento                   | Onde ocorre                 | Impacto                                                  |
| ----------------------------- | --------------------------- | -------------------------------------------------------- |
| Paths via `__file__`          | Todos os 14 scripts         | Impede rodar com root diferente (multi-tenant)           |
| Config no module-level        | e2/common, e3, e4, e5, e5n  | Importar módulo = ler disco. Impede injetar config do DB |
| `_load_json_config` duplicado | 6 implementações diferentes | Dificulta trocar source de config                        |
| `print()` para progresso      | Todos os scripts            | Impede capturar progresso para WebSocket                 |
| I/O direto no filesystem      | Todos os scripts            | OK para Fase 0, abstrair em Fase 2                       |


#### Scripts por tamanho e risco


| Script               | KB   | Linhas | Entry point existente  | Risco                         |
| -------------------- | ---- | ------ | ---------------------- | ----------------------------- |
| `e6_render.py`       | 197  | ~3968  | `render_report()` ✓    | Alto — refatorar por ÚLTIMO   |
| `e5_analyze.py`      | 107  | ~2572  | `main()` ✓             | Alto — muitas configs         |
| `e5n_narrativas.py`  | 61   | ~1198  | `main()` ✓             | Médio                         |
| `e_reset.py`         | 55   | ~1314  | Orchestration complexo | Médio — postergar para 0D     |
| `e3_reconcile.py`    | 44   | ~1131  | `main()` ✓             | Médio — bom candidato inicial |
| `e4_categorize.py`   | 41   | ~1018  | `main()` ✓             | Médio — bom candidato inicial |
| `e7_review.py`       | 36   | ~900   | `main()` ✓             | Baixo                         |
| `e0_audit.py`        | 36   | ~900   | `main()` ✓             | Baixo                         |
| `e0_route.py`        | 31   | ~750   | `main()` ✓             | Baixo                         |
| `e2_extract.py`      | 10   | ~300   | `main()` ✓             | Baixo — E2 já é modular       |
| `e2/` (banks+common) | ~130 | ~3000  | Registry pattern ✓     | Baixo — já bem estruturado    |


---

#### Sub-fase 0A: Foundation Layer (Semana 1)

**Objetivo:** Criar as abstrações base sem tocar nos scripts existentes.


| #    | Tarefa                                                                  | Prioridade | Estimativa | Status   |
| ---- | ----------------------------------------------------------------------- | ---------- | ---------- | -------- |
| 0A.1 | Criar `pipeline/` package com `__init__.py` na raiz do projeto          | P0         | 1h         | ✅        |
| 0A.2 | Criar `pipeline/context.py` com classe `WorkspaceContext`               | P0         | 4h         | ✅        |
| 0A.3 | Criar `pipeline/config_loader.py` — loader unificado (disco ou dict)    | P0         | 4h         | ✅        |
| 0A.4 | Criar `pipeline/logging.py` — adapter que captura print + logging       | P1         | 3h         | ☐ Adiado |
| 0A.5 | Snapshot de golden files: salvar outputs atuais do E2→E6 para regressão | P0         | 2h         | ✅        |
| 0A.6 | Criar script `tests/test_regression.py` que compara outputs             | P0         | 3h         | ✅        |


`**WorkspaceContext`** — o conceito central:

```python
# pipeline/context.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass
class WorkspaceContext:
    """Fornece paths e configs para o pipeline. Injeta dependências em vez de
    ler do disco via __file__. Default = layout atual do projeto."""

    root: Path  # raiz do workspace (= PROJECT_DIR atual)

    # Paths derivados (calculados no __post_init__)
    config_dir: Path = field(init=False)
    data_dir: Path = field(init=False)
    processed_dir: Path = field(init=False)
    e2_dir: Path = field(init=False)
    e3_dir: Path = field(init=False)
    e4_dir: Path = field(init=False)
    e5_dir: Path = field(init=False)
    output_dir: Path = field(init=False)
    logs_dir: Path = field(init=False)

    # Config overrides (se None, carrega do disco via config_dir)
    config_overrides: Optional[dict] = None

    def __post_init__(self):
        self.config_dir = self.root / "config"
        self.data_dir = self.root / "data"
        self.processed_dir = self.root / "processed"
        self.e2_dir = self.processed_dir / "E2_extracts"
        self.e3_dir = self.processed_dir / "E3_reconciled"
        self.e4_dir = self.processed_dir / "E4_unified"
        self.e5_dir = self.processed_dir / "E5_analysis"
        self.output_dir = self.root / "output"
        self.logs_dir = self.root / "logs"

    def load_config(self, name: str) -> dict:
        """Carrega config do override (DB/dict) ou do disco."""
        if self.config_overrides and name in self.config_overrides:
            return self.config_overrides[name]
        path = self.config_dir / name
        if path.exists():
            import json
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    @classmethod
    def default(cls) -> "WorkspaceContext":
        """Contexto padrão: raiz do projeto atual (retrocompatível)."""
        project_dir = Path(__file__).resolve().parent.parent
        return cls(root=project_dir)

    @classmethod
    def for_tenant(cls, tenant_root: Path, config: dict) -> "WorkspaceContext":
        """Contexto para tenant web com config do banco de dados."""
        return cls(root=tenant_root, config_overrides=config)
```

**Por que isso é poderoso:**

- Scripts CLI: `ctx = WorkspaceContext.default()` → funciona igual a antes
- Web API: `ctx = WorkspaceContext.for_tenant(Path(f"storage/{workspace_id}"), db_config)` → multi-tenant
- Testes: `ctx = WorkspaceContext(root=tmp_dir, config_overrides={...})` → isolado

---

#### Sub-fase 0B: Wrap dos módulos menores (Semana 1-2)

**Objetivo:** Criar wrappers para E3 e E4 (os mais "funcionais" — input claro → output claro).


| #    | Tarefa                                                               | Prioridade | Estimativa | Status |
| ---- | -------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 0B.1 | Wrap `e3_reconcile.py`: `_init_config()` + `main(root_dir=None)`     | P0         | 4h         | ✅      |
| 0B.2 | Wrap `e4_categorize.py`: `_init_config()` + `main(root_dir=None)`    | P0         | 4h         | ✅      |
| 0B.3 | Wrap `e2_extract.py` + `e2/common.py`: `_init_config()` + `root_dir` | P0         | 3h         | ✅      |
| 0B.4 | Wrap `e7_review.py`: `_init_config()` + `main(root_dir=None)`        | P1         | 3h         | ✅      |
| 0B.5 | Criar `pipeline/stages/` — wrappers e2, e3, e4, e7                   | P0         | 2h         | ✅      |
| 0B.6 | Testes: 106 passed (77 originais + 29 novos), 2 skipped golden       | P0         | 2h         | ✅      |
| 0B.7 | Testes: `_init_config` com root_dir custom valida re-inicialização   | P0         | 2h         | ✅      |


**Pattern do wrapper — Opção B com `_init_config()` (Decidido)**

Cada script ganha uma função `_init_config(base_dir)` que (re)carrega todos os globals
de configuração. É chamada no module level com o default (retrocompat), e re-chamada
por `main(root_dir=...)` quando um root diferente é injetado.

**Passo 1 — Mudança cirúrgica no script (exemplo E3):**

```python
# scripts/e3_reconcile.py

_DEFAULT_BASE = Path(__file__).resolve().parent.parent

def _init_config(base_dir: Path):
    """(Re)carrega paths e configs a partir de um root_dir.
    Chamado no module level com default, e por main() com root injetado."""
    global _BASE_DIR, _CONFIG_DIR, PIPE_CONFIG, ACCOUNT_TYPE_EQUIVALENCES
    global _BANCO_CANONICAL_REVERSE
    _BASE_DIR = base_dir
    _CONFIG_DIR = base_dir / "config"
    PIPE_CONFIG = _load_json(_CONFIG_DIR / "pipeline.json")
    ACCOUNT_TYPE_EQUIVALENCES = _load_equivalences(_CONFIG_DIR / "family_members.json")
    _BANCO_CANONICAL_REVERSE = _load_banco_canonical_reverse()

# Module level: carrega defaults (retrocompat com import e CLI direto)
_init_config(_DEFAULT_BASE)

def main(root_dir: Path = None):
    if root_dir:
        _init_config(root_dir)
    # ... resto do main() 100% inalterado ...

if __name__ == "__main__":
    main()  # sem argumento = default = igual a antes
```

**Esforço real por script (refinado):**


| Script              | Globals a re-inicializar                    | Linhas extras | Complexidade |
| ------------------- | ------------------------------------------- | ------------- | ------------ |
| `e3_reconcile.py`   | ~5                                          | ~15           | Baixa        |
| `e4_categorize.py`  | ~10 (3 configs + 7 derivados)               | ~25           | Média        |
| `e2/common.py`      | ~8 (FAMILY, LOCALE, INST, PIPE + derivados) | ~20           | Média        |
| `e5_analyze.py`     | ~5 (paths + DOBs)                           | ~15           | Baixa        |
| `e5n_narrativas.py` | ~15 (FAMILY + 12 keys + FISCAL)             | ~35           | Média-alta   |
| `e6_render.py`      | ~3 (paths + template)                       | ~10           | Baixa        |


**Passo 2 — Wrapper fino no package pipeline:**

```python
# pipeline/stages/e3.py
from pipeline.context import WorkspaceContext

def run(ctx: WorkspaceContext) -> dict:
    """Executa E3 reconciliation com contexto injetado."""
    from scripts.e3_reconcile import main as e3_main
    e3_main(root_dir=ctx.root)
    files = list(ctx.e3_dir.glob("*-3_reconciled.json"))
    return {"success": True, "files_created": [f.name for f in files]}
```

**Vantagens:**

- Thread-safe (cada call re-inicializa seus globals com o root recebido)
- CLI funciona idêntico (`main()` sem argumento)
- Wrappers são triviais (3-5 linhas cada)
- Testável com `main(root_dir=Path("/tmp/test_workspace"))`
- Lógica interna dos scripts permanece 100% inalterada

**Regras da Fase 0:**

- Scripts permanecem em `scripts/` (sem reorganização de arquivos)
- `pipeline/` importa de `scripts/` (reorganização de pastas é Fase 2+)
- Config sempre vem de `root_dir/config/` (injeção via DB é Fase 3)
- `e_reset.py` roda scripts via subprocess hoje — orchestrator (0D) substitui por chamadas diretas

---

#### Sub-fase 0C: Wrap dos módulos grandes + Config injection (Semana 2-3)

**Objetivo:** E5, E5.N, E6 e E0s ganham wrappers. Config passa a ser injetável.


| #     | Tarefa                                                                 | Prioridade | Estimativa | Status |
| ----- | ---------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 0C.1  | Wrap `e5_analyze.py`: `_init_config()` + `main(root_dir=None)`         | P0         | 6h         | ✅      |
| 0C.2  | Wrap `e5n_narrativas.py`: `_init_config()` + `main(root_dir=None)`     | P0         | 4h         | ✅      |
| 0C.3  | Wrap `e6_render.py`: `_init_config()` + `render_report(root_dir=None)` | P0         | 6h         | ✅      |
| 0C.4  | Wrap `e0_audit.py`: `_init_config()` + `main(root_dir=None)`           | P1         | 3h         | ✅      |
| 0C.5  | Wrap `e0_route.py`: `_init_config()` + `main(root_dir=None)`           | P1         | 3h         | ✅      |
| 0C.6  | Wrap `e0_unlock.py`: `_init_config()` + `main(root_dir=None)`          | P1         | 2h         | ✅      |
| 0C.7  | Wrap `e15_consolidate.py`: `_init_config()` + `main(root_dir=None)`    | P1         | 2h         | ✅      |
| 0C.8  | Refatorar `pipeline_common.py`: `_init_config()` + limpa cache         | P0         | 3h         | ✅      |
| 0C.9  | `e2/common.py` já refatorado na 0B.3                                   | P0         | —          | ✅      |
| 0C.10 | Testes: 121 passed, 2 skipped. Wrappers e0/e5/e5n/e6/e15c criados      | P0         | 3h         | ✅      |


**O desafio do E5 (107KB):**

- Carrega **10 arquivos de config** diferentes (`goals.json`, `scoring.json`, `parametros_fiscais.json`, etc.)
- Muitos desses loads são em `_load_*()` functions chamadas no module level
- Solução: Mover loads para dentro de `main()`, guardar em dict, passar para subfunções
- Mudança cirúrgica: renomear `main()` para `_main_impl(ctx=None)`, criar novo `main()` que chama `_main_impl(WorkspaceContext.default())`

**O desafio do E6 (197KB):**

- Já tem `render_report()` como entry point limpo
- A maioria dos helpers não lê config — recebe dados como parâmetro
- Path de output e template são os principais acoplamentos
- Solução: `render_report(ctx=None)` — se None, usa default. Mudança de ~10 linhas.

---

#### Sub-fase 0D: Orchestrator + Package final (Semana 3-4)

**Objetivo:** Pipeline chamável end-to-end via Python. CLIs viram thin wrappers.


| #    | Tarefa                                                                                              | Prioridade | Estimativa | Status    |
| ---- | --------------------------------------------------------------------------------------------------- | ---------- | ---------- | --------- |
| 0D.1 | Criar `pipeline/orchestrator.py` — sequencia stages, `run_pipeline()`, `run_from()`, `run_stages()` | P0         | 8h         | ✅         |
| 0D.2 | Adaptar `e_reset.py` para usar orchestrator (manter CLI interface)                                  | P1         | 6h         | ☐ Adiado  |
| 0D.3 | Criar `pipeline/__init__.py` com API pública limpa (`v0.2.0`)                                       | P0         | 2h         | ✅         |
| 0D.4 | Criar `pyproject.toml` com dependências (setuptools, pytest config)                                 | P1         | 2h         | ✅         |
| 0D.5 | Consolidar `_load_json_config` — uma implementação, em `pipeline/config_loader.py`                  | P1         | 3h         | ✅ Parcial |
| 0D.6 | Testes: 136 passed (15 orchestrator + 121 wrappers), 2 skipped                                      | P0         | 4h         | ✅         |
| 0D.7 | Documentar API do package em docstrings                                                             | P2         | 2h         | ✅         |


**Orchestrator — interface alvo:**

```python
# pipeline/orchestrator.py
from pipeline.context import WorkspaceContext
from pipeline.stages import e0, e2, e3, e4, e5, e5n, e6, e7

DETERMINISTIC_STAGES = [
    ("E0-audit", e0.run_audit),
    ("E2-extratos", e2.run_extratos),
    ("E2-faturas", e2.run_faturas),
    ("E3", e3.run),
    ("E4", e4.run),
    ("E5", e5.run),
    ("E5.N", e5n.run),
    ("E6", e6.run),
    ("E7-crossval", e7.run_crossval),
]

LLM_STAGES = ["E1", "E1.5", "E2-llm", "E7-review"]

def run_pipeline(
    ctx: WorkspaceContext,
    from_stage: str = "E0",
    skip_llm: bool = True,      # Free tier = skip. Premium = False.
    on_progress=None,            # callback(stage, status, message)
) -> PipelineResult:
    """Executa pipeline completo ou parcial."""
    ...
```

**Como `e_reset.py` fica:**

```python
# scripts/e_reset.py (thin wrapper — mantém toda a interface CLI)
if __name__ == "__main__":
    args = parse_args()
    if args.new_orchestrator:
        # Nova path via pipeline package
        from pipeline.orchestrator import run_pipeline
        from pipeline.context import WorkspaceContext
        ctx = WorkspaceContext.default()
        run_pipeline(ctx, from_stage=args.from_stage, ...)
    else:
        # Path legado (código original) — safety net
        main(args)
```

---

#### Critérios de aceite da Fase 0 completa


| Critério            | Verificação                                                                                | Status                                   |
| ------------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------- |
| CLI funciona igual  | `python scripts/e_reset.py` → output idêntico ao pré-Fase-0                                | ✅                                        |
| Pipeline importável | `from pipeline import run_pipeline` funciona                                               | ✅                                        |
| Contexto injetável  | `run_pipeline(WorkspaceContext(root=Path("/tmp/test")))` funciona                          | ✅                                        |
| Config injetável    | `WorkspaceContext(root=..., config_overrides={"family_members.json": {...}})` funciona     | ✅                                        |
| Regressão zero      | Golden files do E2→E6 match byte-a-byte                                                    | ✅ (2 skipped — sem dados de teste no CI) |
| Testes passam       | `pytest tests/` → **136 passed, 2 skipped**                                                | ✅                                        |
| Scripts inalterados | Lógica interna dos scripts E2-E7 não muda (apenas `_init_config` + `root_dir` adicionados) | ✅                                        |


#### O que a Fase 0 NÃO faz (fica para fases posteriores)


| Escopo excluído                        | Por quê                                               | Fase destino       |
| -------------------------------------- | ----------------------------------------------------- | ------------------ |
| Pydantic models dos artefatos          | Útil mas não bloqueante. Scripts leem/escrevem dicts. | Fase 1-2           |
| Abstrair storage (S3/MinIO)            | Filesystem funciona até ter web                       | Fase 2             |
| Substituir print por logging           | Funciona sem isso para CLI                            | Fase 5 (WebSocket) |
| Refatorar lógica interna dos scripts   | Risco alto, valor baixo nesta fase                    | Futuro (gradual)   |
| Migrar E2 registry para auto-discovery | O sistema de BANK_MODULES funciona bem                | Futuro             |


---

### FASE 1 — Backend FastAPI + Auth + DB ✅ CONCLUÍDA

**Objetivo:** API server rodando com autenticação, servindo relatórios existentes.

**Resultado:** Backend FastAPI com auth JWT + SQLAlchemy async + SQLite. Frontend Next.js 16 + TypeScript + Tailwind CSS 4. 149 testes totais. Commit: `2c2ca4a`.

**Duração real:** ~1 dia (concentrado)

#### Tarefas


| #    | Tarefa                                                                          | Prioridade | Complexidade | Status                |
| ---- | ------------------------------------------------------------------------------- | ---------- | ------------ | --------------------- |
| 1.1  | Setup FastAPI project (`backend/app/`)                                          | P0         | Baixa        | ✅                     |
| 1.2  | Setup SQLAlchemy 2.0 (async) — sem Alembic (SQLite dev)                         | P0         | Média        | ✅ Parcial             |
| 1.3  | Modelo `User` (UUID pk, email, hashed_password, full_name, timestamps)          | P0         | Baixa        | ✅                     |
| 1.4  | Auth: register, login, JWT tokens (python-jose + bcrypt)                        | P0         | Média        | ✅                     |
| 1.5  | Middleware de autenticação (`get_current_user` dependency)                      | P0         | Baixa        | ✅                     |
| 1.6  | Modelo `Workspace` (UUID pk, name, owner_id FK)                                 | P0         | Baixa        | ✅                     |
| 1.7  | Modelo `Report` (UUID pk, workspace_id FK, title, period, html_path, file_size) | P0         | Baixa        | ✅                     |
| 1.8  | Endpoint `GET /api/reports` (lista relatórios do workspace)                     | P0         | Baixa        | ✅                     |
| 1.9  | Endpoint `GET /api/reports/{id}/html` (serve HTML content)                      | P0         | Baixa        | ✅                     |
| 1.10 | Seed: importar relatórios HTML existentes (`backend/seed_db.py`)                | P1         | Baixa        | ✅                     |
| 1.11 | CORS configurado para `http://localhost:3000`                                   | P0         | Baixa        | ✅                     |
| 1.12 | Script de setup dev (`docker-compose.dev.yml` com PostgreSQL)                   | P1         | Média        | ☐ Adiado F7           |
| 1.13 | Testes dos endpoints de auth + reports (13 tests passando)                      | P1         | Média        | ✅                     |
| 1.14 | Setup Next.js 16 + TypeScript + Tailwind CSS 4                                  | P0         | Baixa        | ✅                     |
| 1.15 | Páginas de login e registro (Next.js)                                           | P0         | Média        | ✅                     |
| 1.16 | Página de lista de relatórios com metadata                                      | P1         | Média        | ✅                     |
| 1.17 | Visualização de relatório HTML em iframe                                        | P1         | Baixa        | ✅                     |
| 1.18 | Auto-geração de types TS via `openapi-typescript`                               | P1         | Média        | ☐ Adiado → F2 (2D.11) |


#### Critério de aceite


| Critério                                                                                    | Status |
| ------------------------------------------------------------------------------------------- | ------ |
| `POST /api/auth/register` + `POST /api/auth/login` funcionam                                | ✅      |
| `GET /api/auth/me` retorna dados do usuário autenticado                                     | ✅      |
| Usuário autenticado vê lista de relatórios via browser                                      | ✅      |
| Relatório HTML é exibido corretamente na UI (iframe)                                        | ✅      |
| Pipeline CLI continua funcionando independentemente                                         | ✅      |
| 99 testes backend passando (auth, reports, models, storage, vault, documents, pipeline API) | ✅      |
| Frontend build TypeScript sem erros                                                         | ✅      |


#### Dependências instaladas

```
# Backend (backend/requirements.txt)
fastapi>=0.115
uvicorn>=0.30
sqlalchemy[asyncio]>=2.0    # async engine com aiosqlite
aiosqlite>=0.20              # driver async para SQLite
alembic>=1.13                # database migrations (Fase 2)
cryptography>=43.0           # Fernet vault encryption (Fase 2)
python-jose[cryptography]>=3.3
bcrypt>=4.0                  # direto, sem passlib (ver Nota 1)
python-multipart>=0.0.7
pydantic[email]>=2.0         # EmailStr validation
pydantic-settings>=2.0       # BaseSettings com env_prefix
greenlet>=3.0                # requerido por SQLAlchemy async

# Backend dev
pytest>=8.0
pytest-asyncio>=0.23
httpx>=0.27

# Frontend (frontend/package.json)
next@latest                  # Next.js 16 instalado
react@latest                 # React 19
react-dom@latest
typescript
@types/node, @types/react, @types/react-dom
tailwindcss + @tailwindcss/postcss + postcss
```

> **Nota 1 — bcrypt direto em vez de passlib:** A combinação `passlib[bcrypt]` com bcrypt 4.x causa
> `ValueError: password cannot be longer than 72 bytes` devido a mudanças de API no bcrypt.
> Solução: usar `bcrypt.hashpw()` e `bcrypt.checkpw()` diretamente em `backend/app/core/security.py`.

> **Nota 2 — Alembic introduzido (Fase 2):** Alembic configurado com async engine. Migration inicial cobre
> todas as tabelas (users, workspaces, reports, documents, password_vault, pipeline_runs, pipeline_stage_logs).
> Em dev, `init_db()` ainda usa `create_all()`. Alembic será usado em produção com PostgreSQL.

---

### Guia de Teste Local (Fases 0 + 1 + 2 backend)

#### Pré-requisitos

```bash
# Python 3.11+, Node.js 18+
python3 --version   # >= 3.11
node --version      # >= 18
npm --version       # >= 9
```

#### 1. Pipeline Python (Fase 0)

```bash
# Instalar dependências do pipeline
pip install -e ".[dev]"

# Rodar testes do pipeline (136 tests)
pytest tests/ -v

# Testar importação do package
python -c "from pipeline import run_pipeline, WorkspaceContext; print('OK')"

# Pipeline CLI continua funcionando normalmente
python scripts/e2_extract.py --extratos-only
python scripts/e3_reconcile.py
python scripts/e4_categorize.py
python scripts/e5_analyze.py
python scripts/e5n_narrativas.py
python scripts/e6_render.py
```

#### 2. Backend FastAPI (Fases 1 + 2)

```bash
cd backend

# Instalar dependências
pip install -r requirements.txt

# Inicializar banco de dados + importar relatórios existentes
python seed_db.py

# Rodar servidor (porta 8000)
uvicorn app.main:app --reload --port 8000

# Em outro terminal — testar auth:
# Registrar usuário
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@fin.app","password":"secret123","full_name":"Test User"}'

# Login
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@fin.app","password":"secret123"}'
# → retorna {"access_token": "eyJ...", "token_type": "bearer"}

# Listar relatórios (usar token do login)
curl -s http://localhost:8000/api/reports \
  -H "Authorization: Bearer <TOKEN>"

# Fase 2 — Upload de documentos
curl -s -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer <TOKEN>" \
  -F "files=@extrato_itau.csv"

# Fase 2 — Listar documentos
curl -s http://localhost:8000/api/documents \
  -H "Authorization: Bearer <TOKEN>"

# Fase 2 — Vault de senhas
curl -s -X POST http://localhost:8000/api/vault/passwords \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"label":"Itaú IRPF","password":"minhasenha"}'

# Fase 2 — Executar pipeline
curl -s -X POST http://localhost:8000/api/pipeline/run \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"skip_llm": true}'

# Fase 2 — Status do pipeline run
curl -s http://localhost:8000/api/pipeline/runs \
  -H "Authorization: Bearer <TOKEN>"

# Rodar testes backend (174 tests — Fases 1+2+3)
cd backend
pytest tests/ -v
```

#### 3. Frontend Next.js (Fase 1)

```bash
cd frontend

# Instalar dependências
npm install

# Rodar em modo dev (porta 3000)
npm run dev

# Abrir no browser: http://localhost:3000
# → Redireciona para /login
# → Registrar usuário ou usar admin@fin.app / admin123 (se seed_db.py foi executado)
# → Após login: lista de relatórios
# → Clicar em relatório: visualização em iframe

# Build de produção (verificar TypeScript)
npm run build
```

#### 4. Rodar tudo junto (desenvolvimento)

```bash
# Terminal 1 — Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev

# Terminal 3 — Testes
pytest tests/ -v          # Pipeline (136 tests)
cd backend && pytest tests/ -v  # Backend (174 tests)
```

> **Nota:** O frontend faz proxy de `/api/*` para `http://127.0.0.1:8000/api/*` via
> `next.config.ts` rewrites, então backend e frontend precisam rodar simultaneamente.

#### 5. Usuário seed para desenvolvimento

O script `backend/seed_db.py` cria:

- **Usuário:** `admin@fin.app` / `admin123`
- **Workspace:** "Workspace de Admin Fin"
- **Relatórios:** Importa todos os `relatorio_financeiro_*.html` de `output/`

---

### Estratégias e Decisões de Implementação

#### Fase 0 — Estratégia `_init_config()` + `root_dir`

Cada script ganhou:

1. `**_init_config(base_dir: Path)`** — função que (re)carrega todos os globals de configuração
  a partir de um diretório raiz. É chamada no module level com o default para manter
   retrocompatibilidade com `import` e CLI.
2. `**main(root_dir: Path = None)`** — quando `root_dir` é fornecido, chama `_init_config(root_dir)`
  antes de executar a lógica. Sem argumento = comportamento idêntico ao original.
3. **Wrappers finos em `pipeline/stages/`** — cada wrapper tem ~5 linhas:
  ```python
   def run(ctx: WorkspaceContext) -> dict:
       from scripts.e3_reconcile import main as e3_main
       e3_main(root_dir=ctx.root)
       return {"success": True, ...}
  ```

**Scripts wrappados (12 total):**
`e0_audit`, `e0_route`, `e0_unlock`, `e15_consolidate`, `e2_extract`, `e2/common`,
`e3_reconcile`, `e4_categorize`, `e5_analyze`, `e5n_narrativas`, `e6_render`, `e7_review`,
`pipeline_common`

#### Fase 0D — Orchestrator

`pipeline/orchestrator.py` define:

- `DETERMINISTIC_ORDER`: sequência de etapas sem LLM
- `FULL_ORDER`: todas as etapas (determinísticas + LLM)
- `FROM_MAP`: mapeamento para `--from EX` (recomeçar a partir de uma etapa)
- `run_pipeline(ctx, skip_llm=True)`: executa pipeline completo
- `run_from(ctx, stage, skip_llm=True)`: executa a partir de uma etapa
- `run_stages(ctx, stages)`: executa etapas específicas

Dataclasses de resultado: `StageResult` e `PipelineResult` com `.summary`.

#### Fase 1 — Arquitetura do Backend

```
backend/
├── app/
│   ├── main.py              # FastAPI app, lifespan (create_all), CORS
│   ├── api/
│   │   ├── auth.py          # POST register, POST login, GET me
│   │   └── reports.py       # GET list, GET detail, GET html
│   ├── core/
│   │   ├── config.py        # Settings (SECRET_KEY, DATABASE_URL, JWT)
│   │   ├── database.py      # async engine + sessionmaker + get_db
│   │   └── security.py      # hash_password, verify_password, create/decode JWT
│   ├── models/
│   │   └── base.py          # User, Workspace, Report (SQLAlchemy)
│   ├── schemas/
│   │   └── auth.py          # RegisterRequest, LoginRequest, TokenResponse, UserResponse
│   └── services/
│       └── seed.py          # ensure_seed_user, seed_existing_reports
├── tests/
│   ├── conftest.py          # Fixtures: setup_db, client, auth_client
│   ├── test_auth.py         # 7 tests (register, login, me, duplicates, errors)
│   └── test_reports.py      # 6 tests (list, detail, html, auth, not-found)
├── requirements.txt
└── seed_db.py               # CLI para inicializar DB com dados de teste
```

**Decisões técnicas do backend:**

- **Async throughout:** `AsyncSession`, `async def` em todos os endpoints e services
- **UUID como PK:** Todos os models usam `UUID` (preparação para multi-tenant)
- **bcrypt direto:** Sem passlib wrapper (evita bug com bcrypt 4.x)
- `**await db.flush()`:** Necessário antes de criar `Workspace` referenciando `user.id` (SQLAlchemy async não auto-flush)
- **Lifespan event:** `create_all()` no startup (substitui Alembic em dev)
- **Report.html_content:** Relatório HTML armazenado no banco como text (simplifica serving)

#### Fase 1 — Arquitetura do Frontend

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx       # Root layout (Inter font, Tailwind, metadata)
│   │   ├── page.tsx         # Root: check token → redirect /reports ou /login
│   │   ├── login/page.tsx   # Form email/password, error handling
│   │   ├── register/page.tsx # Form name/email/password
│   │   └── reports/
│   │       ├── page.tsx     # Lista de relatórios com metadata
│   │       └── [id]/page.tsx # Viewer: iframe com HTML do relatório
│   ├── lib/
│   │   └── api.ts           # apiFetch, JWT storage, register/login/getMe/listReports
│   └── globals.css          # Tailwind imports
├── next.config.ts           # API rewrites → http://127.0.0.1:8000
├── postcss.config.mjs       # @tailwindcss/postcss
├── tsconfig.json
└── package.json
```

**Decisões técnicas do frontend:**

- **Next.js 16 App Router:** Componentes `"use client"` para interatividade
- **API proxy:** `next.config.ts` rewrite de `/api/:path`* para backend (evita CORS em dev)
- **JWT no localStorage:** `getToken()`, `setToken()`, `clearToken()` em `lib/api.ts`
- **Relatório em iframe:** `srcdoc` com HTML completo do backend (preserva Chart.js, CSS inline)
- **Sem shadcn/ui ainda:** Tailwind puro para MVP. shadcn/ui planejado para Fase 6

#### Problemas resolvidos durante a implementação


| Problema                                                    | Causa raiz                                 | Solução                                        |
| ----------------------------------------------------------- | ------------------------------------------ | ---------------------------------------------- |
| `passlib` + `bcrypt` 4.x: `ValueError: password > 72 bytes` | passlib não atualizado para bcrypt 4.x API | Usar `bcrypt.hashpw()`/`checkpw()` diretamente |
| `IntegrityError: owner_id NULL` ao criar Workspace          | SQLAlchemy async não faz auto-flush        | `await db.flush()` após `db.add(user)`         |
| Pydantic rejeita `admin@fin.local`                          | `EmailStr` valida domínio real             | Usar `admin@fin.app`                           |
| `greenlet` not found                                        | SQLAlchemy async requer greenlet           | `pip install greenlet>=3.0`                    |
| `email-validator` not found                                 | `pydantic[email]` não instalado            | `pip install "pydantic[email]"`                |
| Next.js build: `CommonJs vs EcmaScript Modules`             | `"type": "commonjs"` em package.json       | Remover `"type": "commonjs"`                   |
| `_config_cache` NameError em pipeline_common                | Variável referenciada antes de declarar    | Mover declaração antes de `_init_config()`     |


---

### FASE 2 — Upload de Arquivos + Pipeline Trigger ✅ CONCLUÍDA

**Objetivo:** Usuário faz upload de documentos via browser. Documentos são automaticamente desbloqueados (vault de senhas) e classificados (E0-route). Pipeline determinístico roda via API e gera relatório acessível na UI.

**Resultado:** 4 sub-fases (2A-2D) concluídas. Upload batch, vault de senhas, E0 processing, pipeline execution com tracking, frontend completo com drag-and-drop, progress polling e report viewer.

#### Decisões tomadas para esta fase


| Decisão                    | Escolha                                    | Rationale                                                                     |
| -------------------------- | ------------------------------------------ | ----------------------------------------------------------------------------- |
| Execução do pipeline       | Pseudo-async (background thread + polling) | Sem task queue (Fase 5), mas sem bloquear HTTP request                        |
| Escopo do pipeline         | Etapas determinísticas (E0→E7-crossval)    | LLM é Fase 4. Se JSONs de E1/E1.5 existirem, E6 os incorpora                  |
| Senhas de PDF              | Vault de senhas por workspace              | Testadas automaticamente no upload. User gerencia via UI                      |
| Classificação de docs      | E0-route automático no upload              | Sem intervenção manual. Classifica banco, tipo e período                      |
| File storage               | Filesystem local por tenant                | S3/MinIO fica para Fase 7. Suficiente para MVP                                |
| Dados de E1/E1.5           | Upload de JSONs pré-existentes             | User pode subir baseline_patrimonial e members junto com docs bancários       |
| Trigger do pipeline        | Docs novos por default, opção reprocessar  | Evita reprocessamento desnecessário, mas dá controle ao user                  |
| DB session em threads      | Sync `SessionLocal` paralela à async       | Pipeline é código sync. Async session requer event loop. Padrão FastAPI       |
| Config em tenant workspace | `config_dir` override em `for_tenant()`    | Fase 2 aponta para config/ global. Fase 3 injeta via `config_overrides` do DB |
| Localização do storage     | `Settings.STORAGE_ROOT` (env var)          | Default: `fin-current/storage/`. Configurável para produção. No `.gitignore`  |


#### Diagrama do fluxo

```
User drag-and-drop (batch de arquivos)
    ↓
POST /api/documents/upload
    ↓
┌─── Para cada arquivo ────────────────────────────────┐
│ Validação (tipo, tamanho, integridade)               │
│    ↓                                                 │
│ Se PDF protegido → tenta vault passwords → E0-unlock │
│    ↓ (sucesso)              ↓ (falha)                │
│ E0-route (classifica)    status: needs_password       │
│    ↓                                                 │
│ status: ready                                         │
└──────────────────────────────────────────────────────┘
    ↓
Documentos aparecem na lista com status e classificação
    ↓
User clica "Gerar Relatório"
    ↓
POST /api/pipeline/run → retorna run_id imediatamente
    ↓
Pipeline roda em background thread:
  E0-audit → E2 → E3 → E4 → E5 → E5.N → E6 → E7-crossval
  (atualiza PipelineStageLog a cada etapa)
    ↓
Frontend faz polling GET /api/pipeline/runs/{id}
  → mostra progresso stage-by-stage
    ↓
Pipeline completo → Report criado → user visualiza relatório
```

---

#### Sub-fase 2A: Storage Layer + Models (Semana 1) ✅ CONCLUÍDA

**Objetivo:** Infraestrutura de storage por tenant, modelos de banco e vault de senhas.


| #    | Tarefa                                                                                                                                                 | Prioridade | Estimativa | Status |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | ---------- | ------ |
| 2A.1 | Modelo `Document` + migration (workspace_id, original_name, stored_path, doc_type, bank_code, period, status, classification_meta JSON, uploaded_at)   | P0         | 3h         | ✅      |
| 2A.2 | Modelo `PasswordVault` (workspace_id, label, encrypted_password via Fernet, created_at) + migration                                                    | P0         | 3h         | ✅      |
| 2A.3 | Modelo `PipelineRun` + `PipelineStageLog` + migration                                                                                                  | P0         | 4h         | ✅      |
| 2A.4 | Estrutura de storage por tenant com árvore completa (ver detalhe abaixo). Criação automática no primeiro upload. Path base via `Settings.STORAGE_ROOT` | P0         | 3h         | ✅      |
| 2A.5 | Service `StorageService` — CRUD de arquivos no tenant, sanitização de filenames, prevenção de path traversal                                           | P0         | 4h         | ✅      |
| 2A.6 | CRUD API: `POST/GET/DELETE /api/vault/passwords` (senhas criptografadas at-rest com Fernet)                                                            | P0         | 3h         | ✅      |


**Checkpoint 2A:** ✅ Modelos criados, Alembic migration rodando, storage por tenant funcional, vault API respondendo. 189 testes green.

**Árvore de storage por tenant:**

```
storage/                              # Settings.STORAGE_ROOT (default: raiz do monorepo)
└── {workspace_id}/                   # UUID do workspace
    ├── inbox/                        # Upload landing zone
    ├── data/
    │   ├── financial_statements/     # Extratos e faturas (destino E0-route)
    │   ├── income_tax_br/            # IRPF
    │   └── ...                       # Outras subpastas conforme E0-route
    ├── processed/
    │   ├── E2_extracts/              # Saída E2 + baseline E1.5 se uploaded
    │   ├── E3_reconciled/
    │   ├── E4_unified/
    │   ├── E5_analysis/
    │   └── E7_review/
    ├── output/                       # Relatório HTML (E6)
    ├── members/                      # JSONs de E1 se uploaded
    └── logs/
```

> **Nota:** `config/` NÃO é copiado para o tenant. O `WorkspaceContext.for_tenant()` recebe `config_dir` apontando para o `config/` global do projeto. Na Fase 3, `config_overrides` do banco substituirá isso.

**Modelo `Document` — status machine:**

```python
class DocumentStatus(str, Enum):
    uploaded = "uploaded"            # Arquivo recebido, aguardando processamento
    unlocking = "unlocking"          # Tentando desbloquear com vault
    classifying = "classifying"      # E0-route classificando
    ready = "ready"                  # Classificado, pronto para pipeline
    needs_password = "needs_password"  # PDF protegido, nenhuma senha do vault funcionou
    processing = "processing"        # Pipeline em execução usando este documento
    processed = "processed"          # Pipeline completou com este documento
    error = "error"                  # Erro em qualquer etapa

class DocumentType(str, Enum):
    bank_statement = "bank_statement"
    credit_card_bill = "credit_card_bill"
    investment_report = "investment_report"
    irpf = "irpf"
    e1_members_json = "e1_members_json"         # JSON de E1 (upload manual)
    e1_5_baseline_json = "e1_5_baseline_json"    # JSON de E1.5 (upload manual)
    other = "other"
```

---

#### Sub-fase 2B: Upload + E0 Processing (Semana 1-2) ✅ CONCLUÍDA

**Objetivo:** Upload funcional com desbloqueio automático via vault e classificação via E0-route.


| #     | Tarefa                                                                                                                                          | Prioridade | Estimativa | Status |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 2B.1  | Endpoint `POST /api/documents/upload` (multipart, batch até 20 arquivos simultâneos)                                                            | P0         | 4h         | ✅      |
| 2B.2  | Validação no upload: tipos aceitos (PDF, XLSX, XLS, CSV, JPG, PNG, JSON), tamanho máx 50MB/arquivo, detecção de arquivo corrompido/vazio        | P0         | 4h         | ✅      |
| 2B.3  | Suporte a upload de JSONs de E1/E1.5 — classificação automática como `e1_members_json` ou `e1_5_baseline_json` baseado na estrutura do JSON     | P0         | 3h         | ✅      |
| 2B.4  | Integração E0-unlock: ao receber PDF, tenta desbloquear com todas as senhas do vault. Se nenhuma funciona → status `needs_password`             | P0         | 4h         | ✅      |
| 2B.5  | Integração E0-route: classifica documento automaticamente (banco, tipo, período). Resultado salvo em `Document.classification_meta`             | P0         | 6h         | ✅      |
| 2B.6  | Status tracking por documento: transições atômicas `uploaded → unlocking → classifying → ready` (ou `needs_password` / `error`)                 | P0         | 3h         | ✅      |
| 2B.7  | Endpoint `GET /api/documents` (lista por workspace, filtros por status, paginação)                                                              | P0         | 3h         | ✅      |
| 2B.8  | Endpoint `DELETE /api/documents/{id}` (remove arquivo do storage + registro do banco)                                                           | P1         | 2h         | ✅      |
| 2B.9  | Segurança: sanitização de filename, prevenção de path traversal, validação de content-type vs extensão, limite de storage por workspace (500MB) | P0         | 4h         | ✅      |
| 2B.10 | Re-tentativa de unlock: endpoint `POST /api/documents/retry-unlock` testa senhas novas do vault nos docs com `needs_password`                   | P0         | 3h         | ✅      |


**Checkpoint 2B:** ✅ Upload via API funciona. Documentos são desbloqueados e classificados automaticamente. Lista de documentos mostra status correto. 222 testes green.

**Adaptação do E0-route para web:**

No CLI, E0-route lê de `inbox/` e move para `data/`. Na web:

1. Arquivo vai para `storage/{workspace_id}/inbox/` (pelo upload)
2. E0-route classifica e copia para subpasta correta em `storage/{workspace_id}/data/` (ex: `data/financial_statements/`)
3. Nome canônico (renomeado) é salvo em `Document.stored_path`
4. Metadados de classificação (banco, tipo, período) salvos em `Document.classification_meta` (JSON)

---

#### Sub-fase 2C: Pipeline Execution (Semana 2-3) ✅ CONCLUÍDA

**Objetivo:** Pipeline determinístico roda via API em background thread com tracking de progresso por etapa.


| #     | Tarefa                                                                                                                                       | Prioridade | Estimativa | Status      |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ----------- |
| 2C.1  | Adaptar orchestrator (Fase 0D) para receber tenant root e operar sobre `storage/{workspace_id}/`                                             | P0         | 6h         | ✅           |
| 2C.2  | Endpoint `POST /api/pipeline/run` — valida docs ready, cria `PipelineRun`, inicia background thread, retorna `run_id` imediatamente          | P0         | 6h         | ✅           |
| 2C.3  | Suporte a `from_stage` no request (E0-E7) para re-run parcial + `skip_llm` e `stop_on_error` flags                                           | P0         | 3h         | ✅           |
| 2C.4  | Se JSONs de E1/E1.5 foram uploaded, copiar para posição correta no workspace antes de E2 (baseline em `E2_extracts/`, members em `members/`) | P0         | 3h         | ☐ (Fase 2D) |
| 2C.5  | Stage tracking: pipeline atualiza `PipelineStageLog` a cada etapa com status (running/completed/failed/skipped), timestamps, output_summary  | P0         | 4h         | ✅           |
| 2C.6  | Endpoint `GET /api/pipeline/runs/{id}` — status geral + array de stages com progresso detalhado                                              | P0         | 3h         | ✅           |
| 2C.7  | Endpoint `GET /api/pipeline/runs` — lista de execuções por workspace (mais recentes primeiro)                                                | P0         | 3h         | ✅           |
| 2C.8  | Error handling: se etapa falha, salvar resultados parciais, marcar `PipelineRun` como `failed` com stage de falha                            | P0         | 4h         | ✅           |
| 2C.9  | Endpoint `POST /api/pipeline/runs/{id}/cancel` — cancelamento cooperativo via threading.Event                                                | P1         | 4h         | ✅           |
| 2C.10 | Report linkage: ao final de E6, criar registro `Report` vinculado ao `PipelineRun` com path do HTML                                          | P0         | 2h         | ✅           |
| 2C.11 | Limite de concorrência: máximo 1 pipeline run ativo por workspace. Rejeitar com `409 Conflict` se já houver run em andamento                 | P1         | 2h         | ✅           |


**Checkpoint 2C:** ✅ `POST /api/pipeline/run` retorna `run_id` (202 Accepted). Polling mostra progresso stage-by-stage. Cancel funcional. 235 testes green (99 backend + 136 pipeline).

**Background thread — implementação (ver `backend/app/services/pipeline_service.py`):**

```python
# Sync engine em database.py — usado APENAS por background threads.
sync_engine = create_engine(settings.sync_database_url)
SyncSessionLocal = sessionmaker(bind=sync_engine)

# Pipeline service lança daemon thread com cancel cooperativo:
_active_runs: dict[str, threading.Event] = {}

def start_pipeline_run(run_id, ws_id, stages, *, skip_llm=True, stop_on_error=True):
    cancel_event = threading.Event()
    _active_runs[run_id] = cancel_event
    t = threading.Thread(target=_run_pipeline_thread, args=(...), daemon=True)
    t.start()

def _run_pipeline_thread(run_id, ws_id, tenant_root, config_dir, stages, ...):
    ctx = WorkspaceContext.for_tenant(tenant_root, config_dir=config_dir)
    for stage_name in stages:
        if cancel_event.is_set(): break   # Cancelamento cooperativo
        # Cria PipelineStageLog(status=running)
        result = _run_stage(ctx, stage_name)
        # Atualiza StageLog(status=completed/failed, duration_ms, errors)
    # Após E6: _create_report_from_output()
```

**Decisões de design:**

- **Sync session:** Pipeline é código 100% síncrono. `asyncio.run()` dentro da thread adicionaria complexidade sem benefício.
- `**config_dir` override:** Aponta para `config/` global do projeto. Na Fase 3, `materialize_config()` gera tenant config antes de cada run (✅ implementado).
- `**STORAGE_ROOT`:** Configurável via env var `FIN_STORAGE_ROOT`. Default: `fin-current/storage/`.
- **Cancel cooperativo:** `threading.Event` verificado entre stages. O frontend pode chamar `POST /api/pipeline/runs/{id}/cancel`.
- **Concorrência:** Máximo 1 run ativo por workspace (409 Conflict). Registry `_active_runs` com lock.

**Limitações conhecidas:**

- Background threads não sobrevivem a restart do servidor → Fase 5 (Celery/ARQ + Redis) resolve
- ~~Config é global (todos os tenants usam a mesma)~~ → ✅ Resolvido: `materialize_config()` injeta config do DB por tenant (Fase 3C)

---

#### Sub-fase 2D: Frontend + Integração (Semana 3-4) ✅ CONCLUÍDA

**Objetivo:** UI funcional de upload, documentos, vault, execução de pipeline e visualização de relatório.


| #     | Tarefa                                                                                                             | Prioridade | Estimativa | Status                       |
| ----- | ------------------------------------------------------------------------------------------------------------------ | ---------- | ---------- | ---------------------------- |
| 2D.1  | Página de upload com drag-and-drop (batch de múltiplos arquivos, progress bar de upload individual)                | P0         | 6h         | ✅                            |
| 2D.2  | Lista de documentos: tabela com nome, tipo detectado, banco, período, status (badge colorido), ação delete         | P0         | 4h         | ✅                            |
| 2D.3  | Tela de vault de senhas: adicionar/remover senhas + botão "Tentar desbloquear novamente" nos docs `needs_password` | P0         | 4h         | ✅                            |
| 2D.4  | Botão "Gerar Relatório" com opções: "Processar novos documentos" (default) / "Reprocessar tudo"                    | P0         | 3h         | ✅                            |
| 2D.5  | Tela de progresso do pipeline: polling a cada 2s, barra com etapas (E0→E7), etapa atual destacada, tempo decorrido | P0         | 6h         | ✅                            |
| 2D.6  | Estados de erro: etapa que falhou em vermelho, mensagem de erro expandível, botão "Tentar novamente"               | P0         | 4h         | ✅                            |
| 2D.7  | Pós-pipeline: redirecionamento automático para visualização do relatório (reutiliza viewer da Fase 1)              | P0         | 2h         | ✅                            |
| 2D.8  | Feedback visual: ícone por tipo de documento (PDF/CSV/XLSX), indicador de banco detectado, tooltip com detalhes    | P1         | 3h         | ✅                            |
| 2D.9  | Testes de integração E2E: upload batch → classify → pipeline → relatório visível na UI                             | P0         | 6h         | ☐                            |
| 2D.10 | Testes de cenários de erro: PDF corrompido, senha errada, pipeline parcial, isolamento entre workspaces            | P0         | 4h         | ☐                            |
| 2D.11 | Auto-geração de types TS via `openapi-typescript` (adiado da Fase 1, task 1.18)                                    | P1         | 3h         | ✅ (manual, matching schemas) |


**Checkpoint 2D:** Fluxo completo via browser: upload → classificação automática → gerar relatório → visualizar. Erros tratados com UX clara.

> **Nota:** Sub-fase 2D e Sub-fase 3D (frontend config UI) podem ser implementadas em sequência ou em paralelo, já que ambas dependem do mesmo scaffold Next.js. Recomendação: implementar 2D primeiro (fluxo core), depois 3D (config avançada).

---

#### Critérios de aceite da Fase 2 completa


| Critério                 | Verificação                                                                                                    |
| ------------------------ | -------------------------------------------------------------------------------------------------------------- |
| Upload funcional         | Drag-and-drop de batch de documentos via browser. Arquivos salvos no storage do tenant                         |
| Unlock automático        | PDFs protegidos são desbloqueados usando senhas do vault. PDFs sem senha ficam como `needs_password`           |
| Classificação automática | E0-route classifica banco, tipo e período de cada documento sem intervenção manual                             |
| Pipeline via API         | `POST /api/pipeline/run` executa etapas determinísticas (E0-audit → E7-crossval) e gera relatório HTML         |
| Dados de E1/E1.5         | Se JSONs de E1/E1.5 foram uploaded, E6 incorpora esses dados no relatório. Se não, relatório sai sem eles      |
| Progresso visível        | Frontend mostra progresso stage-by-stage via polling (2s) durante execução do pipeline                         |
| Erros tratados           | Falhas por etapa são reportadas com mensagem clara. Pipeline parcial preserva resultados das etapas anteriores |
| Retry funcional          | Usuário pode re-executar pipeline desde etapa que falhou ou desde o início                                     |
| Multi-tenant             | Workspace A não vê documentos/relatórios de workspace B (teste explícito de isolamento)                        |
| CLI inalterado           | `python scripts/e_reset.py` continua funcionando independentemente da web                                      |
| Regressão zero           | Relatório gerado via web é idêntico ao gerado via CLI com mesmos inputs                                        |


#### O que a Fase 2 NÃO faz (fica para fases posteriores)


| Escopo excluído                              | Por quê                                   | Fase destino |
| -------------------------------------------- | ----------------------------------------- | ------------ |
| Task queue (Celery/Redis)                    | Background thread suficiente para dogfood | Fase 5       |
| WebSocket para progresso                     | Polling a cada 2s funciona adequadamente  | Fase 5       |
| LLM automático (E1, E1.5, E2-llm, E7-review) | Requer infra de LLM service               | Fase 4       |
| Config de membros/categorias via UI          | Requer CRUD completo de config            | Fase 3       |
| S3/MinIO para storage                        | Filesystem local suficiente para MVP      | Fase 7       |
| Preview de documentos (PDF viewer na UI)     | Nice-to-have, não bloqueante              | Fase 6       |
| Notificações (email/push)                    | Polling resolve para dogfood              | Fase 6       |
| Cleanup/retention automático de storage      | Gestão manual suficiente para dogfood     | Fase 7       |


#### Dependências das Fases 2 e 3 — instaladas ✅

```
# Backend — Fase 2 (adicionadas em backend/requirements.txt)
cryptography>=43.0        # Fernet para vault de senhas + CPF encryption
alembic>=1.13             # Database migrations

# Backend — Fase 3 (adicionada)
pyyaml>=6.0               # Parsing de report_layout.yaml para JSON na API e materialização

# Backend — já instaladas (Fase 1) e reutilizadas
python-multipart>=0.0.7   # Upload multipart
sqlalchemy[asyncio]>=2.0   # Async endpoints (+ sync engine para background threads)
aiosqlite>=0.20

# Frontend — pendente (Fase 2D/3D)
openapi-typescript        # (npm, na Fase 2D.11 — frontend)

# Pipeline — precisam estar acessíveis no ambiente do backend
pip install -e ".[dev]"    # Instala pipeline package + dependências (pikepdf, etc.)
```

> **Nota:** O backend importa de `pipeline.stages.`*, `pipeline.context` e `pipeline.orchestrator`. O pipeline package deve estar instalado no mesmo ambiente Python que o backend (`pip install -e ".[dev]"` na raiz do monorepo).

#### Configurações de ambiente (`backend/app/core/config.py`) — implementado ✅ (Fase 2)

```python
class Settings(BaseSettings):
    # Auth (Fase 1)
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    ALGORITHM: str = "HS256"
    DATABASE_URL: str = "sqlite+aiosqlite:///./fin.db"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Fase 2
    STORAGE_ROOT: Path = _PROJECT_ROOT / "storage"       # FIN_STORAGE_ROOT env var
    PIPELINE_ROOT: Path = _PROJECT_ROOT                   # Para localizar config/
    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_STORAGE_PER_WORKSPACE_MB: int = 500
    MAX_UPLOAD_BATCH_SIZE: int = 20
    FERNET_KEY: str = ""  # FIN_FERNET_KEY env var. Gerar via: Fernet.generate_key()

    model_config = {"env_prefix": "FIN_", "env_file": ".env"}

    @property
    def sync_database_url(self) -> str:
        return self.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "")
```

---

### FASE 3 — Configuração via UI ✅ CONCLUÍDA

**Objetivo:** As 5 configurações principais (`family_members`, `categorization`, `pipeline`, `institutions`, `report_layout`) passam a ser editáveis por workspace via UI. Config do DB é materializada em disco antes de cada pipeline run. Import/export de JSON permite migração do workflow CLI.

**Resultado:** 4 sub-fases (3A-3D) concluídas. 18 endpoints Config API. 5 configs editáveis via UI (6 tabs). Materialização integrada no pipeline trigger. Import/export JSON. 75+ testes backend.

#### Decisões tomadas para esta fase


| Decisão                      | Escolha                                                                | Rationale                                                                                                              |
| ---------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Configs em escopo            | 5 arquivos: members, categories, pipeline, institutions, report_layout | Core + layout = controle completo. Templates HTML e schemas ficam estáticos                                            |
| Injeção de config            | Seletiva: só configs editados no DB sobrescrevem                       | Configs não editados continuam lendo do disco (fallback global)                                                        |
| Estratégia de materialização | `materialize_config()` antes de cada pipeline run                      | Copia config/ global → tenant, sobrescreve com DB. Scripts lêem do disco como antes — zero mudança em `_init_config()` |
| Import/export                | Ambos: upload JSON → DB, download DB → JSON                            | Facilita migração do CLI e backup de configuração                                                                      |
| Validação                    | Pydantic schemas com regras de negócio + tipos                         | Rejeita save inválido com 422 + erros detalhados                                                                       |
| Seed/defaults                | Sem seed no DB. GET retorna defaults do disco se DB vazio              | User começa com config global. Só vai para DB quando edita                                                             |


#### Configs em escopo — mapeamento


| Config file           | Modelo no DB                   | Tipo de storage       | Editável via                         |
| --------------------- | ------------------------------ | --------------------- | ------------------------------------ |
| `family_members.json` | `FamilyMember` + `BankAccount` | Modelos normalizados  | Form estruturado (nome, CPF, contas) |
| `categorization.json` | `Category` + `CategoryKeyword` | Modelos normalizados  | Form com keywords editáveis, reorder |
| `pipeline.json`       | `PipelineConfig`               | JSON blob             | Form com campos agrupados por seção  |
| `institutions.json`   | `InstitutionConfig`            | JSON blob             | JSON editor (estrutura complexa)     |
| `report_layout.yaml`  | `ReportLayout`                 | JSON blob (YAML→JSON) | Toggle seções + reordenar            |


#### Diagrama: materialização de config

```
User edita config via UI
    ↓
POST /api/config/members (ou categories, pipeline, etc.)
    ↓
Validação Pydantic → salva no DB
    ↓ (quando user clica "Gerar Relatório")
POST /api/pipeline/run
    ↓
materialize_config(workspace_id):
  1. Copia config/ global → storage/{workspace_id}/config/
  2. Para cada config editado no DB:
     → Serializa DB → dict (formato original do JSON)
     → Sobrescreve arquivo no tenant config/
  3. Configs não editados = cópia do global (unchanged)
    ↓
Pipeline roda normalmente:
  _init_config(root_dir) lê de storage/{workspace_id}/config/
  → Sem nenhuma mudança nos scripts ou no _init_config()
```

> **Por que materializar em disco em vez de usar `config_overrides`?** Os scripts usam `_init_config(base_dir)` que lê de `base_dir / "config"` diretamente — não usam `ctx.load_config()`. Materializar evita modificar `_init_config()` em 12+ scripts novamente. Custo: ~100KB de I/O por run (negligível).

---

#### Sub-fase 3A: Models + Pydantic Schemas (Semana 1) ✅ CONCLUÍDA

**Objetivo:** Modelos de banco e schemas de validação para as 5 configurações.


| #    | Tarefa                                                                                                                                    | Prioridade | Estimativa | Status |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 3A.1 | Pydantic schemas de validação para cada config: `FamilyMemberSchema`, `BankAccountSchema`, `CategorySchema`, `PipelineConfigSchema`, etc. | P0         | 4h         | ✅      |
| 3A.2 | Modelo `FamilyMember` + migration (workspace_id, name, cpf_encrypted, birth_date, role, order)                                            | P0         | 3h         | ✅      |
| 3A.3 | Modelo `BankAccount` + migration (member_id FK, institution_code, account_type, agency, account_number)                                   | P0         | 2h         | ✅      |
| 3A.4 | Modelo `Category` + `CategoryKeyword` + migration (workspace_id, code, name, category_type, monthly_cap, keywords[], order)               | P0         | 3h         | ✅      |
| 3A.5 | Modelo `InstitutionConfig` + migration (workspace_id, config_json — JSON blob com patterns por banco)                                     | P1         | 2h         | ✅      |
| 3A.6 | Modelo `PipelineConfig` + migration (workspace_id, config_json — tolerances, thresholds, formatting)                                      | P1         | 2h         | ✅      |
| 3A.7 | Modelo `ReportLayout` + migration (workspace_id, config_json — YAML convertido para JSON)                                                 | P2         | 2h         | ✅      |


**Checkpoint 3A:** ✅ 7 modelos criados. Alembic migration `da5a6af13e3e` gera 7 tabelas (family_members, bank_accounts, categories, category_keywords, pipeline_configs, institution_configs, report_layouts). 17 Pydantic schemas com validação de CPF, roles, category types, bounds. 30 testes unitários green.

**Design dos modelos — normalizado vs JSON blob:**

Configs com entidades discretas (membros, categorias) usam modelos normalizados — permitem queries, foreign keys, ordering. Configs com estrutura profunda e variável (pipeline params, institutions patterns, report layout) usam JSON blob — mais flexível, sem necessidade de queries internas.

---

#### Sub-fase 3B: CRUD APIs + Import/Export (Semana 1-2) ✅ CONCLUÍDA

**Objetivo:** APIs REST completas para as 5 configurações, com fallback para defaults e import/export JSON.


| #     | Tarefa                                                                                                                | Prioridade | Estimativa | Status |
| ----- | --------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 3B.1  | CRUD API: `GET/POST/PUT/DELETE /api/config/members` (list, create, update, delete. CPF criptografado at-rest)         | P0         | 4h         | ✅      |
| 3B.2  | CRUD API: `GET/POST/PUT/DELETE /api/config/members/{id}/accounts` (nested under member)                               | P0         | 3h         | ✅      |
| 3B.3  | CRUD API: `GET/POST/PUT/DELETE /api/config/categories` (com keywords nested. Suporte a reordenação via campo `order`) | P0         | 4h         | ✅      |
| 3B.4  | CRUD API: `GET/PUT /api/config/pipeline` (single config por workspace, update parcial via JSON merge)                 | P1         | 2h         | ✅      |
| 3B.5  | CRUD API: `GET/PUT /api/config/institutions` (single config por workspace)                                            | P1         | 2h         | ✅      |
| 3B.6  | CRUD API: `GET/PUT /api/config/report-layout` (single config por workspace)                                           | P2         | 2h         | ✅      |
| 3B.7  | GET com fallback: se DB vazio para um config → carregar de `config/` global e retornar defaults (sem salvar no DB)    | P0         | 3h         | ✅      |
| 3B.8  | Endpoint `POST /api/config/import` — aceita JSON (formato original de config/*.json), valida via Pydantic, popula DB  | P0         | 4h         | ✅      |
| 3B.9  | Endpoint `GET /api/config/export` — serializa todas as configs do workspace (DB + defaults) como JSON download        | P0         | 3h         | ✅      |
| 3B.10 | Validação: Pydantic schemas em todo save/update. 422 com erros detalhados (campo, mensagem, valor recebido)           | P0         | 3h         | ✅      |


**Checkpoint 3B:** ✅ 18 endpoints REST em `backend/app/api/config.py`. Import de JSON (family_members, categorization, pipeline, institutions, report_layout) → popula DB. Export gera JSON compatível com pipeline CLI. Roundtrip import→export verificado. Fallback retorna defaults do disco se DB vazio. 30 testes de integração green.

**Fallback design — implementado:**

```python
# GET /api/config/members (backend/app/api/config.py)
@router.get("/config/members")
async def get_members(workspace_id: str, db: AsyncSession):
    ws = await _get_workspace(workspace_id, db)
    result = await db.execute(
        select(FamilyMember).where(FamilyMember.workspace_id == ws.id)
        .options(selectinload(FamilyMember.accounts))
        .order_by(FamilyMember.order)
    )
    members = result.scalars().all()
    if members:
        return {"members": [_member_to_schema(m) for m in members]}
    # Fallback: carregar defaults do disco (NÃO salva no DB)
    data = _load_global_json("family_members.json")
    return data  # Retorna formato original do pipeline
```

**Endpoints implementados (18 total):**

- `GET/POST /api/config/members` + `PUT/DELETE /api/config/members/{id}`
- `POST /api/config/members/{id}/accounts` + `DELETE /api/config/members/{mid}/accounts/{aid}`
- `GET/POST /api/config/categories` + `PUT/DELETE /api/config/categories/{id}`
- `GET/PUT /api/config/pipeline` (deep merge parcial)
- `GET/PUT /api/config/institutions`
- `GET/PUT /api/config/report-layout`
- `POST /api/config/import` + `GET /api/config/export`

---

#### Sub-fase 3C: Config Injection — Materialização (Semana 2-3) ✅ CONCLUÍDA

**Objetivo:** Config do DB chega ao pipeline via materialização em disco. Zero mudanças nos scripts.


| #    | Tarefa                                                                                                                      | Prioridade | Estimativa | Status |
| ---- | --------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 3C.1 | Service `ConfigSerializer` — 5 serializers que convertem modelos DB → dicts no formato exato esperado pelo pipeline         | P0         | 6h         | ✅      |
| 3C.2 | Service `materialize_config(workspace_id, db)` — copia config/ global para tenant, sobrescreve com configs editados do DB   | P0         | 4h         | ✅      |
| 3C.3 | Integrar `materialize_config()` no pipeline trigger (`POST /api/pipeline/run`) — chamado antes de iniciar background thread | P0         | 2h         | ✅      |
| 3C.4 | Testes unitários: cada serializer produz dict idêntico ao JSON original quando alimentado com dados equivalentes            | P0         | 4h         | ✅      |
| 3C.5 | Teste de paridade end-to-end: config do DB → materializa → pipeline → relatório idêntico ao gerado com config do disco      | P0         | 4h         | ✅      |


**Checkpoint 3C:** ✅ `config_materializer.py` implementado com 5 serializers (family_members, categorization, pipeline, institutions, report_layout). Integrado no `pipeline_service.py` — chamado antes de cada `Thread.start()`. 15 testes unitários de serialização + materialização green. Paridade DB↔disco verificada.

`**materialize_config()` — implementação real** (`backend/app/services/config_materializer.py`):

```python
def materialize_config(workspace_id: str, tenant_root: Path, db: Session) -> Path:
    """Materializa config do DB em disco para o pipeline ler via _init_config()."""
    tenant_config = tenant_root / "config"
    global_config = _global_config_dir()

    # 1. Copia TUDO do config/ global (base)
    _copy_global(global_config, tenant_config)

    # 2. Sobrescreve apenas configs editados no DB
    _override_family_members(workspace_id, tenant_config, db)
    _override_categorization(workspace_id, tenant_config, db)
    _override_pipeline(workspace_id, tenant_config, db)
    _override_institutions(workspace_id, tenant_config, db)
    _override_report_layout(workspace_id, tenant_config, db)

    return tenant_config
```

**Integração no pipeline trigger** (`pipeline_service.py`):

```python
def start_pipeline_run(ws_id, ...):
    from backend.app.services.config_materializer import materialize_config
    tenant_root = storage.ensure_tenant_dirs(ws_id)
    with SyncSessionLocal() as db:
        config_dir = materialize_config(ws_id, tenant_root, db)
    thread = Thread(target=_run_pipeline_thread, args=(..., config_dir))
    thread.start()
```

**5 serializers implementados:**

- `serialize_family_members()` → `family_members.json` (inclui accounts nested)
- `serialize_categorization()` → `categorization.json` (inclui keywords nested)
- `serialize_pipeline_config()` → `pipeline.json`
- `serialize_institution_config()` → `institutions.json`
- `serialize_report_layout()` → `report_layout.yaml` (via pyyaml)

**Por que copiar TUDO e sobrescrever?**

- Scripts leem VÁRIOS arquivos de `config/` (não apenas os 5 editáveis): `definitions.md`, `templates/`, `schemas/`, etc.
- Copiar a árvore inteira garante que tudo está disponível.
- Sobrescrever os editados garante que o DB tem prioridade.
- Custo: ~500KB por run. Tempo: <50ms. Aceitável.

---

#### Sub-fase 3D: Frontend + Testes (Semana 3-4) ✅ CONCLUÍDA

**Objetivo:** UI para editar configs, importar/exportar JSON, e testes de integração completos.


| #     | Tarefa                                                                                                                           | Prioridade | Estimativa | Status |
| ----- | -------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 3D.1  | UI: tela de membros da família (CRUD inline: nome, CPF mascarado, data nascimento, role) + adição de contas bancárias por membro | P0         | 6h         | ✅      |
| 3D.2  | UI: tela de contas bancárias (vinculadas a membros, select de banco, tipo de conta, agência, número)                             | P0         | 4h         | ✅      |
| 3D.3  | UI: tela de categorias (add/remove keywords por categoria, editar monthly_cap, drag-and-drop para reordenar)                     | P0         | 6h         | ✅      |
| 3D.4  | UI: tela de parâmetros do pipeline (form com campos agrupados: tolerâncias, thresholds, formatting)                              | P1         | 4h         | ✅      |
| 3D.5  | UI: tela de instituições (toggle bancos ativos, editor JSON para patterns avançados)                                             | P1         | 4h         | ✅      |
| 3D.6  | UI: tela de layout do relatório (toggle visibilidade de seções, drag-and-drop reorder)                                           | P2         | 4h         | ✅      |
| 3D.7  | UI: botão "Importar Config" (upload de JSON, preview das mudanças, confirmar)                                                    | P0         | 4h         | ✅      |
| 3D.8  | UI: botão "Exportar Config" (download de JSON com toda a config do workspace)                                                    | P0         | 2h         | ✅      |
| 3D.9  | Testes E2E: editar config (member + category) → run pipeline → relatório reflete nova config                                     | P0         | 6h         | ☐ → 7E |
| 3D.10 | Testes de validação: config inválida mostra erro claro na UI (CPF inválido, categoria duplicada, etc.)                           | P0         | 3h         | ☐ → 7E |


**Checkpoint 3D:** Fluxo completo via browser: editar config → importar/exportar → gerar relatório com nova config. Validação clara.

---

#### Critérios de aceite da Fase 3 completa


| Critério                    | Verificação                                                                                                                                     |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 5 configs editáveis via API | ✅ Members, categories, pipeline, institutions e report_layout são editáveis via 18 endpoints REST                                               |
| 5 configs editáveis via UI  | ✅ Config page com 6 tabs: Members CRUD, Categories CRUD, Pipeline params, Institutions toggle+JSON, Report Layout toggle+reorder, Import/Export |
| Fallback funcional          | ✅ Config não editado no DB → GET retorna default global. Nenhum config é obrigatório no DB                                                      |
| Materialização correta      | ✅ `materialize_config()` produz arquivos em `tenant/config/` idênticos aos originais quando dados são iguais                                    |
| Import funcional            | ✅ `POST /api/config/import` popula DB corretamente a partir de JSON (formato original de config/*.json)                                         |
| Export funcional            | ✅ `GET /api/config/export` gera JSON compatível com pipeline CLI (roundtrip verificado)                                                         |
| Validação Pydantic          | ✅ Config inválida é rejeitada com 422 + erros detalhados (CPF, roles, bounds, tipos)                                                            |
| Paridade de relatório       | ✅ Serializers produzem dict idêntico ao JSON original (testado). Materialização integrada no pipeline trigger                                   |
| CLI inalterado              | ✅ Pipeline CLI continua lendo de `config/` global sem nenhuma mudança (136 tests passing)                                                       |
| Multi-tenant                | ☐ Teste de isolamento entre workspaces (pendente testes E2E na Fase 6.5C)                                                                       |
| Regressão zero              | ✅ 310 testes (174 backend + 136 pipeline) todos green. Nenhuma regressão                                                                        |


#### O que a Fase 3 NÃO faz (fica para fases posteriores)


| Escopo excluído                            | Por quê                                                    | Fase destino |
| ------------------------------------------ | ---------------------------------------------------------- | ------------ |
| ~~Config de LLM (api_key, model, limits)~~ | ~~Requer LLM service~~                                     | ✅ Fase 4     |
| Histórico/versionamento de config          | Nice-to-have, não bloqueante                               | Fase 6       |
| Templates HTML editáveis                   | `report_template.html` é complexo (197KB), mantém estático | Futuro       |
| Schemas JSON editáveis                     | `schemas/` são de validação interna                        | Futuro       |
| Config compartilhada entre workspaces      | Cada workspace é independente por design                   | Futuro       |


#### Dependências da Fase 3 — instaladas ✅

```
# Backend — nova (adicionada em backend/requirements.txt)
pyyaml>=6.0               # Parsing de report_layout.yaml para JSON na API e materialização

# Backend — já instaladas (Fases 1-2) e reutilizadas
cryptography>=43.0        # Fernet para CPF encryption (reuso do vault)
sqlalchemy[asyncio]>=2.0  # Novos modelos config + queries
alembic>=1.13             # Migration Fase 3 (da5a6af13e3e)

# Nota: categorization.json tem 300+ keywords. A UI de categorias precisa
# de boa performance para listar/editar. Considerar paginação se necessário.
```

---

### FASE 4 — Automação LLM (Premium) ✅ CONCLUÍDA

**Objetivo:** As 4 etapas LLM (E1, E1.5, E2-llm, E7-review) rodam automaticamente via API. Pipeline Premium gera relatório completo end-to-end sem intervenção. Pipeline Free continua determinístico. Stages que falham validação após retries entram em review manual via UI.

**Resultado:** 444 testes green (240 backend + 204 pipeline), 0 failures, 2 skipped. LLM infrastructure + 4 stage runners + tier detection + needs_review workflow + resume + review CRUD. UI de LLM config/review adiada para Fase 6.

**Duração estimada:** 3-4 semanas (4 sub-fases)

#### Decisões tomadas para esta fase


| Decisão            | Escolha                                                | Rationale                                                                |
| ------------------ | ------------------------------------------------------ | ------------------------------------------------------------------------ |
| Provedor LLM       | LiteLLM (proxy universal, 100+ provedores)             | Máxima flexibilidade: Anthropic, OpenAI, local models. User escolhe      |
| API key model      | BYOK (Bring Your Own Key)                              | Zero custo para plataforma. User paga direto ao provedor. Simples        |
| Structured output  | Instructor + Pydantic schemas                          | Auto-retry em validação, menos código custom, Pydantic nativo            |
| Falha de validação | Retry 3x → `needs_review` (review manual via UI)       | Pipeline pausa, user edita JSON, retoma. Nenhum dado perdido             |
| E7 scope           | E7-review (LLM) + E7-apply (det.) + E6-final. Completo | Pipeline 100% end-to-end na Fase 4                                       |
| Prompts            | Em código (`pipeline/llm/prompts/{stage}.py`)          | Acoplados ao output schema. Versionados via git. Config-based é overhead |
| Token tracking     | Logging por call (model, tokens, cost estimate)        | BYOK = user precisa de visibilidade sobre custos                         |


#### Stack LLM

```
Pydantic output schemas (define estrutura esperada)
    ↓
Instructor (enforça schema via LLM, auto-retry em validation failure)
    ↓
LiteLLM (proxy universal — traduz para API de qualquer provedor)
    ↓
Qualquer LLM API (Anthropic Claude, OpenAI GPT, Ollama local, etc.)
```

#### Diagrama: pipeline Premium vs Free

```
POST /api/pipeline/run
    ↓
Detectar tier:
  LLMConfig válida + API key funcional → PREMIUM
  Sem LLMConfig ou API key inválida  → FREE
    ↓
┌─────────────────────────────────┬─────────────────────────────────┐
│         PREMIUM (FULL_ORDER)    │        FREE (DET_ORDER)         │
├─────────────────────────────────┼─────────────────────────────────┤
│ E1 (LLM) → members extract     │ ⊘ E1 skipped_free_tier          │
│ E1.5 (LLM) → baseline patrim.  │ ⊘ E1.5 skipped_free_tier        │
│ E1.5c (det.) → consolidate     │ E1.5c (se JSON uploadado F2)    │
│ E2-llm (LLM) → investimentos   │ ⊘ E2-llm skipped_free_tier      │
│ E2-fat (det.) → faturas         │ E2-fat (det.)                   │
│ E2-ext (det.) → extratos        │ E2-ext (det.)                   │
│ E3 → E4 → E5 → E5.N → E6      │ E3 → E4 → E5 → E5.N → E6      │
│ E7-crossval (det.)              │ E7-crossval (det.)              │
│ E7-review (LLM) → review       │ ⊘ E7-review skipped_free_tier   │
│ E7-apply (det.) → refinements   │ (sem refinements)               │
│ E6-final (det.) → relatório     │ ← relatório sem review section  │
└─────────────────────────────────┴─────────────────────────────────┘
```

#### Diagrama: fluxo needs_review

```
LLM stage (e.g. E2-llm)
    ↓
Instructor: call LLM → parse response → validate Pydantic schema
    ↓ (falha validação)
Retry #1 (prompt refinado com erros de validação)
    ↓ (falha novamente)
Retry #2
    ↓ (falha novamente)
Retry #3
    ↓ (falha final)
Stage status = 'needs_review'
PipelineRun status = 'needs_review'
StageReview criado com original_output
    ↓
User notificado: "E2-llm precisa de revisão"
    ↓
User abre Review UI:
  - Vê output original do LLM
  - Vê erros de validação
  - Edita JSON (ou cola JSON corrigido)
  - Clica "Aprovar e Continuar"
    ↓
POST /api/pipeline/runs/{id}/resume
  - Salva edited_output
  - Valida contra schema
  - Spawns new background thread
  - Pipeline retoma do stage seguinte
```

---

#### Sub-fase 4A: LLM Infrastructure (Semana 1) ✅ CONCLUÍDA

**Objetivo:** Setup de LiteLLM + Instructor, modelo de config, retry policy, e document text extraction.

**Resultado:** `LLMConfig` + `StageReview` models com migration. `LLMService` com LiteLLM + Instructor, retry exponencial, error classification, token tracking. `DocumentTextExtractor` (PDF/XLSX/CSV). 5 endpoints LLM API (CRUD + test + tier). Materialização estendida. 52 novos testes. 362 testes green total.


| #    | Tarefa                                                                                                                       | Prioridade | Estimativa | Status |
| ---- | ---------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 4A.1 | Modelo `LLMConfig` + migration (workspace_id, provider, api_key_encrypted via Fernet, model_name, max_tokens, temperature)   | P0         | 3h         | ✅      |
| 4A.2 | Setup LiteLLM: provider registry, connection factory, error classification (rate_limit, auth, timeout, validation)           | P0         | 4h         | ✅      |
| 4A.3 | Setup Instructor: integração com LiteLLM client, Pydantic schema enforcement, max_retries=3                                  | P0         | 3h         | ✅      |
| 4A.4 | Service `DocumentTextExtractor`: PDF→text (pdfplumber), XLSX→text/rows (openpyxl). Input prep para prompts LLM               | P0         | 4h         | ✅      |
| 4A.5 | Prompt templates framework: `pipeline/llm/prompts/{stage}.py` com system_prompt + user_prompt + output_schema ref            | P0         | 3h         | ✅      |
| 4A.6 | Retry policy: exponential backoff (2s, 4s, 8s), rate_limit→wait, auth→fail_fast, timeout→retry, validation→retry_with_errors | P0         | 3h         | ✅      |
| 4A.7 | Token usage logger: log por call (provider, model, tokens_in, tokens_out, cost_estimate, duration_ms) + summary por run      | P1         | 3h         | ✅      |
| 4A.8 | API endpoint `POST /api/config/llm` — save config (API key encrypted) + `POST /api/config/llm/test` — test connectivity      | P0         | 3h         | ✅      |
| 4A.9 | Estender `materialize_config()` (Fase 3) para incluir LLM config no tenant                                                   | P0         | 2h         | ✅      |


**Checkpoint 4A:** ✅ LiteLLM + Instructor configurados. API key salva encrypted. Test endpoint confirma conectividade com provedor escolhido.

**Pattern: LLM call com Instructor**

```python
import instructor
import litellm
from pydantic import BaseModel

client = instructor.from_litellm(litellm.completion)

class MembersExtractOutput(BaseModel):
    """Schema Pydantic = contrato do output LLM."""
    members: list[MemberData]

def call_llm_stage(llm_config: LLMConfig, system_prompt: str, user_prompt: str, output_schema: type[BaseModel]):
    """Chamada LLM padronizada via Instructor + LiteLLM."""
    return client.chat.completions.create(
        model=f"{llm_config.provider}/{llm_config.model_name}",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_model=output_schema,
        max_retries=3,  # Instructor auto-retry com erros de validação no prompt
        api_key=decrypt_key(llm_config.api_key_encrypted),
    )
```

---

#### Sub-fase 4B: E1 + E1.5 + E2-llm — Extração (Semana 1-2) ✅ CONCLUÍDA

**Objetivo:** As 3 etapas de extração LLM funcionam: dados pessoais, baseline patrimonial, investimentos/docs sem parser.

**Resultado:** 3 stage runners (`pipeline/stages/e1.py`, `e15.py`, `e2_llm.py`) com validadores de compatibilidade (`pipeline/llm/validators.py`). 4 golden files. Orchestrator atualizado com runners registrados. 67 novos testes (48 stages + 19 golden). 430 testes green total.


| #    | Tarefa                                                                                                                               | Prioridade | Estimativa | Status |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------ | ---------- | ---------- | ------ |
| 4B.1 | Pydantic output schemas: `MembersExtractOutput`, `BaselinePatrimonialOutput`, `LLMExtractOutput` — compatíveis com stages downstream | P0         | 4h         | ✅      |
| 4B.2 | Prompt + implementação E1: ler docs pessoais → extrair membros (nome, CPF, nascimento, role, contas) → validar → salvar members JSON | P0         | 6h         | ✅      |
| 4B.3 | Prompt + implementação E1.5: ler IRPFs + XLSX imóveis/veículos → extrair baseline patrimonial → validar → salvar baseline JSON       | P0         | 6h         | ✅      |
| 4B.4 | Prompt + implementação E2-llm: identificar docs sem parser det. → extrair transações/investimentos → validar → salvar extract JSONs  | P0         | 8h         | ✅      |
| 4B.5 | Integração E1.5c: roda automaticamente após E1.5 (LLM) no orchestrator. Output E1.5 → input E1.5c → baseline consolidado             | P0         | 2h         | ✅      |
| 4B.6 | Validadores de compatibilidade: output E1 é input válido para config members, output E1.5/E2-llm são inputs válidos para E3          | P0         | 4h         | ✅      |
| 4B.7 | Testes unitários com mock LLM: schemas produzidos, retry em validation failure, rejeição de output malformado                        | P0         | 4h         | ✅      |
| 4B.8 | Snapshot tests: fixtures com output LLM esperado (golden files) para detectar regressões em prompts                                  | P0         | 3h         | ✅      |


**Checkpoint 4B:** ✅ E1, E1.5, E2-llm produzem output válido e compatível com stages determinísticos downstream. Mock tests green.

**Nota sobre E2-llm:** Esta etapa lida com documentos que não têm parser determinístico em `scripts/e2/banks/`. Exemplos: informes de rendimentos bancários, posições de investimentos sem formato padronizado, CDBs/RDBs em PDF. O LLM recebe o texto extraído e produz o mesmo formato JSON que os parsers determinísticos — permitindo que E3 reconcile normalmente.

---

#### Sub-fase 4C: E7-review + E7-apply + Pipeline Completo (Semana 2-3) ✅ CONCLUÍDA

**Objetivo:** E7-review (LLM) + E7-apply (det.) + E6-final integrados. Pipeline FULL_ORDER funcional.

**Resultado:** `pipeline/stages/e7_review_llm.py` com runner completo. Todos os 4 LLM stages registrados no orchestrator (`_get_stage_runner`). FULL_ORDER testado (sequência correta E1→E1.5→E1.5c→E2-llm→...→E7-review→E7-apply→E6-final). Golden file + testes do E7-review. 444 testes green total.


| #    | Tarefa                                                                                                                                    | Prioridade | Estimativa | Status |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 4C.1 | Pydantic output schema: `E7ReviewOutput` (insights[], recommendations[], score_adjustments{}, narrative_sections{})                       | P0         | 3h         | ✅      |
| 4C.2 | Prompt E7-review: persona de consultor financeiro sênior, analisa E5 JSON + E7-crossval, gera review estruturado                          | P0         | 6h         | ✅      |
| 4C.3 | Implementação E7-review: ler E5 analysis + E7 crossval output → chamar LLM → validar → salvar review JSON                                 | P0         | 4h         | ✅      |
| 4C.4 | Integrar E7-apply (det.) + E6-final render no orchestrator — E7-apply lê review JSON, refina E5, E6-final re-renderiza                    | P0         | 3h         | ✅      |
| 4C.5 | Orchestrator FULL_ORDER: sequência completa (E1→E1.5→E1.5c→E2-llm→E2-fat→E2-ext→E3→E4→E5→E5.N→E6→E7-crossval→E7-review→E7-apply→E6-final) | P0         | 4h         | ✅      |
| 4C.6 | Teste E2E com mock LLM: pipeline premium completo → relatório final com review section integrada                                          | P0         | 4h         | ✅      |
| 4C.7 | Teste de paridade estrutural: relatório premium (mock) tem mesmas seções + review section vs relatório free (sem review)                  | P0         | 3h         | ✅      |


**Checkpoint 4C:** ✅ Pipeline premium FULL_ORDER funcional. E7-review integrado com E7-apply e E6-final.

---

#### Sub-fase 4D: Tier Detection + Manual Review + Backend APIs (Semana 3-4) ✅ CONCLUÍDA

**Objetivo:** Diferenciação Free/Premium funcional. Workflow de review manual para stages que falham. APIs completas.

**Resultado:** Tier detection via `LLMConfig` existência (async query no API handler). `pipeline_service.py` com auto-skip free tier + needs_review handling + resume. 3 novos API endpoints (resume, list reviews, action review). `PipelineRunStatus` expandido (needs_review, resuming). `PipelineStageStatus` expandido (skipped_free_tier, needs_review). 14 novos testes. 444 testes green total (240 backend + 204 pipeline), 0 failures.

**Nota:** As tasks de UI (4D.8, 4D.9, 4D.10) foram movidas para a Fase 6 (Frontend Polished), onde serão implementadas junto com as demais telas de frontend. Os endpoints de API estão prontos para consumo.


| #     | Tarefa                                                                                                                                  | Prioridade | Estimativa | Status   |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | -------- |
| 4D.1  | Modelo `StageReview` + migration (pipeline_run_id, stage, original_output_json, edited_output_json, status, reviewer_notes, timestamps) | P0         | 2h         | ✅        |
| 4D.2  | Enum `PipelineRunStatus` expandido: adicionar `needs_review`, `resuming` aos status existentes                                          | P0         | 1h         | ✅        |
| 4D.3  | Orchestrator: detectar tier — `LLMConfig` válida + API key testada → premium, sem config → free                                         | P0         | 2h         | ✅        |
| 4D.4  | Pipeline Free: skip LLM stages com `status='skipped_free_tier'` no `PipelineStageLog`, continuar com determinísticos                    | P0         | 3h         | ✅        |
| 4D.5  | Pipeline `needs_review`: após retries falhados → criar `StageReview`, setar run `status='needs_review'`, thread retorna                 | P0         | 4h         | ✅        |
| 4D.6  | APIs de review: `GET /runs/{id}/reviews`, `POST /runs/{id}/reviews/{review_id}` (approve/edit), `POST /runs/{id}/resume` (retomar)      | P0         | 4h         | ✅        |
| 4D.7  | Resume: valida que reviews estão resolvidas, spawna nova thread a partir do stage seguinte com tier correto                             | P0         | 3h         | ✅        |
| 4D.8  | UI: tela de configuração LLM (select provider, input API key mascarada, select modelo, botão testar conectividade)                      | P0         | 4h         | → Fase 6 |
| 4D.9  | UI: indicador de tier no dashboard (badge Free/Premium) + lock icons em etapas LLM no progress tracker                                  | P1         | 3h         | → Fase 6 |
| 4D.10 | UI: tela de review manual (JSON editor com syntax highlighting, erros de validação inline, diff com original, botão aprovar + retomar)  | P0         | 6h         | → Fase 6 |
| 4D.11 | Testes: free skipa LLM stages, premium roda E2E (mock), needs_review pausa corretamente, resume retoma do stage certo                   | P0         | 4h         | ✅        |


**Checkpoint 4D:** ✅ Tier detection funcional. Free skipa LLM. Premium roda E2E (backend). Review manual funciona: pause → edit → resume. UI adiada para Fase 6.

**Pattern: needs_review no background thread**

```python
def _run_pipeline_background(run_id: int, workspace_id: str, is_premium: bool):
    db = SyncSessionLocal()
    try:
        stages = FULL_ORDER if is_premium else DETERMINISTIC_ORDER
        for stage_name, stage_fn, is_llm in stages:
            if is_llm and not is_premium:
                log = PipelineStageLog(
                    pipeline_run_id=run_id, stage=stage_name,
                    status="skipped_free_tier"
                )
                db.add(log); db.commit()
                continue
            log = PipelineStageLog(
                pipeline_run_id=run_id, stage=stage_name, status="running"
            )
            db.add(log); db.commit()
            try:
                result = stage_fn(ctx)
                log.status = "completed"
            except LLMValidationError as e:
                log.status = "needs_review"
                review = StageReview(
                    pipeline_run_id=run_id,
                    stage=stage_name,
                    original_output_json=e.last_output,
                    validation_errors=e.errors,
                    status="pending",
                )
                db.add(review)
                run.status = "needs_review"
                run.paused_at_stage = stage_name
                db.commit()
                return  # Thread encerra. Será retomada via POST /resume
            except Exception as e:
                log.status = "failed"
                run.status = "partial_failure"
                run.failed_at_stage = stage_name
                db.commit()
                return
            db.commit()
        run.status = "completed"
        db.commit()
    finally:
        db.close()
```

---

#### Critérios de aceite da Fase 4 completa ✅


| Critério                   | Verificação                                                                                               | Status             |
| -------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------ |
| Premium E2E                | Pipeline premium roda end-to-end sem intervenção humana (com API key válida)                              | ✅ (backend + mock) |
| Free determinístico        | Pipeline free roda apenas stages det., LLM stages marcados como `skipped_free_tier`                       | ✅                  |
| Relatório premium          | Inclui review section (E7-review), score adjustments (E7-apply), re-render (E6-final)                     | ✅ (FULL_ORDER)     |
| Relatório free             | Idêntico ao da Fase 3 (determinístico, sem review section)                                                | ✅                  |
| Output validado            | Todo output LLM é validado contra Pydantic schema antes de ser aceito                                     | ✅                  |
| needs_review funcional     | Stage que falha validação → pipeline pausa → user edita via API → pipeline retoma                         | ✅                  |
| API key segura             | Armazenada com Fernet encryption at-rest. Nunca retornada em plaintext pela API (mascarada: `sk-...****`) | ✅                  |
| Multi-provider             | Funciona com pelo menos Anthropic + OpenAI (testado via LiteLLM). 6 providers suportados                  | ✅                  |
| Token visibility           | Token tracking por call (tokens_in, tokens_out, cost_estimate, duration_ms) + summary por run             | ✅                  |
| Compatibilidade downstream | Output de E1, E1.5, E2-llm alimentam stages det. (E1.5c, E3, E4, E5) sem erros. Validadores dedicados     | ✅                  |
| Regressão zero             | 444 testes green (204 pipeline + 240 backend). Pipeline det. stages inalterados                           | ✅                  |


#### O que a Fase 4 NÃO faz (fica para fases posteriores)


| Escopo excluído                                     | Por quê                                                               | Fase destino |
| --------------------------------------------------- | --------------------------------------------------------------------- | ------------ |
| Billing / subscription management                   | BYOK elimina necessidade. Billing se plataforma provê key futuramente | Fase 7       |
| Rate limiting por user                              | BYOK = rate limit é do provedor, não nosso                            | Fase 7       |
| Prompt A/B testing / evaluation framework           | Otimização de prompts é iterativa pós-launch                          | Futuro       |
| Fine-tuning de modelos                              | Premature optimization                                                | Futuro       |
| Cache de responses LLM (mesmo input → mesmo output) | LLM é não-determinístico, cache requer design cuidadoso               | Fase 6       |
| OCR para imagens/scans (PDFs não-nativos)           | Escopo limitado a PDFs com texto selecionável                         | Futuro       |


#### Dependências da Fase 4 ✅

```
# Dependências adicionadas (requirements.txt)
litellm>=1.40.0    # Proxy universal para LLM providers
instructor>=1.3.0  # Structured output via Pydantic enforcement
pdfplumber>=0.11.0 # PDF text extraction para DocumentTextExtractor

# Já disponíveis (Fases 0-3):
# openpyxl (XLSX), cryptography (Fernet), pydantic, sqlalchemy, fastapi, pyyaml
```

---

### FASE 4.5 — Design System Foundation ✅ CONCLUÍDA

**Objetivo:** Estabelecer a fundação visual e de UX que todas as fases subsequentes (5, 6, 7) consomem. Definir design tokens via Tailwind v4 `@theme`, instalar shadcn/ui, criar componentes financeiros core, padronizar formatação numérica, e migrar todas as pages existentes para o design system.

**Resultado:** 3 sub-fases (4.5A-4.5C) concluídas. 30+ tokens oklch, Geist fonts, 16 primitivos shadcn/ui, 7 compostos financeiros, 10 pages migradas. Build green.

**Rationale:** Produtos financeiros profissionais exigem consistência visual extrema. Números formatados diferente em páginas diferentes, cores inconsistentes entre charts e tabelas, ou tipografia sem hierarchy destróem confiança. Criar a fundação ANTES do frontend polish (Fase 6) custa 10x menos do que retrofitar depois.

#### Audit do frontend pré-4.5 (baseline)

Audit realizado em 2026-04-14 para informar decisões desta fase:

- **Stack:** Next.js 16.2.3, React 19.2.5, Tailwind CSS 4.2.2, TypeScript 6.0.2 (App Router, `src/` dir)
- **Escopo atual:** ~3.320 linhas, 21 arquivos em `frontend/src/`. 10 pages, 1 componente (`AppShell`), 2 libs (`api.ts`, `format.ts`)
- **Zero component library:** toda UI é raw HTML + Tailwind utility classes
- **Zero fonts configuradas:** sem `next/font`, usa system fonts do browser
- **Zero design tokens:** `globals.css` = `@import "tailwindcss"` (1 linha). Sem `@theme`, sem CSS custom properties, sem `:root`
- **Zero testes frontend:** nenhum Vitest/Jest/Playwright
- **Spinner duplicado ~10x:** mesmo bloco CSS copy-paste em quase todo arquivo
- **Botões inconsistentes:** classes copy-paste com variações (`py-2` vs `py-2.5`, `shadow-sm` intermitente)
- **Alertas inconsistentes:** MembersTab usa helper `Alerts`; outros pages fazem inline com diferenças sutis
- `**format.ts` retorna classes Tailwind hardcoded:** `bg-red-100 text-red-700` — quebrará com dark mode / temas
- **Config tabs sem ARIA:** sem `role="tablist"`, `aria-selected`, `aria-controls`
- **Custom toggles sem semântica:** sem `aria-pressed`, sem role de switch
- `**confirm()` nativo** para ações destrutivas — não customizável, quebra UX
- **Reports list silently fails:** `.catch(() => {})` sem error UI
- **Responsive OK mas parcial:** sidebar mobile funciona, mas tabela de documentos sem `overflow-x-auto`

#### Decisões tomadas para esta fase


| Decisão             | Escolha                                                 | Rationale                                                                                                        |
| ------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Component library   | **shadcn/ui** (Radix primitives + Tailwind)             | Composable, acessível by default, customizável, sem vendor lock. Suporte oficial Tailwind v4 + React 19          |
| Design tokens       | **Tailwind v4 `@theme` directive** em `globals.css`     | CSS-first (v4 nativo). Sem `tailwind.config.ts`. `@theme inline` para shadcn/ui. Dark mode via `@custom-variant` |
| Typography          | **Geist Sans + Geist Mono** via `next/font`             | Geist é a font padrão do ecossistema Next.js/Vercel. Mono para números financeiros (tabular nums)                |
| Number formatting   | `**Intl.NumberFormat`** + utility library (`format.ts`) | Nativo do browser, locale-aware (pt-BR, en-US), consistente. Zero deps externas                                  |
| Financial colors    | Paleta semântica com alternativas **colorblind-safe**   | Verde/vermelho para gain/loss, com fallback para shape+icon (↑↓) para acessibilidade                             |
| Status badge colors | **Variants do design system** (não Tailwind hardcoded)  | Migrar `format.ts` de `bg-red-100 text-red-700` para semantic variant names                                      |
| Chart color palette | **12 cores categóricas** derivadas dos design tokens    | Preparar palette para Recharts (Fase 6). Distinguíveis em simulação colorblind                                   |
| Icon library        | **Lucide React** (padrão shadcn/ui)                     | Consistente, tree-shakeable, substituir SVGs inline e emojis atuais                                              |
| Utility function    | `**cn()` helper** (clsx + tailwind-merge)               | Padrão shadcn/ui para merge seguro de classes Tailwind. Eliminar duplicação de classes                           |


---

#### Sub-fase 4.5A: Design Tokens + Typography + Financial Formatting (Semana 1) ✅ CONCLUÍDA

**Objetivo:** Definir a linguagem visual do produto. Tokens via `@theme`, tipografia profissional, e formatação financeira padronizada. Tudo em `globals.css` + `format.ts` — nenhum componente React ainda.

**Contexto técnico:** O projeto usa Tailwind CSS v4 com config CSS-first (sem `tailwind.config.ts`). Design tokens são definidos via `@theme` / `@theme inline` no `globals.css`. Dark mode via `@custom-variant dark (&:is(.dark *))`. shadcn/ui injeta suas CSS variables nesta mesma estrutura.


| #      | Tarefa                                                                                                                                                                                                                                                                                                                                                       | Prioridade | Estimativa | Status |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | ---------- | ------ |
| 4.5A.1 | **Font setup:** Instalar Geist Sans + Geist Mono via `next/font/google`. Aplicar no root `layout.tsx`. Font variables: `--font-sans`, `--font-mono`                                                                                                                                                                                                          | P0         | 1h         | ✅      |
| 4.5A.2 | **Design tokens em `globals.css`:** `@theme inline` com cores semânticas (background, foreground, primary, secondary, muted, accent, destructive, border, ring, card, popover), tipografia (font-family, font-size scale 6 níveis), radius, spacing. Light mode `:root` + dark mode `.dark` via CSS variables (oklch). Compatível com shadcn/ui color system | P0         | 4h         | ✅      |
| 4.5A.3 | **Paleta financeira semântica:** Adicionar tokens: `--gain` (verde), `--loss` (vermelho), `--neutral-financial` (cinza), `--alert` (amber), `--info-financial` (azul). Variantes light + dark. Testar com Sim Daltonism (protanopia, deuteranopia). Incluir na `@theme`                                                                                      | P0         | 2h         | ✅      |
| 4.5A.4 | **Chart color palette:** 12 cores categóricas como CSS variables (`--chart-1` a `--chart-12`). Distinguíveis em simulação colorblind. Gradients para AreaChart. Registrar na `@theme` para uso via Tailwind classes (`bg-chart-1`, etc.)                                                                                                                     | P0         | 2h         | ✅      |
| 4.5A.5 | **Financial formatting utilities** em `format.ts`: `formatCurrency(value, currency?)` (BRL default, USD), `formatPercent(value, decimals?)`, `formatDelta(value, opts?)` ("+R$ 1.234 (+12,5%)"), `formatCompact(value)` ("R$ 1,2M"). Usar `Intl.NumberFormat` com locale `pt-BR`. Unit tests inline ou separados                                             | P0         | 3h         | ✅      |
| 4.5A.6 | **Date formatting utilities** em `format.ts`: `formatPeriod(yyyymm)` ("jan/2026"), `formatMonth(date)`, `formatRange(start, end)` ("jan–abr/2026"). Padrão BR. Sem `date-fns` — usar `Intl.DateTimeFormat` nativo. Manter `formatDate` e `formatDateShort` existentes                                                                                        | P0         | 1h         | ✅      |
| 4.5A.7 | **Utility `cn()`:** Criar `lib/utils.ts` com helper `cn(...inputs)` usando `clsx` + `tailwind-merge`. Instalar deps: `npm install clsx tailwind-merge`. Este é o padrão shadcn/ui para composição de classes                                                                                                                                                 | P0         | 0.5h       | ✅      |


**Checkpoint 4.5A:** Fonts Geist aplicadas. `globals.css` com `@theme inline` + CSS variables light/dark. `format.ts` com 8+ formatters financeiros. `cn()` disponível. `next build` green. Visualmente: fontes mudaram, cores base ainda as mesmas (migração visual é na 4.5C).

---

#### Sub-fase 4.5B: shadcn/ui Setup + Core Components (Semana 1) ✅ CONCLUÍDA

**Objetivo:** Instalar shadcn/ui (Tailwind v4 mode), gerar primitivos base, e criar componentes financeiros compostos que todas as páginas subsequentes consomem. Nenhuma page existente é modificada nesta sub-fase — apenas novos componentes em `components/ui/` e `components/`.


| #      | Tarefa                                                                                                                                                                                                                                                                                                                                                                                                                  | Prioridade | Estimativa | Status |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 4.5B.1 | **shadcn/ui init:** `npx shadcn@latest init` (Tailwind v4 mode). Gera `components.json`. Verifica `globals.css` — shadcn injeta CSS variables + `@theme inline` automaticamente. Resolver conflitos com tokens da 4.5A.2 (merge manual se necessário)                                                                                                                                                                   | P0         | 1h         | ✅      |
| 4.5B.2 | **Primitivos base (batch install):** `npx shadcn@latest add button input label select textarea card badge table tabs switch alert-dialog dialog sheet tooltip separator skeleton sonner`. ~15 componentes em `components/ui/`. Verificar imports e build                                                                                                                                                                | P0         | 1h         | ✅      |
| 4.5B.3 | `**<StatusBadge>`:** Componente composto sobre shadcn `Badge`. Variants: `success`, `warning`, `error`, `info`, `neutral`, `premium`, `muted`. Mapear nomes semânticos para as cores dos design tokens. Substituir pattern atual do `format.ts` (que retorna classes hardcoded) por variant names. Atualizar `format.ts`: funções de status retornam `{ label, variant }` em vez de `{ label, color: "bg-red-100..." }` | P0         | 2h         | ✅      |
| 4.5B.4 | `**<Spinner>`:** Componente shared (loading indicator). Props: `size` (sm/md/lg), `className`. Eliminar o spinner CSS duplicado em ~10 arquivos. Não migrar pages ainda — apenas criar o componente                                                                                                                                                                                                                     | P0         | 0.5h       | ✅      |
| 4.5B.5 | `**<EmptyState>`:** Ícone Lucide + título + descrição + CTA button opcional. Variants por contexto (`no-documents`, `no-reports`, `no-data`, `error`). Props tipadas                                                                                                                                                                                                                                                    | P0         | 1.5h       | ✅      |
| 4.5B.6 | `**<Delta>`:** Gain/loss display. Seta ↑↓ via Lucide (`TrendingUp`/`TrendingDown`), cor semântica (`--gain`/`--loss`), formato via `formatDelta()`. Props: `value`, `percent?`, `currency?`, `invert?` (para despesas onde negativo = bom). Acessibilidade: `aria-label` com valor textual completo                                                                                                                     | P0         | 2h         | ✅      |
| 4.5B.7 | `**<KPICard>`:** Sobre shadcn `Card`. Props: `label`, `value` (formatted string), `delta?` (usa `<Delta>`), `icon?` (Lucide), `loading?` (usa `Skeleton`). Tamanho responsivo. Será usado no Dashboard (F6A)                                                                                                                                                                                                            | P0         | 2h         | ✅      |
| 4.5B.8 | `**<PageHeader>`:** Título + descrição + actions slot (botões). Padroniza o header de todas as pages (atualmente cada page tem `<h1>` + `<p>` com classes ligeiramente diferentes)                                                                                                                                                                                                                                      | P0         | 1h         | ✅      |
| 4.5B.9 | `**<ConfirmDialog>`:** Sobre shadcn `AlertDialog`. Props: `title`, `description`, `confirmLabel`, `variant` (`destructive`/`default`), `onConfirm`. Substitui `confirm()` nativo                                                                                                                                                                                                                                        | P0         | 1h         | ✅      |


**Checkpoint 4.5B:** shadcn/ui instalado com ~15 primitivos. 7 componentes compostos criados (`StatusBadge`, `Spinner`, `EmptyState`, `Delta`, `KPICard`, `PageHeader`, `ConfirmDialog`). `format.ts` retorna variant names em vez de classes hardcoded. `next build` green. Nenhuma page existente foi alterada ainda.

**Componentes adiados para Fase 6 (não necessários até lá):**


| Componente          | Motivo do adiamento                                       | Fase destino |
| ------------------- | --------------------------------------------------------- | ------------ |
| `<DataTable>`       | Requer decisão de sorting/filtering lib. Só usado em F6E  | Fase 6E      |
| `<DateRangePicker>` | Requer `date-fns` ou `@internationalized/date`. Só em F6A | Fase 6A      |
| `<SourceTooltip>`   | Requer data lineage model. Só usado em F6B                | Fase 6B      |


---

#### Sub-fase 4.5C: Page Migration (Semana 2) ✅ CONCLUÍDA

**Objetivo:** Migrar todas as 10 pages existentes e o `AppShell` para usar shadcn/ui primitivos, design tokens, Lucide icons, e os componentes compostos da 4.5B. Resultado: visual consistente, acessibilidade melhorada, zero spinner/button/alert duplicado.

**Estratégia:** Migrar page por page, rodando `next build` após cada uma. Ordem: pages menores e mais simples primeiro (login, register), depois pages mais complexas (config tabs). Manter funcionalidade idêntica — mudar apenas apresentação.


| #       | Tarefa                                                                                                                                                                                                                                                                                         | Prioridade | Estimativa | Status |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 4.5C.1  | **Root layout:** Aplicar font variables Geist (`className={fontSans.variable} ${fontMono.variable}`). Classe `antialiased` já presente. Trocar `bg-gray-50 text-gray-900` por `bg-background text-foreground` (design tokens)                                                                  | P0         | 0.5h       | ✅      |
| 4.5C.2  | **Login + Register:** Migrar para shadcn `Card`, `Input`, `Label`, `Button`. Substituir alert strips por inline error semântico. Manter `htmlFor`/`id` (já corretos). Adicionar `Button` variant `default` e loading state                                                                     | P0         | 2h         | ✅      |
| 4.5C.3  | **AppShell:** Migrar sidebar para shadcn `Button` variant `ghost` para nav items, `Separator`, Lucide icons (`FileText`, `Zap`, `BarChart3`, `KeyRound`, `Settings`, `Menu`, `LogOut`). Manter lógica de auth gate e mobile toggle                                                             | P0         | 2h         | ✅      |
| 4.5C.4  | **Documents page:** Migrar para shadcn `Table` (com `overflow-x-auto` para mobile), `Button`, `StatusBadge`. Emoji file icons → Lucide (`FileText`, `FileSpreadsheet`, `File`, `Wrench`). `ConfirmDialog` para delete. Upload zone: `Card` dashed. Progress bar: design tokens                 | P0         | 3h         | ✅      |
| 4.5C.5  | **Pipeline page:** Migrar stage progress bar para `StatusBadge` + design tokens. `Spinner` para loading. `ConfirmDialog` para cancel. `Card` para active run. Expandable errors com Lucide chevrons                                                                                            | P0         | 2.5h       | ✅      |
| 4.5C.6  | **Vault page:** Migrar form para shadcn `Input`, `Button`. `ConfirmDialog` para delete. `EmptyState` quando lista vazia                                                                                                                                                                        | P0         | 1.5h       | ✅      |
| 4.5C.7  | **Reports list:** Migrar para `EmptyState` com CTA. Lucide `BarChart3` para ícone. **Fix silent error:** `.catch(() => {})` → mostra error state                                                                                                                                               | P0         | 1.5h       | ✅      |
| 4.5C.8  | **Report viewer:** Migrar loading para `Spinner`. Error com Lucide `AlertCircle` + design tokens                                                                                                                                                                                               | P0         | 0.5h       | ✅      |
| 4.5C.9  | **Config page + tabs:** shadcn `Tabs` (ARIA automático + keyboard nav). `Input`, `Label`, `Button`, `Switch`, `Card`, `Textarea`. `ConfirmDialog` em MembersTab+CategoriesTab. `StatusBadge` em CategoriesTab stats. `CardHeader`/`CardTitle`/`CardDescription` em PipelineTab+ImportExportTab | P0         | 4h         | ✅      |
| 4.5C.10 | **Home redirect page:** Migrar spinner para `<Spinner>`                                                                                                                                                                                                                                        | P0         | 0.5h       | ✅      |
| 4.5C.11 | **Cleanup:** Zero spinner CSS inline. Zero `confirm()` nativo. Zero botão hardcoded. `next build` + `tsc --noEmit` green                                                                                                                                                                       | P0         | 1h         | ✅      |


**Checkpoint 4.5C:** Todas as 10 pages + AppShell migradas para design system. Visual consistente cross-page. Zero spinner duplicado, zero `confirm()` nativo, zero botão com classes copy-paste. Tabs de config acessíveis (ARIA). Toggles semânticos (Switch). `next build` green.

---

#### Critérios de aceite da Fase 4.5 completa ✅


| Critério                    | Verificação                                                                                                         | Status |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------ |
| Fonts profissionais         | Geist Sans + Geist Mono aplicadas via `next/font/google`. Números financeiros em monospace (tabular-nums)           | ✅      |
| Design tokens definidos     | `globals.css` com `@theme inline` + CSS variables oklch (light + dark). ~30+ tokens semânticos                      | ✅      |
| Formatação padronizada      | `formatCurrency(1234.56)` → "R$ 1.234,56". `formatDelta(0.125)` → "+12,5%". Zero inconsistência numérica            | ✅      |
| Paleta financeira semântica | Gain/loss/alert/info/neutral-financial. 5 tokens com variantes light + dark em oklch                                | ✅      |
| shadcn/ui funcional         | 16 primitivos instalados (base-ui/react). `import { Button } from "@/components/ui/button"` funciona                | ✅      |
| Componentes compostos       | `StatusBadge`, `Spinner`, `EmptyState`, `Delta`, `KPICard`, `PageHeader`, `ConfirmDialog` + `useConfirmDialog` hook | ✅      |
| `cn()` utility              | `lib/utils.ts` com `cn()` (clsx + tailwind-merge). Usado em todos os componentes novos                              | ✅      |
| Lucide icons                | SVGs inline e emojis substituídos por Lucide icons em todas as pages (FileText, Zap, BarChart3, KeyRound, etc.)     | ✅      |
| format.ts migrado           | Funções de status retornam `{ label, variant }` (nomes semânticos `StatusVariant`), não classes Tailwind hardcoded  | ✅      |
| Tabs acessíveis             | Config tabs usam shadcn `Tabs` (base-ui) com `role="tablist"`, `aria-selected`, navegação por teclado               | ✅      |
| Destructive confirms        | Todo `confirm()` nativo substituído por `ConfirmDialog` (shadcn `AlertDialog`)                                      | ✅      |
| Zero duplicação             | Nenhum spinner CSS inline restante. Nenhum bloco de classes de botão copy-paste                                     | ✅      |
| Reports error handling      | `reports/page.tsx` mostra error state quando API falha (fix do `.catch(() => {})`)                                  | ✅      |
| Mobile table scroll         | Documents table tem `overflow-x-auto` no container                                                                  | ✅      |
| Pages migradas              | Todas as 10 pages + AppShell usam design system. Consistência visual cross-page                                     | ✅      |
| Build green                 | `next build` + `tsc --noEmit` green. Funcionalidades das Fases 2-4 inalteradas                                      | ✅      |


#### O que a Fase 4.5 NÃO faz


| Escopo excluído                    | Por quê                                                                               | Fase destino |
| ---------------------------------- | ------------------------------------------------------------------------------------- | ------------ |
| Dashboard charts/KPIs reais        | Requer API backend + dados E5. Aqui cria `KPICard` pattern sem dados reais            | Fase 6A      |
| Transaction Explorer / `DataTable` | Requer API transactions + decisão de sorting lib. Complexo demais para fundação       | Fase 6E      |
| `DateRangePicker`                  | Requer lib de datas (date-fns ou @internationalized/date). Só necessário em F6A       | Fase 6A      |
| `SourceTooltip` (data lineage)     | Requer data lineage model no backend. Só necessário em F6B                            | Fase 6B      |
| Dark mode **toggle**               | Toggle UI é Fase 6D (6D.1). Aqui os tokens **suportam** dark mode (variáveis prontas) | Fase 6D      |
| Animações e micro-interactions     | Polish visual diferido para F8. Aqui garante que a base estrutural é sólida           | Fase 8       |
| Command palette (cmdk)             | Feature de UX avançada. Só necessário em F6D                                          | Fase 6D      |
| Testes de componentes (Vitest)     | Importante mas não bloqueante. Setup + testes adicionados na Fase 6.5                 | Fase 6.5     |


#### Dependências da Fase 4.5 (instaladas ✅)

```
# Instalados via shadcn/ui init (automático)
@base-ui/react              # Base primitivos (shadcn/ui v4 usa base-ui em vez de radix)
@radix-ui/react-*           # Primitivos acessíveis (alert-dialog, dialog, tabs, etc.)
class-variance-authority    # Variant management (cva) — componentes shadcn/ui
tw-animate-css              # Animações Tailwind (substitui tailwindcss-animate no v4)

# Instalados manualmente
clsx                        # Conditional class composition
tailwind-merge              # Class merging (via cn() utility)
lucide-react                # Icon library (consistente com shadcn/ui, tree-shakeable)

# Já disponíveis (sem instalar)
next/font/google            # Geist Sans + Geist Mono (built-in Next.js)
Intl.NumberFormat           # Financial formatting (nativo do browser)
Intl.DateTimeFormat         # Date formatting (nativo do browser)

# NÃO instalados nesta fase (adiados)
date-fns                    # Só necessário com DateRangePicker (Fase 6A)
cmdk                        # Command palette (Fase 6D)
recharts                    # Charts (Fase 6A)
@tanstack/react-virtual     # Virtual scrolling (Fase 6E)
```

---

### FASE 5 — Task Queue + Real-time Progress ✅ CONCLUÍDA

**Objetivo:** Migrar execução do pipeline de `threading.Thread` (Fase 2) para Celery + Redis. Progresso em tempo real via WebSocket (com polling como fallback). Cancelamento stage-boundary. Concurrency limit por workspace.

**Resultado:** 3 sub-fases (5A-5C) concluídas. Pipeline via Celery com fallback Thread. Redis Pub/Sub. WebSocket real-time + polling backward-compat. Stage-boundary cancel + per-stage retry. Health check expandido (Redis + Celery + DB). 44 novos testes backend.

#### Decisões tomadas para esta fase


| Decisão            | Escolha                                          | Rationale                                                                 |
| ------------------ | ------------------------------------------------ | ------------------------------------------------------------------------- |
| Task queue         | Celery + Redis                                   | Pipeline é sync. Celery é sync-native, maduro, tem Flower para monitoring |
| Real-time progress | WebSocket + polling fallback (coexistem)         | WS para tempo real, polling como fallback robusto (Fase 2 compat)         |
| Redis scope        | Broker + result backend + Pub/Sub                | Pub/Sub: worker→WS handler inter-process. Cache como bônus                |
| Cancelamento       | Stage-boundary (espera stage atual, depois para) | Seguro, sem cleanup de estado parcial. LLM stages podem demorar 5-10min   |
| Concurrency        | 1 pipeline run por workspace                     | Evita race conditions em arquivos do tenant. 409 se já tem run ativo      |


#### Diagrama: arquitetura Celery + WebSocket

```
Browser (React)
  ├─ POST /api/pipeline/run → FastAPI → celery_task.delay() → 202 {run_id}
  ├─ WS /api/pipeline/runs/{id}/ws → subscribe Redis channel → receive events
  └─ GET /api/pipeline/runs/{id} → polling fallback (sempre funciona)

Celery Worker (processo separado):
  run_pipeline_task(run_id, workspace_id, is_premium)
    ├─ Para cada stage:
    │   ├─ Atualiza PipelineStageLog no DB (sync session)
    │   ├─ Publica event no Redis channel pipeline:{run_id}
    │   │   → { "event": "stage_completed", "stage": "E3", "progress": 45% }
    │   ├─ Se needs_review → publica event, task retorna
    │   └─ Se cancelled → publica event, task retorna
    └─ Ao final: publica "run_completed" + atualiza PipelineRun

FastAPI WS Handler:
  async def ws_pipeline_progress(websocket, run_id):
    pubsub = redis.pubsub()
    pubsub.subscribe(f"pipeline:{run_id}")
    for message in pubsub.listen():
      await websocket.send_json(message)
```

#### Migração de threading.Thread → Celery

```
FASE 2 (pseudo-async):                    FASE 5 (task queue):
─────────────────────                      ─────────────────────
POST /api/pipeline/run                     POST /api/pipeline/run
  ↓                                          ↓
thread = Thread(target=_run_bg)            task = run_pipeline.delay(run_id, ...)
thread.start()                             PipelineRun.celery_task_id = task.id
  ↓                                          ↓
return {run_id}                            return {run_id}  (202 Accepted)
  ↓                                          ↓
Client polls GET /runs/{id}                Client: WS /runs/{id}/ws OU polls GET
  ↓                                          ↓
Thread usa SyncSessionLocal                Celery worker usa SyncSessionLocal
  (mesmo pattern, migração suave)            + publica events via Redis Pub/Sub
```

> **Migração suave:** O `SyncSessionLocal` e a lógica do background thread (Fase 2) são reutilizados quase intactos dentro da Celery task. A diferença é o scheduler (Celery em vez de `Thread`) e a adição de Pub/Sub para events.

---

#### Sub-fase 5A: Task Queue Infrastructure (Semana 1) ✅ CONCLUÍDA

**Objetivo:** Celery + Redis rodando. Pipeline execution migrado de Thread para Celery task.


| #    | Tarefa                                                                                                                                                | Prioridade | Estimativa | Status |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 5A.1 | Docker Compose: adicionar Redis service (redis:7-alpine) + volume para persistência                                                                   | P0         | 2h         | ✅      |
| 5A.2 | Setup Celery: app config, broker_url, result_backend, task_serializer='json', task_track_started=True                                                 | P0         | 3h         | ✅      |
| 5A.3 | Celery task `run_pipeline`: encapsula lógica do background thread (Fase 2/4) como `@shared_task`. Mesmo SyncSessionLocal + stage loop                 | P0         | 4h         | ✅      |
| 5A.4 | Migrar `POST /api/pipeline/run`: de `Thread.start()` para `task.delay()`. Armazenar `celery_task_id` no `PipelineRun`                                 | P0         | 2h         | ✅      |
| 5A.5 | Redis Pub/Sub: task publica events `stage_started`, `stage_completed`, `stage_failed`, `needs_review`, `run_completed` no channel `pipeline:{run_id}` | P0         | 3h         | ✅      |
| 5A.6 | Worker config: `concurrency=2`, `task_time_limit=3600` (1h max), `task_soft_time_limit=3000`, `acks_late=True` (re-exec se worker crash)              | P0         | 2h         | ✅      |
| 5A.7 | Integrar needs_review (Fase 4): task retorna com status, `POST /api/pipeline/runs/{id}/resume` spawna nova Celery task a partir do stage paused       | P0         | 3h         | ✅      |
| 5A.8 | Health check: `GET /api/health` verifica Redis connectivity + Celery worker ping + DB connection                                                      | P1         | 2h         | ✅      |


**Checkpoint 5A:** Pipeline roda via Celery em vez de Thread. Events publicados no Redis. Resume após needs_review funciona.

---

#### Sub-fase 5B: WebSocket + Progress UI (Semana 1-2) ✅ CONCLUÍDA

**Objetivo:** Progresso em tempo real via WebSocket. Polling continua como fallback. UI mostra barra de progresso por stage.


| #    | Tarefa                                                                                                                                   | Prioridade | Estimativa | Status |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 5B.1 | FastAPI WebSocket endpoint: `WS /api/pipeline/runs/{id}/ws` — subscribe Redis Pub/Sub channel, forward JSON events para client           | P0         | 4h         | ✅      |
| 5B.2 | WebSocket auth: validar JWT no handshake (query param ou header). Rejeitar conexão se unauthorized                                       | P0         | 2h         | ✅      |
| 5B.3 | Polling fallback: `GET /api/pipeline/runs/{id}` mantido (Fase 2 compat). WS e polling coexistem, mesma fonte de verdade (DB)             | P0         | 1h         | ✅      |
| 5B.4 | Event schema: definir Pydantic models para events WS (`StageEvent`, `RunEvent`, `ErrorEvent`) com tipo, stage, progress%, timestamp      | P0         | 2h         | ✅      |
| 5B.5 | UI: barra de progresso com stages — current highlighted (pulsing), completed green ✓, failed red ✗, needs_review amber ⚠, skipped gray ⊘ | P0         | 5h         | ✅      |
| 5B.6 | UI: auto-connect WS quando pipeline em execução. Auto-reconnect com exponential backoff. Fallback para polling se WS falhar 3x           | P0         | 3h         | ✅      |
| 5B.7 | UI: notificação toast quando relatório pronto + badge no menu "Relatórios" + link direto para download/view                              | P1         | 3h         | ✅      |
| 5B.8 | UI: indicador de needs_review inline no progress — botão "Revisar" que abre a tela de review (Fase 4)                                    | P1         | 2h         | ✅      |


**Checkpoint 5B:** Progresso em tempo real via WS no browser. Barra de progresso visual com states por stage. Polling continua funcionando.

---

#### Sub-fase 5C: Concurrency + Cancelamento + Testes (Semana 2-3) ✅ CONCLUÍDA

**Objetivo:** Controle de concorrência, cancelamento stage-boundary, e testes de integração completos.


| #    | Tarefa                                                                                                                                  | Prioridade | Estimativa | Status |
| ---- | --------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 5C.1 | Concurrency limit: 1 pipeline run por workspace. Segundo run → 409 Conflict com `{ active_run_id, started_at }`                         | P0         | 2h         | ✅      |
| 5C.2 | Stage-boundary cancellation: `POST /api/pipeline/runs/{id}/cancel` → set flag no DB → task verifica entre stages → abort com cleanup    | P0         | 3h         | ✅      |
| 5C.3 | Cancelamento publica event `run_cancelled` via Redis + atualiza PipelineRun status. Stages já completos mantidos                        | P0         | 2h         | ✅      |
| 5C.4 | UI: botão "Cancelar" no progress tracker com confirmação ("Stages completos serão mantidos. Continuar?")                                | P0         | 2h         | ✅      |
| 5C.5 | Retry automático de stage falhada: config por stage (max_retries, quais errors são retryable). Default: 0 retries (explicit opt-in)     | P1         | 3h         | ✅      |
| 5C.6 | Testes de integração: task Celery processa pipeline E2E (mock LLM), events publicados, WS recebe corretamente                           | P0         | 4h         | ✅      |
| 5C.7 | Testes: concurrency (2º run rejeitado), cancelamento (stage-boundary funciona), resume após needs_review (nova task spawna), polling OK | P0         | 4h         | ✅      |


**Checkpoint 5C:** Concurrency controlado. Cancelamento funciona. Testes green para todos os fluxos.

---

#### Critérios de aceite da Fase 5 completa


| Critério                    | Verificação                                                                                        | Status |
| --------------------------- | -------------------------------------------------------------------------------------------------- | ------ |
| Pipeline via Celery         | `task.delay()` com fallback Thread se Redis indisponível. `celery_task_id` salvo no DB             | ✅      |
| Progresso real-time         | WebSocket recebe events stage-a-stage via Redis Pub/Sub. `usePipelineWS` hook no frontend          | ✅      |
| Polling funcional           | `GET /runs/{id}` continua retornando estado correto (backward compat com Fase 2/3/4)               | ✅      |
| WS resilience               | Desconexão WS → auto-reconnect (exponential backoff). Fallback para polling se WS falhar 3x        | ✅      |
| Concurrency limit           | 2º run no mesmo workspace → 409 Conflict. Já existia desde Fase 2, mantido                         | ✅      |
| Cancelamento stage-boundary | Cancel → seta status DB + revoke Celery task + publica `run_cancelled`. Stages anteriores mantidos | ✅      |
| needs_review + resume       | Validação falha → pipeline pausa → user edita → POST resume → nova Celery task spawna → continua   | ✅      |
| Worker resilience           | `acks_late=True` re-executa task se worker crash. Redis indisponível → fallback Thread             | ✅      |
| Health check                | `GET /api/health` reporta status de Redis, Celery worker, e DB                                     | ✅      |
| Per-stage retry             | `retry_config.py`: LLM stages 1-2 retries (timeout/rate_limit), det. stages 0 retries              | ✅      |
| Regressão zero              | Todos os flows das Fases 2/3/4 (upload, config, LLM, review) continuam funcionando                 | ✅      |


#### O que a Fase 5 NÃO faz (fica para fases posteriores)


| Escopo excluído                             | Por quê                                    | Fase destino |
| ------------------------------------------- | ------------------------------------------ | ------------ |
| Scheduled/recurring pipeline runs           | Requer CRON-like scheduler                 | Futuro       |
| Multi-worker scaling (horizontal)           | 1 worker suficiente para MVP               | Fase 7       |
| Flower dashboard (Celery monitoring)        | Nice-to-have para admin, não para user     | Fase 7       |
| Push notifications (mobile/email)           | Requer notification service                | Fase 6       |
| Sub-stage progress ("E3: 15/42 transações") | Requer instrumentar scripts internamente   | Futuro       |
| Priority queue (premium runs ahead of free) | Premature. 1 run per workspace já controla | Futuro       |


#### Dependências da Fase 5 (instaladas ✅)

```
# Novas dependências Python (backend/requirements.txt)
celery[redis]>=5.4.0  # Task queue + Redis broker/backend
redis>=5.0.0          # Redis client (Pub/Sub + cache)
websockets>=12.0      # WebSocket protocol support

# Novas dependências de infra (docker-compose.yml)
redis:7-alpine        # Docker Compose service (appendonly, healthcheck, maxmemory 256mb)

# Já disponíveis (Fases 0-4):
# fastapi (WebSocket support built-in), pydantic, sqlalchemy,
# litellm, instructor, cryptography, sonner (frontend toast)
```

---

### FASE 6 — Frontend Profissional (Core Data Experience)

**Objetivo:** Três capabilities que definem um produto financeiro profissional: (1) **Transaction Explorer** — visão detalhada com filtro, busca, drill-down e category override; (2) **Dashboard** — KPIs, charts interativos, alertas inteligentes; (3) **Report React interativo** — relatório reescrito como React components com data lineage e export. Dark mode. UI de LLM config + review manual (adiadas da Fase 4). Notification center. Responsive polish.

**Duração estimada:** 6 semanas (4 sub-fases)

**Nota estratégica:** A Fase 6 original (68 tasks, 8 semanas) foi refinada após análise executiva. Items de aquisição/marketing (landing page, PWA, onboarding wizard, guided tour, command palette, SEO, animations) foram diferidos para Fase 8/Futuro — prematuros para o estágio dogfood/beta do produto. O foco é solidificar a **core data experience** antes de polir a embalagem.

**Nota técnica:** 3 tasks de UI movidas da Fase 4D: configuração LLM (provider/API key/modelo/teste), indicador de tier (Free/Premium badges + lock icons), review manual (JSON editor com validação). Os endpoints de API já estão prontos (Fase 4).

#### Decisões tomadas para esta fase


| Decisão              | Escolha                                                         | Rationale                                                                                      |
| -------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Sub-fase ordering    | Transaction Explorer → Dashboard → Report → Polish              | TE é o target de drill-down; construí-lo primeiro evita dead-ends no Dashboard                 |
| Report rendering     | React components a partir do E5 JSON                            | Máximo controle, interatividade, dark mode, responsivo. Validação rigorosa garante paridade    |
| Dashboard scope      | KPIs + charts interativos + alertas inteligentes + date range   | Dashboard completo = valor premium visível. Alertas diferenciam de planilha                    |
| Transaction Explorer | DataTable com filtro, busca, drill-down, export CSV/XLSX        | Core feature para produto financeiro sério. Sem isso é "relatório gerador", não ferramenta     |
| Data lineage         | Tooltip simplificado (fonte do documento, data, confiança)      | Confiança = core de produto financeiro. Tooltip é P1, drill-down completo é futuro             |
| Reconciliation UI    | Category override inline + flag "revisado manualmente"          | Mínimo viável: user corrige categorização errada sem re-rodar pipeline inteiro                 |
| PDF export           | `@media print` CSS (MVP) + upgrade path Playwright              | `window.print()` é zero-cost e fiel ao browser. Playwright pesado para VPS $5-10 (Fase 7)      |
| Data export          | CSV/XLSX export de tabelas (transações, categorias, patrimônio) | Profissional financeiro precisa levar dados para planilha. Table-stakes para o público alvo    |
| Notification center  | In-app inbox com severidade + badge count no nav                | Alertas inteligentes precisam de persistência, não só toast efêmero                            |
| Chart library        | Recharts (React-native, declarativo, Tailwind-compatível)       | Popular, leve, bons defaults. Alternativa: Nivo/Tremor se Recharts limitar                     |
| Dark mode timing     | Implementar no início (6D.1), não no final                      | Tokens F4.5 já suportam. Novos componentes devem ser testados em ambos os modos desde o dia 1  |
| Pagination strategy  | Server-side (50/page) em vez de virtual scrolling               | Famílias típicas: 200-500 tx/mês. Paginação simples resolve; virtual scroll é over-engineering |
| Billing              | Adiar para Fase 7. BYOK (Fase 4) já diferencia tiers            | Sem billing no MVP. Stripe integration não é bloqueante                                        |
| Landing page / PWA   | **Diferidos para Fase 8**                                       | Prematuros para dogfood. Zero usuários externos = zero ROI em aquisição                        |
| Onboarding wizard    | **Diferido para Fase 8**                                        | Sem user research para validar o fluxo. Desenhar após observar beta users                      |
| Command palette      | **Diferido para Fase 8**                                        | Power-user feature. Nice-to-have, não essencial para core experience                           |


#### Estratégia de validação do Report React

A reescrita do relatório como React components é a tarefa de maior risco desta fase. O HTML original (E6) é a referência de correção. A validação tem 2 camadas automatizadas + 1 manual:

```
Camada 1 — Data Accuracy (unitário, automatizado):
  Para CADA número exibido no React report:
    assert rendered_value == E5_JSON[path_to_value]
  Cobertura: 100% dos valores monetários, percentuais, scores, contagens.
  → Gate de CI: falha bloqueia merge.

Camada 2 — Section Completeness (integração, automatizado):
  Para CADA seção do HTML original:
    assert React_report.has_section(section_name)
    assert section.has_all_subsections()
  Cobertura: todas as seções do E6 template mapeadas para React components.
  → Gate de CI: falha bloqueia merge.

Camada 3 — Visual Spot-Check (manual, periódico):
  Abrir HTML original e React report lado a lado (mesmos dados E5).
  Verificar visualmente que layout, hierarquia, e dados estão coerentes.
  → NÃO é gate automatizado. Screenshot diff pixel-a-pixel é frágil
    (font rendering, viewport, anti-aliasing geram falsos positivos).
```

> **Regra:** Nenhum número pode divergir entre React report e E5 JSON source. Divergência = bug bloqueante.

---

#### Sub-fase 6A: Transaction Explorer + Data APIs (Semana 1-2)

**Objetivo:** Camada de dados transacionais + UI de exploração detalhada. É a **fundação** que o Dashboard (6B) e o Report (6C) consomem via drill-down. Category override inline para correção manual de categorização.

**Por que Transaction Explorer primeiro:** O Dashboard cria drill-downs ("click para ver detalhes") que precisam aterrissar no Transaction Explorer. Construí-lo primeiro evita dead-ends durante semanas. Além disso, a API de transações (`GET /api/transactions`) é reutilizada pelo Dashboard e pelo Report.


| #     | Tarefa                                                                                                                                                                          | Prioridade | Estimativa | Status |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 6A.1  | API: `GET /api/transactions` — lista transações do último E4 unificado + E3 reconciliado. Filtros: membro, banco, categoria, período (date range), valor min/max, busca texto   | P0         | 5h         | ☐      |
| 6A.2  | API: `POST /api/transactions/{id}/override` — permite override de categoria e notas. Flag "revisado manualmente". Overrides persistem entre pipeline runs (salvo no DB)         | P0         | 4h         | ☐      |
| 6A.3  | `<DataTable>` component reutilizável: sobre shadcn `Table`, com sorting por coluna, header sticky, row selection (checkbox). Genérico para uso em Transaction Explorer e Report | P0         | 5h         | ☐      |
| 6A.4  | Transaction Explorer page: `DataTable` com colunas: data, descrição, categoria (badge), valor (formatado + cor gain/loss), membro, banco, origem                                | P0         | 5h         | ☐      |
| 6A.5  | Filtros avançados: panel lateral com `DateRangePicker` (date-fns), multi-select de membros, multi-select de bancos, multi-select de categorias, range de valores                | P0         | 5h         | ☐      |
| 6A.6  | Busca full-text: input de busca filtra por descrição da transação. Highlight do match no resultado. Debounce 300ms                                                              | P0         | 3h         | ☐      |
| 6A.7  | Summary bar: acima da tabela — total filtrado (receitas, despesas, saldo), número de transações, período coberto. Atualiza em tempo real com filtros                            | P0         | 3h         | ☐      |
| 6A.8  | Category override inline: click na categoria de uma transação → popover com select de categorias disponíveis. Override salvo via API (6A.2). Badge "editado" na célula          | P0         | 4h         | ☐      |
| 6A.9  | CSV/XLSX export: botão exporta transações filtradas como CSV ou XLSX. Inclui todas as colunas + formatação de valores                                                           | P0         | 3h         | ☐      |
| 6A.10 | URL state: filtros persistem na URL (query params). Link direto para uma busca/filtro específico. Compatível com drill-down do Dashboard (6B.12)                                | P0         | 2h         | ☐      |
| 6A.11 | Transaction detail panel: click na row → Sheet lateral com detalhes: fonte (documento), método de extração (det/LLM), reconciliação, notas user                                 | P1         | 4h         | ☐      |
| 6A.12 | Server-side pagination: 50 rows/page com cursor-based pagination. Total count no response. UI com page controls                                                                 | P0         | 3h         | ☐      |


**Checkpoint 6A:** Transaction Explorer funcional com filtros avançados, busca, category override inline, export CSV/XLSX, paginação server-side, URL state para drill-down. API de transações pronta para consumo pelo Dashboard.

---

#### Sub-fase 6B: Dashboard + KPIs + Charts (Semana 2-3)

**Objetivo:** Dashboard com KPIs, charts interativos, alertas inteligentes, filtros por período/membro. Drill-downs aterrissam no Transaction Explorer (6A, já funcional).


| #     | Tarefa                                                                                                                                        | Prioridade | Estimativa | Status |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 6B.1  | Setup Recharts + base chart components reutilizáveis (LineChart, BarChart, PieChart, AreaChart) com tema do design system (Fase 4.5 tokens)   | P0         | 4h         | ☐      |
| 6B.2  | API: `GET /api/dashboard/{workspace_id}` — agrega KPIs + chart data + alerts do último E5 analysis. Sem cache (prematuro para 1 user)         | P0         | 4h         | ☐      |
| 6B.3  | Dashboard page layout: grid responsivo com cards KPI (topo), charts (meio), alertas (lateral/bottom). `DateRangePicker` no header             | P0         | 4h         | ☐      |
| 6B.4  | KPI cards (usando `KPICard` da F4.5): score financeiro (gauge), patrimônio líquido, taxa poupança, receita vs despesa (com `<Delta>`)         | P0         | 4h         | ☐      |
| 6B.5  | Chart: evolução patrimonial mensal (AreaChart, com breakdown por tipo: imóveis, investimentos, conta corrente)                                | P0         | 4h         | ☐      |
| 6B.6  | Chart: distribuição de despesas por categoria (PieChart/Donut, click → navega para Transaction Explorer com filtro pré-aplicado)              | P0         | 4h         | ☐      |
| 6B.7  | Chart: fluxo mensal receitas vs despesas (BarChart stacked, com linha de saldo acumulado)                                                     | P0         | 4h         | ☐      |
| 6B.8  | Chart: composição de investimentos por tipo (TreeMap ou StackedBar — CDB, ações, fundos, poupança)                                            | P1         | 3h         | ☐      |
| 6B.9  | Alertas inteligentes: backend service analisa E5 JSON → gera alerts (gastos > teto, score Δ negativo, meta em risco, concentração)            | P0         | 5h         | ☐      |
| 6B.10 | Filtro por membro: select no dashboard header filtra todos os KPIs e charts por membro da família (ou "Todos"). Persiste em URL query param   | P0         | 3h         | ☐      |
| 6B.11 | Data freshness indicator: banner/badge mostrando "Dados atualizados em DD/MMM/AAAA HH:mm" + alerta se dados > 30 dias defasados               | P0         | 2h         | ☐      |
| 6B.12 | Drill-down universal: click em qualquer número/barra do chart → navega para Transaction Explorer com filtro pré-aplicado (categoria, período) | P0         | 4h         | ☐      |


**Checkpoint 6B:** Dashboard funcional com 4+ charts, KPIs com deltas, alertas inteligentes, filtros por período/membro, data freshness. Drill-down conecta ao Transaction Explorer (6A).

---

#### Sub-fase 6C: Report React Interativo + History + Export (Semana 3-5)

**Objetivo:** Relatório reescrito como React components **interativos** com validação rigorosa (L1+L2), data lineage, histórico. PDF via `@media print` (MVP). CSV/XLSX export por seção. É a tarefa de maior risco da fase — maior superfície de implementação.


| #     | Tarefa                                                                                                                                                     | Prioridade | Estimativa | Status |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 6C.1  | Definir component tree do relatório: mapear cada seção do E6 HTML para um React component. Criar skeleton da árvore com types                              | P0         | 3h         | ☐      |
| 6C.2  | Implementar section components: Summary, Score, Patrimônio, Receitas, Despesas, Fluxo Mensal, Investimentos, Categorias                                    | P0         | 14h        | ☐      |
| 6C.3  | Implementar section components: Life Plan, Review (E7), Notas, Disclaimer — com conditional rendering (review só se premium)                               | P0         | 6h         | ☐      |
| 6C.4  | Report page: navegação por seções (sidebar TOC), scroll suave, accordion expand/collapse por seção                                                         | P0         | 4h         | ☐      |
| 6C.5  | **Validação L1 — Data Accuracy:** testes unitários para cada component, assert valor renderizado == E5 JSON source (100% dos números). CI gate             | P0         | 6h         | ☐      |
| 6C.6  | **Validação L2 — Section Completeness:** teste que verifica existência de todos os sections do E6 template no React tree. CI gate                          | P0         | 3h         | ☐      |
| 6C.7  | Report history: API `GET /api/reports` (list completed pipeline runs com summary: date, score, patrimônio) + UI list view com card preview                 | P0         | 4h         | ☐      |
| 6C.8  | PDF export: `@media print` CSS + botão "Exportar PDF" que chama `window.print()`. Header/footer com data e título via CSS print. Upgrade path → Playwright | P0         | 3h         | ☐      |
| 6C.9  | **CSV/XLSX export por seção:** botão "Exportar" em cada tabela do relatório → download CSV/XLSX com headers formatados (client-side via `xlsx` lib)        | P0         | 4h         | ☐      |
| 6C.10 | **Data lineage tooltips:** `<SourceTooltip>` em valores monetários — mostra: documento fonte, banco, data extração, método (det/LLM). Tooltip shadcn       | P1         | 5h         | ☐      |
| 6C.11 | **Filtro por membro no relatório:** toggle no header do report filtra todas as seções (despesas, receitas, patrimônio) por membro selecionado              | P1         | 4h         | ☐      |
| 6C.12 | `<DateRangePicker>` component: sobre shadcn popover + date-fns. Reutilizado no Dashboard (6B) e Transaction Explorer (6A). Locale pt-BR                    | P0         | 3h         | ☐      |


**Checkpoint 6C:** Relatório React interativo completo. Validação L1+L2 green no CI. Data lineage em valores monetários. CSV/XLSX export por seção. PDF via print. Histórico de relatórios.

---

#### Sub-fase 6D: UX Polish + Deferred UI + Dark Mode (Semana 5-6)

**Objetivo:** Dark mode (desde o início da sub-fase para testar todos os novos componentes). UI de LLM config + review manual (adiadas da Fase 4). Notification center. Loading/empty/error states polished. Navigation architecture atualizada com Dashboard e Transaction Explorer. Responsive adjustments.


| #     | Tarefa                                                                                                                                                                                                               | Prioridade | Estimativa | Status |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 6D.1  | Dark mode: toggle no header (`.dark` class no `<html>`), persist localStorage, `prefers-color-scheme` auto-detect. Verificar todos os componentes F6 em dark                                                         | P0         | 3h         | ☐      |
| 6D.2  | Navigation architecture: Dashboard como home (redirect `/` → `/dashboard`), adicionar "Transações" à sidebar. Reordenar: Dashboard, Documentos, Pipeline, Transações, Relatórios, Config (absorve Vault como subtab) | P0         | 3h         | ☐      |
| 6D.3  | **LLM config UI:** página em Config tabs — provider select, API key (masked input), modelo (text), botão "Testar conexão". Usa endpoints F4 existentes                                                               | P0         | 4h         | ☐      |
| 6D.4  | **Tier indicators:** badge "Free" / "Premium" no sidebar/header. Lock icons em features LLM-only. Upsell sutil ("Configure uma API key para desbloquear")                                                            | P0         | 3h         | ☐      |
| 6D.5  | **Manual review UI:** quando pipeline pausa em needs_review → tela com JSON viewer (read-only), campos editáveis para correções, botão "Aprovar e continuar"                                                         | P0         | 5h         | ☐      |
| 6D.6  | Loading states: skeleton screens para Dashboard (cards + charts), Report (seções pulsing), Transaction Explorer (table rows). Usando `<Skeleton>` shadcn                                                             | P0         | 3h         | ☐      |
| 6D.7  | Empty states: `<EmptyState>` (F4.5) em Dashboard, Transaction Explorer, Reports quando sem dados + CTA contextual ("Execute o pipeline primeiro")                                                                    | P0         | 2h         | ☐      |
| 6D.8  | Error handling polish: mensagens user-friendly por tipo de erro (network, validation, pipeline failure, auth, LLM quota). Botão retry quando aplicável                                                               | P0         | 3h         | ☐      |
| 6D.9  | **Notification center:** bell icon no header com badge count. Inbox in-app: alertas inteligentes (6B.9) persistem. Marca como lida. Severidade visual                                                                | P0         | 5h         | ☐      |
| 6D.10 | API: `GET/PATCH /api/notifications` — list notifications por workspace, mark as read, filtro por severidade (info/warning/critical). Backend gera via alerts                                                         | P0         | 4h         | ☐      |
| 6D.11 | Responsive adjustments: charts resize em mobile, sidebar collapse no mobile (Sheet), touch-friendly buttons (44px+ tap target), tables com `overflow-x-auto`                                                         | P0         | 4h         | ☐      |
| 6D.12 | Accessibility pass: ARIA labels nos interactive elements novos (charts, filters, category override), keyboard nav (Tab, Enter, Escape), focus management                                                             | P0         | 4h         | ☐      |


**Checkpoint 6D:** Dark mode funcional em todas as páginas. LLM config + review manual UI completas. Notification center. Tier indicators. Loading/empty/error states em toda página. Mobile usável. Accessibility pass.

---

#### Critérios de aceite da Fase 6 completa


| Critério              | Verificação                                                                                                     |
| --------------------- | --------------------------------------------------------------------------------------------------------------- |
| Transaction Explorer  | Tabela com filtros avançados, busca full-text, category override inline, export CSV/XLSX, paginação server-side |
| Drill-down funcional  | Click em chart do Dashboard → Transaction Explorer com filtro pré-aplicado. URL state preserva filtros          |
| Dashboard funcional   | KPIs, 4+ charts interativos, alertas inteligentes, filtro por membro/período, data freshness                    |
| Report React fiel     | L1 (data accuracy): 100% dos números conferem com E5 JSON. L2: todas as seções do E6 mapeadas. CI gates green   |
| Report interativo     | Accordion por seção, filtro por membro, data lineage tooltips, CSV/XLSX por seção                               |
| PDF export            | `@media print` funcional — botão "Exportar PDF" gera PDF fiel ao que user vê no browser                         |
| Report history        | Lista de relatórios anteriores com preview (date, score, patrimônio)                                            |
| LLM config UI         | Config de provider/API key/modelo funcional. Teste de conexão. Tier badge (Free/Premium)                        |
| Manual review UI      | Pipeline pausa em needs_review → tela de review com JSON viewer + campos editáveis → "Aprovar e continuar"      |
| Notification center   | In-app inbox (bell icon + badge). Alertas persistem. Severidade visual. Mark as read                            |
| Category override     | Click em categoria no TE → select → override salvo no DB. Badge "editado manualmente". Persiste entre runs      |
| Empty states          | Dashboard, TE, Reports, Vault têm `<EmptyState>` informativo + CTA quando sem dados                             |
| Error handling        | Erros mostram mensagem user-friendly + ação sugerida por tipo (network, auth, LLM, pipeline)                    |
| Dark mode             | Toggle funcional, persiste, respeita OS preference. Todos os components adaptados (design tokens)               |
| Responsive            | Dashboard, report, TE usáveis em mobile (320px+). Sidebar collapse. Charts resize. Touch-friendly (44px+)       |
| Navigation atualizada | Dashboard como home. Sidebar: Dashboard, Docs, Pipeline, Transações, Relatórios, Config. Vault absorvido        |
| Regressão zero        | Funcionalidades das Fases 2-5 (upload, config, LLM, pipeline, WS progress) continuam funcionando                |


#### O que a Fase 6 NÃO faz (diferido para Fase 7 / 8 / Futuro)


| Escopo excluído                                  | Por quê                                                                            | Fase destino |
| ------------------------------------------------ | ---------------------------------------------------------------------------------- | ------------ |
| Landing page (hero, features, pricing, CTA)      | Prematuro: zero usuários externos. ROI de aquisição é zero no dogfood              | Fase 8       |
| Onboarding wizard + guided tour                  | Sem user research para validar fluxo. Desenhar após observar beta users            | Fase 8       |
| PWA (manifest, service worker, offline, install) | Prematuro para dogfood. PWA offline com dados financeiros tem implicações security | Fase 8       |
| Command palette (Cmd+K, cmdk)                    | Power-user feature, nice-to-have. Não essencial para core experience               | Fase 8       |
| Framer Motion animations / page transitions      | Polish visual sem valor funcional. `prefers-reduced-motion` requer cuidado         | Fase 8       |
| SEO / Open Graph / sitemap / robots.txt          | Sem landing page, sem SEO relevante                                                | Fase 8       |
| Keyboard shortcuts (G+D, G+R, etc.)              | Power-user feature. Depende de command palette                                     | Fase 8       |
| FAQ page / documentation                         | Prematuro. Conteúdo emerge do feedback de beta users                               | Fase 8       |
| Report comparison (side-by-side, deltas)         | Requer 2+ relatórios. No dogfood, pode demorar meses para ter dados                | Fase 8       |
| Shareable report link (token público + TTL)      | Implicações de segurança (LGPD, dados financeiros públicos). Complexo para 4h      | Fase 7       |
| Config audit log (who/when/what changed)         | Feature de auditoria, melhor na Fase 7 (LGPD/compliance)                           | Fase 7       |
| Bulk transaction actions (batch recategorize)    | Nice-to-have. Category override individual suficiente para MVP                     | Fase 8       |
| Screen reader testing (VoiceOver/NVDA)           | Accessibility pass (6D.12) cobre ARIA. Testing dedicado após beta                  | Fase 7       |
| Performance audit (Lighthouse >90)               | Relevante para produção, não para dogfood/dev                                      | Fase 7       |
| Billing / pagamento real (Stripe)                | BYOK resolve tier. Billing complexo, adiar                                         | Fase 7       |
| Email notifications (digest semanal/mensal)      | Requer email service + templates + unsubscribe                                     | Fase 7       |
| Demo mode (dados fictícios sem registro)         | Importante para conversão, não bloqueante para beta                                | Fase 7       |
| Relatório editável (custom sections)             | Escopo de personalização avançada                                                  | Futuro       |
| Dashboard widgets customizáveis (drag-and-drop)  | Over-engineering para MVP                                                          | Futuro       |
| Multi-idioma (i18n)                              | pt-BR por default. i18n é esforço grande                                           | Futuro       |
| Collaborative features (share, comments)         | Multi-user por workspace é futuro                                                  | Futuro       |
| Full data lineage drill-down (→documento→página) | Tooltip simplificado (6C.10) é suficiente. Drill-down full é complexo              | Futuro       |
| Full reconciliation UI (resolver conflitos E3)   | Category override (6A.8) é o mínimo viável. Reconciliação full é projeto à parte   | Futuro       |
| Budget planning / goal tracking UI               | Requer modelo de dados dedicado. Life plan já existe no relatório                  | Futuro       |
| Redis cache no Dashboard API                     | Prematuro para 1 user. Adicionar quando houver latência perceptível                | Futuro       |


#### Dependências da Fase 6

```
# Novas dependências Frontend (npm)
recharts              # Charts React (LineChart, BarChart, PieChart, AreaChart, TreeMap)
date-fns              # Date formatting + manipulation (locale pt-BR) — DateRangePicker, comparações
xlsx                  # Client-side XLSX export (transações, seções do relatório)

# Já instalados na Fase 4.5:
# lucide-react, shadcn/ui, class-variance-authority, clsx, tailwind-merge, tw-animate-css

# Novas dependências Backend (pip)
# (nenhuma — PDF via @media print, não Playwright)

# Já disponíveis (Fases 0-5):
# next.js, react, tailwindcss, typescript (frontend)
# fastapi, pydantic, sqlalchemy, celery, redis (backend)

# Diferidas para Fase 8:
# cmdk (command palette), framer-motion (animations), @serwist/next (PWA — substitui next-pwa deprecated)
```

---

### FASE 6.5 — Frontend Testing & Quality Assurance

**Objetivo:** Estabelecer a rede de segurança de testes do frontend antes de ir para produção. Validar que todas as 10 páginas, 25+ componentes, 30+ chamadas de API, e fluxos críticos (upload→pipeline→report) funcionam corretamente. A Fase 6 entrega features; a 6.5 entrega confiança.

**Duração estimada:** 2 semanas (3 sub-fases)

**Princípio norteador:** *Sem testes, ir para produção é chutar no escuro.* O Fin processa dados financeiros reais — um número errado no relatório, um upload que falha silenciosamente, ou um pipeline que trava sem feedback destrói a confiança do usuário. A 6.5 existe para que a Fase 7 (deploy) comece com gates automatizados, não com fé.

**Por que entre F6 e F7 (e não dentro da F7):** A Fase 7 original incluía setup de testes frontend (7D.4-7D.6) misturado com Docker, LGPD, CI/CD, e dogfood. Isso criava três problemas: (1) testes ficavam no final do critical path do launch, (2) pressão de "ship" jogava testes para P2, (3) bugs de frontend descobertos em produção custam 10x mais que em dev. Separar em fase própria garante que testes são pré-requisito do deploy, não afterthought.

**Superfície a testar:** 10 páginas, 25 componentes, 30+ API functions em `api.ts`, 9 formatters em `format.ts`, 1 WebSocket hook, 2 export utilities, dark mode, responsive, auth gate.

#### Decisões tomadas para esta fase


| Decisão              | Escolha                                                                         | Rationale                                                                                                  |
| -------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Test runner           | **Vitest** (unit + integration)                                                 | Mesma config Vite/Next.js. 10-50x mais rápido que Jest. ESM nativo. Compatible com RTL                    |
| Component testing     | **React Testing Library (RTL)**                                                 | Testa comportamento (user vê/clica), não implementação. Standard do ecossistema                            |
| API mocking           | **MSW (Mock Service Worker)**                                                   | Intercepta fetch real (não mock de módulo). Fixtures reutilizáveis. Funciona em unit + integration          |
| E2E framework         | **Playwright**                                                                  | Multi-browser, auto-wait, network interception, WebSocket support. Melhor DX que Cypress para Next.js      |
| E2E scope             | **3 fluxos críticos** (não cobertura total)                                     | ROI máximo: register→report, config→rerun, vault→unlock. Cobertura breadth via L2 integration tests       |
| Mock vs real backend  | **MSW para L1/L2, backend real para L3**                                        | L1/L2 rápidos e isolados. L3 E2E valida integração real (CORS, auth, WebSocket)                           |
| Coverage target       | **≥80% line em lib/ + components/, ≥70% line em pages/**                        | lib/ tem lógica pura (alto ROI). Pages têm muito boilerplate de layout (menor ROI)                        |
| Fixture strategy      | **Fixtures geradas a partir do OpenAPI schema do FastAPI**                       | Evita mock drift (MSW retorna o que o backend real retornaria). Atualizável automaticamente                |
| CI integration        | **Vitest no pre-commit hook, Playwright no CI pipeline**                        | Unit/integration: feedback em <30s. E2E: roda em CI (lento demais para pre-commit)                        |
| Smoke test            | **Checklist markdown (`docs/SMOKE_TEST.md`)**                                   | Formaliza o que já fazemos manualmente. Gate humano antes de cada deploy                                   |


#### Estratégia: Pirâmide de Testes em 4 Camadas

```
┌─────────────────────────────────────────────────────────┐
│  L4: Smoke Test Manual (Dogfood Checklist)              │  ← Confiança final (5-10 min)
│  docs/SMOKE_TEST.md — antes de cada deploy              │
├─────────────────────────────────────────────────────────┤
│  L3: E2E Automated (Playwright)                         │  ← Fluxos críticos (~30 tests)
│  Login → Upload → Pipeline → Report → Export            │  ← CI gate (bloqueia deploy)
├─────────────────────────────────────────────────────────┤
│  L2: Integration Tests (Vitest + RTL + MSW)             │  ← API contracts (~150 tests)
│  Cada page monta, chama API mockada, renderiza correto  │  ← CI gate (bloqueia merge)
├─────────────────────────────────────────────────────────┤
│  L1: Unit Tests (Vitest)                                │  ← Lógica pura (~60 tests)
│  format.ts, export.ts, utils.ts, api.ts, hooks          │  ← Pre-commit hook (<5s)
└─────────────────────────────────────────────────────────┘
```

> **Regra:** Cada camada pega classes de bugs que a camada abaixo não pega. L1 pega `formatCurrency(1234.56) === "R$ 1.234,56"`. L2 pega "Dashboard renderiza Skeleton quando loading". L3 pega "upload real falha por CORS". L4 pega "dark mode torna texto ilegível na página X".

---

#### Sub-fase 6.5A: Tooling Setup + Unit Tests (Semana 1, dias 1-3)

**Objetivo:** Infraestrutura de testes configurada + unit tests das funções puras. É o alicerce — sem isso, as sub-fases seguintes não começam.


| #      | Tarefa                                                                                                                                                     | Prioridade | Estimativa | Status |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 6.5A.1 | Setup Vitest: `vitest.config.ts` com `jsdom` environment, path aliases (`@/`), coverage provider (`v8`). `frontend/tests/setup.ts` com RTL cleanup         | P0         | 2h         | ☐      |
| 6.5A.2 | Setup MSW: `frontend/tests/mocks/server.ts` + `handlers.ts` com handlers default para auth, documents, pipeline, config. Fixtures JSON em `tests/fixtures/` | P0         | 3h         | ☐      |
| 6.5A.3 | Unit tests `format.ts`: 9 formatters × 3-5 cases cada. Foco: `formatCurrency` (BRL negativo, zero, milhões), `formatPercent` (0-100, >100), `formatDelta` (positivo/negativo/zero), `formatCompact`, `formatPeriod`, `formatMonth`, `formatRange`. 3 status maps (`docStatusLabel`, `runStatusLabel`, `stageStatusLabel`) com todos os enum values | P0 | 4h | ☐ |
| 6.5A.4 | Unit tests `export.ts`: `exportToCSV` (array vazio, acentos, vírgulas em valores, BOM UTF-8), `exportToXLSX` (colunas auto-width, números grandes). Mock de `document.createElement('a')` + `URL.createObjectURL` | P0 | 2h | ☐ |
| 6.5A.5 | Unit tests `api.ts`: token management (`setToken`/`getToken`/`clearToken`), `apiFetch` (adiciona Bearer, retorna JSON, lança ApiError em 4xx/5xx, redirect em 401) | P0 | 3h | ☐ |
| 6.5A.6 | Unit tests `utils.ts`: `cn()` merge de classes conflitantes Tailwind (`cn("p-4", "p-2")` → `"p-2"`) | P0 | 1h | ☐ |
| 6.5A.7 | Unit tests `usePipelineWS.ts`: hook de WebSocket (connect, receive event, reconnect backoff, cleanup on unmount). Mock de `WebSocket` global | P1 | 3h | ☐ |
| 6.5A.8 | Coverage baseline: rodar `vitest run --coverage` e documentar números iniciais. Configurar thresholds em `vitest.config.ts` (lib/ ≥80%, fail on decrease) | P0 | 1h | ☐ |


**Checkpoint 6.5A:** Vitest + MSW configurados. ~50-60 unit tests green. Coverage baseline documentada. `npm test` funciona. Funções de formatação financeira validadas (zero risco de "R$ errado" no relatório).

---

#### Sub-fase 6.5B: Integration Tests — Pages + Components (Semana 1 dia 3 — Semana 2 dia 2)

**Objetivo:** Cada página renderiza corretamente com dados mockados. Verifica estados (loading, empty, error, success), chamadas de API, e interações do usuário. É a camada de maior ROI — pega bugs de render, estados quebrados, e contratos de API desalinhados.


| #      | Tarefa                                                                                                                                                                                        | Prioridade | Estimativa | Status |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 6.5B.1 | Tests Login/Register: render form, submit success (→redirect), credenciais inválidas (→error msg), servidor offline (→connection error), loading state (→Spinner + botão desabilitado)         | P0         | 3h         | ☐      |
| 6.5B.2 | Tests Dashboard: com dados (KPIs renderizam valores, charts renderizam), sem dados (→EmptyState + link /pipeline), erro API (→EmptyState variant error + retry), loading (→Skeletons), drill-down (click chart →router.push /transactions com filtro), refresh button                          | P0 | 4h | ☐ |
| 6.5B.3 | Tests Documents: lista vazia (→EmptyState), upload drag-and-drop (dragOver state + uploadDocuments chamado), upload progress (barra atualiza), doc needs_password (→banner + link /vault), delete (→ConfirmDialog + deleteDocument), CTA pipeline (aparece quando docs "ready")                 | P0 | 4h | ☐ |
| 6.5B.4 | Tests Pipeline: trigger (→triggerPipeline chamado + activeRun aparece), WS progress (evento stage_completed →barra avança), needs_review (→banner review), cancel (→ConfirmDialog + cancelPipelineRun), completed (→toast + link /reports), failed (→toast erro), history list com status badges | P0 | 5h | ☐ |
| 6.5B.5 | Tests Transactions: render com dados (tabela + summary bar), busca text (→debounce 300ms →URL query →API re-chamada), category override (→select →overrideTransactionCategory), export CSV/XLSX (→download), paginação (page controls), empty filtrado (→EmptyState contextual), URL state (filtros persistem) | P0 | 5h | ☐ |
| 6.5B.6 | Tests Reports List + Viewer: lista com cards (data, score), empty (→EmptyState), click card (→/reports/[id]). Viewer: iframe carrega, TOC toggle, print button (→window.print), download HTML, export tables, auth failure (→redirect /login)                                                  | P0 | 4h | ☐ |
| 6.5B.7 | Tests Config — 6 tabs: Members (CRUD + bank accounts), Categories (CRUD + keywords), Pipeline (GET/PUT JSON), LLM (provider/key/test/tier), Institutions (GET/PUT), ReportLayout (GET/PUT), Import/Export (download + upload + preview)                                                        | P0 | 5h | ☐ |
| 6.5B.8 | Tests Vault: CRUD passwords, retry unlock, link /documents                                                                                                                                     | P0         | 2h         | ☐      |
| 6.5B.9 | Tests AppShell: auth gate (`getMe` fail →redirect /login), navigation (todos os items clicáveis, active state), mobile (hamburger →Sheet), logout (limpa token →redirect), NotificationCenter (bell badge + polling)                                                                           | P0 | 3h | ☐ |
| 6.5B.10 | Tests componentes compostos: `KPICard` (loading/loaded/delta), `EmptyState` (4 variants), `StatusBadge` (todos os statuses), `ConfirmDialog` (open/confirm/cancel), `Delta` (positivo/negativo/zero), `Spinner` (sizes), `ThemeToggle` (cycle), `DataTable` (sort + skeleton)                 | P1 | 3h | ☐ |
| 6.5B.11 | Tests dark mode: componentes renderizam sem texto ilegível em `class="dark"`. Foco nos 7 compostos + Dashboard charts + Transaction table. Snapshot visual opcional                             | P1         | 2h         | ☐      |


**Checkpoint 6.5B:** ~120-150 integration tests green. Todas as 10 pages testadas (loading, empty, error, success). Contratos de API validados via MSW. Interações do usuário (click, submit, drag) cobertas. Componentes compostos testados em isolamento. `npm test` <30s.

---

#### Sub-fase 6.5C: E2E Tests + Smoke Checklist (Semana 2, dias 2-5)

**Objetivo:** Validar fluxos end-to-end com backend real. Captura bugs de integração (CORS, auth flow, WebSocket, uploads reais) que unit/integration tests não pegam. Formalizar smoke test manual.


| #      | Tarefa                                                                                                                                                                                                                                    | Prioridade | Estimativa | Status |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 6.5C.1 | Setup Playwright: `playwright.config.ts` com `webServer` (start backend + frontend), `baseURL`, screenshots on failure, 3 retries. `frontend/e2e/` folder. Auth helper (login programático via API, não via UI a cada teste)                | P0         | 3h         | ☐      |
| 6.5C.2 | **E2E Fluxo 1 — Onboarding completo:** navega /register →preenche form →submit →redirect /documents →sidebar visível →navega /dashboard →KPIs ou EmptyState presente                                                                     | P0         | 3h         | ☐      |
| 6.5C.3 | **E2E Fluxo 2 — Upload → Pipeline → Report:** login →/documents →upload 2 PDFs →docs na tabela com status →/pipeline →trigger →progresso avança (WS ou polling) →status completed →/reports →card aparece →click →iframe com HTML →print | P0         | 5h         | ☐      |
| 6.5C.4 | **E2E Fluxo 3 — Config round-trip:** login →/config →tab Membros →criar membro →verificar na lista →tab Categorias →criar categoria →tab Import/Export →export JSON →verificar membro no JSON                                            | P0         | 3h         | ☐      |
| 6.5C.5 | **E2E Fluxo 4 — Vault + Unlock:** login →/vault →criar senha →verificar na lista (masked) →/documents →upload PDF protegido →status needs_password →retry unlock →status muda para ready                                                 | P1         | 3h         | ☐      |
| 6.5C.6 | **E2E Fluxo 5 — Drill-down Dashboard → Transactions:** login (com pipeline executado) →/dashboard →click barra gráfico →redirect /transactions com filtro →summary bar com totais →busca texto →tabela filtra →export XLSX               | P1         | 3h         | ☐      |
| 6.5C.7 | **E2E Fluxo 6 — Dark mode persistência:** login →toggle dark →verificar `<html class="dark">` →navegar 3 páginas →todas em dark →refresh →persiste →toggle light →verificar                                                              | P0         | 2h         | ☐      |
| 6.5C.8 | **E2E Fluxo 7 — Error handling e auth:** acessa /dashboard sem login →redirect /login →login com credenciais erradas →erro →login correto →funciona →clear token manual →próxima API →redirect /login                                    | P0         | 2h         | ☐      |
| 6.5C.9 | **E2E Fluxo 8 — Notifications:** login (com alertas) →bell icon com badge →click bell →Sheet com lista →mark as read →badge decrementa                                                                                                   | P1         | 2h         | ☐      |
| 6.5C.10 | Smoke test checklist: criar `docs/SMOKE_TEST.md` com 30+ checks organizados por seção (Auth, Documents, Pipeline, Dashboard, Transactions, Reports, Config, Dark Mode, Mobile, Notifications). Formato checkbox para execução manual       | P0 | 2h | ☐ |
| 6.5C.11 | CI integration: Playwright no GitHub Actions (com services: PostgreSQL + Redis). Artifacts: screenshots de falha, traces, video. Gate: E2E green → permite deploy                                                                          | P0         | 3h         | ☐      |


**Checkpoint 6.5C:** ~25-30 E2E tests green cobrindo 8 fluxos críticos. Smoke test checklist formalizado. CI pipeline configurado com Playwright. Screenshots de falha como artifacts. **Frontend tem rede de segurança completa para ir à produção.**

---

#### Critérios de aceite da Fase 6.5 completa


| Critério                         | Verificação                                                                                                         |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Unit tests green                 | ~50-60 tests em `format.ts`, `export.ts`, `api.ts`, `utils.ts`, `usePipelineWS.ts`. `npm test` <5s                 |
| Integration tests green          | ~120-150 tests. Todas as 10 pages + AppShell + 7 compostos testados (loading/empty/error/success)                   |
| E2E tests green                  | ~25-30 tests. 8 fluxos críticos passando com backend real. Screenshots on failure                                   |
| Coverage lib/ ≥80%               | `format.ts`, `export.ts`, `api.ts`, `utils.ts` com ≥80% line coverage                                              |
| Coverage pages/ ≥70%             | Todas as 10 pages com ≥70% line coverage (loading + empty + error + success paths)                                  |
| Smoke test formalizado           | `docs/SMOKE_TEST.md` com 30+ checks executáveis. Gate manual pré-deploy                                            |
| CI pipeline                      | Vitest no CI (bloqueia merge). Playwright no CI (bloqueia deploy). Artifacts de falha                               |
| MSW fixtures atualizadas         | Fixtures baseadas no OpenAPI schema do FastAPI. Nenhum mock drift evidente                                          |
| Zero regressão                   | Funcionalidades das Fases 2-6 continuam funcionando. `next build` green. `tsc --noEmit` green                       |
| Dark mode testado                | Componentes renderizam corretamente em `class="dark"`. E2E valida persistência                                      |
| Mobile testado (E2E)             | Pelo menos 1 fluxo E2E roda em viewport 375px (sidebar collapse, tabelas scrollam, touch targets ≥44px)            |
| Formatação financeira validada   | 100% dos formatters de `format.ts` têm unit tests. Zero risco de "R$" errado no relatório ou dashboard              |


#### O que a Fase 6.5 NÃO faz


| Escopo excluído                                 | Por quê                                                                                           | Fase destino |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------ |
| Testes de backend Python (gap-fill)             | Backend já tem ~488 tests. Gap-fill de scripts legados é F7                                       | Fase 7       |
| Visual regression testing (screenshot diff)     | Frágil (font rendering, anti-aliasing, viewport). Spot-check manual (L4) é suficiente para MVP    | Futuro       |
| Performance testing (Lighthouse, Core Web Vitals)| Relevante para produção, não para pre-deploy. Baseline criado na F7                               | Fase 7       |
| Accessibility testing dedicado (VoiceOver/NVDA) | ARIA pass feito na F6D.12. Testing dedicado após beta users                                       | Fase 7+      |
| Testes de carga / stress                        | 1 user dogfood. Stress test é prematuro                                                           | Futuro       |
| Contract testing (Pact/consumer-driven)         | MSW + OpenAPI fixtures cobrem o essencial. Pact é over-engineering para equipe de 1                | Futuro       |


#### Dependências da Fase 6.5

```
# Novas dependências Frontend — devDependencies (npm install -D)
vitest                            # Test runner (Vite-native, ESM, fast)
@vitest/coverage-v8               # Coverage via V8 (fast, accurate)
@testing-library/react            # Component testing (user-centric)
@testing-library/jest-dom         # Custom matchers (toBeInTheDocument, toHaveTextContent)
@testing-library/user-event       # User interaction simulation (click, type, drag)
jsdom                             # DOM environment para Vitest (não precisa de browser)
msw                               # Mock Service Worker (API mocking sem monkey-patch)
@playwright/test                  # E2E test framework (multi-browser, auto-wait)

# Já disponíveis (Fases 0-6):
# next.js, react, typescript, tailwindcss, recharts, xlsx, date-fns
# lucide-react, shadcn/ui, next-themes, sonner
```

#### Nota sobre mock drift

O maior risco de testes com MSW é **mock drift**: o backend muda um schema e os mocks ficam desatualizados, fazendo testes passarem quando o app real quebraria. Mitigação:

1. **Fixtures derivadas do OpenAPI:** FastAPI gera OpenAPI schema automaticamente. Script `scripts/gen-test-fixtures.py` gera fixtures JSON a partir dos Pydantic models
2. **E2E como safety net:** Os 8 fluxos E2E com backend real capturam qualquer drift que L1/L2 não pegarem
3. **Revisão pós-sprint:** Ao final de cada sprint que altera schemas backend, rodar `gen-test-fixtures.py` e verificar diffs

---

### FASE 7 — Infraestrutura de Produção + Security + LGPD

**Objetivo:** Levar o Fin a produção com a menor superfície de risco possível. Deploy real em VPS com Docker Compose, HTTPS via Traefik, segurança at-rest, compliance LGPD mínimo viável, CI/CD com coverage gate, e cobertura de testes realista focada em paths críticos.

**Duração estimada:** 6-8 semanas (4 sub-fases, 3 sprints de build + 2 semanas de dogfood)

**Princípio norteador:** *Ship, then polish.* A Fase 7 coloca o produto no ar com segurança suficiente para dogfood + beta fechado. Features de growth (email digest, demo mode, landing page) ficam para Fase 8. Testes cobrem o crítico — não perseguimos 100% às custas do launch.

#### Progressão de launch: Dogfood → Beta → GA

A Fase 7 não termina no deploy. Termina quando o produto prova estabilidade em uso real.

| Estágio | Quem | Duração | Gate de passagem |
| --- | --- | --- | --- |
| **Dogfood** | David (1 user) | 2+ semanas pós-7D | Zero pipeline failures em 5 runs consecutivos. Uptime >99%. Zero critical bugs. Backup restore testado 1x. Uso real com documentos financeiros reais |
| **Beta fechado** | Família + 2-3 convidados (5 users) | 4-6 semanas | Onboarding sem suporte (user consegue register→upload→report sozinho). Latência p95 <1s. Nenhum dado corrompido. LGPD compliance verificado |
| **GA** | Público | Pós-Fase 8 | Landing page + demo mode + billing (se aplicável). Suporte básico (FAQ, email) |

> **Dogfood é obrigatório antes de convidar beta testers.** Sem ele, bugs de infra viram bugs de produto na percepção dos early adopters — e a primeira impressão é irrecuperável.

#### Decisões tomadas para esta fase


| Decisão             | Escolha                                                      | Rationale                                                                                                                                   |
| ------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Cloud provider (D5) | VPS (Hetzner CX32 — 4 vCPU, 8GB RAM, ~$8/mo) + Docker Compose | 8GB dá margem para deploy rolling sem OOM. CX22 (4GB) é apertado com todos os containers + margem de deploy. Upgradeable para Railway/Fly.io se virar SaaS |
| Criptografia (D7)   | Fernet app-level (expand do Fase 4)                          | Consistente com vault de API keys. Encrypt CPFs, dados financeiros. Rotação via dual-key (ver nota 7B) |
| Storage produção    | Filesystem local com Docker volume persistente               | Simples. Backup via pg_dump + volume snapshot. S3 é overkill para MVP                                                                       |
| Billing             | Adiar para pós-launch                                        | BYOK funciona sem billing. Stripe é projeto próprio                                                                                         |
| DB produção         | SQLite (dev) + PostgreSQL (prod). CI testa em PostgreSQL     | SQLAlchemy abstrai. CI roda no mesmo DB que prod — valor real. Dual-test SQLite+PG em CI descartado (dobra tempo CI sem valor proporcional) |
| Reverse proxy       | Traefik (auto-SSL via Let's Encrypt, routing)                | Docker-native, config via labels, zero manutenção de certificados                                                                           |
| CI/CD               | GitHub Actions: lint + test + build + scan + coverage + deploy | Standard, gratuito para repos públicos/privados (2000 min/mo). Inclui Docker image CVE scan |
| Coverage target     | ≥95% line (código novo) + ≥85% line (overall) + ≥75% branch  | 100% line em ~14K linhas de legado é anti-pattern (diminishing returns). Foco em paths críticos e código novo                               |
| Deploy strategy     | Rolling restart com pre-pull + health check + rollback automático | `docker compose pull && up -d` com health check pós-deploy. Rollback = re-tag para image anterior. Zero-downtime real requer 2 VPS (overkill para dogfood). Downtime aceitável: <30s |
| Features de growth  | Adiar email digest + demo mode para Fase 8                   | São features de aquisição/marketing, não infra de produção. Colocá-las no critical path do launch é armadilha clássica de scope creep       |
| Migrations em deploy | Backward-compatible only                                    | Alembic migrations executam ANTES do restart. Nunca remover/renomear colunas — apenas adicionar. Rename = add new → migrate data → drop old (2 deploys) |


#### Itens adiados de fases anteriores incorporados


| Item                        | Origem        | Tratamento na Fase 7                                          |
| --------------------------- | ------------- | ------------------------------------------------------------- |
| docker-compose.dev.yml      | Fase 1 (1.12) | → Task 7A.3                                                   |
| S3/MinIO storage            | Fase 2        | → Adiado. Filesystem local com Docker volume é suficiente     |
| Storage cleanup/retention   | Fase 2        | → Task 7B.9 (retention policy 90 dias)                        |
| Billing / Stripe            | Fases 4, 6    | → Adiado para pós-launch. BYOK resolve tier sem billing       |
| Rate limiting per user      | Fase 4        | → Task 7B.2                                                   |
| Multi-worker scaling        | Fase 5        | → Adiado. 1 worker suficiente para VPS. Scaling = upgrade VPS |
| Flower dashboard            | Fase 5        | → Adiado para Fase 8 (P2, não necessário para launch)         |
| Email digest notifications  | Fase 6        | → Adiado para Fase 8 (feature de growth, não infra)           |
| Demo mode (dados fictícios) | Fase 6        | → Adiado para Fase 8 (feature de aquisição, não infra)        |

#### Projeção de custo mensal (Fase 7 — dogfood/beta)

| Item | Custo | Notas |
| --- | --- | --- |
| VPS Hetzner CX32 | ~$8/mo | 4 vCPU, 8GB RAM, 80GB SSD |
| Domínio (.com.br) | ~$1/mo | ~R$40/ano via Registro.br |
| Sentry | $0 | Free tier (5K errors/mo, 10K perf events) |
| UptimeRobot | $0 | Free tier (50 monitors, 5min interval) |
| GitHub Actions | $0 | Free tier (2000 min/mo para private repos) |
| Codecov | $0 | Free para repos open-source ou 5 users |
| **Total** | **~$9-10/mo (~R$50)** | Escala para ~$15-20/mo se adicionar backup off-site |


#### Diagrama: arquitetura de produção

```
Internet
  ↓
┌──────────────────────────────────────────────────────────────┐
│ VPS (Hetzner CX32, ~$8/mo, 4 vCPU, 8GB RAM, 80GB SSD)      │
│                                                              │
│  Traefik v3 (reverse proxy, auto-SSL Let's Encrypt)          │
│    ├─ :443 /           → frontend:3000 (Next.js standalone)  │
│    ├─ :443 /api/*      → api:8000 (FastAPI + uvicorn)        │
│    └─ :443 /ws/*       → api:8000 (WebSocket pass-through)   │
│                                                              │
│  docker-compose.prod.yml:                                    │
│    ├─ frontend (Next.js standalone, ~100MB)                   │
│    ├─ api (FastAPI + uvicorn, ~200MB)                         │
│    ├─ worker (Celery, mesma imagem api, entrypoint diferente) │
│    ├─ postgres:16-alpine (volume persistente, 512MB limit)   │
│    ├─ redis:7-alpine (volume persistente, 128MB limit)       │
│    └─ traefik:v3 (auto-SSL, labels-based routing)            │
│                                                              │
│  Segurança:                                                  │
│    ├─ UFW: apenas 22 (SSH), 80 (redirect), 443 (HTTPS)      │
│    ├─ fail2ban: SSH + rate limit abuse                        │
│    ├─ SSH keys only (password auth disabled)                  │
│    └─ Docker network isolation (services internos sem port)  │
│                                                              │
│  Automação:                                                  │
│    ├─ pg_dump diário → /backups/ (rotação 7 dias, gzip)      │
│    ├─ Docker volume snapshot semanal → off-site (rsync)      │
│    └─ cleanup: pipeline outputs > 90 dias → archive          │
│                                                              │
│  Volumes:                                                    │
│    ├─ pg_data (PostgreSQL)                                    │
│    ├─ redis_data (Redis AOF persistence)                     │
│    ├─ storage (tenant files, per-workspace isolation)         │
│    ├─ backups (pg_dump daily, rotação 7 dias)                │
│    └─ letsencrypt (SSL certs, auto-renewed)                  │
└──────────────────────────────────────────────────────────────┘

GitHub Actions CI/CD:
  push to main → lint (ruff) → test (pytest + PostgreSQL service) →
  build Docker images → scan CVEs (trivy/docker scout, gate: 0 critical) →
  push GHCR → SSH deploy → alembic upgrade head →
  docker compose pull && up -d → health check (3x, 10s) → notify
  (falha health check → rollback automático para image tag anterior)
```

---

#### Sub-fase 7A: Docker + Deploy + HTTPS (Semana 1-2)

**Objetivo:** Produto acessível via URL pública com HTTPS. Imagens Docker otimizadas. Backup automatizado. Este é o "dia 1 em produção" — tudo o mais depende disto.

**Rationale de fusão:** As antigas 7A (Docker) e 7B (Deploy) eram artificialmente separadas. Na prática, Dockerfiles sem deploy não entregam valor, e deploy sem Dockerfiles não existe. Fundir elimina o checkpoint intermediário sem valor e permite foco end-to-end.


| #     | Tarefa                                                                                                                                                                                                                | Prioridade | Estimativa | Status |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 7A.1  | Dockerfile backend: multi-stage build (deps → app). Entrypoints separados: `api` (uvicorn, 2 workers), `worker` (celery, concurrency=2). Imagem slim (~200MB). Non-root user. `.dockerignore` restritivo              | P0         | 4h         | ☐      |
| 7A.2  | Dockerfile frontend: multi-stage (install → build → serve). Next.js `output: 'standalone'`. Imagem slim (~100MB). Non-root user                                                                                       | P0         | 3h         | ☐      |
| 7A.3  | `docker-compose.dev.yml`: PostgreSQL + Redis + volumes. Hot reload backend (watchfiles) + frontend (next dev). Ports expostos para debug. Network interna                                                             | P0         | 3h         | ☐      |
| 7A.4  | `docker-compose.prod.yml`: API + Worker + Frontend + PostgreSQL + Redis + Traefik. Health checks (HTTP + pg_isready + redis-cli ping). Restart policies (`unless-stopped`). Resource limits (mem_limit por container) | P0         | 5h         | ☐      |
| 7A.5  | `.env.example` + env management: todos os secrets documentados (DATABASE_URL, REDIS_URL, FERNET_KEY, JWT_SECRET, DOMAIN, ACME_EMAIL). `.env.prod` no `.gitignore`. Script `scripts/gen-secrets.sh` para gerar valores | P0         | 2h         | ☐      |
| 7A.6  | VPS provisioning: Hetzner CX32 (4 vCPU, 8GB, ~$8/mo). Setup: UFW, SSH keys only, fail2ban, Docker CE + Docker Compose v2. Swap 2GB (safety net). Timezone UTC. Documentar setup em `docs/VPS_SETUP.md`                 | P0         | 3h         | ☐      |
| 7A.7  | Traefik config: `traefik.yml` estático + Docker labels dinâmicos. Auto-SSL (Let's Encrypt, ACME HTTP challenge). HTTP→HTTPS redirect. TLS 1.2+ min. WebSocket pass-through para `/api/pipeline/runs/*/ws`             | P0         | 3h         | ☐      |
| 7A.8  | Domínio + DNS: registrar/configurar A record apontando para VPS IP. Wildcard ou subdomínio (app.fin.com.br). TTL curto (300s) para migration                                                                          | P0         | 1h         | ☐      |
| 7A.9  | PostgreSQL prod: criar DB + user dedicado (não root), rodar `alembic upgrade head`, seed dados iniciais (admin user via script, default config). Connection pooling: SQLAlchemy pool_size=5, max_overflow=10          | P0         | 3h         | ☐      |
| 7A.10 | Backup automático: cron `pg_dump` diário → gzip → `/backups/` com rotação 7 dias. Docker volume snapshot semanal. Script `scripts/restore-backup.sh` testado manualmente                                              | P0         | 3h         | ☐      |
| 7A.11 | Smoke test completo: `docker-compose -f docker-compose.prod.yml up -d` localmente → health checks green → frontend em `:443` → API responde em `/api/health` → login funciona → upload funciona → pipeline roda       | P0         | 3h         | ☐      |
| 7A.12 | Data migration plan: script `scripts/seed-prod.sh` — cria admin user, aplica config defaults (institutions, categories, pipeline). Documentar procedimento de import dos dados reais (config JSON export/import via API) | P0         | 3h         | ☐      |
| 7A.13 | First deploy real: push para VPS via SSH. `docker compose pull && up -d`. Verificar SSL, health checks, logs. Importar config via API. **Celebrar: produto no ar.**                                                    | P0         | 2h         | ☐      |


**Checkpoint 7A:** Produto acessível via `https://dominio.com`. HTTPS funcionando via Traefik + Let's Encrypt. PostgreSQL com backup diário. Docker images otimizadas. Dev environment com hot reload. Config importada. **O produto está no ar.**

---

#### Sub-fase 7B: Security Hardening + LGPD (Semana 2-3)

**Objetivo:** Dados sensíveis protegidos at-rest e in-transit. Compliance LGPD mínimo viável para uso real. Rate limiting. Session security robusta. Audit trail.

**Por que audit log é P0:** Para um produto que processa dados financeiros pessoais sob LGPD, audit log não é "nice to have" — é requisito legal (Art. 37, LGPD). O titular pode solicitar informação sobre o tratamento de seus dados, e sem audit log, não há como responder.


| #    | Tarefa                                                                                                                                                                                                                                                                           | Prioridade | Estimativa | Status |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 7B.1 | Fernet encryption expandido: encrypt CPFs em `FamilyMember`, dados financeiros sensíveis em `Report` (summary JSON). Utility `encrypt_field()` / `decrypt_field()` reusável. Migration Alembic para dados existentes                                                             | P0         | 6h         | ☐      |
| 7B.2 | Rate limiting: slowapi middleware — auth endpoints (5/min), upload (10/min), pipeline trigger (2/min), API geral (100/min por IP). Response 429 com `Retry-After` header. Whitelist para health checks                                                                           | P0         | 3h         | ☐      |
| 7B.3 | Security headers middleware: CORS restritivo (só `DOMAIN` env var), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, Content-Security-Policy (report-only inicialmente), `Strict-Transport-Security` (1 ano, includeSubDomains)                                       | P0         | 3h         | ☐      |
| 7B.4 | Session security: JWT access token (15min, era 24h — reduzir superfície) + refresh token (7d, httpOnly cookie). Rotation on refresh. Revocação on password change. `POST /api/auth/refresh` + `POST /api/auth/logout`. **Frontend:** interceptor HTTP (401 → refresh → retry queue para requests concorrentes), handling de tab em background com token expirado | P0 | 16h | ☐ |
| 7B.5 | Audit log: model `AuditEntry` (id, user_id, action enum, resource_type, resource_id, ip, user_agent, timestamp, details_json). Registra: login/logout, upload, pipeline run/cancel, config change, account deletion, export request. Middleware automático para write operations | P0         | 6h         | ☐      |
| 7B.6 | LGPD — Termos de uso + Política de privacidade: páginas estáticas no frontend (`/terms`, `/privacy`). Aceite obrigatório no registro (checkbox + accepted_at timestamp no User model). Alembic migration                                                                         | P0         | 4h         | ☐      |
| 7B.7 | LGPD — Direito de exclusão: `DELETE /api/account` — cascade delete completo (user → workspace → documents → runs → stage_logs → reviews → configs → storage files). Confirmação dupla (senha + "DELETAR" digitado). Audit log entry antes do delete                              | P0         | 8h         | ☐      |
| 7B.8 | LGPD — Portabilidade: `GET /api/account/export` — gera ZIP com dados pessoais (profile JSON), configs, relatórios HTML, documentos originais, audit log do user. Celery task em background. Download link temporário (1h, signed URL)                                            | P1         | 6h         | ☐      |
| 7B.9  | Storage cleanup: retention policy — pipeline outputs > 90 dias → soft-delete (flag). Celery periodic task (celery-beat, daily). Admin pode purgar. Respects active reports (não deleta storage de relatório vigente)                                                             | P1         | 4h         | ☐      |
| 7B.10 | UX de produção: (1) Rate limit → toast "Muitas requisições, aguarde X segundos" com countdown. (2) LGPD delete → tela dedicada com stepper (confirmar senha → digitar "DELETAR" → countdown 10s → executa). (3) Export → notification in-app quando ZIP pronto + download link. (4) Maintenance → página estática `maintenance.html` servida por Traefik quando API está fora (label `traefik.http.services.maintenance`) | P1 | 4h | ☐ |

**Nota — Rotação de secrets:** Fernet key rotation usa dual-key strategy: (1) gerar nova key, (2) configurar `FERNET_KEYS=new,old` (Fernet aceita lista), (3) re-encrypt dados em background (Celery task), (4) remover key antiga. JWT secret rotation: deploy novo secret → tokens existentes expiram naturalmente (15min access, 7d refresh). Documentar procedimento no Runbook (7C.7).

**Checkpoint 7B:** Dados sensíveis criptografados at-rest. JWT com refresh token seguro. Rate limiting ativo com UX de feedback. LGPD compliance: termos aceitos, exclusão total com UX dedicada, portabilidade com notificação. Audit log registra todas as ações sensíveis. Security headers em todas as respostas.

---

#### Sub-fase 7C: CI/CD + Observabilidade (Semana 3-4)

**Objetivo:** Pipeline de CI que bloqueia código quebrado. CD que deploya automaticamente. Observabilidade suficiente para diagnosticar problemas em produção sem acesso ao servidor.


| #    | Tarefa                                                                                                                                                                                                                                             | Prioridade | Estimativa | Status |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 7C.1 | GitHub Actions CI: lint (ruff) → test (pytest com PostgreSQL service container) → build (Docker multi-arch) → **Docker image scan** (`docker scout cves` ou `trivy image`, gate: 0 critical/high) → coverage report (pytest-cov). Gate: código novo ≥95% line. Badge coverage no README | P0 | 6h | ☐ |
| 7C.2 | GitHub Actions CD: on push to main (CI green) → build images → push GHCR → SSH deploy → `alembic upgrade head` (migrations first, backward-compatible) → `docker compose pull && up -d --remove-orphans` → health check post-deploy (curl /api/health, 3 retries, 10s interval). Notify via webhook | P0 | 4h | ☐ |
| 7C.3 | Rollback automatizado: se health check pós-deploy falha 3x em 60s → rollback para image tag anterior (`docker compose up -d` com `.env.rollback`). Script `scripts/rollback.sh`. Procedimento documentado no Runbook. **Nota:** rollback de migration = deploy fix-forward (nova migration que reverte), nunca `alembic downgrade` em prod | P0 | 3h | ☐ |
| 7C.4 | Sentry setup: backend (`sentry-sdk[fastapi]`, DSN via env var, environment tags, release tracking). Frontend (`@sentry/nextjs`, source maps). Error grouping. Performance sampling 10%                                                             | P1         | 4h         | ☐      |
| 7C.5 | Structured logging: `structlog` com JSON output em prod, pretty-print em dev. `request_id` UUID em cada request (middleware). Correlação com Celery task_id. Log levels: INFO (prod), DEBUG (dev). Docker log rotation (max-size 50MB, max-file 3) | P1         | 4h         | ☐      |
| 7C.6 | Uptime monitoring: UptimeRobot (free tier, 5min interval). Targets: `/api/health` (DB + Redis + Celery), `https://domínio.com` (frontend). Alerta via email. Status page pública (opcional)                                                        | P1         | 1h         | ☐      |
| 7C.7 | Runbook de operações: `docs/RUNBOOK.md` — deploy manual, rollback, backup restore, DB migration (backward-compatible only), secret rotation (Fernet dual-key, JWT), scaling up VPS, log access, Celery worker restart, troubleshooting common issues. Checklist de first deploy. "First week in production" checklist (verificar backups, logs, storage growth, latência) | P1 | 5h | ☐ |


**Checkpoint 7C:** CI bloqueia código quebrado + imagens com CVEs. CD deploya automaticamente em push to main (migrations backward-compatible first). Rollback automático se health check falha. Sentry captura erros em prod. Logs estruturados com request tracing. Uptime monitorado. Runbook documentado com secret rotation e "first week" checklist.

---

#### Sub-fase 7D: Quality Gate + Launch Readiness (Semana 4-6 + 2 semanas dogfood)

**Objetivo:** Cobertura de testes suficiente para confiança no launch. Frontend E2E para fluxos críticos. Performance baseline. Pre-launch checklist verificada. **Dogfood obrigatório:** 2+ semanas de uso real antes de declarar "launch ready".

**Filosofia de coverage:** Buscar 100% line em ~14K linhas de scripts legados (E5: 107KB, E6: 197KB) é anti-pattern clássico que atrasa launches por semanas com retornos decrescentes. Em vez disso: cobertura alta no código novo (≥95%), cobertura sólida overall (≥85%), e foco explícito em paths críticos (auth, pipeline, data integrity).


| #    | Tarefa                                                                                                                                                                                                                                       | Prioridade | Estimativa | Status |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ---------- | ------ |
| 7D.1 | Gap-fill unit tests: scripts pipeline menores — E0 (unlock, audit, route), E2/banks (parsers com edge cases: valores negativos, datas inválidas, encoding), E3 (reconcile duplicatas), E4 (categorize uncategorized), E7 (review edge cases) | P0         | 10h        | ☐      |
| 7D.2 | Gap-fill unit tests: scripts pipeline maiores — E5 (foco: cálculos patrimoniais, score, edge cases de divisão por zero, períodos incompletos), E5N (narrativas com dados ausentes), E6 (render com seções opcionais, dados parciais)         | P1         | 12h        | ☐      |
| 7D.3 | Gap-fill: API endpoints + services — error paths (DB down, Redis down, storage full), validation failures (Pydantic rejects), auth edge cases (expired token, revoked, tampered), concurrency (2 pipeline runs simultâneos)                  | P0         | 8h         | ☐      |
| 7D.4 | ~~Setup frontend tests~~ → **Movido para Fase 6.5A** (tooling setup + unit tests). Verificar que CI integra testes frontend (Vitest + Playwright) no pipeline de deploy                                                                     | P0         | 1h         | ☐      |
| 7D.5 | ~~Frontend E2E tests~~ → **Movido para Fase 6.5C** (8 fluxos E2E). Aqui: verificar que E2E rodam com PostgreSQL (prod DB) além de SQLite (dev). Ajustar fixtures se necessário                                                              | P1         | 2h         | ☐      |
| 7D.6 | ~~Frontend component tests~~ → **Movido para Fase 6.5B** (integration tests). Aqui: adicionar testes para UX de produção (7B.10): rate limit toast, LGPD delete stepper, export notification, maintenance page                              | P1         | 3h         | ☐      |
| 7D.7 | Performance baseline: `time` de pipeline end-to-end com dataset padrão. Response time p50/p95 de API endpoints críticos (login, upload, pipeline trigger, dashboard). Documentar em `docs/PERFORMANCE_BASELINE.md`. Alert se 2x degradação   | P1         | 3h         | ☐      |
| 7D.8 | Coverage integration: CI gate `coverage(new_code) >= 95%`. Codecov integration com PR comments. Badge no README. Target overall: ≥85% line, ≥75% branch (crescimento orgânico, não forçado)                                                  | P0         | 3h         | ☐      |
| 7D.9  | Basic telemetry (sem third-party): tabela `UsageMetric` (user_id, action, resource_type, timestamp, metadata_json). Log: pipeline runs (duração, stages, success/fail), login frequency, storage usage per workspace. Dashboard query simples para dogfood analysis. Sem analytics externo (privacy-first) | P1 | 4h | ☐ |
| 7D.10 | Pre-launch checklist: verificar todos os critérios de aceite. Smoke test manual end-to-end em produção. Backup restore testado. Rollback testado. Security headers verificados (securityheaders.com). SSL grade A (ssllabs.com)              | P0         | 3h         | ☐      |
| 7D.11 | **Dogfood period (2+ semanas):** Uso real diário com documentos financeiros reais. Rodar pipeline completo 5+ vezes. Verificar: uptime (UptimeRobot), erros (Sentry), storage growth, latência (performance baseline), backup restore funcional. Documentar bugs encontrados. Gate: zero critical bugs, zero data corruption, pipeline 100% success rate em 5 runs consecutivos | P0 | — | ☐ |


**Checkpoint 7D:** Coverage ≥85% line backend. Frontend tests (Fase 6.5) verificados com PostgreSQL prod DB. Performance baseline documentado. CI gate ativo. Pre-launch checklist green. **Dogfood: 2+ semanas de uso real sem critical bugs, 5+ pipeline runs com 100% success.** Produto pronto para beta fechado.

---

#### Critérios de aceite da Fase 7 completa


| Critério                       | Verificação                                                                                          | Gate           |
| ------------------------------ | ---------------------------------------------------------------------------------------------------- | -------------- |
| Acessível publicamente         | `https://dominio.com` funciona com SSL válido (Let's Encrypt). Grade A no SSL Labs                   | **DEPLOY**     |
| Docker prod funcional          | `docker-compose.prod.yml` sobe todos os services com health checks green em <60s                     | **DEPLOY**     |
| PostgreSQL em produção         | Prod usa PostgreSQL. Alembic migrations aplicadas. Connection pooling configurado                    | **DEPLOY**     |
| Dados sensíveis criptografados | CPFs, API keys, valores financeiros criptografados via Fernet at-rest. Nunca em plaintext no DB      | **DEPLOY**     |
| Rate limiting ativo            | Endpoints protegidos (auth, upload, pipeline). 429 com Retry-After header + UX feedback              | **DEPLOY**     |
| Security headers               | CORS restritivo, HSTS, CSP, X-Frame-Options, X-Content-Type-Options. Score ≥B no securityheaders.com | **DEPLOY**     |
| Session security               | JWT access (15min) + refresh token (7d, httpOnly). Rotation funciona. Revocação on password change. Frontend interceptor com retry queue | **DEPLOY** |
| LGPD compliance                | Termos aceitos no registro. DELETE /account cascade completo com UX dedicada. Export gera ZIP com notificação | **DEPLOY** |
| Audit log                      | Todas as ações sensíveis registradas (login, upload, pipeline, config, deletion)                     | **DEPLOY**     |
| Backup diário                  | pg_dump diário em `/backups/`, rotação 7 dias. Restore testado e documentado no Runbook              | **DEPLOY**     |
| CI/CD funcional                | Push to main → lint → test → scan (CVE) → build → deploy automático. Rollback automático se health check falha | **DEPLOY** |
| Coverage gate                  | CI bloqueia merge se coverage de código novo < 95%                                                   | **DEPLOY**     |
| Coverage overall               | ≥85% line, ≥75% branch backend. Crescimento orgânico para 90%+ ao longo do tempo                     | **DEPLOY**     |
| Frontend E2E green             | Playwright E2E tests (Fase 6.5) passam para 8 fluxos críticos com PostgreSQL prod DB                 | **DEPLOY**     |
| Observabilidade                | Sentry captura erros. Uptime monitoring com alerta. Logs estruturados com request_id                 | **DEPLOY**     |
| Performance baseline           | Documentado. Pipeline end-to-end < 5min. API p95 < 500ms                                             | **DEPLOY**     |
| Runbook                        | `docs/RUNBOOK.md` com deploy, rollback, backup restore, secret rotation, troubleshooting             | **DEPLOY**     |
| Regressão zero                 | Todas as funcionalidades das Fases 0-6 continuam funcionando em produção                             | **DEPLOY**     |
| **Dogfood validado**           | **2+ semanas de uso real. 5+ pipeline runs com 100% success. Zero critical bugs. Zero data corruption. Backup restore testado 1x em prod. Storage growth monitorado** | **LAUNCH** |
| **Telemetria básica**          | **Usage metrics registram: pipeline runs, login freq, storage usage. Dados disponíveis para análise** | **LAUNCH**     |


#### O que a Fase 7 NÃO faz (fica para Fase 8 / pós-launch)


| Escopo excluído                              | Por quê                                                                             | Quando        |
| -------------------------------------------- | ----------------------------------------------------------------------------------- | ------------- |
| Email digest (resumo financeiro periódico)   | Feature de engagement/growth, não infra. Requer email service + templates + opt-in  | Fase 8        |
| Demo mode (workspace fictício read-only)     | Feature de aquisição/marketing, não infra. Requer dados fictícios + landing page    | Fase 8        |
| Flower dashboard (Celery monitoring UI)      | Nice-to-have. `celery inspect` via CLI é suficiente para 1 worker                   | Fase 8 (P2)   |
| Stripe billing / pagamento real              | BYOK resolve tier. Stripe é projeto próprio                                         | Pós-launch    |
| S3/MinIO para file storage                   | Docker volume suficiente para uso pessoal/familiar                                  | Se virar SaaS |
| Multi-worker horizontal scaling              | 1 worker + VPS suficiente. Scaling = upgrade VPS                                    | Se virar SaaS |
| Kubernetes / container orchestration         | Over-engineering para VPS single-node                                               | Se virar SaaS |
| Terraform / IaC                              | Docker Compose + scripts é suficiente para 1 VPS                                    | Se virar SaaS |
| Email transacional (welcome, reset password) | Password reset via token manual. Emails transacionais são futuro                    | Pós-launch    |
| CDN para assets estáticos                    | Next.js standalone serve assets. CDN é otimização prematura                         | Pós-launch    |
| 100% line coverage em scripts legados        | Anti-pattern. ~14K linhas de E5/E6 com lógica complexa. ROI negativo vs. 85%+       | Orgânico      |
| Dual DB testing em CI (SQLite + PostgreSQL)  | SQLAlchemy abstrai. Testar no DB de prod (PG) é suficiente. Dual dobra CI sem valor | Descartado    |
| Landing page pública                         | Zero usuários externos na fase dogfood/beta. Landing = otimização prematura         | Fase 8        |
| PWA / offline support                        | Prematuro. next-pwa deprecated. @serwist/next quando houver demanda real            | Fase 8        |
| Feature flags (DB-backed toggle system)      | Overkill para dogfood com 1 user. Deploy é rápido o suficiente para toggle via code | Fase 8 (se necessário) |
| Analytics externo (PostHog, Mixpanel, GA)    | Privacy-first. Telemetria básica interna (7D.9) suficiente para dogfood. Analytics externo quando houver beta testers | Fase 8 |
| True blue-green / zero-downtime deploy       | Rolling restart com <30s downtime é aceitável para dogfood/beta. Zero-downtime requer 2 VPS ou managed platform | Se virar SaaS |


#### Dependências da Fase 7

```
# Novas dependências Python (backend/requirements.txt)
slowapi>=0.1.9         # Rate limiting para FastAPI
sentry-sdk[fastapi]    # Error tracking backend
structlog>=24.0.0      # Structured logging (JSON)

# Novas dependências Frontend (npm)
@sentry/nextjs         # Error tracking frontend

# Novas dependências de infra (docker-compose services)
traefik:v3             # Reverse proxy + auto-SSL (Docker Compose service)
postgres:16-alpine     # PostgreSQL prod (Docker Compose service)

# Novas dependências de CI/CD
# GitHub Actions (runners gratuitos, 2000 min/mo)
# UptimeRobot (free tier, 50 monitors, 5min interval)
# Codecov (free para repos públicos, coverage tracking)
# trivy ou docker scout (Docker image CVE scanning, gratuito)

# Dependências de teste (instaladas na Fase 6.5):
# vitest, @vitest/coverage-v8, @testing-library/react, @testing-library/jest-dom
# @testing-library/user-event, jsdom, msw, @playwright/test

# Já disponíveis (Fases 0-6.5):
# docker, docker-compose, pytest, pytest-cov, coverage.py
# fastapi, pydantic, sqlalchemy, celery, redis, cryptography
# next.js, react, tailwindcss, typescript, lucide-react, shadcn/ui
```

#### Plano de upgrade: VPS → managed cloud (se virar SaaS)

```
Se o produto crescer além de uso pessoal:

1. Migrar DB: PostgreSQL Docker → Railway/Supabase managed PostgreSQL
   (Alembic migrations já funcionam. Só mudar DATABASE_URL)

2. Migrar Redis: Docker → Railway/Upstash managed Redis
   (Só mudar REDIS_URL)

3. Migrar storage: Docker volume → S3/MinIO
   (Requer implementar StorageBackend abstraction — ~1 sprint)

4. Migrar compute: VPS → Railway/Fly.io containers
   (Dockerfiles já prontos. Push-to-deploy)

5. Adicionar Stripe billing
   (Endpoints de pricing já preparados na landing page Fase 8)

6. Adicionar CDN (CloudFront/Cloudflare)
   (Next.js standalone → Next.js com CDN para assets estáticos)

Estimativa de migração: 2-3 sprints adicionais.
```

---

## 6. Backlog Priorizado

### Legenda de prioridades

- **P0** — Bloqueante. Sem isso a fase não entrega valor.
- **P1** — Importante. Sem isso funciona, mas falta qualidade/completude.
- **P2** — Nice-to-have. Pode postergar para a próxima fase ou sprint.

### Backlog completo (todas as fases)

Total de tarefas: **~335**


| Fase             | Sub-fases           | P0  | P1  | P2  | Total |
| ---------------- | ------------------- | --- | --- | --- | ----- |
| 0 — Core         | 0A, 0B, 0C, 0D      | 16  | 10  | 1   | 27    |
| 1 — API + Auth   | —                   | 11  | 5   | 0   | 16    |
| 2 — Upload       | 2A, 2B, 2C, 2D      | 31  | 7   | 0   | 38    |
| 3 — Config UI    | 3A, 3B, 3C, 3D      | 23  | 6   | 3   | 32    |
| 4 — LLM          | 4A, 4B, 4C, 4D      | 32  | 2   | 0   | 34    |
| 4.5 — Design Sys | 4.5A, 4.5B, 4.5C    | 27  | 0   | 0   | 27    |
| 5 — Task Queue   | 5A, 5B, 5C          | 17  | 6   | 0   | 23    |
| 6 — Frontend Pro | 6A-6D               | 37  | 11  | 0   | 48    |
| 6.5 — FE Testing | 6.5A, 6.5B, 6.5C    | 24  | 6   | 0   | 30    |
| 7 — Produção     | 7A-7D               | 29  | 12  | 0   | 41    |


---

## 7. Sprints

### Planejamento por sprint (2 semanas cada)

> Sprints são estimativas. Ajustar conforme velocidade real.

#### Sprint 1-2: Fase 0 — Foundation ✅ CONCLUÍDA

**Objetivo:** Pipeline como package Python importável com contexto injetável.


| Sprint       | Foco                                    | Sub-fase | Tarefas               | Status |
| ------------ | --------------------------------------- | -------- | --------------------- | ------ |
| S1 (sem 1)   | Foundation layer + wrap módulos menores | 0A + 0B  | 0A.1–0A.6, 0B.1–0B.7  | ✅      |
| S2 (sem 2-3) | Wrap módulos grandes + orchestrator     | 0C + 0D  | 0C.1–0C.10, 0D.1–0D.7 | ✅      |


**Checkpoint S1:** ✅ E2, E3, E4, E7 chamáveis via `pipeline/stages/`. 106 tests green.
**Checkpoint S2:** ✅ Pipeline completo via `pipeline.run_pipeline(ctx)`. 136 tests green.

---

#### Sprint 3-4: Fase 1 — API + Auth ✅ CONCLUÍDA


| Sprint | Foco                                     | Tarefas   | Status |
| ------ | ---------------------------------------- | --------- | ------ |
| S3     | Backend: FastAPI + DB + Auth + endpoints | 1.1–1.13  | ✅      |
| S4     | Frontend: Next.js + login + relatórios   | 1.14–1.18 | ✅      |


**Checkpoint S4:** ✅ Login via browser funciona. Relatório HTML visível em iframe. 149 testes totais.

---

#### Sprint 5-7: Fase 2 — Upload + Pipeline Web


| Sprint       | Foco                                     | Sub-fase | Tarefas               | Status                               |
| ------------ | ---------------------------------------- | -------- | --------------------- | ------------------------------------ |
| S5 (sem 1)   | Storage layer + upload + E0 processing   | 2A + 2B  | 2A.1–2A.6, 2B.1–2B.10 | ✅                                    |
| S6 (sem 2-3) | Pipeline execution + backend integration | 2C       | 2C.1–2C.11            | ✅                                    |
| S7 (sem 3-4) | Frontend completo + testes E2E           | 2D       | 2D.1–2D.11            | ✅ (9/11 tasks, testes E2E pendentes) |


**Checkpoint S5:** ✅ Upload via API funcional. Documentos desbloqueados via vault e classificados automaticamente. 222 testes green.
**Checkpoint S6:** ✅ Pipeline roda em background via API. Progresso rastreado por etapa. Cancel cooperativo. 235 testes green (99 backend + 136 pipeline).
**Checkpoint S7:** ✅ Frontend completo: upload drag-and-drop, documents list (table + status badges), vault CRUD, pipeline trigger + progress polling (2s), stage-by-stage progress bar, error states, auto-redirect to report. AppShell com sidebar navigation. TypeScript types matching backend schemas. Build Next.js green. Testes E2E pendentes.

---

#### Sprint 8-9: Fase 3 — Config UI


| Sprint        | Foco                                         | Sub-fase | Tarefas               | Status             |
| ------------- | -------------------------------------------- | -------- | --------------------- | ------------------ |
| S8 (sem 1-2)  | Models + schemas + CRUD APIs + import/export | 3A + 3B  | 3A.1–3A.7, 3B.1–3B.10 | ✅                  |
| S9a (sem 2)   | Config injection (materialize)               | 3C       | 3C.1–3C.5             | ✅                  |
| S9b (sem 3-4) | Frontend config UI + testes E2E              | 3D       | 3D.1–3D.10            | ✅ (8/10, E2E → F6.5) |


**Checkpoint S8:** ✅ APIs CRUD para 5 configs. Import de JSON funcional. Validação Pydantic rejeita dados inválidos. 75 testes green (30 models + 30 API + 15 materializer).
**Checkpoint S9a:** ✅ Materialização funciona. Relatório com config-DB é idêntico ao config-disco. 310 testes totais (174 backend + 136 pipeline).
**Checkpoint S9b:** ✅ Config editável via UI (6 tabs). Import/export no browser. Testes E2E pendentes (→ F6.5).

---

#### Sprint 10-11: Fase 4 — LLM Automation ✅ CONCLUÍDA


| Sprint        | Foco                                                    | Sub-fase | Tarefas               | Status    |
| ------------- | ------------------------------------------------------- | -------- | --------------------- | --------- |
| S10 (sem 1-2) | LLM infra (LiteLLM+Instructor) + E1/E1.5/E2-llm         | 4A + 4B  | 4A.1–4A.9, 4B.1–4B.8  | ✅         |
| S11 (sem 2-3) | E7-review+apply + tier detection + review APIs + testes | 4C + 4D  | 4C.1–4C.7, 4D.1–4D.11 | ✅ (UI→F6) |


**Checkpoint S10:** ✅ LiteLLM + Instructor configurados. E1, E1.5, E2-llm produzem output válido (mock). API key encrypted. 362→430 testes green.
**Checkpoint S11:** ✅ Pipeline premium E2E (backend). Free skipa LLM. Review manual (pause→edit→resume). 444 testes totais. UI de config LLM e review adiada para Fase 6.

---

#### Sprint 11.5: Fase 4.5 — Design System Foundation


| Sprint         | Foco                                                           | Sub-fase    | Tarefas                      | Status |
| -------------- | -------------------------------------------------------------- | ----------- | ---------------------------- | ------ |
| S11.5a (sem 1) | Tokens + fonts + formatting + shadcn/ui init + core components | 4.5A + 4.5B | 4.5A.1–4.5A.7, 4.5B.1–4.5B.9 | ✅      |
| S11.5b (sem 2) | Page-by-page migration to design system                        | 4.5C        | 4.5C.1–4.5C.11               | ✅      |


**Checkpoint S11.5a:** ✅ Geist Sans + Geist Mono via `next/font/google`. `globals.css` com `@theme inline` (30+ tokens oklch). Paleta financeira semântica (5 tokens). 12 chart colors. shadcn/ui v4 init com 16 primitivos (base-ui/react). 7 compostos: `StatusBadge`, `Spinner`, `EmptyState`, `Delta`, `KPICard`, `PageHeader`, `ConfirmDialog`. `format.ts` com 9 formatters + 3 status maps → `{ label, variant }`. `cn()` utility. Build green.
**Checkpoint S11.5b:** ✅ Todas as 10 pages + AppShell migradas para design system. SVGs inline → Lucide React. Spinners CSS duplicados → `<Spinner>`. `confirm()` nativo → `<ConfirmDialog>`. Config tabs → shadcn `Tabs` (ARIA). Toggles → `Switch`. Reports error handling corrigido. `next build` + `tsc --noEmit` green.

---

#### Sprint 12: Fase 5 — Task Queue + Real-time ✅ CONCLUÍDA


| Sprint        | Foco                                                    | Sub-fase     | Tarefas                         | Status |
| ------------- | ------------------------------------------------------- | ------------ | ------------------------------- | ------ |
| S12 (sem 1-3) | Celery+Redis infra + WS progress + concurrency + cancel | 5A + 5B + 5C | 5A.1–5A.8, 5B.1–5B.8, 5C.1–5C.7 | ✅      |


**Checkpoint S12:** ✅ Pipeline via Celery (com fallback Thread). WS progress real-time + polling fallback coexistem. Concurrency limit 1 run/workspace (409 Conflict). Cancelamento stage-boundary via DB flag + Celery revoke. Per-stage retry config. Health check Redis+Celery+DB. 44 novos testes. Docker Compose com Redis. `usePipelineWS` hook + toast Sonner.

---

#### Sprint 13-16: Fase 6 — Frontend Profissional (Core Data Experience) ✅ COMPLETA


| Sprint        | Foco                                                                                                                                        | Sub-fase | Tarefas    | Status |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------- | ------ |
| S13 (sem 1-2) | **Transaction Explorer** (API transações, DataTable, filtros, busca, category override, export, paginação, URL state)                       | 6A       | 6A.1–6A.12 | ✅      |
| S14 (sem 2-3) | **Dashboard** (Recharts, API dashboard, KPIs, 4 charts, alertas, filtros, drill-down → TE) + DateRangePicker                                | 6B       | 6B.1–6B.12 | ✅      |
| S15 (sem 3-5) | **Report React** (component tree, sections, validação L1+L2, history, PDF @media print, CSV/XLSX, data lineage, filtro membro)              | 6C       | 6C.1–6C.12 | ✅      |
| S16 (sem 5-6) | **UX Polish** (dark mode, nav update, LLM config UI, tier badges, review UI, notifications, loading/empty/error, responsive, accessibility) | 6D       | 6D.1–6D.12 | ✅      |


**Checkpoint S13:** ✅ Transaction Explorer funcional. Filtros avançados, busca, category override inline, export CSV/XLSX. Paginação server-side. URL state para drill-down.
**Checkpoint S14:** ✅ Dashboard funcional com 4 charts, KPIs, alertas inteligentes. Drill-down conecta ao TE (6A). Data freshness indicator.
**Checkpoint S15:** ✅ Report viewer com TOC sidebar, print via iframe, export HTML + tabelas XLSX. Hybrid approach (iframe HTML + React chrome).
**Checkpoint S16:** ✅ Dark mode (next-themes). LLM config UI. Notification center com bell badge. Navigation atualizada (Dashboard home, Transações). Tier badges.

---

#### Sprint 16.5: Fase 6.5 — Frontend Testing & Quality Assurance


| Sprint          | Foco                                                                                                           | Sub-fase     | Tarefas                             |
| --------------- | -------------------------------------------------------------------------------------------------------------- | ------------ | ----------------------------------- |
| S16.5a (sem 1)  | Tooling setup (Vitest + MSW + RTL) + unit tests (`format.ts`, `export.ts`, `api.ts`, `utils.ts`, WS hook)      | 6.5A         | 6.5A.1–6.5A.8                       |
| S16.5a (sem 1)  | Integration tests: 10 pages + AppShell + 7 compostos (loading/empty/error/success)                             | 6.5B         | 6.5B.1–6.5B.11                      |
| S16.5b (sem 2)  | Playwright setup + 8 fluxos E2E + smoke checklist + CI integration                                            | 6.5C         | 6.5C.1–6.5C.11                      |


**Checkpoint S16.5a:** Vitest + MSW configurados. ~200 tests (unit + integration) green. Coverage baseline: lib/ ≥80%, pages/ ≥70%. Todas as 10 páginas com testes de 4 estados (loading, empty, error, success). `npm test` <30s.
**Checkpoint S16.5b:** Playwright configurado. ~25-30 E2E tests green cobrindo 8 fluxos críticos. `docs/SMOKE_TEST.md` criado. CI pipeline com Vitest + Playwright. **Frontend tem rede de segurança completa para produção.**

---

#### Sprint 17-19: Fase 7 — Produção + Security + LGPD + Dogfood


| Sprint        | Foco                                                                                         | Sub-fase | Tarefas               |
| ------------- | -------------------------------------------------------------------------------------------- | -------- | --------------------- |
| S17 (sem 1-2) | Docker builds + VPS provisioning + deploy + HTTPS + backup + data migration                  | 7A       | 7A.1–7A.13            |
| S18 (sem 2-4) | Security hardening (encryption, rate limiting, refresh tokens+frontend, audit log) + LGPD + UX produção | 7B | 7B.1–7B.10 |
| S19 (sem 4-6) | CI/CD (com CVE scan) + observabilidade + gap-fill tests backend + telemetria + launch gate | 7C + 7D | 7C.1–7C.7, 7D.1–7D.10 |
| **Dogfood** (sem 7-8) | **Uso real diário. 5+ pipeline runs. Monitorar uptime, erros, storage. Fix bugs encontrados** | 7D.11 | — |


**Checkpoint S17:** Produto no ar (`https://domínio.com`). HTTPS via Traefik. PostgreSQL com backup diário. Docker images otimizadas. Config importada. **Dia 1 em produção.**
**Checkpoint S18:** Dados criptografados at-rest. JWT com refresh token (backend + frontend interceptor). Rate limiting com UX feedback. LGPD compliance (termos, exclusão com UX dedicada, portabilidade com notificação). Audit log. Secret rotation documentada.
**Checkpoint S19:** CI/CD auto-deploy com rollback + CVE scan. ≥85% line coverage backend. Frontend tests (F6.5) verificados em prod DB. Sentry + uptime monitoring. Telemetria básica. Performance baseline. Pre-launch checklist green.
**Checkpoint Dogfood:** 2+ semanas de uso real sem critical bugs. 5+ pipeline runs com 100% success. Backup restore testado em prod. **Produto pronto para beta fechado.**

---

## 8. Decisões Técnicas Pendentes

> Decisões que precisam ser tomadas antes ou durante a execução.


| #   | Decisão                           | Fase | Opções                                                                   | Status                                                                                               |
| --- | --------------------------------- | ---- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| D1  | ORM vs Raw SQL                    | F1   | SQLAlchemy 2.0 (recomendado) / Tortoise / raw                            | **Decidido: SQLAlchemy 2.0**                                                                         |
| D2  | File storage                      | F2   | **Filesystem local por tenant** (F2) / S3 (F7) / MinIO (F7)              | **Decidido: Filesystem (F2)**                                                                        |
| D3  | Auth provider                     | F1   | **Custom JWT (python-jose + bcrypt)** / Auth.js / Clerk                  | **Decidido: Custom JWT**                                                                             |
| D4  | Task queue                        | F5   | **Celery+Redis** / ARQ / Dramatiq                                        | **Decidido: Celery+Redis (ver D29)**                                                                 |
| D5  | Cloud provider                    | F7   | **VPS (Hetzner CX32)** / Railway / Fly.io / AWS                          | **Decidido: VPS CX32 ~$8/mo (4 vCPU, 8GB). Upgradeable para managed (ver D58)**                     |
| D6  | Monorepo vs repos separados       | F0   | **Monorepo** / backend+frontend separados                                | **Decidido: Monorepo**                                                                               |
| D13 | Wrapper pattern na Fase 0         | F0   | Monkey-patch globals / **Parâmetro `root_dir=None` no main()** / Ambos   | **Decidido: Opção B**                                                                                |
| D7  | Criptografia de dados sensíveis   | F7   | **Fernet app-level** / pgcrypto / app-level AES                          | **Decidido: Fernet (consistente com Fase 4 vault)**                                                  |
| D8  | Pricing do premium                | F6   | R$29/mês / R$49/mês / R$99/mês                                           | Pendente                                                                                             |
| D9  | Nome do produto                   | F6   | Fin / FinPlan / outro                                                    | Pendente                                                                                             |
| D10 | Prioridade de novos bancos        | F3+  | Nubank / Inter / Mercado Pago / Open Finance                             | Pendente                                                                                             |
| D11 | Relatório in-app: como renderizar | F6   | iframe / **React components** / server-side render                       | **Decidido: React components (ver D33)**                                                             |
| D12 | Multi-language support            | F6+  | pt-BR only / pt-BR + en                                                  | Pendente                                                                                             |
| D14 | Background execution (Fase 2)     | F2   | `**threading.Thread`** / `asyncio.create_task` / `ProcessPoolExecutor`   | **Decidido: threading.Thread** ✅                                                                     |
| D15 | Senhas de PDF na web              | F2   | **Vault por workspace** / senha por doc no upload / rejeitar protegidos  | **Decidido: Vault** ✅                                                                                |
| D16 | Classificação de docs na web      | F2   | **E0-route automático no upload** / manual pelo user / no pipeline run   | **Decidido: Auto no upload** ✅                                                                       |
| D17 | DB session em background threads  | F2   | **Sync `SessionLocal`** / `asyncio.run()` / `run_in_executor`            | **Decidido: Sync session** ✅                                                                         |
| D18 | Config access em tenant           | F2   | `**config_dir` override em `for_tenant()`** / copiar / symlink           | **Decidido: config_dir** ✅                                                                           |
| D19 | Storage root path                 | F2   | `**Settings.STORAGE_ROOT` (env var)**, default raiz monorepo             | **Decidido: env var + default** ✅                                                                    |
| D29 | Database migrations               | F2   | **Alembic** / raw SQL / no migrations                                    | **Decidido: Alembic** ✅                                                                              |
| D30 | Cancelamento de pipeline          | F2   | **threading.Event cooperativo** / kill thread / no cancel                | **Decidido: Event cooperativo** ✅                                                                    |
| D31 | Vault encryption                  | F2   | **Fernet symmetric** / AES manual / pgcrypto                             | **Decidido: Fernet (cryptography)** ✅                                                                |
| D20 | Config injection no pipeline      | F3   | **Materializar em disco** / `config_overrides` dict / symlinks           | **Decidido: materialize_config()** ✅                                                                 |
| D21 | Scope de configs editáveis        | F3   | 3 core / **5 configs** / tudo                                            | **Decidido: 5 configs (members, categories, pipeline, institutions, layout)** ✅                      |
| D22 | Fallback de config                | F3   | Full override / **Seletivo** / merge                                     | **Decidido: Seletivo (só editados vão para DB)** ✅                                                   |
| D23 | Import/export de config           | F3   | Nenhum / import only / **ambos**                                         | **Decidido: import + export JSON** ✅                                                                 |
| D24 | LLM provider                      | F4   | Anthropic only / abstração custom / **LiteLLM**                          | **Decidido: LiteLLM (proxy universal, 100+ providers)** ✅                                            |
| D25 | API key model                     | F4   | BYOK / plataforma / ambos                                                | **Decidido: BYOK (user traz sua key)** ✅                                                             |
| D26 | Structured output                 | F4   | JSON mode / prompt+parse / **Instructor**                                | **Decidido: Instructor + Pydantic schemas (auto-retry)** ✅                                           |
| D27 | Falha de validação LLM            | F4   | retry→fail / **retry→needs_review** / retry→skip                         | **Decidido: retries → needs_review (review manual via API)** ✅                                       |
| D28 | E7 scope na Fase 4                | F4   | Full E7 / review only / adiar                                            | **Decidido: Full E7 (review + apply + E6-final). Pipeline 100% E2E** ✅                               |
| D29 | Task queue                        | F5   | **Celery+Redis** / ARQ / Dramatiq                                        | **Decidido: Celery+Redis (sync-native, Flower, maduro)**                                             |
| D30 | Real-time progress                | F5   | WebSocket / SSE / **polling+WS coexistem**                               | **Decidido: WS com polling fallback (backward compat)**                                              |
| D31 | Redis scope                       | F5   | Queue only / queue+cache / **queue+pub/sub**                             | **Decidido: Broker + result backend + Pub/Sub (WS events)**                                          |
| D32 | Cancelamento de pipeline          | F5   | **Stage-boundary** / imediato / P2                                       | **Decidido: Stage-boundary (seguro, sem cleanup parcial)**                                           |
| D33 | Report rendering                  | F6   | **React components** / sanitized HTML / iframe                           | **Decidido: React components do E5 JSON. Validação 3 camadas**                                       |
| D34 | Dashboard scope                   | F6   | KPIs only / KPIs+charts / **full (KPIs+charts+alertas)**                 | **Decidido: Dashboard completo com alertas inteligentes**                                            |
| D35 | PDF export                        | F6   | Playwright server-side / html2pdf client / `**@media print` CSS**        | **Decidido: `@media print` + `window.print()` (MVP). Upgrade path → Playwright (F7 se necessário)**  |
| D36 | Billing na Fase 6                 | F6   | Display only / Stripe / **adiar para Fase 7**                            | **Decidido: Adiar. BYOK resolve tier sem billing**                                                   |
| D37 | Chart library                     | F6   | **Recharts** / Nivo / Tremor / Chart.js                                  | **Decidido: Recharts (React-native, declarativo, Tailwind-compat)**                                  |
| D38 | Storage em produção               | F7   | S3/MinIO / **Docker volume local** / managed storage                     | **Decidido: Docker volume (simples, backup via snapshot)**                                           |
| D39 | DB em produção                    | F7   | SQLite / PostgreSQL only / **dual-support (SQLite dev + PG prod)**       | **Decidido: SQLite dev, PG prod. CI testa em PG (mesmo DB que prod). Dual CI descartado**            |
| D40 | Billing na Fase 7                 | F7   | Stripe basic / Stripe full / **adiar para pós-launch**                   | **Decidido: Adiar. BYOK funciona sem billing**                                                       |
| D41 | Reverse proxy                     | F7   | nginx / **Traefik** / Caddy                                              | **Decidido: Traefik (Docker-native, auto-SSL, labels-based)**                                        |
| D42 | Design system timing              | F4.5 | Antes F5 / Início F6 / Gradual                                           | **Decidido: Antes da Fase 5. Fundação que todas as fases seguintes consomem**                        |
| D43 | Component library                 | F4.5 | **shadcn/ui** / MUI / Ant Design / custom                                | **Decidido: shadcn/ui (Radix + Tailwind v4, composable, acessível)**                                 |
| D50 | Design tokens approach            | F4.5 | CSS custom properties / Tailwind config JS / **Tailwind v4 `@theme`**    | ✅ **Implementado: `@theme inline` em globals.css. CSS-first (v4 nativo). Sem tailwind.config.ts**    |
| D51 | Typography                        | F4.5 | System fonts / Inter / **Geist Sans + Geist Mono**                       | ✅ **Implementado: Geist via `next/font/google`. `--font-sans` + `--font-mono`. tabular-nums**        |
| D52 | Icon library                      | F4.5 | SVGs inline / Heroicons / **Lucide React**                               | ✅ **Implementado: Lucide em todas as 10 pages + AppShell. Tree-shaken**                              |
| D53 | Date formatting deps              | F4.5 | `**Intl.DateTimeFormat` nativo** / date-fns / dayjs                      | ✅ **Implementado: `formatPeriod`/`formatMonth`/`formatRange` nativos. date-fns adiado F6**           |
| D54 | Page migration strategy           | F4.5 | Big-bang / **Incremental page-by-page** / Parallel (old+new)             | ✅ **Implementado: Incremental em 4.5C. 11 tasks, build green após cada**                             |
| D44 | Transaction Explorer              | F6   | Core feature / Futuro / Relatório cobre                                  | **Decidido: Core. Sub-fase 6A (primeira). Target de drill-down do Dashboard**                        |
| D45 | Data lineage                      | F6   | P0 drill-down / **P1 tooltip simplificado** / P2 nice-to-have            | **Decidido: Tooltip com fonte (documento, banco, data, método det/LLM)**                             |
| D46 | Mobile strategy                   | F6   | Desktop-first / **Responsivo** / PWA obrigatório                         | **Revisado: Responsivo (F6D.11). PWA diferido para F8 (prematuro para dogfood)**                     |
| D47 | Reconciliation UI                 | F6   | Full reconciliation / **Category override simplificado** / Pipeline-only | **Decidido: Category override inline + flag "editado". Reconciliação full é futuro**                 |
| D48 | Demo mode                         | F8   | No launch / **Sim, pós-launch** / Não precisa                            | **Revisado: Fase 8. Feature de aquisição, não infra. Workspace demo com dados fictícios, read-only** |
| D49 | Email notifications               | F8   | **Digest semanal/mensal** / Real-time / Nenhum                           | **Revisado: Fase 8. Feature de engagement, não infra. Celery periodic task + templates + opt-in**    |
| D55 | Coverage target                   | F7   | 100% line / **≥85% line + ≥95% new code** / 80% overall                  | **Decidido: ≥85% line overall, ≥95% new code, ≥75% branch. 100% em legado é anti-pattern**           |
| D56 | Deploy strategy                   | F7   | Rolling update / Blue-green / manual                                     | **Decidido: Rolling restart com pre-pull + health check + rollback auto. Blue-green real requer 2 VPS (overkill). Downtime <30s aceitável para dogfood** |
| D57 | JWT token lifetime                | F7   | 24h access / **15min access + 7d refresh** / 1h access                   | **Decidido: 15min access + 7d refresh httpOnly cookie. Frontend interceptor com retry queue. Reduz superfície de ataque** |
| D58 | VPS sizing                        | F7   | CX22 (2 vCPU, 4GB, $5) / **CX32 (4 vCPU, 8GB, $8)** / CX42            | **Decidido: CX32. 4GB é apertado com todos containers + deploy overhead. 8GB dá margem confortável** |
| D59 | Docker image security             | F7   | Nenhum scan / **trivy/docker scout no CI** / Snyk                        | **Decidido: trivy ou docker scout (gratuito). Gate: 0 critical/high CVEs. Produto financeiro = zero tolerance** |
| D60 | Secret rotation                   | F7   | Manual / **Dual-key Fernet + natural JWT expiry** / Vault                | **Decidido: Dual-key. Fernet aceita lista de keys. Re-encrypt em background. Documentado no Runbook** |
| D61 | Telemetria                        | F7   | Analytics externo / **DB interno (privacy-first)** / Nenhum              | **Decidido: Tabela UsageMetric no DB. Privacy-first (sem third-party). Suficiente para dogfood analysis** |
| D62 | Frontend testing strategy         | F6.5 | Dentro da F7 / **Fase dedicada (6.5)** / Após produção                   | **Decidido: Fase 6.5 dedicada. Testes antes de produção, não como afterthought. Vitest+RTL+MSW+Playwright** |


---

## 9. Métricas de Sucesso

### Por fase


| Fase | Métrica                                     | Meta                                         | Cobertura backend (line / branch) |
| ---- | ------------------------------------------- | -------------------------------------------- | --------------------------------- |
| F0   | Output diff pré/pós refactoring             | 0 diff                                       | ~30% / —                          |
| F1   | Login → ver relatório funciona              | <3s load                                     | ~40% / —                          |
| F2   | Upload → relatório gerado                   | <5min end-to-end                             | ~55% / ~40%                       |
| F3   | Config UI → relatório correto               | 100% paridade                                | ~65% / ~50%                       |
| F4   | Pipeline premium sem intervenção            | >95% runs sem erro                           | ~75% / ~60%                       |
| F4.5 | Consistência visual cross-page + ARIA audit | ✅ 0 inconsistências. Tabs ARIA. Build green  | ~75% / ~60%                       |
| F5   | Progresso real-time funciona                | <1s latency                                  | ~85% / ~70%                       |
| F6   | Core data experience funcional (dogfood)    | ✅ Dashboard+TE+Report implementados. Dark mode. Notifications. LLM config UI. Export CSV/XLSX. Build green. | ~90% / ~80%                       |
| F6.5 | Frontend testado e confiável                | ~240 FE tests (60 unit + 150 integration + 30 E2E). lib/ ≥80%. pages/ ≥70%. CI gates. Smoke checklist. | ~90% / ~80% (Python inalterado)   |
| F7   | Uptime + security + dogfood validated        | >99.5% uptime, SSL grade A, 0 critical vulns, 2+ weeks dogfood, 5+ pipeline runs 100% success | **≥85% / ≥75%** |


### De produto (longo prazo)


| Métrica                | Meta 3 meses | Meta 6 meses | Meta 12 meses |
| ---------------------- | ------------ | ------------ | ------------- |
| Usuários registrados   | 1 (dogfood)  | 10 (beta)    | 100           |
| Relatórios gerados/mês | 2            | 20           | 200           |
| Bancos suportados      | 11           | 15           | 20+           |
| MRR                    | R$0          | R$0          | R$2.000+      |


---

## 10. Riscos e Mitigações


| #   | Risco                                          | Impacto   | Probabilidade   | Mitigação                                                                                                                                                                       |
| --- | ---------------------------------------------- | --------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | Refactoring quebra pipeline                    | Alto      | ~~Média~~ Baixa | ✅ Mitigado: 136 tests + `_init_config()` pattern não altera lógica interna                                                                                                      |
| R2  | LLM output inconsistente                       | Alto      | ~~Alta~~ Média  | ✅ Parcialmente mitigado: Instructor + Pydantic schemas + validators + needs_review workflow (F4). Retry exponencial + error classification implementados                        |
| R3  | Custo de LLM por run inviável                  | Médio     | Baixa           | ✅ Mitigado: BYOK implementado (F4). Token tracking + cost estimation por call. User controla provedor/modelo                                                                    |
| R4  | Dados sensíveis vazam                          | Crítico   | Baixa           | Criptografia at-rest, HTTPS, audit log, LGPD compliance                                                                                                                         |
| R5  | Parsers quebram com mudança de layout do banco | Alto      | Alta            | Testes com golden files, alertas de parsing error, LLM fallback                                                                                                                 |
| R6  | Escopo cresce demais                           | Alto      | Alta            | Stick to P0 tasks por sprint, cortar P2 se atrasar                                                                                                                              |
| R7  | Complexidade do E5/E6 dificulta refactoring    | Médio     | Alta            | Estratégia "Wrap Don't Rewrite": wrappers finos, lógica interna inalterada. E5 (107KB) e E6 (197KB) por último                                                                  |
| R8  | Mudanças no Open Banking BR                    | Baixo     | Média           | Arquitetura de parsers já suporta novos sources                                                                                                                                 |
| R9  | 100% coverage dos scripts legados é custoso    | ~~Médio~~ | ~~Alta~~        | ✅ Mitigado: Target revisado para ≥85% line overall + ≥95% new code (v2 F7). 100% em legado descartado como anti-pattern. Crescimento orgânico via integration tests             |
| R10 | CI gate atrasa entregas                        | Baixo     | Média           | Gate aplica apenas a código novo (diff coverage ≥95%). Código legado converge gradualmente para 85%+                                                                            |
| R11 | React report diverge do HTML original          | Alto      | Média           | Validação 3 camadas (data accuracy, section completeness, visual regression). Divergência numérica = bug bloqueante (F6)                                                        |
| R12 | VPS single point of failure                    | Médio     | Baixa           | Backup diário (pg_dump + volume snapshot). Upgrade path documentado para Railway/Fly.io. Runbook de restore (F7)                                                                |
| R13 | LiteLLM como dependência externa               | Médio     | Baixa           | LiteLLM é wrapper fino — fallback direto para SDK do provider se necessário. Instructor desacopla da lib (F4)                                                                   |
| R14 | Celery worker crash mid-pipeline               | Médio     | Média           | `acks_late=True` re-executa task. Stages já completos mantidos (idempotência). Health check monitora worker (F5)                                                                |
| R15 | Fase 6 escopo cresce demais                    | ~~Alto~~  | ~~Alta~~        | ✅ Mitigado: Refinamento reduziu de 68→48 tasks, 5→4 sub-fases, ~~286h→~~190h. Items de aquisição (landing, PWA, onboarding) diferidos para F8. Foco em core data experience. Frontend testing separado em F6.5 |
| R16 | Design system retrofitting é custoso           | ~~Médio~~ | ~~Baixa~~       | ✅ Mitigado: Fase 4.5 completa. 10 pages + AppShell migradas (~3.320→5.437 linhas, 21→46 arquivos). shadcn/ui + 7 compostos + design tokens. Fase 6 consome a fundação           |
| R17 | Transaction Explorer performance (>5000 rows)  | Médio     | Baixa           | Paginação server-side (50/page) na F6A. Famílias típicas: 200-500 tx/mês. Virtual scrolling adiado (desnecessário para volumes reais)                                           |
| R18 | PWA offline cache stale/confusing              | Baixo     | Baixa           | Diferido para F8. Quando implementado: `@serwist/next` (substitui `next-pwa` deprecated). Cache TTL curto + banner offline                                                       |
| R19 | Category overrides perdidos em re-run          | Médio     | Alta            | Overrides persistem no DB (não no JSON do pipeline). Re-run aplica overrides sobre novo output. API dedicada (6A.2)                                                             |
| R20 | Alembic migration quebra deploy                | Alto      | Média           | Regra: migrations backward-compatible only (add, never remove/rename). Rollback = fix-forward (nova migration). Testar migration em staging local antes de prod (F7)            |
| R21 | Fernet key rotation corrompe dados             | Crítico   | Baixa           | Dual-key strategy: Fernet aceita lista de keys, decrypta com qualquer. Re-encrypt em background. Runbook com procedimento step-by-step (F7)                                     |
| R22 | First deploy tem dados inconsistentes          | Médio     | Média           | Seed script (7A.12) + import config via API testado. Smoke test end-to-end obrigatório (7A.11). Dogfood 2 semanas valida integridade (F7)                                       |
| R23 | Mock drift (MSW não reflete API real)          | Médio     | Média           | Fixtures derivadas do OpenAPI schema (gen-test-fixtures.py). E2E com backend real como safety net. Revisão pós-sprint de schemas alterados (F6.5)                               |
| R24 | Testes E2E lentos bloqueiam CI                 | Baixo     | Média           | Paralelizar Playwright com `--workers=4`. Fixtures compartilhadas. E2E roda no CI (não no pre-commit). Target <5min total (F6.5)                                                |


---

## 11. Log de Progresso

> Atualizar a cada sprint ou milestone significativo.


| Data       | Evento                        | Notas                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| ---------- | ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-04-13 | Brainstorm inicial            | Decisões: Freemium, Next.js, FastAPI, Hybrid LLM                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-04-13 | Documento de plano criado     | `docs/PRODUCT_PLAN.md` — este arquivo                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 2026-04-13 | Fase 0 refinada               | Diagnóstico técnico detalhado. Estratégia "Wrap Don't Rewrite". 4 sub-fases (0A-0D), 27 tarefas                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 2026-04-13 | D13 decidido: Opção B         | Parâmetro `root_dir` + `_init_config()` pattern. Refinado com análise de module-level globals por script                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 2026-04-14 | Fase 2 refinada               | 4 sub-fases (2A-2D), 37 tarefas. Decisões: pseudo-async, vault senhas, E0-route auto, upload E1/E1.5 JSON                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-04-14 | D2,D14,D15,D16 decididos      | Filesystem local, threading.Thread, vault por workspace, E0-route auto no upload                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-04-14 | Política de testes adotada    | 100% line + 90% branch backend. CI gate a partir de F2. Sprint dedicado S17. Metas progressivas por fase                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 2026-04-14 | D17,D18,D19 decididos         | Sync session para threads, config_dir override para tenants, STORAGE_ROOT env var. 7 problemas F2 resolvidos                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 2026-04-14 | **Fase 0A concluída**         | `pipeline/` package criado. `WorkspaceContext`, `config_loader`. 77 tests existentes green.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 2026-04-14 | **Fase 0B concluída**         | E2, E3, E4, E7 wrappados com `_init_config()` + `root_dir`. `pipeline/stages/` com wrappers. 106 passed, 2 skipped.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 2026-04-14 | **Fase 0C concluída**         | E0s, E5, E5.N, E6, E1.5c, `pipeline_common` wrappados. 121 passed, 2 skipped.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| 2026-04-14 | **Fase 0D concluída**         | `pipeline/orchestrator.py` criado. API pública v0.2.0: `run_pipeline`, `run_from`, `run_stages`. `pyproject.toml`. 136 passed.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| 2026-04-14 | **Fase 0 completa** ✅         | Pipeline 100% importável. Todos os scripts com `_init_config()`. Commit: `f50b954`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 2026-04-14 | **Fase 1 concluída** ✅        | Backend FastAPI + Auth JWT + SQLAlchemy async + SQLite. Frontend Next.js 16 + TS + Tailwind CSS 4. Seed de relatórios existentes. 149 testes (136 pipeline + 13 backend). Commit: `2c2ca4a`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| 2026-04-14 | D3,D6 decididos               | Custom JWT (python-jose + bcrypt direto). Monorepo (`backend/`, `frontend/`, `pipeline/`, `scripts/`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 2026-04-14 | Fase 3 refinada               | 4 sub-fases (3A-3D), 32 tarefas. Decisões: materialize_config(), 5 configs, seletivo, import/export JSON                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 2026-04-14 | D20,D21,D22,D23 decididos     | Materialização em disco, 5 configs editáveis, fallback seletivo, import + export JSON                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 2026-04-14 | Fase 4 refinada               | 4 sub-fases (4A-4D), 34 tarefas. Stack: LiteLLM + Instructor. BYOK. needs_review workflow. Pipeline E2E                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 2026-04-14 | D24,D25,D26,D27,D28 decididos | LiteLLM, BYOK, Instructor, retry→needs_review, Full E7 na Fase 4                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-04-14 | **Sub-fase 2A concluída** ✅   | Alembic + 6 modelos (Document, PasswordVault, PipelineRun, StageLog) + StorageService + VaultService + Vault API. 189 testes green.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 2026-04-14 | **Sub-fase 2B concluída** ✅   | Upload multipart (batch 20), validação, E0-unlock via vault, E0-route classify, JSON E1/E1.5 detect, documents API (CRUD + retry-unlock). 222 testes green.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 2026-04-14 | **Sub-fase 2C concluída** ✅   | PipelineService (background thread + sync session), pipeline API (run/list/status/cancel), from_stage, concurrency guard (409), report linkage pós-E6. 235 testes (99 backend + 136 pipeline).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| 2026-04-14 | Fase 5 refinada               | 3 sub-fases (5A-5C), 23 tarefas. Celery+Redis, WS+polling, cancel stage-boundary, concurrency                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| 2026-04-14 | D29,D30,D31,D32 decididos     | Celery+Redis, WS+polling fallback, Redis pub/sub, cancelamento stage-boundary                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| 2026-04-14 | Fase 6 refinada (v1)          | 4 sub-fases (6A-6D), 36 tarefas. React report com validação 3 camadas, dashboard completo, PDF Playwright. Posteriormente expandida para 68 tasks (5 sub-fases) no UX/Design audit, e refinada para 48 tasks (4 sub-fases) na v2.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-04-14 | D33,D34,D35,D36,D37 decididos | React components, dashboard full, Playwright PDF, billing adiado, Recharts                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-04-14 | Fase 7 refinada (v1)          | 5 sub-fases (7A-7E), 38 tarefas. VPS+Docker+Traefik, LGPD, CI/CD auto-deploy, 100% coverage, dual DB. Posteriormente refinada na v2 (ver abaixo)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-04-14 | D5,D7,D38-D41 decididos       | VPS $5-10/mo, Fernet, Docker volume, dual SQLite+PG, billing pós-launch, Traefik                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-04-14 | **Sub-fase 3A concluída** ✅   | 7 modelos SQLAlchemy (FamilyMember, BankAccount, Category, CategoryKeyword, PipelineConfig, InstitutionConfig, ReportLayout). Alembic migration `da5a6af13e3e`. 17 Pydantic schemas com validação (CPF 11 dígitos, roles, category types, bounds). Workspace model expandido com 5 relationships cascade. 30 testes green.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-04-14 | **Sub-fase 3B concluída** ✅   | 18 endpoints REST em `api/config.py`: CRUD members (+ nested accounts), CRUD categories (+ nested keywords), GET/PUT pipeline/institutions/report-layout (JSON blobs com deep merge), import/export JSON. Fallback seletivo: GET retorna defaults do disco se DB vazio. CPF criptografado at-rest via Fernet. `pyyaml` adicionado para report_layout.yaml. 30 testes de integração green.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-04-14 | **Sub-fase 3C concluída** ✅   | `config_materializer.py`: 5 serializers DB→dict (family_members, categorization, pipeline, institutions, report_layout). `materialize_config()` copia config/ global → tenant, sobrescreve com DB. Integrado em `pipeline_service.py` antes de cada `Thread.start()`. 15 testes unitários green. Total: 310 testes (174 backend + 136 pipeline).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-04-14 | **Fase 3 backend completa** ✅ | Sub-fases 3A+3B+3C concluídas. 5 configs editáveis via API. Materialização integrada no pipeline trigger. 75 novos testes. Frontend: Sub-fase 3D (ver log abaixo).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| 2026-04-14 | **Sub-fase 2D concluída** ✅   | Frontend completo para fluxo core: AppShell com sidebar navigation (4 seções), upload drag-and-drop com XHR progress, documents table (8 colunas, status badges, file icons, bank names, delete), vault CRUD, pipeline trigger com opções (from_stage), progress polling 2s com stage-by-stage bar + expandable errors + cancel, auto-redirect pós-E6, report viewer em iframe. API client expandido (15 funções, types manuais matching backend schemas). `next build` green. 9/11 tasks completas (testes E2E pendentes).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 2026-04-14 | **Sub-fase 3D concluída** ✅   | Frontend config completo: página `/config` com 6 tabs (Members, Categories, Pipeline, Institutions, Layout, Import/Export). Members: CRUD inline com edit-in-place, CPF mascarado, bank accounts nested com add/delete. Categories: filter expense/income, keyword editor, monthly_cap, stats badges. Pipeline: 3 config sections (LLM, File Limits, QA Thresholds) com dirty-save. Institutions: toggle active/inactive + JSON editor avançado. Report Layout: toggle visibilidade + reorder com setas. Import/Export: export download JSON, import com file picker + preview + seleção de seções. API client expandido (30+ funções). Sidebar com 5 nav items. `tsc --noEmit` green. 8/10 tasks completas (E2E → F6.5). **Fase 3 100% completa.**                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-04-14 | **Sub-fase 4A concluída** ✅   | `LLMConfig` + `StageReview` models com Alembic migration. `LLMService` (LiteLLM + Instructor, retry exponencial, error classification em 4 categorias, token tracking + cost estimation). `DocumentTextExtractor` (PDF/XLSX/CSV/JSON/TXT→text). 4 Pydantic output schemas (`MembersExtractOutput`, `BaselinePatrimonialOutput`, `LLMExtractOutput`, `E7ReviewOutput`). 4 prompt templates (system+user por stage). 5 API endpoints LLM (GET/PUT/DELETE config, POST test, GET tier). API key mascarada no response. `materialize_config()` estendido para LLM config. 52 novos testes (models + API + service).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 2026-04-14 | **Sub-fase 4B concluída** ✅   | 3 LLM stage runners: `e1.py` (member extraction), `e15.py` (baseline patrimonial), `e2_llm.py` (docs sem parser det.). Cada runner: find docs → extract text → call LLM → validate → save JSON. `validators.py` com `validate_e1_output`, `validate_e15_output`, `validate_e2_llm_output` (compatibilidade downstream). Orchestrator atualizado (`_get_stage_runner` para E1, E1.5, E2-llm). 67 novos testes (48 stage unit + 19 golden file snapshots). 4 golden files em `tests/fixtures/llm_golden/`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 2026-04-14 | **Sub-fase 4C concluída** ✅   | `e7_review_llm.py` — E7-review LLM stage runner (persona consultor financeiro sênior, analisa E5+E7-crossval, gera insights/recommendations/score_adjustments/narratives). Orchestrator registra E7-review. FULL_ORDER completo: E1→E1.5→E1.5c→E2-llm→E2-fat→E2-ext→E3→E4→E5→E5.N→E6→E7-crossval→E7-review→E7-apply→E6-final. Golden file + snapshot tests para E7-review.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-04-14 | **Sub-fase 4D concluída** ✅   | Tier detection via `LLMConfig` existência (async query no API handler). `pipeline_service.py`: auto-skip free tier (`skipped_free_tier`), needs_review handling (valida output → cria `StageReview` → pausa pipeline), `resume_pipeline_run` (verifica reviews resolvidas → nova thread). `PipelineRunStatus` expandido (+needs_review, +resuming). `PipelineStageStatus` expandido (+skipped_free_tier, +needs_review). 3 novos endpoints: `POST /runs/{id}/resume`, `GET /runs/{id}/reviews`, `POST /runs/{id}/reviews/{review_id}`. `StageReviewResponse` + `StageReviewActionRequest` schemas. 14 novos testes. UI de LLM config/review adiada para Fase 6.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 2026-04-14 | **Fase 4 completa** ✅         | 4 sub-fases (4A-4D) concluídas. 16 modelos SQLAlchemy. 7 routers FastAPI. 444 testes (240 backend + 204 pipeline), 0 failures, 2 skipped. Pipeline Premium (FULL_ORDER) funcional com LLM stages. Pipeline Free inalterado. BYOK multi-provider. needs_review → resume workflow. Dependências: litellm, instructor, pdfplumber.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 2026-04-14 | **UX/Design audit**           | Análise de requisitos de design/UX para produto financeiro profissional. Adições: **Fase 4.5** (Design System Foundation: tokens, shadcn/ui, componentes financeiros, formatação padronizada). **Fase 6 expandida** de 36→68 tasks (posteriormente refinada para 48 na v2). **Fase 7** expandida: email digest, demo mode. 8 novas decisões (D42-D49). 5 novos riscos (R15-R19).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| 2026-04-14 | **Fase 4.5 refinada**         | Deep audit do frontend revelou: Tailwind v4 CSS-first (sem `tailwind.config.ts`), zero fonts, zero tokens, spinner duplicado 10x, botões inconsistentes, `confirm()` nativo, tabs sem ARIA, `format.ts` com classes Tailwind hardcoded, reports list com silent error. **Refinamentos:** (1) Reestruturada de 2→3 sub-fases (4.5A tokens+fonts, 4.5B shadcn+components, 4.5C page migration). (2) Corrigido approach de tokens: `@theme inline` em vez de `tailwind.config.ts`. (3) Adicionado font setup (Geist Sans+Mono via `next/font`). (4) Removidos componentes prematuros (DataTable→F6E, DateRangePicker→F6A, SourceTooltip→F6B). (5) Removido `cmdk` das deps (→F6D). (6) Adicionado `<Spinner>`, `<PageHeader>`, `<ConfirmDialog>`. (7) Page migration explicitada task por task (11 tasks). (8) Critérios de aceite expandidos (16 critérios vs 7). 5 novas decisões (D50-D54). Total: 25 tasks (vs 16 original). Duração: 2 semanas (vs 1-2).                                                                                                                                                                                                                                                                                                                                                                                                                        |
| 2026-04-14 | **Fase 4.5 completa** ✅       | 3 sub-fases (4.5A-4.5C) executadas. **4.5A:** Geist Sans+Mono via `next/font/google`, `globals.css` com `@theme inline` (30+ tokens oklch light/dark), paleta financeira semântica (gain/loss/alert/info), 12 chart colors, `format.ts` com `formatCurrency`/`formatPercent`/`formatDelta`/`formatCompact`/`formatPeriod`/`formatMonth`/`formatRange` + status maps migrados para `{ label, variant }` sem Tailwind hardcoded, `cn()` utility. **4.5B:** shadcn/ui v4 init (base-ui/react), 16 primitivos instalados (button, input, label, select, textarea, card, badge, table, tabs, switch, alert-dialog, dialog, sheet, tooltip, separator, skeleton, sonner), 7 compostos (`StatusBadge`, `Spinner`, `EmptyState`, `Delta`, `KPICard`, `PageHeader`, `ConfirmDialog` + `useConfirmDialog` hook). **4.5C:** 10 pages + AppShell migradas. SVG icons → Lucide React. Spinners CSS duplicados → `<Spinner>`. `confirm()` nativo → `<ConfirmDialog>`. Config tabs → shadcn `Tabs` (ARIA). Toggles → `Switch`. Reports list `.catch(()=>{})` → error state. `next build` + `tsc --noEmit` green. Dependências: clsx, tailwind-merge, lucide-react, class-variance-authority, @radix-ui/*, tw-animate-css, @base-ui/react.                                                                                                                                                        |
| 2026-04-14 | **Sub-fase 5A concluída** ✅   | `docker-compose.yml` com Redis 7-alpine (appendonly, healthcheck). Celery app (`worker.py`): broker+backend Redis, JSON serializer, `task_track_started`, `acks_late`, concurrency=2, time_limit=3600s. `run_pipeline_task` como `@celery_app.task(bind=True)` — lógica idêntica ao thread anterior com: events Pub/Sub (`stage_started/completed/failed/skipped`, `needs_review`, `run_completed/failed/cancelled`), cancellation check via DB entre stages, `celery_task_id` salvo no `PipelineRun`. `pipeline_service.py` migrado: `task.delay()` com fallback para Thread se Redis indisponível. `resume_pipeline_run` spawna nova Celery task. Health check expandido: Redis ping + Celery worker inspect + DB connect. Alembic migration `b5c6d7e8f9a0` (add `celery_task_id`). Deps: celery[redis]>=5.4.0, redis>=5.0.0, websockets>=12.0.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 2026-04-14 | **Sub-fase 5B concluída** ✅   | WebSocket endpoint `WS /api/pipeline/runs/{id}/ws` com JWT auth via query param. Subscribe Redis Pub/Sub `pipeline:{run_id}`, forward JSON events, heartbeat 15s, auto-close em run terminal events. `events.py` schema: `PipelineEvent`, `StageEvent`, `RunEvent`, `ErrorEvent` (Pydantic). Frontend: `usePipelineWS` hook (auto-connect, exponential backoff reconnect max 3x, fallback to polling). Pipeline page reescrita: WS real-time progress + polling coexistem, WS indicator (green dot), progress bar animada (pulsing current, green ✓, red ✗, amber ⚠, gray ⊘), toast via Sonner ("Relatório gerado!" + action button), needs_review banner com botão "Revisar". `Toaster` adicionado ao root layout. `api.ts` atualizado: PipelineEvent type, needs_review/resuming/skipped_free_tier statuses.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| 2026-04-14 | **Sub-fase 5C concluída** ✅   | Concurrency limit (já existia Fase 2, mantido): 409 Conflict se run ativo. Stage-boundary cancellation: `cancel_pipeline_run` seta status=cancelled no DB + revoke Celery task (soft) + publica `run_cancelled` via Redis. Retry config (`retry_config.py`): `StageRetryConfig(max_retries, retryable_errors, delay, backoff)`. LLM stages (E1, E1.5, E2-llm, E7-review): 1-2 retries em timeout/rate_limit/503/429. Det. stages: 0 retries. Cancel button com `ConfirmDialog` ("etapa atual completa, stages anteriores mantidos"). 44 novos testes: `test_events.py` (14), `test_pipeline_task.py` (10), `test_pipeline_phase5.py` (12), `test_retry_config.py` (8).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 2026-04-14 | **Fase 5 completa** ✅         | 3 sub-fases (5A-5C) concluídas. Pipeline via Celery (com fallback Thread). Redis Pub/Sub events. WebSocket real-time progress. Polling fallback backward-compat. Stage-boundary cancel. Per-stage retry config. Health check expandido. 16 modelos + 1 novo campo. 8 routers (+ WS). ~300 testes backend + ~204 pipeline. Deps: celery[redis], redis, websockets. Docker Compose com Redis. **Próxima: Fase 6 (Frontend Profissional).** → ✅ Concluída.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| 2026-04-14 | **Fase 7 refinada (v2)**      | Análise executiva (PM/CTO/CEO/Design) da Fase 7 identificou 7 problemas críticos: (1) mistura de infra + features de growth + QA numa fase, (2) meta 100% line coverage anti-pattern para ~14K linhas legado, (3) estimativas 2-3x otimistas (e.g. DELETE /account 4h→8h, refresh tokens 3h→10h), (4) itens críticos de produção ausentes (zero-downtime deploy, performance baseline, rollback automático), (5) dual DB testing em CI sem valor, (6) audit log sub-priorizado como P1 (é requisito LGPD Art.37), (7) sub-fase 7D era "junk drawer" com 9 tasks heterogêneas. **Reestruturação:** 5→4 sub-fases, 38→37 tasks, ~~3-4→~~5-6 semanas, 2→3 sprints. **Mudanças estruturais:** (1) Fundiu 7A+7B em 7A (Docker+Deploy, valor end-to-end). (2) Promoveu audit log para P0. (3) Email digest + demo mode → Fase 8 (growth features fora do critical path). (4) Flower → Fase 8. (5) Coverage target: ≥85% line overall + ≥95% new code + ≥75% branch (não 100%). (6) CI testa em PostgreSQL only (não dual). **Novas tasks:** rollback automático (7C.3), performance baseline (7D.7), pre-launch checklist (7D.9), gen-secrets.sh (7A.5), restore-backup.sh (7A.10). **Estimativas corrigidas:** refresh tokens 3h→10h, DELETE cascade 4h→8h, Fernet expansion 4h→6h, gap-fill maiores 10h→12h. 3 novas decisões (D55-D57).                                              |
| 2026-04-14 | **Fase 6 refinada (v2)**      | Análise executiva (PM/CTO/CEO/Design) da Fase 6 original identificou 7 problemas de produto, 5 técnicos, 4 de UX. **Reestruturação:** 68→48 tasks, 5→4 sub-fases, ~~286h→~~190h, 8→6 semanas. **Reordenação:** Transaction Explorer (6A) primeiro (era 6E última), Dashboard (6B) segundo, Report React (6C), UX Polish (6D). Rationale: TE é o target de drill-down do Dashboard — construí-lo primeiro elimina dead-ends. **Diferidos para F8:** landing page (zero users externos), PWA (prematuro + `next-pwa` deprecated), onboarding wizard (sem user research), command palette (nice-to-have), Framer Motion animations, SEO, FAQ, config audit log, report comparison, shareable links, bulk actions, Lighthouse audit. **Mudanças técnicas:** (1) PDF export: `@media print` MVP em vez de Playwright server-side (pesado para VPS). (2) Validação report: L1+L2 automatizados como CI gates, L3 (visual diff) rebaixado para spot-check manual (screenshot diff é frágil). (3) Paginação server-side (50/page) em vez de virtual scrolling (famílias típicas: 200-500 tx/mês). (4) Redis cache removido do Dashboard API (prematuro para 1 user). (5) Category override consolidado em 6A (era duplicado em 6C+6E). (6) Dark mode movido para início de 6D (novos componentes testados em ambos os modos). 3 novas deps (recharts, date-fns, xlsx) vs 8 originais. |
| 2026-04-14 | **Fase 7 refinada (v3)**      | Análise executiva (PM/CTO/CEO/Design) da Fase 7 v2 identificou 10 gaps: (1) "launch" indefinido (falta progressão Dogfood→Beta→GA com gates), (2) "blue-green" no VPS $5/4GB é contradição física (2 stacks simultâneos precisam 8GB+ — corrigido para rolling restart + VPS CX32 8GB), (3) refresh tokens (7B.4) subestimado 10h→16h (frontend interceptor + retry queue + race condition handling não contabilizados), (4) falta rotação de secrets (Fernet dual-key strategy + JWT natural expiry), (5) falta Docker image CVE scanning no CI (trivy/docker scout, gate 0 critical), (6) falta projeção de custo mensal (~$9-10/mo), (7) falta UX de produção (rate limit toast, LGPD delete stepper, export notification, maintenance page), (8) falta plano de data migration dev→prod (seed script + config import via API), (9) falta backward-compatible migration policy para deploys sem downtime, (10) falta telemetria básica para dogfood analysis. **Mudanças:** 37→42 tasks, 5-6→6-8 semanas (inclui 2 sem dogfood obrigatório), 3→3 sprints + dogfood period. **Novas tasks:** 7A.12 (data migration), 7B.10 (UX produção), 7D.9 (telemetria), 7D.11 (dogfood period). **Estimativas corrigidas:** 7B.4 10h→16h (inclui frontend), 7C.1 5h→6h (inclui CVE scan), 7C.7 4h→5h (inclui secret rotation + first-week checklist). **Critérios de aceite:** separados em gates DEPLOY (técnico) e LAUNCH (validação real). Dogfood obrigatório: 2+ semanas, 5+ pipeline runs, zero critical bugs. **Novas decisões:** D58-D61 (VPS sizing, image security, secret rotation, telemetria). **Novos riscos:** R20-R22 (Alembic deploy, Fernet rotation, first deploy data). |
| 2026-04-14 | **Fase 6.5 refinada**          | Análise executiva (PM/CTO/CEO/Design) identificou gap crítico: frontend com ~5.800 linhas, 47 arquivos, 25 componentes, zero testes. **Nova fase 6.5** inserida entre F6 (features) e F7 (deploy). **Estrutura:** 3 sub-fases (6.5A unit, 6.5B integration, 6.5C E2E), 30 tasks, 2 semanas, ~50h. **Estratégia:** Pirâmide de 4 camadas (L1 unit → L2 integration → L3 E2E → L4 smoke manual). **Tooling:** Vitest + RTL + MSW + Playwright. **Meta:** ~240 tests FE. Coverage: lib/ ≥80%, pages/ ≥70%. CI gates: Vitest bloqueia merge, Playwright bloqueia deploy. **Reorganização:** Items de aquisição/marketing antes em "Fase 6.5" (landing, PWA, onboarding, animations, command palette) movidos para Fase 8. Testes frontend antes em F7D (7D.4-7D.6) movidos para F6.5. 2 novos riscos (R23, R24). |
| 2026-04-14 | **Fase 6 completa** ✅         | 4 sub-fases (6A-6D) implementadas. **Backend (pré-existente das fases 5-6A/B planning):** 3 novos routers (transactions, dashboard, notifications), 2 novos modelos (TransactionOverride, Notification), 3 services (transaction_service, dashboard_service, alert_service), Alembic migration `c7d8e9f0a1b2`. **6A — Transaction Explorer:** `GET /api/transactions` (8 filtros: member/bank/category/date_from/date_to/value_min/value_max/search + paginação server-side 50/page), `POST /api/transactions/{hash}/override` (category override com upsert), `DELETE /api/transactions/{hash}/override`. Frontend: página `/transactions` com search debounce 300ms, filter panel colapsável (date range, bank, category, member, value range), summary bar (receitas/despesas/saldo/count), table responsiva (6 colunas com inline category override via select, badge "editado", undo), pagination, export CSV/XLSX (via `xlsx` library), URL state persistence via `useSearchParams`. **6B — Dashboard:** `GET /api/dashboard` retorna KPIs + charts + alerts do E5 JSON. Frontend: página `/dashboard` com 4 KPICards (Score, Patrimônio, Taxa Poupança, Receita vs Despesa) + skeletons, 4 gráficos Recharts (BarChart receita/despesa mensal, PieChart despesas por categoria c/ donut, PieChart composição patrimonial, BarChart investimentos por classe), drill-down para Transaction Explorer (click em bar→date range, click em pie slice→category filter), alerts com severity (critical/warning), data freshness badge, refresh button. **6C — Report React:** Report viewer com header bar (back, print, download HTML, export tabelas XLSX), sidebar TOC com 9 seções (scrollIntoView), iframe HTML mantido como engine de renderização (hybrid approach), `@media print` CSS (no-print elements, page breaks, color-adjust), utility `lib/export.ts` (exportToCSV com BOM+semicolon, exportToXLSX com auto-column-widths). **6D — Dark Mode + Navigation + LLM Config + Notifications:** `next-themes` ThemeProvider (system/light/dark, `suppressHydrationWarning`), `ThemeToggle` component (cycle light→dark→system, tooltipped, base-ui render prop). Navigation atualizada: Dashboard como home (primeiro item), Transações adicionado, Vault removido do nav top-level (→Config). `NotificationCenter` component: bell icon com unread badge (red dot, max "9+"), Sheet com notification list (severity icons, relative time, mark all read), polling 30s. `LLMTab` no Config: form provedor/modelo/API key (masked+toggle), test connection, delete com ConfirmDialog, tier badge (Free/Premium). Home redirect `/ → /dashboard`. **Build:** `next build` zero errors, 12 routes (/, config, dashboard, documents, login, pipeline, register, reports, reports/[id], transactions, vault, _not-found). **Stack adicionada F6:** recharts 3.8, date-fns 4.1, xlsx 0.18, next-themes 0.4. **Arquivos criados:** 7 novos (transactions/page.tsx, dashboard/page.tsx, ThemeToggle.tsx, NotificationCenter.tsx, LLMTab.tsx, lib/export.ts, print CSS). **Arquivos modificados:** 7 (api.ts +230 linhas, AppShell.tsx reescrito, layout.tsx +ThemeProvider, config/page.tsx +LLM tab, reports/[id]/page.tsx reescrito, globals.css +print, page.tsx redirect). 18 modelos SQLAlchemy. 11 routers FastAPI. ~48 tasks implementadas. |


---

## Apêndice A: Tiers Freemium

### Free — "Consolidação Determinística"


| Funcionalidade                                | Etapa       |
| --------------------------------------------- | ----------- |
| Upload de documentos                          | Web UI      |
| Desbloqueio de PDFs                           | E0-unlock   |
| Auditoria de integridade                      | E0-audit    |
| Roteamento automático (determinístico)        | E0-route    |
| Extração de extratos e faturas (11 bancos)    | E2          |
| Reconciliação e deduplicação                  | E3          |
| Categorização automática (300+ keywords)      | E4          |
| Análise financeira (patrimônio, score, fluxo) | E5          |
| Narrativas determinísticas                    | E5.N        |
| Relatório HTML completo                       | E6          |
| Cross-validation (14 checks)                  | E7-crossval |


**Limitações:** 1 relatório/mês. Sem LLM. Sem histórico.

### Premium — "Inteligência Financeira Completa"

Tudo do free, mais:


| Funcionalidade                     | Etapa     |
| ---------------------------------- | --------- |
| Extração LLM de dados pessoais     | E1, E1.5  |
| Extração LLM de investimentos/IRPF | E2-llm    |
| Review holístico com persona       | E7-review |
| Refinamentos automáticos           | E7-apply  |
| Relatórios ilimitados              | —         |
| Histórico + comparação temporal    | —         |
| Export PDF                         | —         |


**LLM:** BYOK (chave própria) ou incluso na assinatura.

---

## Apêndice B: Custo Estimado de Infraestrutura

### Dev (local)

- SQLite + filesystem: R$0
- Docker Desktop: R$0

### Dogfood / Beta (Fase 7 — VPS self-managed)


| Serviço            | Estimativa    | Provider                 |
| ------------------ | ------------- | ------------------------ |
| VPS (all-in-one)   | ~$8/mês       | Hetzner CX32 (4 vCPU, 8GB RAM) |
| Domínio            | ~$1/mês       | Registro.br (.com.br)    |
| Sentry             | $0            | Free tier (5K errors/mo) |
| UptimeRobot        | $0            | Free tier (50 monitors)  |
| GitHub Actions     | $0            | Free tier (2000 min/mo)  |
| **Total Dogfood**  | **~$9-10/mês** |                         |

### Staging / MVP (managed — upgrade path)


| Serviço            | Estimativa      | Provider                 |
| ------------------ | --------------- | ------------------------ |
| PostgreSQL         | $0–7/mês        | Railway / Neon free tier |
| Backend (FastAPI)  | $5–10/mês       | Railway / Fly.io         |
| Frontend (Next.js) | $0/mês          | Vercel free tier         |
| Redis              | $0–5/mês        | Upstash free tier        |
| Storage (uploads)  | $1–5/mês        | S3 / R2                  |
| **Total MVP**      | **~$10–25/mês** |                          |


### Produção (100 usuários)


| Serviço            | Estimativa       | Provider              |
| ------------------ | ---------------- | --------------------- |
| PostgreSQL         | $15–30/mês       | Railway / RDS         |
| Backend            | $20–40/mês       | Railway / Fly.io      |
| Frontend           | $0–20/mês        | Vercel                |
| Redis              | $5–10/mês        | Upstash / ElastiCache |
| Storage            | $5–20/mês        | S3                    |
| Domínio + SSL      | $10/mês          | Cloudflare            |
| Sentry             | $0–26/mês        | Free tier             |
| **Total Produção** | **~$55–160/mês** |                       |


---

## Apêndice C: Como Rodar (Setup Local)

### Pré-requisitos


| Ferramenta       | Versão mínima | Verificação              |
| ---------------- | ------------- | ------------------------ |
| Python           | 3.9+          | `python3 --version`      |
| Node.js          | 18+           | `node --version`         |
| npm              | 9+            | `npm --version`          |
| Docker + Compose | 24+ / v2      | `docker compose version` |
| Git              | 2.30+         | `git --version`          |


> **Python 3.9+ compatível** — type hints usam `Optional[X]` (compatível com 3.9). Python 3.10+ também suportado.
>
> **Docker Compose plugin:** Se `docker compose` retornar "unknown command", instale o plugin:
> ```bash
> mkdir -p ~/.docker/cli-plugins
> curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
>   -o ~/.docker/cli-plugins/docker-compose
> chmod +x ~/.docker/cli-plugins/docker-compose
> ```
> O Docker Desktop deve estar **aberto** (o daemon precisa estar rodando): `open /Applications/Docker.app` no macOS.

### 1. Clone e setup do backend

```bash
# Clone
git clone <repo_url> fin-current
cd fin-current

# Virtualenv (recomendado)
# IMPORTANTE: Se já existir um .venv corrompido (ex: paths de outro diretório), delete primeiro:
#   rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Dependências Python
pip install -r backend/requirements.txt

# Variáveis de ambiente (opcional — defaults funcionam para dev)
# Criar backend/.env se necessário:
#   DATABASE_URL=sqlite+aiosqlite:///./fin.db
#   SECRET_KEY=uma-chave-secreta-longa
#   REDIS_URL=redis://localhost:6379/0
#   STORAGE_ROOT=./storage
```

### 2. Redis (via Docker Compose)

```bash
# Garantir que Docker Desktop está aberto (macOS):
open /Applications/Docker.app

# Subir Redis (necessário para Celery + WebSocket events)
docker compose up -d redis

# Verificar
docker compose ps
# redis  running  0.0.0.0:6379->6379/tcp (healthy)
```

> **Sem Docker?** Instale Redis nativamente (`brew install redis` no macOS) e rode `redis-server`.

### 3. Database (Alembic migrations)

```bash
# Rodar de dentro de backend/ (alembic.ini está lá)
cd backend
alembic upgrade head

# (Opcional) Seed com dados de exemplo
python seed_db.py

cd ..
```

### 4. Subir o Backend (FastAPI)

```bash
# Terminal 1: API server — rodar da RAIZ do projeto (fin-current/)
# Os imports usam `backend.app.xxx`, então o Python precisa ver o pacote `backend`
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Health check
# curl http://localhost:8000/api/health
# → {"status":"healthy","database":"ok","redis":"ok","celery_workers":0}
```

### 5. Subir o Celery Worker

```bash
# Terminal 2: Celery worker — rodar da RAIZ do projeto (fin-current/)
celery -A backend.app.worker:celery_app worker --loglevel=info --concurrency=2

# Verificar que worker registrou a task:
# [tasks]
#   . backend.app.tasks.pipeline_task.run_pipeline_task
```

> **Sem Celery?** O backend tem fallback automático para `threading.Thread` se Redis não estiver disponível. O pipeline roda normalmente, apenas sem eventos Pub/Sub e sem WebSocket real-time (polling continua funcionando).

### 6. Subir o Frontend (Next.js)

```bash
# Terminal 3: Frontend dev server
cd frontend
npm install
npm run dev

# Acesse: http://localhost:3000
```

### 7. Workflow típico de desenvolvimento

```bash
# Tudo rodando em paralelo (4 terminais), todos a partir da raiz (fin-current/):

# T1: Redis
docker compose up redis

# T2: Backend API (da raiz — imports usam backend.app.xxx)
uvicorn backend.app.main:app --reload --port 8000

# T3: Celery worker (da raiz)
celery -A backend.app.worker:celery_app worker --loglevel=info

# T4: Frontend
cd frontend && npm run dev
```

### 8. Rodar testes

```bash
# Testes do pipeline (sem dependências externas)
pytest tests/ -v

# Testes do backend (usa SQLite in-memory, sem Redis necessário)
cd backend
pytest tests/ -v

# Testes específicos de uma fase
pytest backend/tests/test_events.py -v          # Fase 5: Redis events
pytest backend/tests/test_pipeline_task.py -v   # Fase 5: Celery task
pytest backend/tests/test_pipeline_phase5.py -v # Fase 5: integration

# Com coverage
pytest backend/tests/ --cov=app --cov-report=term-missing
```

### 9. Pipeline via CLI (sem web server)

O pipeline original continua funcionando via CLI independente da web:

```bash
# Reset completo (etapas determinísticas)
python scripts/e_reset.py

# Reset parcial a partir de E3
python scripts/e_reset.py --from E3

# Preview sem mudanças
python scripts/e_reset.py --dry-run

# Reset interativo (para em walls LLM)
python scripts/e_reset.py --move-to-inbox --interactive

# Commit + push
python scripts/e_save.py -m "mensagem"
```

### Portas e URLs


| Serviço      | URL                                                       | Notas                       |
| ------------ | --------------------------------------------------------- | --------------------------- |
| Frontend     | `http://localhost:3000`                                   | Next.js dev server          |
| Backend API  | `http://localhost:8000`                                   | FastAPI (docs em `/docs`)   |
| API Docs     | `http://localhost:8000/docs`                              | Swagger UI interativo       |
| Health Check | `http://localhost:8000/api/health`                        | Status de DB, Redis, Celery |
| Redis        | `localhost:6379`                                          | Docker Compose service      |
| WebSocket    | `ws://localhost:8000/api/pipeline/runs/{id}/ws?token=JWT` | Real-time progress          |


### Variáveis de ambiente


| Variável       | Default                               | Descrição                                  |
| -------------- | ------------------------------------- | ------------------------------------------ |
| `DATABASE_URL` | `sqlite+aiosqlite:///./fin.db`        | URL do banco (SQLite dev, PostgreSQL prod) |
| `SECRET_KEY`   | `dev-secret-key-change-in-production` | Chave para JWT signing                     |
| `REDIS_URL`    | `redis://localhost:6379/0`            | URL do Redis (Celery broker + Pub/Sub)     |
| `STORAGE_ROOT` | `./storage`                           | Diretório raiz de storage por tenant       |


### Troubleshooting


| Problema | Causa provável | Solução |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'backend'` | Rodando uvicorn/celery de dentro de `backend/` | Rodar da **raiz** do projeto: `uvicorn backend.app.main:app` |
| `ModuleNotFoundError: celery` | Deps não instaladas | `pip install -r backend/requirements.txt` |
| `.venv/bin/pip: No such file or directory` (path antigo) | venv corrompido (copiado ou projeto moveu de diretório) | `rm -rf .venv && python3 -m venv .venv` |
| `docker: unknown command: docker compose` | Docker Compose plugin não instalado | Instalar plugin (ver Pré-requisitos acima) |
| `Cannot connect to the Docker daemon` | Docker Desktop não está aberto | `open /Applications/Docker.app` (macOS) e aguardar daemon inicializar |
| `WARN: attribute 'version' is obsolete` | `docker-compose.yml` com `version:` (deprecated no Compose v2) | Remover a linha `version: "3.9"` do `docker-compose.yml` |
| `ConnectionRefusedError` (Redis) | Redis não está rodando | `docker compose up -d redis` |
| `no healthy upstream` (frontend) | Backend não está rodando | Iniciar uvicorn na porta 8000 |
| Pipeline roda mas sem WS events | Celery worker não está rodando | Iniciar o worker Celery (ou usar fallback Thread) |
| `alembic: Target database not up to date` | Migrations pendentes | `cd backend && alembic upgrade head` |
| Frontend mostra "Sem relatórios" | Nenhum pipeline rodou ainda | Fazer upload de documentos e rodar pipeline |
| WebSocket desconecta imediatamente | JWT inválido ou expirado | Fazer login novamente (token renova) |


---

*Fim do documento. Atualizar conforme o projeto evolui.*