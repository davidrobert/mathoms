---
id: ADR-090
type: adr
title: "Decimal para valores monetários"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 090"]
tags:
  - type/adr
  - status/decidido
size_lines: 76
---

# ADR-090 — Decimal para valores monetários

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 5.2

**Contexto:** `float` tem imprecisão binária — `0.1 + 0.2` é
`0.30000000000000004`. Somas de centenas de transações acumulam erro.
Valores financeiros exigem precisão exata.

**Decisão:** `Money` (frozen dataclass) com `amount: Decimal` + `currency: str`.

Regras firmes:
- **Construtor** rejeita `float` com `TypeError`. `Money(0.1, "BRL")` quebra.
- **Factory** `Money.of(value, currency)` aceita `str | Decimal | int` — também
  rejeita `float`. Dev com float deve converter explicitamente:
  `Decimal(str(v))` no call-site.
- **Precisão por moeda** via `CURRENCY_PRECISION: dict[str, int]`:
  BRL=2, USD=2, EUR=2, JPY=0. `Money.of("1.234", "BRL")` → `Decimal("1.23")`.
- **Operadores** `+`, `-`, `neg`, `*` (rejeita float), `<`, `<=`, `==`. Moedas
  incompatíveis levantam `ValueError`.
- **Serialização:** `to_float()` existe apenas para JSON legado — documentado
  como "não usar em cálculos".

**Consequências:**
- ✅ `Money.brl("0.1") + Money.brl("0.2") == Money.brl("0.3")` (exato).
- ✅ Erros de arredondamento localizados no serializador, não acumulados.
- ✅ Moedas multi-precisão funcionam — JPY tem 0 casas, BRL 2.
- ⚠️ Conversão de `float` → `Decimal(str(v))` no call-site é carga de
  adoção — intencional, para que o dev veja o trade-off.
- ❌ Schemas JSON existentes continuam com `float` — adaptadores usam
  `to_float` / `Decimal(str(v))`.

**Follow-ups (2026-04-22, pós-A6g.6 enforcement):**

- **A6g.6** (ADR-114 ✅) instala `dev/check_float_money.py` + detector P5
  no audit que catalogam os ofensores ainda em `float` (13 em
  `backend/app/` no snapshot 2026-04-22: 7 goal DTOs + 4 transactions +
  1 tolerance + 1 helper).
- **A6g.3b** (🚧 sessões 1+2 ✅ 2026-04-22) migra campos em DTO via tipo
  `MoneyBRL = Annotated[Decimal, BeforeValidator(_coerce_to_decimal),
  PlainSerializer(float, when_used="json")]` (idem `MoneyUSD`).
  Decimal em memória + number no JSON (via serializer), preservando
  wire-compat com frontend manual que espera `number` em TS. **Sessão
  1 (slices 1+3):** tipo criado em `backend/app/schemas/money.py` +
  4 campos transactions migrados (cascade em `transaction_service` e
  `task_progress_service`). **Sessão 2 (slice 2, commit `71dc379`):**
  11 campos goal DTOs (`aporte`/`dolar`/`if_goal`) + math em
  `goal_service.py` refatorada em Decimal (`_retorno_mensal_decimal`
  via `Decimal.ln()/.exp()` — expoente fracionário não suportado
  nativo; `_pmt_constante_ate_fv`, `_if_meta_targets`,
  `_aporte_cobrindo_gap_com_patrimonio` com Decimal puro;
  `compute_dolar_derived` promove câmbio a Decimal, horizonte em
  meses fica float (duração); `.quantize(Decimal("0.01"))` em
  returns). Persistência via `model_dump(mode="json")` (SQLAlchemy
  JSON column não tem codec Decimal). OpenAPI snapshot ganha
  Input/Output split para schemas com `MoneyBRL` (Input `anyOf
  [number, string]`, Output `number` puro) — wire TS intacto.
- **A6g.3b ✅ 2026-04-22 (sessão 3, polish final):** factory
  `make_if_goal` migra `renda_passiva_mensal_brl` para `Decimal`;
  `ReconciliationTolerancesSchema.saldo_diff` ganha docstring
  explícita documentando que é **tolerância** (não money) — nome
  persistido em `config/pipeline.json` + schema, rename exigiria
  migração cruzada. Aceito como `P5_float_money=1` residual no
  baseline (false-positive do `MONEY_NAME_PATTERN` que casa `saldo`).
  Baseline regenerado: P5 total 76 → 67 (-9); backend 10 → 1.
  Frontend sanity validado via OpenAPI snapshot commitado nos
  slices 1+3 (wire continua `number`). **Lane A6g.3b fechada.**
- **Tolerâncias** (`saldo_diff`, `baseline_irpf_diff`, `score_diff_max`,
  `cv_*_diff_max`) NÃO são money — são deltas/thresholds. O audit
  pode flaggar como false positive (nome contém "saldo"). Rename para
  `_tolerance` suffix OU skip documentado em comentário (`# tolerance,
  not money`).
- **Pipeline legacy** (`pipeline/`, `scripts/e*`) continua `float` —
  escopo fora de A6g.3b. Migração dele quando `main_with_store` for
  deletado (pós-A6c) com refactor maior.
