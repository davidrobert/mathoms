---
id: ADR-141
type: adr
title: "Goal alocação-alvo schema v2 (7 classes AUVP)"
status: Decidido
date: "2026-04-27"
phase: A12.alocacao-v2
amended_at: ["2026-07-08"]
relates_to: ["[[ADR-075]]", "[[ADR-140]]", "[[ADR-193]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 141"]
tags:
  - area/frontend
  - area/money
  - area/persistence
  - methodology/auvp
  - status/decidido
  - type/adr
size_lines: 75
---

# ADR-141 — Goal alocação-alvo schema v2 (7 classes AUVP)

**Status:** Decidido (A12.alocacao-v2) • **Data:** 2026-04-27, promoção Roadmap→Proposto em 2026-05-11 • **Implementação:** em execução pela lane [[A12.alocacao-v2]] (plano de 11 PRs na lane). Nota histórica: o flip Proposto→Decidido veio do lote #668 (status stale) e cobriu a decisão de schema; a migração runtime só começou em 2026-07-08.

> **Emenda 2026-07-08 (A12.alocacao-v2):** co-design
> `financial-planner` + `data-engineer` + `product-designer` fechou as
> decisões normativas da implementação — regra do denominador (caixa
> fora, renormalização), mapping 10 buckets→7 classes (Imóveis
> Investimento sai da carteira líquida — mudança deliberada vs Fase A),
> comparação por chaves agregadas, split do derived write-time vs
> run-time, migração on-read por fingerprint de shape (inclui o shape
> órfão do seed) e rename atômico de chart ids. Ver §Emenda ao fim.

**Contexto:** Auditoria multi-agente (rodada 1, item 9; rodada 2, item B2) identificou que a caracterização da AUVP em [methodology.md](../../config/methodology.md) e nos schemas era reducionista. AUVP é **alocação multi-classe + rebalanceamento por aporte via Diagrama do Cerrado** — não "fundamentalista + FIIs" como dizia v1 do `methodology.md`. O schema v1 de alocação-alvo (`renda_fixa_pct`, `acoes_pct`, `imoveis_reits_pct`, `liquidez_usd_pct` — 4 buckets) cola RF pré/pós/IPCA em um único bucket e mistura ações BR com internacionais — perde o que é distintivo na metodologia.

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

**Débito de Fase A (A11 · 2026-05-11):** O card `AlocacaoAtualVsAlvoCard` (S3) entregue na promoção Roadmap→Proposto desta ADR roda o cálculo de desvio client-side em `frontend/src/components/report/utils/alocacaoBucketMapper.ts` agregando 10 buckets canônicos ([ADR-193](193-taxonomia-canonica-classes-de-ativo-no-e5.md)) em 4 buckets v1. Decisões pragmáticas validadas pelo financial-planner:

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

**Relaciona-se a:** [ADR-075](075-cutover-cli-web-estrategia-de-transicao-faseada.md) (origem do schema v1), [ADR-140](140-goal-if-schema-v2-renda-passiva-atual-if-meta.md), [ADR-193](193-taxonomia-canonica-classes-de-ativo-no-e5.md) (taxonomia 10 buckets canônicos no E5). Caracterização correta da AUVP em [`.claude/agents/financial-planner.md`](../../.claude/agents/financial-planner.md).

## Emenda — decisões de co-design da implementação (2026-07-08)

Co-design `financial-planner` + `data-engineer` + `product-designer`
(lane [[A12.alocacao-v2]], que carrega o plano operacional de 11 PRs).
Decisões normativas:

1. **Denominador do desvio: caixa fora** (preserva Fase A). Alvos das 6
   classes de investimento renormalizados `alvo_i / (100 − caixa_pct) × 100`.
   `caixa_pct` segue required no input (declaração do plano) mas vira linha
   informativa com **sinal unidirecional de excesso** — nunca entra em
   `desvio_max_pct` nem no next-aporte. Reserva incompleta
   (`goal.reserva_emergencia`) **silencia** o sinal de excesso (precedência).
   Edge cases: `caixa_pct = 100` → carteira comparável vazia, desvios null;
   Σ inputs ≠ 100 → rejeitado no write; no read (rows legadas) renormaliza
   defensivamente com flag. A description de `caixa_pct` no schema v2 será
   corrigida (hoje induz a re-incluir caixa no denominador).
