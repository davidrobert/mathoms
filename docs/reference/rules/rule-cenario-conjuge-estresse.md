---
id: RULE-cenario-conjuge-estresse
type: domain-rule
concept: "Cenário de estresse Sem renda do cônjuge"
methodology: [cerbasi]
canonical_adr: "[[ADR-167]]"
enforcer_modules:
  - pipeline/domain/services/cenarios_conjuge_analyzer.py
  - pipeline/domain/services/methodology_constants.py
formula_ref: null
tags:
  - type/domain-rule
  - methodology/cerbasi
---

# RULE — Cenário de estresse "Sem renda do cônjuge"

**Conceito.** Stress test que recalcula IF do casal removendo a renda do cônjuge e reduzindo o aporte mensal por `APORTE_REDUZIDO_FATOR_CONJUGE = 0.66` (66% do aporte total preservado). Eligibility gate determinístico decide se o bloco entra no payload E5 — não é cenário universal **obrigatório**, é universal **condicionado**.

**Por quê.** Aplicar o cenário a solteiros, casais com 1 renda só, ou famílias onde o cônjuge tem <15% da renda total gera ruído: tabela com cenário irrelevante, narrativa LLM forçada, APP_C ocupando página em PDF premium sem servir o cliente.

**Doutrina canônica.** Decidida em [ADR-167](../../adr/167-eligibility-gate-de-cenario-do-conjuge-no-domain.md). Critérios: (a) `if_meta > 0`, (b) ≥2 membros com renda recorrente, (c) renda do cônjuge ≥15% da renda familiar. Função `should_render_conjuge_scenarios` no domain service decide; pipeline E5 omite quando `False`. Frontend só checa presença (`if (!data.cenarios_conjuge) return null`) — zero lógica de elegibilidade duplicada em TS (combate drift backend↔frontend, ADR-143). Numeração estável A/B/C/D/E preservada — APP_C oculto não recompõe APP_D para "C". Alternativas (frontend decide / orchestrator decide) rejeitadas — granularidade errada.

**Enforcer.**
- [`pipeline/domain/services/cenarios_conjuge_analyzer.py`](../../../pipeline/domain/services/cenarios_conjuge_analyzer.py) — `CenariosConjugeAnalyzer` + `should_render_conjuge_scenarios` (eligibility gate).
- [`pipeline/domain/services/methodology_constants.py`](../../../pipeline/domain/services/methodology_constants.py) — constante `APORTE_REDUZIDO_FATOR_CONJUGE` (ADR-177).

**Metodologias.** Cerbasi (Equilíbrio Financeiro — casal de renda dupla preserva ~2/3 da poupança quando uma renda cessa; resiliência financeira como contingência operacional).
