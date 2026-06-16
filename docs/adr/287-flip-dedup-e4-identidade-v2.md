---
id: ADR-287
type: adr
title: "Flip do dedup E4 para identidade natural_key v2 (passo 2 da B4)"
status: Decidido
phase: "A25 · l2/l6B"
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
  - status/decidido
  - area/data-lineage
  - area/pipeline
---

# ADR-287 — Flip do dedup E4 para identidade `natural_key` v2

**Status:** Decidido (A25 · l2/l6B) • **Data:** 2026-06-10 • **Relaciona** [[ADR-278]]
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

## Cutover (Decidido — A25.l2/l6B, 2026-06-13)

Fechado em 3 commits sob a flag por workspace (resolver com 2 ramos: DB soberano em
produção; env `MATHOMS_DEDUP_NATURAL_KEY_V2` materializa v2 nos goldens InMemory —
sentinela anti-perenidade trava o 3º caminho, [[ADR-282]] §1). Achados que emendam o
critério acima:

- **Rebaseline materializou-se vazio.** Goldens E3/E4/E5 + view-model snapshot +
  conservação + lineage passam byte-idênticos sob v2 — as fixtures sintéticas não
  exercem os casos discriminantes do v2 (entrada/saída de mesmo valor fora de
  transferência; BRL/USD colidindo). Consistente com o G-f (zero delta monetário no
  dado real). A paridade de colapso é coberta pelos 16 testes de domínio
  (`test_dedup_natural_key_v2_flag.py`), não por rebaseline de execução.
- **Critério drift-PIX obsoleto** — v1 já colapsa drift desde [[ADR-255]] it.2; o
  "2 sob v1" do critério não se aplica ao shim atual. Confirmado pelo G-f.
- **`member_hashes` reais (l6B) eram eixo ortogonal ao flip.** Dependem de
  `natural_key`{hash, hash_version} estampado **no item E4**, não do `transaction_hash`
  que o dedup muda. O E4 recomputa `natural_key` (via `build_item_identity` em
  `_tx_identity`) só sob v2 + discriminantes (gate classe-c reusado de `_has_discriminants`
  — nunca hash degenerado). Cobertura full provada por fixture K4 dedicada; a dogfood
  é classe-c (`titular` resolvido vazio sem mapa de membros) → `k4_coverage=partial`,
  por design PII-zero.
- **Default flipado para `True`** após G-f aprovado. **Rollback = flag off por
  workspace** (E4 volta a v1). **Drop do shim v1 (M2) é carry-over ≥1 sprint** com
  counter de fallback zerado — não faz parte deste cutover.
