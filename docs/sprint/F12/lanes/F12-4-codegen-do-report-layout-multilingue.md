---
id: F12.4
type: lane
title: "Codegen do report layout multilíngue"
sprint: F12
status: blocked
priority: P0
adrs: ["[[ADR-130]]"]
depends_on: []
parallel_with: ["[[F12.2]]", "[[F12.3]]", "[[F12.5]]"]
tags:
  - type/lane
  - sprint/f12
  - status/blocked
  - priority/p0
---


# F12.4 — Codegen do report layout multilíngue


> 🚧 **Blocked-by-gate.** Aguarda gatilho de §10 do
> [plan/I18N/_README.md](../../../plan/I18N/_README.md). Escopo: 3 locales
> (pt-BR + en + es).

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F12.4a | Schema do `config/report_layout.yaml` migra labels para `i18n_key`. | P0 | 4h | ⏳ |
| F12.4b | `dev/codegen_report_layout.py` emite tipos sem strings; valida que cada `i18n_key` existe nos 3 locales. | P0 | 3h | ⏳ |
| F12.4c | Teste `tests/test_i18n_parity.py` — paridade de chaves entre 3 locales; falha CI se faltar entrada. | P0 | 3h | ⏳ |
