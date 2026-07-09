---
id: A12.alocacao-v2
type: lane
title: "Alocação-alvo schema v1→v2 (7 classes AUVP, desvio backend-driven)"
sprint: A12
status: open
aliases: ["A12.alocacao-v2-migration", "A12.ALOCACAO_V2", "A12 alocacao v2"]
priority: P2
depends_on: []
parallel_with: ["[[A12.cat-learning-loop]]"]
adrs_canonical:
  - "[[ADR-141]]"
tags:
  - type/lane
  - sprint/a12
  - status/ready
  - priority/p2
  - area/methodology
  - area/persistence
  - methodology/auvp
---

# A12.alocacao-v2-migration — Alocação-alvo schema v2

> Lane multi-PR (~5d eng estimados; escopo real inclui camada API de goals).
> ADR canônica: [[ADR-141]] (Decidida; **emenda 2026-07-08** consolida as
> decisões de co-design — leia a emenda antes de implementar).
> Track: [[TRACK-alocacao-v2-7-classes-migration]].

## Origem

Débito explícito da Fase A entregue em A11 (`AlocacaoAtualVsAlvoCard`, 2026-05-11). Card de relatório S3 calcula desvio em pp client-side agregando 10 buckets canônicos do [[ADR-193]] em 4 buckets v1 — solução pragmática para entregar valor enquanto v2 não está em produção. Lane atual migra para schema v2 (7 classes) com `derived.desvio_*` calculado no backend, eliminando o util client-side.

**Retomada 2026-07-08:** owner decidiu entregar dentro da A12. Workflow de
investigação (4 leitores + crítico) + co-design `financial-planner` +
`data-engineer` + `product-designer` fecharam as decisões normativas
(emenda da [[ADR-141]]) e expuseram escopo que a lane original não via:
a camada API de goals (DTOs/mapper/endpoints/`compute_alocacao_derived`
operam em v1 com hard-fail), a projeção do Decision aggregate
([[ADR-136]]), o shape órfão do seed (`{rf_pct, rv_pct, alternativos_pct}`
carimbado `meta_version: 1` — **bug vivo**: quebra `GET /goals/alocacao`
em workspace seedado), a regra dormante `rule_alocacao_fora_alvo` e o gap
de goldens (fixture dogfood sem goal de alocação).

## Plano de execução (11 PRs, ordem do co-design)

| PR | Escopo | Depende de |
|---|---|---|
| PR1 | docs-only: emenda ADR-141 + esta lane (decisões travadas) | — |
| PR2 | service de desvio puro em `pipeline/domain/services/` (mapping 10→7, RF agregada, renormalização sem caixa, desvio assinado, next-aporte com tie-break, `Decimal` ADR-090) + unit tests exaustivos (herdam os casos do `alocacaoBucketMapper.test.ts`) | PR1 |
| PR3 | DTOs v2 + conversão on-read única (fingerprint por key-set: v1 / órfão / v2) + writers com `META_VERSION_BY_TYPE` + `compute_alocacao_derived` v2 + fix `decision_goal_projection` (converter-antes-de-patchar) | PR2 |
| PR4 | API: endpoints v2, history com conversão universal + `converted_from`, telemetria `shape_conversion`, `make update-openapi-snapshot` | PR3 |
| PR5 | seed grava v2 canônico + teste de regressão do bug órfão | PR3 |
| PR6 | schema `e5_analysis` (bloco `goals.alocacao_alvo.derived` rico) **antes** do emitter; serializer `_serialize_alocacao_goal` v2 + narrativas (M-mapping + template fundido); goldens E5N re-verificados | PR2, PR3 |
| PR7 | card relatório consome `derived.*` + DELETE `alocacaoBucketMapper.ts` + `conclusionUtils` + fallback 3-shapes + counter `alocacao_fallback_v1_hit` + badge "Alvo estimado"/supressão CTA + rebaseline visual S3 | PR6 |
| PR8 | wizard 7 classes (inputs inteiros em grupos, "Completar com Caixa", Step3 `rebalanceamento_modo` enum, `alocacaoClasses.ts` fonte única + dict py + teste de paridade) + `goalPremissas`/`SupportGoalsRow` rollup + E2E @critical | PR4 |
| PR9 | rename chart ids → `alocacao_atual_vs_alvo` em lockstep (7+ pontos: `validate_cross`, `format_helpers`, `charts_narrator`, `generate_narratives`, testes, llmFooter, YAML+codegen, grep catálogo de citação) + fallback chain no reader | PR6 |
| PR10 | golden isolado (gate G-c): fixture dogfood com goal v2 + snapshot view-model + `golden_diff` com `_pp`/`soma_percentuais` não-monetários + invariante de conservação (Σ valor classe == `total_investivel` em cents) | PR6 |
| PR11 | cleanup condicional owner-gated: migração-por-append das rows vigentes (internal_ops), schema v1 demovido a histórico, remoção do fallback v1 quando counter flat-zero | PR4-PR10 |

## Pré-requisitos

- Nenhum pré-requisito interno do A12.
- PR6 antes do emitter mudar (strict mode do `schema_validation`).

## Branch prefix

`agent/a12-alocacao-v2/<yyyyMMdd-HHmm>` (PRs sequenciais na mesma família de branch).

## Time-box

~5d eng originais; escopo real revisto no co-design — PR2-PR8 são o núcleo; PR9-PR11 fecham dívidas acopladas.

## Gate de merge

- Suíte verde (`pytest backend/tests -q`, `pytest tests -q`, `npm test -- --run`; E2E @critical no PR8).
- Goldens E5N revisados manualmente (diff consciente — base investível muda com Imóveis fora da carteira líquida).
- Decisões de co-design da emenda ADR-141 são vinculantes; divergência na implementação exige nova rodada com o especialista dono.
- Snapshot OpenAPI atualizado nos PRs que tocam endpoint (ADR-109).
- Regra dormante `rule_alocacao_fora_alvo` NÃO ativa nesta lane (gate: key `investimentos.desvios_alvo` ausente do payload E5).
