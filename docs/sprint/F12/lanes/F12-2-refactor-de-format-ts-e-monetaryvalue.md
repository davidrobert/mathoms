---
id: F12.2
type: lane
title: "Refactor de `format.ts` e `<MonetaryValue/>`"
sprint: F12
plan: PLAN-i18n
status: blocked
priority: P0
adrs: ["[[ADR-130]]"]
depends_on: []
parallel_with: ["[[F12.3]]", "[[F12.4]]", "[[F12.5]]"]
tags:
  - type/lane
  - sprint/f12
  - status/blocked
  - priority/p0
---


# F12.2 — Refactor de `format.ts` e `<MonetaryValue/>`


> 🚧 **Blocked-by-gate.** Aguarda gatilho de §10 do
> [plan/I18N/_README.md](../../../plan/I18N/_README.md): ≥30 leads EN/ES
> qualificados OU ≥3 churns por idioma OU decisão pricing internacional.
> ICP confirmado 2026-05-15: brasileiros nômades digitais — escopo
> reduzido para 3 locales (pt-BR + en + es). ADR-130 revisada.

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F12.2a | `format.ts` aceita `locale` em todas as funções públicas; remove constantes top-level; substitui por funções puras. | P0 | 4h | ⏳ |
| F12.2b | `<MonetaryValue/>` consome `useLocale()`. Helper `useFormat()` injeta locale. | P0 | 2h | ⏳ |
| F12.2c | Mapas `STAGE_DISPLAY_NAMES`, `DOC_STATUS_MAP`, `BANK_NAMES`, etc. → `messages/<locale>.json`. Snapshots Vitest nos 3 locales. | P0 | 2h | ⏳ |
