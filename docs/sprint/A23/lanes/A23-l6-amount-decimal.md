---
id: A23.l6
type: lane
title: "Data Lineage F1 — amount decimal ao lado de valor (B5)"
sprint: A23
plan: PLAN-data-lineage
status: shipped
priority: P0
branch_slug: dl-f1-amount-decimal
adrs:
  - "[[ADR-278]]"
depends_on: []
parallel_with:
  - "[[A23.l7]]"
tags:
  - type/lane
  - sprint/a23
  - status/in-progress
  - priority/p0
  - area/data-lineage
  - area/pipeline
---

# A23.l6 — `amount` decimal ao lado de `valor` (B5)

> **Plano:** [[PLAN-data-lineage]] · Onda 1 (F1, contrato aditivo). Conforma à
> [[ADR-278]] §B5 (Decidida); não reabre. Co-design `data-engineer` registrado em
> 2026-06-09.

## Objetivo

Introduzir `transacoes[].amount` (decimal string, [[ADR-090]]) **ao lado** de `valor`
(float) no contrato E2 — primeira fase da migração `valor`→`amount` de 2 fases (B5).
Aditivo: emite + mede, **não consome**. Os leitores seguem `valor` nesta onda; o
cutover é A24.

## Escopo (contrato aditivo, NÃO consumido ainda — G1)

| Item | Onde | Status |
|---|---|---|
| `to_amount_string(valor)` (decimal canônico, ponto-fixo, sem `E+`) | `pipeline/domain/services/_tx_identity.py` | ✅ |
| stamp `tx["amount"]` no loop comum de E2 | `pipeline/domain/services/e2_natural_key.py::stamp_natural_key` | ✅ |
| `transacoes[].amount` `{"type":["string","null"]}` (opcional) | `config/schemas/e2_extract.schema.json` | ✅ |
| gate de paridade `decimal_cents(amount)==decimal_cents(valor)` | `tests/test_e2_amount_parity.py` | ✅ |
| unit `to_amount_string` + stamp (bordas) | `tests/unit/pipeline/test_natural_key_v2.py` | ✅ |

## Decisões travadas (co-design)

- **Formato canônico = `format(Decimal(...), "f")`, não `str(Decimal(str(valor)))`.** O
  segundo herda notação científica do `repr(float)` (`1E+16`) — lixo no wire — e torna o
  gate tautológico (`data-engineer`). `format("f")` força ponto-fixo; **sem quantizar**
  (preserva 3+ casas de FX/Wise); sinal preservado.
- **`amount` deriva de coerção numérica; BR-string / não-numérico → `None` → chave
  omitida** (espelha `valor`-ausente). Hoje todos os parsers emitem `valor` float; a guarda
  é defensiva (`_coerce_valor` do E4 aceita `"1.234,56"`, mas o stamp não pode explodir).
- **Gate não-tautológico:** assere `decimal_cents(amount) == decimal_cents(valor)` (a
  invariante de conservação que protege o cutover) **e** `Decimal(amount) == Decimal(str(valor))`
  (sinal+valor), sobre payloads E2 representativos. Roda em golden-execution — sem AST/pre-commit
  adicional (A23.l3 provou que golden basta para campo aditivo).
- **Só `transacoes[]` nesta onda.** Posição de investimento (2º contrato canônico,
  [[ADR-271]]) usa `valor_brl` (`Money`), fora do escopo de B5 — confirmado pela
  [[ADR-278]] §Decisão.

## Inventário de leitores de `valor` (mapa do cutover A24 — NÃO cutover agora)

| Leitor | file:line | Nota |
|---|---|---|
| `BankStatement.from_e2_dict` | `pipeline/domain/models/document.py:132` | **Primeiro a flipar** — `Money.of(str(valor), currency)`; E3 reconciler converte E2→`Transaction` aqui |
| `_coerce_valor` (E4 classifier) | `pipeline/domain/services/transaction_classifier.py` | Aceita **BR-string** — motivo de `amount` derivar de coerção canônica, não de `valor` cru |
| `cash_flow_builder` | `pipeline/domain/services/cash_flow_builder.py` | Lê `Transaction.valor` (já coagido via `from_e2_dict`), não o dict E2 — coberto |
| `decimal_cents` / `build_hash_inputs` | `pipeline/domain/services/_tx_identity.py` | Já usa `Decimal(str(valor))` — compatível com `amount` |
| `reconciliation_service.is_duplicate` | `pipeline/domain/services/reconciliation_service.py` | Compara `Money.amount` (Decimal) — via `from_e2_dict` |

## Critério de aceite

- `tests/unit/pipeline/test_natural_key_v2.py::TestAmountString`/`TestStampAmount` verdes
  (bordas: `0.575`, negativo, USD, grande anti-`E+`, `valor=None`→omite, BR-string→`None`).
- `tests/test_e2_amount_parity.py` verde (paridade em cents sobre fixtures E2 + bateria sintética).
- Goldens E3/E4/E5 + view-model snapshot (`backend/tests/test_report_view_model_snapshot.py`)
  + invariantes de conservação (`tests/test_e5_conservation_invariants.py`) verdes **sem
  rebaseline** (G1) — `amount` é chave nova aditiva no payload E2, mas não consumida; provado
  por `dev/golden_diff.py` zero-delta.
- `dev/check_pipeline_boundaries.py` + `dev/check_code_style_regression.py` verdes.

## Não-escopo

- Cutover de leitores `valor`→`amount` + deprecação de `valor` → A24 (2ª fase).
- `amount` na posição de investimento (2º contrato canônico) → fora de B5.
- Emissão de `source_ref` no `content_json` → F2 (`dl-f1-extract-check`/de-leak).

## Owner sugerido

`data-engineer` (formato canônico + gate de paridade + inventário de leitores). Co-design
da decisão em [[ADR-278]] §B5.
