---
id: A26.l3
type: lane
title: "M2-A — drop do shim v1 do dedup (compute_transaction_hash)"
sprint: A26
plan: PLAN-data-lineage
status: blocked
priority: P2
branch_slug: drop-dedup-v1-shim
adrs:
  - "[[ADR-287]]"
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a26
  - status/shipped
  - priority/p2
  - area/data-lineage
  - area/pipeline
---

# A26.l3 — `drop-dedup-v1-shim` (Regime B · destrutivo REVERSÍVEL · "canário")

> **Plano:** [[PLAN-data-lineage]] · executa a M2 do dedup ([[ADR-287]] §Cutover: "o shim
> v1 é deletado no cutover final"). Co-design `data-engineer` 2026-06-16. É o drop de
> **menor blast radius e reversível** — serve de canário antes do drop irreversível da [[A26.l5]].
>
> **Status: `shipped` (2026-07-01).** Deletado o shim público `compute_transaction_hash`
> de `_tx_identity.py` — era **dead code** (zero callers vivos; G3 verde: só docstring +
> testes o referenciavam). Por ser dead code, a deleção **independe do gate de tráfego** e
> é reversível por `git revert`. **`_hash_v1` NÃO foi removido** — continua como fallback
> flag-OFF em `compute_identity_hash` (contrato congelado do DB histórico); sua remoção é
> passo futuro, aí sim gated por `dedup_natural_key_v2_enabled` zerado em tráfego real.
> Testes do shim retargetados a `_hash_v1` (rename mecânico, assinatura idêntica) em vez de
> deletados — preserva cobertura do contrato v1 congelado (desvio consciente do "deletar
> testes" da lane, pois o path v1 segue vivo). 1787 testes de `tests/unit/pipeline/` verdes.

## Objetivo

Deletar o shim v1 do dedup `compute_transaction_hash` (e o alias, se houver) de
`pipeline/domain/services/_tx_identity.py`. O dedup E3→E4 já roda v2 por default
(`dedup_natural_key_v2_enabled=True`, mergeado #648 na [[A25.l2]]). É **só código** — a v1
do dedup nunca foi coluna (era função pura computada inline). Reversível por `git revert`.

> ⚠️ **Não confundir:** esta lane deleta `compute_transaction_hash` (dedup, em
> `_tx_identity.py`). A função `generate_transaction_hash` (override) vive em
> `transaction_service.py` e é alvo da [[A26.l5]], não desta lane.

## Gate

- `dedup_natural_key_v2_enabled = True` no DEFAULT (já está) por **≥1 sprint**.
- Counter de fallback v1 do dedup zerado no período (o flip da A25.l2 teve rebaseline
  vazio v2≡v1, mas o gate exige observação de tráfego real, não só goldens).
- **G3 (sentinela de código):** `grep` prova zero caller residual de `compute_transaction_hash`
  em `backend/app` e `pipeline` (exceto migrations/testes históricos).

## Escopo

- Deletar `compute_transaction_hash` + alias de `_tx_identity.py`; atualizar docstring do módulo.
- Remover os testes que exercem **só** o shim v1 do dedup (deletar, não comentar);
  **manter** os de `compute_natural_key` / `build_item_identity` (v2).
- CI verde prova que nenhum path ainda chama o shim v1.

## Critério de aceite

- `check_pipeline_boundaries.py` verde; `tests/unit/pipeline/` verde com testes v1-only removidos.
- `git revert` documentado como rollback (reversível — re-adicionar função pura é trivial).
- Sem ADR nova (ADR-287 já `Decidido`).

## Owner

Agente da lane; co-design `data-engineer`.
