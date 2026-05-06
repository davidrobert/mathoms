# Mathoms AI — Changelog

> Log cronológico reverso do que foi entregue. Atualizar por sprint/milestone.

---

## [Unreleased]

- **refactor(pipeline): A8.4 PR2 — eligibility gate + analyzer reduzido a 1 cenário (ADR-167) (2026-05-06):**
  `CenariosConjugeAnalyzer` reduzido de 3 cenários família-específicos ("Sem Trabalhar", "Com NCLEX", "Com NCLEX + Green Card") para **1 cenário universal** "Sem renda do cônjuge". `_LABELS = ("Sem renda do cônjuge",)`. Removidos do `CenariosConjugeConfig`: defaults USD/cambio (`renda_rn_minima_usd`, `renda_rn_maxima_usd`, `cambio_usd_brl`, `surplus_share_pct`, `surplus_cap_pct`); helpers `_resumo_s2`/`_resumo_s3`; premissas `renda_nclex_*`, `renda_gc_*`, `recovery_*_pct`. `from_configs(taxas=..., cambio_usd_brl=...)` simplificado para `from_configs(goals=..., titular_dob=..., ...)` — pipeline interno sem dependência de USD pós PR2.
  Nova função pura `should_render_conjuge_scenarios(*, family_members, fluxo, goals) -> bool` no mesmo domain service (ADR-167) decide elegibilidade: meta IF presente E ≥2 membros com renda recorrente E renda do cônjuge ≥15% da renda familiar total. Pipeline E5 omite o bloco quando `False`; frontend só checa presença. **5 casos canônicos cobertos por unit tests** (solteiro, casal sem meta IF, casal 95/5, casal 70/30 elegível, casal sem renda do cônjuge).
  `pipeline/domain/services/e5_analyzer_adapter.py:365` atualizado: `CenariosConjugeConfig.from_configs` invocado sem `taxas`/`cambio_usd_brl`. Tests dependentes ajustados: `tests/unit/pipeline/test_a72b_typed_inputs.py::TestCenariosConjugeWithTypedCambio` removida (4 tests da feature A7.2b — `cambio_usd_brl` no analyzer — não existe mais); `tests/unit/pipeline/test_cenarios_conjuge_analyzer.py` reescrito (260 → 240 LOC, 16 tests cobrindo 1 cenário + gate). Pipeline 1750/1750 verde (+16 vs PR1).
  ADR-167 movida para Status `Decidido (A8.4 PR2)`.

- **refactor(pipeline,backend,frontend): A8.4 PR1 — schema estável `cenarios_conjuge` no payload E5 (ADR-166) (2026-05-06):**
  Chave do bloco "Cenários do cônjuge" no JSON E5 passa de `cenarios_{_CONJUGE_KEY}` (workspace-dependent — gerava `cenarios_mariana` no piloto, `cenarios_ana` em hipotético) para literal universal `cenarios_conjuge`. **5 sites do producer atualizados** atomicamente: `pipeline/domain/services/e5_serialization.py` (campo `cenarios_conjuge_key` removido do dataclass; chave literal no dict), `scripts/e5_analyze.py:147,3105` (global `_KEY_CENARIOS_CONJUGE` + kwarg removidos), `scripts/e5n_narrativas.py:68,121,363` (mesma limpeza), `pipeline/domain/services/narrativas/context.py:59` (`key_cenarios_conjuge="cenarios_conjuge"` literal pós ADR-166). Consumers atualizados: `pipeline/stages/review_finances.py:59` (`_E5_SUBKEYS`), `backend/app/services/section_summary_orchestrator.py:239,245` (S7/T5).
  Frontend mantém **fallback dual-key transitório** (`data.cenarios_conjuge ?? data.cenarios_mariana`) em 3 components (ApendicesSections, S3InvestimentosSection, UsaSections) + types em `frontend/src/lib/api/reports.ts` durante PR1→PR3; `cenarios_mariana` marcado `@deprecated`. Fixtures: `frontend/tests/components/report/{apendices,usaSections}.test.tsx`, `frontend/tests/e2e/fixtures/reports/medium.json:117` migradas para chave nova.
  Tests Python: `tests/unit/pipeline/test_e5_serialization.py:258-265` invertido — `test_cenarios_conjuge_usa_key_configuravel` → `test_cenarios_conjuge_usa_chave_universal_estavel` (documenta que campo configurável foi removido; regressão-bloqueada por dataclass shape). Pipeline 1734/1734 + backend 1593/1593 verdes.
  Logging `INFO` em `mathoms.pipeline.e5_serialization` (`extra={"key": "cenarios_conjuge", "has_data": ...}`) para confirmar migração via Loki/Cloudwatch.
  **Sem mudanças em DB/schema:** `pipeline_artifacts.content_json` é JSON cru sem index; OpenAPI snapshot inalterado (`/reports/{id}/data` retorna `{type: object}`); LLM cache (ADR-144) invalida sozinho via hash de payload. **Backfill operacional:** novo script `dev/backfill_e5_universal_keys.py` (idempotente) re-roda `analyze_finances` em workspaces com chave legada após o merge do PR1, antes do PR3 remover o fallback. ADR-166 + ADR-167 (eligibility gate, status Proposto para PR2) registradas em `docs/DECISIONS.md`. Glossary `docs/ARCHITECTURE.md §4.1` atualizada.

