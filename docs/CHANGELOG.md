# Fin — Changelog

> Log cronológico reverso do que foi entregue. Atualizar por sprint/milestone.

---

## [Unreleased]

Trabalho em andamento: preparação para **F6.5 (Frontend Testing)** e **F7 (Produção)**.

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
