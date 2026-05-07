---
id: F7.a
type: lane
title: "Docker + Deploy + HTTPS (semana 1-2)"
sprint: F7
status: shipped
priority: P0
adrs: ["[[ADR-108]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/f7
  - status/shipped
  - priority/p0
---


# 7A — Docker + Deploy + HTTPS (semana 1-2)


**URLs canônicas (ADR-108):** `app.mathoms.ai` (produto) · `api.mathoms.ai/v1/...` (backend + WS) · `ops.mathoms.ai` (console interno F7F) · `docs.mathoms.ai` · `status.mathoms.ai` · apex `mathoms.ai` (landing). Staging: `*.staging.mathoms.ai`. Domínio em **Cloudflare Domains**. Ver [ARCHITECTURE.md §18](ARCHITECTURE.md#18-domínios-e-urls-públicas-f7a).

#### 7A-dev — Fatia mínima local-first (pré-Hetzner) — ✅ local fechado 2026-04-26 · ☐ dev.9 aguardando VPS

**Meta:** subir `dev.mathoms.ai` no Hetzner CX32 + Coolify (~R$45/mês) com o **mínimo absoluto** — sem F7B/F7C/F7D/F7E. Endurece depois, incremental. Acesso restrito (single user / equipe), sem LGPD, sem rate limit, sem backup off-site. **Substitui a versão "completa" das tasks 7A.1/7A.2/7A.4/7A.6/7A.7/7A.8/7A.11** por fatias mínimas; o restante de 7A entra quando promover dev → prod real.

**Hospedagem confirmada:** Hetzner Cloud CX32 Falkenstein (€7.55/mês) + Coolify self-host (substitui 7A.7 Traefik manual + parte de 7C.2 deploy). Justificativa: comparativo Hetzner × DO Droplet × DO App Platform × Heroku × Railway × Render — Hetzner ~3-10× mais barato pelo mesmo recurso, GDPR/LGPD-friendly, controle total. ADR formal pode ser escrita quando promover para produção.

**Plano de ondas paralelas:**

- **Onda 1 (3 agentes paralelos):** dev.1 + dev.2 + dev.6 — read-only audit, edits triviais, novos arquivos isolados.
- **Onda 2 (2 agentes paralelos):** (dev.3 + dev.7 num único agente — backend container completo) + dev.4 (frontend container).
- **Onda 3 (sequencial):** dev.5 — `compose.prod.yml` que referencia o output das Ondas 1+2.
- **Onda 4 (sequencial):** dev.8 — smoke local end-to-end valida tudo.

Cada agente roda em worktree isolado (`.claude/worktrees/`) a partir de `origin/main`; orquestrador mergeia branches sequencialmente. Status atualizado no BACKLOG (commit + push) a cada start/end.

**Sequência de execução (8 itens, ~5h total — 4h local, 1h pós-VPS):**

| #     | Item                                                                                              | Local-only? | Mapeia em | Tempo  | Status |
| ----- | ------------------------------------------------------------------------------------------------- | ----------- | --------- | ------ | ------ |
| dev.1 | **Audit dos compose existentes + Makefile** — decidir reuso vs novo (5 composes já no repo)      | ✅ sim      | pré-7A    | 30min  | ✅ Onda 1 |
| dev.2 | **Verificar `output: 'standalone'`** em `frontend/next.config.ts` e `frontend-ops/next.config.ts` | ✅ sim      | pré-7A.2  | 15min  | ✅ Onda 1 (`9939a3f`) |
| dev.3 | **Backend Dockerfile minimal** (single-stage, 3 CMDs: `api`/`worker`/`beat`, sem otimizar tamanho) | ✅ sim     | 7A.1 (fatia) | 1h    | ✅ Onda 2 (`56458df`, 1.38GB disk / 318MB content) |
| dev.4 | **Frontend Dockerfile minimal** (multi-stage Next standalone, só `frontend/` cliente)             | ✅ sim      | 7A.2 (fatia) | 45min | ✅ Onda 2 (`1e28bf5`, 291MB disk / 71.5MB content) |
| dev.5 | **`docker-compose.prod.yml` minimal** (api+worker+beat + frontend + PG + Redis; **sem Traefik** — Coolify cuida; portas em `127.0.0.1` para teste local) | ✅ sim | 7A.4 (fatia) | 1h | ✅ Onda 3 (`95e2b0d`, 6 services + 3 volumes) |
| dev.6 | **`.env.prod.example` + `dev/gen-secrets.sh`** (FERNET_KEY, JWT_SECRET via `python -c`)           | ✅ sim      | 7A.5 ✅ (já feito; só script novo) | 15min | ✅ Onda 1 (`4b2d5b8`) |
| dev.7 | **Wrapper de boot backend** (`backend/scripts/entrypoint.sh`): `alembic upgrade head` antes de `uvicorn`/`celery`, idempotente, só na role `api` | ✅ sim | 7A.9 (fatia) | 30min | ✅ Onda 2 (junto com dev.3, `56458df`) |
| dev.8 | **Smoke local prod-mode end-to-end**: `docker compose -f docker-compose.prod.yml up`, registrar user, login, upload PDF, trigger pipeline, ver relatório | ✅ sim | 7A.11 (fatia) | 30min | ✅ Onda 4 (`10681ad` — passou com 2 fixes: asyncpg + frontend healthcheck wget) |
| dev.9 | (pós-VPS) Hetzner CX32 + UFW + Docker + Coolify + Cloudflare A record `dev.mathoms.ai` + deploy + smoke remoto | ❌ precisa VPS | 7A.6/7A.7/7A.8/7A.13 (fatia) | 1h20 | ☐ |

**Notas do audit dev.1 (2026-04-26):** Já existem 2 Dockerfiles — `frontend-ops/Dockerfile` (multi-stage Next standalone, bind 127.0.0.1:3100) e `pipeline-service/Dockerfile` (Python uvicorn). **Não existem** Dockerfiles para backend nem frontend principal — dev.3 e dev.4 criam do zero. Backend boota via `uvicorn backend.app.main:app`, env prefix `MATHOMS_`, vars obrigatórias: `MATHOMS_FERNET_KEY`, `MATHOMS_SECRET_KEY`, `MATHOMS_DATABASE_URL`, `MATHOMS_REDIS_URL`, `MATHOMS_STORAGE_ROOT`. Alembic config em `backend/alembic.ini`. Celery: `celery -A backend.app.worker worker`. `frontend/next.config.ts` usa `withNextIntl(nextConfig)` wrapper — `output: 'standalone'` foi adicionado no objeto interno (commit `9939a3f`, dev.2). `storage/` precisa volume persistente. Compose atual: `docker-compose.yml` é só Redis (base), `.dev.yml` é só `frontend-ops`, `.test.yml` é PG+Redis isolados (porta 5433/6380), `.smoke.yml` Redis pra Makefile dev. **Decisão:** `compose.prod.yml` será novo arquivo standalone (não `include:`-compõe os outros), porque escopo é diferente (containers self-contained pra Coolify). `pipeline-service/` e `services/` ficam fora do compose.prod minimal (sem cliente).

**Notas das Ondas 1+2 (achados que orientam dev.5):**
- **Backend `requirements.txt` é dual:** raiz (594B, deps de pipeline) + `backend/requirements.txt` (1475B, fastapi/sqlalchemy/celery/alembic/psycopg2-binary). Dockerfile (`56458df`) instala os dois.
- **Backend image `Dockerfile`** na raiz; entrypoint em `backend/scripts/entrypoint.sh` aceita `api`/`worker`/`beat`. Alembic só roda em `api` (limitação multi-replica aceita).
- **Frontend image `frontend/Dockerfile`** com build context na raiz (`docker build -f frontend/Dockerfile .`) — precisa de `design-tokens/` + `config/report_layout.yaml` para `prebuild`.
- **`@swc/helpers`** copy explícito do stage `deps` (workaround do tracer Next standalone).
- **Rewrite frontend** parametrizada: env `BACKEND_INTERNAL_URL` (default dev `http://127.0.0.1:8000`; em compose prod = `http://backend:8000`).
- **`.dockerignore`** raiz (criado em dev.4) é conservador — só caches/secrets/dados; preserva `pipeline/`/`backend/`/`config/`/`design-tokens/` para builds que usam o monorepo.
- **Healthcheck backend `/health`** falha em modos `worker`/`beat` (sem HTTP). `compose.prod.yml` deve dar `healthcheck: disable: true` por serviço nesses modos.

**Premissas e cortes conscientes:**

- Domínio `mathoms.ai` é do usuário (confirmado 2026-04-26). Apenas **1 record DNS** necessário nesta fase: `dev.mathoms.ai` A → IP do CX32, proxy **OFF** (Coolify quer 80/443 direto pra cert Let's Encrypt). Resto de 7A.8 (apex/www/api/ops/staging/MX/SPF/DKIM) **adiado**.
- **Pula nesta fase:** F7B inteira (rate limit, CSP, audit log, email verification, password reset, brute-force lockout, prompt injection defense), F7C inteira (CI/CD — deploy via push GitHub + webhook Coolify), F7D inteira (coverage gate, dogfood), F7E inteira (off-site backup, status page, LLM cap), `frontend-ops/` em container (roda local), `pipeline-service/` Go (sem cliente).
- **Limitações aceitas** (registrar para retomada na promoção dev → prod):
  - Sem rate limit → não compartilhar URL publicamente; mitigação opcional: basic-auth Cloudflare por cima.
  - Sem backup off-site → snapshot Hetzner manual (€0 até 7d) é a única rede.
  - Sem email verification → desligar `REQUIRE_EMAIL_VERIFICATION` no `.env.prod.local`.
  - 1 réplica de api (Alembic no entrypoint não tem lock) — escalonar exige migrar lock pra Postgres ou beat-only-runs-migration.
  - `.env` em texto puro no diretório Coolify do servidor.

**Preserva dev local:** todos os arquivos novos são adicionais (`Dockerfile`, `frontend/Dockerfile`, `docker-compose.prod.yml`, `.env.prod.example`, `dev/gen-secrets.sh`, `backend/scripts/entrypoint.sh`). Nenhum edit em `docker-compose.dev.yml`, `requirements.txt`, `package.json` ou código de aplicação. `next.config.ts` ganha `output: 'standalone'` sem afetar `npm run dev`.

**Promoção dev → prod (incremental, depois):** F7B P0 (~3 dias) → 7A.10 + 7E.4 backup off-site (~1 dia) → 7C.1+7C.2 CI/CD (~1 dia) → trocar subdomain `dev.` por `app.` + `api.` (~1h). Nenhum trabalho de `7A-dev` é jogado fora — só endurecido.

**✅ Estado de fechamento (2026-04-26):** dev.1–dev.8 entregues em main em 4 ondas paralelas (~3h total wall-clock, 7 agentes em worktrees isolados). Stack containerizado validado end-to-end via smoke (`10681ad`): 6 services healthy (postgres/redis/api/worker/beat/frontend), Alembic 31 tabelas, auth flow completo (register/login/me), worker+beat boot OK. **2 bugs reais corrigidos durante smoke:** `asyncpg` faltava em `backend/requirements.txt` (URL é `postgresql+asyncpg://`); frontend healthcheck usava `curl` mas alpine só tem `wget`. **Débito leve registrado** (não bloqueia VPS): `dev/gen-secrets.sh` exige `cryptography` no python ativo, falha silenciosa em system python. **Próximo:** dev.9 (provisionar Hetzner CX32 + Coolify + DNS + smoke remoto, ~1h20).

---

**Tabela canônica F7A** (versões "completas" das tasks; fatias mínimas estão em 7A-dev acima):

| #     | Tarefa                                                                               | Prio | Est. | Status |
| ----- | ------------------------------------------------------------------------------------ | ---- | ---- | ------ |
| 7A.1  | Dockerfile backend (multi-stage, entrypoints api/worker, ~200MB, non-root)           | P0   | 4h   | ☐      |
| 7A.2  | Dockerfile frontend (multi-stage, Next.js standalone, ~100MB)                        | P0   | 3h   | ☐      |
| 7A.3  | `docker-compose.dev.yml` (PG + Redis + hot reload)                                   | P0   | 3h   | ☐      |
| 7A.4  | `docker-compose.prod.yml` (API + Worker + Frontend + Ops + PG + Redis + Traefik) com labels Traefik para `app`/`api`/`ops`/`docs` | P0 | 6h | ☐ |
| 7A.5  | `.env.example` + env management + `scripts/gen-secrets.sh`                           | P0   | 2h   | ✅     |
| 7A.6  | VPS provisioning (Hetzner CX32, UFW, SSH keys, fail2ban, Docker)                     | P0   | 3h   | ☐      |
| 7A.7  | Traefik config (auto-SSL via **DNS-01 Cloudflare**, HTTP→HTTPS, TLS 1.3+, WebSocket pass-through, wildcard `*.mathoms.ai` + `*.staging.mathoms.ai`) | P0 | 5h | ☐ |
| 7A.7b | **Middleware `ipAllowList` em Traefik para `ops.mathoms.ai`** (IPs do time) + middleware CORS estrito em `api.mathoms.ai` | P0 | 2h | ☐ |
| 7A.8  | **DNS Cloudflare** — configurar records: apex A (proxy ON), `www` CNAME (proxy ON), `app/api/ops` A (proxy OFF), `docs/status` (proxy ON), `*.staging` A (proxy OFF). Criar API token `Zone:DNS:Edit` (scope apenas `mathoms.ai`) para Traefik. | P0 | 2h | ☐ |
| 7A.8b | **MX records + SPF + DKIM + DMARC** em Cloudflare para `mathoms.ai`; provider transacional (Postmark ou Resend) configurado | P0 | 3h | ☐ |
| 7A.8c | **Emails institucionais** (`noreply@`, `support@`, `hello@`, `ops@`, `security@`) — Google Workspace ou Fastmail | P0 | 1h | ☐ |
| 7A.9  | PostgreSQL prod (DB + user dedicado, Alembic upgrade, pool_size)                     | P0   | 3h   | ☐      |
| 7A.10 | Backup automático (pg_dump diário, rotação 7 dias, script restore testado)           | P0   | 3h   | ☐      |
| 7A.11 | Smoke test completo local (prod compose, health checks, SSL, login, upload)          | P0   | 3h   | ☐      |
| 7A.11b | **Teste cookie leakage** (Playwright): validar que session de `app.mathoms.ai` não é aceita em `ops.mathoms.ai` e vice-versa | P0 | 2h | ☐ |
| 7A.12 | Data migration plan (`scripts/seed-prod.sh`, procedimento import via API)            | P0   | 3h   | ☐      |
| 7A.13 | First deploy real → Produto no ar em `app.mathoms.ai`; ops em `ops.mathoms.ai`       | P0   | 2h   | ☐      |

**Meta 7A:** TLS 1.3 em 100% dos endpoints · Lighthouse `app.mathoms.ai` > 90 · Zero cookie leakage entre `app.` e `ops.` · Time-to-setup novo subdomain < 5 min.
