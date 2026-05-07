---
id: F11.6
type: lane
title: "Metadados de premissas (metas e relatório)"
sprint: F11
status: shipped
priority: P1
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f11
  - status/shipped
  - priority/p1
---


# F11.6 — Metadados de premissas (metas e relatório)


| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.6a | **Metas (Goals):** versão de premissas por tipo (IF, aporte, dólar, alocação): taxa, inflação, horizonte, data de vigência; exibir no wizard e na visualização. | P1 | 10h | ✅ `GoalPremissasCard` + `goalPremissas.ts` em todos os wizards e formulários `/plano/*`; API expõe `meta_version` em `GET`/`PUT` goals; teste `tests/lib/goalPremissas.test.ts` |
| F11.6b | **Snapshot de relatório:** quando números dependerem de premissas, gravar referência (versão goal ou blob JSON mínimo) para comparação mês a mês. | P1 | 8h | ✅ Coluna `reports.premissas_snapshot_json` + `build_premissas_snapshot_sync` (SHA-256 de `config/goals.json` + metas `effective_to IS NULL`); pipeline preenche em `_create_report_from_output`; API `ReportResponse.premissas_snapshot` + merge em `goals.premissas_snapshot` no GET `/data`; testes `backend/tests/test_premissas_snapshot.py`, `test_reports` |
| F11.6c | **Relatório UI:** bloco opcional “Premissas deste relatório” (colapsável). | P2 | 4h | ✅ `ReportPremissasBlock` (snapshot opcional `goals.premissas_snapshot` se existir) |
