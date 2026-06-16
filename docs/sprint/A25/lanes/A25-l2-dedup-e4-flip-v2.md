---
id: A25.l2
type: lane
title: "Flip do consumo E4 para identidade v2 (passo 2 da B4)"
sprint: A25
plan: PLAN-data-lineage
status: in_progress
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
  - status/in-progress
  - priority/p0
  - area/data-lineage
  - area/pipeline
---

# A25.l2 — `dedup-e4-flip-v2` (passo 2 da B4 · lane própria por blast radius)

> **Plano:** [[PLAN-data-lineage]] · executa o passo 2 da estratégia B4 ([[ADR-278]]).
> **Bloqueada por [[A25.l1]]** (gate de sequenciamento [[ADR-282]] §7: cutover de
> leitura do override + dogfood de reancoragem ANTES do flip).
>
> **Gate FECHADO (2026-06-12):** [[A25.l1]] shipped (#604), [[ADR-287]] `Proposto`
> em main (#605), inspeção do owner concluída (7/7 órfãos confirmados no app) e
> **backfill real aplicado** — 7 quarentenados, zero legado restante (detalhes em
> [[A25.l1]] §Resultado). **Lane DESBLOQUEADA** — pré-condição "overrides
> reancorados em v2" satisfeita por quarentena (não havia reancorável).

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

## Resultado parcial — slice 1 + G-f (2026-06-12)

**Slice 1 shipped (#619):** flag `dedup_natural_key_v2_enabled` default OFF em
DEFAULTS; `transaction_classifier`/`cash_flow_builder` derivam identidade do
dispatch `compute_identity_hash` (v2 sob flag; shim v1 congelado); flag flui como
campo tipado (`ClassifierConfig` → adapter → boundary de `scripts/e4_categorize.py`);
16 testes de paridade de colapso + zero-behavior. **Desvio documentado:** critério
drift-PIX da [[ADR-287]] estava obsoleto — v1 também colapsa drift desde
[[ADR-255]] it.2; testes refletem o comportamento real.

**Dogfood G-f executado e APROVADO pelo owner (2026-06-12):** dois runs full no
workspace real (flag off → on), diff valor-a-valor: **zero delta monetário**
(`new=0, removed=0`; nenhuma linha separada/fundida; nenhum total mudou).
3.936 deltas de `transaction_hash` (v1→v2, por construção) + 122 de Monte Carlo
(RNG não-seedado do `if_projector` — ruído entre quaisquer runs) + 3 timestamps.
Flag permanece **ON no dogfood**; rollback = flag off. Implicação: REBASELINE de
goldens não se materializa com default OFF — reavaliar critério no cutover final.
`k4_coverage` segue `partial` (ativação de `member_hashes` é a [[A25.l6]] parte B).

**Bug pré-existente descoberto (fora da lane, registrado):** run com
`from_stage="E4"` produz E4/E5 vazios silenciosamente — `DBArtifactStore.read` é
run-scoped e E3 não está em `_WORKSPACE_SCOPED_STAGES` (fallback não se aplica);
`list_keys` acha as keys, `read` retorna None. Detectado porque os 2 primeiros runs
do G-f (parciais) zeraram E4 com flag on E off; discriminado com run full.

## Resultado — cutover final (2026-06-13)

Fechado em 3 commits (resolver com env override + sentinela anti-perenidade; flip
DEFAULTS→True; member_hashes via [[A25.l6]] parte B). Achados que emendam o critério
([[ADR-287]] §Cutover):

- **Rebaseline materializou-se vazio:** goldens E3/E4/E5 + view-model snapshot +
  conservação + lineage byte-idênticos sob v2 — fixtures sintéticas não exercem os
  casos discriminantes do v2; paridade de colapso coberta pelos 16 testes de domínio.
  Consistente com o G-f. Backend suite inteira verde com o flip (2647 passed).
- **Resolver com 2 ramos (sem 3º):** DB soberano em produção; env
  `MATHOMS_DEDUP_NATURAL_KEY_V2` materializa v2 nos goldens InMemory (sentinela
  anti-perenidade [[ADR-282]] §1). env **não** setado no CI (redundante — v2≡v1).
- **DEFAULTS→True** (rollback = flag off por workspace); **drop do shim v1 (M2) é
  carry-over ≥1 sprint**.

## Owner

Agente da lane; co-design `data-engineer` + `senior-cto` (gatilho obrigatório na ADR).
