---
id: ADR-232
type: adr
title: "Security headers + CORS strict no backend FastAPI (CSP report-only, HSTS, HSTS, allowlist explícita)"
status: Decidido
phase: A11.W2
date: "2026-05-20"
relates_to:
  - "[[ADR-108]]"
  - "[[ADR-110]]"
  - "[[ADR-170]]"
  - "[[ADR-230]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 232"
  - "security-headers"
  - "CSP HSTS CORS"
tags:
  - area/security
  - area/backend
  - phase/a11
  - status/decidido
  - type/adr
---

## Contexto

Sprint A11 W2-T02 consolida findings SR-001 + SR-013 da revisão
multi-agente 2026-05-06: o backend FastAPI **não emite nenhum header
de segurança HTTP** e o `CORSMiddleware` está em modo permissivo
(`allow_methods=["*"]`, `allow_headers=["*"]`).

Verificações de superfície em `backend/app/main.py:96-102` (commit
`fbc15d1`):

- Sem `Strict-Transport-Security` → MITM em redes hostis pode rebaixar
  para HTTP.
- Sem `Content-Security-Policy` (nem report-only) → XSS reflected
  qualquer pequena falha de escape no relatório vira `<script>`.
- Sem `X-Frame-Options` nem `frame-ancestors` → clickjacking trivial em
  `/reports/[id]` (relatório financeiro embedável).
- Sem `X-Content-Type-Options: nosniff` → IE/legacy interpretam `.json`
  como `text/html` se Content-Type for ambíguo.
- Sem `Referrer-Policy` → URL do relatório (com query params sensíveis)
  vaza para terceiros via header `Referer`.
- Sem `Permissions-Policy` → policy default do browser dá acesso a
  `geolocation`, `camera`, `microphone`, `payment` que o produto nunca
  usa.
- `CORS allow_methods=["*"] + allow_headers=["*"]` + `allow_credentials=True`
  é combinação que o spec CORS aceita mas é overpermissiva — qualquer
  método novo (TRACE, CONNECT) e qualquer header arbitrário passam.
  CSRF é mitigado por SameSite cookies + JWT em header (ADR-170), mas
  o gate de defesa em profundidade falta.

Mathoms é fintech multi-tenant manipulando dados financeiros + LGPD;
P0 para go-live de `app.mathoms.ai`/`api.mathoms.ai` (ADR-108).

### Trade-offs operacionais

1. **CSP enforce vs report-only.** Política CSP estrita em modo enforce
   sem janela de telemetria quebra integrações silenciosas (Google
   Fonts via Next.js, Sentry beacon W4-T03, Resend tracking pixel
   W3-T02 se houver). Caminho seguro: começar em **report-only** com
   endpoint coletor de violations; promover a enforce em ADR follow-up
   após observação.
2. **HSTS preload.** Listar `mathoms.ai` no preload-list do Chromium
   é one-way: revert ~6 meses. Não fazer agora; só pós-cutover prod com
   pelo menos 30 dias estável.
3. **CORS dev vs prod.** Em dev local o backend serve `localhost:8000`
   e o frontend `localhost:3000`. Em prod, `api.mathoms.ai` ↔
   `app.mathoms.ai`. `CORS_ORIGINS` em `Settings` já é lista — basta
   garantir que valores vêm de env e não default sticky.

## Decisão

**Adotar middleware Starlette dedicado `SecurityHeadersMiddleware`**
em `backend/app/middleware/security_headers.py`, registrado em
`backend/app/main.py` **antes** de `CORSMiddleware` (middleware stack
do Starlette executa em ordem reversa de `add_middleware`; vide
ADR-110 ordem `correlation → deprecation → cors → ...`).
Tightening simultâneo do `CORSMiddleware` para listas explícitas.

### D1 — Headers HTTP emitidos em toda resposta

| Header | Valor | Motivação |
|---|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS por 1 ano. **Sem `preload`** (ver Trade-off 2). |
| `X-Frame-Options` | `DENY` | Bloqueia framing total. Relatório legítimo é renderizado in-app, não embedado. CSP `frame-ancestors 'none'` cobre browsers modernos; `X-Frame-Options` é fallback IE/legacy. |
| `X-Content-Type-Options` | `nosniff` | Bloqueia MIME-sniffing — JSON respondido como `text/html` por bug não vira execução. |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Path + query não vaza cross-origin; só o origin. Equilíbrio entre privacidade e analytics próprio. |
| `Permissions-Policy` | `accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()` | Allowlist vazia para 8 features que produto não usa. |
| `Content-Security-Policy-Report-Only` | Ver D2 | Coleta violations sem bloquear. |

`Content-Security-Policy` (enforce) **não é emitido nesta ADR** — só
report-only. Promoção a enforce em ADR-follow-up depois de janela de
telemetria (mínimo 14 dias em prod com tráfego real).

