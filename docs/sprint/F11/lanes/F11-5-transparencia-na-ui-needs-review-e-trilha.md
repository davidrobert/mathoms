---
id: F11.5
type: lane
title: "Transparência na UI: `needs_review` e trilha LLM"
sprint: F11
status: shipped
priority: P0
adrs: ["[[ADR-068]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f11
  - status/shipped
  - priority/p0
---


# F11.5 — Transparência na UI: `needs_review` e trilha LLM


| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.5a | **Mapa de estados:** definir rótulos user-facing para: sucesso determinístico; dado inferido por LLM; `needs_review`; falha de estágio. Proibido expor códigos internos E0–E7 na UI (ADR-068). | P0 | 4h | ✅ Sprint B: `pipelineTransparency.ts` (footnote LLM por etapa); removido badge com código E* na linha de etapa; `pipelineE2TouchLabel` sem “E2” na UI |
| F11.5b | **Pipeline / Relatório:** banner ou badge persistente quando houver revisão pendente; link para tela de review ou lista de itens. | P0 | 8h | ✅ Sprint B: banner `needs_review` reforçado + CTA retomar (já existia; copy e caixa LLM) |
| F11.5c | **Linguagem de risco:** distinguir “pode afetar categorização” vs “pode afetar saldo exibido”; texto revisado por produto. | P1 | 3h | ✅ Sprint B: `reviewPauseImpactHint()` por etapa pausada |
