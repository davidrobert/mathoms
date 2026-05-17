---
id: CHG-2026-04-25-A10-LANE-REPORT-A11Y-FIN
type: changelog-entry
date: "2026-04-25"
sprint: A10
summary: |
  Lane `report-a11y-finalize` item 5 (2026-04-25). - **Lane `report-a11y-finalize` item 5 (2026-04-25):** checklist WCAG 2.1 AA operacional em [`docs/plan/REPORT_PREMIUM/A11Y_CHECKLIST.md`](../../../plan/REPORT_PREMIUM/A11Y_CHECKLIST.md).
tags:
  - type/changelog-entry
  - sprint/a10
---


# Lane `report-a11y-finalize` item 5 (2026-04-25)

- **Lane `report-a11y-finalize` item 5 (2026-04-25):** checklist WCAG
  2.1 AA operacional em [`docs/plan/REPORT_PREMIUM/A11Y_CHECKLIST.md`](../../../plan/REPORT_PREMIUM/A11Y_CHECKLIST.md).
  Tabela seção × critério (1.4.3 contraste, 2.1.1 teclado, 2.4.3 ordem
  de foco, 2.4.7 foco visível, 4.1.2 nome/papel/valor) com cobertura
  automática (✅ via gate) vs checklist humano (👁 obrigatório no PR)
  para shell global + S1-S10 + APP_A-E + T1-T6 + U1-U4. Pontos de
  atenção destacados: T3 Kanban (drag&drop por teclado), `<MonetaryValue/>`
  em estados de hover light/dark, qualidade semântica de `aria-label`.
  **Absorve [batch2.14](../../../BACKLOG.md#docs-reviewbatch2--reescrita-de-documentos-decisões-de-escopo-pendentes)**
  do docs-review/batch2 (✅ fechado). Resta apenas item 3 (snapshots
  por seção × tema) na lane — sugerido abrir como lane separada quando
  decisão D3 (mobile spec in/out) estiver fechada.
