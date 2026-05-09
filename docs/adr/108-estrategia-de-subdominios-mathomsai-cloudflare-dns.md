---
id: ADR-108
type: adr
title: "Estratégia de subdomínios `mathoms.ai` + Cloudflare DNS"
status: Decidido
date: "2026-04-20"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 108"]
tags:
  - area/multitenancy
  - area/ops
  - area/security
  - status/decidido
  - type/adr
size_lines: 105
---

# ADR-108 — Estratégia de subdomínios `mathoms.ai` + Cloudflare DNS

**Status:** Decidido • **Data:** 2026-04-20

**Contexto:** Domínio `mathoms.ai` adquirido via Cloudflare Domains em
2026-04-20. Precisamos definir estrutura de URLs públicas para produto,
API, console interno (F7F), docs e status page — em três ambientes (prod,
staging, dev). Alternativas consideradas:

1. **Path-based** (`mathoms.ai/app/`, `/api/`, `/admin/`): 1 cert, DNS
   simples, mas cookies e CORS compartilhados entre serviços (admin
   session pode vazar para app); CDN/cache uniforme, rate limit uniforme
   — pouco cirúrgico.
2. **Subdomain-based** (`app.mathoms.ai`, `api.mathoms.ai`, etc.): cookies
   isolados (`__Host-` por subdomain), TLS independente, CORS explícito,
   políticas de rate limit e CDN por serviço. Custo: 1 cert wildcard
   (Let's Encrypt via DNS-01).
3. **Subdomain-per-tenant** (`<slug>.mathoms.ai`): enterprise feel,
   isolamento total; complexidade de DNS e cert-per-tenant; prematuro.

**Decisão:**

1. **Subdomínios por serviço** (opção 2) com sufixo de ambiente. Produção
   omite sufixo:

   | Papel | Produção | Staging | Dev local |
   |---|---|---|---|
   | Landing marketing | `mathoms.ai` (apex) | `staging.mathoms.ai` | — |
   | Produto (Next.js) | `app.mathoms.ai` | `app.staging.mathoms.ai` | `localhost:3000` |
   | API (FastAPI + WS) | `api.mathoms.ai` | `api.staging.mathoms.ai` | `localhost:8000` |
   | Console interno | `ops.mathoms.ai` | `ops.staging.mathoms.ai` | `localhost:3000/ops` |
   | Docs do produto | `docs.mathoms.ai` | — | — |
   | Status page | `status.mathoms.ai` | — | — |
   | Sharing público (F10+) | `share.mathoms.ai` (reservado) | — | — |
   | Previews (opt) | `<branch>.preview.mathoms.ai` | — | — |

2. **Multi-tenancy via path**, não subdomain: `app.mathoms.ai/w/<slug>/...`
   — subdomain-per-tenant adiado para enterprise tier futuro.

3. **Naming do console interno = `ops.`** (não `admin.`) — "admin" é
   ambíguo em SaaS multi-tenant (colide com role `owner` de workspace);
   `ops.` é explicitamente para operadores Mathoms.

4. **Versionamento de API = `api.mathoms.ai/v1/`** (não `/api/v1/` —
   redundante com o subdomain). Alinha com R16 (ADR-101) sem duplicar
   prefix.

5. **DNS = Cloudflare** (domínio já está lá):
   - **(Sugestão, condicional a [[ADR-005]] / [[ADR-058]] — ambas
     `Proposto`)** Wildcard `*.mathoms.ai` → A record do VPS Hetzner
     (proxy Cloudflare **desligado** para `app/api/ops` — evita double-TLS
     e WebSocket issues; **ligado** para `mathoms.ai` apex e `docs.` —
     CDN/WAF grátis). Caso a decisão de hosting de backend seja fechada
     em outra direção (Cloud Run, Fly.io, etc.), esta linha é revisitada
     no momento da decisão. **A landing estática (`mathoms.ai` apex) já
     publica via Cloudflare Pages — ver [[ADR-184]]; não depende de
     [[ADR-005]].**
   - `*.staging.mathoms.ai` → mesmo VPS (ou ambiente separado quando
     crescer).
   - TLS via Let's Encrypt DNS-01 challenge (Traefik + Cloudflare API
     token com permissão `Zone:DNS:Edit`) — aplicável **a partir do
     momento que** o hosting de backend for decidido com Traefik no path.
     Para a landing estática (`mathoms.ai` apex via CF Pages), TLS é
     Universal SSL automático do Cloudflare (não precisa Let's Encrypt).
   - `www.mathoms.ai` → 301 apex.

6. **Cookies e sessão:**
   - Sempre `__Host-` prefix (força `Secure`, `HttpOnly`, `Path=/`, sem
     `Domain`).
   - `app.mathoms.ai` e `ops.mathoms.ai` nunca compartilham cookies.
   - Nenhum cookie com `Domain=mathoms.ai`.

7. **CORS estrito:** `api.mathoms.ai` aceita apenas origins
   `https://app.mathoms.ai` + `https://ops.mathoms.ai` (+ staging
   equivalentes). Nenhum `*`.

8. **Segurança do console interno (`ops.`):**
   - IP allowlist no Traefik (`ipAllowList` middleware).
   - MFA obrigatório (TOTP no mínimo).
   - Rotas sensíveis do backend sob `api.mathoms.ai/v1/internal/*` com
     middleware próprio.

**Por que Cloudflare DNS:** domínio já comprado lá — zero fricção; API
estável para DNS-01 (Traefik provider nativo); proxy opcional grátis
(CDN/WAF para landing e docs); DDoS L3/L4 grátis.

**Discarded options:**
- Path-based: cookies e CORS não isoláveis → inaceitável para console
  interno.
- Subdomain-per-tenant: prematuro; upgrade-path disponível.
- `admin.mathoms.ai`: conflito semântico com role de workspace.

**Consequências:**
- ✅ Isolamento de segurança entre produto e console interno.
- ✅ CDN/cache/rate-limit configuráveis por subdomain.
- ✅ Blast radius de cert/WAF misconfig contido.
- ✅ URL predizível para suporte.
- ✅ Upgrade path para enterprise custom-domain sem refactor.
- ⚠️ Cert wildcard exige DNS-01 (Cloudflare API token) — dependência
  operacional adicional.
- ⚠️ Subdomain `ops.` pesquisável via CT logs; segurança vem de IP
  allowlist + MFA, não obscuridade.

**Esforço estimado:** +4h sobre F7A original (DNS Cloudflare 30min +
Traefik DNS-01 1-2h + migração CORS/cookies/env 2h).

**Metas:**
- TLS 1.3 em 100% dos endpoints públicos.
- Lighthouse `app.mathoms.ai` > 90.
- Zero cookie leakage entre `app.` e `ops.` (validado com Playwright).
- Time-to-setup novo subdomain < 5 min.
