---
id: CHG-2026-06-18-A26-L1-EVIDENCIA-CATALOGO
type: changelog-entry
date: "2026-06-18"
sprint: A26
lane: "[[A26.l1]]"
adrs: ["[[ADR-279]]", "[[ADR-292]]"]
prs: [654]
summary: |
  Catálogo de citação do evidencia_path + eval golden (ponto de entrada da A26).
  Expõe ao LLM os paths disponíveis do E5 para citação verificada (fecha o gap
  comportamental do ADR-292 onde o modelo inventava JSONPath com filtro); eval
  golden owner-gated mede conformidade. Destrava a métrica dos gates seguintes da
  Onda 5 (flip strict evidencia_path).
tags:
  - type/changelog-entry
  - sprint/a26
  - area/llm
---
