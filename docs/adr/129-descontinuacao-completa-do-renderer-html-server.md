---
id: ADR-129
type: adr
title: "Descontinuação completa do renderer HTML server-side"
status: Decidido
date: "2026-04-24"
relates_to: []
supersedes: ["[[ADR-078]]", "[[ADR-124]]"]
superseded_by: []
aliases: ["ADR 129"]
tags:
  - area/frontend
  - area/pipeline
  - area/report
  - status/decidido
  - type/adr
size_lines: 164
---

# ADR-129 — Descontinuação completa do renderer HTML server-side

**Status:** Decidido • **Data:** 2026-04-24 • **Supersedes [ADR-124](#adr-124--scriptse6_renderpy-aposentado-em-favor-de-ssr-standalone-do-next)** e encerra a parte
do [ADR-078](#adr-078--render-nativo-react--e6-como-exportador-standalone) que
declarava `e6_render.py` como "exportador standalone".

**Contexto:** ADR-124 (2026-04-23) decidiu matar o script `e6_render.py`
mas **preservar o endpoint HTTP** `GET /v1/reports/{id}/html` migrando
o render para uma rota Next SSR `/reports/[id]/export`. A premissa era
que três consumidores reais precisavam de HTML standalone: email para
contador, backup offline e impressão sem app.

Em 2026-04-24, ao fechar o plano de execução, o usuário afirmou
explicitamente:

1. o produto ainda está em **desenvolvimento** (não em produção);
2. todo o uso é via **interface web** — CLI descontinuada (código pode
   ser removido);
3. **não existe caso de uso** para "download HTML".

Os três consumidores que justificavam ADR-124 nunca foram consumidores
reais — eram hipóteses herdadas da fase CLI. Email não está implementado;
"backup offline" e "impressão sem app" são cobertos pelo export PDF
server-side ([backend/app/services/pdf_renderer.py](../../backend/app/services/pdf_renderer.py)
via Playwright sobre a rota React `/reports/[id]`). A rota Next SSR
proposta por ADR-124 gastaria esforço para servir um endpoint sem
cliente.

O relatório nativo React em `frontend/src/components/report/**` já é o
renderer primário desde [ADR-078](#adr-078--render-nativo-react--e6-como-exportador-standalone)
e ganhou paridade visual com `EXEMPLO_DE_RELATORIO.html` via Fases 0-10
do [Report Premium Plan](../plan/REPORT_PREMIUM/_README.md).

**Decisão:** **Descontinuar completamente o renderer HTML server-side.**
Nenhum Python renderiza relatório; nenhum endpoint HTTP serve HTML de
relatório. O único renderer é a rota React `/reports/[id]`; o único
export server-side é PDF via Playwright.

Escopo concreto da remoção (executado em PR sequencial pós-ADR):

- **Scripts:** `scripts/e6_render.py`, `scripts/e6/` (`sanitize.py`,
  `validate.py`, `__init__.py`), `scripts/e6_regen.py`.
- **Pipeline:** `pipeline/stages/e6.py`, `pipeline/stage_materialization.py`,
  `tests/unit/pipeline/test_stage_materialization.py`. Remover entradas
  `"E6"`, `"E6-final"` e variantes de `STAGE_REGISTRY`, `FULL_ORDER`,
  `DETERMINISTIC_ORDER`, mapeamentos `_STAGE_TO_DIR`/`_STAGE_TO_SUFFIX`
  (se houver), e `_E6_DISK_INPUTS`.
- **Backend API:** [backend/app/api/reports.py](../../backend/app/api/reports.py)
  — rotas `GET /html` e `GET /download.html`;
  [backend/app/api/admin/reports.py](../../backend/app/api/admin/reports.py)
  — rota admin `/html`;
  `backend/app/application/report/get_report_html.py`
  — use cases inteiros (`get_report_html`, `download_report_html`).
- **Backend task:** [backend/app/tasks/pipeline_task.py](../../backend/app/tasks/pipeline_task.py)
  `_create_report_from_output` deixa de procurar `.html`. `Report` passa
  a ser criado sem `html_path`.
- **Backend seed:** [backend/app/services/seed.py](../../backend/app/services/seed.py)
  `seed_existing_reports` inteiro é removido (dependia de CLI gerando
  `output/relatorio_financeiro_*.html`). `ensure_seed_user` permanece.
  O entrypoint `backend/seed_db.py` é removido junto — não há mais o
  que importar do filesystem.
- **Modelo + migration:** [backend/app/models/report.py](../../backend/app/models/report.py)
  — campo `html_path` **removido**. Nova migration Alembic
  `DROP COLUMN html_path` (Opção A — drop total; não é nullable).
- **Frontend dead code:** `getReportHtmlUrl`, `getReportHtmlDownloadUrl`
  em `frontend/src/lib/api/reports.ts` — não consumidos por nenhum
  componente; removidos junto. `frontend/src/lib/pipelinePhases.ts` e
  `frontend/src/app/(app)/reports/[id]/page.tsx` perdem labels do stage
  E6.
- **Design tokens:** `design-tokens/build.py` emite hoje **dois** CSS
  (um para Next, outro standalone para E6 HTML). Simplifica para único
  emit — bloco standalone é removido.
- **Docs:** `docs/e6_render_readme.md` deletado; `EXEMPLO_DE_RELATORIO.html`
  mantido como **referência visual histórica** (não é entregável).
- **Refs residuais:** `scripts/e7_review.py` tem `print("...python
  scripts/e6_render.py")` em docstrings e no fim — atualizar para
  "relatório disponível em `/reports/[id]`" ou remover se o script
  inteiro é CLI-only e deprecated.
- **Testes removidos:** `tests/test_e6_golden_execution.py`,
  `tests/test_e5_e6_e5n_edges.py` (parte E6), `tests/test_regression.py`
  (seções E6), `tests/test_design_tokens_build.py` (checks de CSS
  standalone), `backend/tests/test_reports.py` (cases `/html`),
  `test_report_tasks_snapshot.py` (asserts `html_path`),
  `test_golden_pipeline.py` (wait por HTML), `internal_ops/test_list_reports.py`
  (campo `html_path` no shape), `api/admin/test_docs_metrics_reports.py`
  (se houver), `backend/tests/factories/builders.py` e
  `fixtures/pipeline_runs.py` (factories que preenchem `html_path`),
  `frontend/tests/mocks/handlers.ts` (mock de `/html`).

**Trabalho cancelado (precisa de alinhamento com agentes ativos):**

- **Report Premium Fase 11** — branch `agent/report-premium/phase11-e6-parity/20260424-1558`
  construía a rota Next SSR de export. **Cancelada.** Branch fica como
  histórico; não será mergeada. Coordenação com o agente ativo:
  anúncio no `docs/BACKLOG.md` + na sprint atual.
- **Report Premium Fase 13** (como planejada) — rollout + delete de
  `e6_render.py`. Absorvida pela execução desta ADR (PR seguinte).
- **Fase 11.1 — `StaticReportModeProvider`** (commit `667ed4d` já em
  `main`): **mantida.** O provider estático é útil independente do export
  HTML — funciona como refactor limpo do `ReportModeContext`. Ver
  [ADR-124 §Implementação §Onda 11.1](#adr-124--scriptse6_renderpy-aposentado-em-favor-de-ssr-standalone-do-next)
  para contexto histórico.

**Consequências:**

- ✅ **Um renderer só**, sem duplicação. Cada mudança visual viaja
  sozinha no React; zero risco de divergência entre HTML server e
  React.
- ✅ **~5500 LOC removidos**: `e6_render.py` (4867) + `e6/*` + stage
  wrapper + materialization + 3 endpoints + use cases + seed importer
  + dead code frontend + testes. Bônus arquitetural: o único uso do
  `MaterializationBridge` para "espelhar DB → disco" some; pipeline
  fica 100 % ArtifactStore-native para stages de domínio.
- ✅ **Coluna `html_path` drop total** (Opção A). `Report` fica sem
  campo morto; schema enxuto. Sem prod = janela perfeita para limpar
  sem migration reversa complexa.
- ✅ PDF server-side **continua funcionando** exatamente como hoje
  (Playwright sobre `/reports/[id]?print=1`).
- ⚠️ Agente `phase11-e6-parity` perde o trabalho em progresso (~4h
  de docs + reconnaissance). Comunicação necessária; branch fica
  arquivada.
- ⚠️ Usuários que (eventualmente, no futuro) pedirem "link
  compartilhável do relatório" vão precisar da rota React autenticada,
  não um HTML estático. Solução: share link público autenticado
  via token — décima próxima fase se surgir demanda.
- ❌ **`EXEMPLO_DE_RELATORIO.html` perde utilidade operacional** —
  continua no repo como spec visual histórica, mas não há mais
  script que regenere.
- ❌ Se algum ambiente de dev ainda depender de `seed_existing_reports`
  (importar HTMLs de `output/`), quebra. Mitigação: ambientes novos
  seguem fluxo via UI (upload + "Gerar Relatório") — não há mais
  atalho CLI → seed.

**Ordem de execução (PR sequencial pós-merge desta ADR):**

1. Backend API + use cases + modelo + migration drop `html_path` +
   pipeline_task sem HTML path.
2. Pipeline: remove stage E6 + `stage_materialization` + entradas em
   registry/orchestrator/spec.
3. Scripts: deleta `scripts/e6_render.py`, `scripts/e6/`,
   `scripts/e6_regen.py`; atualiza mensagens em `scripts/e7_review.py`.
4. Frontend dead code: remove `getReportHtmlUrl*`; limpa `pipelinePhases.ts`
   e `reports/[id]/page.tsx` de labels E6; simplifica mocks.
5. Design tokens: remove emit standalone do `design-tokens/build.py`.
6. Seed: remove `seed_existing_reports` + `backend/seed_db.py`;
   `ensure_seed_user` permanece (com possível relocação para
   `backend/app/services/bootstrap.py`).
7. Testes: remove os listados acima; atualiza `backend/tests/factories/builders.py`
   e fixtures para não preencher `html_path`.
8. Docs: remove `docs/e6_render_readme.md`; atualiza ARCHITECTURE.md
   (§7 tabela de stages, §8 data flow, §10 tree de dirs, §11
   persistência), CLAUDE.md (§Design System, §Convenções do pipeline),
   ROADMAP.md (crítical path), plan/REPORT_PREMIUM/_README.md (Fases 11/12/13
   canceladas/redirecionadas), BACKLOG.md (remove lane + marca
   concluída a sub-sprint).

Relaciona-se a: ADR-076 (design system), ADR-117 (Report Premium),
ADR-124 (superseded), ADR-083 (ArtifactStore — materialization bridge
agora pode ser simplificada), ADR-127 + ADR-128 (últimas stages de
domínio migradas para store; E6 era o último bolsão de disco intencional
em stage de domínio), ADR-111 (stateless — E6 forçava materialização
para filesystem, violação pragmática agora removida).
