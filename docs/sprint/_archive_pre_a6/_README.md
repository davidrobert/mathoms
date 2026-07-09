---
id: ARCHIVE-pre-a6
type: archive-index
title: "Histórico pré-Sprint A6 (F6.5 + Bootstrap blocks)"
---

# Histórico pré-Sprint A6

Blocos H3 do `docs/BACKLOG.md` que precederam o regime de Sprints
(Bootstrap + Blocos 1-6 + 6.5A-F). Não são lanes ativas; ficam aqui
como histórico de execução para arqueologia.

## 🛠 — Bootstrap (executado em 2026-04-15) ✅


Bloco zero da reordenação CTO (ver discussão em conselho 2026-04-15): toda a fundação que A-E vão consumir, antes de qualquer test funcional. Itens entregues:

- **6.5A.1** Vitest + jsdom + coverage v8 + path alias `@/*` ([`frontend/vitest.config.ts`](../../../frontend/vitest.config.ts), [`frontend/tests/setup.ts`](../../../frontend/tests/setup.ts))
  - Polyfill explícito de `localStorage`/`sessionStorage` (jsdom 25 + vitest 2.1.x não instanciam Storage nativa — workaround em setup.ts)
  - Polyfills de `matchMedia`, `IntersectionObserver`, `ResizeObserver`, `URL.createObjectURL`, `crypto.randomUUID`
- **6.5A.2** MSW v2 (`tests/mocks/server.ts` + `handlers.ts` + `fixtures.ts`) com defaults para 50+ endpoints de `lib/api.ts`
- **6.5C.1** Playwright multi-browser (chromium + firefox + webkit + projeto `visual` isolado), auth helper com workspace isolation por worker
- **6.5F.1** DB isolation strategy documentada em [`backend/tests/conftest.py`](../../../backend/tests/conftest.py) (recreate-per-test sobre SQLite in-memory; ADR inline com alternativas e gatilho de migração para PG)
- **6.5F.2** Backend factories type-safe em [`backend/tests/factories/`](../../../backend/tests/factories) (12 builders: user, workspace, member, account, category, document, vault, run, stage_log, report, notification, llm_config)
- **6.5F.3** [`docker-compose.test.yml`](../../../docker-compose.test.yml) (PG 5433 + Redis 6380, isolados do dev) + scripts `test_backend_up.sh`/`test_backend_down.sh` + `.env.test` gitignored
- **6.5F.7** Frontend factories type-safe em [`frontend/tests/factories/`](../../../frontend/tests/factories) (12 builders alinhados com `lib/api.ts`)
- **6.5F.12** Gerador determinístico de PDFs sintéticos para 14 códigos (`BankCode`) em [`tests/fixtures/pdf_generator.py`](../../../tests/fixtures/pdf_generator.py) (reportlab; CPF placeholder LGPD-safe)
- **6.5F.13** Esqueleto de [`docs/reference/TESTING.md`](../../reference/TESTING.md) com TL;DR, comandos, FAQ
- Smoke test [`frontend/tests/bootstrap.test.tsx`](../../../frontend/tests/bootstrap.test.tsx) cobrindo Vitest + jsdom + jest-dom + MSW + factories: **7/7 passando em 941ms**

**Bugs pré-existentes detectados durante validação** (entrarão em 6.5E.8 anti-regression bank):
- `backend/tests/test_pipeline_api.py`: 6 testes falhando (KeyError 'id' + assert errors em trigger/cancel/list/get_run_detail)
- `backend/tests/test_pipeline_phase5.py`: 2 testes falhando (concurrency + health)
- `backend/tests/test_pipeline_review.py`: 2 testes falhando (tier detection)
- `backend/tests/test_retry_config.py`: 1 teste falhando (multiple retryable errors)
- `backend/tests/test_pipeline_task.py`: 3 ERROR (celery_task_id field, cancellation flag)
- **Total:** 7 failed + 3 errors em 269 passados (estado inicial pré-F6.5)

## 🛡 — Bloco 1 — Backend Hardening 6.5E (executado em 2026-04-15) ✅


Segundo bloco da reordenação CTO: blindar a fronteira DB → pipeline contra a classe de bugs do BUG-015 antes de ataque ao frontend. Itens entregues:

- **6.5E.4** Fix cwd-sensitivity:
  - [`backend/alembic.ini`](../../../backend/alembic.ini): URL agora usa `%(here)s/../mathoms.db` (absoluto)
  - [`backend/alembic/env.py`](../../../backend/alembic/env.py): guard que rejeita SQLite com path relativo (com bypass `MATHOMS_ALEMBIC_ALLOW_RELATIVE_SQLITE=1` para tests)
  - [`backend/app/core/config.py`](../../../backend/app/core/config.py): `DATABASE_URL` default agora absoluto via `_PROJECT_ROOT`
  - [`docs/reference/SETUP.md`](../../reference/SETUP.md): seção "Migrations (Alembic)" documentando políticas
- **6.5E.1 + 6.5E.5** [`backend/tests/test_serializers_round_trip.py`](../../../backend/tests/test_serializers_round_trip.py) — **15 testes** cobrindo:
  - `serialize_family_members` round-trip + 4 cenários anti-regressão BUG-015 (com/sem surname, com/sem members, round-trip por disco)
  - `serialize_categorization` (expense/income separation)
  - `serialize_pipeline_config`, `serialize_institution_config`, `serialize_report_layout` (blob round-trip + YAML em disco)
  - `serialize_llm_config` (decifração de api_key + round-trip por disco)
- **6.5E.3** [`backend/tests/test_alembic_guardrails.py`](../../../backend/tests/test_alembic_guardrails.py) — **4 testes**:
  - drift detection model↔migration (catálogo `KNOWN_PRE_EXISTING_DRIFT` com 4 itens conhecidos a regenerar; novo drift falha imediato)
  - idempotency test (`upgrade → downgrade → upgrade` = mesmo schema)
  - linearidade do histórico (sem branches/heads múltiplos)
  - offline SQL preview gera `CREATE TABLE` válido
- **6.5E.2** [`backend/tests/test_golden_pipeline.py`](../../../backend/tests/test_golden_pipeline.py) — **18 testes + 1 skip**:
  - workspace fixture canônica → materialize → asserts no JSON em disco
  - 13 PDFs sintéticos parametrizados (1 por banco) abrem no pdfplumber
  - token `{{COVER_FAMILIA}}` substituído corretamente no template
  - **Skip documentado:** full E2E pipeline (E0→E6) deferido (requer refinar gerador por banco + mocks LLM + refator de globals em `e6_render.py`)
- **6.5E.8** [`backend/tests/regressions/`](../../../backend/tests/regressions) — **20 testes ativos + 1 placeholder frontend**:
  - BUG-001 (Celery task discovery), BUG-002 (sys.path em fork worker)
  - BUG-003 (on_failure callback), BUG-004 (CPF leak fallback)
  - BUG-007 (skip_llm tier respect), BUG-014 (BankAccount.label)
  - BUG-015 (familia.sobrenome — sentinela; cobertura primária em test_serializers_round_trip)
  - OP-001 (parse_args sys.argv parametrizado em 6 scripts), OP-002 (SystemExit em Celery)
  - OP-008 (FERNET persistence), OP-009 (max_tokens schema + DB default)
  - OP-010 (started_at tz-aware no Pydantic serializer)
  - Placeholder para BUG-005/006/008/011/012 + OP-011 (frontend — cobertos em 6.5B/D)
- [`backend/tests/regressions/README.md`](../../../backend/tests/regressions/README.md) com catálogo + convenções

**Resultado agregado Bloco 1:** 57 passing + 2 skipped em 5.32s.

