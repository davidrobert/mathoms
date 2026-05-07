---
id: F12.2
type: lane
title: "Refactor de `format.ts` e `<MonetaryValue/>`"
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


# F12.2 — Refactor de `format.ts` e `<MonetaryValue/>`


| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F12.2a | `format.ts` aceita `locale` em todas as funções públicas; remove constantes top-level; substitui por funções puras. | P0 | 4h | ⏳ |
| F12.2b | `<MonetaryValue/>` consome `useLocale()`. Helper `useFormat()` injeta locale. | P0 | 2h | ⏳ |
| F12.2c | Mapas `STAGE_DISPLAY_NAMES`, `DOC_STATUS_MAP`, `BANK_NAMES`, etc. → `messages/<locale>.json`. Snapshots Vitest nos 10 locales. | P0 | 2h | ⏳ |
