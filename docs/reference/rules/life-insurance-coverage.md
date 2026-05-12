---
id: RULE-life-insurance-coverage
type: domain-rule
concept: "Cobertura ideal de seguro de vida (Cerbasi + Perini)"
methodology: [cerbasi, perini]
canonical_adr: "[[ADR-192]]"
enforcer_modules:
  - pipeline/domain/services/protection/life_insurance_coverage.py
tags:
  - type/domain-rule
  - methodology/cerbasi
  - methodology/perini
  - area/domain
---

# RULE — Cobertura ideal de seguro de vida

**Conceito.** Capital segurado ideal = `max(Cerbasi, Perini) + dívidas em aberto`. Calculator determinístico recebe value object tipado e emite `CoverageRecommendation` com decomposição auditável (`cerbasi_ideal_brl_cents`, `perini_ideal_brl_cents`, `ideal_brl_cents`, `methodology="max"`).

**Por quê.** Cobertura insuficiente é o risco financeiro mais comum em famílias com renda ativa dominante e dependentes em minoridade — quita dívidas, substitui renda durante o luto e cobre custos de educação até a maioridade do dependente mais novo. Duas escolas convergem:

- **Cerbasi** (`Equilíbrio Financeiro` §"Proteção da Renda"): regra de bolso `10× renda_anual × fator_dependência` (1.0 sem deps minoridade · 1.5 com 1-2 · 2.0 com 3+). Simples de comunicar; assume reposição de renda durante uma década (suficiente para reorganização familiar).
- **Perini** (`Viver de Renda`): PV de fluxo de renda anual durante anos restantes de minoridade do dependente mais novo, descontado por taxa real conservadora (default 3% a.a.). Mais fiel a famílias jovens com filhos pequenos — Cerbasi tende a subestimar quando o horizonte de dependência ainda é longo.

`max` é a postura conservadora para evitar pegar o cliente em sub-cobertura pelo lado menos pessimista. Ambos os números ficam expostos no output para o planejador justificar o pick.

**Doutrina canônica.** Decidida em [ADR-192](../../adr/192-protection-aggregate-protectionbundle-secao-9.md) §D3 (Sprint A11.W5, S9-T03). Calculator puro (ADR-097 D3 / ADR-111 stateless rigoroso); thresholds vêm de constantes documentadas como débito de migração para `fiscal_parameters` (ADR-135).

**Enforcer.**
- [`pipeline/domain/services/protection/life_insurance_coverage.py`](../../../pipeline/domain/services/protection/life_insurance_coverage.py) — `life_insurance_coverage_ideal(LifeInsuranceInputs) -> CoverageRecommendation`. Emite `RiskInferred("falta_seguro_vida_cobertura_insuficiente")` quando gap > 5% do ideal **e** > R$ 50k.
- Adapter (app layer): [`backend/app/services/protection_bundle_adapter.py`](../../../backend/app/services/protection_bundle_adapter.py) injeta value objects a partir do DB (family_members, dívidas, renda).

**Disclaimer fiduciário.** "Estimativa metodológica baseada em Cerbasi (10× renda) e Perini (PV minoridade); não constitui recomendação fiduciária. Consultar corretor habilitado pela Susep e planejador CFP®. Dados fiscais válidos para `<effective_date>`."

**Fórmula.**

```
fator(n_minors) = 1.0  se n_minors == 0
                = 1.5  se n_minors ∈ {1, 2}
                = 2.0  se n_minors >= 3

cerbasi_ideal  = 10 × renda_anual_ativa × fator(n_minors) + dívidas
perini_ideal   = renda_anual_ativa × ((1 - (1+i)^-n) / i) + dívidas
                 onde i = taxa_real_anual / 100
                       n = 18 - idade_dep_mais_novo (anos)

ideal = max(cerbasi_ideal, perini_ideal)
gap   = max(0, ideal - cobertura_atual)
```

**Casos de teste.** [tests/pipeline/domain/services/protection/test_life_insurance_coverage.py](../../../tests/pipeline/domain/services/protection/test_life_insurance_coverage.py) cobre 12 perfis:
- solteiro sem renda (zero everything),
- solteiro com renda (Cerbasi puro),
- casado com 2 deps minoridade (max ativo),
- dependente recém-nascido (Perini 18 anos),
- cliente over-segurado (gap=0),
- gap imaterial,
- disclaimer presente,
- idempotência,
- fator 2× com 3+ deps,
- deps em maioridade (fator 1.0),
- renda negativa/zero (não explode).

**Metodologias.** Cerbasi (regra de bolso operacional) + Perini (PV anuidade conservadora). AUVP não trata cobertura ideal explicitamente; mantém-se fora desta regra.
