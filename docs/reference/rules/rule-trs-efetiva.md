---
id: RULE-trs-efetiva
type: domain-rule
concept: "TRS efetiva"
methodology: [perini, auvp]
canonical_adr: "[[ADR-164]]"
enforcer_modules:
  - pipeline/domain/services/passive_income_calculator.py
  - pipeline/domain/services/ratios_calculator.py
formula_ref: "FORMULAS.md#independência-financeira"
tags:
  - type/domain-rule
  - methodology/perini
  - methodology/auvp
---

# RULE — TRS efetiva

**Conceito.** Taxa de Retirada Sustentável **efetiva** = `renda_passiva_anual_observada / patrimonio_gerador_brl × 100`. Confronta o yield real da carteira de renda do cliente com a TRS-meta (5% Perini / 4% Trinity).

**Por quê.** Sem TRS efetiva o produto só projeta IF; não responde "minha carteira sustenta retirada **hoje**?". É a pergunta canônica do Perini e o gatilho da regra `rule_trs_desalinhada`. Renda passiva nominal (R$/mês) entra primeiro na UI para evitar erro do iniciante "vender growth para perseguir DY".

**Doutrina canônica.** Decidida em [ADR-164](../../adr/164-carteira-de-renda-e-taxa-de-retirada-efetiva.md). Numerador agrega buckets RFB do IRPF (dividendos, JCP, aplicações, ganho de capital, exterior, aluguéis re-classificados de trabalho → capital). Denominador inclui investimentos, caixa excedente, imóveis investimento (config), e ativos com yield 0% (cripto/growth/PGBL acumulação) — excluí-los mascararia concentração. Filtro de fase: regra só dispara com `goals.if_pct >= 50` para evitar ruído em acumuladores.

**Enforcer.**
- [`pipeline/domain/services/passive_income_calculator.py`](../../../pipeline/domain/services/passive_income_calculator.py) — `PassiveIncomeCalculator`, computa numerador e denominador.
- [`pipeline/domain/services/ratios_calculator.py`](../../../pipeline/domain/services/ratios_calculator.py) — campo `rentabilidade_pct` (TRS efetiva) consumido pelo S7.

**Fórmula.** Ver [FORMULAS.md §Independência Financeira](../FORMULAS.md#independência-financeira) (campo `progresso_if_pct` e fórmulas correlatas).

**Metodologias.** Convergência Perini (taxa de retirada sobre carteira de renda real, não 4% genérico) + AUVP (composição multi-classe com yield diferenciado por bucket).
