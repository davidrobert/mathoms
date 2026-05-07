---
id: F11.4
type: lane
title: "Transparência na UI: origem da informação"
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


# F11.4 — Transparência na UI: origem da informação


| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.4a | **Modelo de dados / API:** expor por bloco ou seção (ou agregado no JSON do relatório) referência a: `document_id`(s), período, run_id opcional — sem vazar dados entre workspaces. | P1 | 10h | ✅ Agregado: `source_document_count` / `source_document_ids` na API + `_report_lineage` em GET `/data`; linhagem por bloco no JSON fica como evolução futura |
| F11.4b | **UI:** componente discreto “Fonte” / “Origem” (tooltip ou linha secundária): ex. “Extrato Itaú · jan/2026 · run `abc…`”. | P1 | 8h | ✅ Sprint B: `ReportSourceStrip` abaixo do header do relatório (links Documentos + Pipeline; período snapshot + gerado em) |
| F11.4c | **Fallback:** quando dado for agregado de várias fontes, texto explícito “Consolidado de N documentos”. | P1 | 3h | ✅ Sprint B: copy “consolidados a partir dos documentos…” na faixa de origem |