**Achados não previstos:**
- 6 serializers confirmados (não 5 como cogitado): `family_members`, `categorization`, `pipeline_config`, `institution_config`, `report_layout`, `llm_config`
- Drift real catalogado: `bank_accounts.label`, `notifications.created_at NOT NULL`, `transaction_overrides.created_at NOT NULL`, `pipeline_stage_logs.status` Enum (4 itens — gerar migration consolidada como follow-up)
- `LLMConfigCreate` schema chamado de `LLMConfigCreateRequest`
- `max_tokens=16384` é configuração runtime, não default — schema permite (`le=200000`); test ajustado

## 🛡 — Bloco 2 — Multi-tenant gate 6.5B.12 + 6.5E.6 (executado em 2026-04-15) ✅


Terceiro bloco da reordenação CTO: blindar fronteira tenant↔tenant antes de qualquer test de UI. Sem isso, beta com >1 user é roleta russa.

- **6.5B.12** [`backend/tests/test_multi_tenant_isolation.py`](../../../backend/tests/test_multi_tenant_isolation.py) — **27 tests**:
  - Fixture `tenants` cria 2 universos paralelos (User A + Workspace A com `family_surname="Alves"` + 9 entidades vs User B com `family_surname="Brito"`)
  - 9 domínios cobertos: workspace settings, members + bank accounts, categories, documents, vault, pipeline runs + reviews, reports, transactions, LLM config, notifications
  - Cada classe testa: (a) GET retorna só dados de A, (b) mutação por path-id de B retorna 404
  - Helper `_assert_no_b_leak` faz dump JSON e busca signatures de B (IDs + valores únicos: `Brito`, `Bob Brito`, `claude-haiku-4-5`, etc.)
  - Sanity test: B continua vendo seus dados (cobre falso negativo no setup)
- **6.5E.6** [`backend/tests/test_neutral_global_defaults.py`](../../../backend/tests/test_neutral_global_defaults.py) — **3 tests** + fix em [`backend/app/api/config.py`](../../../backend/app/api/config.py):
  - **Vazamento detectado durante auditoria:** BUG-004 só strippava CPF; `full_name`, `short_name`, `data_nascimento` do founder ainda vazavam via `_convert_members_json_to_schemas`
  - **2º vazamento:** `_export_family_members` retornava `_load_global_json("family_members.json")` cru para tenant vazio (founder full identity + surname "Andrade Silva")
  - **Fix systemic:** `_NEUTRAL_PLACEHOLDER_NAMES` por role (Titular Exemplo, Cônjuge Exemplo, etc.) + export retorna `{"membros": {}}` para tenant sem members
  - Tests anti-leak via `_FOUNDER_LEAK_SIGNALS` set (8 sinais de identidade do founder)

**Resultado agregado Bloco 2:** 30 passing em ~12s.

**Bug encontrado e corrigido nas factories:** `make_member` default `role="responsavel"` não passava validação de schema (`^(titular|conjuge|filho|dependente)$`). Corrigido para `role="titular"`.

**Resultado consolidado Bloco 1 + Bloco 2:** 87 passing + 2 skipped em 16.59s.

## 🧪 — Bloco 3a — Unit Tests Frontend 6.5A (executado em 2026-04-15) ✅


Quarto bloco da reordenação CTO: unit tests do `lib/` consumindo a fundação criada no Bootstrap.

- **6.5A.6** `frontend/tests/lib/utils.test.ts` — **9 tests** (`cn()` clsx + tailwind-merge: concatenação, falsy, conflitos Tailwind, variants condicionais)
- **6.5A.3** [`frontend/tests/lib/format.test.ts`](../../../frontend/tests/lib/format.test.ts) — **102 tests**:
  - 9 formatters (currency BRL/USD, percent, delta, compact, number, bytes, duration, date)
  - 4 status maps (docStatus, docType, runStatus, stageStatus, bankLabel) cobrindo TODOS os enums conhecidos via parametrização
  - Stage display names parametrizado
  - **Property-based via `fast-check`** (F6.5D.2 antecipada): BRL sempre tem R$ + 2 decimais, separadores BR íntegros, percent inverte sinal corretamente, formatDelta positivo sempre `+`, formatBytes monotônico
- **6.5A.4** [`frontend/tests/lib/export.test.ts`](../../../frontend/tests/lib/export.test.ts) — **16 tests** (CSV BOM UTF-8, delimitador `;`, MIME, acentos, XLSX MIME spreadsheetml, auto-width via spy em `book_append_sheet`, sheet names, round-trip XLSX)
- **6.5A.5** [`frontend/tests/lib/api.test.ts`](../../../frontend/tests/lib/api.test.ts) — **17 tests** (token mgmt, Bearer header, Content-Type, ApiError 401/422/500, 204 No Content, XHR upload com progress events + ApiError 4xx)
- **6.5A.7** [`frontend/tests/lib/usePipelineWS.test.tsx`](../../../frontend/tests/lib/usePipelineWS.test.tsx) — **15 tests** (mock WebSocket, connect com URL-encoded token, status transitions, heartbeat ignorado, terminal events `run_completed/failed/cancelled`, reconnect com backoff exponencial, max retries → `failed`, close 1000 sem reconnect, contador zerado em sucesso, cleanup ao desmontar/runId change)
- **6.5A.8** [`frontend/vitest.config.ts`](../../../frontend/vitest.config.ts) — thresholds calibrados (5% global, 65% lib/) com TODOs para subir em 6.5B/D

**Resultado Bloco 3a:** 167/167 passing em 1.15s. Coverage: utils 100%, format 98.96%, export 100%, usePipelineWS 97.75%, api 35.57% (50+ endpoints ficam para integration tests em 6.5B).

**Achados não previstos:**
- jsdom 25 + vitest 2.1.x: `Blob.text()` e `Blob.arrayBuffer()` quebrados → workaround spy no construtor `Blob` para capturar `parts` + `options` diretamente
- `WebSocket` é `readonly` no globalThis → `vi.stubGlobal()` em vez de assignment
- `XLSX.utils.book_append_sheet` precisa ser espionado para validar `!cols` (auto-write não persiste no formato XLSX, é metadata runtime)

## 🧩 — Bloco 3b — Integration Tests 6.5B (executado em 2026-04-15) ✅


Quinto bloco da reordenação CTO. Cobertura completa de 6.5B com integration tests para todas as 10 pages, 8 compostos, dark mode, form validation, WS real e tz regression. Restou minoria de detalhes (tabs individuais de Config, Reports viewer React nativo) para PRs focados em sequência.

**Pages (10 pages):**
- **6.5B.1** [`pages/login.test.tsx`](../../../frontend/tests/pages/login.test.tsx) — **8 tests** + [`pages/register.test.tsx`](../../../frontend/tests/pages/register.test.tsx) — **6 tests**
- **6.5B.2** `frontend/tests/pages/dashboard.test.tsx` — **7 tests** (Recharts mockado; KPIs, empty/error/loading, refresh, retry)
- **6.5B.3** [`pages/documents.test.tsx`](../../../frontend/tests/pages/documents.test.tsx) — **8 tests** (drop zone, empty CTA, banner needs_password, delete via ConfirmDialog)
- **6.5B.4** [`pages/pipeline.test.tsx`](../../../frontend/tests/pages/pipeline.test.tsx) — **7 tests** (trigger, contador docs ready, **BUG-007 anti-regression: free→skip_llm:true / premium→false**)
- **6.5B.5** [`pages/transactions.test.tsx`](../../../frontend/tests/pages/transactions.test.tsx) — **4 tests** + **XSS smoke F6.5D.6 antecipada** (`<script>` + `<img onerror>` em descrição renderizados escapados)
- **6.5B.6** [`pages/reports.test.tsx`](../../../frontend/tests/pages/reports.test.tsx) — **5 tests** (lista, empty CTA, link individual)
- **6.5B.7** [`pages/config.test.tsx`](../../../frontend/tests/pages/config.test.tsx) — **5 tests** (7 tabs presentes, default Members, navegação tab→tab, LLM tab fetch)
- **6.5B.8** [`pages/vault.test.tsx`](../../../frontend/tests/pages/vault.test.tsx) — **9 tests** (CRUD passwords, retry-unlock com contador)
- **6.5B.9** [`components/AppShell.test.tsx`](../../../frontend/tests/components/AppShell.test.tsx) — **9 tests** (auth gate, **BUG-005 anti-regression: Vault no nav**, logout, mobile sidebar)

