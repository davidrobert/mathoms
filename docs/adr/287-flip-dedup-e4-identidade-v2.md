---
id: ADR-287
type: adr
title: "Flip do dedup E4 para identidade natural_key v2 (passo 2 da B4)"
status: Proposto
phase: "A25 · l2"
date: "2026-06-10"
relates_to:
  - "[[ADR-278]]"
  - "[[ADR-282]]"
  - "[[ADR-255]]"
  - "[[ADR-090]]"
  - "[[ADR-279]]"
supersedes: []
superseded_by: []
aliases: ["ADR 287", "flip dedup v2", "passo 2 B4"]
tags:
  - type/adr
  - status/proposto
  - area/data-lineage
  - area/pipeline
---

# ADR-287 — Flip do dedup E4 para identidade `natural_key` v2

**Status:** Proposto (A25 · l2) • **Data:** 2026-06-10 • **Relaciona** [[ADR-278]]
(B3/B4), [[ADR-282]] (§7 gate), [[ADR-255]], [[ADR-090]], [[ADR-279]] (member_hashes).

> Executa o **passo 2 da estratégia B4** ([[ADR-278]]): E4 passa a consumir a
> identidade v2. A [[ADR-282]] §7 cravou o *sequenciamento* (cutover de override
> antes do flip); esta ADR crava o **desenho do flip** — algoritmo, rollout e
> rollback. Lane de implementação: [[A25.l2]]. Co-design `senior-cto` +
> `data-engineer` no kickoff A25 (2026-06-10).

## Contexto

O dedup/chaveamento de linhas no caminho E3→E4 usa hoje `compute_transaction_hash`
(v1, congelado — `pipeline/domain/services/_tx_identity.py`): `abs(valor)` sem
`moeda`/`direction`, ingere `float`, não despluga sufixo PIX. O v2
(`compute_natural_key`) corrige tudo isso ([[ADR-278]] B3) e já é emitido no
write-path E2 ([[A23.l3]]), mas **não é consumido** por E3/E4 — a cobertura K4 em
E4 é 0% ([[A24.l6]] §Resultado), o que mantém `member_hashes: []` nos agregados
transaction-fed do lineage ([[ADR-279]]).

## Decisão

1. **Consumo:** `transaction_classifier`/`cash_flow_builder` (e o caminho de dedup
   E3→E4) passam a derivar identidade de `compute_natural_key(build_hash_inputs(...))`
   (v2) em vez do shim `compute_transaction_hash` (v1). O shim v1 é **deletado no
   cutover final** — não vira shim perene (lição dos três hashes, [[ADR-282]] §1).
2. **Rollout por feature flag por workspace** (`feature_flags_service`, DEFAULT
   registrado no mesmo PR). **Não** big-bang: o flip muda quais linhas colapsam —
   v2 *separa* entrada/saída de mesmo valor e BRL/USD que v1 fundia, e *funde*
   drift de sufixo PIX que v1 separava — logo muda totais por categoria.
3. **Pré-condição (gate [[ADR-282]] §7):** overrides reancorados em v2 — cutover de
   leitura ([[A25.l1]]) mergeado + gate dogfood de reancoragem
   (`reanchored/(total−orphaned−ambiguous) ≥ 0.98`, zero `ambiguous`
   não-investigado) registrado no SMOKE_TEST_HUMAN.
4. **Rollback = flag off** (E4 volta a chavear por v1). Por isso a **M2 destrutiva
   da [[ADR-282]] não pode preceder este flip** — o drop do v1 só após flag a 100%
   + counter `mathoms.categorization.dualread.v1_fallback` zerado por ≥1 sprint.
5. **Rebaseline esperado e auditável:** goldens E3/E4/E5 + view-model snapshot
   mudam por construção — manifesto valor-a-valor (`ref`/`adr`/`rationale`),
   commit isolado (`check_golden_rebaseline_isolation`), label `golden-rebaseline`,
   2º revisor (G-c). Invariantes de conservação (incl. por categoria, F2-DB7) são a
   segunda testemunha.

## Alternativas rejeitadas

- **Big-bang sem flag** — o flip muda valores por categoria; sem rollback barato,
  um erro de colapso reedita o gênero do bug R$ 811k. Rejeitado.
- **Manter v1 como shim pós-flip** — recria o problema dos múltiplos hashes que a
  [[ADR-282]] acabou de pagar. Rejeitado.
- **Flip junto com o cutover de override (uma lane só)** — blast radius distinto
  (override = backend read-path; flip = identidade do pipeline com rebaseline);
  separação decidida na revisão PM+CTO do plano (2026-06-10). Rejeitado.

## Critério de aceite (flippa → Decidido no merge da implementação)

- Golden de **paridade de colapso**: entrada/saída de mesmo valor → 2 linhas sob
  v2 vs 1 sob v1; drift-PIX → 1 linha sob v2 vs 2 sob v1; BRL100 ≠ USD100.
- `check_lineage_sum` verde com `member_hashes` v2 reais
  (`signals.k4_coverage="partial"` → cobertura total no nó de despesa).
- Rebaseline manifestado em commit isolado + label + 2º revisor; invariantes de
  conservação verdes pós-rebaseline.
- Dogfood (G-f): diff de números do workspace real pré/pós-flip inspecionado pelo
  owner antes do flip a 100%.
- Flag-OFF byte-idêntico ao comportamento atual (zero-behavior sem flag).
