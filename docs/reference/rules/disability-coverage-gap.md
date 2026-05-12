---
id: RULE-disability-coverage-gap
type: domain-rule
concept: "Gap de cobertura de invalidez (Cerbasi)"
methodology: [cerbasi]
canonical_adr: "[[ADR-192]]"
enforcer_modules:
  - pipeline/domain/services/protection/disability_coverage.py
tags:
  - type/domain-rule
  - methodology/cerbasi
  - area/domain
---

# RULE — Gap de cobertura de invalidez

**Conceito.** Famílias com **renda ativa dominante** (`renda_ativa > 40% da renda total`) carregam risco concentrado em capital humano. Cerbasi recomenda cobertura mensal de invalidez ≥ **60% da renda ativa líquida** para sustentar o padrão essencial enquanto o titular se reorganiza ou retoma capacidade laborativa parcial.

**Por quê.** Sem cobertura, invalidez total ou parcial colapsa o fluxo de caixa sem suporte de patrimônio gerador. O gate de 40% (renda ativa / renda total) garante que o calculator não dispara quando o cliente já tem renda passiva substancial que cobre o risco. O 60% (`target_pct`) coincide com a fração de despesa essencial típica observada no perfil Mathoms — abaixo disso o orçamento essencial colapsa.

**Doutrina canônica.** Decidida em [ADR-192](../../adr/192-protection-aggregate-protectionbundle-secao-9.md) §D3 (Sprint A11.W5, S9-T03). Calculator puro (ADR-097 D3 / ADR-111). Thresholds (`target_pct=0.60`, `dependency_threshold=0.40`) hardcoded como constantes no calculator com referência à fonte metodológica — não vêm de `fiscal_parameters` porque são thresholds **metodológicos**, não fiscais.

**Enforcer.**
- [`pipeline/domain/services/protection/disability_coverage.py`](../../../pipeline/domain/services/protection/disability_coverage.py) — `disability_coverage_gap(DisabilityInputs) -> CoverageGap`. Emite `RiskInferred("invalidez_subcobertura")` quando share > 40% **e** gap > R$ 1k/mês.

**Disclaimer fiduciário.** "Estimativa metodológica baseada em Cerbasi (renda ativa dominante → 60% mínimo); não constitui recomendação fiduciária. Consultar corretor habilitado pela Susep e planejador CFP®. Dados fiscais válidos para `<effective_date>`."

**Fórmula.**

```
share_ativa     = renda_ativa / (renda_ativa + renda_passiva)
target_coverage = renda_ativa × target_pct       (target_pct = 0.6 default)
gap_mensal      = max(0, target_coverage - cobertura_atual_mensal)

dispara_risk    = (share_ativa > 0.40) AND (gap_mensal > R$ 1k/mês)
impact_anual    = gap_mensal × 12   (campo RiskInferred.estimated_impact_brl_cents)
```

**Casos de teste.** [tests/pipeline/domain/services/protection/test_disability_coverage.py](../../../tests/pipeline/domain/services/protection/test_disability_coverage.py) cobre 9 perfis:
- solteiro CLT sem cobertura,
- casado com renda passiva majoritária (não dispara),
- expatriado freelance com cobertura parcial,
- share exatamente 40% (gate strict),
- workspace vazio,
- disclaimer presente,
- idempotência,
- gap imaterial (< R$ 1k/mês),
- cobertura > target (gap=0).

**Metodologias.** Apenas Cerbasi trata gap de invalidez de forma quantitativa no corpus Mathoms. Perini e AUVP focam em alocação patrimonial; não overrid am esta regra.
