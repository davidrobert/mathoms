---
id: A25.l2
type: lane
title: "Flip do consumo E4 para identidade v2 (passo 2 da B4)"
sprint: A25
plan: PLAN-data-lineage
status: blocked
priority: P0
branch_slug: dedup-e4-flip-v2
adrs:
  - "[[ADR-278]]"
  - "[[ADR-282]]"
depends_on:
  - "[[A25.l1]]"
parallel_with: []
tags:
  - type/lane
  - sprint/a25
  - status/blocked
  - priority/p0
  - area/data-lineage
  - area/pipeline
---

# A25.l2 — `dedup-e4-flip-v2` (passo 2 da B4 · lane própria por blast radius)

> **Plano:** [[PLAN-data-lineage]] · executa o passo 2 da estratégia B4 ([[ADR-278]]).
> **Bloqueada por [[A25.l1]]** (gate de sequenciamento [[ADR-282]] §7: cutover de
> leitura do override + dogfood de reancoragem ANTES do flip).

## Objetivo

E4 passa a chavear/colapsar linhas por `compute_natural_key` v2 (+moeda +direction,
strip PIX) em vez do shim `compute_transaction_hash` v1. Ativa `member_hashes` reais
(destrava parte da [[A25.l6]]) e fecha a convergência de identidade do plano.

## ⚠️ ADR Proposto obrigatória antes de codar

O DESENHO do flip (algoritmo/rollout/rollback) **não está em ADR** — [[ADR-282]] §7 é
só gate de sequenciamento. Decisão do co-design (senior-cto, 2026-06-10): abrir
**ADR nova `Proposto`** antes do PR de implementação, com o esqueleto:

- `transaction_classifier`/`cash_flow_builder` derivam identidade de
  `compute_natural_key(build_hash_inputs(...))` v2; o shim v1 é deletado **no cutover
  final** (não vira shim perene — lição dos 3 hashes, [[ADR-282]] §1).
- **Rollout por flag por workspace** (`feature_flags_service`, DEFAULT no mesmo PR).
  NÃO big-bang: o flip muda quais linhas colapsam (v2 separa entrada/saída e BRL/USD
  que v1 fundia; funde drift-PIX que v1 separava) → muda totais por categoria.
- **Pré-condição:** overrides reancorados em v2 ([[A25.l1]] dogfood verde).
- **Rollback = flag off** (E4 volta a v1) — por isso a M2 ([[A25.l1]] §5) não pode
  preceder este flip.
- **Paridade de colapso:** golden com entrada/saída mesmo valor → 2 linhas sob v2 vs
  1 sob v1; drift-PIX → 1 sob v2 vs 2 sob v1.

## Critério de aceite

- ADR `Proposto` mergeada antes do PR de implementação; flippa `Decidido` no merge.
- **REBASELINE esperado** de goldens E3/E4/E5 + view-model snapshot — manifestado
  valor-a-valor (`ref`/`adr`/`rationale`), commit isolado
  (`check_golden_rebaseline_isolation`), label `golden-rebaseline`, 2º revisor (G-c).
- Invariantes de conservação (incl. por categoria, F2-DB7) verdes pós-rebaseline —
  a 2ª testemunha.
- `check_lineage_sum` verde com `member_hashes` v2 reais onde K4 existe.
- Dogfood (G-f): diff de números do workspace real pré/pós-flip inspecionado pelo
  owner antes do flip a 100%.

## Owner

Agente da lane; co-design `data-engineer` + `senior-cto` (gatilho obrigatório na ADR).
