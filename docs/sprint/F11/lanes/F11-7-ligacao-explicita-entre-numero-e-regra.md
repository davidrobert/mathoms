---
id: F11.7
type: lane
title: "Ligação explícita entre número e regra"
sprint: F11
status: in_progress
priority: P1
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f11
  - status/in-progress
  - priority/p1
---


# F11.7 — Ligação explícita entre número e regra


| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.7a | **Catálogo de fórmulas** relevantes (FV anuidade, etc.): texto curto + referência ao código ou doc (`compute_if_derived`, E5). | P1 | 6h | ✅ [FORMULAS.md](FORMULAS.md) + `reportFormulas.ts` |
| F11.7b | **UI:** tooltip ou painel “Como calculamos” a partir de KPIs principais e metas; link para glossário. | P1 | 8h | ✅ Bloco premissas + glossário expansível no relatório nativo |
| F11.7c | **Testes:** golden ou snapshot garante que o número exibido bate com o motor para casos fixos. | P1 | 4h | 🚧 Smoke vitest do catálogo (`tests/lib/reportFormulas.test.ts`); golden motor ↔ UI deferido |
