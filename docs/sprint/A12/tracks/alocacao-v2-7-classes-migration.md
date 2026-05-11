---
id: TRACK-alocacao-v2-7-classes-migration
type: track
title: "Track Alocação v2 — migração schema 4→7 classes e desvio backend-driven"
sprint: A12
status: ready
created_at: "2026-05-11"
consumed_at: null
agent_role: senior-cto
tags:
  - type/track
  - sprint/a12
  - status/ready
  - area/methodology
  - area/persistence
  - area/frontend
  - methodology/auvp
---

# Track Alocação v2 — migração schema 4→7 classes

> **Lane:** [[A12.alocacao-v2-migration]]
> · **ADR canônica:** [[ADR-141]] (Proposto → Decidido no PR de implementação)
> · **Origem:** débito explícito da Fase A entregue em A11 (`AlocacaoAtualVsAlvoCard`)
> · **Branch prefix:** `agent/alocacao-v2/*`

## Contexto

Fase A (A11 · 2026-05-11) entregou redesenho do card S3 "Alocação · Atual vs Alvo" calculando desvio **client-side** sobre schema v1 (4 buckets). v1 v2 ([ADR-141]) define 7 classes canônicas alinhadas com [ADR-193] (taxonomia de classes de ativo no E5) e tem `derived.desvio_por_classe` + `derived.desvio_max_pct` nativos no backend — eliminando a aproximação de mapeamento 10→4 que vive hoje no frontend.

## Escopo

1. **Backend serializer.** Atualizar `backend/app/services/pipeline_adapter.py::_serialize_alocacao_goal` para emitir v2 (7 buckets + `derived.*`). Calcular `desvio_max_pct` + `desvio_por_classe` no serviço (input: `Goal.params_json` + `tabela_classes` do investimentos analyzer). Compatibilidade: se workspace ainda tem Goal v1 no DB, migrator interno traduz com split default 50/25/25 para pré/pós/IPCA (ADR-141 §Migração).

2. **Seed.** Corrigir `backend/app/scripts/seed_goals_workspace.py` — atualmente escreve `rf_pct/rv_pct/alternativos_pct` (3 keys legadas) inconsistente com serializer (`renda_fixa_pct` etc.). Refazer para gravar v2 diretamente nos novos workspaces.

3. **Wizard `/plano/alocacao`.** Migrar `Step1Distribution.tsx`, `AlocacaoBar.tsx`, `AlocacaoSummary.tsx` para 7 sliders. Preserva CTA "Próximo aporte sugerido: classe X (-Y%)" como derivado do `desvio_por_classe`.

4. **Frontend card.** Em `AlocacaoAtualVsAlvoCard`:
   - Remover `alocacaoBucketMapper.ts` (cálculo client-side); consumir `derived.desvio_por_classe` direto do payload.
   - Atualizar `conclusionUtils.ts::buildAlocacaoFooter` para ler `derived.*` em vez de recomputar.
   - Tabela passa a ter 7 linhas (não 4); validar densidade em 375px.

5. **Tombstones.** Remover de `config/report_layout.yaml`:
   - `charts.alocacao_atual` (S3) `enabled: false`
   - `charts.alocacao_alvo` (S3) `enabled: false`
   - `cards.investimentos_classe` (S3) `enabled: false`
   - `chart_canvas_map.alocacao_atual` e `.alocacao_alvo` (dead-code desde ADR-129)
   - Entries em `ALL_CHART_IDS` (codegen regenera)

6. **Pipeline enforcers.** Os 4 lugares que exigem `alocacao_atual`/`alocacao_alvo` em `narrativas.charts` (mapeados pelo data-engineer 2026-05-11):
   - `scripts/e7_review.py::_REQUIRED_CHARTS`
   - `pipeline/domain/services/narrativas/format_helpers.py::required_charts`
   - `pipeline/domain/services/narrativas/charts_narrator.py`
   - `tests/test_e5n_builder_decomposition.py`

   Decisão: ou (a) substituir os chart_ids `alocacao_atual`/`alocacao_alvo` por `alocacao_atual_vs_alvo` (novo) consistentemente, ou (b) manter os 2 chart_ids como aliases narrativos do mesmo card e descartar geração só dos templates. Validar com data-engineer no PR.

7. **Goldens E5N + tests pipeline.** Regenerar `tests/test_e5n_golden_execution.py` e `tests/test_e5_golden_execution.py` se templates de `alocacao_*` mudarem para refletir v2. Schema validation em `config/schemas/goal.alocacao_alvo.v2.schema.json` é fonte; v1 schema removido **só** se nenhum workspace ativo emite v1 (snapshot DB necessário).

8. **ADR-141.** Flippar `Proposto` → `Decidido (A12.alocacao-v2)` no PR de implementação. Adicionar bidirecional `superseded_by` em v1 ↔ `supersedes` em v2 se decidirmos retirar `goal.alocacao_alvo.schema.json` v1.

## Critérios de aceite

- [ ] `pipeline_adapter._serialize_alocacao_goal` emite v2 com 7 chaves + `derived.desvio_max_pct` + `derived.desvio_por_classe`.
- [ ] Wizard `/plano/alocacao` editor de 7 sliders + validação `Σ = 100`.
- [ ] `AlocacaoAtualVsAlvoCard` consome `derived.*` (sem cálculo client-side); `alocacaoBucketMapper.ts` deletado.
- [ ] Tombstones do YAML removidos (entries excluídas em vez de `enabled: false`).
- [ ] Suíte pipeline + backend verde após remoção de chart_ids `alocacao_atual`/`alocacao_alvo` (ou rename consistente).
- [ ] Goldens E5N regenerados com revisão manual de diff.
- [ ] ADR-141 Decidida; ADR-077 v1 schema com `superseded_by` se removido.

## Pré-requisitos

- A11.report-publication mergeado (já está em main, PR #185).
- A11.cat-learning-loop **não** é pré-requisito (escopos disjuntos).
- Lane pode rodar em paralelo com outras tracks de A12.

## Time-box

5d eng (1d backend serializer + migrator, 1d seed + wizard, 1d frontend card refactor, 1d tests + tombstones, 1d goldens E5N + ADR flip).

## Riscos

- **Migração de seeds existentes.** Se houver Goals v1 ativos em DBs de demo/dev, o migrator precisa ser idempotente. Critério: rodar migration em fixture de smoke test e validar `Σ inputs = 100`.
- **Wizard regressão visual.** 7 sliders em mobile (375px) podem virar fadiga visual — co-design com `product-designer` antes do PR.
- **Pipeline enforcer rename.** Mudar `alocacao_atual` em 4 lugares é mecânico mas requer atenção a ordering (E5N decomposition tests fazem set-equality).
