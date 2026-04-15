# Fin — Roadmap

> Visão de alto nível das fases do projeto. Atualizar mensalmente ou ao mudar de fase.
>
> **Última atualização:** 2026-04-15
> **Fase atual:** F6 completa • próxima: F6.5 (Frontend Testing) → F7 (Produção)

---

## Visão geral das fases

| Fase    | Nome                     | Status       | Entrega principal                                                                              |
| ------- | ------------------------ | ------------ | ---------------------------------------------------------------------------------------------- |
| **0**   | Desacoplar Core          | ✅ Concluída  | Pipeline como package Python importável + contexto injetável                                   |
| **1**   | Backend API + Auth       | ✅ Concluída  | Login/registro + API de relatórios + Frontend MVP                                              |
| **2**   | Upload + Pipeline Web    | ✅ Concluída  | Upload + unlock/classify auto + pipeline pseudo-async                                          |
| **3**   | Configuração via UI      | ✅ Concluída  | Config editável via UI + materialização + import/export JSON                                   |
| **4**   | Automação LLM            | ✅ Concluída  | LiteLLM+Instructor, BYOK, Premium E2E, review manual, tier                                     |
| **4.5** | Design System Foundation | ✅ Concluída  | Tailwind v4 @theme, Geist fonts, shadcn/ui, 7 compostos financeiros                            |
| **5**   | Task Queue + Async       | ✅ Concluída  | Celery+Redis, WS+polling, cancel stage-boundary, concurrency                                   |
| **6**   | Frontend Profissional    | ✅ Concluída  | Dashboard, Transaction Explorer, Report React, Dark mode, Notifications                        |
| **6.5** | Frontend Testing & QA + Backend Hardening | ☐ Planejada | Vitest + RTL + MSW + Playwright. ~240 tests + hardening fintech (a11y, visual reg., resilience) + backend round-trip serializers (anti-BUG-015) + frontend não-funcional (error boundary, CWV) |
| **7**   | Produção + LGPD + Ops    | ☐ Planejada  | VPS+Docker+Traefik, LGPD completo, auth flows (email verify/pwd reset/brute-force), prompt injection defense, operational readiness (DR testado, business metrics, incident comms, LLM cost cap), CI/CD, dogfood validado |

---

## Status detalhado por fase

### F0-F6 — Concluídas ✅

Resumo do que foi entregue em cada uma:

| Fase | Tasks | Duração real | Testes adicionados |
| ---- | ----- | ------------ | ------------------ |
| F0   | 27    | 3-4 semanas  | +136 (pipeline)    |
| F1   | 16    | ~1 dia       | +13 (backend)      |
| F2   | 38    | ~4 semanas   | +~100              |
| F3   | 32    | ~4 semanas   | +~90               |
| F4   | 34    | ~4 semanas   | +132 (LLM)         |
| F4.5 | 27    | 2 semanas    | 0 (só frontend)    |
| F5   | 23    | ~3 semanas   | +44                |
| F6   | 48    | ~6 semanas   | 0 (testes em F6.5) |

Para detalhes do que foi entregue, ver **[CHANGELOG.md](CHANGELOG.md)**.

Para tasks específicas já feitas e ainda pendentes por sub-fase, ver **[BACKLOG.md](BACKLOG.md)**.

---

### F6.5 — Frontend Testing & QA + Backend Hardening (próxima)

**Objetivo:** Rede de segurança de testes no frontend antes de ir para produção, mais blindagem da fronteira backend (DB → pipeline) que demonstrou ser frágil (BUG-015). A Fase 6 entregou features; a 6.5 entrega confiança end-to-end.

**Duração estimada:** 3 semanas (5 sub-fases)

**Escopo:**
- ~50-60 unit tests (format.ts, export.ts, api.ts, utils.ts, usePipelineWS hook)
- ~120-150 integration tests (10 pages + AppShell + 7 compostos, loading/empty/error/success)
- ~25-30 E2E tests (Golden Path + 8 fluxos críticos, Playwright com backend real)
- **Hardening fintech frontend (6.5D):** axe-core, property-based em formatadores BRL, visual regression, cross-browser (Firefox + WebKit), resilience (WS reconnect, polling fallback, offline, 5xx), security smoke (XSS, JWT expiry, logout cleanup), fixtures sintéticas auditadas, **error boundary audit, empty state CTA audit, focus management, Core Web Vitals baseline**
- **Backend hardening (6.5E):** round-trip tests para os 6 serializers do `config_materializer` (anti-BUG-015), golden file pipeline com PDFs sintéticos, alembic CI guardrails (drift + idempotency + dry-run preview), fix cwd-sensitivity em alembic.ini, test anti-regressão BUG-015, systemic fix para fallback-leak class
- Smoke test checklist (`docs/SMOKE_TEST.md`)
- CI integration (Vitest + Playwright gates)

