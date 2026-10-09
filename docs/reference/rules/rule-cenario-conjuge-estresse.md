---
id: RULE-cenario-conjuge-estresse
type: domain-rule
concept: "Cenário de estresse Sem renda do cônjuge"
methodology: [cerbasi]
canonical_adr: "[[ADR-167]]"
enforcer_modules:
  - pipeline/domain/services/cenarios_conjuge_analyzer.py
  - pipeline/domain/services/e5_analyzer_adapter.py
  - pipeline/domain/services/methodology_constants.py
formula_ref: null
tags:
  - type/domain-rule
  - methodology/cerbasi
---

# RULE — Cenário de estresse "Sem renda do cônjuge"

**Conceito.** Stress test que recalcula IF do casal removendo a renda do cônjuge e reduzindo o aporte mensal por `APORTE_REDUZIDO_FATOR_CONJUGE = 0.66` (66% do aporte total preservado). Eligibility gate determinístico decide se o bloco entra no payload E5 — não é cenário universal **obrigatório**, é universal **condicionado**.

**Por quê.** Aplicar o cenário a solteiros, casais com 1 renda só, ou famílias onde o cônjuge tem <15% da renda total gera ruído: tabela com cenário irrelevante, narrativa LLM forçada, APP_C ocupando página em PDF premium sem servir o cliente.

**Doutrina canônica.** Decidida em [ADR-167](../../adr/167-eligibility-gate-de-cenario-do-conjuge-no-domain.md), emendada em 2026-10-09. `veredito_cenario_conjuge(conjuge_key, if_meta)` decide pelo que o cadastro prova: cônjuge declarado (`papel = conjuge`) e meta IF > 0. Os critérios de renda da redação original — ≥2 membros com renda recorrente e cônjuge ≥15% da renda familiar — estão **deferidos**: o label de receita não carrega o membro, então a divisão não é mensurável; a retomada é o escritor de `protection_income_declarations` ([ADR-387](../../adr/387-protection-computation-snapshot-v1-computabilidade-por-categoria.md)). Casal sem divisão mensurável fica elegível (fail-open). Inelegível → `cenarios_conjuge: {}`, a forma canônica de "omitido". O frontend lê presença em um lugar (`readCenariosConjuge`, em `frontend/src/components/report/utils/reportContractGuards.ts`) para S3, APP_C e o card de aportes — zero lógica de elegibilidade em TS (combate drift backend↔frontend, ADR-143). Numeração estável A/B/C/D/E preservada — APP_C oculto não recompõe APP_D para "C". Alternativas (frontend decide / orchestrator decide) rejeitadas — granularidade errada.

**Enforcer.**
- [`pipeline/domain/services/cenarios_conjuge_analyzer.py`](../../../pipeline/domain/services/cenarios_conjuge_analyzer.py) — `CenariosConjugeAnalyzer` + `veredito_cenario_conjuge` (eligibility gate).
- [`pipeline/domain/services/e5_analyzer_adapter.py`](../../../pipeline/domain/services/e5_analyzer_adapter.py) — `E5AnalyzerAdapter._cenarios_conjuge` aplica o veredito antes do cálculo e o loga.
- [`pipeline/domain/services/methodology_constants.py`](../../../pipeline/domain/services/methodology_constants.py) — constante `APORTE_REDUZIDO_FATOR_CONJUGE` (ADR-177).

**Metodologias.** Cerbasi (Equilíbrio Financeiro — casal de renda dupla preserva ~2/3 da poupança quando uma renda cessa; resiliência financeira como contingência operacional).
