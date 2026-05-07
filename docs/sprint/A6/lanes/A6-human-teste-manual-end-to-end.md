---
id: A6-human
type: lane
title: "Teste manual end-to-end (David)"
sprint: A6
status: shipped
priority: P0
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a6
  - status/shipped
  - priority/p0
---


# A6-human — Teste manual end-to-end (David)


| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6-human.1 | Auth + multi-tenancy (5 checks) | P0 | 30min | ✅ |
| A6-human.2 | Documentos + classificação (10 checks) | P0 | 1h | ✅ |
| A6-human.3 | Pipeline full + incremental + erro + histórico (7 checks) | P0 | 1h | ✅ |
| A6-human.4 | Cada stage E0-E7 (6 checks) | P0 | 1h | ✅ |
| A6-human.5 | Relatório completo (10 checks — seções, KPIs, linhagem, print, PDF, narrativas) | P0 | 1h | ✅ |
| A6-human.6 | Goals/Plano (7 checks — dashboard + 4 wizards + premissas) | P0 | 1h | ✅ |
| A6-human.7 | Configuração + admin + WS (8 checks) | P0 | 1h | ✅ |
| A6-human.8 | Cutover DB específico (5 checks — `pipeline_artifacts` + paridade disk/DB) | P0 | 1h | ✅ |
| A6-human.9 | Edge cases (5 checks — workspace sem baseline, fatura sem período, transf interna, etc.) | P0 | 1h | ✅ |
| A6-human.10 | Relatório final: checklist + lista de bugs + **decisão explícita** aprovar A6c ou bloquear | P0 | 30min | ✅ |

**Gate:** ✅ **APROVADO 2026-04-24** — smoke test humano completo, A6c destravado.
