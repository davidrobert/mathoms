---
id: A25.l6
type: lane
title: "KR2 6/6 — fluxo_liquido + endividamento.total_dividas + member_hashes reais"
sprint: A25
plan: PLAN-data-lineage
status: in_progress
priority: P2
branch_slug: kr2-resto
adrs:
  - "[[ADR-279]]"
depends_on:
  - "[[A25.l2]]"
parallel_with: []
tags:
  - type/lane
  - sprint/a25
  - status/in-progress
  - priority/p2
  - area/data-lineage
  - area/pipeline
---

# A25.l6 — `kr2-resto` (P2/stretch — cortável sem culpa)

> **Plano:** [[PLAN-data-lineage]] · fecha KR2 6/6. **Bloqueada por [[A25.l2]]**
> (a parte de `member_hashes` reais depende do flip dedup, não só do cutover l1).
> Se l1/l2 escorregarem, esta lane cai — e tudo bem.

## Objetivo

Fechar KR2 6/6 com os 2 agregados definidos no kickoff (product-manager, 2026-06-10)
+ `member_hashes` REAIS no nó de despesa.

## Lista canônica do KR2 (decisão de kickoff — registrada no plano §KRs)

Patrimônio (`patrimonio.liquido`+`bruto` = **1** agregado, 2 níveis intra-E5) ·
`reserva_emergencia.total_liquida` · `fluxo_caixa.despesa_total` ·
`investimentos.total` · **`fluxo_caixa.fluxo_liquido`** (novo — capacidade de
poupança; `FluxoCaixaEnricher.enrich`, `edge_type: formula`, inputs
`receita_total`+`despesa_total`, invariante G-b já existe) ·
**`endividamento.total_dividas`** (novo — prioridade de quitação;
`EndividamentoAnalyzer.analyze`, `edge_type: aggregation`).
⚠️ dot-path real é `endividamento.total_dividas` (NÃO `dividas.total` — campo
inexistente viraria nó `dangling`). Declarar o lineage no enforcer do campo
(`EndividamentoAnalyzer`), não re-derivar de `patrimonio.dividas` (2 fontes de
verdade); são nós distintos do mesmo valor — correto.

## Escopo

- `_lineage` nos 2 agregados (padrão [[A24.l5]] — value string .2f do payload,
  inputs sort canônico, zero timestamp, topologia honesta) + entradas no
  `lineage_registry`. Ambos baseline/formula-fed → `member_hashes: []` (sem
  dependência de l2 — podem adiantar se houver capacidade).
- `member_hashes` REAIS no nó de despesa: trocar `signals.k4_coverage="partial"` →
  cobertura total (mecanismo já implementado, ativa com o flip da l2) +
  `check_lineage_sum` `Σ amount[member_hashes] == value` (cents int, ancorado ao
  run_id — B8) + **teto inline 200** (acima → edge table da [[A25.l3]], decisão
  registrada).
- G-d nos agregados novos.

## Critério de aceite

- KR2 6/6 com `check_lineage_sum`/`check_lineage_refs` verdes; run 2× byte-idêntico
  (view-model snapshot); invariantes de conservação verdes pós-rebaseline; rebaseline
  auditável (G-c). Sem ADR nova (ambos reusam ADR canônica do enforcer).

## Resultado parcial — parte A shipped (2026-06-11, #609)

**KR2 6/6 na dimensão lineage:** `fluxo_caixa.fluxo_liquido` (formula,
2 inputs) + `endividamento.total_dividas` (aggregation, ADR-227) resolvíveis via
`dev/explain_number.py`; 7 refs no registry; rebaseline isolado com zero
`value_delta` monetário. **Parte B** (member_hashes reais no nó de despesa +
teto inline 200) permanece bloqueada pela [[A25.l2]].

## Resultado — parte B implementada com a l2 (2026-06-13)

⚠️ **Premissa "member_hashes ativa com o flip da l2" estava incompleta.**
`member_hashes` lê `natural_key.hash` v2 (objeto K4 `{hash, hash_version}`) do item
de despesa E4 — eixo **ortogonal** ao `transaction_hash` que o dedup v2 muda. O item
E4 só carregava `transaction_hash`. A parte B exigiu **mudança de código** (não só o
flip): o classifier E4 passa a recomputar e estampar `natural_key` via
`build_item_identity` (`_tx_identity`), só sob v2 + discriminantes (gate classe-c
[[ADR-278]] reusado de `_has_discriminants` — nunca hash degenerado). Cobertura full
provada por fixture K4 dedicada (`test_member_hashes_k4_full.py`: `k4_coverage` full,
sobreviventes pós-dedup, `check_lineage_sum` tolerância zero). A **dogfood** é
classe-c (`titular` resolvido vazio sem mapa de membros) → `partial`, por design
PII-zero — cobre o ramo `partial`; a fixture K4 cobre o ramo full. Sem ADR nova
(reusa contrato K4 [[ADR-278]] + lineage [[ADR-279]]); registrado em [[ADR-287]]
§Cutover. Co-design `senior-cto` (recompute vs propagate) + `data-engineer` (fixture).

## Owner

Agente da lane; co-design herdado de [[A24.l5]] (`senior-cto` + `data-engineer`).
