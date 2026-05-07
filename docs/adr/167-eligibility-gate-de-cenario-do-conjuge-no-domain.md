---
id: ADR-167
type: adr
title: "Eligibility gate de cenário do cônjuge no domain service"
status: Decidido
phase: "A8.4 PR2"
date: "2026-05-06"
relates_to: ["[[ADR-143]]", "[[ADR-166]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 167"]
tags:
  - type/adr
  - status/decidido
size_lines: 52
---

# ADR-167 — Eligibility gate de cenário do cônjuge no domain service

**Status:** Decidido (A8.4 PR2) • **Data:** 2026-05-06 • **Relaciona** [ADR-143](#adr-143--docsmethodology-é-rules-as-code-sprint-a76), [ADR-166](#adr-166--schema-estável-cenarios_conjuge-no-payload-e5).

**Contexto:** O analyzer `cenarios_conjuge_analyzer.py` (PR2 reduz a 1 cenário "Sem renda do cônjuge") computa stress test de IF para casais com 2 rendas. Aplicar universalmente — para solteiros, casais com 1 renda, ou famílias onde cônjuge tem renda <15% — gera ruído: tabela com cenário irrelevante, narrativa LLM forçada, APP_C ocupando página em PDF premium sem servir o cliente. financial-planner (consultado em A8.4 / 2026-05-06) é taxativo: cenário é universal **conditionado**, não universal **obrigatório**.

**Decisão:** Função pura `should_render_conjuge_scenarios(family_members, fluxo, goals) -> bool` no domain service (`pipeline/domain/services/cenarios_conjuge_analyzer.py`) decide se o bloco entra no payload. Pipeline E5 omite o bloco quando `False`. Frontend só checa presença (`if (!data.cenarios_conjuge) return null`) — zero lógica de elegibilidade duplicada em TS (ADR-143 combate drift backend↔frontend).

**Critérios de elegibilidade (universal, Cerbasi/Perini, ≤20 linhas):**

```python
def should_render_conjuge_scenarios(*, family_members, fluxo, goals) -> bool:
    """ADR-167: cenário 'cônjuge sem trabalhar' é elegível?

    Critérios:
    - Meta IF presente (if_meta > 0)
    - ≥2 membros com renda recorrente
    - Renda do cônjuge ≥15% da renda familiar total

    Casos:
      Solteiro / 1 renda                → False (sem o que stressar)
      Casal sem meta IF                 → False (sem âncora de impacto)
      Casal 95/5 (cônjuge < 15%)         → False (impacto < ruído)
      Casal 70/30 + meta IF              → True
      Casal 60/40 + meta IF              → True
    """
```

**Alternativas avaliadas:**

- (a) Frontend decide (sempre recebe payload, oculta quando vazio) — duplica regra em TS; risco de drift que ADR-143 combate.
- (b) `section_summary_orchestrator` decide quais seções listar — orchestrator é seção-level, gate é chart-level; granularidade errada.
- (c) **Pipeline E5 emite ou omite** ✅ — uma camada decide; frontend confia no payload.

**Consequências:**

- ✅ Regra co-localizada com enforcer (ADR-143).
- ✅ APP_C dinâmico: workspace solteiro → APP_C ausente; workspace casal 70/30 → APP_C presente.
- ✅ Numeração estável A/B/C/D/E preservada — APP_C oculto não recompõe APP_D para "C" (D4 do plano A8.4).
- ⚠️ Mudança de elegibilidade entre ciclos do mesmo workspace (ex.: cônjuge passa a ter renda) muda payload — esperado e desejável; planner explica ao cliente.

**Critério de aceite (PR2):**

- 4 unit tests cobrindo: 1 renda, 2 rendas casal elegível, 2 rendas solteiro, casal sem renda do cônjuge.
- Workspace de teste com 1 renda → payload sem `cenarios_conjuge`.
- Workspace de teste com 2 rendas 70/30 + meta IF → payload com `cenarios_conjuge` (1 cenário).

**Follow-ups:**

1. Cenários adicionais (perda de renda do titular, aposentadoria antecipada) propostos pelo financial-planner — backlog futuro (A8.4 §8 backlog).
