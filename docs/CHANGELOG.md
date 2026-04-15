# Fin — Changelog

> Log cronológico reverso do que foi entregue. Atualizar por sprint/milestone.

---

## [Unreleased]

Trabalho em andamento: preparação para **F7 (Produção + LGPD + Ops)**.

### Bug fixes 2026-04-14/15

**Context:** Passagem de QA em todo o sistema. 14 bugs identificados, 12 corrigidos (BUG-010 mantido by-design, BUG-013 adiado para F7).

**Critical:**
- [BUG-001] Celery worker não registrava task `pipeline.run` — `autodiscover_tasks` procurava `tasks.py`, mas o arquivo real é `pipeline_task.py`. Fix: `include=["backend.app.tasks.pipeline_task"]` em `worker.py`.
- [BUG-002] `ModuleNotFoundError: No module named 'pipeline'` no Celery fork pool worker. Fix: `sys.path.insert(0, project_root)` em `worker.py` **e** dentro da task (fork workers não herdam `sys.path`).

**High:**
- [BUG-003] Pipeline ficava "pending" indefinidamente quando Celery task crasheava fora do try-catch. Fix: `on_failure` callback marca run como `failed`.
- [BUG-004] Config members fallback expunha CPFs reais do JSON global. Fix: `cpf=None` no fallback (nunca expor).
- [BUG-005] Vault não acessível pela navegação. Fix: adicionado ao `NAV_ITEMS` do AppShell.

**Medium:**
- [BUG-006] Botão "Revisar" na pipeline page era inerte. Fix: chama `resumePipelineRun()` + toast.
- [BUG-007] Pipeline sempre usava `skip_llm=true`. Fix: detecta tier via `getLLMTier()`, envia `skip_llm: !isPremium`.
- [BUG-008] NotificationCenter silenciava erros. Fix: `toast.error()` em fetch e markRead.
- [BUG-009] Export CSV exportava só página atual. Fix: novo endpoint `GET /api/transactions/export` server-side (todas as transações filtradas, BOM UTF-8).

**Low:**
- [BUG-011] Dead imports (`BarChart3`, `exportToXLSX`). Fix: removidos.
- [BUG-012] `deleteNotification` existia em api.ts mas sem UI. Fix: botão X por item no NotificationCenter.
- [BUG-014] POST /config/members/accounts não incluía `label`. Fix: campo adicionado ao modelo, schema e endpoint.
- [BUG-015] **Capa do relatório vazia para workspaces multi-tenant.** `serialize_family_members` no `config_materializer.py` perdia `familia.sobrenome` ao sobrescrever o `family_members.json` materializado — workspaces com membros no DB tinham `{{COVER_FAMILIA}}` renderizado como string vazia. Fix: nova coluna `Workspace.family_surname` (migration `d3f4e5a6b7c8`), serializer/exporter/importer preservam o campo, endpoint `GET/PATCH /api/config/workspace`, input "Sobrenome da família" em `MembersTab`. Round-trip UI → DB → materialize → E6 cover funciona.

### Bugs operacionais corrigidos durante dogfood (2026-04-15)

- **parse_args() lendo `sys.argv` do Celery** — 6 scripts (e0_audit, e0_unlock, e0_route, e15_consolidate, e2_extract, e7_review) faziam `parser.parse_args()` que dentro do Celery fork worker lia os argumentos do comando `celery` causando crash. Fix: `parse_args([] if root_dir else None)`.
- **SystemExit matando Celery worker** — scripts legados usam `sys.exit(1)` que em fork pool mata o processo inteiro. Fix: `_run_stage()` do orchestrator captura `SystemExit` → converte para `StageResult(success=False)`.
- **Stages dependentes de LLM não skipavam graciosamente** — E1.5c crasheava sem baseline (free tier), E7-apply crasheava sem review. Fix: ambos skippam graciosamente se dados ausentes.
- **Validação pré-pipeline + captura de stderr** — Pipeline dava "Script exited with code 1" genérico sem docs. Fix: validação pré-pipeline (HTTP 400) + captura de stdout/stderr no `_run_stage` com extração de linhas `[ERROR]`/`FATAL`.
- **Upload → classify → data/ roteamento** — 107 docs ficavam no `inbox/` sem chegar ao `data/`. Fix: `route_to_data_dir()` no document processor copia arquivo classificado de `inbox/` para `data/{dest_group}/`.
- **`_categorization` global missing no E4** — Scope issue. Fix: adicionar `_categorization` à declaração `global` do `_init_config`.
- **`skip_llm` default ignorava tier premium** — API sempre usava `DETERMINISTIC_ORDER`. Fix: `FULL_ORDER` quando `skip_llm=false`.
- **`FERNET_KEY` não persistida → secrets ilegíveis** — Nova key gerada a cada restart. Fix: persistir em `.env`.
- **`max_tokens=4096` insuficiente para E1.5** — LLM truncava. Fix: aumentado para 16384.
- **`started_at` sem timezone → "0s" elapsed** — SQLite salvava datetime naive → browser interpretava como hora local. Fix: `field_serializer` no Pydantic adiciona `tzinfo=UTC` antes de serializar.
- **Bolinha de running sem animação visual** — Fix: `animate-pulse` no ícone de stage em `running`.

