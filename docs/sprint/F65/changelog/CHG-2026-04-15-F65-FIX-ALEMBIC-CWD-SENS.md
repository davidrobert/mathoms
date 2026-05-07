---
id: CHG-2026-04-15-F65-FIX-ALEMBIC-CWD-SENS
type: changelog-entry
date: "2026-04-15"
sprint: F65
summary: "Fix alembic cwd-sensitivity. - **Fix alembic cwd-sensitivity:** `%(here)s/../mathoms.db` absoluto + guard em `env.py` rejeita SQLite relativo + `DATABASE_URL` default absoluto via `_PROJECT"
tags:
  - type/changelog-entry
  - sprint/f65
---


# Fix alembic cwd-sensitivity

- **Fix alembic cwd-sensitivity:** `%(here)s/../mathoms.db` absoluto + guard em `env.py` rejeita SQLite relativo + `DATABASE_URL` default absoluto via `_PROJECT_ROOT`
