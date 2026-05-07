---
id: ADR-170
type: adr
title: "Refresh tokens com httpOnly cookie e family-based revocation"
status: Proposto
date: "2026-05-06"
relates_to: ["[[ADR-003]]", "[[ADR-057]]", "[[ADR-109]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 170"]
tags:
  - type/adr
  - status/proposto
size_lines: 34
---

# ADR-170 — Refresh tokens com httpOnly cookie e family-based revocation

**Status:** Proposto • **Data:** 2026-05-06 • **Relaciona** [ADR-003](#adr-003--jwt-custom-para-auth), [ADR-057](#adr-057--jwt-15min--refresh-7d), [ADR-109](#adr-109--auth-portability-jwt-hs256--fernet-documentados-como-contratos-portáveis-a6f5a). **Origem:** SR-002 em [docs/plan/PLATFORM_REVIEW/_README.md](plan/PLATFORM_REVIEW/_README.md) (Wave 1 backfill, implementação em W3-T03).

**Contexto:** ADR-057 estabeleceu access 15 min + refresh 7 dias, mas o backend hoje emite **só** access tokens com TTL longo via `core/security.py`. Não há refresh token em circulação, não há revocation, e tokens roubados continuam válidos até a expiração natural. Em fluxos `Bearer` o front salva o access em `localStorage` (XSS = takeover). ADR-109 documenta JWT HS256 como contrato portável; uma migração para refresh-flow é breaking — exige nova ADR antes do PR.

**Alternativas avaliadas:**

1. **Status quo (access longo, sem refresh)** — simples mas insegura: roubo de localStorage = posse permanente até TTL. Rejeitada.
2. **Refresh em localStorage** — não fecha o vetor XSS; mantém `access_token` exposto. Rejeitada.
3. **Refresh em httpOnly cookie + access em memória + family-revocation (escolhida)** — refresh inacessível a JS; access rotaciona a cada 15 min via fetch silencioso; reuse-detection invalida toda a família, bloqueando uso pós-roubo.

**Decisão:** Adotar (3) com os contratos:

- **Access JWT (HS256):** TTL 15 min, payload mínimo (`sub`, `workspace_id`, `iat`, `exp`, `jti`). Enviado em `Authorization: Bearer <token>`.
- **Refresh token:** opaque random 256-bit + hash em `refresh_token_families` (Postgres). TTL 7 dias deslizante, `rotation_count` incrementa a cada refresh. Cookie `Secure`, `HttpOnly`, `SameSite=Lax`, path `/auth/refresh`.
- **Family revocation:** cada login cria `family_id` novo. Reuse de refresh já consumido (rotation_count drift) → família inteira revogada (`revoked_at`). Logout faz revoke da família atual.
- **Frontend interceptor:** 401 dispara `/auth/refresh` transparente; falha aí → redireciona ao login.
- **Backward-compat por 1 release:** flag `MATHOMS_AUTH_REFRESH_FLOW` (default off em prod até PR-frontend mergear). Quando off, mantém ADR-057 access longo.

**Consequências:**

- ✅ Roubo de `access_token` (XSS efêmero) é mitigado por TTL curto.
- ✅ Reuse-detection bloqueia replay pós-extração de refresh.
- ✅ HttpOnly cookie protege contra XSS extraction.
- ⚠️ Cookie + Bearer é setup híbrido — middleware backend precisa lidar com ambos durante migração.
- ⚠️ Migração breaking exige PR coordenado backend+frontend (W3-T03 endereça).
- ❌ Não substitui WAF + CSP — defesa em profundidade requer ambas.

**Implementação:** lane W3-T03 (Wave 3). Esta ADR vira `Decidido (W3-T03)` no merge da implementação. Supersede parcialmente ADR-057 (refresh era roadmap).

**Referências:** [plan/PLATFORM_REVIEW/_README.md §W3-T03](plan/PLATFORM_REVIEW/_README.md), finding SR-002.
