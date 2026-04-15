# Fin — Architecture Decision Records (ADRs)

> Histórico de decisões técnicas com contexto, alternativas e consequências.
>
> **Quando adicionar uma ADR:** toda vez que uma decisão não-trivial é tomada (escolha de tecnologia, padrão arquitetural, trade-off). ADRs são imutáveis — se uma decisão muda, adicione uma nova ADR que a substitua (ref: "Supersedes ADR-NNN").

---

## Índice por categoria

**Fundação:**
[D1](#adr-001--sqlalchemy-20-como-orm) [D2](#adr-002--filesystem-local-para-storage) [D3](#adr-003--jwt-custom-para-auth) [D5](#adr-005--vps-hetzner-para-produção) [D6](#adr-006--monorepo) [D13](#adr-013--wrap-dont-rewrite-pattern)

**Persistência:**
[D39](#adr-039--dual-db-sqlite-dev--postgresql-prod) [D29-DB](#adr-029--alembic-para-migrations) [D38](#adr-038--docker-volume-para-storage-prod)

**Pipeline:**
[D14](#adr-014--threading-para-execução-background) [D15](#adr-015--vault-por-workspace) [D16](#adr-016--e0-route-automático-no-upload) [D17](#adr-017--sync-session-em-background-threads) [D18](#adr-018--config-dir-override-em-fortenant) [D19](#adr-019--storage-root-via-env-var) [D30](#adr-030--cancelamento-cooperativo-via-event)

**Config:**
[D20](#adr-020--materializar-config-em-disco) [D21](#adr-021--5-configs-editáveis) [D22](#adr-022--fallback-seletivo-de-config) [D23](#adr-023--importexport-json-de-config)

**LLM:**
[D24](#adr-024--litellm-como-proxy-universal) [D25](#adr-025--byok-bring-your-own-key) [D26](#adr-026--instructor--pydantic-para-structured-output) [D27](#adr-027--retry-→-needsreview-em-falha-de-validação) [D28](#adr-028--e7-full-scope-na-fase-4)

**Task Queue:**
[D29-TQ](#adr-029tq--celery--redis) [D30-WS](#adr-030ws--websocket--polling-fallback) [D31](#adr-031--redis-para-queue--pubsub) [D32](#adr-032--cancel-stage-boundary)

**Frontend:**
[D33](#adr-033--react-components-para-report) [D34](#adr-034--dashboard-completo-com-alertas) [D35](#adr-035--media-print-para-pdf-export) [D37](#adr-037--recharts-para-charts) [D42](#adr-042--design-system-antes-da-fase-5) [D43](#adr-043--shadcnui-como-component-library) [D50](#adr-050--tailwind-v4-theme-inline) [D51](#adr-051--geist-fonts) [D52](#adr-052--lucide-react-para-ícones) [D53](#adr-053--intl-nativo-para-datas) [D54](#adr-054--migração-incremental-de-pages)

**Produto:**
[D44](#adr-044--transaction-explorer-como-core) [D45](#adr-045--data-lineage-via-tooltip) [D46](#adr-046--responsivo-sem-pwa-obrigatório) [D47](#adr-047--category-override-em-vez-de-reconciliação-ui)

**Produção:**
[D7](#adr-007--fernet-app-level-para-criptografia) [D40](#adr-040--billing-adiado-para-pós-launch) [D41](#adr-041--traefik-como-reverse-proxy) [D55](#adr-055--coverage-target--85-line--95-new-code) [D56](#adr-056--rolling-restart-em-vez-de-blue-green) [D57](#adr-057--jwt-15min--refresh-7d) [D58](#adr-058--vps-cx32-para-sizing) [D59](#adr-059--docker-image-cve-scan-no-ci) [D60](#adr-060--fernet-dual-key-para-secret-rotation) [D61](#adr-061--telemetria-privacy-first)

**Testing:**
[D62](#adr-062--frontend-testing-em-fase-dedicada-65) [D63](#adr-063--hardening-fintech-em-sub-fase-65d) [D64](#adr-064--backend-hardening-em-sub-fase-65e) [D67](#adr-067--test-infrastructure-em-sub-fase-65f) [D69](#adr-069--msw-sync-strategy-manual--lint-ci-não-codegen) [D70](#adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in) [D71](#adr-071--playwright-workspace-isolation-email-unique-por-worker)

**Operations:**
[D65](#adr-065--sub-fase-7e-operational-readiness) [D66](#adr-066--auth-flows-completos-e-prompt-injection-em-7b-bloqueadores-de-beta)

**UX/Linguagem:**
[D68](#adr-068--códigos-internos-do-pipeline-nunca-vazam-na-ui)

**Multi-tenancy (F8):**
[D72](#adr-072--multi-tenancy-workspace_id-scoping-explícito--workspacemember-para-multi-família)

**Goals & Tasks (F8):**
[D73](#adr-073--goals-como-entidade-versionada-não-config-estático) [D74](#adr-074--tasks-como-entidade-de-1ª-classe-fora-do-relatório) [D75](#adr-075--cutover-cli--web-estratégia-de-transição-faseada-com-adapters)

**Design System (F9):**
[D76](#adr-076--design-tokens-unificados-site--relatório)

---

## ADR-001 — SQLAlchemy 2.0 como ORM

**Status:** Decidido (F1) • **Data:** 2026-04-13

**Contexto:** Precisamos de ORM async-compatible para FastAPI. Opções: SQLAlchemy 2.0, Tortoise ORM, SQL raw.

**Decisão:** SQLAlchemy 2.0 com async engine + Alembic para migrations.

**Consequências:**
- ✅ Maduro, grande ecossistema
- ✅ Async nativo (`AsyncSession`)
- ✅ Abstrai SQLite (dev) ↔ PostgreSQL (prod)
- ⚠️ Curva de aprendizado mais alta que Tortoise
- ⚠️ Precisa de `greenlet` + cuidados com `flush()` manual em async

---

## ADR-002 — Filesystem local para storage

**Status:** Decidido (F2) • **Data:** 2026-04-13

**Contexto:** Onde armazenar documentos uploaded e outputs do pipeline?

**Decisão:** Filesystem local por tenant. S3/MinIO só na F7 se necessário.

**Consequências:**
- ✅ Simples. Backup via pg_dump + volume snapshot (F7)
- ✅ Zero dependências externas no MVP
- ❌ Não escala horizontalmente (um VPS)
- ❌ Backup é manual/cron

---

## ADR-003 — JWT custom para auth

**Status:** Decidido (F1) • **Data:** 2026-04-13

**Contexto:** Auth provider? Custom JWT, Auth.js, Clerk, Auth0?

**Decisão:** Custom JWT (`python-jose` + `bcrypt`).

**Consequências:**
- ✅ Sem vendor lock-in
- ✅ Zero custo
- ⚠️ Nós somos responsáveis por segurança (hashing, rotation)
- Nota: bcrypt 4.x direto, sem passlib (passlib quebra com bcrypt 4.x API)

---

## ADR-005 — VPS Hetzner para produção

**Status:** Decidido (F7) • **Data:** 2026-04-14

**Contexto:** Onde hospedar em produção? VPS, Railway, Fly.io, AWS?

**Decisão:** Hetzner CX32 (4 vCPU, 8GB, ~$8/mo) + Docker Compose.

**Consequências:**
- ✅ Custo baixo (~$10/mo total incluindo domínio)
- ✅ Controle total do stack
- ✅ Upgradeable para Railway/Fly.io se virar SaaS
- ⚠️ Nós gerenciamos OS updates, security patches

Ver [D58](#adr-058--vps-cx32-para-sizing) para sizing rationale.

---

## ADR-006 — Monorepo

**Status:** Decidido (F0) • **Data:** 2026-04-12

**Decisão:** Monorepo único com backend/, frontend/, pipeline/, scripts/.

**Consequências:**
- ✅ Refactoring cross-layer fica fácil (modelo Python + schema TS)
- ✅ CI único
- ⚠️ Repos gigantes escalam pior

---

## ADR-013 — "Wrap, Don't Rewrite" pattern

**Status:** Decidido (F0) • **Data:** 2026-04-12

**Contexto:** Scripts legados (E5=107KB, E6=197KB) têm lógica refinada de domínio. Reescrever é arriscado e demorado.

**Decisão:** Cada script ganha `_init_config(base_dir)` + `main(root_dir=None)`. Wrappers finos em `pipeline/stages/` (3-15 linhas).

**Consequências:**
- ✅ CLI continua funcionando idêntico
- ✅ Thread-safe (cada call re-inicializa seus globals)
- ✅ Multi-tenant via `root_dir` injection
- ✅ Testável com `main(root_dir=tmp_dir)`
- ⚠️ Globals patteren persiste (código legado não idiomático)

Alternativa descartada: injetar config via dict. Exigiria refatorar `_init_config` em todos os scripts.

---

## ADR-014 — Threading para execução background

**Status:** Decidido (F2) → Substituído por Celery em [D29-TQ](#adr-029tq--celery--redis)

**Decisão original:** `threading.Thread` daemon para pipeline execution.

**Por que foi substituído:** Threads não sobrevivem a restart do servidor. Celery resolve isso + permite workers múltiplos.

**Fallback:** Celery mantém thread fallback se Redis indisponível.

---

## ADR-015 — Vault por workspace

**Status:** Decidido (F2)

**Decisão:** Senhas de PDF são armazenadas em um vault por workspace, encriptadas com Fernet. Tentadas automaticamente no upload.

---

## ADR-016 — E0-route automático no upload

**Status:** Decidido (F2)

**Decisão:** Ao uploadar, o documento é automaticamente classificado (banco, tipo, período) via regex do E0-route. Sem intervenção manual.

**Extensão (2026-04-15):** Documento também é copiado de `inbox/` para `data/{dest_group}/` imediatamente, para que o pipeline encontre os arquivos depois.

---

## ADR-017 — Sync session em background threads

**Status:** Decidido (F2)

**Decisão:** Pipeline é 100% código sync. Usar `SessionLocal` (sync) em threads/tasks de background. AsyncSession requer event loop complexo.

---

## ADR-018 — `config_dir` override em `for_tenant()`

**Status:** Decidido (F2)

**Decisão:** `WorkspaceContext.for_tenant()` aceita `config_dir` apontando para `config/` global ou para tenant-specific. Na F3, passa a apontar para tenant config materializada.

---

## ADR-019 — `STORAGE_ROOT` via env var

**Status:** Decidido (F2)

**Decisão:** `Settings.STORAGE_ROOT` configurável via `FIN_STORAGE_ROOT`. Default `./storage/`. No `.gitignore`.

---

## ADR-020 — Materializar config em disco

**Status:** Decidido (F3)

**Contexto:** Scripts usam `_init_config(base_dir)` que lê de `base_dir/config/`. Como injetar config do DB sem reescrever 12+ scripts?

**Decisão:** `materialize_config()` copia `config/` global para `tenant/config/`, depois sobrescreve apenas os configs editados no DB.

**Consequências:**
- ✅ Zero mudança nos scripts legados
- ✅ Fallback automático (configs não editados lêem do global)
- ⚠️ ~500KB de I/O por run (negligível)

---

## ADR-021 — 5 configs editáveis

**Status:** Decidido (F3)

**Decisão:** `family_members`, `categorization`, `pipeline`, `institutions`, `report_layout`. Templates HTML e schemas ficam estáticos.

---

## ADR-022 — Fallback seletivo de config

**Status:** Decidido (F3)

**Decisão:** GET retorna defaults do disco se DB vazio. Save vai só para DB. Configs não editados continuam lendo do global (fallback).

**Nota crítica:** Fallback de `family_members` **nunca** expõe CPFs reais (retorna `cpf=None`). Ver bug fix 2026-04-14.

---

## ADR-023 — Import/export JSON de config

**Status:** Decidido (F3)

**Decisão:** Ambos. Upload JSON → DB. Download DB → JSON. Facilita migração do CLI e backup.

---

## ADR-024 — LiteLLM como proxy universal

**Status:** Decidido (F4)

**Decisão:** LiteLLM como camada de abstração para 100+ LLM providers.

**Consequências:**
- ✅ Anthropic, OpenAI, Ollama local, etc. via mesma interface
- ✅ User escolhe provedor (BYOK)
- ⚠️ Dependência adicional

---

## ADR-025 — BYOK (Bring Your Own Key)

**Status:** Decidido (F4) — **Estratégica**

**Decisão:** User fornece sua própria API key. Zero custo para plataforma.

**Consequências:**
- ✅ Modelo de negócio viável sem billing
- ✅ User controla custos e provedor
- ❌ Onboarding fricciona (user precisa criar conta no provedor)
- ❌ Plataforma não lucra direto com uso do LLM

---

## ADR-026 — Instructor + Pydantic para structured output

**Status:** Decidido (F4)

**Decisão:** Instructor enforça output Pydantic no LLM com auto-retry em validation failure.

**Consequências:**
- ✅ Menos código custom de parsing
- ✅ Retry automático com erros de validação no prompt
- ✅ Pydantic v2 nativo

---

## ADR-027 — Retry → needs_review em falha de validação

**Status:** Decidido (F4)

**Decisão:** Se 3 retries falham validação, stage entra em `needs_review`. User edita JSON via API, depois faz resume do pipeline.

**Consequências:**
- ✅ Nenhum dado perdido
- ✅ User tem controle em edge cases
- ⚠️ Interface de review é complexa (JSON editor)

---

## ADR-028 — E7 full scope na Fase 4

**Status:** Decidido (F4)

**Decisão:** E7 completo (review LLM + apply determinístico + E6-final). Pipeline 100% E2E na F4.

---

## ADR-029 — Alembic para migrations

**Status:** Decidido (F2)

**Decisão:** Alembic com async engine. Migration inicial cobre todas as tabelas.

---

## ADR-029-TQ — Celery + Redis

**Status:** Decidido (F5)

**Contexto:** Precisamos de task queue para pipeline assíncrono. Opções: Celery, ARQ, Dramatiq.

**Decisão:** Celery + Redis.

**Consequências:**
- ✅ Sync-native (pipeline é sync)
- ✅ Maduro, grande ecossistema
- ✅ Flower dashboard (se necessário)
- ⚠️ Mais pesado que ARQ

Alternativas descartadas:
- **ARQ:** async-native, mas pipeline é sync; sobrecarga de event loop
- **Dramatiq:** menos maduro, menor ecossistema

---

## ADR-030 — Cancelamento cooperativo via `threading.Event`

**Status:** Decidido (F2) → Substituído por [D32](#adr-032--cancel-stage-boundary)

**Decisão inicial:** Cooperative cancel via `threading.Event` entre stages.

**Evolução (F5):** Substituído por DB flag + Celery revoke. Mesmo princípio (stage-boundary).

---

## ADR-030-WS — WebSocket + polling fallback

**Status:** Decidido (F5)

**Decisão:** WebSocket principal com polling fallback automático (compat F2).

**Consequências:**
- ✅ Real-time em navegadores modernos
- ✅ Funciona atrás de proxies que bloqueiam WS
- ✅ Backward compatibility com polling

---

## ADR-031 — Redis para queue + pub/sub

**Status:** Decidido (F5)

**Decisão:** Redis serve como broker Celery, result backend e pub/sub (eventos WebSocket).

---

## ADR-032 — Cancel stage-boundary

**Status:** Decidido (F5)

**Decisão:** Cancel verificado entre stages (não mid-stage). Stages completos são preservados. Seguro, sem cleanup parcial.

---

## ADR-033 — React components para report

**Status:** Decidido (F6)

**Contexto:** Como renderizar o relatório no frontend? iframe (reaproveita E6), sanitized HTML, React components.

**Decisão:** React components a partir do E5 JSON.

**Consequências:**
- ✅ Máximo controle (interatividade, dark mode, responsivo)
- ✅ Drill-down para Transaction Explorer
- ⚠️ Validação rigorosa necessária (L1 data accuracy, L2 section completeness) para evitar divergência com E6 HTML
- **Status da implementação:** Hybrid — iframe HTML + React chrome (toolbar, navegação)

---

## ADR-034 — Dashboard completo com alertas

**Status:** Decidido (F6)

**Decisão:** KPIs + 4 charts + alertas inteligentes + filtros por período/membro. Não MVP de KPIs apenas.

---

## ADR-035 — `@media print` para PDF export

**Status:** Decidido (F6)

**Decisão:** PDF via `window.print()` + CSS `@media print`. Upgrade path → Playwright server-side se necessário.

**Consequências:**
- ✅ Zero custo, fiel ao browser
- ❌ Qualidade depende do browser do user

---

## ADR-037 — Recharts para charts

**Status:** Decidido (F6)

**Decisão:** Recharts (React-native, declarativo, Tailwind-compat).

Alternativas descartadas: Nivo (mais pesado), Tremor (menos flexível), Chart.js (imperativo).

---

## ADR-038 — Docker volume para storage prod

**Status:** Decidido (F7)

**Decisão:** Docker volume persistente. S3/MinIO adiado.

---

## ADR-039 — Dual DB: SQLite (dev) + PostgreSQL (prod)

**Status:** Decidido (F7)

**Decisão:** SQLite em dev (zero setup). PostgreSQL em prod. CI testa em PostgreSQL (mesmo DB que prod).

**Rationale:** Dual-test CI (SQLite + PG) dobra tempo de CI sem valor proporcional. SQLAlchemy abstrai ambos.

---

## ADR-040 — Billing adiado para pós-launch

**Status:** Decidido (F7)

**Decisão:** BYOK resolve tier sem billing. Stripe é projeto próprio, adiado para F8.

---

## ADR-041 — Traefik como reverse proxy

**Status:** Decidido (F7)

**Decisão:** Traefik v3 (Docker-native, auto-SSL via Let's Encrypt, labels-based routing).

Alternativas descartadas: nginx (config manual), Caddy (ecossistema menor).

---

## ADR-042 — Design system antes da Fase 5

**Status:** Decidido (F4.5)

**Contexto:** Quando fazer design system foundation? Antes de F5, no início de F6, ou gradualmente?

**Decisão:** F4.5 dedicada (2 semanas) antes de F5.

**Rationale:** Produtos financeiros exigem consistência visual extrema. Retrofitar tokens em 10+ pages custa 10x mais que criar a fundação antes.

---

## ADR-043 — shadcn/ui como component library

**Status:** Decidido (F4.5)

**Decisão:** shadcn/ui (Radix primitives + Tailwind).

Alternativas descartadas: MUI (opinião forte), Ant Design (visual Chinese-first), custom (reinventar a roda).

---

## ADR-050 — Tailwind v4 `@theme inline`

**Status:** Decidido (F4.5)

**Decisão:** Design tokens via `@theme inline` em `globals.css`. CSS-first (v4 nativo). Sem `tailwind.config.ts`.

---

## ADR-051 — Geist fonts

**Status:** Decidido (F4.5)

**Decisão:** Geist Sans + Geist Mono via `next/font/google`. Mono para números financeiros (tabular-nums).

---

## ADR-052 — Lucide React para ícones

**Status:** Decidido (F4.5)

**Decisão:** Lucide (padrão shadcn/ui). Tree-shakeable. Substituir SVGs inline e emojis.

---

## ADR-053 — `Intl` nativo para datas

**Status:** Decidido (F4.5)

**Decisão:** `Intl.DateTimeFormat` / `Intl.NumberFormat` nativos. date-fns adiado para F6 (DateRangePicker).

**Rationale:** Locale-aware, zero deps externas.

---

## ADR-054 — Migração incremental de pages

**Status:** Decidido (F4.5)

**Decisão:** Migration page-by-page (11 pages). Build green após cada page migrada.

Alternativa descartada: Big-bang. Alto risco de quebrar tudo.

---

## ADR-044 — Transaction Explorer como core

**Status:** Decidido (F6)

**Decisão:** TE é a primeira sub-fase (6A). É target de drill-down do Dashboard (6B) e Report (6C).

---

## ADR-045 — Data lineage via tooltip

**Status:** Decidido (F6)

**Decisão:** P1 com tooltip simplificado (fonte, banco, data, método det/LLM). Drill-down full para documento/página fica para futuro.

---

## ADR-046 — Responsivo sem PWA obrigatório

**Status:** Revisado (F6)

**Decisão original:** PWA obrigatório com offline.

**Decisão revisada:** Responsivo em F6. PWA adiada para F8.

**Rationale:** PWA offline com dados financeiros tem implicações de security. Prematuro para dogfood.

---

## ADR-047 — Category override em vez de reconciliação UI

**Status:** Decidido (F6)

**Decisão:** Category override inline em Transaction Explorer. Reconciliação full (resolver conflitos E3) é projeto à parte, adiado para Futuro.

---

## ADR-007 — Fernet app-level para criptografia

**Status:** Decidido (F4→F7)

**Decisão:** Fernet symmetric encryption em app-level. Consistente em vault de senhas (F2), CPFs (F3), API keys LLM (F4), e dados sensíveis adicionais (F7).

Alternativas descartadas: pgcrypto (DB-level, menos portável), AES manual (propenso a erros).

**Consequências críticas:** Ver [D60](#adr-060--fernet-dual-key-para-secret-rotation) sobre rotação. **Perder a FERNET_KEY = perder todos os dados encriptados.**

---

## ADR-055 — Coverage target: ≥85% line + ≥95% new code

**Status:** Decidido (F7)

**Contexto:** Buscar 100% line em 14K linhas de scripts legados é anti-pattern.

**Decisão:**
- Overall: ≥85% line, ≥75% branch
- Novo código: ≥95% line (CI gate)
- Crescimento orgânico a 90%+ ao longo do tempo

---

## ADR-056 — Rolling restart em vez de blue-green

**Status:** Decidido (F7)

**Decisão:** `docker compose pull && up -d` com health check pós-deploy + rollback automático.

**Rationale:** Blue-green real requer 2 VPS (overkill para dogfood). Downtime <30s é aceitável.

---

## ADR-057 — JWT 15min + refresh 7d

**Status:** Decidido (F7)

**Decisão:** JWT access token 15min + refresh token 7d httpOnly cookie. Frontend interceptor com retry queue para 401.

**Rationale:** Reduz superfície de ataque (access token expira rápido) sem fricção (refresh automático).

---

## ADR-058 — VPS CX32 para sizing

**Status:** Decidido (F7)

**Decisão:** Hetzner CX32 (4 vCPU, 8GB, ~$8/mo). CX22 (4GB) é apertado com todos os containers + overhead de deploy.

---

## ADR-059 — Docker image CVE scan no CI

**Status:** Decidido (F7)

**Decisão:** Trivy ou docker scout no CI. Gate: 0 critical/high CVEs.

**Rationale:** Produto financeiro = zero tolerance para vulnerabilidades conhecidas.

---

## ADR-060 — Fernet dual-key para secret rotation

**Status:** Decidido (F7)

**Decisão:** Dual-key rotation:
1. Gerar nova key
2. Configurar `FERNET_KEYS=new,old` (Fernet aceita lista)
3. Re-encrypt dados em background (Celery task)
4. Remover key antiga

Documentado no Runbook.

**⚠️ Nota de operação:** `FERNET_KEY` precisa estar persistida em `.env` (nunca gerar nova sem rotação). Ver [SETUP.md](SETUP.md).

---

## ADR-061 — Telemetria privacy-first

**Status:** Decidido (F7)

**Decisão:** Tabela `UsageMetric` no DB próprio. Sem analytics externo (GA, Mixpanel, etc.).

**Consequências:**
- ✅ Zero third-party tracking
- ✅ Dados do user nunca saem do servidor
- ⚠️ Dashboards precisam ser construídos custom

---

## ADR-062 — Frontend testing em fase dedicada (6.5)

**Status:** Decidido • **Data:** 2026-04-14

**Contexto:** Versão anterior do plano tinha setup de testes frontend dentro de F7 misturado com Docker, LGPD, CI/CD, dogfood.

**Decisão:** Fase 6.5 dedicada (2 semanas). Vitest + RTL + MSW + Playwright.

**Rationale:**
- Testes ficavam no final do critical path do launch
- Pressão de "ship" empurrava testes para P2
- Bugs frontend descobertos em produção custam 10x mais
- Separar garante que testes são pré-requisito do deploy

---

## ADR-063 — Hardening fintech em sub-fase 6.5D

**Status:** Decidido • **Data:** 2026-04-15 • **Supersedes parcialmente:** ADR-062 (estende escopo)

**Contexto:** Revisão do escopo de F6.5 por conselho de especialistas (CEO, CTO, CPO, Lead Designer Fintech) identificou 7 gaps P0 e 3 gaps P1 não cobertos pelo escopo original (apenas 6.5A/B/C: unit, integration, E2E + smoke). Os gaps são especificamente sensíveis em produto financeiro indo a beta:

1. Acessibilidade automatizada (axe-core) — apenas pass manual em 6D
2. Property-based em formatadores BRL — bug de formatação monetária destrói confiança permanentemente
3. Visual regression — Recharts, dark mode oklch e `@media print` podem regredir silenciosamente
4. Cross-browser real — Playwright default só Chromium; Safari iOS e Firefox têm quirks relevantes
5. Resilience — WS reconnect, polling fallback, offline, 5xx; cenários que vão ocorrer em prod
6. Security smoke frontend — XSS em campos user-controlled, JWT expiry mid-sessão, logout cleanup
7. Fixtures sintéticas auditadas — risco LGPD se contributor commitar PII real em fixture

**Alternativas consideradas:**
- (A) Inflar 6.5A/B/C com os P0 → risco de cortar sob pressão de prazo
- (B) Empurrar para F7 (gap-fill) → repete o erro corrigido em ADR-062 (testes no critical path do launch)
- (C) **[escolhida]** Sub-fase 6.5D dedicada, blindada, ~3-4 dias

**Decisão:** Criar sub-fase **6.5D — Hardening Fintech** com 7 P0 + 3 P1, prazo total de F6.5 estendido de 2 → 2.5 semanas.

**Critérios de aceite adicionais em F6.5:**
- axe-core: 0 violations critical/serious
- Visual regression: zero diffs não-aprovados (baseline versionado)
- Cross-browser: 3 fluxos críticos green em chromium + firefox + webkit
- Lint anti-vazamento de PII em fixtures: green

**Itens explicitamente fora de 6.5D (vão para F7 ou F8):**
- Mutation testing (Stryker) → F7 (sem baseline estável agora)
- Storybook → F8 (sem time de design colaborando)
- Analytics instrumentation tests → F7/F8 (telemetria definida em ADR-061, ainda não implementada)
- Lighthouse perf >90 como gate hard → F7D.7 (em 6.5D só medir, não bloquear merge)

**Consequências:**
- ✅ Beta entra com fundação robusta para fintech (a11y, resilience, security)
- ✅ Visual regression captura drift de Recharts/dark mode antes de afetar usuário
- ✅ Risco LGPD de PII em fixtures eliminado por lint automatizado
- ✅ Cross-browser previne abandono em Safari iOS no beta
- ⚠️ Prazo de F6.5 +0.5 semana (2 → 2.5)
- ⚠️ Visual regression baseline precisa de manutenção quando design muda intencionalmente
- ❌ Sem mutation testing nesta fase (aceito; chega em F7)

---

## ADR-064 — Backend hardening em sub-fase 6.5E

**Status:** Decidido • **Data:** 2026-04-15

**Contexto:** O incidente BUG-015 (capa do relatório vazia para workspaces multi-tenant porque `serialize_family_members` perdia `familia.sobrenome` ao sobrescrever o JSON tenant) revelou uma classe inteira de bugs latente:

1. Os serializers (DB → pipeline JSON) são **contratos silenciosos** — sem testes de round-trip, qualquer mudança quebra o pipeline sem que o backend perceba
2. O fallback do `_copy_global` permite que dados do founder vazem para workspaces reais (relacionado a BUG-004)
3. Migrations Alembic rodam contra qualquer DB no `cwd` — possível aplicar migration na DB errada (foi exatamente o que aconteceu durante o fix de BUG-015)
4. `_init_config` é compartilhado entre Celery workers — sem teste de concorrência

F6.5 originalmente cobria só frontend. F7D.1-3 falava em "gap-fill" mas sem foco específico nessas fronteiras.

**Alternativas consideradas:**
- (A) Adicionar tasks soltas em F7D — se diluem entre 30+ outras tarefas, alta chance de cair
- (B) Esperar primeira regressão real em prod — inaceitável para produto financeiro
- (C) **[escolhida]** Sub-fase 6.5E dedicada (~2 dias), antes do deploy para prod

**Decisão:** Criar sub-fase **6.5E — Backend Hardening** com 7 tasks (5 P0 + 2 P1) cobrindo:
- Round-trip tests para os 6 serializers
- Golden file pipeline com PDFs sintéticos (proves zero data leakage)
- Alembic CI guardrails (drift + idempotency + dry-run)
- Fix de cwd-sensitivity em alembic.ini
- Test anti-regressão BUG-015 explícito
- Systemic fix para fallback-leak class
- Concurrency test para `_init_config`

**Critérios de aceite adicionais em F6.5:**
- 6 serializers com round-trip green
- Golden pipeline test com PDFs sintéticos: green
- CI falha em migration drift ou non-idempotent
- BUG-015 coberto por test que falharia se removermos o fix

**Consequências:**
- ✅ Classe BUG-015 eliminada via cobertura sistemática
- ✅ Confiança em mudar serializers no futuro
- ✅ Migrations não podem aplicar na DB errada por acidente
- ✅ Pipeline test golden com dados sintéticos = base reusável para 6.5C.0 E2E
- ⚠️ Prazo de F6.5 +2 dias (2.5 → 3 semanas)
- ⚠️ Manutenção: golden file precisa ser regenerado quando schema do report muda intencionalmente
- ❌ Não cobre todos os edge cases de scripts E5/E6 — ainda fica para 7D.2 gap-fill

---

## ADR-065 — Sub-fase 7E Operational Readiness

**Status:** Decidido • **Data:** 2026-04-15

**Contexto:** A versão original da F7 cobria deploy (7A), security/LGPD (7B), CI/observabilidade (7C) e quality gate (7D). Faltam concerns operacionais que só aparecem **depois** que o produto está rodando com usuários:

1. **Pipeline runs órfãs:** Celery worker morre → run fica `"running"` para sempre → user vê spinner eterno
2. **Disaster recovery não testado:** 7A.10 menciona backup mas sem restore drill, RPO/RTO não declarados, backup mora no mesmo DC do Hetzner (incêndio = perda total)
3. **FERNET_KEY recovery:** ADR-060 menciona dual-key mas sem procedure testado
4. **Observabilidade só captura erros:** Sentry vê crashes; nada vê "0 reports nas últimas 24h" = produto silenciosamente quebrado
5. **Comunicação durante incidente:** sem template, sem status page público, sem support runbook
6. **LLM cost runaway:** BYOK não isenta de monitoring; user pode estourar próprio budget sem perceber, e nós não sabemos
7. **API key inválida** crasha mid-pipeline com 500 em vez de validar antes

**Alternativas consideradas:**
- (A) Distribuir essas tasks entre 7A/7B/7C/7D — risco de virar P2 e ser cortado
- (B) Empurrar para pós-launch — significa primeiro incidente sem ferramentas para responder
- (C) **[escolhida]** Sub-fase dedicada 7E, ~2 semanas, executada após 7D mas **antes** do dogfood

**Decisão:** Criar sub-fase **7E — Operational Readiness** com 14 tasks organizadas em 5 grupos:
- **7E.A Pipeline operacional:** stuck-run detector
- **7E.B Disaster recovery:** restore drill, RPO/RTO, off-site backup, FERNET recovery
- **7E.C Observabilidade de negócio:** status page, business metrics, SLOs/SLAs
- **7E.D Comunicação de incidentes:** templates de comms, support runbook
- **7E.E LLM cost runaway protection:** cost cap, dashboard, API key validation, fallback model

**Consequências:**
- ✅ Beta começa com ferramentas para responder ao primeiro incidente
- ✅ Off-site backup elimina risco de perda total em falha de DC
- ✅ Pipeline runs órfãs viram tickets, não experiências silenciosamente quebradas
- ✅ Cost cap protege user de queimar próprio budget BYOK
- ✅ Status page + comms templates = comunicação profissional desde dia 1
- ⚠️ Prazo de F7 +2 semanas (6-8 → 8-10 semanas, sem contar dogfood)
- ⚠️ Off-site backup adiciona custo (~$1-3/mo S3 BR ou Backblaze B2)
- ❌ MFA fica para F8 (decisão deliberada — ver ADR-066)

---

## ADR-066 — Auth flows completos e prompt injection em 7B (bloqueadores de beta)

**Status:** Decidido • **Data:** 2026-04-15

**Contexto:** F7B original cobria session security (JWT + refresh), audit log e LGPD (termos, exclusão, portabilidade). Faltam fluxos de auth básicos que **bloqueiam GA**:

1. **Email verification** ausente — qualquer um pode registrar `presidente@empresa.com` e receber relatórios financeiros (impersonation)
2. **Password reset** ausente — esqueci minha senha = produto inutilizável, sem recovery
3. **Brute-force lockout** ausente — rate limit de 5/min ainda permite 7200 tentativas/dia
4. **MFA** não está nem no roadmap explícito — fintech bare minimum para GA
5. **Prompt injection no E2-llm/E1.5:** PDFs vêm de usuários; um PDF malicioso pode conter texto invisível instruindo o LLM a vazar dados via campo `notes` ou similar — sem defesa hoje
6. **Terms versioning:** quando termos mudam, LGPD requer consentimento informado; hoje não há mecanismo

**Alternativas consideradas:**
- (A) Empurrar email verify/password reset para F8 — significa que beta fechado roda com auth quebrado
- (B) Implementar tudo só quando necessário — impossível abrir GA sem isso
- (C) **[escolhida]** Adicionar 8 tasks novas em 7B (7B.11-7B.18) cobrindo auth completo, prompt injection e terms versioning. MFA stub via ADR (decidir timing F7 vs F8 separadamente — task 7B.14)

**Decisão:** Expandir F7B com:
- 7B.11 Email verification (P0)
- 7B.12 Password reset completo (P0)
- 7B.13 Brute-force lockout escalonado (P0)
- 7B.14 MFA decision stub + campo `mfa_enabled` migration-ready (P1, decisão de timing em ADR futura)
- 7B.15 Prompt injection defense (P0)
- 7B.16 Terms versioning + re-aceitação (P1)
- 7B.17 Soft-delete period 30d (P1)
- 7B.18 DSAR SLA workflow (P1)

**Consequências:**
- ✅ Beta fechado pode rodar com fluxos de auth reais
- ✅ Caminho claro para GA (não há show-stopper de auth descoberto na hora)
- ✅ Prompt injection defense em produto LLM-augmented = não-negociável para fintech
- ✅ LGPD coberto além do mínimo (terms versioning + DSAR + soft-delete)
- ⚠️ Prazo de F7B +1-2 semanas
- ⚠️ Email transactional precisa ser configurado (provider TBD: Resend? Mailgun? AWS SES? Decisão pendente em D11 a criar)
- ❌ MFA fica como decisão pendente — provavelmente F8, mas migration-safe via stub

---

## ADR-067 — Test infrastructure em sub-fase 6.5F

**Status:** Decidido • **Data:** 2026-04-15

**Contexto:** Revisão de F6.5 após 6.5A-E definidas revelou que **fundamentos de teste estavam implícitos** e iam virar dor durante execução:

1. **Test DB isolation:** sem decisão entre transactions+rollback / truncate / recreate, tests vão leak state e ficar flaky
2. **Test data factories:** sem `make_user()`/`make_workspace()` etc., 250+ tests duplicam setup → manutenção dobra
3. **MSW sync com backend:** 50+ endpoints em `lib/api.ts` — se MSW handlers divergem do backend real, integration tests viram falsos positivos
4. **Parallelização + workspace isolation:** Playwright default = paralelo; múltiplos workers criando users no mesmo backend = race conditions
5. **Flaky test policy:** E2E vai flakear (natureza); sem política, ou CI vira ruído ou bloqueia tudo
6. **CI artifacts:** quando falha em CI, sem vídeo/trace = debug vira detective work
7. **Backend-real para E2E:** sobe via docker-compose? processo direto? que DB? que Redis? Sem spec, 6.5C.11 trava
8. **Long-running pipeline em E2E:** pipeline real = 5-15min; Playwright timeout = 30s → 6.5C.0 e 6.5C.3 dão timeout sem estratégia
9. **Premium tier LLM em E2E:** chama Anthropic real (caro, key em CI)? Mocka? Decisão pendente
10. **Synthetic PDF generator:** 6.5D.7 cita "PDFs sintéticos versionados" sem dizer **como gera**; cada banco tem layout próprio
11. **`docs/TESTING.md` ausente:** investimento de 4 semanas sem doc de onboarding = código que ninguém mantém

Esses não são "nice-to-have" — são pré-requisitos sem os quais 6.5A-E entregam testes que **viram débito técnico em 3 meses**.

**Alternativas consideradas:**
- (A) Distribuir entre 6.5A-E — fundamentos diluídos = nunca priorizados
- (B) Empurrar para F7D — aí 250+ testes já existem com infra ad-hoc, refactor caro
- (C) **[escolhida]** Sub-fase 6.5F dedicada (~1 semana), executada após 6.5E mas **antes** de F6.5 fechar; investe em fundamentos para sustentar o resto

**Decisão:** Criar sub-fase **6.5F — Test Infrastructure & Process** com 14 tasks organizadas em 4 grupos:
- **6.5F.A Backend test infrastructure:** DB isolation, factories backend, backend-real spec, long-running pipeline strategy
- **6.5F.B Frontend test infrastructure:** MSW sync strategy, parallelization + workspace isolation, factories frontend
- **6.5F.C CI/Process:** flaky policy, CI artifacts (vídeo+trace), snapshot review process, premium LLM E2E decision
- **6.5F.D Documentação + tooling:** synthetic PDF generator (11 bancos), `docs/TESTING.md`, pre-commit hooks

**Critérios de aceite adicionais em F6.5:**
- DB isolation green, factories adotadas em 100% novos tests
- Backend-real CI roda em <3min
- CI artifacts com vídeo+trace acessíveis em PR
- `TESTING.md` cobre 100% dos cenários de novo contributor
- Synthetic PDFs para 11 bancos versionados; zero PDFs reais em `tests/`
- Premium LLM E2E definido (mock default + nightly real opt-in)

**Consequências:**
- ✅ 250+ testes sustentáveis após launch (factories, doc, CI mature)
- ✅ Multi-tenant isolation testável de forma confiável (workspace pool)
- ✅ Custo de adicionar novo test cai drasticamente (factory pattern + docs)
- ✅ Falha em CI debugável em <5min via artifacts
- ✅ Zero PII leak risk em fixtures (synthetic PDF generator + lint 6.5D.7)
- ✅ Onboarding de novo contributor em horas, não dias (TESTING.md)
- ⚠️ Prazo de F6.5 +1 semana (3 → 4 semanas)
- ⚠️ Synthetic PDF generator exige manutenção quando bancos mudam layout (mas isso já é necessário para parsers de E2)
- ⚠️ Decisão D11/D13-D18 (decisões pendentes) precisa ser tomada antes de algumas tasks (premium LLM API key se opt-in real)
- ❌ Pre-commit hooks (6.5F.14) é P1 — pode cair se prazo apertar; aceito

**Trade-offs específicos:**
- Mock LiteLLM em CI default (não real Anthropic) → custo $0 mas perde validação real do provider; nightly opt-in mitiga
- Pipeline mock fixtures pré-computadas em 6.5C.0 → mais rápido mas cobre menos do código real; nightly `--real-pipeline` cobre
- Workspace pool vs worker_id-suffix → trade-off entre isolation e setup cost; ADR durante 6.5F.6 decide

---

## ADR-068 — Códigos internos do pipeline nunca vazam na UI

**Status:** Decidido • **Data:** 2026-04-15

**Contexto:** O pipeline interno opera em 14+ etapas técnicas (`E0-audit`, `E1.5c`, `E2-llm`, `E3`, `E5.N`, `E7-crossval`, `E7-review`, `E7-apply`, `E6-final`...). Esses códigos faziam sentido para engenharia e operação manual, mas começaram a vazar para a UI:

- Toasts e banners exibiam `"Processando: E3"` ou `"Erro na etapa E1.5c"`
- Botões hardcoded como `"Reprocessar a partir do E3"`
- Texto em `LLMTab` listava `"E1, E1.5, E2-LLM, E7-review"` para o usuário
- `STAGE_DISPLAY_NAMES` (mapa de tradução em `format.ts`) cobria apenas ~70% das etapas; o resto caía no fallback que mostrava o código cru
- Lista vertical de 14 etapas técnicas no `ActiveRunCard` virava ruído cognitivo, não feedback útil

Para um produto fintech B2C cobrando assinatura, expor jargão de pipeline destrói confiança e parece "gambiarra de DevOps".

**Alternativas consideradas:**
- (A) Renomear apenas as strings visíveis sem reagrupar — resolve o vazamento mas mantém 14 itens cognitivamente pesados
- (B) Esconder completamente as etapas individuais — perdemos transparência e capacidade de debug pelo suporte
- (C) **[escolhida]** Tradução completa + reagrupamento em **4 fases narrativas** com **disclosure progressivo** para detalhes técnicos

**Decisão:** Adotar separação rígida entre **camada de observabilidade** (preserva códigos) e **camada de apresentação** (sempre traduzida e agrupada).

### Regras invioláveis

1. **API, WebSocket, banco, logs, telemetria → continuam usando códigos `E*`** (ex: `current_stage="E3"`).
2. **UI, toasts, e-mails, push notifications → nunca exibem códigos `E*`.** Sempre passam por:
   - `stageName(code)` (tradução 1:1) — `format.ts:STAGE_DISPLAY_NAMES`
   - `getPhase(stageOrPhaseId)` (agrupamento em 4 fases) — `pipelinePhases.ts:PIPELINE_PHASES`
3. **Mapa de etapas é exaustivo:** toda etapa que aparece em `current_stage`/`failed_at_stage`/`paused_at_stage`/`stage_logs[].stage` DEVE ter entrada em `STAGE_DISPLAY_NAMES`. Adicionar nova etapa no backend = adicionar entrada no mapa (test `format.test.ts` enumera).
4. **Disclosure progressivo:** etapas técnicas individuais ficam atrás de "Ver detalhes técnicos" (collapsed por default). Quando expandido, cada linha exibe um chip `[E3]` com tooltip "Código interno usado em logs e suporte" — preserva debug sem poluir.
5. **Mensagens de erro centradas em impacto:** `pipelineErrorMessages.ts` mapeia padrões técnicos (timeout, rate limit, password, schema...) → headline + hint user-facing. Stack trace continua disponível via "Ver detalhes do erro".

### Agrupamento em 4 fases narrativas

| # | Fase (UI)                       | Etapas internas                                            | Mensagem ativa                                      |
|---|---------------------------------|------------------------------------------------------------|-----------------------------------------------------|
| 1 | Preparando seus documentos      | E0-audit, E0-route, E0-unlock                              | "Verificando e organizando os arquivos enviados"    |
| 2 | Lendo os dados                  | E1, E1.5, E1.5c, E2, E2-llm, E2-extratos, E2-faturas       | "Extraindo transações, saldos e posições"           |
| 3 | Organizando suas finanças       | E3, E4, E5, E5.N                                           | "Reconciliando, categorizando e calculando patrimônio" |
| 4 | Montando seu relatório          | E6, E6-final, E7-crossval, E7-review, E7-apply             | "Gerando o relatório e revisando consistência"      |

Renderizado como **stepper horizontal de 4 nós** (`PhaseStepper.tsx`) com tooltip educativo por fase. Adicionar nova etapa = adicionar em **uma e apenas uma** fase em `PIPELINE_PHASES`.

**Consequências:**
- ✅ Linguagem coerente e profissional em toda a UI; remove "cara de pipeline interno"
- ✅ Carga cognitiva cai de 14 itens para 4 fases visíveis; detalhes ficam sob demanda
- ✅ Backend, logs e métricas inalterados — debug e observabilidade preservados
- ✅ Adicionar nova etapa exige toque em 2 lugares (mapa + grupo de fase) com lint/teste pegando ausências
- ✅ Mensagens de erro orientam o usuário para o **próximo passo** (ex: "cadastre a senha no Cofre"), não para a stack trace
- ⚠️ Tradução adiciona uma camada que precisa ser mantida sincronizada com o backend
- ⚠️ Para suporte interagir com o usuário, o chip `[E3]` no disclosure técnico precisa estar acessível — documentar em runbook

**Aplicação imediata:**
- `frontend/src/lib/format.ts` — `STAGE_DISPLAY_NAMES` agora exaustivo (19 entradas)
- `frontend/src/lib/pipelinePhases.ts` (novo) — 4 fases + helpers `getPhase`, `phaseOfStage`, `computePhaseStates`
- `frontend/src/lib/pipelineErrorMessages.ts` (novo) — `buildUserFacingError(text, stage)`
- `frontend/src/components/PhaseStepper.tsx` (novo) — stepper horizontal com tooltips
- `frontend/src/app/(app)/pipeline/page.tsx` — `ActiveRunCard` usa stepper + disclosure; `FailedRunCard` usa `buildUserFacingError`
- `frontend/src/app/(app)/config/{LLMTab,PipelineTab}.tsx` — copy reescrito sem códigos

---

## ADR-069 — MSW sync strategy: manual + lint CI (não codegen)

**Status:** Decidido • **Data:** 2026-04-15 • **Contexto da task:** F6.5F.5

**Contexto:** `frontend/tests/mocks/handlers.ts` define 50+ endpoints MSW que espelham `lib/api.ts`. Duas estratégias possíveis para manter sync com backend:

1. **Codegen via `openapi-typescript`:** baixar `openapi.json` do backend → gerar types + validar shapes dos handlers.
2. **Manual + lint CI:** handlers escritos à mão, contract test (6.5D.10) garante drift zero.

**Alternativas consideradas:**
- (A) Codegen completo → MSW handlers re-gerados a partir do OpenAPI + mocks auto-derivados. Custoso: requer adapter entre tipos OpenAPI e `HttpResponse.json()`, difícil testar cenários de erro customizados.
- (B) **[escolhida]** Manual + lint CI — devs escrevem handlers usando `lib/api.ts` types. Lint rodado em CI compara endpoints declarados em `handlers.ts` vs `openapi.json` do backend. Falha se há drift.
- (C) Nenhum mecanismo — confiar em reviews. Não-escalável com 50+ endpoints.

**Decisão:** Abordagem (B). `frontend/scripts/msw-lint.mjs` (scaffold inicial) lista URLs em `handlers.ts` (via AST parse de `http.<method>("/api/...")`) e diff contra `openapi.json` paths. Falha em endpoints backend sem handler correspondente OU handlers com URL que não existe no OpenAPI.

Integração com 6.5D.10 (contract test types) = complementar: aquele valida types, este valida URLs.

**Consequências:**
- ✅ Handlers escritos manualmente são leves (response body inline, fácil variar em tests)
- ✅ Cenários de erro (401, 422, 500) modelados naturalmente — codegen teria dificuldade
- ✅ Lint CI cobre "drift" — novo endpoint no backend sem handler → CI falha
- ⚠️ Primeiro run do lint precisa de baseline (lista de endpoints já presentes)
- ⚠️ Depende de backend estar UP para baixar `openapi.json` (ou pre-commit snapshot)
- ❌ Sem auto-sincronização — dev precisa atualizar `handlers.ts` ao adicionar endpoint

**Implementação:** scaffold em `frontend/scripts/msw-lint.mjs` (a criar, similar a `contract-check.mjs`). Ativar em CI após primeiro baseline.

---

## ADR-070 — Premium LLM E2E: mock default + nightly real opt-in

**Status:** Decidido • **Data:** 2026-04-15 • **Contexto da task:** F6.5F.11

**Contexto:** Pipeline premium tier chama LiteLLM → Anthropic/OpenAI/etc. Em CI, duas estratégias:

1. **Mock LiteLLM:** interceptar chamadas, retornar fixtures pré-computadas. Custo zero, reproduzível.
2. **Real API calls:** anotar chave do provedor em GH secret, chamar API real. Valida comportamento real do provider (rate limit, token counting, etc.).

**Alternativas consideradas:**
- (A) Só real em TODO PR — custo imprevisível ($$$), flaky com rate limits do provider, chave em CI de PRs de contributors externos = risco
- (B) Só mock — perde validação de mudanças no provider API (breaking changes do Anthropic SDK, por exemplo)
- (C) **[escolhida]** Mock default em PR + nightly real opt-in (workflow schedulado)

**Decisão:**
1. **PR checks:** `frontend-e2e` job usa LiteLLM mockado (adapter em `backend/tests/fixtures/llm_mock.py` retorna outputs válidos por stage). Custo $0.
2. **Nightly:** GH Actions scheduled workflow `nightly-e2e-real-llm.yml` (a criar em 6.5F.11 implementação) roda 6.5C.0 com `PW_REAL_LLM=1` + `ANTHROPIC_API_KEY` em secret. Falha → issue automática.
3. **Custo monitorado:** dashboard interno lista token spending do nightly; alerta se >$10/mês.

**Consequências:**
- ✅ PR checks são rápidos + gratuitos
- ✅ Validação de integração real provider é mantida (nightly)
- ✅ Breaking changes do Anthropic SDK pegos em <24h
- ⚠️ Se nightly falha por rate limit do provider, issue gerada pode ser ruído — mitigado por retry + detecção
- ❌ Sem validação de "LLM output shape" em cada PR — aceito (cobertura de validators em pipeline/llm/validators.py)

**Implementação:**
- `backend/tests/fixtures/llm_mock.py`: fixtures por stage (E1, E1.5, E2-llm, E7-review) com JSON válido.
- `.github/workflows/nightly-e2e-real-llm.yml` — scheduled (cron: `0 3 * * *`) rodando só `@critical` em chromium, com `PW_REAL_LLM=1` + ANTHROPIC_API_KEY.
- ADR referencia decisão D11 (pendente): provider pode mudar no futuro, ADR ajusta.

---

## ADR-071 — Playwright workspace isolation: email unique por worker

**Status:** Decidido • **Data:** 2026-04-15 • **Contexto da task:** F6.5F.6

**Contexto:** Playwright roda workers paralelos por default. Em E2E que faz registro de users (golden path, onboarding), 2 workers paralelos criando `e2e@test.com` causa race 409. Duas opções de isolation:

1. **Pool de workspaces pré-criadas:** seed 10 users/workspaces antes dos tests, workers sacam da pool + devolvem.
2. **Email unique por worker:** cada worker usa `e2e-w${parallelIndex}-${STAMP}@test.com`.

**Alternativas consideradas:**
- (A) Pool pré-criada — complexidade de setup (seed + cleanup), eficiente para testes longos mas overkill para smoke
- (B) **[escolhida]** Email unique por worker — helper `userForWorker(info)` gera email derivado de `parallelIndex` + `STAMP`. Cada worker opera em seu próprio "workspace fresco" sem coordenação
- (C) `fullyParallel: false` — serializa tests, mata paralelização

**Decisão:** Abordagem (B). Já implementada em `frontend/tests/e2e/helpers/auth.ts::userForWorker()` no Bootstrap. Workers NÃO compartilham state; cada um registra user novo por run.

**Cleanup:** users criados ficam no DB. Estratégia:
- **CI:** DB PG service é efêmero (spun up por run) → sem cleanup necessário
- **Local:** users acumulam em `fin.db`; documented em `TESTING.md` que dev pode dar `./scripts/test_backend_up.sh --reset` para zerar

**Consequências:**
- ✅ Zero coordenação entre workers — paralelização total
- ✅ Simples (3 linhas de código no helper)
- ✅ Cada test é hermético — falha de um worker não afeta outro
- ⚠️ DB local acumula users — reset manual quando ficar pesado
- ❌ Não exercita "user com dados pré-existentes" — esses cenários cobertos em integration tests (factories backend)

**Implementação:** já feita em Bootstrap. Esta ADR documenta a decisão para future-me não reabrir.

---

## ADR-072 — Multi-tenancy: `workspace_id` scoping explícito + `WorkspaceMember` para multi-família

**Status:** Decidido (F8) • **Data:** 2026-04-15 • **Contexto da task:** F8.0 — Fundação Goals & Tasks

**Contexto:** Até F6.5 o produto operou assumindo **1 workspace por usuário** (query `Workspace WHERE owner_id = user.id` replicada em helpers `_get_workspace(user)` em cada arquivo de API — ex: [backend/app/api/documents.py:30](backend/app/api/documents.py:30)). Esse contrato foi aceitável no MVP com a família Ferreira Campos como único tenant. Para F8, a premissa do produto muda: **"será utilizado por diferentes clientes (e famílias) com objetivos, metas e dinâmicas próprias e distintas"**. Isso exige:

1. Múltiplos workspaces por usuário (um consultor pode acompanhar várias famílias).
2. Múltiplos usuários por workspace (cônjuges, dependentes, contador convidado).
3. Isolamento rigoroso: zero vazamento cross-tenant em queries, notificações, LLM prompts, exports.

**Alternativas consideradas:**
- (A) **Postgres Row-Level Security (RLS)** — `CREATE POLICY ... USING (workspace_id = current_setting('app.workspace_id')::uuid)`. Segurança no banco, independente da aplicação.
  - ❌ Rejeitada por ora: dual-db SQLite (dev) + PostgreSQL (prod) do [ADR-039](#adr-039--dual-db-sqlite-dev--postgresql-prod) — SQLite não tem RLS. Forçaria divergência dev/prod ou migração para só-PG no dev.
- (B) **Scoping explícito no service layer + lint custom** — toda query recebe `workspace_id` como primeiro argumento; ruff custom rule barra queries sem filtro.
  - ✅ **Escolhida**: portável entre SQLite e Postgres, testável, e o lint evita regressão humana.
- (C) **Continuar com `owner_id` implícito** — manter 1:1 user↔workspace e resolver multi-família via múltiplos users.
  - ❌ Rejeitada: quebra o caso do consultor com várias famílias e não acomoda múltiplos membros adultos com login próprio.

**Decisão:**
1. **Modelo `WorkspaceMember`** (nova tabela) — `(workspace_id, user_id, role, invited_by, joined_at)`. Roles iniciais: `owner`, `member`. Substitui o uso exclusivo de `Workspace.owner_id` (que permanece como "criador original" por audit, mas não é mais usado como filtro de acesso).
2. **Resolução explícita via path param** — todo endpoint novo de F8+ usa prefixo `/api/workspaces/{workspace_id}/...`. A dependency FastAPI `get_current_workspace()` valida que o `user_id` tem `WorkspaceMember` na `workspace_id` pedida; 403 se não tiver.
3. **Lint rule custom** — `scripts/lint/check_workspace_scoping.py` (CI-gated) escaneia `backend/app/services/**/*.py` por queries (`select(X).where(...)`, `db.execute(...)`) e falha se a primeira condição não referenciar `workspace_id`. Exceções marcadas com `# tenancy: global` (ex: `User` auth, `Category` templates globais).
4. **Services recebem `workspace_id` como primeiro argumento**, nunca inferem por `user_id`. Padrão obrigatório para qualquer código novo: `def list_tasks(workspace_id: UUID, filters: TaskFilters) -> list[Task]`.
5. **Testes de isolamento automáticos** — factory cria 2 workspaces, e para cada novo endpoint há teste `test_<endpoint>_tenant_isolation` que verifica que dados do WS-A nunca vazam em resposta com token do WS-B.
6. **Migração dos endpoints legados** — endpoints pré-F8 continuam usando `_get_workspace(user)` até serem tocados. Quando forem tocados, migram para `get_current_workspace()`. Deadline rígido: F8.4 (cutover final).
7. **UUIDs não-enumeráveis** — todas as novas tabelas usam `uuid.uuid4()` (já é padrão; reforçar nos novos models).

**Consequências:**
- ✅ Multi-família viável sem mudar banco (SQLite dev + Postgres prod continua valendo)
- ✅ Path-based workspace resolution é explícito, debugável, e funciona bem com OpenAPI/typed clients no frontend
- ✅ Lint custom pega regressões antes do review humano
- ✅ `WorkspaceMember` abre caminho para RBAC granular futuro sem re-modelagem (roles evoluem)
- ⚠️ Migração dos 10+ endpoints legados é esforço incremental, não big-bang — aceito
- ⚠️ Sem RLS, bug na app = vazamento. Mitigado por lint + testes de isolamento + audit log
- ❌ Cross-workspace queries (ex: "advisor dashboard agregado") exigem endpoint especial com check explícito por workspace — aceito como débito documentado

**Implementação inicial (F8.0):**
- Migration alembic: criar tabela `workspace_members`; backfill `(workspace_id, owner_id, 'owner', NULL, created_at)` para todo `Workspace` existente.
- `backend/app/core/tenancy.py` com `get_current_workspace(workspace_id: UUID, user = Depends(get_current_user), db = Depends(get_db))`.
- `scripts/lint/check_workspace_scoping.py` + job `tenancy-lint` no CI.
- Documentação em `docs/tenancy.md` (criar) com exemplos de do/don't.

**Débito explícito (fora do escopo desta ADR):**
- RBAC granular por papel (`read_only`, `approver`, `admin`) — endereçar quando primeiro consultor pedir.
- Workspace sharing UI (convite, aceite, revogação) — F9+.
- Cross-tenant analytics (produto) — requer ADR própria quando surgir.

---

## ADR-073 — Goals como entidade versionada (não config estático)

**Status:** Decidido (F8) • **Data:** 2026-04-15 • **Contexto da task:** F8.1 — Metas IF

**Contexto:** Hoje o objetivo de Independência Financeira (IF) vive em [config/goals.json:19-27](config/goals.json:19) como `if_meta: 7200000.0` — um número digitado à mão, sem derivação matemática, sem histórico de mudanças, sem audit de quem alterou. No modelo multi-família, cada workspace precisa ter sua meta própria, editável por UI, e é essencial preservar **trajetória** (qual era a meta em jan/2025 vs. abr/2026) para gráficos de progresso e comparativos "antes/depois". O valor tampouco deve ser digitado diretamente: é derivado de `renda_passiva_mensal × 12 / trs_pct` — e o usuário pensa em termos de renda desejada, não de patrimônio-alvo.

**Alternativas consideradas:**
- (A) **Reusar `ConfigBlob`** (modelo existente que armazena JSON arbitrário por workspace — padrão do [ADR-020](#adr-020--materializar-config-em-disco)).
  - ❌ Rejeitada: não versiona por default, sem semântica de "vigência", e mistura goals (dado crítico com narrativa no produto) com configs operacionais (keywords, thresholds). Goal merece tipo forte.
- (B) **Model único `Goal` com JSONB `params_json` + `derived_json`** — `type` discrimina IF, Aporte Mensal, Dolarização, etc.
  - ✅ **Escolhida**: flexível para tipos variados (goals.json atual tem 10+ "seções" de meta), versiona com `effective_from`, valida por tipo via JSON Schema.
- (C) **Model por tipo (`IFGoal`, `MonthlyContributionGoal`, ...)** — rigor máximo de tipagem.
  - ❌ Rejeitada: cada novo tipo de goal exige migration; a variação acontece muito cedo no produto para cristalizar em tabelas separadas.
- (D) **Digitar `if_meta` diretamente no formulário** — simpler.
  - ❌ Rejeitada: usuário pensa em "quanto quero receber por mês?", não "qual meu patrimônio-alvo?". Forçar o cálculo matemático explícito é pedagógico e elimina inconsistências.

**Decisão:**
1. **Tabela `goals`** com colunas: `id (UUID)`, `workspace_id (FK)`, `type (Enum)`, `params_json (JSONB)`, `derived_json (JSONB)`, `effective_from (Date)`, `effective_to (Date|NULL)`, `created_by (FK user)`, `notes (text)`, `created_at`, `updated_at`.
2. **Versionamento por append-only** — edição cria novo registro com `effective_from = hoje` e fecha o anterior com `effective_to = ontem`. Registro vigente é único por `(workspace_id, type)` e tem `effective_to IS NULL`.
3. **Derivação server-side** — `goal_service.compute_if_derived(inputs: dict) -> dict` é função pura, testada, e é **a única fonte** do cálculo. Frontend chama `POST /goals/if/compute` para preview live; pipeline chama a mesma função.
4. **Schema canônico por tipo** — `config/schemas/goal.if.schema.json` (criar) define `params_json.inputs.{renda_passiva_mensal_brl, trs_pct, retorno_real_anual_pct, horizonte_anos, taxa_retirada_conservadora_pct}` e `derived.{if_meta_brl, aporte_necessario_mensal_brl, if_meta_conservadora_brl}`. Backend valida write, frontend gera tipos TS via codegen (OpenAPI).
5. **Tipos de goal implementados em F8.1**: apenas `INDEPENDENCIA_FINANCEIRA`. Outros tipos (`APORTE_MENSAL`, `DOLARIZACAO`, alocação-alvo) ficam como débito para F8.5+; campos correspondentes em `goals.json` continuam sendo lidos via adapter até migração.
6. **Migração do `goals.json` de Ferreira Campos** — one-shot script em `backend/app/scripts/seed_if_goal_ferreira_campos.py` cria registro inicial para a workspace existente com `renda_passiva_mensal_brl=30000, trs_pct=5.0, retorno_real_anual_pct=6.0` → `derived.if_meta_brl=7200000` (paridade bit-a-bit com valor legado).
7. **Novos workspaces** — seed cria Goal template flag `is_template=true` com valores default (renda 20k/mês, trs 5%). UI do dashboard detecta a flag e força wizard antes de liberar outras funcionalidades.
8. **Pipeline (E5/E5.N)** — lê Goal vigente via `pipeline_adapter.build_goals_payload(workspace_id)` que retorna dict no formato atual de `goals.json` (campo `independencia_financeira`). Rest de `goals.json` (`aportes`, `fase_f1f2`, etc.) continua servido pelo adapter a partir de fontes legadas até F8.5.

**Consequências:**
- ✅ Histórico preservado — é possível mostrar "sua meta subiu 8% no último ano" e gerar gráfico de progresso real
- ✅ Derivação única — zero risco de UI mostrar 7.2M enquanto pipeline calcula 7.5M
- ✅ Validação por schema versionável (`meta_version`) — permite evoluir sem quebrar históricos
- ✅ Audit log natural via `created_by` + `effective_from`
- ⚠️ Migração dos outros "tipos de goal" (aportes, alocação alvo) fica como débito — durante transição, `goals.json` continua existindo como seed + override legado
- ❌ Não temos "rascunho" de goal (user editando sem commit) — aceito; wizard confirma antes de persistir

**Implementação inicial (F8.1):**
- `backend/app/models/goal.py` + Alembic migration
- `backend/app/services/goal_service.py` (`compute_if_derived`, `create_goal_version`, `get_current_goal`, `get_goal_history`)
- `backend/app/api/goals.py` com endpoints documentados no plano de execução
- `config/schemas/goal.if.schema.json`
- Testes unitários de `compute_if_derived` (10+ casos) + integração multi-workspace
- Script one-shot de seed para Ferreira Campos

---

## ADR-074 — Tasks como entidade de 1ª classe (fora do relatório)

**Status:** Decidido (F8) • **Data:** 2026-04-15 • **Contexto da task:** F8.2 — Plano de Ação

**Contexto:** Hoje a "checklist de tarefas" vive em [config/tarefas.md](config/tarefas.md) como markdown versionado no git, parseado deterministicamente pelo E5, enriquecido pelo E5.N (LLM), e renderizado no relatório HTML final pelo E6. Esse fluxo é elegante para o pipeline batch, mas **impossibilita execução interativa**:
- Usuário não consegue marcar "feito" sem editar markdown e rodar pipeline de novo.
- Não há notificação de prazo (ex: IPTU 30/04 é time-bomb).
- Sem anexos de comprovante, sem conexão com transações, sem histórico estruturado.
- Sugestões do E5.N ficam em `tarefas_sugeridas[]` que o usuário precisa copiar/colar manualmente.
- Relatório vira poluído de operacional — deveria ser estratégico (foto do momento).

No modelo multi-família, cada workspace tem seu próprio backlog com dinâmica distinta — um arquivo compartilhado no repo não escala.

**Alternativas consideradas:**
- (A) **Manter `tarefas.md` por workspace** (um arquivo por tenant no storage local).
  - ❌ Rejeitada: não resolve execução interativa; arquivo compartilhado entre pipeline e UI gera race; sem audit/versionamento/anexos.
- (B) **Tabela `tasks` como entidade de 1ª classe + `task_suggestions` queue + `task_attachments`**.
  - ✅ **Escolhida**: resolve todos os problemas. `tarefas.md` vira *export* gerado on-demand (compat pipeline legado).
- (C) **Integrar com Todoist/Things/Linear via OAuth**.
  - ❌ Rejeitada: acopla produto a SaaS externo, perde ligação semântica com dados financeiros (task↔transaction↔goal), e LGPD + contexto fintech exigem dados sob controle.

**Decisão:**
1. **Tabelas novas**: `tasks`, `task_suggestions`, `task_attachments` (reusa padrão do vault para anexos).
2. **`Task` preserva `number int` único por workspace** — mantém a ref `#5` do `tarefas.md` atual, crítica para rastreabilidade em commits, ADRs e narrativas do E5.N.
3. **`Task.deadline`** é modelado com `deadline_kind Enum("HARD_DATE", "MONTH", "QUARTER", "CONDITIONAL", "UNSCHEDULED")` + `deadline_date Date|NULL` + `deadline_label str|NULL`. Acomoda os padrões do MD atual ("Abr/2026", "30/04/2026", "Antes EUA", "T3/26").
4. **`Task.status`** com transições validadas: `pending → in_progress | done | cancelled | blocked`; `blocked → pending | cancelled`; `done` e `cancelled` são terminais (exigem `unarchive` explícito para reabrir). Enforcer em `task_service.transition_status`.
5. **Dependências explícitas** via `parent_task_id` — UI bloqueia marcar como `done` se parent estiver pendente (regra do `enforce_dependency_rule`). Migração inicial infere dependências a partir das Notas do `tarefas.md` (ex: "#19 depende de #18").
6. **E5.N escreve em `task_suggestions`** (não mais em `tarefas_sugeridas[]` do JSON). Sugestão contém `proposed_payload JSONB` com estrutura idêntica à `Task`. Usuário aprova 1-click → cria `Task` + marca suggestion como `approved`. Queue aparece em `/plano-de-acao/sugestoes` com badge contador.
7. **Relatório lê snapshot imutável** — no momento da geração do relatório (E6), o serviço copia o estado atual de `tasks` para `report.snapshot_json`. O relatório renderiza a partir do snapshot, não do DB live. Garante que "relatório de 15/abr/2026" sempre mostra o que estava pendente naquele dia.
8. **Export `GET /tasks/export.md`** — gera `tarefas.md` on-demand a partir do DB, preservando formato atual. Usado durante transição para scripts legados que ainda esperam o arquivo.
9. **Migração one-shot do `tarefas.md` de Ferreira Campos** — importer em `backend/app/scripts/seed_tasks_ferreira_campos.py` parseia o MD, cria tasks preservando `number` (1..43, com `#2` e `#12` como `status=done`), categorias, prioridades, status, ref. Notas com dependência ("#19 depende de #18") são parsed e materializadas em `parent_task_id`.
10. **Novos workspaces recebem templates genéricos** (não dados Ferreira Campos) — 10-12 tarefas essenciais comuns a qualquer família (contratar seguro vida, consultar CPA expatriado se aplicável, etc.) com `created_from='seed'`. Usuário pode aceitar, editar, ou descartar no onboarding.
11. **Integração Task↔Transaction↔Goal (F8.3)** — `related_transaction_id` e `related_goal_id` opcionais. UI usa para mostrar "% executado" (tarefa "Aporte R$20k/mês" lê aportes do mês atual agregados por `aporte_match_keywords` do `goals.json`).
12. **Remoção do `tarefas.md` do repo** acontece em F8.4 (cutover final) — até lá, arquivo permanece como seed/fallback.

**Consequências:**
- ✅ Execução interativa real — marca feito, anexa comprovante, recebe notificação
- ✅ Relatório volta a ser estratégico (snapshot imutável) — operacional fica no módulo próprio
- ✅ Sugestões do E5.N viram fluxo de aprovação UI, não copy-paste em markdown
- ✅ Dependências explícitas destravam UX ("cadeado" em task bloqueada)
- ✅ Audit log natural de transições
- ✅ Multi-tenant desde o dia 1 via [ADR-072](#adr-072--multi-tenancy-workspace_id-scoping-explícito--workspacemember-para-multi-família)
- ⚠️ Pipeline E5 precisa refatorar leitura — de parser MD para `task_service.list_tasks(workspace_id)` via adapter. Contrato JSON preservado.
- ⚠️ Novas tarefas criadas via UI precisam de `number` — incrementa `max(number) + 1` por workspace (lock em transação para evitar race)
- ❌ Sem sync bidirecional com Google Tasks / Todoist — aceito (débito; pode ser adicionado sem quebrar modelo)

**Implementação inicial (F8.2):**
- Models + migrations
- Services (`task_service`, `task_suggestion_service`) com transições validadas
- Endpoints documentados no plano
- Rota frontend `/plano-de-acao` + drawer + sugestões
- Widget `UpcomingTasksWidget` no dashboard (`deadline_date <= today + 7d` e `status in (pending, in_progress)`)
- Importer one-shot + testes de paridade (MD inicial vs. DB pós-import)
- Feature flag `tasks_v2_enabled` (workspace-level)

---

## ADR-075 — Cutover CLI → Web: estratégia de transição faseada com adapters

**Status:** Decidido (F8) • **Data:** 2026-04-15 • **Contexto da task:** F8.0-F8.4 — migração completa

**Contexto:** O pipeline original (E0-E7) foi construído como CLI determinístico + etapas LLM manuais — scripts Python em `scripts/` que leem `config/*.json`, `config/tarefas.md`, `data/` e escrevem em `processed/` e `output/`. A partir de F1 o produto incorporou backend + frontend, mas o pipeline determinístico continua rodando via worker Celery que envelopa os scripts CLI ([ADR-013](#adr-013--wrap-dont-rewrite-pattern) — "wrap, don't rewrite"). **A decisão confirmada pelo usuário em F8 é: a app web substitui o pipeline CLI**. Isso não significa reescrever tudo de uma vez — significa que o CLI deixa de ser interface suportada e a fonte de verdade migra `config/*.json` → DB.

O risco principal: quebrar o pipeline durante a transição e perder capacidade de gerar relatórios antes que a UI seja equivalente. Mitigação via **adapters**: scripts continuam rodando com I/O preservado, mas leem do DB em vez de arquivos.

**Alternativas consideradas:**
- (A) **Big-bang rewrite** — reescreve E5, E5.N, E6 em F8.4 e desliga CLI.
  - ❌ Rejeitada: F6.5 acabou de consolidar 438 testes contra o pipeline atual. Reescrever antes de substituir integralmente a UI perde a rede de segurança.
- (B) **Manter dual-source indefinidamente** — DB como source of truth para UI, `config/*.json` para pipeline.
  - ❌ Rejeitada: dual-write é origem clássica de inconsistência. Aceitável como fase, não como destino.
- (C) **Adapter pattern faseado + remoção gradual de arquivos do repo** — DB passa a ser fonte única; scripts consultam DB via `pipeline_adapter`; arquivos de config de usuário são removidos do repo fase por fase.
  - ✅ **Escolhida**: preserva robustez do pipeline atual, migra source of truth uma entidade por vez, e termina com `config/` contendo apenas seeds/templates de produto (institutions, categorization keywords) — não mais dados de usuário.

**Decisão:**
1. **Contrato de adapter** — `backend/app/services/pipeline_adapter.py` é a única fachada entre pipeline scripts e DB. Funções:
   - `build_goals_payload(workspace_id) -> dict` (replica estrutura de `goals.json`)
   - `build_tasks_payload(workspace_id) -> dict` (replica `tarefas[]` do JSON E5)
   - `build_tarefas_md(workspace_id) -> str` (formato markdown, compat legado)
   - `build_family_members_payload(workspace_id) -> dict` (de `family_members.json`)
   - ...outras conforme entidades migrem
2. **Classificação dos artefatos de `config/`** em 3 grupos:
   - **Grupo A — Dados do usuário** (migram para DB): `goals.json`, `tarefas.md`, `family_members.json`, `cenarios.json`, `decisions.md`. Removidos do repo ao final de F8.4.
   - **Grupo B — Seeds/templates de produto** (permanecem no repo): `institutions.json` (padrões de banco), `categorization.json` (keywords default), `parametros_fiscais.json` (alíquotas), `localization.json`, `taxas.json`, `scoring.json`. Carregados como seed no primeiro acesso do workspace; usuário pode editar cópia via `config_blob`.
   - **Grupo C — Documentação** (permanecem): `definitions.md`, `manual_operacao.md`, `methodology.md`, `source_hierarchy.md`, `regras_composicao_patrimonial.md`, `decisions.md`, `report_layout.yaml`, `report_spec.md`. Atualizar seções que referenciam Grupo A.
3. **Ordem de migração** (escolhida para minimizar risco):
   - **F8.1**: `goals.json` (parcial — só `independencia_financeira`) + adapter para resto
   - **F8.2**: `tarefas.md` completo
   - **F8.3**: integrações profundas (Task↔Transaction↔Goal)
   - **F8.4**: migração completa do resto do `goals.json` (aportes, alocação, riscos), `family_members.json`, `cenarios.json`, `decisions.md` — E5 passa a ler tudo do DB, remoção dos arquivos de Grupo A do repo.
4. **Feature flags** por módulo — `goals_v2_enabled`, `tasks_v2_enabled`, `report_snapshot_v2_enabled`, todas workspace-level. Durante transição, flag OFF = pipeline usa arquivo legado; flag ON = pipeline usa adapter. Default ON na workspace de Ferreira Campos assim que módulo entrega; default ON para todos em F8.4.
5. **Scripts CLI desabilitados em produção** — a partir de F8.4, `scripts/e*.py` são executáveis **apenas** via worker (import como módulo, não invocação CLI). Mantidos no repo como implementação de reference; `README.md` documenta que a interface suportada é a UI. Remoção total dos scripts fica como débito F9+ quando for seguro.
6. **Regressão blindada** — cada fase roda o ciclo completo E0→E7 antes/depois em workspace de teste e faz diff dos artefatos (tolerância: só diferença em timestamps). Falha de paridade = rollback automático.
7. **Backup dos Grupo A antes da remoção** — último snapshot pre-F8.4 vai para `_archive/pre-f8-cutover-2026-XX-XX/` com tag git, para referência histórica e auditoria.

**Consequências:**
- ✅ Pipeline atual segue funcionando a cada fase — risco de quebra limitado à entidade que migra
- ✅ Rollback de uma fase é reversão de flag, não de deploy
- ✅ `config/` termina enxuto (só produto), não mais mistura dados de usuário
- ✅ Claro para desenvolvedores: fontes de verdade explícitas por grupo
- ⚠️ Complexidade adicional do adapter durante transição — aceito; código isolado, removível
- ⚠️ Testes duplicados (pipeline lendo arquivo vs. pipeline lendo DB) durante transição — removidos ao fim de F8.4
- ❌ Advanced pipeline features novas (ex: goal recalculation on-demand disparado por UI) ficam esperando F8.4 — aceito
- ❌ CLI permanece tecnicamente executável pós-F8.4 (scripts não removidos), mas sem suporte — aceito

**Supersedes parcial:** [ADR-013 "Wrap, don't rewrite"](#adr-013--wrap-dont-rewrite-pattern) — a filosofia original era wrap indefinido. F8 formaliza migração eventual dos wraps em adapters DB, com remoção dos arquivos de config de usuário do repo. O padrão "wrap" continua válido para scripts que não migram (E0 route, E2 parsers).

**Implementação:**
- F8.0: contrato e stubs do adapter, CI test que valida assinatura de funções do adapter
- F8.1+: cada fase implementa as funções correspondentes e migra scripts para usá-las
- F8.4: checklist de cutover (backup → remoção de arquivos Grupo A → desabilitar entradas CLI do Makefile/documentação → atualizar `manual_operacao.md`)

---

## ADR-076 — Design Tokens Unificados Site ↔ Relatório

**Status:** Decidido (F9) • **Data:** 2026-04-15

**Contexto:**
Auditoria visual comparando `frontend/src/app/globals.css` e `config/templates/report_template.html` revelou duas linguagens de design completamente divergentes, sem ponte:

| Eixo | Site | Relatório |
|---|---|---|
| Cor primária | `oklch(0.205 0 0)` (navy neutro) | `#1A3A5C` (navy quente, hex fixo) |
| Accent | `oklch(0.97 0 0)` (quase sem saturação) | `#15803D` (verde floresta) |
| Fonte | Geist | Inter + Plus Jakarta Sans |
| Cards | Minimais, borda neutra | Left-border 4px colorida, gradientes |
| Dark mode | CSS vars + `next-themes` | `data-theme="dark"` com hex hardcoded |

Ao abrir `/reports/{id}`, o usuário experimenta uma quebra visual perceptível — duas identidades de produto disputando o mesmo espaço. O relatório tem o DNA fintech mais maduro (navy institucional, verde/vermelho semânticos, tipografia editorial); o site está na paleta shadcn default.

**Alternativas consideradas:**
- **A** — Nivelar o site pelo relatório manualmente (copiar cores/fontes no `globals.css`). Resolve agora, diverge de novo no próximo ciclo.
- **B** — TypeScript como fonte de verdade (tokens em `.ts`, exportar CSS). Bom para frontend, mas E6 (Python) vira consumidor de TS — inversão estranha.
- **C** — ✅ **Escolhida**: fonte única declarativa (`design-tokens/tokens.json`) + build step que gera CSS para Next.js e CSS para o template standalone do E6. Padrão OpenAPI/Stripe.

**Decisão:**

1. **Fonte de verdade:** `design-tokens/tokens.json` na raiz do monorepo. Estrutura semântica por categoria (color, typography, spacing, radius, shadow) com variantes light/dark. Referência visual: DNA do relatório (navy + verde/vermelho semânticos + Plus Jakarta + Inter).

2. **Build step:** `design-tokens/build.py` — emite dois arquivos:
   - `frontend/src/styles/tokens.css` — custom properties CSS consumidas por `globals.css` via `@import`. Tailwind v4 lê via `@theme inline`.
   - `config/templates/_tokens.css` — custom properties injetadas no `<style>` do relatório standalone (E6).
   Ambos são **gerados e gitignored no frontend** (regenerados no build), mas **commitados no template E6** (standalone precisa funcionar offline sem build step).

3. **Valores semânticos canônicos** (derivados do DNA do relatório):
   - `--brand-primary: #1A3A5C` (navy institucional)
   - `--brand-accent: #15803D` (verde patrimônio/gain)
   - `--brand-danger: #B91C1C` (vermelho passivo/loss)
   - `--brand-warning: #F4A261` (atenção)
   - `--font-display: 'Plus Jakarta Sans'`
   - `--font-body: 'Inter'`
   - `--font-mono: 'JetBrains Mono'` (exclusivo para valores monetários com tabular-nums)
   - `--radius-card: 12px`

4. **Dark mode:** ambos ambientes consomem os mesmos tokens; a classe `.dark` (ou `[data-theme="dark"]`) reescreve as mesmas custom properties. Elimina o divergence atual onde site usa OKLch swap e relatório usa hex hardcoded.

5. **Migração das variantes de card do relatório** (highlight, feature, success, warn, critical, primary, neutral, top-danger, top-accent) viram tokens compostos em `tokens.json` sob `card.variants.*`, consumidos identicamente pelos componentes React novos (Fase 2) e pelo E6 standalone.

6. **Regras de uso obrigatórias** (enforçadas via ESLint + pre-commit):
   - Nenhum `#` hex literal em CSS/TSX de `frontend/src/` (exceto tokens gerados).
   - Nenhum `font-family:` fora de `tokens.css`.
   - Valores monetários SEMPRE com `font-family: var(--font-mono); font-variant-numeric: tabular-nums;` — centralizado no componente `<MonetaryValue/>`.

7. **Backwards-compat:** ADR-050 (Tailwind v4 `@theme inline`) e ADR-051 (Geist fonts) são **parcialmente supersedidos** — Tailwind v4 theme continua, mas agora hidratado por `tokens.css` ao invés de hardcoded; Geist é substituído por Plus Jakarta + Inter.

**Consequências:**
- ✅ Uma identidade visual, um lugar para mudar. Fin vira produto coeso.
- ✅ Fim da dissonância site × relatório — critério de aceite F9.
- ✅ Rebase rápido para tema white-label futuro (multi-família com branding próprio — F10+): sobrescrever `tokens.json` por workspace.
- ✅ Testes de token via snapshot (`tests/design_tokens/test_build.py`) garantem paridade.
- ✅ Princípio de "config/ é fonte de verdade" preservado: tokens vivem na raiz do monorepo, acima de site e pipeline.
- ⚠️ Adiciona build step obrigatório antes de rodar `pnpm dev` — mitigado por hook `pnpm predev` e CI check.
- ⚠️ Fontes Plus Jakarta + Inter adicionam ~150KB de fontes sobre Geist (~80KB). Aceito — trade visual > bytes.
- ❌ `globals.css` atual precisa ser reescrito (~200 linhas). Aceito — custo pontual, ganho permanente.
- ❌ Qualquer branch em andamento com CSS hardcoded conflita na merge. Aceito — migração concentrada em F9.

**Supersedes parcial:**
- [ADR-050 "Tailwind v4 theme inline"](#adr-050--tailwind-v4-theme-inline) — tema continua inline, agora hidratado por tokens gerados.
- [ADR-051 "Geist fonts"](#adr-051--geist-fonts) — Geist substituída por Plus Jakarta Sans (display) + Inter (body).

**Implementação (F9):**
- F0.2: `design-tokens/tokens.json` + `build.py` + geração de ambos os CSS
- F0.2.5: estender build step para também gerar tipos do layout (YAML→TS/Pydantic)
- F1.2: `globals.css` consome `tokens.css`; fontes carregadas via Next.js `next/font/google`
- F4.1: E6 standalone template importa `_tokens.css` gerado
- F5.x: ESLint rule `no-hex-literal` + `no-direct-font-family` ativadas

---

## Decisões pendentes

| #   | Decisão                           | Quando precisa | Opções                                                               |
| --- | --------------------------------- | -------------- | -------------------------------------------------------------------- |
| D8  | Pricing do premium                | Pós-beta       | R$29/mês / R$49/mês / R$99/mês                                       |
| D9  | Nome do produto                   | Pré-GA         | Fin / FinPlan / outro                                                |
| D10 | Prioridade de novos bancos        | Pós-beta       | Nubank / Inter / Mercado Pago / Open Finance                         |
| D11 | Email transactional provider      | Pré-7B.11      | Resend / Mailgun / AWS SES / SendGrid                                |
| D12 | Multi-language support            | F8+            | pt-BR only / pt-BR + en                                              |
| D13 | MFA: F7 ou F8                     | Pré-7B.14      | F7 (TOTP via authenticator app) / F8 (após beta validado)            |
| D14 | Menores como `FamilyMember`       | Pré-beta       | Permitir (LGPD/ECA exigem cuidados) / Bloquear (apenas adultos)      |
| D15 | Cost cap mensal default           | Pré-7E.11      | 500K tokens / 1M / 2M / configurável sem default                     |
| D16 | Off-site backup destination       | Pré-7E.4       | S3 BR (custo) / Backblaze B2 (US, mais barato) / R2 Cloudflare       |
| D17 | Status page provider              | Pré-7E.6       | uptime-kuma self-hosted / instatus.com free / better-stack           |
| D18 | RPO/RTO target                    | Pré-7E.3       | Dogfood: RPO=24h RTO=4h • Beta: RPO=1h RTO=1h • GA: RPO=15min RTO=30min |

---

## Como registrar uma nova ADR

Ao tomar uma decisão não-trivial, adicione aqui com o template:

```markdown
## ADR-NNN — Título curto

**Status:** Decidido (FX) • **Data:** YYYY-MM-DD

**Contexto:** Por que estamos decidindo isso? Quais eram as alternativas?

**Decisão:** A decisão tomada, em uma frase.

**Consequências:**
- ✅ Benefícios
- ⚠️ Trade-offs
- ❌ Drawbacks aceitos
```

Se substituir uma ADR anterior, marcar: `Supersedes ADR-NNN`.