### Documentação reorganizada (2026-04-15)

- PRODUCT_PLAN.md (390KB) arquivado em `docs/archive/`.
- Estrutura nova: README + 4 foundational (PRODUCT, ARCHITECTURE, SETUP) + 4 execution (ROADMAP, BACKLOG, DECISIONS, CHANGELOG).

---

## [F6.5] Testing & Hardening — 2026-04-15 ✅

**1 dia concentrado** (executado em 6 blocos pela ordem do CTO, não A→F documentada). Entregou rede de segurança completa antes de F7: testes em todas as camadas + hardening fintech + anti-regression bank + infraestrutura de teste profissional.

### Resultado agregado

- **438 tests passing em ~25s** (94 backend pytest + 344 frontend Vitest, 1 skipped documentado)
- **~25 E2E specs Playwright** (Golden Path + 8 fluxos críticos; 13 tagged `@critical` para cross-browser chromium+firefox+webkit)
- **7 ADRs** novas/atualizadas: [ADR-062](DECISIONS.md#adr-062--frontend-testing-em-fase-dedicada-65) F6.5 dedicada, [ADR-063](DECISIONS.md#adr-063--hardening-fintech-em-sub-fase-65d) Hardening fintech, [ADR-064](DECISIONS.md#adr-064--backend-hardening-em-sub-fase-65e) Backend hardening, [ADR-067](DECISIONS.md#adr-067--test-infrastructure-em-sub-fase-65f) Test infrastructure, [ADR-069](DECISIONS.md#adr-069--msw-sync-strategy-manual--lint-ci-não-codegen) MSW sync, [ADR-070](DECISIONS.md#adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in) Premium LLM E2E mock, [ADR-071](DECISIONS.md#adr-071--playwright-workspace-isolation-email-unique-por-worker) Workspace isolation

### Bloco 0 — Bootstrap

Fundação de teste consumida por todos os blocos seguintes:
- Vitest + jsdom + `@vitejs/plugin-react` + coverage v8 com thresholds calibrados
- MSW v2 com handlers default para 50+ endpoints de `lib/api.ts`
- Playwright multi-browser (chromium + firefox + webkit + projeto `visual` isolado) + auth helper com workspace isolation por worker
- Backend factories type-safe (`make_user`, `make_workspace`, `make_member`, 12 builders)
- Frontend factories alinhadas com `lib/api.ts` types
- DB isolation strategy documentada inline em `backend/tests/conftest.py`
- `docker-compose.test.yml` (PG 5433 + Redis 6380 isolados do dev) + scripts up/down
- Synthetic PDF generator para 13 bancos via `reportlab` (CPF placeholder LGPD-safe)
- Esqueleto de `docs/TESTING.md`
- Smoke test inicial 7/7 passing em 941ms

### Bloco 1 — Backend Hardening (6.5E)

- **Fix alembic cwd-sensitivity:** `%(here)s/../fin.db` absoluto + guard em `env.py` rejeita SQLite relativo + `DATABASE_URL` default absoluto via `_PROJECT_ROOT`
- **Round-trip tests para 6 serializers** (`family_members`, `categorization`, `pipeline_config`, `institution_config`, `report_layout`, `llm_config`) — 15 tests incluindo 4 cenários anti-regressão BUG-015
- **Alembic guardrails:** drift detection model↔migration (catálogo `KNOWN_PRE_EXISTING_DRIFT` com 4 itens conhecidos), idempotency upgrade→downgrade→upgrade, linearidade do histórico, offline SQL preview
- **Golden file pipeline:** workspace fixture → materialize → 13 PDFs sintéticos parseáveis por pdfplumber → token `{{COVER_FAMILIA}}` substituído (full E2E pipeline deferido documentadamente)
- **Anti-regression bank:** `backend/tests/regressions/` com 20 tests ativos cobrindo BUG-001/002/003/004/007/014/015 + OP-001/002/008/009/010 + 6 placeholders frontend

### Bloco 2 — Multi-tenant gate

- **Isolation paramétrica:** 27 tests cobrindo 9 domínios (workspace settings, members+accounts, categories, documents, vault, pipeline runs+reviews, reports, transactions, LLM config, notifications). 2 universos paralelos User A/B — `_assert_no_b_leak()` via signatures únicas. **0 vazamentos.**
- **Systemic fallback-leak fix:** BUG-004 só strippava CPF; auditoria detectou `full_name`/`short_name`/`birth_date` do founder vazando via `_convert_members_json_to_schemas` + export cru em `_export_family_members` para tenant vazio. Fix: `_NEUTRAL_PLACEHOLDER_NAMES` por role + export retorna `{"membros": {}}` para workspace sem members
- Bug colateral: factory `make_member(role="responsavel")` não passava schema; corrigido para `"titular"`

### Bloco 3a — Unit Tests Frontend (6.5A)

- **102 tests em `format.ts`** (9 formatters + 4 status maps + **5 property-based via fast-check** antecipando 6.5D.2: BRL round-trip, separadores BR íntegros, percent sinal, formatDelta positivo sempre `+`, formatBytes monotônico)
- **16 tests em `export.ts`** (CSV BOM UTF-8, `;` delimitador, XLSX auto-width via spy em `book_append_sheet`)
- **17 tests em `api.ts`** (token mgmt, Bearer, Content-Type, ApiError 401/422/500, XHR upload com progress)
- **15 tests em `usePipelineWS.ts`** (mock WebSocket com backoff exponencial + terminal events + cleanup)
- **9 tests em `utils.ts`** (cn() Tailwind merge)
- Coverage: utils 100%, format 98.96%, export 100%, usePipelineWS 97.75%, api 35.57%

### Bloco 3b — Integration Tests (6.5B)

- **10 pages cobertas:** Login (8), Register (6), Dashboard (7 — Recharts mockado), Documents (8 — drop zone + banner needs_password + delete), Pipeline (7 — **BUG-007 regression: free→skip_llm:true / premium→false**), Transactions (4 + **XSS smoke F6.5D.6 antecipada**), Reports (5), Config (5 — 7 tabs), Vault (9), AppShell (9 — **BUG-005 regression: Vault no nav**)
- **8 compostos:** KPICard, EmptyState (com CTA F6.5D.12), StatusBadge (7 variants), Delta (aria-label semântico), Spinner (anti-regression OP-011), ConfirmDialog, ThemeToggle, DataTable (sort + onRowClick)
- **Dark mode integration:** 10 tests (classes semânticas, sem cores hardcoded green/red)
- **Form validation paramétrica:** 8 tests (HTML5 type=email/password/required/minLength)
- **WebSocket integration real (6.5B.14):** 4 backend tests com fakeredis (JWT 4001, aceita válido, mensagem pub/sub, terminal event close)
- **TZ regression (6.5B.15):** 5 frontend tests (formatDate com/sem Z — OP-010 regression)

### Bloco 4 — Hardening Fintech (6.5D)

- **axe-core (`vitest-axe`):** 13 tests, 0 violations critical/serious. **2 violations reais detectadas e corrigidas no source:** aria-label em file input hidden (`documents/page.tsx`) + aria-label em botões delete (`documents/page.tsx` e `vault/page.tsx`)
- **Error Boundary:** `ErrorBoundary.tsx` class component + wrap em `app/(app)/layout.tsx` + 6 tests (crash em subárvore não derruba siblings)
- **Security smoke:** 8 tests (XSS em 4 campos + JWT expiry mid-session + logout cleanup cirúrgico)
- **Resilience:** 8 tests (5xx handling, network error, navigator.onLine events)
- **Focus management:** 3 tests (dialog focus, close retorna ao trigger, form submit)
- **CPF mod-11 determinístico** (`tests/utils/cpf.py`) + **lint anti-PII** (`tests/utils/lint_no_real_pii.py`) — **7 CPFs reais do founder substituídos** em tests backend por gerado+noqa
- **Scaffolds P1:** `.lighthouserc.json`, `.size-limit.json`, `scripts/contract-check.mjs`, `visual-regression.visual.spec.ts` (5 snapshots baseline)

### Bloco 5 — E2E + Smoke + CI (6.5C + 6.5F.4)

- **9 Playwright specs, ~25 tests:** `golden-path.spec.ts` (gate sagrado), `onboarding.spec.ts` (5), `upload-pipeline-report.spec.ts` (3 incluindo BUG-007 via route interceptor), `config-round-trip.spec.ts` (2), `vault.spec.ts` (2), `drill-down.spec.ts` (3), `dark-mode.spec.ts` (1), `error-auth.spec.ts` (5), `notifications.spec.ts` (2). 13 tests tagged `@critical`
- **`docs/SMOKE_TEST.md`:** 13 seções, 70+ checks manuais (LGPD pré-beta, multi-tenant, BUG-015/BUG-007/ADR-068 regressions, rollback triggers)
- **CI GH Actions (`.github/workflows/ci.yml`):** 7 jobs — lint pre-commit, lint-pii, pipeline-tests, backend-tests + Redis service, frontend-tests (Vitest + JUnit), frontend-e2e (condicional: push main OU label `e2e` em PR) com PG+Redis services + alembic upgrade + Playwright cross-browser + artifacts 30d + all-green gate
- **Pipeline mock fixtures** (`backend/tests/fixtures/pipeline_runs.py::seed_completed_run`): `PipelineRun(status="completed")` + 13 StageLogs + Report com HTML stub — permite Golden Path rodar em <30s; `PW_REAL_PIPELINE=1` para opt-in real

### Bloco 6 — 6.5F residuais + 6.5E.7

- **Concurrency test `materialize_config`:** 3 tests (2 workspaces paralelos, idempotency do mesmo ws, 10 workspaces simultâneos com `ThreadPoolExecutor`) — SQLite file-based + `check_same_thread=False` para thread-safety
- **MSW sync lint** (`frontend/scripts/msw-lint.mjs`): AST regex sobre handlers.ts vs `openapi.json` do backend
- **LLM mock fixtures** (`backend/tests/fixtures/llm_mock.py`): outputs Pydantic válidos por stage (E1, E1.5, E2-llm, E7-review) — `FIN_LLM_MOCK=1` default em CI
- **`.github/CODEOWNERS`:** review obrigatório em `__snapshots__/`, `alembic/versions/`, `tests/fixtures/`, `DECISIONS.md`
- **`docs/TESTING.md` expandido:** debug CI (tabela de artifacts), flaky test policy, snapshot review process, premium LLM E2E mock/nightly
- **CI reporter expandido:** `actions/upload-artifact@v4` retention 30d + `actions/github-script@v7` PR comment automático
- **Pre-commit hooks** já entregues em commit anterior (`a7a055d`): `.pre-commit-config.yaml` + `dev/check_forbidden_paths.py` + `dev/validate_commit_msg.py`

### Achados não previstos

Descobertos durante a execução e documentados nos blocos:
- jsdom 25 + vitest 2.1.x: `Blob.text()`, `Blob.arrayBuffer()` quebrados + Storage não instanciada → workarounds em setup.ts
- base-ui Tabs usa `aria-selected="true"` (não `data-state="active"`)
- shadcn `CardTitle` não tem role="heading" semântico; `Skeleton` usa `data-slot="skeleton"`; `Button render={<a>}` não emite role="link"
- WebSocket é `readonly` em globalThis → `vi.stubGlobal()` em vez de assignment
- XLSX `!cols` não persiste no formato → spy em `book_append_sheet`
- Celery `include` é lazy → import explícito em tests
- `config/` tem 8+ CPFs reais do founder (definitions.md + family_members.json) — **NÃO fixtures**; cobertos por neutralização API em 6.5E.6; lint exclui o dir
- 10 tests pré-existentes falhando em `test_pipeline_api`/`test_pipeline_phase5`/`test_pipeline_review`/`test_retry_config`/`test_pipeline_task` (não causados por F6.5)

### Arquivos criados (highlights)

- 26 arquivos frontend de test (Vitest + Playwright)
- 8 arquivos backend de test novos
- 7 arquivos de infra: `docker-compose.test.yml`, `scripts/test_backend_up.sh`/`_down.sh`, `.github/workflows/ci.yml`, `.github/CODEOWNERS`, `tests/fixtures/pdf_generator.py`, `tests/utils/{cpf,lint_no_real_pii}.py`
- 4 fixtures: `backend/tests/fixtures/{pipeline_runs,llm_mock}.py`, `frontend/scripts/{msw-lint,contract-check}.mjs`
- 3 scaffolds CI P1: `.lighthouserc.json`, `.size-limit.json`, `visual-regression.visual.spec.ts`
- 2 componentes novos: `ErrorBoundary.tsx`, wrap em `(app)/layout.tsx`
- 3 novas ADRs (069-071) + 1 nova doc (`SMOKE_TEST.md`) + `TESTING.md` expandido

### Pendências carregadas para CI primeiro-run

Não bloqueiam close da fase:
- Visual regression baseline capture
- Nightly `e2e-real-llm.yml` workflow ativação
- MSW lint CI integration (quando backend subir como service)
- Lighthouse / bundle-size / contract-check gates
- Flaky report semanal workflow

---

## [F6] Frontend Profissional — 2026-04-14 ✅

**Sprints 13-16** (~6 semanas)

- **6A Transaction Explorer:** API `/transactions` com filtros/busca/paginação. `DataTable` component. URL state. Category override inline. Export CSV/XLSX.
- **6B Dashboard:** Recharts integration. 4 charts (patrimônio mensal, despesas por categoria, fluxo receitas×despesas, composição investimentos). Alertas inteligentes. Drill-down → TE.
- **6C Report React:** Component tree do E5 JSON. Validação L1 (data accuracy) + L2 (section completeness). Report history. PDF via `@media print`. Export CSV/XLSX por seção. Data lineage tooltips.
- **6D UX Polish:** Dark mode (next-themes). Navigation architecture atualizada. LLM config UI. Tier badges. Manual review UI. Notification center. Loading/empty/error states. Responsive. Accessibility pass.

Pendente: testes E2E (movidos para F6.5).

---

## [F5] Task Queue + Real-time — 2026-04-14 ✅

**Sprint 12** (~3 semanas)

- **5A:** Celery + Redis. `run_pipeline_task` como `@celery_app.task`. Fallback Thread. Redis Pub/Sub para eventos WebSocket.
- **5B:** WebSocket `/pipeline/runs/{id}/ws` com JWT auth. `usePipelineWS` React hook com auto-reconnect.
- **5C:** Stage-boundary cancel (DB flag + Celery revoke). Per-stage retry config. Health check (Redis + Celery + DB).

44 novos testes. Docker Compose com Redis.

---

## [F4.5] Design System Foundation — 2026-04-14 ✅

**Sprint 11.5** (2 semanas)

- **4.5A:** Geist Sans + Mono via `next/font/google`. `globals.css` com `@theme inline` (30+ tokens oklch). Paleta financeira semântica (gain/loss/alert/info/neutral). 12 chart colors. `format.ts` com 9 formatters. `cn()` utility.
- **4.5B:** shadcn/ui v4 init (16 primitivos base-ui/react + radix). 7 compostos: `StatusBadge`, `Spinner`, `EmptyState`, `Delta`, `KPICard`, `PageHeader`, `ConfirmDialog`.
- **4.5C:** Todas as 10 pages + AppShell migradas. SVGs inline → Lucide. Spinners CSS duplicados → `<Spinner>`. `confirm()` nativo → `<ConfirmDialog>`. Config tabs → shadcn `Tabs` (ARIA). Build green.

---

## [F4] Automação LLM — 2026-04-14 ✅

**Sprints 10-11** (~4 semanas)

- **4A:** LiteLLM + Instructor configurados. `LLMConfig` + `StageReview` models. API key encrypted at-rest. `DocumentTextExtractor` (PDF/XLSX/CSV). 5 endpoints LLM API. Materialização estendida.
- **4B:** 4 LLM stage runners: E1 (members extract), E1.5 (baseline patrimonial), E2-llm (investimentos sem parser det), E7-review. Validadores de compatibilidade downstream.
- **4C:** E7-review + E7-apply + E6-final integrados. FULL_ORDER funcional.
- **4D:** Tier detection (free/premium). Free auto-skipa LLM stages (`skipped_free_tier`). Pipeline `needs_review` workflow: pausa → edit JSON via API → resume.

444 testes total (204 pipeline + 240 backend).

---

## [F3] Configuração via UI — 2026-04-14 ✅

**Sprints 8-9** (~4 semanas)

- **3A:** 7 modelos Fase 3. Alembic migration `da5a6af13e3e`. 17 Pydantic schemas (CPF validation, roles, category types, bounds).
- **3B:** 18 endpoints Config API. Fallback seletivo do disco global. Import/export JSON.
- **3C:** `config_materializer.py` com 5 serializers. Integrado no pipeline trigger.
- **3D:** Config page com 6 tabs: Members CRUD, Categories CRUD, Pipeline params, Institutions toggle+JSON, Report Layout, Import/Export.

75+ testes backend adicionados.

---

## [F2] Upload + Pipeline Web — 2026-04-14 ✅

**Sprints 5-7** (~4 semanas)

- **2A:** 6 modelos Fase 2 (Document, PasswordVault, PipelineRun, PipelineStageLog). StorageService com per-tenant isolation + path traversal prevention. VaultService com Fernet.
- **2B:** Upload endpoint (multipart batch até 20 arquivos). E0-unlock via vault. E0-route classification automática. Status machine. Retry-unlock endpoint.
- **2C:** Pipeline execution API. Background thread com cancel cooperativo. Stage tracking. Pipeline runs list/detail. Max 1 run ativo por workspace.
- **2D:** Frontend completo: drag-and-drop upload, documents table com status badges, vault CRUD, pipeline trigger + progress polling, stage-by-stage progress bar, AppShell com sidebar.

235+ testes (99 backend + 136 pipeline).

---

## [F1] Backend API + Auth — 2026-04-13 ✅

**Sprints 3-4** (~1 dia concentrado)

- FastAPI + SQLAlchemy 2.0 async + SQLite + Alembic (setup inicial)
- Auth: register, login, JWT tokens (python-jose + bcrypt direto)
- Modelos: User, Workspace, Report
- Endpoints: auth (register/login/me), reports (list/detail/html)
- Frontend: Next.js 16 + TypeScript + Tailwind 4. Login, register, reports list, report viewer (iframe)
- 149 testes total

---

## [F0] Desacoplar Core — 2026-04-12 ✅

**Sprints 1-2** (~3 semanas)

- `pipeline/` package Python com `__init__.py` (API pública v0.2.0)
- `WorkspaceContext` dataclass com paths + config injection
- `config_loader.py` unificado
- 12 scripts wrappados com `_init_config(base_dir)` + `main(root_dir=None)`:
  `e0_audit`, `e0_route`, `e0_unlock`, `e15_consolidate`, `e2_extract`, `e2/common`, `e3_reconcile`, `e4_categorize`, `e5_analyze`, `e5n_narrativas`, `e6_render`, `e7_review`, `pipeline_common`
- `pipeline/orchestrator.py` com `run_pipeline`, `run_from`, `run_stages`
- `pyproject.toml` com package `fin-pipeline` v0.2.0
- Golden files para regression tests
- 136 testes passando

---

## Versões pré-F0

**pre-F0:** Pipeline CLI puro. 11 parsers bancários. 14 etapas (E0→E7). 31 scripts. ~860KB de código. Relatório HTML ~411KB com Chart.js.

Histórico completo pré-refactoring está em `docs/archive/PRODUCT_PLAN-2026-04-15.md`.

---

## Como atualizar este arquivo

1. Ao concluir uma sub-fase, mover da seção `[Unreleased]` para uma nova seção `[FX]`.
2. Mencionar apenas o que foi entregue (o "o quê"), não o como (detalhes em commits).
3. Destacar breaking changes e migrations.
4. Bugs críticos corrigidos ficam em `[Unreleased]` até a próxima release formal.
