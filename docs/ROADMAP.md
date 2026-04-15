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
| **6.5** | Frontend Testing & QA    | ☐ Planejada  | Vitest + RTL + MSW + Playwright. ~240 tests + hardening fintech (a11y, visual reg., resilience). CI gates. Smoke checklist |
| **7**   | Produção + LGPD          | ☐ Planejada  | VPS+Docker+Traefik, LGPD, CI/CD, coverage gate, dogfood validado                               |

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

### F6.5 — Frontend Testing & QA (próxima)

**Objetivo:** Rede de segurança de testes no frontend antes de ir para produção. A Fase 6 entregou features; a 6.5 entrega confiança. Inclui hardening específico de fintech (a11y, visual regression, resilience, security smoke).

**Duração estimada:** 2.5 semanas (4 sub-fases)

**Escopo:**
- ~50-60 unit tests (format.ts, export.ts, api.ts, utils.ts, usePipelineWS hook)
- ~120-150 integration tests (10 pages + AppShell + 7 compostos, loading/empty/error/success)
- ~25-30 E2E tests (8 fluxos críticos, Playwright com backend real)
- **Hardening fintech (6.5D):** axe-core, property-based em formatadores BRL, visual regression, cross-browser (Firefox + WebKit), resilience (WS reconnect, polling fallback, offline, 5xx), security smoke (XSS, JWT expiry, logout cleanup), fixtures sintéticas auditadas
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
- Gate de CI bloqueia merge/deploy se algum nível falha

**Por que entre F6 e F7 (e não dentro da F7):** Separar garante que testes são pré-requisito do deploy, não afterthought. Bugs descobertos em dev custam 10x menos que em produção. Hardening fintech (6.5D) blindado em sub-fase própria para não ser cortado sob pressão de P0.

Detalhes das tasks: **[BACKLOG.md#f65](BACKLOG.md#f65--frontend-testing--qa)** • Decisão: **[DECISIONS.md#adr-063](DECISIONS.md#adr-063--hardening-fintech-em-sub-fase-65d)**

---

### F7 — Produção + Security + LGPD

**Objetivo:** Levar o Fin a produção com a menor superfície de risco possível.

**Duração estimada:** 6-8 semanas (4 sub-fases + 2 semanas de dogfood validado)

**Sub-fases:**

| Sub-fase | Foco                                                      | Duração    |
| -------- | --------------------------------------------------------- | ---------- |
| 7A       | Docker + Deploy + HTTPS (VPS, Traefik, Let's Encrypt)     | 1-2 sem    |
| 7B       | Security Hardening + LGPD (Fernet expandido, rate limit, JWT refresh, audit, termos) | 2-3 sem |
| 7C       | CI/CD + Observabilidade (GH Actions, Sentry, logs, uptime)| 1-2 sem    |
| 7D       | Quality Gate + Launch Readiness (gap-fill, baseline perf, checklist) | 2-3 sem |
| Dogfood  | 2+ semanas de uso real antes de beta                      | 2+ sem     |

**Deploy target:** VPS Hetzner CX32 (4 vCPU, 8GB, ~$8/mo) + Docker Compose + PostgreSQL + Traefik.

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

---

## Timeline geral estimada

| Período              | Milestone                                        |
| -------------------- | ------------------------------------------------ |
| Q1 2026              | F0-F4 ✅ (Core → LLM)                            |
| Q2 2026 (Abr-Jun)    | F4.5, F5, F6 ✅ • F6.5 + F7 em andamento         |
| Q3 2026              | F7 completa → Dogfood validado → Beta fechado    |
| Q4 2026              | Beta → preparação GA (F8)                        |
| 2027+                | GA + features de growth                          |

---

## Como priorizamos

- **P0** — Bloqueante. Sem isso a fase não entrega valor.
- **P1** — Importante. Sem isso funciona, mas falta qualidade/completude.
- **P2** — Nice-to-have. Pode postergar para próxima fase ou sprint.

Ver [BACKLOG.md](BACKLOG.md) para priorização detalhada por task.