2. **Mapping 10 buckets → 7 classes** (denominador entre parênteses):
   RF + Previdência → `renda_fixa` agregada (sim); Ações BR + Fundos →
   `acoes_br` (sim); FIIs → `fiis` (sim); Internacional → `acoes_int` (sim,
   aproximação com rodapé); Caixa → informativo (não); **Imóveis
   Investimento → fora da carteira líquida** (não — linha própria sem alvo;
   mudança deliberada vs Fase A: imóvel físico não é FII e domina o desvio
   sem sinal acionável); Cripto/Outros → fora do alvo, alvo=0 (sim).
   O card comunica base "carteira líquida" em copy explícita.
3. **Comparação por chaves agregadas comparáveis**: `desvio_por_classe`
   emite `renda_fixa` (Σ rf_pos+rf_pre+rf_ipca vs RF+Previdência atual),
   `acoes_br`, `acoes_int`, `fiis`, `fora_alvo` + flag
   `rf_comparacao: "agregada"`. Não fabricar desvio por sub-RF que o E5
   não observa (ADR-193 sub-4). Tie-break do next-aporte: ordem canônica
   fixa das classes. Next-aporte não deve ler como "pare o PGBL"
   (interação com [[ADR-236]] — rodapé).
4. **Derived em duas temporalidades**: write-time magro
   (`soma_percentuais` → `goals.derived_json`); run-time rico (valor R$,
   atual_pct, alvo_pct, desvio_pp, severity, next_aporte_class,
   total_investivel) → **bundle E5** `goals.alocacao_alvo.derived`, com
   proveniência (`alvo_goal_id`, `effective_from`) e campos null sem dados
   de investimento. O schema do goal descreve a row; o shape do bundle
   vive em `AlocacaoGoalSection` + schema `e5_analysis` (atualizar schema
   **antes** do emitter — strict mode).
5. **Migração on-read por fingerprint de key-set** (precedência sobre
   `meta_version`, que mente nas rows do seed), em módulo único consumido
   pelo adapter E5 e pelo mapper da API. Tabelas: v1→v2 (§Migração acima);
   **órfão** `{rf_pct, rv_pct, alternativos_pct}` → rf 50/25/25,
   rv 70/30 `acoes_br`/`acoes_int`, `alternativos_pct` → `fiis_pct`
   integral, `caixa_pct` = 0 — inteiros por largest-remainder com resíduo
   em `rf_pos_pct`. Rows **vigentes** v1/órfãs migram por **nova versão**
   (INSERT via internal_ops, append-only preservado); converter on-read é
   infraestrutura permanente (history serve rows antigas para sempre);
   schema v1 demovido a "shape histórico", não deletado. Telemetria:
   `mathoms.goals.alocacao.shape_conversion{from_shape,boundary}` +
   `mathoms.report.alocacao_fallback_v1_hit` (remoção do fallback guiada
   por counter, não por calendário).
6. **API**: conversão universal no history (response só v2) + campo
   `converted_from: 1 | "orphan" | null`; `meta_version` centralizado por
   tipo nos writers (hoje 3 pontos hardcoded); OpenAPI snapshot no mesmo PR.
7. **Conversão nunca silenciosa**: on-read não persiste; alvo migrado carrega
   `is_template` até re-confirmação no wizard; card exibe badge "Alvo
   estimado" (tom informativo) e **suprime o CTA de próximo aporte** até
   confirmação.
8. **Chart ids**: rename atômico `alocacao_atual`/`alocacao_alvo` →
   `alocacao_atual_vs_alvo` com lockstep completo (enforcers E7/E5N,
   M-mapping de `generate_narratives`, templates narrativos fundidos,
   testes, llmFooter, `report_layout.yaml` + codegen, grep no catálogo de
   citação A26.l1) + fallback chain key nova→velha no reader durante a
   janela de compat.
9. **`rule_alocacao_fora_alvo` permanece dormante** — `investimentos.desvios_alvo`
   não é emitido nesta lane; ativação futura exige recalibração do
   threshold (10pp absolutos ≠ mesmo significado com 7 classes) + dogfood
   de volume (precedente red-lines 58/60).
10. **Thresholds de severidade 2/5pp mantidos** (consistente com regra
    5/25 e `trigger_5pct`); calibração relativa é roadmap pós-dogfood.
    Copy: "rebalancear" = direcionar aportes, nunca venda.
11. **UI**: inputs numéricos inteiros (não sliders) em grupos visuais
    fixos com subtotais; sem auto-normalização; ação determinística
    "Completar com Caixa"; labels/cores canônicos em fonte única
    (`alocacaoClasses.ts` + dict py + teste de paridade com o schema);
    `rebalanceamento_modo` exposto no Step3 (3 escolhas agrupadas, strings
    legadas mapeadas para o enum); `SupportGoalsRow` usa rollup por
    família. Conversões garantem Σ=100 em inteiros (wizard bloqueia Σ≠100).
