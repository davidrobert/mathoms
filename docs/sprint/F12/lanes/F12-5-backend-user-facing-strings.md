---
id: F12.5
type: lane
title: "Backend user-facing strings"
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


# F12.5 — Backend user-facing strings


| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F12.5a | Centralizar 24 mensagens em `backend/app/i18n/messages.py` (dataclass `UserFacingError`). | P0 | 3h | ⏳ |
| F12.5b | `Depends(get_current_locale)` resolve JWT claim → `Accept-Language` → default. Endpoints `documents.py`/`tasks.py`/`admin/users.py` consomem `error_message(code, locale)`. | P0 | 3h | ⏳ |
| F12.5c | ICU plural Python (via `babel.support.Translations` ou helper) para mensagens com contagem. | P1 | 2h | ⏳ |
