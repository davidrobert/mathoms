---
id: F12.3
type: lane
title: "Persistência da escolha (DB + JWT)"
sprint: F12
status: open
priority: P0
adrs: ["[[ADR-109]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f12
  - status/open
  - priority/p0
---


# F12.3 — Persistência da escolha (DB + JWT)


| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F12.3a | **ADR-A6f.5b** — JWT claim `locale` (extensão de auth payload, breaking segundo ADR-109). Atualiza golden `test_auth_portability.py`. | P0 | 2h | ⏳ |
| F12.3b | Migration Alembic: `users.locale VARCHAR(10) NOT NULL DEFAULT 'pt-BR'` + CHECK constraint nos 10 valores. Pydantic `Locale` enum em `backend/app/domain/locale.py`. | P0 | 3h | ⏳ |
| F12.3c | Endpoint `PATCH /users/me/preferences` (response_model explícito ADR-109; rodar `make update-openapi-snapshot`). | P0 | 3h | ⏳ |
| F12.3d | Frontend `/settings/preferences` com seletor 10 opções (nome nativo); grava cookie + chama API; teste integração login pt-PT/ja preserva idioma. | P0 | 2h | ⏳ |