**Composites (8 compostos):**
- **6.5B.10** [`components/composites.test.tsx`](../../../frontend/tests/components/composites.test.tsx) — **26 tests** (KPICard, EmptyState com CTA F6.5D.12, StatusBadge param, Delta com aria-label semântico, Spinner anti-regressão OP-011)
- + [`components/composites-extra.test.tsx`](../../../frontend/tests/components/composites-extra.test.tsx) — **13 tests** (ConfirmDialog, ThemeToggle, DataTable com sort + onRowClick)

**Dark mode (6.5B.11):** [`components/dark-mode.test.tsx`](../../../frontend/tests/components/dark-mode.test.tsx) — **10 tests** (validação de classes semânticas, sem cores hardcoded green/red, todos os 7 variants do StatusBadge sob dark)

**Form validation (6.5B.13):** [`integration/form-validation.test.tsx`](../../../frontend/tests/integration/form-validation.test.tsx) — **8 tests** (HTML5 type=email/password, required, minLength, paramétrico Login + Register; CPF mod-11/duplicate cobertos via ApiError em login/register tests)

**WS real (6.5B.14):** [`backend/tests/test_websocket_integration.py`](../../../backend/tests/test_websocket_integration.py) — **4 tests** com fakeredis (rejeita JWT inválido com 4001, aceita válido, mensagem via pub/sub chega, terminal event fecha conexão)

**TZ regression (6.5B.15):** [`lib/timezone.test.ts`](../../../frontend/tests/lib/timezone.test.ts) — **5 tests** (formatDate com Z, **BUG OP-010 anti-regression: ISO sem Z != ISO com Z**, formatElapsed com tz-aware system time)

**Resultado Bloco 3b consolidado:**
- Frontend: **305 tests passing em 6.42s** (21 arquivos)
- Backend: **91 passing + 2 skipped em ~18s** (incluindo Bootstrap + 6.5E + 6.5B.12 + 6.5B.14)
- **Total F6.5: 396 tests passing em ~24s**

**Achados não previstos do Bloco 3b:**
- base-ui Tabs usa `aria-selected="true"` (não `data-state="active"` como Radix)
- shadcn `CardTitle` não tem role="heading" semântico (usar `data-slot="card-title"`)
- shadcn `Skeleton` usa `data-slot="skeleton"` (não classe `bg-accent`)
- shadcn `Button render={<a>}` não emite role="link" — buscar via `closest("a")`
- factory `make_member(role="responsavel")` falhava schema (corrigido para `"titular"`)

**Pendente para PRs sucessivos** (não bloqueador):
- 6.5B.6 Reports viewer (React nativo, print, download tables) — concluído em F9
- 6.5B.7 Tabs individuais (CategoriesTab, PipelineTab, LLMTab CRUD) — cobertura por tab
- 6.5B.10 NotificationCenter (interaction completa)

## 🛡️ — Bloco 4 — Hardening Fintech 6.5D (executado em 2026-04-15) ✅


Sexto bloco da reordenação CTO. Cobre todos os itens P0 de 6.5D e scaffolds para os P1 (Lighthouse, bundle size, contract test, CWV) — ativáveis em CI quando infra estiver estável.

**Entregas P0:**

- **6.5D.1 axe-core** [`frontend/tests/a11y/accessibility.test.tsx`](../../../frontend/tests/a11y/accessibility.test.tsx) — **13 tests** (compostos + 5 pages). Gate: 0 critical/serious. **2 violations reais detectadas e fixadas** no código fonte:
  - `../frontend/src/app/(app)/documents/page.tsx`: `aria-label` no file input hidden + `aria-label` dinâmico em cada botão delete
  - `../frontend/src/app/(app)/vault/page.tsx`: `aria-label` em botão delete por senha
- **6.5D.2 Property-based BRL** — já cumprido em Bloco 3a com 5 property-based tests via `fast-check` em `format.test.ts`
- **6.5D.4 Cross-browser** — já cumprido em Bootstrap com `playwright.config.ts` configurado com 3 projects (chromium + firefox + webkit) e grep `@critical`
- **6.5D.5 Resilience** [`frontend/tests/integration/resilience.test.tsx`](../../../frontend/tests/integration/resilience.test.tsx) — **8 tests** (5xx 502/503/504, network error vs ApiError, retry após 5xx, navigator.onLine events online/offline, slow response tolerance). WS reconnect cobre 15 tests em 6.5A.7
- **6.5D.6 Security smoke** [`frontend/tests/integration/security-smoke.test.tsx`](../../../frontend/tests/integration/security-smoke.test.tsx) — **8 tests** (XSS em member.full_name + category.name + vault.label + transação.descrição; JWT expiry mid-session → 401 → clearToken + redirect; logout cleanup cirúrgico de fin_token)
- **6.5D.7 Fixtures auditadas**:
  - [`tests/utils/cpf.py`](../../../tests/utils/cpf.py): gerador mod-11 determinístico (seed → CPF válido reproduzível) + validator `is_valid_cpf`
  - [`tests/utils/lint_no_real_pii.py`](../../../tests/utils/lint_no_real_pii.py): scan recursivo de `tests/`, `backend/tests/`, `frontend/tests/` procurando padrão `\d{3}\.\d{3}\.\d{3}-\d{2}`. Whitelist: placeholders (000.000.000-00 etc.) + anotação `# noqa: PII-ok` por linha. **7 CPFs reais substituídos** por gerado+noqa (test_config_api, test_config_materializer, test_config_models, test_serializers_round_trip). Lint green.
- **6.5D.11 Error boundary** [`frontend/src/components/ErrorBoundary.tsx`](../../../frontend/src/components/ErrorBoundary.tsx) + `../frontend/src/app/(app)/layout.tsx` wrap + [`frontend/tests/components/ErrorBoundary.test.tsx`](../../../frontend/tests/components/ErrorBoundary.test.tsx) — **6 tests** (children passam sem erro, captura erro + fallback, reset volta a renderizar, onError callback, fallback customizado, crash isolado em subárvore sem derrubar siblings)
- **6.5D.12 Empty state CTA audit** — coberto em 6.5B tests (Documents "Enviar documentos", Reports "Enviar documentos → /documents", Dashboard "Ir para Pipeline", Vault "Adicionar senhas")
- **6.5D.13 Focus management** [`frontend/tests/integration/focus-mgmt.test.tsx`](../../../frontend/tests/integration/focus-mgmt.test.tsx) — **3 tests** (dialog open → foco dentro, dialog close → trigger retorna, form submit mantém foco; SPA route change deferido para Playwright E2E)

**Scaffolds P1 (ativar em CI quando build estável):**

