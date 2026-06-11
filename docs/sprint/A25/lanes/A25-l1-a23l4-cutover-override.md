---
id: A25.l1
type: lane
title: "Override v2 — cutover de leitura (A23.l4 slice 4) + gate M2"
sprint: A25
plan: PLAN-data-lineage
status: shipped
priority: P0
branch_slug: a23l4-cutover-override
adrs:
  - "[[ADR-282]]"
depends_on:
  - "[[A23.l4]]"
parallel_with: ["[[A25.l3]]", "[[A25.l4]]", "[[A25.l5]]"]
tags:
  - type/lane
  - sprint/a25
  - status/shipped
  - priority/p0
  - area/data-lineage
  - area/backend
---

# A25.l1 — `a23l4-cutover-override` (slice 4 da [[A23.l4]] · gate da l2)

> **Plano:** [[PLAN-data-lineage]] · herdado da [[A23.l4]] (slices 1–3 ✅ em `main`
> — #556, #562, #563). Conforma à [[ADR-282]]; não reabre a decisão.
> **Gate de abertura satisfeito:** slice 3 (backfill) mergeado em 2026-06-09 (#563).
> ⚠️ NÃO inclui o flip dedup E4→v2 — é a [[A25.l2]] (blast radius distinto).

## Objetivo

Cutover de **leitura** do override para identidade v2 (`natural_key_hash`), com
dual-read v2→fallback-v1 atrás de flag por workspace. Desbloqueia o passo 2 da B4
(flip dedup, [[A25.l2]]) sem orfanizar override em massa ([[ADR-282]] §7).

## Decisões de co-design (data-engineer + senior-cto, 2026-06-10 — travadas)

1. **O dual-read NÃO existe ainda** — o slice 2 entregou dual-*write*; o match continua
   100% por `transaction_hash` v1 nos **6 call-sites**: `_loading.py:31`,
   `create_override.py:36`, `_apply_engine.py:74`, `rule_preview_service.py:90`,
   `delete_override.py:21`, `categorization_learning_loop.py`. O slice 4 **constrói**
   o dual-read nos 6 (mapa v2 ∪ fallback v1, gated por `override_natural_key_v2_enabled`).
2. **Flag em `DEFAULTS`** de `feature_flags_service.py` é pré-requisito (hoje só o
   backfill a checa). Flag-OFF ⇒ comportamento byte-idêntico ao atual.
3. **Write-paths que recebem hash opaco do FE** (`create_override`/`delete_override`):
   sob flag-ON, recomputar v2 da linha E4 correspondente e casar por v2 OU v1 no
   upsert (senão cria duplicata).
4. **Limiar do gate dogfood de reancoragem:**
   `reanchored / (overrides_total − orphaned − ambiguous) ≥ 0.98` **E** todo
   `ambiguous` inspecionado por humano (zero não-investigado). Lido do dry-run
   (`preview=True`) do backfill no workspace real — step no SMOKE_TEST_HUMAN,
   PII fora do CI.
5. **M2 destrutiva (slice 5) SAI desta sprint.** Ordem cravada: slice 4 (esta lane) →
   flip dedup ([[A25.l2]]) **com a rede v1 viva** → observação ≥1 sprint → M2.
   Critério objetivo de "pode dropar": flag de leitura v2 a 100%; cobertura de
   backfill 100% exceto quarentenados; **zero leitura via fallback v1** por ≥1 sprint
   (instrumentar counter `mathoms.categorization.dualread.v1_fallback`); dogfood verde.
   M2 vira carry-over (A26) com runbook Fase E (gate pré-M2: count de
   `natural_key_hash IS NULL AND orphaned_at IS NULL` == 0; `downgrade` documentado
   irreversível; PITR registrado; `generate_transaction_hash` deletado na mesma PR).

## Critério de aceite

- Dual-read nos 6 call-sites; `test_dual_read_window` estendido a todos; flag em
  `DEFAULTS` no mesmo PR; flag-OFF = zero-behavior (fixture com override backfillado
  + legado coexistindo prova o fallback).
- Counter `mathoms.categorization.dualread.v1_fallback` instrumentado (gate empírico
  do futuro M2).
- Goldens E3/E4/E5 verdes **sem rebaseline** (leitura de override não toca dedup).
- Gate dogfood ≥98% + zero `ambiguous` não-investigado registrado no SMOKE_TEST_HUMAN
  **antes** de declarar a [[A25.l2]] desbloqueada.
- `make update-openapi-snapshot` se `hash_version` entrar em DTO.

## Resultado (shipped 2026-06-11, #604)

Dual-read v2→v1 nos 6 call-sites (`OverrideMatchIndex` em
`backend/app/services/override_dual_read.py`), counter
`mathoms.categorization.dualread.v1_fallback`, flag-OFF zero-behavior,
goldens sem rebaseline.

**Gate dogfood executado (2026-06-11, dry-run preview, zero escrita):**
`overrides_total=7 · reanchored=0 · orphaned=7 · ambiguous=0 · collided=0` —
nenhum hash v1 armazenado casa com o E4 atual (overrides de 04/28–05/11 vs E4 de
05/30; re-extrações no intervalo). **Os 7 overrides já estão funcionalmente órfãos
hoje** — confirma o bug vivo da [[ADR-282]] §Contexto. Denominador de reancoráveis
= 0 ⇒ taxa vácua. Relatório: `_scratch/a25_l1_dogfood_gate_report.md` (local).
**Decisão de inspeção pendente do owner** antes de declarar a [[A25.l2]]
desbloqueada (aplicar backfill real quarentena os 7; ADR-282 §5 — nunca drop).

## Owner

Agente da lane; co-design `data-engineer` + `senior-cto` (2026-06-10).
