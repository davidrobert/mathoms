# Fin — Changelog

> Log cronológico reverso do que foi entregue. Atualizar por sprint/milestone.

---

## [Unreleased]

Trabalho em andamento: preparação para **F7 (Produção + LGPD + Ops)**.

- **F7 / 7A.5:** `.env.example` na raiz (todas as `FIN_*` documentadas + opcionais comentadas); `scripts/gen-secrets.sh` para gerar `FIN_FERNET_KEY` / `FIN_SECRET_KEY` (modo imprimir ou `--init-env` a partir do example); `docs/SETUP.md` e README atualizados.

**F8.5 · Multi-tenant Goals completo (ADR-079):**
- **Backend**: API completa para APORTE_MENSAL, DOLARIZACAO e ALOCACAO_ALVO (12 novos endpoints: POST compute, GET current, GET history, PUT upsert por tipo)
- **Backend**: 3 compute functions puras (`compute_aporte_derived`, `compute_dolar_derived`, `compute_alocacao_derived`); `create_goal_version` genérica + helpers tipados (`get_current_goal_typed`, `get_goal_history_typed`)
- **Backend**: Pydantic models com validadores (distribuição == meta, alocação soma 100%); `_GoalResponseBase` compartilhada por IF + 3 novos
- **Frontend**: `/plano` refatorada para dashboard multi-goal (grid 2×2 com status cards) + banner CTA quando 0 goals configurados
- **Frontend**: 6 novas páginas (3 edit + 3 wizards): `/plano/aportes`, `/plano/dolarizacao`, `/plano/alocacao`
- **Frontend**: Types + 12 funções API client em `lib/api.ts`
- **Pipeline**: `scripts/e6_render.py` — resiliência (ValueError → fallback gracioso em `build_estrategia_aporte` e `_build_top5_decisoes_fallback`); banner CTA injetado no HTML quando goals vazios
- **Câmbio hardcoded**: `DEFAULT_CAMBIO_BRL_USD = 5.70` em DOLARIZACAO — override via `cambio_brl_usd` no compute request (débito futuro: API externa)
- Fluxo end-to-end completo: UI → DB (append-only versionado) → adapter → `goals.json` materializado → E5/E6 → relatório

**Pipeline hardening (revisão arquitetural):**
- `pipeline_common.py`: novos paths (INBOX_DIR, INBOX_PROCESSED_DIR, MEMBERS_DIR, OUTPUT_DIR) + `validate_artifact()` para validação de schemas
- `pipeline_common.py`: `write_json_atomic()` para escrita atômica via temp+rename (crash-safe, com flag `fsync=True` para artefatos críticos)
- `pipeline_common.py`: `safe_float(val, locale="BRL")` — agora suporta BRL/USD/EUR, corrigindo parsing de valores multi-moeda (contas Wise, Bank of America)
- `pipeline_common.py`: `log_stage()` migrado para structured logging (`logging.getLogger("fin.pipeline")`) com mapeamento WARN→WARNING, ERROR→ERROR
- E0 scripts (`e0_unlock`, `e0_audit`, `e0_route`) migrados para importar de `pipeline_common` — eliminada duplicação de `_init_config()`
- `e3_reconcile.py`: I/O delegado a `pipeline_common`; `deduplicate_transactions()` agora retorna audit details (3 valores) para rastreabilidade
- `e3_reconcile.py`: `should_skip_file()` não usa mais substring matching de SKIP_TYPES no filename — filtragem por tipo feita em `should_skip_extract()` via campo JSON
- `e3_reconcile.py`: temporal gap default 2→4 dias (cobre weekends + feriados); baseline validation usa canonical bank codes
- `e4_categorize.py`: delega config loading e writes a `pipeline_common`; despesas não-categorizadas logadas explicitamente (`[E4.2] UNCATEGORIZED`)
- `e5_analyze.py`: 7 sanity checks em valores computados (patrimônio negativo, receita/despesa negativa, taxa poupança range, IF%, endividamento >200%, score [0,10])
- `e5_analyze.py`: output escrito via `write_json_atomic(fsync=True)` para durabilidade
- `pipeline_task.py`: `_persist_llm_suggestions()` usa `SyncSessionLocal` (sync) em vez de `asyncio.run()` que crasharia em Celery fork workers
- `pipeline_task.py`: todos `except: pass` substituídos por `except Exception` com logging observável
- `e0_route.py`: LLM fallback agora com timeout 30s + retry 3x com backoff exponencial (1s/2s/4s)
- `e0_unlock.py`: limite de tamanho em extração ZIP (500MB/arquivo, 2GB total) — proteção contra zip bomb
- `e0_route.py` + `e2/common.py`: validação de período extraído por regex (mês 01-12, ano 2018-2030)
- `e_reset.py`: campo `in_progress` no state interativo para crash recovery no `--continue`
- 4 JSON Schemas: `e2_extract`, `e4_unified`, `e5_analysis`, `pipeline` (novo) — validação via `pipeline.json` → `schema_validation` (modo warn)
- `jsonschema>=4.20` adicionado como dependência (anteriormente comentado)
- `e5n_narrativas.py`: `_MetricsProxy` retorna `None` (não `0`) para chaves ausentes; formatadores (`fmt_currency`, etc.) tratam `None` → "N/D"
- `scripts/e6/` package: `sanitize.py` e `validate.py` extraídos de `e6_render.py` (-187 linhas)
- 61 novos testes: `test_e2_parsers.py`, `test_e5n_formatting.py`, `test_schema_validation.py` + extensões em testes existentes

