# Mathoms AI — Changelog

> Log cronológico reverso do que foi entregue. Atualizar por sprint/milestone.

---

## [Unreleased]

Trabalho em andamento: preparação para **F7 (Produção + LGPD + Ops)**.

- **A6g.2 — 1ª rodada pipeline style sweep (2026-04-21):**
  Aplica `## Code style` do CLAUDE.md a `scripts/`, `pipeline/` e
  `tests/fixtures/`, consumindo o baseline P1/P2 de
  [`docs/audits/code_style_audit_20260421.md`](audits/code_style_audit_20260421.md).
  Escopo: **Tier 1 seguro** (zero goldens expostos). Tier 3 (scripts
  `e3/e4/e5/e5n/e6/e7` com goldens) volta como **A6g.2b** pós-A6c.3.
  - **T1.a — `scripts/e_reset.py::main`:** 372 → 27 linhas. Extraídos 18
    helpers nomeados (`_build_arg_parser`, `_print_reset_header`,
    `_phase_{move_to_inbox,unlock_pdfs,audit,route,clean_artifacts,
    clean_narrativas_review}`, `_detect_leading_llm`,
    `_execute_non_interactive`, `_run_interactive_mode`, …).
    `LLM_DESCRIPTIONS` promovida a constante de módulo. Gate: `--help`
    idêntico byte-a-byte; `pytest tests -q` = 1461 passed (baseline).
  - **T1.b — `tests/fixtures/pdf_generator.py`:** 1067 → 29 linhas (shim
    self-contained). Novo pacote `tests/fixtures/pdf/` com
    `formatters.py` (helpers BRL/USD + meses) + 11 módulos por banco
    (`btg.py`, `rico.py`, `wise.py`, `picpay.py`, `bankofamerica.py`,
    `santander.py`, `itau.py`, `c6.py`, `bradesco.py`, `caixa.py`,
    `quintoandar.py`) + `generator.py` (306 linhas, dispatcher
    `generate_statement`). Shim tem fallback de `importlib.util` para
    `backend/tests/test_golden_pipeline.py` (que carrega por path para
    evitar namespace conflict com `backend/tests/`). Gate:
    `tests/test_e2_synthetic_pdf_parsers.py` = 22 passed;
    `backend/tests/test_golden_pipeline.py` = 19 passed, 1 skipped.
  - **T1.c — `scripts/e0_audit.py`:** 948 → 238 linhas. Checks movidos
    para novo pacote `scripts/e0/`:
    `audit_helpers.py` (`normalize`, `parse_data_filename`,
    `parse_e2_filename`, globais + `init_config`),
    `audit_filename.py` (checks 1, 7, 8, 9 + `fix_extract_naming`),
    `audit_integrity.py` (checks 2, 3, 6),
    `audit_ledger.py` (checks 4, 5). `e0_audit.py` fica só com CLI +
    `ALL_CHECKS` + `_init_config` wrapper que rebina globais para
    preservar contrato de `test_stage_wrappers.py`. Gate: JSON output
    idêntico antes/depois; `tests/test_stage_wrappers.py` = 29 passed.
  - **T2.b — `backend/app/tasks/pipeline_task.py::run_pipeline_task`:**
    273 → 58 linhas (orchestrator incluindo signature + docstring;
    corpo efetivo ~30 linhas). Extraídos 11 helpers nomeados por fase
    do ciclo de vida de um ``PipelineRun``:
    `_bootstrap_pipeline_sys_path`, `_setup_run_context` (ctx +
    DBArtifactStore session), `_mark_run_started` (status → running),
    `_execute_stages_loop` (loop principal, retorna
    `(has_failure, paused_for_review)`), `_record_stage_{skip,running,
    exception,needs_review,result}` (5 snapshots de persistência +
    publish_* de eventos), `_has_validation_errors` (predicate sobre
    `result.detail`), `_finalize_run` (status final),
    `_run_post_processing` (sync docs, report, sugestões LLM — cada um
    best-effort), `_close_artifact_session` (commit+close DB).
    Gate: `pytest backend/tests/test_pipeline_task.py -q` = 13 passed;
    `pytest backend/tests/test_openapi_snapshot.py -q` = 1 passed
    (sem mudança de wire contract).
  - **Fora de escopo nesta rodada (documentado):**
    - Scripts com goldens (e3/e4/e5/e5n/e6/e7) — 11 ofensores P2 + ~250
      P1 ficam para **A6g.2b** pós-A6c.3 (quando `main(root_dir)`
      legados forem deletados).
    - `ChartsNarrator.narrate` (T2.a) skipped — paridade de narrativas
      tem tolerância zero e o `return {...}` dict literal com locals
      compartilhados força passagem de 15+ argumentos por método
      extraído; pouco ganho vs. risco de rollback em golden. Volta
      junto com A6g.2b.
  - **Impact numérico nos targets:**
    - `long_functions` P1: `e_reset.main` 372 → 27; `e0_audit.main`
      140 → <25; `run_pipeline_task` 273 → 58 — todas removidas da
      lista high-severity (>40 linhas).
    - `long_files` P2: `pdf_generator.py` 1067 → 29 (remove da lista);
      `e_reset.py` 1332 → 1379 (stretch — targets extraídos mas main
      file ainda >1000; consolidação em módulos separados planejada
      para A6g.2b); `e0_audit.py` 948 → 238 (remove da lista);
      `pipeline_task.py` 628 → 742 (+114 por framing de helpers — file
      ainda >500 mas função principal cai 78%).
  - **Gates consolidados:**
    - `pytest tests -q` = 1461 passed, 2 skipped (igual baseline).
    - `pytest backend/tests/test_golden_pipeline.py -q` = 19 passed,
      1 skipped.
    - `pytest backend/tests/test_pipeline_task.py -q` = 13 passed.
    - `pytest backend/tests/test_openapi_snapshot.py -q` = 1 passed.
    - `python scripts/e_reset.py --help` output idêntico.
    - `python scripts/e0_audit.py --json` output idêntico.
    - `pre-commit run` passa nos arquivos tocados.

- **A6g.4 — 1ª rodada frontend style sweep (2026-04-21):**
  Aplica `## Code style` do CLAUDE.md a `frontend/src/`, consumindo o
  baseline T1-T5 de [`docs/audits/code_style_audit_20260421.md`](audits/code_style_audit_20260421.md).
  Delta por categoria:
  - **T1 `ts_any`:** 9 → 0. Cards (`InvestimentosClasseCard`,
    `EstrategiaAporteCard`, `ContrafluxoCard`, `PrevidenciaPgblCard`)
    passam a exportar seus `*Data` interfaces; S3/S7 sections narrow
    via `as unknown as <CardData>` em vez de `as any`.
    `ExtractJsonResponse.data: any` → `unknown`. `dashboard` Bar
    onClick callback vira `(entry: unknown)` + narrow inline.
  - **T2 `ts_long_files`:** 7 → 6. `frontend/src/lib/api.ts` (1880 linhas)
    decomposto em 14 módulos por domínio (`lib/api/{core,auth,reports,
    documents,vault,pipeline,config,transactions,dashboard,notifications,
    workspaces,goals,tasks,feature-flags}.ts`). `lib/api.ts` vira barrel
    re-export de 19 linhas — imports existentes seguem intactos. Páginas
    >500 linhas (`pipeline/page.tsx`, `documents/page.tsx`,
    `transactions/page.tsx`, `plano/page.tsx`, `plano/alocacao/wizard/page.tsx`,
    `dashboard/page.tsx`) ficam para 2ª rodada.
  - **T3 `ts_long_functions`:** 24 → 18 (high severity: 12 → 0). 10
    componentes/hooks decompostos:
    `NotificationCenter` (164→11, extrai hook + 3 sub-componentes),
    `CommandPalette` (111→31), `RegisterPageInner` (130→24),
    `LoginPageInner` (108→20), `UpcomingTasksWidget` (94→25),
    `ApendiceASection` (61→10), `WorkspaceSwitcher` (49→5),
    `useConfirmDialog` (48→<20), `useCurrentUser` (41→<20),
    `useCurrentWorkspace` (46→16), `computePhaseStates` (44→16),
    `ThemeToggle` (41→8), `GoalPremissasCard` (43→14).
  - **T4 `ts_forbidden_filename`:** 1 → 0. `frontend/src/lib/utils.ts`
    renomeado para `lib/cn.ts` (único export era o helper `cn()`);
    49 imports atualizados mecanicamente.
  - **T5 `ts_hex_colors`:** 12 → 0. Paleta inline de 12 hex no
    `dashboard/page.tsx` → `var(--chart-1..12)` (ADR-076). Vars já
    emitidas pelo build de `design-tokens/tokens.json`.
  - **Impact:** frontend offenders 53 → 30 (redução 43%). Zero regressão
    — 397 vitest tests passam. Zero mudança funcional/visual (sweep
    puramente organizacional + tipagem). Próximos passos A6g.4b (2ª
    rodada) atacam 6 páginas ainda >500 linhas + 18 funções
    remanescentes de média severidade.

- **A6e.3 — application layer: 3 slices (2026-04-21):** Primeira
  entrega do trilho "1 endpoint = 1 use case" (ADR-101 R15) com escopo
  restrito a 3 agregados sem acoplamento ao pipeline. 22 use cases
  testáveis sem DB, 56 tests novos em `backend/tests/application/`
  rodando em ~8s com fakes em memória.
  - **Base compartilhada:** `backend/app/application/base/errors.py`
    (`DomainError`/`NotFoundError`/`ConflictError`/`ValidationError`
    tipadas); exception handlers globais em `main.py` traduzem para
    HTTP (404/409/422) — routers não têm try/except.
  - **Slice 1 (FamilyMember · commit `46a704c`):** 8 use cases
    (`create_family_member`, `list_family_members`, `update_family_member`,
    `delete_family_member` + `create_bank_account`, `list_bank_accounts`,
    `update_bank_account`, `delete_bank_account`). Router novo
    `backend/app/api/family_members.py` (160l, 8 endpoints).
    `backend/app/api/config.py` encolheu 846 → 600 linhas; helpers
    `_import_family_members`/`_export_family_members` usam
    `FamilyMemberRepository` (zero `select(FamilyMember)` no api/).
    25 tests puros com `FakeFamilyMemberRepository` + `FakeVault`.
  - **Slice 2 (Category · commit `39c6711`):** 4 use cases
    (`create_category`, `list_categories`, `update_category`,
    `delete_category`). Router novo `backend/app/api/categories.py`
    (87l). `config.py` 600 → 464 linhas; `_import_categorization`/
    `_export_categorization` usam `CategoryRepository`. Helper
    compartilhado `backend/app/services/config_defaults.py`
    (`load_global_json`/`load_global_yaml`) evita duplicar I/O de
    defaults em 3 routers. 12 tests puros.
  - **Slice 3 (Goal · commit `3b4c306`):** 10 use cases cobrindo os
    4 tipos (IF, aportes, dólar, alocação) versionados append-only
    (ADR-073): 4 `compute_*_projection` (dry-run), 2 read
    (`get_active_if_goal`/`get_active_typed_goal`), 2 list
    (`list_if_goal_versions`/`list_typed_goal_versions`), 2 write
    (`create_if_goal_version`/`create_typed_goal_version` genérica).
    Router `backend/app/api/goals.py` reescrito com helpers internos
    `_read_active_typed`/`_history_typed`/`_write_typed`/`_with_author`
    — User lookup permanece no router como cross-aggregate.
    `FakeGoalRepository` replica a semântica append-only (tiebreak por
    contador de inserção evita ordenação não-determinística em testes
    com 2 versões no mesmo dia). `goal_service.py` intocado (compute
    functions continuam domain-pure). 19 tests puros.
  - **OpenAPI snapshot inalterado** nos 3 slices — operationIds
    preservados via nomes idênticos dos endpoints (FamilyMember/Goal)
    ou alias de import (Category: `uc_list_categories` etc.).
  - **Fora do escopo (explícito):** ConfigBlob (ficou em `config.py`),
    Document, Task, `/api/v1/` prefix, domain events tipados — todos
    esperam A6e.3b (pós-A6f.1) ou slices subsequentes (A6e.4/.5/.6).

- **A6g.5 — tests sweep Tier 4 (2026-04-21):** Split de
  `tests/test_llm_stages.py` (920 linhas, maior arquivo in-scope da
  sweep) em 3 arquivos de teste + 1 módulo de helpers compartilhados.
  Os 52 tests coletados permaneceram idênticos ao baseline.
  - `tests/_llm_stage_fixtures.py` (201l, prefixo `_` mantém fora da
    coleção pytest): `make_llm_ctx`, `make_llm_ctx_no_llm`,
    `make_e{1,15,2_llm,7_review}_output`, `make_llm_call_result`.
    Ex-`_mock_*` privados viraram API pública do suite.
  - `tests/test_llm_stages.py` (920 → 384l): validadores (E1/E1.5/E2),
    `TestValidationResult`, `TestOutputConverters`,
    `TestOrchestratorLLMStages`.
  - `tests/test_llm_stages_per_stage.py` (328l, novo): `TestE1Stage`,
    `TestE15Stage`, `TestE2LLMStage`, `TestA6aStructural` (ADR-105).
  - `tests/test_llm_stages_e7.py` (84l, novo): `TestE7ReviewStage`,
    `TestE7ReviewOutputConverter`.
  - Suíte `pytest tests` 1461 passed / 2 skipped (baseline preservado).
  - A6g.5 agora entrega **todos os 4 tiers**; nenhum arquivo in-scope
    acima de 500 linhas em `tests/`. `backend/tests/test_content_classifier.py`
    (655l), `test_task_repository.py` (532l), `test_multi_tenant_isolation.py`
    (537l) e `tests/unit/pipeline/test_patrimonio_resolvers.py` (705l) /
    `test_e3_reconciler_adapter.py` (545l) seguem fora do escopo
    (prompt pediu só `test_llm_stages.py`).

- **A6f.1 — Pipeline-as-Service HTTP boundary (2026-04-21 · ADR-112):**
  Primeira fronteira language-neutral real. Nasce o serviço standalone
  `pipeline-service/` (FastAPI, 3 rotas + WS) que envolve
  `pipeline.orchestrator` atrás de HTTP. Backend passa a consumir via
  `PipelineServiceClient` (Protocol) com duas implementações
  intercambiáveis: `HttpPipelineClient` (quando `MATHOMS_PIPELINE_SERVICE_URL`
  está setada) e `InProcessPipelineClient` (default — zero regressão em
  dev/test/single-process). **`backend/app/tasks/pipeline_task.py` zero
  `from pipeline.orchestrator` imports** (gate verificável por grep).
  Três slices:

  1. **Bootstrap FastAPI standalone** — 23 arquivos novos em
     `pipeline-service/` (app/api + contracts + services); 11 tests
     greenfield (executor com monkeypatch do orchestrator, coordinator
     com stop_on_error/skip_llm, event publisher com fakeredis, health).
  2. **Backend adapter** — `backend/app/services/pipeline_client.py`
     com Protocol + 2 implementações + factory idempotente singleton
     (stateless-safe, ADR-111). `pipeline_task.py` usa
     `client.execute_stage(...)` via closure que injeta `workspace_id`;
     `client.is_llm_stage(stage)` substitui `LLM_STAGES`. 8 novos tests
     em `test_pipeline_client.py` (MockTransport round-trip HTTP,
     factory switching, protocol compliance).
  3. **Smoke + docker-compose + OpenAPI snapshot** —
     `docker-compose.pipeline-service.yml` compõe sobre o smoke.yml
     (porta 8001, healthcheck, mount ro de `pipeline/`).
     `backend /health` passa a reportar `pipeline_service_url` +
     `pipeline_service_reachable` (informational). Novo snapshot
     `docs/api/v1/pipeline-service.openapi.json` + snapshot test
     espelhando o do backend. `make update-openapi-snapshot` agora
     depende de `update-pipeline-service-openapi`.

  **Stateless rigoroso (ADR-111):** pipeline-service **sem DB** — backend
  permanece dono do `DBArtifactStore`; artefatos cruzam a fronteira via
  `workspace_root` em disco. Redis singleton é lazy+idempotente.

  **Escopo deferido explícito** (anotado em ADR-112 + commit messages):
  extração de `_materialize_adapter_configs`/`_persist_llm_suggestions`/
  `_create_report_from_output` para services dedicados e redução de
  `pipeline_task.py` para ≤100 linhas ficam em slice próprio
  (comportamento-preservante). Go rewrite do pipeline-service é sprint
  A6f seguinte — contrato HTTP já está fixado.

  **Testes verdes:** `pytest pipeline-service/tests -q` (12) + backend
  934 passed / 4 skipped (baseline 926 + 8 tests novos) + pipeline 1461
  passed. `dev/check_pipeline_boundaries.py` passa. OpenAPI snapshot
  regenerado com 22 linhas novas (dois campos de health).

  **Commits:** `7ee9703` (slice 1) · `bacb218` (slice 2) · `d4c4361` (slice 3).

- **A6g.5 — tests sweep Tier 3 (2026-04-21):** Decomposição das 3
  fixtures in-scope >30 linhas via helpers privados nomeados. Zero
  mudança semântica; mesmo contador de tests.
  - `tenants` (69 → 11 linhas) em `test_multi_tenant_isolation.py`:
    `_TenantSpec` dataclass congelado + `_TENANT_A`/`_TENANT_B`
    constantes + helper `_seed_full_tenant(db, spec)`. Elimina
    duplicação ~30 linhas entre tenants A e B.
  - `workspace_with_run` (70 → 24 linhas) em `test_pipeline_task.py`:
    split em `_build_file_backed_engines(db_file)` (cria async+sync
    engines + metadata no mesmo SQLite file) e `_seed_pending_run`
    (user+workspace+run). Fixture body agora só orquestra.
  - `golden_workspace` (70 → 12 linhas) em `test_golden_pipeline.py`:
    split em 3 helpers com responsabilidade única
    (`_seed_golden_user_and_workspace`,
    `_seed_golden_titular_with_account`,
    `_seed_golden_categories_with_keywords`).

  Suítes: `pytest backend/tests` 926 passed/4 skipped (baseline
  preservado). A6g.5 agora entrega Tiers 1 + 2 + 3 — Tier 4 (split de
  arquivos >500 linhas) segue opcional e fora do escopo executado.