### D2 — Política CSP report-only

```
default-src 'self';
script-src 'self' https://cdn.jsdelivr.net;
style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;
img-src 'self' data: blob: https://fastapi.tiangolo.com;
font-src 'self' data:;
connect-src 'self';
worker-src 'self';
frame-ancestors 'none';
base-uri 'self';
form-action 'self';
object-src 'none';
report-uri /v1/csp-report
```

- `style-src 'unsafe-inline'`: Next.js inline styles via CSS-in-JS no
  relatório premium (ADR-076). Migração para nonce-based fica como
  follow-up no ADR de promoção a enforce.
- `script-src` + `style-src` + `img-src` permitem `cdn.jsdelivr.net`
  + favicon `fastapi.tiangolo.com`: Swagger UI bundle default do
  FastAPI carrega assets daí. **Follow-up:** self-host Swagger
  (`swagger_ui_parameters` apontando para assets locais) descarta
  esta exceção. Sem o allowlist, `/api/v1/docs` floda `/v1/csp-report`
  com violations a cada boot.
- `connect-src 'self'`: aplica-se apenas a recursos que o backend
  serve diretamente e que disparem fetch (raro — Swagger UI,
  console interno futuro). CSP que governa o app SPA é
  responsabilidade do `frontend/next.config.ts` (out of scope deste
  PR). Defesa em profundidade no backend mesmo assim.
- `worker-src 'self'`: futuras edge functions / web workers em
  endpoints próprios. Trivial agora, evita follow-up.
- `report-uri /v1/csp-report`: endpoint criado nesta ADR
  (`POST` recebendo JSON, logando estruturado com level `WARNING`).
  Não é stub — endpoint real, ingest no formato CSP Level 2 (browsers
  legacy) e Level 3 (`report-to` directive fica para a promoção).
- **Payload cap defensivo neste PR:** handler `POST /v1/csp-report`
  lê `await request.body()` e rejeita 413 antes de parse se
  `Content-Length > 8192` OU se `body` bruto excede 8KB. Endpoint é
  anônimo → cap é P0 desta lane, não pode ficar dependente do rate
  limit global (W4-T04).
- **Auth:** endpoint `csp-report` aceita anônimo (sem JWT) — é
  navegador relatando, não consumer interno. Rate limit dele entra
  em W4-T04 como camada adicional (não substitui o cap de payload).

### D3 — CORS tightening

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,      # explicit list, sem wildcards
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Trace-Id",
        "X-Workspace-Id",
        "Accept",
        "Accept-Language",
        "If-None-Match",
        "If-Modified-Since",
    ],
    expose_headers=["X-Trace-Id"],
    max_age=600,
)
```

- `allow_methods` enumera os métodos que o produto realmente usa.
  `TRACE`, `CONNECT`, `HEAD` ficam de fora — `HEAD` é gerado por
  `GET` automaticamente pelo Starlette quando preciso.
- `allow_headers` enumera headers permitidos no preflight. `X-Trace-Id`
  é da ADR-110 (correlation); `X-Workspace-Id` é usado pela tenancy
  guard (ADR-101).
- `expose_headers=["X-Trace-Id"]` permite o frontend ler trace ID em
  resposta cross-origin (para correlação client-side).
- `max_age=600`: 10min de cache do preflight; reduz N+1 OPTIONS em
  bursts de requests.

`settings.CORS_ORIGINS` continua vindo de env (`CORS_ORIGINS` lista),
default `["http://localhost:3000"]` em dev. Em prod
`["https://app.mathoms.ai"]` (e `https://*.staging.mathoms.ai` em
staging por ADR-108).

### D4 — Ordem dos middlewares

```python
app.add_middleware(CorrelationIdMiddleware)         # primeiro a executar
app.add_middleware(LegacyApiDeprecationMiddleware)
app.add_middleware(SecurityHeadersMiddleware)        # NOVO — antes do CORS
app.add_middleware(CORSMiddleware, ...)              # depois
```

Starlette executa em ordem reversa do `add_middleware`. Logo:
`CORS → SecurityHeaders → LegacyDeprecation → Correlation → endpoint`.

Importante: o middleware de segurança adiciona headers no `response`
de **todas** as rotas, **inclusive** preflight CORS (200 do
`OPTIONS`). Se CORS rodasse antes (mais externo), o preflight nem
chegaria ao security headers. Logo, security depois do CORS na chain
de chamada externa (ou seja, security mais "interno" → security é
adicionado **antes** de CORS via `add_middleware` na visão do
desenvolvedor).

## Alternativas consideradas

### (A) Lib third-party (`starlette-secure-headers`, `secure.py`)

