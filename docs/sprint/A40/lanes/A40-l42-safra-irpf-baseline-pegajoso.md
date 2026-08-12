---
id: A40.l42
type: lane
title: "Safra IRPF errada: baseline pegajoso — E1.5c re-consolida o próprio output do run anterior e ignora o E1.5 fresco"
sprint: A40
ship_date: "2026-08-12"
ship_pr: 1395
plan: PLAN-report-trust
status: shipped
priority: P1
branch_slug: a40-l42-safra-irpf-baseline-pegajoso
adrs:
  - "[[ADR-271]]"
  - "[[ADR-241]]"
  - "[[ADR-274]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p1
  - area/pipeline
---

# A40.l42 — `safra-irpf-baseline-pegajoso`

> **Aberta em 2026-08-11** com root-cause candidato do co-design
> (`_latest_value` lexicográfico); **investigação de 2026-08-11 provou causa
> primária diferente** — esta nota reflete o diagnóstico provado, não o
> candidato. O sintoma original: `top_ativos`/`tabela_classes` publicam
> Itaú RDB R$ 151.602,49 e PicPay R$ 46.684,62 (31/12/2024) quando o IRPF
> 2026 declara R$ 290.000,00 e R$ 52.303,69 (31/12/2025).

## Root cause provado (dogfood, 40+ runs)

**Primário — baseline pegajoso.** `consolidate_baseline.main_with_store`
lia o **próprio** artifact E1.5c antes do insumo E1.5. O read é run-scoped,
mas `consolidate_baseline` está em `_WORKSPACE_SCOPED_STAGES`
([db_artifact_store.py:358](../../../../backend/app/services/storage/db_artifact_store.py),
[[ADR-241]]) — o miss no run corrente caía no consolidado do **run
anterior**, e o E1.5c re-consolidava os itens velhos para sempre. Evidência:
todos os runs do dogfood desde 2026-07-03 publicam E1.5c com o **mesmo hash
de itens** (67 itens; 4 de 2025) enquanto cada run re-agrega um E1.5 fresco
(89 itens; 45 de 2025, com Itaú RDB 290k). O log
`mathoms.pipeline.artifact.workspace_fallback` acusava a cada run.

**Secundário (latente) — `max()` lexicográfico sobre chave de ano.**
`investimentos_dedup._latest_value` e `dividas_dedup._latest_value` faziam
`max(vals.keys())` sobre formatos mistos (`"2025"` vs `"31_12_2024"` —
`"3" > "2"`); a decisão de fusão de conta/dívida conjunta ("casal" exige
valor idêntico ao centavo) comparava a safra errada. O consumidor E5
(`_resolve_item_valor` + `resolve_value_year`, [[ADR-274]]) já era robusto
a formato — por isso o dano ficou confinado ao dedup.

## Entregável (PR único)

1. Inverte a ordem de leitura: E1.5 (insumo) primeiro; E1.5c só como último
   recurso (`from_stage` sem E1.5 no workspace). Teste de regressão em
   formato dois-runs (o 2º run consolida o E1.5 NOVO, não o próprio output).
2. `parse_ano_31_12` público em `patrimonio_types` (regex canônica ADR-274)
   e `_latest_value` dos dois dedups passa a comparar por ano parseado.
   Testes de mutação via API pública: chave legada no histórico não muda a
   safra da decisão de fusão "casal" (investimentos e dívidas).
3. Polaridade provada: os 3 testes novos falham no código antigo.

**Vetado** (mantido do co-design `data-engineer`): mexer em
`_identity_key`/`_merge_cross_year` para compensar bug de ordenação.

## Critério de aceite

- Teste dois-runs verde no novo código e vermelho no antigo (verificado por
  stash).
- No dogfood pós-merge: E1.5c consolida os ~89 itens do E1.5 corrente
  (safra 2025 presente em `valores_31_12`), e `top_ativos` reflete
  31/12/2025 — re-medição via `pipeline-review`.
- Nenhuma mudança em `_identity_key`/`_merge_cross_year`.
- Goldens de fixture inalterados (o harness não exercita o caminho pegajoso;
  zero rebaseline neste PR).

## Fechamento — 2026-08-12 (PR #1395)

Entregue: `consolidate_baseline` lê o insumo E1.5 primeiro (E1.5c vira último
recurso), matando o baseline pegajoso; `parse_ano_31_12` público em
`patrimonio_types` e `_latest_value` dos dedups de investimentos e dívidas
comparam ano parseado. Três testes com polaridade provada por stash.

O consumidor E5 ([[ADR-274]]) já era robusto a formato de chave — **zero
rebaseline de golden** neste PR. A verificação da instância (E1.5c do dogfood
passar a consolidar os ~89 itens com safra 2025, e `top_ativos` refletir
31/12/2025) fica para o `pipeline-review` da próxima onda: o artefato só
refresca em run novo.