- **A6g.5 — tests sweep Tier 1 + 2 (2026-04-21):** Aplicação do `§Code
  style › Testes` aos arquivos não-golden de `backend/tests/` +
  `tests/unit/pipeline/`. Zero lógica de negócio tocada.
  - **Tier 1 — fakes nomeados > `MagicMock` inline** (commit `cf8a4a5`):
    39 ofensores zerados em 4 arquivos. Novo diretório
    `backend/tests/fakes/` com 4 fakes:
    - `FakeRedisPublisher` (substitui 13 `MagicMock` em `test_events.py`;
      captura `publish(channel, payload)` em lista inspecionável).
    - `FakeSyncDbSession` + `FakeSyncSessionFactory` (substituem 22
      `MagicMock` em `test_pipeline_task.py::TestPipelineService`; drop-in
      para `SyncSessionLocal()` + `db.query(...).filter(...).first()` +
      `db.get(...)`).
    - `FakeScalarSession` (substitui 3 `MagicMock` em
      `test_premissas_snapshot.py`; `scalars(stmt).all()` com rows
      pré-populadas).
    - `FakeLLMClient` (substitui 1 `MagicMock` em `test_llm_service.py`;
      shape `.chat.completions.create(...)` como LiteLLM client).
  - **Tier 2 — nomes descritivos** (commit `e35837e`, 3 renames):
    `TestSafeFilename.test_basic` → `test_plain_pdf_name_is_preserved`;
    `TestClassifyFileWithInjectedExtractor.test_happy_path` →
    `test_classifies_from_injected_extractor_content`;
    `TestTemporalGapConfig.test_default` → `test_default_tolerance_is_4_days`.
  - **Tier 3 (fixtures >30l)** — inicialmente adiada (só 3 fixtures
    in-scope, abaixo do threshold ≥5 do prompt); entregue na mesma
    data em commit separado (ver entrada "A6g.5 — tests sweep Tier 3"
    acima).
  - **Fora de escopo (inalterado):** 16 arquivos golden/paridade,
    `tests/fixtures/**` (A6g.2), `frontend/tests/**` (A6g.4),
    enforcement em pre-commit (A6g.6). Suítes: `pytest backend/tests`
    926 passed/4 skipped; `pytest tests` 1461 passed/2 skipped.

