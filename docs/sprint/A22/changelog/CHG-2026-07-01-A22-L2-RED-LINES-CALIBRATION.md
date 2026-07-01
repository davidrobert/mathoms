---
id: CHG-2026-07-01-A22-L2-RED-LINES-CALIBRATION
type: changelog-entry
date: "2026-07-01"
sprint: A22
lane: "[[A22.l2]]"
adrs: ["[[ADR-300]]"]
prs: [697, 698, 700, 701]
summary: |
  Calibração das red lines do parecer via 2 rodadas de dogfood do eval LLM
  (RED_LINES_VERSION 1.0→1.4 + PROMPT_VERSION 2.1.0). O eval real pegou over-firing
  em massa (needs_review 90%): RL3 casava garantia isolada e substring
  ("comprometer"/"incerteza"); RL1 bloqueava planejamento de arcabouço e
  rebalanceamento/de-risking como se fossem deploy de risco; RL7 exigia severidade
  Alta em toda concentração >40%. Fixes (co-design financial-planner + senior-cto):
  RL3 exige garantia+objeto-de-retorno em proximidade + \b anti-substring (#697/#700);
  RL1 composicional exec-conjugado ∧ objeto ∧ ¬(rebalance∨planejamento) (#698); RL7
  graduado >60%|alerta→Alta, 40-60%→Média+ (#700); REGRA 14 prompt-side espelhando os
  predicados como prevenção (#701). Holdout do eval estratificado por cobertura_meses
  com estrato de controle negativo (mede precision). Resultado: needs_review 90%→~14%
  (dentro do budget UX ≤15% da A26.l2), densidade de citação preservada. Segurança
  fail-closed inalterada.
tags:
  - type/changelog-entry
  - sprint/a22
  - area/llm
  - area/seguranca
---
