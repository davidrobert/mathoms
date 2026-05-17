---
id: F12.3
type: lane
title: "Persistência da escolha (DB + JWT)"
sprint: F12
plan: PLAN-i18n
status: blocked
priority: P0
adrs: ["[[ADR-109]]", "[[ADR-130]]"]
depends_on: []
parallel_with: ["[[F12.2]]", "[[F12.4]]", "[[F12.5]]"]
tags:
  - type/lane
  - sprint/f12
  - status/blocked
  - priority/p0
---


# F12.3 — Persistência da escolha (DB + JWT)


> 🚧 **Blocked-by-gate.** Aguarda gatilho de §10 do
> [plan/I18N/_README.md](../../../plan/I18N/_README.md). Escopo: 3 locales
> (pt-BR + en + es) — ADR-130 revisada 2026-05-15.

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F12.3a | **ADR-A6f.5b** — JWT claim `locale` (extensão de auth payload, breaking segundo ADR-109). Atualiza golden `test_auth_portability.py`. | P0 | 2h | ⏳ |
| F12.3b | Migration Alembic: `users.locale VARCHAR(10) NOT NULL DEFAULT 'pt-BR'` + CHECK constraint nos 3 valores (`'pt-BR'`, `'en'`, `'es'`). Pydantic `Locale` enum em `backend/app/domain/locale.py`. | P0 | 3h | ⏳ |
| F12.3c | Endpoint `PATCH /users/me/preferences` (response_model explícito ADR-109; rodar `make update-openapi-snapshot`). | P0 | 3h | ⏳ |
| F12.3d | Frontend `/settings/preferences` com seletor 3 opções (nome nativo); grava cookie + chama API; teste integração login en/es preserva idioma. | P0 | 2h | ⏳ |
