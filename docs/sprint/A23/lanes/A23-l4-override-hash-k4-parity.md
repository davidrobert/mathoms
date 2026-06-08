---
id: A23.l4
type: lane
title: "Data Lineage F1 — alinhar 3º hash (override) ao K4 v2 (D6)"
sprint: A23
plan: PLAN-data-lineage
status: in_progress
priority: P0
branch_slug: a23-l4-override-hash-k4-parity
adrs:
  - "[[ADR-282]]"
depends_on:
  - "[[A23.l3]]"
parallel_with: []
tags:
  - type/lane
  - sprint/a23
  - status/in-progress
  - priority/p0
  - area/data-lineage
  - area/backend
---

# A23.l4 — alinhar o 3º hash (override) ao `natural_key` K4 v2 (D6)

> **Plano:** [[PLAN-data-lineage]] · Onda 1 · materializa a dívida **D6** registrada
> em [[A23.l3]] §D6. Conforma à [[ADR-282]] (Proposto); não reabre a decisão.
> **Fonte única do status das slices é esta lane** — os outros docos só apontam.

## Objetivo

Unificar a identidade do subsistema de override/learning no `natural_key` v2 do
pipeline (`compute_natural_key`), **aposentando o terceiro hash**
`generate_transaction_hash` (`backend/app/services/transaction_service.py:17`).

Dois jobs, o primeiro soberano:

1. **Bug vivo (P0, dogfood).** `generate_transaction_hash` não normaliza `descricao`
   nem inclui `tipo_conta` → re-extração de extrato C6 com **drift de sufixo PIX
   orfaniza silenciosamente a categorização manual** do usuário (classe [[ADR-255]],
   blast radius pior por ser silencioso). Acontece **hoje**, independente do passo 2.
2. **Desbloqueio do passo 2 da B4.** Quando o E4 passar a chavear linhas por v2
   (passo 2, futuro), todo override keyado no hash legado vira órfão em massa no
   instante do flip (gênero do incidente "membro identity por CPF").

## Escopo

Migração **expand → contract** (aditiva primeiro, destrutiva só no fim). Esta lane
(A23) cobre o **expand auto-contido (slices 1–3)** — tudo aditivo, zero-behavior,
mergeável sem ativar nada. O **cutover + contract (slices 4–5)** é trabalho da
próxima janela (§Não-escopo).

Identidade canônica do override = **a linha E4 recomputada via v2** (não o
`natural_key` herdado do E2, ambíguo sob colapso N→1 do dedup). Linha de override
**auto-suficiente**: snapshot dos inputs do hash → re-hasheável sem replay de E4 +
fecha o lineage reverso. Detalhe e alternativas rejeitadas em [[ADR-282]].

## Slices (fonte única de status)

| # | Slice | PR | Status | Escopo |
|---|---|---|---|---|
| 1 | Fundação aditiva | [#556](https://github.com/davidrobert/mathoms/pull/556) | ✅ shipped (`c96c4915`) | Migration aditiva (`natural_key_hash`/`hash_version`/snapshot 8 inputs/`orphaned_at` + índice parcial `ix_txov_ws_natural_key`); adapter `override_identity.py` (`ClassifiedTransaction → HashInputs → compute_natural_key`); dual-write no **learning loop** (caminho limpo); flag `override_natural_key_v2_enabled=False`. Zero-behavior-change. |
| 2 | Read-path | — | ⬜ pendente | Propagar `direction` no E4 (alinhado [[ADR-278]]) + adapter `inputs_from_transaction_item` (`TransactionItem` não carrega `tipo`/`direction` → derivar via `derive_direction`, D2) + dual-write em `create_override` e `_apply_engine`. |
| 3 | Backfill (report-only) | — | ⬜ pendente | Script idempotente, **report-only antes de escrever**, **quiesce-aware** (coordena lock com `pipeline_reset`): replay-E4, recomputa v1+v2 por linha, mapa `{v1:v2}`, log `{workspace_id, overrides_total, reanchored, orphaned, collided}`. |

Slices 4–5 (cutover + M2 destrutiva) → §Não-escopo (próxima janela / A24).

## Critério de aceite

Lane só vira `shipped` quando os **3 PRs estão em `main`** (CLAUDE.md §Concluído).
Gate por slice:

- **Slice 1** — PR mergeado, CI verde; migration `pytestmark = pytest.mark.migration`;
  flag em `DEFAULTS` no mesmo PR; goldens E3/E4/E5 verdes **sem rebaseline** (D6 não
  toca dedup). *Prova: zero-behavior-change.*
- **Slice 2** — `test_override_hash_equals_dedup_hash` verde (**invariante central**:
  hash do override == hash v2 do dedup para a mesma linha E4); casos fatura-estorno +
  drift-sufixo-PIX no read-path do backend; `make update-openapi-snapshot` se DTO mudar.
- **Slice 3** — `test_override_backfill_reanchors` + `test_collision_precedence` verdes;
  **dry-run inspecionado por humano** (mapeados/órfãos/colididos); nada escrito em
  report-only.

## Sequenciamento

Serial por construção (expand→contract): 1 → 2 → 3 → [4 → 5]. Slices 1–3 são
aditivas/independentes (mergeáveis sem ativar nada). **Gate de sequenciamento da
[[ADR-282]] §7:** o passo 2 da B4 (flip dedup E4→v2) **não abre** antes do cutover
(slices 4–5) + dogfood de reancoragem verde.

## Não-escopo (próxima janela — A24)

- **Slice 4 — cutover:** dual-read (v2 → fallback v1-legado) → flip da flag por
  workspace (cobertura 100% exceto órfãos quarentenados) → **gate dogfood: reancoragem
  ≥ limiar no workspace real** (step no `SMOKE_TEST_HUMAN`, PII real fora do CI).
- **Slice 5 — M2 destrutiva:** drop `transaction_hash` + UK velha + delete
  `generate_transaction_hash`; [[ADR-282]] flippa `Proposto → Decidido`.
- Os slices 4–5 nascem como lane própria em A24 (mesma janela do passo 2 da B4, que
  esta lane desbloqueia), `depends_on` esta A23.l4. Não criada ainda (A24 não aberta).

## Owner sugerido

`senior-cto` (unificação de identidade + read-path) com co-design `data-engineer`
(backfill + schema da migração). Co-design da decisão registrado em [[ADR-282]].
