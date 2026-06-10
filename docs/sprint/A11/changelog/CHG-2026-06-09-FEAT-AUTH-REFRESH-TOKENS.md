---
id: CHG-2026-06-09-FEAT-AUTH-REFRESH-TOKENS
type: changelog-entry
date: "2026-06-09"
sprint: A11
adrs: ["[[ADR-170]]", "[[ADR-057]]"]
prs: [584]
summary: |
  W3-T03 (SR-002): refresh tokens httpOnly com family revocation — rotação com
  grace window 60s + teto 30d, CSRF via header custom, interceptor frontend;
  flag default off. ADR-170 Decidido; supersede ADR-057.
tags:
  - type/changelog-entry
  - sprint/a11
---

# W3-T03 — Refresh tokens httpOnly + family revocation (ADR-170)

Fecha o finding **SR-002** (P0 security): a ADR-057 (F7) decidira access 15min +
refresh 7d, mas só o access de 24h existia. Entrega: tabela
`refresh_token_families` (hash sha256, secret independente de SECRET_KEY/Fernet),
`POST /auth/refresh` (rotação sliding 7d com teto absoluto 30d, grace window 60s
anti-falso-positivo de 2 tabs, reuse detection revoga a família, CSRF via header
`X-Refresh-Request`, rate limit Redis por família+IP), `POST /auth/logout`
idempotente, e interceptor 401→refresh transparente no `apiFetch` com promise
compartilhada. Payload JWT mantém `{sub, exp, tv}` (ADR-109 intacto); `tv` bump
agora também mata a família (forced logout F9 completo). Flag
`MATHOMS_AUTH_REFRESH_FLOW` default off — ADR-057 legado intacto até ativação;
remoção da flag 1 release após estabilizar em prod.
