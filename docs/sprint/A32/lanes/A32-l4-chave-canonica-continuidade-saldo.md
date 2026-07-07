---
id: A32.l4
type: lane
title: "chave canônica de conta na continuidade de saldo + ordenação determinística (ADR-310)"
sprint: A32
plan: PLAN-data-lineage
status: shipped
ship_pr: 829
ship_date: "2026-07-07"
priority: P1
branch_slug: a32-l4-saldo-continuity-account-key
adrs: ["[[ADR-310]]", "[[ADR-278]]"]
depends_on: ["[[A32.l2]]", "[[A32.l3]]"]
parallel_with: ["[[A32.l5]]"]
tags:
  - type/lane
  - sprint/a32
  - status/shipped
  - priority/p1
  - area/pipeline
  - area/domain
---

# A32.l4 — `saldo-continuity-account-key` (mata os 21 balance_gap falsos)

## Problema

`SaldoContinuityValidator._account_key`
(`pipeline/domain/services/reconciliation_validators.py:84-88`) =
`(institution, member, currency)` — **sem** `account_type` nem número de
conta. Fatura de cartão, conta corrente e poupança do mesmo banco viram
uma cadeia única (casos reais: bradesco `extratopoupanca→extratoconta`,
c6bank `faturacarbon→extratoconta→faturacarbon`) — gap garantido.
Ordenação só por `period_start` (`reconciliation_validators.py:203`) com
empate resolvido pela ordem alfabética da artifact_key
(`db_artifact_store.py:344` + sort estável) = sequência embaralhada; em
faturas Santander, `fatura_inicio_adjusted_to_tx`
(`statement_preprocessor.py:432-443`) colapsa múltiplas faturas para o
mesmo início (parcelamentos carregam a data da compra original).
Enquanto isso, `AccountGrouper.key` (`account_grouper.py:177`) **já**
separa fatura — as duas chaves divergiram. Decisões fechadas em
[[ADR-310]] — **ler a ADR antes de codar**; esta lane operacionaliza.

## Escopo

1. **Chave canônica compartilhada** — `_account_key` passa a derivar da
   `AccountKey` do `AccountGrouper` (value object em
   `pipeline/domain`), incluindo `account_type` +
   `account_number_norm`: fatura, CC e poupança do mesmo banco viram
   cadeias separadas.
2. **Faturas fora da cadeia de saldo** — `is_fatura` sai da validação de
   continuidade (passivo rotativo não tem "saldo que continua";
   `saldo_inicial/final` de fatura = `saldo_anterior/atual`,
   `statement_preprocessor.py:281-284`, é semanticamente outra coisa).
3. **Desempate determinístico** — ordenação por
   `(period_start, period_end, source_document)`; nunca ordem de
   inserção/hash.
4. **Teste negativo (objeção senior-cto):** nenhuma conta legítima
   classificada como fatura por engano some da validação sem sinal.
5. **Rebaseline dos goldens OBRIGATORIAMENTE via `dev/golden_diff.py` +
   manifesto** (padrão A23.l2) provando que cada delta é remoção de
   falso positivo.

## Critérios de aceite

1. ADR-310 mergeada como Proposto ANTES do PR de impl (gate P1 do
   CLAUDE.md); flip para `Decidido (A32.l4)` no merge.
2. Zero `balance_gap` falso entre account_types distintos do mesmo banco
   (testes reproduzindo os casos c6bank/bradesco/santander do dossiê).
3. Faturas Santander com início colapsado por
   `fatura_inicio_adjusted_to_tx` não geram gap nem sequência
   embaralhada (teste com empate de `period_start`).
4. Manifesto de rebaseline justifica cada warning removido; suíte de
   invariantes de conservação (`tests/test_e5_conservation_invariants.py`)
   verde.
5. PR mergeado em `main` (squash) com CI verde.

## Arquivos load-bearing

| Arquivo | Papel |
|---|---|
| `pipeline/domain/services/reconciliation_validators.py:84-88,182-229` | Validator + chave a substituir |
| `pipeline/domain/services/account_grouper.py:51,177` | `AccountKey` canônica a reusar |
| `pipeline/domain/services/statement_preprocessor.py:281-284,432-443` | Semântica de saldo de fatura + colapso de início |
| `dev/golden_diff.py` | Protocolo de rebaseline (A23.l2) |
| `docs/adr/310-chave-canonica-conta-continuidade-saldo.md` | Decisões fechadas |