**Critérios de aceite:**
- `npm test` <30s (unit + integration)
- Coverage lib/ ≥80%, pages/ ≥70%
- E2E green com backend real (CORS, auth, WebSocket testados)
- **axe-core: 0 violations critical/serious** em todas as pages e fluxos E2E
- **Visual regression: zero diffs não-aprovados** (charts, KPIs, dark/light, print, mobile)
- **Cross-browser:** 3 fluxos críticos green em Chromium + Firefox + WebKit
- **Lint anti-vazamento de PII em fixtures:** green (CPFs gerados por mod-11, sem nomes/dados reais)
- **6 serializers com round-trip green** • golden pipeline test verde com PDFs sintéticos
- **CI falha em migration drift/non-idempotent**
- **Todas as pages com error boundary** • empty states com CTA • focus management validado • CWV baseline registrado
- Gate de CI bloqueia merge/deploy se algum nível falha

**Por que entre F6 e F7 (e não dentro da F7):** Separar garante que testes e hardening são pré-requisito do deploy, não afterthought. Bugs descobertos em dev custam 10x menos que em produção. Sub-fases 6.5D e 6.5E blindadas em escopo próprio para não serem cortadas sob pressão de P0.

Detalhes das tasks: **[BACKLOG.md#f65](BACKLOG.md#f65--frontend-testing--qa)** • Decisões: **[ADR-063](DECISIONS.md#adr-063--hardening-fintech-em-sub-fase-65d)** • **[ADR-064](DECISIONS.md#adr-064--backend-hardening-em-sub-fase-65e)**

---

### F7 — Produção + Security + LGPD + Operational Readiness

**Objetivo:** Levar o Fin a produção com a menor superfície de risco possível, fluxos de auth completos para suportar usuários reais, e maturidade operacional para sobreviver ao primeiro incidente.

**Duração estimada:** 8-10 semanas (5 sub-fases + 2 semanas de dogfood validado)

**Sub-fases:**

| Sub-fase | Foco                                                                                                                                                              | Duração    |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| 7A       | Docker + Deploy + HTTPS (VPS, Traefik, Let's Encrypt)                                                                                                             | 1-2 sem    |
| 7B       | Security + LGPD + Auth (Fernet expandido, rate limit, JWT refresh, audit, termos versionados, **email verification, password reset, brute-force lockout, prompt injection defense, soft-delete, DSAR**) | 3-4 sem    |
| 7C       | CI/CD + Observabilidade (GH Actions, Sentry, logs, uptime)                                                                                                        | 1-2 sem    |
| 7D       | Quality Gate + Launch Readiness (gap-fill, baseline perf, checklist)                                                                                              | 2-3 sem    |
| 7E       | **Operational Readiness** (stuck-run detector, restore drill, off-site backup, FERNET recovery, status page, business metrics, SLOs, incident comms templates, support runbook, LLM cost cap, API key validation, fallback model) | ~2 sem     |
| Dogfood  | 2+ semanas de uso real antes de beta                                                                                                                              | 2+ sem     |

**Deploy target:** VPS Hetzner CX32 (4 vCPU, 8GB, ~$8/mo) + Docker Compose + PostgreSQL + Traefik. Backup off-site em S3 BR ou Backblaze B2.

**Progressão pós-F7:**

| Estágio     | Quem                                  | Gate de passagem                                                                    |
| ----------- | ------------------------------------- | ----------------------------------------------------------------------------------- |
| **Dogfood** | founder                               | Zero pipeline failures em 5 runs consecutivos. Uptime >99%. Zero critical bugs      |
| **Beta**    | Família + 2-3 convidados (5 users)    | Onboarding sem suporte. Latência p95 <1s. Nenhum dado corrompido. LGPD verificado   |
| **GA**      | Público                               | Landing page + demo mode + billing (se aplicável). Suporte básico                   |

Detalhes das tasks: **[BACKLOG.md#f7](BACKLOG.md#f7--produção--lgpd)**

---

### F8 — Growth & Aquisição (pós-launch, Futuro)

Adiado conscientemente: são features de aquisição/marketing que não fazem sentido no estágio dogfood/beta. Incluídas para referência futura.

- Landing page + onboarding wizard + guided tour
- PWA (service worker, install, offline seguro)
- Command palette (Cmd+K)
- SEO / Open Graph / sitemap
- Email digest notifications
- Demo mode (workspace fictício read-only)
- Billing real (Stripe)
- Keyboard shortcuts
- Report comparison (side-by-side)

---

## Métricas de sucesso por fase

Política de cobertura (Python backend + pipeline):

| Fase     | Meta line | Meta branch | Foco                                                                         |
| -------- | --------- | ----------- | ---------------------------------------------------------------------------- |
| F0       | ~30%      | —           | ✅ Regressão golden files                                                     |
| F1       | ~40%      | —           | ✅ Auth endpoints, JWT                                                        |
| F2       | ~55%      | ~40%        | ✅ Upload, vault, pipeline execution. **CI gate ativado**                    |
| F3       | ~65%      | ~50%        | ✅ CRUD config, materialização                                               |
| F4       | ~75%      | ~60%        | ✅ LLM service (mocks), validators, retry, tier detection                    |
| F4.5     | ~75%      | ~60%        | Frontend-only. Zero Python novo                                              |
| F5       | ~85%      | ~70%        | ✅ Task queue, async execution, WebSocket, cancelamento                      |
| F6       | ~90%      | ~80%        | Edge cases restantes, error paths                                            |
| F6.5     | ~90%      | ~80%        | **Frontend:** ~240 tests. lib/ ≥80%, pages/ ≥70%                             |
| F7       | **≥95%**  | **≥85%**    | Gap-fill scripts legados + CI coverage gate                                  |

---

## Riscos e mitigações

| #   | Risco                                          | Impacto   | Probab.         | Status    | Mitigação                                                                                 |
| --- | ---------------------------------------------- | --------- | --------------- | --------- | ----------------------------------------------------------------------------------------- |
| R1  | Refactoring quebra pipeline                    | Alto      | ~~Média~~ Baixa | ✅ Mitigado | 136 tests + `_init_config()` pattern                                                      |
| R2  | LLM output inconsistente                       | Alto      | ~~Alta~~ Média  | ✅ Parcial  | Instructor + Pydantic + validators + needs_review workflow (F4)                            |
| R3  | Custo de LLM por run inviável                  | Médio     | Baixa           | ✅ Mitigado | BYOK (F4). Token tracking + cost estimation                                               |
| R4  | Dados sensíveis vazam                          | Crítico   | Baixa           | ⏳ F7       | Fernet at-rest (parcial). HTTPS + audit log + LGPD em F7                                  |
| R5  | Parsers quebram com mudança de layout          | Alto      | Alta            | ⚠️ Ativo   | Testes golden files. Alertas de parsing error. LLM fallback (E2-llm) em F4                |
| R6  | Escopo cresce demais                           | Alto      | Alta            | ⚠️ Ativo   | P0 por sprint. Cortar P2. Itens de F8 adiados explicitamente                              |
| R7  | Complexidade E5/E6 dificulta refactoring       | Médio     | Alta            | ✅ Mitigado | "Wrap, Don't Rewrite" strategy. Lógica interna inalterada                                 |
| R8  | FERNET_KEY perdida entre restarts              | Alto      | Resolvido       | ✅ Mitigado | Persistência em `.env`. Procedimento documentado em SETUP.md                              |
| R9  | Dogfood reta para beta sem bugs bloqueantes    | Médio     | Média           | ⏳ F7       | 2+ semanas de dogfood obrigatórias. 5+ pipeline runs 100% success                         |
| R10 | Serializers DB→pipeline perdem campos silenciosamente (BUG-015 class) | Alto | ~~Alta~~ Média | 🚧 F6.5E | Round-trip tests para 6 serializers + golden file pipeline + test anti-regressão BUG-015 |
| R11 | Migration aplicada em DB errada por cwd ambíguo | Alto    | Média           | 🚧 F6.5E   | Caminho absoluto em alembic.ini + guard no env.py + documentação em SETUP.md              |
| R12 | LLM BYOK consome budget do user descontroladamente | Médio  | Alta            | ⏳ F7E      | Cost cap mensal por workspace + toast 80%/95% + hard stop 100%                            |
| R13 | Pipeline run "running" para sempre (worker morto) | Médio  | Média           | ⏳ F7E      | Heartbeat + Celery beat detector marca como failed >1h sem heartbeat                       |
| R14 | Prompt injection em PDF malicioso vaza dados via LLM | Alto | Baixa-Média    | ⏳ F7B      | Sanitização texto extraído + allowlist output + fixture PDF adversarial                   |
| R15 | FERNET_KEY perdida em prod = todos os secrets ilegíveis | Crítico | Baixa         | ⏳ F7E      | Backup criptografado off-site (1Password vault) + procedure testado em staging            |
| R16 | Backup Hetzner perdido junto com DC (incêndio/falha) | Crítico | Muito baixa    | ⏳ F7E      | Off-site backup S3/B2 BR + restore drill quarterly                                        |
| R17 | GA bloqueado por falta de email verify/password reset | Alto | Certa          | ⏳ F7B      | Auth flows completos em 7B.11-13 antes do Beta abrir                                       |

---

## Timeline geral estimada

| Período              | Milestone                                        |
| -------------------- | ------------------------------------------------ |
| Q1 2026              | F0-F4 ✅ (Core → LLM)                            |
| Q2 2026 (Abr-Jun)    | F4.5, F5, F6 ✅ • F6.5 (3 sem, com 6.5D + 6.5E) em andamento     |
| Q3 2026              | F7 (8-10 sem, com 7E) → Dogfood validado → Beta fechado          |
| Q4 2026              | Beta → preparação GA (F8)                        |
| 2027+                | GA + features de growth                          |

---

## Como priorizamos

- **P0** — Bloqueante. Sem isso a fase não entrega valor.
- **P1** — Importante. Sem isso funciona, mas falta qualidade/completude.
- **P2** — Nice-to-have. Pode postergar para próxima fase ou sprint.

Ver [BACKLOG.md](BACKLOG.md) para priorização detalhada por task.
