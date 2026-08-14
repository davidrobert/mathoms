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

> **Hold normativo 2026-08-14 ([[ADR-387]]).** O gap é por segurado. Cobertura
> atual exige benefício mensal contratual e inventário confirmado; dividir
> capital segurado por 12 é proibido. Até o contrato existir, `missing_data`.

**Conceito.** Para cada segurado, comparar o benefício mensal contratual com uma
fração versionada da sua renda ativa líquida recorrente. O calculator Mathoms
histórico usa gates de 40% de dependência da renda ativa e alvo de 60%; são
heurísticas metodológicas, não prova de suficiência contratual.

**Por quê.** Invalidez pode interromper a renda do trabalho. A estimativa serve
para explicitar quanto do alvo metodológico não está coberto pelo benefício
mensal confirmado, sem inferir que capital único, patrimônio ou cobertura de
outra pessoa substituem essa renda.

**Doutrina canônica.** A fórmula histórica foi decidida em
[ADR-192](../../adr/192-protection-aggregate-protectionbundle-secao-9.md) §D3.
Seus thresholds são metodológicos, não fiscais, e precisam de versão explícita
no snapshot da [[ADR-387]].

**Computabilidade (emenda 2026-08-13).** Renda ativa e passiva líquidas mensais
devem vir da mesma base temporal. Ausência de qualquer lado produz
`missing_data`; receita recorrente bruta ou subtração entre janelas não é proxy.
O calculator também exige `insured_family_member_id`, benefício mensal na unidade
contratual e completude do inventário. Capital único permanece descritivo e não
reduz o gap mensal.

**Enforcer.**
- [`pipeline/domain/services/protection/disability_coverage.py`](../../../pipeline/domain/services/protection/disability_coverage.py) — `disability_coverage_gap(DisabilityInputs) -> CoverageGap`. Emite `RiskInferred("invalidez_subcobertura")` quando share > 40% **e** gap > R$ 1k/mês.

**Disclaimer fiduciário.** "Estimativa metodológica baseada em Cerbasi (renda ativa dominante → 60% mínimo); não constitui recomendação fiduciária. Consultar corretor habilitado pela Susep e planejador CFP®. Dados fiscais válidos para `<effective_date>`."

**Fórmula histórica sob hold.** `cobertura_atual_mensal` só pode ser benefício
mensal contratual do mesmo segurado, com inventário confirmado.

```
share_ativa     = renda_ativa / (renda_ativa + renda_passiva)
target_coverage = renda_ativa × target_pct       (target_pct = 0.6 default)
gap_mensal      = max(0, target_coverage - cobertura_atual_mensal)

dispara_risk    = (share_ativa > 0.40) AND (gap_mensal > R$ 1k/mês)
impact_anual    = gap_mensal × 12   (campo RiskInferred.estimated_impact_brl_cents)
```

**Cobertura de teste legada.** [tests/pipeline/domain/services/protection/test_disability_coverage.py](../../../tests/pipeline/domain/services/protection/test_disability_coverage.py) cobre 9 perfis do calculator puro; não satisfaz, sozinho, o gate de computabilidade:
- solteiro CLT sem cobertura,
- casado com renda passiva majoritária (não dispara),
- expatriado freelance com cobertura parcial,
- share exatamente 40% (gate strict),
- workspace vazio,
- disclaimer presente,
- idempotência,
- gap imaterial (< R$ 1k/mês),
- cobertura > target (gap=0).

**Metodologias.** O corpus Mathoms atribui a regra quantitativa a Cerbasi. Perini
e AUVP não adicionam fórmula concorrente neste contrato.
