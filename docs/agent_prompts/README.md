# Agent Prompts — índice e convenções

Pasta contém **prompts self-contained** para rodar uma task específica do
Sprint A6 (ou outra sprint transversal). Cada prompt é consumido por um
agente LLM rodando em branch `agent/<slug>/<timestamp>` — deve conter
contexto suficiente para a task começar sem precisar ler o BACKLOG
inteiro.

## Índice de prompts

> **Fonte única de status/ocupação:** [../BACKLOG.md §Lanes abertas agora](../BACKLOG.md#lanes-abertas-agora--pickup-table) (A6) e [§Lanes A7](../BACKLOG.md#lanes-a7--pickup-table) (A7). Este índice lista apenas **o que tem prompt escrito** — **status omitido de propósito** para evitar drift entre dois lugares. Marcadores ✅/🚧/☐ **não pertencem** às linhas desta tabela; descrição da lane (escopo, dependências) é o único conteúdo permitido aqui. Confirme estado real com `git for-each-ref --sort=-committerdate refs/remotes/origin/agent/` antes de pickup.

| Lane | Arquivo | Onda | Branch prefix |
| --- | --- | --- | --- |
| A6g.2 Pipeline Code Style Sweep | [track_a6g2_pipeline_style_sweep.md](track_a6g2_pipeline_style_sweep.md) | 1 | `agent/a6g2-pipeline-style/*` |
| A6g.4 Frontend Code Style Sweep | [track_a6g4_frontend_style_sweep.md](track_a6g4_frontend_style_sweep.md) | 1 | `agent/a6g4-frontend-style/*` |
| A6f.1 Pipeline-as-Service (HTTP boundary) | [track_a6f1_pipeline_service.md](track_a6f1_pipeline_service.md) | 2 (greenfield) | `agent/a6f1-pipeline-service/*` |
| A6g.5 Tests Sweep (fakes + nomes descritivos) | [track_a6g5_tests_sweep.md](track_a6g5_tests_sweep.md) | 2 | `agent/a6g5-tests-sweep/*` |
| A6e.3 Application Layer (use cases — slice FamilyMember+Category+Goal) | [track_a6e3_use_cases.md](track_a6e3_use_cases.md) | 2 | `agent/a6e3-use-cases/*` |
| A6e.5 `/api/v1/` prefix + aliases + OpenAPI versionado | [track_a6e5_v1_prefix.md](track_a6e5_v1_prefix.md) | 2 | `agent/a6e5-v1-prefix/*` |
| A6e.3b Use cases remanescentes (ConfigBlob+Document+Task) | [track_a6e3b_use_cases_rest.md](track_a6e3b_use_cases_rest.md) | 2 | `agent/a6e3b-use-cases-rest/*` |
| A6e.4 Routers finos (≤50 linhas/endpoint) + teste AST | [track_a6e4_thin_routers.md](track_a6e4_thin_routers.md) | 2 | `agent/a6e4-thin-routers/*` |
| A6g.7 Go prep (`.golangci.yml` + CI skip + `services/` skeleton + ADR-113) | [track_a6g7_go_prep.md](track_a6g7_go_prep.md) | 3 | `agent/a6g7-go-prep/*` |
| A6e.events Domain events tipados (ADR-101 R17) — ex-`A6e.6` | [track_a6e_events_domain_events.md](track_a6e_events_domain_events.md) | 2 | `agent/a6e-events/*` |
| A6g.6 Enforcement automatizado (Ruff + ESLint + pre-commit + testes AST) | [track_a6g6_enforcement.md](track_a6g6_enforcement.md) | 3 | `agent/a6g6-enforcement/*` |
| A6g.3 Backend Python code style sweep (services, repos, models, schemas) | [track_a6g3_backend_style_sweep.md](track_a6g3_backend_style_sweep.md) | 3 | `agent/a6g3-backend-style/*` |
| A6g.3b Decimal money migration (`float` BRL/USD → `Decimal`) | [track_a6g3b_decimal_money_migration.md](track_a6g3b_decimal_money_migration.md) | 3 | `agent/a6g3b-decimal-money/*` |
| F7F-Local Console interno pré-produção (IA-0) — UI Next separada + anonimização + auth yaml | [track_f7f_local.md](track_f7f_local.md) | 3 (Lane C6, independente de 7A/B/C) | `agent/f7f-local/*` |
| F9.0 Audit referências legadas + exhaustividade `STAGE_RENAME_MAP` | [track_f9_0_audit.md](track_f9_0_audit.md) | F9 (1/7) | `agent/f9-stage-rename/0-audit/*` |
| F9.1 `git mv pipeline/stages/e*.py` → descritivos | [track_f9_1_pipeline_stages_rename.md](track_f9_1_pipeline_stages_rename.md) | F9 (2/7) | `agent/f9-stage-rename/1-pipeline-stages/*` |
| F9.2 Strings literais `"E*"` → descritivas em produção (master + sub-fatias 9.2a-e) | [track_f9_2_string_literals.md](track_f9_2_string_literals.md) | F9 (3/7) | `agent/f9-stage-rename/2-strings/*` |
| F9.2a Pipeline core (artifact_store + llm + stages + domain/services) | [track_f9_2a_pipeline_core_strings.md](track_f9_2a_pipeline_core_strings.md) | F9 (3a/7) | `agent/f9-stage-rename/2a-pipeline-core/*` |
| F9.2b Scripts (e0/e2/e3/e4/e5/e7/e15 internos, exceto e_reset) | [track_f9_2b_scripts_strings.md](track_f9_2b_scripts_strings.md) | F9 (3b/7) | `agent/f9-stage-rename/2b-scripts/*` |
| F9.2c `scripts/e_reset.py` deprecation warning + flip interno | [track_f9_2c_e_reset_deprecation.md](track_f9_2c_e_reset_deprecation.md) | F9 (3c/7) | `agent/f9-stage-rename/2c-e-reset/*` |
| F9.2d Backend residual + tests não-golden | [track_f9_2d_backend_tests.md](track_f9_2d_backend_tests.md) | F9 (3d/7) | `agent/f9-stage-rename/2d-backend-tests/*` |
| F9.2e Closeout F9.2 (audit + docs + destrava F9.3) | [track_f9_2e_closeout.md](track_f9_2e_closeout.md) | F9 (3e/7) | `agent/f9-stage-rename/2e-closeout/*` |
| F9.3 Alembic migration `pipeline_artifacts.stage` em massa | [track_f9_3_alembic_migration.md](track_f9_3_alembic_migration.md) | F9 (4/7) | `agent/f9-stage-rename/3-alembic/*` |
| F9.4 `git mv scripts/e*.py` + alias CLI compat | [track_f9_4_scripts_rename.md](track_f9_4_scripts_rename.md) | F9 (5/7) | `agent/f9-stage-rename/4-scripts/*` |
| F9.5 Guardrail hard-fail contra identificadores legados | [track_f9_5_guardrail_hardfail.md](track_f9_5_guardrail_hardfail.md) | F9 (6/7) | `agent/f9-stage-rename/5-guardrail/*` |
| F9.6 Cleanup final: remover wrappers compat, aliases, globals | [track_f9_6_cleanup.md](track_f9_6_cleanup.md) | F9 (7/7) | `agent/f9-stage-rename/6-cleanup/*` |
| Report a11y + Playwright finalize (resíduo F12) | [track_report_a11y_finalize.md](track_report_a11y_finalize.md) | Report Premium · resíduo F12 | `agent/report-a11y-finalize/*` |
| Report Premium v1 polish (resíduo F13) | [track_report_v1_polish.md](track_report_v1_polish.md) | Report Premium · resíduo F13 | `agent/report-v1-polish/*` |
| **Report Premium UI v2 — meta-prompt + ondas** (paralelização explícita das 10 lanes v2) | [track_report_v2.md](track_report_v2.md) | Report Premium · v2 | `agent/report-v2-*/*` |
| Report v2.4 — T2 Aportes seção real (substituir stub) | [track_report_v2_t2_aportes.md](track_report_v2_t2_aportes.md) | Report Premium · v2 (Onda B) | `agent/report-v2-t2-aportes/*` |
| Report v2.D.1 + v2.8 — Snapshot changelog engine + comparisons/changelog ON | [track_report_v2_changelog_engine.md](track_report_v2_changelog_engine.md) | Report Premium · v2 (Onda D + ativação) | `agent/report-v2-changelog-engine/*` |
| **Report Onda v2.E — charts UX (8 sub-lanes: PeriodToggle + 5 charts Recharts→Chart.js + ScoreCard plug + re-baseline)** | [track_report_v2_charts_ux.md](track_report_v2_charts_ux.md) | Report Premium · v2 (Onda E) | `agent/report-v2-{period-toggle,fluxo-types,fluxo-mensal-chartjs,receita-bar-chartjs,despesas-doughnut-chartjs,receita-despesa-chartjs,score-card-plug,charts-rebaseline}/*` |
| Report Appearance Menu (refinement ADR-121 Fase 4 — popover Aa unifica fonte+tema) | [track_report_appearance_menu.md](track_report_appearance_menu.md) | Report Premium · refinement | `agent/report-appearance-menu/*` |
| **A7.0 ConfigStore protocol + adapters** (Sprint A7 · Onda 1 BLOQUEANTE) | [track_a7_0_config_store.md](track_a7_0_config_store.md) | A7 (1/4) | `agent/a7-0-config-store/*` |
| **A7.1 Cutover `materialize_config` → ConfigStore** (Sprint A7 · Onda 2) | [track_a7_1_cutover_materialize.md](track_a7_1_cutover_materialize.md) | A7 (2/4) | `agent/a7-1-cutover-materialize/*` |
| **A7.2a Decision aggregate + UI Plano de Ação + migrator** (Sprint A7 · Onda 2) | [track_a7_2a_decision_aggregate.md](track_a7_2a_decision_aggregate.md) | A7 (2/4) | `agent/a7-2a-decision-aggregate/*` |
| **A7.2b Tabelas globais fiscal/market versionadas** (Sprint A7 · Onda 2) | [track_a7_2b_fiscal_market_tables.md](track_a7_2b_fiscal_market_tables.md) | A7 (2/4) | `agent/a7-2b-fiscal-market-tables/*` |
| **A7.3 Catalog + Override resolver** (Sprint A7 · Onda 3) | [track_a7_3_catalog_override.md](track_a7_3_catalog_override.md) | A7 (3/4) | `agent/a7-3-catalog-override/*` |
| **A7.4 Metodologia → docs/methodology/** (Sprint A7 · paralelo livre) | [track_a7_4_methodology_docs.md](track_a7_4_methodology_docs.md) | A7 (livre) | `agent/a7-4-methodology-docs/*` |
| **A7.5 Cleanup final** (Sprint A7 · Onda 4 BLOQUEANTE) | [track_a7_5_cleanup.md](track_a7_5_cleanup.md) | A7 (4/4) | `agent/a7-5-cleanup/*` |
| **Onda 5 Suggestion full-stack** (Direção E — redesign de interfaces) | [track_onda_5_suggestion_aggregate.md](track_onda_5_suggestion_aggregate.md) | Direção E (5/6) | `agent/onda-5-suggestion-aggregate/*` |
| **Onda 1 Migration kanban→task + notes→workspace_notes** (Direção E — paralelizável com Onda 5) | [track_onda_1_kanban_task_migration.md](track_onda_1_kanban_task_migration.md) | Direção E (1/6) | `agent/onda-1-kanban-task-migration/*` |
| **Onda 7 P0 bloqueadores** ✅ entregue 2026-04-29 (5 fixes em main, vitest 691 passing, ADR-156) | [track_onda_7_p0_blockers.md](track_onda_7_p0_blockers.md) | Direção E pós-revisão (7/9) | `agent/onda-7-p0-blockers/*` |
| **Onda 8 Coerência metodológica** (Direção E pós-revisão · ~5-7d · P1 — Cerbasi/AUVP/Perini completos) | [track_onda_8_methodology_coherence.md](track_onda_8_methodology_coherence.md) | Direção E pós-revisão (8/9) | `agent/onda-8-methodology-coherence/*` |
| **Onda 9 Design system polish + mobile** (Direção E pós-revisão · ~3d · P2 — paralelizável) | [track_onda_9_design_system_polish.md](track_onda_9_design_system_polish.md) | Direção E pós-revisão (9/9) | `agent/onda-9-design-system-polish/*` |
| **IRPF Full Schema (E1.6)** — extração completa da declaração (rendimentos + imposto + dependentes + dedutíveis), não só Bens & Direitos. Desbloqueia KPIs de renda anual e otimização tributária. ADR obrigatória + financial-planner G0. | [track_irpf_full_schema.md](track_irpf_full_schema.md) | independente | `agent/irpf-full-schema/*` |
| **IRPF Full Schema UI** — relatório premium consome `output["irpf_kpis"]` do E5: 2 seções novas (Renda anual + Otimização tributária), cards/charts em Chart.js, codegen YAML. **G4 (product-designer) obrigatório.** Pré-req: lane `irpf-full-schema` ✅ mergeada. | [track_irpf_full_schema_ui.md](track_irpf_full_schema_ui.md) | independente (paralelo a outras IRPF sub-lanes) | `agent/irpf-full-schema-ui/*` |
| **IRPF Full Schema Goldens** — fixtures sintéticas (completo + simplificado + edge cases) + opcional 1 real anon + golden tests + stage test com FakeLLMClient. Fecha DoD da ADR-157. Pré-req: lane `irpf-full-schema` ✅ mergeada. | [track_irpf_full_schema_goldens.md](track_irpf_full_schema_goldens.md) | independente (paralelo a outras IRPF sub-lanes) | `agent/irpf-full-schema-goldens/*` |
| **IRPF Full Schema Cutover** — flag `MATHOMS_E16_SUPERSEDES_E15_BENS` por workspace + short-circuit do E1.5 quando E1.6 disponível + adapter Decimal→float no consumer + ADR nova. **Bloqueante:** depende de `irpf-full-schema-goldens` ✅ + ≥3 declarações reais validadas paridade byte-byte. | [track_irpf_full_schema_cutover.md](track_irpf_full_schema_cutover.md) | bloqueante (após UI + goldens) | `agent/irpf-full-schema-cutover/*` |
| **Pipeline Review — Quick Unblock (caminho A)** — stop-gap: `handleResume` aprova `StageReview` pendentes implicitamente + copy honesta no `NeedsReviewCard` + lista `validation_errors`. Destrava runs em `needs_review`. **Mutuamente exclusivo** com `pipeline-review-screen` (B). | [track_pipeline_review_quick_unblock.md](track_pipeline_review_quick_unblock.md) | hotfix UX (independente) | `agent/pipeline-review-quick-unblock/*` |
| **Pipeline Review — Tela de revisão real (caminho B)** — rota `/pipeline/runs/[id]/reviews` (lista + detalhe + editor JSON), `NeedsReviewCard` vira ponteiro. ADR obrigatória; sign-off `product-designer`. **Substitui** A se A foi mergeado antes. | [track_pipeline_review_screen.md](track_pipeline_review_screen.md) | produto premium (independente) | `agent/pipeline-review-screen/*` |
| **Real estate efficiency feature** (ADR-160) — nova feature S4 do relatório premium: tabela imóvel direto vs FII + calculadora interativa + 3 ações canônicas via Suggestion (ADR-153) + Decision (ADR-136). G0 (financial-planner) e G4 (product-designer) **já feitos** na ADR. ~3-5 dias dev. | [track_real_estate_efficiency.md](track_real_estate_efficiency.md) | produto premium (independente) | `agent/real-estate-efficiency/*` |

Lanes com prompt inline (escopo documentado direto na linha da tabela "Lanes abertas agora" do BACKLOG, sem prompt dedicado): A6g.6b, A6g.2c, A6e.3c, A6e.events-migration, A6e.events-followup, A6g.2b, A6c, **v2.1, v2.2, v2.3, v2.5, v2.6, v2.7, v2.9, v2.10** (escopo curto — ver linhas v2.X em [BACKLOG.md › Report Premium UI v2](../BACKLOG.md#report-premium-ui--paridade-com-exemplo_de_relatoriohtml) ou no meta-prompt [track_report_v2.md](track_report_v2.md) §3). Status (entregue / em andamento / aberta) **somente no BACKLOG**.

## Antes de começar — pickup protocol

1. Verifique a lane na tabela "Lanes abertas agora" do BACKLOG.
2. Rode o check de colisão (CLAUDE.md §Antes de pegar uma task):

   ```bash
   git fetch origin
   git for-each-ref --sort=-committerdate \
     --format='%(committerdate:iso) %(refname:short) %(subject)' \
     refs/remotes/origin/agent/ | head -15
   ```

3. Se já existe `origin/agent/<slug>-*` com commit <24h → pegue **outra**
   lane. Se stale >24h → anuncie retomada e continue OU abra nova
   branch.
4. Crie branch **antes** da primeira edição:
   `git checkout -b agent/<slug>/$(date +%Y%m%d-%H%M)`.

## Cabeçalho padrão de um prompt

Todo prompt novo deve começar com este bloco — permite ao agente decidir
em 10s se essa é a lane dele:

```markdown
# Track <Lane ID> — <Título curto>

> **Lane ID:** A6g.2 (exemplo)
> **Branch prefix:** `agent/a6g2-pipeline-style/*`
> **Depende de:** A6g.1 ✅ (baseline de ofensores)
> **Paralelo com:** A6g.4 frontend sweep (zero overlap de arquivos)
> **Conflita com:** qualquer commit ativo em `scripts/` ou `pipeline/`
> **Onda:** 1
> **Objetivo (1 frase):** aplicar §Code style do CLAUDE.md em X, Y, Z.
> **Fonte de verdade das regras:** [CLAUDE.md §Code style](../../CLAUDE.md#code-style)
```

Depois do cabeçalho, o corpo livre (regras, targets, tiers, gates,
rollback). Ver `track_a6g2_*.md` e `track_a6g4_*.md` como modelo.

## Criando um novo prompt

1. Nome: `track_<lane>_<descricao-curta>.md` (ex.:
   `track_a6e3_use_cases.md`). Lane em lowercase + pontos substituídos
   por nada (`a6e.3` → `a6e3`).
2. Comece com o cabeçalho padrão acima.
3. Inclua pelo menos: **Regras inegociáveis** (do CLAUDE.md), **Targets
   por tier** (tier 1 seguro, tier 2 opcional, tier 3 fora de escopo),
   **Sequência de commits** sugerida, **Gates de push** (pytest, lint,
   drift check), **Rollback criteria**, **Coordenação com outros
   agentes** (paralelos vs conflitantes), **O que NÃO entrega**.
4. Adicione linha na tabela "Índice de prompts" acima.
5. Adicione entrada na tabela "Lanes abertas agora" do BACKLOG.
6. Commit separado: `docs(agent-prompts): add track_<lane>_<desc> (<motivo>)`.

## Por que prompts dedicados?

- **Onboarding em 5 minutos**: agente lê 1 arquivo, não 3 (BACKLOG +
  CLAUDE + ADR relevante).
- **Contexto cristalizado**: gates, rollback criteria, o que **não**
  tocar. Reduz oscilação entre sessões do mesmo agente.
- **Anti-colisão**: branch prefix + lane ID explícitos permitem grep
  rápido ao decidir pickup.
- **Rastreio**: commits no slice citam Lane ID (`(A6g.2 — T1.a)`),
  fácil correlacionar com prompt original.
