# Mathoms AI — Architecture Decision Records (ADRs)

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
[D14](#adr-014--threading-para-execução-background) [D15](#adr-015--vault-por-workspace) [D16](#adr-016--e0-route-automático-no-upload) [D17](#adr-017--sync-session-em-background-threads) [D18](#adr-018--config-dir-override-em-fortenant) [D19](#adr-019--storage-root-via-env-var) [D30](#adr-030--cancelamento-cooperativo-via-event) [D75](#adr-075--content-first-classification-no-upload-web) [D81](#adr-081--classificação-de-documentos-unificada-p2)

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
[D73](#adr-073--goals-como-entidade-versionada-não-config-estático) [D74](#adr-074--tasks-como-entidade-de-1ª-classe-fora-do-relatório) [D75](#adr-075--cutover-cli--web-estratégia-de-transição-faseada-com-adapters) [D77](#adr-077--pipeline-adapter-como-contrato-de-cutover-cli--web)

**Design System (F9):**
[D76](#adr-076--design-tokens-unificados-site--relatório) [D78](#adr-078--render-nativo-react--e6-como-exportador-standalone)

**Infra + Domínio (migração `plano_migracao_artifacts_db.md`):**
[D82](#adr-082--pipelineartifact-artefatos-computacionais-no-banco)
[D83](#adr-083--artifactstore-abstração-de-io-para-artefatos)
[D84](#adr-084--content-addressed-uploads)
[D85](#adr-085--eliminar-materialização-de-config-em-disco)
[D86](#adr-086--materializationbridge-adapter-temporário)
[D87](#adr-087--stagespec-dependências-declarativas)
[D88](#adr-088--stageconfig-configuração-imutável-por-parâmetro)
[D89](#adr-089--pipelinedomain-camada-de-domínio-isolada-de-io)
[D90](#adr-090--decimal-para-valores-monetários)
[D91](#adr-091--pydantic-para-domain-objects-com-coleções)
[D92](#adr-092--renomear-scripts-para-nomes-descritivos-de-domínio)
[D93](#adr-093--rename-completo-de-identificadores-de-stage-opção-a)
[D94](#adr-094--report-single-active-vs-versionado)
[D95](#adr-095--segurança-de-content_json-lgpd)
[D96](#adr-096--observabilidade-de-cutover)
[D97](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy)
[D98](#adr-098--caminho-b-pragmático-vs-puro-nomenclatura-oficial)
[D99](#adr-099--reuse-de-analyze_-legadas-em-main_with_store-decisão-de-a5da5e)
[D100](#adr-100--a6d-commitment-fechar-caminho-b-puro-nos-5-stages-pragmáticos)
[D101](#adr-101--princípios-r12-r17-ddd-solid-no-backend-api-a6e)
[D102](#adr-102--princípios-r18-r20-language-neutral-boundaries-a6f)
[D103](#adr-103--teste-manual-como-gate-antes-de-remoção-do-bridge-a6b5--a6-human)
[D104](#adr-104--e15c-em-caminho-b-pragmático-sessão-a5f)
[D105](#adr-105--llm-stages-escrevem-via-artifactstore-e1-e-e7-review-llm-não-migram-a6a)
[D106](#adr-106--opt-in-db-artifacts-por-workspace--dbartifactstore-no-celery-task-a6b)
[D107](#adr-107--remoção-de-materializationbridge-e-stage_runner_compat-a6c1-2)
[D109](#adr-109--auth-portability-jwt-hs256--fernet-documentados-como-contratos-portáveis-a6f5a)

**Infra de produção (F7):**
[D108](#adr-108--estratégia-de-subdomínios-mathomsai--cloudflare-dns)

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

**Decisão:** `Settings.STORAGE_ROOT` configurável via `MATHOMS_STORAGE_ROOT`. Default `./storage/`. No `.gitignore`.

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
- **Local:** users acumulam em `mathoms.db`; documented em `TESTING.md` que dev pode dar `./scripts/test_backend_up.sh --reset` para zerar

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
5. **Tipos de goal implementados**: `INDEPENDENCIA_FINANCEIRA` em F8.1; `APORTE_MENSAL`, `DOLARIZACAO`, `ALOCACAO_ALVO` em F8.5 (ver ADR-079). `PLANNING_CONTEXT` cobre as 23 seções restantes do `goals.json` como blob genérico via adapter.
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
   - **Grupo C — Documentação** (permanecem): `definitions.md`, `methodology.md`, `source_hierarchy.md`, `regras_composicao_patrimonial.md`, `report_layout.yaml`, `report_spec.md`. Nota: `manual_operacao.md` foi arquivado em `_archive/manual_operacao_v6.1.md` (versão agora em `pipeline.json::report_version`). `decisions.md` listado em Grupo A para migração ao DB.
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
- F8.4: checklist de cutover (backup → remoção de arquivos Grupo A → desabilitar entradas CLI do Makefile/documentação → atualizar docs relevantes)

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
- ✅ Uma identidade visual, um lugar para mudar. Mathoms AI vira produto coeso.
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

## ADR-077 — Pipeline adapter como contrato de cutover (CLI → Web)

**Status:** Decidido (F8.4) • **Data:** 2026-04-15

**Contexto:** As 4 fases anteriores (F8.0–F8.3) criaram entidades `Goal`, `Task`, `TaskSuggestion`, `TaskAttachment`, `FeatureFlag` no DB, endpoints REST, UI completa e testes. O pipeline legado (E5, E5.N, E6) continua lendo de `config/goals.json` e `config/tarefas.md`. O cutover precisa de uma ponte que permita ao pipeline operar via DB sem reescrevê-lo. Esta ADR formaliza o contrato dessa ponte.

**Decisão:**
1. **`backend/app/services/pipeline_adapter.py`** é a fachada única entre pipeline e DB. Expõe 3 pares de funções (sync + async):
   - `build_goals_payload` → dict compatível com `goals.json`
   - `build_tasks_payload` → dict compatível com E5 `tarefas[]`
   - `build_tarefas_md` → string markdown compatível com `config/tarefas.md`
2. **Worker beat** (`backend/app/tasks/periodic_tasks.py`) roda `scan_all_deadlines` diariamente via Celery beat schedule — substitui a necessidade de cron externo.
3. **Feature flags** (`FeatureFlag` + `feature_flags_service.py`) controlam rollout por workspace: `tasks_v2_enabled`, `task_attachments_enabled`, `report_tasks_snapshot_enabled`, `task_deadline_notifications_enabled`.
4. **Snapshot automático** (ADR-074 §F8.3): `pipeline_task._create_report_from_output` chama `build_snapshot_sync` — relatórios novos nascem com foto imutável das tasks.

**Contrato de cutover** — a remoção de `config/goals.json` e `config/tarefas.md` do repo acontece quando:
- [ ] O adapter cobre 100% dos campos lidos pelo E5/E5.N/E6 (seção `independencia_financeira` migrada em F8.1; `aportes`, `alocacao_alvo`, `dolarizacao` types adicionados em F8.4; restante de goals.json via `legacy_extras` parameter até cobertura total)
- [ ] Feature flag `tasks_v2_enabled` default ON para todas as workspaces
- [ ] Pipeline roda ciclo completo E0→E7 consumindo adapter (não arquivo) sem regressão
- [ ] Backup dos Grupo A (`_archive/pre-f8-cutover/`) + tag git

**Consequências:**
- ✅ Pipeline não precisa ser reescrito — consome adapter com mesmo contrato
- ✅ Cutover reversível via feature flag OFF (fallback para arquivo legado)
- ✅ Beat schedule descentraliza notificações — zero dependência de humano rodar scan
- ⚠️ Período de dual-source (DB + arquivo) até cobertura de 100% dos campos — aceito, mitigado pelo `_adapter_version` field que permite detectar payloads vindos do adapter vs. arquivo
- ❌ Scripts CLI (`scripts/e*.py`) ficam no repo como reference mesmo após cutover — remoção só em F9+ quando houver confiança de que a UI é autossuficiente

**Supersedes:** [ADR-075](#adr-075--cutover-cli--web-estratégia-de-transição-faseada-com-adapters) — esta ADR implementa e detalha o contrato declarado na 075.

---

## ADR-078 — Render Nativo React + E6 como Exportador Standalone

**Status:** Decidido (F9) • **Data:** 2026-04-15

**Contexto:**
O relatório financeiro era exibido via iframe carregando o HTML produzido pelo `e6_render.py` (4000 linhas, string replacement, Chart.js Canvas). Isso causava:
- Dissonância visual com o site (duas linguagens de design, cf. ADR-076)
- Limitações de UX: sem deep-links, search, dark mode sincronizado, a11y parcial
- Dependência de `doc.write()` + MutationObserver para scroll-spy e mode toggle
- Charts Canvas não imprimiam bem (fallback PNG manual no template)

**Alternativas:**
- **A** — Manter iframe, injetar CSS via postMessage. Resolve dissonância mas não UX.
- **B** — ✅ **Escolhida**: eliminar iframe, renderizar como rota Next.js nativa consumindo E5 JSON. E6 vira exportador HTML standalone (produto preservado).
- **C** — Reescrever E6 em React Server Components. Over-engineering; E6 faz um bom trabalho como gerador estático.

**Decisão:**

1. **Render primário**: rota Next.js `/reports/[id]` consome `GET /reports/{id}/data` (E5 JSON snapshot) e renderiza via componentes React com design tokens do ADR-076.
2. **Estrutura**: `report_layout.yaml` é fonte de verdade (codegen TS/Pydantic, F0.2.5). 18 seções em 3 modos (Estratégico S1-S10, Tático T1-T6, USA U1-U4).
3. **Charts**: Recharts (SVG) substituiu Chart.js (Canvas). SVG imprime nativamente — elimina fallback PNG.
4. **PDF server-side**: Playwright headless Chromium renderiza a rota React. Token efêmero (60s) para autenticação.
5. **E6 preservado**: `e6_render.py --html` continua gerando HTML standalone para 3 use cases: contador (email), backup (offline), impressão (sem app).
6. **Migration**: iframe removido; relatórios pré-F9 (sem `analysis_json_path`) redirecionam para download HTML.

**Componentes criados** (frontend/src/components/report/):
- Shell: ReportShell, ReportHeader, ReportToc, ReportModeProvider
- Cards: 13 componentes (Patrimonio, Fluxo, Investimentos, Previdencia, Pontos, etc.)
- Charts: 8 componentes Recharts + NarrativeChartCard genérico
- Infra: MonetaryValue (font-mono tabular-nums), card registry, chart registry

**Consequências:**
- ✅ Uma linguagem visual, uma codebase — fim da dissonância site × relatório
- ✅ Deep-links (`/reports/id?mode=usa#U2`), scroll-spy nativo, dark mode sincronizado
- ✅ SVG charts imprimem perfeitamente (zero workaround)
- ✅ Tipagem end-to-end: YAML → TS → componentes → runtime validated
- ✅ PDF server-side resolve o "salvar como PDF" que antes dependia de Cmd+P do browser
- ✅ E6 standalone preservado — valor real para contador e backup
- ⚠️ Playwright adiciona ~200MB ao container Docker (Chromium) — aceito para v1
- ⚠️ `e6_render.py` (4000 linhas) fica como código legado — aceito; mantém valor como exportador
- ❌ Sem export XLSX de tabelas (existia via iframe `table_to_sheet`). Recuperar como feature futura

**Supersedes parcial:**
- [ADR-033 "React components para report"](#adr-033--react-components-para-report) — era placeholder; esta ADR implementa a decisão com arquitetura completa.
- [ADR-035 "Media print para PDF export"](#adr-035--media-print-para-pdf-export) — media print continua como fallback mas Playwright é o caminho primário.

---

## Decisões pendentes

| #   | Decisão                           | Quando precisa | Opções                                                               |
| --- | --------------------------------- | -------------- | -------------------------------------------------------------------- |
| D8  | Pricing do premium                | Pós-beta       | R$29/mês / R$49/mês / R$99/mês                                       |
| D9  | Nome do produto                   | Pré-GA         | Mathoms AI (escolhido) / FinPlan / outros                                                |
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

## ADR-078 — Workspace sharing: convites, viewer role, forced logout

**Status:** Decidido (F9) • **Data:** 2026-04-15

**Contexto:** Dados financeiros familiares precisam ser compartilhados entre
membros da mesma família (casal, filhos adultos) e, no futuro, com
consultores financeiros. ADR-072 criou a infraestrutura de multi-tenancy
(`WorkspaceMember` com roles owner/member), mas não cobria o fluxo de
convite, o papel read-only, nem a invalidação de sessão ao remover um
membro. F9 endereça esses 3 gaps.

**Decisão:**

1. **3 roles fixos** (`owner`, `member`, `viewer`) com sets de conveniência
   (`WRITE_ROLES`, `MEMBER_ADMIN_ROLES`). Roles customizadas e escopos
   parciais (ex: "contador vê transações mas não metas") ficam como débito
   explícito.
2. **Convite por link copiável** (sem provider de email no V1). Backend gera
   token aleatório 256-bit, armazena `SHA-256(token)`, retorna token cru uma
   vez. Owner envia o link manualmente.
3. **`WorkspaceInvitation`** como entidade separada de `WorkspaceMember` —
   token + TTL 72h + uso único + revogável. Convite aceito cria membership.
4. **`require_role(allowed)` factory** em `tenancy.py` como dependency FastAPI.
   Reutiliza `workspace_member` já carregado por `get_current_workspace` (zero
   query extra). Pré-instanciados: `require_write_role`, `require_member_admin_role`.
5. **`User.token_version`** — claim `tv` no JWT. Incrementado ao remover membro.
   `get_current_user` rejeita tokens stale com `code: "token_revoked"` → frontend
   detecta e redireciona para login.
6. **Reuso de `AuditLog`** existente — sem tabela nova. Ações de membership usam
   convenção de naming (`workspace.member.invite`, `.accept`, `.remove`, etc).
7. **Default de role no convite: `viewer`** — upgrade para `member` é explícito.
   Convite como `owner` é bloqueado. Transferência de ownership é débito.
8. **Nomenclatura UI em PT-BR** — "Responsável" / "Coadministrador" / "Acompanha"
   (não "Owner/Admin/Viewer").

**Consequências:**

- ✅ Fluxo completo convite → aceite → membership funcional sem provider externo.
- ✅ Viewer read-only com enforcement duplo (backend 403 + frontend UI guards).
- ✅ Forced logout imediato ao remover membro — sem janela de exposição.
- ✅ 39 testes + tenancy lint cobrem a feature end-to-end.
- ⚠️ Convite manual (copiar link) é friction — email automático é F9.8.
- ⚠️ `token_version` bump invalida TODAS as sessões do user, não só a do workspace removido. Aceitável porque o user faz login de novo e acessa seus outros workspaces normalmente.
- ❌ Sem escopos parciais — um viewer vê tudo (metas, transações, patrimônio). Primeiro cliente consultor vai pedir isso.
- ❌ Sem transferência de ownership — bloqueado explicitamente nos services com mensagem clara.

---

## ADR-079 — Content-first classification no upload web

**Status:** Decidido • **Data:** 2026-04-15 • Supersedes D16 (parcialmente — D16 vale para CLI) • Nota: renumerado de ADR-075 (duplicado) para ADR-079

**Contexto:** O upload web classificava documentos pelo nome do arquivo (via `e0_route.classify_by_name`). Na prática, bancos brasileiros exportam PDFs/CSVs com nomes arbitrários ou genéricos (ex: `document.pdf`, `export_20260415.csv`). Resultado: ~65% dos uploads caíam no tipo "Outro".

**Alternativas avaliadas:**
1. **Filename regex (status quo)** — funciona no pipeline CLI onde o E0-route renomeia antes, mas inútil para uploads web crus.
2. **Sempre LLM** — precisão ~98%, custo ~$0,005/doc, latência +2s por upload, dependência de API key.
3. **Content-regex + LLM fallback (escolhida)** — regex sobre texto extraído (pdfplumber/openpyxl) cobre ~85% com confidence 1.0; LLM só para os ~15% ambíguos.

**Decisão:** Upload web classifica por **conteúdo extraído**, ignorando filename. Pipeline de 3 camadas: content-regex (confidence >= 0.8) → LLM fallback (>= 0.7) → `needs_review=true`.

**Consequências:**
- ✅ Precisão estimada ~97% com LLM ativo (era ~35% com filename).
- ✅ Filename não importa — drag-and-drop de qualquer export bancário funciona.
- ✅ `needs_review` flag permite fluxo humano-no-loop para casos ambíguos.
- ✅ Fuzzy dedupe (por `doc_type+bank_code+period`) complementa o exact dedupe por hash.
- ⚠️ Requer `anthropic` SDK + `ANTHROPIC_API_KEY` no env do backend. Sem a key, degrada para regex-only (~85%).
- ⚠️ Imagens (JPG/PNG) não podem ser classificadas por content-regex — vão direto para `needs_review`. OCR/vision é work futuro.
- ❌ Soft FK em `possible_duplicate_of_id` (sem constraint real) por limitação de alembic offline mode em SQLite. Dangling pointers são harmless — o JOIN retorna empty.

---

## ADR-080 — Pipeline incremental: extrair só docs novos, consolidar full

**Status:** Decidido (F7) • **Data:** 2026-04-16

**Contexto:** Com 96+ documentos, o pipeline reprocessava tudo do zero a cada execução — incluindo etapas caras de LLM (E1, E1.5, E2-llm). Após upload de 1 doc novo, rodar o pipeline completo desperdiçava tempo e custo. O modelo `Document` já tinha `pipeline_last_run_at` (adicionado na sync pós-pipeline), permitindo distinguir docs novos de já processados.

**Alternativas avaliadas:**
1. **Sempre full (status quo)** — simples, mas O(n) no custo/tempo com crescimento de docs.
2. **E0→E7 incremental puro** — processaria só docs novos em todas as etapas. Quebraria E3 (reconciliação cross-period) e E5 (análise consolidada).
3. **Híbrido: E0→E2 incremental + E3→E7 full (escolhida)** — extrai só novos (custo LLM proporcional a novos), consolida sobre todos os extracts (relatório sempre completo).

**Decisão:** Modo incremental (`POST /pipeline/run { incremental: true }`) filtra E0→E2 para docs com `pipeline_last_run_at IS NULL`. E3→E7 sempre rodam full sobre todos os E2_extracts existentes.

**Implementação:**
- `PipelineRun.incremental` (bool) + `incremental_doc_ids` (JSON) — rastreabilidade
- `WorkspaceContext.incremental` + `incremental_doc_paths` — propagação ao orchestrator
- `pipeline/stages/e2.py` — filtragem por stem matching dos stored_paths
- `GET /pipeline/new-doc-count` — endpoint leve para UI
- UI dinâmica: botão primary muda entre "Processar N novo(s)" e "Processar documentos"

**Consequências:**
- ✅ Custo de LLM proporcional a docs novos, não ao total do workspace.
- ✅ E3→E7 full garante reconciliação, categorização e análise sempre completas.
- ✅ Botão "Processar todos" mantido como fallback explícito.
- ⚠️ Se parser E2 for corrigido, extracts antigos ficam desatualizados — mitigado por "Processar todos".
- ⚠️ Stem matching entre stored_path e filename no filesystem pode falhar se renaming E0 for complexo — na prática, uploads web não passam por E0-route.
- ❌ E0 stages (unlock/audit/route) não são filtrados — operam em inbox (CLI flow). No web flow, inbox está vazio e eles fazem no-op naturalmente.

---

## ADR-079 — Multi-tenant Goals completos (APORTE_MENSAL, DOLARIZACAO, ALOCACAO_ALVO)

**Status:** Decidido (F8.5) • **Data:** 2026-04-16

**Contexto:**
Após F8.1 (ADR-073), apenas `INDEPENDENCIA_FINANCEIRA` tinha API + UI; os outros 3 tipos declarados em `VALID_GOAL_TYPES` ficavam como débito. O `config/goals.json` foi arquivado no cutover F8.4, mas sem UI para substituí-lo, workspaces sem seed travavam o pipeline com `ValueError: Estratégia de aportes não encontrada em goals.json` no E6. Diagnóstico: (1) E6 violava fail-safe defaults (duas funções com `raise` em vez de fallback); (2) não havia caminho multi-tenant para o usuário configurar aportes/dolarização/alocação via UI.

**Decisão:**
1. **Resiliência do E6**: `build_estrategia_aporte` e `_build_top5_decisoes_fallback` em `scripts/e6_render.py` passam a degradar graciosamente (warning + struct mínima) em vez de `raise ValueError`, alinhando com o padrão do resto do arquivo (`_build_riscos_fallback`, etc.). Banner CTA é injetado no HTML quando goals estão vazios.
2. **Backend F8.5** — API completa para os 3 tipos restantes, seguindo o padrão IF literalmente:
   - Schemas Pydantic em `backend/app/schemas/goal.py` (validadores: soma distribuição == meta, soma pcts alocação == 100)
   - `_GoalResponseBase` compartilhada por todos os Response types
   - Service funcs puras: `compute_aporte_derived`, `compute_dolar_derived`, `compute_alocacao_derived`
   - `create_goal_version` genérica (substitui duplicação de 3x `create_*_goal_version`)
   - `get_current_goal_typed` / `get_goal_history_typed` via mapa `_GOAL_TYPE_CLASSES`
   - 12 endpoints: POST compute, GET current, GET history, PUT upsert (por tipo)
3. **Frontend F8.5**:
   - 3 edit pages + 3 wizards em `frontend/src/app/(app)/plano/{aportes,dolarizacao,alocacao}/`
   - Types + 12 funções API client em `lib/api.ts`
   - `/plano` refatorada para dashboard multi-goal (grid 2×2 status cards) + banner CTA quando 0 goals configurados
4. **DOLARIZACAO usa câmbio hardcoded (`DEFAULT_CAMBIO_BRL_USD = 5.70`)** como MVP — override via `cambio_brl_usd` no compute request. Integração com API externa fica como débito futuro.
5. **ALOCACAO_ALVO valida soma=100** tanto no Pydantic (`model_validator`) quanto no endpoint (`valido` flag no compute response).

**Consequências:**
- ✅ Qualquer workspace pode configurar todas as 4 metas via UI sem depender de arquivo pré-seedado
- ✅ Pipeline nunca mais crasha por goals ausentes — degrada graciosamente com warning + banner CTA
- ✅ Refactor para generic helpers (`create_goal_version`, `get_current_goal_typed`) evita 3x duplicação mantendo backward compat com IF
- ✅ Fluxo end-to-end: UI → DB → adapter → `goals.json` materializado → E5/E6 → relatório
- ⚠️ Câmbio hardcoded em DOLARIZACAO fica desatualizado — aceito; override manual + débito futuro
- ⚠️ Validação de distribuição no APORTE é strict (soma == meta ±0.01) — usuário não pode salvar parcial
- ❌ PLANNING_CONTEXT (23 seções legadas) ainda sem UI — goals restantes (fase_f1f2, seguros, etc.) são seedados só via `seed_goals_full_ferreira_campos.py` ou permanecem vazios

**Arquivos críticos:**
- Backend: `backend/app/schemas/goal.py`, `backend/app/services/goal_service.py`, `backend/app/api/goals.py`
- Frontend: `frontend/src/lib/api.ts`, `frontend/src/app/(app)/plano/page.tsx`, `frontend/src/app/(app)/plano/{aportes,dolarizacao,alocacao}/{page,wizard/page}.tsx` (7 arquivos novos/refatorados)
- Pipeline: `scripts/e6_render.py` (resiliência + banner CTA)

---

## ADR-081 — Classificação de documentos unificada (P2)

**Status:** Decidido • **Data:** 2026-04-17

**Contexto:** O backlog P2 exige eliminar drift entre classificação no upload web, no pipeline (E0-route) e em reclassificação manual. Antes desta ADR, a lógica já era majoritariamente compartilhada via ``classify_document`` em ``document_processor.py``, mas o contrato não estava formalizado e o roteamento por nome (CLI sem backend) era um segundo caminho.

**Decisão:**

1. **Módulo único** ``backend/app/services/document_classification.py`` expõe:
   - ``classify_document(path, base_dir, use_llm=…) -> dict`` — regex sobre preview de conteúdo → LLM opcional → ``needs_review`` se confiança < 0,7;
   - ``ClassificationResult`` (Pydantic) com ``.as_dict()`` compatível com o formato histórico;
   - ``classification_can_route_to_data(dict)`` — gate para mover inbox → ``data/`` (exige ``dest_group`` + ``e0_doc_type`` e ``needs_review=False``);
   - ``map_e0_doc_type_to_document_type`` — mapa códigos E0 → ``DocumentType`` API.
2. **Entradas:**
   - **Upload web:** ``process_uploaded_document`` chama o classificador após unlock; JSON E1/E1.5 seguem detector estrutural (fora do classificador de PDF).
   - **Batch / inbox (``data/`` via CLI):** ``scripts/e0_route.route_file`` usa o **mesmo** ``classify_document`` quando o pacote ``backend`` é importável; caso contrário, fallback **filename regex + LLM** (legado documentado).
   - **Reclassificação:** ``POST /workspaces/.../documents/reclassify`` e ``backend.app.scripts.reclassify_documents`` chamam o mesmo ``classify_document``.
3. **LLM:** participa só como fallback quando a camada regex tem confiança < 0,8 e credenciais existem; erros de API são classificados (P1.4) em transiente/permanente no ``classification_meta``.
4. **Compatibilidade:** ``canonical_routing.rename_to_canonical`` / ``route_inbox_to_canonical_data`` continuam a receber o dict de classificação; ``POST`` de correção manual (tipo/banco) permanece o fluxo de ajuste quando a UI marca incerteza (P2.4).
5. **Paridade nome canônico:** testes garantem que ``build_final_name`` + ``classify_by_name`` reproduzem ``institution`` e ``doc_type`` para padrões representativos (evita drift pasta ↔ basename).

**Consequências:**

- ✅ Um lugar para evoluir limiares e meta de classificação.
- ✅ E0-route alinhado ao upload quando o worker/CLI roda com venv do projeto.
- ⚠️ CLI totalmente offline sem pacote ``backend`` mantém comportamento por nome — documentado como fallback.
- ❌ Linhagem por ``document_id`` por seção de relatório não é escopo desta ADR (F11.4a).

---

## ADR-082 — PipelineArtifact: artefatos computacionais no banco

**Status:** Decidido • **Data:** 2026-04-19 • **Status de execução:** [BACKLOG §Sprint A6](BACKLOG.md#sprint-a6--migração-infradomínio-plano-transversal)

**Contexto:** Artefatos intermediários do pipeline (E2–E7) viviam em
`storage/<ws>/processed/*.json` e o backend se referia a eles por convenção de
nome de arquivo (`_find_e2_extract`, `_e2_json_name`). Isso causava:

- Acoplamento frágil — renomear um arquivo quebra silenciosamente o backend.
- Modo incremental ambíguo — filtragem por stem matching permite dois E2 para o
  mesmo documento após reclassificação.
- Ausência de histórico auditável — sobrescrever é a única operação.
- Dificulta multi-tenant coerente — pastas por tenant mas linkage fora do DB.

**Decisão:** Nova tabela `pipeline_artifacts` como **fonte de verdade** para
artefatos computacionais do pipeline. Schema mínimo:

| Coluna | Tipo | Observação |
|---|---|---|
| `id` | INTEGER PK | autoincrement |
| `workspace_id` | FK workspaces, NOT NULL, indexed | CASCADE |
| `pipeline_run_id` | FK pipeline_runs, NOT NULL, indexed | CASCADE |
| `stage` | VARCHAR(50) NOT NULL | `"E2"`... (Fases 1-8); `"reconcile_transactions"`... (pós-9) |
| `artifact_key` | VARCHAR(255) NOT NULL | stem do doc (E2) ou nome canônico (E3+) |
| `document_id` | FK documents, nullable | só E2-* (SET NULL no delete) |
| `content_json` | JSON NOT NULL | JSONB em Postgres |
| `schema_version`, `byte_size`, `created_at` | — | metadados |

Constraints: `UNIQUE(pipeline_run_id, stage, artifact_key)` + índices em
`(workspace_id, stage, artifact_key)` e `document_id`.

`document_id` é preenchido apenas em stages de extração (E2-*); `ON DELETE
SET NULL` preserva histórico do artefato mesmo se o documento for apagado.

**Consequências:**
- ✅ Elimina regex em nome de arquivo em `document_pipeline_sync.py` (Fase 3.2).
- ✅ Modo incremental determinístico via `Document.pipeline_last_run_at`.
- ✅ FK garante integridade referencial (antes: stored_path vs. stored_path estimado).
- ✅ Histórico auditável — cada run cria novos artefatos; runs anteriores permanecem.
- ⚠️ `content_json` em SQLite não é queryable por campo interno (aceitável hoje).
- ⚠️ Dados sensíveis em `content_json` — endereçado em ADR-095 (LGPD, fase futura).

**Arquivos:** `backend/app/models/pipeline_artifact.py`,
`backend/alembic/versions/p4q5r6s7t8u9_pipeline_artifacts.py`,
`backend/tests/test_pipeline_artifact_model.py`.

---

## ADR-083 — ArtifactStore: abstração de I/O para artefatos

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 1.2 / 2.1

**Contexto:** Com `pipeline_artifacts` como nova fonte de verdade (ADR-082),
stages precisam de uma API comum que:
- Funcione tanto em CLI dev (disco, sem DB) quanto em web (DB).
- Seja testável em isolamento, sem banco nem disco.
- Respeite a fronteira arquitetural: `pipeline/` não importa SQLAlchemy
  (garantido por `dev/check_pipeline_boundaries.py`).

**Decisão:** `ArtifactStore` como **Protocol** (`@runtime_checkable`) em
`pipeline/artifact_store.py` com três implementações:

| Classe | Localização | Uso |
|---|---|---|
| `DiskArtifactStore` | `pipeline/artifact_store.py` | CLI dev, backward compat com `processed/` |
| `InMemoryArtifactStore` | `pipeline/artifact_store.py` | **Obrigatória** em testes de domain services |
| `DBArtifactStore` | `backend/app/services/db_artifact_store.py` | Web/Celery — sessão injetada pelo chamador |

Interface segregada (ISP): `ReadableArtifactStore` (read/list/exists) é um
subset para clientes só-leitura.

API canônica:
```python
store.read(stage, key) -> dict | None
store.list_keys(stage) -> list[str]
store.exists(stage, key) -> bool
store.write(stage, key, data, *, document_id=None) -> None
store.delete(stage, key) -> None
store.delete_stage(stage) -> int
```

`DBArtifactStore.__init__(session, workspace_id, pipeline_run_id)` — sessão é
**injetada** pelo chamador (Celery task abre, passa, fecha). O store não cria
nem fecha sessão — evita sessões órfãs e garante que toda a run compartilha
uma transação.

`WorkspaceContext.get_artifact_store()` retorna `DiskArtifactStore` por
default; web/Celery injetam `DBArtifactStore` via `for_tenant(artifact_store=)`.

Mapeamentos compartilhados `_STAGE_TO_DIR` e `_STAGE_TO_SUFFIX` (em
`pipeline/artifact_store.py`) formalizam a convenção legada de `processed/`
e servem tanto o `DiskArtifactStore` quanto o `MaterializationBridge`
(ADR-086). Invariante: `set(_STAGE_TO_DIR) == set(_STAGE_TO_SUFFIX)`.

**Consequências:**
- ✅ Services de domínio (Fase 6-8) testáveis sem fixtures de arquivo.
- ✅ Cutover gradual — flag `MATHOMS_USE_DB_ARTIFACTS` escolhe o store.
- ✅ Boundary `pipeline/` ↔ `sqlalchemy` preservada (DBArtifactStore fora).
- ⚠️ Três impls duplicam shape da API — protocolo garante paridade via testes.

**Arquivos:** `pipeline/artifact_store.py`,
`backend/app/services/db_artifact_store.py`,
`backend/app/repositories/pipeline_artifact_repository.py`,
`tests/unit/pipeline/test_artifact_stores.py`,
`backend/tests/test_db_artifact_store.py`,
`backend/tests/test_pipeline_artifact_repository.py`.

---

## ADR-084 — Content-addressed uploads

**Status:** Decidido • **Data:** 2026-04-18 • **Plano:** Fase 0

**Contexto:** Antes: `stored_path` usa o nome canônico
(`itau_extratoconta_202603-0_original.pdf`). Dois uploads distintos com nome
canônico idêntico (mesmo tipo + banco + período) sobrescreveriam o arquivo —
a deduplicação por `content_hash` já impedia salvar o mesmo hash duas vezes,
mas o upload legítimo de um **documento diferente** com o mesmo nome canônico
não era distinto no disco.

**Decisão:** Prefixar `stored_path` com os primeiros 12 hex do `sha256` do
conteúdo:

    itau_extratoconta_202603-0_original.pdf
    → a3f9c1b4d2e8_itau_extratoconta_202603-0_original.pdf

Aplicado em `scripts/e0_route.build_final_name` e
`backend/app/services/canonical_routing`. Migration
`o3p4q5r6s7t8_backfill_stored_path_content_hash` é **documentação-only**:
não renomeia arquivos existentes (risco desnecessário) — apenas novos uploads
adquirem o prefixo. Reclassificação de documento naturalmente aplica.

**Consequências:**
- ✅ Dois documentos diferentes com mesmo nome canônico ficam em paths distintos.
- ✅ `content_hash` do DB é consistente com o prefixo do path (auditável).
- ⚠️ Path visível ao usuário em logs tem um prefixo "enigmático" — aceitável (UI esconde).
- ❌ Documentos legados mantêm formato antigo — rename retroativo não é feito.

**Arquivos:** `scripts/e0_route.py`, `backend/app/services/canonical_routing.py`,
`backend/alembic/versions/o3p4q5r6s7t8_*.py`,
`backend/tests/test_content_addressed_upload.py`.

---

## ADR-085 — Eliminar materialização de config em disco

**Status:** Decidido (parcial — implementação na Fase 4) • **Data:** 2026-04-19
**Supersedes:** ADR-020

**Contexto:** ADR-020 materializava 5 configs editáveis em
`storage/<ws>/config/` a cada run para que scripts do pipeline lessem do
disco. Efeitos colaterais:

- Drift entre DB ↔ disco exige script de validação (`validate_adapter_parity.py`).
- I/O desnecessário a cada run.
- Acoplamento entre `config/` no disco e `PipelineConfig`/`FamilyMember`/…
  no DB.

Com `StageConfig` (ADR-088) passando config por parâmetro, a materialização
torna-se redundante.

**Decisão:** `StageConfig.from_context(ctx)` lê diretamente de
`ctx.config_overrides` (dict do DB, injetado em `for_tenant`) ou do disco
legado (CLI dev). `config_materializer.py` é no-op a partir da Fase 4 e removido
quando nenhum script legado depender mais dele.

`validate_adapter_parity.py` é reposto como validação DB ↔ `StageConfig`
(plano §12).

**Consequências:**
- ✅ Uma única fonte de verdade (DB em web, `config/` em CLI).
- ✅ Remove race condition entre materialização e execução.
- ⚠️ CLI dev continua lendo `config/<name>.json` — comportamento preservado.
- ❌ Scripts legados (Caminho A) ainda leem do disco — mitigado pelo bridge.

---

## ADR-086 — MaterializationBridge: adapter temporário

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 2.2 / 9.6

**Contexto:** Migrar todos os scripts legados (48-108KB cada) para escrita
direta no `ArtifactStore` simultaneamente é inviável. Precisamos de um
mecanismo que permita ao orquestrador usar `DBArtifactStore` enquanto os
scripts ainda leem/escrevem em `processed/*.json`.

**Decisão:** `MaterializationBridge` context manager em
`pipeline/materialization_bridge.py`:

```python
with MaterializationBridge(store, pipeline_run_id=run_id) as bridge:
    root_dir = bridge.hydrate_for_stage("E3")   # DB → tmp/processed/E2_extracts/
    legacy_script(root_dir=root_dir)
    bridge.persist_from_stage("E3")             # tmp/processed/E3_reconciled/ → DB
```

- Hidratação consulta `StageSpec.reads` (sem lógica por stage hardcoded).
- Persistência consulta `StageSpec.writes`.
- Diretório efêmero `/tmp/fin_pipeline_{run_id}/` limpo no `__exit__` (mesmo
  em exception).
- Orquestrador detecta o tipo do store via helper
  `pipeline.stage_runner_compat.run_legacy_with_bridge_if_db`: `DiskArtifactStore`
  → roda com `root_dir=ctx.root`; outro store → bridge.

**Consequências:**
- ✅ Cutover stage-por-stage sem reescrever scripts pesados.
- ✅ Mesma bridge serve E3, E4, E5, E5.N, E7 — zero duplicação.
- ⚠️ I/O duplo (DB → disco → DB) em cada stage — overhead aceitável durante
  cutover; medido em Fase 1.4 (baseline).
- ❌ Temporário por contrato: removido na Fase 9.6 quando todos os stages
  estiverem no Caminho B. Guardrail: `grep -r MaterializationBridge` deve
  retornar zero antes da Fase 9.6.

**Arquivos:** `pipeline/materialization_bridge.py`,
`pipeline/stage_runner_compat.py`,
`tests/unit/pipeline/test_materialization_bridge.py`,
`tests/unit/pipeline/test_stage_runner_compat.py`.

---

## ADR-087 — StageSpec: dependências declarativas

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 1.5

**Contexto:** `pipeline/orchestrator.py` mantinha `FROM_MAP` manualmente —
inserir um stage entre E3 e E4 exigia editar `FULL_ORDER`, `FROM_MAP`
(calculado à mão), `DETERMINISTIC_ORDER` e `_get_stage_runner()`, propenso a
erros silenciosos. Bug real: `E2-faturas` e `E2-extratos` mapeavam para o
mesmo `e2.run(ctx)` sem flags — ambos processavam tudo.

**Decisão:** `pipeline/stage_spec.py` com:

```python
@dataclass(frozen=True)
class StageSpec:
    name: str
    reads: tuple[str, ...]     # stages de input
    writes: tuple[str, ...]    # stages de output
    is_llm: bool = False
    tier: str = "free" | "premium"

STAGE_REGISTRY: dict[str, StageSpec] = { ... }  # Nomes legados nas Fases 1-8
VIRTUAL_ARTIFACT_STAGES = frozenset({"E5-revised"})  # não executáveis
FULL_ORDER = [...]                                   # decisão explícita do orquestrador
DETERMINISTIC_ORDER = [s for s in FULL_ORDER if not STAGE_REGISTRY[s].is_llm]
```

- `build_from_map(order)` deriva `FROM_MAP` sem manutenção manual.
- `validate_full_order(FULL_ORDER)` é chamado no import — falha rápido
  (`AssertionError`) se uma dependência é consumida antes de ser produzida.
- `validate_artifact_stage(stage)` aceita executável + virtual, rejeita
  desconhecido.
- `E2-faturas`/`E2-extratos` têm wrappers separados (`e2_faturas.py`/`e2_extratos.py`)
  que chamam `e2.run(ctx, faturas_only=True)` / `extratos_only=True`.

**Consequências:**
- ✅ Adicionar stage = uma linha no REGISTRY + uma posição no FULL_ORDER.
- ✅ Inconsistências de ordem são detectadas no startup, não em runtime.
- ✅ Três artifact stages distintos para E2 (`extract_statements`/`extract_invoices`/`extract_with_llm`)
  evitam colisão de `UNIQUE(run, stage, key)` quando o mesmo documento é
  processado por extrator determinístico + LLM fallback.
- ⚠️ Nomes legados `"E2"`, `"E3"`, `"E5"` permanecem até Fase 9 (renaming em
  bloco via `STAGE_RENAME_MAP`).

**Arquivos:** `pipeline/stage_spec.py`, `pipeline/orchestrator.py`,
`pipeline/stages/e2_faturas.py`, `pipeline/stages/e2_extratos.py`,
`tests/unit/pipeline/test_stage_spec.py`.

---

## ADR-088 — StageConfig: configuração imutável por parâmetro

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 1.5.5

**Contexto:** `scripts/pipeline_common._init_config(base_dir)` reescrevia 12+
variáveis globais a cada reinicialização. Celery com processos separados é
seguro hoje, mas é uma bomba-relógio para qualquer mudança de topologia de
workers (multi-thread, async). Além disso, `from_context` silenciava
config faltante (`or {}` silenciava bugs de deploy).

**Decisão:** `pipeline/stage_config.py` com Pydantic `BaseModel` +
`ConfigDict(frozen=True)`:

```python
class StageConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    family_members: dict = {}
    pipeline: dict = {}
    institutions: dict = {}
    categorization: dict = {}
    goals: dict = {}
    scoring: dict = {}
    fiscal: dict = {}

    REQUIRED = frozenset({"family_members", "pipeline", "institutions", "categorization"})
```

- Pydantic frozen **deep-copia** na construção — imutabilidade verdadeira
  mesmo com campos dict/list (dataclass frozen só proíbe reassignment).
- `from_context(ctx)` **falha rápido** com `ConfigError` quando um dos 4
  `REQUIRED` está ausente. Campos opcionais (`goals`, `scoring`, `fiscal`)
  degradam para `{}` silenciosamente.
- `empty()` é o factory para testes que não precisam de config real.
- Thread-safe por construção — pode ser compartilhada entre workers.

**Regra geral de imutabilidade no plano (R11):**

| Tipo de objeto | Padrão | Motivo |
|---------------|--------|--------|
| Campos primitivos (str, int, Decimal, date) | `@dataclass(frozen=True)` | Sem dep extra |
| Campos dict/list (StageConfig) | Pydantic frozen | Deep-copy real |
| Campos `list[ValueObject]` que mutam (BankStatement.transactions) | dataclass não-frozen com invariante | Mutação restrita |

**Consequências:**
- ✅ `_init_config()` global removível na Fase 9.6.
- ✅ Config ausente quebra deploy imediatamente em vez de produzir output
  silenciosamente degradado.
- ⚠️ Todos os stages recebem o `StageConfig` completo mesmo quando só usam
  um subset — ISP é aplicado nos **domain services** (ADR-089).

**Arquivos:** `pipeline/stage_config.py`,
`tests/unit/pipeline/test_stage_config.py`.

---

## ADR-089 — pipeline/domain/: camada de domínio isolada de I/O

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 5

**Contexto:** Transações, extratos, patrimônio viviam como `dict` genéricos.
Mudar a estrutura de uma transação exigia grep em múltiplos scripts. Lógica
de reconciliação, categorização e análise estava acoplada a I/O de disco —
testar "transações de mesmo valor em ±3 dias são duplicatas" exigia montar
fixtures de arquivo.

**Decisão:** Nova camada `pipeline/domain/`:

```
pipeline/domain/
  models/
    transaction.py     Money, Transaction
    document.py        BankStatement, Investment, InvestmentStatement, BaselinePatrimonial
  services/
    reconciliation_service.py  ReconciliationService(ReconciliationConfig)
    categorization_service.py  CategorizationService(CategorizationRules)
    calculators.py             CashFlowAggregator, PatrimonioCalculator,
                               EmergencyReserveCalculator, FinancialScoreCalculator
```

- **Value objects** (`Money`, `Transaction`, `Investment`, `Baseline`) são
  frozen dataclasses — "modificar" produz novo objeto via
  `dataclasses.replace`. `BankStatement.transactions` é `list` mutável
  restrito ao pipeline de reconciliação (invariante documentado).
- **Services** são **puros** — sem I/O de disco, sem globals. Recebem
  `(config_value_object, input_value_objects)`, retornam output.
- Services NÃO recebem `StageConfig` inteiro (R9 / Interface Segregation):
  `ReconciliationService(ReconciliationConfig)`,
  `CategorizationService(CategorizationRules)`.
- Services são testáveis com `InMemoryArtifactStore` + fixtures de 3 linhas.

**Consequências:**
- ✅ Lógica de domínio testável em isolamento — fixtures não são arquivos.
- ✅ Contrato tipado expõe o modelo mental do domínio financeiro.
- ✅ Extensões futuras (reconciliação multi-moeda, novo tipo de ativo)
  ficam localizadas no domínio.
- ⚠️ Scripts legados (Caminho A) continuam trabalhando com `dict` até migração.

**Arquivos:** `pipeline/domain/**`,
`tests/unit/pipeline/test_domain_money.py`,
`tests/unit/pipeline/test_domain_transaction_document.py`,
`tests/unit/pipeline/test_reconciliation_service.py`,
`tests/unit/pipeline/test_categorization_service.py`,
`tests/unit/pipeline/test_calculators.py`.

---

## ADR-090 — Decimal para valores monetários

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 5.2

**Contexto:** `float` tem imprecisão binária — `0.1 + 0.2` é
`0.30000000000000004`. Somas de centenas de transações acumulam erro.
Valores financeiros exigem precisão exata.

**Decisão:** `Money` (frozen dataclass) com `amount: Decimal` + `currency: str`.

Regras firmes:
- **Construtor** rejeita `float` com `TypeError`. `Money(0.1, "BRL")` quebra.
- **Factory** `Money.of(value, currency)` aceita `str | Decimal | int` — também
  rejeita `float`. Dev com float deve converter explicitamente:
  `Decimal(str(v))` no call-site.
- **Precisão por moeda** via `CURRENCY_PRECISION: dict[str, int]`:
  BRL=2, USD=2, EUR=2, JPY=0. `Money.of("1.234", "BRL")` → `Decimal("1.23")`.
- **Operadores** `+`, `-`, `neg`, `*` (rejeita float), `<`, `<=`, `==`. Moedas
  incompatíveis levantam `ValueError`.
- **Serialização:** `to_float()` existe apenas para JSON legado — documentado
  como "não usar em cálculos".

**Consequências:**
- ✅ `Money.brl("0.1") + Money.brl("0.2") == Money.brl("0.3")` (exato).
- ✅ Erros de arredondamento localizados no serializador, não acumulados.
- ✅ Moedas multi-precisão funcionam — JPY tem 0 casas, BRL 2.
- ⚠️ Conversão de `float` → `Decimal(str(v))` no call-site é carga de
  adoção — intencional, para que o dev veja o trade-off.
- ❌ Schemas JSON existentes continuam com `float` — adaptadores usam
  `to_float` / `Decimal(str(v))`.

---

## ADR-091 — Pydantic para domain objects com coleções

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 5 / R11

**Contexto:** Python dataclasses frozen só proíbem reassignment — mutação
interna de campos `dict`/`list` ainda é possível (`obj.rules["new"] = "x"`).
Para `StageConfig` (com 7 campos dict), isso é inaceitável.

**Decisão:** Regra de imutabilidade por tipo de objeto:

| Objeto | Escolha | Motivo |
|---|---|---|
| `Money`, `Transaction`, `Investment`, `Baseline`, `ReconciliationConfig`, `CategorizationRules`, `StageSpec` | `@dataclass(frozen=True)` | Campos primitivos + tuples — dataclass suficiente |
| `StageConfig` | `pydantic.BaseModel` + `ConfigDict(frozen=True)` | Campos dict — pydantic deep-copia na construção |
| `BankStatement` | `@dataclass` (não-frozen) | `transactions: list` muta pela lógica do pipeline; invariante documentado |

Services domain (`ReconciliationService`, `CategorizationService`, calculadoras)
consomem os value objects e retornam `@dataclass(frozen=True)` para reports
(`CashFlowReport`, `PatrimonioReport`, etc.).

**Consequências:**
- ✅ Tipos em `pipeline/domain/models/` e `pipeline/domain/services/calculators.py`
  são seguros para compartilhar entre threads.
- ✅ Pydantic frozen bloqueia `model.pipeline = {}` em runtime — `ValidationError`.
- ⚠️ Pydantic adiciona overhead (~100μs/construção) — irrelevante em workloads
  de pipeline (segundos-minutos por stage).

---

## ADR-092 — Renomear scripts para nomes descritivos de domínio

**Status:** Proposto (execução na Fase 9 pós-Caminho B dos stages) • **Data:** 2026-04-19 • **Plano:** Fase 9.4

**Contexto:** Scripts em `scripts/` usam o padrão `eN_nome.py` (ex: `e3_reconcile.py`,
`e5_analyze.py`). O número implica posição na fila — responsabilidade do
orquestrador, não do arquivo. Conflita com o rename de stage identifiers
(ADR-093) e acopla o nome do arquivo à ordem de execução, dificultando
refactor.

**Decisão:** Renomear os scripts para nomes descritivos de domínio usando
`git mv` (preserva histórico):

| Antes | Depois |
|---|---|
| `scripts/e0_audit.py` | `scripts/document_auditor.py` |
| `scripts/e0_route.py` | `scripts/document_router.py` |
| `scripts/e0_unlock.py` | `scripts/document_unlocker.py` |
| `scripts/e15_consolidate.py` | `scripts/baseline_consolidator.py` |
| `scripts/e2_extract.py` | `scripts/transaction_extractor.py` |
| `scripts/e3_reconcile.py` | `scripts/transaction_reconciler.py` |
| `scripts/e4_categorize.py` | `scripts/transaction_categorizer.py` |
| `scripts/e5_analyze.py` | `scripts/financial_analyzer.py` |
| `scripts/e5n_narrativas.py` | `scripts/narrative_generator.py` |
| `scripts/e6_render.py` | `scripts/report_renderer.py` |
| `scripts/e7_review.py` | `scripts/quality_reviewer.py` |

Wrappers em `pipeline/stages/` também são renomeados (ver ADR-093).

**Pré-requisito:** Fases 5-8 completas (stages em Caminho B). Renomear antes
mantém o sistema consistente, rename antecipado cria estado misto perigoso.

**Consequências:**
- ✅ Nomes descrevem a operação de domínio, não a posição na fila.
- ✅ `git mv` preserva histórico — blame funciona.
- ⚠️ Imports em todo o codebase precisam ser atualizados (guardrail: grep
  survivors no CI da Fase 9.5).
- ❌ Scripts de automação externos (cron, CI externo) que invocam
  `python scripts/eN_*.py` quebram — 1 release de alias em `e_reset.py`
  mitiga parcialmente.

---

## ADR-093 — Rename completo de identificadores de stage (Opção A)

**Status:** Infraestrutura pronta • **Execução:** pós-Fases 5-8 completas
**Data:** 2026-04-19 • **Plano:** Fase 9 inteira

**Contexto:** Os identificadores legados (`"E0-audit"`, `"E1.5c"`, `"E2-faturas"`,
`"E5"`, `"E7-apply"`…) são posicionais e opacos sem contexto. Aparecem em
código (strings literais), DB (coluna `pipeline_artifacts.stage`), logs,
flags de CLI (`--from E3`), dashboards. O mapeamento para nomes descritivos
é 1:1, documentado em `STAGE_RENAME_MAP` (ADR-087) — mas renomear em produção
exige coordenação entre código, DB, dev-ops e docs.

**Decisão:** Aplicar **Opção A — rename em bloco** em 7 sub-fases (Fase 9 do plano):

1. **9.0** — Auditoria: `_scratch/audit_stage_references.py` lista ocorrências;
   teste `test_rename_map_covers_all_legacy_names` garante `STAGE_RENAME_MAP` exaustivo.
2. **9.1** — `git mv pipeline/stages/e*.py → *descriptive*.py` (17 wrappers).
3. **9.2** — Substituir strings literais em Python um arquivo por vez,
   com `pytest` entre cada.
4. **9.3** — Alembic migration `q5r6s7t8u9v0_rename_stage_identifiers`:
   `UPDATE pipeline_artifacts SET stage = <new> WHERE stage = <old>` +
   idem para `pipeline_stage_logs`. Upgrade+downgrade testados
   (`test_stage_rename_migration.py`, 5 testes).
5. **9.4** — `git mv scripts/e*.py → *descriptive*.py` + `e_reset.py --from X`
   alias de compat por 1 release.
6. **9.5** — Guardrail: `tests/unit/pipeline/test_no_legacy_stage_names.py`
   (parametrizado por todos os legados) com soft-fail default + hard-fail
   via `MATHOMS_ENFORCE_STAGE_RENAME=1`.
7. **9.6** — Remover `MaterializationBridge`, `_init_config()` global, aliases.

**Mapa canônico** (fonte de verdade: `pipeline.stage_spec.STAGE_RENAME_MAP`):

```
E0-audit    → audit_documents        E2-extratos → extract_statements
E0-unlock   → unlock_documents       E2-llm      → extract_with_llm
E0-route    → route_documents        E3          → reconcile_transactions
E1          → extract_members        E4          → categorize_transactions
E1.5        → extract_baseline       E5          → analyze_finances
E1.5c       → consolidate_baseline   E5.N        → generate_narratives
E2-faturas  → extract_invoices       E6          → render_report
                                     E7-crossval → validate_cross
                                     E7-review   → review_finances
                                     E7-apply    → apply_review
                                     E6-final    → render_final_report
                                     E5-revised  → analyze_finances_revised
```

**Procedimento em produção** (pré-migration):
1. Backup obrigatório (`sqlite3 mathoms.db .dump > backup.sql`).
2. Verificar: `SELECT DISTINCT stage FROM pipeline_artifacts` — nenhum
   nome fora do mapa (investigar antes de prosseguir).
3. Deploy do código pós-Fase 9.2 com alias compat.
4. `alembic upgrade head`.

**Consequências:**
- ✅ Nomes descritivos em logs/dashboards — engenheiro novo entende sem consultar tabela.
- ✅ Mapa exaustivo testado bloqueia divergência silenciosa.
- ⚠️ Queries hardcoded externas (Grafana, Retool) quebram — comunicar antes.
- ⚠️ Uma janela de manutenção para migration — `pipeline_artifacts` pode ser grande.
- ❌ Aliases de compat em `e_reset.py` são técnica-debt temporária.

**Artefatos:** `pipeline/stage_spec.py::STAGE_RENAME_MAP`,
`backend/alembic/versions/q5r6s7t8u9v0_rename_stage_identifiers.py`,
`backend/tests/test_stage_rename_migration.py`,
`tests/unit/pipeline/test_no_legacy_stage_names.py`,
`_scratch/audit_stage_references.py`.

---

## ADR-094 — Report: single-active vs. versionado

**Status:** Decidido (single-active para F9; evolução planejada) • **Data:** 2026-04-19 • **Plano:** §4.5

**Contexto:** Com artefatos migrando para `pipeline_artifacts` (ADR-082),
a coluna `Report.analysis_json_path` (string apontando para arquivo) passa
a ser `Report.artifact_id` (FK opcional para o E5 da run). Re-run do pipeline
cria um novo `PipelineArtifact` E5; precisamos decidir se o Report aponta
para o **novo** (overwrite) ou mantém **histórico versionado**.

**Alternativas:**
1. **Single-active** (escolhida para F9): um relatório ativo por workspace;
   re-run sobrescreve o ponteiro.
2. **Versionado** (iteração futura): nova tabela `ReportVersion` com FK para
   Report + pipeline_run_id; UI pode mostrar múltiplas versões.

**Decisão:** **Single-active** na Fase 4 do plano de migração. Justificativas:

- Simplicidade: Report.artifact_id é a única FK de relatório.
- UI sem decisão "qual versão mostrar" (atual sempre válida).
- Os `PipelineArtifact`s históricos permanecem no banco — não há perda
  de dados, apenas ausência de apresentação.
- Menor peso no DB: um ponteiro ativo por workspace.

**Caminho evolutivo previsto (não este sprint):**

1. Fase 4: single-active entregue.
2. Sprint futuro: introduzir `ReportVersion(report_id, pipeline_run_id, artifact_id, created_at)`
   — todos os dados necessários já existem em `pipeline_artifacts`.
3. Decisão guiada por métrica de produto: % de usuários que consultam
   relatórios anteriores via workarounds (export HTML, screenshots).

**Consequências:**
- ✅ Fase 4 cabe num sprint (~5 dias).
- ✅ UI inalterada — migração transparente para o usuário.
- ⚠️ Histórico só acessível via query/script até ReportVersion existir.
- ❌ Usuários que re-rodam e querem comparar com versão anterior precisam
  exportar HTML antes do re-run (documentado em release notes).

---

## ADR-095 — Segurança de `content_json` (LGPD)

**Status:** Proposto (execução distribuída em Fases 1-4 do plano) • **Data:** 2026-04-19 • **Plano:** §15

**Contexto:** `pipeline_artifacts.content_json` armazena dados financeiros
pessoais — saldos, transações, CPFs (via membros), posições de investimento.
Postgres TDE protege contra roubo de disco físico, **não** contra SQL
injection ou leak de backup lógico. LGPD Art. 18 exige direito ao
esquecimento em até 24h úteis. A v3.3 do plano não endereçava — v3.4 formaliza
em §15.

**Decisão:** Cinco políticas complementares:

**D1 — Criptografia app-level em campos de PII.** CPF e nome completo em
`content_json` são armazenados como `enc:<base64>` via `cryptography.fernet`.
Chave em `MATHOMS_PII_ENCRYPTION_KEY` (secret manager). Read path:
`PipelineArtifactRepository.read_decrypted` faz decrypt on-demand. Deploy
sem a chave em produção **falha**.

**D2 — Não criptografar valores monetários.** Criptografar `amount` quebra
agregações SQL e torna relatórios O(n) em memória. Risco aceitável: valores
sem nome/CPF têm baixa identificabilidade isolada. Proteger via controles
de acesso (D3).

**D3 — Audit log em acesso a `pipeline_artifacts`.** Toda leitura via API
(`GET /reports/{id}/data`, etc.) registra em `access_audit_log`
(tabela nova): `user_id, workspace_id, artifact_id, timestamp, ip`.
Retenção: 1 ano. Consultado em incident response.

**D4 — Política de retenção.** Artefatos ativos: indefinido (user pode
deletar via `/workspace/delete`). Artefatos de runs não-ativas: 2 anos →
soft delete. Direito ao esquecimento: `DELETE /workspace/{id}/artifacts`
remove TODOS os `pipeline_artifacts` + `documents.*_content` em até 24h úteis.

**D5 — Masking em logs.** `DBArtifactStore.read/write` log sem `content_json`
em nível INFO; nível DEBUG só em dev. Nomes de membros viram `member_<hash[:6]>`
em logs estruturados.

**Implementação por fase:**

| Fase | Entregável |
|------|-----------|
| Fase 1 | `PipelineArtifact.content_json` JSONB + `schema_version`; sem crypto ainda ✅ |
| Fase 2 | `PipelineArtifactRepository` encapsula queries; crypto hooks preparados (no-op default) ✅ |
| Fase 3 | Crypto ativa para `extract_members` (piloto com CPF mascarado) — **pendente** |
| Fase 4 | Audit log em 100% dos GETs; endpoint esquecimento — **pendente** |
| Fase 4+ | Estender crypto para demais stages conforme volume — **pendente** |

**Consequências:**
- ✅ LGPD Art. 18/46 atendidos explicitamente.
- ✅ Defense-in-depth: crypto app-level + TDE (prod) + audit log.
- ⚠️ Deploy exige gestão segura de chave (secret manager, KMS em prod).
- ❌ Crypto quebra queries `JSON_EXTRACT` em campos PII — mitigado por
  indexação separada (hash searchable quando necessário).

---

## ADR-096 — Observabilidade de cutover

**Status:** Proposto (execução paralela à Fase 2) • **Data:** 2026-04-19 • **Plano:** §16

**Contexto:** §4.6 do plano descreve o **procedimento** de cutover, mas não
**como detectar** que deu errado. Ativar `MATHOMS_USE_DB_ARTIFACTS=True` em
workspace com dados históricos precisa de validação contínua — ficaria
invisível se diferenças estruturais aparecessem no output.

**Decisão:** Kit operacional de 4 peças:

**1. Script de comparação disk-vs-db** — `_scratch/compare_disk_vs_db.py`:

```
python compare_disk_vs_db.py --workspace-id <uuid> [--stage STAGE] [--strict]

Saída:
  - 0: sem diff estrutural
  - 1: diff detectado (com detalhes)
  - 2: erro de leitura (um dos stores não tem o artifact)
```

Lista `(stage, key)` em cada store; para cada par presente nos dois, compara
estruturalmente com tolerância para floats. Reporta: artefatos só em disk,
só em DB, diferentes, idênticos.

**2. Métricas em produção** (`backend/app/observability/cutover_metrics.py`):

| Métrica | Tipo | Uso |
|---------|------|-----|
| `pipeline_run_duration_seconds{store="disk\|db"}` | Histogram | Regressão perf |
| `artifact_write_count{stage, store}` | Counter | Saúde de escrita |
| `artifact_read_missing{stage}` | Counter | Detectar cutover incompleto |
| `artifact_diff_count{stage}` | Counter | Incrementado pelo compare em job nightly |
| `pipeline_run_failed_total{stage, use_db}` | Counter | Taxa de falha por modo |

Expostas em `/metrics` (Prometheus). Dashboard durante janela de cutover
com os 5 painéis.

**3. Alertas**:

| Alerta | Condição | Ação |
|--------|----------|------|
| `CutoverRegression` | p95(duration_db) > baseline × 1.5 por 15min | Reverter deploy ou flag |
| `ArtifactReadMissing` | rate(read_missing) > 0 | Investigar |
| `DiskDbDiffDetected` | diff_count > 0 por stage | Pausar cutover |
| `PipelineFailureSpike` | rate(failed{use_db=True}) > 2× rate({use_db=False}) | Flip back |

**4. Runbook** — `docs/RUNBOOKS/cutover.md` com procedimento T-24h / T-0 / T+48h.

**Status de implementação:**

- Fase 1 entregou baseline placeholder em `tests/pipeline/perf/`.
- Scripts `compare_disk_vs_db.py`, métricas Prometheus, dashboard Grafana:
  **pendentes** — devem ser entregues antes de qualquer cutover em produção
  (pré-Fase 4.6).

**Consequências:**
- ✅ Cutover reversível com sinal claro de problema.
- ✅ Métricas contínuas validam paridade em background.
- ⚠️ Requer stack Prometheus/Grafana (não existe em dev hoje).
- ❌ Alertas dependem de receiver configurado (PagerDuty/Slack).

---

## ADR-097 — Extract-then-refactor: estratégia de decomposição de `e3_reconcile.py`

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 6 · Sessão A1 · ADR-089 (domain layer)

**Contexto:** `scripts/e3_reconcile.py` tem 1193 linhas com 30+ globals, lógica
bank-specific (faturas, CDBs), validações (saldo, gap temporal, baseline IRPF)
e orquestração misturadas. A estratégia "big-bang rewrite" — reescrever o
`main()` inteiro consumindo `ReconciliationService` — tem risco alto:

1. Bugs sutis em validações bank-specific só aparecem em produção.
2. Golden fixture cobre output final, não cada validator isoladamente.
3. Um sprint inteiro bloqueado sem entregar código testável em memória.

A alternativa — extrair validators/helpers **primeiro**, deixando o `main()`
legado intacto — permite progresso incremental com zero risco de regressão.

**Decisão:** Adotar **extract-then-refactor** como padrão para decomposição de
scripts legados grandes (E3, E4, E5). Ordem de trabalho:

1. **Extract**: mover cada responsabilidade para um domain service puro em
   `pipeline/domain/{models,services}/`, com:
   - Value objects tipados para config (ISP — R9) e warnings estruturados.
   - Testes unitários exaustivos com `InMemoryArtifactStore` (nenhuma fixture de arquivo).
   - Zero mudança em `scripts/e3_reconcile.py::main()` — script legado continua
     rodando via Caminho A (bridge).
2. **Compose**: `E3ReconcilerAdapter` (ou análogo) integra os services extraídos
   — testado end-to-end contra fixtures sintéticas.
3. **Refactor**: quando todos os blocos estiverem extraídos e testados, o
   `main_with_store(config, store)` substitui o legado. Golden fixture valida
   paridade. `MaterializationBridge` desliga para o stage.

**Sessão A1 (2026-04-19)** entregou Extract para E3 — 7 artefatos novos, **92
testes**, zero linha alterada em `e3_reconcile.py::main()`:

| Arquivo | Responsabilidade | Extraído de | Testes |
|---------|------------------|-------------|--------|
| `pipeline/domain/models/bank.py` | `BankCanonicalizer` + `canonicalize_bank()` — índice explícito `normalized_form → canonical_code`, strip acento/espaço/`/&` | `_BANCO_DISPLAY_TO_CANONICAL` dict-global em `_init_config` | 21 |
| `pipeline/domain/services/reconciliation_validators.py` | `SaldoContinuityValidator` (1ª metade de `validate_saldo_and_gaps`) + `TemporalGapDetector` (2ª metade); cada um com `*Config` dataclass ISP; retorna `SaldoGapWarning`/`TemporalGapWarning` estruturados | `validate_saldo_and_gaps()` | 32 |
| `pipeline/domain/services/baseline_validator.py` | `BaselineValidator` — compara `closing_balance` de `BankStatement` contra saldos IRPF 31/12 via `BankCanonicalizer`; value object `BaselineAccountSaldo` com factory `from_baseline_dict` (aceita `members`/`membros`, dict ou list) | `validate_against_baseline()` | 39 |
| `pipeline/domain/services/account_grouper.py` | `AccountGrouper` — skip rules + chave de conta canônica com `account_type_equivalences` | `group_by_account()` + skip logic | — |
| `pipeline/domain/services/statement_preprocessor.py` | `StatementPeriodNormalizer` (sintetiza período para faturas sem `periodo`) + `AnachronicTransactionDropper` (>180d antes do início) | Fatura period adjustment + anachronic guard | — |
| `pipeline/domain/services/e3_reconciler_adapter.py` (estendido) | Integra todos os services acima; `ReconciliationStoreResult` com warnings tipados + acesso dict-like retro-compat | — | — |

**Princípios fixados por esta ADR:**

- **D1. Warnings como dataclasses, não strings.** `SaldoGapWarning(account_key, expected, actual, diff)`
  tem `.format()` para render. Strings fazem parsing reverso em testes.
- **D2. Services não recebem `Path` nem `dict`.** Recebem `list[BankStatement]`
  ou value objects. Conversão `dict → BankStatement` é responsabilidade do
  adapter (`E3ReconcilerAdapter.load_bank_statements_with_warnings`).
- **D3. Config por service, não `StageConfig` inteiro.** Cada validator tem
  seu `*Config` dataclass frozen (ISP). Fixture de teste é uma linha.
- **D4. Zero mudança no script legado durante a fase Extract.** O `main()`
  segue intacto; golden fixture valida na fase Refactor.
- **D5. `E3ReconcilerAdapter` é mutável por injeção.** Todos os collaborators
  têm default seguro (`or default_factory()`), permitindo teste com subset.

**Consequências:**
- ✅ Sessão A1 entregou +92 testes em uma session sem risco de regressão em
  produção (719 pipeline passando, 0 regressão).
- ✅ Padrão reusável para Fases 7 (E4) e 8 (E5).
- ✅ Cada validator tem cobertura granular — bugs aparecem em unit test, não
  em golden fixture rodando 5 minutos.
- ⚠️ Existe uma janela onde services novos **coexistem** com lógica legada no
  script — o adapter é o único consumidor. Durante a janela, mudanças em
  ambos os lados exigem coordenação.
- ❌ Fase Refactor (substituir `main()` legado) ainda não foi feita — esta
  ADR cobre apenas a fase Extract. O golden fixture e o `main_with_store`
  ficam para sessão subsequente.

**Ordem de execução restante para completar Fase 6 (Caminho B):**
1. Implementar `reconcile_account()` equivalente em
   `E3ReconcilerAdapter.reconcile_via_store()` — hoje faz merge simples;
   precisa incorporar lógica fatura-specific legada.
2. Extrair `generate_output_filename()` para `BankCanonicalizer.output_filename(statement)`.
3. Capturar golden fixture do E3 legado em `tests/pipeline/goldens/e3/`.
4. Implementar `main_with_store(config, store)` em `scripts/e3_reconcile.py`.
5. Atualizar `pipeline/stages/e3.py` para não usar `run_legacy_with_bridge_if_db`.
6. Validar: golden fixture passa; zero regressão em 719+ testes.

**Artefatos:** `pipeline/domain/models/bank.py`,
`pipeline/domain/services/{reconciliation_validators,baseline_validator,account_grouper,statement_preprocessor,e3_reconciler_adapter}.py`,
`tests/unit/pipeline/test_{bank_canonicalizer,reconciliation_validators,baseline_validator,account_grouper,statement_preprocessor,e3_reconciler_adapter}.py`.

---

## ADR-098 — Caminho B pragmático vs puro: nomenclatura oficial

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 8 pós-A5e · §17.2.5

**Contexto:** A proposta original de "Caminho B" (§3.2 do plano, linha 1190)
definia "script refatorado: recebe `StageConfig` + `ArtifactStore`, **sem I/O
de disco**". Isso implicava remover `_init_config`, eliminar globals de módulo
e fazer funções puras de `analyze_*`. Na prática, as sessões A2 (E3), A4b (E4),
A5d (E5), A5e (E5.N+E7) entregaram **duas variantes distintas** sem
formalizar a distinção.

**E3 (A2)** seguiu a proposta original: `E3ReconcilerAdapter` integra 8
domain services (`BankCanonicalizer`, `SaldoContinuityValidator`, etc.),
helpers extraídos, lazy init dos globais (A3b).

**E4/E5/E5.N/E7** optaram por reutilizar as funções `analyze_*` legadas
dentro de `main_with_store(ctx)`, preservando globals (`_init_config`,
`_TITULAR_KEY`, `FAMILY_CONFIG`, `_MEMBROS`, `_TITULAR_NOME`, `_CONJUGE_NOME`,
`GOALS_CONFIG`, `SCORING_CONFIG`, `FISCAL_CONFIG`, `METRICS`). Trade-off:
paridade 100% garantida em golden, mas testabilidade e thread-safety dos
scripts não mudaram. Os 14+ domain services extraídos em A1/A3c/A5a/A5b/A5c
ficam em prateleira — 1200+ testes cobrindo código que não é invocado por
`main_with_store`.

**Decisão:** Formalizar duas variantes no plano:

| Variante | Stages | Características |
|---|---|---|
| **Caminho B puro** | E3 (A2) | Refactor com domain services integrados, helpers extraídos, lazy init |
| **Caminho B pragmático** | E4, E5, E5.N, E7 | I/O via `ArtifactStore` ✅ · Wrapper limpo sem `stage_runner_compat` ✅ · **Mantém** `_init_config` + globals + `analyze_*` legadas · Domain services em prateleira |

O Caminho B pragmático **não é débito técnico definitivo** — ADR-100 fixa
A6d como commitment de converter os 5 stages pragmáticos para puros.

**Consequências:**
- ✅ Documentação honesta evita que próximo dev pense que services estão integrados.
- ✅ Nomenclatura comum para referência cross-team.
- ⚠️ Reconhece dívida técnica pendente nos 5 stages pragmáticos.
- ❌ Aceita que ~3500 linhas de domain services + testes ficam em prateleira
  até A6d executar.

**Artefatos:** [ARCHITECTURE.md §17.1](ARCHITECTURE.md#171-caminho-b-puro-vs-pragmático-estado-atual-e-alvo) (Caminho B puro vs pragmático); `CLAUDE.md` "Caminho B puro vs pragmático"; `docs/CHANGELOG.md` entry Sessão A5e.

---

## ADR-099 — Reuse de `analyze_*` legadas em `main_with_store` (decisão de A5d/A5e)

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Sessões A4b, A5d, A5e
**Contexto de ADR-098** (Caminho B pragmático)

**Contexto:** Em A5d (E5), A4b (E4), A5e (E5.N+E7), o escopo de cada sessão
era "fechar Caminho B para este stage". A abordagem purista — reescrever
`analyze_patrimonio`, `analyze_fluxo_caixa`, `calculate_score`,
`build_narrativas`, `run_cross_validation` usando os domain services já
extraídos — teria custo estimado de 5-8 sessões adicionais por stage,
inviabilizando a fase dentro do sprint.

A alternativa pragmática: `main_with_store(ctx)` lê E4 + baseline via
`ArtifactStore`, invoca as funções `analyze_*` legadas (preservando globals),
serializa output via helpers novos (`e5_serialization.build_e5_output`),
escreve via `store.write(...)`. Paridade 100% garantida no golden.

**Decisão:** Aceitar o padrão "`main_with_store` reutiliza `analyze_*`
legadas" como trade-off explícito. Ganhos imediatos:

1. **Bridge eliminado** — `pipeline/stages/e5.py`, `e4.py`, `e5n.py`, `e7.py`
   não importam mais `stage_runner_compat`.
2. **I/O abstraído** — `ArtifactStore.read/write` em todos os stages.
3. **Golden de paridade garantido** — bugs sutis em funções legadas
   permanecem reproduzíveis.
4. **Domain services preservados como foundation** — testados, sem cliente.
   Serão integrados em A6d (ver ADR-100).

**Princípios fixados:**
- **D6. `main_with_store` pode chamar funções legadas.** Não é violação da
  arquitetura; é estratégia de transição.
- **D7. Serialização via helpers novos** — output shape controlado por
  `e5_serialization.py`, não por dict inline em `main()`.
- **D8. Globais via `_init_config(ctx.root)`** — `main_with_store` reinicia
  globals do módulo antes de invocar legados; preserva thread-safety por
  processo Celery (fork-based).

**Consequências:**
- ✅ Fase 8 fechada em cronograma realista (3 sessões: A5a, A5b, A5c, A5d, A5e).
- ✅ Testes de paridade rigorosos (tolerância 0.01 BRL) garantem
  equivalência semântica ao legado.
- ⚠️ Globais continuam existindo — thread-unsafety por processo (Celery fork
  workers mitiga, mas `gunicorn --threads` ou `asyncio.run_in_executor` seriam
  problemáticos).
- ❌ Testes dos `analyze_*` continuam exigindo fixtures de disco
  (`life_plan_goals.md`, `tarefas.md`, `milhas.md`, `methodology.md`).
- ❌ 14+ domain services em prateleira até A6d.

**Artefatos:** `scripts/e4_categorize.main_with_store`,
`scripts/e5_analyze.main_with_store`, `scripts/e5n_narrativas.main_with_store`,
`scripts/e7_review.main_with_store`; goldens de paridade
`tests/test_e4_main_with_store_parity.py`,
`tests/test_e5_main_with_store_parity.py`,
`tests/test_e5n_e7_main_with_store_parity.py`.

---

## ADR-100 — A6d commitment: fechar Caminho B puro nos 5 stages pragmáticos

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** §18 A6d
**Supersedes:** nota original de A6d como "opcional" no plano inicial

**Contexto:** ADR-099 deixa explícito que Caminho B pragmático é trade-off
temporário. A questão: converter ou não para puro?

Hoje 14+ domain services estão testados (1200+ testes) mas não invocados.
Custo de manter é baixo (já estáveis); custo de deletar seria perder
trabalho que tem valor arquitetural conhecido. Mas manter sem integrar é
**trabalho morto** — nunca paga seu custo.

Alternativas avaliadas:
- **Opção X** (integrar): executa A6d em 3-5 sessões grandes; fecha Caminho
  B puro; services passam a ser invocados. Valor arquitetural real.
- **Opção Y** (manter em prateleira indefinidamente): custo baixo, valor zero.
- **Opção Z** (deletar services): libera ~3500 linhas, mas perde
  investimento + bloqueia testabilidade futura.

**Decisão:** Executar **Opção X** (A6d) como commitment, não opcional.

Escopo de A6d dividido em 3 sub-fases:

**A6d.1 — Eliminação de globals nos 5 scripts** (padrão A3b replicado em
`e4_categorize`, `e5_analyze`, `e5n_narrativas`, `e7_review`,
`e15_consolidate`). Globais recebem defaults sensatos no módulo;
`_init_config(base_dir)` é opt-in via `main(root_dir=...)`. Teste estrutural
AST bloqueia regressão. ~1 sessão, ~20-30 testes.

**A6d.2 — Testabilidade dos `analyze_*` sem disco**. Extrair reads de
`life_plan_goals.md`, `tarefas.md`, `milhas.md`, `methodology.md` para shell;
funções ficam puras (recebem dict, retornam dict). Critério: `analyze_*`
testáveis com `{dict_input}` sem criar arquivo. ~2 sessões, ~60-80 testes.

**A6d.3 — Integração dos 14+ domain services em `main_with_store`**.
Refactor **por stage** (não big bang):
1. E4: `process_transactions` → composição `TransactionClassifier` +
   `CashFlowBuilder` + `BaselineNormalizer` + `InvestmentsConsolidator` +
   `E4CategorizerAdapter`.
2. E5.N: `build_narrativas` → composição (ou aceitar que E5.N é templating
   e manter legado).
3. E5: 13 `analyze_*` → `E5AnalyzerAdapter` (já existe desde A5c).
Cada refactor preserva golden de paridade. ~2-3 sessões grandes, ~200+ testes.

Ordem: A6d.1 → A6d.2 → A6d.3 (dependências: .2 depende de .1; .3 depende de .1+.2).

**Consequências:**
- ✅ Paga o investimento em foundation (A1/A3c/A5a/A5b/A5c).
- ✅ Testabilidade dos `analyze_*` habilita TDD futuro em mudanças de
  fórmulas financeiras.
- ✅ Elimina thread-unsafety dos globais — worker topology changes
  (gunicorn threads, asyncio pools) deixam de ser risco.
- ⚠️ Estimativa 3-5 sessões grandes — maior sessão continua sendo E5
  (1-2 sessões sozinha).
- ❌ Durante execução de A6d, risco de bug sutil em refactor (mitigado
  por golden de paridade).
- ❌ Bloqueia operacionalmente apenas LGPD/Obs **se** refactor quebrar —
  por isso A6d é independente de A6a-c e de §15/§16.

**Relação com A6a-e**: independente. Pode rodar em paralelo com cutover DB.
§15 (LGPD) e §16 (Observabilidade) não dependem de A6d.

**Artefatos:** [BACKLOG §A6d](BACKLOG.md#a6d--fechar-caminho-b-puro-nos-5-stages-pragmáticos-adr-100).

---

## ADR-101 — Princípios R12-R17: DDD/SOLID no backend API (A6e)

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** §18 A6e

**Contexto:** O plano P3 original focou em `pipeline/` + `scripts/`.
`backend/app/` seguiu padrões razoáveis de Python profissional, mas não
passou pela disciplina DDD/SOLID do pipeline. Auditoria (2026-04-19) mostra:

| Sintoma | Evidência |
|---|---|
| Routers pesados com lógica inline | `api/config.py` 935 linhas · `api/documents.py` 794 · `api/tasks.py` 481 · `api/goals.py` 468 · `api/pipeline.py` 421 |
| Repositórios quase ausentes | Apenas `PipelineArtifactRepository`; 10+ aggregates com queries SQLAlchemy espalhadas |
| DTOs confundidos com ORM | Endpoints retornam Pydantic espelhando SQLAlchemy |
| Sem camada de use cases | Services organizados por entidade, não por caso de uso |
| API sem versionamento | `/workspaces/...` direto, sem `/v1/` |
| Domain events ad-hoc | Notificações, task_progress inline em múltiplos lugares |

**Decisão:** Adicionar A6e como extensão formal do plano P3, com princípios
**R12–R17** (estendem R9-R11 do pipeline):

- **R12 (ISP no backend)** — endpoints retornam DTO dedicado, não ORM model.
- **R13 (Repositórios por aggregate)** — todo acesso a DB via
  `repositories/<aggregate>_repository.py`; routers não importam SQLAlchemy.
- **R14 (Routers finos)** — ≤50 linhas por router (teste estrutural
  enforça).
- **R15 (Application layer por use case)** — `backend/app/application/`
  com 1 módulo por caso de uso; testável sem DB via fakes.
- **R16 (Versionamento explícito)** — `/api/v1/` prefix; breaking changes
  coexistem em `/v2/`.
- **R17 (Domain events tipados)** — `backend/app/events/` com `Event` base
  + handlers registrados; side-effects desacoplados.

Escopo em 6 sub-fases (A6e.1 Repos → A6e.2 DTOs → A6e.3 Use cases → A6e.4
Routers finos → A6e.5 Versioning → A6e.events Events — renomeada de `A6e.6`
em 2026-04-22 para evitar colisão histórica com o Goal slice do track
per-aggregate). Estimativa: 5-7 sessões grandes, ~400+ testes novos.

**Consequências:**
- ✅ Backend ganha a mesma disciplina do pipeline. Qualquer feature nova
  segue padrão consistente.
- ✅ Repository pattern protege cutover DB — múltiplos backends de storage
  convivem sem fricção.
- ✅ Routers finos + codegen (A6f.2) reduzem bugs de integração frontend.
- ⚠️ Refactor de 4900 linhas de routers — trabalho mecânico mas demorado.
- ❌ Adiciona 2 diretórios novos (`application/`, mais repositories) —
  aumenta mental load para devs novos no repo.

**Relação com A6a-d/f**: independente. Recomendado depois de A6b (cutover
DB) para repository pattern entregar valor máximo.

**Artefatos:** [BACKLOG §A6e](BACKLOG.md#a6e--ddd-solid-no-backend-api-adr-101-r12-r17).

---

## ADR-102 — Princípios R18-R20: language-neutral boundaries (A6f)

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** §18 A6f

**Contexto:** Discussão estratégica (2026-04-19) sobre cenário hipotético
plausível: backend eventualmente migrado para Go, mantendo Python em
parsers (`scripts/e2/banks/`), LLM (`pipeline/llm/`) e domain services.

Hoje o backend Python importa funções do pipeline diretamente
(`from scripts.e3_reconcile import main_with_store`) — incompatível com
processos de linguagens diferentes. A fronteira entre backend e pipeline
precisa virar **contrato de rede ou mensageria**.

Alternativas avaliadas (3 categorias):
- **Categoria 1 — "no regret"** (valor independente de Go): pipeline-service
  HTTP, OpenAPI exaustivo, structured logs + OTel, DB schema review, Fernet
  → AES-GCM.
- **Categoria 2 — Go-specific com valor marginal**: contract tests, stateless
  rigoroso, broker neutro (substituir Celery), gRPC.
- **Categoria 3 — not yet**: port de domain services para Go, microserviços.

**Decisão:** Adicionar A6f com Categoria 1 + Categoria 2.4 (stateless
rigoroso). Princípios **R18–R20**:

- **R18 (Wire formats explícitos)** — zero pickle cross-process; JSON Schema/
  OpenAPI/Protobuf versionados em toda fronteira.
- **R19 (Stateless-ready)** — zero estado in-memory que impeça múltiplos
  workers concorrentes.
- **R20 (Language-neutral data)** — DB schema, JSON artifacts e message
  envelopes sem features Python-only.

**NÃO adotado nesta rodada**:
- Broker neutro (Celery mantido) — risco alto, ganho condicionado à Go real.
- gRPC — HTTP JSON + OpenAPI é suficiente para monolito→serviços separados.
- Port de domain services para Go — só durante migração real, não antes.

6 sub-fases (A6f.1 Pipeline-service → A6f.2 OpenAPI → A6f.3 OTel → A6f.4 DB
schema → A6f.5 Auth → A6f.6 Stateless). Estimativa: 6-8 sessões grandes.

**Consequências:**
- ✅ Todas as entregas têm valor independente (escala pipeline, debug real,
  best-practice cripto, horizontal scale).
- ✅ Migração Go futura sem retrabalho grande — fronteiras HTTP + OpenAPI
  prontas.
- ⚠️ Custo operacional em prod: +1 container (`pipeline-service`) +
  OTel collector.
- ⚠️ Fernet → AES-GCM exige data migration (mitigado: pouco PII hoje
  encriptado via Fernet).
- ❌ Adiciona latência HTTP ao pipeline (1 hop extra).

**Relação com A6a-e**: independente. Recomendado depois de A6b (cutover DB)
— pipeline-service precisa de DB como fonte de verdade.

**Artefatos:** [BACKLOG §A6f](BACKLOG.md#a6f--language-neutral-boundaries-adr-102-r18-r20).

---

## ADR-103 — Teste manual como gate antes de remoção do bridge (A6b.5 + A6-human)

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** §18 A6b.5/A6-human

**Contexto:** A sequência original do plano era A6b (cutover DB validado
tecnicamente) → A6c (deletar bridge). Na auditoria de 2026-04-19 surgiram
2 pontos críticos:

1. **`USE_DB_ARTIFACTS=False` em produção** — `DBArtifactStore` nunca
   instanciado pelo backend; cutover DB é teórico, validação técnica de A6b
   não garante que **uso real** funciona.
2. **LLM stages escrevem direto em disco** (ADR-099 mitiga parcial, A6a
   resolve) — mesmo após A6a, só teste humano em workflow real valida.

Deletar bridge (A6c) sem teste humano é arriscado: se o pipeline quebrar
em cenário real (ex.: upload de 50 docs com LLM premium, pipeline
incremental), rollback do bridge removido exige revert.

**Decisão:** Adicionar 2 etapas obrigatórias entre A6b e A6c:

**A6b.5 — Preparação para teste humano**:
- `docker-compose.smoke.yml` + `Makefile` smoke-up/seed/reset/logs
- Seed de dados (2 workspaces, 2 users) + fixtures comitadas em
  `tests/fixtures/smoke_inbox/` (extratos, faturas, IRPFs, ambíguos,
  duplicatas, PDF com senha, life plan)
- `docs/SMOKE_TEST_HUMAN.md` exaustivo (setup + matriz features + cenários
  parametrizados + template bug report + troubleshooting)
- Observabilidade mínima (health check, admin console, logs agregados,
  indicador visual "Artifact store: DB/Disk")
- Modo free-tier funcional (sem LLM key → `skipped: true` com banners)

**A6-human — Teste manual pelo David**:
- Checklist de ~70 verificações cobrindo auth, multi-tenancy, documentos,
  pipeline full+incremental, cada stage E0-E7, relatório, goals, cutover
  DB, edge cases.
- Template de bug report inline no runbook.
- Decisão **explícita** de aprovar A6c ou bloquear até correções.

**A6c (deletar bridge) depende de aprovação humana documentada.**

**Consequências:**
- ✅ Remoção do bridge só acontece com confiança real do sistema em uso.
- ✅ Runbook serve como onboarding para novos devs + operação contínua.
- ✅ Fixtures comitadas permitem reprodução de bugs reportados pelo tester.
- ⚠️ Adiciona 1-2 sessões de preparação + janela de teste manual (pode ser
  dias até semanas).
- ⚠️ Custo operacional: manter `docker-compose.smoke.yml` funcional ao longo
  do projeto (CI pode validar).
- ❌ Aceita que A6c (remover bridge) é bloqueado se teste humano revelar
  regressões.

**Artefatos:** [BACKLOG §A6b.5](BACKLOG.md#a6b5--preparação-para-teste-humano-adr-103) + [§A6-human](BACKLOG.md#a6-human--teste-manual-end-to-end-david).

---

## ADR-104 — E1.5c em Caminho B pragmático (Sessão A5f)

**Status:** Decidido (A5f) • **Data:** 2026-04-19

**Contexto:** Após A5e, E1.5c era o único stage determinístico fora do
Caminho B — usava `stage_runner_compat` + `MaterializationBridge` no wrapper
`pipeline/stages/e15c.py`. A consolidação de baseline é um script simples
(lê JSON, enriquece com chaves consolidadas, grava de volta), sem domain
services adicionais a extrair — candidato natural ao padrão pragmático já
adotado em E4/E5/E5.N/E7.

**Decisao:** Aplicar Caminho B pragmático (padrão ADR-097/A4b, ADR-099/A5d):
`main_with_store(ctx)` reutiliza `consolidate()` legado; wrapper limpo sem
bridge. `main(root_dir)` legado coexiste para CLI direto e testes existentes.

**Consequencias:**
- ✅ 7 de 7 stages determinísticos no Caminho B — `stage_runner_compat`
  sem clientes vivos em `pipeline/stages/`.
- ✅ Caminho A6c (remoção definitiva do bridge) desbloqueado assim que
  A6a+A6b+A6-human concluídos.
- ✅ Paridade comprovada por golden (cenários `itens[]` e `declarations[]`).
- ⚠️ `_init_config` e globals de módulo permanecem — remoção em A6d.1.
- ⚠️ Bridge e `stage_runner_compat` **não são removidos** aqui; aguardam
  A6a (LLM stages) + A6b (cutover DB) + A6-human (validação end-to-end).

---

## ADR-105 — LLM stages escrevem via ArtifactStore; E1 e E7-review LLM não migram (A6a)

**Status:** Decidido (A6a) • **Data:** 2026-04-19

**Contexto:** Antes de A6a, E1.5 e E2-llm escreviam artefatos do pipeline
direto em disco (`.write_text`), bypassando o `ArtifactStore`. Com
`MATHOMS_USE_DB_ARTIFACTS=true`, o pipeline quebraria: E3 buscaria esses
artefatos no DB e não os encontraria. Dois outros LLM stages existem: E1
(produz `family_members.json`, que é config do workspace, não artefato do
pipeline) e E7-review-LLM (produz um JSON de review ad-hoc consumido por
E7-apply; já persiste no path correto via disco).

**Decisao:**
1. E1.5 (`pipeline/stages/e15.py`): troca `out_path.write_text(...)` por
   `store.write("E1.5", "baseline_patrimonial", baseline_json)` → produz
   `baseline_patrimonial-1.5_baseline.json`. E1.5c lê via fallback.
2. E2-llm (`pipeline/stages/e2_llm.py`): troca `out_path.write_text(...)` por
   `store.write("E2-llm", safe_stem, e2_json)`. `_find_unprocessed_docs`
   migrada para `store.list_keys(stage)` em vez de glob de disco.
3. **E1 não migra**: `family_members.json` é configuração do workspace, não
   artefato do pipeline. Escrita em `ctx.members_dir/` é correta.
4. **E7-review LLM não migra**: o reviewer externo (humano ou automação)
   escreve o arquivo de review; E7-apply já lê via path convencional. Não é
   stage de produção contínua — é input ad-hoc fora do loop determinístico.

**Consequencias:**
- ✅ `MATHOMS_USE_DB_ARTIFACTS=true` pode ser ativado sem quebrar E3→E7.
- ✅ E1.5c lê corretamente via `store.read("E1.5", ...)` (fallback já em A5f).
- ✅ E2-llm: `_find_unprocessed_docs` via `store.list_keys` funciona em modo Disk e DB.
- ✅ Critérios estruturais enforçados por testes (`store.write` presente; `write_text` ausente).
- ⚠️ E1.5: filename em disco mudou de `-1.5_consolidated.json` para `-1.5_baseline.json`
  para novos workspaces. Workspaces existentes com arquivo no caminho antigo continuam
  funcionando (E1.5c lê E1.5c key primeiro → encontra o consolidated existente).
- ⚠️ E7-review LLM: se `MATHOMS_USE_DB_ARTIFACTS=true` e o arquivo de review foi
  escrito via disco, E7-apply pode não encontrá-lo em DB store. Documentado como
  limitação conhecida — review LLM é input ad-hoc, não stage automatizado.

---

## ADR-106 — Opt-in DB artifacts por workspace + DBArtifactStore no Celery task (A6b)

**Status:** Decidido (A6b) • **Data:** 2026-04-19

**Contexto:** Após A6a, todos os stages escrevem via `ArtifactStore` — mas o
pipeline web (`pipeline_task.py`) sempre criava um `DiskArtifactStore` via
`WorkspaceContext.for_tenant` (default). O flag global `MATHOMS_USE_DB_ARTIFACTS`
existia na config mas nunca era consultado pelo task. Ativar o modo DB globalmente
de uma vez é arriscado — prefere-se opt-in por workspace para piloto controlado.

**Decisão:**
1. **Coluna `workspaces.use_db_artifacts_override: bool | None`** (migration
   `r6s7t8u9v0w1`): `None` → global flag; `True` → força DB; `False` → força Disk.
2. **`pipeline_task.run_pipeline_task`**: antes de iniciar os stages, verifica
   `_resolve_use_db_artifacts(ws_id)` (workspace override > global flag). Se `True`,
   abre uma sessão longa (`SyncSessionLocal()`), cria `DBArtifactStore`, injeta em
   `ctx.artifact_store`. Sessão sofre `commit()` após cada stage com sucesso.
   `finally` fecha a sessão mesmo em caso de falha/pausa.
3. **`dev/compare_disk_vs_db.py`**: script operacional que compara artefatos em
   disco vs DB para um workspace + run. Gate ≥99% de paridade. Ignora `_meta`,
   `created_at`, `updated_at` (diferenças esperadas).

**Por que sessão longa no Celery task (e não uma por stage)?**
`DBArtifactStore.write` faz `flush()`, não `commit()`. O commit ocorre após cada
stage para persistir progressivamente — se o pipeline falhar no stage N, os
artefatos dos stages 1..N-1 já estão no DB. Uma sessão por stage criaria N
transações sem o benefício de leitura cross-stage (E3 lê artefatos do E2 que
foram escritos na mesma run).

**Discrepâncias esperadas entre disco e DB (não são bugs):**
- `_meta.confidence`, `_meta.notes` — presentes em E2-llm, sem equivalente no DB.
- `created_at` no DB vs timestamp no path do disco — ignorado pelo script.
- Ordem de listas JSON (transações, investimentos) — SQLite/Postgres não garante
  ordem de inserção nas queries sem `ORDER BY` explícito. E3→E7 são insensíveis
  à ordem; o compare script ignora ordem de listas de top-level.
- `byte_size`, `schema_version` no `pipeline_artifacts` — não têm equivalente
  em disco; ignorados na comparação.

**Consequências:**
- ✅ Ativação gradual: piloto por workspace sem impacto em outros.
- ✅ `_resolve_use_db_artifacts` é um ponto único de decisão — fácil de remover em A6c.
- ✅ Script de paridade operacional; gate ≥99% mensurável.
- ⚠️ Sessão longa no Celery worker: para pipelines com muitos stages, a sessão
  pode ficar aberta por minutos. Aceitável para SQLite (dev) e PostgreSQL com
  pool_size adequado.
- ⚠️ A6b.3 (validação em workspace real) ainda pendente — depende de teste humano
  com dataset real (A6-human.8).

---

## ADR-107 — Remoção de `MaterializationBridge` e `stage_runner_compat` (A6c.1-2)

**Status:** Decidido e executado (A6c.1-2) • **Data:** 2026-04-19 • **Commit:** `f7b824e`

**Contexto:** Após A5f (E1.5c em Caminho B pragmático) e A6a (LLM stages
escrevendo via `ArtifactStore`), o bridge ficou **sem clientes vivos** no
repo. Os 7 wrappers determinísticos (`pipeline/stages/e3.py`, `e4.py`,
`e5.py`, `e5n.py`, `e7.py`, `e15c.py` — e, via A6a, `e15.py` + `e2_llm.py`)
chamam `main_with_store(ctx)` direto. Nenhum código importa
`pipeline/stage_runner_compat.py` ou `pipeline/materialization_bridge.py`.
Manter código morto confunde auditorias futuras e contradiz docs.

**Decisão:**
1. **Deletar** `pipeline/materialization_bridge.py` e
   `pipeline/stage_runner_compat.py` no commit `f7b824e`.
2. **Manter** `main(root_dir)` legado nos 7 scripts determinísticos até
   A6c.3 — usado por CLI direto e golden tests de paridade.
3. **Testes estruturais** permanecem: imports não existem no codebase,
   falhariam imediatamente se recriados.

**Por que antes do A6-human:** remoção reversível por `git revert`, não
afetava produção (bridge não era invocado). Simplifica mensagem do
A6-human — falhas no cutover DB são reais, não resíduo de legado.

**Consequências:**
- ✅ Codebase livre de código morto.
- ✅ Arquitetura alvo pós-A6 mais próxima do estado real.
- ✅ A6c.3 (deletar `main(root_dir)` dos 6 scripts) concluído em
  2026-04-20 após A6-human; A6c.4 (docs) idem. **A6c completo**.
- ⚠️ R7 (princípio "MaterializationBridge temporário") fica apenas como
  registro histórico.

**Supersedes (parcialmente)**: ADR-086.

---

## ADR-108 — Estratégia de subdomínios `mathoms.ai` + Cloudflare DNS

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
   - Wildcard `*.mathoms.ai` → A record do VPS Hetzner (proxy
     Cloudflare **desligado** para `app/api/ops` — evita double-TLS e
     WebSocket issues; **ligado** para `mathoms.ai` apex e `docs.` —
     CDN/WAF grátis).
   - `*.staging.mathoms.ai` → mesmo VPS (ou ambiente separado quando
     crescer).
   - TLS via Let's Encrypt DNS-01 challenge (Traefik + Cloudflare API
     token com permissão `Zone:DNS:Edit`).
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

---

## ADR-109 — Auth portability: JWT HS256 + Fernet documentados como contratos portáveis (A6f.5a)

**Status:** Decidido • **Data:** 2026-04-20 • **Plano:** §18 A6f.5

**Contexto:** A6f.5 pede "auth portátil" — cenário hipotético em que backend
migra para Go. Auditoria (2026-04-20) revelou que o estado atual já é
language-neutral:

- **JWT**: `python-jose` com HS256, payload canônico `{sub, exp, tv}` —
  RFC 7519 puro, qualquer biblioteca Go (`golang-jwt/jwt`), TS
  (`jsonwebtoken`) ou Rust (`jsonwebtoken`) lê sem ajuste.
- **Fernet** (`cryptography.fernet`): AES-128-CBC + HMAC-SHA256 no formato
  documentado, 5 campos binários (version, timestamp, IV, ciphertext,
  HMAC). Existem libs Go (`fernet-go`), TS (`fernet`) e Rust (`fernet`).

Três caminhos considerados:

1. **Migrar para AES-256-GCM + HKDF-SHA256** agora — ganho marginal (Fernet
   já é seguro), custo alto (re-encrypt de `LLMConfig.api_key_encrypted`
   em produção, migration de `vault_entries` multi-tenant, compat
   backward no decrypt por N versões).
2. **Documentar o contrato e adiar AES-GCM** — Fernet é portátil, o gap é
   só ausência de documentação formal e teste de parity. ROI alto, risco
   zero.
3. **Migrar JWT de HS256 para RS256** — ganha separação key signing vs.
   validation, mas HS256 é suficiente até múltiplos serviços precisarem
   validar tokens sem compartilhar segredo.

**Decisão:**

1. **Manter JWT HS256** com payload canônico `{sub: str, exp: int,
   tv: int}`. Documentar em ADR que qualquer cliente Go/TS lê com a
   mesma `SECRET_KEY`.
2. **Manter Fernet** para symmetric encryption de segredos em banco
   (LLM keys, futuros vault entries). Documentar vetor de teste que
   qualquer lib Fernet-compatível (Go, TS, Rust) deve decriptar.
3. **Criar sub-fase A6f.5b** (deferida) para migrar Fernet → AES-256-GCM
   com HKDF-SHA256 + migration de dados encriptados. Gatilho de ativação:
   *(a)* requisito de auditoria (ex: SOC 2 type II exige AEAD moderno)
   OU *(b)* migração Go real em curso OU *(c)* qualquer CVE contra
   Fernet.
4. **Criar sub-fase A6f.5c** (deferida) para migrar JWT HS256 → RS256 se
   houver separação real entre serviço emissor e validador (ex: pipeline-
   service precisa validar tokens emitidos pelo backend).

**Contratos a testar em `test_auth_portability.py`:**

- JWT: roundtrip com a `SECRET_KEY` mockada — payload RFC 7519, algoritmo
  HS256 no header, claim `tv` propagado.
- Fernet: decrypt de um vetor canônico (ciphertext base64 + plaintext
  esperado) — garante que o valor em banco permanece legível mesmo se
  reimplementarmos o decrypt em outra linguagem.

**Política de documentação A6f** (aplicável a todas as sub-fases):

- ADR por sub-fase com decisão não-trivial.
- Entrada em `docs/CHANGELOG.md`.
- Status atualizado em `docs/BACKLOG.md`.
- Regra operacional nova em `CLAUDE.md` se afetar dia-a-dia.

**Consequências:**

- ✅ Contrato de auth documentado e testado sem tocar dados produtivos.
- ✅ Zero risco de perder `LLMConfig.api_key_encrypted` em prod por
  migração de cripto.
- ✅ Cliente Go hipotético hoje consegue fazer login e ler segredos
  encriptados — sem retrabalho.
- ⚠️ AES-GCM fica deferido — se virar requisito de compliance, abre
  A6f.5b.
- ❌ Formato Fernet (AES-128-CBC + HMAC) é "moderno o suficiente" mas
  não AEAD — aceito conscientemente por ora.

**Artefatos:**

- [BACKLOG §A6f.5](BACKLOG.md#a6f--language-neutral-boundaries-adr-102-r18-r20) (A6f.5a entregue, A6f.5b/.5c deferidos).
- `backend/tests/test_auth_portability.py` (parity tests).
- `docs/api/v1/openapi.json` (snapshot que qualquer codegen consome).

---

## ADR-110 — Structured JSON logging + OpenTelemetry bootstrap (A6f.3)

**Status:** Decidido • **Data:** 2026-04-20 • **Plano:** §19 A6f.3

**Contexto:** A6f.3 pede logs estruturados + tracing cross-service. Sem isso,
qualquer investigação em produção exige grepar linhas de texto livre e
correlacionar manualmente request → task → DB query. Se um dia o pipeline
migrar para Go (cenário A6f.1), manter o contrato de observabilidade em
formato neutro (JSON + OTLP) é obrigatório — binding a um agente específico
(Sentry SDK, DataDog tracer) amarra todos os serviços à mesma linguagem.

Três dimensões:

1. **Formato de log**: texto humano (status atual) vs. JSON. JSON é
   jq-compatível, parseável por qualquer log aggregator (Loki, Elasticsearch,
   CloudWatch Insights), e obrigatório se múltiplos serviços (API, worker,
   pipeline-service) gravam no mesmo stream.
2. **Correlation IDs**: trace_id precisa fluir request → Celery task → DB
   query → log line. Opções: (a) thread-locals (quebra em async), (b)
   contextvars (Python 3.7+ oficial, seguro em asyncio + threads),
   (c) OpenTelemetry context propagation (trace API). Escolha canônica:
   contextvars próprios (baseline) + OTel trace context (quando habilitado),
   ambos injetados nos log records.
3. **Tracing**: instrumentação opt-in via OTLP. Habilitar só quando
   `OTEL_EXPORTER_OTLP_ENDPOINT` estiver no env — evita custo de rede
   em dev e em workspaces sem collector.

**Alternativas consideradas:**

- **Apenas logs de texto + grep** — inviável cross-service; regex frágil.
- **Sentry SDK para tudo** — vendor lock-in, custo por volume; não cobre
  traces no formato OTLP neutro.
- **Logfmt em vez de JSON** — menor overhead, mas jq não parse nativamente
  e campos aninhados (ex.: `extra={"custom": {"nested": "ok"}}`) ficam
  serializados como strings.
- **FastAPIInstrumentor + SQLAlchemyInstrumentor sempre ligados** — custo
  de CPU em testes e dev quando nenhum backend está escutando. Só liga em
  `setup_otel()` se o endpoint OTLP estiver setado; `LoggingInstrumentor`
  liga sempre (custo desprezível, mas popula `otelTraceID`/`otelSpanID`
  nos log records).

**Decisão:**

1. **Formato padrão: JSON** (`python-json-logger` `JsonFormatter`).
   Feature flag `MATHOMS_LOG_FORMAT=text` volta para formatter humano com
   sufixo `[trace=XXXXXXXX]` quando há correlation id — útil em REPL e
   debugging local.
2. **Correlation context via contextvars próprios** em
   `backend/app/middleware/correlation.py`:
   - `_trace_id` (UUID v4, auto-gerado ou lido do header `X-Trace-Id`)
   - `_workspace_id` (setado pelo dispatcher quando conhecido)
   - `_user_id` (setado pelo dispatcher quando conhecido)
   - `_pipeline_run_id` (setado pela Celery task quando dentro de um run)
3. **MathomsJsonFormatter** injeta todos os 4 IDs + `timestamp` (UTC ISO
   8601 com `Z`) + `level` + `logger` + `otelTraceID`/`otelSpanID` (quando
   presentes via `LoggingInstrumentor`).
4. **`CorrelationIdMiddleware`** (Starlette): gera/lê `X-Trace-Id` no
   request, reflete no header da response, emite contextvar token.
5. **`setup_otel(service_name)`** idempotente via `_INSTRUMENTED`.
   `LoggingInstrumentor` sempre liga (popula trace context em records);
   `OTLPSpanExporter` só liga se `OTEL_EXPORTER_OTLP_ENDPOINT` estiver
   setado. Falha silenciosa (warning) se exporter não consegue inicializar
   — observabilidade nunca derruba a API.
6. **`instrument_fastapi(app)`** chamado no lifespan, antes de
   `init_db()`. Instala `FastAPIInstrumentor` + `SQLAlchemyInstrumentor`.
7. **`instrument_celery()`** chamado em `worker_process_init` signal —
   fork-safe; cada worker process reinicializa SDK + handlers.
8. **Namespace `mathoms.*`** para loggers de aplicação (`get_logger("api.foo")`
   vira `mathoms.api.foo`). Permite filtrar nossos logs dos de terceiros
   (uvicorn, sqlalchemy, celery).
9. **Idempotência**: `setup_logging()` marca o handler com atributo
   `_mathoms_managed = True` e remove duplicatas. Chamar N vezes (tests,
   lifespan, celery init) não acumula handlers.

**Contratos a manter:**

- Todo log line é JSON autocontido (uma linha = um objeto JSON válido).
  Enforçado por `test_json_lines_are_jq_compatible` — cada linha
  `json.loads()` limpo.
- Quando o contextvar está setado, o campo aparece no JSON. Quando não
  está, o campo é omitido (não vira `"trace_id": null`) — reduz ruído.
- `X-Trace-Id` é reflexivo: header de entrada preservado; senão, gerado
  como UUID v4 e devolvido. Cross-service ganha propagation grátis desde
  que o cliente envie o header.
- OTLP endpoint ausente não quebra a app — `is_otel_enabled() == False`
  e `setup_otel` só faz log correlation (sem exporter).

**Consequências:**

- ✅ Logs de API, worker e (futuro) pipeline-service têm mesmo formato,
  mesma semântica de correlation, mesmo shape de trace context.
- ✅ Auditoria post-hoc por `trace_id` resolve via jq/Loki — zero regex
  sobre campos textuais.
- ✅ Migração hipotética para Go mantém contrato — qualquer tracer
  OTLP-compliant interopera.
- ✅ Feature flag `MATHOMS_LOG_FORMAT=text` preserva UX de debugging local.
- ✅ OTLP off-by-default — zero custo em dev.
- ⚠️ Overhead de JSON serialize por log line (desprezível em prática,
  medido <5% em benchmark local).
- ⚠️ `LoggingInstrumentor().instrument(set_logging_format=False)` faz
  monkey-patch global — inofensivo mas obriga reset cuidadoso em testes.
- ❌ Log format atual existente (texto simples) será quebrado para
  consumidores externos; mitigado pelo feature flag text.

**Artefatos:**

- `backend/app/core/logging.py` — formatter + `setup_logging()` + `get_logger()`.
- `backend/app/core/otel.py` — `setup_otel()` + `instrument_fastapi()`
  + `instrument_celery()` + `is_otel_enabled()`.
- `backend/app/middleware/correlation.py` — middleware + contextvars +
  setters/getters.
- `backend/app/main.py` — wire no módulo (`setup_logging`, `setup_otel`)
  + lifespan (`instrument_fastapi`) + `CorrelationIdMiddleware`.
- `backend/app/worker.py` — `@worker_process_init.connect` calls
  `setup_logging` + `setup_otel("mathoms-worker")` + `instrument_celery`.
- `backend/requirements.txt` — `python-json-logger>=3.2`,
  `opentelemetry-api/sdk>=1.30`, `opentelemetry-exporter-otlp-proto-http`,
  `opentelemetry-instrumentation-{fastapi,sqlalchemy,celery,logging}>=0.50b0`.
- `backend/tests/test_structured_logging.py` — 8 tests cobrindo formatter,
  context propagation, middleware, idempotência, OTel opt-in, jq compat.

**Env vars (novas):**

- `MATHOMS_LOG_LEVEL` (default `INFO`) — `DEBUG|INFO|WARNING|ERROR|CRITICAL`.
- `MATHOMS_LOG_FORMAT` (default `json`) — `json|text`. Text é humano com
  `[trace=XXXXXXXX]` quando há correlation id.
- `OTEL_EXPORTER_OTLP_ENDPOINT` (opt-in) — URL do collector. Ausente =
  só correlation nos logs, sem exporter.

**Próxima sub-fase relacionada:** A6f.6 (stateless rigoroso + WS Redis
pub/sub + multi-worker test) — ver §19.6 do plano.

---

## ADR-111 — Stateless-rigoroso: padrão e gate empírico (A6f.6)

**Status:** Decidido (A6f.6) • **Data:** 2026-04-20

**Contexto:** Para que a stack escale horizontalmente (ADR-102 R19 — "Stateless-ready")
precisa existir uma garantia — auditada e testada — de que nada no código da
aplicação *requer* que um request pertença ao mesmo worker do anterior. Um
único `@lru_cache` mal colocado, um `dict` global que acumula estado ou um
`set[WebSocket]` em memória quebram a premissa e escondem o bug até o
segundo uvicorn worker entrar em produção.

A6f.6 foi planejada como refactor preventivo (mover WS para Redis pub/sub,
migrar rate limit para DB, etc.). Durante o audit `docs/STATELESS_AUDIT.md`,
concluímos que **o backend já está multi-worker-safe**:

- `@lru_cache`/`cached_property` em `backend/app/`: 0 ocorrências.
- Globais de módulo: 17 cataloged, todos imutáveis (constantes de regex,
  mappings, thresholds) ou singletons lazy idempotentes (`engine`, `_redis_client`,
  `_singleton` do Vault) — cada worker inicializa o seu, sem interop necessário.
- WS sessions: `api/ws.py` já era Redis pub/sub desde P5 (F6.5B.14) — nenhum
  `set[WebSocket]` ou `dict[run_id, list]` local.
- Rate limits: único existente (`MAX_PENDING_PER_WORKSPACE = 10`) é DB-backed.
- Background tasks: 0 ocorrências de `asyncio.create_task`, `BackgroundTasks`
  ou `threading.Thread` em app code — tudo vai pelo Celery.
- File locks: 0 ocorrências de `fcntl`/`flock`/`filelock` em `backend/` + `pipeline/`.

O risco portanto já **estava** mitigado por acaso/coincidência de boas
decisões anteriores. A contribuição de A6f.6 passa a ser:

1. **Auditar** e documentar o estado (cria memória organizacional).
2. **Proteger** com um teste de integração que falha em regressões.
3. **Formalizar** o padrão como regra operacional para novo código.

**Alternativas consideradas:**

1. **Não formalizar** (status quo) — risco: próxima sessão adiciona
   `_request_counter = {}` num módulo e não tem como diferenciar isso
   de `_MONTH_PT` (constante OK). Descartada: o custo de uma regra
   explícita é pequeno.
2. **Lint custom** (proibir globais mutáveis via AST check) — descartada
   por ora; exemplos legítimos (singletons lazy, `engine`) tornam a regra
   difícil de expressar sem falsos positivos. Audit + teste empírico
   dão o mesmo valor com menos fricção.
3. **Teste multi-processo real** (spawn 2 uvicorn + 2 celery via
   `multiprocessing.Process`) — descartada: flaky em CI, lento, exige
   Redis real + Postgres real. O teste empírico com `AsyncClient`s
   duplos + fakeredis compartilhado exercita o que a aplicação pode
   quebrar; isolamento real de processos é responsabilidade do
   framework (FastAPI + Celery).
4. **Gate manual via runbook** sem teste automatizado — descartada: o
   teste é barato, dá sinal imediato em PR e não depende de humano
   executar checklist.

**Decisão:**

1. `docs/STATELESS_AUDIT.md` é o catálogo canônico — qualquer novo
   global de módulo entra nessa tabela com veredito (imutável,
   idempotente, ou **proibido**).
2. `backend/tests/integration/test_multi_worker_concurrency.py` é o gate
   automatizado. Cobre os 4 cenários críticos:
   - JWT cross-worker (2 AsyncClients + mesmo `SECRET_KEY`).
   - Upload/query cross-worker (2 AsyncClients + mesma DB).
   - Rate limit cross-worker (alternância A/B, 11ª = 429).
   - WS + pub/sub cross-worker (TestClient sync + fakeredis shared server).
3. Regra operacional **R19** formalizada (complementar ao R19 genérico
   em ADR-102):
   - **Zero estado mutável in-memory** em nível de módulo/classe em
     `backend/app/` e `pipeline/`. Exceções explicitamente aceitas:
     (a) constantes imutáveis (regex compilados, mappings de domínio,
     thresholds); (b) singletons lazy **idempotentes** (mesma key
     produz mesmo objeto em qualquer worker — ex: `engine` SQLAlchemy,
     `_redis_client` Redis, `_singleton` Vault).
   - **Proibido**: cache por-request, counter compartilhado, `set` ou
     `dict` que acumula entre requests, `@lru_cache` em código de
     aplicação, `asyncio.create_task` fora do Celery, file lock
     (`fcntl`/`flock`/`filelock`).
   - Qualquer "queria usar cache de resposta" resolve via Redis, não
     memória local.
   - Qualquer "queria rate-limit" resolve via DB (invitation pattern)
     ou Redis `SET NX` + TTL — nunca token bucket em memória.
4. `_PLAYWRIGHT_AVAILABLE` em `services/pdf_renderer.py` é **workaround
   aceito** (capability probe idempotente cross-worker) — documentado no
   audit §2.
5. **Runbook de fail-over manual** (cenário 5 — worker A morre durante
   request) referenciado em `docs/RUNBOOK.md`; não é parte do gate
   automatizado porque depende de infra real.

**Contratos a manter:**

- `publish_event()` em `services/events.py` é a **única** via de
  comunicação workers → clientes. Qualquer evento novo (stage,
  activity, needs_review, terminal) passa por aí — Celery não
  abre WebSocket direto, uvicorn não pushea para Celery sem Redis.
- Canal `pipeline:{run_id}` é o contrato pub/sub (ver ADR-095 F6.5B.14).
- `MaterializationBridge` + `DBArtifactStore` (ADR-086) são os únicos
  adapters autorizados a cruzar framework boundary do `pipeline/`.
- Adicionar módulo global novo (`_ALGO = ...` no topo de um arquivo)
  exige decisão consciente: se não é imutável nem idempotente, **não
  adicione**. Se é, adicione entrada ao audit.

**Consequências:**

- ✅ Garantia empírica testada (5 tests) de que 2 workers + 1 Celery
  funcionam com Redis + Postgres como único estado compartilhado.
- ✅ Zero refactor de código de aplicação (WS já era pub/sub, rate
  limit já era DB). A6f.6 fecha em docs + testes.
- ✅ Regra de oro documentada para novos módulos (audit + §R19 do
  ADR-102 + regra operacional no CLAUDE.md).
- ⚠️ Teste usa **fakeredis** + `AsyncClient` duplicado, não processos
  reais. Runbook manual (`docs/RUNBOOK.md` — a criar) cobre fail-over.
- ⚠️ `MATHOMS_USE_DB_ARTIFACTS=False` (default) mantém escrita em disco
  via `DiskArtifactStore`. Em produção multi-worker com disco
  compartilhado, concurrency depende de Celery `task_acks_late=True`
  garantir 1 worker por `run_id`. Cutover pleno (A6-human → A6c) elimina
  essa classe de risco escrevendo via DB.
- ❌ Novo dev que adicione dict mutável global precisa conhecer a regra
  — mitigado por (a) code review; (b) audit como referência viva;
  (c) CLAUDE.md "Regras operacionais" lista a proibição.

**Artefatos:**

- [docs/STATELESS_AUDIT.md](STATELESS_AUDIT.md) — catálogo de 10 seções
  com veredito por arquivo + gap list.
- [backend/tests/integration/test_multi_worker_concurrency.py](../backend/tests/integration/test_multi_worker_concurrency.py) —
  5 tests, 1.05s, sem Redis/Postgres reais.
- Regras novas em `CLAUDE.md` §"Regras operacionais" — proibição
  explícita de `asyncio.create_task`, globais mutáveis, file locks.

**Próxima sub-fase relacionada:** nenhuma direta — A6f está dividida em
.2 ✅, .3 ✅, .5a ✅, .6 ✅; .1 (pipeline-as-service) e .4 (DB schema
review) seguem independentes. A6-human (§18 do plano) valida cutover DB
end-to-end e destrava A6c (remoção do `MaterializationBridge`).

---

## ADR-112 — Pipeline-as-Service: HTTP boundary para execução de stages (A6f.1)

**Status:** Decidido (A6f.1) • **Data:** 2026-04-21

**Contexto:** Até A6e, `backend/app/tasks/pipeline_task.py` importava
`pipeline.orchestrator._run_stage` diretamente para executar cada stage
dentro do worker Celery. Isso acoplava o ciclo de vida do pipeline ao
processo Python do backend: qualquer refactor de orquestração obrigava a
reiniciar o worker, e a fronteira language-neutral que ADR-102 R18 pede
(clientes não-Python conseguirem falar com o pipeline) continuava
imaginária. A6e.1–.4 fecharam per-aggregate repos/DTOs; A6f.2/.3/.4/.5a/.6
destravaram OpenAPI snapshot, logs JSON, schema DB neutro e gate
empírico de multi-worker. O degrau restante era a execução de pipeline.

Duas opções consideradas:

1. **Subprocess/Celery task dedicado** — pipeline continua in-tree mas
   roda em worker separado. Ganho de isolamento, zero ganho de
   portabilidade (ainda Python-to-Python via broker).
2. **HTTP service standalone** — pipeline-service expõe REST+WS. Qualquer
   consumidor (Go futuro, CLI externo, script de staging) fala contrato
   documentado. Cutover gradual via feature flag.

**Decisão:** implementar a opção 2. Nasce `pipeline-service/` (FastAPI
greenfield) expondo `POST /api/v1/pipeline/runs`,
`POST /api/v1/pipeline/stages/{stage}/execute` e WS
`/api/v1/pipeline/events/{run_id}`. Backend consome via
`PipelineServiceClient` (Protocol) com duas implementações: `HttpPipelineClient`
quando `MATHOMS_PIPELINE_SERVICE_URL` está setada, `InProcessPipelineClient`
caso contrário (dev, test, single-process deploy). A flag é env var — não
config de app — para permitir cutover por ambiente sem redeploy do
backend.

Pipeline-service é **stateless rigoroso** (ADR-111): zero DB, zero cache
por-request, Redis singleton lazy+idempotente. Artefatos atravessam a
fronteira por `workspace_root` (path em disco) — backend permanece dono
do `DBArtifactStore`; pipeline-service opera com o `DiskArtifactStore`
que vê em disco, sem consultar DB. Isso mantém a fronteira fina e torna
trivial rodar múltiplas instâncias do pipeline-service atrás de um LB.

Não é migração para Go ainda. ADR-112 define o **contrato**; a
substituição da implementação Python por Go é uma A6f seguinte, sem
mudança de wire format.

**Consequências:**

- ✅ Fronteira language-neutral real — OpenAPI snapshot em
  `docs/api/v1/pipeline-service.openapi.json` é fonte de verdade; qualquer
  cliente pode consumir.
- ✅ `backend/app/tasks/pipeline_task.py` zero `from pipeline.orchestrator`
  imports — gate enforçável por grep + revisão de PR.
- ✅ `InProcessPipelineClient` evita regressão: ambiente atual (sem
  `MATHOMS_PIPELINE_SERVICE_URL`) roda idêntico. Test suite inteira
  valida ambos os clients.
- ✅ Redis pub/sub preserva compat com `backend/app/services/events.py` —
  mesmo envelope, mesmo canal, WS do backend continua funcionando
  durante transição.
- ⚠️ Um processo a mais no deploy. Em smoke local, `docker-compose.pipeline-service.yml`
  sobe junto. Em prod, cutover exige orquestração (K8s manifest, ECS
  service, etc.) — escopo de A6-deploy, não A6f.1.
- ⚠️ Overhead HTTP por stage: serialização JSON + round-trip ~2–5ms em
  rede local. Irrelevante frente aos minutos que stages reais levam
  (E3/E5), mas registrar para comparações futuras.
- ❌ Duplicação mínima de DTOs (Pydantic em `pipeline-service/app/contracts/`
  espelhando `backend/app/schemas/pipeline.py`). Aceito porque cada lado
  publica seu próprio OpenAPI; manter em sync é responsabilidade dos
  snapshot tests (ambos falham se contrato diverge sem intenção).

**Escopo deferido (follow-ups explícitos):**

- Extração de helpers (`_materialize_adapter_configs`,
  `_persist_llm_suggestions`, `_create_report_from_output`) de
  `pipeline_task.py` para services dedicados e redução do arquivo para
  ≤100 linhas — refactor comportamento-preservante, slice próprio.
- Migração do backend para usar `HttpPipelineClient` por default em
  staging (flip do env var nos pipelines CI/CD). Gate humano.
- Go rewrite do pipeline-service (A6f seguinte). Contrato HTTP fixo
  permite rodar ambas as implementações atrás do mesmo LB.

**Artefatos:**

- `pipeline-service/app/**` — FastAPI app, contratos, services.
- `backend/app/services/pipeline_client.py` — Protocol + 2 implementações.
- `docs/api/v1/pipeline-service.openapi.json` — snapshot do contrato.
- `docker-compose.pipeline-service.yml` — compose overlay para smoke.
- `Makefile` — `update-pipeline-service-openapi` target e composição
  automática com `update-openapi-snapshot`.

---

## ADR-113 — Convenções Go: `.golangci.yml` + CI + skeleton (A6g.7)

**Status:** Decidido (A6g.7) • **Data:** 2026-04-22

**Contexto:** A6f.1 (ADR-112) estabeleceu `pipeline-service/` como
FastAPI standalone falando HTTP — candidato natural à reescrita em Go
(footprint, startup, deploy estático, ausência de GIL). `CLAUDE.md`
§Code style já define regras Go inegociáveis (sem `interface{}`/`any`,
errors tipados, `int64` cents, interfaces pequenas no consumer, `log/slog`
com handler JSON, sem estado mutável em package-level). Sem linter +
CI + ADR rastreável, a convenção vira letra morta: o primeiro PR de Go
inevitavelmente perde tempo debatendo `.golangci.yml` no meio do
trabalho produtivo, e regras específicas do projeto (`int64` cents,
ausência de globais mutáveis) não vivem no `effective-go` para alguém
deduzir sozinho.

Duas alternativas consideradas:

1. **Deferir para o primeiro PR de Go** — rejeitada. Linter vira
   bikeshed no meio do PR que deveria ser foco na reescrita. Zero
   retorno em não fazer agora; custo próximo-de-zero (skeleton + config,
   sessão curta).
2. **Aderir estritamente ao `effective-go` sem ADR próprio** — rejeitada.
   Regras específicas do repo (`int64` cents, stateless package-level
   paralelo a ADR-111, `log/slog` JSON obrigatório) não estão em
   Effective Go; ficariam órfãs em `CLAUDE.md` sem justificativa
   histórica rastreável.

**Decisão:** adotar `.golangci.yml` conservador (errcheck, staticcheck,
gocritic, revive, bodyclose, noctx, sqlclosecheck, rowserrcheck,
errorlint, gocyclo min-complexity=15, goconst, prealloc, unparam,
unconvert, misspell, govet `enable-all`) — sem `forbidigo`/`depguard`
até A6g.6, que calibra com código real. CI em `.github/workflows/go.yml`
com detecção por `hashFiles('**/*.go') != ''` faz skip inteligente
enquanto o repo não tem `.go`, ativando gofmt + vet + golangci-lint +
`go test ./... -race` automaticamente no primeiro PR que introduzir o
primeiro serviço. `services/` skeleton reserva raiz para
`services/<name>/` com `go.mod` próprio. `go.work` declarado na raiz
com apenas `go 1.22` — `use` directive entra no mesmo PR do primeiro
módulo (dir sem `go.mod` faz `go work sync` falhar). Regras
inegociáveis de código (sem `interface{}`/`any`, errors tipados, `int64`
cents, `log/slog` JSON, ausência de estado mutável package-level, race
detector sempre on) continuam em `CLAUDE.md` §Code style › Go — ADR
referencia, não duplica.

**Consequências:**

- ✅ Linter pronto antes do primeiro PR de Go — revisão foca em domínio,
  não em estilo.
- ✅ Regras específicas do projeto (`int64` cents, stateless package-level)
  ganham referência ADR rastreável; quem chegar novo entende **por que**,
  não só **o que**.
- ✅ CI workflow é idempotente — mesmo arquivo funciona em repo com zero
  `.go` (hoje) e em repo com serviços Go (amanhã), sem edição.
- ✅ `Makefile` ganha `go-fmt`/`go-lint`/`go-test`/`go-all` com skip
  defensivo; `make go-all` num repo sem Go retorna 0.
- ⚠️ `.golangci.yml` versão conservadora — A6g.6 ativa
  `forbidigo`/`depguard` (banindo `interface{}`, `fmt.Println` fora de
  `cmd/`, imports cruzando boundary) **depois** que houver código para
  calibrar sem false-positives ruidosos.
- ⚠️ `golangci-lint` pinado em `v1.60` no workflow; upgrade exige
  verificação manual de compatibilidade com as regras ativas.
- ❌ `go.work` com apenas `go 1.22` (sem `use`) é menos idiomático que
  `use (./services/<name>)` apontando para um módulo real — aceito
  porque nenhum módulo existe ainda e `go work sync` com `use` para dir
  vazio aborta. O primeiro PR de Go adiciona `go.mod` + `use` no mesmo
  slice.

**Escopo deferido (follow-ups explícitos):**

- `forbidigo`/`depguard` rules em `.golangci.yml` — A6g.6, depois que
  houver `.go` para calibrar sem ruído.
- Codegen Go do OpenAPI via `oapi-codegen` consumindo
  `docs/api/v1/pipeline-service.openapi.json` — A6g.7b ou parte do
  primeiro PR produtivo.
- Hook `pre-commit` local para `gofmt`/`go vet`/`golangci-lint` —
  A6g.6 (`.pre-commit-config.yaml` ganha entrada Go paralela às
  Python/TS).
- Reescrita efetiva de `pipeline-service/` para Go — decisão separada
  com ADR própria; contrato HTTP de ADR-112 permite rodar ambas
  implementações atrás do mesmo LB durante cutover.

**Artefatos:**

- `.golangci.yml` — config do linter (linters-settings + revive rules
  + errorlint + gocyclo).
- `go.work` — workspace multi-module com guia embutida.
- `services/README.md` + `services/.gitkeep` — onboarding + reserva de
  diretório.
- `.github/workflows/go.yml` — CI com skip inteligente.
- `Makefile` — targets `go-fmt`, `go-lint`, `go-test`, `go-all`.

---

## ADR-115 — Domain events tipados: arquitetura e boundaries (A6e.events)

**Status:** Decidido (A6e.events) • **Data:** 2026-04-22

**Contexto:** A6e.3/.3b fecharam a application layer — 47 use cases
limpos, zero side-effect inline. Side-effects transversais (audit log,
notificações, cache invalidation futura) continuam dispersos: `audit_log()`
é chamado inline em ~5 routers; notificações de prazo vivem em polling
cron (`scan_and_create_notifications`) desconectado do lifecycle da
Task. F7B.5 vai consumir audit log completo em produção — formalizar o
padrão antes de espalhar reduz retrabalho.

`backend/app/services/events.py` já existe mas é Redis pub/sub para
**progresso de pipeline stages** (publish_stage_started/completed) —
escopo diferente; tentar unificar cria acoplamento inútil.

Três alternativas consideradas:

1. **Sem eventos, side-effects inline continuam** — rejeitada. Audit em
   ~15 call-sites hoje cresce quadraticamente; cada novo agregado
   duplica o padrão. Notificação de prazo permanece órfã do ciclo de
   Task (cron só vê snapshot periódico).
2. **Event store persistido (event sourcing)** — rejeitada por over-engineering.
   Não há necessidade de reconstrução de agregados por replay; só
   desacoplar side-effect do use case. Event sourcing completo exigiria
   refactor de repositories (estado vs. log), impacto maior que o
   ganho atual.
3. **Handlers async pós-commit por padrão (Celery)** — rejeitada como
   default. Handler que escreve audit precisa de atomicidade com o use
   case (commit falha → audit não fica órfão). Async post-commit volta
   como segundo modo quando houver caso concreto (email, WebSocket
   broadcast); ponte `enqueue_async` fica como stub.

**Decisão:** introduzir camada `backend/app/events/` com:

- **`Event` base**: `@dataclass(frozen=True, slots=True, kw_only=True)`
  com `event_id` (UUID hex), `occurred_at` (tz-aware UTC),
  `aggregate_id/type`, `workspace_id`. Subclasses adicionam payload
  tipado; imutabilidade garantida por `frozen` + `slots`.
- **Registro estático** via `@register_handler(EventClass)` — decorator
  roda em tempo de import (singleton idempotente, ADR-111 permite).
  `backend.app.events.handlers.__init__` importa cada módulo de
  handler explicitamente; zero glob auto-discovery.
- **Dispatch síncrono por padrão**: `dispatch_sync(event, deps)` roda
  handlers na transação do caller. Falha propaga → caller decide
  rollback. Handlers async são aguardados (`inspect.isawaitable`).
- **Deps injetados explicitamente** via `EventHandlerDeps` (TypedDict
  com `total=False`): dispatcher passa o mapping; cada handler pulls
  o que precisa (`deps["db"]`). Nada de context var global (ADR-111).
- **`enqueue_async` stub**: ponte para Celery / SQLAlchemy
  `after_commit` listener; levanta `NotImplementedError` até slice
  dedicado ativar (quando aparecer handler que escreva fora do DB).
- **Handlers são funções puras** sem estado interno — nenhum `_cache`,
  `@lru_cache` ou counter compartilhado (ADR-111 stateless rigoroso).

**Entregue na lane A6e.events (3 slices + docs):**

- **Slice 1 (infra):** base/registry/dispatcher/protocols + 18 unit
  tests (frozen, slots, UUID, ordem determinística, propagação de
  exceção, injeção de deps).
- **Slice 2 (AuditLogEvent):** `AuditLogEvent` +
  `FamilyMemberCreatedEvent` + handler `write_audit_entry` /
  `audit_family_member_created` (traduz agregado → audit). Migra
  `application/family_member/create_family_member.py` para emitir
  `FamilyMemberCreatedEvent` após `repo.create()`. Router passa
  `db` + `current_user.id` explicitamente.
- **Slice 3 (Task events):** `TaskCreatedEvent` + `TaskUpdatedEvent` +
  handler `on_task_created` / `on_task_updated` (cria Notification
  quando prazo está no horizonte). Flag
  `MATHOMS_USE_EVENT_DRIVEN_TASK_NOTIFICATIONS` default False —
  `scan_and_create_notifications` cron continua fonte única até
  validação humana (A6e.events-followup).

**Consequências:**

- ✅ Use cases emitem eventos e ignoram handlers — zero import de
  audit/notification service na application layer. Novos agregados
  seguem mesmo padrão.
- ✅ Atomicidade preservada em repos caller-owns-commit (Task): task +
  notification na mesma txn; rollback descarta ambos.
- ✅ Handler do tipo errado explode ruidoso (TypeError por kwargs); sem
  fallback silencioso. Registro explícito → auditar handlers é `grep
  @register_handler`.
- ✅ Novo agregado que precisa de audit ganha `XCreatedEvent` + handler
  que traduz para `AuditLogEvent`; zero código duplicado em routers.
- ⚠️ **Atomicidade parcial** em repos legados que commitam internamente
  (`FamilyMemberRepository.create()` faz `session.commit()`). Audit
  vive em transação separada que o use case fecha logo depois; falha
  no handler desfaz o audit mas deixa o membro committed. Aceito como
  limitação temporária — fechar quando repositories não-Task migrarem
  para caller-owns-commit (R14). Testes cobrem rollback isolado do
  handler.
- ⚠️ Registro global `_HANDLERS` é estado de módulo — considerado
  singleton idempotente (populado em import time, imutável em runtime
  de produção). Testes usam `clear_handlers` + save/restore em
  fixture para não apagar registros reais.
- ⚠️ ~14 call-sites de `audit_log()` inline em `backend/app/api/` ainda
  não foram migrados — tarefa dedicada "A6e.events-migration" depois
  de padrão validado.
- ❌ Documentação da descoberta de handler é manual (precisa editar
  `handlers/__init__.py`). Aceito para rejeitar descoberta automática
  por glob, que esconde side-effects de registro.

**Escopo deferido (follow-ups explícitos):**

- **Migração dos ~14 `audit_log()` call-sites** restantes em
  `backend/app/api/*.py` — tarefa dedicada A6e.events-migration.
- **Handlers async (Celery dispatch, email, broadcast WS)** — quando
  houver caso concreto; `enqueue_async` stub já sinaliza o caminho.
- **Event store persistido** (event sourcing) — explicitamente fora de
  escopo; eventos são ephemeral, vivem só durante dispatch.
- **Remoção do cron `scan_and_create_notifications`** — após A6e.events-
  followup ativar `MATHOMS_USE_EVENT_DRIVEN_TASK_NOTIFICATIONS=True`
  em produção e validar por 2+ semanas.
- **Repo FamilyMember/outros não-Task migrarem para caller-owns-commit**
  (R14) — fecha a atomicidade parcial documentada acima.

**Nota de naming** (ADR-101): `R17` originalmente referenciava `A6e.6`
(domain events). Em 2026-04-22 a lane foi renomeada `A6e.6 → A6e.events`
para evitar colisão histórica com 5 commits de `(A6e.6)` que eram o
slice Goal do track per-aggregate. ADR-101 R17 aponta para a nova
sub-fase; commits desta lane filtráveis por `git log --grep "A6e.events"`.

**Artefatos:**

- `backend/app/events/{base,registry,dispatcher,protocols,domain,__init__}.py`
- `backend/app/events/handlers/{audit_log_handler,task_notification_handler}.py`
- `backend/tests/events/` — 32 testes (unit + integration DB + flow via API)
- `backend/app/core/config.py` — flag `USE_EVENT_DRIVEN_TASK_NOTIFICATIONS`
- `backend/app/application/family_member/create_family_member.py` — emite evento
- `backend/app/application/task/{create_task,update_task}.py` — emitem eventos
- `backend/app/api/family_members.py` — injeta `db` + `actor_user_id`

---

## ADR-NNN — Titulo curto

**Status:** Decidido (FX) • **Data:** YYYY-MM-DD

**Contexto:** Por que estamos decidindo isso? Quais eram as alternativas?

**Decisao:** A decisao tomada, em uma frase.

**Consequencias:**
- ✅ Beneficios
- ⚠️ Trade-offs
- ❌ Drawbacks aceitos

Se substituir uma ADR anterior, marcar: `Supersedes ADR-NNN`.
