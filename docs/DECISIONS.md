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
[D62](#adr-062--frontend-testing-em-fase-dedicada-65) [D63](#adr-063--hardening-fintech-em-sub-fase-65d) [D64](#adr-064--backend-hardening-em-sub-fase-65e) [D67](#adr-067--test-infrastructure-em-sub-fase-65f)

**Operations:**
[D65](#adr-065--sub-fase-7e-operational-readiness) [D66](#adr-066--auth-flows-completos-e-prompt-injection-em-7b-bloqueadores-de-beta)

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
