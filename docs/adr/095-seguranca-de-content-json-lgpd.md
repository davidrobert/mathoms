---
id: ADR-095
type: adr
title: "Segurança de `content_json` (LGPD)"
status: Proposto
phase: "execução distribuída em Fases 1-4 do plano"
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 095"]
tags:
  - area/persistence
  - area/pipeline
  - area/security
  - status/proposto
  - type/adr
size_lines: 56
---

# ADR-095 — Segurança de `content_json` (LGPD)

**Status:** Proposto (execução distribuída em Fases 1-4 do plano) • **Data:** 2026-04-19 • **Plano:** §15

**Contexto:** `pipeline_artifacts.content_json` armazena dados financeiros
pessoais — saldos, transações, CPFs (via membros), posições de investimento.
Postgres TDE protege contra roubo de disco físico, **não** contra SQL
injection ou leak de backup lógico. LGPD Art. 18 exige direito ao
esquecimento em até 24h úteis. A v3.3 do plano não endereçava — v3.4 formaliza
em §15.

**Decisão:** Cinco políticas complementares:

**D1 — Criptografia app-level em campos de PII.** CPF e nome completo em
`content_json` são armazenados como `enc:<base64>` via `cryptography.fernet`.
Chave em `MATHOMS_PII_ENCRYPTION_KEY` (secret manager). Read path:
`PipelineArtifactRepository.read_decrypted` faz decrypt on-demand. Deploy
sem a chave em produção **falha**.

**D2 — Não criptografar valores monetários.** Criptografar `amount` quebra
agregações SQL e torna relatórios O(n) em memória. Risco aceitável: valores
sem nome/CPF têm baixa identificabilidade isolada. Proteger via controles
de acesso (D3).

**D3 — Audit log em acesso a `pipeline_artifacts`.** Toda leitura via API
(`GET /reports/{id}/data`, etc.) registra em `access_audit_log`
(tabela nova): `user_id, workspace_id, artifact_id, timestamp, ip`.
Retenção: 1 ano. Consultado em incident response.

**D4 — Política de retenção.** Artefatos ativos: indefinido (user pode
deletar via `/workspace/delete`). Artefatos de runs não-ativas: 2 anos →
soft delete. Direito ao esquecimento: `DELETE /workspace/{id}/artifacts`
remove TODOS os `pipeline_artifacts` + `documents.*_content` em até 24h úteis.

**D5 — Masking em logs.** `DBArtifactStore.read/write` log sem `content_json`
em nível INFO; nível DEBUG só em dev. Nomes de membros viram `member_<hash[:6]>`
em logs estruturados.

**Implementação por fase:**

| Fase | Entregável |
|------|-----------|
| Fase 1 | `PipelineArtifact.content_json` JSONB + `schema_version`; sem crypto ainda ✅ |
| Fase 2 | `PipelineArtifactRepository` encapsula queries; crypto hooks preparados (no-op default) ✅ |
| Fase 3 | Crypto ativa para `extract_members` (piloto com CPF mascarado) — **pendente** |
| Fase 4 | Audit log em 100% dos GETs; endpoint esquecimento — **pendente** |
| Fase 4+ | Estender crypto para demais stages conforme volume — **pendente** |

**Consequências:**
- ✅ LGPD Art. 18/46 atendidos explicitamente.
- ✅ Defense-in-depth: crypto app-level + TDE (prod) + audit log.
- ⚠️ Deploy exige gestão segura de chave (secret manager, KMS em prod).
- ❌ Crypto quebra queries `JSON_EXTRACT` em campos PII — mitigado por
  indexação separada (hash searchable quando necessário).