- **6.5D.3 Visual regression** [`frontend/tests/e2e/visual-regression.visual.spec.ts`](../../../frontend/tests/e2e/visual-regression.visual.spec.ts) — 5 specs (login light/dark, register, AppShell mobile 360px, documents empty). Baseline capturada em CI primeiro run (Playwright projeto `visual` isolado com `maxDiffPixelRatio: 0.01`).
- **6.5D.8 Lighthouse CI** [`frontend/.lighthouserc.json`](../../../frontend/.lighthouserc.json) — 4 URLs (login/dashboard/documents/reports) × 3 runs; thresholds: perf warn 85, a11y error 95, bp warn 90, SEO off.
- **6.5D.9 Bundle size** [`frontend/.size-limit.json`](../../../frontend/.size-limit.json) — budgets por route chunk (dashboard <250KB, transactions <200KB, reports <300KB, main app <1MB).
- **6.5D.10 Contract test** [`frontend/scripts/contract-check.mjs`](../../../frontend/scripts/contract-check.mjs) — baixa openapi.json do backend → roda openapi-typescript → diff vs `tests/contracts/openapi.types.d.ts` snapshot. Requer backend UP.
- **6.5D.14 Core Web Vitals** — coberto parcialmente via Lighthouse; script dedicado com `web-vitals` lib em Playwright E2E deferido para 6.5C.

**Resultado Bloco 4 agregado frontend:** +47 novos testes (13 a11y + 6 error boundary + 8 security + 8 resilience + 3 focus + 4 misc em XSS/JWT/logout = 47 tests adicionais para um total frontend de **344 passing + 1 skipped em 14.07s**).

**Resultado consolidado F6.5 (Bootstrap + Blocos 1-4) até agora:**
- Frontend: **344 passing + 1 skipped em 14.07s** (26 arquivos de teste)
- Backend: **91 passing + 2 skipped em ~21s** (serializers + alembic + golden pipeline + regressions + multi-tenant + neutral defaults + WS integration)
- **Total: 435 tests passing em ~35s**

**Achados não previstos do Bloco 4:**
- axe-core detectou 2 **a11y violations REAIS** em produção (file input sem label + delete buttons sem aria-label). Corrigidos no source.
- Lint anti-PII detectou 7 CPFs reais em tests backend (do founder, `123.456.789-09`) — substituídos por CPF gerado (mod-11 válido) + anotação `noqa: PII-ok`.
- `config/` tem 8+ CPFs reais do founder (definitions.md + family_members.json) — **NÃO é fixture de teste**, é config dev-time real. Neutralização via API já coberta em 6.5E.6. Lint explicitamente exclui `config/`.
- Template literal para aria-label dinâmico (`aria-label={\`Remover senha ${pw.label}\`}`) foi a ergonomia escolhida.

**Critérios de aceite F6.5 ATENDIDOS após Bloco 4:**
- ✅ axe-core: 0 violations critical/serious em pages + compostos principais
- ✅ Fixtures sintéticas auditadas — gerador mod-11 + lint CI anti-PII
- ✅ Todas as pages com error boundary (via layout wrap)
- ✅ Empty states com CTA acionável
- ✅ Focus management em dialogs
- ❌ Visual regression baseline versionado — scaffold pronto, aguarda primeiro run em CI
- ❌ Cross-browser rodando em CI — config pronto, depende de 6.5F.3 backend-real
- ❌ Lighthouse/size-limit/contract rodando em CI — scaffolds prontos, aguardam F7C CI/CD

## 🎯 — Bloco 5 — E2E + Smoke + CI 6.5C + 6.5F.4 (executado em 2026-04-15) ✅


Sétimo bloco da reordenação CTO. E2E coverage via Playwright + Smoke checklist manual + GH Actions CI + pipeline mock fixtures para viabilizar Golden Path em CI rápido.

**E2E specs (9 specs, ~25 tests, tagged `@critical` para cross-browser):**

- **6.5C.0** [`golden-path.spec.ts`](../../../frontend/tests/e2e/golden-path.spec.ts) — **O GATE SAGRADO**: registro → setup surname → upload sintético → trigger pipeline → report contém `FAMILY_SURNAME` (BUG-015 regression inline). Timeout 5min (com mock fixtures cai para 30s).
- **6.5C.2** [`onboarding.spec.ts`](../../../frontend/tests/e2e/onboarding.spec.ts) — 5 tests @critical (happy, email duplicado, senha curta HTML5, link register↔login, login inválido)
- **6.5C.3** [`upload-pipeline-report.spec.ts`](../../../frontend/tests/e2e/upload-pipeline-report.spec.ts) — 3 tests @critical (cancel mid-pipeline, real-pipeline opt-in, **BUG-007 regression: premium → skip_llm=false** via route interceptor)
- **6.5C.4** [`config-round-trip.spec.ts`](../../../frontend/tests/e2e/config-round-trip.spec.ts) — 2 tests (criar membro UI + export JSON, family_surname persiste)
- **6.5C.5** [`vault.spec.ts`](../../../frontend/tests/e2e/vault.spec.ts) — 2 tests (CRUD + retry-unlock 0-desbloqueados)
- **6.5C.6** [`drill-down.spec.ts`](../../../frontend/tests/e2e/drill-down.spec.ts) — 3 tests (URL state filters em `/transactions`)
- **6.5C.7** [`dark-mode.spec.ts`](../../../frontend/tests/e2e/dark-mode.spec.ts) — 1 test @critical (toggle → reload → dark persiste)
- **6.5C.8** [`error-auth.spec.ts`](../../../frontend/tests/e2e/error-auth.spec.ts) — 5 tests @critical (sem token → /login, token inválido → clearToken, 404, /login sempre acessível)
- **6.5C.9** [`notifications.spec.ts`](../../../frontend/tests/e2e/notifications.spec.ts) — 2 tests (bell opens sheet)

**Smoke Checklist** ([`docs/reference/SMOKE_TEST.md`](../../reference/SMOKE_TEST.md)): 13 seções, 70+ checks manuais. Inclui:
- Seção 8 (Multi-tenant) e 12 (LGPD pré-beta) com gates de rollback
- Checks dedicados às regressões: **BUG-015** (cover com surname), **BUG-007** (skip_llm tier), **ADR-068** (fases narrativas, zero códigos E* na UI)