**Pipeline incremental (ADR-080):**
- `POST /pipeline/run { incremental: true }` — processa só docs novos (E0→E2 filtrado, E3→E7 full)
- `GET /pipeline/new-doc-count` — contagem de docs nunca processados
- UI: botão "Processar N novo(s)" quando há docs novos + botão "Processar todos" como secundário
- Model: `PipelineRun.incremental` + `incremental_doc_ids` (JSON)
- Pipeline: `WorkspaceContext.incremental` + `incremental_doc_paths` propagados ao E2 wrapper

**Documentação:**
- Plano do **console interno** (operadores CEO/Ops/CS/Financeiro/LGPD): [INTERNAL_ADMIN_ROADMAP.md](INTERNAL_ADMIN_ROADMAP.md); sub-fase **F7F** no [BACKLOG.md](BACKLOG.md); menções em [ROADMAP.md](ROADMAP.md) e [ARCHITECTURE.md](ARCHITECTURE.md).

**UX & Robustez — Meu Plano (P0–P5):**
- **P0 fix:** `/plano` reescrito com `async/await` + estado de erro explícito (fix loading infinito por promise chain frágil)
- **P1 feat:** Barra de progresso % da meta IF (patrimônio atual vs. meta, via `computeIFGoal`)
- **P2 refactor:** `WorkspaceProvider` (React Context) no layout — resolve workspace uma vez, `useWorkspace()` substitui N fetches paralelos de `useCurrentWorkspace()`
- **P4 feat:** Empty state de tarefas no Plano agora mostra CTAs: "Criar tarefa manual" + "Ver sugestões automáticas" (link `/plano-de-acao/sugestoes`)
- **P5 feat:** `/plano` é a nova home do app (redirect `/` → `/plano`, sidebar reordenada, logo, invite flow, ErrorBoundary fallback, `nextUrl` default)

---

## [F9] Relatório Nativo React + Workspace Sharing + Design System — 2026-04-15 ✅

