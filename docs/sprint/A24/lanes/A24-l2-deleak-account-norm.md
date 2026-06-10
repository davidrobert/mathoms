---
id: A24.l2
type: lane
title: "Data Lineage F2 — de-leak numero_conta_norm (extração emite raw)"
sprint: A24
plan: PLAN-data-lineage
status: blocked
priority: P0
branch_slug: dl-f2-deleak-account-norm
adrs:
  - "[[ADR-280]]"
  - "[[ADR-226]]"
depends_on: ["[[A24.l1]]"]
parallel_with: ["[[A24.l3]]"]
tags:
  - type/lane
  - sprint/a24
  - status/blocked
  - priority/p0
  - area/data-lineage
  - area/pipeline
---

# A24.l2 — `dl-f2-deleak-account-norm`

> **Plano:** [[PLAN-data-lineage]] · Onda 2 (F2). Bloqueada por [[A24.l1]] (discovery).
> Re-fatiada **por vazamento** (F2-B6), não por seção do relatório.

## Objetivo

Remover o único import de domínio na extração: `normalize_account_number` em
`finalize_e2_result` (`scripts/e2/common.py:393-399`). Extração passa a emitir
**só `numero_conta` raw**; a normalização canônica roda nos consumidores (que já
re-normalizam hoje — `document.from_e2_dict:158`, fallback mantido durante a
janela, defesa em profundidade conforme [[ADR-226]]).

## Escopo

| Item | Detalhe |
|---|---|
| Remover chamada/import de `normalize_account_number` da extração | `scripts/e2/common.py:393` (e o call-site `scripts/e2_extract.py:166` se aplicável) |
| Manter fallback no consumidor | `document.from_e2_dict` re-normaliza quando `numero_conta_norm` ausente — já existe, não tocar |
| **F2-B4**: ampliar `dev/check_extract_no_domain_imports.py` com `account_normalization` | matcher por componente + teste de violação sintética → exit 1; remover a nota de dívida da linha 17 |
| Golden esperado **NO-OP** | Transform recomputa idêntico; rebaseline deve ser **delta-zero verificável** via `golden_diff`, não manifesto de valores |

## Critério de aceite

- `check_extract_no_domain_imports` verde com matcher `account_normalization` ativo; teste de leak sintético → exit 1.
- `golden_diff` E3/E4/E5 + dogfood: **zero `value_delta`** (no-op).
- Invariantes de conservação (incl. por categoria, l1) verdes.
- Dogfood real (G-f) sem delta — step humano documentado.
- `bank_accounts` ([[ADR-226]]) inalterado: o partial unique é sobre o norm da config, não do E2.

## Não-escopo

- `tipo_lancamento` → [[A24.l3]]. Schema E2 → l3 (este campo `numero_conta_norm`
  não está no contrato por-transação; verificar se aparece no top-level do schema
  e tratar na mesma PR se sim).

## Owner

Co-design `data-engineer` + `senior-cto` (registrado na l1).