- **docs(plan): A8.4 Cenários de Estresse — plano canônico + lane no BACKLOG (2026-05-06):**
  [docs/CENARIOS_ESTRESSE_PLAN.md](CENARIOS_ESTRESSE_PLAN.md) entregue como SOT da iniciativa
  "remover prototipagem família-específica + APP_C universal". 4 especialistas consultados em
  paralelo (financial-planner, product-designer, senior-cto, data-engineer); decisões D1-D5
  fixadas; 6 PRs sequenciais escopados (PR0 docs · PR1 schema rename `cenarios_mariana` →
  `cenarios_conjuge` em 5 sites · PR2 gate de elegibilidade `should_render_conjuge_scenarios`
  + analyzer reduzido a 1 cenário · PR3 frontend lê chave nova + APP_C "Cenários de Estresse"
  com hide-when-empty + numeração estável A/B/C/D/E + visualização comparativa lado-a-lado
  base vs estresse · PR4 delete Modo USA U1-U4 inteiro · PR5 limpeza). 3 ADRs alvo: ADR-165
  (remoção Modo USA, supersede parcial ADR-117/123, conclui agenda ADR-151), ADR-166
  (schema estável `cenarios_conjuge` no payload E5, ancora ADR-143 + ADR-076), ADR-167
  (eligibility gate no domain service, ancora ADR-143). Lane A8.4 aberta no
  [BACKLOG.md](BACKLOG.md#sprint-a8--continuação-multi-tenant-aberta-após-a7-fechar-2026-04-27).

- **feat(db): B7 M3 — DROP _legacy_kanban_items + _legacy_report_notes + model cleanup (ADR-154) (2026-05-05):**
  Migration final após 7 dias de validação pós-M2 (2026-04-29). `_legacy_kanban_items` e
  `_legacy_report_notes` DROPadas. Cleanup de todos os artefatos dependentes:
  - `b7c8d9e0f1a2_adr154_m3_drop_legacy_collab_tables.py`: DROP `_legacy_kanban_items` + `_legacy_report_notes`
  - `backend/app/models/report_collab.py`: modelos `KanbanItem`/`ReportNotes` removidos
  - `backend/app/schemas/report_collab.py`: schemas `ReportNotesRead/Write`, `KanbanItem*` removidos
  - `backend/app/services/internal_ops/purge_reports.py`: import + `_delete_report_collab()` removidos
  - `backend/tests/internal_ops/test_purge_reports.py`: helper `_add_report_collab` + asserts collab removidos
  - `backend/tests/test_kanban_to_task_backfill.py`: teste de paridade M1 removido (tabelas não existem mais)
  - `backend/tests/test_alembic_guardrails.py`: `IRREVERSIBLE_MIGRATIONS` + lógica de floor parcial para suportar DROP sem downgrade
  - `frontend/src/lib/api/reports.ts`: 6 funções deprecated (`getReportNotes`, `putReportNotes`, `listKanbanItems`, `createKanbanItem`, `updateKanbanItem`, `deleteKanbanItem`) + tipos (`ReportNotesPayload`, `KanbanItem*`) removidos
  - `docs/DB_SCHEMA_REFERENCE.md` regenerado — tabelas `_legacy_*` ausentes

- **feat(api,security): LGPD self-service + tenancy isolation gate (Bloco 0.6 P2/P3 · 2026-05-04):**
  Endpoints `POST /api/v1/me/data-export`, `GET /me/data-export/{id}`,
  `GET /me/data-export/{id}/download` (one-shot, TTL 7d), `POST
  /me/delete-request` (soft-delete + grace 30d, bumps `token_version`),
  `DELETE /me/delete-request` (cancel). Worker Celery
  `fin.lgpd.process_data_export` empacota NDJSON tar.gz com manifest
  (`backend/app/services/lgpd_export_service.py`) — exclui
  `users.hashed_password` e `password_vaults.encrypted_password`. Cron
  beat `fin.lgpd.expire_data_exports` (6h) e
  `fin.lgpd.process_user_deletions` (24h, grace 30d). 8 ações novas em
  `AuditAction` (`lgpd.export_*`, `lgpd.deletion_*`); hard-delete usa
  email-hash truncado para registro auditável anonimizado (LGPD §V).
  Migration `c3d4e5f6a7b8_lgpd_self_service` adiciona
  `data_export_requests` + `users.deletion_requested_at`. Cobertura: 9
  testes em `backend/tests/test_lgpd_self_service.py` (happy path,
  cooldown, audit trail, TTL/expire, soft-then-hard delete, cancel,
  token inválido, cross-tenant 404). LGPD Art. 18, V e VI atendidos
  por self-service — antes só via console interno
  (`MATHOMS_INTERNAL_OPS_UI_ENABLED`), bloqueador P0 para abrir signup
  público. Doc nova em [SECURITY.md §Direitos do titular
  LGPD](../SECURITY.md). **Tenancy gate estrutural** em
  [backend/tests/integration/test_tenancy_isolation.py](../backend/tests/integration/test_tenancy_isolation.py):
  3 testes complementam o suite per-domain — fuzz de todas as rotas
  `/api/v1/workspaces/{workspace_id}/...` GET (User A nunca obtém 200
  no ws de B), AST scan que exige `Depends(get_current_workspace)` em
  toda função com `workspace_id` (whitelist 6 sunset endpoints
  ADR-129/154), e fuzz path-id em `/documents/{id}/extract-json`. Doc
  em [docs/TESTING.md §Tenancy isolation](TESTING.md). Snapshot
  OpenAPI + DB schema reference regenerados.

- **feat(ui): Onda 9 — design system polish + mobile (2026-05-05):**
  Unificação de 3 primitivos de design system + 2 fixes de produto + ergonomia mobile.
  Entregue em 1 PR (#51):
  - **SectionHeading:** novo primitivo unificando 4 patterns de H2 em `/plano`
  - **EmptyState:** novo primitivo com layouts card/inline/hero unificando 5 patterns
  - **SegmentedTabs:** novo primitivo com variantes pill/segment unificando 3 patterns de filter-tab
  - **Badge Inbox pending:** AppShell mostra contagem de sugestões pendentes em `/acao`
  - **Kill Timeline tab:** tab placeholder removida de `/acao`; TimelineTab.tsx deletado
  - **Mobile collapsibles:** seção 'Plano de Ação' em `/plano` colapsada por default;
    spec Playwright iPhone 13 (390x844px) valida estado inicial colapsado

- **feat(db): F9.3 — Alembic stage rename migration validada (ADR-093) (2026-05-05):**
  `q5r6s7t8u9v0_rename_stage_identifiers.py` sincronizado com `STAGE_RENAME_MAP`:
  add `"E1.6" → "extract_irpf_full"` (ADR-157); remove `"E6"` e `"E6-final"`
  (ADR-129 — renderer descontinuado). Pre-check `_check_unknown_stages` aborta
  com `RuntimeError` se banco tiver stages desconhecidos; skip automático em
  modo offline (SQL generation). 5 testes em `backend/tests/test_stage_rename_migration.py`
  exercitam upgrade/downgrade/idempotência via Alembic programático + SQLite.
  Runbook em `docs/runbooks/f9_3_alembic_upgrade.md`. F9.4 destravada.

- **feat(report): Lane A8.3 — TRS efetiva + carteira de renda em S7 (2026-05-05):**
  Independência Financeira agora confronta **TRS meta** (5%/4% — D15) com
  **TRS efetiva** (yield real do patrimônio investido) — antes só projeção.
  Entregue em 3 PRs:
  - **PR-A (#43):** `PassiveIncomeCalculator` + `RatiosCalculator` consume
    (TRS efetiva + alíquota efetiva). Service puro com 15+ unit tests.
  - **PR-B (#42):** Aluguéis re-classificados de trabalho → capital no
    `IRPFAnalyzer` (Perini/AUVP). Helper `IRPFAnalyzer.declarations_for_year()`
    público. Impacto colateral em S8 e chart `irpf_renda` documentado.
  - **PR-C (este):** Wire IRPF + `PassiveIncomeCalculator` no `E5AnalyzerAdapter`;
    populate goals (taxa_retirada_efetiva_pct + 6 KPIs derivados); regra
    `rule_trs_desalinhada` ganha filtro de fase (`if_pct >= 50` — evita
    ruído em acumulação). UI do S7 ganha 4 KPIs (Renda passiva R$/mês ·
    Patrimônio investido · TRS efetiva · Em acumuladores), `InfoTooltip`
    WCAG-compliant ao lado do label, caption permanente em acumulação,
    `AcumuladoresBanner` (>40%) e `DefasagemWarningBanner` (≥15m), 2 empty
    states (`sem_irpf` com CTA · `gerador_zero`). Helper `trsTone` condiciona
    o tom à fase do plano (acumulação sempre neutro · independência
    confronta meta diretamente).

  Fechado: regra dormente `rule_trs_desalinhada` finalmente dispara;
  pergunta canônica do Perini ("minha carteira sustenta retirada hoje?")
  agora responde com dado real. Mitigação obrigatória do erro #1 do
  iniciante (vender growth para perseguir DY) está incorporada na
  hierarquia visual + copy + tom condicionado.

  ADR canônica: [ADR-164](DECISIONS.md#adr-164--carteira-de-renda-e-taxa-de-retirada-efetiva).
  `config/methodology.md` ganha §TRS efetiva + §Re-classificação aluguel.
  18 cenários (3 fases × 2 acumuladores × 3 defasagens) cobertos via Vitest;
  5 unit tests novos no adapter; 1 test de regra silenciosa em acumulação +
  4 fixtures atualizadas com `if_pct: 60` no `test_suggestion_generator`.

- **feat(pipeline): N3 — IFProjector v2 Monte Carlo + IFConeChart (2026-05-05):**
  Simulação estocástica de Independência Financeira com 3 percentis.
  Entregue em 2 PRs:
  - **PR-A (#52):** `IFProjector` v2 com `run_monte_carlo_if()`: 1 000
    trajetórias, distribuição normal em retorno (`mean±std`), `IFMonteCarloConfig`
    (tipado, valor object), `MonteCarloIFResult` com `p10`/`p50`/`p90` cone
    paths + `years_to_if` por percentil.
  - **PR-B+C (#55):** Chart.js `IFConeChart` em S7 com 3 bandas coloridas
    P10/P50/P90 + linha "Meta IF"; E5 exporta `monte_carlo_if` key no
    output JSON para consumo frontend. CI re-running, auto-merge habilitado.
  Nota: ADR formal para Monte Carlo (candidato ADR-165) pendente de sign-off
  G0 (financial-planner) — regras de domínio precisam de revisão antes de
  formalizar hipóteses de retorno.

- **refactor(backend): decompose content_classifier monolith (2026-05-05):**
  Módulo `content_classifier.py` com 727 LOC decomposto em 3 módulos
  focados sem alteração de comportamento: `institution_classifier` (lógica
  de regex + banco), `type_classifier` (mapeamento doc_type), `period_extractor`
  (parsing de período). PR [#50](https://github.com/davidrobert/mathoms/pull/50),
  CI verde, auto-merge. Desbloqueia manutenção independente dos 3 domínios
  de classificação.

- **fix(backend): canonical stage names em artifact_reader (2026-05-05):**
  `dashboard_service.py` usava `"E5"` (legado) em vez de `"analyze_finances"`;
  `transaction_service.py` usava `"E4"` em vez de `"categorize_transactions"`.
  Corrigido para nomes descritivos (ADR-093). B2 (renomear dispatcher stub
  test) absorvido no mesmo PR [#47](https://github.com/davidrobert/mathoms/pull/47).
  CI rodando, auto-merge habilitado.

- **refactor(pipeline): deprecate calculators.py (2026-05-05):**
  PR [#46](https://github.com/davidrobert/mathoms/pull/46). Exports legados
  de `calculators.py` redirecionados para serviços canônicos em
  `pipeline/domain/services/`. Sem quebra de import externo — módulo continua
  importável com deprecation warning. CI verde, auto-merge.

- **test(e2e): fix stale selectors em vault e config-round-trip (2026-05-05):**
  PR [#48](https://github.com/davidrobert/mathoms/pull/48). Seletores obsoletos
  nas specs Playwright `vault.spec.ts` e `config-round-trip.spec.ts` atualizados
  para DOM atual. Suíte E2E `@critical` volta a passar sem flaky.

- **feat(frontend): FreeTierSkippedBanner no pipeline monitor (2026-05-05):**
  PR [#49](https://github.com/davidrobert/mathoms/pull/49). Alert amber
  dismissível aparece no monitor de pipeline quando stages premium são
  detectados como pulados (status `skipped` no free tier). Usa `EmptyState`
  primitivo entregue na Onda 9.

- **feat(db): M3 drop _legacy_kanban_items + _legacy_report_notes (ADR-154) (2026-05-05):**
  PR [#56](https://github.com/davidrobert/mathoms/pull/56). Migration Alembic M3
  remove tabelas legadas `_legacy_kanban_items` e `_legacy_report_notes`
  (bridge criado pela ADR-154 em sprint anterior, agora confirmado sem
  leitores). Modelos SQLAlchemy e rotas API correspondentes limpos.
  CI verde, auto-merge.

- **feat(suggestions+decisions): Onda 8 — coerência metodológica (2026-05-04):**
  Fecha 6 gaps identificados na revisão de produto 2026-04-29:
  - **#1 (ADR-161):** 6 regras canônicas v2 no `SuggestionGenerator`
    (Cerbasi/AUVP/Perini completos): `endividamento_perigoso` (danger),
    `taxa_poupanca_caindo` (warning · comportamental), `seguros_insuficientes`
    (danger · proteção), `concentracao_instituicao` (warning · AUVP),
    `lifestyle_creep` (warning · comportamental), `renda_passiva_real_baixa`
    (info · Perini "300"). `SUGGESTION_CAP` sobe 6→8. Campo `category`
    auto-derivado (alvo_if/carteira/protecao/comportamental/endividamento/
    usa_plano). Refactor: rules → `suggestion_rules.py`, config →
    `suggestion_config.py`. Onda 10 #5 enrichments preservados (rationale
    com gap+ETA em reserva e atual/alvo/tabela em alocação). Migration
    aditiva `d9e0f1a2b3c4`. 43 testes verdes (39 v2 + 4 Onda 10).
  - **#2 (ADR-162):** Decisions atualizam Goals via event projection.
    Campos novos: `target_field`, `target_value`, `target_value_type`.
    Tabela `PROJECTIONS` em `backend/app/services/decision_goal_projection.py`
    mapeia 6 paths (goal.if.*, goal.aporte.*, goal.dolar.*).
    `mark_decision_executed` dispara `project_decision_to_goal` na mesma
    transação; falha → ValidationError + rollback. Goal nova carrega
    `notes="Derivada da Decision <code>"` e DecisionEvent `GoalProjected`
    com `goal_id`. 6 testes novos.
  - **#3:** DecisionCard ganha botão "Gerar tarefas" (status Decidido|Executado);
    `GenerateTasksDialog` pré-popula 1-3 templates por `target_field` (goal.if
    → "Atualizar planilha de IF" + "Reler relatório com novo TRS"; etc.).
    Cada Task criada carrega `derived_from_decision_id` (FK→decisions,
    migration `g3b4c5d6e7f8`). UI: lista editável antes de salvar.
  - **#4:** SuggestionCard aplica `border-l-4` colorida por severidade
    (antes definida em `SEVERITY_CONFIG.cls` mas nunca chegava ao Card).
    InboxTab ordena por `suggestionSortComparator` (severity desc →
    created_at desc). 3 testes novos.
  - **#5:** `/suggestions/summary` novo endpoint (count + max_severity +
    by_category). `useSuggestionsSummary` substitui `useSuggestionsCount`
    em /plano. SuggestionsBanner colore por max_severity (danger=vermelho,
    warning=amarelo, info=azul) — antes escalava por volume, mostrando
    banner azul calmo para 1 sugestão `danger`. Bug semântico fechado.
  - **#6 (ADR-163):** Decision congela `context_snapshot` (JSON nullable)
    ao aceitar Suggestion: 5 campos (`patrimonio_brl`, `if_progress_pct`,
    `trs_pct_when_decided`, `report_id`, `report_period`) lidos do
    relatório-fonte via `report_id`. DecisionCard exibe "Decidida com
    base em: ..." quando snapshot presente. Migration única
    `e0f1a2b3c4d5` para campos #2 + #6.

  Total: 3 ADRs novas (161/162/163), 3 migrations. 1586 backend tests +
  1661 pipeline tests + 739+ frontend tests verdes. OpenAPI snapshot
  atualizado.

- **feat(ui): Onda 10 — coerência cross-rota /plano · /reports · /acao
  (2026-05-04):** 6 fixes UI fecham os gaps de navegação entre as 3 telas
  críticas do ritual mensal do casal usuário identificados na revisão
  multi-agente (`product-designer` 2026-05-04).
  1. `<MonetaryValue/>` ganha prop `size={"hero"|"kpi"|"body"}` que aplica
     `text-style-hero` / `text-style-kpi-value` do design-tokens.
     `<IFHeroCard/>` Patrimônio migra para `size="hero"` — chega à mesma
     fonte do `<HeroKpiGrid/>` em /reports. Demais `formatCurrency()` em
     JSX dentro de `(app)/plano/_components/**` substituídos por
     `<MonetaryValue/>` (zero ofensores no grep gate).
  2. CTA primário "Abrir relatório de {mês}" via `<ReportLinkAction/>`
     nas actions do `<PageHeader/>` de /plano. Workspace sem Report → CTA
     outline "Gerar relatório" → /documents. Cada KPI da `<PlanoKpiRow/>`
     vira `<Link>` para a seção do relatório que aprofunda o número
     (Patrimônio → §S1, IF → §S7, Aporte → §S2).
  3. `<SuggestionReportLink/>` adiciona backward link "Ver no relatório
     do mês · §{section_id}" no card da Inbox em /acao — fecha o ciclo
     forward (Onda 7 #3) ↔ backward. Dialogs (Accept/Modify/Dismiss)
     extraídos para `SuggestionDialogs.tsx` para manter `SuggestionCard.tsx`
     ≤500 linhas.
  4. `<SuggestionCallout/>` migra de Tailwind utilities (`border-l-sky-500`,
     `bg-amber-50`, `text-red-900`) para tokens semânticos
     `var(--semantic-info-financial | --semantic-alert | --semantic-loss)`
     com `color-mix(in oklab, ...)`. Dark mode resolve automaticamente
     pelo `tokens.css`.
  5. `suggestion_generator.py` enriquece `rationale` das regras 2
     (reserva insuficiente) e 3 (alocação fora do alvo): gap em BRL +
     ETA com aporte mensal projetado (regra 2); atual/alvo/Δ + tabela
     markdown de classes + sugestão de próximo aporte (regra 3). Helper
     `_format_brl()` formata Decimal em padrão BR sem locale do sistema.
     Defensivo — degrada para versão curta se snapshot incompleto.
     Cobertura: 4 testes novos em `tests/test_suggestion_generator.py`
     (24 total, todos verdes).
  6. /acao em workspace zero (pending+tasks+notes = 0) cai em
     `<EmptyState/>` apontando para /plano (entrada canônica do
     `<OnboardingHero/>`). Hook novo `useAcaoZeroSignals(workspaceId)`
     compõe os 3 sinais.
  Track: [docs/agent_prompts/track_onda_10_cross_route_coherence.md](agent_prompts/track_onda_10_cross_route_coherence.md).

- **test(pipeline): IRPF full schema goldens — A8.2 sub-lane (2026-04-30):**
  3 fixtures sintéticas (`tests/fixtures/llm_golden/e16_irpf_full_{completo,simplificado,edge_cases}.json`)
  para regressão byte-byte do stage E1.6 (`extract_irpf_full`, ADR-157).
  Cobertura de edge cases: rendimento exterior multi-moeda (USD+EUR),
  dependente sem CPF + dependente filho universitário 23 anos,
  dívida sem amortização (`valor_inicial == valor_final`), modelo
  simplificado sem PGBL (RFB), reconcile `ir_pago` ≈ Σ retidos PJ/PF
  com tolerância 0,02 BRL. **Origem 100% sintética** — zero PII real,
  CPFs sempre `***.***.***-XX`, nomes "Test User", valores realistas
  mas fictícios. Sign-off G0 (financial-planner) com paridade RFB 2024
  tabela progressiva (`ir_devido = base × 0,275 − 10.740,98` na faixa
  27,5%); G2 (data-engineer) com cobertura adicional do enum fallback
  `99_outro` em rendimentos isentos e do sandtrap `simplificado + PGBL`
  (warning) via mutate-in-test. 30 testes novos: 22 em `TestE16Goldens`
  ([tests/test_llm_golden.py](../tests/test_llm_golden.py)) cobrindo
  schema parse + validator zero-error + anti-PII re-scan + reconcile
  + KPIs explícitos do `IRPFAnalyzer` (renda 371.800,00, tributável
  310.300,00, ir_pago 48.080,00, alíquotas 15.49% / 12.93%, PGBL
  capacidade 7.236, split trabalho 320k / capital 46,8k); 8 em
  `tests/test_extract_irpf_full_stage.py` cobrindo skips, paridade
  semântica de persistência via roundtrip Pydantic, preservação de
  confidence baixa, strip de sufixo `-0_original`, e cap de
  confidence em 0.7 quando reconcile diverge. `FakeStructuredLLMClient`
  novo em [tests/fakes/llm.py](../tests/fakes/llm.py) — stand-in
  reutilizável para `LLMService.call` em qualquer stage de extração.
  Bump de prompt LLM agora é detectado por `prompt_version` pinned
  nas fixtures.
  [ADR-157](DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full)

- **feat(report): seções IRPF no relatório premium — UI lane (2026-04-30):**
  materializa os 6 KPIs do `IRPFAnalyzer` (já em produção via E5 try-read)
  em duas seções novas do shell nativo: **S_IRPF_RENDA** (renda anual e
  impostos — cards de renda bruta/líquida, IR pago + alíquota dual, split
  trabalho×capital + chart de evolução multi-anos via Chart.js + dual gauge
  RFB/Cerbasi) e **S_IRPF_OTIMIZACAO** (capacidade PGBL não usada,
  dependentes declarados, dedutíveis subutilizados — placeholders para
  follow-up em copy editorial). Inseridas no `config/report_layout.yaml`
  entre S8 e S9, com codegen sincronizado para `frontend/src/generated/
  report-layout.ts` + `backend/app/generated/report_layout.py`. Tipo
  `IrpfKpis` em `frontend/src/types/irpf.ts` com narrow guard
  `isIrpfKpis` (TS strict — `unknown` → tipado), hook `useIrpfKpis`
  (memoiza leitura de `output.irpf_kpis` do snapshot E5). **Degrada
  gracioso**: workspaces sem declaração IRPF têm as duas seções inteiras
  omitidas (componentes retornam `null`, sem placeholder vazio). Tokens
  de cor (`var(--brand-*)`, `var(--semantic-*)`) — nenhum hex literal,
  alinhado com ADR-076. Side effect saudável: `MigratedSection` extraída
  de `ReportShell.tsx` (de 500→403 linhas) para um módulo próprio,
  destrancando o limite T2 do baseline. 16 testes Vitest novos (narrow
  guard + null-render das seções) — 712 testes frontend e 1536 backend
  todos passando. Acompanha fix de paridade `pipelineStageNames.ts`
  (E1.6 → `extract_irpf_full`). Lane pendente de G0/G4 sign-off em PR
  comment + visual baselines + Playwright `@critical` (follow-ups).
  [ADR-157](DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full)
  · [ADR-076](DECISIONS.md#adr-076--design-tokens-unificados-site--relatório)

- **feat(pipeline): IRPF full schema (E1.6 / `extract_irpf_full`) — Sprint A8 (2026-04-30):**
  novo stage paralelo a `extract_baseline` que captura **todo** o conteúdo
  financeiro de declarações IRPF (rendimentos PJ/PF/exterior, isentos,
  exclusiva, pagamentos dedutíveis, dependentes, dívidas, imposto
  apurado, bens & direitos). Hoje o E1.5 só extrai Bens & Direitos
  (~30% do PDF); este commit destrava 6 KPIs novos: renda anual líquida,
  alíquota efetiva dupla (RFB-style + Cerbasi-style), capacidade PGBL
  não usada, split trabalho×capital (Perini), evolução de renda
  multi-anos. Schema `IRPFFullOutput` (Pydantic) + JSON Schema
  espelhado, prompt LLM dedicado, validator com anti-PII em campos
  livres + reconcile cross-field obrigatória, stage runner com cap
  de confidence em 0.7 quando reconcile falha + WARNING em
  `mathoms.pipeline.e16` para campos top-level desconhecidos,
  `IRPFAnalyzer` com queries puras. E5 consome via try-read opcional
  (workspaces sem IRPF não regridem). Coexiste com E1.5 — cutover de
  Bens & Direitos (E1.5 → E1.6) é deliberadamente fora desta lane,
  flag `MATHOMS_E16_SUPERSEDES_E15_BENS` definida para sprint futura.
  G0 (financial-planner) + G2 (data-engineer) + G1 (senior-cto) sign-off
  na ADR-157. 22 testes unitários cobrem schema/validator/analyzer.
  Frontend (componentes do relatório premium) fica em lane separada com
  G4 (product-designer) review.
  [ADR-157](DECISIONS.md#adr-157--schema-irpf-completo-stage-extract_irpf_full)

- **fix(suggestions): auto-trigger no post-processing do pipeline (2026-04-29):**
  rodar o pipeline completo deixava `/acao` Inbox e `SuggestionCallout`
  do relatório vazios — Onda 5 entregou gerador, endpoint
  `POST /reports/{id}/regenerate-suggestions` e UI consumidora, mas
  **nenhum lugar disparava** o endpoint. Adicionado
  `_persist_aggregate_suggestions(ws_id, run_id)` em
  `backend/app/tasks/pipeline_task.py` (sync, espelha o use case async
  pelo motivo já documentado em `_persist_llm_suggestions`:
  `asyncio.run()` em gevent crasha) chamado dentro de
  `_run_post_processing` após `_create_report_from_output`. Idempotente
  via `dedup_key` (ADR-153 §2). [ADR-153](DECISIONS.md#adr-153--suggestion-aggregate-direção-e--onda-5-proposal-imutável--state-machine-simples)
  recebeu nota datada clarificando que "trigger via endpoint dedicado,
  NÃO hook do pipeline" referia-se ao boundary `pipeline/**` →
  `backend.*` (que segue valendo); disparar de `pipeline_task.py`
  (backend→backend) não viola o boundary. Endpoint REST permanece para
  re-execução manual (debug, smoke test, regerar após mudança nas
  regras). 4 testes novos em `TestPersistAggregateSuggestions`
  (caminho feliz · idempotência · sem artefato · snapshot saudável).

- **Direção E · Onda 7 — bloqueadores P0 fechados (2026-04-29):** os 5
  fixes da [track_onda_7_p0_blockers.md](agent_prompts/track_onda_7_p0_blockers.md)
  entregues em main, ritual mensal volta a funcionar ponta-a-ponta:

  1. **`/plano` reordenado** — Estratégia → Plano de Ação → Mês
     corrente. "Mês corrente" agora é `<details>` colapsado por default
     (alertas + KPIs operacionais + ChartsGrid abrem com 1 clique).
     Reduz ~12 blocos visíveis para ~6-8 na leitura típica casal.
  2. **`/acao` default = Inbox quando há sugestões pendentes** + lê
     `?tab=inbox|tarefas|timeline|notas` da URL (deep-link do
     relatório). Wrappado em `<Suspense>` (padrão das demais rotas
     `useSearchParams`). TODO esquecido em `acao/page.tsx:10-12`
     fechado.
  3. **Anchor scroll `#SUG-XXX` corrigido** — `SuggestionCard` agora
     emite `id="SUG-${suggestion.id}"` (mantendo
     `data-suggestion-id` para testes). Página `/acao` faz polling
     2s pelo elemento (Inbox carrega assíncrono) e dispara
     `scrollIntoView` quando aparece. Highlight via `:target` Tailwind.
     Link em `SuggestionCallout` (relatório) atualizado para
     `/acao?tab=inbox#SUG-${id}`.
  4. **Patrimônio single-source ([ADR-156](DECISIONS.md#adr-156--patrimônio-em-plano-é-single-source-via-patrimonio_snapshot-direção-e--onda-7))** —
     `usePlanoOverview` expõe `patrimonio_snapshot: { value, asOf,
     sourceReportId } | null`. `PlanoKpiRow` e `IFHeroCard` consomem o
     **mesmo** valor; `IFProgress.patrimonio` removido como campo
     duplicado. Test de paridade em
     `tests/components/PatrimonioSingleSource.test.tsx` bloqueia
     regressão de "dois números diferentes na mesma tela".
  5. **`<OnboardingHero/>` para workspace zero** — quando
     `!ifGoal && decisions == 0 && tasks == 0`, `/plano` substitui
     todo o conteúdo por hero ensinante de 3 next-steps (Configurar
     IF · Importar relatório · Criar primeira decisão; passos com
     badge progressivo + CTA terciário desabilitado até IF vigente).
     Mata a "parede de blocos vazios" da primeira impressão. Hook
     auxiliar `useWorkspaceZeroSignals` lê `listDecisions` +
     `listTasks` em paralelo.

  Toques em produção: `frontend/src/app/(app)/plano/page.tsx`,
  `frontend/src/app/(app)/acao/page.tsx`,
  `frontend/src/app/(app)/plano/_components/{usePlanoOverview,PlanoKpiRow,IFHeroCard,OnboardingHero,useWorkspaceZeroSignals}.{ts,tsx}`,
  `frontend/src/app/(app)/acao/_components/SuggestionCard.tsx`,
  `frontend/src/components/report/sections/SuggestionCallout.tsx`,
  `frontend/tests/components/PatrimonioSingleSource.test.tsx`. Vitest
  691 passing (+2 novos), code-style baseline mantido (T3 ofensores
  novos contidos via extração para `useTabSelection` /
  `runZeroLoadEffect` / `AcaoLoaded`). Onda 7 ✅; Ondas 8 e 9 abertas.

- **Direção E pós-revisão de produto — Ondas 7/8/9 abertas (2026-04-29):**

  Revisão completa das interfaces consolidadas (Plano + Ação +
  Relatório) executada com `product-designer` + `financial-planner` +
  análise de PM. Identificou **5 bloqueadores P0** que impedem o
  ritual mensal funcionar ponta-a-ponta, **6 lacunas metodológicas**
  (Cerbasi não coberto), **5 inconsistências de design system**.

  **3 ondas dedicadas** com prompts self-contained em `docs/agent_prompts/`:

  - [track_onda_7_p0_blockers.md](agent_prompts/track_onda_7_p0_blockers.md)
    (~3d, **P0** — recomendado primeiro): reordenar `/plano`
    (Estratégia → Plano de Ação → Mês corrente collapsible); `/acao`
    default = Inbox quando há pendentes + ler `?tab=`; fix anchor
    `#SUG-XXX` do relatório → Inbox; single-source `patrimonio_snapshot`;
    `<OnboardingHero/>` para workspace zero.
  - [track_onda_8_methodology_coherence.md](agent_prompts/track_onda_8_methodology_coherence.md)
    (~5-7d, P1, depende parcial de Onda 7 #4): 6 novas regras Suggestion
    (Cerbasi: endividamento, taxa poupança caindo, seguros, concentração
    instituição, lifestyle creep, renda passiva Perini); Decisions
    atualizam Goals via event projection; `context_snapshot` ao aceitar
    Suggestion; Decision → Task automática com templates `derived_from`;
    SuggestionCard borda colorida + sort por severidade; SuggestionsBanner
    com `maxSeverity` real.
  - [track_onda_9_design_system_polish.md](agent_prompts/track_onda_9_design_system_polish.md)
    (~3d, P2, independente): `<SectionHeading/>` primitivo (4 H2 → 1);
    `<EmptyState/>` primitivo (5 → 1); `<SegmentedTabs/>` primitivo
    (3 → 1); dedup tarefas Upcoming/Linked + filter param em `/acao`;
    badge sugestões pendentes no AppShell; **kill Timeline tab**
    (placeholder ensinante sem fonte virou ruído); mobile collapsibles
    + tap targets + Playwright iPhone 13.

  **Decisões de produto travadas (incorporadas nos prompts):** (i)
  `/plano` usa **collapsibles** (não tabs); (ii) Inbox continua tab em
  `/acao` (não vira rota top-level), visibilidade via badge no AppShell;
  (iii) Tasks aceitam ad-hoc e derivadas, com `derived_from`; (iv)
  Timeline tab removida; (v) Seguros em v1 só como regra de Suggestion
  (módulo é pós-GA).

  ADRs futuras já reservadas: ADR-156 (Patrimônio single-source · Onda 7),
  ADR-157 (Suggestion regras v2 · Onda 8), ADR-158 (Decisions → Goals
  projection · Onda 8), ADR-159 (Decision context_snapshot · Onda 8),
  ADR-160 (design system primitivos v2 · Onda 9).

  Entrada do banner em `BACKLOG.md` atualizada com tabela das 3 ondas
  + critérios de pickup.

- **Direção E — `/dashboard` absorvido por `/plano` (consolidação, 2026-04-29):**

  Cumpre a agenda da Direção E original que declarou "/dashboard será
  absorvido pelo /plano em onda futura"
  ([ADR-155](DECISIONS.md#adr-155--dashboard-absorvido-por-plano-direção-e-consolidação)).
  Mathoms agora tem **2 superfícies vivas**: `/plano` (home única —
  estratégia + operacional do mês + plano de ação) e `/acao`
  (superfície dinâmica de execução). Modelo mental do usuário: "Plano
  é onde você lê; Ação é onde você faz".

  **Frontend:**
  - 8 componentes movidos via `git mv` de
    `frontend/src/app/(app)/dashboard/_components/` para
    `frontend/src/app/(app)/plano/_components/_dashboard/`
    (AlertCard, BarChartCard, ChartSkeleton, ChartsGrid,
    HeaderActions, KpiRow, PieChartCard, dashboardHelpers).
  - `frontend/src/app/(app)/plano/page.tsx` reescrito em 3 seções
    verticais separadas por `<SectionDivider/>`: (1) topo
    estratégico (PlanoKpiRow + SuggestionsBanner + Hero IF +
    SupportGoalsRow); (2) "Mês corrente" (alertas + KpiRow
    operacional + ChartsGrid); (3) "Plano de Ação" (DecisionsSection
    + UpcomingTasksWidget + LinkedTasksSection).
  - Hook local `useDashboardData` em `plano/page.tsx` consume
    `getDashboard` (endpoint `/v1/dashboard` permanece intacto).
  - `frontend/src/app/(app)/dashboard/page.tsx` vira **redirect 308**
    via `redirect()` Server Component.
  - `frontend/src/components/AppShell.tsx`: entry "Dashboard" removida
    do grupo "Fechamento do período"; `LayoutDashboard` import
    retirado.
  - `frontend/src/components/command-palette/CommandMenuDialog.tsx`:
    entry "Dashboard" removida; tipo do icon trocado para `Target`.
  - `frontend/src/types/report-analysis.ts`: comentários atualizados
    para refletir `/plano` como destino.
  - `frontend/tests/pages/dashboard.test.tsx`: **deletado** (testava
    página que não existe mais; componentes movidos sem cobertura
    específica — gap futuro vira `plano.test.tsx`).

  **Backend:** sem mudanças (endpoint `/v1/dashboard` permanece
  intacto, agora consumido pelo `/plano`).

- **Direção E — Onda 1 M2 (sunset legacy `report_collab`, 2026-04-29):**

  M2 da Onda 1 entregue como **estratégia conservadora** — RENAME +
  endpoints 410 Gone em vez do DROP direto previsto no
  [ADR-154](DECISIONS.md#adr-154--fusão-kanbanitem-em-task--migração-reportnotes-para-workspacenotes-direção-e--onda-1).
  Razão: M1 e M2 no mesmo dia (2026-04-29); janela de 7 dias de
  validação não cumprida; rename é reversível em segundos via
  downgrade, drop é irreversível sem backup. Drop final fica para PR
  M3 (sprint+2, ~2026-05-13).

  **Backend:**
  - Migration `a0b1c2d3e4f5_adr154_m2_sunset_legacy.py`:
    `op.rename_table("kanban_items", "_legacy_kanban_items")` +
    `op.rename_table("report_notes", "_legacy_report_notes")`.
    Downgrade reverte.
  - `backend/app/api/reports_collab.py` reescrito: 6 rotas (notes
    GET/PUT + kanban GET/POST/PATCH/DELETE) retornam **HTTP 410 Gone**
    com payload `{code, message, migrated_to}` apontando para
    `/workspaces/{ws}/notes` e `/workspaces/{ws}/tasks`.
  - `backend/app/models/report_collab.py`: `__tablename__` atualizado
    para `_legacy_*`; docstring marca como deprecated. Models
    permanecem porque `purge_reports.py` ainda usa em DELETE.
  - `backend/tests/test_reports_collab_api.py` reescrito: 6 testes
    novos validam 410 Gone + payload com código + ADR-154 reference.

  **Frontend:**
  - `frontend/src/lib/api/reports.ts`: 6 funções legadas
    (`getReportNotes`, `putReportNotes`, `listKanbanItems`,
    `createKanbanItem`, `updateKanbanItem`, `deleteKanbanItem`)
    marcadas com `@deprecated` JSDoc apontando para os hooks novos.
    Tipos preservados.

  **Documentação:**
  - [ADR-154](DECISIONS.md#adr-154--fusão-kanbanitem-em-task--migração-reportnotes-para-workspacenotes-direção-e--onda-1)
    ganha banner "M2 sunset entregue" + reescreve seção "Migration
    M1 → M2 → M3" (3 fases agora).
  - `docs/RUNBOOK.md` atualizado: localStorage `notas:*` e `kanban:*`
    chaves agora marcadas como "endpoints retornam 410 Gone desde
    ADR-154 M2".

- **Direção E — Onda 1: `KanbanItem` → `Task` + `ReportNotes` → `WorkspaceNotes` (M1, 2026-04-29):**

  Onda 1 da Direção E entregue como migration **M1 additive**
  ([ADR-154](DECISIONS.md#adr-154--fusão-kanbanitem-em-task--migração-reportnotes-para-workspacenotes-direção-e--onda-1)).
  Funde o aggregate `KanbanItem` (ADR-123) no aggregate `Task`
  (ADR-074) e migra `ReportNotes` (ADR-123) para um aggregate novo
  `WorkspaceNotes` (workspace-scoped, multi-row, com pin). Substitui
  o placeholder ensinante de Notas em `/acao` (Onda 6) por UI real.

  **Backend:**
  - Migration Alembic `e9f0a1b2c3d4`: ALTER `tasks` ADD `board_column`,
    `board_order`, `urgency`, `origin_report_id` (FK→reports SET NULL),
    `is_board_only`. CREATE TABLE `workspace_notes`. Índice
    `ix_tasks_ws_board_column`. `created_from` ganha `'kanban_migration'`.
    Zero-downtime; offline SQL preview validado pelo
    `test_alembic_guardrails`.
  - Aggregate `WorkspaceNotes` completo (model, repository, 4 use
    cases, DTOs, mapper) seguindo padrão Decision (ADR-136).
  - 4 endpoints REST `/v1/workspaces/{ws}/notes` (GET list, POST,
    PATCH, DELETE 204) registrados em `main.py` e refletidos no
    OpenAPI snapshot.
  - Backfill idempotente em `dev/migrate_kanban_to_task.py`: cada
    `KanbanItem` vira `Task` com `created_from='kanban_migration'`,
    `is_board_only=true`, `source_suggestion_id=kanban_item.id`;
    `report_notes` do workspace concatenam em **uma** `WorkspaceNotes`
    com `title="Notas migradas do relatório"`, `pinned=true`. Re-run
    skipa via `source_suggestion_id` / título.
  - Tests: 8 endpoint integration + 6 backfill paridade
    (`test_workspace_notes_api.py`, `test_kanban_to_task_backfill.py`),
    todos verdes.

  **Frontend:**
  - `frontend/src/lib/api/workspace-notes.ts` (cliente HTTP) +
    `frontend/src/hooks/useWorkspaceNotes.ts` (CRUD + reload).
  - `<NotasTab/>` real em `/acao` (Onda 6 placeholder substituído):
    lista pinned-first, edição inline com autosave 500ms (flush
    onBlur), botão "Nova nota", toggle pin, delete inline.
  - Tests vitest: 6 hook + 3 component (todos verdes).

  **Decisões de UX/schema travadas:**
  - `board_column` é coluna **física nullable** (não computada de
    `status`) — só preenchida em itens de origem Kanban; board view
    futuro filtra `WHERE board_column IS NOT NULL`.
  - `priority` (S/R/O metodológico) e `urgency` (alta/media/baixa
    tático) são **eixos ortogonais** — UI default mostra priority;
    urgency é opt-in (herdado do Kanban migrado).
  - `workspace_notes` é **multi-row** com `title` opcional + `pinned`;
    cobre tanto "anotação livre única" quanto "agenda do casal"
    (múltiplas notas tituladas).
  - **Board view em `/acao` Tarefas: deferred** (não-v1). M1 entrega
    fundação; itens migrados aparecem em listas normais (filtrados
    por `is_board_only` em widgets como `UpcomingTasksWidget`).

  **M2 (sprint+1, em PR separado):** drop tabelas legadas
  `kanban_items` + `report_notes`, endpoints `/kanban` e
  `/report_notes` retornam 410 Gone. Roda só após validação manual
  em workspace Allen + 7 dias sem regressão.

- **Direção E — Onda 5: aggregate `Suggestion` full-stack
  ([ADR-153](DECISIONS.md#adr-153--suggestion-aggregate-direção-e--onda-5-proposal-imutável--state-machine-simples),
  2026-04-29):** Peça central da Direção E — completa o ritual
  *relatório → sugere → usuário aceita/modifica/descarta em `/acao`
  → vira Decision*.

  **Backend:** modelo `Suggestion` (proposal imutável + state machine
  simples Pendente/Aceita/Modificada/Descartada), migration Alembic,
  repositório, 8 use cases (list, count, get, accept, modify, dismiss,
  regenerate-for-report) + protocols, router REST com 7 endpoints.
  Aceitar cria `Decision` via use case canônico (ADR-136), com evento
  extra `derivation` para rastreabilidade. OpenAPI snapshot atualizado.

  **Pipeline:** `pipeline/domain/services/suggestion_generator.py` —
  gerador determinístico puro com 5 regras canônicas (TRS desalinhada,
  reserva insuficiente, alocação fora do alvo, aporte abaixo da meta,
  dolarização atrasada). Cap=6, ranking severity → amount, dedup_key
  com buckets que toleram ruído pequeno. `SuggestionDraft` em
  `pipeline/domain/types/suggestion.py` preserva boundary do pipeline
  (não importa backend). Trigger via endpoint dedicado, NÃO hook do
  pipeline (idempotência + boundary respeitado).

  **Frontend:** cliente `lib/api/suggestions.ts`, hook `useSuggestions`,
  `useSuggestionsCount` real (substitui stub Onda 4). `SuggestionCard`
  em `acao/_components/` com Aceitar/Modificar/Descartar via dialogs
  locais; `InboxTab` agora lista cards filtráveis. `SuggestionCallout`
  inline em S2/S7 + agregador "Próximos passos" no fim do relatório.
  Severidade tripla (info/warning/danger) com faixa lateral 3px +
  ícone Lucide + copy de leigo escondendo vocabulário event-sourced.

  **Testes:** 40 backend (10 use case + 10 API + 20 unit gen) + 11
  frontend (6 hook + 5 helper); suítes completas verdes (688 vitest +
  24 alembic guardrails).

- **Direção E — Onda 4 + Onda 6: `/plano` executive + `/acao` consolidada (2026-04-29):**

  **Onda 4 entregue (`/plano` executive summary):** novos componentes
  em `frontend/src/app/(app)/plano/_components/`: `PlanoKpiRow` (3
  KPIs no topo: patrimônio · IF % · aporte alvo), `SuggestionsBanner`
  (visível só se há sugestões pendentes; severidade info/warning),
  `useSuggestionsCount` (stub determinístico até Onda 5). Refactor
  interno em `usePlanoOverview` expõe `patrimonio` independente de
  `IFProgress` e elimina chamada duplicada a `listReports`.

  **Onda 6 entregue (rota `/acao` com tabs,
  [ADR-152](DECISIONS.md#adr-152--plano-de-acao-renomeada-para-acao-com-tabs-direção-e--onda-6)):**
  `/plano-de-acao` → `/acao` com 4 tabs (Inbox · Tarefas · Timeline ·
  Notas) e `ActionStatusBar` no topo agregando contadores (sugestões
  pendentes · tarefas próximos 7 dias · decisões a executar).
  Conteúdo de Tarefas migrado de `/plano-de-acao/page.tsx` (332 LOC
  monolítico) para `TasksTab.tsx` decomposto em sub-componentes
  (TasksHeader, ViewToggle, TasksGroups, helpers de groupBy). Inbox,
  Timeline, Notas ficam como **placeholders ensinantes** até Ondas 5
  e 1 ligarem o backend (Suggestion aggregate e workspace_notes).
  `/plano-de-acao` (e `/sugestoes`) viram redirects 308. Links
  atualizados em `SuggestionsBanner`, `LinkedTasksSection`, `AppShell`
  (label "Plano de Ação" → "Ação"), `CommandMenuDialog`,
  `UpcomingTasksWidget`. Sub-rota `sugestoes` movida com `git mv`.

- **Direção E — Onda 2 + Onda 3: redesign de interfaces (2026-04-28/29):**
  Brainstorm convergiu em Direção E (refinada por product-designer +
  financial-planner). Modelo mental novo: **Relatório = foto + análise**
  (gera sugestões), **`/plano` = one-page executivo** (KPIs + metas +
  Decisions), **`/acao` = superfície dinâmica** (Inbox de sugestões +
  Tasks + Timeline + Notas). `/dashboard` será absorvido pelo `/plano`
  em onda futura.

  **Onda 2 entregue (UI Decisions em `/plano`):** 6 componentes novos
  em `frontend/src/app/(app)/plano/_components/` (DecisionsSection,
  DecisionCard, DecisionFormDialog, DecisionSupersedeDialog,
  DecisionStatusBadge, decisionsCopy) — primeira UI de gestão exposta
  ao usuário para o aggregate Decision (ADR-136 entregue em A7.5 sem
  UI). Hook `useDecisions` estendido com `create()`. Copy PT-BR de
  leigo (Pendente→A decidir, Decidido→Em vigor, Executado→Aplicada,
  Superseded→Substituída) — esconde vocabulário event-sourced.
  Rationale obrigatório (≥10 chars) implementa deliberação consciente
  exigida por Cerbasi/AUVP. 11 testes para helpers puros. Branch
  `agent/decisions-ui-plano/20260428-1654`.

  **Onda 3 entregue (remoção do Modo Tático do relatório,
  [ADR-151](DECISIONS.md#adr-151--remoção-do-modo-tático-do-relatório-direção-e-do-redesign-de-interfaces)):**
  Modo Tático (T1-T6) removido do relatório nativo React. `tatico:`
  removido de `config/report_layout.yaml`; `plano_de_acao` movido para
  `estrategico:` (apêndice "Decisões em Vigor no Período").
  `TaticoSections.tsx` (494 LOC) e `aportesAdapter.ts` deletados.
  `ReportShell`/`ModeContext`/`ModeProvider`/`ModeToggle`/
  `ReportActions`/`ReportTopNav` simplificados — `ReportMode` reduzido
  a `'estrategico' | 'usa'`. ADR-117 e ADR-123 marcadas como
  parcialmente superseded. Tabelas `kanban_items` e `report_notes`
  permanecem no DB durante janela transitória (migração para `tasks` +
  `workspace_notes` é Onda 1 futura).

- **Test charts — lint anti-regressão `--chart-N: oklch(…)` (2026-04-27):**
  Follow-up do CAVEAT registrado no fix `de2c00a` (barras pretas RDM).
  Novo spec em
  [`frontend/tests/styles/chart-vars-no-oklch.test.ts`](../frontend/tests/styles/chart-vars-no-oklch.test.ts)
  varre `frontend/src/**/*.css` e falha se qualquer `--chart-\d+`
  estiver definido com `oklch()`, `oklab()`, `lab()` ou `lch()` —
  funções que `@kurkle/color@0.3.4` (parser do Chart.js) não suporta,
  produzindo `ctx.fillStyle` inválido e canvas preto. O teste
  componente existente em
  [`ReceitaDespesaMensalChart.test.tsx:274-301`](../frontend/tests/components/report/ReceitaDespesaMensalChart.test.tsx)
  só pega literal `var(...)` no dataset; em jsdom `useChartTheme`
  cai pro `LIGHT_FALLBACK` (hex hard-coded), então regressão na CSS
  escapava. Verificado revertendo `de2c00a` localmente: 24 ofensores
  flagged, fix-forward retornou 4/4 verdes.

- **Fix charts — barras pretas em ReceitaDespesaMensalChart (2026-04-27, [`de2c00a`](https://github.com/davidrobert/mathoms/commit/de2c00a)):**
  Bug visual reportado via screenshot de produção (S2 — Fluxo de Caixa):
  todas as barras renderizavam pretas, mesmo com legendas coloridas
  corretamente. Sintoma parecido com 9ce3ce2 ("cores resolvidas"),
  porém raiz diferente. **Root cause:** `--chart-1..12` definidos
  duas vezes — `tokens.css:101-112` como hex (`#1A3A5C`, ...) e
  `globals.css:58-70` como `oklch(...)`. Como `globals.css` importa
  `tokens.css` na linha 10, o cascade terminava com os `oklch()`
  ganhando. Chart.js usa `@kurkle/color@0.3.4`, que só parseia
  hex/rgb/hsl/hwb — `oklch()` é silenciosamente inválido →
  `ctx.fillStyle` cai pro default preto no canvas. Legendas (HTML+CSS)
  funcionavam porque o browser resolve `oklch()` nativamente em CSS;
  só o canvas quebrava. **Fix:** remover ambos os blocos `--chart-N`
  duplicados (light + dark) de `globals.css` — o próprio comentário
  em `globals.css:14-16` já proibia essa duplicação ("NÃO duplicar
  variáveis que já estão em tokens.css"). Cascade volta a resolver
  pelos hex de `tokens.css`. Tests 22/22 verdes (mock de Chart.js
  não capturava o bug; `LIGHT_FALLBACK` em `useChartTheme` mascarava
  o que `getComputedStyle` retornaria em produção). CAVEAT: regressão
  futura — adicionar lint que rejeite `--chart-\d+: oklch` em
  qualquer CSS é candidato a follow-up.

- **Fix charts S2 — eixo X yy/mm → MMM/aa pt-BR (2026-04-27, [`5eb956f`](https://github.com/davidrobert/mathoms/commit/5eb956f)):**
  Bug 3 do trio reportado pelo usuário. Backend `e5_analyze.py:1311` emite
  labels de chart mensais como `"26/02"` (yy/mm), formato facilmente lido
  como `dd/MM` ("dia 26 fev"). Fix puramente no frontend (backend canônico
  é parseado por `previdencia_analyzer`, `cenarios_conjuge_analyzer`,
  `orcamento_calculator` etc. — não tocar). Helper `formatChartMonthLabel`
  em [`charts/_shared.ts`](../frontend/src/components/report/charts/_shared.ts)
  converte `"26/02"` → `"fev/26"` via regex + `MONTH_SHORT_PT_LOWER`.
  Aplicado em `FluxoMensalChart.slicedLabels` e
  `ReceitaDespesaMensalChart.sliceWindow.labels`. Outros consumidores
  (`ReceitaBarChart`, `DespesasDoughnutChart`) usam labels de fonte/
  categoria, não meses — não precisam. Vitest 3 cenários (canônico,
  não-casa, mês fora 01-12). Helper colocado em `charts/_shared.ts`
  (não em `lib/format.ts`) para ficar coeso com `fmtBRL` e evitar
  cruzar threshold T2_ts_long_files do gate code-style-baseline.
  CAVEAT: visual baselines de S2 mudam (texto eixo X diferente).

- **Fix charts S2 — cores resolvidas + eixo Y (2026-04-27):** Bugs visuais
  reportados via screenshots de produção em `ReceitaDespesaMensalChart`
  e `FluxoMensalChart` (S2 — Fluxo de Caixa). **Bug 1 (cores pretas):**
  ambos os charts passavam literais `var(--chart-N)` / `var(--semantic-gain)`
  como `backgroundColor` ao Chart.js — Chart.js não resolve CSS vars no
  canvas (apenas no DOM, motivo pelo qual a legenda `RDMLegend` mostrava
  cores corretas mas o canvas ficava preto). Fix: `useChartTheme()`
  estendido com `theme.semantic.{gain,loss}` (resolvidos via
  `getComputedStyle`); `ReceitaDespesaMensalChart` consome
  `theme.categorical` em vez de `pickColorByIndex` (que retorna literal
  `var(...)`); `FluxoMensalChart` consome `theme.semantic`. **Bug 2
  (eixo Y):** (a) `ReceitaDespesaMensalChart` começava em `-R$ 20k`
  mesmo sem valores negativos — fix `beginAtZero: true` no scale `y`;
  (b) `FluxoMensalChart` duplicava label "R$ 50.000" sem sinal `−` no
  negativo (bipolar ok, mas formatter aplicava `Math.abs`) — fix
  removendo `Math.abs` em `formatValue`. `pickColorByIndex` marcado
  `@deprecated` (mantido por compat com `PatrimonioDoughnutChart`/
  `ReceitaBarChart`/`DespesasDoughnutChart`). Anti-regressão Vitest:
  novos testes garantem `dataset.backgroundColor` jamais começa com
  `"var("`. **CAVEAT:** visual baselines de S2
  (`S2-light-visual-linux.png`, `S2-dark-visual-linux.png`) precisam
  refresh em próxima rodada de visual gate via humano com
  `update_visual_baselines=true` — preto → colorido e Y-axis zerado
  mudam pixel rendering.

- **A8.0 Follow-ups A7 — ✅ entregue (2026-04-27):** 3 itens herdados de
  CTO G4 sign-off do PR #15 (Sprint A7 closeout). XS (~1h) lane.

  **Entregas:**
  - **(a) ADR-149** formalizando o trade-off da Sprint A7.5: `config/report_layout.yaml`
    permanece como **asset de produto** (não dado cliente). Critério explícito:
    arquivos em `config/` devem cumprir 4 itens (não-PII, consumido por código,
    time Mathoms edita, sem schema DB redundante). Política de paths proibidos
    é por arquivo (não diretório). Lista atual de assets legítimos: `report_layout.yaml`,
    `pipeline.json`, `scoring.json`, `schemas/`, `prompts/`, `templates/`.
    [ADR-149](DECISIONS.md#adr-149--configreport_layoutyaml-permanece-como-asset-de-produto-sprint-a80).
  - **(b) `docs/ARCHITECTURE.md §Fluxo de runtime`** atualizado: §Materialização
    de config → §Carregamento de config (DB-first pós-Sprint A7) descreve
    `_prepare_run_context` + `prepare_pipeline_config_dir` + `build_config_overrides_from_db`
    + `build_config_store(DBConfigStore)` em vez de `materialize_config`.
    §12 Padrões arquiteturais: "Materialize, Don't Inject" marcado como
    **superseded por ConfigStore em Sprint A7** (preserva história F3 mas
    aponta para o padrão atual). Tabela §11 atualizada para `prepare_pipeline_config_dir`.
  - **(c) Pruning de 3 dead `load_global_json` calls** em
    `backend/app/api/{categories.py,family_members.py,config.py}` para os
    nomes deletados em A7.5 (`family_members.json`, `categorization.json`,
    `institutions.json`). Code path morto: `load_global_json` retornava `{}`
    graceful pós-A7.5 (file ausente). Substituído por `{}` literal com
    comentário de contexto. Helper `_export_institutions` separado de
    `_export_blob_or_default` (institutions perdeu o default disco; pipeline
    e report_layout permanecem com fallback global).

  **Tests:** 1479 backend passed (zero regressão). Endpoints legacy
  `/categories`, `/members`, `/export` continuam retornando shape vazio
  coerente para workspace sem rows (comportamento multi-tenant correto:
  não vaza identidade do founder, F6.5E.6).

  **Bridges remanescentes pós-A8.0:** nenhum novo. Helper `load_global_json`
  + `load_global_yaml` em `config_defaults.py` permanecem (usados por
  `pipeline.json` + `report_layout.yaml` que **permanecem em `config/`**
  conforme ADR-149).

- **Spec mobile do relatório ✅ docs-only (2026-04-27):** D3 do
  `report-a11y-finalize` (deixada em aberto) e [batch2.13](BACKLOG.md)
  resolvidos com [REPORT_MOBILE_SPEC.md](REPORT_MOBILE_SPEC.md) novo +
  delta em [REPORT_PREMIUM_PLAN.md §17.10](REPORT_PREMIUM_PLAN.md).
  Decisão de produto convergida: relatório suporta `<767px` em
  leitura/consulta; modo Tático fica acessível com tooltip
  "Otimizado para tablet/desktop"; T3 Kanban vira lista vertical
  agrupada estendendo o fallback v2.7; charts ganham fallback
  agregado (donut top-7 + "outros", slide window 6m default,
  Top-15→Top-5); tabelas com >3 cols viram cards; tipografia escala
  87.5% global. Print/PDF mantém layout desktop em qualquer viewport
  (não-escopo). Auditoria estática catalogou 9 issues (3 estruturais
  P0/P1, 3 estéticos P1/P2, 3 informacionais P0/P1). Implementação
  fica em lane futura `report-mobile-impl` (P2, 2-5d, ~34h em 7
  slices) — esta entrega é spec only. Commit `4c76c4b`.

- **Regressão visual fixada + rebaseline parcial (Items 4+2) ✅ (2026-04-27):**
  Item 4 fixou a regressão silenciosa que fazia 28 baselines visuais (cover×2 +
  S1-S4×2 + S7-S10×2 + APP_A-E×2) skipar com `count===0` para
  `section#S1[data-report-section]`. Causa raiz: commit `ba29df1`
  (`ConsumoConscienteCard` em S2) chamava `pontuais.length` sobre items vindos
  de `useConsumoPontuais`, que confiava no shape de `ConsumoPontuaisResponse`.
  Em ambientes mockados (mock catch-all `{}` em `tests/e2e/helpers/mock-report.ts`),
  `items` chegava `undefined`, lançando `TypeError: Cannot read properties of
  undefined (reading 'length')`. ErrorBoundary do shell capturava e
  substituía o `<article>` inteiro — fazendo S1-S10/APP_A-E desaparecerem do
  DOM, e `count() === 0` em `snapshotSection()` chamar `test.skip()` em vez
  de capturar screenshot. Sintoma silencioso: visual job verde, mas baselines
  não atualizavam. Commit [`b47dd47`](https://github.com/davidrobert/mathoms/commit/b47dd47):
  fix em duas camadas defensivas — (1) `useConsumoPontuais.toState()` coerce
  `items`/`total`/`total_valor` para defaults seguros (`Array.isArray` +
  `typeof number`); (2) `mock-report.ts` adiciona rota explícita
  `/reports/consumo-pontuais` retornando shape completo. Anti-regressão:
  `tests/hooks/useConsumoPontuais.test.tsx` cobre 3 cenários (resposta
  válida, malformada `{}`, erro de rede).

  Item 2 disparou run [25011732190](https://github.com/davidrobert/mathoms/actions/runs/25011732190)
  em main com `update_visual_baselines=true`. **24 PNGs regenerados** em
  `frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts-snapshots/`:
  cover×2 + S1-S10×2 = 16 + APP_A-D×2 = 8 (todas estratégicas + apêndices
  exceto APP-E). **Cover, APP-E, T1-T6, U1-U4 preservados** — Playwright
  detectou conteúdo idêntico (não mudaram visualmente apesar de v2.F.3b
  cover identity, v2.4 T2 Aportes, v2.7 DnD Kanban, v2.8 SectionSnapshotDiff;
  layouts e cores absorveram alterações sem mudança pixel-detectável). Cover
  pré-existia desde `0558ea3` (Apr 26 manhã, antes de `db6cf6f` cover
  identity 15:54), mas o screenshot é fullPage clip do `#report-main` na
  zona y=0..720 — área não afetada pelos meta-cards reordenados.

  **CAVEATS:**
  - **Tático Tx flakiness CI** — 5 flaky + 2 failed (T5 light, T6 dark)
    timeoutaram em `[data-report-ready="true"]` no CI Linux. Não reproduz
    localmente (darwin), e PNGs no artefato são idênticos ao main —
    sugerindo race condition no warmup do dev server (CI cold start vs
    local hot reload). Investigar em lane separada. Não bloqueia merge dos
    24 baselines novos.
  - Run conclusion=`failure` por causa dos 2 fails Tático, mas a Playwright
    re-tenta antes de chamar fail e os 24 PNGs corretos chegaram via artefato
    `report-visual-baselines-generated`.

- **DECISIONS.md cleanup — plano F0-F8 ✅ (2026-04-27):**
  Plano de correção em 9 fases derivado da auditoria estrutural pelo
  `senior-cto`. Estado final: 142 headings · 280 anchor refs · 0 broken
  · ToC cobrindo 100% das ADRs (era 30%) · 141/141 ADRs validam formato.

  Entregas:
  - **F0** [`95c1aed`](https://github.com/davidrobert/mathoms/commit/95c1aed):
    [dev/check_adr_anchors.py](dev/check_adr_anchors.py) — gate de
    GitHub Slugger; valida toda referência `[X](#adr-...)` contra slugs
    canônicos gerados a partir dos headings. Modo `--suggest` gera sed
    pronto.
  - **F1** [`95c1aed`](https://github.com/davidrobert/mathoms/commit/95c1aed):
    15 anchor links broken corrigidos (ToC: D18/D19/D30/D75/D29-TQ/D30-WS/D55;
    cross-refs internas: ADR-082, ADR-106 ×2, ADR-115 ×2, ADR-073, ADR-141).
  - **F2** [`d1d2531`](https://github.com/davidrobert/mathoms/commit/d1d2531):
    drift de conteúdo. PII "Ferreira-Campos" removida em prosa (4 lugares;
    3 mantidas em refs a paths reais de scripts). Path obsoleto
    `config/definitions.md` substituído por nota cruzada para ADR-143.
    Banner pós-ADR-129 em ADR-078.
  - **F3** [`8afdb9d`](https://github.com/davidrobert/mathoms/commit/8afdb9d):
    move ADR-143 antes de ADR-144 (restaura ordem cronológica + numérica
    da Sprint A7.6). Bug fix unicode em
    [dev/check_adr_anchors.py](dev/check_adr_anchors.py) (regex
    `[a-z0-9_\-]` não pegava ã/é/ó) revelou +15 anchors broken escondidos
    (ADR-101 ×7 `ddd-solid`/`dddsolid`, ADR-128 ×4 `lê-escreve`/`lêescreve`,
    ADR-090 ×2, ADR-075/093/097 ×1 cada).
  - **F4** [`27ba9b0`](https://github.com/davidrobert/mathoms/commit/27ba9b0):
    [dev/build_adr_toc.py](dev/build_adr_toc.py) — auto-gen idempotente
    do ToC com 19 categorias canônicas + tabela de overrides por número.
    Marcações `<!-- ADR-TOC-START -->` / `<!-- ADR-TOC-END -->`
    delimitam a área editável.
  - **F5** [`7fe3517`](https://github.com/davidrobert/mathoms/commit/7fe3517):
    Status outliers padronizados (ADR-046 `Revisado` → `Decidido` +
    revisão inline; ADR-093 `🚧 Em execução` → `Decidido (F9 · execução
    em andamento)`). ADR-140/141 consolidam Status+Data+Implementação
    na mesma linha.
  - **F6** [`f0a09b3`](https://github.com/davidrobert/mathoms/commit/f0a09b3):
    bidirecional supersedure — banners em 5 ADRs históricas substituídas
    (ADR-013 ← ADR-072; ADR-016 ← ADR-079; ADR-020 ← ADR-085; ADR-062
    ← ADR-064; ADR-122 ← ADR-144).
  - **F7** SKIPPED — quebrar ADR-148 (269 linhas) e ADR-132 (205 linhas)
    fica como follow-up oportunístico quando ADRs forem revisitadas.
    Trade-off "ADR enxuta perde rastreabilidade vs. ADR densa é a doença"
    sem ganho claro.
  - **F8** [`ff1465c`](https://github.com/davidrobert/mathoms/commit/ff1465c):
    [dev/validate_adr_format.py](dev/validate_adr_format.py) (formato
    Status/Data/seções estruturadas) + cheat-sheet no preâmbulo do
    `docs/DECISIONS.md` + protocolo em [CLAUDE.md §"ADRs →
    docs/DECISIONS.md"](CLAUDE.md). 3 hooks pre-commit registrados em
    `.pre-commit-config.yaml` (`adr-anchors`, `adr-toc`, `adr-format`)
    rodam apenas em mudanças no DECISIONS.md.

  **Recomendação institucionalizada:** novas ADRs devem rodar
  `python3 dev/check_adr_anchors.py --suggest` antes de citar anchor;
  `python3 dev/build_adr_toc.py --inline` após mudar headings; gates
  pre-commit pegam regressões automaticamente.

- **`code_style_baseline.json` refresh — fecha débito P1+P7 herdado ✅ (2026-04-27, [`e90cbd9`](https://github.com/davidrobert/mathoms/commit/e90cbd9)):**
  Baseline `dev/code_style_baseline.json` estava bloqueando CI em main com 5 ofensores não-absorvidos. Premissa original do orquestrador ("herdado de A7.6 `19e0068`") estava desatualizada — A7.6 já tinha refrescado próprio baseline em 3 commits sequenciais (`63162a8` + `db75a33` + `92dc03c`). Ofensores reais: 4 em [`dev/check_adr_anchors.py`](dev/check_adr_anchors.py) (commit `26437e9` F0+F1 anchors gate) + 1 em [`tests/test_snapshot_changelog.py`](tests/test_snapshot_changelog.py) (commit `2ae9dcd` v2.D.1.1 cenário 9 T5 expense polarity). Refresh focado nos arquivos específicos, sem absorção genérica. Bonus: ruff-format faltante em `check_adr_anchors.py` corrigido em commit separado [`43735ee`](https://github.com/davidrobert/mathoms/commit/43735ee). **`pre-commit run --all-files` verde sem nenhum SKIP** — workaround `SKIP=code-style-baseline` que v2.D.1, v2.8, v2.9, v2.D.1.1 usaram durante o Cenário B não é mais necessário.

- **E2E `@critical` débito ✅ resolvido (2026-04-27):** Lane separada lançada em paralelo (`a86a806e8da6d60f1`) foi cancelada após Lane 4+2 (`b47dd47`) descobrir e fixar o **mesmo root cause**: `useConsumoPontuais.toState()` shape coercion + `mock-report.ts` rota `/reports/consumo-pontuais`. Os 19 specs `@critical` que falhavam com `Cannot read properties of undefined 'length'` voltam ao verde após `b47dd47`; spec `snapshot-changelog.@critical.spec.ts` (marcado `test.skip` em v2.8 por causa desse bug) pode ter `skip` removido em lane futura quando alguém validar.

- **Report Premium UI v2.2b completa — modo USA re-habilitado + 8 baselines U1-U4 ✅ (2026-04-27):**
  Decisão de produto autorizou retomar o modo USA. Reverte parcialmente
  `adc3a15` ("ocultar USA temporariamente"): U1-U4 `enabled: true` no
  `config/report_layout.yaml`, bloco `navigation.usa` descomentado, codegen
  TS+Pydantic regerados; `ReportActions.VISIBLE_MODES` e `ModeToggle` voltam
  a expor a aba "EUA" no tablist do header; `ReportShell.test` re-afirma
  `getByRole("tab", { name: "EUA" })`. Spec visual `sections.snapshots.visual.spec.ts`
  troca `test.describe.skip("Snapshots — modo USA")` por `test.describe(...)`;
  helper `setupReport(..., "usa")` (já entregue em v2.2b parcial via deep-link
  `?mode=usa`) cobre os 4 sections × {light,dark}. Run CI dispara
  `update_visual_baselines=true` para popular as 8 baselines pendentes
  (U1-U4 × {light,dark}) em `sections.snapshots.visual.spec.ts-snapshots/`.
  Vitest 668/668 verde; baseline drift `code-style-baseline` + `ruff-format`
  pendentes em outras lanes (Lane 5) — não tocados.
- **Report Premium UI v2.D.1.1 + v2.9.1 — copy review entregue pelo product-designer ✅ (2026-04-27):**
  Cenário B fechou os dois débitos editoriais abertos durante a saída do v2.
  **v2.D.1.1 (`2ae9dcd`):** `SnapshotChangelogBuilder` ganha `SECTION_POLARITY`
  classificando S1/S2/S3/T2 como `asset` e T5 como `expense`. Verbos sem viés
  (`avançou/recuou` para asset, `subiu/recuou` para expense) substituem
  `cresceu/caiu`; cauda temporal "no mês" reduz repetição em listas. Cópia de
  zero ajustada (`passou a registrar`, `antes sem valor`, `zerou neste relatório`,
  `segue sem valor registrado`). 5 goldens atualizados + 1 cenário novo
  (`test_cenario_9_expense_polarity_t5_usa_subiu`) trava regressão de viés em
  despesa. **v2.9.1 (`2b8b144`):** `config/prompts/section_summaries.yaml` salta
  para `version: "1.1"`. System prompt reescrito com persona Mathoms ancorada em
  COPY_GUIDELINES (Perini/Cerbasi/AUVP), regras anti-hallucination explícitas
  (proibida projeção sem payload, comparação externa, inferência causal,
  promessa de retorno) e anti-padrões de tom (sem exclamação/gamificação/
  alarmismo). 13 user_prompts ganham contexto editorial específico, ângulo
  narrativo claro e thresholds explícitos para `tone`. Labels alinhadas a
  `report_layout.yaml`; correções de divergência: T3 `Tributação tática` →
  `Checklist de Tarefas` e T5 `Cenários e simulações` → `Próximos Passos`. Sem
  mudança de schema (`SectionSummaryOutput` intacto). Toggle prod
  `MATHOMS_LLM_SECTION_SUMMARIES` permanece OFF até QA editorial humano em
  workspace dogfood (escopo do dono do produto). Follow-up v3: hash-de-prompt
  na cache key.

Trabalho em andamento: execução da **[ADR-093](DECISIONS.md#adr-093--rename-completo-de-identificadores-de-stage-opção-a)** (rename de stages F9) +
preparação para **F7 (Produção + LGPD + Ops)**.
**[ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side)**
(descontinuação do renderer HTML server-side) — concluída em 2026-04-25.

- **Sprint A7 ✅ entregue 2026-04-27 — Config DB Cutover (CLI legacy removal):**
  7 lanes mergeadas em `main` no mesmo dia (A7.0 → A7.6). Plano canônico arquivado
  em [docs/archive/CONFIG_CUTOVER_PLAN-2026-04-27.md](archive/CONFIG_CUTOVER_PLAN-2026-04-27.md).
  Resultado: produto roda 100% DB-first via `DBConfigStore` (ADR-134); 5 arquivos
  legados de `config/` deletados em A7.5 (`categorization.json`,
  `family_members.json`, `institutions.json`, `parametros_fiscais.json`,
  `taxas.json`) + `decisions.md` (A7.2a) + 4 docs metodológicos saídos via
  A7.4/A7.6. Tabelas globais versionadas substituem `parametros_fiscais.json`
  + `taxas.json` (ADR-135); entidade `Decision` event-sourced substitui markdown
  editorial (ADR-136); catalog+override resolver substitui
  `categorization.json`/`institutions.json` legados (ADR-137); rules-as-code
  dissolveu `docs/methodology/` (ADR-143). **Bridges removidos em A7.5 (commit
  final):** `FileConfigStore`, `materialize_config()` + helpers `_override_*`,
  `legacy_json_to_fiscal`. **`config/report_layout.yaml`** permanece como
  source-of-truth do codegen `dev/codegen_report_layout.py` (ADR-076) + default
  global do blob — débito A8. **Testes:** 1555+ pipeline + 1475+ backend
  continuam verdes; tests legacy adaptados (`test_config_materializer`,
  `test_serializers_round_trip`, `test_golden_pipeline`, `test_config_api/_fallback`,
  `test_consumo_pontuais`, `test_e5/e5n_golden_execution`, `test_stage_wrappers`);
  fixtures `parametros_fiscais.json` + `taxas.json` migradas para
  `tests/fixtures/legacy_configs/`. **STATELESS_AUDIT.md atualizado**
  (`FileConfigStore._cache` saiu da lista). **`dev/check_forbidden_paths.py`**
  bloqueia 11 paths legados de `config/`. CTO sign-off em 4 gates por lane.


- **Report Premium UI v2 — saída ✅ (Cenário B fechou as 6 sub-lanes finais 2026-04-27):**
  6 lanes em 2 ondas paralelas + recovery: v2.2b (Tático ✅, USA ⏸ produto),
  v2.4 (T2 Aportes), v2.10 (PDF visual diff), v2.D.1 (SnapshotChangelogBuilder
  · [ADR-148](DECISIONS.md#adr-148--snapshotchangelogbuilder-comparações-mês-a-mês-de-relatório)),
  v2.8 (comparisons/changelog ON), v2.9 (LLM section_summaries · [ADR-144](DECISIONS.md#adr-144--section_summaries-llm-driven-em-e5-com-cache--fallback-determinístico-v29)).
  **Caminho crítico v2.D.1 → v2.8 fechado.** **2 ADRs novas:** ADR-148
  (Snapshot — renumerada de 143 após colisão dupla: ADR-140 com Goal IF v2 e
  A7.6 com rules-as-code) e ADR-144 (LLM section_summaries; toggle default OFF).
  **Aprendizado de processo:** senior-cto recusou implementação corretamente —
  escopo dele é review/ADR; general-purpose para FASE 2 daqui pra frente. Cada
  agente FASE 1 (ADR) → senior-cto; FASE 2 (impl) → general-purpose. Reservas
  de número de ADR colidiram 2× durante a sprint (ADR-140 reservado/perdido para
  Goal IF v2; ADR-143 reservado/perdido para A7.6 rules-as-code) — renumeração
  cirúrgica via `git rebase` na branch resolveu sem reescrever main. **Débitos
  abertos** que não bloqueiam a saída: ~~v2.D.1.1~~ ✅ 2026-04-27 (`2ae9dcd`),
  ~~v2.9.1~~ ✅ 2026-04-27 (`2b8b144`), re-baseline visual
  S1/S2/S3/T2/T3/T5, E2E `@critical` herdado de débito alheio em main,
  regressão visual herdada de `0558ea3`. **Total v2:** Onda A 3/3 (v2.2b
  parcial USA) · B 3/3 · C 3/3 · D 2/2 · E 8/8 · F 5/5.

- **Report Premium UI v2.8 — comparisons + changelog ativos no relatório ✅ (2026-04-27):**
  Conecta o `SnapshotChangelogBuilder` (v2.D.1 · [ADR-148](DECISIONS.md#adr-148--snapshotchangelogbuilder-comparações-mês-a-mês-de-relatório))
  ao endpoint + UI. 12 placeholders YAML em S1/S2/S3/T2/T3/T5 flippados de
  `enabled:false → true` (commit `384b5bf`); `GET /reports/{id}/data` injeta
  `comparisons: ComparisonItemRead[] | null` + `changelog: ChangelogEntryRead[] | null`
  top-level via `snapshot_pair_loader` + `build_comparison()` (commit `0576b11`);
  novos componentes React `ComparisonItemsBlock` (tabela antes→depois com sinal
  ▲▼•), `SnapshotChangelogList` (lista com borda colorida por delta_signal) e
  `SectionSnapshotDiff` wrapper que filtra por sectionId (commit `076d8f3`).
  `conclusionUtils.deriveSectionSummary` ganha 3 camadas: LLM v2.9 prioritário >
  template + changelog summary determinístico > template puro. **Caveats:**
  (a) débito alheio em origin/main pós-v2.9 — todos os 19 specs `@critical` de
  `/reports/[id]` quebram com erro genérico "Cannot read properties of undefined"
  (verificado em worktree limpa de origin/main); spec novo `snapshot-changelog.@critical.spec.ts`
  marcado `test.skip` com plano de unfreeze. (b) baselines visuais não regenerados
  nesta lane — próxima rodada de visual gate vai precisar `update_visual_baselines=true`
  para S1/S2/S3/T2/T3/T5 (componentes novos renderizam onde antes era nada).
  Onda D do plano Report Premium fechada (2/2). v2.D.1.1 segue aberta como
  débito de copy review pelo product-designer.

- **A7.6 — Rules-as-code: dissolver `docs/methodology/` ✅ entregue (2026-04-27):**
  Branch `agent/a7-6-rules-as-code/20260427-1311`, 7 commits + baseline
  refresh, mergeados em `main`. Auditoria pós-A7.4 detectou que os 4
  markdowns movidos para `docs/methodology/` continham 102 hits
  cliente-PII (David, Mariana, Tasso, Hashdex, valores BRL, contas
  Itaú/BTG/Santander) violando CLAUDE.md §Regras críticas. A7.6 dissolveu
  o diretório (rules-as-code, [ADR-143](DECISIONS.md#adr-143--docsmethodology-é-rules-as-code-sprint-a76)):

  - **regras_composicao_patrimonial.md** → docstring de módulo expandido
    em `pipeline/domain/services/patrimonio_calculator.py` documentando
    as 7 categorias canonical + 3 fixtures de teste anônimas
    (titular/conjuge, ImovelExemplo, FundoExemplo, BancoExemplo) +
    [ADR-145](DECISIONS.md#adr-145--7-categorias-canonical-da-composição-patrimonial).
  - **source_hierarchy.md** → novo módulo
    `pipeline/domain/services/source_tier.py` com constants TIER_*,
    `SourcedTransaction`, `pick_winner`, `resolve_account_tier` +
    docstring expandido em `reconciliation_service.py` +
    [ADR-146](DECISIONS.md#adr-146--e3-source-hierarchy--bankaccountsource_tier-schema).
    Schema migration `BankAccount.source_tier` (Alembic
    `z4a5b6c7d8e9_adr146_bank_account_source_tier.py`) backwards-compat
    (add nullable + default None — populate/flip ficam para PR futuro
    quando `is_duplicate` plumbar tier). 9 specs novos em
    `tests/unit/pipeline/test_e3_source_tier_tie_breaking.py` cobrindo
    invariantes ADR-146 §Consequências (tier mais alto vence; mesmo
    tier → timestamp mais recente vence).
  - **milhas.md** → bridge `parse_milhas_md` lê `<workspace>/notes/milhas.md`
    primeiro com fallback warned para legado (removido em A7.5). Migrator
    one-shot `dev/migrate_milhas_to_workspace_storage.py` (idempotente,
    `--workspace-id`/`--workspace-root`/`--source`/`--force`). Universal
    valuation methodology em docstring de `parse_milhas_md_content` +
    [ADR-147](DECISIONS.md#adr-147--milhas-valuation-methodology-universal--storage-workspace-scoped).
    `MileageProgram` DB aggregate = débito técnico aceito p/ Sprint A8.1.
  - **definitions.md** → cliente puro dropado (DB rows); decisões de
    planejamento absorvidas em A7.2a `Decision`; categorias absorvidas
    em A7.3 catalog/override (em curso); regras universais cobertas
    pelos docstrings de A7.6. Novo índice em
    [docs/ARCHITECTURE.md §4.1 Domain glossary](ARCHITECTURE.md) com
    11 conceitos × módulo enforcer × ADR canônica.

  **Cleanup final:** `docs/methodology/` deletado;
  `dev/check_forbidden_paths.py` + `dev/commit.py` bloqueiam recriação
  via `FORBIDDEN_DIRS += "docs/methodology/"`. CLAUDE.md ganha bloco
  "§Methodology = code" em Regras críticas + `docs/methodology/` em
  §Paths proibidos. Comentários stale em `scripts/{e4_categorize,e_reset,e5_analyze}.py`
  e `backend/tests/test_config_materializer.py` atualizados.

  **Fix incidental — alembic heads collision (pre-existing bug):** A7.2a
  e A7.2b ambas geraram revision id `x2y3z4a5b6c7`, deixando 2 alembic
  heads em main. A7.6 renomeia o ID interno da fiscal migration para
  `x2adr135fp01` e meu `z4a5b6c7d8e9` colapsa via tupla
  `down_revision = (x2y3z4a5b6c7, y3z4a5b6c7d8)`. Resultado: `pytest
  backend/tests/test_alembic_guardrails.py` (4 specs antes red) volta
  a verde.

  **Tests:** `pytest backend/tests -q` 1413 passed (era 1413, +1 por
  schema snapshot); `pytest tests/test_e3_golden_execution.py
  tests/test_e4_golden_execution.py tests/test_e5_golden_execution.py
  tests/test_e5n_golden_execution.py` 9 passed (paridade byte-a-byte
  preservada); `pytest tests/unit/pipeline/test_e3_source_tier_tie_breaking.py
  test_e5_content_parsers.py test_patrimonio_calculator.py` 89 passed
  (+12 novas specs A7.6); `dev/check_forbidden_paths.py` bloqueia
  `docs/methodology/**`; `dev/check_code_style_regression.py` baseline
  refresh intencional (P7+10 multi-paragraph docstrings co-localizados
  com regras enforce — ADR-143 mandate).

  **Coordenação:** zero overlap com A7.3 (em curso, toca catalog/override);
  Sub-task 1 (definitions.md cleanup) já cobriu todo o conteúdo non-A7.3.
  A7.3 finaliza categorias/instituições remanescentes quando mergear.

  **Spawn task:** `chore(format): ruff format A7.2a/A7.2b leftovers` —
  12 arquivos pré-existentes precisam ruff format (decisions, fiscal_parameters)
  fora do escopo desta lane. Side task criada para commit dedicado.

- **Report Premium UI v2.9 — LLM section_summaries em E5 ✅ (2026-04-27):**
  Fase 2 da [ADR-144](DECISIONS.md#adr-144--section_summaries-llm-driven-em-e5-com-cache--fallback-determinístico-v29)
  (mergeada como `22627e6` 2026-04-27 manhã). Substitui templates
  determinísticos puros por LLM (LiteLLM + Instructor + Pydantic) com
  cache Redis 24h e fallback determinístico. Toggle global default OFF
  (env `MATHOMS_LLM_SECTION_SUMMARIES=1`) até **v2.9.1** revisar copy
  com [product-designer](.claude/agents/product-designer.md).

  **Decisões fechadas em ADR-144 (Fase 1) — implementadas em Fase 2:**
  - Stack LiteLLM + Instructor + Pydantic (paridade E1/E1.5/E2-llm/E7-review-llm).
  - Cache key `mathoms:llm:section_summary:{workspace_id}:{snapshot_hash}:{section_id}`.
  - TTL 24h. Storage Redis preferido (NoOp se ausente; Postgres+TTL não
    implementado — cobertura atual: Redis ou degrade silencioso).
  - Fallback determinístico via Callable (lê `narrativas.summaries` legado
    do snapshot, ou string genérica por section_id).
  - Telemetry logger `mathoms.llm.section_summaries` (ADR-110), sem PII
    (snapshot_hash truncado a 12 chars; nunca loga texto gerado nem snapshot).
  - Stateless rigoroso (ADR-111): cache Protocol + impls injetadas;
    proibido `lru_cache`/dict global.

  **Estrutura:**
  - `pipeline/llm/schemas/section_summaries.py`: `SectionSummaryOutput`
    Pydantic — `summary_md` (10-400 chars), `tone: Literal["neutral","positive","warning"]`,
    `key_metric_ref?: str`. LLM nunca emite BRL inline (ADR-090); referencia
    métrica via `key_metric_ref` e renderer formata com `<MonetaryValue/>`.
  - `pipeline/domain/services/section_summary_generator.py`:
    `SectionSummaryGenerator` (Protocol-driven — `SectionSummaryLLMClient`,
    `SectionSummaryCache`, `DeterministicFallback Callable`); pipeline
    `cache → LLM → fallback`; `SectionSummaryGeneratorConfig` value-object
    frozen (não recebe `StageConfig` — ADR-097 D2/D3); `SectionSummaryResult`
    com `source: Literal["llm","cache","fallback"]`, `latency_ms`,
    `cost_usd: Decimal` (ADR-090). Telemetria via `_TelemetryEvent` dataclass
    tipado (ADR-097 D1, sem strings ad-hoc).
  - `backend/app/services/llm_cache.py`: `LLMCacheBackend` Protocol;
    `RedisLLMCache` (reusa singleton de `events.py`, falha aberta);
    `NoOpLLMCache`; `InMemoryLLMCache` (apenas tests); helper
    `build_section_summary_cache_key`. Distinto de `ArtifactStore`
    (ADR-127/128) — artefatos têm lineage; cache LLM é runtime efêmero.
  - `backend/app/services/section_summary_orchestrator.py`:
    `_LiteLLMSectionSummaryClient` adapter sobre `pipeline.llm.LLMService`;
    `build_default_generator` wires LiteLLM (Anthropic via env) + Redis
    cache + fallback; `generate_all_section_summaries` itera
    `SUPPORTED_SECTION_IDS` (S1/S2/S3/S4/S7/S8/S9/S10 + T2/T3/T5 + U1/U2 = 13);
    `compute_snapshot_hash` SHA-256 com sort_keys (cache key isola
    seções diferentes do mesmo snapshot — ADR-144 §2).
  - `config/prompts/section_summaries.yaml`: `system_prompt` compartilhado
    + 13 `user_prompt` templates por section_id. Copy editorial é
    placeholder; v2.9.1 abre revisão pelo product-designer.
  - `scripts/e5n_narrativas.py::main_with_store`: hook
    `_e5n_generate_section_summaries(ctx, e5_data)` chama orquestrador
    backend após narrativas determinísticas; persiste
    `e5_data["section_summaries"]` quando toggle ON. Falha aberta se
    backend indisponível (CLI standalone).
  - `frontend/src/lib/api/reports.ts`: `ReportAnalysisData` ganha
    `section_summaries?: Record<string, string>`.
  - `frontend/src/components/report/utils/conclusionUtils.ts`:
    `deriveSectionSummary` prefere `data.section_summaries[id]` quando
    presente e não-vazio; senão cai no template determinístico (rede
    de segurança quando LLM falha ou está OFF).

  **Goldens (sem bater Anthropic em CI):**
  - `tests/test_section_summary_generator.py` (10 testes) — 6 cenários
    do prompt (LLM success, cache hit, timeout, rate limit HTTP 429,
    invalid JSON, cache write→read entre chamadas) + 4 extras (template
    missing, cost_usd Decimal Haiku 4.5 pricing $1/M in + $5/M out,
    cache key formato canônico ADR-144, `SectionSummaryOutput` rejeita
    tone inválido).
  - `tests/test_section_summary_orchestrator.py` (8 testes) — toggle
    env default OFF, generator injetado, snapshot_hash determinístico
    (sort_keys), drift YAML↔código, fallback paths legacy/genérico/None.
  - `tests/fakes/llm.py` — fakes nomeados (CLAUDE.md §Testes "não
    MagicMock"): `FakeLLMSuccess`, `FakeLLMRaisingClient`,
    `make_fake_fallback`. Cobre TimeoutError, RuntimeError com "429",
    ValueError com "pydantic validation error".
  - `frontend/tests/components/report/dataAdapters.test.ts` — 3 testes
    novos (LLM presente, ausente, whitespace).

  **Boundary preservado:** generator não importa
  `redis`/`fastapi`/`celery`/`sqlalchemy` (`dev/check_pipeline_boundaries.py`
  verde). Redis client wire-up vive em `backend/app/services/`. Generator
  recebe Protocol + Callable via construtor.

  **Custo estimado real (refino ADR-144 §5 com pricing 2026-04 vigente):**
  - Haiku 4.5: $1.00/M input + $5.00/M output → 13 seções × (2k in + 500 out)
    = 26k tokens in + 6.5k tokens out = $0.026 + $0.0325 = **~$0.0585 por
    relatório novo**. Com cache hit ratio 60% (TTL 24h, mesmo dia): **~$0.023
    amortizado por relatório**. Para 1000 relatórios/mês = **$23-58/mês**
    (vs $18-54 da estimativa ADR-144 §5 que usava 10 seções; v2.9 entrega
    13 seções — drift +30% vs ADR mas ainda dentro do envelope aceito).
  - Sonnet 4.6 opt-in (`MATHOMS_LLM_SECTION_SUMMARY_MODEL=claude-sonnet-4-6`):
    $3/M in + $15/M out → ~$0.176 por relatório novo, ~$0.070 amortizado.
    Cap mensal: $5/workspace (alarme em telemetria — não implementado em
    Fase 2; lane futura junto com tier upgrade Anthropic).

  **Não entregue (escopo da Fase 2 declarado):**
  - Provisionamento de Redis (assumido pré-existente; reusa singleton de
    `events.py`; degrada para NoOp).
  - Ativação em prod — requer v2.9.1 (revisão de copy) + flip do env em
    deploy.
  - Cap mensal por workspace ($5 alarme) — telemetria registra `cost_usd`
    por chamada; agregação fica para lane futura.
  - Postgres+TTL fallback de cache (ADR-144 §2) — não necessário em deploy
    atual com Redis garantido.

  Hashes: `5a1142d` (C1 generator+cache+schema+prompts) · `c0a79df` (C2
  E5.N integração+orquestrador+adapter LiteLLM) · `d2b1827` (C3 frontend
  prefer-snapshot) · `93992c5` (C4 testes 18 backend + 3 frontend).

- **Report Premium UI v2.D.1 — `SnapshotChangelogBuilder` ✅ (2026-04-27):**
  Fundação determinística para os blocos `comparisons` e `changelog` que
  v2.1 plantou no [config/report_layout.yaml](../config/report_layout.yaml)
  com `enabled: false` + `deferred_until: "v2.D.1 SnapshotChangelogBuilder"`.
  v2.D.1 entrega o builder + adapter + tipos; v2.8 conecta no endpoint e
  flipa `enabled: true` (lane separada).

  **ADR:** [ADR-148 — `SnapshotChangelogBuilder`](DECISIONS.md#adr-148--snapshotchangelogbuilder-comparações-mês-a-mês-de-relatório)
  (renumerada de ADR-143 durante o merge: A7.6 ocupou ADR-143 com
  `docs/methodology/` é rules-as-code entre o branch base 2026-04-27 12:04
  e o rebase ~13:18). Decidiu storage = reuso de `pipeline_artifacts`
  (zero migration), granularidade por seção (5 default: S1/S2/S3/T2/T5),
  primeiro relatório → `null` no wire (não array vazio), narrativa via
  template determinístico (sem LLM — `delta_signal: Literal["up","down","stable"]`,
  threshold default `Decimal("0.5")` = 0,5%).

  **Estrutura:**
  - `pipeline/domain/types/snapshot_changelog.py`: dataclasses frozen
    `AnalyzeFinancesSnapshot`, `ComparisonItem`, `ChangelogEntry`,
    `ComparisonResult`, `SnapshotChangelogConfig`, `UnknownSectionError`.
    `delta_pct: Decimal | None` (None nos edges com zero).
  - `pipeline/domain/services/snapshot_changelog/{builder,narratives}.py`:
    `build_comparison(prev, curr, config) -> ComparisonResult` puro;
    `format_summary(item)` com 6 templates (`up`/`down`/`stable`/
    `from_zero`/`to_zero`/`both_zero`).
  - `backend/app/services/snapshot_pair_loader.py`: query SQLAlchemy
    `(workspace_id, stage IN ('analyze_finances','E5'), artifact_key=
    'analise_financeira', created_at < current)` ORDER BY DESC LIMIT 1
    (compat ADR-093). `analysis_hash = sha256(canonical_json(content))[:16]`
    derivada on-read, **não** persistida no DB.

  **Tests (18 verdes):** 8 goldens v2.D.1 cobrindo trade-off T1
  (`before==0`/`after==0`/`both_zero`) + 3 helpers/defesas em
  [`tests/test_snapshot_changelog.py`](../tests/test_snapshot_changelog.py)
  (sem `MagicMock` — fixtures puros nomeados); 7 integração SQLite em
  memória em [`backend/tests/test_snapshot_pair_loader.py`](../backend/tests/test_snapshot_pair_loader.py)
  (não mocado — CLAUDE.md §Testes), incluindo estabilidade do
  `_canonical_json` (chaves em ordem distinta → mesmo hash) e cobertura
  de formatos diversos do `periodo_dados`.

  **Boundary preservada:** `pipeline/**` não importa
  `fastapi`/`celery`/`sqlalchemy` (`dev/check_pipeline_boundaries.py`
  verde). Money sempre `Decimal` (ADR-090). 0 ofensores P1/P7 nos
  arquivos novos.

  **Débito aberto:** v2.D.1.1 (P2, ≤2h) — product-designer revisa copy
  dos 6 templates determinísticos antes de v2.8 flipar YAML.

- **A7.6 — Rules-as-code (lane aberta 2026-04-27 → ✅ entregue mesmo dia):**
  ver entrada acima com detalhes completos da entrega.

- **Report Premium UI v2.2b — fix `clickMode()` + 12 baselines Tático ✅ parcial (2026-04-27):**
  Resíduo da v2.2 fechado parcialmente — Tático populado, USA bloqueado
  por decisão de produto.

  **Diagnose:** `clickMode()` em `sections.snapshots.visual.spec.ts:77-83`
  retornava `false` silenciosamente para `/Tático/i` e `/USA|EUA/i` por
  dois motivos sobrepostos: (1) o toggle real é `ReportActions` (não o
  `ModeToggle` legado), com `<button role="tab">` envolto em
  `<TooltipTrigger>` — o label "Tático"/"EUA" fica fora do `<button>`,
  então `getByRole("button", { name: ... })` não casa; (2) modo `usa`
  foi removido de `VALID_MODES` em `adc3a15` (decisão de produto:
  ocultar USA temporariamente), então `?mode=usa` caía no default e a
  aba "EUA" também sumiu da UI.

  **Fix:** `setupReport(page, theme, mode)` aceita `mode` opcional e
  navega via deep-link `?mode=tatico|usa` em vez de click —
  `ReportModeProvider` já lê `searchParams.get("mode")` na montagem.
  `usa` re-incluído em `VALID_MODES` (apenas no `Set`; toggle UI
  permanece hidden — link compartilhável era a intenção do TEMP). Commit
  `d4e0dfe`.

  **Baselines Tático:** run [25002843680](https://github.com/davidrobert/mathoms/actions/runs/25002843680)
  com `gh workflow run CI -f run_visual=true -f update_visual_baselines=true`
  gerou 12 PNGs (T1-T6 × {light,dark}); copiadas do artefato
  `report-visual-baselines-generated` para
  `frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts-snapshots/`.
  Commit `029c3d9`.

  **USA pendente (8 baselines):** U1-U4 têm `enabled: false` em
  `config/report_layout.yaml` (commit `adc3a15`). `ReportShell` filtra
  por `enabledSections` antes de montar `<section>`, então as seções
  não existem no DOM nem em prod nem com mock. Re-habilitar no YAML
  mudaria runtime de produção (USA voltaria a aparecer); fora de
  escopo. Marcado `test.describe.skip()` com motivação inline; quando
  produto retomar, basta flip dos 4 `enabled: false` + remover TEMP em
  `ReportActions.VISIBLE_MODES` + trocar `skip` por `describe` + nova
  run `update_visual_baselines`. Helper já está pronto.

  **Regressão pre-existente fora de escopo:** 28 baselines estratégicas
  + APP + cover (commit `0558ea3` em 2026-04-26) "passavam" no run
  #24952539088 mas "skipam" em [25002843680](https://github.com/davidrobert/mathoms/actions/runs/25002843680)
  com `count() === 0` para `section#S1[data-report-section]`. Mesmo
  `setupReport()`, mesma URL — não causada por v2.2b. Commits
  candidatos: `db6cf6f` (cover identity v2.F.3b), `35eee5f` (Hero out
  of S1 v2.F.2), `a534e9d` (header refactor). Investigar em lane
  separada antes de re-rodar gate empírico.

- **Report Premium UI v2.4 — T2 Aportes seção real ✅ (2026-04-27):**
  Substitui stub "estará disponível…" de `T2AportesSection` por seção
  real, fechando o débito que a Fase 8 da v1 marcou ✅ embora T2 nunca
  tenha sido implementada. **Decisão D1=(a) MVP determinístico:** dados
  já existem em `dashboard.aportes` (status por destino, meta,
  valor_feito) + `dashboard.investimentos_delta` (variação por bloco)
  do snapshot E5 — paridade com `EXEMPLO_DE_RELATORIO.html:1477-1484`
  (`dash-aportes`); zero mudança de pipeline/backend/endpoint.

  Render: KPI strip (5 slots: destinos, concluídos, total realizado,
  meta, % cobertura), grade de cards (1 por aporte com badge
  OK/Pendente, valor efetivo vs meta) e tabela "Variação Patrimonial
  por Bloco". Conclusion lê `narrativas[t2_aportes].conclusion` (E5.N
  LLM) com fallback determinístico.

  Tipos novos em
  [`frontend/src/types/report-analysis.ts`](../frontend/src/types/report-analysis.ts):
  `AporteItem`, `InvestimentoDeltaItem`, `DashboardData` (subset
  tipado, mantém `[key: string]: unknown` para chaves consumidas por
  T1/T3/T5). Adapter puro em
  [`frontend/src/components/report/utils/aportesAdapter.ts`](../frontend/src/components/report/utils/aportesAdapter.ts):
  `deriveAporteSummary` + `deriveInvestimentosDelta`. YAML
  [`config/report_layout.yaml`](../config/report_layout.yaml) T2
  declara `cards: [aportes_status, investimentos_delta]` (eram `[]`)
  + codegen TS/py atualizado.

  Tests: 5 casos novos em `dataAdapters.test.ts` + 4 em
  `taticoSections.test.tsx`; vitest 655 passed. Money sempre via
  `<MonetaryValue/>` (ADR-090). Funções TS ≤20 linhas (extração de
  helper `summarize()` no adapter para honrar code-style baseline).
  Commits: `0805a87` (feat) + `38aa0ee` (refactor honrando 20 linhas).

- **v2.10 ✅ PDF visual diff em Playwright (2026-04-27):** spec novo
  [`frontend/tests/e2e/reports/print.@critical.spec.ts`](frontend/tests/e2e/reports/print.@critical.spec.ts)
  renderiza `/reports/[id]?print=1` via CDP `Page.printToPDF()` (paridade
  com [`backend/app/services/pdf_renderer.py:109`](backend/app/services/pdf_renderer.py):
  A4 portrait, margens 15/12/15/12mm, `printBackground: true`), converte
  primeira página em PNG via `pdf-to-png-converter@^3.18.0` e compara
  contra baseline em
  [`frontend/tests/e2e/reports/__snapshots__/report.print.pdf.png`](frontend/tests/e2e/reports/__snapshots__/)
  usando `pixelmatch@^7.1.0` + `pngjs@^7.0.0` com tolerância
  `maxDiffPixels: 500`. **Por que PNG e não diff binário do PDF:** PDFs
  carregam timestamps + IDs de objetos que mudam por geração, gerando
  ~100% diff binário no mesmo render visual. **Job CI dedicado**
  `frontend-print-visual` em [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
  opt-in via label `print` (PR) ou `workflow_dispatch run_print=true`
  (paridade com `frontend-visual`); 2 inputs novos: `run_print` +
  `update_print_baseline`. Job fora do `all-green needs` — não bloqueia
  merge default; gate é deliberado. Spec faz skip silencioso fora de
  Chromium (CDP `Page.printToPDF` é Chrome-specific) e quando deps
  PDF→PNG não estão presentes (caminho de degradação para job
  cross-browser não rodar este spec por engano). Baselines
  OS-específicas (Linux/CI runner). **Gate empírico validado** via
  branch descartável `agent/test-print-visual-gate-throwaway/20260427-1212`
  (commit `19a79c7` — muda `@page margin: 15mm 12mm` → `25mm 22mm` em
  [report-print.css](frontend/src/components/report/report-print.css):
  CI run `25003234190` job `frontend-print-visual` falhou conforme
  esperado em `expect(diffPixels).toBeLessThanOrEqual(500)`. Branch
  fechada sem merge logo após. Run de baseline-generation:
  `25003003442` (job `73218060762`, conclusion=success). Refs:
  [REPORT_PREMIUM_PLAN.md §11.1](REPORT_PREMIUM_PLAN.md) ·
  [track_report_v2.md §3 v2.10](agent_prompts/track_report_v2.md).

- **Auditoria multi-agente 2 rodadas — drift cleanup + unificação metodológica ✅ (2026-04-27):**
  Auditoria executada por 3 especialistas (senior-cto + product-designer + financial-planner)
  em duas rodadas (~150 itens). Entregas em 3 commits:
  - **`ae67141`** — drift técnico pós-ADR-129/131/A6c + sincronização Sprint A6→A7 (16 fixes em 15 arquivos):
    endpoint `/full`→`/data` em RUNBOOK; `analysis_json_path`→`analysis_artifact_id` em
    ARCHITECTURE/PIPELINE_ARTIFACTS (ADR-131); `POST /api/pipeline/run`→`/api/v1/pipeline/runs`
    em ARCHITECTURE; ADR-076→ADR-078 em refs (4×); 32 anchor links broken corrigidos em DECISIONS;
    SMOKE_TEST §5 e SMOKE_TEST_HUMAN A3.5 reescritos sem iframe/HTML/E6; CANONICAL_ENGINE_P0 +
    P1_STRUCTURAL_PLAN sem refs E6; SETUP `_scratch`→`dev/`; BACKLOG F8 Growth→F10 Growth;
    Sprint A7 marcada como atual; senior-cto.md briefing ADRs 076–latest; TESTING.md
    bullets MaterializationBridge marcados como histórico (A6c).
  - **`ea22837`** — unificação metodológica (17 arquivos, +862/-106; **batch2.1 ✅**):
    Score Financeiro com fonte única em `scoring.json` (escala 0-10, 5 critérios com fontes
    Perini/Cerbasi/AUVP); `methodology.md §SCORE` reescrito como referência ao JSON;
    `methodology_template.md` reescrito sem componente fantasma. Reserva de emergência
    canônica em `FORMULAS.md` + `methodology.md §RESERVA` + `scoring.json:reserva_emergencia`
    com `_definicao` + `_base_calculo` (custo essencial trimestral, meses_alvo por perfil de renda).
    Composição patrimonial: cat_5 sempre presente, dois conceitos de investível
    (financeiro vs total + efetivo via toggle `imoveis_no_if`); `goal.if.schema.json` v1→v2
    com `renda_passiva_atual_mensal_brl` + `if_meta_bruta_brl/liquida_brl`;
    `goal.alocacao_alvo.v2.schema.json` criado (7 classes AUVP + KPI desvio).
    AUVP corretamente caracterizada (Diagrama do Cerrado + rebalanceamento por aporte).
    `categorization.json` ABDO MOHAMED → saúde + `_keyword_collisions` documenta risco EINSTEIN.
    `COPY_GUIDELINES.md` reescrito (12 seções, glossário 28 termos, decisão IF graduada,
    formato monetário, anti-padrões); pointers em `report_spec.md` + `methodology.md` + `I18N_PLAN.md`.
    `agent_prompts/README.md` reforça fonte única de status no BACKLOG.
  - **(este commit)** — fixes de regressão da rodada 2:
    `methodology.md:119` `analysis_json_path` → `Report.analysis_artifact_id` (drift introduzido em ea22837);
    `methodology.md:161` `score.py` → `financial_score_calculator.py` (drift idem);
    `definitions.md` validação `if_gap` corrigida (era falsa acima da meta — `MAX(0, ...)`);
    invariante anti-dupla-contagem documentada para `imoveis_no_if` × `renda_passiva_atual`.
    BACKLOG marca `batch2.1 — Expandir FORMULAS.md` como ✅ (era ☐).

- **CI fix — Vitest hang em `ReceitaDespesaMensalChart.test.tsx` ✅ (2026-04-27):**
  Conserto definitivo do hang que cancelou o CI Frontend Vitest em 10min
  desde v2.E.6 (commit `6b09407`). Substitui o workaround
  `.slow.test.tsx` aplicado em `10bf48b`/`fd1f1fd` (também 2026-04-27).
  **Causa raiz:** o mock de `react-chartjs-2` em
  [ReceitaDespesaMensalChart.test.tsx](frontend/tests/components/report/ReceitaDespesaMensalChart.test.tsx)
  construía um `fakeChart` **novo a cada render** e invocava
  `props.ref?.(fakeChart)` no corpo do componente.
  [`ChartCanvas.setRef`](frontend/src/components/report/charts/primitives/ChartCanvas.tsx)
  faz short-circuit por igualdade de **referência** (`if (chartRef.current === chart) return`) —
  como cada render produzia objeto novo, `onChartReady`
  (`setChartInstance`) disparava a cada render, novo render gerava novo
  `fakeChart`, infinite render loop. Por isso testes isolados via `-t`
  passavam em <1s (1 render apenas) e o file inteiro hangava — qualquer
  teste que renderizasse o chart caía no loop.

  **Fix:**
  - `fakeChart` movido para `vi.hoisted` (singleton estável entre
    renders); o short-circuit em `ChartCanvas.setRef` agora bate.
  - Entrega do ref deferida para `useEffect` (pós-commit) em vez de
    chamada síncrona no corpo do mock — evita warning React "Cannot
    update a component while rendering a different component".
  - `beforeEach` reseta `chartUpdate.mockClear()` +
    `datasetMeta.length = 0` (cleanup antes manual em 1 teste).

  **Reversão do workaround:**
  - `git mv ReceitaDespesaMensalChart.slow.test.tsx ...test.tsx`.
  - `vitest.config.ts` — removido `"tests/**/*.slow.{test,spec}.{ts,tsx}"`
    do `exclude`.
  - `vitest.slow.config.ts` — deletado (era infra exclusiva do workaround).
  - `package.json` — script `test:slow` removido.

  **Validação:** 15/15 tests do file passam em 1.17s; suite Vitest
  completa **55 files / 646 passed + 1 skipped em 43.15s** (era cancelled
  em 10min). Sem regressões em outros test files.

- **Report Premium UI v2 — v2.7 DnD real Kanban ✅ (2026-04-27):**
  Fecha o **débito #1 do BACKLOG** (declarado pré-v2:
  `@dnd-kit/core` não foi adicionado à v1; primitivo Kanban usava
  botões "→ Coluna X" em vez de drag-and-drop). Lane v2.7 instala
  `@dnd-kit/core@^6.3.1` (42KB minified / 13KB gzipped — bem abaixo
  dos 50KB do gate de bundle do prompt) e refatora
  [Kanban.tsx](frontend/src/components/report/ui/kanban/Kanban.tsx)
  para usar `DndContext` + `useDraggable` (cards) + `useDroppable`
  (colunas). API `onMove(id, to)` preservada — `TaticoSections.tsx`
  não muda; o handler `onDragEnd` chama o mesmo callback quando o
  card é solto sobre uma coluna diferente.

  **Decisões:**
  - **`@dnd-kit/sortable` NÃO instalado.** O escopo desta lane cobre
    apenas drag entre colunas (cross-column moves), que é o caso de
    uso de `onMove(id, to)`. Reordenação dentro da mesma coluna
    (campo `ordem` do backend) ficaria mais natural com sortable, mas
    exige extensão da API (`onReorder?` callback novo) e mudança em
    TaticoSections para fazer PATCH de `ordem`. Conservadorismo: o
    handler em `Kanban.tsx` checa `item.coluna === target` e retorna
    sem chamar `onMove` — drag intra-coluna é no-op (Vitest +
    Playwright validam).
  - **Fallback mobile via CSS media query.** Botões "→ Coluna" agora
    ficam em `data-kanban-move-buttons`. Em viewports `≥768px`
    (`globals.css` regra adicionada), `display: none !important`
    esconde os botões — DnD mouse é a interação primária. Em
    `<767px`, os botões aparecem (long-press em touch é problemático
    com scroll natural). Trade-off documentado em comentário CSS +
    docstring do componente.
  - **`activationConstraint: { distance: 6 }`** em `useSensor(PointerSensor)`
    evita drag acidental ao clicar nos botões de fallback (3px
    movimento espontâneo do dedo não dispara drag).

  **Validação:**
  - 3 specs Vitest novos em `tests/components/report/uiPrimitives.test.tsx`:
    drop zones renderizados; cards com `data-kanban-item`; sem onMove
    não renderiza botões de fallback. Mais 1 spec atualizado (caminho
    botão clicável continua chamando `onMove`).
  - Playwright `@critical` em
    `frontend/tests/e2e/reports/kanban.@critical.spec.ts`:
    drag de "A fazer" → "Em andamento" emite PATCH com `coluna:
    em_andamento`; drag dentro da mesma coluna NÃO emite PATCH.
    Roda em CI opt-in via label `e2e` (workflow `frontend-e2e` —
    cross-browser).
  - Vitest 36 tests pass localmente (uiPrimitives 29 + taticoSections 7
    — superfície tocada por v2.7); tsc clean em `src/`; pre-commit verde.

  **Hang RDM em CI Vitest:** o run `24998747289` cancelou em 10min no
  job "Frontend unit + integration (Vitest)" por hang em
  `tests/components/report/ReceitaDespesaMensalChart.test.tsx`
  (introduzido em `6b09407`, v2.E.6, 2026-04-26 — pré-existe v2.7).
  Workaround aplicado em `10bf48b`/`fd1f1fd` (rename `.slow.test.tsx` +
  exclude do glob default) substituído pelo fix definitivo descrito no
  bullet "CI fix — Vitest hang…" acima.

- **Report Premium UI v2 — v2.6 `cards/` cleanup ✅ (2026-04-27):**
  Auditoria pós-v1 (2026-04-25) classificou
  `frontend/src/components/report/cards/` como "pré-Fase 3" e propôs
  três caminhos: (a) migrar para `ui/`; (b) deprecar como wrappers;
  (c) aceitar legacy. A lane reabriu com evidência empírica e a
  decisão final é **(c) refinada** — `cards/` é a **camada
  section-composer** legítima entre primitivos `ui/`
  (`Alert`/`Badge`/`Kpi`/`ScoreCard`/`Timeline`/…) e `sections/`
  (`S1`–`S10`). Todos os 14 cards já consomem o primitivo canônico
  `ReportCard`; carregam lógica de domínio atrelada a shapes
  específicos do DTO (`PatrimonioData`,
  `OrcamentoProspectivoData`, `EquilibrioCerbasiData`…) e
  pertencem a esta camada por design.

  **Cleanup entregue:**
  - `cards/_registry.ts` (com `MIGRATED_CARD_IDS` morto + nomenclatura
    F2.A obsoleta da migração v1) → `cards/index.ts` (barrel padrão
    com docstring de fronteira de camada + instrução explícita "não
    migrar para `ui/`");
  - 6 consumidores (`S1PatrimonioSection`, `S2FluxoCaixaSection`,
    `S3InvestimentosSection`, `S7IndependenciaSection`,
    `S10SinteseSection`, `ReportShell`) passam a importar pelo barrel
    (`from "../cards"`) em vez de cada arquivo individual;
  - `cards/PontosFortesList` → `cards/PontosFortesCard` (rename)
    resolve colisão de nome com `ui/PontoForteItem::PontosFortesList`
    (este último é primitivo `<ul>` com children; o card recebe
    `pontos: PontoForte[]` do DTO e wrappa em `ReportCard`);
  - `cards/PontosUrgentesList` → `cards/PontosUrgentesCard` por
    simetria;
  - decisão arquitetural registrada em
    [REPORT_PREMIUM_PLAN.md §17.9](REPORT_PREMIUM_PLAN.md) com
    diagrama das camadas (`sections/` → `cards/` → `ui/` →
    `ReportCard`).

  **Zero mudança visual.** Apenas reorganização de imports + 2
  renames + docs. Vitest + pre-commit verdes; tsc clean em `src/`
  (erros pré-existentes em `tests/` são unrelated).

  **Não escopo (deferido):** dedup de
  `report/PeriodToggle.tsx` (legado, encaixa em `headerRight` de
  `ReportCard`) vs `ui/PeriodToggle.tsx` (v2.E.1, segmented control
  acima de chart) — APIs distintas com propósitos legítimos
  diferentes; eventual dedup vai para v2.6b/v3. `lib/periodUtils.ts`
  e `hooks/usePeriodTransactions` ficam intocados (servem caso de
  lista bruta de `TransactionItem[]`, não competem com
  `report/hooks/usePeriodWindow` da v2.E.1).

- **Report Premium UI v2 — Onda E (Charts UX) ✅ 8/8 (2026-04-26):**
  Onda E fechou a migração Recharts→Chart.js dentro de `/reports/**`
  que [ADR-117](DECISIONS.md#adr-117--report-premium-ui-baseline-paridade-com-exemplo_de_relatoriohtml)
  Fase 2 abriu mas Fase 7 não fechou. **8 sub-lanes** documentadas em
  [track_report_v2_charts_ux.md](agent_prompts/track_report_v2_charts_ux.md);
  duas levas paralelas (3+4 agentes simultâneos em worktrees
  isoladas) + closeout sequencial; todas mergeadas em main no mesmo
  dia. Decisão consolidada em
  [ADR-139](DECISIONS.md#adr-139--finalização-migração-recharts→chart.js-em-reports).

  **Leva 1 (3 agentes paralelos):**
  - ✅ **v2.E.1** — `PeriodToggle` UI primitive + hook `usePeriodWindow`
    (commit `da841c2`). Segmented control 3M/6M/12M/Ano portado para
    tokens (`--brand-primary`, `--surface-card`, `--surface-border`),
    paridade `EXEMPLO_DE_RELATORIO.html:381-413`. Hook puro suporta
    formato `"YY/MM"` e `"mes/aa"` pt-BR. 16 specs Vitest (10 hook + 6
    componente) em `frontend/tests/components/report/` (config vitest
    exige). Enabler de v2.E.3/E.4/E.5.
  - ✅ **v2.E.2** — TS types `receita_datasets`/`despesa_datasets`
    em `FluxoCaixaSummary` (commit `8ee4bd6`). Tipo `ChartSeries` em
    `frontend/src/types/chart-series.ts` (separado de
    `primitives/types.ts::ChartSeries` para evitar colisão).
    **Divergência registrada:** backend hoje só emite `{label, data}`
    por dataset; `backgroundColor`/`stack`/`borderRadius` opcionais —
    enriquecimento client-side fica em E.4-E.6. Enabler de
    v2.E.4/E.5/E.6.
  - ✅ **v2.E.7** — `ScoreCard` premium plugado em S1 + score top-level
    no DTO + backend `score.context`/`score.conclusion` (commits
    `55f00fa` + `22ca7d0` + `334f5f7` + `529cd70`). **Absorve v2.5**
    (score-dto). `S1PatrimonioSection` consome `<ScoreCard/>` (era
    `<ScoreGaugeChart/>` Recharts); `ScoreCardProps` ganhou `context?`
    e `conclusion?` com classes CSS `chart-context`/`chart-conclusion`.
    Backend `financial_score_calculator` agora emite `breakdown`
    (renomeado de `componentes` — peso normalizado fração [0..1] +
    `contribuicao` calculada), `formula`, `context`, `conclusion`.
    Templates Python determinísticos paridade
    `EXEMPLO_DE_RELATORIO.html:1809-1811`; top-2 drivers em `conclusion`
    ranked por `contribuicao`. Frontend prefere
    `narrativas[score_gauge]?.conclusion` (E5.N LLM) sobre
    `score.conclusion` (template) — alinhamento com
    [ADR-122](DECISIONS.md#adr-122--chart_conclusions-e-section_summaries-em-modo-híbrido-template--llm).
    `ScoreGaugeChart.tsx` deletado; `_registry.ts` limpo. Vitest 593
    passed; `pytest tests` 1470; `pytest backend/tests` 1324. Zero
    `as ScoreData` ou `ScoreGaugeChart` em `frontend/src/`.

  **Leva 2 (4 agentes paralelos simultâneos):**
  - ✅ **v2.E.3** — `FluxoMensalChart` Recharts→Chart.js stacked +
    `PeriodToggle` + `usePeriodWindow` (commit `5b8d54a`). 7 specs
    Vitest novas (5 chart + 2 hook); 610 testes passed; pre-commit
    verde. **Side-effect positivo:** criou
    `frontend/src/components/report/hooks/useIsPrint.ts`
    (`matchMedia("print")` + listener SSR-safe) — reaproveitado por
    E.4/E.5/E.6.
  - ✅ **v2.E.4** — `ReceitaBarChart` Recharts→Chart.js horizontal +
    `PeriodToggle` (commit `0e07499`). Consome `receita_datasets[]`
    somando dentro da janela escolhida; ordenação desc por total;
    paleta estável via `pickColorByIndex`; 9 specs Vitest; 628 testes
    passed. **Hotspot resolvido:** commit `d2ae024` (helper duplicado)
    foi **dropado durante rebase** após v2.E.5 entrar primeiro com
    função idêntica — protocolo CLAUDE.md §Hotspots funcionou
    automaticamente.
  - ✅ **v2.E.5** — `DespesasDoughnutChart` Recharts→Chart.js +
    datalabels + `PeriodToggle` (commit `6d0ab67`). Consome
    `despesa_datasets[]` somando por janela; datalabels `R$ Xk` para
    fatias ≥5%; `cutout: '50%'`; fallback gracioso em
    `despesas_por_categoria` agregado quando datasets ausentes (toggle
    oculto nesse caminho); 9 specs Vitest; 612 testes passed.
    **Side-effects positivos:** (a) criou helper `pickColorByIndex`
    em `_shared.ts` (módulo 12, estável por índice — reutilizado por
    E.4/E.6); (b) `ChartDonut` primitive ganhou prop opcional
    `dataLabelFormatter(value, pct, label)` + `textStrokeColor`/
    `textStrokeWidth` (extensão aditiva, backwards-compat).
    **Conflito resolvido:** rebase em `useIsPrint.ts` adotou versão
    canônica de E.3 já em main.
  - ✅ **v2.E.6** — `ReceitaDespesaMensalChart` Recharts→Chart.js
    stacked + slide window 12m + tooltip por stack + legenda agrupada
    custom + Vitest + E2E Playwright `@critical` (commits `6c2efc4` +
    `f8cb30f` + `6b09407` + `32089ce` + cleanup `d9fa765` + baseline
    `358d5ea`). Bar empilhado com 2 stack groups (`receita`/`despesa`),
    enriquecimento client-side de `backgroundColor` via
    `pickColorByIndex` e `stack` derivado do array de origem; slide
    window 12m com prev/next + dots (oculto se ≤12m); tooltip custom
    apenas do stack hovered (title/body/footer paridade
    `EXEMPLO_DE_RELATORIO.html:7798-7829`); `RDMLegend.tsx` (legenda
    agrupada Receitas/Despesas, swatches clicáveis com
    `data-legend-swatch`/`aria-pressed`); chart-context +
    chart-conclusion auto-gerados; print mode oculta nav/legenda
    interativa, fixa última janela 12m, renderiza bloco textual de
    totais consolidados; `ChartCanvas` ganhou prop
    `onChartReady?(chart)` opcional (extensão aditiva).
    **Anomalia aprendida:** agente pulou gates locais (worktree sem
    `node_modules`/`pre-commit`) e confiou no CI como gate efetivo →
    2 funções TS >20 linhas detectadas pós-merge na branch principal
    (`useEnrichedDatasets` 26 linhas, `buildOptions` 25 linhas) →
    cleanup follow-up `d9fa765` extraiu helpers
    `enrichSeriesForStack` e `formatMoneyAxisTick` (sem mudança de
    comportamento) + baseline atualizado em `358d5ea`. Lição para
    futuros prompts: exigir gate local ou explicitar fallback quando
    `node_modules` indisponível.

  **Closeout sequencial:**
  - ✅ **v2.E.8** — cleanup imports Recharts em `_registry.ts`
    (header atualizado refletindo Chart.js 4 + Recharts intencional
    para `WaterfallIfChart`/`PatrimonioDoughnutChart`); ADR-139
    "Finalização migração Recharts→Chart.js em /reports/**" gravada
    em main relacionando-se a ADR-037, ADR-076, ADR-117, ADR-122;
    BACKLOG/CHANGELOG sincronizados. Verificação por grep: `from
    "recharts"` em `frontend/src/components/report/charts/` retorna
    apenas os 2 charts intencionais. **Re-baseline visual delegada
    ao operador humano:** workflow `frontend-visual` opt-in
    (`gh workflow run CI -f run_visual=true
    -f update_visual_baselines=true`) exige permissão `gh` ausente
    do sandbox do agente; baselines esperadas mudarem: cover×2 +
    S1×2 + S2×2 = 6 PNGs; restantes (40 PNGs S3-S10/T*/U*/APP_*)
    idênticos.

  **Coordenação de hotspot empiricamente validada** entre os 4
  agentes paralelos da Leva 2:
  - `useIsPrint.ts` — E.3 venceu (criou primeiro); E.4/E.5/E.6
    convergiram via rebase.
  - `pickColorByIndex` em `_shared.ts` — E.5 venceu; E.4 detectou
    duplicação idêntica no rebase e dropou commit (sem perda).
  - `ChartCanvas.tsx` — E.6 fez extensão aditiva (`onChartReady?`)
    sem conflito.

  **Bonus colateral:** T5_ts_hex_colors baseline -2 (4 migrations
  removeram hex literals em favor de tokens `var(--brand-*)`/
  `pickColorByIndex`).

  **Fora de escopo (preservado intencionalmente — eventual v2.E.9):**
  `WaterfallIfChart.tsx` e `PatrimonioDoughnutChart.tsx` continuam em
  Recharts. Recharts permanece também em
  `frontend/src/components/charts/Mathom*.tsx` e
  `frontend/src/app/(app)/dashboard/_components/`
  ([ADR-037](DECISIONS.md#adr-037--recharts-para-charts) com escopo
  restringido).

- **A7.3 Catalog + Override resolver (categorization + institutions) — ✅ entregue (2026-04-27):**
  Sprint A7 · Onda 3 · única lane · serial após A7.1 mergeada. Implementa
  [ADR-137](DECISIONS.md#adr-137--catalog--override-resolver-para-categorization-e-institutions):
  storage explícito de **template global versionado** (`category_templates`)
  + **overrides por workspace** (`workspace_category_overrides`, somente
  diff). `institutions.json` vira tabela global `institution_catalog`
  (sem override por workspace nesta lane).

  **Entregas (8 commits):**
  - **Models** (`backend/app/models/category_template.py`,
    `institution_catalog.py`): `CategoryTemplate` (template_version + key
    UNIQUE), `WorkspaceCategoryOverride` (UNIQUE workspace_id + template_key),
    `InstitutionCatalog` (code UNIQUE). `monthly_cap_brl_cents` em
    `BigInteger` (ADR-090, money nunca float). `default_keywords`/
    `keywords_override` em `JSON` (SQLite-friendly).
  - **Alembic chain (4 migrations chained):**
    - `aa1b2c3d4e5f` — DDL das 3 tabelas com índices + UNIQUE constraints.
    - `a5b6c7d8e9f0` — seed `category_templates` v1: 16 expense + 8 income
      categories + 1 row reservada `__categorization_metadata__` carregando
      `pj_source_mapping`/`clt_source_mapping`/`internal_transfer_patterns`/
      `one_time_income_*`/`qa_investigation_patterns` em `metadata_json`.
    - `b6c7d8e9f0a1` — seed `institution_catalog`: 17 instituições com
      categoria heurística (bank/broker/exchange/fintech/government/
      real_estate/employer).
    - `d8e9f0a1b2c3` — backfill `workspace_category_overrides` a partir de
      `categories` rows existentes; cria override SOMENTE onde diverge do
      template (label/keywords/cap). Float→cents (ADR-090). Não dropa
      tabelas legadas (A7.5 cleanup).
  - **Resolver** (`backend/app/services/category_resolver.py`):
    `resolve_categories(workspace_id, db)` → `list[ResolvedCategory]`
    frozen dataclass (key, label, category_type, keywords, monthly_cap_brl_cents,
    sort_order, parent_key, disabled). Cache Redis em
    `category_cache.py` com invalidação ativa por evento (sem `@lru_cache`,
    ADR-111). Falha aberta sem Redis. `get_categorization_metadata(db)`
    retorna o blob auxiliar do row reservado.
  - **Institution resolver** (`backend/app/services/institution_resolver.py`):
    `resolve_institutions(db) -> InstitutionsCatalog` cached.
  - **Repositories** (`category_template_repository.py`,
    `workspace_category_override_repository.py`,
    `institution_catalog_repository.py`): sync para template/catalog,
    async para override CRUD; upsert idempotente respeita UNIQUE.
  - **DBConfigStore wiring** (`backend/app/services/db_config_store.py`):
    `get_categorization` delega ao resolver com fallback legado para
    paridade pré→pós cutover. `get_institutions` lê do
    `institution_catalog` global. `build_config_overrides_from_db`
    monta `categorization.json` do worker boundary com expense/income
    keywords + auxiliary metadata; `institutions.json` vem do catálogo
    global.
  - **API** (`backend/app/api/category_overrides.py`): 4 endpoints novos
    com `response_model` Pydantic (ADR-102 R18) sob
    `/workspaces/{id}/config/category-overrides`:
    - `GET .../resolved` — lista template+overrides mergeados.
    - `PUT .../{template_key}` — upsert override (cria/atualiza diff).
    - `DELETE .../{template_key}` — desabilita (`override.disabled=True`).
    - `POST .../{template_key}/reset` — apaga override → volta ao default.
    Endpoints legados em `/categories` mantidos intactos para compat
    com frontend; A7.5 migrará frontend e removerá os legados.
  - **Tests (68 specs novas):** `test_category_resolver.py` (17),
    `test_institution_resolver.py` (5),
    `test_workspace_category_override_repository.py` (8),
    `test_db_config_store_categorization_a73.py` (7),
    `test_category_overrides_api.py` (10),
    `test_pipeline_adapter_a73.py` (5),
    `test_a73_seed_migrations.py` (16). Fakes nomeados
    (`FakeRedisClient`) — sem `MagicMock` inline (CLAUDE.md §Testes).

  **Gates:** `pre-commit run --all-files` ✅ · `pytest backend/tests -q`
  1488 passed / 5 skipped ✅ · `pytest tests -q` 1570 passed / 2 skipped
  ✅ · `make update-openapi-snapshot` + `update-db-schema-reference`
  comitados ✅ · `alembic upgrade head` em SQLite fresco produz 25
  category_templates rows + 17 institution_catalog rows + paridade com
  legacy `categories` (resolver fallback até A7.5).

  **Coordenação cross-lane:**
  - **A7.5 desbloqueada:** Onda 4 cleanup (`git rm config/*` + remoção
    de bridges) agora pode rodar.
  - **Risco de drift quando template renomear key:** ADR-137 §Decisão
    documenta proibição de rename de `template_key` (só add/deprecate);
    rename de key implicaria nova `template_version` + migration de
    overrides — fora do escopo desta lane.

- **A7.4 Metodologia → `docs/methodology/` — ✅ entregue (2026-04-27):**
  Reorganização editorial: 4 arquivos de documentação humana movidos de
  `config/` para `docs/methodology/` (Sprint A7 · Onda 2 · paralelo livre ·
  CONFIG_CUTOVER_PLAN.md §5.4). Histórico preservado via `git mv` (rename
  detection 99-100%). Lane independente — não bloqueia nem é bloqueada
  por nenhuma outra A7.

  **Entregas (5 commits):**
  - `git mv` de `config/{definitions,regras_composicao_patrimonial,
    source_hierarchy,milhas}.md` → `docs/methodology/`. `definitions.md`
    teve auto-referência interna a `regras_composicao_patrimonial.md`
    atualizada para o novo path.
  - `docs/methodology/README.md` — index editorial (1 linha por arquivo).
  - `scripts/e5_analyze.py` — `CONFIG_MILHAS` agora aponta para
    `docs/methodology/milhas.md` (esse é o único arquivo *parseado*
    em runtime via `parse_milhas_md` para o card de milhas em E5; demais
    são referência humana). `CONFIG_DEFINITIONS` atualizado por
    consistência (declarado mas não lido).
  - `scripts/e7_review.py`, `scripts/e4_categorize.py`, `scripts/e_reset.py` —
    paths/comments alinhados.
  - `backend/tests/test_config_materializer.py` — assertion de
    `definitions.md` em config materializado removida (arquivo não está
    mais em `config/`, materializer não copia).
  - `CLAUDE.md §Fontes de verdade` — entrada `definitions.md` aponta para
    `docs/methodology/`.
  - `.claude/agents/financial-planner.md` — link Read atualizado.
  - `docs/COPY_GUIDELINES.md` (§2 + §11), `docs/REPORT_PREMIUM_PLAN.md`
    (§0.3), `docs/ARCHITECTURE.md` (tree §10), `config/report_spec.md`
    (3 hits) — paths cross-doc atualizados.
  - `dev/check_forbidden_paths.py` + `dev/commit.py` — 4 paths antigos
    bloqueados em `FORBIDDEN_FILES` (defesa contra rebase regressivo).

  **Gates:** `pre-commit run --all-files` ✅ · `pytest backend/tests -q`
  1350 passed / 4 skipped ✅ · `pytest tests -q` 1495 passed / 2 skipped
  ✅ · `grep -rn 'config/{definitions,regras_composicao,source_hierarchy,milhas}'`
  retorna apenas as entradas legítimas em `dev/*.py` (block list).

- **A7.2b Tabelas globais `fiscal_parameters` + `market_rates` versionadas — ✅ entregue (2026-04-27):**
  Onda 2 (paralela com A7.1, A7.2a, A7.4): séries fiscais e cotações de
  câmbio agora são **tabelas globais com vigência temporal** (não mais
  `parametros_fiscais.json`/`taxas.json` em disco). Reproducibilidade
  histórica garantida — relatório de fev/2025 usa parâmetros de 2025
  mesmo quando regerado em 2027.

  **Entregas (6 commits):**
  - `backend/app/models/fiscal_parameter.py` + `market_rate.py` — modelos
    SQLAlchemy: `fiscal_parameters` (id, year, ir_brackets JSON,
    pgbl_limit_brl_cents BigInt, inss_ceiling_brl_cents BigInt,
    lucro_presumido_aliquota DECIMAL(5,4), effective_from/to,
    source) + `market_rates` (pair, rate DECIMAL(20,10),
    observed_at, source, UNIQUE(pair, observed_at)).
  - `backend/alembic/versions/x2y3z4a5b6c7_*` — migration cria as duas
    tabelas (idempotente, offline-mode-safe).
  - `backend/alembic/versions/y3z4a5b6c7d8_seed_*` — data migration
    materializa snapshot de `parametros_fiscais.json` para 2024/2025/2026
    + `taxas.json` para `today` e bootstrap em `2024-01-01` (impede
    `MarketRateNotFound` em relatórios históricos).
  - `backend/app/repositories/fiscal_parameter_repository.py` — lookup
    por vigência (`effective_from <= start AND (effective_to IS NULL OR
    effective_to >= end)`); raise `FiscalParameterAmbiguous` em overlap
    mid-year + `FiscalParameterNotFound` em miss.
  - `backend/app/repositories/market_rate_repository.py` —
    `get_latest_on_or_before(pair, observed_at)` retorna última cotação
    conhecida na data ou antes (regra ADR-135).
  - `backend/app/services/fiscal_cache.py` — cache Redis (chaves
    `fiscal:y={year}` TTL 1h fallback + `market:p={pair}:d={iso}` TTL 30d
    immutable). Sem `@lru_cache` em processo (ADR-111). Falha aberta:
    Redis down → DB direto.
  - `backend/app/services/db_config_store.py` — `get_fiscal_for_period`
    e `get_market_rate` saem de `NotImplementedError` (A7.0 stubs) e
    delegam aos repositórios + cache.
  - `pipeline/adapters/fiscal_parsers.py` — conversões row ↔
    `FiscalParameters` typed dataclass + bridge legacy JSON.
  - `pipeline/adapters/file_config_store.py` — `get_fiscal_for_period` /
    `get_market_rate` lêem dos JSONs legados via `legacy_json_to_fiscal`
    (bridge até A7.5; vigência fina ignorada — apenas year-bound).
  - `pipeline/domain/services/previdencia_analyzer.py` —
    `PrevidenciaConfig.from_fiscal_parameters(fiscal: FiscalParameters)`
    constrói config a partir do dataclass typed; `from_fiscal(dict)`
    permanece como fallback legacy.
  - `pipeline/domain/services/cenarios_conjuge_analyzer.py` —
    `from_configs` aceita `cambio_usd_brl: Decimal` typed com prioridade
    sobre `taxas` dict.
  - `pipeline/domain/services/e5_analyzer_adapter.py` — `from_configs`
    ganha kwargs `fiscal_parameters` e `cambio_usd_brl` (prioridade
    sobre dicts legacy).
  - `scripts/e5_analyze.py:_e5_build_adapter(life_plan, ctx)` —
    quando `ctx.config_store` disponível, resolve via
    `get_fiscal_for_period(year_start, year_end)` +
    `get_market_rate("USD/BRL", TODAY)`. Fallback warn-only se DB miss.

  **Testes (49 specs novos):**
  - `backend/tests/test_fiscal_market_repos.py` (16) — repos isolados +
    overlap → ambíguo, miss → not found, UNIQUE constraint.
  - `backend/tests/test_db_config_store_fiscal.py` (14) — DBConfigStore
    typed return + cache key shape + fake redis round-trip + invalidação.
  - `tests/unit/pipeline/test_fiscal_parsers.py` (10) — row → payload →
    dataclass round-trip + legacy JSON bridge.
  - `tests/unit/pipeline/test_a72b_typed_inputs.py` (9) — typed
    constructors dos analyzers + fallback dict legacy.
  - 2 specs A7.0 atualizados em `test_config_store_protocol.py` (stubs
    `NotImplementedError` → bridge real).

  **Acceptance gates batidos:**
  - ✅ `pytest tests` 1515 passed (+2 skipped, +19 vs A7.1 baseline).
  - ✅ `pytest backend/tests` 1372 passed (+4 skipped, +30 vs A7.1
    baseline) incluindo `test_alembic_guardrails::test_offline_sql_generation_works`
    (offline-mode guard no seed) e `test_db_schema_reference_snapshot`
    (regenerado).
  - ✅ `dev/check_pipeline_boundaries.py` verde (zero SQLAlchemy/FastAPI
    em `pipeline/`).
  - ✅ `dev/check_code_style_regression.py` verde (P9 −1 vs baseline;
    nenhum P1/P7 novo após cleanup).
  - ✅ `pre-commit run --all-files` verde.

  **Bridges remanescentes (até A7.5):**
  - `config/parametros_fiscais.json` + `config/taxas.json` mantidos:
    consumidores secundários (`_load_caixa_from_e3` em
    `e5_analyzer_adapter.py`, `e5n_narrativas.py`) ainda lêem dict
    direto. Cleanup completo migra para `ConfigStore` em A7.5.
  - `FileConfigStore.get_fiscal_for_period`/`get_market_rate` continuam
    funcionando (bridge); janela de remoção termina em A7.5.

  **ADR:** [ADR-135](DECISIONS.md#adr-135--versionamento-temporal-de-séries-fiscais-e-câmbio)
  já estava status Decidido (criado em A7.0); esta lane implementa.

- **A7.2a Decision aggregate (event-sourced) + migrator + Plano de Ação — ✅ entregue (2026-04-27):**
  Onda 2 paralela com A7.1: caderno editorial em `config/decisions.md` (que
  violava política PII com valores BRL reais) substituído por aggregate
  event-sourced (`decisions` + `decision_events`). Driver duplo: arquitetura
  (lifecycle Pendente → Decidido → Executado, supersede chain auditável) +
  remoção de PII no mesmo PR.

  **Entregas (8 commits):**
  - `backend/app/models/decision.py` + Alembic `x2y3z4a5b6c7` — 2 tabelas
    com `UNIQUE (workspace_id, code)`, self-FK `supersedes_id`,
    `amount_brl_cents BIGINT` (ADR-090).
  - `backend/app/repositories/decision_repository.py` + 6 use cases
    em `backend/app/application/decisions/` (create/get/list/update/
    mark_executed/supersede). Cada comando emite `DecisionEvent`
    append-only via `repo.add_event` — invariante do aggregate.
  - `backend/app/api/decisions.py` — 6 endpoints com `response_model`
    explícito (ADR-109): `GET/POST /decisions`, `GET/PATCH /decisions/{id}`,
    `POST /decisions/{id}/execute`, `POST /decisions/{id}/supersede`.
    Write endpoints gated por `require_write_role`.
  - `frontend/src/lib/api/decisions.ts` + `frontend/src/hooks/useDecisions.ts`
    + `frontend/src/components/report/sections/PlanoDeAcao/` —
    seção do relatório com tabela ordenada por `code`, filtro por status,
    CTA "Marcar como executada" para Decisões `Decidido`.
  - `config/report_layout.yaml` — entrada `tatico/plano_de_acao` +
    codegen regenerado para frontend + backend.
  - `dev/migrate_decisions_to_db.py` — script one-shot CLI
    (`--workspace-id`, `--dry-run`); idempotente; **descartável** (não
    importado em backend/app).
  - `git rm config/decisions.md` + `dev/check_forbidden_paths.py` +
    `dev/commit.py` bloqueiam re-introdução (defense-in-depth contra
    regressão PII).

  **Testes adicionais (38 specs novos):**
  - `backend/tests/test_decision_repository.py` (5 specs) — CRUD,
    UNIQUE constraint, isolamento cross-tenant, append-only events.
  - `backend/tests/test_decision_use_cases.py` (11 specs) — felizes +
    erros de domínio (Conflict 409, NotFound 404, Validation 422).
  - `backend/tests/test_decisions_api.py` (9 specs) — integração HTTP
    end-to-end + cross-tenant 403/404.
  - `backend/tests/test_decisions_migrator.py` (5 specs) — parser
    markdown table + status normalizer + anti-regressão sobre o
    decisions.md atual (skip pós-cutover).
  - `frontend/tests/components/PlanoDeAcaoSection.test.tsx` (3 specs) —
    render, filtro por status, CTA execute.
  - `frontend/tests/e2e/plano-de-acao.spec.ts` `@critical` — fluxo
    HTTP API-only (cria → execute → GET persiste).

  **Acceptance gates batidos:**
  - ✅ Snapshots `docs/api/v1/openapi.json` + `docs/DB_SCHEMA_REFERENCE.md`
    regenerados (32 → 34 tabelas).
  - ✅ Decision tests todos verdes (29 passed).
  - ✅ Frontend 649 vitest passed (sem regressão fora do escopo).
  - ✅ Pipeline boundary: zero SQLAlchemy/FastAPI no migrator (vive em
    `dev/`, importável standalone).
  - ✅ `config/decisions.md` removido + bloqueado por
    `check_forbidden_paths.py`.

  **Bridges remanescentes:** nenhum — aggregate é independente de
  outras lanes da Sprint A7.

  Track: [track_a7_2a_decision_aggregate.md](agent_prompts/track_a7_2a_decision_aggregate.md).
  ADR: [ADR-136](DECISIONS.md#adr-136--decision-aggregate-event-sourced-com-supersede-chain).

- **A7.1 Cutover `materialize_config` → `ConfigStore` — ✅ entregue (2026-04-27):**
  Onda 2 começa: configs A7.1 (categorization, family_members, institutions,
  report_layout, transfer_config) já não são materializados em disco no fluxo
  produtivo do worker — fluem via `WorkspaceContext.config_overrides` populado
  por `build_config_overrides_from_db` no boundary `_setup_run_context`.

  **Entregas (5 commits):**
  - `pipeline/context.py` — `WorkspaceContext` ganha `workspace_id` +
    `config_store: Optional[ConfigStore]`; `for_tenant` aceita ambos. Stages
    podem opcionalmente consumir o Protocol typed via `ctx.config_store`.
  - `pipeline/stage_config.py` — `ConfigStore` import movido p/ runtime
    (Pydantic v2 não resolvia o forward ref via TYPE_CHECKING — bug
    pré-existente em A7.0 que bloqueava `test_stage_config.py`).
  - `backend/app/services/pipeline_adapter.py` — `build_config_store(db, use_db_artifacts)`
    devolve `DBConfigStore` quando flag on, `FileConfigStore` legacy senão;
    `build_config_overrides_from_db(workspace_id, db)` pré-serializa configs
    A7.1 em dict para `WorkspaceContext.config_overrides`.
  - `backend/app/tasks/pipeline_task._setup_run_context` — abre sessão
    long-lived só com flag on, instancia store, popula overrides, injeta
    no ctx; `_close_config_store_session` fecha no try/finally do task.
  - `backend/app/services/config_materializer.py` — `materialize_config()`
    emite `DeprecationWarning` + structured log `mathoms.config.materialize.legacy_call`
    (logger `mathoms.config.materialize`). **Novo `prepare_pipeline_config_dir`**:
    copia tree global + materializa apenas `pipeline.json` + `llm_config.json`
    (configs FORA do escopo A7.1). **Não emite legacy_call.**
  - `backend/app/services/pipeline_service._prepare_run_context` — usa
    `prepare_pipeline_config_dir` em produção; bridge `materialize_config`
    permanece p/ tests legados (test_config_materializer, test_serializers_round_trip,
    test_materialize_concurrency) e `ensure_tenant_pipeline_config` (upload flow,
    também migrado).
  - `scripts/e5_analyze.py` + `scripts/e5n_narrativas.py` — `_init_config(base_dir, *, ctx=None)`
    aceita ctx; `family_members.json` + `categorization.json` lidos via
    `ctx.load_config(name)` (DB-first via overrides) quando ctx fornecido.
    `main(root_dir)` legado mantém leitura disco.

  **Testes adicionais (10 specs novos):**
  - `tests/unit/pipeline/test_context_config_store.py` (4 specs) —
    field defaults, for_tenant injection, Protocol satisfação.
  - `tests/unit/pipeline/test_e5_config_overrides_parity.py` (3 specs) —
    E5/E5.N preferem overrides sobre disco.
  - `backend/tests/test_pipeline_adapter.py` (6 specs novos) —
    build_config_store + build_config_overrides_from_db.
  - `backend/tests/test_config_materializer.py` (4 specs novos) —
    DeprecationWarning fires, legacy_call log fires (mock spy p/ robustez
    cross-test), prepare skip A7.1 sentinels, prepare zero legacy_call.

  **Acceptance gates batidos:**
  - ✅ `pytest tests` 1495 passed (+2 skipped) — pipeline goldens E3/E4/E5/E5.N
    paridade byte-a-byte preservada.
  - ✅ `pytest backend/tests` 1347 passed (+4 skipped) — incluindo todos os
    legacy materialize_config tests com DeprecationWarning emitida.
  - ✅ `dev/check_pipeline_boundaries.py` verde (zero SQLAlchemy/FastAPI em pipeline/).
  - ✅ `dev/check_code_style_regression.py` verde (P7 -2 vs baseline; nenhum P1/P9 novo).
  - ✅ Fluxo produtivo (`_prepare_run_context` + `ensure_tenant_pipeline_config`)
    não chama mais `materialize_config` — zero `legacy_call` em smoke E2E.

  **Bridges remanescentes (até A7.5):**
  - `materialize_config()` continua callable (tests legados); cada chamada
    emite warning + log estruturado.
  - `FileConfigStore` (Sprint A7.0) continua disponível como fallback.

  Track: [track_a7_1_cutover_materialize.md](agent_prompts/track_a7_1_cutover_materialize.md).
  ADR: [ADR-134](DECISIONS.md#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend).

- **A7.0 ConfigStore protocol + adapters — ✅ entregue (2026-04-26):**
  Onda 1 da Sprint A7 fechada em 7 commits sequenciais. Boundary única
  para leitura de configs do pipeline destrava toda Onda 2 (A7.1, A7.2a,
  A7.2b livres em paralelo) + A7.4 (docs metodologia, paralelo livre).

  **Entregas:**
  - `pipeline/domain/types/config.py` — 12 frozen dataclasses (CategorizationConfig, FamilyMembersConfig, InstitutionsCatalog, ReportLayout, TransferConfig, FiscalParameters stub A7.2b, MarketRate stub A7.2b, etc.).
  - `pipeline/ports/config_store.py` — `ConfigStore` Protocol `@runtime_checkable` com 7 métodos (5 per-workspace + 2 globais com vigência stub).
  - `pipeline/adapters/file_config_store.py` — adapter legado que lê `config/*.json` + `report_layout.yaml` e emite `DeprecationWarning` com data de remoção (Sprint A7.5). Cache lazy idempotente (R19) registrado em `STATELESS_AUDIT.md`.
  - `pipeline/adapters/config_parsers.py` — parsers compartilhados entre File + DB stores (mesma DB row → mesma dataclass que mesmo arquivo disco).
  - `backend/app/services/db_config_store.py` — `DBConfigStore` SQLAlchemy delega aos `serialize_*` existentes em `config_materializer.py` + parsers compartilhados; mescla bloco `transferencias_internas` (ADR-133) automaticamente.
  - `pipeline/adapters/in_memory_config_store.py` — fake nomeado para testes (padrão R15) + 18 specs em `tests/unit/pipeline/test_config_store_protocol.py` cobrindo Protocol shape, DeprecationWarning, parse, stubs A7.2b.
  - `pipeline/stage_config.py` — campo `config_store: Optional[ConfigStore]` adicionado (default `None`; ConfigDict `arbitrary_types_allowed=True`); A7.1 popula em `pipeline_adapter.py`.

  **Boundary preservado:** `dev/check_pipeline_boundaries.py` continua
  verde — `pipeline/**` não importa SQLAlchemy/FastAPI/Celery. Adapter
  DB vive em `backend/`; Protocol em `pipeline/ports/`.

  **Zero call-sites migrados** nesta lane (intencional). A7.1 começa a
  consumir `config_store` em E3/E4/E5/E5.N.

  Track: [track_a7_0_config_store.md](agent_prompts/track_a7_0_config_store.md).
  ADR: [ADR-134](DECISIONS.md#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend).

- **Sprint A7 aberta — Config DB Cutover (CLI legacy removal) (2026-04-26) — 🚧 Onda 1 ✅ · Onda 2 destravada:**
  Plano canônico em [CONFIG_CUTOVER_PLAN.md](CONFIG_CUTOVER_PLAN.md) — 11
  arquivos de `config/` (heranças do CLI mono-cliente) migram para DB
  multi-tenant + tabelas globais versionadas + entidade `Decision`
  event-sourced + `docs/methodology/`. Após cutover, `config/` perde os
  11 arquivos do plano (10 outros legítimos permanecem: schemas, prompts,
  pipeline.json, templates).

  **Estrutura:** 7 lanes em 4 ondas, multi-agente paralelo na Onda 2 (até
  4 agentes simultâneos), supervisão CTO em 4 gates (G1 ADR / G2 schema /
  G3 PR pré-merge / G4 wave boundary). Princípio P1 não-negociável:
  produto continua funcionando entre ondas (smoke E2E verde a cada
  merge em `main`).

  **ADRs novas:** [ADR-134](DECISIONS.md#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend) (ConfigStore protocol + adapters), [ADR-135](DECISIONS.md#adr-135--versionamento-temporal-de-séries-fiscais-e-câmbio) (versionamento temporal fiscal/câmbio), [ADR-136](DECISIONS.md#adr-136--decision-aggregate-event-sourced-com-supersede-chain) (Decision aggregate event-sourced), [ADR-137](DECISIONS.md#adr-137--catalog--override-resolver-para-categorization-e-institutions) (catalog + override resolver), [ADR-138](DECISIONS.md#adr-138--protocolo-de-supervisão-cto-para-sprint-a7) (protocolo CTO supervision multi-agente).

  **Lanes:**
  - **A7.0** ConfigStore protocol + adapters — Onda 1 (BLOQUEANTE) · prompt: [track_a7_0_config_store.md](agent_prompts/track_a7_0_config_store.md).
  - **A7.1** Cutover `materialize_config` → `ConfigStore` — Onda 2 · [track_a7_1_cutover_materialize.md](agent_prompts/track_a7_1_cutover_materialize.md).
  - **A7.2a** Decision aggregate event-sourced + migrator + UI Plano de Ação + remove `decisions.md` — Onda 2 · [track_a7_2a_decision_aggregate.md](agent_prompts/track_a7_2a_decision_aggregate.md).
  - **A7.2b** `fiscal_parameters` + `market_rates` versionadas + remove `parametros_fiscais.json` + `taxas.json` — Onda 2 · [track_a7_2b_fiscal_market_tables.md](agent_prompts/track_a7_2b_fiscal_market_tables.md).
  - **A7.3** Catalog + Override resolver (categorization + institutions) + remove `categorization.json` + `institutions.json` — Onda 3 · [track_a7_3_catalog_override.md](agent_prompts/track_a7_3_catalog_override.md).
  - **A7.4** 4 `.md` metodologia → `docs/methodology/` — paralelo livre · [track_a7_4_methodology_docs.md](agent_prompts/track_a7_4_methodology_docs.md).
  - **A7.5** Cleanup final (`FileConfigStore`, `materialize_config`, paths proibidos) — Onda 4 (BLOQUEANTE) · [track_a7_5_cleanup.md](agent_prompts/track_a7_5_cleanup.md).

  **Driver duplo para `decisions.md`:** arquitetura (entidade event-sourced)
  + compliance (CLAUDE.md §Regras críticas proíbe valores BRL reais em
  commits — `decisions.md` viola hoje).

  **Caminho crítico:** A7.0 → (A7.1 ‖ A7.2a ‖ A7.2b ‖ A7.4) → A7.3 → A7.5.
  Tabela e pickup protocol em [BACKLOG.md §Sprint A7](BACKLOG.md#sprint-a7--config-db-cutover-cli-legacy-removal).

- **Report Appearance Menu — refinement [ADR-121](DECISIONS.md#adr-121--typography-base-13px-com-override-configurável) Fase 4 (2026-04-26) — ✅:**
  Funde `FontScaleToggle` (3 botões "Compacto/Normal/Confortável") e
  `ReportThemeToggle` (Light/Dark) em um único `<AppearanceMenu/>` com
  botão trigger `Aa` que abre popover. Mudanças:
  - Default `useReportFontScale` `"compact"` → `"normal"` — 13px era
    mesquinho para tabela monetária com `tabular-nums` (padrão fintech
    moderno opera 14-16px).
  - Passos `13/15/17px` → `14/16/18px`. 4px entre extremos torna a
    diferença perceptível (antes 2px era imperceptível — origem da
    queixa "aparentemente esses botões não fazem nada").
  - Labels "Compacto/Normal/Confortável" trocados por ícone `Aa` em
    3 tamanhos progressivos dentro do popover (padrão Medium/NYT/Apple
    Books). Tooltip com nome textual mantido para a11y.
  - `transition: font-size 180ms ease-out` em `[data-report-scope]` para
    feedback visual imediato.
  - Top-nav reduz 2 controles para 1; abre espaço para futuras prefs de
    leitura no mesmo popover (line-height, largura de coluna, modo print).

  Arquitetura **inalterada** — continua local + localStorage
  (`mathoms:report:font-scale`). Reading-time prefs (fonte, tema,
  line-height) seguem padrão da indústria: ficam inline na superfície de
  leitura, não em `/settings`. ADR-121 ganhou subseção
  "Refinamento UX (2026-04-26)" — não é ADR nova. `FontScaleToggle.tsx`
  e `ReportThemeToggle.tsx` deletados (único consumer era `ReportShell`).
  Lane: [`report-appearance-menu`](BACKLOG.md#lanes-abertas-agora--pickup-table).
  Prompt: [`track_report_appearance_menu.md`](agent_prompts/track_report_appearance_menu.md).

- **Report Premium UI v2 — Onda F (Hero KPI + Cover identity) ✅ 5/5
  (2026-04-26):** polish completo do topo do relatório estratégico,
  alinhando com `EXEMPLO_DE_RELATORIO.html`. **v2.F.1** trocou 4 KPIs
  uniformes por 6 com hierarquia (`fa1b4ef`); **v2.F.2** reposicionou
  o conjunto para sumário executivo dedicado fora de S1 (`35eee5f`);
  **v2.F.3a/b/c** entregou cover identity (título estático + família
  no badge/meta-card + PDF filename) executada por **3 agentes
  paralelos em worktrees isoladas** com contrato API firmado no plano
  §17.8 — `710ae15` backend, `fc74ab3` PDF filename, `db6cf6f`
  frontend cover. Zero conflito (arquivos disjuntos). Cross-check com
  `EXEMPLO_DE_RELATORIO.html:1379-1419` (8 KPIs com `kpi-hero`) e
  `:1281-1305` (cover) identificou que o hero atual não respondia à
  pergunta central ("quando ficamos independentes?") e o cover soava
  contábil/operacional ("Fechamento Abril 2026") com período
  triplicado. Decisões finais sintetizadas após review cruzado de
  financial-planner (Perini/Cerbasi/AUVP) + product-designer (a11y/
  hierarquia/densidade), em `docs/REPORT_PREMIUM_PLAN.md` §§17.6-17.8:

  - ✅ **v2.F.3c** — PDF filename composto no backend
    ([download_pdf.py](backend/app/application/report/download_pdf.py)
    via header `Content-Disposition`). Helpers `slugify_family`,
    `extract_period_yyyymm`, `compose_pdf_filename` em `_common.py`.
    Slug ASCII-safe (`Gonçalves d'Ávila` → `goncalves-d-avila`).
    Padrão: `mathoms-planejamento-{slug-familia}-{YYYY-MM}.pdf`.
    Fallback gracioso: sem surname omite slot; sem período cai em
    `generated_at`. Envolvido em `sanitize_filename` (defesa
    anti-injeção; whitelist `[A-Za-z0-9._-]` preserva hífens). 4
    testes novos; 24 passed em `test_reports.py`. `ExportToolbar` no
    frontend só dispara `window.print()` ou `onDownloadPdf` injetado,
    sem gerar nome.

  - ✅ **v2.F.3b** — Frontend cover refresh
    ([ReportCover.tsx](frontend/src/components/report/shell/ReportCover.tsx)
    +
    [ReportShell.tsx](frontend/src/components/report/ReportShell.tsx)).
    Título estático `Planejamento Financeiro` (descarta
    `displayTitle` dinâmico — brand nav passa a usar `reportTitle`);
    subtítulo estático `Pessoal e Patrimonial`; badge dinâmico
    `Relatório · Família {Surname}` ou fallback `Relatório
    Patrimonial`; meta-cards reordenados (Família condicional,
    Período de referência em pt-BR `jan 2023 — abr 2026` com em-dash
    U+2014, Gerado em pt-BR, `Mathoms v{N}` lido de `package.json`).
    Helper exportado `formatPeriodCoverPtBR()` em
    [format.ts](frontend/src/lib/format.ts). Tipo TS
    `workspace_family_surname?: string | null` em `ReportResponse`.
    9 testes novos; 603 passed (1 skipped).

  - ✅ **v2.F.3a** — Backend expõe `workspace_family_surname:
    Optional[str] = None` em `ReportResponse` (lookup escalar
    `select(Workspace.family_surname).where(Workspace.id == workspace_id)`
    em `application/report/get_report.py`); snapshot OpenAPI
    atualizado (ADR-109); 2 testes (com surname → "Silva"; sem →
    `None`); 1328 testes backend passed. **Lista
    (`list_reports`) não alterada** (escopo era GET singular; lista
    devolve `null` no campo opcional para clientes que não usam).

  - ✅ **v2.F.2** — `ExecutiveSummarySection` (container não-numerado,
    fora da TOC seccional, `id="sumario-executivo"`) wrapping
    `HeroKpiGrid`, renderizado no `ReportShell` entre
    `ReportPremissasBlock` e `PerfilFamiliaCard`, gated por
    `mode==="estrategico"`. Paridade com
    `EXEMPLO_DE_RELATORIO.html:1376` (`<section id="kpis">` antes de
    `secao-1`). `S1PatrimonioSection` deixa de importar `HeroKpiGrid`
    e seu prop `ratios` (não usado fora do hero); volta a ser focada em
    estrutura+composição (3 charts + 4 cards). Score continua duplicado
    propositalmente entre hero (mini KPI) e S1 (gauge `ScoreCard`) —
    leitura em 5s × breakdown completo. Refactor de posicionamento
    puro, zero mudança de componente, dado ou contrato DTO. Vitest 593
    passed.

  - ✅ **v2.F.1** — `HeroKpiGrid` substitui `PatrimonioKpiRow`. 6 KPIs
    em 2 linhas (3-3 em xl, 2-2 em sm-md, empilhados em sm).
    **Linha 1** — onde estou: Patrimônio Líquido · **Investível
    (HERO)** · Reserva (semáforo verde≥6m / warning 3-6m / red <3m).
    **Linha 2** — para onde vou: Taxa de Poupança · **Independência
    Financeira (HERO composto)** · Score. Card de IF funde
    Meta+Gap+Prazo numa narrativa única (% atingido + progress bar +
    prazo em anos + gap em R$ vermelho), em vez dos 3 cards paralelos
    do exemplo. Custo de Vida e Renda Mensal **não entram** no hero —
    são inputs de fluxo, vivem em S2; aparecem só como contexto inline
    em sub-labels (Reserva em meses, etc.). `KpiTone` estendido com
    `"warning"` (`var(--brand-warning)`) — additivo, sem breaking
    change para consumers existentes (UiDevPlayground, demais
    sections). Lane puramente frontend, zero mudança de contrato DTO.
    `PatrimonioKpiRow.tsx` removido. Vitest 593 passed; ESLint clean
    em `src/`; pre-commit verde.

- **Card "Consumo Consciente" — bug fix + ADR-133 (2026-04-26) — ✅:**
  resolução do bug onde PIX entre contas próprias da família apareciam
  como gastos pontuais no card. Solução em três camadas:
  (a) novo endpoint `GET /workspaces/{id}/reports/consumo-pontuais` que
  centraliza no backend a lista filtrada — antes vivia em
  `frontend/src/lib/periodUtils.ts::filterConsumoPontuais` (filtro local
  só por valor + receita, sem detecção de transferência interna);
  (b) defesa em profundidade aplicando `InternalTransferDetector` sobre
  a descrição mesmo quando o E4 cai em `nao_identificado`;
  (c) **[ADR-133](DECISIONS.md#adr-133--transferencias_internas-modelado-em-transfer_configs-workspace-scoped)** —
  bloco `transferencias_internas` extraído de `config/family_members.json`
  para a tabela `transfer_configs` (workspace-scoped). Migration
  `w1x2y3z4a5b6`. Endpoints `GET/PUT /config/transfer`. Materializer
  ganha `_override_transfer_config` (overlay em `family_members.json`
  com fallback ao global). `list_consumo_pontuais` deixa de ler disco;
  recebe `InternalTransferDetector` injetado via
  `resolve_internal_transfer_detector` (DB-first → defaults globais).
  UI de edição entregue em **ADR-133b** (commits `95f841c` + `ba7b92e`
  + `66e9030`): aba "Transferências" em `/config` + rota dedicada
  `/config/transfer` com 4 seções editáveis (Recipients, Padrões PIX,
  Padrões Globais, Padrões por Banco). Add/edit/remove inline + Save
  desabilitado até dirty + `role="alert"`/`role="status"` para erro/
  sucesso. 6 unit tests Vitest verde + 1 E2E Playwright `@critical`.

- **CI — otimização de uso GitHub Actions (2026-04-26) — ✅:** workflow
  `.github/workflows/ci.yml` agora skipa jobs irrelevantes via
  [`dorny/paths-filter@v3`](https://github.com/dorny/paths-filter). Job
  `changes` no topo classifica diff em 4 áreas (`backend`, `frontend`,
  `pipeline`, `any_code`) e cada job code-related ganha `if:`
  correspondente; `all-green` aceita `success` ou `skipped`. PR docs-only
  cai de ~30 min (13 jobs) para ~1 min (só `changes` + `all-green`
  no-op), alinhando com CLAUDE.md §"Concluído" linhas 64–68 que já
  declarava docs-only fora do gate. PR backend-only pula frontend-* e
  Lighthouse (~10 min); PR frontend-only pula pipeline + backend tests
  (~15 min); PR mixed mantém comportamento atual (regressão zero).
  Onda 2: `actions/cache@v4` em `~/.cache/ms-playwright` para
  `frontend-e2e` (3 browsers) e `frontend-visual` (chromium) — chaves
  separadas por conjunto, invalida em bump de `@playwright/test`,
  economiza ~2-3 min/run em cache hit. Retention de 5 artifacts
  descartáveis (backend-coverage, vitest-results, backend-logs,
  playwright-report, lighthouse-reports) reduzido de 14-30d → 7d;
  `report-visual-snapshots` mantém 30d para revisão de baselines
  OS-específicas. Bug latente descoberto e corrigido durante validação:
  `dorny/paths-filter` precisa de `permissions: pull-requests: read`
  explícito no job (token default falha com "Resource not accessible by
  integration" quando settings repo está em "Read repository contents
  only"). Branch protection do `main` não está habilitada (repo privado
  em GH Free), então `all-green` permanece informativo até gate ser
  ativado. Commits: `ca7a9f4` (paths-filter), `a637a17` (cache),
  `cbf508c` (retention), `663bc0b` (permission fix).

- **Report Premium UI v2.1 — `comparisons`/`changelog` placeholders no
  YAML (2026-04-26) — ✅:** cumpre promessa do BACKLOG §3.1 de "declarados
  `enabled: false` no YAML" (até hoje só registrada em texto, sem entrada
  real). Adicionados blocos placeholder em **6 seções candidatas óbvias**
  — S1, S2, S3 (estratégico) e T2, T3, T5 (tático) — totalizando
  **12 placeholders** (6 seções × 2 tipos). Cada bloco tem
  `id: comparisons_<sec>` / `changelog_<sec>`, `enabled: false` e
  `deferred_until: "v2.D.1 SnapshotChangelogBuilder"`. Schema
  ([`config/schemas/report_layout.schema.json`](../config/schemas/report_layout.schema.json))
  ganhou `$defs/comparisonSpec` + `$defs/changelogSpec` e expõe
  `comparisons[]` / `changelog[]` em `sectionSpec.properties`. Codegen
  ([`dev/codegen_report_layout.py`](../dev/codegen_report_layout.py))
  emite `ComparisonSpec` / `ChangelogSpec` em TS e Pydantic; arquivos
  gerados ([`frontend/src/generated/report-layout.ts`](../frontend/src/generated/report-layout.ts),
  [`backend/app/generated/report_layout.py`](../backend/app/generated/report_layout.py))
  regenerados no mesmo commit. `MIGRATED_SECTIONS` em `ReportShell.tsx`
  já filtra seções `enabled:false` no nível superior; novos arrays não
  são iterados pelo renderer (invisible by default) — render real virá
  em **v2.8** depois que **v2.D.1 SnapshotChangelogBuilder** popular os
  dados. Ver [docs/agent_prompts/track_report_v2.md §3 v2.1](agent_prompts/track_report_v2.md).

- **F12.1e — Correção da lista de locales para 10 (2026-04-26) — ✅
  ([ADR-130](DECISIONS.md#adr-130--internacionalização-com-next-intl--persistência-em-userslocale)
  revisado, commit `94cf939`):** sincroniza `frontend/src/i18n/config.ts`,
  `fonts.ts`, `messages/`, `globals.css` e `tests/i18n/foundation.test.tsx`
  com a revisão de escopo do ADR-130 (11→10 locales). Remove
  `hi`/`ar`/`bn`/`id` (RTL e Indic/SE-Asia fora do escopo F12); adiciona
  `de`/`ja`/`ko` (mercados-alvo APAC/EU/DACH). `RTL_LOCALES` vira `Set`
  vazio; fontes secundárias passam a ser Noto SC (zh-CN), Noto JP (ja),
  Noto KR (ko). Desbloqueia F12.2/F12.3/F12.4/F12.5, que dependiam da
  fundação corrigida. Origem: F12.1a-d mergeada em 2026-04-25 contra a
  lista antiga, antes da revisão de escopo.

- **Report Premium UI v2.3 — S5/S6 esclarecimento (2026-04-26) — ✅
  decisão (b):** auditoria confirmou que `S5` e `S6` existiram em draft
  anterior do `EXEMPLO_DE_RELATORIO.html` cobrindo "Mudança EUA — F1/F2"
  e "Green Card — EB2-NIW", e foram **migrados para o modo USA** como
  `U1` e `U2` quando o modo USA virou bloco opcional separado. A
  numeração estratégica ficou `S1-S4, S7-S10` para preservar IDs já
  citados em ADRs/snapshots/prompts. Documentação inline no
  `config/report_layout.yaml` (header do bloco `usa:` e comentários
  `# ex-S5`/`# ex-S6`) e nos comentários `<!-- ex-S5 -->`/`<!-- ex-S6 -->`
  do exemplo HTML já registravam o mapeamento — auditoria apenas
  formalizou em [REPORT_PREMIUM_PLAN.md §17.5](REPORT_PREMIUM_PLAN.md)
  (tabela de mapeamento + rationale) e em §9.2 (nota inline explicando
  o gap intencional). Sem mudança estrutural em código ou YAML.
  Origem: lane v2.3 da Onda v2.A do roadmap pós-v1.

- **Pre-commit gates de code-style baseline e frontend-lock sync
  (2026-04-25) — ✅:** dois jobs que só rodavam em CI passam a rodar
  localmente, fechando a janela em que `main` fica vermelho até
  alguém regenerar baseline ou lockfile. Origem: dois incidentes no
  mesmo dia (cb0ff11 + ADR-119/ADR-131) — ambos teriam sido pegos
  antes do push se o gate fosse local.
  - `code-style-baseline`: roda
    [`dev/check_code_style_regression.py`](../dev/check_code_style_regression.py)
    quando `.py`/`.ts`/`.tsx` são staged (~5s). Gate idêntico ao job
    CI "Code style baseline regression" (ADR-114).
  - `frontend-lock-sync`: novo
    [`dev/check_frontend_lock_sync.py`](../dev/check_frontend_lock_sync.py)
    executa `npm ci --dry-run --ignore-scripts` em `frontend/`. Falha
    quando o lockfile não satisfaz `package.json`. Pula limpo se
    `npm` ausente (dev sem Node). Roda quando `frontend/package.json`
    ou `frontend/package-lock.json` são staged.
  - Pré-requisito: regenerou
    [`dev/code_style_baseline.json`](../dev/code_style_baseline.json)
    absorvendo offenders residuais de ADR-119/ADR-131 que `3c29e17`
    não capturou (P1 +3, P7 +2, P8 +1). Funções continuam violando
    "4-20 linhas"; baseline serve como floor até sweep dedicado.

- **Report referencia `pipeline_artifact` por FK (2026-04-25) — ✅
  [ADR-131](DECISIONS.md#adr-131--report-referencia-pipeline_artifact-por-fk-drop-analysis_json_path):**
  encerra estruturalmente a regressão A6c+ADR-129 que a Fatia 1 (commit
  `6112f7f`) havia mitigado materializando o JSON em disco. Agora o
  `Report` aponta direto para `pipeline_artifacts.id` via FK
  (`analysis_artifact_id` ON DELETE SET NULL); `analysis_json_path` e
  `size_bytes` saíram do schema. `GET /reports/{id}/data` lê
  `content_json` direto do DB — zero filesystem.
  - Migration `v0w1x2y3z4a5_adr131_report_analysis_artifact_fk` em 3
    passos (`batch_alter_table`): add column + FK, backfill SQL puro
    (`UPDATE reports SET analysis_artifact_id = (SELECT pa.id FROM
    pipeline_artifacts pa WHERE pa.pipeline_run_id =
    reports.pipeline_run_id AND pa.stage='E5' AND
    pa.artifact_key='analise_financeira' LIMIT 1)`), drop colunas
    antigas. Snapshots `_table_pre/intermediate/post` declaram a FK
    para preservá-la em rebuild SQLite.
  - Reader (`get_report_data`): trocou
    `Path(analysis_json_path).read_text()` +
    `json.loads()` por `report.analysis_artifact.content_json` direto
    (relationship `lazy="joined"`). "Arquivo inexistente" e "JSON
    corrompido" deixam de existir como failure modes; resta só
    "FK NULL → 404", coberto por novo teste
    `test_get_report_data_404_after_artifact_deleted`.
  - Writers atualizados: `_create_report_from_output`,
    `_persist_llm_suggestions` e
    `backend/app/scripts/backfill_reports_from_artifacts.py` leem o
    artefato direto do DB e setam `analysis_artifact_id`. Helper
    `_find_latest_analysis_json` (filesystem-based) deletado;
    `_materialize_analysis_json_from_db` (Fatia 1) deletado.
  - DTOs: `ReportResponse` e `ReportSummaryDTO` perdem `size_bytes`;
    frontend `/reports` deixa de exibir tamanho do arquivo (UX
    cosmético, sem caso de uso declarado).
  - Snapshots regenerados: `docs/api/v1/openapi.json` e
    `docs/DB_SCHEMA_REFERENCE.md`.
  - Suíte: 1310 backend + 1464 pipeline ✓ (incl. 4 alembic guardrails).

- **F12.1 — Fundação i18n no frontend (2026-04-25) — ✅ concluída
  (commit `cb0ff11` em `main`):** primeira fase de
  [ADR-130](DECISIONS.md#adr-130--internacionalização-com-next-intl--persistência-em-userslocale)
  (plano canônico em [docs/I18N_PLAN.md](I18N_PLAN.md)) entregue.
  - `next-intl@^4` instalado (Next 16 não aceita v3 — desvio do plano
    documentado; API equivalente para `useTranslations`/`Provider`).
  - [`frontend/src/i18n/{config,request,plural,fonts}.ts`](../frontend/src/i18n/)
    — whitelist tipada dos 11 locales (pt-BR default, en, pt-PT, zh-CN,
    hi, es, ar, fr, bn, ru, id), `RTL_LOCALES = {ar}`, `getDir()`,
    `localeFontHrefs()` para Noto Sans secundárias condicionais.
  - 11 arquivos [`frontend/src/i18n/messages/<locale>.json`](../frontend/src/i18n/messages/)
    com `_meta` + `header.title` (única chave neste corte; bulk
    extraction fica para F12.6).
  - [`frontend/middleware.ts`](../frontend/middleware.ts) cookie-based
    (`NEXT_LOCALE`) — sem prefixo URL, preserva contrato ADR-108.
  - [`frontend/next.config.ts`](../frontend/next.config.ts) registra
    `next-intl/plugin` apontando para `src/i18n/request.ts`.
  - [`frontend/src/app/layout.tsx`](../frontend/src/app/layout.tsx)
    async: `getLocale()` define `<html lang dir>`;
    `NextIntlClientProvider` no client tree; `<link>` condicional para
    Noto Sans SC/Devanagari/Bengali/Arabic no `<head>`.
  - [`frontend/src/app/globals.css`](../frontend/src/app/globals.css)
    — fallback tipográfico via seletor `[lang="..."]` para
    zh-CN/hi/bn/ar.
  - [`AppShell`](../frontend/src/components/AppShell.tsx) substitui
    literal "Mathoms AI" por `useTranslations("header").title` (sidebar
    + mobile header — primeira string traduzida nos 11 locales).
  - [`tests/i18n/foundation.test.tsx`](../frontend/tests/i18n/foundation.test.tsx)
    — 26 asserts: paridade JSON × 11 locales, render real via
    `NextIntlClientProvider` (override por `vi.doUnmock` +
    `vi.importActual`), `getDir`/`isLocale`/`localeFontHrefs`.
  - [`tests/setup.ts`](../frontend/tests/setup.ts) ganha mock global de
    `next-intl` como identity (`key→key`) — preserva suítes existentes
    que renderizam `AppShell` sem provider.
  - Suíte: **561 vitest passed** (46 files, +26 novos asserts).
  - Critério de aceite F12.1 atingido: troca de `NEXT_LOCALE` muda a
    string do header em qualquer dos 11 locales; Noto Sans SC só
    carrega em zh-CN; `dir="rtl"` ativo em ar.
  - **Próximas lanes (paralelizáveis após F12.1):** F12.2 (`format.ts` +
    `<MonetaryValue/>`), F12.3 (persistência em `users.locale` + JWT
    claim, exige ADR-A6f.5b), F12.4 (codegen `report_layout.yaml`),
    F12.5 (mensagens user-facing do backend).

- **Lane `livestep-emit-stages` E0-route — loop sequencial (2026-04-25)
  — saga ADR-119 fechada ✅:** nono e último emissor migrado para o
  contrato [ADR-119](DECISIONS.md#adr-119--contrato-livestep-para-progresso-de-etapas)
  (após E1.5/E2/E1/E1.5c/E4/E5/E2-llm/E3). Última stage do pipeline
  com loop sequencial — fecha a migração progressiva de
  `emit_stage_activity` para `emit_item_progress` em **todas as 9
  stages instrumentáveis**.
  - **`scripts/e0_route.py`:** `route_all` ganha kwarg opcional
    `pipeline_run_id: str | None = None`. No loop `for filepath in
    files` emite `preparing` por arquivo (`current_item=filepath.name`,
    `items_done=idx`). Após o loop, `finalizing` único bypassa
    throttle.
  - **`pipeline/stages/route_documents.py`:** wrapper refatorado para
    chamar `route_all` diretamente com `pipeline_run_id=
    ctx.pipeline_run_id`, mapeando stats → `{success, warning?}`.
    Drop do `SystemExit` dance (exit codes 0/1/2) — agora inspeciona
    stats explicitamente. Mais legível e permite plumbing do
    `pipeline_run_id`.
  - **Design — só `preparing` por arquivo:** `route_file` tem 4
    return paths (skipped, unidentified, duplicate, routed) e LLM
    fallback opcional. Instrumentar `awaiting_llm`/`persisting`
    internamente exigiria refactor invasivo de `classify_by_llm` +
    propagação de `pipeline_run_id` no `route_file`. Throttle de
    250ms já cobre o caso comum (regex path <100ms, LLM segundos);
    `preparing` per-file basta para barra avançar e `current_item`
    rotacionar.
  Commit `26225b1`. Suíte verde: 1464 pipeline + 22 events + 6
  live_progress + tests/test_e0_route_edges + tests/test_stage_wrappers.
  **0 lanes ADR-119 abertas** — saga concluída.

- **Lane `livestep-emit-stages` E3 — adapter instrumentado (2026-04-25):**
  oitavo emissor migrado para o contrato
  [ADR-119](DECISIONS.md#adr-119--contrato-livestep-para-progresso-de-etapas)
  (após E1.5/E2/E1/E1.5c/E4/E5/E2-llm). Primeira lane que **instrumenta
  o adapter de domínio** — diferente das stages batch (E1.5c, E4, E5)
  que só ganharam preparing+finalizing pobres no wrapper, E3 tem loop
  real por (banco, conta, período) dentro de
  `E3ReconcilerAdapter.reconcile_via_store`.
  - **Adapter** ganha kwarg opcional `pipeline_run_id: str | None =
    None`. No loop `for key, stmts in grouped.items()` emite duas
    fases por chave: `preparing` (início da iteração) e `persisting`
    (antes de `store.write`). Após o loop, `finalizing` único bypassa
    throttle. `current_item` carrega a chave do artefato (ex.:
    `itau_BRL_202304_202404`).
  - **`scripts/e3_reconcile.py`:** `_e3_run_reconciliation` repassa
    `ctx.pipeline_run_id`; `main_with_store` emite `preparing`
    cosmético (items_total=1) cobrindo a fase silenciosa de
    load+reconcile que precede o primeiro per-key emit.
  - **Trade-off ISP:** domain adapter agora importa
    `pipeline.live_progress.emit_item_progress`. Aceitável porque
    (a) é opcional (None default), (b) `live_progress` é defensivo
    (no-op sem run_id), (c) há precedente de `output_stage`/
    `output_key_fn` como infrastructure concerns na mesma assinatura.
  Commit `e6e9ebd`. Suíte verde: 1464 pipeline + 22 events + 77 E3
  (incluindo golden e adapter direto).

- **Lane `livestep-emit-stages` E2-llm — concorrente (2026-04-25):**
  sétimo emissor migrado para o contrato
  [ADR-119](DECISIONS.md#adr-119--contrato-livestep-para-progresso-de-etapas)
  (após E1.5/E2/E1/E1.5c/E4/E5). Primeira lane com **concorrência
  real**: `pipeline/stages/extract_with_llm.py` usa
  `ThreadPoolExecutor(max_workers=workers)` (1–8 conforme
  `pipeline.json`). Quatro fases por documento dentro do worker
  (`preparing → awaiting_llm → validating → persisting`); thread
  principal emite `finalizing` único após `as_completed`, bypassando
  o throttle. `items_done` é snapshot atômico via
  `_E2LLMProgress` (helper local `threading.Lock` + counter
  compartilhado, increment no main após `fut.result()`, fora do
  crítico). Remove o `emit_stage_activity` inicial "Iniciando
  leitura com IA" — substituído pelo primeiro `preparing` do worker.
  Commit `56d8c42`. Suíte verde: 1464 pipeline + 22 events + 6
  live_progress + 7 e2_llm. Restam **2 lanes** ADR-119 abertas: E0
  (route loop), E3 (reconcile loop, exige instrumentar adapter).

- **Lane `livestep-emit-stages` E4 + E5 — batch (2026-04-25):**
  quinto e sexto emissores migrados para o contrato
  [ADR-119](DECISIONS.md#adr-119--contrato-livestep-para-progresso-de-etapas)
  (após E1.5/E2/E1/E1.5c). Stages **single-batch** sem loop visível
  no wrapper:
  - **E4 — `pipeline/stages/categorize_transactions.py`:**
    `current_item="Categorização de transações"`.
  - **E5 — `pipeline/stages/analyze_finances.py`:**
    `current_item="Análise financeira"`.
  Apenas `preparing` + `finalizing` por stage — adapter
  (`adapter.categorize_via_store`/`adapter.analyze_via_store`) é
  chamada única, e instrumentar fases internas exigiria mexer no
  adapter de domínio (fora do escopo desta lane). Commit `2a6d5e5`.
  Suíte verde: 1464 pipeline + 22 events.

- **Lane `livestep-emit-stages` E1 + E1.5c — mecânicas (2026-04-25):**
  terceiro e quarto emissores migrados para o contrato
  [ADR-119](DECISIONS.md#adr-119--contrato-livestep-para-progresso-de-etapas)
  (após E1.5 em `3bc9d25` e E2 em `09858df`). Stages **single-batch**
  (não-loop):
  - **E1 — `pipeline/stages/extract_members.py`:** chamada LLM única
    em batch (todos docs pessoais combinados num prompt). 5 fases
    sequenciais (`preparing → awaiting_llm → validating → persisting →
    finalizing`), `items_total=1`, `current_item="N documento(s) pessoais"`.
  - **E1.5c — `pipeline/stages/consolidate_baseline.py`:** stage
    determinística rápida (sem LLM, sem loop, <1s). Apenas
    `preparing` + `finalizing` — granularidade maior é desnecessária
    (throttle 250ms engoliria emits intermediários).
  Commit `3d819db`. Suíte verde: 1464 pipeline + 22 events.

- **Lane `livestep-emit-stages` E2 (2026-04-25):** segundo emissor migrado
  para o contrato [ADR-119](DECISIONS.md#adr-119--contrato-livestep-para-progresso-de-etapas)
  (após E1.5 em `3bc9d25`). `scripts/e2_extract.py` agora chama
  `emit_item_progress(phase="preparing")` no início do loop e
  `emit_item_progress(phase="persisting")` antes de `store.write`,
  com `finalizing` único após o loop. Substitui o `emit_stage_activity`
  com texto embutido `"Processando idx/N"` por progresso tipado +
  throttled. UI ganha barra determinística, label PT-BR rotando e
  `current_item` preservado por `<LiveStepProgress/>`. E2 não emite
  `awaiting_llm` no main path (parser determinístico; LLM fallback é
  stub). Suíte verde: 1464 pipeline + 22 events + 16 e2/live_progress.
  Commit `09858df`.

- **Lane `report-a11y-finalize` item 3 (2026-04-25) — lane fechada
  ✅:** snapshots visuais por seção × tema light/dark.
  - [`frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts`](../frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts)
    — 48 testes (24 seções × 2 temas) no projeto `visual` do Playwright;
    setup injeta `theme` em localStorage antes do mount p/ evitar flash
    light→dark; tolerância `maxDiffPixels: 200`; suporte a
    `[data-mask-snapshot]` para volates legítimos.
  - Job CI `frontend-visual` opt-in via label `visual` ou
    `workflow_dispatch` com input `run_visual` (lento + baselines
    OS-específicas). Adicionado a `.github/workflows/ci.yml`.
  - `.gitignore` bloqueia `*-darwin.png`/`*-win32.png` — baselines
    macOS/Windows nunca devem ser commitadas, source of truth é Linux
    do CI.
  - Ops doc [`docs/REPORT_VISUAL_SNAPSHOTS.md`](REPORT_VISUAL_SNAPSHOTS.md)
    explica fluxo de baseline (workflow_dispatch → artefato →
    commitar `__snapshots__/*-linux.png` → diffs subsequentes).
  - Decisão D3 do track aplicada: spec mobile fica fora — lane futura
    `report-mobile-spec` quando produto decidir o que sai em <767px.
  - Fecha **F11.2c** (regressão visual) do
    [REPORT_PREMIUM_PLAN](REPORT_PREMIUM_PLAN.md).
  - Baselines Linux pendentes — passo manual de mantenedor após o
    merge desta entrada.
  - **Lane `report-a11y-finalize` integralmente entregue**: 6/6 itens
    (1 tab-order, 2 axe, 3 visual, 4 Lighthouse, 5 checklist, 6 gate
    empírico).

- **Lane `report-a11y-finalize` item 5 (2026-04-25):** checklist WCAG
  2.1 AA operacional em [`docs/REPORT_A11Y_CHECKLIST.md`](REPORT_A11Y_CHECKLIST.md).
  Tabela seção × critério (1.4.3 contraste, 2.1.1 teclado, 2.4.3 ordem
  de foco, 2.4.7 foco visível, 4.1.2 nome/papel/valor) com cobertura
  automática (✅ via gate) vs checklist humano (👁 obrigatório no PR)
  para shell global + S1-S10 + APP_A-E + T1-T6 + U1-U4. Pontos de
  atenção destacados: T3 Kanban (drag&drop por teclado), `<MonetaryValue/>`
  em estados de hover light/dark, qualidade semântica de `aria-label`.
  **Absorve [batch2.14](BACKLOG.md#docs-reviewbatch2--reescrita-de-documentos-decisões-de-escopo-pendentes)**
  do docs-review/batch2 (✅ fechado). Resta apenas item 3 (snapshots
  por seção × tema) na lane — sugerido abrir como lane separada quando
  decisão D3 (mobile spec in/out) estiver fechada.

- **Lane `report-a11y-finalize` item 6 (2026-04-25):** gate empírico
  validado. Em vez de PR descartável remoto, regressão exercitada
  localmente — `<button>` com `<svg>` filho, sem `aria-label`/texto,
  inserido em `S10SinteseSection.tsx`. Resultado:
  - axe-core: 2 testes `@critical` falharam com `button-name` critical
    (`Element does not have inner text that is visible to screen readers`).
  - tab-order: 1 teste `@critical` falhou em "nenhum focável dentro de
    `[data-report-scope]` sem accessible name".
  - Após `git checkout` da regressão: 28/28 verde de novo.
  - Evidência arquivada em
    [`docs/REPORT_A11Y_GATE_PROOF.md`](REPORT_A11Y_GATE_PROOF.md) (não
    em commit msg, que rota com o tempo).
  - Resíduos da lane: items 3 (snapshots por seção × tema) e 5
    (checklist WCAG operacional).

### 2026-04-25 — F9.2 resíduo split em 5 sub-fatias (ADR-093)

- T1 fechado em main; T2-T5 organizados em prompts auto-contidos para
  execução em sessões distintas:
  - **F9.2a** pipeline core (`artifact_store` + `llm/*` + `stages/*` +
    `domain/services/*`, ~150 hits) —
    [track_f9_2a_pipeline_core_strings.md](agent_prompts/track_f9_2a_pipeline_core_strings.md).
  - **F9.2b** scripts internos (`e0/e2/e3/e4/e5/e7/e15`, exceto
    `e_reset.py`, ~120 hits) —
    [track_f9_2b_scripts_strings.md](agent_prompts/track_f9_2b_scripts_strings.md).
  - **F9.2c** `scripts/e_reset.py` deprecation warning + flip interno —
    [track_f9_2c_e_reset_deprecation.md](agent_prompts/track_f9_2c_e_reset_deprecation.md).
  - **F9.2d** backend residual (~40 hits) + tests não-golden (~600 hits,
    goldens preservados) —
    [track_f9_2d_backend_tests.md](agent_prompts/track_f9_2d_backend_tests.md).
  - **F9.2e** closeout — re-audit + BACKLOG/CHANGELOG/ADR-093/CLAUDE.md
    + destrava F9.3 (doc-only) —
    [track_f9_2e_closeout.md](agent_prompts/track_f9_2e_closeout.md).
- Ordem: 2a → (2b ‖ 2c ‖ 2d) → 2e. 2a bloqueia downstream porque
  `artifact_store.py` é dependência de scripts/tests.
- Compat layer (`resolve_stage_name`/`to_legacy_stage_name` +
  `STAGE_RENAME_MAP`) permite migração piecemeal — sub-fatias podem
  rodar em sessões e branches independentes.

### 2026-04-25 — F9.2 T1 STAGE_REGISTRY descritivo + compat reverso (ADR-093)

- `pipeline/stage_spec.py` — `STAGE_REGISTRY`, `FULL_ORDER`,
  `DETERMINISTIC_ORDER`, `VIRTUAL_ARTIFACT_STAGES` agora usam keys
  descritivas (`reconcile_transactions`, `analyze_finances`,
  `extract_statements`, …). `STAGE_RENAME_MAP` permanece (legacy →
  descriptive) como compat reverso; novo `DESCRIPTIVE_TO_LEGACY`
  é o inverso.
- Helpers públicos novos:
  - `resolve_stage_name(name)` — aceita legacy ou descriptive,
    retorna sempre descriptive. Use em qualquer boundary externo
    (HTTP body, CLI arg, DB row durante janela F9.2 → F9.3).
  - `to_legacy_stage_name(name)` — inverso, para adapters que
    ainda gravam DB em formato legado.
- `pipeline/orchestrator.py` — `_get_stage_runner` aplica
  `resolve_stage_name` na entrada; `FROM_MAP` estendido com
  keys legadas (`run_from("E3")` continua funcionando).
- `backend/app/services/pipeline_client.py` — `is_llm_stage`
  aceita ambos formatos.
- **DB `pipeline_artifacts.stage` inalterado** — F9.3 (Alembic)
  endereça migração de rows. Janela: app lê via
  `resolve_stage_name`.
- **CLI alias** `scripts/e_reset.py --from E3` ainda funciona
  (deprecação formal será adicionada com warning em sub-fatia
  T5; remoção em F9.6).
- Cobertura: `tests/unit/pipeline/test_stage_spec.py` reescrito
  para `EXPECTED_DESCRIPTIVE_STAGES` + novos casos para
  `resolve_stage_name`/`to_legacy_stage_name`. Pipeline 1464
  passed, backend 1307 passed.

**Pendente para T2-T5 (sub-fatias futuras):** substituir strings
literais `"E3"`/`"E5"` por descritivas em pipeline/orchestrator
(call-sites diretos), backend services/repositories/routers, scripts
CLI, tests não-golden, configs e docstrings. Compat reverso via
`resolve_stage_name` permite essa migração ser **incremental** —
qualquer novo código deve usar descritivo; legado migra piecemeal.

### 2026-04-25 — A6g.3 r3 backend sweep final (A6g 100% fechado)

- **5 HIGH P1** (≥40 linhas) nos alvos finais da rodada 3 eliminados.
  1307 backend tests verdes em todos os commits (paridade preservada).
  Commits push progressivo direto em `main`:
  - `3aa8a35` — `task_repository.list` 59 → 21 linhas; extraídos
    `_apply_status_filter`, `_apply_field_filters`,
    `_priority_order_clause` (module-level helpers). 204 task tests verdes.
  - `51a1430` — `goal_repository.create_new_version` 53 → 26 linhas;
    extraído `_close_current_version` (encapsula flush intermediário
    do unique index parcial `ux_goals_current_ws_type` — ADR-073).
    105 goal tests verdes.
  - `a88033f` — `content_classifier.classify_text` 42 → 16 linhas;
    extraídos `_empty_classification` (builder reutilizado em 2
    early-returns) e `_resolve_institution` (override IRPF →
    Receita Federal). 88 classifier tests verdes.
  - `9fea45c` — `pipeline_service.start_pipeline_run` 67 → 33
    linhas (extrai `_dispatch_celery_task`); `resume_pipeline_run`
    43 → 14 linhas (extrai `_flip_run_to_resuming`,
    `_stages_after_paused`, `_mark_run_completed`). 161 pipeline
    tests verdes.
  - `4c4c39a` — `start_pipeline_run` 58 → 23 linhas (refinamento);
    extrai `_prepare_run_context` consolidando tier detection +
    `StorageService().ensure_tenant_dirs` + `materialize_config`,
    e empacota dispatch args num tuple compartilhado entre Celery
    e fallback. 167 pipeline tests verdes. Último HIGH P1 nos
    alvos r3 eliminado.
- **Auditoria** (`dev/audit_code_style.py` rodado pós-rebase):
  HIGH P1 nos arquivos r3 caiu de 5 → 0; restantes nos arquivos
  alvo viraram MED (≥21l).
- **A6g 100% fechado**: .1 ✅ · .2 1ª rodada ✅ · .2b T3 ✅ ·
  .2c ✅ · .3 r1+r2+r3 ✅ · .3b ✅ · .4 ✅ · .5 ✅ · .6 ✅ · .6b ✅
  · .7 ✅. Próxima frente do caminho crítico: F7A (Docker compose
  staging) → F7B → F7D + dogfood → GA.

### 2026-04-25 — A6g.2b T3 pipeline scripts decomp (goldens-safe)

- **5 scripts com goldens** decompostos em orchestrators finos +
  helpers nomeados, paridade byte-a-byte preservada (1458 pipeline
  tests verdes em todos os commits, incluindo
  `tests/test_e{3,4,5,5n}_golden_execution.py`):
  - `scripts/e7_review.py` — `run_cross_validation` 270 → 11 linhas
    + 14 helpers `_cv{1..14}_*` (cada um 7-25 linhas) + 2 tuplas de
    registro `_CV_OPTIONAL_CHECKS`/`_CV_ALWAYS_CHECKS`. Constante
    `_REQUIRED_CHARTS` extraída.
  - `scripts/e5n_narrativas.py` — `main_with_store` 76 → 32 linhas
    orquestrando 5 fases (`_e5n_print_header`, `_e5n_load_e5`,
    `_e5n_load_metrics`, `_e5n_build_and_validate`, `_e5n_persist`).
  - `scripts/e3_reconcile.py` — `main_with_store` 179 → 27 linhas
    orquestrando 7 fases (`_e3_build_adapter`, `_e3_run_reconciliation`,
    `_e3_validate_outputs`, `_e3_write_sidecar_logs`, `_e3_log_warnings`,
    `_e3_print_summary`, `_e3_build_result_dict`). Imports mortos
    (`generate_legacy_filename`, `ReconciliationService`) removidos.
  - `scripts/e4_categorize.py` — `main_with_store` 131 → 27 linhas
    orquestrando 5 fases (`_e4_build_adapter`, `_e4_persist_artifacts`,
    `_e4_write_qa_sidecar`, `_e4_print_summary`, `_e4_build_result_dict`).
    Import morto `all_filenames` removido.
  - `scripts/e5_analyze.py` — `main_with_store` 195 → 35 linhas
    orquestrando 10 fases (`_e5_init_workspace`, `_e5_load_md_inputs`,
    `_e5_check_e4_inputs`, `_e5_build_adapter`, `_e5_extract_legacy_dicts`,
    `_e5_resolve_periodo_dados`, `_e5_run_sanity_checks`,
    `_e5_compose_output`, `_e5_persist`, `_e5_print_summary`,
    `_e5_build_result_dict`). O anti-exemplo de 2998 linhas continua
    existindo (5 funções `analyze_*` legadas com >100 linhas), mas a
    entrada via Caminho B agora é orchestrator fino — restante depende
    de cleanup pós-F9.
- **Fora de escopo (preservado):** `main(root_dir)` legados não foram
  tocados — A6c.3 já os deletou (2026-04-24); reescritas adicionais em
  `analyze_*` ficam como work residual fora de A6g.
- **Commits:** `0a82790` (e7), `8d31d1c` (e5n), `d6f511a` (e3),
  `fe20f3b` (e4), `ff0757c` (e5).

### 2026-04-25 — F9.1 pipeline/stages rename (ADR-093)

- `git mv` em 14 wrappers de `pipeline/stages/e*.py` para nomes
  descritivos conforme `STAGE_RENAME_MAP`: `audit_documents`,
  `unlock_documents`, `route_documents`, `extract_members`,
  `extract_baseline`, `consolidate_baseline`, `extract_statements`,
  `extract_invoices`, `extract_with_llm`, `reconcile_transactions`,
  `categorize_transactions`, `analyze_finances`, `generate_narratives`,
  `review_finances`.
- Imports atualizados em `pipeline/orchestrator.py`,
  `pipeline/__init__.py`, `tests/test_llm_*.py`,
  `tests/test_stage_wrappers.py`,
  `tests/unit/pipeline/test_e15_artifact_key.py`.
- Strings literais (`"E2"`, `"E3"`…) em `STAGE_REGISTRY` / código de
  produção **inalteradas** — F9.2 endereça.
- Itens deferidos: `pipeline/stages/e2.py` (shim compartilhado, fora do
  mapa) e `pipeline/stages/e7.py` (`run_crossval` + `run_apply`
  agrupados — split planejado para F9.6).
- Goldens E3/E4/E5/E5.N/E7 verdes; 1458 pipeline + 1307 backend tests
  passando, zero regressão. F9.2 destravada.

- **Lane `report-a11y-finalize` itens 1+2 (2026-04-25):** primeiro gate
  empírico de a11y do relatório React. Decisão D1 do track adotada com
  default sugerido — severidade `critical+serious`. Entregas:
  - `frontend/tests/e2e/helpers/mock-report.ts`: helper `mockReportPage`
    intercepta `/api/v1/**` via `page.route()` + injeta token, permitindo
    `/reports/[id]` renderizar com fixture sintética sem backend (mocka
    `/auth/me`, `/me/workspaces`, GET report + data, notes, kanban,
    transactions, notifications).
  - `frontend/tests/e2e/fixtures/reports/medium.json`: fixture única,
    zero PII, densidade média (`small`/`large` ficam para iteração de
    snapshots futura).
  - `frontend/tests/e2e/helpers/axe.ts`: `expectNoA11yViolations` com
    gate configurável (default critical+serious), formata mensagem com
    regra + nó ofensor + helpUrl.
  - `frontend/tests/e2e/reports/a11y.@critical.spec.ts` (24 testes
    verdes): scan axe-core por seção em modo estratégico (S1-S10,
    APP_A-E), tático (T1-T6) e USA (U1-U4) + scan da página inteira.
  - `frontend/tests/e2e/reports/tab-order.@critical.spec.ts` (4 testes
    verdes): asserções escopadas a `[data-report-scope]` (relatório
    roda dentro do `(app)/layout` com sidebar global) — skip-nav
    primeiro focável do escopo + Enter foca `#report-main` + controles
    globais com `aria-label` esperado + nenhum focável sem accessible
    name.
  - Resíduos da lane (itens 3, 5, 6): snapshots por seção × tema,
    checklist WCAG operacional, gate empírico via PR descartável.
  - Commits: `4c089e4` (fixture + helpers + specs) + `fbdf53c` (mock
    `/transactions` p/ destravar `ReceitasFonteCard` + tab-order
    re-escopado ao AppShell).

- **Lane `report-a11y-finalize` item 4 (2026-04-25):** Lighthouse gate
  na rota nativa do relatório. Decisão D2 do track adotada com default
  sugerido — PR-time, fixture `medium`, 3 runs, preset desktop,
  thresholds perf 0.85 / a11y 0.95 / bp 0.95 / seo 0.90 (warn). Entregas:
  - `frontend/lighthouserc.cjs`: config `@lhci/cli` com `puppeteerScript`,
    `numberOfRuns: 3`, assertions categóricas conforme D2.
  - `frontend/tests/lighthouse/lighthouse-mock.cjs`: análogo Puppeteer
    do `mock-report.ts` (Playwright); intercepta `/api/v1/**` com
    fixture sintética + injeta token + pre-aquece a rota para
    estabilizar `next-themes` antes do Lighthouse navegar.
  - `.github/workflows/ci.yml`: novo job `frontend-lighthouse` (npm ci
    + `next build` + `next start` + `lhci autorun` + upload de
    reports). Sem backend — fixture sintética cobre tudo. Adicionado
    a `all-green`.
  - `.gitignore`: ignora `.lighthouseci/`, `playwright-report/`,
    `playwright-results/`.
  - Smoke local (`next dev` + 3 runs): perf=0.89 a11y=1.00 bp=0.96
    seo=1.00 — todos os thresholds passam com folga.
  - Commit: `1618a4e`.

### Report Premium UI v1 (2026-04-25)

Marco: shell React `/reports/[id]` atinge paridade visual com
`EXEMPLO_DE_RELATORIO.html` (raiz do repo) e se torna o **único renderer**
do relatório.

- **10 fases entregues** (F0–F10) entre 2026-04-15 e 2026-04-24, do
  discovery aos apêndices A–E. Detalhe por fase: ver tabela em
  [REPORT_PREMIUM_PLAN.md §2](REPORT_PREMIUM_PLAN.md) ou em
  [BACKLOG.md › Report Premium UI](BACKLOG.md#report-premium-ui--paridade-com-exemplo_de_relatoriohtml).
  Hashes principais: F1.1 `2751dea` (rota nativa substitui iframe),
  F2.A `78a351b` (Patrimônio S1), F2.B `431f39c` (Fluxo S2), F2.C–G
  `1289ea8` (S3–S10 estratégico), F2.H `a3411e6` (USA + Tático), F3.1
  `dc4f9d0` (scroll-spy + deep-links), F3.2 `92d8de1` (mode via URL +
  print A4), F4.0+F4.2 `bc232cc` (PDF Playwright server-side), F8
  `dbc1195` (T3/T6 + Timeline), F11.1 `667ed4d`
  (`StaticReportModeProvider` SSR), sync final `0b8a78c` (PLAN +
  BACKLOG + CHANGELOG na Fase 10).
- **Decomposição do shell** em primitivos por responsabilidade
  (`frontend/src/components/report/{ui,charts,sections,shell,kpi,
  cards,utils}/`) — provider de modo dual: `ReportModeProvider`
  (cliente, dinâmico) + `StaticReportModeProvider` (SSR/standalone).
- **Renderer HTML server-side descontinuado** via
  [ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side):
  React é único renderer; PDF via Playwright é único export server-side.
  Aposentadoria executada na lane `adr-129-e6-kill` (~12 000 LOC
  removidos; ADR-124 superseded; Fases 11/12/13 do plano canceladas).
- **Resíduos abertos:**
  [`report-a11y-finalize`](BACKLOG.md#lanes-abertas-agora--pickup-table)
  itens 3-6 (Lighthouse CI + snapshots por seção + checklist WCAG + gate
  empírico) — itens 1+2 (axe-core + tab-order) entregues em 2026-04-25,
  ver entrada acima. Esta entrada **fecha**
  [`report-v1-polish`](BACKLOG.md#lanes-abertas-agora--pickup-table)
  (resíduo F13 — milestone + ARCHITECTURE/RUNBOOK/SMOKE/CLAUDE).

ADRs relacionadas: ADR-076 (design tokens), ADR-117/118/121/122/123/124
(Report Premium série), ADR-129 (descontinuação E6).

- **ADR-129 lane `adr-129-e6-kill` concluída (2026-04-25):** todas as
  6 fatias mergeadas em `main`. Renderer HTML server-side erradicado;
  React (`/reports/[id]`) é o único renderer; PDF via Playwright
  continua como único export server-side. Hashes por fatia:
  - **Fatia 1** backend API + drop `Report.html_path`: `94f693d`
    (rotas removidas) + `4127abe` (`seed_existing_reports`) + `5e72e72`
    (docs SETUP).
  - **Fatia 2** pipeline + `stage_materialization`: `9f4c616`.
  - **Fatia 3** scripts E6 + refs CLI: `e6d4fdf` → `2c17c77` →
    `f947828` → `e74774f` → `2b18a29` → `152f205`.
  - **Fatia 4** frontend dead code: `b7e4c70` → `1a2f385` →
    `5865d8b`.
  - **Fatia 5** design-tokens + templates standalone: `d395946`
    (build.py) + `4e68061` (delete templates) + `dbcf5e1`
    (re-aponta tests) + `85dc9fb` (sweep refs órfãs).
  - **Fatia 6** docs finais: deletado `docs/e6_render_readme.md`,
    `docs/PIPELINE_ARTIFACTS.md` reescrito (fluxo de produção
    pós-ADR-129), refs em `ARCHITECTURE.md`/`TESTING.md`/
    `ROADMAP.md`/`CLAUDE.md` limpas.

  **Resultado agregado:** ~12 000 LOC removidos (5 693 de
  `scripts/e6_render.py`, 5 047 dos templates standalone, restante
  espalhado entre stages, helpers, UI e testes). ADR-124 (Jinja2
  paridade) superseded; Fases 11/12/13 do Report Premium oficialmente
  canceladas.

### 2026-04-24 — F9.0 audit ADR-093

- `dev/audit_stage_references.py` (ferramenta reutilizável) +
  `docs/audits/f9_audit_20260424.md` (resumo): 3468 ocorrências de
  identificadores legados mapeadas em 6 categorias (doc 1412 · code 1353 ·
  test 602 · config 55 · alembic 30 · filename 16).
- `STAGE_RENAME_MAP` validado contra todo o código + docs + configs +
  alembic — zero blockers; 17 nomes legados em uso, todos cobertos
  (`E5`/`E3`/`E1`/`E4`/`E1.5`/`E2-llm`/`E5.N`/`E7-review`/`E1.5c`/
  `E2-extratos`/`E2-faturas`/`E7-apply`/`E7-crossval`/`E0-route`/
  `E0-audit`/`E0-unlock`/`E5-revised`).
- Tests `test_covers_all_legacy_names` e `test_is_bijective` em
  `tests/unit/pipeline/test_stage_spec.py` já validavam exhaustividade +
  unicidade (não foi necessário criar novos).
- DB sanity check pendente (sem `mathoms.db` local) — re-validar antes
  de F9.3. F9.1 destravada.

- **A6c · Bridge + main(root_dir) legados removidos (2026-04-24):**
  cutover Caminho B concluído após aprovação A6-human (smoke test).
  Limpeza pós-cutover em 4 commits atômicos:
  - **A6c.1 · `pipeline/stage_runner_compat.py` removido** —
    helper `run_legacy_with_bridge_if_db` não tinha mais callers desde
    A5e/f. ALLOWED_PREFIXES de `test_no_legacy_stage_names.py` ajustado.
  - **A6c.2 · `pipeline/materialization_bridge.py` removido** (ADR-086)
    — adapter DB↔disco temporário. Refs em docstrings de
    `pipeline/stages/{e3,e4,e5,e5n,e7}.py`,
    `pipeline/artifact_store.py`,
    `pipeline/domain/services/e3_reconciler_adapter.py`,
    `backend/app/scripts/backfill_artifacts_from_disk.py` e
    `tests/unit/pipeline/test_artifact_stores.py` limpas.
    (`stage_materialization.py` foi deletado em paralelo pela ADR-129
    fatia 2 — não há mais ref a limpar lá.)
  - **A6c.3 · `main(root_dir)` removido dos 6 scripts determinísticos**
    (`scripts/{e15_consolidate,e3_reconcile,e4_categorize,e5_analyze,
    e5n_narrativas,e7_review}.py`) + `if __name__ == "__main__"` blocks.
    Helper `_merge_life_plan_into_goals` em `e5_analyze` preservado
    (consumido por `main_with_store`). 5 parity tests
    (`test_e{15c,3,4,5,5n_e7}_main_with_store_parity.py`) deletados —
    paridade já provada e legado eliminado. 4 golden execution tests
    (`test_e{3,4,5,5n}_golden_execution.py`) migrados para
    `main_with_store(ctx)` via `WorkspaceContext`
    (`test_e6_golden_execution.py` foi removido em paralelo pela
    ADR-129 fatia 2). Fixture autouse em `tests/conftest.py` reseta
    globals de `pipeline_common` após cada teste (substitui o reset
    que vinha no `finally` do main legado).
    `backend/tests/regressions/test_anti_regression_bank.py` ajustado:
    OP-001 parametrize remove `e15_consolidate.py` e `e7_review.py`
    (sem mais `parse_args` — só `main_with_store`).
  - **A6c.4 · Docs:** `docs/ARCHITECTURE.md` (diagrama, §17 bridge,
    seção E3, árvore de pastas), `CLAUDE.md` (seção
    `MATHOMS_USE_DB_ARTIFACTS`), `docs/BACKLOG.md` (A6c.1-.4 ✅, lane
    fechada, "Restante" atualizada — A6g.2b T3 destravado).
  - **Resultado:** pipeline + backend tests verdes localmente. Total
    code+test removido: ~3 100 linhas. Destrava `A6g.2b T3` (scripts
    com goldens) e marca fim formal da migração ADR-086 → ADR-083.

- **ADR-129 fatia 4 · Frontend dead code limpo (2026-04-24 · commits
  `b7e4c70` → `5865d8b`):** quarta de 6 fatias da lane `adr-129-e6-kill`.
  Removidos os helpers `getReportHtmlUrl` e `getReportDownloadHtmlUrl`
  em `frontend/src/lib/api/reports.ts` (endpoints backend já deletados
  na fatia 1). Botões UI "Baixar HTML standalone" removidos do
  `ReportHeader` (ícone Download), `ReportSectionStub` (botão "Baixar
  HTML completo") e da rota `/reports/[id]` (estado pré-F9 reescrito
  para "Relatório indisponível" sem download). `ExportToolbar` perdeu
  o prop `onDownloadHtml` (sem callers no app) e o teste
  correspondente em `shellPrimitives.test.tsx` foi removido. Stages
  `E6` e `E6-final` removidos de `STAGE_DISPLAY_NAMES` (`format.ts`)
  e de `PIPELINE_PHASES` (`pipelinePhases.ts`). MSW handlers para
  `/reports/:id/html` e `/download.html` removidos em
  `tests/mocks/handlers.ts`. Comentários "Substitui ... do
  e6_render.py" limpos em 5 cards/sections (`S1PatrimonioSection`,
  `NarrativeChartCard`, `PatrimonioCategoriasCard`,
  `ReservaEmergenciaCard`, `EndividamentoCard`) e referência a
  `/reports/{id}/html` no comentário de `golden-path.spec.ts`
  reescrita. Suíte frontend 519 testes verde, ESLint 0 errors,
  typecheck OK nos arquivos tocados. Próxima: fatia 5 (design-tokens).

- **ADR-129 fatia 3 · Scripts E6 deletados + refs CLI residuais limpas
  (2026-04-24 · commits `e6d4fdf` → `152f205`):** terceira de 6 fatias
  da lane `adr-129-e6-kill`. Deletados `scripts/e6_render.py` (4867 LOC),
  `scripts/e6/` (sanitize.py + validate.py), `scripts/e6_regen.py`.
  Refs CLI a `python scripts/e6_render.py` removidas/atualizadas em
  `scripts/e7_review.py` (docstring + bloco "próximos passos LLM" + apply
  mode prints) e `scripts/e_reset.py` (instruções pós-LLM). Bônus
  absorvido: `e_reset.py` tinha estrutura runtime de E6/E6-final que
  apontava para arquivo deletado — limpeza completa de
  `DETERMINISTIC_SCRIPTS`, `EXECUTION_ORDER_FULL/_FROM`, `stages_cascade`
  (renomeado de `"E6"` para `"LEGACY-HTML"` no cleanup de
  `output/*.html` legado em disco), `VALID_FROM_STAGES`,
  `check_dependencies` e docstrings (E0→E6 → E0→E7). Tests E6 órfãos
  removidos: `test_e6_init_config_custom_root` em
  `tests/test_stage_wrappers.py`; `TestE6TemplateUsesFamilySurname` +
  `test_global_template_files_preserved` em
  `backend/tests/test_golden_pipeline.py`. Comentários órfãos em
  `config/report_layout.yaml` apontando para `e6_render.py`/`e6_regen.py`
  atualizados (4 comentários — só metadados, não muda valores). Code
  style baseline regenerado: −1 272 ofensores (de 3 619 para 2 347).
  Próxima: fatia 4 (frontend dead code).

- **A6d.1 · Eliminação de globals nos 5 scripts deterministas
  (2026-04-24):** padrão A3b (já aplicado em `e3_reconcile.py`)
  replicado em `e4_categorize.py`, `e5_analyze.py`,
  `e5n_narrativas.py`, `e7_review.py` e `e15_consolidate.py`. Cada
  script: remoção da invocação top-level de
  `_init_config(_pc.PROJECT_DIR)` + defaults sensatos imutáveis no
  nível de módulo. Em `e5n`, `FISCAL = _load_fiscal()` e
  `_CLT_SOURCE_LABELS` (também side-effect de import) movidos para
  dentro de `_init_config`. AST guard estrutural em
  `tests/unit/pipeline/test_no_init_config_at_import.py` percorre
  os 6 scripts (e3 + os 5 novos) e falha se encontrar
  `_init_config(...)` em escopo top-level — ignorando `def`/`async def`.
  Após A6c.3 que removeu `main(root_dir)` legado, apenas
  `main_with_store(ctx)` invoca `_init_config(ctx.root)`.
  1456 pipeline tests + 1307 backend tests passando, zero regressão.

- **ADR-129 fatia 2 · Pipeline E6 + `stage_materialization` removidos
  (2026-04-24 · commit `9f4c616`):** segunda de 6 fatias da lane
  `adr-129-e6-kill`. Deletados `pipeline/stages/e6.py` e
  `pipeline/stage_materialization.py` (último caller de
  `materialize_stages_to_root` era o próprio E6). Stages `E6`/`E6-final`
  removidos de `STAGE_REGISTRY` + `FULL_ORDER` + `DETERMINISTIC_ORDER`
  + `STAGE_RENAME_MAP` + `VALID_FROM_STAGES` (schema da API). Testes
  removidos: `test_stage_materialization.py`, `test_e6_golden_execution.py`,
  `test_import_e6` em `test_stage_wrappers.py`, `TestE6RenderEdges` em
  `test_e5_e6_e5n_edges.py`. Fixtures (`pipeline_runs.py`, `baseline_disk.json`)
  e tests (`test_orchestrator.py`, `test_stage_spec.py`,
  `test_materialization_bridge.py`, `test_retry_config.py`) ajustados.
  Pipeline determinístico agora termina em `E7-apply`; orchestrator não
  importa mais E6. Scripts (`scripts/e6_render.py`, `scripts/e6/`,
  `scripts/e6_regen.py`) ficam órfãos como dead code intencional —
  removidos na fatia 3. Próxima: fatia 3 (scripts).

- **ADR-129 fatia 1 · Backend API + drop `Report.html_path` (2026-04-24
  · commits `94f693d` + `4127abe` + `5e72e72`):** primeira de 6 fatias
  da lane `adr-129-e6-kill`. Removidas rotas `GET /reports/{id}/html` e
  `/download.html` (workspace + admin), use cases
  `get_report_html`/`download_report_html`, coluna `Report.html_path`
  (Alembic `u9v0w1x2y3z4` com `batch_alter_table`+`copy_from` para
  offline SQL), e `_create_report_from_output` agora usa o JSON E5 como
  fonte de `size_bytes`. Bônus absorvendo a fatia 6 original:
  `seed_existing_reports` removido (escaneava `output/*.html` morto) e
  `backend/seed_db.py` encolhido para só bootstrapar
  `admin@mathoms.ai`. OpenAPI snapshot + `DB_SCHEMA_REFERENCE.md`
  regenerados. E6 segue rodando no pipeline; o HTML produzido vira
  garbage em `output/` até a fatia 2 removê-lo. Próxima: fatia 2
  (pipeline `E6` + `stage_materialization`).

- **ADR-129 · Descontinuação completa do renderer HTML server-side
  (2026-04-24 · docs-only):** supersede
  [ADR-124](DECISIONS.md#adr-124--scriptse6_renderpy-aposentado-em-favor-de-ssr-standalone-do-next)
  (2026-04-23) sob premissas atualizadas — produto em desenvolvimento,
  uso 100 % web, CLI deprecated, sem caso de uso para "download HTML".
  Os 3 consumidores hipotéticos de ADR-124 (email contador, backup
  offline, impressão sem app) nunca foram reais; email não existe em
  prod e as outras 2 situações são cobertas por PDF via Playwright.
  **Consequência direta:** Report Premium Fases 11/12/13 canceladas;
  lane `agent/report-premium/phase11-e6-parity/20260424-1558` é
  arquivada (não mergeada). Execução da remoção — `scripts/e6_render.py`
  (4867 LOC), `scripts/e6/`, `scripts/e6_regen.py`, `pipeline/stages/e6.py`,
  `stage_materialization`, stages `E6`/`E6-final`, endpoints `/html`
  (público + admin) + `/download.html`, use cases `get_report_html.py`,
  coluna `Report.html_path` (drop via Alembic), `seed_existing_reports`
  + `backend/seed_db.py`, dead code frontend (`getReportHtmlUrl*`,
  labels E6), emit CSS standalone em `design-tokens/build.py`,
  `docs/e6_render_readme.md`, refs CLI em `scripts/e7_review.py`,
  testes correlatos — tracked em BACKLOG sob a lane `adr-129-e6-kill`
  (PRs sequenciais pós-merge desta ADR). ~5500 LOC a serem removidos;
  último uso de `MaterializationBridge` para "espelhar DB → disco"
  desaparece, pipeline fica 100 % ArtifactStore-native para stages de
  domínio. Docs afetados: DECISIONS.md (ADR-124 superseded + ADR-129
  nova), BACKLOG.md (Fase 11 ❌ + nova lane), REPORT_PREMIUM_PLAN.md
  (§10/§11/§12 marcados histórico), CLAUDE.md, ARCHITECTURE.md, ROADMAP.md.

- **E7-review-llm via ArtifactStore (2026-04-24 · ADR-128):** stage
  `pipeline/stages/e7_review_llm.py` passa a ler E5 (`store.read("E5",
  "analise_financeira")`) e crossval (primeira chave alfabética via
  `list_keys("E7-crossval")`, fallback `"{}"`), e a gravar review via
  `store.write("E7-review", "review_llm", ...)`. Helpers `_load_*`
  refatorados para receber `dict | None`; teste migrado para
  `InMemoryArtifactStore`. Mapping `E7-review` pré-existente (ADR-083).

- **E1 members via ArtifactStore (2026-04-24 · ADR-127):** última stage
  de domínio escrevendo direto em disco migrada para
  `ctx.get_artifact_store().write("E1", "members", ...)`. Mapping E1
  registrado em `_STAGE_TO_DIR`/`_STAGE_TO_SUFFIX`; bridge +
  DBArtifactStore passam a enxergar o artefato. TODO separado: estender
  whitelist de `scripts/e_reset.py` para proteger o registro em DB.

- **Report Premium UI — Fases 0-10 mergedas em `main` (2026-04-24 · ADR-117/
  121/122/123/124):** migração do relatório nativo para paridade visual
  com `EXEMPLO_DE_RELATORIO.html`. Plano e status tracker em
  [REPORT_PREMIUM_PLAN.md](REPORT_PREMIUM_PLAN.md); gaps na Fase 0 em
  [REPORT_PREMIUM_GAPS.md](REPORT_PREMIUM_GAPS.md). **10 das 13 fases**
  concluídas (falta 11 `e6_render.py` paridade → 12 Polish → 13
  Rollout).
  - **F0 Discovery & gaps** (`0f7ddeb..07c44fa`) — plan + inventário +
    ADRs 117/121/122/123/124 emitidas.
  - **F1 Design tokens + dark mode** (`e634173`, `a2123e2`, `6f7c7a9`)
    — `design-tokens/tokens.json` expandido; typography scope 13px
    default + toggle (`ReportThemeToggle`, `useReportFontScale`);
    paleta report.
  - **F2 Chart.js foundation** (`d8041e2..502d65f..31a44c7`) — Chart.js
    4 + react-chartjs-2 + datalabels; 9 primitivos em
    `frontend/src/components/report/charts/primitives/` + `useChartTheme`
    + `ChartConclusion` + `ChartNav` + playground `/reports/_dev/charts`.
  - **F3 UI primitives** (`10179dd`, `1ae3475`, `144eb07`, `5c8e584`,
    `289fa57`) — 19 primitives (`Alert`, `Badge`, `IconBadge`,
    `SectionDivider`, família `Kpi*`, `ScoreCard`, `PontoForteItem`,
    `Kanban`, `NotasCard`, `Timeline`, `ChangelogList`, badges de
    Priority/Deadline/Effort) + playground `/reports/_dev/ui` + 26
    tests Vitest.
  - **F4 Shell** (`6a09ff2`, `84a0187`, `bda1d17`) — `ReportCover`
    (hero gradient + meta), `ReportTopNav` (sticky + active link via
    IntersectionObserver), `ModeToggle`, `FontScaleToggle`,
    `FloatingNav`, `SkipNav`, `ExportToolbar`. Integrados em
    `ReportShell` com `data-report-scope`. 9 Vitest tests.
  - **F5 Layout YAML** (`0f2811f`, `91a2780`, `c3af835`, `8510cfa`) —
    `config/report_layout.yaml` expandido: `cover:` / `navigation:` /
    atributos `summary`/`divider_before`/`collapsible` por section,
    `conclusion`/`period_toggle` por chart, `top_border` por card.
    Apêndices B-E declarados `enabled: false` (até F10). Codegen TS
    (`frontend/src/generated/report-layout.ts`) + Pydantic
    (`backend/app/generated/report_layout.py`) sincronizados.
  - **F6 Derivadores determinísticos** (`7a8a46c`, `9c11749`,
    `eb29688`) — `deriveChartConclusion`, `deriveSectionSummary`,
    `adaptTarefasToKanban`, `adaptProximos15dToTimeline`,
    `priorityFromEffort`. Templates em
    `config/prompts/chart_conclusions.yaml`. 20 tests de adapter. LLM
    em E5 para `section_summaries` adiado (Q11 — revisar pós-F12).
  - **F6.5 Backend persistence** (`2a1261f`, `c2fa932`, `2663ec3` ·
    ADR-123) — tabelas `report_notes` + `kanban_items` via Alembic.
    6 endpoints REST em `backend/app/api/reports_collab.py`
    (GET/PUT `/notes`, GET/POST/PATCH/DELETE `/kanban`), schemas em
    `backend/app/schemas/report_collab.py`, OpenAPI snapshot
    atualizado, 10 tests pytest.
  - **F7 Seções estratégicas S1-S10** (`0f4663a`, `073db70`, `44468ec`)
    — cada seção renderiza `<SectionSummary>` com fallback derivado
    (`deriveSectionSummary`) quando `narrativas[S*]` ausente.
    `NarrativeChartCard` recebe `fallbackConclusion` via
    `deriveChartConclusion`. S10 adota primitivo `ScoreCard`.
  - **F8 Seções táticas + API wire-up** (`ac6fa81`, `dbc1195`,
    `a2f8843` · ADR-123) — HTTP client em
    `frontend/src/lib/api/reports.ts` (`getReportNotes`,
    `putReportNotes`, `listKanbanItems`, `create/update/deleteKanbanItem`).
    T3 TarefasSection consome kanban API + move otimista com rollback.
    T6 NotasSection consome notes API com autosave (debounce 500ms
    via primitivo). T5 ProximosPassos consome `adaptProximos15dToTimeline`.
    `ReportShell` recebe `workspaceId` e repassa a T3/T6. 7 tests MSW.
    DnD real com `@dnd-kit` **adiado** — primitivo usa botões de coluna
    que cobrem o caso de uso imediato.
  - **F9 Seções USA U1-U4** (`9d5fbce`) — mesmo padrão F7 aplicado:
    `<SectionSummary>` + fallback; U1/U2/U4 passam `fallbackConclusion`
    ao `NarrativeChartCard`. 6 tests.
  - **F10 Apêndices A-E** (`c63497d`, `78f9193`, `5fc8cc4`, `31f72cd`) —
    APP_A refatorado para padrão Fase 7 (recebe `data` opcional +
    `<SectionSummary>` com fallback). APP_B (Premissas e Metodologia)
    lista `goals.premissas_snapshot` + card estático com
    Perini/Cerbasi/AUVP/Score Mathoms. APP_C (Cenários Alternativos)
    renderiza `cenarios_mariana` e `programa_milhas` com empty state
    positivo. APP_D (Referências e Fontes) combina metodologias de
    referência + lineage do relatório (`_report_lineage`). APP_E
    (Próximos Ciclos) consome `narrativas.changelog` via `ChangelogList`
    primitivo. YAML `appendices:` B-E flipado para `enabled: true`,
    codegen TS/Pydantic regenerado. `ReportShell` dispatcher estendido.
    10 tests novos em `apendices.test.tsx` cobrindo fallback, render
    com dados e empty state para cada apêndice.
  - **Gates verdes em cada fase:** `vitest run` (suite cresceu para
    520+ tests — falhas pré-existentes em `MonetaryValue compact` e
    `ReportShell > renderiza header` independem destas mudanças),
    `tsc --noEmit` (zero novos erros em arquivos tocados),
    `pytest backend/tests/test_reports_collab_api.py` (10/10),
    `pre-commit run --files …`, drift check zero antes de cada push.
    **Fase 11 (`e6_render.py` paridade · ADR-124)** é a próxima —
    reescrever o exportador HTML standalone com Jinja2 +
    design tokens para paridade visual com a rota `/reports/[id]`.

- **F7F-Local MVP fechado (2026-04-24 · ADR-116):** console interno em
  `127.0.0.1` pronto para dev/staging. 3 slices mergeados em `main`:
  - **S1** (`cd46545..ef1a7ae`) — camada de serviço
    `backend/app/services/internal_ops/` (anonymize, hard_delete,
    reset_password, purge_documents, delete_document, set_developer_flag,
    update_user_email, update_user_profile, get_metrics, list_reports) +
    auth yaml+bcrypt+JWT isolado (`INTERNAL_OPS_SESSION_SECRET`, cookie
    `ops_session` Path=/admin) + rotas `/admin/*` sob flag
    `MATHOMS_INTERNAL_OPS_UI_ENABLED` + `scripts/hash_ops_pw.py` + audit
    JSONL em `logs/internal_ops_audit.log`.
  - **S2** (`e65126b..d7b5a18`) — `frontend-ops/` app Next separada
    (bind `127.0.0.1:3100`, design-tokens compartilhados, zero import do
    frontend cliente); login + 4 telas por área (users/documents/metrics/
    reports) + service `docker-compose.dev.yml`.
  - **S3** (`876d09f..8f1e0ca`) — refino 7F.10–7F.17: tooltip hard-delete
    irreversível, reset pw com 16 chars + invalidação JWT via
    `token_version` (test `test_reset_invalidates_existing_jwt`), purge
    com **DB rollback em OSError de blob** (evita DB/blob fora de sync) +
    preview paginada com botão "excluir" por linha, métricas com filtro
    7d/30d/90d + novos cards `documents_uploaded_last_period` +
    `new_users_last_period`, reports com paginação `offset`/`total`
    (server-side), toggle `is_developer` com confirm só ao ligar, audit
    renomeado `user.email_changed` com `{old,new}` + banner warning de
    logout global no modal, delete document audit com `original_name +
    content_hash + blob_removed`.
  - **Harness Playwright `@internal-ops`** scaffolded em
    `frontend-ops/tests/e2e/` (6 tests: login inv/val + 4 áreas) +
    `scripts/seed_internal_ops_smoke.py` (fixture idempotente). Run
    end-to-end em CI pendente; smoke curl com backend real validado
    manualmente (login/me/users/metrics com campos novos/reports com
    total; fluxos S3.b/f/g auditados).
  - **Gates verdes:** `pytest backend/tests -q` 1307/1307 · `pytest tests
    -q` 1481/1481 · `npm run lint`+`npm run build` em frontend-ops ·
    `pre-commit run --all-files` · `check_forbidden_paths` (YAML
    operator nunca commitado) · OpenAPI snapshot regenerado e comitado.
  - **7F.9 (CLI)** permanece em aberto — só executa se surgir demanda
    concreta de automação; reutiliza `backend/app/services/internal_ops/`
    sem duplicar regra.

- **Contrato `LiveStep` formalizado (2026-04-23 · ADR-119):** payload único
  de progresso intra-stage (`items_done`, `items_total`, `current_item`,
  `phase`) para etapas com loop por item (E1, E1.5, E1.5c, E2-llm, E2-faturas,
  E2-extratos). Helper backend `pipeline.live_progress.emit_item_progress(...)`
  encapsula emissão + throttle; componente frontend `<LiveStepProgress/>`
  renderiza uniforme. Stages sem loop mantêm `emit_stage_activity` simples.
  Primeira implementação: sub-progresso E2 (entrada abaixo). Contrato
  documentado para que demais stages iterativas migrem sem divergência de
  schema. Motivação: E1.5 com 5 IRPFs ficava 44min sem update visual.

- **Readers user-facing DB-first com fallback disco (2026-04-23 · ADR-120):**
  após flip ADR-118, leitores em `backend/app/services/` que apontavam para
  `tenant_root/processed/<dir>/*.json` passaram a consultar
  `ArtifactStore` via helper único `artifact_reader.read_latest_artifact`.
  Incidente 2026-04-23 (workspace caed2272 com E5 novo no DB renderizando
  relatório com dados stale de disco — patrimônio `940k` em vez de `4.3M`)
  motivou a adoção. 4 readers user-facing migrados; disco preservado como
  fallback para CLI dev e workflows de edição manual. Rollback do flip
  ADR-118 permanece viável.

- **UX — sub-progresso por arquivo em E2 (2026-04-23 · ADR-119):**
  `stage_activity`
  agora carrega `current_item`, `items_done`, `items_total` por arquivo
  processado em `E2-extratos` / `E2-faturas` (ver `scripts/e2_extract.py
  run_with_store`). Frontend exibe "Arquivo N/M · nome.pdf" no subtítulo
  do `ActiveRunCard` (sem precisar expandir detalhes técnicos) + barra
  de progresso intra-stage em `StageRow`. Mitiga ansiedade em rodadas
  longas de leitura de faturas (20min+ sem feedback visível).

- **Default `MATHOMS_USE_DB_ARTIFACTS=true` (2026-04-23 · ADR-118):** flip do
  default global de `False` → `True` em `backend/app/core/config.py` após
  cutover DB validado (A6b/A6-human). Consequências operacionais:
  - CI consolidado — removido job informacional
    `backend-tests-db-artifacts` (`continue-on-error: true`); o único job
    `backend-tests` passa a rodar com `MATHOMS_USE_DB_ARTIFACTS=true` e
    bloqueia merge via `all-green`. ~15min/push economizados.
  - `docs/SETUP.md`, `docs/ARCHITECTURE.md` (§17.3, §ArtifactStore),
    `docs/STATELESS_AUDIT.md` (§6, conclusão) e `CLAUDE.md` (§Feature flag)
    atualizados para refletir default `True`.
  - `docs/runbooks/cutover.md` mantido como **referência histórica e
    procedimento de rollback** (setar `false` + redeploy).
  - Override per-workspace (`use_db_artifacts_override`, ADR-106) continua
    válido — agora usado primariamente para debug com disco (`FALSE`).

- **A6e.4 — Routers finos fase 4a COMPLETA (2026-04-22 · ADR-101 R15/R16):**
  **14/14 da fase 4a entregues** — os 7 routers restantes (`invitations`,
  `ws`, `llm`, `transactions`, `reports`, `workspaces`, `pipeline`) viraram
  thin em slices 11-17. THIN_ROUTERS sobe de 12 → 19 routers. Total
  `wc -l` dos 7 antes = 1813 linhas → depois = 715 linhas (-60%). 7
  novos aggregates em `backend/app/application/`:
  `invitation/`, `realtime/`, `llm_config/`, `transaction/`, `report/`,
  `workspace/`, `pipeline_run/`.
  - **`invitations.py`** (slice 11): 127 → 57 linhas. 2 use cases
    (`preview_invitation`, `accept_invitation`). Exception handler global
    `InvitationError` em `main.py` substitui tradução code→status
    ad-hoc (404/409/410/403/422/400). Use case `accept_invitation` emite
    `AuditLogEvent` (alinhado com A6e.events-migration).
  - **`ws.py`** (slice 12): 103 → 31 linhas. Extrai `verify_ws_token` +
    pump loop Redis Pub/Sub para `application/realtime/pipeline_progress.py`
    (`_subscribe`/`_pump_messages`/`_forward`/`_cleanup` privados).
    Handler vira: valida token → accept → delegar. OpenAPI snapshot
    intocado (WebSocket).
  - **`llm.py`** (slice 13): 182 → 89 linhas. 5 use cases em
    `application/llm_config/` (get/save/delete/test/tier) +
    `_response.py` (mask_api_key + to_response). `NotFoundError`
    global substitui `HTTPException(404)` ad-hoc em `test`/`delete`.
  - **`transactions.py`** (slice 14): 231 → 104 linhas. 4 use cases
    (list/export/create_override/delete_override) + `_loading.py`
    (load_overrides_map + load_filtered_transactions). `TransactionFilters`
    dataclass compartilhado entre list/export elimina duplicação de 8
    Query params. `NotFoundError` global substitui 2 `HTTPException(404)`
    ad-hoc. OpenAPI diff só em ordem de query params (consumers parseiam
    por nome, zero breaking).
  - **`reports.py`** (slice 15): 353 → 133 linhas. 7 use cases (list/
    get/html/download_html/data/pdf/tasks) + `_common.py` (serialize_report/
    sanitize_filename/fetch_report). `NotFoundError` global cobre 6 casos
    ad-hoc de 404. `HTTPException(500)` preservado em
    `get_report_data` quando JSON de análise corrompido (infra error,
    não domain). Re-export `_sanitize_filename` no router
    (`noqa: F401`) preserva `test_download_html_sanitize_filename_helper`.
  - **`workspaces.py`** (slice 16): 371 → 163 linhas. 7 use cases em
    `application/workspace/` (list_my_workspaces/list_members/
    update_member_role/remove_member/create_invitation/list_invitations/
    revoke_invitation) + `_dtos.py` (UserWorkspaceResponse/
    UserWorkspaceListResponse + invitation_to_response helper). Exception
    handler global `MembershipError` em `main.py` (not_found→404,
    is_owner→409, invalid_role→422). `InvitationError` ganha
    `limit_reached`→429 (usado em create_invitation). Use cases de
    member/invitation actions emitem `AuditLogEvent` (continuidade de
    A6e.events-migration). Remove 4 blocos `try/except code_to_status`
    ad-hoc.
  - **`pipeline.py`** (slice 17): 439 → 139 linhas. 8 use cases em
    `application/pipeline_run/` (trigger/new_doc_count/list/get/cancel/
    resume/list_reviews/action_review) + `_common.py` (fetch_run/
    fetch_review/run_to_response). `trigger_pipeline` decomposto em 7
    funções privadas (_check_no_active_run/_count_documents/
    _validate_counts/_validate_data_dir/_resolve_incremental/
    _resolve_stages/_create_run) — cada ≤20 linhas. Domain errors
    substituem `HTTPException` ad-hoc: `ConflictError`→409 para
    active-run/already-cancelled/needs-review-gate, `ValidationError`→422
    para incremental-sem-docs/doc-count-zero/from_stage-inválido/
    edit-sem-output. 3 tests atualizados (test_pipeline_api,
    test_pipeline_review, test_pipeline_phase5) — patch locations
    migrados para `application.pipeline_run.*.start_pipeline_run`;
    2 assertions 400→422 (alinhamento com semântica ADR-101).
  - **Gates empíricos:** `pytest backend/tests -q` 1191 passed + 4
    skipped, zero regressão; teste AST `test_routers_thin.py` cobre 19
    routers; OpenAPI snapshot diff apenas em descrições removidas +
    ordem de parâmetros (zero path/method/response_model/status_code
    removido além dos 2 casos 400→422 cobertos acima).
  - **Lane fechada:** A6e.4 agora 17/17 (fase 4a 14/14 + fase 4b 3/3).

- **A6g.3b — polish final: factory Decimal + baseline regenerado (sessão 3 ✅) (2026-04-22):**
  Fecha polish de A6g.3b após slices 1–3 mergeados. Encerra a lane.
  - **`backend/tests/factories/builders.py::make_if_goal`:** assinatura
    `renda_passiva_mensal_brl` migra de `float` → `Decimal("20000")`
    (alinha com DTO `IFGoalInputs.renda_passiva_mensal_brl: MoneyBRL`).
    Callers com literais `int` continuam válidos via coerção do
    `BeforeValidator`.
  - **`ReconciliationTolerancesSchema.saldo_diff`:** docstring explicando
    que é **tolerância de reconciliação**, não money (ADR-090 não se
    aplica). Nome persistido em `config/pipeline.json` + schema — rename
    exigiria migração. Aceito como `P5_float_money=1` residual no
    baseline (false-positive do detector `MONEY_NAME_PATTERN` que casa
    `saldo`).
  - **Baseline regenerado** (`dev/code_style_baseline.json`): P5 total
    **76 → 67** (-9); backend **10 → 1** (só `saldo_diff` residual).
    Slices 1+3 (commits `f348654`, `2804f65`) + slice 2 (`71dc379`)
    consolidados no gate.
  - **S0 (tolerance rename):** aceito como false-positive documentado
    (não renomeado — prompt permitia essa via).
  - **S4 (frontend sanity):** deps não instaladas neste worktree;
    wire-compat validado via OpenAPI snapshot commitado nos slices
    1+3.
  - **Gate:** `pytest backend/tests -q` = **1177 passed, 4 skipped**
    (zero regressão local). **CI no GitHub bloqueado por billing da
    conta** (runs 24811030372 e anteriores falham com `"recent account
    payments have failed"` — não é falha de código); ação fora do
    escopo da lane. Verificação local cobre o gate funcional.
  - **Commits em `main`:** `b17b83f` (code) + `ca9e93e` (docs).
  - **Status:** **lane A6g.3b 100% concluída** (código + docs + baseline
    + ADR-090 nota final).

- **A6e.events-migration — 10 call-sites `audit_log()` inline → `AuditLogEvent` (2026-04-22):**
  Fecha a tarefa A6e.events-migration (destravada por A6e.events/ADR-115).
  Os 10 `await audit_log(...)` / `await audit_service.log(...)` inline em
  routers agora emitem `AuditLogEvent` via `dispatch_sync(..., {"db": db})`;
  handler `write_audit_entry` (já existente) grava `AuditLog` na mesma
  transação do caller. Funções `audit_log` / `audit_service.log` mantidas
  em `services/` (referenciadas por testes) — só os routers pararam de
  chamá-las diretamente.
  - **Sites migrados:** `backend/app/api/documents.py` (5 — upload, delete,
    retry_unlock, update_classification, reclassify), `workspaces.py`
    (4 — purge/export + member changes), `invitations.py` (1).
  - **`client_meta` helper exposto** em `backend/app/services/audit.py`
    (ex-`_client_meta`): routers extraem IP+UA do `request` e passam
    como fields do `AuditLogEvent`. Alias `_client_meta = client_meta`
    preservado para compat.
  - **`AuditAction` enum preservado:** routers continuam usando o
    constante tipado (`AuditAction.document_upload.value`) — zero drift
    de strings de ação.
  - **Emit permanece no router** nos casos onde o composite (upload
    batch, retry_unlock, delete) não tem use case thin ainda — decisão
    documentada no backlog (A6e.4 4b já fechou; further extraction
    deferred). Ainda assim o objetivo da ADR-115 foi atingido: zero
    acoplamento direto com `audit_log()` do router; canal de eventos
    é o único ponto de escrita.
  - **Commits:** `b781ec7` (helper), `da133c0` (documents),
    `d319438` (workspaces), `eabdd04` (invitations).
  - **Gate:** `pytest backend/tests -q` = **1177 passed, 4 skipped**
    (zero regressão); `pre-commit run --all-files` verde. Fix drift
    de format pré-existente em `goal_service.py` (`e52cea1`) commitado
    separado.

- **A6g.3b — Decimal money: goal DTOs + `goal_service` math (slice 2 ✅) (2026-04-22):**
  Fecha a segunda sessão do track A6g.3b: 11 campos money em goal DTOs
  migrados para `MoneyBRL`/`MoneyUSD` e aritmética em `goal_service.py`
  reescrita em `Decimal` (ln/exp para taxa mensal equivalente, `.quantize
  (Decimal("0.01"))` em boundaries). Persistência via `model_dump(mode=
  "json")` mantém JSON `number` no DB — zero migração de schema. Wire
  de response continua `number` via `PlainSerializer`.
  - **DTOs migrados:** `aporte.py` (`meta_aporte_mensal_brl`,
    `distribuicao: dict[str, MoneyBRL]`, `aporte_anual_brl`),
    `dolar.py` (`meta_usd: MoneyUSD`, `aporte_mensal_brl`),
    `if_goal.py` (`renda_passiva_mensal_brl`, `if_meta_brl`,
    `aporte_necessario_mensal_brl`, `if_meta_conservadora_brl`,
    `aporte_mensal_com_patrimonio_atual_brl`,
    `patrimonio_atual_utilizado_brl`, `IFGoalComputeRequest
    .patrimonio_atual_brl`, `IFGoalComputeResponse.faltante_brl`).
  - **Math em Decimal:** `_retorno_mensal_decimal` via
    `((1 + r_annual).ln() / Decimal("12")).exp() - 1` (Decimal não
    suporta expoente fracionário direto); `_pmt_constante_ate_fv`,
    `_if_meta_targets`, `_aporte_cobrindo_gap_com_patrimonio`
    assinam Decimal. `compute_aporte_derived`: `anual = meta *
    Decimal("12")`, distribuição pct via float cast (percentual não
    é money). `compute_dolar_derived`: câmbio promovido a Decimal,
    `horizonte_estimado_meses` permanece float (duração).
    `get_latest_report_patrimonio_liquido` retorna `Optional[Decimal]`.
  - **Persistência:** `create_if_goal_version`,
    `create_typed_goal_version` e `make_if_goal` factory agora usam
    `model_dump(mode="json")` para serializar Decimal → float antes
    do INSERT (coluna SQLAlchemy `JSON` não tem codec Decimal).
  - **OpenAPI snapshot:** Input/Output split agora aparece para DTOs
    com `MoneyBRL` (Input aceita `anyOf [number, string]` por causa
    do `BeforeValidator`, Output emite `number` puro). Frontend TS
    intacto. Diff de +173/−21 linhas em `docs/api/v1/openapi.json`.
  - **Testes:** `test_goal_service` / `test_goals_api` /
    `test_goal_repository` / `test_goal_dto_mapper` verdes (64). Só
    1 assertion ajustada: `test_aporte_zero_quando_patrimonio_ja_
    projeta_acima_da_meta` usa `float(meta)` na aritmética mista
    com `r_m` float. Comparações `Decimal("7200000.00") == 7_200_000.0`
    continuam `True` nativamente.
  - **Gates:** 1174 backend + `test_openapi_snapshot` verde.
  **14/14 da fase 4a entregues** — os 7 routers restantes (`invitations`,
  `ws`, `llm`, `transactions`, `reports`, `workspaces`, `pipeline`) viraram
  thin em slices 11-17. THIN_ROUTERS sobe de 12 → 19 routers. Total
  `wc -l` dos 7 antes = 1813 linhas → depois = 715 linhas (-60%). 7
  novos aggregates em `backend/app/application/`:
  `invitation/`, `realtime/`, `llm_config/`, `transaction/`, `report/`,
  `workspace/`, `pipeline_run/`.
  - **`invitations.py`** (slice 11): 127 → 57 linhas. 2 use cases
    (`preview_invitation`, `accept_invitation`). Exception handler global
    `InvitationError` em `main.py` substitui tradução code→status
    ad-hoc (404/409/410/403/422/400). Mesma base herdada por
    `workspaces.py` depois.
  - **`ws.py`** (slice 12): 103 → 31 linhas. Extrai `verify_ws_token` +
    pump loop Redis Pub/Sub para `application/realtime/pipeline_progress.py`
    (`_subscribe`/`_pump_messages`/`_forward`/`_cleanup` privados).
    Handler vira: valida token → accept → delegar. OpenAPI snapshot
    intocado (WebSocket).
  - **`llm.py`** (slice 13): 182 → 89 linhas. 5 use cases em
    `application/llm_config/` (get/save/delete/test/tier) +
    `_response.py` (mask_api_key + to_response). `NotFoundError`
    global substitui `HTTPException(404)` ad-hoc em `test`/`delete`.
  - **`transactions.py`** (slice 14): 231 → 104 linhas. 4 use cases
    (list/export/create_override/delete_override) + `_loading.py`
    (load_overrides_map + load_filtered_transactions). `TransactionFilters`
    dataclass compartilhado entre list/export elimina duplicação de 8
    Query params. `NotFoundError` global substitui 2 `HTTPException(404)`
    ad-hoc. OpenAPI diff só em ordem de query params (consumers parseiam
    por nome, zero breaking).
  - **`reports.py`** (slice 15): 353 → 133 linhas. 7 use cases (list/
    get/html/download_html/data/pdf/tasks) + `_common.py` (serialize_report/
    sanitize_filename/fetch_report). `NotFoundError` global cobre 6 casos
    ad-hoc de 404. `HTTPException(500)` preservado em
    `get_report_data` quando JSON de análise corrompido (infra error,
    não domain). Re-export `_sanitize_filename` no router
    (`noqa: F401`) preserva `test_download_html_sanitize_filename_helper`.
  - **`workspaces.py`** (slice 16): 371 → 163 linhas. 7 use cases em
    `application/workspace/` (list_my_workspaces/list_members/
    update_member_role/remove_member/create_invitation/list_invitations/
    revoke_invitation) + `_dtos.py` (UserWorkspaceResponse/
    UserWorkspaceListResponse + invitation_to_response helper). Exception
    handler global `MembershipError` em `main.py` (not_found→404,
    is_owner→409, invalid_role→422). `InvitationError` ganha
    `limit_reached`→429 (usado em create_invitation). Remove 4 blocos
    `try/except code_to_status` ad-hoc.
  - **`pipeline.py`** (slice 17): 439 → 139 linhas. 8 use cases em
    `application/pipeline_run/` (trigger/new_doc_count/list/get/cancel/
    resume/list_reviews/action_review) + `_common.py` (fetch_run/
    fetch_review/run_to_response). `trigger_pipeline` decomposto em 7
    funções privadas (_check_no_active_run/_count_documents/
    _validate_counts/_validate_data_dir/_resolve_incremental/
    _resolve_stages/_create_run) — cada ≤20 linhas. Domain errors
    substituem `HTTPException` ad-hoc: `ConflictError`→409 para
    active-run/already-cancelled/needs-review-gate, `ValidationError`→422
    para incremental-sem-docs/doc-count-zero/from_stage-inválido/
    edit-sem-output. 2 tests atualizados (test_pipeline_api,
    test_pipeline_review) — patch locations migrados para
    `application.pipeline_run.*.start_pipeline_run`; 2 assertions
    400→422 (alinhamento com semântica ADR-101).
  - **Gates empíricos:** `pytest backend/tests -q` verde; teste AST
    `test_routers_thin.py` cobre 19 routers; OpenAPI snapshot diff
    apenas em descrições removidas + ordem de parâmetros (zero
    path/method/response_model/status_code removido além dos 2 casos
    400→422 cobertos acima).

- **A6g.3b — Decimal money: tipo `MoneyBRL`/`MoneyUSD` + transactions migrado (parcial) (2026-04-22):**
  Executa slices 1+3 do track A6g.3b (goal DTOs + math `compute_if_derived`
  ficam para sessão dedicada). Cria tipo money com Decimal em memória +
  number no JSON wire, migra 4 campos de transactions + cascata em
  services + OpenAPI snapshot intocado. 4 P5 eliminados sem wire break.
  - **Slice 1 — `backend/app/schemas/money.py`:** `MoneyBRL =
    Annotated[Decimal, BeforeValidator(_coerce_to_decimal), PlainSerializer
    (lambda v: float(v), return_type=float, when_used='json')]`;
    idem `MoneyUSD` (distinção semântica, sem cast entre moedas).
    `_coerce_to_decimal(v: object)` — aceita int/float/str/Decimal via
    `Decimal(str(v))` (evita IEEE-754 binary imprecision); rejeita outros
    com ValueError (Pydantic → ValidationError). `object` em lugar de
    `Any` satisfaz `test_no_any_in_boundary`.
    `backend/tests/test_money_type.py` — 11 testes (inputs aceitos/
    rejeitados, JSON emite number não string, roundtrip preservado
    para valores típicos BRL 2 casas).
  - **Slice 3 — transactions migrated:**
    - `backend/app/schemas/transactions.py`: 4 campos `float` →
      `MoneyBRL` (`TransactionItem.valor`, `TransactionSummary.
      total_receitas/total_despesas/saldo`).
    - `backend/app/schemas/dto/task/progress.py`:
      `TaskProgressResponse.{target_brl, executed_brl}: Optional[MoneyBRL]`.
    - `backend/app/services/transaction_service.py::load_transactions`:
      `Decimal(str(tx.get("valor", 0)))` ao invés de `float(...)`.
      Filter converte `value_min/value_max` (float da query string)
      para Decimal antes de comparar. `paginate_transactions` usa
      `sum(..., Decimal("0"))` start explícito.
    - `backend/app/services/task_progress_service.py`: `_parse_brl_target`
      retorna `Optional[Decimal]`; `_match_transactions_by_keyword`
      retorna `tuple[Decimal, int, set]` (executed = Decimal("0"));
      `compute_progress` calcula percent como `float(Decimal("100") *
      executed / target)` (percent não é money) e `executed_brl =
      executed.quantize(Decimal("0.01"))`.
    - `backend/tests/test_task_progress.py`: 8 assertions de
      `_parse_brl_target` migradas de float literal para `Decimal(...)`
      — `Decimal == float` retorna False em Python.
  - **Wire format preservado:** `make update-openapi-snapshot` zero
    diff. `TransactionItem` só aparece em response schemas (serialization
    mode emite `type: number`). Input mode emitiria `anyOf [number,
    string]` mas não há endpoint que aceita `TransactionItem` como
    body.
  - **Gates verdes:** 1163 backend + 1461 pipeline + 397 frontend
    vitest + frontend ESLint 0 errors + audit regression exit 0.
  - **Deixado para slice 2 (sessão dedicada):** 7 campos goal DTOs
    (`aporte.py`, `dolar.py`, `if_goal.py`) + refactor Decimal math
    em `goal_service.py` (`_pmt_constante_ate_fv`, `_if_meta_targets`,
    `_aporte_cobrindo_gap_com_patrimonio`, `compute_if_derived`,
    `compute_aporte_derived`, `compute_dolar_derived`). Todo o plano
    detalhado em `docs/agent_prompts/track_a6g3b_decimal_money_migration.md`
    §Slice 2.

- **A6g.3b — prompt de migração Decimal money criado (2026-04-22):**
  Documenta o full scope do follow-up diferido de A6g.3 para eliminar
  `P5_float_money` em `backend/app/` (13 ofensores). Prompt em
  `docs/agent_prompts/track_a6g3b_decimal_money_migration.md` cobre:
  (a) tipo `MoneyBRL`/`MoneyUSD = Annotated[Decimal, BeforeValidator,
  PlainSerializer(float, when_used='json')]` — Decimal em memória,
  number no JSON; (b) migração de 7 campos goal DTOs (`aporte`,
  `dolar`, `if_goal`) + 4 campos transactions; (c) refactor cascata
  em `goal_service.py` (fórmulas compute_if_derived, _if_meta_targets,
  _aporte_cobrindo_gap_com_patrimonio, _pmt_constante_ate_fv,
  compute_aporte_derived, compute_dolar_derived) para Decimal
  arithmetic com quantize; (d) `task_progress_service.py` +
  `transaction_service.py` callers; (e) OpenAPI snapshot refresh
  (request schemas ganham `anyOf [number, string]`); (f) frontend
  sanity check — codegen manual em `goals.ts` permanece `number`
  porque wire serializa como number. 6 slices atômicos com gates
  separados; estimativa 1 sessão dedicada (~2.5h). ADR-090 atualizada
  com §Follow-ups apontando para esta lane.

- **A6g.3 — backend style sweep (2ª rodada) (2026-04-22):**
  Continuação do sweep backend — 4 slices adicionais reduzindo P1 em
  services pesadamente acoplados. **Impacto real:** funções ≥40
  linhas (high severity) caem de 72 → 68 (−4 no escopo `backend/app/`).
  Ofensores P1 contados sobem +5 porque decomposição introduz
  helpers ≤39 linhas cada (acima do threshold 20l mas muito abaixo
  das monstras originais); trade-off aceito — legibilidade >
  contagem.
  - **Slice 3a — `services/invitation_service.py` P1 4→2:**
    `create_invitation` 69 → 28 linhas via `_validate_role_for_
    invitation` (guard de role + owner rule), `_assert_not_already_
    member` (join user×member via email), `_assert_pending_quota`
    (rate limit MAX_PENDING). `accept_invitation` 68 → 23 linhas
    via `_assert_invitation_is_acceptable` (4 checks:
    revoked/accepted/expired/email_mismatch) + `_get_or_create_
    member` (idempotência). 12 tests verdes.
  - **Slice 3b — `services/document_processor.py` P1 2→1:**
    `process_uploaded_document` 151 → 25 linhas via
    `_process_json_document` (E1/E1.5 canonical copy),
    `_locked_pdf_response` (telemetry + payload), e
    `_route_classified_file` (decide route vs inbox-stays,
    delegando a `_move_and_record_routed` + `_inbox_rel_path`).
    Constante `_JSON_TYPE_DEST_SUBDIR` elimina if-else paralelo.
    25 tests verdes.
  - **Slice 3c — `services/canonical_routing.py` P1 3→1:**
    Elimina duplicação de 15 linhas entre `rename_to_canonical`
    e `route_inbox_to_canonical_data` via
    `_compute_canonical_dest_path(source_path, tenant_root,
    project_root, ...)` (init_config + ext correction +
    classification + hash + final_name + dest_dir) e
    `_rel_path_str` (POSIX relative path com fallback).
    `rename_to_canonical` 80 → 37 linhas; `route_inbox` 66 → 29.
    26 tests verdes.
  - **Slice 3d — `services/tarefas_md_parser.py` P1 2→1:**
    `parse_tarefas_md` 93 → 35 linhas via `_parse_concluidas_row`,
    `_parse_active_row`, `_apply_dependency_pass`, `_is_table_row`.
    Main loop agora é switch de seção + delegate + 2ª passe de
    dependências. 11 tests verdes.
  - **Zero mudança funcional:** 1150 backend + 1461 pipeline;
    funções >100 linhas (monstras) eliminadas em todos os 4
    services. Sobraram ≤28 linhas cada helper; audit regression
    refletida no baseline atualizado (2263 → 2270, net +7
    collateral de P1 helper-count).
  - **Deixado para próxima rodada:** `content_classifier.py`
    (621 l, P1×3), `services/pipeline_service.py` P1×4,
    `models/task.py` P1×2, repositories P1×5. Continuação após
    A6e.4 fechar fase 4a.

- **A6g.6b — sweep ruff I001/F541 + `ruff format .` + `max-lines` warn→error (2026-04-22 · ADR-114):**
  Follow-up de A6g.6 que esvazia os ignores temporários em `pyproject.toml`
  e ativa o gate de formatação. Bloco único porque quebrar em slices
  intercalados de code-style criaria N cascatas de rebase nas lanes
  ativas (a6e4-thin-routers, a6g3-backend-style-r2).
  - **Slice 1 — `ruff check --fix --select I001,F541 .`:** 361 fixes
    (290 I001 unsorted-imports + 71 F541 f-string-missing-placeholders)
    em 263 arquivos. `ignore = ["I001", "F541"]` removido de
    `[tool.ruff.lint]`.
  - **Slice 2 — `ruff format .`:** 435 arquivos reformatados (287 já
    estavam no padrão). Quote-style `"double"`, indent-style `"space"`,
    line-ending `"auto"` (config pré-existente em `[tool.ruff.format]`,
    só o hook não rodava).
  - **Slice 3 — hook `ruff-format` no pre-commit:** `.pre-commit-config.yaml`
    ganha `ruff-format --check` no bloco `ruff-pre-commit`. Dev roda
    `ruff format .` manual; commit bloqueia se alguém fugir do padrão.
  - **Slice 4 — ESLint `max-lines` warn→error:** zero ofensores hoje
    (A6g.4 zerou T2), promoção direta. `max-lines-per-function` **fica
    em warn** — 64 offenders em 59 arquivos de `components/tasks/`,
    `components/report/`, `app/(app)/config/` (React components JSX
    naturalmente pushando 60 linhas); promoção depende de sweep
    refactor dedicado (lane futura, fora de escopo A6g.6b).
  - **Coordenação com lanes ativas:** a6e4-thin-routers e
    a6g3-backend-style-r2 rodam em worktrees separados. Ambas precisarão
    rebase através deste merge, mas os conflitos são mecânicos
    (formatação). Feito em turno único (anúncio → commit → push ≤15min)
    para minimizar janela de colisão.
  - **Baseline code-style atualizado:** `dev/code_style_baseline.json`
    regenerado via `python3 dev/check_code_style_regression.py
    --save-baseline`. P1_long_functions 883 → 917 (**+34**) — artefato
    de `ruff format` quebrando linhas longas (function signatures
    multi-line, dicts expandidos); mesmo código, mais linhas físicas
    contadas. Outras categorias inalteradas (I001/F541 já estavam fora
    do audit; `ruff format` só afeta P1).
  - **Gates pós-sweep:** `ruff check .` ✅ "All checks passed";
    `ruff format --check .` ✅ "722 files already formatted";
    `pytest tests -q` ✅ 1461 passed + 2 skipped; `pytest backend/tests
    -q` ✅ 1159 passed + 4 skipped (zero regressão); `cd frontend &&
    npm test -- --run` ✅ 397 passed + 1 skipped; `cd frontend && npx
    eslint src/` ✅ zero errors.

- **A6g.3 — backend style sweep (1ª rodada parcial) (2026-04-22):**
  Primeira rodada do sweep `backend/app/` (fora de `api/` + `application/`).
  Reduz P4/P8/P1 sem tocar wire format. **P5 float money (12) deferido
  como A6g.3b** — migração `float → Decimal` muda JSON wire (Pydantic
  serializa Decimal como string); lane dedicada com frontend/codegen
  sync é próximo passo.
  - **Slice 1a — P4 + P8 (−7 ofensores):** 5 `Optional[...]` sem
    default ganham `= None` (`goal/mapper.py::meta_version_from_params`,
    `schemas/pipeline.py::validate_from_stage`,
    `services/audit.py::_client_meta`,
    `services/task_progress_service.py::_load_aporte_keywords_from_config`,
    `scripts/backfill_artifacts_from_disk.py::_iter_workspaces`).
    2 comentários WHAT removidos (`pipeline_task.py` "Check idempotência",
    `cutover_execute.py` "Check pré-condições").
  - **Slice 2a — `services/pipeline_adapter.py` P1 5→2:** extract
    `_TASK_STATUS_LEGACY_LABEL`, `_IF_GOAL_TAXA_RETIRADA_NOTA`,
    `_PRIORITY_SECTION_TITLE` const + helpers `_goals_by_type_async`,
    `_apply_goals_to_payload`, `_md_header_lines`,
    `_md_priority_section_lines`, `_md_done_section_lines`.
    `build_tarefas_md_sync` 76 → 13 linhas; `build_goals_payload`
    async 37 → 7 linhas (elimina duplicação com versão sync).
  - **Slice 2b — `services/goal_service.py` P1 4→3:** extract
    `_if_meta_targets(inputs)` e `_aporte_cobrindo_gap_com_patrimonio
    (if_meta, n_meses, retorno_mensal, patrimonio_atual_brl)`;
    `compute_if_derived` 50 → 23 linhas (orquestração clara de 3
    passos). 23 tests verdes com fórmulas byte-a-byte preservadas.
  - **Slice 2c — `services/task_service.py` P1 4→1 +
    `task_progress_service.py` P1 3→0:** em `task_service`:
    `transition_status` 60 → 18 linhas via
    `_validate_transition`, `_assert_parent_done_before_completing`,
    `_apply_status_timestamps`; `export_markdown` 64 → 13 linhas com
    helpers `_md_export_header_lines`, `_md_priority_block_lines`,
    `_md_done_block_lines`. Em `task_progress_service`:
    `compute_progress` 61 → 23 linhas via
    `_tx_date_in_period`, `_match_transactions_by_keyword`;
    `_raw_to_float` 46 → 18 linhas via
    `_normalize_both_separators`, `_normalize_single_separator`.
  - **Zero mudança funcional:** 1146 backend tests + 1461 pipeline
    tests + 9 `pipeline_adapter` + 23 `goal_service` + 25
    `task_service` + 17 `task_progress_service` — todos verdes.
    Baseline decresceu 2269 → 2263 (net −6; P4 −5, P8 −2, P5 +1
    collateral por helper replicar `patrimonio_atual_brl: float` de
    `compute_if_derived`).
  - **Deixado para próxima rodada:** `services/invitation_service.py`
    (P1×3 longos: `create_invitation` 69l, `accept_invitation` 68l),
    `content_classifier.py` (621 l, P1×3), repositories P1×5,
    `models/task.py` (308 l). Continuação pode vir após A6e.4
    fechar fase 4a.

- **A6e.3c — tipar DTOs de FamilyMember + Category (follow-up ADR-114) (2026-04-22 · `35c7502`):**
  Promove 4 arquivos de `LEGACY_FILES` → `CLEAN_FILES` em
  `backend/tests/architecture/test_no_any_in_boundary.py`. Gate AST
  passa de 31 → 35 clean files; regressão futura de `Any` nesses
  arquivos fica bloqueada.
  - **`dto/family_member/command.py`** (Create + Update):
    `extra: Optional[dict[str, Any]]` → `dict[str, object]`. Campo é
    genuinamente dinâmico (workspace-specific metadata: variantes_nome,
    regex_nome_fatura, profissao…), mas `object` força callers a
    narrow via isinstance em vez de propagar `Any` pela codebase.
  - **`dto/family_member/response.py`**: mesmo tratamento em
    `FamilyMemberResponse.extra`.
  - **`dto/family_member/mapper.py`**: TypedDict `_FamilyMembersConfig`
    + `_FamilyMemberDefault` descrevem shape de
    `config/family_members.json`. Apenas `papel` é lido; `total=False`
    permite chaves adicionais no JSON sem quebrar tipagem.
    `_birth_name_from_extra` aceita `dict[str, object] | None`.
  - **`dto/category/mapper.py`**: TypedDict `_CategorizationConfig`
    para `config/categorization.json` com `expense_keywords` /
    `income_keywords` tipados como `dict[str, list[str]]`.
    `convert_global_defaults_to_responses` refatora o loop para
    literal access (`data.get("expense_keywords")` em vez de variável
    runtime `data.get(key)`) — compat com type-checker TypedDict.
    `count_defaults` idem.
  - **Restante em LEGACY_FILES:** `events.py` (track A6e.events),
    `dashboard.py` + `report.py` (A6g.6b sweep), `dto/config_blob/*` +
    `config.py` + `dto/document/response.py` marcados como OPAQUE
    (config blob dinâmico + debug endpoint extract-json).
  - **Gates empíricos:** `pytest backend/tests -q` 1159 passed + 4
    skipped (zero regressão pré-A6e.3c: 1155); `pytest backend/tests/
    architecture/test_no_any_in_boundary.py -q` 35 passed.

- **A6g.2c — rename `pipeline/llm/service.py` → `litellm_client.py` (2026-04-22):**
  Follow-up de A6g.6 — fecha a única entry da ALLOWLIST de
  `dev/check_forbidden_names.py`. Nome explicita a tech underlying
  (LiteLLM + Instructor) e distingue de outros clients (`pipeline_client`,
  `fake_llm_client`). Classes públicas (LLMService, LLMConfig etc.)
  mantidas — prefixo `LLM` já as torna específicas.
  - **11 imports atualizados:** `pipeline/llm/__init__.py` (re-export);
    `pipeline/stages/{e1,e15,e2_llm,e7_review_llm}.py` (5 imports
    lazy); `backend/app/api/llm.py` (1 lazy); `backend/tests/fixtures/
    llm_mock.py` (docstring + import); `backend/tests/test_llm_service.py`
    (import + 1 `@patch`); `tests/_llm_stage_fixtures.py`;
    `tests/test_llm_stages_per_stage.py` (10 `@patch` strings);
    `tests/test_llm_stages_e7.py` (2 `@patch` strings).
  - **ALLOWLISTs zeradas** em `dev/check_forbidden_names.py` e
    `backend/tests/architecture/test_no_forbidden_names.py` — gate
    `forbidden-names` agora 100% limpo, qualquer novo `service.py`
    solto é bloqueado sem exceção.
  - **Fix colateral `check_float_money.py`:** git mv puro fazia git
    ver todas as linhas como 'adicionadas', disparando false positive
    em `cost_estimate_usd: float` pré-existente. `_is_rename()`
    consulta `git diff --name-status --find-renames=90%` e pula
    arquivos com status R — gate continua bloqueando novos floats
    monetários, não renames.
  - **Gates:** pre-commit verde; 51 architecture tests, 31 LLM
    backend tests, 22 LLM pipeline tests, 1461 pipeline, 1145 backend
    (1 flaky pré-existente em `test_auth_portability` passa
    isoladamente). Zero regressão funcional.

- **A6g.6 — enforcement automatizado de code style (2026-04-22 · ADR-114):**
  Transforma as regras do `CLAUDE.md` §Code style em gates de CI para
  impedir regressão dos sweeps A6g.2/.4/.5. Bicameral — gates imediatos
  bloqueiam código novo; gate progressivo decrementa via baseline
  auditado.
  - **Slice 1 — Ruff:** `[tool.ruff]` em `pyproject.toml` com seleção
    conservadora (E/F/I/W); `ignore` de I001/F541 (285+71 auto-fixáveis
    ficam para A6g.6b — evita tocar 356 arquivos hoje). Hook
    `ruff-pre-commit` sem `--fix` (gate bloqueante); CI job `Ruff check`
    dedicado. `ruff format` **não** ativado — 422 arquivos reformatariam.
  - **Slice 2 — ESLint:** flat config v9 em `frontend/eslint.config.mjs`.
    `@typescript-eslint/no-explicit-any: error` preserva sweep A6g.4
    (zero `any` em frontend/src hoje); `no-unused-vars: error`.
    `max-lines` e `max-lines-per-function` em `warn` (74 warns legados).
    Script `lint` muda de `next lint` (deprecado em Next 16) para
    `eslint src/` direto. Cleanup de 9 unused imports inline (XCircle,
    Wallet, DollarSign, ApiError + helpers fmtBRL/fmtPct mortos em
    TaticoSections). Hook pre-commit via `dev/run_eslint_frontend.sh`
    (pula se `node_modules` ausente localmente). CI job
    `frontend-lint`.
  - **Slice 3 — hooks grep:** `dev/check_forbidden_names.py` bloqueia
    filenames genéricos `{utils,helpers,manager,handler,service}.
    {py,ts,tsx}` (match exato; `audit_helpers.py` OK). ALLOWLIST com
    1 entry (`pipeline/llm/service.py`, rename em A6g.2c).
    `dev/check_float_money.py` bloqueia `: float` em campo monetário
    (ADR-090) analisando apenas linhas ADICIONADAS em `git diff --cached`
    — 79 legados passam. Skip explícito para tolerance/rate/percentage.
  - **Slice 4 — testes AST fail-safe:** `test_no_any_in_boundary.py`
    varre `backend/app/schemas/**/*.py`, parametriza por arquivo;
    12 em `LEGACY_FILES` (4 OPAQUE permanentes; 8 com track).
    `test_no_forbidden_names.py` varre repo inteiro (não só staged)
    como fail-safe do pre-commit hook. 43 testes passam em
    `backend/tests/architecture/` (inclui `test_routers_thin.py` de
    A6e.4).
  - **Slice 5 — audit regression:**
    `dev/check_code_style_regression.py` compara audit atual com
    `dev/code_style_baseline.json` (snapshot 2026-04-22: 2223
    ofensores; P1=874, P7=825, P9=239 dominantes). Exit 1 se qualquer
    categoria crescer; `--save-baseline` para atualizar após sweep.
    CI job `code-style-regression` + adicionado a `all-green`.
  - **Impacto pós-merge:** zero regressão nos sweeps A6g.2/.4/.5;
    baseline pode apenas decrescer via A6g.6b (ruff-format + I001/F541
    sweep), A6g.2c (rename `pipeline/llm/service.py`), A6e.3c
    (eliminar `dict[str, Any]` em DTOs não-OPAQUE).

- **A6e.events — domain events tipados (infra + 2 agregados) (2026-04-22 · ADR-101 R17 · ADR-115):**
  Introduz `backend/app/events/` com `Event` frozen-dataclass, registro
  estático via `@register_handler` e dispatcher síncrono (em transação).
  Desacopla side-effects transversais (audit log, notificações) dos use
  cases — novo agregado que precisar de audit ganha `XCreatedEvent` +
  handler que traduz para `AuditLogEvent`, sem tocar router ou service.
  - **Slice 1 (infra) — 18 unit tests:** `base.py` (`Event` imutável com
    `event_id` UUID hex, `occurred_at` UTC, `aggregate_id/type`,
    `workspace_id`); `registry.py` (`@register_handler` + `_HANDLERS`
    dict); `dispatcher.py` (`dispatch_sync(event, deps)` + stub
    `enqueue_async`); `protocols.py` (`EventHandlerDeps` TypedDict
    `total=False`). Fixture `save/restore` isola registry em testes sem
    apagar handlers reais registrados via import.
  - **Slice 2 (AuditLogEvent) — 7 tests:** `AuditLogEvent` persiste
    `AuditLog` na sessão injetada; `FamilyMemberCreatedEvent` traduz
    via `audit_family_member_created` (member_name fora do payload;
    só `member_key` em `details` — ADR-110 §PII). Migra
    `application/family_member/create_family_member.py` para emitir
    após `repo.create()`. Router `family_members.py` passa `db` +
    `current_user.id` explicitamente (ADR-111: deps via argumento).
  - **Slice 3 (Task events) — 7 tests:** `TaskCreatedEvent` +
    `TaskUpdatedEvent` + handler `task_notification_handler` cria
    `Notification` reativa para deadline em horizonte
    (overdue/urgent/soon). Dedupe por title sufixo `[#N:bucket]`
    converge com cron legado. Flag
    `MATHOMS_USE_EVENT_DRIVEN_TASK_NOTIFICATIONS=false` default
    mantém `scan_and_create_notifications` como fonte única até gate
    humano (A6e.events-followup). `application/task/create_task.py` +
    `update_task.py` emitem eventos com `db` opcional (None → no-op,
    preserva testes unitários com fakes).
  - **Total:** 32 testes novos no pacote `backend/tests/events` (~10s);
    zero regressão em suíte completa (baseline pré-A6e.events: 1064 items
    — 1063 passed + 1 flaky; pós-A6e.events: 1096 passed + 4 skipped).
  - **Atomicidade parcial reconhecida:** `FamilyMemberRepository.create()`
    commita internamente (pré-A6e.events), então audit roda em txn
    separada fechada pelo use case. Task é full-atomic
    (`TaskRepository` segue caller-owns-commit, R14). ADR-115 documenta
    como limitação a fechar quando repos não-Task migrarem para R14.
  - **Out of scope explícito:** migração dos ~14 call-sites de
    `audit_log()` inline em `backend/app/api/*.py` (tarefa
    A6e.events-migration); handlers async pós-commit (Celery/WS); event
    sourcing persistido.
  - **Naming:** lane renomeada `A6e.6 → A6e.events` em 2026-04-22 para
    evitar colisão com 5 commits históricos do Goal slice. Filtro:
    `git log --grep "A6e.events"` retorna só esta lane.

- **A6e.3b — application layer completa (ConfigBlob + Task + Document) (2026-04-22 · ADR-101 R15 · ADR-112):**
  Fecha a superfície DDD começada em A6e.3 — os 3 agregados deferidos
  (ConfigBlob, Task, Document) ganham use cases em
  `backend/app/application/<agg>/`, seguindo o padrão 1 endpoint = 1
  use case com Protocol + fake + testes puros. Desbloqueia **A6e.4
  fase 4b** (thin routers finos para `config.py`, `documents.py`,
  `tasks.py`).
  - **ConfigBlob (slice 1) — 6 use cases, 9 testes:**
    `get/update_pipeline_config`, `get/update_institution_config`,
    `get/update_report_layout`. `ConfigBlobRepositoryProtocol`
    paramétrico (mesmo repo atende 3 modelos isomórficos);
    `GlobalDefaultsLoaderProtocol` isola reads de `config/*.json|yaml`
    do disco (fake devolve dict fixo). `reset_config_to_defaults` e
    `validate_config_schema` do prompt original ficam fora do escopo
    — nenhum endpoint os expõe hoje. Composites `/import`, `/export`
    e `/workspace` settings continuam no router por serem
    cross-aggregate (ADR-112 rollback criteria).
  - **Task + sub-agregados (slice 2) — 13 use cases, 32 testes:**
    Task core (6): `list_workspace_tasks`, `get_task`, `create_task`,
    `update_task`, `transition_task_status`, `cancel_task`.
    TaskSuggestion (5): `list/create/approve/reject`, `merge_into_task`
    (cross-agg: approve materializa Task via `create_task`).
    TaskAttachment (2): `list_task_attachments`,
    `delete_task_attachment` (só a row; arquivo em disco fica no
    composite). `_rules.py` declara `ALLOWED_TRANSITIONS` como fonte
    de verdade do novo layer — duplica `task_service.py`
    temporariamente até A6e.4 4b apagar a versão antiga. Erros de
    domínio tipados (ValidationError → 422, ConflictError → 409,
    NotFoundError → 404). Composites deferidos: upload/download de
    attachment (Storage), `scan_deadlines` (cross-agg Notification),
    `export_markdown` (PlainText), `get_task_progress`.
  - **Document (slice 3) — 6 use cases, 20 testes:**
    `list_workspace_documents` (filtros status/doc_type com CSV),
    `get_document` (retorna entity para callers composite),
    `update_document_classification` (manual_override + invalida E2
    quando doc_type/bank_code mudam), `delete_document` (só a row),
    `list_duplicate_candidates` (fuzzy ADR-081),
    `reclassify_document` (per-doc; bulk fica no router).
    `ClassificationServiceProtocol` envolve
    `document_classification.classify_document` (ADR-081) — teste
    injeta `FakeClassificationService` com resultado fixo; zero LLM
    real. Composites deferidos: `POST /upload` (storage+classify+
    audit+fuzzy dedup+IntegrityError savepoint), `/retry-unlock`,
    `GET /{id}/file`, `/extract-json`, `/reclassify` bulk.
  - **Total nos 3 slices:** 25 use cases, 61 testes puros rodando em
    <8s sem DB, sem LLM (`pytest backend/tests/application/ -q`). Com
    A6e.3, a application layer cobre 6 agregados (category,
    family_member, goal, config_blob, task, document) e 47 use cases.
  - **Fakes nomeados** em `backend/tests/fakes/{config_blob,task,document}.py`
    seguindo política A6g.5 — zero `MagicMock` inline.
  - **Gates empíricos:** `pytest backend/tests -q` 1054 passed + 4
    skipped (baseline pré-A6e.3b: 997); `grep -rn "from fastapi|
    HTTPException|Depends(" backend/app/application/` = 0 (boundary
    ADR-101 R15); `grep "pipeline_task|celery"
    backend/app/application/` = 0 (A6f.1 boundary enforçado).
  - **Out of scope explícito (A6e.3b):** thin routers (A6e.4 4b),
    emissão de domain events (A6e.6), refactor de services (A6g.3),
    enforcement AST (A6e.4).

- **A6e.4 — Routers finos (parcial, 2026-04-22 · ADR-101 R15/R16):**
  **9/14 da fase 4a entregues** (slices 1-7): padrão thin (delegação
  pura a use case) + teste AST que enforça o padrão + 4 novos
  aggregates na application layer.
  - **`goals.py`** (slice 1): 444 → 333 linhas, 17 handlers com 1-4
    statements cada. `_author_names`/`_with_author` migram para
    `backend/app/application/goal/_author_enrichment.py` (helper
    interno do agregado, prefixo `_`). Router remove
    `from sqlalchemy import select`; query de `User.full_name` vive
    no helper application-layer.
  - **`audit.py`** (slice 2): 69 → 47 linhas, 1 handler × 1 stmt.
    Novo `backend/app/application/audit/list_audit_logs.py` com DTOs
    (`AuditLogEntry`/`AuditLogListResponse`); novo
    `backend/app/repositories/audit_log_repository.py` (read-only —
    audit log é imutável). Router re-exporta DTOs para backward-compat
    de imports externos.
  - **Teste AST** (slice 3):
    `backend/tests/architecture/test_routers_thin.py` parseia cada
    router do `THIN_ROUTERS` set e falha se endpoint tem > 15
    statements ou importa `sqlalchemy.select/delete/update/insert/func`
    ou contém `session.commit(` / `.execute(select` no source.
  - **`feature_flags.py`** (slice 4): 68 → 47 linhas, 2 handlers × 1
    stmt. Novo `backend/app/application/feature_flag/` com
    `get_feature_flags` / `set_feature_flag`; schema renomeado
    `FlagUpdateRequest` → `FlagUpdateCommand` (convenção Command).
    Flag desconhecida: antes `HTTPException(400)` inline; agora
    `ValidationError` → 422 (padrão global ADR-101 R15).
  - **`auth.py`** (slice 5): 72 → 48 linhas, 3 handlers × 1 stmt.
    Novo `backend/app/application/auth/` com `register_user` /
    `login_user`. `/me` continua no router (dependency
    `get_current_user` já responde 401 antes do handler). **Novo erro
    tipado `AuthenticationError`** em `application/base/errors.py` +
    handler global → 401 (substitui `HTTPException(401)` inline).
  - **`vault.py`** (slice 6): 80 → 61 linhas, 3 handlers × 1 stmt.
    Novo `backend/app/application/vault/` com `list_passwords` /
    `create_password` / `delete_password`. Crypto continua delegada
    ao singleton `VaultService`; use cases injetam-no via parâmetro
    para testabilidade. `NotFoundError` → 404 substitui
    `HTTPException(404)` inline.
  - **`notifications.py`** (slice 7): 110 → 66 linhas, 3 handlers × 1
    stmt. Novo `backend/app/application/notification/` com
    `list_notifications` (filtros severity/is_read + counters de
    badge), `mark_notifications_read`, `delete_notification`. Queries
    SQLAlchemy saem do router.
  - **`config.py`** (slice 8 · fase 4b · `d6cd3b3`): 464 → 417 linhas,
    6 handlers de ConfigBlob (pipeline/institutions/report-layout GET+PUT)
    delegam aos use cases de `application/config_blob/`. Novo adapter
    `ConfigDefaultsLoader` em `services/config_defaults.py` implementa
    `GlobalDefaultsLoaderProtocol` (wraps `load_global_*` nos nomes
    `load_json`/`load_yaml` esperados pelo Protocol). Use cases importadas
    com alias `_uc_*` para preservar `operationId` no OpenAPI (zero diff
    no snapshot). Helpers `_import_family_members`/`_export_family_members`
    aceitam `workspace: Workspace` em vez de `ws_id` — elimina
    `select(Workspace)` + `db.execute` inline. Composites
    `/import`+`/export` permanecem no router (multi-aggregate, ADR-112).
    Workspace settings (GET/PATCH) continuam inline (não há use case e
    são triviais). 2 routers de fase 4b ainda pendentes (`documents.py`,
    `tasks.py`).
  - **`tasks.py`** (slice 9 · fase 4b · `09bcc9c`): 487 → 509 linhas
    (cresce 22 linhas em troca de aliases explícitos + DI helpers +
    response types anotados; endpoint bodies encolhem de 5-15 stmts
    para 1-6 stmts). 13 dos 19 handlers delegam aos use cases de
    `application/task/` (7 Task CRUD + 5 TaskSuggestion + 1
    list_attachments + 1 delete_attachment). 6 composites permanecem:
    `export.md` (compat pipeline), `scan-deadlines` (cross-aggregate
    Notification — reativo em A6e.events-followup), `progress`
    (Storage + heurística), `upload`/`download`/`get_attachment` (side-
    effect filesystem). 3 DI helpers `_get_task_repo` /
    `_get_suggestion_repo` / `_get_attachment_repo`. `delete_attachment`
    fica thin-composite: use case retorna entidade → router resolve
    path → commit → unlink filesystem. Aliases `_uc_*` preservam
    operationIds (snapshot só diff em descriptions).
  - **`documents.py`** (slice 10 · fase 4b · `4f13b4a`): 770 → 447
    linhas (-42%). 8 endpoints; 3 use cases + 5 composites extraídos
    para `backend/app/services/document_*`:
    - `password_vault_reader.get_workspace_passwords`: remove
      `from sqlalchemy import select` do router.
    - `document_upload_service.upload_document_batch`: quota + validação
      + partial-unique-index savepoint + process + fuzzy dedup.
    - `document_retry_service.retry_unlock_workspace_documents`:
      re-processa docs travados com senhas atuais do vault.
    - `document_reclassify_bulk_service.reclassify_workspace_documents`:
      regex + LLM fallback em todos os docs + rename canônico + fuzzy
      rebuild.
    - `document_extract_json_service.read_document_extract_json`: match
      por stored_path → fallback por bank+type+period.

    Use-case handlers: `list_documents` → `list_workspace_documents`
    (CSV parsing no use case); `delete_document` → `delete_document` +
    file unlink inline; `update_document_classification` mantém helpers
    privados (`_snapshot_before`, `_apply_classification_update`,
    `_invalidate_e2_if_needed`) porque o use case atual não cobre
    invalidação E2 + downgrade de status. **Breaking**: status filter
    inválido agora retorna 422 (antes 400) — ADR-101 R15
    (`ValidationError` → 422 global); teste atualizado.

    `audit_log` permanece inline em 5 sites (upload/delete/update/retry/
    reclassify) — migração para evento em A6e.events-migration dedicado.

    **Fase 4b ✅ 3/3** (config + tasks + documents).
  - **Allowlist atual `THIN_ROUTERS` (12):** `audit`, `auth`,
    `categories`, `config`, `dashboard`, `documents`, `family_members`,
    `feature_flags`, `goals`, `notifications`, `tasks`, `vault`.
  - **Openapi snapshot** regenerado: apenas `FlagUpdateRequest` →
    `FlagUpdateCommand` (rename) + descrições deletadas de docstrings
    de handler. Zero path/method/response_model mudou — contrato
    preservado (aliased imports nos routers com nomes ambíguos).
  - **Gates empíricos:** `pytest backend/tests -q` 1085 passed + 4
    skipped (baseline pós-A6e.events: 1064; +21 novos testes de use
    case rodando <10s sem DB externo); AST enforcer verde para os 9
    routers finos; zero `HTTPException` nos 4 routers dos slices 4-7.
  - **Não entrega nesta fatia:** 7 routers restantes da fase 4a
    (`pipeline`, `workspaces`, `reports`, `transactions`, `llm`,
    `invitations`, `ws`) + 3 da fase 4b (`documents`, `tasks`,
    `config`, já destravados por A6e.3b ✅). Domain events nos use
    cases novos (feature_flag/auth/vault/notification) ficam para
    A6e.events expandir.

- **A6g.7 — Go prep: `.golangci.yml` + CI job + skeleton (2026-04-22 · ADR-113):**
  Guardrails infra para a primeira reescrita Go (candidato natural:
  `pipeline-service/` destravado por A6f.1 · ADR-112). Zero `.go`
  produtivo — apenas skeleton + config + CI workflow + ADR rastreável.
  - **`.golangci.yml`** conservador: `errcheck`, `staticcheck`,
    `gocritic`, `revive` (exported + error-* + var-naming +
    package-comments + unused-parameter), `bodyclose`, `noctx`,
    `sqlclosecheck`, `rowserrcheck`, `errorlint` (errorf + asserts +
    comparison), `gocyclo` (min-complexity=15), `goconst`, `prealloc`,
    `unparam`, `unconvert`, `misspell`, `govet --enable-all`.
    `forbidigo`/`depguard` ficam para A6g.6 — precisam de código real
    para calibrar sem ruído de false-positives.
  - **`go.work`** na raiz com `go 1.22` + comentário-guia. Sem `use`
    directive por ora — `use ./services/<nome>` entra no mesmo PR do
    primeiro módulo (`go work sync` com `use` apontando para dir sem
    `go.mod` aborta). `services/README.md` documenta a sequência
    exata de passos para o primeiro serviço.
  - **`services/`** skeleton com `README.md` (convenções consolidadas
    do `CLAUDE.md` §Code style › Go — `int64` cents, `log/slog` JSON,
    errors tipados, interfaces pequenas no consumer) + `.gitkeep`.
    `services/pipeline-service-go/` é mencionado como candidato, sem
    entrar no escopo desta lane.
  - **`.github/workflows/go.yml`** com step `detect` que seta
    `has_go=true|false` via `find . -type f -name "*.go"`. Todos os
    jobs subsequentes gateados por `if: steps.detect.outputs.has_go ==
    'true'`; caso contrário, emitem "Skip notice". Resultado:
    workflow vacuously true em CI enquanto não há `.go`; quando o
    primeiro entrar, ativa `go work sync` + `gofmt -s -l` + `go vet
    ./...` + `golangci-lint v1.60` + `go test ./... -race` sem edição
    do workflow.
  - **`Makefile`** ganha `go-fmt`, `go-lint`, `go-test`, `go-all` com
    skip defensivo (`GO_FILES` vazio ou sem `go.work` → no-op +
    mensagem informativa). `make go-all` retorna 0 num repo sem Go.
  - **`CLAUDE.md`** §Code style › Go ganha link inline para ADR-113 —
    zero duplicação de regras.
  - **Gate local:** `python -c "import yaml; yaml.safe_load(...)"`
    valida `.golangci.yml` e `.github/workflows/go.yml` sem erro de
    sintaxe; `make go-fmt`/`go-lint`/`go-test`/`go-all` retornam 0.
  - **Out of scope (explícito):** código Go produtivo, reescrita de
    `pipeline-service/`, ativação de `forbidigo`/`depguard`, codegen
    `oapi-codegen`, hook pre-commit Go. Cada item tem dependência
    específica e ADR própria quando chegar.

- **A6e.5 — `/api/v1/` prefix + alias deprecated + OpenAPI versionado (2026-04-22 · ADR-108):**
  Versionamento da API pública. Rotas canônicas passam para `/api/v1/*`;
  alias `/api/*` continua funcional via `LegacyApiDeprecationMiddleware`
  (Deprecation + Sunset + Link rel="successor-version") até remoção em
  F7A, quando reverse proxy estará pronto. OpenAPI declara
  `info.version = "1.0.0"` + `servers: [{url: "/api/v1"}]`, habilitando
  clients gerados com contrato congelado.
  - **Backend:** `settings.API_PREFIX = "/api/v1"` (novo default),
    `LEGACY_API_PREFIX = "/api"`, `API_VERSION = "1.0.0"`,
    `LEGACY_SUNSET_DATE = "TBD F7A"`. `main.py` registra cada router
    2× (canônico + alias, `include_in_schema=False` no legado) via
    `_ALL_ROUTERS`. Handlers, DTOs e response models intocados
    (ADR-109).
  - **Middleware:** `backend/app/middleware/legacy_deprecation.py`
    (≤45 linhas) — anexa 3 headers em responses do alias (RFC 8594 +
    IETF draft-dalal-deprecation-header + RFC 8288). Guard evita
    falso-positivo quando `API_PREFIX` é extensão do `LEGACY_API_PREFIX`.
  - **OpenAPI snapshot** regenerado: 88 paths migram `/api/*` →
    `/api/v1/*`, `info.version` 0.1.0 → 1.0.0, novo `servers` com
    `/api/v1`. Alias fora do schema.
  - **Frontend:** `API_BASE = "/api/v1"` em `src/lib/api/core.ts`
    (ponto único). Literal `/api/transactions/export` em
    `transactions/_components/exportTransactions.ts` trocado por
    `${API_BASE}/...`. MSW handlers + 19 arquivos de teste
    atualizados para `/api/v1/...`; constante `API` em
    `tests/mocks/handlers.ts`, `tests/lib/reports.test.ts` e
    `tests/hooks/useReportData.test.tsx` passa a valer `/api/v1`.
    `msw-lint.mjs` aponta para `${BACKEND_URL}/api/v1/openapi.json`.
  - **Gate:**
    - `pytest backend/tests -q` = 984 passed, 4 skipped.
    - `pytest backend/tests/middleware/test_legacy_deprecation.py -q`
      = 3 passed (canônico sem headers; alias com 3 headers; `/health`
      unaffected).
    - `pytest backend/tests/test_openapi_snapshot.py
      backend/tests/test_openapi_response_models.py -q` = 2 passed.
    - `pytest pipeline-service/tests -q` = 12 passed (sem regressão).
    - `cd frontend && npm test -- --run` = 397 passed, 1 skipped
      (34 arquivos).
    - `curl -I http://localhost:8000/api/v1/health` 200 sem
      `Deprecation`; `/api/health` 200 + `Deprecation: true` +
      `Sunset: TBD F7A` + `Link: </api/v1>; rel="successor-version"`.
  - **Out of scope (explícito):** remoção do alias `/api/*` fica em
    F7A (exige métricas de tráfego mostrando zero clientes legados +
    reverse proxy configurado); `/api/v2/*` não criado (YAGNI);
    clients SDK gerados (F7C/F7D). Rewrite em `frontend/next.config.ts`
    segue `/api/:path*` — cobre ambos prefixes automaticamente.

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
  - **T2.a — `pipeline/domain/services/narrativas/charts_narrator.py::narrate`:**
    284 → 36 linhas (corpo ~23, assinatura spans 7 linhas). Extraídos
    6 métodos privados por grupo de charts, preservando ordem de
    inserção e strings byte-a-byte:
    `_narrate_patrimonio_aloc` (charts 1-4: score_gauge,
    patrimonio_doughnut, alocacao_atual, alocacao_alvo),
    `_narrate_fluxo_receita` (5-8: fluxo_mensal, receita_bar,
    receita_despesa_mensal, despesas_doughnut),
    `_narrate_projecao_if` (9-14: projecao_3cenarios, waterfall_if,
    renda_passiva, yield_imoveis, top15_ativos, impostos_pj),
    `_narrate_cenarios_conjuge` (15, chave dinâmica
    `ctx.key_cenarios_section`), `_narrate_fase_eua` (16-18:
    custos_f1f2, viagens, cenarios_cambiais),
    `_narrate_riscos_decisoes` (19-20: bubble_riscos, top5_decisoes).
    `narrate()` computa locals compartilhados (`_fontes_receita`,
    `_riscos_top3`, `_imovel_acima`, `_cm_*`) e faz merge via `**`.
    Gate: `pytest tests/test_e5n_golden_execution.py
    tests/test_e5n_builder_decomposition.py -q` = 12 passed (paridade
    de narrativas em TODAS as strings).
  - **Fora de escopo nesta rodada (documentado):**
    - Scripts com goldens (e3/e4/e5/e5n/e6/e7) — 11 ofensores P2 + ~250
      P1 ficam para **A6g.2b** pós-A6c.3 (quando `main(root_dir)`
      legados forem deletados).
  - **Impact numérico nos targets:**
    - `long_functions` P1: `e_reset.main` 372 → 27; `e0_audit.main`
      140 → <25; `run_pipeline_task` 273 → 58; `ChartsNarrator.narrate`
      284 → 36 — todas removidas da lista high-severity (>40 linhas).
      Helper mais longo criado: `_narrate_projecao_if` (69 linhas,
      6 charts agrupados).
    - `long_files` P2: `pdf_generator.py` 1067 → 29 (remove da lista);
      `e_reset.py` 1332 → 1379 (stretch — targets extraídos mas main
      file ainda >1000; consolidação em módulos separados planejada
      para A6g.2b); `e0_audit.py` 948 → 238 (remove da lista);
      `pipeline_task.py` 628 → 742 (+114 por framing de helpers — file
      ainda >500 mas função principal cai 78%);
      `charts_narrator.py` 312 → 359 (+47 por framing de métodos;
      função principal cai 87%).
  - **Gates consolidados:**
    - `pytest tests -q` = 1461 passed, 2 skipped (igual baseline).
    - `pytest tests/test_e5n_golden_execution.py tests/test_e5n_builder_decomposition.py -q` = 12 passed (paridade byte-a-byte preservada).
    - `pytest backend/tests/test_golden_pipeline.py -q` = 19 passed,
      1 skipped.
    - `pytest backend/tests/test_pipeline_task.py -q` = 13 passed.
    - `pytest backend/tests/test_openapi_snapshot.py -q` = 1 passed.
    - `python scripts/e_reset.py --help` output idêntico.
    - `python scripts/e0_audit.py --json` output idêntico.
    - `pre-commit run` passa nos arquivos tocados.

- **A6g.4c — 3ª rodada frontend style sweep: páginas `plano/*` (2026-04-22):**
  Fechamento do ataque a T2 — as duas páginas `>500 l` remanescentes após
  A6g.4b (`plano/page.tsx` 630 e `plano/alocacao/wizard/page.tsx` 533)
  decompostas com a mesma convenção `_components/` colocated.
  - **`plano/page.tsx` (630 → 152):** extrai `GoalCard` (66) reutilizável
    pelo grid 2×2, `GoalsOverviewGrid` (97) como wrapper do grid,
    `EmptyGoalsBanner` (33) para CTA de configuração inicial,
    `IFProgressBar` (53), `IFKPIsRow` (57) com cenário partindo de zero,
    `IFParamsCard` (62) com dl de parâmetros vigentes,
    `LinkedTasksSection` (109) com header + empty state + row dedicados;
    hook `usePlanoOverview` (161) consolida `Promise.allSettled` dos 4
    goals + tasks IF + progresso IF. Estados `loading`/`error`/`no-workspace`
    viram subfunções locais do orchestrator.
  - **`plano/alocacao/wizard/page.tsx` (533 → 185):** extrai
    `Step1Distribution` (150) com presets + inputs + sum indicator,
    `Step2Instruments` (52), `Step3Rebalance` (55) + `AlocacaoSummary` (93),
    `AlocacaoBar` (43) compartilhada entre passo 1 e passo 3 (remove
    duplicação visual); `constants.ts` (40) agrega `PRESETS`,
    `REBAL_OPTIONS`, `COLORS`, tipo `Pcts`; hook `useAlocacaoWizard` (111)
    consolida estado dos 3 passos + derivados (soma, somaValida,
    canAdvance, draftAlocacaoInputs/Derived para `GoalPremissasCard`) +
    `handleSave`. `StepProgressBar` e `WizardNavigation` como subfunções
    locais.
  - **T2 `ts_long_files`:** 2 → **0** 🎯 (todas as páginas `>500 l`
    decompostas).
  - **T3 `ts_long_functions`:** 25 → 29. Sub-componentes novos (JSX puros
    como `EmptyGoalsBanner` 25, `EmptyLinkedTasks` 30) ficam em severidade
    `med`. Hook `usePlanoOverview` inicial caiu em severidade `high` (50
    linhas) e foi tightened num terceiro commit extraindo `runPlanoLoad` +
    `computeIFProgress` + `errorMessage` (50 → 27); `high` severity
    frontend: 2 → **1** (só `TransactionsContent` pré-existente).
  - **Impact:** frontend offenders 27 → 29 no total (líquido +2 por
    granularidade JSX), mas **T2 zerado** e **T3 high -50%**. Zero
    regressão — 397 vitest tests passam, `tsc --noEmit` limpo em
    `src/` (erros pré-existentes em `tests/` preservados). Zero mudança
    funcional/visual (sweep puramente organizacional + hook extraction).
    Com A6g.4c fechada, a lane A6g.4 está cumprida para arquivos `>500 l`;
    ataques adicionais a T3 med ficariam para A6g.6 (enforcement
    automatizado: ESLint `@typescript-eslint/no-explicit-any` + lint
    rule de function length).

- **A6g.4b — 2ª rodada frontend style sweep (2026-04-22):**
  Continuação de A6g.4 atacando as 6 páginas `>500` linhas ainda no
  baseline + 1 orchestrator monolítico em `transactions/`. Convenção
  Next.js `_components/` colocated (pasta com prefixo `_` é ignorada
  pelo roteador) preserva localidade.
  - **T2 `ts_long_files`:** 6 → 2.
    - `pipeline/page.tsx` (1195 → 368): extrai `ActiveRunCard`
      (360), `FailedRunCard` (169), `HistoryRow` (124), `StageRow`
      (120), `TriggerCard` (119), `NeedsReviewCard` (58),
      `ConnectionChip` (55), `RunHistoryList` (46), hooks
      `useDeepLinkScroll`/`useNowInterval` e helper
      `dismissedFailedRun` para localStorage.
    - `documents/page.tsx` (801 → 347): extrai `DocumentRow`
      (272), `FilterReclassifyBar` (103), `UploadZone` (83),
      `DocumentsTable` (74), `ExtractJsonModal` (55),
      `SortableHead` (53), helpers `sortDocs` (36) /
      `fileFormat` (28) / `classificationHints` (12),
      `NeedsPasswordBanner` (30).
    - `transactions/page.tsx` (741 → 399): extrai `FiltersPanel`
      (135), `TransactionRow` (149), `exportTransactions` (75),
      `SummaryBar` (66), `TransactionsTable` (60), `Pagination`
      (39), `bankOptions` (17), hooks `useTransactionsFetch` (67)
      / `useCategoryOverride` (63) / `useCategoriesAndMembers` (22).
    - `dashboard/page.tsx` (515 → 142): extrai `dashboardHelpers`
      (101, inclui `monthLabelToDateRange` + normalizadores Bar/Pie),
      `BarChartCard` (91), `PieChartCard` (81), `ChartsGrid` (62),
      `KpiRow` (48), `HeaderActions` (40), `AlertCard` (24),
      `ChartSkeleton` (17). Hook `useDashboardData` para load/reload.
    - **Fora desta rodada:** `plano/page.tsx` (630) e
      `plano/alocacao/wizard/page.tsx` (533). Ficam para A6g.4c.
  - **T3 `ts_long_functions`:** 18 → 25 (high severity: 0 →
    mantido). Sub-componentes criados pela decomposição ficam
    em 25-40 linhas — severidade `med`, não `high`. Single HIGH
    `TransactionsContent` (263→147) extraiu 3 hooks e segue como
    orchestrator fino (state de UI + URL sync).
  - **Impact:** frontend offenders (pós-rebase com main)
    continuam em **27** (T2=2, T3=25). 4 das 6 páginas
    monolíticas `>500 l` decompostas; apenas `plano/*` (2
    arquivos) pendentes. Zero regressão — 397 vitest tests
    passam, tsc limpo em `src/` (erros pré-existentes em
    `tests/` preservados). Zero mudança funcional/visual
    (sweep puramente físico). Próximo: A6g.4c ataca as duas
    páginas `plano/*` remanescentes.


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

**F8.5 · Multi-tenant Goals completo (ADR-126; renumerado de ADR-079 duplicado em 2026-04-24):**
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
- [ADR-076](DECISIONS.md#adr-076--design-tokens-unificados-site--relatório) Design tokens unificados site × relatório (fonte única `tokens.json`)
- [ADR-078](DECISIONS.md#adr-078--render-nativo-react--e6-como-exportador-standalone) Render nativo React + E6 como exportador standalone

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

**Workspace Sharing (ADR-125; renumerado de ADR-078 duplicado em 2026-04-24):**

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
- [ADR-072](DECISIONS.md#adr-072--multi-tenancy-workspace_id-scoping-explícito--workspacemember-para-multi-família) Multi-tenancy: `WorkspaceMember` N:N, `get_current_workspace` dependency, tenancy lint AST-based com baseline
- [ADR-073](DECISIONS.md#adr-073--goals-como-entidade-versionada-não-config-estático) Goals como entidade versionada (append-only, derivação server-side)
- [ADR-074](DECISIONS.md#adr-074--tasks-como-entidade-de-1ª-classe-fora-do-relatório) Tasks como entidade de 1ª classe (fora do relatório)
- [ADR-075](DECISIONS.md#adr-075--cutover-cli--web-estratégia-de-transição-faseada-com-adapters) Cutover CLI→Web: estratégia de transição faseada com adapters
- [ADR-077](DECISIONS.md#adr-077--pipeline-adapter-como-contrato-de-cutover-cli--web) Pipeline adapter como contrato de cutover

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
