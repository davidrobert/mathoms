---
id: F12.5
type: lane
title: "Backend user-facing strings"
sprint: F12
plan: PLAN-i18n
status: blocked
priority: P0
adrs: ["[[ADR-130]]"]
depends_on: []
parallel_with: ["[[F12.2]]", "[[F12.3]]", "[[F12.4]]"]
tags:
  - type/lane
  - sprint/f12
  - status/blocked
  - priority/p0
---


# F12.5 — Backend user-facing strings


> 🚧 **Blocked-by-gate.** Aguarda gatilho de §10 do
> [plan/I18N/_README.md](../../../plan/I18N/_README.md). Escopo: 3 locales
> (pt-BR + en + es).

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F12.5a | Centralizar 24 mensagens em `backend/app/i18n/messages.py` (dataclass `UserFacingError`). | P0 | 3h | ⏳ |
| F12.5b | `Depends(get_current_locale)` resolve JWT claim → `Accept-Language` → default. Endpoints `documents.py`/`tasks.py`/`admin/users.py` consomem `error_message(code, locale)`. | P0 | 3h | ⏳ |
| F12.5c | ICU plural Python (via `babel.support.Translations` ou helper) para mensagens com contagem (plurais 2-form em pt-BR/en/es). | P1 | 2h | ⏳ |
