---
id: RULE-composicao-patrimonial-7-categorias
type: domain-rule
concept: "Composição patrimonial canônica (7 categorias)"
methodology: [auvp, perini]
canonical_adr: "[[ADR-145]]"
enforcer_modules:
  - pipeline/domain/services/patrimonio_calculator.py
formula_ref: "FORMULAS.md#patrimônio"
tags:
  - type/domain-rule
  - methodology/auvp
  - methodology/perini
---

# RULE — Composição patrimonial (7 categorias)

**Conceito.** Taxonomia fixa de 7 buckets para o doughnut da Composição Patrimonial: (1) Residência própria, (2) Imóveis investimento, (3) Investimentos {TITULAR}, (4) Investimentos {CONJUGE}, (5) Criptoativos, (6) Caixa + Moeda Estrangeira, (7) Veículos.

**Por quê.** Comparabilidade entre relatórios e benchmarks externos é parte do produto; N categorias dinâmicas por workspace quebrariam comparação e UI. As 7 fixas capturam a nuance de produto (Perini distingue residência de investimento; AUVP distingue patrimônio investível por membro) sem pulverizar.

**Doutrina canônica.** Decidida em [ADR-145](../../adr/145-7-categorias-canonical-da-composicao-patrimonial.md). Alternativas rejeitadas: (a) N categorias dinâmicas — quebra comparabilidade e infla complexidade sem demanda; (b) 5 categorias agregadas — perde granularidade clínica entre residência × investimento e titular × cônjuge. Premissa de produto: exatamente 2 titulares de investimentos (>2 membros = ADR futuro). `template_key` interno é estável — renaming PROIBIDO (apenas add/deprecate, paralelo a ADR-137).

**Enforcer.**
- [`pipeline/domain/services/patrimonio_calculator.py`](../../../pipeline/domain/services/patrimonio_calculator.py) — `PatrimonioCalculator` aplica regras determinísticas; docstring carrega a especificação canônica (rules-as-code, ADR-143).

**Fórmula.** Ver [FORMULAS.md §Patrimônio](../FORMULAS.md#patrimônio) (`bruto = cat_1 + … + cat_7`, e `investivel_financeiro = cat_3 + cat_4 + cat_5 + cat_6`).

**Metodologias.** AUVP (composição multi-classe com separação titular/cônjuge) + Perini (residência principal exclusa do patrimônio investível, distinção do imóvel-investimento).
