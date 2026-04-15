# Fin — Backlog

> Fonte de verdade operacional. Atualizar semanalmente.
>
> **Legenda de status:** ☐ Pendente • 🚧 Em andamento • ✅ Concluído • ⏭ Adiado • ❌ Descartado
>
> **Legenda de prioridade:** **P0** bloqueante • **P1** importante • **P2** nice-to-have

---

## Índice

- [Fases concluídas (F0-F6)](#fases-concluídas-f0-f6)
- [F6.5 — Frontend Testing & QA](#f65--frontend-testing--qa) ← **próxima**
- [F7 — Produção + LGPD](#f7--produção--lgpd)
- [F8 — Growth (Futuro)](#f8--growth-futuro)

---

## Fases concluídas (F0-F6)

Fases já entregues. Tasks mantidas aqui para referência histórica e para identificar eventuais débitos técnicos.

<details>
<summary><b>F0 — Desacoplar Core ✅ (27 tasks)</b></summary>

Pipeline como package Python importável. "Wrap, Don't Rewrite" strategy.

**Sub-fases:**
- **0A** Foundation (`WorkspaceContext`, `config_loader`, golden files) — 6 tasks ✅
- **0B** Wrap módulos menores (E3, E4, E2, E7) — 7 tasks ✅
- **0C** Wrap módulos grandes (E5, E5.N, E6, E0s, E1.5c) — 10 tasks ✅ parcial
- **0D** Orchestrator + Package final — 7 tasks ✅ parcial

**Pendências (débito técnico baixa prioridade):**
- 0A.4 — `pipeline/logging.py` adapter (adiado, funciona sem)
- 0D.2 — Adaptar `e_reset.py` para usar orchestrator (mantém CLI legada)

</details>

<details>
<summary><b>F1 — Backend API + Auth ✅ (16 tasks)</b></summary>

FastAPI + SQLAlchemy async + JWT auth + Next.js 16 + Tailwind 4.

**Pendências (adiadas):**
- 1.12 — `docker-compose.dev.yml` → F7
- 1.18 — `openapi-typescript` → Usamos types manuais sincronizados. Evolui se dor aumenta.

</details>

<details>
<summary><b>F2 — Upload + Pipeline Web ✅ (38 tasks)</b></summary>

Upload batch, vault de senhas, E0 processing automático no upload, pipeline execution com tracking.

**Pendências:**
- 2C.4 — Se JSONs E1/E1.5 foram uploaded, copiar para posição correta (✅ resolvido em fix recente: `route_to_data_dir`)
- 2D.9, 2D.10 — Testes E2E → F6.5

</details>

<details>
<summary><b>F3 — Config UI ✅ (32 tasks)</b></summary>

18 endpoints CRUD + 5 configs editáveis via UI (6 tabs) + materialização + import/export JSON.

**Pendências:**
- 3D.9, 3D.10 — Testes E2E de config → F6.5

</details>

<details>
<summary><b>F4 — Automação LLM ✅ (34 tasks)</b></summary>

LiteLLM + Instructor. 4 LLM stages (E1, E1.5, E2-llm, E7-review). BYOK. Tier detection. Needs_review workflow.

**Pendências:**
- 4D.8, 4D.9, 4D.10 — UI de config LLM, tier badges, review manual → ✅ Feitos em F6D

</details>

<details>
<summary><b>F4.5 — Design System Foundation ✅ (27 tasks)</b></summary>

Tailwind v4 `@theme inline` (30+ tokens oklch) + Geist fonts + shadcn/ui (16 primitivos + 7 compostos) + 10 pages migradas.

**Sem pendências.**

</details>

<details>
<summary><b>F5 — Task Queue + Real-time ✅ (23 tasks)</b></summary>

Celery + Redis. WebSocket + polling fallback. Stage-boundary cancel. Per-stage retry config. Health check.

**Sem pendências estruturais.**

</details>

<details>
<summary><b>F6 — Frontend Profissional ✅ (48 tasks)</b></summary>

- **6A** Transaction Explorer (DataTable, filtros, busca, category override, export, paginação, URL state) — ✅ 12 tasks
- **6B** Dashboard (Recharts, KPIs, 4 charts, alertas, filtros, drill-down) — ✅ 12 tasks
- **6C** Report React (sections, validação L1+L2, history, PDF print, CSV/XLSX, data lineage) — ✅ 12 tasks
- **6D** UX Polish (dark mode, nav, LLM config UI, tier badges, review UI, notifications) — ✅ 12 tasks

**Bugs corrigidos na passagem recente de QA** (2026-04-14/15):
Ver [CHANGELOG.md](CHANGELOG.md#bug-fixes-2026-04-1415).

</details>

---

## F6.5 — Frontend Testing & QA

**Objetivo:** Rede de segurança de testes. Vitest + RTL + MSW + Playwright.

**Duração estimada:** 2 semanas

### 6.5A — Tooling Setup + Unit Tests (semana 1, dias 1-3)

| #      | Tarefa                                                                      | Prio | Est. | Status |
| ------ | --------------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5A.1 | Setup Vitest (`vitest.config.ts`, jsdom, path aliases, coverage v8)         | P0   | 2h   | ☐      |
| 6.5A.2 | Setup MSW (`tests/mocks/server.ts` + handlers + fixtures JSON)              | P0   | 3h   | ☐      |
| 6.5A.3 | Unit tests `format.ts` (9 formatters + 3 status maps, ~40 cases)            | P0   | 4h   | ☐      |
| 6.5A.4 | Unit tests `export.ts` (CSV BOM, XLSX auto-width, mock document.createElement) | P0 | 2h | ☐      |
| 6.5A.5 | Unit tests `api.ts` (token mgmt, apiFetch, ApiError, 401 redirect)          | P0   | 3h   | ☐      |
| 6.5A.6 | Unit tests `utils.ts` (`cn()` Tailwind merge)                               | P0   | 1h   | ☐      |
| 6.5A.7 | Unit tests `usePipelineWS.ts` (connect, events, reconnect backoff)          | P1   | 3h   | ☐      |
| 6.5A.8 | Coverage baseline + thresholds em `vitest.config.ts`                        | P0   | 1h   | ☐      |

**Checkpoint:** ~50-60 unit tests green. `npm test` <5s.

### 6.5B — Integration Tests — Pages + Components (semana 1-2)

| #       | Tarefa                                                                     | Prio | Est. | Status |
| ------- | -------------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5B.1  | Tests Login/Register (render, submit, errors, loading)                     | P0   | 3h   | ☐      |
| 6.5B.2  | Tests Dashboard (KPIs, charts, empty, error, loading, drill-down, refresh) | P0   | 4h   | ☐      |
| 6.5B.3  | Tests Documents (empty, drag-drop, progress, needs_password, delete, CTA)  | P0   | 4h   | ☐      |
| 6.5B.4  | Tests Pipeline (trigger, WS progress, needs_review, cancel, failed)        | P0   | 5h   | ☐      |
| 6.5B.5  | Tests Transactions (render, busca, override, export, paginação, URL state) | P0   | 5h   | ☐      |
| 6.5B.6  | Tests Reports (list, viewer iframe, print, download, export tables)        | P0   | 4h   | ☐      |
| 6.5B.7  | Tests Config (6 tabs: Members, Categories, Pipeline, LLM, Inst, Layout)    | P0   | 5h   | ☐      |
| 6.5B.8  | Tests Vault (CRUD passwords, retry unlock)                                 | P0   | 2h   | ☐      |
| 6.5B.9  | Tests AppShell (auth gate, navigation, mobile, logout, NotificationCenter) | P0   | 3h   | ☐      |
| 6.5B.10 | Tests compostos (KPICard, EmptyState, StatusBadge, ConfirmDialog, Delta, Spinner, ThemeToggle, DataTable) | P1 | 3h | ☐ |
| 6.5B.11 | Tests dark mode (7 compostos + Dashboard charts + Transaction table)       | P1   | 2h   | ☐      |

**Checkpoint:** ~120-150 integration tests green. `npm test` <30s.

### 6.5C — E2E Tests + Smoke Checklist (semana 2)

| #       | Tarefa                                                              | Prio | Est. | Status |
| ------- | ------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5C.1  | Setup Playwright (`playwright.config.ts`, webServer, auth helper)   | P0   | 3h   | ☐      |
| 6.5C.2  | E2E Fluxo 1 — Onboarding completo                                   | P0   | 3h   | ☐      |
| 6.5C.3  | E2E Fluxo 2 — Upload → Pipeline → Report                            | P0   | 5h   | ☐      |
| 6.5C.4  | E2E Fluxo 3 — Config round-trip (criar membro → export JSON)        | P0   | 3h   | ☐      |
| 6.5C.5  | E2E Fluxo 4 — Vault + Unlock                                        | P1   | 3h   | ☐      |
| 6.5C.6  | E2E Fluxo 5 — Drill-down Dashboard → Transactions                   | P1   | 3h   | ☐      |
| 6.5C.7  | E2E Fluxo 6 — Dark mode persistência                                | P0   | 2h   | ☐      |
| 6.5C.8  | E2E Fluxo 7 — Error handling e auth redirect                        | P0   | 2h   | ☐      |
| 6.5C.9  | E2E Fluxo 8 — Notifications (bell + Sheet + mark read)              | P1   | 2h   | ☐      |
| 6.5C.10 | Smoke test checklist (`docs/SMOKE_TEST.md`, 30+ checks)             | P0   | 2h   | ☐      |
| 6.5C.11 | CI integration (GH Actions com PostgreSQL + Redis services)         | P0   | 3h   | ☐      |

**Checkpoint:** ~25-30 E2E tests green cobrindo 8 fluxos críticos. `docs/SMOKE_TEST.md` criado.

---

## F7 — Produção + LGPD

**Objetivo:** Produto no ar com segurança, CI/CD, LGPD.

**Duração estimada:** 6-8 semanas + 2 semanas dogfood.

### 7A — Docker + Deploy + HTTPS (semana 1-2)

| #     | Tarefa                                                                               | Prio | Est. | Status |
| ----- | ------------------------------------------------------------------------------------ | ---- | ---- | ------ |
| 7A.1  | Dockerfile backend (multi-stage, entrypoints api/worker, ~200MB, non-root)           | P0   | 4h   | ☐      |
| 7A.2  | Dockerfile frontend (multi-stage, Next.js standalone, ~100MB)                        | P0   | 3h   | ☐      |
| 7A.3  | `docker-compose.dev.yml` (PG + Redis + hot reload)                                   | P0   | 3h   | ☐      |
| 7A.4  | `docker-compose.prod.yml` (API + Worker + Frontend + PG + Redis + Traefik)           | P0   | 5h   | ☐      |
| 7A.5  | `.env.example` + env management + `scripts/gen-secrets.sh`                           | P0   | 2h   | ☐      |
| 7A.6  | VPS provisioning (Hetzner CX32, UFW, SSH keys, fail2ban, Docker)                     | P0   | 3h   | ☐      |
| 7A.7  | Traefik config (auto-SSL, HTTP→HTTPS, TLS 1.2+, WebSocket pass-through)              | P0   | 3h   | ☐      |
| 7A.8  | Domínio + DNS (A record, TTL curto)                                                  | P0   | 1h   | ☐      |
| 7A.9  | PostgreSQL prod (DB + user dedicado, Alembic upgrade, pool_size)                     | P0   | 3h   | ☐      |
| 7A.10 | Backup automático (pg_dump diário, rotação 7 dias, script restore testado)           | P0   | 3h   | ☐      |
| 7A.11 | Smoke test completo local (prod compose, health checks, SSL, login, upload)          | P0   | 3h   | ☐      |
| 7A.12 | Data migration plan (`scripts/seed-prod.sh`, procedimento import via API)            | P0   | 3h   | ☐      |
| 7A.13 | First deploy real → Produto no ar                                                    | P0   | 2h   | ☐      |

### 7B — Security Hardening + LGPD (semana 2-3)

| #     | Tarefa                                                                                               | Prio | Est. | Status |
| ----- | ---------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 7B.1  | Fernet expandido (CPFs + dados financeiros sensíveis + utility `encrypt_field()`/`decrypt_field()`)  | P0   | 6h   | ☐      |
| 7B.2  | Rate limiting (slowapi: auth 5/min, upload 10/min, pipeline 2/min, geral 100/min)                    | P0   | 3h   | ☐      |
| 7B.3  | Security headers (CORS restritivo, HSTS, CSP, X-Frame-Options, X-Content-Type-Options)               | P0   | 3h   | ☐      |
| 7B.4  | Session security (JWT 15min + refresh 7d httpOnly, rotation, revogação on password change, frontend interceptor) | P0 | 16h | ☐ |
| 7B.5  | Audit log (model `AuditEntry`, middleware para write ops, todas ações sensíveis)                     | P0   | 6h   | ☐      |
| 7B.6  | LGPD — Termos + Privacy (páginas `/terms` `/privacy`, aceite obrigatório, `accepted_at`)             | P0   | 4h   | ☐      |
| 7B.7  | LGPD — Exclusão (`DELETE /api/account`, cascade completo, confirmação dupla + audit)                 | P0   | 8h   | ☐      |
| 7B.8  | LGPD — Portabilidade (`GET /api/account/export`, ZIP com dados pessoais, download link temporário)   | P1   | 6h   | ☐      |
| 7B.9  | Storage cleanup (retention 90 dias, Celery periodic task, soft-delete)                               | P1   | 4h   | ☐      |
| 7B.10 | UX de produção (rate limit toast, LGPD delete stepper, export notification, maintenance page)        | P1   | 4h   | ☐      |

### 7C — CI/CD + Observabilidade (semana 3-4)

| #    | Tarefa                                                                                         | Prio | Est. | Status |
| ---- | ---------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 7C.1 | GH Actions CI (lint ruff + pytest + PG service + Docker scan CVE + coverage ≥95% new code)    | P0   | 6h   | ☐      |
| 7C.2 | GH Actions CD (push GHCR + SSH deploy + `alembic upgrade head` + compose pull + health check) | P0   | 4h   | ☐      |
| 7C.3 | Rollback automatizado (health check 3x fail → `.env.rollback`, `scripts/rollback.sh`)          | P0   | 3h   | ☐      |
| 7C.4 | Sentry setup (backend + frontend, DSN, environment tags, release tracking, perf 10%)           | P1   | 4h   | ☐      |
| 7C.5 | Structured logging (structlog JSON prod, request_id UUID, Celery task_id correlation)          | P1   | 4h   | ☐      |
| 7C.6 | Uptime monitoring (UptimeRobot, /health + frontend, email alerts)                              | P1   | 1h   | ☐      |
| 7C.7 | Runbook (`docs/RUNBOOK.md` — deploy, rollback, backup, secret rotation, scaling, first week)   | P1   | 5h   | ☐      |

### 7D — Quality Gate + Launch Readiness (semana 4-6 + 2 sem dogfood)

| #     | Tarefa                                                                                           | Prio | Est. | Status |
| ----- | ------------------------------------------------------------------------------------------------ | ---- | ---- | ------ |
| 7D.1  | Gap-fill unit tests (E0, E2/banks, E3, E4, E7 edge cases)                                       | P0   | 10h  | ☐      |
| 7D.2  | Gap-fill unit tests (E5, E5N, E6 — scripts maiores)                                             | P1   | 12h  | ☐      |
| 7D.3  | Gap-fill API endpoints + services (error paths, DB/Redis down, auth edge, concurrency)           | P0   | 8h   | ☐      |
| 7D.4  | CI integra frontend tests (Vitest + Playwright da F6.5) no pipeline de deploy                    | P0   | 1h   | ☐      |
| 7D.5  | Frontend E2E com PostgreSQL prod DB (ajustar fixtures)                                           | P1   | 2h   | ☐      |
| 7D.6  | Testes de UX de produção (rate limit toast, LGPD delete, export notification, maintenance)      | P1   | 3h   | ☐      |
| 7D.7  | Performance baseline (`time` pipeline E2E, p50/p95 API endpoints, `docs/PERFORMANCE_BASELINE.md`)| P1   | 3h   | ☐      |
| 7D.8  | Coverage integration (CI gate, Codecov, badge README, target ≥85% line / ≥75% branch)           | P0   | 3h   | ☐      |
| 7D.9  | Telemetria básica (tabela `UsageMetric`, privacy-first, dashboard query simples)                 | P1   | 4h   | ☐      |
| 7D.10 | Pre-launch checklist (smoke test prod, backup restore, rollback test, SSL Labs grade A)          | P0   | 3h   | ☐      |
| 7D.11 | **Dogfood period** (2+ semanas uso real, 5+ pipeline runs, zero critical bugs)                   | P0   | —    | ☐      |

---

## F8 — Growth (Futuro)

Adiados conscientemente. São features de aquisição/marketing/polish pós-launch.

| Item                                              | Justificativa para adiar                                |
| ------------------------------------------------- | ------------------------------------------------------- |
| Landing page (hero, features, pricing, CTA)       | Prematuro: zero usuários externos no dogfood            |
| Onboarding wizard + guided tour                   | Sem user research para validar fluxo                    |
| PWA (manifest, service worker, offline, install)  | Implicações de security com dados financeiros           |
| Command palette (Cmd+K, cmdk)                     | Power-user feature, não essencial                       |
| Framer Motion / page transitions                  | Polish sem valor funcional                              |
| SEO / Open Graph / sitemap / robots.txt           | Sem landing page, sem SEO relevante                     |
| Keyboard shortcuts (G+D, G+R)                     | Depende de command palette                              |
| FAQ / documentation page                          | Conteúdo emerge do feedback de beta                     |
| Report comparison (side-by-side, deltas)          | Requer 2+ relatórios (demora meses no dogfood)          |
| Shareable report link (token + TTL)               | Security complexa para dados financeiros públicos       |
| Bulk transaction actions (batch recategorize)     | Category override individual suficiente                 |
| Email digest notifications                        | Feature de engagement, requer email service + templates |
| Demo mode (dados fictícios)                       | Feature de aquisição, não infra                         |
| Billing real (Stripe)                             | BYOK resolve tier. Billing é projeto próprio            |
| Screen reader testing (VoiceOver/NVDA)            | Testing dedicado após beta users                        |
| Performance audit (Lighthouse >90)                | Relevante para produção pública, não dogfood            |
| Multi-idioma (i18n)                               | pt-BR por default. i18n é esforço grande                |
| Collaborative features (share, comments)          | Multi-user por workspace é projeto separado             |
| Dashboard widgets customizáveis (drag-and-drop)   | Over-engineering                                        |

---

## Como trabalhar com o backlog

1. **Uma fase por vez.** F6.5 precisa terminar antes de começar F7.
2. **P0 antes de P1.** Dentro da fase, priorizar por dependência e risco.
3. **Atualizar status aqui.** Ao concluir uma task, marcar ✅ e mover contexto relevante para [CHANGELOG.md](CHANGELOG.md).
4. **Decisões técnicas importantes** → [DECISIONS.md](DECISIONS.md).
5. **Mudanças de escopo/visão** → atualizar [ROADMAP.md](ROADMAP.md) e discutir antes de executar.
