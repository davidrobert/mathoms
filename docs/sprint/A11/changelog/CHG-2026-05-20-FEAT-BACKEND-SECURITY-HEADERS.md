---
id: CHG-2026-05-20-FEAT-BACKEND-SECURITY-HEADERS
type: changelog-entry
date: "2026-05-20"
sprint: A11
lane: "[[A11.w2]]"
adrs:
  - "[[ADR-232]]"
tags:
  - type/changelog-entry
  - sprint/a11
  - area/backend
  - area/security
summary: |
  feat(backend): security headers + CORS strict no FastAPI (ADR-232). Middleware
  emite HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff,
  Referrer-Policy strict-origin-when-cross-origin, Permissions-Policy e CSP
  report-only com report-uri funcional. CORS migrado para allow_methods +
  allow_headers explícitos (sem wildcards). Endpoint POST /v1/csp-report aceita
  payload cap 8KB e loga violations estruturadas. Fecha SR-001 + SR-013.
---

# feat(backend): security headers + CORS strict (ADR-232)

W2-T02 da Sprint A11 ([PR #361](https://github.com/davidrobert/mathoms/pull/361))
consolida findings SR-001 + SR-013 da revisão multi-agente 2026-05-06: o
backend FastAPI não emitia headers de segurança HTTP e o CORS dependia de
wildcards implícitos.

## O que entrou

- `backend/app/middleware/security_headers.py` — `SecurityHeadersMiddleware`
  com `setdefault` em cada header (permite override por router quando
  necessário). Headers cobertos:
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - `X-Frame-Options: DENY`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: accelerometer=(), camera=(), geolocation=(), ...`
  - `Content-Security-Policy-Report-Only: default-src 'self'; ... report-uri /v1/csp-report`
- `backend/app/api/csp_report.py` — endpoint `POST /v1/csp-report` aceita
  payload cap 8KB + log estruturado em `mathoms.security.csp_violation`.
- `backend/app/main.py` — CORS migrado para `allow_methods` + `allow_headers`
  whitelist explícita (sem wildcards), `expose_headers=["X-Trace-Id"]`,
  `max_age=600`.
- `backend/tests/test_security_headers.py` + `backend/tests/test_csp_report.py`
  — cobertura de 2xx/4xx/5xx + payload cap + endpoint contract.

## Por que importa

Closure de 2 P0 da revisão pré-produção. Combinado com [[ADR-230]] (gates CI
Trivy/gitleaks/pip-audit), fecha a frente "runtime + supply-chain" de hardening
antes do go-live de `app.mathoms.ai`. CSP entra em modo `report-only` para
coletar violações reais ~30 dias antes de promover para `enforce` (W4-T04).

## Referências

- ADR canônica: [[ADR-232]]
- Plano: [PLATFORM_REVIEW §W2-T02](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md#w2-t02-sr-001013-security-headers--cors-strict)
- Lane: [[A11.w2]]
