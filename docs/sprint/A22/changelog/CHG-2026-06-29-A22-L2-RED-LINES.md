---
id: CHG-2026-06-29-A22-L2-RED-LINES
type: changelog-entry
date: "2026-06-29"
sprint: A22
lane: "[[A22.l2]]"
adrs: ["[[ADR-300]]"]
prs: [690]
summary: |
  Camada de red lines do parecer (F3-O1 / KR7). 4ª validação determinística
  parecer_red_lines.py: 7 red lines como predicados puros (output dict + E5, zero
  LLM); _check_red_lines roda 1º no orchestrator; ≥1 hard-block → needs_review
  GLOBAL (não drop per-item). RED_LINES_VERSION no cache key; red_lines_summary p/
  drift. Predicados reconciliados contra campos reais do E5 (financial-planner):
  RL1 reserva-antes-de-risco · RL2 dívida-cara (best-effort) · RL3 promessa-retorno
  (CVM) · RL4 ticker · RL5 P0-sem-âncora · RL6 mexer-reserva/proteção · RL7
  subdiagnóstico. Eval determinístico no PR gate (14 envenenadas + 7 limpas +
  completude). ADR-300 Decidido. Prompt-side (REGRA 14) fica owner-gated.
tags:
  - type/changelog-entry
  - sprint/a22
  - area/llm
  - area/seguranca
---
