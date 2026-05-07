---
id: F7.b
type: lane
title: "Security Hardening + LGPD (semana 2-3)"
sprint: F7
status: shipped
priority: P0
ship_pr: 60
adrs: ["[[ADR-110]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f7
  - status/shipped
  - priority/p0
---


# 7B — Security Hardening + LGPD (semana 2-3)


#### Decisões arquiteturais LGPD (D1–D5)

Estas decisões moldam as tasks 7B.* abaixo. Absorvidas em 2026-04-21 do
plano-mestre A6 §15 (antes em `_scratch/`, agora canônico aqui).
**Motivação:** `pipeline_artifacts.content_json` armazena dados
financeiros pessoais (saldos, transações) + membros (CPF, nome, data
nascimento, ocupação). Postgres TDE protege disco físico, não leaks
lógicos — a defesa é app-level + audit + retenção.

**D1 — Criptografia app-level em campos de PII**
- Campos com PII (CPF, nome completo) cifrados via `cryptography.fernet`; chave em `FIN_PII_ENCRYPTION_KEY` (secret manager, obrigatória em prod — deploy falha se ausente).
- Campos em `content_json` armazenados como string `enc:<base64_ciphertext>`; `PipelineArtifact.content_json` JSONB preserva chave original, valor é o ciphertext.
- Leitura: decrypt on-demand em `PipelineArtifactRepository.read_decrypted()` — nunca retorna ciphertext ao caller.
- **Tasks relacionadas:** 7B.1 expande a utility `encrypt_field()` / `decrypt_field()`.

**D2 — Não criptografar valores monetários**
- Cifrar `amount` quebra agregações SQL e força O(n) em memória para relatórios.
- Risco aceitável: valores sem nome/CPF têm baixa identificabilidade isolada.
- Proteção via controles de acesso (D3) + retenção (D4), não criptografia.

**D3 — Audit log em acesso de leitura a `pipeline_artifacts`**
- Toda leitura via API (`GET /reports/{id}/data`, `GET /pipeline/artifacts/*`) registra em `access_audit_log`: `user_id`, `workspace_id`, `artifact_id`, `timestamp`, `ip`.
- Retenção: 1 ano. Consultado em incident response.
- **Tasks relacionadas:** 7B.5 audit log — estender middleware para incluir READ ops em artefatos (hoje cobre só write).

**D4 — Política de retenção + direito ao esquecimento (LGPD Art. 18)**
- Artefatos ativos: mantidos indefinidamente; usuário pode deletar via `/workspace/delete`.
- Artefatos de runs não-ativas (histórico): 2 anos → arquivados (soft delete).
- Direito ao esquecimento: endpoint `DELETE /workspace/{id}/artifacts` remove **todos** `pipeline_artifacts` + `documents.*_content` do workspace em ≤24h úteis.
- **Tasks relacionadas:** 7B.7 (LGPD Exclusão), 7B.9 (Storage cleanup), 7B.17 (Soft-delete 30d), 7B.18 (DSAR SLA 15d).

**D5 — Masking em logs estruturados**
- ADR-110 já cobre redaction no `MathomsJsonFormatter` para campos sensíveis (password, secret, token, api_key, cpf, cnpj, valor, saldo). **Estender:**
- Nomes de membros viram `member_<hash[:6]>` em logs estruturados (hash determinístico com salt por workspace — permite correlação de eventos sem expor nome real).
- Níveis: `INFO` nunca inclui `content_json` de `DBArtifactStore.read/write`; `DEBUG` pode incluir (apenas dev).
- **Tasks relacionadas:** 7B.5 (audit log também respeita masking).

#### Implementação por fase

| Marco | Entregável |
|-------|-----------|
| Pré-F7B | `PipelineArtifact.content_json` JSONB + `schema_version`; sem crypto ainda (entregue em A6a) |
| F7B.1 | `encrypt_field()` / `decrypt_field()` utilities; `PipelineArtifactRepository.read_decrypted()` hook (no-op se chave ausente em dev) |
| F7B.1+ | Crypto ativa em `extract_members` (piloto com CPF mascarado) |
| F7B.5 | Audit log cobrindo todas leituras via API (D3); retenção 1 ano configurada |
| F7B.7 | `DELETE /workspace/{id}/artifacts` (D4, direito ao esquecimento) + soft-delete 30d + DSAR 15d |
| F7B.9 | Retenção de 2 anos em runs não-ativas (D4) via Celery periodic task |

#### Critérios de aceite globais (F7B → produção)

- [ ] `FIN_PII_ENCRYPTION_KEY` obrigatória em produção (deploy falha se ausente)
- [ ] `extract_members` em produção armazena CPF criptografado em `content_json`
- [ ] `access_audit_log` populado em 100% dos GETs de `/reports/{id}/data`
- [ ] `DELETE /workspace/{id}/artifacts` remove todos artefatos e confirma via count
- [ ] Logs INFO não contêm CPF, nome completo ou valores monetários totais (validar via `dev/scan_logs_for_pii.py`)

---

| #     | Tarefa                                                                                               | Prio | Est. | Status |
| ----- | ---------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 7B.1  | Fernet expandido (CPFs + dados financeiros sensíveis + utility `encrypt_field()`/`decrypt_field()`) — implementa **D1** | P0   | 6h   | ☐      |
| 7B.2  | Rate limiting (slowapi: auth 5/min, upload 10/min, pipeline 2/min, geral 100/min)                    | P0   | 3h   | ☐      |
| 7B.3  | Security headers (CORS restritivo, HSTS, CSP, X-Frame-Options, X-Content-Type-Options)               | P0   | 3h   | ☐      |
| 7B.4  | Session security (JWT 15min + refresh 7d httpOnly, rotation, revogação on password change, frontend interceptor) | P0 | 16h | ☐ |
| 7B.5  | Audit log (model `AuditEntry`, middleware para write ops, todas ações sensíveis)                     | P0   | 6h   | ☐      |
| 7B.6  | LGPD — Termos + Privacy (páginas `/terms` `/privacy`, aceite obrigatório, `accepted_at`)             | P0   | 4h   | ☐      |
| 7B.7  | LGPD — Exclusão (`DELETE /api/account`, cascade completo, confirmação dupla + audit)                 | P0   | 8h   | ✅ Advance delivery [#60](https://github.com/davidrobert/mathoms/pull/60) — `POST /me/delete-request` (soft-delete 30d, bumps `token_version`, `lgpd.deletion_*` audit) + `DELETE /me/delete-request` (cancel); cron `fin.lgpd.process_user_deletions` (24h, grace 30d). Pendente: UI stepper (7B.10) |
| 7B.8  | LGPD — Portabilidade (`GET /api/account/export`, ZIP com dados pessoais, download link temporário)   | P1   | 6h   | ✅ Advance delivery [#60](https://github.com/davidrobert/mathoms/pull/60) — `POST /me/data-export` → worker Celery NDJSON tar.gz → `GET /me/data-export/{id}/download` (token 1-shot TTL 7d); cron `fin.lgpd.expire_data_exports` (6h). |
| 7B.9  | Storage cleanup (retention 90 dias, Celery periodic task, soft-delete)                               | P1   | 4h   | ☐      |
| 7B.10 | UX de produção (rate limit toast, LGPD delete stepper, export notification, maintenance page)        | P1   | 4h   | ☐      |
| 7B.11 | **Email verification** no registro (token 24h, link em email, bloqueio de login até verificar, reenvio) — **sem isso GA é impossível** | P0 | 6h | ☐ |
| 7B.12 | **Password reset** (fluxo completo: endpoint request, token Fernet 1h, email com link, página `/reset-password/{token}`, invalidação de refresh tokens) | P0 | 8h | ☐ |
| 7B.13 | **Brute-force lockout**: N falhas consecutivas (5) → cooldown escalonado (1min → 5min → 15min → 1h); contador em Redis com TTL; unlock automático e manual (admin) | P0 | 3h | ☐ |
| 7B.14 | **MFA decision stub**: ADR documentando se TOTP entra F7 ou F8; se F8, stub de campo `mfa_enabled` em `User` para migration path futura sem breaking change | P1 | 1h | ☐ |
| 7B.15 | **Prompt injection defense** para E2-llm/E1.5: sanitização de texto extraído (strip invisível/zero-width/ANSI), allowlist rígida de campos no output via Instructor, truncamento de input com warning, teste com PDF adversarial fixture | P0 | 6h | ☐ |
| 7B.16 | **Terms versioning + re-aceitação**: `TermsVersion` model (`version`, `content_md`, `effective_at`); `UserTermsAcceptance` (`user_id`, `version_id`, `accepted_at`); prompt de re-aceitação quando versão ativa muda; bloqueio de API até aceitar | P1 | 4h | ☐ |
| 7B.17 | **Soft-delete period** em LGPD delete (7B.7): `deleted_at` timestamp, 30 dias de reversibilidade via endpoint, Celery task purga definitivamente após 30d, email de confirmação | P1 | 4h | ☐ |
| 7B.18 | **DSAR SLA workflow** (LGPD art. 18, 15 dias): endpoint `POST /api/account/dsar`, cria ticket, notifica admin, template de resposta, audit log; exportação automatizada reusa 7B.8 | P1 | 5h | ☐ |
