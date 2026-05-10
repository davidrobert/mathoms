---
id: CHG-2026-05-10-FEAT-REPORT-PUBLICATION
type: changelog-entry
date: "2026-05-10"
sprint: A11
lane: "[[A11.report-publication]]"
adrs:
  - "[[ADR-187]]"
summary: |
  feat(report): conceito de mês fechado imutável — tabela report_publications,
  helper canônico is_month_closed, endpoints publish/unpublish/list e banner UI
  (ADR-187, lane A11.report-publication).
tags:
  - type/changelog-entry
  - sprint/a11
  - area/report
  - area/methodology
---

# feat(report): mês fechado imutável (ADR-187)

Lane standalone A11.report-publication entrega evento explícito,
imutável e auditável de "relatório publicado / mês fechado". Habilita
futuro learning loop de categorização (lane A12 em rascunho) sem
violar contrato implícito com cliente ("o relatório que recebi não muda
sozinho").

**Entregue:**

- Migration Alembic `d6e7f8a9b0c1` cria `report_publications` com partial
  unique em `(workspace_id, period_yyyymm) WHERE unpublished_at IS NULL`.
- Helper canônico `is_month_closed(workspace_id, period_yyyymm)` é o
  único ponto de leitura da invariante temporal.
- Endpoints `POST/DELETE /reports/{period}/publish`,
  `GET /reports/publications`, `GET /reports/{period}/publication`
  com `response_model` explícito (ADR-109 R18).
- Hash imutável SHA-256 do snapshot E7 normalizado — chaves voláteis
  removidas (`generated_at`, `rendered_at`...) para ser estável entre
  runs idênticos.
- Banner cinza V1 no relatório (`MonthClosedBanner`) avisa
  "Relatório publicado em … Mudanças retroativas bloqueadas para este
  mês."
- Doc `docs/reference/REPORT_PUBLICATION.md` + entrada no glossário de
  domínio em `ARCHITECTURE.md §4.1`.
- Tests: 17 unit (helper/hash/serviço) + 12 integration (API + 403
  cross-tenant). OpenAPI + DB schema reference regenerados.

**Fora de escopo desta lane** (V2 / sprints futuras):

- Auto-publish após N dias.
- UI dedicada de gerenciamento (CTA "Publicar mês").
- Plumbing efetivo do `is_month_closed` em learning loop (lane A12).
