---
id: RULE-concentracao-imobiliaria
type: domain-rule
concept: "Concentração imobiliária (>50% PL = alerta)"
methodology: [perini, auvp]
canonical_adr: "[[ADR-177]]"
enforcer_modules:
  - pipeline/domain/services/methodology_constants.py
  - pipeline/domain/services/patrimonio_calculator.py
formula_ref: null
tags:
  - type/domain-rule
  - methodology/perini
  - methodology/auvp
---

# RULE — Concentração imobiliária

**Conceito.** Constante imutável `IMOVEL_PCT_PATRIMONIO_IDEAL = 50` (Decimal). Quando a soma de imóveis (residência + investimento) ultrapassa 50% do patrimônio líquido, o relatório sinaliza alerta de concentração — passivo imobilizado dominante em vez de carteira diversificada.

**Por quê.** Concentração imobiliária >50% é sinal canônico de risco em ambas as metodologias do produto: Perini ("Viver de Renda" — patrimônio dominado por imóvel é passivo imobilizado, não carteira de renda) e AUVP (princípio de diversificação multi-classe). Threshold é universal — não varia por workspace nem por data fiscal — então **não cabe em DB versionada** (estilo `fiscal_parameters`); custo de migration sem ganho concreto.

**Doutrina canônica.** Decidida em [ADR-177](../../adr/177-thresholds-e-referencias-metodologicas-como.md) (rules-as-code consolidation Sprint A10.2). Alternativas rejeitadas: (1) `goals.json` como source of truth via `ConfigStore.get_methodology_thresholds()` — perpetua mock-config-driven, ninguém edita JSON em produção (ADR-143 já provou); (2) tabela DB versionada estilo `fiscal_parameters` — overkill para 7 thresholds estáveis. Mudar o valor exige PR + revisão (gate intencional); demanda real de override por cliente migra para Goal type dedicado.

**Enforcer.**
- [`pipeline/domain/services/methodology_constants.py`](../../../pipeline/domain/services/methodology_constants.py) — `IMOVEL_PCT_PATRIMONIO_IDEAL: Decimal = Decimal("50")`.
- [`pipeline/domain/services/patrimonio_calculator.py`](../../../pipeline/domain/services/patrimonio_calculator.py) — consumidor (sinaliza concentração na composição patrimonial).

**Validação.** Test unitário afirma invariante: `IMOVEL_PCT_PATRIMONIO_IDEAL == Decimal("50")`. Drift via JSON de config eliminado (zero `goals_cfg["thresholds"]["imovel_pct…"]` no codebase pós-A10.2).

**Metodologias.** Perini (Viver de Renda — passivo imobilizado vs. carteira de renda) + AUVP (diversificação multi-classe como princípio canônico, não preferência opcional).
