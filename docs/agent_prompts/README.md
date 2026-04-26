# Agent Prompts — índice e convenções

Pasta contém **prompts self-contained** para rodar uma task específica do
Sprint A6 (ou outra sprint transversal). Cada prompt é consumido por um
agente LLM rodando em branch `agent/<slug>/<timestamp>` — deve conter
contexto suficiente para a task começar sem precisar ler o BACKLOG
inteiro.

## Índice de prompts

> **Fonte única de status/ocupação:** [../BACKLOG.md §Lanes abertas agora](../BACKLOG.md#lanes-abertas-agora--pickup-table). Este índice lista apenas **o que tem prompt escrito** — status omitido de propósito para evitar drift entre dois lugares.

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
| F7F-Local Console interno pré-produção (IA-0) — UI Next separada + anonimização + auth yaml | [track_f7f_local.md](track_f7f_local.md) | 3 (Lane C6, independente de 7A/B/C) | `agent/f7f-local/*` |
| F9.0 Audit referências legadas + exhaustividade `STAGE_RENAME_MAP` | [track_f9_0_audit.md](track_f9_0_audit.md) | F9 (1/7) | `agent/f9-stage-rename/0-audit/*` |
| F9.1 `git mv pipeline/stages/e*.py` → descritivos | [track_f9_1_pipeline_stages_rename.md](track_f9_1_pipeline_stages_rename.md) | F9 (2/7) | `agent/f9-stage-rename/1-pipeline-stages/*` |
| F9.2 Strings literais `"E*"` → descritivas em produção (master + T1 ✅) | [track_f9_2_string_literals.md](track_f9_2_string_literals.md) | F9 (3/7) | `agent/f9-stage-rename/2-strings/*` |
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

Lanes com prompt inline (escopo documentado direto na linha da tabela "Lanes abertas agora" do BACKLOG, sem prompt dedicado): A6g.6b, A6g.2c, A6e.3c, A6e.events-migration, A6e.events-followup, A6g.2b, A6c, **v2.1, v2.2, v2.3, v2.6, v2.7, v2.9, v2.10** (escopo curto — ver linhas v2.X em [BACKLOG.md › Report Premium UI v2](../BACKLOG.md#report-premium-ui--paridade-com-exemplo_de_relatoriohtml) ou no meta-prompt [track_report_v2.md](track_report_v2.md) §3). **v2.5 absorvida em v2.E.7** ([track_report_v2_charts_ux.md §3 v2.E.7](track_report_v2_charts_ux.md)).

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
