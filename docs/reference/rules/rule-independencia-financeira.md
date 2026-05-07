---
id: RULE-independencia-financeira
type: domain-rule
concept: "Independência Financeira (IF)"
methodology: [perini, auvp]
canonical_adr: "[[ADR-140]]"
enforcer_modules:
  - pipeline/domain/services/if_projector.py
  - pipeline/domain/services/passive_income_calculator.py
formula_ref: "FORMULAS.md#independência-financeira"
tags:
  - type/domain-rule
  - methodology/perini
  - methodology/auvp
---

# RULE — Independência Financeira (IF)

**Conceito.** IF = patrimônio investível efetivo que sustenta a renda passiva mensal alvo, dada uma TRS-meta. Schema v2 distingue `if_meta_bruta` (didática — `renda × 12 / TRS`) de `if_meta_liquida` (operacional — desconta a renda passiva atual já fluindo) e declara explicitamente que valores são em **BRL de hoje** (poder de compra atual, não nominal futuro).

**Por quê.** Schema v1 ignorava renda passiva atual e produzia gap superestimado: família com R$9k/mês de aluguel + meta de R$30k/mês de IF tem gap real de R$21k/mês, não R$30k. Trinity Study assume retorno e retirada **reais**; o produto opera em BRL de hoje — sem campo explícito, planejadores B2B2C podem capturar errado.

**Doutrina canônica.** Roadmap em [ADR-140](../../adr/140-goal-if-schema-v2-renda-passiva-atual-if-meta.md). `progresso_if = investivel_efetivo / if_meta_liquida × 100` é a métrica usada em score; `if_gap = MAX(0, if_meta_liquida − investivel_efetivo)`. Default `renda_passiva_atual_mensal_brl = 0` preserva v1 enquanto migrator não roda. Anti-dupla-contagem com `imoveis_no_if` está em [ADR-142](../../adr/142-toggle-imoveis-no-if-em-pipelinejson-invariante.md) — ver `RULE-imoveis-no-if`.

**Enforcer.**
- [`pipeline/domain/services/if_projector.py`](../../../pipeline/domain/services/if_projector.py) — `IFProjector`, projeção (`if_meta`, `if_pct`, `if_gap`, `prazo_anos_realista`) por juros compostos PV+PMT.
- [`pipeline/domain/services/passive_income_calculator.py`](../../../pipeline/domain/services/passive_income_calculator.py) — alimenta `renda_passiva_atual` no schema v2 (TRS efetiva).

**Fórmula.** Ver [FORMULAS.md §Independência Financeira](../FORMULAS.md#independência-financeira) — fórmulas bruta/líquida e gap.

**Metodologias.** Perini (Viver de Renda — IF como independência operacional, não independência absoluta) + AUVP (carteira que sustenta retirada calculada por classe).