- **Plano-mestre A6 absorvido em fontes canônicas (2026-04-21):** O
  `_scratch/plano_migracao_artifacts_db.md` (4146 linhas, v3.6) que
  vivia gitignored na máquina do founder foi absorvido nas fontes
  versionadas. Motivação: 20+ refs em canônicos (ROADMAP, BACKLOG,
  ARCHITECTURE, SETUP, DECISIONS, runbooks, prompts) apontavam para
  arquivo que não existia em clones frescos — agentes LLM batiam em
  404. Também: drift silencioso entre o plano (detalhado) e BACKLOG/
  ROADMAP (resumidos).

  Conteúdo único migrado:
  - **§7 Checklist de testes por fase** (92 linhas, 8 fases + métricas
    de sucesso) → `docs/TESTING.md §Critérios de aceite por fase`.
  - **§15 LGPD D1-D5** (5 decisões arquiteturais: crypto app-level,
    audit log, retenção 2 anos, masking de logs) → `docs/BACKLOG.md
    §F7B — Decisões arquiteturais LGPD`, com link para tasks 7B.1/.5/
    .7/.9/.17/.18 que as implementam.
  - **§16 Observabilidade de cutover** (5 métricas Prometheus + 4
    alertas + runbook T-24h/T-0/T+48h) → `docs/runbooks/cutover.md`
    (nova §2.5 e §2.6; fix de 6 refs a `_scratch/compare_disk_vs_db.py`
    → `dev/compare_disk_vs_db.py` onde o script realmente vive).
  - **§1 Motivação P1-P11** → `docs/ARCHITECTURE.md §17.0` em 3
    bullets consolidados com links para as ADRs individuais que
    formalizam cada problema.

  Refs removidas/fixadas (5 commits no trilho de absorção):
  - `ROADMAP.md §Sprint A6`, `SETUP.md §10`: substituídas por
    pointers para BACKLOG + ARCHITECTURE + DECISIONS.
  - `BACKLOG.md §Sprint A6` cabeçalho: nova linha "Fontes canônicas"
    listando os 4 targets.
  - `ARCHITECTURE.md §17`: removido "Plano completo" broken link.
  - `DECISIONS.md`: 7 refs em ADRs 082/098/100/101/102/103/109
    substituídas por links para as subseções respectivas do BACKLOG.
  - `docs/agent_prompts/track_a6g2...`: ref em "Referências" aponta
    para as 4 fontes canônicas.

  Refs intencionalmente preservadas: 4 entradas históricas em
  CHANGELOG.md (registros temporais das sessões A5a-A6f); 1 em
  ARCHITECTURE.md §17.0 (narrativa histórica "plano viveu em
  _scratch...", não link clicável).

  `_scratch/plano_migracao_artifacts_db.md` deletado localmente —
  tudo de único foi migrado; o restante estava duplicado com ADRs
  082-111, BACKLOG §Sprint A6, e código real em `pipeline/**`.

- **Agent prompts — 3 novas lanes paralelas da Onda 2 (2026-04-21):**
  Prompts self-contained para as 3 próximas lanes que podem ser
  executadas em paralelo agora, sem esperar A6g.4 (🚧 ocupada com 2
  worktrees). Cada prompt segue o cabeçalho padrão da README
  (`Lane ID`, `Branch prefix`, `Paralelo com`, `Conflita com`, `Onda`)
  + estrutura tiers/gates/rollback/coordenação.

  - **[track_a6f1_pipeline_service.md](agent_prompts/track_a6f1_pipeline_service.md)** — Pipeline-as-service (HTTP boundary, ADR-102). **Greenfield** em `pipeline-service/`; 3 slices (bootstrap FastAPI standalone → backend `PipelineServiceClient` adapter com fallback `InProcessPipelineClient` → smoke + OpenAPI + docker-compose). Mapeado ~2200 linhas core afetadas; 2-3 sessões estimadas.
  - **[track_a6g5_tests_sweep.md](agent_prompts/track_a6g5_tests_sweep.md)** — Tests sweep em `tests/`, `tests/unit/pipeline/`, `backend/tests/` (excluindo 16 goldens + fixtures A6g.2). Tier 1 `MagicMock` → fake nomeado (39 ofensores; top 2 em `test_events.py` + `test_pipeline_task.py`). Tier 2 nomes descritivos. Tier 3+4 opcionais.
  - **[track_a6e3_use_cases.md](agent_prompts/track_a6e3_use_cases.md)** — Application layer R15 (ADR-101) com **scope slicing** para evitar overlap com A6f.1: cobre apenas FamilyMember + Category + Goal (3 agregados sem imports de `PipelineRun`). ConfigBlob/Document/Task ficam para A6e.3b pós-A6f.1 merge.

  **Mapeamento de overlap** (documentado em cada prompt):
  - A6f.1 + A6g.5 podem colidir em `backend/tests/test_pipeline_task.py` — resolvido por precedência de merge.
  - A6e.3 scope reduzido evita `backend/app/api/pipeline.py` e deps → zero conflito com A6f.1.
  - A6g.5 cria testes novos em `backend/tests/application/` (novo dir) → zero conflito com A6e.3.

  **README + BACKLOG atualizados**: `docs/agent_prompts/README.md` ganha 3 linhas no índice; tabela "Lanes abertas agora" no BACKLOG agora linka os 3 prompts.

- **Docs — pickup-protocol + fonte única de ondas (2026-04-21):** Reorganização
  dos 4 artefatos de orientação (CLAUDE.md, ROADMAP.md, BACKLOG.md,
  docs/agent_prompts/) para resolver dois gaps que vinham causando
  drift entre ROADMAP e BACKLOG e colisão esporádica entre agentes:

  - **CLAUDE.md §Antes de pegar uma task** (nova subseção entre
    §Protocolo de início de sessão e §Naming de branch): comando
    `git for-each-ref refs/remotes/origin/agent/` para listar branches
    ativas por recência + regra "slug de branch == slug de lane; se
    já há commit <24h, pegue outra lane".
  - **BACKLOG §Sprint A6** ganhou no topo (logo após o Status global)
    as subseções **"Lanes abertas agora — pickup table"** (Lane, branch
    slug, prompt, dependências, onda, status) e **"Ondas paralelas —
    mapa de dependências"** (diagrama ASCII movido do final de §A6g).
    Bloco duplicado removido. Índice do BACKLOG aponta para as 2 novas
    subseções com "← agente começa aqui".
  - **ROADMAP §Sprint A6** enxugado — tabela detalhada de sessões foi
    removida; ROADMAP agora traz só snapshot curto + link para BACKLOG
    como fonte única. Elimina drift (ROADMAP ficava parado em
    2026-04-19 enquanto BACKLOG avançava).
  - **docs/agent_prompts/README.md** (novo): índice de prompts
    disponíveis + pickup protocol + cabeçalho padrão recomendado
    (`Lane ID`, `Branch prefix`, `Depende de`, `Paralelo com`,
    `Conflita com`, `Onda`). Retrofita o cabeçalho em
    `track_a6g2_pipeline_style_sweep.md` e
    `track_a6g4_frontend_style_sweep.md`.

  **Motivação**: o diagrama de ondas estava 250+ linhas depois do
  início de §Sprint A6 no BACKLOG (agente raramente chegava nele);
  CLAUDE.md §Protocolo de início de sessão só checava working tree
  local, sem instruir agentes a olharem branches `agent/*` remotas
  antes de pegar task. Mudança cirúrgica — nenhum código tocado,
  só documentação.

- **A6f.3 — follow-up: redaction + pipeline stage spans (2026-04-21) — ADR-110:**
  Fecha dois gaps do track original de A6f.3 que haviam ficado fora da
  primeira entrega (2026-04-20).

  - **Gap 9 — redaction no `MathomsJsonFormatter`** (`backend/app/core/logging.py`):
    `SENSITIVE_FIELD_SUBSTRINGS` + `_redact()` recursivo substituem por
    `***` qualquer campo cujo nome contenha `password`, `secret`, `token`,
    `api_key`, `authorization`, `cpf`, `cnpj`, `valor`, `value_brl`,
    `amount_brl`, `saldo`. Match case-insensitive em substring (ex.: cobre
    `anthropic_api_key`, `Authorization` header). Aplica também em dicts
    e listas aninhadas passadas via `extra=`. Defesa em profundidade
    contra vazamento de credenciais e PII monetária para Loki/Datadog/
    CloudWatch — complementa CLAUDE.md §"Regras críticas" (proibição de
    logar dinheiro real).
  - **Gap 7 — spans OTel custom por stage** (`pipeline/orchestrator.py`):
    `_run_stage` envolve o runner em `tracer.start_as_current_span("pipeline.{stage}")`
    com atributos `pipeline.stage`, `pipeline.run_id`,
    `pipeline.workspace_root`, `pipeline.is_llm`. Branches de falha
    (`SystemExit`, `Exception`) marcam `pipeline.success=False` e, no
    caso de exceção genérica, chamam `span.record_exception(exc)`.
    Import via `try/except ImportError` com fallback `nullcontext()` —
    preserva boundary ADR (`opentelemetry-api` é framework-neutral;
    `dev/check_pipeline_boundaries.py` OK). Sem provider configurado,
    `get_tracer` retorna `NoOpTracer` — zero overhead em CLI/testes.
  - **Novo: `backend/tests/test_otel_traces.py`** — 6 tests com
    `InMemorySpanExporter`: idempotência de `setup_otel`, success path
    de stage span, `SystemExit(1)` fecha span com atributos de falha,
    exceção genérica registra `record_exception`, FastAPI emite span
    `GET /ping`, fallback quando `_TRACER is None`.
  - **Impact**: backend pass +6 (test_otel_traces.py), pipeline
    inalterado, boundary check OK. `test_structured_logging.py`
    cresce de 8 → 11 tests (top-level redaction, nested redaction,
    cobertura de lista).

- **A6e.7 — Slice vertical `Task` (2026-04-21) — ADR-101:**
  Oitavo e **último** agregado per-slice do trilho A6e. Último também
  em complexidade (3 sub-agregados: Task + TaskAttachment +
  TaskSuggestion). Fecha a migração por agregado; próximos passos A6e
  são transversais (use cases R15, routers finos R16, /v1 prefix,
  domain events).
  - **Novo: 3 repositórios separados** (decisão do prompt — agregados
    relacionados mas com ciclos de vida distintos):
    - [`TaskRepository`](../backend/app/repositories/task_repository.py):
      `list` (com `TaskFilters` + priority_rank CASE S<R<O), `list_all`
      (inclui done/cancelled para export), `get_by_id`,
      `get_by_number`, `list_by_parent` (subtasks), `next_number`
      (max+1 atômico), `add` (flush-opt-in), `save` (dirty flush),
      `delete`.
    - [`TaskAttachmentRepository`](../backend/app/repositories/task_attachment_repository.py):
      `list_by_task` (DESC created_at), `get_by_id`, `add`, `delete`.
      **Só DB** — storage (FS/MinIO) fica no service que compõe.
    - [`TaskSuggestionRepository`](../backend/app/repositories/task_suggestion_repository.py):
      `list_by_status` (default pending, `status=None` retorna todas),
      `get_by_id`, `add`, `save` (approve/reject flow).
  - **Novo: DTOs canônicos em [`schemas/dto/task/`](../backend/app/schemas/dto/task/)**
    (R12 ISP) — 9 módulos especializados: `types.py` (Literals
    compartilhados), `response.py` (TaskBase + TaskResponse +
    ScanDeadlinesResponse), `command.py` (Create/Update/StatusTransition
    — todos `*Command`), `filters.py` (TaskFilters), `progress.py`
    (TaskProgressResponse), `attachment.py` (sub-agregado),
    `suggestion.py` (sub-agregado), `mapper.py` (3 funções
    `*_to_response` puras, testáveis sem DB).
  - **Refactor: services** (net -200 linhas):
    - `task_service.py` delega persistência ao TaskRepository;
      regras de domínio intactas (ALLOWED_TRANSITIONS, dependency
      check de parent, vocab validation de categoria).
    - `task_attachment_service.py` compõe StorageService +
      TaskAttachmentRepository; binário fica fora do repo.
    - `task_suggestion_service.py` workflow approve/reject/merge com
      transação única (materializa Task via task_service na aprovação).
  - **Refactor: [`api/tasks.py`](../backend/app/api/tasks.py)**
    (17 endpoints) — `grep "select(Task|TaskAttachment|TaskSuggestion"
    = zero`; todos os retornos via mapper (`task_to_response`,
    `task_attachment_to_response`, `task_suggestion_to_response`);
    commands em todos os PATCH/POST bodies.
  - **Compat binária:** [`schemas/task.py`](../backend/app/schemas/task.py)
    vira shim re-exportando todos os nomes legados: `TaskCreate`,
    `TaskUpdate`, `TaskStatusTransition`, `TaskProgress`,
    `TaskSuggestionCreate/Approve/Reject`, `TaskFilters`, etc.
    `task_notification_service`, `task_progress_service`, seed
    scripts e `test_task_service.py`/`test_tasks_api.py` passam sem
    modificação.
  - **Testes novos:**
    [test_task_dto_mapper.py](../backend/tests/test_task_dto_mapper.py)
    (18 testes, puros) +
    [test_task_repository.py](../backend/tests/test_task_repository.py)
    (24 testes com DB real — filtros, ordenação S→R→O + deadline asc,
    isolamento multi-tenant em 3 repos, cross-tenant safety em
    attachments/suggestions, `next_number` por workspace,
    `list_by_parent` para subtasks).
  - **OpenAPI snapshot atualizado:** 7 renames `*Request`→`*Command`
    + `TaskProgress`→`TaskProgressResponse`; descrições populadas dos
    docstrings dos DTOs.
  - **Escopo deixado para frente:** nenhum aggregate residual. O trilho
    A6e per-aggregate está completo — próximos slices A6e (.3 use cases,
    .4 routers finos, .5 /v1 prefix, .6 events) são transversais.
  - **Impact**: 926 passed / 4 skipped (+42 tests vs 884 pós-A6e.6;
    zero regressão). Commits: `daddb8d` (3 repos), `93cef55` (dto),
    `c05e51b` (services+router+shim), `0c8fd11` (testes),
    `042c6ed` (openapi snapshot).

- **A6g.1 — Auditoria inicial de code style drift (2026-04-21):**
  Entrega o gate que destrava as sub-fases A6g.2-.5. Script
  [`dev/audit_code_style.py`](../dev/audit_code_style.py) (CLI fino) +
  pacote interno [`dev/_audit_cs_internals/`](../dev/_audit_cs_internals/)
  (models, walker, detectores Python/TS, renderers, runner — todos
  arquivos ≤360 linhas, funções ≤20 linhas, sem `Dict[str, Any]` nos
  boundaries). Mede **10 categorias Python (P1-P10)** e **5 TypeScript
  (T1-T5)** com severidade `critical/high/med/low/info` e IDs estáveis
  (`P1-0001`...) para diff entre rodadas. Primeira rodada em
  `_scratch/code_style_audit_20260421.{json,md}`: **467 py + 159 ts
  escaneados, 2047 ofensores** (462 high, 556 med, 1001 low, 28 info).
  Top alvos de sweep: `scripts/e6_render.py` (3875 linhas — anti-exemplo
  acima do e5_analyze.py), `scripts/e_reset.py::main` (372 linhas),
  `backend/app/api/config.py` (7 `Dict[str, Any]` em boundary). Dogfood:
  `python dev/audit_code_style.py --path dev/audit_code_style.py
  --category P1,P2,P6 --severity high,med --strict` → 0 ofensores. Tempo
  total: ~2s (alvo <30s). Flag `--strict` exit 1 se houver ofensor
  ≥ med (default exit 0 — informativo). Reaproveita
  `dev/check_pipeline_boundaries.py` para P10 (sem duplicação). BACKLOG
  §A6g.1 ✅.

- **A6e.6 — Slice vertical `Goal` (2026-04-21) — ADR-101:**
  Sétimo agregado migrado para o padrão DDD/SOLID do backend API
  (R12-R14). Goal é o único agregado multi-tipo (4 types: IF,
  APORTE_MENSAL, DOLARIZACAO, ALOCACAO_ALVO) — testa a estrutura de
  DTOs separados por tipo com mapper paramétrico.
  - **Novo: [`GoalRepository`](../backend/app/repositories/goal_repository.py)**
    async (170 linhas) — 4 métodos encapsulando a semântica versionada
    (ADR-073): `get_active_by_type` (vigente — `effective_to IS NULL`),
    `get_by_id`, `list_by_workspace_and_type` (histórico DESC por
    `effective_from`), `create_new_version` (atômico `close active +
    flush + insert` — o flush intermediário resolve o unique index
    parcial `ux_goals_current_ws_type` antes do insert).
    Validação de `goal_type` contra `VALID_GOAL_TYPES` em todas as
    operações; R13 em todo predicado; não commita (R14) — caller é
    dono do boundary transacional.
  - **Novo: DTOs canônicos em [`schemas/dto/goal/`](../backend/app/schemas/dto/goal/)**
    (R12 ISP) — 4 módulos por tipo (`if_goal.py`, `aporte.py`,
    `dolar.py`, `alocacao.py`), cada um com 7 DTOs (Inputs, Derived,
    ComputeRequest/Response, UpsertCommand, Response, HistoryResponse).
    `base.py` (`GoalResponseBase`, ex-`_GoalResponseBase`) com campos
    comuns. `mapper.py` (`goal_to_typed_response`) resolve a classe
    correta por `goal.type` via `GOAL_TYPE_DTO_CLASSES` — ponto único
    de extensão. `goal_to_if_response` atalho narrow para IF.
    `meta_version_from_params` migra do service para o mapper.
  - **Refactor: [`goal_service.py`](../backend/app/services/goal_service.py)**
    (-200 linhas) — persistência delegada ao repo; compute services
    (`compute_if/aporte/dolar/alocacao_derived`) **intocados** (domain
    logic puro, ficam no service por design); helpers cross-aggregate
    (`_resolve_author_names` para User lookup,
    `get_latest_report_patrimonio_liquido` para Report) permanecem
    por serem composição fora do agregado Goal.
  - **Refactor: [`api/goals.py`](../backend/app/api/goals.py)**
    (16 endpoints) — `grep "select(Goal" = zero`; chamadas de mapper
    passam apenas `created_by_name` (sem mais 3 kwargs de classes);
    `*UpsertRequest` → `*UpsertCommand`.
  - **Compat binária:** [`schemas/goal.py`](../backend/app/schemas/goal.py)
    vira shim re-exportando todos os DTOs com nomes legados
    (`*UpsertCommand` alias `*UpsertRequest`, `GoalResponseBase` alias
    `_GoalResponseBase`). Seed scripts (`seed_goals_*`), factory
    builder `make_if_goal` e `test_goal_service.py` passam sem
    modificação.
  - **Testes novos:**
    [test_goal_dto_mapper.py](../backend/tests/test_goal_dto_mapper.py)
    (16 testes, puros — dispatch por tipo, fallbacks de `meta_version`,
    `goal_to_if_response` narrow) +
    [test_goal_repository.py](../backend/tests/test_goal_repository.py)
    (12 testes com DB real — vigente scoped ao ws, histórico ordenado,
    `create_new_version` fecha vigente ANTES do insert e cross-tenant
    safety garantida).
  - **OpenAPI snapshot atualizado:** 4 renames `*UpsertRequest` →
    `*UpsertCommand` + descrições de docstrings reformatados.
  - **Escopo deixado para frente:** `goal_compute_*.py` services são
    domain logic e permanecem; Report lookup
    (`get_latest_report_patrimonio_liquido`) fica em goal_service
    até Report virar agregado próprio (slice futuro).
  - **Impact**: 884 passed / 4 skipped (+28 tests vs 856 pós-A6e.5;
    zero regressão). Commits: `41fa878` (repo), `b2e1f90` (dto),
    `eca59b0` (service+router+shim), `1c8ecfb` (testes),
    `8760d7e` (openapi snapshot).

- **A6e.5 — Slice vertical `Document` (2026-04-21) — ADR-101:**
  Sexto agregado migrado para o padrão DDD/SOLID do backend API (R12-R14).
  Continua o trilho iniciado em A6e.1+.2 (FamilyMember) e seguido por
  A6e.3 (Category) + A6e.4 (ConfigBlob). Document é o maior router do
  backend (~794 linhas, 13 endpoints) e destrava A6e.6/.7.
  - **Novo: [`DocumentRepository`](../backend/app/repositories/document_repository.py)**
    async (190 linhas) — 7 métodos com `workspace_id` no predicado (R13):
    `list` (filtros `statuses` [=, IN, lista vazia early-return] +
    `doc_type`), `get_by_id`, `get_by_content_hash`,
    `find_fuzzy_duplicate_id` (dedupe por triplo doc_type+bank_code+period
    com `exclude_id`), `list_non_error`, `add` (flush controlado),
    `delete`. **Não commita** — caller é dono do boundary transacional
    (R14), essencial para o upload que usa savepoint por arquivo para
    tratar `IntegrityError` da unique index `content_hash`.
  - **Novo: DTOs canônicos em [`schemas/dto/document/`](../backend/app/schemas/dto/document/)**
    (R12 ISP) — `response.py` (`DocumentResponse`, `DocumentListResponse`,
    `DocumentUploadResponse`, `DocumentExtractJsonResponse` e
    `DocumentReclassifyResponse` — os 2 últimos migram classes inline do
    router), `command.py` (`DocumentUpdateCommand` com empty-string → None
    validator, paridade com legado), `mapper.py` (`document_to_response`
    puro, testável sem DB).
  - **Refactor: [`api/documents.py`](../backend/app/api/documents.py)**
    (-67 linhas líquidas) — todos os 8 endpoints recebem
    `repo = Depends(_get_document_repo)`; `grep "select(Document"` vazio.
    Upload flow preservado em todos os detalhes (savepoint, fuzzy-dedupe
    cross-referencial via `repo.find_fuzzy_duplicate_id`, audit log
    seletivo, cleanup de arquivo órfão).
  - **Compat binária:** [`schemas/document.py`](../backend/app/schemas/document.py)
    vira shim re-exportando `DocumentResponse`, `DocumentListResponse`,
    `DocumentUploadResponse` e `DocumentUpdateRequest` (alias para
    `DocumentUpdateCommand`) — `test_documents.py` e demais testes
    legados passam sem modificação.
  - **Testes novos:**
    [test_document_dto_mapper.py](../backend/tests/test_document_dto_mapper.py)
    (15 testes, puros) + [test_document_repository.py](../backend/tests/test_document_repository.py)
    (16 testes com DB real — isolamento multi-tenant em todos os métodos,
    `statuses=[]` early-return, ordenação por `uploaded_at` DESC, fuzzy
    dedupe cross-tenant safety).
  - **OpenAPI snapshot atualizado:** 3 renames (`DocumentUpdateRequest`
    → `DocumentUpdateCommand`, inline `ExtractJsonResponse` →
    `DocumentExtractJsonResponse`, inline `ReclassifyResponse` →
    `DocumentReclassifyResponse`) + descrições populadas dos docstrings
    dos DTOs.
  - **Escopo deixado para frente:** `document_processor.py`,
    `document_pipeline_sync.py` e `tasks/pipeline_task.py` continuam
    acessando ORM direto — migração é R15 (use-case layer) em slice
    futuro, conforme planejado no prompt da track.
  - **Impact**: 847 passed / 4 skipped (+31 tests vs 816 baseline; zero
    regressão). Commits: `9cbcf2f` (repo), `16ef59c` (dto),
    `4958d9a` (router + shim), `ab240aa` (testes),
    `2c5c134` (openapi snapshot).
- **A6f.6 — Stateless-rigoroso: audit + multi-worker integration test (2026-04-20) — ADR-111:**
  Terceira entrega da A6f (language-neutral boundaries). Prova empírica que
  o backend já é multi-worker-safe e formaliza a regra arquitetural que
  proíbe estado mutável in-memory de processo.

  - **Novo: `docs/STATELESS_AUDIT.md`** — 214 linhas, 10 seções auditando o
    backend para R19 (stateless-ready): `@lru_cache` (zero), globals de
    módulo (17 catalogados — todos imutáveis ou idempotentes), sessões
    WebSocket (já via Redis pub/sub desde P5), rate limits (DB-backed),
    background tasks (zero `asyncio.create_task`), file locks (zero),
    contextvars (request-scoped), settings (imutáveis), Celery globals
    (zero), Vault (idempotente). **Conclusão: zero gaps críticos.**
  - **Novo: `backend/tests/integration/test_multi_worker_concurrency.py`** —
    5 tests de integração rodando **dois `httpx.AsyncClient` simultâneos**
    sobre `ASGITransport` (simula dois workers uvicorn) com `fakeredis.FakeServer`
    compartilhado entre `fakeredis.FakeRedis` (sync, publisher Celery) e
    `fakeredis.aioredis.FakeRedis` (async, subscriber FastAPI WebSocket):
    1. JWT válido em worker A → worker B aceita (prova statelessness de auth).
    2. Workspace criado via worker A → visível em worker B via
       `/api/me/workspaces` (prova DB como única fonte de verdade).
    3. Rate limit de invitations (`MAX_PENDING_PER_WORKSPACE=10`) alternando
       criações entre A e B → 11ª retorna 429 `{code: "limit_reached"}`
       (prova contador DB-backed).
    4. Evento `stage.started` publicado por Celery (sync Redis) → WebSocket
       conectado em worker B recebe via subscriber async (prova canal
       `pipeline:{run_id}` como única ponte cross-process).
    5. Evento `run.completed` cross-worker → WS fecha graciosamente.
    Tempo de suite: ~1.05s. Fixture `shared_redis` injeta FakeServer em
    `redis.Redis.from_url` + `redis.asyncio.from_url`.
  - **Novo: ADR-111** — formaliza **R19 (stateless-rigoroso)**: zero estado
    mutável in-memory de processo; exceções (constantes/settings/singletons
    idempotentes) catalogadas em `docs/STATELESS_AUDIT.md`; proíbe
    `asyncio.create_task` para estado, `@lru_cache` em hot-path com
    invalidação, file locks cross-process, dicts globais mutáveis.
    `publish_event` é a **única** ponte cross-worker; canal
    `pipeline:{run_id}` é contrato.
  - **CLAUDE.md**: nova seção `### Stateless rigoroso (ADR-111 · A6f.6 · R19)`
    em §"Auth portability" — referência canônica para agentes que vão
    adicionar endpoints/tasks novos.
  - **Impact**: 740 pass / 12 fail (+5 tests novos vs 735 baseline A6f.3;
    mesmo 12 fail pré-existentes; zero regressão). A6f.6 desbloqueia
    escalonamento horizontal (K8s/ECS) sem mudanças de código.

  Commits: `9881135` (audit), `817f447` (test), `52c252d` (docs ADR/etc).

- **A6f.4 — DB Schema Reference auto-gerado + snapshot test (2026-04-20) — ADR-102 R20:**
  Segunda entrega da A6f (language-neutral boundaries). Formaliza o schema
  do banco como referência canônica e detecta regressões de portabilidade.

  - **`dev/generate_db_schema_reference.py`** — gerador idempotente que
    introspecciona `Base.metadata` (todos os 27 models via
    `backend/app/models/__init__.py`) e produz markdown determinístico:
    - Tabelas em ordem alfabética; colunas com tipo SQL literal
      (`str(col.type)`), nullability, default, PK/FK/UNIQUE/INDEX tags.
    - Constraints formais (PK multi-col, FK com ON DELETE/UPDATE, UK, CHECK)
      agrupadas e sorted; indexes sorted by name.
    - Auditoria em 3 categorias de risco:
      1. `PickleType` / `TypeDecorator` exótico (bloqueante).
      2. `DateTime` naive (sem `timezone=True`).
      3. Enums nativos vs `VARCHAR + CHECK` (informativo).
    - Inventário de colunas JSON (hotspot para schemas explícitos).
    - Bloco Go struct por tabela com tags `db:"..." json:"..."` para
      servir de referência em migração futura.
  - **`docs/DB_SCHEMA_REFERENCE.md`** — 1193 linhas, committed, atualizado
    via `make update-db-schema-reference`.
  - **`backend/tests/test_db_schema_reference_snapshot.py`** — compara
    byte-a-byte o `.md` committed com o output atual do gerador; falha
    com diff unified em caso de drift.
  - **`Makefile`** — target `update-db-schema-reference` (padrão A6f.2).

  Resultado da auditoria no schema atual (27 tabelas):
  - ✅ **Zero `PickleType` / `TypeDecorator`** — schema 100% nativo SQL.
  - ✅ **Zero `DateTime` naive** — todos usam `timezone=True`.
  - 5 Enums nativos (`documents.doc_type`/`status`, `pipeline_runs.status`,
    `pipeline_stage_logs.status`, `stage_reviews.status`) — portáveis
    para Go via `type Status string` + constantes.
  - 18 colunas JSON inventariadas.

  Commit: `1e4ab08` em `main` (2026-04-20).

- **A6d.3 (fechada) — Caminho B puro para E5 + E5.N (2026-04-20) — ADR-100 · ADR-097:**
  Fecha a promessa de A6d (commitment não-opcional) para os dois últimos
  stages que rodavam em Caminho B pragmático:

  - **A6d.3.3 Etapa 2+3 — E5 via adapter**: ``scripts/e5_analyze.main_with_store``
    agora delega para ``E5AnalyzerAdapter.from_configs(...).analyze_via_store(store)``
    (+143/-54 locs). 14+ domain services (``PatrimonioCalculator``,
    ``EmergencyReserveCalculator``, ``FinancialScoreCalculator``,
    ``RatiosCalculator``, ``IFProjector``, ``CenariosConjugeAnalyzer``,
    ``FluxoCaixaEnricher``, 7 analyzers A5a/b/c) passam a compor o E5.
    Helper ``_merge_life_plan_into_goals`` extrai metas de
    ``life_plan_goals.md`` (regex) e injeta em ``goals.json`` no Caminho B.
    Dois ajustes de paridade em ``E5AnalyzerAdapter``:
    ``conjuge_key=""`` quando não há cônjuge (não força ``"mariana"``);
    ``goals={}`` ao instanciar ``PontosFortesAnalyzer`` (legado omite
    ``progresso_pct``). Bug de tipo corrigido em
    ``CenariosConjugeAnalyzer._compute_prazo`` — fallback ``999`` (int)
    ao invés de ``999.0`` (float) para paridade JSON-string.
    Golden: ``tests/test_e5_main_with_store_parity.py`` (2 cenários,
    tolerância 0.01 BRL em whitelist monetária).

  - **A6d.3.2 — Decomposição E5.N ``build_narrativas``**: 425 locs inline em
    ``scripts/e5n_narrativas.build_narrativas`` extraídos para novo pacote
    ``pipeline/domain/services/narrativas/`` com arquitetura ISP/R9 limpa:

    - ``context.py`` — ``NarrativasContext`` (dataclass frozen) concentra
      titular_key/conjuge_key/nomes + 10 ``key_*`` strings derivadas
      (``key_inv_titular``, ``key_cenarios_section``, etc.), substituindo
      globals ``_KEY_*`` de módulo. Factory ``from_family_config(family)``.
    - ``format_helpers.py`` — ``fmt_currency``, ``fmt_percent``, ``fmt_num``,
      ``fmt_usd``, ``validate_narrativas`` (aceita override de
      ``cenarios_section_key`` para contexto dinâmico).
    - ``perfil_familia_narrator.py`` — ``PerfilFamiliaNarrator(ctx).narrate()``
      produz ``{left, right}`` com 4 ``<p>`` cada (≤300 chars, enforçado
      pelo validator).
    - ``summaries_narrator.py`` — ``SummariesNarrator(ctx).narrate()``
      produz ``{s1..s10}`` (dimensões patrimônio, score, carteira, imóveis,
      EUA, cambial, IF, PJ, riscos, decisões).
    - ``charts_narrator.py`` — ``ChartsNarrator(ctx).narrate()`` produz 20
      blocos ``{context, conclusion}`` para os charts do relatório,
      incluindo bloco dinâmico ``<conjuge>_cenarios`` (chave via
      ``ctx.key_cenarios_section``).
    - ``builder.py`` — ``E5NarrativasBuilder(ctx)`` orquestra os 3
      narradores + extrai ``riscos_prioritarios`` / ``decisoes_prioritarias``
      de ``metrics`` com guards de tipo (``isinstance``). Factory
      ``from_family_config(family)``.

    ``scripts.e5n_narrativas.build_narrativas()`` vira delegate de 2 linhas.
    ``validate_narrativas`` legado vira wrapper que injeta
    ``_KEY_CENARIOS_SECTION`` para o helper. Aliases
    ``fmt_currency``/``fmt_percent``/``fmt_num``/``fmt_usd`` mantidos em
    ``scripts.e5n_narrativas`` via re-export para backward-compat.

    **Golden**: ``tests/test_e5n_builder_decomposition.py`` — 10 tests
    cobrindo (1) output estrutural (3 sections, s1-s10, 20 charts,
    validator pass), (2) keys dinâmicas (substituir ``bob``→``yolanda``
    propaga em ``<conjuge>_cenarios``), (3) delegação bit-a-bit
    (``scripts.build_narrativas`` == ``builder.build``), (4) back-compat
    de format helpers, (5) exposição pública dos 3 narradores.
    Parity legado↔novo continua coberto por
    ``tests/test_e5n_e7_main_with_store_parity.py``.

  - **Caminho B puro — estado final pós-A6d.3**: E3 (A2), E4 (A6d.3 refactor
    pendente), **E5 (A6d.3.3)**, **E5.N (A6d.3.2)**, E7 (pragmático — LLM-bound,
    não migra), E1.5c (pragmático — stage trivial, não justifica refactor).
    Scripts ``e5_analyze.py`` e ``e5n_narrativas.py`` mantêm ``_init_config``
    globals para CLI direto (``main(root_dir)`` legado), mas ``main_with_store``
    não depende deles no hot-path — domain services consomem value objects de
    config tipados.

  - **Testes**: 1427 tests passando (+80 vs baseline A6d.3.3), zero
    regressão. Suite tempo: 15.2s.

- **A6d.3.3 (parcial) — Calculadoras puras + adapter sem placeholders (2026-04-20) — ADR-100:**
  Foundation definitiva para fechar Caminho B puro no E5. Três calculadoras
  de domínio novas substituem a lógica inline de ``scripts/e5_analyze.py``:

  - **``pipeline/domain/services/patrimonio_types.py``** — value objects puros
    (``MemberIdentity``, ``PatrimonioConfig``, ``CaixaDetalhe``,
    ``PatrimonioInputs``) + extractors triviais (``imovel_valor``,
    ``imovel_desc``, ``veiculo_valor``, ``investimento_valor``, ``get_bens``,
    ``safe_float``). Zero globals.
  - **``pipeline/domain/services/patrimonio_resolvers.py``** — 4 formatos de
    baseline (dict members, list-of-dicts, E1.5 declarations com G01-G99,
    v1.5 consolidated com aliased keys E1.5 v2). Helpers privados
    ``_classify_bens_by_grupo``, ``_resolve_ano_ref``, ``_is_conjuge_exclusive``.
  - **``pipeline/domain/services/patrimonio_calculator.py``** — orquestração
    com paridade byte-a-byte vs ``analyze_patrimonio`` legado (residência via
    keyword, investimentos atuais vs IRPF fallback, caixa E3 vs residual,
    largest-remainder method para percentuais soma=100%, chaves dinâmicas
    ``investimentos_<titular>``/``<conjuge>`` via ``MemberIdentity``).
  - **``pipeline/domain/services/reserva_emergencia_calculator.py``** —
    ``EmergencyReserveCalculator`` + ``ReservaEmergenciaConfig.from_scoring_json``.
    Paridade com ``analyze_reserva_emergencia``.
  - **``pipeline/domain/services/financial_score_calculator.py``** —
    ``FinancialScoreCalculator`` + 5 componentes configuráveis (taxa_poupanca,
    cobertura, endividamento com flag ``invertido``, progresso_if,
    diversificacao). Paridade com ``calculate_score``.

  - **``E5AnalyzerAdapter`` refatorado** — remove ``_extract_patrimonio_for_ratios``,
    ``score_placeholder``, ``reserva_placeholder``. ``analyze_via_store``
    agora produz ``patrimonio_full``/``reserva``/``score`` com dados completos
    via os 3 calculadores injetados. Novo helper ``_load_caixa_from_e3``
    (shell I/O via ``store.list_keys("E3")``).

  - **Testes**: +178 unit tests novos (45 types + 59 resolvers + 23 calculator
    + 12 reserva + 25 score + 14 wiring). Suite ``tests/unit/pipeline/``
    total: 1003 passando, zero regressão.

  - **Pendente (próxima sessão)**: switch ``scripts/e5_analyze.main_with_store``
    para usar o adapter + golden parity E5 + decomposição ``build_narrativas``
    (A6d.3.2) + docs finais. Branch: ``agent/a6d3-close-caminho-b/20260420-1223``.
- **A6f.3 — Structured JSON logging + OpenTelemetry bootstrap (2026-04-20) — ADR-110:**
  Logs estruturados + tracing opt-in para API e worker. Essencial para
  qualquer investigação cross-service e pré-requisito para A6f.1 (pipeline-
  service) e A6f.6 (multi-worker stateless).

  - **Novo: `backend/app/core/logging.py`** — `MathomsJsonFormatter`
    (extende `python-json-logger`) com campos `timestamp` (UTC ISO 8601 `Z`),
    `level`, `logger`, `message`, `trace_id`, `workspace_id`, `user_id`,
    `pipeline_run_id`. `setup_logging()` idempotente, respeita
    `MATHOMS_LOG_LEVEL` e `MATHOMS_LOG_FORMAT=json|text`.
    `get_logger(name)` força namespace `mathoms.*`.
  - **Novo: `backend/app/middleware/correlation.py`** —
    `CorrelationIdMiddleware` (Starlette) lê/gera header `X-Trace-Id`
    e reflete no response. Contextvars `_trace_id`, `_workspace_id`,
    `_user_id`, `_pipeline_run_id` com setters/getters tipados.
  - **Novo: `backend/app/core/otel.py`** — `setup_otel(service_name)`
    idempotente; `LoggingInstrumentor` sempre liga (popula
    `otelTraceID`/`otelSpanID` nos records); `OTLPSpanExporter` opt-in
    via `OTEL_EXPORTER_OTLP_ENDPOINT`. `instrument_fastapi(app)` instala
    FastAPI + SQLAlchemy instrumentation no lifespan; `instrument_celery()`
    no `worker_process_init` signal (fork-safe).
  - **Wire-up**: `backend/app/main.py` chama `setup_logging()` +
    `setup_otel("mathoms-api")` no módulo; lifespan chama
    `instrument_fastapi(app)` antes de `init_db()`;
    `CorrelationIdMiddleware` registrado antes do CORS.
    `backend/app/worker.py` adiciona `@worker_process_init.connect` que
    chama `setup_logging` + `setup_otel("mathoms-worker")` +
    `instrument_celery` em cada worker process.
  - **Dependências**: `python-json-logger>=3.2`, `opentelemetry-api/sdk>=1.30`,
    `opentelemetry-exporter-otlp-proto-http>=1.30`,
    `opentelemetry-instrumentation-{fastapi,sqlalchemy,celery,logging}>=0.50b0`.
  - **Tests**: [`test_structured_logging.py`](../backend/tests/test_structured_logging.py)
    com 8 tests — formatter JSON parseável, correlation context,
    omit-when-unset, idempotência, middleware generate+reflect trace_id,
    middleware honor incoming header, OTel opt-in, jq-compat.
  - **Env vars novas**: `MATHOMS_LOG_LEVEL` (INFO), `MATHOMS_LOG_FORMAT`
    (json), `OTEL_EXPORTER_OTLP_ENDPOINT` (unset).
  - **Impacto**: 735 pass / 12 fail — zero regressão vs. baseline
    origin/main (727 pass / 12 fail; as 12 falhas são pré-existentes).

- **A6f.2 + A6f.5a — OpenAPI completo + Auth portability (2026-04-20) — ADR-109:**
  Primeira sessão da A6f (language-neutral boundaries, ADR-102 · R18-R20).
  Fecha gap de contrato explícito para clients em outras linguagens
  (Go, TS, Rust hipotéticos) sem mexer em dados produtivos.

  - **A6f.2 — OpenAPI completo**:
    - ~12 DTOs novos cobrindo endpoints que retornavam `dict` genérico:
      `HealthResponse`, `NewDocCountResponse`, `RunActionResponse`,
      `NotificationsMarkedReadResponse`, `ScanDeadlinesResponse`,
      `ConfigImportResponse`, `ReportTasksResponse` +
      `ReportTaskSnapshotItem`.
    - 4 endpoints de file streaming (`/reports/{id}/download.html`,
      `/reports/{id}/download.pdf`, `/transactions/export`,
      `/documents/{id}/file`) ganham `response_class=` explícito.
    - `/reports/{id}/data` recebe `response_class=JSONResponse` com
      `responses` OpenAPI documentando o shape dinâmico do E5.
    - Snapshot committed em [`docs/api/v1/openapi.json`](api/v1/openapi.json)
      (12856 linhas, sorted keys). README em [`docs/api/v1/README.md`](api/v1/README.md).
    - `make update-openapi-snapshot` regenera com um comando.
    - Teste estrutural [`test_openapi_response_models.py`](../backend/tests/test_openapi_response_models.py)
      falha se novo endpoint for mergeado sem contrato explícito.
    - Teste de snapshot [`test_openapi_snapshot.py`](../backend/tests/test_openapi_snapshot.py)
      com diff determinístico em caso de drift.

  - **A6f.5a — Auth portability documentada** (ADR-109):
    - JWT **mantido em HS256** com payload canônico `{sub, exp, tv}` —
      qualquer lib Go/TS/Rust lê sem ajuste.
    - Fernet **mantido** para secrets — spec público (version byte 0x80),
      existe lib Go (`fernet-go`).
    - [`test_auth_portability.py`](../backend/tests/test_auth_portability.py)
      com 12 testes de parity: JWT (algoritmo + claims + expiração +
      tamper + encode externo) e Fernet (roundtrip + formato estável
      + tamper + Unicode + edge cases).
    - AES-GCM + HKDF **deferido** para sub-fase nova **A6f.5b** com
      gatilho explícito (requisito compliance / migração Go real / CVE).
    - RS256 também deferido (**A6f.5c**) — só com separação real entre
      emissor e validador.

  - **Impacto**: Zero breaking change em produção; zero dados
    re-encriptados; contrato de 118 endpoints formalizado em JSON.
    14 tests novos passando, zero regressão nos 691+ tests originais.

- **A6e.1+.2 — Slice vertical `FamilyMember` (2026-04-20) — ADR-101:**
  Primeiro agregado migrado para o padrão DDD/SOLID do backend (R12-R13).
  Estabelece o trilho que sessões A6e seguintes replicam para outros
  agregados (Category, Document, Goal, Task, PipelineRun).
  - **Novo: `FamilyMemberRepository` async** ([family_member_repository.py](../backend/app/repositories/family_member_repository.py))
    — 13 métodos (list_by_workspace, get_by_id[_with_accounts], get_by_key,
    key_exists com exclude_id, create, update, delete, delete_all_in_workspace,
    list_accounts, get_account, add_account, update_account, delete_account).
    `BankAccount` é sub-entidade do mesmo agregado (sem repo separado,
    cascade delete explícito para funcionar em SQLite + PostgreSQL).
  - **Novo: DTOs canônicos em `schemas/dto/family_member/`** (R12 ISP)
    — `response.py` (FamilyMemberResponse, BankAccountResponse,
    FamilyMemberListResponse), `command.py` (Create/Update Commands com
    validação de slug e CPF), `mapper.py` (member_to_response faz CPF
    decrypt via Vault Protocol + birth_name unpack;
    convert_global_defaults_to_responses preserva F6.5E.6 neutralização).
  - **Refactor: [`config.py`](../backend/app/api/config.py) endpoints members/accounts**
    — 5 endpoints (list/create/update/delete membros + 4 nested accounts)
    delegam ao repositório e retornam DTOs; zero `select(FamilyMember)` ou
    `select(BankAccount)` nos endpoints (os imports/exports ainda acessam
    ORM direto — migram junto com ConfigBlob aggregate).
  - **Compat binária:** [`schemas/config.py`](../backend/app/schemas/config.py)
    preserva nomes legados (`FamilyMemberSchema`, `FamilyMemberCreateRequest`,
    etc.) como aliases dos novos DTOs — `test_config_api.py` e
    `test_config_models.py` passam sem modificação. ~130 linhas de
    duplicação removidas.
  - **Testes novos:**
    [test_family_member_dto_mapper.py](../backend/tests/test_family_member_dto_mapper.py)
    (10 testes, puros, sem DB; usam vault fake via Protocol) +
    [test_family_member_repository.py](../backend/tests/test_family_member_repository.py)
    (13 testes com DB real — isolamento multi-tenant, key unicity com
    exclude_id, cascade explícito, get_by_id_with_accounts com
    populate_existing).
  - **Regression gate:** `test_anti_regression_bank.py::TestBug004FallbackCPFLeak`
    aponta agora para `schemas/dto/family_member/mapper.py` (novo lar do
    `cpf=None` sentinel).
  - Delivered on branch `a6e/family-member-slice` — 4 commits ancorados.

- **Estratégia de subdomínios `mathoms.ai` (2026-04-20) — ADR-108:**
  Domínio `mathoms.ai` adquirido via Cloudflare Domains. URLs canônicas
  definidas para F7A:
  - **Produção:** `app.mathoms.ai` (produto) · `api.mathoms.ai/v1/...`
    (backend + WS) · `ops.mathoms.ai` (console interno F7F) ·
    `docs.mathoms.ai` · `status.mathoms.ai` · apex `mathoms.ai` (landing).
  - **Staging:** `*.staging.mathoms.ai`.
  - **Dev local:** `localhost:3000` / `localhost:8000`.
  - Multi-tenancy via path (`app.mathoms.ai/w/<slug>/...`), subdomain-
    per-tenant reservado para enterprise.
  - DNS em Cloudflare (proxy ON para apex/docs/status, OFF para
    app/api/ops). TLS via Let's Encrypt DNS-01 challenge + Traefik
    provider `cloudflare`.
  - Console interno `ops.` com IP allowlist + MFA; session cookie
    separado de `app.` (zero-trust).
  - Rotas internas do backend em `api.mathoms.ai/v1/internal/*`.
  - Emails institucionais: `noreply@`, `support@`, `hello@`, `ops@`,
    `security@` com SPF+DKIM+DMARC obrigatório.
  - **Docs atualizados:** [ADR-108](DECISIONS.md#adr-108--estratégia-de-subdomínios-mathomsai--cloudflare-dns),
    [ARCHITECTURE.md §18](ARCHITECTURE.md#18-domínios-e-urls-públicas-f7a),
    [ROADMAP.md F7A](ROADMAP.md#f7--produção--security--lgpd--operational-readiness-próxima),
    [BACKLOG.md 7A](BACKLOG.md#7a--docker--deploy--https-semana-1-2) (+4 tasks
    novas: 7A.7b CORS/ipAllowList, 7A.8b SPF/DKIM/DMARC, 7A.8c emails,
    7A.11b cookie leakage test), INTERNAL_ADMIN_ROADMAP (P1/P4),
    `_scratch/plano_migracao_artifacts_db.md` (A6f.1 → pipeline-service
    em rede privada, **sem** subdomain público).
  - **Esforço agregado em F7A:** +4h sobre o planejado original (DNS
    Cloudflare 30min + Traefik DNS-01 1-2h + migração CORS/cookies/env 2h).

- **A6d.2 — Testabilidade dos `analyze_*` sem disco (2026-04-20):**
  Parsers de arquivos MD (`life_plan_goals.md`, `tarefas.md`, `milhas.md`)
  extraídos em funções **content-based puras**, com shell loaders finos
  para back-compat. Fecha o primeiro pilar do A6d.
  - `scripts/e5_analyze.py`:
    - `parse_tarefas_md_content(text)` + `parse_milhas_md_content(text)` —
      puras, sem I/O, testáveis sem `tmp_path`. Os wrappers
      `parse_tarefas_md(content=None)` e `parse_milhas_md(content=None)`
      aceitam `content` para delegação direta; quando `None`, delegam ao
      shell loader (lê `CONFIG_TAREFAS` / `CONFIG_MILHAS` do disco).
    - `extract_if_target_from_life_plan(life_plan_content=None)`,
      `extract_if_trs(life_plan_content=None)`,
      `extract_renda_passiva_from_life_plan(life_plan_content=None)` —
      agora aceitam content string opcional. `_read_life_plan_content()` é
      o único ponto de I/O para `LIFE_PLAN_GOALS`.
    - `analyze_goals(patrimonio, life_plan_content=None)` — propaga
      `life_plan_content` para os extractors. Paridade preservada (None →
      comportamento legado de disco).
    - `main_with_store(ctx)` lê os 3 MDs uma única vez no shell e repassa
      aos helpers puros (evita múltiplas leituras + torna o pipeline
      testável sem disco quando content é injetado).
  - `scripts/e7_review.py::load_methodology()` — docstring formaliza a
    separação shell↔parser (a função já era um shell loader fino;
    `extract_persona_from_methodology(content)` sempre foi pura).
  - `tests/unit/pipeline/test_e5_content_parsers.py` — **26 testes** cobrindo
    parsers content-based (tarefas: sections, priorities, status, invalid
    rows; milhas: programas, filtros, totais; extract_if_*: priority
    `goals.json > content > raise`; shell loaders tolerando arquivos
    ausentes). Zero uso de `tmp_path` nos casos puros.
  - **ADR-100** (A6d commitment): A6d.2 delivered; A6d.3 partialmente
    delivered (§ abaixo).
  - **Tests** — 1240 passam, 2 skips, 1 deselect (teste pré-existente
    unrelated) · zero regressão nos goldens (E3/E4/E5/E5.N/E6/E7).

- **A6d.3.1 — E4 já em Caminho B puro (verificado 2026-04-20):**
  Auditoria confirmou que `scripts/e4_categorize.main_with_store(ctx)` **já
  usa** `E4CategorizerAdapter.from_configs(...)` +
  `adapter.categorize_via_store(store)` + `serialize_e4_artifacts(result)`.
  Zero uso das funções legadas `process_transactions`,
  `build_receitas_unified`, `build_despesas_unified`, `build_fluxo_mensal_detalhado`
  dentro de `main_with_store`. Essas funções permanecem em uso apenas no
  legado `main(root_dir)` (CLI / back-compat). **A6d.3.1 marcado como ✅.**

- **A6d.3.2 / A6d.3.3 — E5.N e E5 permanecem em Caminho B pragmático (deferred):**
  A decisão de manter `main_with_store` desses stages reutilizando funções
  legadas foi **mantida explicitamente** após auditoria:
  - **E5.N**: `build_narrativas()` legado ainda é o único caminho completo;
    decompor para domain service é P2 no backlog e aumenta risco sem ganho
    de cobertura relevante.
  - **E5**: `E5AnalyzerAdapter` (A5c) existe mas é **incompleto para paridade**
    — `_extract_patrimonio_for_ratios` é simplificado vs `analyze_patrimonio`
    (muitos campos ausentes), `score`/`reserva` usam placeholders, e a API
    de pontos-fortes/urgentes depende de score real. Reescrever
    `main_with_store` usando-o diretamente quebraria o golden de paridade.
    O plano para A6d.3.3 fica estendido: completar os placeholders do adapter
    (integrar `PatrimonioCalculator`, `EmergencyReserveCalculator`,
    `FinancialScoreCalculator` nos resultados tipados) antes do switch.
  - Ambos stages já atingem o critério estrutural: zero `_init_config` em
    `pipeline/stages/` para E5/E5.N (apenas `pipeline/stages/e2.py:41`
    mantém, por E2 ter estrutura multi-módulo separada).

- **Rename do produto: Fin → Mathoms AI (2026-04-19):**
  Renomeação completa do produto em toda a base de código.
  - `env_prefix` do pydantic-settings: `FIN_` → `MATHOMS_` (19 variáveis de ambiente)
  - `PROJECT_NAME`: `"Fin API"` → `"Mathoms AI"` em `backend/app/core/config.py`
  - Banco de dados de dev: `fin.db` → `mathoms.db` (config, alembic.ini, alembic/env.py)
  - Email de seed: `admin@fin.app` → `admin@mathoms.ai`
  - Package Python: `fin-pipeline` → `mathoms-pipeline` em `pyproject.toml`
  - Componentes React: `FinBarChart` / `FinPieChart` / `FinAreaChart` → `MathomBarChart` / `MathomPieChart` / `MathomAreaChart`
  - Schema `$id` URIs: `fin://schemas/...` → `mathoms://schemas/...` (5 schemas em `config/schemas/`)
  - Docstring `backend/app/main.py`: `"Fin API —"` → `"Mathoms AI —"`
  - Todos os cabeçalhos de documentação: `# Fin —` → `# Mathoms AI —`
  - `CLAUDE.md`: produto renomeado de "Fin" para "Mathoms AI"
  - `.env.example`: todas as vars `FIN_*` → `MATHOMS_*` com comentários atualizados

- **Migração infra + domínio — Fases 1-5 completas + 6-8 foundation (2026-04-19):**
  Plano [`_scratch/plano_migracao_artifacts_db.md`](../_scratch/plano_migracao_artifacts_db.md)
  (ADRs 082-096 em [DECISIONS.md](DECISIONS.md)).
  - **Fase 1** — `PipelineArtifact` model + migration `p4q5r6s7t8u9`; `ArtifactStore`
    protocol (`DiskArtifactStore`, `InMemoryArtifactStore`) em `pipeline/artifact_store.py`;
    `DBArtifactStore` em `backend/app/services/db_artifact_store.py` (respeita boundary
    `pipeline/` sem SQLAlchemy); `WorkspaceContext.get_artifact_store()`.
  - **Fase 1.5** — `pipeline/stage_spec.py` (`StageSpec`, `STAGE_REGISTRY`,
    `STAGE_RENAME_MAP`, `FULL_ORDER`, `build_from_map`, `validate_full_order`);
    `pipeline/stage_config.py` (Pydantic frozen, fail-fast); wrappers separados
    `e2_faturas.py` / `e2_extratos.py` (fix de flags); `init_workspace_paths_from_env`
    non-strict no import.
  - **Fase 2** — `MaterializationBridge` context manager (hydrate/persist);
    `PipelineArtifactRepository`; feature flag `MATHOMS_USE_DB_ARTIFACTS` (default `False`).
  - **Fase 3** — `pipeline.stage_runner_compat.run_legacy_with_bridge_if_db` —
    wrappers E3/E4/E5/E5.N/E7/E1.5c rodam via bridge quando store é DB-backed.
  - **Fase 3.2 Caminho B (E2)** — `BankStatement.from_e2_dict()` / `to_e2_dict()`;
    `scripts/e2_extract.run_with_store()` escreve direto via `ArtifactStore`;
    `pipeline/stages/e2.py` refatorado.
  - **Fase 4** — `backend/app/scripts/backfill_artifacts_from_disk.py` (idempotente);
    `reset_documents.py` apaga `pipeline_artifacts`.
  - **Fase 5** — Domain layer `pipeline/domain/` (`Money` com `Decimal` +
    `CURRENCY_PRECISION` rejeitando `float`; `Transaction`, `BankStatement`,
    `Investment`, `InvestmentStatement`, `BaselinePatrimonial`).
  - **Fase 6-7 foundation** — `ReconciliationService(ReconciliationConfig)`,
    `CategorizationService(CategorizationRules)` puros, testáveis sem I/O.
  - **Fase 8 foundation** — 4 calculadoras: `CashFlowAggregator`,
    `PatrimonioCalculator`, `EmergencyReserveCalculator`, `FinancialScoreCalculator`.
    (Faltam `IndependenciaFinanceiraProjector` + `MemberAnalyzer` + refactor real
    do `e5_analyze.py`.)
  - **Fase 9 infra** — Migration Alembic `q5r6s7t8u9v0_rename_stage_identifiers`
    com `apply_rename(bind, mapping)` testável (5 testes); audit script
    `_scratch/audit_stage_references.py`; guardrail
    `tests/unit/pipeline/test_no_legacy_stage_names.py` (soft-fail default,
    hard-fail com `MATHOMS_ENFORCE_STAGE_RENAME=1`). **Não aplicado**: rename físico
    de arquivos em `pipeline/stages/` e `scripts/` (pré-req: Fases 6-8 completas).
  - **Docs** — ADRs 082-096 em [DECISIONS.md](DECISIONS.md); [ARCHITECTURE.md](ARCHITECTURE.md)
    §7 atualizado com abstrações (Pipeline + Domínio); [CLAUDE.md](../CLAUDE.md) com
    tabela de etapas incluindo coluna `Identificador pós-F9`; [README.md](../README.md)
    com status da migração; [SETUP.md](SETUP.md) §10 com instruções de cutover.
  - **Não entregue nesta onda** (planejado para sprint seguinte):
    - Fase 6 Caminho B completo (E3 refactor — 1193 linhas com lógica bank-specific);
    - Fase 7 Caminho B (E4);
    - Fase 8 decomposição completa de `e5_analyze.py` (2598 linhas — estimado 5-8 sem);
    - §15 LGPD (crypto em PII, `access_audit_log`, retention, endpoint esquecimento);
    - §16 Observabilidade (`compare_disk_vs_db.py`, métricas Prometheus, alertas,
      dashboard Grafana).
  - **Fase 6 foundation (Caminho B gradual para E3)** — `E3ReconcilerAdapter`
    em `pipeline/domain/services/e3_reconciler_adapter.py`: lê E2 artifacts do
    store, converte via `BankStatement.from_e2_dict`, aplica `ReconciliationService`,
    persiste E3 no store. Cobre caso simples (extratos de conta); lógica
    bank-specific legada (faturas, CDB, baseline validation, saldo continuity,
    temporal gaps) continua no script via `MaterializationBridge`.
  - **Docs complementares (2026-04-19)** — ADRs 092-096 escritas; [TESTING.md](TESTING.md)
    com seção de testes de domínio e `InMemoryArtifactStore`; [runbooks/cutover.md](runbooks/cutover.md)
    com procedimento T-24h/T-0/T+48h (§16.4 do plano).
  - **Tests** — 1240 testes passando (572 pipeline + 668 backend, zero regressão).

- **A6b.5 — Preparação para smoke test humano (2026-04-19):**
  Infraestrutura para teste end-to-end antes da remoção do bridge (A6c). ADR-103.
  - `docker-compose.smoke.yml`: stack Redis isolada para smoke (`make smoke-up`).
  - `Makefile`: targets `smoke-up/down/reset/seed/logs` + `test/lint/format/check-boundaries`.
    Backend + worker + frontend sobem como processos locais com PIDs em `_smoke_pids/`.
  - `backend/app/scripts/seed_smoke.py`: cria `smoke@mathoms.ai` + `viewer@mathoms.ai`
    com workspaces e copia fixtures para inbox. Idempotente; `--force` recria.
  - `tests/fixtures/smoke_inbox/`: 7 fixtures sintéticos — 2 extratos C6 CSV, 1 duplicata,
    1 extrato Nubank, 1 fatura Nubank, 1 `ambiguous_document-smoke.txt`, 1 `life_plan_goals.md`.
    README descreve cenários cobertos e arquivos que precisam ser adicionados manualmente.
  - `docs/SMOKE_TEST_HUMAN.md`: runbook com 46 checks em 8 categorias
    (auth, docs, pipeline, LLM free-tier, relatório, goals, cutover DB, edge cases) +
    template de decisão A6c + troubleshooting.
  - `GET /health`: inclui `artifact_store_mode: "disk"|"db"` para verificar flag ativa.

- **A6b — Opt-in DB artifacts por workspace + DBArtifactStore no Celery task (2026-04-19):**
  Infraestrutura para ativar `DBArtifactStore` de forma gradual por workspace,
  sem cutover global. ADR-106.
  - `backend/app/models/workspace.py`: campo `use_db_artifacts_override: bool | None`.
    `None` → global flag; `True` → força DB; `False` → força Disk.
  - `backend/alembic/versions/r6s7t8u9v0w1_...py`: migration Alembic.
  - `backend/app/tasks/pipeline_task.py`: `_resolve_use_db_artifacts(ws_id)` verifica
    override do workspace > global flag. Quando DB ativo: abre sessão longa
    (`SyncSessionLocal`), cria `DBArtifactStore`, injeta em `ctx.artifact_store`.
    Commit após cada stage com sucesso; `finally` fecha a sessão.
  - `dev/compare_disk_vs_db.py`: script de paridade — carrega artefatos de disco e
    DB, reporta keys ausentes + conteúdo divergente, gate ≥99%. Ignora `_meta`,
    `created_at`, `updated_at` (diferenças esperadas). Uso: `python dev/compare_disk_vs_db.py <ws_id>`.
  - Discrepâncias esperadas documentadas em ADR-106: timestamps, ordem de listas.
  - A6b.3 (validação em workspace real) fica para A6-human.

- **A6a — LLM stages via ArtifactStore — desbloqueio cutover DB (2026-04-19):**
  E1.5 e E2-llm deixam de escrever artefatos direto em disco e passam a usar
  ``ArtifactStore``. Pré-requisito para ``MATHOMS_USE_DB_ARTIFACTS=true``.
  - `pipeline/stages/e15.py`: `out_path.write_text(...)` → `store.write("E1.5",
    "baseline_patrimonial", baseline_json)`. Artefato produzido: `baseline_patrimonial-
    1.5_baseline.json` (antes: `_consolidated.json`). E1.5c já lê via fallback
    `store.read("E1.5", ...)` (A5f). Workspaces existentes continuam funcionando.
  - `pipeline/stages/e2_llm.py`: `out_path.write_text(...)` → `store.write("E2-llm",
    safe_stem, e2_json)`. `_find_unprocessed_docs` migrada para `store.list_keys(stage)`
    em vez de glob de disco (necessário para DB mode).
  - **E1 e E7-review LLM não migram** (ADR-105): E1 escreve `family_members.json`
    (config do workspace, não artefato de pipeline); E7-review LLM é input ad-hoc
    externo ao loop determinístico.
  - `tests/test_llm_stages.py` — +4 testes (critérios estruturais A6a.3 +
    integration tests com DiskArtifactStore). 52 testes no arquivo.
  - **ADR-105** em [DECISIONS.md](DECISIONS.md).
  - **Tests** — +4 testes (1214 total) · zero regressão.

- **Fase 8 Sessão A5f — E1.5c em Caminho B pragmático (2026-04-19):**
  **Fecha os 7 de 7 stages determinísticos no Caminho B.** `E1.5c`
  (consolidação de baseline patrimonial) era o único stage determinístico
  ainda usando `stage_runner_compat` + `MaterializationBridge` no wrapper.
  - `scripts/e15_consolidate.main_with_store(ctx)` — lê baseline via
    `store.read("E1.5c", "baseline_patrimonial")` (fallback para
    `store.read("E1.5", ...)` quando é a primeira consolidação), invoca
    `consolidate()` legado (paridade 100%), grava resultado via
    `store.write("E1.5c", "baseline_patrimonial", ...)`. Skip gracioso
    quando nenhum baseline encontrado (free tier sem LLM). Coexiste com
    `main(root_dir)` legado.
  - `pipeline/stages/e15c.py` — refatorado para chamar `main_with_store(ctx)`
    direto, via `emit_stage_activity` + delegação. Zero referências a
    `stage_runner_compat` ou `MaterializationBridge`.
  - `tests/test_e15c_main_with_store_parity.py` — **4 testes**: golden de
    paridade com 2 cenários sintéticos (formato `itens[]` atual + formato
    `declarations[]` legado), teste de skip gracioso (free tier sem
    baseline), critério estrutural (wrapper sem bridge).
  - **ADR-104** em [DECISIONS.md](DECISIONS.md): "E1.5c em Caminho B pragmático".
  - **Tests** — +4 testes pipeline (1210 total) · zero regressão.
  - **Status pós-A5f**: `MaterializationBridge` e `stage_runner_compat`
    ficam **sem clientes vivos no Caminho B** (remoção definitiva aguarda
    A6a cutover LLM stages + A6b cutover DB + A6-human). Caminho A6c
    desbloqueado assim que A6a+A6b+A6-human forem concluídos.

- **Fase 8 Sessão A5e — Caminho B ativo para E5.N + E7 (2026-04-19):**
  **Fecha todos os stages determinísticos do pipeline no Caminho B.** E5.N
  (narrativas) e E7 (crossval + apply) saem do bridge. O modo E7-review LLM
  permanece fora do Caminho B — é passo externo/humano, não determinístico.
  - `scripts/e5n_narrativas.main_with_store(ctx)` — lê E5 via `ArtifactStore`,
    invoca `load_metrics_from_e5` + `build_narrativas` + `validate_narrativas`
    legados (paridade 100%), injeta `narrativas` no E5 e grava via
    `store.write("E5", "analise_financeira", ...)`. Coexiste com
    `main(root_dir)` legado.
  - `scripts/e7_review.main_with_store(ctx, mode=...)` com 2 modos:
    - `mode="crossval"` — 14 checks CV1-CV14, extrai persona de
      `methodology.md`, gera template em
      `processed/E7_review/e7_review_template.json` via disco direto
      (paridade com filename legado).
    - `mode="apply"` — valida review JSON, aplica refinamentos ao E5, grava
      E5 atualizado via `store.write(...)`. Skip gracioso quando
      `review_path` ausente + sem template no workspace (free tier).
  - `pipeline/stages/e5n.py` e `pipeline/stages/e7.py` — **não importam
    mais `stage_runner_compat`**. Wrappers chamam `main_with_store(ctx)`
    direto. Critérios estruturais enforçados por testes.
  - `tests/test_e5n_e7_main_with_store_parity.py` — **6 testes**:
    - Golden E5.N: roda E4+E5+E5.N legado e novo sobre mesmo workspace,
      compara `narrativas` campo-a-campo (deve ser idêntico — funções puras).
    - E7 crossval: grava template no path correto, chaves esperadas presentes.
    - E7 apply: skip gracioso sem review_path; rejeita review malformado.
    - 2 critérios estruturais (wrappers sem `stage_runner_compat`).
  - **Tests** — +6 testes pipeline (1206 total, vs 1200 pós-A5d) · backend
    inalterado · boundary check verde · zero regressão.
  - **Status da migração pós-A5e** (revisado após auditoria 2026-04-19):
    - **Caminho B ativo (6 de 7 stages determinísticos)**: E3 (A2) ·
      E4 (A4b) · E5 (A5d) · **E5.N (A5e)** · **E7-crossval (A5e)** ·
      **E7-apply (A5e)**.
    - **Pendente — A5f**: `E1.5c` (`pipeline/stages/e15c.py`) ainda importa
      `stage_runner_compat`. Stage **determinístico** que foi omitido da
      lista da rodada original; corrigido em sessão A5f (ver
      `_scratch/plano_migracao_artifacts_db.md` §18).
    - **LLM stages (5)**: E0-route · E1 · E1.5 · E2-llm · E7-review-LLM
      **não migram para `main_with_store`** (padrão incompatível — invocam
      LLM, não orquestrar stage-to-stage). Mas 3 deles (E1.5, E2-llm) hoje
      escrevem artefatos do pipeline **direto em disco**, bypassando
      `ArtifactStore`. Precisa ajuste separado antes do cutover DB — ver
      **A6a** no plano.
  - **Descoberta crítica na auditoria pós-A5e**: `USE_DB_ARTIFACTS=False`
    em produção; `DBArtifactStore` nunca instanciado pelo backend.
    **Cutover para DB é teórico** — todos os stages rodam sobre
    `DiskArtifactStore` hoje. A migração infra está 100% no código e nos
    testes; falta validação end-to-end em workspace real.
  - **Consequência**: `MaterializationBridge` e `stage_runner_compat`
    ainda têm **1 cliente vivo** (E1.5c). Remoção condicional ao
    completar A5f + A6a + A6b — não "automática" como antes declarado.
    Ver `_scratch/plano_migracao_artifacts_db.md` §17-§19 para plano
    revisado.
  - **Nomenclatura revisada** (§17.2.5 do plano): os 6 stages entregues
    em A2–A5e dividem-se em 2 variantes:
    - **Caminho B puro** (E3, A2): refactor com domain services integrados,
      helpers extraídos, lazy init dos globais.
    - **Caminho B pragmático** (E4, E5, E5.N, E7): I/O via `ArtifactStore`
      + wrapper limpo, mas **mantém** `_init_config`, globals de módulo e
      funções `analyze_*` legadas acopladas a disco. Domain services
      extraídos em A1/A3c/A5a/A5b/A5c (14+ services, 1200+ testes) ficam
      em prateleira — documentação executável sem integração.
  - **A6b.5 + A6-human adicionados** como gate obrigatório antes de
    A6c (remoção do bridge): infraestrutura smoke
    (`docker-compose.smoke.yml`, `Makefile smoke-*`, seed de dados,
    fixtures de documentos, runbook `docs/SMOKE_TEST_HUMAN.md`,
    observabilidade mínima, modo free-tier testável) + **teste manual
    end-to-end pelo David** cobrindo todas as features (auth,
    multi-tenancy, documentos, pipeline, relatório, plano, cutover DB,
    edge cases). Decisão de deletar bridge **depende de aprovação
    humana explícita**.
  - **A6f adicionado ao plano** (commitment): Language-neutral boundaries
    — preparação para eventual migração Go do backend, mantendo Python
    apenas em parsers (`scripts/e2/banks/`), LLM (`pipeline/llm/`) e
    domain services. 6 sub-fases com princípios novos **R18-R20** (wire
    formats explícitos via JSON Schema/OpenAPI, stateless-ready,
    language-neutral data):
    - **A6f.1** — Pipeline como serviço HTTP standalone
      (`pipeline-service/` FastAPI com endpoints `/api/v1/pipeline/...`);
      backend fala com pipeline só via HTTP, nunca por import.
    - **A6f.2** — OpenAPI 3.1 exaustivo + codegen frontend (extensão
      natural de A6e.5).
    - **A6f.3** — Structured logging JSON + OpenTelemetry (traces
      cross-service via OTLP).
    - **A6f.4** — DB schema language-neutral (UUIDs, UTC-aware
      timestamps, enums como VARCHAR + CHECK, JSON columns com keys
      camelCase, sem TypeDecorator exótico).
    - **A6f.5** — Auth portátil (Fernet → AES-GCM; JWT RS256/HS256;
      session store Redis com schema JSON explícito).
    - **A6f.6** — Stateless rigoroso (WebSocket via Redis pub/sub,
      rate limiting em Redis, zero cache in-memory mutable; teste
      multi-worker).
    Estimativa: 6-8 sessões grandes. Independente de A6a-e (pode rodar
    em paralelo). **Valor imediato mesmo se migração Go não acontecer**:
    escala pipeline independente, zero bugs de integração frontend,
    observabilidade real, best-practice de criptografia.
  - **A6e adicionado ao plano** (commitment): DDD/SOLID no backend API
    em 6 sub-fases — traz a disciplina do `pipeline/` para
    `backend/app/` inteiro. Princípios novos R12-R17 (ISP no backend,
    repositórios por aggregate, routers ≤50 linhas, application layer
    por use case, versionamento `/api/v1/`, domain events tipados).
    Escopo: extrair queries SQLAlchemy dos routers (~4900 linhas hoje)
    para repositories; separar DTOs ↔ ORM models; criar
    `backend/app/application/` com use cases explícitos; padronizar
    side-effects via events. Estimativa: 5-7 sessões grandes.
    Independente de A6a-d (pode rodar em paralelo; recomendado depois
    de A6b para validar repository pattern com múltiplos storage
    backends).
  - **A6d confirmado como commitment** (não mais opcional): fechar
    Caminho B puro nos 5 stages pragmáticos em 3 sub-fases:
    - **A6d.1** — Eliminação de globals nos 5 scripts (padrão A3b
      aplicado a `e4_categorize`, `e5_analyze`, `e5n_narrativas`,
      `e7_review`, `e15_consolidate`).
    - **A6d.2** — Testabilidade dos `analyze_*` sem disco (extrair
      reads de `life_plan_goals.md`, `tarefas.md`, `milhas.md`,
      `methodology.md` para shell; funções ficam puras).
    - **A6d.3** — Integração dos 14+ domain services em `main_with_store`
      (E4, E5.N, E5), com golden de paridade por stage.
    Estimativa total: 3-5 sessões grandes. Independente de A6a/b/c
    (cutover DB) — pode rodar em paralelo.

- **Fase 8 Sessão A5d — Caminho B ativo para E5 + golden de paridade (2026-04-19):**
  Fecha a **Fase 8**. E5 sai do bridge e passa ao Caminho B. Estratégia
  pragmática: reutiliza as funções ``analyze_*`` legadas (já testadas,
  isoladas, sem dependências de disco) no ``main_with_store`` para garantir
  paridade 100% no golden — domain services extraídos em A1/A3c/A5a/A5b/A5c
  ficam como foundation para refactor completo num sprint futuro.
  - `pipeline/domain/services/e5_serialization.py` — helpers para montar
    o output `analise_financeira-5_analysis.json`: `build_e5_output`,
    `run_sanity_checks` (7 checks do legado), `build_default_tarefas`,
    `build_default_tarefas_status`, `build_alertas`. Value object
    `E5OutputInputs` consolida os 20+ sub-resultados. **24 testes**.
  - `scripts/e5_analyze.main_with_store(ctx)` — lê E4 + baseline via
    `ArtifactStore`, invoca as 13 funções `analyze_*` legadas, aplica
    sanity checks, preserva `narrativas` de run anterior, escreve via
    `store.write("E5", "analise_financeira", ...)`, valida contra schema
    em Disk. **Coexiste com `main(root_dir)` legado**.
  - `pipeline/stages/e5.py` — **não importa mais `stage_runner_compat`**.
    Chama `main_with_store(ctx)` direto. Critério estrutural enforçado por
    `test_pipeline_stages_e5_does_not_import_stage_runner_compat`.
  - `tests/test_e5_main_with_store_parity.py` — golden de paridade real:
    roda E4+E5 legados vs E4+E5 `main_with_store` sobre **o mesmo** workspace
    sintético, compara `analise_financeira-5_analysis.json` campo-a-campo
    (tolerância 0.01 BRL em whitelist de monetários, ordem-insensitive em
    listas de dicts, normalização de timestamps). **2 testes** (paridade +
    critério estrutural).
  - **Tests** — +26 testes pipeline (1200 total, vs 1174 pós-A5c) · backend
    inalterado · boundary check verde · zero regressão.
  - **Decisão arquitetural documentada**: o `main_with_store` do E5 **não**
    reescreve `analyze_*` com os domain services foundation. Dois motivos:
    (1) `analyze_patrimonio` e `calculate_score` têm lógica complexa
    acoplada a globals (`_TITULAR_KEY`, `_MEMBROS`, etc.) que exigiria um
    sprint dedicado de refactor; (2) paridade 100% com o golden é mais
    importante agora do que puritanismo arquitetural. Os 14+ services
    extraídos em A1/A3c/A5a/A5b/A5c ficam como foundation documentada e
    testada para esse refactor futuro (sprint A6+).
  - **Fase 8 fechada**: E3 + E4 + E5 no Caminho B. Restam E5.N e E7 via
    bridge (sessão A5e).

- **Fase 8 Sessão A5c — 7 analyzers complementares + E5AnalyzerAdapter (2026-04-19):**
  Fecha a **foundation** completa do E5 (todos os analyzers do `e5_analyze.py`
  extraídos). `scripts/e5_analyze.py` e `pipeline/stages/e5.py` **inalterados**
  — bridge ativo. A5d (serializer + `main_with_store` + switch + golden de
  paridade) fica para sessão dedicada (escopo comparável a A4b).
  - `pipeline/domain/services/diagnostico_comportamental_analyzer.py` —
    `DiagnosticoComportamentalAnalyzer` + `DiagnosticoComportamentalConfig`
    + `DiagnosticoItem`. Extrai `analyze_diagnostico_comportamental`
    (e5_analyze.py:2130). Detecta: disciplina poupança, poupança abaixo
    ideal, alta dependência receita pontual. **12 testes**.
  - `pipeline/domain/services/pontos_urgentes_analyzer.py` —
    `PontosUrgentesAnalyzer` + `PontosUrgentesConfig` + `PontoUrgenteItem`.
    Extrai `analyze_pontos_urgentes` (e5_analyze.py:1990). Checks: reserva
    < mínimo, endividamento > max, seguro sempre, rentabilidade N/D.
    **10 testes**.
  - `pipeline/domain/services/equilibrio_cerbasi_analyzer.py` —
    `EquilibrioCerbasiAnalyzer` + `EquilibrioCerbasiConfig` +
    `EquilibrioCerbasi` + `ClassificacaoFaixa`. Extrai
    `analyze_equilibrio_cerbasi` (e5_analyze.py:2351). Classifica perfil
    em Investidor/Equilibrado/Endividado consciente/Gastador a partir do
    % de gastos em categorias "futuro" vs "presente". **14 testes**.
  - `pipeline/domain/services/pontos_fortes_analyzer.py` —
    `PontosFortesAnalyzer` + `PontosFortesConfig` + `PontoForteItem`.
    Extrai `analyze_pontos_fortes` (e5_analyze.py:1694). 8 checks +
    fallback "Análise em Andamento". **19 testes**.
  - `pipeline/domain/services/e5_member_resolver.py` — `E5MemberResolver`
    + `MemberResolverConfig` + `ResolvedMembers`. Extrai
    `_resolve_members` + `_build_members_from_declarations` +
    `_build_members_from_consolidated` (e5_analyze.py:274/311/429). 4
    formatos suportados (dict, list-of-dicts, declarations IRPF,
    consolidado v1.5). **16 testes**.
  - `pipeline/domain/services/fluxo_caixa_enricher.py` —
    `FluxoCaixaEnricher` + `FluxoEnricherConfig` + `FluxoCaixaEnriched` +
    `Janela12m`. Extrai `analyze_fluxo_caixa` (e5_analyze.py:1050).
    Complementa `CashFlowBuilder` (A4a) com one-time vs recorrente,
    janela de 12 meses (rolling), datasets Chart.js. **19 testes**.
  - `pipeline/domain/services/cenarios_conjuge_analyzer.py` —
    `CenariosConjugeAnalyzer` + `CenariosConjugeConfig` +
    `CenariosConjugeResult` + `CenarioItem`. Extrai
    `analyze_cenarios_conjuge` (e5_analyze.py:2181). 3 cenários (Sem
    Trabalhar, Com NCLEX, Com NCLEX + Green Card) com juros compostos.
    **17 testes**.
  - `pipeline/domain/services/e5_analyzer_adapter.py` — `E5AnalyzerAdapter`
    + `E5AnalysisResult`. **Orquestrador** que compõe todos os 13+
    services (A1/A3c/A5a/A5b/A5c). Lê E4 artifacts do store, compõe
    análises, retorna `E5AnalysisResult` frozen. **Não escreve em E5**
    — escrita fica para A5d com `main_with_store`. Factory `from_configs`
    para reduzir boilerplate. **17 testes**.
  - **Tests** — +124 testes pipeline (1174 total) · backend inalterado ·
    boundary check verde · zero regressão.
  - **Pendente para A5d** (próxima — fecha Fase 8):
    - `pipeline/domain/services/e5_serialization.py` — produz
      `analise_financeira-5_analysis.json` a partir de `E5AnalysisResult`.
    - `scripts/e5_analyze.main_with_store(ctx)` coexistindo com
      `main(root_dir)` legado.
    - `pipeline/stages/e5.py` sem `stage_runner_compat`.
    - Golden de paridade `main()` vs `main_with_store()`.

- **Fase 8 Sessões A5a + A5b — 7 analyzers E5 extraídos (2026-04-19):**
  Foundation da Fase 8 (E5 Caminho B). Domain services puros para 7 funções
  `analyze_*` de `scripts/e5_analyze.py` (2598 linhas). **Nenhum toque** em
  `e5_analyze.py` nem em `pipeline/stages/e5.py` — bridge ativo.
  **Sessão A5a — 3 analyzers centrais:**
  - `pipeline/domain/services/if_projector.py` — `IFProjector` +
    `IFProjection` + `IFProjectorConfig`. Extrai `analyze_goals`
    (e5_analyze.py:971) + `extract_if_target_from_life_plan` +
    `extract_if_trs` + `extract_renda_passiva_from_life_plan` +
    `calculate_edad`. Resolve prazo via juros compostos
    `FV = PV·(1+r)^n + PMT·((1+r)^n − 1)/r`. Config tipada recebe
    DOBs, aporte mensal, TRS, retorno real anual. Helpers regex puros
    para `life_plan_goals.md`. **23 testes**.
  - `pipeline/domain/services/ratios_calculator.py` — `RatiosCalculator` +
    `FinancialRatios`. Extrai `analyze_ratios` (e5_analyze.py:1262):
    taxa poupança (recorrente/total), endividamento, cobertura de despesas.
    Prefere janela 12m. Sem config externa. **11 testes**.
  - `pipeline/domain/services/orcamento_calculator.py` —
    `OrcamentoProspectivoCalculator` + `OrcamentoProspectivo`. Extrai
    `analyze_orcamento_prospectivo` (e5_analyze.py:1428) — média mensal por
    categoria. **7 testes**.
  **Sessão A5b — 4 analyzers complementares:**
  - `pipeline/domain/services/endividamento_analyzer.py` —
    `EndividamentoAnalyzer` + `EndividamentoAnalysis` + `DividaItem`.
    Extrai `analyze_endividamento` (e5_analyze.py:1602). Recebe lista de
    membros já resolvidos (desacoplado de `_resolve_members`). **11 testes**.
  - `pipeline/domain/services/previdencia_analyzer.py` — `PrevidenciaAnalyzer`
    + `PrevidenciaAnalysis` + `PrevidenciaConfig` + `IRPFBracket`. Extrai
    `analyze_previdencia_pgbl` (e5_analyze.py:1632): lucro presumido → base
    tributável → limite PGBL → economia IR. Tabela IRPF progressiva via
    config. Paridade com legado documentada (loop sem break sempre pega
    última faixa `None`). **15 testes**.
  - `pipeline/domain/services/investimentos_classes_analyzer.py` —
    `InvestimentosClassesAnalyzer` + `InvestimentosClassesAnalysis` +
    `InvestimentosClassesConfig` + `ClasseAtivo`. Extrai
    `analyze_investimentos_classes` (e5_analyze.py:1516): classifica em 6
    classes (Ações, Renda Fixa, Imóveis Investimento, Cripto, Contas
    Bancárias, Outros) por keywords configuráveis. Residência principal
    identificada por keyword. **20 testes**.
  - `pipeline/domain/services/consumo_consciente_calculator.py` —
    `ConsumoConscienteCalculator` + `ConsumoConsciente` +
    `ConsumoConscienteConfig` + `GastoPontualItem`. Extrai
    `analyze_consumo_consciente` (e5_analyze.py:2039): identifica gastos
    pontuais ≥ threshold (default R$ 2000) fora de categorias recorrentes,
    calcula folga mensal + teto sugerido + equivalente-meses-aporte.
    **23 testes**.
  - **Tests** — +110 testes pipeline (1050 total) · backend inalterado ·
    boundary check verde · zero regressão.
  - **Achado documentado (A5b)**: `analyze_previdencia_pgbl` no legado tem
    loop sem `break` — para qualquer renda com tabela IRPF que termina em
    faixa `None`, a alíquota efetiva vira a da faixa `None` (geralmente
    27.5%). Paridade preservada; comportamento pode ser revisto em sprint
    dedicado.
  - **Pendente para A5c**: `DiagnosticoComportamentalAnalyzer`,
    `PontosFortesAnalyzer`, `PontosUrgentesAnalyzer`, `CenariosAnalyzer`,
    `EquilibrioCerbasiAnalyzer`, `FluxoCaixaEnricher` (extensão do
    `CashFlowBuilder`), + `E5AnalyzerAdapter` orquestrador + `_resolve_members`.
  - **Pendente para A5d**: `e5_serialization.py` + `main_with_store(ctx)` +
    switch do wrapper `pipeline/stages/e5.py` + golden de paridade.
  - **Pendente para A5e**: E5.N + E7 (mais simples, viriam depois).

- **Fase 7 Sessão A4b — Caminho B ativo para E4 + golden de paridade (2026-04-19):**
  Fecha a Fase 7. E4 sai do bridge (`MaterializationBridge`) e passa ao
  Caminho B real. `scripts/e4_categorize.main(root_dir)` legado **inalterado**
  — coexiste para CLI e testes existentes. Segundo stage rodando Caminho B
  (primeiro foi E3 na A2).
  - `pipeline/domain/services/e4_serialization.py` — `serialize_e4_artifacts(result)`
    produz mapping `{artifact_key: payload}` para os 7 arquivos E4 legados
    (`receitas`, `despesas`, `fluxo_mensal_detalhado`, `patrimonio`,
    `investimentos`, `seguros`, `pontos_milhas`); `build_patrimonio_artifact`
    trata ausência de baseline (`{"dados": []}` paridade); helpers
    `filename_for` / `all_filenames` / `payloads_to_files`. **16 testes**.
  - `scripts/e4_categorize.main_with_store(ctx)` — orquestra
    `E4CategorizerAdapter` + `serialize_e4_artifacts`, escreve os 7
    artefatos via `store.write("E4", key, payload)`, valida cada um contra
    `e4_unified.schema.json`, gera sidecar `qa_log.md` (helper
    `_write_qa_log_e4` replica `generate_qa_log`). **Coexiste com
    `main(root_dir)` legado**.
  - `pipeline/stages/e4.py` — **não importa mais `stage_runner_compat`**.
    Chama `main_with_store(ctx)` direto. Critério estrutural enforçado por
    `test_pipeline_stages_e4_does_not_import_stage_runner_compat`.
  - `tests/test_e4_main_with_store_parity.py` — golden de paridade real:
    roda `main(root_dir)` legado e `main_with_store(ctx)` sobre **o mesmo**
    workspace sintético em `tmp_path`, compara os 7 artefatos campo a campo
    (tolerância 0.01 BRL; normalização de `consolidation_date`/
    `data_consolidacao`/`data_processamento`). **2 cenários** parametrizados
    (receitas+despesas simples; baseline + investimentos) + 1 critério estrutural.
  - **Achado durante a paridade** — `e4_categorize._init_config(root_dir)`
    atualiza os globals do módulo mas **não** reinicializa
    `pipeline_common.CONFIG_DIR`, que o helper `_load_json_config_from` usa
    via `_pc.load_json_config`. O legado então lia configs do repo global
    em vez do workspace passado. O runner do golden chama
    `pipeline_common._init_config(workspace)` explicitamente para forçar a
    paridade; a inconsistência do legado persiste (não vale a pena mexer
    agora — A5+ vai remover `_init_config` global por completo).
  - **Tests** — +19 testes pipeline (940 total, vs 921 pós-A4a) · backend
    inalterado · boundary check verde · zero regressão.
  - **Fase 7 fechada**: E3 + E4 no Caminho B; só E5/E5.N/E7 restam via bridge.

- **Fase 7 Sessão A4a — E4 Caminho B foundation (2026-04-19):**
  Domain services puros do E4 extraídos **sem** tocar `scripts/e4_categorize.py`
  nem `pipeline/stages/e4.py`. Bridge continua ativo. Prepara o
  `main_with_store(ctx)` do E4 e switch do wrapper (Sessão A4b).
  - `pipeline/domain/services/keyword_matcher.py` —
    `find_longest_matching_keyword` + `KeywordMatcher` com suporte a
    wildcards prefix/suffix (`PIX*`, `*BOLETO`) e longest-match wins.
    Paridade direta com `find_longest_matching_keyword` do legado
    (e4_categorize.py:110). **14 testes**.
  - `pipeline/domain/services/transaction_classifier.py` —
    `TransactionClassifier(ClassifierConfig)` + value object frozen
    `ClassifiedTransaction` com `kind in {receita, despesa, transferencia}`,
    normalização de `tipo`, inferência por sinal, coerção de `valor`
    BR, fallbacks (`outras_receitas` / `nao_identificado`). Compõe
    `KeywordMatcher` + `InternalTransferDetector` (A3a) +
    `IncomeOriginResolver` (A3a). Decompõe `process_transactions`
    (e4_categorize.py:589-730). **22 testes**.
  - `pipeline/domain/services/cash_flow_builder.py` —
    `CashFlowBuilder` + value objects frozen `ReceitasUnified`,
    `DespesasUnified`, `FluxoMensal`, `CashFlow`. Paridade com
    `build_receitas_unified` / `build_despesas_unified` /
    `build_fluxo_mensal_detalhado` (linhas 741/767/793). Clock
    injetável (`now`) para testes determinísticos. **10 testes**.
  - `pipeline/domain/services/baseline_normalizer.py` —
    `BaselineNormalizer` + `NormalizedBaseline`. Canoniza baseline v2
    → v1 (7 transformações: `pipeline_stage`, `data_processamento`,
    `membros`, `patrimonio_por_ano` derivado de `resumo_patrimonial`,
    enriquecimento de `imoveis_consolidados`, conversão dict→list de
    investimentos, alias de `dividas`). Não muta input. **21 testes**.
  - `pipeline/domain/services/investments_consolidator.py` —
    `InvestmentsConsolidator(InvestmentsConsolidatorConfig)` +
    `ConsolidatedInvestments`. Decompõe `build_investimentos_unified`
    (linha 260): filtra candidates válidos, dedup por
    (instituição, membro) mantendo o mais recente, agrega posições,
    infere membro via `banco_membro`, valida divergência entre
    `saldo_atual` e soma de itens. **14 testes**.
  - `pipeline/domain/services/e4_categorizer_adapter.py` —
    `E4CategorizerAdapter` orquestra E3 → classify → aggregate sobre
    `ArtifactStore`. Factory `from_configs(categorization, family)` reduz
    boilerplate. Lê baseline (E1.5c) e posições (E2-*) com dedup por key
    entre stages. **Não escreve em E4 ainda** — serialização fica para
    A4b. Retorna `CategorizationResult` frozen com `classified`,
    `cash_flow`, `baseline`, `investments`. **13 testes**.
  - `tests/pipeline/goldens/e4/` — 3 fixtures sintéticas + README:
    `cenario_receitas_despesas_simples.json` (1 CLT + 3 despesas),
    `cenario_transferencia_interna.json` (transferências PIX excluídas
    de receitas/despesas), `cenario_baseline_investimentos.json`
    (baseline v2 + 2 posições BTG/Rico).
  - **Tests** — +94 testes pipeline (921 total) · backend inalterado ·
    boundary check verde · zero regressão.
  - **Fora de escopo desta iteração (A4b — próxima)**:
    - `pipeline/domain/services/e4_serialization.py` com os 7 artefatos
      legados (`receitas`, `despesas`, `fluxo_mensal_detalhado`,
      `patrimonio`, `investimentos`, `seguros` placeholder,
      `pontos_milhas` placeholder).
    - `scripts/e4_categorize.main_with_store(ctx)` coexistindo com `main(root_dir)`.
    - `pipeline/stages/e4.py` sem `stage_runner_compat`.
    - Golden de paridade `main()` vs `main_with_store()` no mesmo workspace.

- **Fase 6/7/8 Sessão A3 — cleanup E3 + foundations E4 e E5 (2026-04-19):**
  Sessão combinada A3a + A3b + A3c em escopos mínimos viáveis. Zero mudança
  em `main()` legado de E3/E4/E5 — toda extração é foundation pura.
  - **A3b (cleanup E3 pós-A2)** — `scripts/e3_reconcile.py` não chama mais
    `_init_config(_pc.PROJECT_DIR)` no top-level do módulo. Globals agora
    recebem defaults sensatos no nível de módulo; `_init_config(base_dir)`
    continua disponível para popular do disco quando explicitamente
    chamado por `main(root_dir=…)` ou por testes. Remove side-effect no
    import — o módulo é agora importável puro. Teste estrutural (AST)
    bloqueia regressão. **7 testes**.
  - **A3c (Fase 8 foundation — `MemberAnalyzer`)** —
    `pipeline/domain/services/member_analyzer.py` com value object
    `MemberPatrimonio` (frozen, `Decimal`) e service puro `MemberAnalyzer`.
    Extrai `_get_bens`, `_imovel_valor`, `_imovel_desc`, `_veiculo_valor`,
    `_investimento_valor` (e5_analyze.py:644-692) + a fatia per-member de
    `analyze_patrimonio`: classificação de imóvel como residência por
    keyword, soma de veículos/investimentos/contas-bancárias-extras,
    extração de `total_bens_irpf` e `total_dividas`. Helper
    `aggregate(members)` para soma cross-membro. `to_legacy_floats()` para
    serialização compatível com output atual do E5 (que usa `float`).
    **31 testes**.
  - **A3a (Fase 7 foundation — 2 services)** — preparando o Caminho B do E4
    sem tocar `main()` legado:
    - `pipeline/domain/services/income_origin_resolver.py` —
      `IncomeOriginResolver` + `IncomeOriginConfig`. Extrai `get_pj_origin`,
      `get_clt_origin` e a classificação estática de origem em
      `process_transactions` (e4_categorize.py:660-679).
      `resolve_for_category(category, description)` roteia para PJ, CLT, ou
      tabela estática (`receita_aluguel → "Aluguéis"`, etc.). Fallbacks
      tipados. **17 testes**.
    - `pipeline/domain/services/internal_transfer_detector.py` —
      `InternalTransferDetector` + `InternalTransferConfig`. Extrai
      `is_internal_transfer` (e4_categorize.py:144) com 4 camadas
      (`internal_patterns` substring, `internal_recipients`,
      `bank_specific_patterns` com **match exato**, `global_transfer_patterns`
      substring). Zero configs globais. **15 testes**.
  - **Tests** — +70 testes pipeline (827 total) · backend inalterado ·
    boundary check verde · zero regressão.
  - **Fora de escopo desta iteração** (futuras sessões):
    - A4 (E4 `main_with_store` + switch do wrapper E4) — depende de
      `CashFlowBuilder` + `BaselineNormalizer` + `E4CategorizerAdapter`
      que não couberam em A3.
    - A5 (E5 `main_with_store`) — depende de 4 outras calculadoras
      faltantes em `e5_analyze.py` (`IndependenciaFinanceiraProjector`,
      `RatiosCalculator`, `OrcamentoProspectivoCalculator`,
      `ConsumoConscienteCalculator`).
    - Deletar `main(root_dir)` legado de `e3_reconcile.py` — adiado até
      deprecation comprovada.

- **Fase 6 Sessão A2 — Caminho B ativo para E3 (2026-04-19):** E3 passa a ser
  o **primeiro stage em Caminho B completo**. `scripts/e3_reconcile.main(root_dir)`
  continua intacto (CLI direto e testes legados); o wrapper web delega ao
  novo entry point.
  - `pipeline/domain/services/e3_serialization.py` (145 linhas, novo módulo)
    — conversão `BankStatement` → schema E3 legado (`e3_reconciled.schema.json`).
    Funções puras, sem I/O: `serialize_to_e3_legacy_format(stmt, sources, dup)`
    → dict aderente ao schema; `generate_legacy_filename(stmt, canonicalizer)`
    → `{banco}_{tipo_conta}_{moeda}_{YYYYMM}_{YYYYMM}-3_reconciled.json`
    (para faturas: sem moeda); `generate_legacy_artifact_key(stmt,
    canonicalizer)` → key sem sufixo para `ArtifactStore`.
    Banco canonicalizado via `BankCanonicalizer` com fallback
    `lower().replace(" ", "")` (paridade com `generate_output_filename` legado).
  - `scripts/e3_reconcile.main_with_store(ctx)` (linha 1186, ~180 linhas)
    — entry point Caminho B. Lê configs via `ctx.load_config`, instancia
    todos os domain services com configs tipadas
    (`AccountGrouperConfig.from_pipeline_config`,
    `SaldoContinuityConfig.from_pipeline_config`, etc.), monta
    `E3ReconcilerAdapter` com `serialize_fn` e `output_key_fn` wireados ao
    `e3_serialization`, chama `reconcile_via_store`, valida schema de cada
    payload escrito (`validate_artifact`), gera sidecar logs
    (`reconciliation.md` + `qa_log.md` E3 section) em `ctx.logs_dir` e
    loga warnings estruturados via `log_progress`. Em mode Disk, faz
    `cleanup_e3_directory` antes de escrever (paridade legado).
  - `pipeline/stages/e3.py` **reescrito** (33 → 22 linhas) — importa
    `main_with_store` direto. **Zero uso** de `stage_runner_compat` ou
    `MaterializationBridge`. Docstring marca como "Caminho B (ADR-097,
    Sessão A2)".
  - `tests/test_e3_main_with_store_parity.py` (253 linhas, 3 testes) —
    rede de segurança: roda `main(root_dir)` legado e `main_with_store(ctx)`
    sobre o **mesmo** workspace sintético em `tmp_path` e compara payload a
    payload (tolerância `0.01` BRL em monetários; ordem-insensitive em
    `fontes`/`transacoes`). 2 cenários parametrizados: extrato simples
    sem dups, 2 extratos sobrepostos com dup cross-file. Terceiro teste
    é guard formal da Sessão A2 — asserta que `pipeline/stages/e3.py` não
    importa `stage_runner_compat` e **chama** `main_with_store`.
  - **Pendente (sessões seguintes):**
    - Fase 7 Caminho B (E4) — mesmo padrão, `E4ReconcilerAdapter`
      (`CategorizationService` já existe como foundation).
    - Decomposição completa de `e5_analyze.py` (Fase 8, 5-8 sem, timebox
      4sem/sprint).
    - Remoção de `_init_config()` global do `e3_reconcile.py` — só após
      todos os stages em Caminho B, para não quebrar coexistência com
      `main(root_dir)` legado.
    - Fase 9 (rename físico + remoção do bridge) — bloqueada até E4/E5
      em Caminho B.
  - **Tests** — +3 testes no pipeline (**757 total**) · backend inalterado ·
    boundary check verde · zero regressão.

- **Fase 6 Sessão A2 — `main_with_store` + switch do wrapper + golden de paridade (2026-04-19):**
  Fecha a Fase 6 do plano: E3 sai do bridge (`MaterializationBridge`) e passa
  ao Caminho B real. `scripts/e3_reconcile.main(root_dir)` legado
  **inalterado** — coexiste para CLI e testes existentes.
  - `pipeline/domain/services/e3_serialization.py` —
    `serialize_to_e3_legacy_format(stmt, sources, dup_count) → dict` aderente
    a `config/schemas/e3_reconciled.schema.json` (banco, tipo_conta,
    periodo_cobertura, fontes, transacoes_total,
    transacoes_duplicadas_removidas, etc.) e
    `generate_legacy_filename(stmt, *, canonicalizer)` /
    `generate_legacy_artifact_key(stmt, ...)` com paridade ao
    `generate_output_filename` legado (fatura sem moeda, conta com moeda).
    **18 testes**.
  - `pipeline/domain/models/document.py` — `BankStatement` ganha campo
    opcional `account_type: str | None`. `from_e2_dict` popula com `tipo`;
    `to_e2_dict` propaga (substitui hardcoded `"tipo": "extrato"`).
    `ReconciliationService._reconcile_group` propaga o campo.
  - `pipeline/domain/services/e3_reconciler_adapter.py` —
    `reconcile_via_store` agora aceita `output_key_fn` e `serialize_fn`
    opcionais (defaults preservam comportamento). `_load_with_outcome`
    deduplica keys por stage (DiskArtifactStore mapeia E2-extratos /
    E2-faturas / E2-llm para o mesmo dir → key apareceria 3x sem dedup) e
    popula `BankStatement.source_document` com filename legado
    (`key + stage_suffix(stage)`) — essencial para `fontes` no output E3.
  - `scripts/e3_reconcile.py` — nova função `main_with_store(ctx)` que
    constrói canonicalizer + grouper + 3 validators + adapter, roda o
    pipeline via `ArtifactStore`, valida cada payload contra o schema,
    e escreve sidecar `reconciliation.md` + `qa_log.md` (E3 Temporal Gaps)
    quando `ctx.logs_dir` existe. **Coexiste com `main(root_dir)` legado.**
  - `pipeline/stages/e3.py` — **não importa mais `stage_runner_compat`**.
    Chama `main_with_store(ctx)` direto. Test
    `test_pipeline_stages_e3_does_not_import_stage_runner_compat`
    enforça o critério.
  - `tests/test_e3_main_with_store_parity.py` — golden de paridade real:
    roda `main(root_dir)` legado e `main_with_store(ctx)` sobre **o mesmo**
    workspace sintético em `tmp_path`, compara payloads E3 campo-a-campo
    (tolerância 0.01 BRL para saldos; ordem-insensitive em fontes/transacoes).
    **2 cenários** parametrizados (extrato simples; extratos sobrepostos com
    duplicata cross-file) + 1 critério estrutural.
  - **Achados durante a paridade**:
    - `DiskArtifactStore` mapeia 3 stages E2 ao mesmo dir — adapter precisa
      dedup por key.
    - `account_type` precisa ser preservado em `_reconcile_group` (cria
      `BankStatement` novo) — esquecido inicialmente; pego pelo golden.
    - `source_document` precisa do sufixo do stage (`-2_extract.json`)
      para casar `fontes` do legado.
  - **Tests** — +21 testes pipeline (757 total) · backend 664 inalterado ·
    boundary check verde · zero regressão.
  - **Fora de escopo (Sessão A3+)**: remoção de `_init_config()` global e
    tolerâncias módulo-level de `e3_reconcile.py` (E4 ainda depende de
    padrão similar; vamos remover juntos no Caminho B do E4); deletar
    `main(root_dir)` legado (mantém-se até deprecation comprovada).

- **Fase 6 Sessão A1 — pre-extraction E3 + adapter completo + goldens (2026-04-19):**
  Continuação direta da Fase 6 foundation estendida. Zero mudança em
  `scripts/e3_reconcile.py` ou em `pipeline/stages/e3.py` — bridge continua
  ativo. Prepara o `main_with_store(config, store)` da Sessão A2.
  - `pipeline/domain/services/statement_preprocessor.py` —
    `StatementPeriodNormalizer` (4 casos: schema oficial `periodo_inicio/fim`,
    `periodo` dict, `periodo` string `YYYYMM`/`YYYY-MM-DD`, fatura sintetizada
    com chain `data_vencimento → tx_dates → fallback`) e
    `AnachronicTransactionDropper` (drop de tx >180d antes de
    `periodo.inicio`, paridade com guard de `e3_reconcile.py:772-795`).
    Warnings frozen (`PeriodDerivationWarning`,
    `AnachronicTransactionWarning`) — nunca strings. Aceita formato dict E
    formato plano `periodo_inicio`/`periodo_fim`. Não muta input.
    **27 testes**.
  - `pipeline/domain/services/account_grouper.py` — `AccountGrouper` com
    value object `AccountKey` (frozen) e `AccountGrouperConfig` injetável
    (R9/ISP). Substitui `get_account_key` + `should_skip_extract` +
    `ACCOUNT_TYPE_EQUIVALENCES` inline do legado. **25 testes**.
  - `pipeline/domain/services/e3_reconciler_adapter.py` extendido —
    integra `BankCanonicalizer` (output_key estável), `AccountGrouper`
    (skip de IRPF/posições), `StatementPeriodNormalizer`,
    `AnachronicTransactionDropper`, `SaldoContinuityValidator`,
    `TemporalGapDetector`, `BaselineValidator` (todos opcionais via DI).
    Novo `ReconciliationStoreResult` (frozen dataclass com acesso dict-like
    para retro-compat com testes legados). Novos
    `load_bank_statements_with_warnings()` e `load_baseline_accounts()`.
    **+15 testes** (23 total no arquivo).
  - `tests/pipeline/goldens/e3/` — 3 fixtures sintéticas autocontidas
    (`cenario_extratos.json`, `cenario_fatura_sem_periodo.json`,
    `cenario_baseline_diff.json`) + README. Testes de golden cobrem dedup
    cross-file, síntese de período em fatura, e diff baseline IRPF vs
    `closing_balance` em 31/12.
  - **Achado documentado** — o ajuste de `inicio` para `min(tx_dates)` em
    fatura sintetizada **anula** o anachronic guard (paridade com legado).
    O guard só dispara em extratos com período fixo. Documentado no golden
    de fatura e via teste explícito em `TestLoadBankStatementsWithWarnings`.
  - **Docs** — `docs/TESTING.md` com seção goldens E3.
  - **Tests** — +69 testes no pipeline (736 total) · backend inalterado ·
    boundary check verde · zero regressão.
  - **Fora de escopo desta iteração** (Sessão A2): `main_with_store`,
    refactor de `pipeline/stages/e3.py` para parar de usar bridge, golden
    de paridade real contra `main()` legado, remoção de `_init_config()`
    global do `e3_reconcile.py`.

- **Fase 6 foundation estendida (2026-04-19):** 4 domain services extraídos
  de `scripts/e3_reconcile.py` (1193 linhas) sem tocar `main()` legado — zero
  risco de regressão; prepara o terreno para o refactor real de E3 (Caminho B)
  num sprint subsequente.
  - `pipeline/domain/models/bank.py` — `BankCanonicalizer.from_institutions()`
    + `canonicalize_bank()` + `_normalize()` (strip acento/espaço/`/&`).
    Substitui o dict-global `_BANCO_DISPLAY_TO_CANONICAL` em
    `scripts/e3_reconcile.py::_init_config`. Elimina falsos positivos de
    substring (fix 4.4) via índice explícito `normalized_form → canonical_code`.
    **21 testes**.
  - `pipeline/domain/services/reconciliation_validators.py` —
    `SaldoContinuityValidator` (substitui primeira metade de
    `validate_saldo_and_gaps`, usa `Money`/`Decimal`) e
    `TemporalGapDetector` (substitui segunda metade). Cada um com
    `*Config` dataclass (ISP/R9), ambos recebem `list[BankStatement]`
    (nunca `Path`/`dict`), ordenam internamente, retornam warnings
    estruturados (`SaldoGapWarning`, `TemporalGapWarning`) — não strings.
    **32 testes**.
  - `pipeline/domain/services/baseline_validator.py` — `BaselineValidator`
    substitui `validate_against_baseline()`. Compara `closing_balance` de
    `BankStatement` contra saldos IRPF 31/12 via `BankCanonicalizer`.
    Inclui value object `BaselineAccountSaldo` + factory
    `from_baseline_dict` (aceita `members`/`membros`, dict ou list,
    aliases de field names). Retorna `list[BaselineDiffWarning]` com
    `percent_diff: Decimal`. **39 testes**.
  - **Fora de escopo desta iteração** (intencional): fatura period
    adjustment, `reconcile_account`, `main_with_store(config, store)`,
    golden fixture E3 via workspace real, refactor de `pipeline/stages/e3.py`.
    `e3_reconcile.py` continua rodando via Caminho A (bridge) — zero mudança
    em produção.
  - **Tests** — +92 testes no pipeline (667 total) · backend inalterado ·
    boundary check verde · zero regressão.

- **Fase 6 foundation — Sessão A1 (2026-04-19):** segunda onda de extração de
  domain services a partir de `scripts/e3_reconcile.py`. A foundation agora
  cobre o caminho end-to-end que o `E3ReconcilerAdapter` precisa para orquestrar
  a reconciliação inteira; o `main_with_store(config, store)` e o switch de
  `pipeline/stages/e3.py` para Caminho B ficam para a Sessão A2.
  - `pipeline/domain/services/account_grouper.py` (~200 linhas) —
    `AccountGrouper` + `AccountGrouperConfig` (R9/ISP) + value object
    `AccountKey` (frozen, `is_fatura`/`to_tuple`). Substitui `get_account_key`
    (`e3_reconcile.py:245`) e `should_skip_extract` (`e3_reconcile.py:219`).
    `from_pipeline_config(family, pipeline)` lê `account_type_equivalences` +
    `skip_types`; faturas têm `currency=None` (paridade com legado); defaults
    `_DEFAULT_SKIP_TYPES` e `_DEFAULT_FATURA_ALLOWED` alinhados ao `_init_config`
    do script.
  - `pipeline/domain/services/statement_preprocessor.py` (~440 linhas) —
    duas responsabilidades extraídas de `load_and_group_e2_extracts`
    (`e3_reconcile.py:655-795`):
    - `StatementPeriodNormalizer` — garante `data["periodo"]` como dict
      `{inicio, fim}`. Expande `YYYYMM`/`YYYY-MM-DD`; sintetiza período para
      faturas sem `periodo` via chain `data_vencimento → tx dates`; ajusta
      `inicio` para min de `transacoes[].data` quando anterior ao sintetizado.
      Retorna `NormalizationResult(data, skip, warnings)` com
      `PeriodDerivationWarning` estruturados + `PeriodDerivationReason`
      (enum-like string constants).
    - `AnachronicTransactionDropper` — descarta transações com `data > N dias`
      antes de `periodo.inicio` (guard #4 do legado, default 180 via
      `AnachronicGuardConfig`). Retorna `AnachronicFilterResult(data, warning?)`.
  - `pipeline/domain/services/e3_reconciler_adapter.py` **reescrito**
    (142 → 365 linhas) — agora orquestra, em sequência: normalize period →
    drop anachronic → group (skip + `AccountKey`) →
    `BankStatement.from_e2_dict` → `ReconciliationService.reconcile` →
    `SaldoContinuityValidator` / `TemporalGapDetector` /
    `BaselineValidator` → write via `store`. Saída tipada em
    `ReconciliationStoreResult` (frozen dataclass: `statements_loaded`,
    `statements_reconciled`, `artifacts_written`, `skipped_inputs`, mais
    5 tuplas de warnings estruturados; `to_dict()` + `__getitem__` para
    retro-compat dos testes). Lógica residual (geração de
    `reconciliation.md` summary, `qa_log.md` rewriting, exit codes,
    `cleanup_e3_directory`) **continua** no script legado via bridge até
    a Sessão A2.
  - **Testes novos** — `tests/unit/pipeline/test_account_grouper.py` +
    `tests/unit/pipeline/test_statement_preprocessor.py` (~680 linhas
    combinadas, +52 testes).
  - **Pendente (Sessão A2 ou subsequente):**
    `scripts/e3_reconcile.main_with_store(config, store)`; refactor de
    `pipeline/stages/e3.py` para chamar direto (eliminar
    `run_legacy_with_bridge_if_db`); golden fixture E3; extração de
    `reconciliation.md` summary + `qa_log.md` rewriting para domain output
    layer; remoção de `_init_config()` global.
  - **Tests** — +52 testes no pipeline (**719 total**) · backend inalterado ·
    boundary check verde · zero regressão.

- **Pipeline paths (2026-04-17):** `MATHOMS_WORKSPACE_ROOT` obrigatória para `scripts.pipeline_common` (sem default para `data/` na raiz do git). `python -m pipeline.run_dev --root …` e a task Celery definem a variável; API/worker/pytest usam `setdefault` para a raiz do repo em dev. Docs: [SETUP.md §8](SETUP.md#8-pipeline-cli-sem-web), `scripts/__init__.py`.

- **Docs — estrutura de pastas (2026-04-17):** [CLAUDE.md](../CLAUDE.md), [dev/README.md](../dev/README.md), [ARCHITECTURE.md](ARCHITECTURE.md) §11 e [SETUP.md](SETUP.md) §8: árvore canónica sob `storage/<workspace_id>/`; pastas de dados na raiz do clone são opcionais (CLI com workspace = repo).

- **Dev — reset completo (2026-04-17):** CLI `python -m backend.app.scripts.reset_platform` (`--dry-run`, `--apply` com duas confirmações, `--skip-redis`). Docs: [SETUP.md](SETUP.md#reset-completo-da-plataforma-cli), [RUNBOOK.md](RUNBOOK.md#51-reset-intencional-dev--staging).

- **F11.6a (2026-04-17):** Premissas por tipo de meta (IF, aporte, dólar, alocação) em `GoalPremissasCard` — wizards e páginas de edição `/plano/*`; vigência (`effective_from`) + texto de rascunho quando há versão salva; campo `meta_version` nas respostas JSON dos goals (`_GoalResponseBase`). Helpers em `frontend/src/lib/goalPremissas.ts`; teste Vitest `tests/lib/goalPremissas.test.ts`; assert `meta_version` em `test_goals_api.py`.

- **F11.3a + F11.3b + F11.6b (2026-04-17):** Print: `report-print.css` — uma regra `@page`, `orphans`/`widows`, sem footer CSS com `counter(page)`; rota `/reports/[id]?print=1` define `html[data-print-route]`; `ReportShell` expõe `data-report-ready` no `<article>`; `pdf_renderer.render_pdf` aguarda estado terminal (`data-report-ready`, `data-report-pdf-legacy` ou `data-report-pdf-error`) antes do PDF. F11.6b: teste `test_snapshot_includes_active_goals_without_goals_file` em `test_premissas_snapshot.py`. `BACKLOG` F11.3a/b atualizado.

- **F11.6b + 7D.1/7D.2 (2026-04-17):** Migração `l7f8g9h0i1j2` — `reports.premissas_snapshot_json`; serviço `premissas_snapshot.py` (hash `config/goals.json` + lista de metas ativas); pipeline grava no relatório; API expõe snapshot na listagem/detalhe e injeta em `goals.premissas_snapshot` em `GET /reports/{id}/data`. Testes de gap-fill: `tests/test_e0_route_edges.py`, `test_e7_edges.py`, `test_e5_e6_e5n_edges.py`, extensões em `test_e3_dedup` / `test_e4_categorize`; `backend/tests/test_premissas_snapshot.py` + asserts em `test_reports`. `BACKLOG` atualizado.

- **Dev — strip de metadados PDF (2026-04-17):** `dev/strip_pdf_metadata.py` (pikepdf; não redige corpo). README em `tests/fixtures/e2_real_pdf_anon/` com fluxo **C6 primeiro** (extrato global USD/EUR típico em `data/financial_statements/`).

- **E2 PDF real anonimizado — scaffold (2026-04-17):** `tests/fixtures/e2_real_pdf_anon/` (README + `.gitkeep`) e `tests/test_e2_real_pdf_regression.py` — regressão opcional com `route_to_parser`; pasta vazia mantém CI verde. Docs: `PIPELINE_ARTIFACTS`, `BACKLOG`, `P1_STRUCTURAL_PLAN`, `SMOKE_TEST`.

- **Docs — fixtures LLM em disco (2026-04-17):** [tests/fixtures/llm_golden/README.md](../tests/fixtures/llm_golden/README.md) — inventário dos JSONs (E1, E1.5, E2-LLM, E7-review), ligação a `tests/test_llm_golden.py`, `backend/tests/fixtures/llm_mock.py` e ADR-070. Atualizações em `PIPELINE_ARTIFACTS`, `CANONICAL_ENGINE_P0` §4, `ROADMAP`, `TESTING`, `BACKLOG`.

- **P2.5 + F11 (2026-04-17):** Log estruturado `fin.classification_telemetry` em `classification_telemetry.py` (upload, reclassify; sem PII). API de relatório: `source_document_count` / `source_document_ids` + `_report_lineage` no JSON de `GET /reports/{id}/data` (`report_lineage.py`). UI: `ReportSourceStrip` com contagem; `ReportPremissasBlock` + `reportFormulas.ts` + `docs/FORMULAS.md` (F11.6/F11.7); hierarquia KPI (`KPICard` emphasis); nav agrupada + `docs/COPY_GUIDELINES.md` (F11.1); `CommandPalette` cmdk + atalhos `?` (F11.8); smoke print/PDF em `SMOKE_TEST.md` §5.1; `login`/`register` com `Suspense` para `useSearchParams`. MSW: `/me/workspaces`, `/workspaces/:id/dashboard`, `/notifications`. Testes: `test_reports` linhagem; `tests/setup` mock global `useWorkspace`.

- **Docs — E2 PDF em duas fases (2026-04-17):** (1) prioridade em concluir **só sintético** alinhado ao parser por banco-alvo; (2) **depois**, opcionalmente, **PDFs reais anonimizados** no repositório como complemento de regressão de layout (processo e critérios em `PIPELINE_ARTIFACTS.md`, linha no `BACKLOG.md`, `CANONICAL_ENGINE_P0` §4, `ROADMAP` motor canônico, `P1_STRUCTURAL_PLAN`, FAQ em `TESTING.md`).

- **P2.1–P2.4 — Unificação da classificação de documentos (2026-04-17):** Módulo `backend/app/services/document_classification.py` (contrato Pydantic + `classify_document`); E0-route, upload (`document_processor`), reclassify API e script passam a usar o mesmo código; testes `test_document_classification.py` e `test_classification_parity.py`; ADR-081; `ARCHITECTURE.md` §9. UI Documentos: banner e avisos por linha para classificação incerta (`needs_review` ou confiança < 0,7) com CTA para `EditDocumentDialog`.

- **Sprint A — Ops leve (7E.6 / 7E.9 / 7E.8, 2026-04-17):** `docs/RUNBOOK.md` (status page, resposta a incidentes, checklist de drill); `docs/SLO.md` (alvos de uptime/latência/pipeline + SLA de comunicação de incidente); `docs/runbooks/incidents/*.pt-BR.md` (templates initial / update / resolved com exemplos); link **Status e incidentes** no rodapé quando `NEXT_PUBLIC_MATHOMS_STATUS_PAGE_URL` está definido (`StatusPageFooter` em login, cadastro, convite, AppShell); `frontend/src/lib/statusPageUrl.ts` + testes; `.env.example` documentando a variável. BACKLOG: 7E.6, 7E.8, 7E.9 marcados concluídos (provisão da ferramenta de uptime continua no deploy).

- **Sprint C — Linhagem do relatório + hierarquia numérica (F11.4a + F11.2a, 2026-04-17):** `ReportResponse.pipeline_run_id` no backend (`schemas/report.py`, `_serialize_report`); `ReportSourceStrip` com link para a execução (`/pipeline?run=<uuid>`); página Pipeline: âncoras `id="pipeline-run-…"` em cartões ativos / falha / `needs_review` / histórico + `useEffect` que rola até o run e remove o query param; MSW: `GET /api/workspaces/:workspaceId/reports` e `/:id` + fixture com `pipeline_run_id`. Transactions: `tabular-nums` em data, cabeçalho Valor e linha de paginação. Relatório: período no hero com `tabular-nums`. Testes: `test_get_report_includes_pipeline_run_id`, `ReportShell` (link da execução).

- **Sprint B — Confiança na UI (F11.5 / F11.4 / fatia F11.2, 2026-04-17):** `frontend/src/lib/pipelineTransparency.ts` (`reviewPauseImpactHint`, `stageLlmFootnote`); página Pipeline: banner `needs_review` e notas por etapa LLM; remoção de códigos E* na linha de etapa; `pipelineE2TouchLabel` em `format.ts` sem “E2” na face do usuário. Relatório: `ReportSourceStrip` + `reportPeriod` / `reportCreatedAt` em `ReportShell` e `[id]/page`. Dashboard: eixos e tooltips de gráficos com `tabular-nums` / `font-mono`. Testes: `pipelineTransparency.test.ts`, ajustes em `format.test`, `ReportShell.test`; `tests/pages/pipeline.test.tsx` com mock de `WorkspaceProvider` + handlers MSW em `/api/workspaces/:workspaceId/...` (alinhado ao client). BACKLOG: F11.5a–c e F11.4b–c concluídos; F11.4a (API por seção) e F11.2a (auditoria completa) em progresso.

- **P1 motor canônico (2026-04-17):** `python -m pipeline.run_dev` (`pipeline/run_dev.py`) — mesmo orquestrador do worker sobre `--root` tenant; `dev/check_pipeline_boundaries.py` (sem imports fastapi/celery/sqlalchemy em `pipeline/`); CI com `MATHOMS_PIPELINE_SCHEMA_MODE=strict` + boundaries; fixtures `tests/fixtures/pipeline_golden/` (E2/E4) + testes jsonschema; docs `CANONICAL_ENGINE_P0`, `P1_STRUCTURAL_PLAN`, `PIPELINE_ARTIFACTS`, atualizações em ARCHITECTURE/ROADMAP/BACKLOG/TESTING.
- **Validação pós-write (2026-04-17):** `validate_artifact` após gravar JSON em E2 (`e2_extract.py`, `e2_llm.py`, exceto fallback LLM stub), E4 (`save_json` → `e4_unified.schema.json`), E5 (`e5_analysis.schema.json`). Testes `test_e3_dedup` / `test_pipeline_common` alinhados ao retorno `(list, int, details)` de `deduplicate_transactions` e ao logging via `caplog` em `safe_float`.
- **E3 schema (2026-04-17):** `config/schemas/e3_reconciled.schema.json` + `validate_artifact` em `e3_reconcile.py` após cada `*-3_reconciled.json`; fixture `tests/fixtures/pipeline_golden/e3/minimal-conta-3_reconciled.json`; testes `test_valid_e3_reconciled` e golden parametrizado.
- **E3 golden execução (2026-04-17):** `tests/test_e3_golden_execution.py` — tenant mínimo, E2 `minimal-extrato` + saldos, `e3_reconcile.main`, assert no JSON + schema.
- **E4 golden execução (2026-04-17):** `tests/test_e4_golden_execution.py` — tenant mínimo + fixture E3 `minimal-conta`, `e4_categorize.main`, asserts em receitas/fluxo + `validate_artifact` em todos os `*-4_unified.json`.
- **E5 golden execução (2026-04-17):** `tests/test_e5_golden_execution.py` — após E4, `e5_analyze.main` com `goals.json` mínimo + configs numéricas copiadas do repo → `analise_financeira-5_analysis.json` + `e5_analysis.schema.json`.
- **Goldens E4/E5 fluxo misto (2026-04-17):** fixture `tests/fixtures/pipeline_golden/e3/minimal-conta-com-despesa-3_reconciled.json`; testes `test_e4_execution_mixed_receita_despesa`, `test_e5_execution_mixed_receita_despesa`.
- **Golden baseline E1.5 (2026-04-17):** `tests/fixtures/pipeline_golden/e2/minimal-baseline-1.5_consolidated.json` + `test_e4_execution_with_baseline_patrimonial` / `test_e5_execution_with_baseline_patrimonial` (patrimônio bruto/líquido; dívidas via `dividas[]` + `saldo_31_12`).
- **Golden E6 (2026-04-17):** `tests/test_e6_golden_execution.py` — E4→E5→`render_report`; `e6_render`: cria `output/` antes do write do HTML.
- **QA log nos goldens (2026-04-17):** `tests/pipeline_golden_asserts.py` — `assert_qa_log_md` usado nos testes de execução E4, E5 e E6.
- **E5.N golden execução (2026-04-17):** `tests/test_e5n_golden_execution.py` — após E5, `e5n_narrativas.main` injeta `narrativas`; `validate_narrativas` corre dentro do `try` (antes do `finally` que repõe globals do script — chart `*_cenarios` depende do tenant). Docs: `PIPELINE_ARTIFACTS.md`, `P1_STRUCTURAL_PLAN`, `CANONICAL_ENGINE_P0` §4, `BACKLOG`, `ROADMAP`, `TESTING`.
- **E5.N golden cônjuge (2026-04-17):** `test_e5n_execution_narrativas_with_conjuge_chart` — `family_members` com `papel: conjuge` (`ana`) → assert `ana_cenarios` em `narrativas.charts`; helper `_build_e5_workspace` partilhado entre cenários.
- **E2 PDF sintético × registry (2026-04-17):** `tests/test_e2_synthetic_pdf_parsers.py` — 11 bancos `BANK_MODULES`, filename canônico → `route_to_parser` → dict; **`caixa`** adicionado a `tests/fixtures/pdf_generator.py`; smoke backend `TestSyntheticPDFsAreParseable` passa a 14 bancos. Docs: `CANONICAL_ENGINE_P0` §4, `PIPELINE_ARTIFACTS`, `ROADMAP`, `BACKLOG`, `P1_STRUCTURAL_PLAN`, `TESTING`.
- **E2 PDF BTG layout (2026-04-17):** `pdf_generator` — extrato `btgpactual` com bloco *Movimentação Conta Corrente* (DD/MM/AAAA, Saldos Ini/Fim) alinhado a `parse_btg`; `test_btgpactual_synthetic_extracts_transactions` (≥1 transação, `saldo_final`).
- **E2 PDF Rico + Wise layouts (2026-04-17):** `pdf_generator` — `_draw_rico_extrato` (evita cabeçalho com duas datas seguidas que gerava falso positivo no `parse_rico`) e `_draw_wise_extrato` (período BRL + linhas de movimento com data); `test_rico_synthetic_extracts_transactions`, `test_wise_synthetic_extracts_transactions`.
- **E2 PDF PicPay layout (2026-04-17):** `pdf_generator` — `_draw_picpay_extrato` (tabela ReportLab + `MOVIMENTAÇÕES 1 DE … A …` + `Conta:` alinhados a `parse_picpay`); `test_picpay_synthetic_extracts_transactions`.
- **E2 PDF Bank of America layout (2026-04-17):** `pdf_generator` — `_draw_bankofamerica_extrato` (`Account number`, `for Month … to …`, `Beginning/Ending balance`, linhas `MM/DD/YY` + valor USD alinhados a `parse_bankofamerica`); `test_bankofamerica_synthetic_extracts_transactions`.
- **E2 PDF Santander layout (2026-04-17):** `pdf_generator` — `_draw_santander_extrato` (`Agência e Conta`, `Período`, linhas `DD/MM/AAAA` + 6 dígitos + valor + saldo, ordem mais recente primeiro como `parse_santander_conta`); `test_santander_synthetic_extracts_transactions`.
- **E2 PDF Itaú layout (2026-04-17):** `pdf_generator` — `_draw_itau_extrato` (tabela ReportLab 4 colunas + `Período`/`Conta` na página 1 + linha `SALDO DO DIA` para `parse_itau`); `test_itau_synthetic_extracts_transactions`.
- **E2 PDF Caixa layout (2026-04-17):** `pdf_generator` — `_draw_caixa_extrato` (`Conta`/`Período dos lançamentos`/`SALDO ANTERIOR` + tabela 7 colunas C/D + linha `SALDO DIA` para `parse_caixa`); `test_caixa_synthetic_extracts_transactions`.
- **E2 PDF Quinto Andar layout (2026-04-17):** `pdf_generator` — `_draw_quintoandar_fatura` (`Faturas de aluguel`, `Total de`/`Receber até`, linhas item + `R$` alinhadas a `parse_quintoandar`); `test_quintoandar_synthetic_extracts_items` (≥1 item, `total_recebido`).
- **E2 PDF C6 + Bradesco layouts (2026-04-17):** `pdf_generator` — `_draw_c6_extrato` (tabela 5 colunas + `Saldo do dia` / `Período •` para `parse_c6bank`) e `_draw_bradesco_extrato` (`Ag | Conta`, `Entre`, `SALDO ANTERIOR`, lançamentos DD/MM/YY, `Total` para `parse_bradesco`); `test_c6bank_synthetic_extracts_transactions`, `test_bradesco_synthetic_extracts_transactions` (Bradesco: `_BRADESCO_TX` com crédito compatível com heurística do parser). Docs: `PIPELINE_ARTIFACTS`, `ROADMAP`, `BACKLOG`, `CANONICAL_ENGINE_P0` §4, `P1_STRUCTURAL_PLAN`, `TESTING`, `tests/fixtures/pipeline_golden/README.md`. Fase 1 só sintética para `BANK_MODULES` fechada; próximo: fixtures LLM (CANONICAL_ENGINE_P0 §4 item 3) ou PDF real anonimizado.

- **F7 / 7A.5:** `.env.example` na raiz (todas as `MATHOMS_*` documentadas + opcionais comentadas); `scripts/gen-secrets.sh` para gerar `MATHOMS_FERNET_KEY` / `MATHOMS_SECRET_KEY` (modo imprimir ou `--init-env` a partir do example); `docs/SETUP.md` e README atualizados.

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

- **Fix alembic cwd-sensitivity:** `%(here)s/../mathoms.db` absoluto + guard em `env.py` rejeita SQLite relativo + `DATABASE_URL` default absoluto via `_PROJECT_ROOT`
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
- **LLM mock fixtures** (`backend/tests/fixtures/llm_mock.py`): outputs Pydantic válidos por stage (E1, E1.5, E2-llm, E7-review) — `MATHOMS_LLM_MOCK=1` default em CI
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
- `pyproject.toml` com package `mathoms-pipeline` v0.2.0
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
