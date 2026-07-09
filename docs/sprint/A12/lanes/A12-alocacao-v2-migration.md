---
id: A12.alocacao-v2
type: lane
title: "Alocação-alvo schema v1→v2 (7 classes AUVP, desvio backend-driven)"
sprint: A12
status: in_progress
aliases: ["A12.alocacao-v2-migration", "A12.ALOCACAO_V2", "A12 alocacao v2"]
priority: P2
depends_on: []
parallel_with: ["[[A12.cat-learning-loop]]"]
adrs_canonical:
  - "[[ADR-141]]"
tags:
  - type/lane
  - sprint/a12
  - status/in-progress
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

**Estado 2026-07-09: 9/11 PRs mergeados — migração funcionalmente completa e verificada end-to-end.** Restam PR8 (polish visual) e PR11 (owner-gated).

| PR | Escopo | Status |
|---|---|---|
| PR1 | docs-only: emenda ADR-141 + esta lane (decisões travadas) | ✅ [#885](https://github.com/davidrobert/mathoms/pull/885) |
| PR2 | service de desvio puro em `pipeline/domain/services/` (mapping 10→7, RF agregada, renormalização sem caixa, desvio assinado, next-aporte, `Decimal`) + 26 unit tests | ✅ [#889](https://github.com/davidrobert/mathoms/pull/889) |
| PR3 | DTOs v2 + conversão on-read única (fingerprint v1/órfão/v2) + `compute_alocacao_derived_v2` | ✅ [#893](https://github.com/davidrobert/mathoms/pull/893) |
| PR4 | API v2: mapper on-read + `converted_from` + `META_VERSION_BY_TYPE` + converter-antes-de-patchar + OpenAPI snapshot + **fix bug seed órfão (GET 500)** + shim frontend | ✅ [#902](https://github.com/davidrobert/mathoms/pull/902) |
| PR5 | seed grava v2 canônico + teste de regressão do bug órfão | ✅ [#904](https://github.com/davidrobert/mathoms/pull/904) |
| PR6 | serializer `_serialize_alocacao_goal` v2 + rollup 4-bucket + `AlocacaoGoalSection` v2 + E5 injeta `derived` rico | ✅ [#905](https://github.com/davidrobert/mathoms/pull/905) |
| PR7 | card relatório consome `derived.*` + **DELETE `alocacaoBucketMapper.ts`** (o débito que originou a lane) + fallback gracioso | ✅ [#906](https://github.com/davidrobert/mathoms/pull/906) |
| PR9 | consolida chart ids `alocacao_atual`/`alocacao_alvo` → `alocacao_atual_vs_alvo` (lockstep; chave de goal intacta) | ✅ [#909](https://github.com/davidrobert/mathoms/pull/909) |
| PR10 | golden E5 cobre `derived` + **fix bug de integração do PR6** (E5 dropava `alocacao_alvo` → enrich não disparava em produção) | ✅ [#910](https://github.com/davidrobert/mathoms/pull/910) |
| PR8 | 🔲 **polish** — wizard redesign completo (inputs em grupos, "Completar com Caixa", Step3 enum, `alocacaoClasses.ts` fonte única + teste de paridade). Shim do PR4 já é funcional (7 inputs); redesign é visual, exige rebaseline de snapshot → beneficia de review | pendente |
| PR11 | 🔒 **owner-gated** — snapshot DB provando zero rows v1 vigentes → remove schema v1 + ativa `rule_alocacao_fora_alvo` (recalibra threshold + dogfood). Não executável sem owner | pendente |

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
