---
id: F7.d
type: lane
title: "Quality Gate + Launch Readiness (semana 4-6 + 2 sem dogfood)"
sprint: F7
status: shipped
priority: P0
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f7
  - status/shipped
  - priority/p0
---


# 7D — Quality Gate + Launch Readiness (semana 4-6 + 2 sem dogfood)


| #     | Tarefa                                                                                           | Prio | Est. | Status |
| ----- | ------------------------------------------------------------------------------------------------ | ---- | ---- | ------ |
| 7D.1  | Gap-fill unit tests (E0, E2/banks, E3, E4, E7 edge cases)                                       | P0   | 10h  | ✅ Leva inicial: `tests/test_e0_route_edges.py`, `test_e3_dedup` (período inválido), `test_e4_categorize` (despesa vazia), `tests/test_e7_edges.py`; E2/banks já cobertos por `test_e2_synthetic_pdf_parsers` + goldens |
| 7D.2  | Gap-fill unit tests (E5, E5N, E6 — scripts maiores)                                             | P1   | 12h  | ✅ Leva inicial: `tests/test_e5_e6_e5n_edges.py` (helpers puros); goldens E5/E5N/E6 existentes continuam como regressão pesada |
| 7D.3  | Gap-fill API endpoints + services (error paths, DB/Redis down, auth edge, concurrency)           | P0   | 8h   | ☐      |
| 7D.4  | CI integra frontend tests (Vitest + Playwright da F6.5) no pipeline de deploy                    | P0   | 1h   | ☐      |
| 7D.5  | Frontend E2E com PostgreSQL prod DB (ajustar fixtures)                                           | P1   | 2h   | ☐      |
| 7D.6  | Testes de UX de produção (rate limit toast, LGPD delete, export notification, maintenance)      | P1   | 3h   | ☐      |
| 7D.7  | Performance baseline (`time` pipeline E2E, p50/p95 API endpoints, `docs/reference/PERFORMANCE_BASELINE.md`)| P1   | 3h   | ☐      |
| 7D.8  | Coverage integration (CI gate, Codecov, badge README, target ≥85% line / ≥75% branch)           | P0   | 3h   | ☐      |
| 7D.9  | Telemetria básica (tabela `UsageMetric`, privacy-first, dashboard query simples)                 | P1   | 4h   | ☐      |
| 7D.10 | Pre-launch checklist (smoke test prod, backup restore, rollback test, SSL Labs grade A)          | P0   | 3h   | ☐      |
| 7D.11 | **Dogfood period** (2+ semanas uso real, 5+ pipeline runs, zero critical bugs)                   | P0   | —    | ☐      |