Custo: dependência nova (~150 LOC equivalente), one more transitive
deps no pip-audit. **Descartada:** middleware é ~60 linhas
self-contained; lib adiciona surface de pen-test sem ganho. Padrão
seguido por outras middleware do projeto (`correlation.py`,
`legacy_deprecation.py`).

### (B) CSP enforce direto (sem report-only)

Mais seguro em curto prazo. **Descartada:** sem janela de telemetria,
arrisca quebrar página de relatório (CSS-in-JS, fontes externas em
dev) e produzir alertas falsos no cutover. Caminho gradual report-only
→ enforce é o recomendado pelo W3C CSP spec.

### (C) Headers no reverse-proxy (Coolify/Caddy/Cloudflare)

Funciona em prod, mas dev local não tem proxy. Diferencial entre dev
e prod produz drift silencioso (header testável em prod, ausente em
dev — bug só descoberto em incident). **Descartada:** middleware é
único ponto de verdade; reverse-proxy fica como reforço opcional.

### (D) Aplicar no `frontend/next.config.ts` via `headers()`

Cobre só rotas Next.js, não as do FastAPI. **Descartada:** AC do W2-T02
trata explicitamente do backend; frontend headers ficam como
follow-up se/quando necessário (Next.js já tem defaults aceitáveis).

## Consequências

**Positivas:**

- ✅ Closure de SR-001 + SR-013 (severity P0).
- ✅ Defesa em profundidade contra XSS reflected (CSP), clickjacking
  (XFO + frame-ancestors), MITM (HSTS), MIME confusion (nosniff).
- ✅ CORS preflight enumerado — `OPTIONS` futuro com header não
  enumerado falha rápido (e dá sinal de tentativa de fingerprinting).
- ✅ Padrão reutilizável: feature flag de policy fica no settings,
  futura ADR de enforce não muda middleware.

**Negativas:**

- ⚠️ CSP report-only gera tráfego de relatório (`/v1/csp-report`) cujo
  volume depende do navegador do usuário. Mitigado: endpoint loga
  estruturado e count é coletado em log analytics; rate limit de
  W4-T04 protege contra flood.
- ⚠️ `style-src 'unsafe-inline'` é aceitação técnica do estado atual
  (CSS-in-JS). Item de débito explícito para promoção CSP enforce.
- ⚠️ Em dev local quem chama `localhost:8000` direto (Postman, curl)
  vê os headers; alguns scripts que dependem de resposta sem `X-Frame-Options`
  podem precisar adaptar (caso raro).

**Riscos:**

| Risco | Mitigação |
|---|---|
| CSP report-only flood (browsers buggy) | Endpoint loga com level WARNING + correlation_id; alarme só se >100/min sustentado. |
| HSTS bloqueia recuperação se cert quebrar | `max-age=31536000` é forte mas sem `preload` — flush é via reset do header (vide D2 e Trade-off 2 do contexto). |
| Browser legado não suporta Permissions-Policy | Header é ignorado silenciosamente — fail-open aceitável (não estamos defendendo de IE6). |
| Endpoint csp-report virar vetor de DoS | Payload cap 8KB **neste PR** (defesa hard) + rate limit W4-T04 (defesa adicional). |
| Swagger UI flooda `/v1/csp-report` em dev/staging | Allowlist explícito de `cdn.jsdelivr.net` + `fastapi.tiangolo.com` na policy; débito de self-host registrado em D2. |

## Gates desta ADR

- **Doc + código no mesmo PR (P0 W2-T02):** middleware + tests + ADR
  flippada para `Decidido (Sprint A11.W2)` no merge.
- **Snapshot OpenAPI:** novo endpoint `POST /v1/csp-report` adiciona
  entrada no schema — `make update-openapi-snapshot` obrigatório.
- **Closure:** PR mergeado, headers verificáveis via
  `curl -I https://api.staging.mathoms.ai/v1/health` em staging.

## Referências

- [SR-001 + SR-013](../plan/PLATFORM_REVIEW/_README.md#wave-2--pipeline--db-hardening-sprint-1-7-dias-dev) — findings origem.
- [ADR-108](108-estrategia-de-subdominios-mathomsai-cloudflare-dns.md) — URLs prod `api.mathoms.ai` ↔ `app.mathoms.ai`.
- [ADR-110](110-structured-json-logging-opentelemetry-bootstrap.md) — `CorrelationIdMiddleware` (referência de padrão).
- [ADR-170](170-refresh-tokens-com-httponly-cookie-e-family.md) — JWT auth scheme (CSRF mitigation paralela).
- [ADR-230](230-security-gates-ci.md) — gates CI já decididos (Trivy, gitleaks); esta ADR cobre runtime.
- [CSP Level 2 spec](https://www.w3.org/TR/CSP2/) — `Content-Security-Policy-Report-Only`.
- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/) — referência de defaults.
