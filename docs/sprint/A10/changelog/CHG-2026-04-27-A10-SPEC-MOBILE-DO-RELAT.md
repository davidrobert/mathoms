---
id: CHG-2026-04-27-A10-SPEC-MOBILE-DO-RELAT
type: changelog-entry
date: "2026-04-27"
sprint: A10
commits: ["4c76c4b"]
summary: |
  Spec mobile do relatório ✅ docs-only (2026-04-27). - **Spec mobile do relatório ✅ docs-only (2026-04-27):** D3 do `report-a11y-finalize` (deixada em aberto) e [batch2.13](BACKLOG.md) resolvidos com [REPORT_MOBIL
tags:
  - type/changelog-entry
  - sprint/a10
---


# Spec mobile do relatório ✅ docs-only (2026-04-27)

- **Spec mobile do relatório ✅ docs-only (2026-04-27):** D3 do
  `report-a11y-finalize` (deixada em aberto) e [batch2.13](BACKLOG.md)
  resolvidos com [REPORT_MOBILE_SPEC.md](REPORT_MOBILE_SPEC.md) novo +
  delta em [plan/REPORT_PREMIUM/_README.md §17.10](plan/REPORT_PREMIUM/_README.md).
  Decisão de produto convergida: relatório suporta `<767px` em
  leitura/consulta; modo Tático fica acessível com tooltip
  "Otimizado para tablet/desktop"; T3 Kanban vira lista vertical
  agrupada estendendo o fallback v2.7; charts ganham fallback
  agregado (donut top-7 + "outros", slide window 6m default,
  Top-15→Top-5); tabelas com >3 cols viram cards; tipografia escala
  87.5% global. Print/PDF mantém layout desktop em qualquer viewport
  (não-escopo). Auditoria estática catalogou 9 issues (3 estruturais
  P0/P1, 3 estéticos P1/P2, 3 informacionais P0/P1). Implementação
  fica em lane futura `report-mobile-impl` (P2, 2-5d, ~34h em 7
  slices) — esta entrega é spec only. Commit `4c76c4b`.
