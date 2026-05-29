---
id: A21.l1
type: lane
title: "Suíte de invariantes de consolidação INV-1..9 (E1.5c)"
sprint: A21
plan: PLAN-launch-trust
status: open
priority: P0
branch_slug: a21-l1-consolidation-invariants
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a21
  - status/open
  - priority/p0
  - area/pipeline
---

# A21.l1 — Suíte de invariantes de consolidação INV-1..9

> **Plano:** [[PLAN-launch-trust]] §F1-O0 ([F1 lanes](../../../plan/LAUNCH_TRUST/_README.md#f1-lanes)).
> **Boundary:** `consolidate_baseline` (E1.5c, `scripts/e15_consolidate.py`).

## Contexto

`imoveis_dedup` e `investimentos_dedup` têm testes unitários próprios, mas
ninguém valida o **resultado agregado** de E1.5c. Um quarto mecanismo de dedup
adicionado amanhã pode quebrar a conservação sem nenhum teste vermelho. Esta
lane é a **rede de segurança** que destrava o refactor (l3) e as novas
entidades (l4) — e é o **gate (a) de F3**.

## Escopo

Nove invariantes empíricos sobre o output de E1.5c, em
`tests/unit/pipeline/test_e15c_dedup_invariants.py` + golden de execução em
`tests/test_e15c_golden_execution.py`.

| # | Invariante |
|---|---|
| INV-1 | Conservação: soma pós-dedup ≤ soma pré-dedup |
| INV-2 | Não-double-count: nenhuma `identity_key` 2× no output |
| INV-3 | Idempotência: `dedup(dedup(x)) == dedup(x)` |
| INV-4 | Cobertura de ID: todo item de saída tem `<entity>_id` estampado |
| INV-5 | Preservação cross-declarante: conta conjunta vira 1 item label "casal", não some |
| INV-6 | Tie-break determinístico: mesmo input → mesmo vencedor |
| INV-7 | Warning não-silencioso: toda fusão emite `DedupWarning` tipado |
| INV-8 | Monotonicidade de série: cross-year `max(ano)`; queda → warning, não erro |
| INV-9 | Não-pessoa (PF-only): contribuinte PJ (`detect_pj_suffix` casa LTDA/S.A./EIRELI/…) não vira membro nem soma ao PL — [[ADR-268]] |

> **INV-9 — por que aqui (ADR-268).** A revisão da ADR-268 (#519) pôs o
> read-filter `partition_irpf_payloads` no boundary de **E5**, não em E1.5c.
> O consolidador (`consolidate_baseline`) ainda pode enxergar o artifact PJ
> persistido (E1.6 só marca `needs_review`, não dropa). INV-9 fecha **o
> boundary de consolidação**: se o teste vier vermelho, o fix — aplicar
> `detect_pj_suffix` como pré-filtro em E1.5c — é **in-scope desta lane**.
> Não é regra de dedup (é pré-filtro de não-pessoa) → não entra no contrato
> de l3.

## Critério de aceite

- 9/9 invariantes verde em CI, **sem skip** (A21-KR1).
- Roda contra o golden de l2 (esta lane pode começar com fixture mínima e
  endurecer quando l2 entregar o golden anotado).

## Dependências e follow-up

- **Sem deps** — pickup imediato no dia 1.
- Destrava: l2 (mede sobre os mesmos invariantes), l3 (rede que prova que o
  refactor não muda comportamento), e o **gate (a) de F3**.
