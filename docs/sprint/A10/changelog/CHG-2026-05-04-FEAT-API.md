---
id: CHG-2026-05-04-FEAT-API
type: changelog-entry
date: "2026-05-04"
sprint: A10
adrs: ["[[ADR-129]]"]
summary: |
  feat(api,security): LGPD self-service + tenancy isolation gate (Bloco 0.6 P2/P3 · 2026-05-04). - **feat(api,security): LGPD self-service + tenancy isolation gate (Bloco 0.6 P2/P3 · 2026-05-04):** Endpoints `POST /api/v1/me/data-export`, `GET /me/data-expo
tags:
  - type/changelog-entry
  - sprint/a10
---


# feat(api,security): LGPD self-service + tenancy isolation gate (Bloco 0.6 P2/P3 · 2026-05-04)

- **feat(api,security): LGPD self-service + tenancy isolation gate (Bloco 0.6 P2/P3 · 2026-05-04):**
  Endpoints `POST /api/v1/me/data-export`, `GET /me/data-export/{id}`,
  `GET /me/data-export/{id}/download` (one-shot, TTL 7d), `POST
  /me/delete-request` (soft-delete + grace 30d, bumps `token_version`),
  `DELETE /me/delete-request` (cancel). Worker Celery
  `fin.lgpd.process_data_export` empacota NDJSON tar.gz com manifest
  (`backend/app/services/lgpd_export_service.py`) — exclui
  `users.hashed_password` e `password_vaults.encrypted_password`. Cron
  beat `fin.lgpd.expire_data_exports` (6h) e
  `fin.lgpd.process_user_deletions` (24h, grace 30d). 8 ações novas em
  `AuditAction` (`lgpd.export_*`, `lgpd.deletion_*`); hard-delete usa
  email-hash truncado para registro auditável anonimizado (LGPD §V).
  Migration `c3d4e5f6a7b8_lgpd_self_service` adiciona
  `data_export_requests` + `users.deletion_requested_at`. Cobertura: 9
  testes em `backend/tests/test_lgpd_self_service.py` (happy path,
  cooldown, audit trail, TTL/expire, soft-then-hard delete, cancel,
  token inválido, cross-tenant 404). LGPD Art. 18, V e VI atendidos
  por self-service — antes só via console interno
  (`MATHOMS_INTERNAL_OPS_UI_ENABLED`), bloqueador P0 para abrir signup
  público. Doc nova em [SECURITY.md §Direitos do titular
  LGPD](../SECURITY.md). **Tenancy gate estrutural** em
  [backend/tests/integration/test_tenancy_isolation.py](../../../../backend/tests/integration/test_tenancy_isolation.py):
  3 testes complementam o suite per-domain — fuzz de todas as rotas
  `/api/v1/workspaces/{workspace_id}/...` GET (User A nunca obtém 200
  no ws de B), AST scan que exige `Depends(get_current_workspace)` em
  toda função com `workspace_id` (whitelist 6 sunset endpoints
  ADR-129/154), e fuzz path-id em `/documents/{id}/extract-json`. Doc
  em [docs/reference/TESTING.md §Tenancy isolation](../../../reference/TESTING.md). Snapshot
  OpenAPI + DB schema reference regenerados.
