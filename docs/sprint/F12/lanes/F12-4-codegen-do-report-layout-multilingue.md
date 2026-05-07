---
id: F12.4
type: lane
title: "Codegen do report layout multilíngue"
sprint: F12
status: open
priority: P0
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f12
  - status/open
  - priority/p0
---


# F12.4 — Codegen do report layout multilíngue


| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F12.4a | Schema do `config/report_layout.yaml` migra labels para `i18n_key`. | P0 | 4h | ⏳ |
| F12.4b | `dev/codegen_report_layout.py` emite tipos sem strings; valida que cada `i18n_key` existe nos 10 locales. | P0 | 4h | ⏳ |
| F12.4c | Teste `tests/test_i18n_parity.py` — paridade de chaves entre 10 locales; falha CI se faltar entrada. | P0 | 4h | ⏳ |
