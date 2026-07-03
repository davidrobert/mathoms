---
id: RULE-concentracao-imobiliaria
type: domain-rule
concept: "Concentração imobiliária (alerta S4 >40% do patrimônio; narrativa E5.N referencia ideal 50%)"
methodology: [perini, auvp]
canonical_adr: "[[ADR-177]]"
enforcer_modules:
  - pipeline/domain/services/real_estate_metrics.py
  - pipeline/domain/services/real_estate_metrics_aggregator.py
  - pipeline/domain/services/methodology_constants.py
formula_ref: null
tags:
  - type/domain-rule
  - methodology/perini
  - methodology/auvp
---

# RULE — Concentração imobiliária

**Conceito.** Dois thresholds coexistem, com papéis distintos:

- **Alerta do produto (S4):** quando a soma de imóveis ultrapassa
  `RealEstateConfig.concentracao_alerta_pct = Decimal("40.0")` do patrimônio,
  o aggregator emite o alerta `concentracao_alta` (FORMULAS.md §Imóveis).
  Default configurável com override por workspace (ADR-134).
- **Referência narrativa (E5.N):** a constante imutável
  `IMOVEL_PCT_PATRIMONIO_IDEAL = 50` (Decimal) é exposta apenas ao narrador
  LLM (`threshold_imovel_pct` em `scripts/e5n_narrativas.py`) como marco
  "ideal" das metodologias — **não dispara alerta**.

Concentração imobiliária alta = passivo imobilizado dominante em vez de carteira diversificada.

**Por quê.** Concentração imobiliária >50% é sinal canônico de risco em ambas as metodologias do produto: Perini ("Viver de Renda" — patrimônio dominado por imóvel é passivo imobilizado, não carteira de renda) e AUVP (princípio de diversificação multi-classe). Threshold é universal — não varia por workspace nem por data fiscal — então **não cabe em DB versionada** (estilo `fiscal_parameters`); custo de migration sem ganho concreto.

**Doutrina canônica.** Decidida em [ADR-177](../../adr/177-thresholds-e-referencias-metodologicas-como.md) (rules-as-code consolidation Sprint A10.2). Alternativas rejeitadas: (1) `goals.json` como source of truth via `ConfigStore.get_methodology_thresholds()` — perpetua mock-config-driven, ninguém edita JSON em produção (ADR-143 já provou); (2) tabela DB versionada estilo `fiscal_parameters` — overkill para 7 thresholds estáveis. Mudar o valor exige PR + revisão (gate intencional); demanda real de override por cliente migra para Goal type dedicado.

**Enforcer.**
- [`pipeline/domain/services/real_estate_metrics.py`](../../../pipeline/domain/services/real_estate_metrics.py) — `RealEstateConfig.concentracao_alerta_pct: Decimal = Decimal("40.0")` (default do alerta).
- [`pipeline/domain/services/real_estate_metrics_aggregator.py`](../../../pipeline/domain/services/real_estate_metrics_aggregator.py) — dispara `concentracao_alta` quando `concentracao_pct > config.concentracao_alerta_pct`.
- [`pipeline/domain/services/methodology_constants.py`](../../../pipeline/domain/services/methodology_constants.py) — `IMOVEL_PCT_PATRIMONIO_IDEAL: Decimal = Decimal("50")`, consumida só por `scripts/e5n_narrativas.py` (contexto do narrador LLM).

**Validação.** Test unitário afirma invariante da constante narrativa: `IMOVEL_PCT_PATRIMONIO_IDEAL == Decimal("50")` (`tests/test_methodology_constants.py`). Drift via JSON de config eliminado (zero `goals_cfg["thresholds"]["imovel_pct…"]` no codebase pós-A10.2).

**Metodologias.** Perini (Viver de Renda — passivo imobilizado vs. carteira de renda) + AUVP (diversificação multi-classe como princípio canônico, não preferência opcional).