**ADRs:**
- [ADR-076](DECISIONS.md#adr-076) Design tokens unificados site × relatório (fonte única `tokens.json`)
- [ADR-078](DECISIONS.md#adr-078) Render nativo React + E6 como exportador standalone

**Design System:**
- `design-tokens/tokens.json`: fonte única de verdade (typography, spacing, radius, shadow, modes, card variants)
- `design-tokens/build.py`: gera CSS para Next.js (com @theme inline) e para E6 standalone
- DNA canônico: navy #1A3A5C, verde #15803D, Plus Jakarta Sans + Inter + JetBrains Mono
- Fontes via next/font/google (otimizadas: subsetting, self-hosting)
- Pre-commit hook `design-tokens-sync` e `report-layout-codegen` garantem consistency

**Codegen:**
- `config/schemas/report_layout.schema.json`: JSON Schema validando o YAML
- `dev/codegen_report_layout.py`: YAML → TypeScript + Pydantic, com `--check` para CI
- `frontend/src/generated/report-layout.ts`: tipos + constantes + ALL_CARD_IDS/ALL_CHART_IDS
- `backend/app/generated/report_layout.py`: Pydantic models validados

**Backend:**
- `Report.analysis_json_path`: ponteiro para snapshot E5 JSON (migration d3e4f5a6b7c8)
- `GET /reports/{id}/data`: serve E5 JSON para render nativo (404 graceful para pré-F9)
- `GET /reports/{id}/download.html`: download HTML standalone com attachment headers
- `GET /reports/{id}/download.pdf`: PDF server-side via Playwright headless Chromium
- `ReportResponse.has_analysis_data`: flag para frontend distinguir relatórios F9+

**Frontend — Relatório nativo (18 seções, 0 stubs):**
- Shell: ReportShell, ReportHeader (mode selector + export buttons), ReportToc (scroll-spy + deep-links)
- 13 cards: PatrimonioCategoriasCard, ReceitasFonteCard, ReservaEmergenciaCard, EndividamentoCard, OrcamentoProspectivoCard, ConsumoConscienteCard, DiagnosticoComportamentalCard, EquilibrioCerbasiCard, InvestimentosClasseCard, EstrategiaAporteCard, PrevidenciaPgblCard, PontosFortesList, PontosUrgentesList
- 8 charts Recharts (SVG, print-native): PatrimonioDoughnut, WaterfallIF, ScoreGauge, FluxoMensal, ReceitaBar, DespesasDoughnut, ReceitaDespesaMensal + NarrativeChartCard genérico
- MonetaryValue (font-mono tabular-nums, BRL/USD, compact, signed, null-safe)
- Mode toggle via URL (?mode=tatico/usa) com sync bidirecional
- Print CSS A4 (report-print.css): break-inside:avoid, print-color-adjust:exact, SVG nativo
- Deep-links via hash (#S3) + scroll-spy debounced + auto-scroll TOC

**Migração por lotes (commits):**
| Lote | Seções | Commit |
|------|--------|--------|
| F0.2–F0.5 | Infra: tokens.json, build.py, codegen, useReportData, /data endpoint | `6020917`→`c88f9a5` |
| F1.1–F1.5 | Rota nativa React substitui iframe, download.html endpoint | `2751dea`→`8b9071d` |
| F1.2 | Design tokens aplicados no site (ADR-076) | `e2a9b29` |
| F2.A | Patrimônio S1 migrado | `78a351b` |
| F2.B | Fluxo de Caixa S2 migrado | `431f39c` |
| F2.C–G | S3-S10 migrados, modo estratégico completo | `1289ea8` |
| F2.H | USA + Tático, Fase 2 completa | `a3411e6` |
| F3.1–3.2 | Scroll-spy, deep-links, print CSS A4, mode via URL | `dc4f9d0`→`92d8de1` |
| F4.0–4.2 | PDF server-side Playwright, E6 como exportador | `bc232cc`→`7733adf` |

**Testes:** 56 backend + 23 frontend + 20 design tokens + 14 codegen = 113 novos

**Iframe removido:** `page.tsx` reescrita de 436 linhas (iframe + MutationObserver) para render React nativo.

**Workspace Sharing (ADR-078):**

Backend:
- `WorkspaceInvitation` model + migration — convites com token SHA-256, TTL 72h, uso único, rate limit 10 pendentes/workspace.
- Role `viewer` adicionado a `VALID_ROLES`. `WRITE_ROLES` e `MEMBER_ADMIN_ROLES` para policy granular.
- `require_role(allowed)` factory em `tenancy.py` — `require_write_role` e `require_member_admin_role` prontos.
- `PUT /goals/if` agora exige `require_write_role` — viewer recebe 403.
- `User.token_version` + claim `tv` no JWT — forced logout ao remover membro (migration `d1b2c3d4e5f6`).
- 7 novos endpoints: invitations CRUD, members CRUD, aceite público.
- 39 testes (invitations + members + viewer role matrix + forced logout + goals regression).

Frontend:
- Aba "Acessos" em Configurações: lista membros, convida por email, muda roles, remove, revoga convites.
- Workspace switcher no header (nome + badge de role; dropdown se 2+ workspaces).
- Viewer banner ("Você está acompanhando") + botão Salvar desabilitado na meta IF.
- Página pública `/invite/{token}` — preview sem auth, aceite com auth.
- `?next=` em login/register — redireciona pós-auth para URL original.
- `AuthBootstrap` global detecta `token_revoked` → limpa sessão + redirect para login.
- `useCurrentUser`, `usePermissions` hooks. `roleLabels.ts` com labels PT-BR.

---

## [F8] Goals & Tasks + Cutover CLI→Web — 2026-04-15 ✅

**ADRs:**
- [ADR-072](DECISIONS.md#adr-072) Multi-tenancy: `WorkspaceMember` N:N, `get_current_workspace` dependency, tenancy lint AST-based com baseline
- [ADR-073](DECISIONS.md#adr-073) Goals como entidade versionada (append-only, derivação server-side)
- [ADR-074](DECISIONS.md#adr-074) Tasks como entidade de 1ª classe (fora do relatório)
- [ADR-075](DECISIONS.md#adr-075) Cutover CLI→Web: estratégia de transição faseada com adapters
- [ADR-077](DECISIONS.md#adr-077) Pipeline adapter como contrato de cutover

**Backend — Models + Migrations:**
- `WorkspaceMember` (N:N user↔workspace, roles owner/member) + backfill migration
- `Goal` (versionado por effective_from/to, params_json + derived_json, 5 types: IF, APORTE_MENSAL, DOLARIZACAO, ALOCACAO_ALVO, PLANNING_CONTEXT)
- `Task` (number único por workspace, 5 statuses, 5 deadline kinds, parent dependency) + `TaskSuggestion` + `TaskAttachment`
- `FeatureFlag` (workspace-level boolean flags, defaults em código)
- `Report.tasks_snapshot_json` — snapshot imutável de tasks no momento da geração
- 5 Alembic migrations encadeadas: workspace_members → goals → tasks → report_snapshot → feature_flags

**Backend — Services (9 novos):**
- `goal_service`: `compute_if_derived` (FV anuidade pura), CRUD versionado append-only
- `task_service`: CRUD + auto-numbering + status transitions validadas (grafo ALLOWED_TRANSITIONS) + dependency enforcement + export markdown
- `task_suggestion_service`: create/bulk_create/approve/reject/merge
- `task_notification_service`: scan prazos ≤7d → notifications (overdue=critical, ≤3d=warning, ≤7d=info), idempotente
- `task_progress_service`: % executado via parser BRL + match transactions por keywords
- `task_attachment_service`: upload/list/delete via StorageService
- `report_tasks_snapshot_service`: build_snapshot sync+async, get_report_snapshot com fallback live
- `feature_flags_service`: DEFAULTS compilados, get/set/is_enabled, fail-safe
- `pipeline_adapter`: build_goals_payload/build_tasks_payload/build_tarefas_md (sync+async), materialização pré-run

**Backend — Endpoints (~30 novos):**
- `/workspaces/{ws}/goals`: IF compute/get/put/history + `/{goal_id}/tasks`
- `/workspaces/{ws}/tasks`: CRUD + status transition + upcoming + export.md + progress + scan-deadlines
- `/workspaces/{ws}/tasks/{id}/attachments`: upload/list/download/delete
- `/workspaces/{ws}/task-suggestions`: list + create + approve + reject + merge-into
- `/workspaces/{ws}/feature-flags`: get + put
- `/reports/{id}/tasks`: snapshot ou fallback live
- `/me/workspaces`: listagem de memberships

**Backend — Pipeline integration:**
- `_materialize_adapter_configs`: grava goals.json + tarefas.md do DB no tenant config dir antes do run
- `_persist_llm_suggestions`: hook pós-E5.N que persiste `tarefas_sugeridas` como TaskSuggestion
- `build_snapshot_sync` no `_create_report_from_output`: relatórios nascem com snapshot imutável
- Worker beat `scan_all_deadlines` (Celery beat schedule, diário)

**Backend — Seeds + Scripts:**
- `seed_if_goal_ferreira_campos.py` (paridade 7.200.000)
- `seed_tasks_ferreira_campos.py` (43 tasks, dep #19→#18, status done #2/#12)
- `seed_goals_full_ferreira_campos.py` (5 Goal types cobrindo 100% do goals.json)
- `validate_adapter_parity.py` (diff recursivo com tolerância de metadata)
- `cutover_execute.py` (check pré-condições + backup _archive/ + remoção)

**Backend — Testes (~146 novos):**
- 12 lint tenancy (AST-based, cobertura de padrões positivos e negativos)
- 32 goal_service (paridade FC, fórmula, arredondamento, versionamento, isolation)
- 48 task_service (transitions, dependencies, filtros, suggestions, export MD)
- 45 integrações (endpoints, multi-tenant 403, progress, snapshot, attachments, feature flags)
- 9 pipeline_adapter (payload format, isolation, legacy merge, MD export)

**Backend — Infra:**
- CI job `tenancy-lint` (AST scan + 12 tests + baseline) no `all-green` gate
- `scripts/lint/check_workspace_scoping.py` com `--baseline` / `--write-baseline`
- `docs/tenancy.md` (300 linhas — guia do/don't + checklist PR + template test isolation)

**Frontend — Rotas (5 novas):**
- `/plano`: overview IF (3 KPI cards + parâmetros + tarefas ligadas à meta)
- `/plano/meta-if`: form edição com simulador live
- `/plano/meta-if/wizard`: 4 passos (renda → TRS → horizonte → confirmação)
- `/plano-de-acao`: lista com 3 views (priority/deadline/category) + create + drawer + sugestões badge
- `/plano-de-acao/sugestoes`: fila approve/reject 1-click

**Frontend — Componentes (10+ novos):**
- TaskCard, TaskDrawer, TaskFormDialog, TaskPriorityChip, TaskStatusPill, TaskDeadlineBadge
- TaskProgressCard (barra % executado mensal)
- TaskAttachments (upload/list/delete inline)
- UpcomingTasksWidget (dashboard, próximos 7 dias)
- useCurrentWorkspace hook (localStorage + /me/workspaces)

**Frontend — AppShell:**
- "Meu Plano" (Target icon) + "Plano de Ação" (ListTodo icon) adicionados ao nav
- UpcomingTasksWidget inserido no dashboard entre KPIs e Charts

---

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
