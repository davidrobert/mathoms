---
id: ADR-141
type: adr
title: "Goal alocação-alvo schema v2 (7 classes AUVP)"
status: Proposto
date: "2026-04-27"
phase: A12
relates_to: ["[[ADR-075]]", "[[ADR-140]]", "[[ADR-193]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 141"]
tags:
  - area/frontend
  - area/money
  - area/persistence
  - methodology/auvp
  - status/proposto
  - type/adr
size_lines: 75
---

# ADR-141 — Goal alocação-alvo schema v2 (7 classes AUVP)

**Status:** Proposto (A12) • **Data:** 2026-04-27, promoção Roadmap→Proposto em 2026-05-11 • **Implementação:** schema candidato em `config/schemas/goal.alocacao_alvo.v2.schema.json`; backend (`pipeline_adapter._serialize_alocacao_goal`), frontend (`plano/alocacao/page.tsx`) e seeds operam em v1. Card de relatório S3 (`AlocacaoAtualVsAlvoCard`) entregue em A11 calcula desvio client-side sobre v1 — débito explícito desta ADR.

**Contexto:** Auditoria multi-agente (rodada 1, item 9; rodada 2, item B2) identificou que a caracterização da AUVP em [methodology.md](../config/methodology.md) e nos schemas era reducionista. AUVP é **alocação multi-classe + rebalanceamento por aporte via Diagrama do Cerrado** — não "fundamentalista + FIIs" como dizia v1 do `methodology.md`. O schema v1 de alocação-alvo (`renda_fixa_pct`, `acoes_pct`, `imoveis_reits_pct`, `liquidez_usd_pct` — 4 buckets) cola RF pré/pós/IPCA em um único bucket e mistura ações BR com internacionais — perde o que é distintivo na metodologia.

**Decisão:** Criar `goal.alocacao_alvo.v2.schema.json` com 7 classes canônicas AUVP:

- `rf_pos_pct` (Tesouro Selic, CDB CDI+, LCI/LCA CDI+)
- `rf_pre_pct` (Tesouro Prefixado, CDB pré, debêntures pré)
- `rf_ipca_pct` (Tesouro IPCA+, CDB IPCA+, debêntures IPCA+, CRI/CRA)
- `acoes_br_pct` (BOVA11, ações domésticas)
- `acoes_int_pct` (IVVB11, S&P500, ações em USD)
- `fiis_pct` (tijolo + papel)
- `caixa_pct` (CC + moeda estrangeira líquida)

Mais:

- `inputs.rebalanceamento_modo` enum (`por_aporte` default — princípio AUVP; `trigger_5pct/10pct` alternativas)
- `derived.desvio_max_pct` — KPI de rebalanceamento (sinaliza classe defasada — onde o próximo aporte vai)
- `derived.desvio_por_classe` — desvio assinado por classe (negativo = subalocada)

**Migração v1→v2 (no migrator):**

| Campo v1 | Mapeamento v2 |
|---|---|
| `renda_fixa_pct` | Default split 50% pos / 25% pré / 25% IPCA |
| `acoes_pct` | `acoes_br_pct` |
| `imoveis_reits_pct` | `fiis_pct` |
| `liquidez_usd_pct` | 70% `acoes_int_pct` + 30% `caixa_pct` |

**Roadmap de adoção:** lane dedicada que migra `pipeline_adapter._serialize_alocacao_goal`, `seed_goals_full_ferreira_campos.py`, `frontend/src/app/(app)/plano/alocacao/page.tsx`, `Step1Distribution.tsx`, `AlocacaoBar.tsx` para o novo schema. Componente UI ganha 7 sliders (em vez de 4) e card "Próximo aporte sugerido: classe X (-Y%)" como derivado.

**Consequências:**

- Schema v1 não é DEPRECATED (label removido em 2026-04-27 após confirmar que produção opera em v1).
- Métrica `desvio_max_pct` é nova — KPI AUVP autêntico, sinaliza onde alocar próximo aporte (princípio Diagrama do Cerrado).
- Públicos com patrimônios pequenos (<R$100k) podem achar 7 classes excessivas — produto pode oferecer "modo simples" (4 buckets) como toggle, mas a fonte de verdade é v2.

**Débito de Fase A (A11 · 2026-05-11):** O card `AlocacaoAtualVsAlvoCard` (S3) entregue na promoção Roadmap→Proposto desta ADR roda o cálculo de desvio client-side em `frontend/src/components/report/utils/alocacaoBucketMapper.ts` agregando 10 buckets canônicos ([ADR-193](193-taxonomia-classes-ativo-e5.md)) em 4 buckets v1. Decisões pragmáticas validadas pelo financial-planner:

- **Caixa** é exibido como "Reserva" separada e **excluído do denominador do desvio** (reserva ≠ investimento).
- **Cripto + Outros** vão para linha "Fora do alvo" (alvo=0, desvio positivo) — não fundem em ações.
- **Previdência → Renda Fixa**, **Fundos → Ações**, **Internacional → Liquidez USD** são aproximações documentadas no rodapé do card.

Itens a remover/migrar ao implementar v2 (escopo da lane Fase B em A12):

1. `frontend/src/components/report/utils/alocacaoBucketMapper.ts` — substituído por `derived.desvio_por_classe` vindo do backend.
2. `frontend/src/components/report/utils/conclusionUtils.ts` `buildAlocacaoFooter` — substituído por templates consumindo `derived.desvio_max_pct`.
3. Tombstones em `config/report_layout.yaml` S3 (entries `alocacao_atual`, `alocacao_alvo` em `charts:` e `investimentos_classe` em `cards:` com `enabled: false`).
4. `chart_canvas_map` entries `alocacao_atual` e `alocacao_alvo` (dead-code latente desde ADR-129).
5. Migração `pipeline_adapter._serialize_alocacao_goal` para emitir v2 (com `derived.*`).
6. Seed `backend/app/scripts/seed_goals_workspace.py` (atualmente escreve `rf_pct/rv_pct/alternativos_pct` — inconsistente com serializer; fixar como parte da migração).

**Relaciona-se a:** [ADR-075](075-cutover-cli-web.md) (origem do schema v1), [ADR-140](140-goal-if-schema-v2.md), [ADR-193](193-taxonomia-classes-ativo-e5.md) (taxonomia 10 buckets canônicos no E5). Caracterização correta da AUVP em [`.claude/agents/financial-planner.md`](../.claude/agents/financial-planner.md).