**CI GH Actions** ([`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml)): **7 jobs** — lint (pre-commit), lint-pii, pipeline-tests, backend-tests (+ Redis service), frontend-tests (Vitest + JUnit), frontend-e2e (condicional: push main OU label `e2e` em PR) com Playwright cross-browser + PG+Redis services + alembic upgrade + artifacts retidos 30d, all-green gate de merge.

**Mock fixtures** ([`backend/tests/fixtures/pipeline_runs.py`](../../../backend/tests/fixtures/pipeline_runs.py)): `seed_completed_run()` cria `PipelineRun(status="completed")` + 13 `PipelineStageLog` + `Report` com HTML stub em `storage/{ws_id}/output/`. Permite 6.5C.0/C.3 rodarem <30s em CI default; `PW_REAL_PIPELINE=1` para opt-in nightly com pipeline real.

**Resultado Bloco 5:** frontend suite segue **344 passing + 1 skipped em 4.14s** (E2E specs não executadas localmente — rodam em CI contra backend real).

**Achados não previstos:**
- Route interceptor Playwright (`page.route`) captura POST body elegantemente — usado para BUG-007 anti-regression sem precisar rodar pipeline
- SMOKE_TEST.md expande de "30+ checks" para 70+ porque ADR-068 e multi-tenant justificaram seções dedicadas
- GH Actions `all-green` job é o padrão de "gate de merge" pré-configurado para branch protection rules

## 🔧 — Bloco 6 — 6.5F residuais + 6.5E.7 (executado em 2026-04-15) ✅


Oitavo e **último bloco da F6.5**: ADRs de infraestrutura de teste + scripts de lint/mock + concurrency test. Fecha a fase inteira.

**Entregas:**

- **6.5E.7** `backend/tests/test_materialize_concurrency.py` — **3 tests** (2 workspaces paralelos / idempotency mesmo ws / 10 workspaces simultâneos com `ThreadPoolExecutor`). SQLite file-based + `check_same_thread=False` para thread-safety.
- **6.5F.5** [ADR-069 MSW sync](../../DECISIONS.md#adr-069--msw-sync-strategy-manual--lint-ci-não-codegen) + [`frontend/scripts/msw-lint.mjs`](../../../frontend/scripts/msw-lint.mjs) — AST regex sobre `http.<method>("/api/...")` em handlers.ts vs `openapi.json` do backend; `--spec`, `--allow-extra`, filtro de WS endpoints.
- **6.5F.6** [ADR-071 Workspace isolation](../../DECISIONS.md#adr-071--playwright-workspace-isolation-email-unique-por-worker) — email-per-worker decision ratificada; implementação já estava em Bootstrap (`userForWorker(info)` usa `parallelIndex` + `STAMP`).
- **6.5F.8** Flaky test policy em [`docs/reference/TESTING.md#flaky-test-policy--f65f8`](../../reference/TESTING.md#flaky-test-policy--f65f8) — `retries: 2` CI / 0 local (já em `playwright.config.ts`), quarentena via `test.skip(true, "flaky: TODO BUG-XXX")`, plano de report semanal.
- **6.5F.9** CI reporter expandido em [`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml):
  - `actions/upload-artifact@v4` para playwright-report (30d), backend-coverage (14d), frontend-vitest-results (14d)
  - `actions/github-script@v7` posta comment em PRs com link para o artifact
  - Tabela de artifacts em [`TESTING.md#como-debugar-falha-em-ci`](../../reference/TESTING.md#como-debugar-falha-em-ci)
- **6.5F.10** Snapshot review em [`.github/CODEOWNERS`](../../../.github/CODEOWNERS) — review obrigatório em `/frontend/tests/e2e/__snapshots__/`, `/backend/alembic/versions/`, `/tests/fixtures/`, `/docs/DECISIONS.md`. Workflow completo em [`TESTING.md#como-atualizar-snapshot-visual-regression--f65f10`](../../reference/TESTING.md#como-atualizar-snapshot-visual-regression--f65f10) com PR template checklist.
- **6.5F.11** [ADR-070 Premium LLM E2E](../../DECISIONS.md#adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in) + [`backend/tests/fixtures/llm_mock.py`](../../../backend/tests/fixtures/llm_mock.py) — fixtures válidas por stage (E1, E1.5, E2-llm, E7-review); `MATHOMS_LLM_MOCK=1` default em CI; nightly workflow `nightly-e2e-real-llm.yml` com `PW_REAL_LLM=1` + ANTHROPIC_API_KEY em secret (scaffold documentado, workflow de CI a ativar pós-primeiro-run).
- **6.5F.14** Pre-commit hooks (já entregues em commit `a7a055d`): `.pre-commit-config.yaml` + `dev/check_forbidden_paths.py` + `dev/validate_commit_msg.py`.

**3 novas ADRs** registradas: [ADR-069](../../DECISIONS.md#adr-069--msw-sync-strategy-manual--lint-ci-não-codegen), [ADR-070](../../DECISIONS.md#adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in), [ADR-071](../../DECISIONS.md#adr-071--playwright-workspace-isolation-email-unique-por-worker). Índice de ADRs na seção "Testing" atualizado.

**Resultado Bloco 6 agregado:** +3 backend tests (concurrency), ~370 linhas de ADRs, +2 scripts (msw-lint.mjs + llm_mock.py fixture), +1 CODEOWNERS. Frontend suite segue 344 passing.

## 6.5A — Tooling Setup + Unit Tests (semana 1, dias 1-3)


| #      | Tarefa                                                                      | Prio | Est. | Status |
| ------ | --------------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5A.1 | Setup Vitest (`vitest.config.ts`, jsdom, path aliases, coverage v8)         | P0   | 2h   | ✅ Bootstrap |
| 6.5A.2 | Setup MSW (`tests/mocks/server.ts` + handlers + fixtures JSON)              | P0   | 3h   | ✅ Bootstrap |
| 6.5A.3 | Unit tests `format.ts` (9 formatters + 3 status maps, ~40 cases) — incluir property-based via `fast-check` (round-trip, edge BRL) | P0 | 5h | ✅ Bloco 3 (102 tests, format.ts 98.96% line) |
| 6.5A.4 | Unit tests `export.ts` (CSV BOM, XLSX auto-width, mock document.createElement) | P0 | 2h | ✅ Bloco 3 (16 tests, 100% line) |
| 6.5A.5 | Unit tests `api.ts` (token mgmt, apiFetch, ApiError, 401 redirect)          | P0   | 3h   | ✅ Bloco 3 (17 tests; api.ts em 35% line — restantes endpoints subem via integration tests em 6.5B) |
| 6.5A.6 | Unit tests `utils.ts` (`cn()` Tailwind merge)                               | P0   | 1h   | ✅ Bloco 3 (9 tests, 100% line) |
| 6.5A.7 | Unit tests `usePipelineWS.ts` (connect, events, reconnect backoff + jitter, polling fallback após 3 falhas, offline) | P1 | 4h | ✅ Bloco 3 (15 tests, 97.75% line) |
| 6.5A.8 | Coverage baseline + thresholds em `vitest.config.ts`                        | P0   | 1h   | ✅ Bloco 3 (thresholds calibrados por sub-fase; sobem em 6.5B/D) |

**Checkpoint:** ~50-60 unit tests green. `npm test` <5s.

## 6.5B — Integration Tests — Pages + Components (semana 1-2)


| #       | Tarefa                                                                     | Prio | Est. | Status |
| ------- | -------------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5B.1  | Tests Login/Register (render, submit, errors, loading)                     | P0   | 3h   | ✅ Bloco 3b (Login 8 tests + Register 6 tests) |
| 6.5B.2  | Tests Dashboard (KPIs, charts, empty, error, loading, drill-down, refresh) | P0   | 4h   | ✅ Bloco 3b (7 tests, Recharts mockado) |
| 6.5B.3  | Tests Documents (empty, drag-drop, progress, needs_password, delete, CTA)  | P0   | 4h   | ✅ Bloco 3b (8 tests) |
| 6.5B.4  | Tests Pipeline (trigger, WS progress, needs_review, cancel, failed)        | P0   | 5h   | ✅ Bloco 3b (7 tests + cobre BUG-007 skip_llm tier) |
| 6.5B.5  | Tests Transactions (render, busca, override, export, paginação, URL state) — incluir XSS smoke: nota com `<script>`/`<img onerror>` deve renderizar escapado | P0 | 5h | ✅ Bloco 3b (4 tests + XSS smoke F6.5D.6 antecipada) |
| 6.5B.6  | Tests Reports (list, viewer React nativo, print, download, export tables)  | P0   | 4h   | ✅ Bloco 3b (5 tests; viewer concluído em F9) |
| 6.5B.7  | Tests Config (6 tabs: Members, Categories, Pipeline, LLM, Inst, Layout)    | P0   | 5h   | ✅ Bloco 3b (5 tests; tabs individuais pendentes em PR focado) |
| 6.5B.8  | Tests Vault (CRUD passwords, retry unlock)                                 | P0   | 2h   | ✅ Bloco 3b (9 tests) |
| 6.5B.9  | Tests AppShell (auth gate, navigation, mobile, logout, NotificationCenter) | P0   | 3h   | ✅ Bloco 3b (9 tests + cobre BUG-005 Vault no nav) |
| 6.5B.10 | Tests compostos (KPICard, EmptyState, StatusBadge, ConfirmDialog, Delta, Spinner, ThemeToggle, DataTable) | P1 | 3h | ✅ Bloco 3b (8 compostos: 26 + 13 = 39 tests) |
| 6.5B.11 | Tests dark mode (7 compostos + Dashboard charts + Transaction table)       | P1   | 2h   | ✅ Bloco 3b (10 tests; classes semânticas + tokens design system + dark class no html) |
| 6.5B.12 | **Multi-tenant isolation suite** (backend, paramétrica): para CADA endpoint write/read, criar 2 workspaces (A e B) + dados em ambos; chamar como user A → assert que dados de B nunca aparecem. Inclui: members, categories, documents, runs, reports, transactions, vault, llm_config, notifications. **Sem isso, beta com >1 user é roleta russa** | P0 | 6h | ✅ Bloco 2 (27 tests, 0 vazamentos) |
| 6.5B.13 | **Form validation suite** (frontend): 6 forms (Login, Register, Member create, Bank account, Vault password, Family surname) × validações (required, email format, password strength, max length, CPF mod-11, duplicate key). Mensagens user-facing testadas | P0 | 4h | ✅ Bloco 3b (8 tests cobrindo Login + Register HTML5 validation; CPF mod-11 + duplicate via ApiError em login/register tests) |
| 6.5B.14 | **WebSocket integration real** (com Redis pub/sub real, não mock): backend publica evento de stage → JWT auth → frontend recebe em <500ms; multiplos clients no mesmo run; reconnect mid-stage não perde eventos posteriores | P0 | 4h | ✅ Bloco 3b (4 backend tests com fakeredis: JWT 4001, accept válido, mensagem via pub/sub, terminal event close) |
| 6.5B.15 | **Date/timezone regression suite**: `started_at`/`completed_at`/`created_at` sempre com tz-aware (regressão BUG do dogfood); render no frontend mostra hora local correta; teste em browsers com TZ=`America/Sao_Paulo`, `UTC`, `America/New_York` | P0 | 3h | ✅ Bloco 3b (5 frontend tests `tests/lib/timezone.test.ts` + cobertura backend OP-010 em 6.5E.8) |

**Checkpoint:** ~140-170 integration tests green. `npm test` <30s. Multi-tenant isolation: 0 vazamentos. Form validation: 100% mensagens cobertas.

## 6.5C — E2E Tests + Smoke Checklist (semana 2)


| #       | Tarefa                                                              | Prio | Est. | Status |
| ------- | ------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5C.1  | Setup Playwright (`playwright.config.ts`, webServer, auth helper, projects: chromium + firefox + webkit) | P0 | 4h | ✅ Bootstrap |
| 6.5C.0  | **E2E Golden Path End-to-End** — fluxo único encadeado: registro fresh → login → **definir Sobrenome da família** (config/members) → upload de PDFs sintéticos (extrato + fatura) → vault unlock se necessário → trigger pipeline (free tier) → aguardar WS até E6 completo → abrir relatório → validar conteúdo: (1) KPIs presentes, (2) charts renderizados, (3) score >0, (4) **`{{COVER_FAMILIA}}` da capa contém o sobrenome definido** (regressão BUG-015), (5) nome do arquivo HTML inclui o sobrenome. **Test único, não-paramétrico, smoke do produto inteiro.** | P0 | 4h | ✅ Bloco 5 (spec completo @critical; BUG-015 regression assertion inline) |
| 6.5C.2  | E2E Fluxo 1 — Onboarding completo (variações: erros de validação, email duplicado, password fraca) | P0 | 3h | ✅ Bloco 5 (5 tests @critical) |
| 6.5C.3  | E2E Fluxo 2 — Upload → Pipeline → Report (variações: needs_review, cancel mid-stage, retry de stage falho, premium tier com LLM) | P0 | 5h | ✅ Bloco 5 (3 tests @critical incluindo BUG-007 premium skip_llm=false) |
| 6.5C.4  | E2E Fluxo 3 — Config round-trip (criar membro → export JSON)        | P0   | 3h   | ✅ Bloco 5 (2 tests) |
| 6.5C.5  | E2E Fluxo 4 — Vault + Unlock                                        | P1   | 3h   | ✅ Bloco 5 (2 tests) |
| 6.5C.6  | E2E Fluxo 5 — Drill-down Dashboard → Transactions                   | P1   | 3h   | ✅ Bloco 5 (3 tests: URL state persist) |
| 6.5C.7  | E2E Fluxo 6 — Dark mode persistência                                | P0   | 2h   | ✅ Bloco 5 (1 test @critical) |
| 6.5C.8  | E2E Fluxo 7 — Error handling e auth redirect                        | P0   | 2h   | ✅ Bloco 5 (5 tests @critical: sem token, invalid token, 404, /login) |
| 6.5C.9  | E2E Fluxo 8 — Notifications (bell + Sheet + mark read)              | P1   | 2h   | ✅ Bloco 5 (2 tests) |
| 6.5C.10 | Smoke test checklist (`docs/reference/SMOKE_TEST.md`, 30+ checks) — incluir seção LGPD pré-beta: nenhum dado real em fixtures, audit do localStorage pós-logout | P0 | 3h | ✅ Bloco 5 ([`docs/reference/SMOKE_TEST.md`](../../reference/SMOKE_TEST.md): 13 seções, 70+ checks, LGPD + anti-regressions) |
| 6.5C.11 | CI integration (GH Actions com PostgreSQL + Redis services)         | P0   | 3h   | ✅ Bloco 5 ([`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml): 7 jobs; E2E com PG+Redis services e Playwright cross-browser condicional) |

**Checkpoint:** ~25-30 E2E tests green cobrindo Golden Path + 8 fluxos críticos. `docs/reference/SMOKE_TEST.md` criado. **Golden Path (6.5C.0) é o gate sagrado:** se ele falha, deploy não sai — independente do resto.

## 6.5D — Hardening Fintech (semana 2-3, 3-4 dias)


> Sub-fase dedicada para garantir que itens P0 fintech-specific (a11y, visual regression, resilience, security smoke) não sejam cortados sob pressão de prazo. Ver [ADR-063](../../DECISIONS.md#adr-063--hardening-fintech-em-sub-fase-65d).

| #       | Tarefa                                                                                                | Prio | Est. | Status |
| ------- | ----------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5D.1  | `axe-core` integrado (`vitest-axe` em integration + `@axe-core/playwright` em E2E). Gate: 0 critical/serious | P0 | 4h | ✅ Bloco 4 (13 tests; 2 violations reais fixadas: aria-label em file input + delete button) |
| 6.5D.2  | Property-based em `format.ts` via `fast-check` (BRL: negativos, micro-valores, R$ 9B+, NaN/null; round-trip) | P0 | 3h | ✅ Bloco 3a (antecipado: 5 property-based em `format.test.ts`) |
| 6.5D.3  | Visual regression (Playwright `toHaveScreenshot()`): 4 charts Recharts, 3 KPI states, dark/light, print preview, AppShell mobile (~12 snapshots) | P0 | 4h | 🚧 Bloco 4 scaffold (5 specs em `visual-regression.visual.spec.ts`; baseline capturada em CI primeiro run) |
| 6.5D.4  | Cross-browser: `playwright.config` adiciona `firefox` + `webkit`; rodar 3 fluxos críticos (Onboarding, Upload→Pipeline→Report, Vault) | P0 | 2h | ✅ Bootstrap (playwright.config.ts já configurado com 3 projetos + grep @critical) |
| 6.5D.5  | Resilience suite: WS drop+reconnect com jitter, polling fallback ativa após 3 falhas, `navigator.onLine` banner, backend 502/503 → toast com retry, slow 3G via `page.route` | P0 | 5h | ✅ Bloco 4 (8 tests: 5xx, network error, retry, navigator.onLine events; WS cobre 15 tests em 6.5A.7) |
| 6.5D.6  | Security smoke: XSS em 4 campos user-controlled (transação.nota, member.full_name, category.name, vault.label), JWT expiry mid-sessão (upload em andamento), logout limpa localStorage | P0 | 4h | ✅ Bloco 4 (8 tests: 4 XSS fields, JWT expiry, logout cleanup; transação.nota cobre em 6.5B.5) |
| 6.5D.7  | Fixtures sintéticas auditadas: gerador CPF mod-11 determinístico, lint custom CI falha se detectar `\d{3}\.\d{3}\.\d{3}-\d{2}` real, repositório de PDFs sintéticos versionados separados | P0 | 3h | ✅ Bloco 4 (tests/utils/cpf.py + lint_no_real_pii.py; lint green após substituir 7 CPFs reais por gerado+noqa) |
| 6.5D.8  | Lighthouse CI (perf>85, a11y>95, best-practices>90; SEO ignorado). **Modo medir, não bloquear** (gate vira hard em F7D.7) | P1 | 3h | 🚧 Bloco 4 scaffold (`.lighthouserc.json` com 4 URLs + thresholds warn; ativar em CI quando build estável) |
| 6.5D.9  | Bundle size budget (`@next/bundle-analyzer` + `size-limit` em CI; budget por chunk: dashboard <250KB, transactions <200KB, reports <300KB) | P1 | 2h | 🚧 Bloco 4 scaffold (`.size-limit.json` com budgets por route chunk; rodar após `npm run build`) |
| 6.5D.10 | Contract test FE↔BE: `openapi-typescript` em CI gera types do OpenAPI do backend; diff vs `lib/api.ts` types → fail se drift | P1 | 4h | 🚧 Bloco 4 scaffold (`scripts/contract-check.mjs` baixa openapi.json + diff snapshot; requer backend UP + primeiro run baseline) |
| 6.5D.11 | **Error boundary audit**: cada página sob `(app)/` envolvida em `<ErrorBoundary>` (React 19); crash em 1 chart não derruba dashboard inteiro; fallback UI com botão "Recarregar"/"Reportar" | P0 | 3h | ✅ Bloco 4 (ErrorBoundary.tsx class component + layout.tsx wrap + 6 tests; crash em subárvore não derruba siblings) |
| 6.5D.12 | **Empty state CTA audit**: toda empty state tem CTA acionável (ex: "Sem transações" → botão "Subir extrato"); sem dead-ends; revisão sistemática de 10 pages | P1 | 3h | ✅ Bloco 4 (coberto em 6.5B sample tests: Documents CTA, Reports CTA para /documents, Dashboard CTA para /pipeline) |
| 6.5D.13 | **Focus management**: route change manda foco pro `<h1>` da nova página; modal close volta foco pro trigger; form submit mantém foco útil; testes Playwright | P1 | 3h | ✅ Bloco 4 (3 tests: dialog focus, close retorna ao trigger, form submit mantém foco; route-change deferido para Playwright E2E) |
| 6.5D.14 | **Core Web Vitals targets** específicos (não só Lighthouse): LCP <2.5s, INP <200ms, CLS <0.1 — medir via `web-vitals` lib em Playwright no Golden Path; gate soft em 6.5, hard em F7 | P1 | 3h | 🚧 Bloco 4 scaffold (coberto em parte via Lighthouse `.lighthouserc.json`; CWV dedicated script deferido para 6.5C E2E com web-vitals lib) |

**Checkpoint:** axe-core 0 violations critical/serious • visual regression baseline criado e versionado • 3 fluxos green em 3 browsers • resilience + security smoke green • lint anti-PII green em CI • todas as pages com error boundary • empty states com CTA • focus management validado • CWV baseline registrado.

## 6.5E — Backend Hardening (semana 3, 2 dias)


> Sub-fase dedicada a blindar a fronteira DB → pipeline contra a classe de bugs que gerou **BUG-015** (serializers perdendo campos silenciosamente, migrations rodando na DB errada por cwd, dados do founder vazando do fallback global). Ver [ADR-064](../../DECISIONS.md#adr-064--backend-hardening-em-sub-fase-65e).

| #       | Tarefa                                                                                                                                                              | Prio | Est. | Status |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5E.1  | **Round-trip tests para os 6 serializers** do `config_materializer` (family_members, categorization, pipeline, institutions, report_layout, llm_config): DB seed → materialize → ler JSON → assert todos os campos preservados (inclui `familia.sobrenome` após BUG-015) | P0 | 6h | ✅ Bloco 1 |
| 6.5E.2  | **Golden file pipeline com PDFs 100% sintéticos** (zero dado real): fixture completa de workspace + PDFs → orchestrator → E6 HTML → assert estrutura + valores esperados. Reutilizável como base do 6.5C.0 E2E | P0 | 4h | ✅ Bloco 1 (caminho crítico — full E2E pipeline deferido com test skip + docs) |
| 6.5E.3  | **Alembic CI guardrails**: `alembic check` detecta drift entre models e migrations; idempotency test (`upgrade → downgrade → upgrade` = mesmo schema); `alembic upgrade head --sql` preview em PR | P0 | 3h | ✅ Bloco 1 (drift catalog ativo — 4 itens conhecidos a regenerar) |
| 6.5E.4  | **Fix cwd-sensitivity em alembic.ini**: caminho absoluto ou env var `MATHOMS_DATABASE_URL` obrigatória; documentar em SETUP.md que alembic roda da raiz; adicionar guard no `env.py` que rejeita paths relativos ambíguos | P0 | 1h | ✅ Bloco 1 |
| 6.5E.5  | **Test anti-regressão BUG-015**: workspace com `FamilyMember` no DB mas sem `family_surname` definido → materialized `family_members.json` NÃO contém `familia.sobrenome` do global (`"Andrade Silva"` do founder) | P0 | 1h | ✅ Bloco 1 (incluso em 6.5E.1) |
| 6.5E.6  | **Systemic fix para fallback-leak class**: políticas "neutral global defaults" (strip identity fields do `config/family_members.json` antes de copiar pro tenant quando workspace tem membros) + test que cobre cada config | P1 | 4h | ✅ Bloco 2 (extension de BUG-004: full_name/short_name/birth_date neutralizados em GET /config/members fallback + GET /config/export para tenant vazio; 3 tests) |
| 6.5E.7  | **Concurrency test para `_init_config` pattern** (thread-safe em Celery fork pool + múltiplas runs paralelas): 2 workspaces materializando ao mesmo tempo não corrompem configs um do outro | P1 | 3h | ✅ Bloco 6 (`backend/tests/test_materialize_concurrency.py` — 3 tests: 2 workspaces paralelos, idempotency mesmo ws, 10 workspaces simultâneos com `ThreadPoolExecutor`) |
| 6.5E.8  | **Anti-regression bank** (catalogar TODOS bugs já vividos): criar `tests/regressions/` com um teste por bug do `CHANGELOG.md`, nomeado `test_bug_NNN_<slug>.py`. Cobrir BUG-001..BUG-015 (14 bugs UI+backend) + 11 bugs operacionais do dogfood (parse_args/Celery, SystemExit, FERNET persistence, max_tokens E1.5, started_at tz, animate-pulse, _categorization global, skip_llm default, route_to_data_dir, validation pré-pipeline, stages LLM skip gracioso). Cada teste falha SE o fix for revertido | P0 | 5h | ✅ Bloco 1 (20 testes ativos cobrindo BUG-001/002/003/004/007/014/015 + OP-001/002/008/009/010; 6 placeholders frontend para 6.5B/D) |

**Checkpoint:** 6 serializers com round-trip green • golden pipeline test verde com PDFs sintéticos • CI falha em migration drift/non-idempotent • BUG-015 coberto por test anti-regressão • alembic roda sempre na DB correta • 25 bugs anti-regressão em `tests/regressions/`.

## 6.5F — Test Infrastructure & Process (semana 4, ~1 semana)


> Sub-fase dedicada aos **fundamentos** de teste que estavam implícitos em 6.5A-E e iam virar dor na execução: isolation strategy, factories, MSW sync, flaky policy, parallelization, CI artifacts, backend-real spec, long-running pipeline strategy, contributor docs e geração de PDFs sintéticos. Sem essa base, os 240+ testes das outras sub-fases viram débito técnico em 3 meses. Ver [ADR-067](../../DECISIONS.md#adr-067--test-infrastructure-em-sub-fase-65f).

#### 6.5F.A — Backend test infrastructure

| #       | Tarefa                                                                                                                                                                  | Prio | Est. | Status |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5F.1  | **Test DB isolation strategy**: ADR + impl em `conftest.py` (decisão entre transactions+rollback vs truncate vs recreate); fixture `db_session` consistente para todos os tests | P0 | 3h | ✅ Bootstrap |
| 6.5F.2  | **Test data factories** em `backend/tests/factories/`: `make_user()`, `make_workspace()`, `make_member()`, `make_run()`, `make_category()`, `make_document()`, `make_report()`. Refatorar tests existentes para usar | P0 | 4h | ✅ Bootstrap (factories criadas; refactor de tests existentes em sub-fase própria) |
| 6.5F.3  | **Backend-real spec para E2E**: `docker-compose.test.yml` com PG + Redis isolados (porta diferente do dev); script `scripts/test_backend_up.sh` que sobe + aguarda health; reset entre test runs | P0 | 4h | ✅ Bootstrap |
| 6.5F.4  | **Long-running pipeline E2E strategy**: pipeline mock fixtures pré-computadas (PipelineRun + StageLog + Report já populados) para 6.5C.0/C.3 happy path; `--real-pipeline` flag para nightly opt-in | P0 | 4h | ✅ Bloco 5 ([`backend/tests/fixtures/pipeline_runs.py::seed_completed_run`](../../../backend/tests/fixtures/pipeline_runs.py): PipelineRun + 13 StageLogs + Report com HTML stub; `upload-pipeline-report.spec.ts` usa `PW_REAL_PIPELINE=1` para opt-in real) |

#### 6.5F.B — Frontend test infrastructure

| #       | Tarefa                                                                                                                                                                                              | Prio | Est. | Status |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5F.5  | **MSW sync strategy**: ADR sobre fonte de verdade (manual+lint vs `openapi-typescript` codegen); integrar com 6.5D.10 contract test; CI falha se MSW handlers divergem do OpenAPI | P0 | 2h | ✅ Bloco 6 ([ADR-069](../../DECISIONS.md#adr-069--msw-sync-strategy-manual--lint-ci-não-codegen) + [`scripts/msw-lint.mjs`](../../../frontend/scripts/msw-lint.mjs) — AST parse de `http.<method>` em `handlers.ts` vs `openapi.json` do backend) |
| 6.5F.6  | **Test parallelization + workspace isolation**: Playwright workers usam pool de workspaces pré-criadas OU `worker-${id}@test.com` no email; doc trade-offs em `TESTING.md` | P0 | 3h | ✅ Bloco 6 ([ADR-071](../../DECISIONS.md#adr-071--playwright-workspace-isolation-email-unique-por-worker) — email-per-worker escolhido; já implementado em Bootstrap via `userForWorker(info)`) |
| 6.5F.7  | **Frontend factories** em `frontend/tests/factories/`: `makeUser`, `makeMember`, `makeTransaction`, `makeRun`, `makeReport` retornam objetos type-safe alinhados com `lib/api.ts` | P0 | 3h | ✅ Bootstrap |

#### 6.5F.C — CI/Process

| #       | Tarefa                                                                                                                                                            | Prio | Est. | Status |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5F.8  | **Flaky test policy**: Playwright `retries: 2` em CI/0 em local; quarentena via `test.skip(true, "flaky: TODO BUG-XXX")`; CI gera report de testes flaky semanal  | P0 | 2h | ✅ Bloco 6 (seção em [`docs/reference/TESTING.md`](../../reference/TESTING.md#flaky-test-policy--f65f8) — `retries: 2` já configurado em `playwright.config.ts`; pattern de quarentena documentado) |
| 6.5F.9  | **CI test reporter + artifacts**: HTML report, vídeo + trace on failure, JUnit XML, retention 30 dias, link automático em PR comment via GH Actions               | P0 | 3h | ✅ Bloco 6 ([`ci.yml`](../../../.github/workflows/ci.yml) com `actions/upload-artifact@v4` retention=30d + `actions/github-script@v7` posting comentário automático em PR com link; tabela de artifacts em [`TESTING.md`](../../reference/TESTING.md#como-debugar-falha-em-ci)) |
| 6.5F.10 | **Snapshot review process**: seção em `TESTING.md` "Visual regression updates"; PR template com checkbox "snapshots intencionais? screenshot do diff?"; CODEOWNERS para `tests/__snapshots__/` | P1 | 2h | ✅ Bloco 6 ([`.github/CODEOWNERS`](../../../.github/CODEOWNERS) com `/frontend/tests/e2e/__snapshots__/` + seção em [`TESTING.md`](../../reference/TESTING.md#como-atualizar-snapshot-visual-regression--f65f10)) |
| 6.5F.11 | **Premium tier LLM E2E decisão**: ADR + impl (mock LiteLLM em CI default; `--real-llm` flag para nightly opt-in com Anthropic key em secret); custo monitorado | P0 | 3h | ✅ Bloco 6 ([ADR-070](../../DECISIONS.md#adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in) + [`backend/tests/fixtures/llm_mock.py`](../../../backend/tests/fixtures/llm_mock.py) com fixtures por stage + `MATHOMS_LLM_MOCK=1` env no CI + nightly opt-in documentado em TESTING.md) |

#### 6.5F.D — Documentação + tooling

| #       | Tarefa                                                                                                                                                                                          | Prio | Est. | Status |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5F.12 | **Synthetic PDF generator** em `tests/fixtures/pdf_generator.py` (`reportlab` ou `weasyprint`): 1 template por banco (14 códigos em `BankCode`), gera fatura + extrato; CI regenera fixtures determinísticas; substitui qualquer PDF real em `tests/` | P0 | 6h | ✅ Bootstrap (gerador implementado; regenerador determinístico em sub-task posterior) |
| 6.5F.13 | **`docs/reference/TESTING.md` contributor guide**: como rodar (backend + frontend), como adicionar test (factory pattern, fixture pattern), como debugar falha CI (artifacts, vídeo, trace), como atualizar snapshot, FAQ, tabela de comandos | P0 | 4h | 🚧 Esqueleto (preenchido ao longo de F6.5) |
| 6.5F.14 | **Pre-commit hooks** (`pre-commit` + `husky`): lint + format obrigatórios; opcional: rodar unit tests rápidos (<5s); opt-out via `--no-verify` documentado mas desencorajado | P1 | 2h | ✅ Entregue em commit `a7a055d` (`.pre-commit-config.yaml` + `dev/check_forbidden_paths.py` + `dev/validate_commit_msg.py` — paths proibidos, prefixos, trailing whitespace, merge conflict, private key detection) |

**Checkpoint:** DB isolation green • factories adotadas em 100% novos tests • backend-real CI roda em <3min • CI artifacts com vídeo+trace acessíveis em PR • `TESTING.md` cobre 100% dos cenários de novo contributor • PDFs sintéticos para 11 bancos versionados • premium LLM E2E definido (mock + nightly real) • snapshot review processado.

---
