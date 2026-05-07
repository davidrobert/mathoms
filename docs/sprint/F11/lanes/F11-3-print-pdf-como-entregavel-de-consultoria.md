---
id: F11.3
type: lane
title: "Print / PDF como entregável de consultoria"
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


# F11.3 — Print / PDF como entregável de consultoria


| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.3a | **Print CSS:** revisão de quebras de página, cabeçalhos repetidos, margens A4, ocultar chrome da app na impressão; numerar páginas se o motor permitir. | P1 | 6h | ✅ Margens A4 numa única `@page`; `orphans`/`widows`; removido `@bottom-center` (suporte irregular); `?print=1` → `html[data-print-route]` |
| F11.3b | **Export PDF server-side (Playwright):** validar que tipografia e cores ficam “apresentáveis” para terceiros; capa com período e sobrenome da família consistente. | P1 | 4h | ✅ `render_pdf` espera `[data-report-ready]` antes do `page.pdf()` (hero visível); checklist §5.1 |
| F11.3c | **Checklist de QA** em [SMOKE_TEST.md](SMOKE_TEST.md) ou seção dedicada: “entrega impressa/PDF” (mínimo 5 itens). | P2 | 2h | ✅ §5.1 em SMOKE_TEST + itens Cmd+K / `?` em Auth |
