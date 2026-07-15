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
amended_at: ["2026-07-08", "2026-07-15"]
aliases: ["ADR 287", "flip dedup v2", "passo 2 B4"]
tags:
  - type/adr
  - status/decidido
  - area/data-lineage
  - area/pipeline
---

# ADR-287 — Flip do dedup E4 para identidade `natural_key` v2

> **Correção 2026-07-08:** o registro do cutover atribuiu o `k4_coverage=partial`
> da dogfood a "sem mapa de membros … por design PII-zero" — premissa falsa.
> Ver §"Correção 2026-07-08" ao final; follow-up em [[ADR-321]].

> **Emenda 2026-07-15 (DE-02):** o nó de despesa emitia `k4_coverage` só como
> binário `partial`/`full` — descartava a **fração** real de cobertura, então
> "partial" não distinguia 8% de 95%. Instrumentada a cobertura K4 (%) por run
> em `signals.k4_coverage_pct` + alerta (log estruturado no ponto de detecção),
> preservando o contrato all-or-nothing (`member_hashes=[]` em partial). Ver
> §"Emenda 2026-07-15" ao final.

**Status:** Decidido (A25 · l2/l6B) • **Data:** 2026-06-10 • **Relaciona** [[ADR-278]]
(B3/B4), [[ADR-282]] (§7 gate), [[ADR-255]], [[ADR-090]], [[ADR-279]] (member_hashes).

> **Cutover (2026-06-13):** flip fechado em 3 commits sob flag por workspace
> (A25.l2/l6B) — ver §"Cutover (Decidido — A25.l2/l6B, 2026-06-13)".

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

## Correção 2026-07-08 — "sem mapa de membros" era mis-diagnóstico

O bullet de cutover acima ("a dogfood é classe-c — `titular` resolvido vazio sem
mapa de membros → `k4_coverage=partial`, por design PII-zero") registrou premissa
**falsa**: a dogfood tem 3 `FamilyMember` com CPF encriptado e roles no DB. O
`titular` vazio vem de regressão de wiring, não de ausência de dado nem de design:
`scripts/e2/common.py::_init_config` lê `family_members.json` de disco (arquivo
que deixou de ser materializado pós-A7.5, [[ADR-134]]) e
`BankStatement.from_e2_dict` nunca mapeou `titular` → `member_key`. Diagnóstico
completo, impacto (lineage [[ADR-279]] a 8%, dedup sem discriminação por membro,
overrides ancorados em hash com titular vazio) e fix em [[ADR-321]]. O
"por design PII-zero" aplica-se à **fixture K4 sintética**, não à dogfood.

## Emenda 2026-07-15 — instrumentação de cobertura K4 (%) + alerta (DE-02)

**Contexto.** O nó `fluxo_caixa.despesa_total` emitia `signals.k4_coverage` apenas
como binário: `"partial"` (≥1 tx sem `natural_key` v2) ou ausente/`"full"`. Isso
descartava a **fração** real de cobertura — a dogfood a 8% ([[ADR-321]]) e um run
a 95% ficavam ambos rotulados `"partial"`, indistinguíveis. Sem o número, não há
como priorizar o gap de extração nem alertar quando a cobertura degrada.

**Decisão.**

1. **Cobertura K4 (%) por run** — `despesa_member_hashes` calcula `n_keyed/total`
   e emite `signals.k4_coverage_pct` (string int, ex.: `"8"`, `"50"`, `"100"`)
   sempre que há transações. Durável no artefato (`_lineage.fields[...].signals`),
   queryável por run pelo console interno / telemetria.
2. **Alerta** — log estruturado `WARNING` no ponto de detecção parcial (namespace
   `mathoms.lineage.k4`, só contagens + pct, zero PII — as tx não são logadas).
3. **Degradação graciosa preservada** — o contrato all-or-nothing de
   `member_hashes` é intocado: cobertura parcial continua `member_hashes=[]` (hash
   parcial furaria a soma silenciosamente) e a soma verifica pelos `inputs` por
   categoria. `k4_coverage_pct` é observabilidade, não muda a topologia da soma.

**Onde.** `pipeline/domain/services/e5_lineage.py::despesa_member_hashes`
(cobertura + alerta) — sem bump de schema (`signals` é objeto aberto,
`e5_analysis.schema.json:37`). Golden `dogfood_view_model.json` ganha
`k4_coverage_pct` no nó de despesa (rebaseline documentado 1× na onda R2.3).
