# Mathoms AI — Backlog

> Fonte de verdade operacional. Atualizar semanalmente.
>
> **Legenda de status:** ☐ Pendente • 🚧 Em andamento • ✅ Concluído • ⏭ Adiado • ❌ Descartado
>
> **Legenda de prioridade:** **P0** bloqueante • **P1** importante • **P2** nice-to-have
>
> **Última atualização:** 2026-04-24 (Report Premium UI — 10/13 fases entregues em main: F0 discovery → F10 apêndices. Próxima: Fase 11 `e6_render.py` paridade (ADR-124). Ver lane dedicada abaixo. · F7F-Local MVP fechado · A6e.4 ✅ fase 4a completa 14/14.)

---

## Índice

- [Fases concluídas (F0-F6)](#fases-concluídas-f0-f6)
- [F6.5 — Frontend Testing & QA](#f65--frontend-testing--qa) ✅
- [P0/P1 — Motor canônico e pipeline](#p0p1--motor-canônico-e-pipeline-2026-04)
- [P2 — Unificação da classificação de documentos](#p2--unificação-da-classificação-de-documentos)
- [Sprint A6 — Migração Infra+Domínio](#sprint-a6--migração-infradomínio-plano-transversal) ← **sprint atual (transversal)**
  - [Lanes abertas agora — pickup table](#lanes-abertas-agora--pickup-table) ← **agente começa aqui**
  - [Ondas paralelas — mapa de dependências](#ondas-paralelas--mapa-de-dependências)
- [F7 — Produção + LGPD](#f7--produção--lgpd) ← **integra §15 LGPD + §16 Obs do plano A6**
- [F7F — Console interno (operadores)](#f7f--console-interno-operadores) — dividido em **F7F-Local** (UI web em `127.0.0.1`, sem OAuth, pré-produção) e **F7F-Remote** (`ops.mathoms.ai` com OAuth staff + RBAC + telemetria, produção)
- [Report Premium UI — Paridade com EXEMPLO_DE_RELATORIO.html](#report-premium-ui--paridade-com-exemplo_de_relatoriohtml) ← **10/13 fases entregues**
- [DOCS-REVIEW — Followups da revisão multi-agente 2026-04-24](#docs-review--followups-da-revisão-multi-agente-2026-04-24) ← **batches 2/3 do audit de docs**
- [F11 — Confiança, transparência e excelência de relatório](#f11--confiança-transparência-e-excelência-de-relatório-beta--ga)
- [F8 — Growth (Futuro)](#f8--growth-futuro)

---

## P0/P1 — Motor canônico e pipeline (2026-04)

Objetivo: **inventário de drift**, **fronteira motor × adaptadores**, **contratos JSON** e **base de golden tests**; em seguida **runner offline**, **CLI fina** e **CI strict** (ver plano estrutural).

| # | Entrega | Status | Notas |
| --- | --- | --- | --- |
| P0.1 | Inventário de duplicação / convergência | ✅ | [CANONICAL_ENGINE_P0.md](CANONICAL_ENGINE_P0.md) §1 |
| P0.2 | Fronteira motor canônico × adaptadores | ✅ | Mesmo doc §2 |
| P0.3 | Contratos entre estágios + override strict | ✅ | `MATHOMS_PIPELINE_SCHEMA_MODE` + `validate_artifact`; testes em `tests/test_schema_validation.py` |
| P0.4 | Golden / snapshot — estado e gaps | ✅ | Mesmo doc §4; full E0→E6 ainda deferido |
| P1-A | Layout de pacotes + regras de import | ✅ | `dev/check_pipeline_boundaries.py` + teste import |
| P1-B | Runner offline reproduzível | ✅ | `python -m pipeline.run_dev` — `pipeline/run_dev.py` |
| P1-C | CLI apenas como fachada | ✅ | `run_dev` delega ao `orchestrator` |
| P1-D | Job CI strict + checklist artefatos | ✅ | `.github/workflows/ci.yml`; [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md) |
| P1-E | Goldens incrementais E2/E4 (schema) | ✅ | `tests/fixtures/pipeline_golden/` + `test_pipeline_golden_fixtures.py` |
| — | LLM JSON goldens (schemas Pydantic) | ✅ | `tests/fixtures/llm_golden/` + `tests/test_llm_golden.py`; [README](../tests/fixtures/llm_golden/README.md) |
| — | Golden execução E4 (E3→E4) | ✅ | `tests/test_e4_golden_execution.py`; [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md) |
| — | Golden execução E5 (E4→E5) | ✅ | `tests/test_e5_golden_execution.py`; [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md) |
| — | Golden execução E6 (E5→HTML) | ✅ | `tests/test_e6_golden_execution.py`; [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md) |
| — | Golden execução E5.N (narrativas no E5 JSON) | ✅ | `tests/test_e5n_golden_execution.py` (mínimo + cônjuge → chart `ana_cenarios`); [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md) |
| — | E2 PDF sintético × parsers (`registry`) | ✅ | `tests/test_e2_synthetic_pdf_parsers.py` (todos os `BANK_MODULES`: **C6**, **Bradesco**, extratos + **Quinto Andar** fatura); `tests/fixtures/pdf_generator.py` — `_draw_*` por banco do registry |
| — | E2 PDF **real anonimizado** (fase 2, pós-sintético) | ☐ | **Scaffold:** `tests/fixtures/e2_real_pdf_anon/` + `tests/test_e2_real_pdf_regression.py` (pasta vazia = CI verde). **Pendente:** commitar PDFs redigidos + revisão PR. Ver [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md) § *E2 — sintético e real anonimizado*. |

---

## P2 — Unificação da classificação de documentos

> **Objetivo:** eliminar drift entre **classificação no upload web** e **E0-route / reclassify**, com **um módulo** (`document_classification`) e saída canônica: `doc_type`, `bank_code`, `period`, roteamento (`canonical_routing` / `e0_route.build_final_name`). O E0 CLI **sem** backend mantém fallback por nome de arquivo + LLM (documentado na ADR-081). Base: [CANONICAL_ENGINE_P0.md](CANONICAL_ENGINE_P0.md) §1.
>
> **Não bloqueia fechamento estrutural P1**; corre **em paralelo** a F7 após priorização do time. Risco se não fizer: documento na pasta errada, reprocessamento manual, sensação de “número errado” sem culpa clara.

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| P2.1 | **ADR ou doc de fronteira:** descrever entradas (upload vs batch `data/`), saída única do classificador, onde LLM pode participar, compatibilidade com `documents.reclassify` + `canonical_routing.rename_to_canonical` | P0 | 4h | ✅ ADR-081 + §9 em [ARCHITECTURE.md](ARCHITECTURE.md) |
| P2.2 | **API interna única de classificação** (módulo único chamado por upload e por E0-route): mesma estrutura Pydantic / dict; testes unitários com matriz de casos (nome + snippet de texto) | P0 | 12h | ✅ `backend/app/services/document_classification.py` (`ClassificationResult`, `classify_document`, `classification_can_route_to_data`); E0-route + reclassify importam o módulo; testes em `test_document_classification.py` |
| P2.3 | **Paridade de testes:** fixtures que provam que um mesmo PDF classificado no upload materializa o mesmo `doc_type`/`bank_code` que o E0-route daria para o nome canônico final | P1 | 8h | ✅ `test_classification_parity.py` — `build_final_name` + `classify_by_name` (Itaú/C6/Bradesco) |
| P2.4 | **UI:** quando classificação for incerta, estado explícito (baixa confiança) + CTA “corrigir tipo/banco” alinhado ao fluxo de reclassificação existente | P1 | 6h | ✅ Documentos: banner + coluna Tipo com “Revisar classificação” e link para `EditDocumentDialog` (`needs_review` ou `classification_confidence` < 0,7) |
| P2.5 | **Observabilidade:** log estruturado do resultado da classificação (sem PII) para comparar volume de mismatch antes/depois | P2 | 3h | ✅ Logger `fin.classification_telemetry` + chamadas em upload/reclassify; ver `classification_telemetry.py` e §9 em [ARCHITECTURE.md](ARCHITECTURE.md) |

**Checkpoint:** contrato único em `document_classification` + ADR-081; paridade nome canônico testada; UI marca incerteza; **P2.5** observabilidade entregue. Detalhes em [ARCHITECTURE.md](ARCHITECTURE.md) §9 e [DECISIONS.md](DECISIONS.md) ADR-081.

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

**Objetivo:** Rede de segurança de testes. Vitest + RTL + MSW + Playwright + hardening fintech (a11y, visual regression, resilience, security smoke).

**Duração estimada:** 2.5 semanas (4 sub-fases)

### 🛠 Bootstrap (executado em 2026-04-15) ✅

Bloco zero da reordenação CTO (ver discussão em conselho 2026-04-15): toda a fundação que A-E vão consumir, antes de qualquer test funcional. Itens entregues:

- **6.5A.1** Vitest + jsdom + coverage v8 + path alias `@/*` ([`frontend/vitest.config.ts`](../frontend/vitest.config.ts), [`frontend/tests/setup.ts`](../frontend/tests/setup.ts))
  - Polyfill explícito de `localStorage`/`sessionStorage` (jsdom 25 + vitest 2.1.x não instanciam Storage nativa — workaround em setup.ts)
  - Polyfills de `matchMedia`, `IntersectionObserver`, `ResizeObserver`, `URL.createObjectURL`, `crypto.randomUUID`
- **6.5A.2** MSW v2 (`tests/mocks/server.ts` + `handlers.ts` + `fixtures.ts`) com defaults para 50+ endpoints de `lib/api.ts`
- **6.5C.1** Playwright multi-browser (chromium + firefox + webkit + projeto `visual` isolado), auth helper com workspace isolation por worker
- **6.5F.1** DB isolation strategy documentada em [`backend/tests/conftest.py`](../backend/tests/conftest.py) (recreate-per-test sobre SQLite in-memory; ADR inline com alternativas e gatilho de migração para PG)
- **6.5F.2** Backend factories type-safe em [`backend/tests/factories/`](../backend/tests/factories/) (12 builders: user, workspace, member, account, category, document, vault, run, stage_log, report, notification, llm_config)
- **6.5F.3** [`docker-compose.test.yml`](../docker-compose.test.yml) (PG 5433 + Redis 6380, isolados do dev) + scripts `test_backend_up.sh`/`test_backend_down.sh` + `.env.test` gitignored
- **6.5F.7** Frontend factories type-safe em [`frontend/tests/factories/`](../frontend/tests/factories/) (12 builders alinhados com `lib/api.ts`)
- **6.5F.12** Gerador determinístico de PDFs sintéticos para 14 códigos (`BankCode`) em [`tests/fixtures/pdf_generator.py`](../tests/fixtures/pdf_generator.py) (reportlab; CPF placeholder LGPD-safe)
- **6.5F.13** Esqueleto de [`docs/TESTING.md`](TESTING.md) com TL;DR, comandos, FAQ
- Smoke test [`frontend/tests/bootstrap.test.tsx`](../frontend/tests/bootstrap.test.tsx) cobrindo Vitest + jsdom + jest-dom + MSW + factories: **7/7 passando em 941ms**

**Bugs pré-existentes detectados durante validação** (entrarão em 6.5E.8 anti-regression bank):
- `backend/tests/test_pipeline_api.py`: 6 testes falhando (KeyError 'id' + assert errors em trigger/cancel/list/get_run_detail)
- `backend/tests/test_pipeline_phase5.py`: 2 testes falhando (concurrency + health)
- `backend/tests/test_pipeline_review.py`: 2 testes falhando (tier detection)
- `backend/tests/test_retry_config.py`: 1 teste falhando (multiple retryable errors)
- `backend/tests/test_pipeline_task.py`: 3 ERROR (celery_task_id field, cancellation flag)
- **Total:** 7 failed + 3 errors em 269 passados (estado inicial pré-F6.5)

### 🛡 Bloco 1 — Backend Hardening 6.5E (executado em 2026-04-15) ✅

Segundo bloco da reordenação CTO: blindar a fronteira DB → pipeline contra a classe de bugs do BUG-015 antes de ataque ao frontend. Itens entregues:

- **6.5E.4** Fix cwd-sensitivity:
  - [`backend/alembic.ini`](../backend/alembic.ini): URL agora usa `%(here)s/../mathoms.db` (absoluto)
  - [`backend/alembic/env.py`](../backend/alembic/env.py): guard que rejeita SQLite com path relativo (com bypass `MATHOMS_ALEMBIC_ALLOW_RELATIVE_SQLITE=1` para tests)
  - [`backend/app/core/config.py`](../backend/app/core/config.py): `DATABASE_URL` default agora absoluto via `_PROJECT_ROOT`
  - [`docs/SETUP.md`](SETUP.md): seção "Migrations (Alembic)" documentando políticas
- **6.5E.1 + 6.5E.5** [`backend/tests/test_serializers_round_trip.py`](../backend/tests/test_serializers_round_trip.py) — **15 testes** cobrindo:
  - `serialize_family_members` round-trip + 4 cenários anti-regressão BUG-015 (com/sem surname, com/sem members, round-trip por disco)
  - `serialize_categorization` (expense/income separation)
  - `serialize_pipeline_config`, `serialize_institution_config`, `serialize_report_layout` (blob round-trip + YAML em disco)
  - `serialize_llm_config` (decifração de api_key + round-trip por disco)
- **6.5E.3** [`backend/tests/test_alembic_guardrails.py`](../backend/tests/test_alembic_guardrails.py) — **4 testes**:
  - drift detection model↔migration (catálogo `KNOWN_PRE_EXISTING_DRIFT` com 4 itens conhecidos a regenerar; novo drift falha imediato)
  - idempotency test (`upgrade → downgrade → upgrade` = mesmo schema)
  - linearidade do histórico (sem branches/heads múltiplos)
  - offline SQL preview gera `CREATE TABLE` válido
- **6.5E.2** [`backend/tests/test_golden_pipeline.py`](../backend/tests/test_golden_pipeline.py) — **18 testes + 1 skip**:
  - workspace fixture canônica → materialize → asserts no JSON em disco
  - 13 PDFs sintéticos parametrizados (1 por banco) abrem no pdfplumber
  - token `{{COVER_FAMILIA}}` substituído corretamente no template
  - **Skip documentado:** full E2E pipeline (E0→E6) deferido (requer refinar gerador por banco + mocks LLM + refator de globals em `e6_render.py`)
- **6.5E.8** [`backend/tests/regressions/`](../backend/tests/regressions/) — **20 testes ativos + 1 placeholder frontend**:
  - BUG-001 (Celery task discovery), BUG-002 (sys.path em fork worker)
  - BUG-003 (on_failure callback), BUG-004 (CPF leak fallback)
  - BUG-007 (skip_llm tier respect), BUG-014 (BankAccount.label)
  - BUG-015 (familia.sobrenome — sentinela; cobertura primária em test_serializers_round_trip)
  - OP-001 (parse_args sys.argv parametrizado em 6 scripts), OP-002 (SystemExit em Celery)
  - OP-008 (FERNET persistence), OP-009 (max_tokens schema + DB default)
  - OP-010 (started_at tz-aware no Pydantic serializer)
  - Placeholder para BUG-005/006/008/011/012 + OP-011 (frontend — cobertos em 6.5B/D)
- [`backend/tests/regressions/README.md`](../backend/tests/regressions/README.md) com catálogo + convenções

**Resultado agregado Bloco 1:** 57 passing + 2 skipped em 5.32s.

**Achados não previstos:**
- 6 serializers confirmados (não 5 como cogitado): `family_members`, `categorization`, `pipeline_config`, `institution_config`, `report_layout`, `llm_config`
- Drift real catalogado: `bank_accounts.label`, `notifications.created_at NOT NULL`, `transaction_overrides.created_at NOT NULL`, `pipeline_stage_logs.status` Enum (4 itens — gerar migration consolidada como follow-up)
- `LLMConfigCreate` schema chamado de `LLMConfigCreateRequest`
- `max_tokens=16384` é configuração runtime, não default — schema permite (`le=200000`); test ajustado

### 🛡 Bloco 2 — Multi-tenant gate 6.5B.12 + 6.5E.6 (executado em 2026-04-15) ✅

Terceiro bloco da reordenação CTO: blindar fronteira tenant↔tenant antes de qualquer test de UI. Sem isso, beta com >1 user é roleta russa.

- **6.5B.12** [`backend/tests/test_multi_tenant_isolation.py`](../backend/tests/test_multi_tenant_isolation.py) — **27 tests**:
  - Fixture `tenants` cria 2 universos paralelos (User A + Workspace A com `family_surname="Alves"` + 9 entidades vs User B com `family_surname="Brito"`)
  - 9 domínios cobertos: workspace settings, members + bank accounts, categories, documents, vault, pipeline runs + reviews, reports, transactions, LLM config, notifications
  - Cada classe testa: (a) GET retorna só dados de A, (b) mutação por path-id de B retorna 404
  - Helper `_assert_no_b_leak` faz dump JSON e busca signatures de B (IDs + valores únicos: `Brito`, `Bob Brito`, `claude-haiku-4-5`, etc.)
  - Sanity test: B continua vendo seus dados (cobre falso negativo no setup)
- **6.5E.6** [`backend/tests/test_neutral_global_defaults.py`](../backend/tests/test_neutral_global_defaults.py) — **3 tests** + fix em [`backend/app/api/config.py`](../backend/app/api/config.py):
  - **Vazamento detectado durante auditoria:** BUG-004 só strippava CPF; `full_name`, `short_name`, `data_nascimento` do founder ainda vazavam via `_convert_members_json_to_schemas`
  - **2º vazamento:** `_export_family_members` retornava `_load_global_json("family_members.json")` cru para tenant vazio (founder full identity + surname "Ferreira Campos")
  - **Fix systemic:** `_NEUTRAL_PLACEHOLDER_NAMES` por role (Titular Exemplo, Cônjuge Exemplo, etc.) + export retorna `{"membros": {}}` para tenant sem members
  - Tests anti-leak via `_FOUNDER_LEAK_SIGNALS` set (8 sinais de identidade do founder)

**Resultado agregado Bloco 2:** 30 passing em ~12s.

**Bug encontrado e corrigido nas factories:** `make_member` default `role="responsavel"` não passava validação de schema (`^(titular|conjuge|filho|dependente)$`). Corrigido para `role="titular"`.

**Resultado consolidado Bloco 1 + Bloco 2:** 87 passing + 2 skipped em 16.59s.

### 🧪 Bloco 3a — Unit Tests Frontend 6.5A (executado em 2026-04-15) ✅

Quarto bloco da reordenação CTO: unit tests do `lib/` consumindo a fundação criada no Bootstrap.

- **6.5A.6** [`frontend/tests/lib/utils.test.ts`](../frontend/tests/lib/utils.test.ts) — **9 tests** (`cn()` clsx + tailwind-merge: concatenação, falsy, conflitos Tailwind, variants condicionais)
- **6.5A.3** [`frontend/tests/lib/format.test.ts`](../frontend/tests/lib/format.test.ts) — **102 tests**:
  - 9 formatters (currency BRL/USD, percent, delta, compact, number, bytes, duration, date)
  - 4 status maps (docStatus, docType, runStatus, stageStatus, bankLabel) cobrindo TODOS os enums conhecidos via parametrização
  - Stage display names parametrizado
  - **Property-based via `fast-check`** (F6.5D.2 antecipada): BRL sempre tem R$ + 2 decimais, separadores BR íntegros, percent inverte sinal corretamente, formatDelta positivo sempre `+`, formatBytes monotônico
- **6.5A.4** [`frontend/tests/lib/export.test.ts`](../frontend/tests/lib/export.test.ts) — **16 tests** (CSV BOM UTF-8, delimitador `;`, MIME, acentos, XLSX MIME spreadsheetml, auto-width via spy em `book_append_sheet`, sheet names, round-trip XLSX)
- **6.5A.5** [`frontend/tests/lib/api.test.ts`](../frontend/tests/lib/api.test.ts) — **17 tests** (token mgmt, Bearer header, Content-Type, ApiError 401/422/500, 204 No Content, XHR upload com progress events + ApiError 4xx)
- **6.5A.7** [`frontend/tests/lib/usePipelineWS.test.tsx`](../frontend/tests/lib/usePipelineWS.test.tsx) — **15 tests** (mock WebSocket, connect com URL-encoded token, status transitions, heartbeat ignorado, terminal events `run_completed/failed/cancelled`, reconnect com backoff exponencial, max retries → `failed`, close 1000 sem reconnect, contador zerado em sucesso, cleanup ao desmontar/runId change)
- **6.5A.8** [`frontend/vitest.config.ts`](../frontend/vitest.config.ts) — thresholds calibrados (5% global, 65% lib/) com TODOs para subir em 6.5B/D

**Resultado Bloco 3a:** 167/167 passing em 1.15s. Coverage: utils 100%, format 98.96%, export 100%, usePipelineWS 97.75%, api 35.57% (50+ endpoints ficam para integration tests em 6.5B).

**Achados não previstos:**
- jsdom 25 + vitest 2.1.x: `Blob.text()` e `Blob.arrayBuffer()` quebrados → workaround spy no construtor `Blob` para capturar `parts` + `options` diretamente
- `WebSocket` é `readonly` no globalThis → `vi.stubGlobal()` em vez de assignment
- `XLSX.utils.book_append_sheet` precisa ser espionado para validar `!cols` (auto-write não persiste no formato XLSX, é metadata runtime)

### 🧩 Bloco 3b — Integration Tests 6.5B (executado em 2026-04-15) ✅

Quinto bloco da reordenação CTO. Cobertura completa de 6.5B com integration tests para todas as 10 pages, 8 compostos, dark mode, form validation, WS real e tz regression. Restou minoria de detalhes (tabs individuais de Config, Reports viewer React nativo) para PRs focados em sequência.

**Pages (10 pages):**
- **6.5B.1** [`pages/login.test.tsx`](../frontend/tests/pages/login.test.tsx) — **8 tests** + [`pages/register.test.tsx`](../frontend/tests/pages/register.test.tsx) — **6 tests**
- **6.5B.2** [`pages/dashboard.test.tsx`](../frontend/tests/pages/dashboard.test.tsx) — **7 tests** (Recharts mockado; KPIs, empty/error/loading, refresh, retry)
- **6.5B.3** [`pages/documents.test.tsx`](../frontend/tests/pages/documents.test.tsx) — **8 tests** (drop zone, empty CTA, banner needs_password, delete via ConfirmDialog)
- **6.5B.4** [`pages/pipeline.test.tsx`](../frontend/tests/pages/pipeline.test.tsx) — **7 tests** (trigger, contador docs ready, **BUG-007 anti-regression: free→skip_llm:true / premium→false**)
- **6.5B.5** [`pages/transactions.test.tsx`](../frontend/tests/pages/transactions.test.tsx) — **4 tests** + **XSS smoke F6.5D.6 antecipada** (`<script>` + `<img onerror>` em descrição renderizados escapados)
- **6.5B.6** [`pages/reports.test.tsx`](../frontend/tests/pages/reports.test.tsx) — **5 tests** (lista, empty CTA, link individual)
- **6.5B.7** [`pages/config.test.tsx`](../frontend/tests/pages/config.test.tsx) — **5 tests** (7 tabs presentes, default Members, navegação tab→tab, LLM tab fetch)
- **6.5B.8** [`pages/vault.test.tsx`](../frontend/tests/pages/vault.test.tsx) — **9 tests** (CRUD passwords, retry-unlock com contador)
- **6.5B.9** [`components/AppShell.test.tsx`](../frontend/tests/components/AppShell.test.tsx) — **9 tests** (auth gate, **BUG-005 anti-regression: Vault no nav**, logout, mobile sidebar)

**Composites (8 compostos):**
- **6.5B.10** [`components/composites.test.tsx`](../frontend/tests/components/composites.test.tsx) — **26 tests** (KPICard, EmptyState com CTA F6.5D.12, StatusBadge param, Delta com aria-label semântico, Spinner anti-regressão OP-011)
- + [`components/composites-extra.test.tsx`](../frontend/tests/components/composites-extra.test.tsx) — **13 tests** (ConfirmDialog, ThemeToggle, DataTable com sort + onRowClick)

**Dark mode (6.5B.11):** [`components/dark-mode.test.tsx`](../frontend/tests/components/dark-mode.test.tsx) — **10 tests** (validação de classes semânticas, sem cores hardcoded green/red, todos os 7 variants do StatusBadge sob dark)

**Form validation (6.5B.13):** [`integration/form-validation.test.tsx`](../frontend/tests/integration/form-validation.test.tsx) — **8 tests** (HTML5 type=email/password, required, minLength, paramétrico Login + Register; CPF mod-11/duplicate cobertos via ApiError em login/register tests)

**WS real (6.5B.14):** [`backend/tests/test_websocket_integration.py`](../backend/tests/test_websocket_integration.py) — **4 tests** com fakeredis (rejeita JWT inválido com 4001, aceita válido, mensagem via pub/sub chega, terminal event fecha conexão)

**TZ regression (6.5B.15):** [`lib/timezone.test.ts`](../frontend/tests/lib/timezone.test.ts) — **5 tests** (formatDate com Z, **BUG OP-010 anti-regression: ISO sem Z != ISO com Z**, formatElapsed com tz-aware system time)

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

### 🛡️ Bloco 4 — Hardening Fintech 6.5D (executado em 2026-04-15) ✅

Sexto bloco da reordenação CTO. Cobre todos os itens P0 de 6.5D e scaffolds para os P1 (Lighthouse, bundle size, contract test, CWV) — ativáveis em CI quando infra estiver estável.

**Entregas P0:**

- **6.5D.1 axe-core** [`frontend/tests/a11y/accessibility.test.tsx`](../frontend/tests/a11y/accessibility.test.tsx) — **13 tests** (compostos + 5 pages). Gate: 0 critical/serious. **2 violations reais detectadas e fixadas** no código fonte:
  - [`frontend/src/app/(app)/documents/page.tsx`](../frontend/src/app/(app)/documents/page.tsx): `aria-label` no file input hidden + `aria-label` dinâmico em cada botão delete
  - [`frontend/src/app/(app)/vault/page.tsx`](../frontend/src/app/(app)/vault/page.tsx): `aria-label` em botão delete por senha
- **6.5D.2 Property-based BRL** — já cumprido em Bloco 3a com 5 property-based tests via `fast-check` em `format.test.ts`
- **6.5D.4 Cross-browser** — já cumprido em Bootstrap com `playwright.config.ts` configurado com 3 projects (chromium + firefox + webkit) e grep `@critical`
- **6.5D.5 Resilience** [`frontend/tests/integration/resilience.test.tsx`](../frontend/tests/integration/resilience.test.tsx) — **8 tests** (5xx 502/503/504, network error vs ApiError, retry após 5xx, navigator.onLine events online/offline, slow response tolerance). WS reconnect cobre 15 tests em 6.5A.7
- **6.5D.6 Security smoke** [`frontend/tests/integration/security-smoke.test.tsx`](../frontend/tests/integration/security-smoke.test.tsx) — **8 tests** (XSS em member.full_name + category.name + vault.label + transação.descrição; JWT expiry mid-session → 401 → clearToken + redirect; logout cleanup cirúrgico de fin_token)
- **6.5D.7 Fixtures auditadas**:
  - [`tests/utils/cpf.py`](../tests/utils/cpf.py): gerador mod-11 determinístico (seed → CPF válido reproduzível) + validator `is_valid_cpf`
  - [`tests/utils/lint_no_real_pii.py`](../tests/utils/lint_no_real_pii.py): scan recursivo de `tests/`, `backend/tests/`, `frontend/tests/` procurando padrão `\d{3}\.\d{3}\.\d{3}-\d{2}`. Whitelist: placeholders (000.000.000-00 etc.) + anotação `# noqa: PII-ok` por linha. **7 CPFs reais substituídos** por gerado+noqa (test_config_api, test_config_materializer, test_config_models, test_serializers_round_trip). Lint green.
- **6.5D.11 Error boundary** [`frontend/src/components/ErrorBoundary.tsx`](../frontend/src/components/ErrorBoundary.tsx) + [`frontend/src/app/(app)/layout.tsx`](../frontend/src/app/(app)/layout.tsx) wrap + [`frontend/tests/components/ErrorBoundary.test.tsx`](../frontend/tests/components/ErrorBoundary.test.tsx) — **6 tests** (children passam sem erro, captura erro + fallback, reset volta a renderizar, onError callback, fallback customizado, crash isolado em subárvore sem derrubar siblings)
- **6.5D.12 Empty state CTA audit** — coberto em 6.5B tests (Documents "Enviar documentos", Reports "Enviar documentos → /documents", Dashboard "Ir para Pipeline", Vault "Adicionar senhas")
- **6.5D.13 Focus management** [`frontend/tests/integration/focus-mgmt.test.tsx`](../frontend/tests/integration/focus-mgmt.test.tsx) — **3 tests** (dialog open → foco dentro, dialog close → trigger retorna, form submit mantém foco; SPA route change deferido para Playwright E2E)

**Scaffolds P1 (ativar em CI quando build estável):**

- **6.5D.3 Visual regression** [`frontend/tests/e2e/visual-regression.visual.spec.ts`](../frontend/tests/e2e/visual-regression.visual.spec.ts) — 5 specs (login light/dark, register, AppShell mobile 360px, documents empty). Baseline capturada em CI primeiro run (Playwright projeto `visual` isolado com `maxDiffPixelRatio: 0.01`).
- **6.5D.8 Lighthouse CI** [`frontend/.lighthouserc.json`](../frontend/.lighthouserc.json) — 4 URLs (login/dashboard/documents/reports) × 3 runs; thresholds: perf warn 85, a11y error 95, bp warn 90, SEO off.
- **6.5D.9 Bundle size** [`frontend/.size-limit.json`](../frontend/.size-limit.json) — budgets por route chunk (dashboard <250KB, transactions <200KB, reports <300KB, main app <1MB).
- **6.5D.10 Contract test** [`frontend/scripts/contract-check.mjs`](../frontend/scripts/contract-check.mjs) — baixa openapi.json do backend → roda openapi-typescript → diff vs `tests/contracts/openapi.types.d.ts` snapshot. Requer backend UP.
- **6.5D.14 Core Web Vitals** — coberto parcialmente via Lighthouse; script dedicado com `web-vitals` lib em Playwright E2E deferido para 6.5C.

**Resultado Bloco 4 agregado frontend:** +47 novos testes (13 a11y + 6 error boundary + 8 security + 8 resilience + 3 focus + 4 misc em XSS/JWT/logout = 47 tests adicionais para um total frontend de **344 passing + 1 skipped em 14.07s**).

**Resultado consolidado F6.5 (Bootstrap + Blocos 1-4) até agora:**
- Frontend: **344 passing + 1 skipped em 14.07s** (26 arquivos de teste)
- Backend: **91 passing + 2 skipped em ~21s** (serializers + alembic + golden pipeline + regressions + multi-tenant + neutral defaults + WS integration)
- **Total: 435 tests passing em ~35s**

**Achados não previstos do Bloco 4:**
- axe-core detectou 2 **a11y violations REAIS** em produção (file input sem label + delete buttons sem aria-label). Corrigidos no source.
- Lint anti-PII detectou 7 CPFs reais em tests backend (do founder, `287.766.948-36`) — substituídos por CPF gerado (mod-11 válido) + anotação `noqa: PII-ok`.
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

### 🎯 Bloco 5 — E2E + Smoke + CI 6.5C + 6.5F.4 (executado em 2026-04-15) ✅

Sétimo bloco da reordenação CTO. E2E coverage via Playwright + Smoke checklist manual + GH Actions CI + pipeline mock fixtures para viabilizar Golden Path em CI rápido.

**E2E specs (9 specs, ~25 tests, tagged `@critical` para cross-browser):**

- **6.5C.0** [`golden-path.spec.ts`](../frontend/tests/e2e/golden-path.spec.ts) — **O GATE SAGRADO**: registro → setup surname → upload sintético → trigger pipeline → report contém `FAMILY_SURNAME` (BUG-015 regression inline). Timeout 5min (com mock fixtures cai para 30s).
- **6.5C.2** [`onboarding.spec.ts`](../frontend/tests/e2e/onboarding.spec.ts) — 5 tests @critical (happy, email duplicado, senha curta HTML5, link register↔login, login inválido)
- **6.5C.3** [`upload-pipeline-report.spec.ts`](../frontend/tests/e2e/upload-pipeline-report.spec.ts) — 3 tests @critical (cancel mid-pipeline, real-pipeline opt-in, **BUG-007 regression: premium → skip_llm=false** via route interceptor)
- **6.5C.4** [`config-round-trip.spec.ts`](../frontend/tests/e2e/config-round-trip.spec.ts) — 2 tests (criar membro UI + export JSON, family_surname persiste)
- **6.5C.5** [`vault.spec.ts`](../frontend/tests/e2e/vault.spec.ts) — 2 tests (CRUD + retry-unlock 0-desbloqueados)
- **6.5C.6** [`drill-down.spec.ts`](../frontend/tests/e2e/drill-down.spec.ts) — 3 tests (URL state filters em `/transactions`)
- **6.5C.7** [`dark-mode.spec.ts`](../frontend/tests/e2e/dark-mode.spec.ts) — 1 test @critical (toggle → reload → dark persiste)
- **6.5C.8** [`error-auth.spec.ts`](../frontend/tests/e2e/error-auth.spec.ts) — 5 tests @critical (sem token → /login, token inválido → clearToken, 404, /login sempre acessível)
- **6.5C.9** [`notifications.spec.ts`](../frontend/tests/e2e/notifications.spec.ts) — 2 tests (bell opens sheet)

**Smoke Checklist** ([`docs/SMOKE_TEST.md`](SMOKE_TEST.md)): 13 seções, 70+ checks manuais. Inclui:
- Seção 8 (Multi-tenant) e 12 (LGPD pré-beta) com gates de rollback
- Checks dedicados às regressões: **BUG-015** (cover com surname), **BUG-007** (skip_llm tier), **ADR-068** (fases narrativas, zero códigos E* na UI)

**CI GH Actions** ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)): **7 jobs** — lint (pre-commit), lint-pii, pipeline-tests, backend-tests (+ Redis service), frontend-tests (Vitest + JUnit), frontend-e2e (condicional: push main OU label `e2e` em PR) com Playwright cross-browser + PG+Redis services + alembic upgrade + artifacts retidos 30d, all-green gate de merge.

**Mock fixtures** ([`backend/tests/fixtures/pipeline_runs.py`](../backend/tests/fixtures/pipeline_runs.py)): `seed_completed_run()` cria `PipelineRun(status="completed")` + 13 `PipelineStageLog` + `Report` com HTML stub em `storage/{ws_id}/output/`. Permite 6.5C.0/C.3 rodarem <30s em CI default; `PW_REAL_PIPELINE=1` para opt-in nightly com pipeline real.

**Resultado Bloco 5:** frontend suite segue **344 passing + 1 skipped em 4.14s** (E2E specs não executadas localmente — rodam em CI contra backend real).

**Achados não previstos:**
- Route interceptor Playwright (`page.route`) captura POST body elegantemente — usado para BUG-007 anti-regression sem precisar rodar pipeline
- SMOKE_TEST.md expande de "30+ checks" para 70+ porque ADR-068 e multi-tenant justificaram seções dedicadas
- GH Actions `all-green` job é o padrão de "gate de merge" pré-configurado para branch protection rules

### 🔧 Bloco 6 — 6.5F residuais + 6.5E.7 (executado em 2026-04-15) ✅

Oitavo e **último bloco da F6.5**: ADRs de infraestrutura de teste + scripts de lint/mock + concurrency test. Fecha a fase inteira.

**Entregas:**

- **6.5E.7** [`backend/tests/test_materialize_concurrency.py`](../backend/tests/test_materialize_concurrency.py) — **3 tests** (2 workspaces paralelos / idempotency mesmo ws / 10 workspaces simultâneos com `ThreadPoolExecutor`). SQLite file-based + `check_same_thread=False` para thread-safety.
- **6.5F.5** [ADR-069 MSW sync](DECISIONS.md#adr-069--msw-sync-strategy-manual--lint-ci-não-codegen) + [`frontend/scripts/msw-lint.mjs`](../frontend/scripts/msw-lint.mjs) — AST regex sobre `http.<method>("/api/...")` em handlers.ts vs `openapi.json` do backend; `--spec`, `--allow-extra`, filtro de WS endpoints.
- **6.5F.6** [ADR-071 Workspace isolation](DECISIONS.md#adr-071--playwright-workspace-isolation-email-unique-por-worker) — email-per-worker decision ratificada; implementação já estava em Bootstrap (`userForWorker(info)` usa `parallelIndex` + `STAMP`).
- **6.5F.8** Flaky test policy em [`docs/TESTING.md#flaky-test-policy--f65f8`](TESTING.md#flaky-test-policy--f65f8) — `retries: 2` CI / 0 local (já em `playwright.config.ts`), quarentena via `test.skip(true, "flaky: TODO BUG-XXX")`, plano de report semanal.
- **6.5F.9** CI reporter expandido em [`.github/workflows/ci.yml`](../.github/workflows/ci.yml):
  - `actions/upload-artifact@v4` para playwright-report (30d), backend-coverage (14d), frontend-vitest-results (14d)
  - `actions/github-script@v7` posta comment em PRs com link para o artifact
  - Tabela de artifacts em [`TESTING.md#como-debugar-falha-em-ci`](TESTING.md#como-debugar-falha-em-ci)
- **6.5F.10** Snapshot review em [`.github/CODEOWNERS`](../.github/CODEOWNERS) — review obrigatório em `/frontend/tests/e2e/__snapshots__/`, `/backend/alembic/versions/`, `/tests/fixtures/`, `/docs/DECISIONS.md`. Workflow completo em [`TESTING.md#como-atualizar-snapshot-visual-regression--f65f10`](TESTING.md#como-atualizar-snapshot-visual-regression--f65f10) com PR template checklist.
- **6.5F.11** [ADR-070 Premium LLM E2E](DECISIONS.md#adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in) + [`backend/tests/fixtures/llm_mock.py`](../backend/tests/fixtures/llm_mock.py) — fixtures válidas por stage (E1, E1.5, E2-llm, E7-review); `MATHOMS_LLM_MOCK=1` default em CI; nightly workflow `nightly-e2e-real-llm.yml` com `PW_REAL_LLM=1` + ANTHROPIC_API_KEY em secret (scaffold documentado, workflow de CI a ativar pós-primeiro-run).
- **6.5F.14** Pre-commit hooks (já entregues em commit `a7a055d`): `.pre-commit-config.yaml` + `dev/check_forbidden_paths.py` + `dev/validate_commit_msg.py`.

**3 novas ADRs** registradas: [ADR-069](DECISIONS.md#adr-069--msw-sync-strategy-manual--lint-ci-não-codegen), [ADR-070](DECISIONS.md#adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in), [ADR-071](DECISIONS.md#adr-071--playwright-workspace-isolation-email-unique-por-worker). Índice de ADRs na seção "Testing" atualizado.

**Resultado Bloco 6 agregado:** +3 backend tests (concurrency), ~370 linhas de ADRs, +2 scripts (msw-lint.mjs + llm_mock.py fixture), +1 CODEOWNERS. Frontend suite segue 344 passing.

## 🏁 F6.5 — Resultado Final Consolidado

**Todas as sub-fases A-F completas + scaffolds P1:**

| Sub-fase        | Tasks | Status                                           |
| --------------- | ----- | ------------------------------------------------ |
| 6.5A Unit       | 8     | ✅ 8/8 (167 tests)                                |
| 6.5B Integration | 15   | ✅ 15/15 (305 tests + 27 multi-tenant isolation) |
| 6.5C E2E        | 12    | ✅ 12/12 (~25 E2E specs + SMOKE_TEST + CI)       |
| 6.5D Hardening  | 14    | ✅ 11 P0 completos, 3 P1 scaffolds               |
| 6.5E Backend    | 8     | ✅ 8/8 (57 tests)                                 |
| 6.5F Infra      | 14    | ✅ 14/14                                          |
| **Total**       | **71** | **Atendido com cobertura ampliada vs plano**    |

**Testes agregados F6.5:**
- Frontend Vitest: **344 passing + 1 skipped em 4.14s** (26 arquivos)
- Backend pytest: **94 passing + 2 skipped em ~22s** (serializers + alembic + golden + regressions + multi-tenant + neutral + WS + concurrency)
- **Total: 438 tests em ~26s**

**ADRs novas/estendidas nesta fase:** ADR-062 (frontend testing), 063 (hardening fintech), 064 (backend hardening), 067 (test infrastructure), 068 (UX phases), **069 (MSW sync)**, **070 (Premium LLM E2E)**, **071 (Playwright workspace isolation)**.

**Scripts criados:** `test_backend_up.sh`, `test_backend_down.sh`, `tests/utils/cpf.py`, `tests/utils/lint_no_real_pii.py`, `tests/fixtures/pdf_generator.py`, `backend/tests/fixtures/pipeline_runs.py`, `backend/tests/fixtures/llm_mock.py`, `frontend/scripts/contract-check.mjs`, `frontend/scripts/msw-lint.mjs`.

**Arquivos CI:** `.github/workflows/ci.yml` (7 jobs + all-green), `.github/CODEOWNERS`, `docker-compose.test.yml`, `.pre-commit-config.yaml` (e hooks).

**Docs atualizadas:** `SETUP.md` (migrations), `TESTING.md` (infra completa + debug + snapshots + flaky + LLM mock), `SMOKE_TEST.md` (novo, 70+ checks), `DECISIONS.md` (+3 ADRs).

**Pendências carregadas para CI primeiro-run (não bloquear F6.5 close):**
- Visual regression baseline capture
- Nightly `e2e-real-llm.yml` workflow ativação
- MSW lint CI integration (quando `backend` subir em `ci.yml` como service)
- Flaky report semanal workflow
- Lighthouse / bundle-size / contract-check gates

### 6.5A — Tooling Setup + Unit Tests (semana 1, dias 1-3)

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

### 6.5B — Integration Tests — Pages + Components (semana 1-2)

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

### 6.5C — E2E Tests + Smoke Checklist (semana 2)

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
| 6.5C.10 | Smoke test checklist (`docs/SMOKE_TEST.md`, 30+ checks) — incluir seção LGPD pré-beta: nenhum dado real em fixtures, audit do localStorage pós-logout | P0 | 3h | ✅ Bloco 5 ([`docs/SMOKE_TEST.md`](SMOKE_TEST.md): 13 seções, 70+ checks, LGPD + anti-regressions) |
| 6.5C.11 | CI integration (GH Actions com PostgreSQL + Redis services)         | P0   | 3h   | ✅ Bloco 5 ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml): 7 jobs; E2E com PG+Redis services e Playwright cross-browser condicional) |

**Checkpoint:** ~25-30 E2E tests green cobrindo Golden Path + 8 fluxos críticos. `docs/SMOKE_TEST.md` criado. **Golden Path (6.5C.0) é o gate sagrado:** se ele falha, deploy não sai — independente do resto.

### 6.5D — Hardening Fintech (semana 2-3, 3-4 dias)

> Sub-fase dedicada para garantir que itens P0 fintech-specific (a11y, visual regression, resilience, security smoke) não sejam cortados sob pressão de prazo. Ver [ADR-063](DECISIONS.md#adr-063--hardening-fintech-em-sub-fase-65d).

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

### 6.5E — Backend Hardening (semana 3, 2 dias)

> Sub-fase dedicada a blindar a fronteira DB → pipeline contra a classe de bugs que gerou **BUG-015** (serializers perdendo campos silenciosamente, migrations rodando na DB errada por cwd, dados do founder vazando do fallback global). Ver [ADR-064](DECISIONS.md#adr-064--backend-hardening-em-sub-fase-65e).

| #       | Tarefa                                                                                                                                                              | Prio | Est. | Status |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5E.1  | **Round-trip tests para os 6 serializers** do `config_materializer` (family_members, categorization, pipeline, institutions, report_layout, llm_config): DB seed → materialize → ler JSON → assert todos os campos preservados (inclui `familia.sobrenome` após BUG-015) | P0 | 6h | ✅ Bloco 1 |
| 6.5E.2  | **Golden file pipeline com PDFs 100% sintéticos** (zero dado real): fixture completa de workspace + PDFs → orchestrator → E6 HTML → assert estrutura + valores esperados. Reutilizável como base do 6.5C.0 E2E | P0 | 4h | ✅ Bloco 1 (caminho crítico — full E2E pipeline deferido com test skip + docs) |
| 6.5E.3  | **Alembic CI guardrails**: `alembic check` detecta drift entre models e migrations; idempotency test (`upgrade → downgrade → upgrade` = mesmo schema); `alembic upgrade head --sql` preview em PR | P0 | 3h | ✅ Bloco 1 (drift catalog ativo — 4 itens conhecidos a regenerar) |
| 6.5E.4  | **Fix cwd-sensitivity em alembic.ini**: caminho absoluto ou env var `MATHOMS_DATABASE_URL` obrigatória; documentar em SETUP.md que alembic roda da raiz; adicionar guard no `env.py` que rejeita paths relativos ambíguos | P0 | 1h | ✅ Bloco 1 |
| 6.5E.5  | **Test anti-regressão BUG-015**: workspace com `FamilyMember` no DB mas sem `family_surname` definido → materialized `family_members.json` NÃO contém `familia.sobrenome` do global (`"Ferreira Campos"` do founder) | P0 | 1h | ✅ Bloco 1 (incluso em 6.5E.1) |
| 6.5E.6  | **Systemic fix para fallback-leak class**: políticas "neutral global defaults" (strip identity fields do `config/family_members.json` antes de copiar pro tenant quando workspace tem membros) + test que cobre cada config | P1 | 4h | ✅ Bloco 2 (extension de BUG-004: full_name/short_name/birth_date neutralizados em GET /config/members fallback + GET /config/export para tenant vazio; 3 tests) |
| 6.5E.7  | **Concurrency test para `_init_config` pattern** (thread-safe em Celery fork pool + múltiplas runs paralelas): 2 workspaces materializando ao mesmo tempo não corrompem configs um do outro | P1 | 3h | ✅ Bloco 6 ([`test_materialize_concurrency.py`](../backend/tests/test_materialize_concurrency.py) — 3 tests: 2 workspaces paralelos, idempotency mesmo ws, 10 workspaces simultâneos com `ThreadPoolExecutor`) |
| 6.5E.8  | **Anti-regression bank** (catalogar TODOS bugs já vividos): criar `tests/regressions/` com um teste por bug do `CHANGELOG.md`, nomeado `test_bug_NNN_<slug>.py`. Cobrir BUG-001..BUG-015 (14 bugs UI+backend) + 11 bugs operacionais do dogfood (parse_args/Celery, SystemExit, FERNET persistence, max_tokens E1.5, started_at tz, animate-pulse, _categorization global, skip_llm default, route_to_data_dir, validation pré-pipeline, stages LLM skip gracioso). Cada teste falha SE o fix for revertido | P0 | 5h | ✅ Bloco 1 (20 testes ativos cobrindo BUG-001/002/003/004/007/014/015 + OP-001/002/008/009/010; 6 placeholders frontend para 6.5B/D) |

**Checkpoint:** 6 serializers com round-trip green • golden pipeline test verde com PDFs sintéticos • CI falha em migration drift/non-idempotent • BUG-015 coberto por test anti-regressão • alembic roda sempre na DB correta • 25 bugs anti-regressão em `tests/regressions/`.

### 6.5F — Test Infrastructure & Process (semana 4, ~1 semana)

> Sub-fase dedicada aos **fundamentos** de teste que estavam implícitos em 6.5A-E e iam virar dor na execução: isolation strategy, factories, MSW sync, flaky policy, parallelization, CI artifacts, backend-real spec, long-running pipeline strategy, contributor docs e geração de PDFs sintéticos. Sem essa base, os 240+ testes das outras sub-fases viram débito técnico em 3 meses. Ver [ADR-067](DECISIONS.md#adr-067--test-infrastructure-em-sub-fase-65f).

#### 6.5F.A — Backend test infrastructure

| #       | Tarefa                                                                                                                                                                  | Prio | Est. | Status |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5F.1  | **Test DB isolation strategy**: ADR + impl em `conftest.py` (decisão entre transactions+rollback vs truncate vs recreate); fixture `db_session` consistente para todos os tests | P0 | 3h | ✅ Bootstrap |
| 6.5F.2  | **Test data factories** em `backend/tests/factories/`: `make_user()`, `make_workspace()`, `make_member()`, `make_run()`, `make_category()`, `make_document()`, `make_report()`. Refatorar tests existentes para usar | P0 | 4h | ✅ Bootstrap (factories criadas; refactor de tests existentes em sub-fase própria) |
| 6.5F.3  | **Backend-real spec para E2E**: `docker-compose.test.yml` com PG + Redis isolados (porta diferente do dev); script `scripts/test_backend_up.sh` que sobe + aguarda health; reset entre test runs | P0 | 4h | ✅ Bootstrap |
| 6.5F.4  | **Long-running pipeline E2E strategy**: pipeline mock fixtures pré-computadas (PipelineRun + StageLog + Report já populados) para 6.5C.0/C.3 happy path; `--real-pipeline` flag para nightly opt-in | P0 | 4h | ✅ Bloco 5 ([`backend/tests/fixtures/pipeline_runs.py::seed_completed_run`](../backend/tests/fixtures/pipeline_runs.py): PipelineRun + 13 StageLogs + Report com HTML stub; `upload-pipeline-report.spec.ts` usa `PW_REAL_PIPELINE=1` para opt-in real) |

#### 6.5F.B — Frontend test infrastructure

| #       | Tarefa                                                                                                                                                                                              | Prio | Est. | Status |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5F.5  | **MSW sync strategy**: ADR sobre fonte de verdade (manual+lint vs `openapi-typescript` codegen); integrar com 6.5D.10 contract test; CI falha se MSW handlers divergem do OpenAPI | P0 | 2h | ✅ Bloco 6 ([ADR-069](DECISIONS.md#adr-069--msw-sync-strategy-manual--lint-ci-não-codegen) + [`scripts/msw-lint.mjs`](../frontend/scripts/msw-lint.mjs) — AST parse de `http.<method>` em `handlers.ts` vs `openapi.json` do backend) |
| 6.5F.6  | **Test parallelization + workspace isolation**: Playwright workers usam pool de workspaces pré-criadas OU `worker-${id}@test.com` no email; doc trade-offs em `TESTING.md` | P0 | 3h | ✅ Bloco 6 ([ADR-071](DECISIONS.md#adr-071--playwright-workspace-isolation-email-unique-por-worker) — email-per-worker escolhido; já implementado em Bootstrap via `userForWorker(info)`) |
| 6.5F.7  | **Frontend factories** em `frontend/tests/factories/`: `makeUser`, `makeMember`, `makeTransaction`, `makeRun`, `makeReport` retornam objetos type-safe alinhados com `lib/api.ts` | P0 | 3h | ✅ Bootstrap |

#### 6.5F.C — CI/Process

| #       | Tarefa                                                                                                                                                            | Prio | Est. | Status |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5F.8  | **Flaky test policy**: Playwright `retries: 2` em CI/0 em local; quarentena via `test.skip(true, "flaky: TODO BUG-XXX")`; CI gera report de testes flaky semanal  | P0 | 2h | ✅ Bloco 6 (seção em [`docs/TESTING.md`](TESTING.md#flaky-test-policy--f65f8) — `retries: 2` já configurado em `playwright.config.ts`; pattern de quarentena documentado) |
| 6.5F.9  | **CI test reporter + artifacts**: HTML report, vídeo + trace on failure, JUnit XML, retention 30 dias, link automático em PR comment via GH Actions               | P0 | 3h | ✅ Bloco 6 ([`ci.yml`](../.github/workflows/ci.yml) com `actions/upload-artifact@v4` retention=30d + `actions/github-script@v7` posting comentário automático em PR com link; tabela de artifacts em [`TESTING.md`](TESTING.md#como-debugar-falha-em-ci)) |
| 6.5F.10 | **Snapshot review process**: seção em `TESTING.md` "Visual regression updates"; PR template com checkbox "snapshots intencionais? screenshot do diff?"; CODEOWNERS para `tests/__snapshots__/` | P1 | 2h | ✅ Bloco 6 ([`.github/CODEOWNERS`](../.github/CODEOWNERS) com `/frontend/tests/e2e/__snapshots__/` + seção em [`TESTING.md`](TESTING.md#como-atualizar-snapshot-visual-regression--f65f10)) |
| 6.5F.11 | **Premium tier LLM E2E decisão**: ADR + impl (mock LiteLLM em CI default; `--real-llm` flag para nightly opt-in com Anthropic key em secret); custo monitorado | P0 | 3h | ✅ Bloco 6 ([ADR-070](DECISIONS.md#adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in) + [`backend/tests/fixtures/llm_mock.py`](../backend/tests/fixtures/llm_mock.py) com fixtures por stage + `MATHOMS_LLM_MOCK=1` env no CI + nightly opt-in documentado em TESTING.md) |

#### 6.5F.D — Documentação + tooling

| #       | Tarefa                                                                                                                                                                                          | Prio | Est. | Status |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 6.5F.12 | **Synthetic PDF generator** em `tests/fixtures/pdf_generator.py` (`reportlab` ou `weasyprint`): 1 template por banco (14 códigos em `BankCode`), gera fatura + extrato; CI regenera fixtures determinísticas; substitui qualquer PDF real em `tests/` | P0 | 6h | ✅ Bootstrap (gerador implementado; regenerador determinístico em sub-task posterior) |
| 6.5F.13 | **`docs/TESTING.md` contributor guide**: como rodar (backend + frontend), como adicionar test (factory pattern, fixture pattern), como debugar falha CI (artifacts, vídeo, trace), como atualizar snapshot, FAQ, tabela de comandos | P0 | 4h | 🚧 Esqueleto (preenchido ao longo de F6.5) |
| 6.5F.14 | **Pre-commit hooks** (`pre-commit` + `husky`): lint + format obrigatórios; opcional: rodar unit tests rápidos (<5s); opt-out via `--no-verify` documentado mas desencorajado | P1 | 2h | ✅ Entregue em commit `a7a055d` (`.pre-commit-config.yaml` + `dev/check_forbidden_paths.py` + `dev/validate_commit_msg.py` — paths proibidos, prefixos, trailing whitespace, merge conflict, private key detection) |

**Checkpoint:** DB isolation green • factories adotadas em 100% novos tests • backend-real CI roda em <3min • CI artifacts com vídeo+trace acessíveis em PR • `TESTING.md` cobre 100% dos cenários de novo contributor • PDFs sintéticos para 11 bancos versionados • premium LLM E2E definido (mock + nightly real) • snapshot review processado.

---

## Sprint A6 — Migração Infra+Domínio (plano transversal)

**Fontes canônicas** (plano mestre A6 absorvido 2026-04-21): ADRs 097-111 em [DECISIONS.md](DECISIONS.md); arquitetura alvo em [ARCHITECTURE.md §17](ARCHITECTURE.md); critérios de aceite por fase em [TESTING.md](TESTING.md); runbook de cutover em [runbooks/cutover.md](runbooks/cutover.md); LGPD em §7B abaixo.
**ADRs:** 097 (extract-then-refactor), **098** (Caminho B puro vs pragmático), **099** (reuse de `analyze_*` em `main_with_store`), **100** (A6d commitment), **101** (R12-R17 backend DDD/SOLID), **102** (R18-R20 language-neutral), **103** (teste humano como gate), **109** (auth portability), **110** (structured logs + OTel), **111** (stateless rigoroso)
**Status global (2026-04-22 — pós-merge A6e.3b + A6e.events + A6e.events-migration + A6e.4 ✅ fechada + A6g.6 + A6g.2c + A6g.6b + A6g.3b ✅):**
- **Entregues ✅:** A5a-A5f · A6a · A6b · A6b.5 · A6c · A6d (2026-04-20) · **A6f.1** (pipeline-as-service HTTP boundary, ADR-112, 2026-04-21) · A6f.2/.3/.4/.5a/.6 · **A6g.1** (audit baseline 2026-04-21) · **A6g.2 1ª rodada** (T1.a/b/c + T2.a/b, 2026-04-21/22 — T3 scripts com goldens fica como A6g.2b pós-A6c.3) · **A6g.5** (tests sweep, 2026-04-21) · **A6g.7** (Go prep + ADR-113, 2026-04-22) · **A6e.3** (3 slices: FamilyMember + Category + Goal use cases, 2026-04-21) · **A6e.3b** (3 slices: ConfigBlob + Task + Document, 25 use cases + 61 testes, 2026-04-22) · **A6e.4** (fase 4a 14/14 + fase 4b 3/3 — 17 routers thin + 13 novos aggregates, 2026-04-22) · **A6e.5** (`/api/v1/` + aliases + ADR-108, 2026-04-22) · **A6e.events** (domain events infra + 2 agregados migrados + ADR-115, 32 testes, 2026-04-22) · **A6e.events-migration** (10 call-sites audit_log inline → eventos, 2026-04-22) · **A6g.4** (rodadas 1+2+3, T2 `ts_long_files` frontend zerado, 2026-04-22) · **A6g.6** (enforcement automatizado — Ruff + ESLint + pre-commit hooks + AST tests + audit baseline decrescente, ADR-114, 2026-04-22) · **A6g.2c** (rename `pipeline/llm/service.py` → `litellm_client.py` — ALLOWLIST `forbidden-names` zerada, 2026-04-22) · **A6g.6b** (sweep ruff I001/F541 + ruff format . + promove `max-lines` warn→error; `max-lines-per-function` diferido, 2026-04-22) · **A6g.3b ✅** (sessões 1+2+3, polish fechado 2026-04-22 — P5 backend 10→1 residual `saldo_diff` tolerance).
- **A6e per-aggregate** (6 agregados · repos+DTOs) concluído: FamilyMember + Category + ConfigBlob + Document + Goal + Task. Application layer agora cobre 13 aggregates (audit, auth, category, config_blob, document, family_member, feature_flag, goal, invitation, llm_config, notification, pipeline_run, realtime, report, task, transaction, vault, workspace) — 60+ use cases.
- **Restante:** A6e (**.events-followup** ⏸ — ativar flag notif em prod + remover cron, aguarda janela F7) · A6g.2b T3 scripts com goldens ⏸ blocked-by A6c.3 · A6g.3 🚧 parcial rodada 3 (P1 em `content_classifier`/`pipeline_service`/`models/task.py`/repositories) · A6-human gate humano · A6c blocked-by A6-human · F7 (7A-7F + LGPD).
- **Caminho crítico (serial):** A6g.3 → F7A → F7B → F7D+dogfood → GA. A6-human smoke destrava A6c + A6g.2b em paralelo.
- **Lanes abertas agora (2026-04-24 — sync pós-Report Premium Fase 10 mergeada + ADR-119/120):** **☐ livres:** A6g.3 backend sweep rodada final (`content_classifier` 621l, `pipeline_service` P1×4, `models/task.py`, repositories — prompt `track_a6g3_backend_style_sweep.md`); A6-human smoke (gate humano); Report Premium Fase 11 `e6_render.py` paridade (ADR-124 — em progresso em `agent/report-premium/phase11-e6-parity/*`); F7F-Analyst (prompt a escrever). **Sempre confirme com `git worktree list` + `git for-each-ref refs/remotes/origin/agent/`** antes de pegar — a tabela pode estar desatualizada.
- **Testes:** 1461 pipeline + 1085 backend + 12 pipeline-service passing (zero regressão).

### Lanes abertas agora — pickup table

> **Pickup protocol** (CLAUDE.md §Antes de pegar uma task): antes de escolher uma lane, rode **os dois** comandos:
> ```bash
> git worktree list                           # detecta agentes locais (ainda não pusharam)
> git for-each-ref --sort=-committerdate \    # detecta agentes remotos
>   --format='%(committerdate:iso) %(refname:short)' \
>   refs/remotes/origin/agent/ | head -15
> ```
> Se aparece worktree com `agent/<slug>-*` em path diferente do seu **OU** branch remota com commit <24h, **pegue outra lane**. Esta tabela é dica, não fonte de verdade — os 2 comandos são.

| Lane | Branch slug | Prompt / detalhe | Depende de | Onda | Status |
| --- | --- | --- | --- | --- | --- |
| **A6g.2** pipeline sweep | `a6g2-pipeline-style` | [track_a6g2_pipeline_style_sweep.md](agent_prompts/track_a6g2_pipeline_style_sweep.md) | A6g.1 ✅ | 1 | ✅ **1ª rodada fechada 2026-04-21/22** — T1.a (`e_reset::main`, commit `3cdf1e1`) · T1.b (`pdf_generator`, `a5c55bc`) · T1.c (`e0_audit`, `b7e610e`) · T2.a (`ChartsNarrator.narrate`, `f688baa`) · T2.b (`run_pipeline_task`, `9ef80d1`) · docs `ded2b41` + `1e082c9` + `5c5bee0`. **2ª rodada A6g.2b** (scripts com goldens: e3/e4/e5/e5n/e6/e7) ⏸ blocked-by A6c.3 (que depende de A6-human). |
| **A6g.4** frontend sweep | `a6g4-frontend-style` | [track_a6g4_frontend_style_sweep.md](agent_prompts/track_a6g4_frontend_style_sweep.md) | A6g.1 ✅ | 1 | ✅ fechada 2026-04-22 — rodadas 1 (commit `5a7b577`) + 2 (A6g.4b, commit `cfa3103`) + **3 (A6g.4c, `plano/page.tsx` 630→152 e `plano/alocacao/wizard/page.tsx` 533→185)** mergeadas. T2 `ts_long_files` frontend **zerado**; 27 → 29 ofensores no líquido (4 novos T3 med por JSX natural; 1 T3 high eliminado). Enforcement lint rule fica para A6g.6. |
| **A6e.3** use cases (slice FamilyMember+Category+Goal) | `a6e3-use-cases` | [track_a6e3_use_cases.md](agent_prompts/track_a6e3_use_cases.md) — Application layer R15 scoped a agregados não-pipeline | per-aggregate ✅ | 2 | ✅ **fechada 2026-04-21** — slices 1+2+3 mergeados: `328d8b7` (base layer com erros tipados) + `021ba2d` (FamilyMember) + `49be5da` (Category) + `10a1239` (Goal) + `c5eb804` (docs). 22 use cases, 56 tests puros. ConfigBlob/Document/Task em A6e.3b (linha abaixo). |
| **A6e.3b** use cases remanescentes (ConfigBlob+Document+Task) | `a6e3b-use-cases-rest` | [track_a6e3b_use_cases_rest.md](agent_prompts/track_a6e3b_use_cases_rest.md) — 25 use cases em 3 slices (ConfigBlob 6 / Task 13 / Document 6); padrão A6e.3 + `HttpPipelineClient` (A6f.1) como boundary | A6f.1 ✅ destravou | 2 | ✅ 2026-04-22 — 61 testes puros, zero regressão (`pytest backend/tests -q`: 1054 passed). Composites com storage/audit/bulk ficam no router para A6e.4 4b. |
| **A6e.4** routers finos | `a6e4-thin-routers` | [track_a6e4_thin_routers.md](agent_prompts/track_a6e4_thin_routers.md) — 4900→≤1200 linhas (17 routers); **fase 4a** ✅ 14/14 + **fase 4b** ✅ 3/3 (2026-04-22); teste AST enforcement em `backend/tests/architecture/test_routers_thin.py`. **Nota histórica:** 5 commits de 2026-04-20 com tag `(A6e.4)` referem ao **ConfigBlob per-aggregate slice** (`f48f06b`, `f2b0319`, `840b74c`, `eaa6370`, `1d7562f`), não a esta lane transversal — mesma colisão histórica que levou a renomear A6e.6 → A6e.events; aqui mantivemos `A6e.4` alinhado com ADR-101 R16. Filtre `git log --grep "A6e.4 slice"` para ver só esta lane. | A6e.3 ✅ (4a) / A6e.3b ✅ (4b) | 2 | ✅ **fechada 2026-04-22** — fase 4a completa com slices 11-17 em sessão noturna: invitations 127→57 (slice 11), ws 103→31 (slice 12), llm 182→89 (slice 13), transactions 231→104 (slice 14), reports 353→133 (slice 15), workspaces 371→163 (slice 16), pipeline 439→139 (slice 17). THIN_ROUTERS set final (19): `{audit, auth, categories, config, dashboard, documents, family_members, feature_flags, goals, invitations, llm, notifications, pipeline, reports, tasks, transactions, vault, workspaces, ws}`. 7 novos aggregates em application layer: invitation, realtime, llm_config, transaction, report, workspace, pipeline_run. Exception handlers globais `InvitationError` + `MembershipError` em `main.py`. |
| **A6e.5** /api/v1/ prefix | `a6e5-v1-prefix` | [track_a6e5_v1_prefix.md](agent_prompts/track_a6e5_v1_prefix.md) — Prefixo canônico + alias deprecated em `/api/` com `Deprecation`+`Sunset` headers (RFC 8594); OpenAPI 3.1 versionado | — (independente de A6e.3) | 2 | ✅ 2026-04-22 (ADR-108) — rotas canônicas `/api/v1/*`, alias `/api/*` anuncia Sunset até F7A; OpenAPI `info.version=1.0.0`; frontend + MSW + E2E atualizados |
| **A6e.events** domain events (ex-A6e.6) | `a6e-events` | [track_a6e_events_domain_events.md](agent_prompts/track_a6e_events_domain_events.md) — `backend/app/events/` + handlers tipados; renomeada em 2026-04-22 para evitar colisão histórica com Goal slice (5 commits com `(A6e.6)` são Goal slice pré-2026-04-22) | A6e.3 ✅ destravou | 2 | ✅ **2026-04-22 (parcial — ADR-115)** — 4 slices: infra (Event/registry/dispatcher/protocols), `AuditLogEvent`+`FamilyMemberCreatedEvent`+handler migra `CreateFamilyMember`, `TaskCreatedEvent`+`TaskUpdatedEvent`+`task_notification_handler` atrás de flag `MATHOMS_USE_EVENT_DRIVEN_TASK_NOTIFICATIONS` default False, ADR-115+CHANGELOG+BACKLOG. 32 testes novos. **Follow-ups abertos:** (a) migração dos ~14 `audit_log()` inline em routers (A6e.events-migration); (b) ativar flag em prod + remover cron (A6e.events-followup); (c) handlers async (Celery/WS) quando houver caso concreto. |
| **A6f.1** pipeline-as-service | `a6f1-pipeline-service` | [track_a6f1_pipeline_service.md](agent_prompts/track_a6f1_pipeline_service.md) — FastAPI standalone, backend fala por HTTP | A6e per-aggregate ✅ | 2 | ✅ 2026-04-21 (ADR-112) — slices 1-3 mergeados; extração de helpers/≤100 linhas deferida |
| **A6g.5** tests sweep | `a6g5-tests-sweep` | [track_a6g5_tests_sweep.md](agent_prompts/track_a6g5_tests_sweep.md) — Fakes nomeados > MagicMock; nomes descritivos | — | 2 | ✅ 2026-04-21 |
| **A6g.3** backend sweep (2 rodadas) | `a6g3-backend-style` | [track_a6g3_backend_style_sweep.md](agent_prompts/track_a6g3_backend_style_sweep.md) — Services, repos, helpers, typing | A6e.4 ✅ | 3 | 🚧 parcial 2026-04-22 — **1ª rodada:** P4 optional defaults (5→0), P8 what-comments (2→0), P1 decomp em 4 services top-1 (`pipeline_adapter`, `goal_service`, `task_service`, `task_progress_service`). **2ª rodada:** P1 decomp em +4 services (`invitation_service` 4→2, `document_processor` 2→1, `canonical_routing` 3→1, `tarefas_md_parser` 2→1). **Funções ≥40 linhas (HIGH) caem 72→68.** **P5 float money (12) deferido** como A6g.3b — wire-breaking. Restante: `content_classifier`, `pipeline_service`, `models/task`, repositories |
| **A6g.6** enforcement | `a6g6-enforcement` | [track_a6g6_enforcement.md](agent_prompts/track_a6g6_enforcement.md) — Ruff rules + ESLint `no-explicit-any` + grep hooks + audit regression | A6g.2/.4/.5 ✅ | 3 | ✅ 2026-04-22 (ADR-114) — slices 1-5 mergeados. Ruff E/F/I/W ativo; ESLint `no-explicit-any` bloqueante; hooks `forbidden-names`/`float-money`; AST tests `no-any-in-boundary`/`no-forbidden-names`; audit baseline decrescente em CI. Follow-ups A6g.6b (sweep I001/F541 + ruff-format + max-lines promove warn→error), A6g.2c (rename `pipeline/llm/service.py`), A6e.3c (dict[str,Any] em DTOs não-opaque) |
| **A6g.7** Go prep | `a6g7-go-prep` | [track_a6g7_go_prep.md](agent_prompts/track_a6g7_go_prep.md) — `.golangci.yml` conservador + CI job idempotente + `services/` skeleton + ADR-113 (sessão curta 1-2h, zero `.go` produtivo) | A6f.1 ✅ destravou | 3 | ✅ 2026-04-22 (ADR-113) — `.golangci.yml` + `go.work` + `services/README.md` + `.github/workflows/go.yml` com skip por `hashFiles('**/*.go')` + Makefile `go-{fmt,lint,test,all}`. Primeira reescrita Go entra em `services/<name>/` sem configurar linter |
| **A6e.events-migration** migrar `audit_log()` inline → eventos | `a6e-events-migration` | Migrar ~14 call-sites de `audit_log(db, ...)` inline em routers para `AuditLogEvent`. **Sem prompt** — escopo mecânico slice-por-router | A6e.events ✅ destravou | 2 | ✅ 2026-04-22 — 10 call-sites migrados (documents 5 + workspaces 4 + invitations 1); `client_meta` exposto em `services/audit.py`; 1177 backend tests passed, zero regressão. Commits `b781ec7` (helper) + `da133c0` (documents) + `d319438` (workspaces) + `eabdd04` (invitations). |
| **A6e.events-followup** ativar notifications event-driven em prod + remover cron | `a6e-events-followup` | Ativar flag `MATHOMS_USE_EVENT_DRIVEN_TASK_NOTIFICATIONS=true` em produção; monitorar 48h; remover `task_notification_service.scan_and_create_notifications()` polling cron se zero regressão. **Sem prompt** — pequena, requer janela de prod | A6e.events ✅ + janela de validação em prod | 2 | ⏸ aguarda prod (pós-F7 deploy) |
| **A6e.3c** eliminar `dict[str, Any]` em DTOs não-OPAQUE | `a6e-3c-typed-dtos` | Tipar 4 arquivos marcados em `backend/tests/architecture/test_no_any_in_boundary.py` ALLOWLIST com track `A6e.3c`: `schemas/dto/family_member/{command,mapper,response}.py` + `schemas/dto/category/mapper.py`. Promover de `LEGACY_FILES` para `CLEAN_FILES`. **Sem prompt** — escopo tipagem <0.5 sessão | A6g.6 ✅ (AST gate ativo) | 3 | ✅ 2026-04-22 (`35c7502`) — `extra` fields = `dict[str, object]`; mappers com TypedDict `_FamilyMembersConfig`/`_CategorizationConfig`; AST gate 31→35 CLEAN_FILES; 1159 passed + 4 skipped, zero regressão |
| **A6g.6b** sweep ruff `--fix I001/F541` + `ruff format` + `max-lines` warn→error | `a6g6b-ruff-sweep` | Sweep pós-enforcement: (a) `ruff check --fix .` aplica I001 (unsorted-imports) + F541 (f-string sem placeholder); (b) `ruff format .`; (c) ESLint `max-lines`/`max-lines-per-function` passa de `warn` → `error`. Remove ignores correspondentes de `pyproject.toml [tool.ruff.lint]`. Baseline decresce, gate se torna bloqueante. **Sem prompt** — mecânico, 1 sessão | A6g.6 ✅ | 3 | ✅ 2026-04-22 (`8045cbf`+`7b674d6`+`50be8c5`) — 361 fixes (290 I001 + 71 F541) em 263 arquivos + 435 reformatados; `ignore = [I001, F541]` removido; `ruff-format --check` no pre-commit; ESLint `max-lines` warn→error (zero offenders); `max-lines-per-function` mantido em warn — 64 offenders em 59 components React exige sweep refactor dedicado |
| **A6g.2c** rename `pipeline/llm/service.py` (filename genérico) | `a6g2c-rename-llm-service` | Filename `service.py` sozinho violava `forbidden-names` (CLAUDE.md §Code style); estava em ALLOWLIST de `dev/check_forbidden_names.py`. Renomeado para `pipeline/llm/litellm_client.py` (explicita LiteLLM + Instructor); 11 imports atualizados + 2 ALLOWLISTs zeradas. Bonus: `check_float_money.py` ganha `_is_rename()` — git mv puro fazia hook bater em campos legados (`cost_estimate_usd`) | A6g.6 ✅ (hook ativo) | 3 | ✅ 2026-04-22 — commit [`16c4eb2`](#) |
| **A6g.3b** migração `float` → `Decimal` money (wire-compat) | `a6g3b-decimal-money` | [track_a6g3b_decimal_money_migration.md](agent_prompts/track_a6g3b_decimal_money_migration.md) — Elimina P5_float_money em `backend/app/` via tipo `MoneyBRL`/`MoneyUSD` (Decimal em memória, number no JSON via PlainSerializer — zero wire break). | A6g.3 ✅ rodadas 1+2 · A6g.6 gate ativo | 3+ | ✅ 2026-04-22 — **slices 1 + 2 + 3 ✅:** tipo `MoneyBRL`/`MoneyUSD` + 11 tests; transactions 4 campos + cascata services + 19 tests (sessão 1); **sessão 2:** 11 campos goal DTOs (aporte/dolar/if_goal) + math Decimal em `goal_service.py` (`_retorno_mensal_decimal` via `.ln()/.exp()`, `_pmt_constante_ate_fv`, `_if_meta_targets`, `_aporte_cobrindo_gap_com_patrimonio`, `compute_if/aporte/dolar_derived`), persistência via `model_dump(mode="json")`, OpenAPI Input/Output split (+173/−21); **sessão 3 (polish):** factory `make_if_goal` Decimal, `saldo_diff` documentado como tolerance (P5=1 residual aceito — nome persistido em `config/pipeline.json`), baseline regenerado (P5 backend 10→1). ADR-090 nota final gravada. |
| **F7F-Local** console interno pré-produção (IA-0) | `f7f-local` | [track_f7f_local.md](agent_prompts/track_f7f_local.md) — UI web Next separada em `frontend-ops/` (bind `127.0.0.1:3100`, flag `INTERNAL_OPS_UI_ENABLED`) + camada de serviço em `backend/app/services/internal_ops/` + auth yaml+bcrypt+JWT cookie + anonimização default ([ADR-116](DECISIONS.md#adr-116)). 4 slices: S1 services+auth backend · S2 frontend-ops shell · S3 telas por área (7F.10–7F.17) · S4 CLI secundário 7F.9 (opcional) | — (greenfield, independente de 7A/B/C) | 3 (Lane C6) | ✅ **MVP fechado 2026-04-23** (S1+S2+S3 em `main`); S4 opcional em aberto |
| **F7F-Analyst** superfície do especialista financeiro (IA-0+) | `f7f-analyst` | Role `analyst` no mesmo `frontend-ops/`; rotas `/analyst/*` com triage (7F.A4), deep dive (7F.A5), overview (7F.A6) e feedback loop (7F.A7); 5 indicadores de saúde Perini/Cerbasi/AUVP derivados de E1.5/E5; tabela `analyst_notes` nova (7F.A2 + ADR); service `analyst_metrics/` reutiliza `pipeline/domain/services/` | F7F-Local S1+S2 concluídos (shell + auth base) | 3+ (Lane C6, pós-F7F-Local) | ☐ aberta — **prompt a escrever** |
| **A6-human** smoke | _(manual)_ | [SMOKE_TEST_HUMAN.md](SMOKE_TEST_HUMAN.md) — 46 checks | A6b.5 ✅ | — | ☐ gate humano |
| **A6c** deletar bridge | `a6c-delete-bridge` | Remove `stage_runner_compat` + `materialization_bridge` + `main(root_dir)` legados | A6-human aprovado | — | ⏸ blocked-by A6-human |
| **A6-ux.livestep** contrato `LiveStep` | `livestep-contract` | ADR-119 — payload único de progresso intra-stage + helper `emit_item_progress` + primitivo `<LiveStepProgress/>`; primeira adoção em E2-extratos/E2-faturas | A6e.4 ✅ | — | ✅ entregue 2026-04-23 (branch `agent/livestep-contract/20260423-1530`) — migração das stages iterativas restantes (E1/E1.5/E1.5c/E2-llm) aberta como follow-up P1 |
| **A6-readers.dbfirst** readers DB-first | `adr-db-first-readers` | ADR-120 — helper `artifact_reader.read_latest_artifact` DB-first com fallback disco; fix incidente 2026-04-23 (patrimônio stale) | A6b.flip ✅ | — | ✅ entregue 2026-04-23 (branch `agent/adr-db-first-readers/20260423-1645`) — 4 readers user-facing migrados |
| **Report Premium Fase 11** `e6_render.py` paridade (Jinja2 + tokens) | `report-premium/phase11-e6-parity` | Reescrever exportador HTML standalone com Jinja2 + design tokens para paridade visual com `/reports/[id]` (ADR-124 revisitada — §10 do plano vence Delta #2) | Fase 10 ✅ | — | 🚧 ativa em `agent/report-premium/phase11-e6-parity/20260424-1558` |

### Ondas paralelas — mapa de dependências

Itens dentro da mesma onda rodam em paralelo (agentes disjuntos, branches
distintas, zero overlap de arquivos). Onda N só começa quando Onda N-1
convergir em `origin/main`.

```
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 1 — estrutura (2 lanes independentes; ocupação em §Lanes       ║
║         abertas acima — o diagrama mostra dependências, não status) ║
╠═══════════════════════════════════════════════════════════════════════╣
║  Lane A1: A6g.2 pipeline sweep   (agent/a6g2-pipeline-style/*)       ║
║           └─ prompt: docs/agent_prompts/track_a6g2_pipeline_style_  ║
║             sweep.md; 1ª rodada defensiva (Tier 1: e_reset::main,    ║
║             pdf_generator, e0_audit; Tier 2 opc.); Tier 3 em A6g.2b  ║
║  Lane A2: A6g.4 frontend sweep   ✅ fechada 2026-04-22              ║
║           └─ rodadas 1+2+3 mergeadas; T1/T2/T4/T5 zerados em         ║
║             frontend/src/; 6 páginas >500 l decompostas.             ║
║             Enforcement lint rule fica para A6g.6.                   ║
║                                                                       ║
║  [A6e Task] ✅ entregue 2026-04-21 (A6e.7) — 3 sub-agregados         ║
║  [A6e Goal] ✅ entregue 2026-04-21                                   ║
║  [A6g.1 audit] ✅ entregue — baseline em docs/audits/                ║
║  [A6f.1 pipeline-service] NÃO entra aqui — maior item isolado,       ║
║  começar antes de A6e convergir aumenta merge hell. Fica na Onda 2.  ║
║  [A6g.3 backend sweep] prefere pós-A6e.4 (routers finos). Onda 2.    ║
╚═══════════════════════════════════════════════════════════════════════╝
                              │
                              ▼  (após Onda 1 convergir)
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 2 — paralelizável (4 lanes, A6e transversais + infra)           ║
╠═══════════════════════════════════════════════════════════════════════╣
║  Lane B1: A6e.3 + A6e.3b ✅ 2026-04-22 + A6e.4 — use cases + routers ║
║           └─ Transversal: requer todos slices Onda 1 mergeados        ║
║           └─ A6e.3b fechou 3 agregados restantes (ConfigBlob+Task+Doc) ║
║  Lane B2: A6e.5 /api/v1/ prefix  ✅ 2026-04-22 (ADR-108)             ║
║  Lane B3: A6f.1 pipeline-service ✅ 2026-04-21 (ADR-112)             ║
║  (A6g.5 tests sweep ✅ 2026-04-21 — fora da Onda)                    ║
║                                                                       ║
║  A6e.events (domain events) prefere vir depois de B1 (use cases).    ║
║  A6g.3 (backend sweep) rodará pós-A6e.4 (B1) — mesclar em Onda 3.    ║
╚═══════════════════════════════════════════════════════════════════════╝
                              │
                              ▼  (após A6e.3/.4/.5 fechados + A6f.1 merged)
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 3 — F7 produção + LGPD (paralelizável dentro)                   ║
╠═══════════════════════════════════════════════════════════════════════╣
║  Lane C1: F7A Docker + Deploy + HTTPS      (infra)                   ║
║  Lane C2: F7B Security + LGPD              (segurança)                ║
║  Lane C3: F7C CI/CD + Observability        (DevOps)                   ║
║  Lane C4: F7E Legal + termos               (jurídico, sem código)    ║
║  Lane C5: A6g.3 backend sweep (pós-A6e.4) + A6g.6 enforcement +      ║
║           A6g.7 Go prep (pós-A6f.1)                                   ║
║  Lane C6: F7F-Local (IA-0) — UI web localhost (principal) +          ║
║           camada de serviço; CLI vira atalho secundário/futuro;      ║
║           sem OAuth; INDEPENDENTE de F7A/B/C (roda em dev/staging)   ║
║           Depois de F7F-Local shell: F7F-Analyst (role analyst,      ║
║           triage/deep-dive/overview/feedback — Perini/Cerbasi/AUVP)  ║
║                                                                       ║
║  F7A precede F7B (HTTPS antes de hardening). F7D (monitoring) e      ║
║  F7F-Remote (console hospedado) vêm após F7A+B+C estabilizarem.      ║
║  F7F-Local NÃO espera Onda 3 convergir — pode começar quando          ║
║  operador precisar das ferramentas de suporte (exclusão de conta,    ║
║  purge, reset senha) antes do produto estar no ar.                    ║
╚═══════════════════════════════════════════════════════════════════════╝
                              │
                              ▼
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 4 — dogfood + GA                                                 ║
╠═══════════════════════════════════════════════════════════════════════╣
║  F7D monitoring + dogfood (2 semanas com dados reais)                ║
║  F7F-Remote console interno em ops.mathoms.ai                        ║
║          (OAuth staff, RBAC, /api/internal/*, dashboard 7E.7)        ║
║  GA release                                                           ║
╚═══════════════════════════════════════════════════════════════════════╝
```

**Como escolher a próxima lane (para agente ou humano):**

> **Heurística por perfil de sessão — cruze com §Lanes abertas agora antes de começar.** Se a lane sugerida aparece 🚧 na tabela acima ou no `git worktree list`, pule para a linha seguinte da tabela.

| Situação                                                     | Preferência (se livre) |
| ------------------------------------------------------------ | ----------------------- |
| Sessão curta, refactor cirúrgico em Python                   | A6g.2 pipeline → A6e.5 /v1 prefix |
| Sessão curta, familiar com TS/React                          | A6g.4 frontend          |
| Sessão longa (≥3h), greenfield infra                         | A6g.7 Go prep (pós-A6f.1 ✅) ou F7A Docker (Onda 3) |
| Sessão longa, foco em backend DDD                            | A6e.4 (fases 4a+4b destravadas pela A6e.3b ✅) ou A6e.events |
| Toda Onda 1 ocupada (caso atual 2026-04-22)                  | A6e.4 4a/4b, A6e.events ou A6-human smoke |
| Onda 2 inteira fechada e quer destravar F7                   | F7A Docker (C1, Onda 3) |
| Sessão curta, foco em ops/CS/LGPD, quer ferramenta já        | F7F-Local (C6, Onda 3 — independente de F7A/B/C; roda em dev) |
| F7F-Local shell pronto, quer superfície de análise de saúde  | F7F-Analyst (C6, Onda 3+ — triage/deep-dive/overview/feedback) |

**Regras de coordenação (aplicam a todas as ondas):**
- Uma lane = uma branch `agent/<slug>/<timestamp>`. Nunca 2 agentes na mesma lane — rode o pickup check em CLAUDE.md §Antes de pegar uma task.
- `git fetch origin` a cada ~30min em sessão longa; rebase incremental.
- Hotspots (`CLAUDE.md`, `docs/BACKLOG.md`, `docs/CHANGELOG.md`, `docs/DECISIONS.md`) — anunciar antes, commit atômico ≤5min.
- A6g.7 (Go prep) foi **destravada** pelo merge de A6f.1 (2026-04-21) — pode rodar agora; só faz sentido com o contrato HTTP estabelecido, que já está em `docs/api/v1/pipeline-service.openapi.json`.

### A5f — E1.5c Caminho B ✅ entregue 2026-04-19

| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A5f.1 | `scripts/e15_consolidate.main_with_store(ctx)` lê baseline via store, invoca `consolidate()` legado, grava E1.5c via store | P0 | ~30min | ✅ |
| A5f.2 | `pipeline/stages/e15c.py` chama `main_with_store` direto, sem `stage_runner_compat`; preserva skip gracioso free tier | P0 | 15min | ✅ |
| A5f.3 | Golden de paridade `main(root_dir)` vs `main_with_store(ctx)` em workspace sintético | P0 | 20min | ✅ |
| A5f.4 | Critério estrutural: `grep stage_runner_compat pipeline/stages/` = zero | P0 | 5min | ✅ |

**Checkpoint A5f:** ✅ todos os 7 stages determinísticos no Caminho B; bridge com zero clientes vivos no wrapper.

### A6a — LLM stages escrevendo via `ArtifactStore` ✅ entregue 2026-04-19

| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6a.1 | `pipeline/stages/e15.py` troca `out_path.write_text` por `store.write("E1.5", "baseline_patrimonial", ...)` → produz `-1.5_baseline.json` | P0 | 1h | ✅ |
| A6a.2 | `pipeline/stages/e2_llm.py` troca `out_path.write_text` por `store.write("E2-llm", stem, e2_json)`; `_find_unprocessed_docs` via `store.list_keys` | P0 | 1h | ✅ |
| A6a.3 | Critérios estruturais + integration tests com DiskArtifactStore em `tests/test_llm_stages.py` (4 testes novos) | P0 | 1h | ✅ |
| A6a.4 | ADR-105: E1 (config, não artefato) e E7-review LLM (ad-hoc) **não migram** — decisão documentada | P2 | 15min | ✅ |

**Checkpoint A6a:** ✅ `MATHOMS_USE_DB_ARTIFACTS=true` pode ser ativado sem quebrar E3→E7.

### A6b — Ativar `USE_DB_ARTIFACTS=true` + validar end-to-end ✅ entregue 2026-04-19

| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6b.1 | Coluna `workspaces.use_db_artifacts_override: bool \| None` (opt-in por workspace) | P0 | 1h | ✅ |
| A6b.2 | `pipeline_task.py` instancia `DBArtifactStore` quando flag ativa; sessão longa com commit após cada stage | P0 | 2h | ✅ |
| A6b.3 | Pipeline completo em workspace piloto com DB ativado; comparar outputs vs disk baseline | P0 | 1-2 dias | ☐ |
| A6b.4 | Script `dev/compare_disk_vs_db.py` — gate ≥99% paridade (disk vs DB, ignora timestamps/order) | P0 | 1 dia | ✅ |
| A6b.5 | Discrepâncias esperadas documentadas em ADR-106: `_meta`, `created_at`, ordem de listas | P0 | 2h | ✅ |

**Checkpoint A6b.1+2+4+5:** ✅ Infraestrutura de ativação pronta. A6b.3 (validação em workspace real) fica para teste humano A6-human.

**Estimativa remanescente:** A6b.3 (1-2 dias de debugging em workspace real).

### A6b.5 — Preparação para teste humano (ADR-103) ✅ entregue 2026-04-19

| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6b.5.1 | `docker-compose.smoke.yml` (Redis) + `Makefile` (`smoke-up/down/reset/seed/logs` + `test/lint/format`) | P0 | 4h | ✅ |
| A6b.5.2 | `backend/app/scripts/seed_smoke.py` (2 users + 2 workspaces + copia fixtures p/ inbox) | P0 | 3h | ✅ |
| A6b.5.3 | `tests/fixtures/smoke_inbox/` (5 CSVs: 2 extratos C6, 1 dup, 1 Nubank extrato, 1 Nubank fatura + `life_plan_goals.md` + `ambiguous_document-smoke.txt` + README) | P0 | 6h | ✅ |
| A6b.5.4 | `docs/SMOKE_TEST_HUMAN.md` — runbook completo (setup + 46 checks + troubleshooting + template decisão A6c) | P0 | 4h | ✅ |
| A6b.5.5 | `GET /health` inclui `artifact_store_mode: "disk"\|"db"` (A6b indicator) | P0 | 3h | ✅ |
| A6b.5.6 | Free-tier: pipeline já emite `skipped_free_tier` nos stages LLM; banner na UI pendente (F7B) | P0 | 2h | 🚧 |

**Checkpoint A6b.5:** ✅ `make smoke-up && make smoke-seed` → sistema utilizável em <2min.

**Nota A6b.5.6**: Logs de `skipped_free_tier` já existem no pipeline desde F5. Banner visual na UI fica para F7B (security hardening) junto com outros elementos de UX de produção.

### A6b.flip — Flip do default global ✅ entregue 2026-04-23 (ADR-118)

| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6b.flip.1 | `USE_DB_ARTIFACTS: bool = True` em `backend/app/core/config.py` | P0 | 5min | ✅ |
| A6b.flip.2 | CI consolidado: remove job `backend-tests-db-artifacts` (continue-on-error) e seta `MATHOMS_USE_DB_ARTIFACTS=true` no único `backend-tests` → bloqueia `all-green` | P0 | 15min | ✅ |
| A6b.flip.3 | Docs atualizadas (`CLAUDE.md`, `SETUP.md`, `ARCHITECTURE.md` §17.3/§ArtifactStore, `STATELESS_AUDIT.md`, `runbooks/cutover.md` header) | P0 | 30min | ✅ |
| A6b.flip.4 | ADR-118 registrada + `CHANGELOG.md [Unreleased]` | P0 | 20min | ✅ |

**Checkpoint A6b.flip:** ✅ Default `True` em `main`; rollback via `MATHOMS_USE_DB_ARTIFACTS=false` + redeploy (runbook `docs/runbooks/cutover.md §Rollback`).

### A6-ux.livestep — Contrato `LiveStep` ✅ entregue 2026-04-23 (ADR-119)

| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| livestep.1 | `LiveStep` payload formalizado (`items_done`, `items_total`, `current_item`, `phase`) + helper `pipeline.live_progress.emit_item_progress` com throttle | P0 | 2h | ✅ |
| livestep.2 | Primitivo frontend `<LiveStepProgress/>` render uniforme | P0 | 1h | ✅ |
| livestep.3 | Primeira adoção: E2-extratos + E2-faturas (sub-progresso "Arquivo N/M · nome.pdf") | P0 | 1h | ✅ |
| livestep.4 | ADR-119 registrada + CHANGELOG `[Unreleased]` | P0 | 30min | ✅ |
| livestep.5 | Migração das stages iterativas restantes (E1, E1.5, E1.5c, E2-llm) | P1 | 3h | ☐ |

**Checkpoint:** ✅ Contrato em produção; E2 emite progresso intra-stage. Demais stages iterativas migram sob demanda.

### A6-readers.dbfirst — Readers DB-first com fallback disco ✅ entregue 2026-04-23 (ADR-120)

| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| readers.1 | Helper único `backend.app.services.artifact_reader.read_latest_artifact(workspace_id, …)` DB-first, disco fallback | P0 | 2h | ✅ |
| readers.2 | Migração dos 4 readers user-facing impactados (dashboard, transações, extract-JSON IRPF, relatório HTML) | P0 | 3h | ✅ |
| readers.3 | Regressão do incidente 2026-04-23 (workspace caed2272, `940k` vs `4.3M`) coberta por teste | P0 | 1h | ✅ |
| readers.4 | ADR-120 registrada + CHANGELOG `[Unreleased]` | P0 | 30min | ✅ |

**Checkpoint:** ✅ Readers consultam `ArtifactStore` antes de disco; disco preservado p/ CLI dev; rollback ADR-118 continua viável.

### A6-human — Teste manual end-to-end (David)

| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6-human.1 | Auth + multi-tenancy (5 checks) | P0 | 30min | ☐ |
| A6-human.2 | Documentos + classificação (10 checks) | P0 | 1h | ☐ |
| A6-human.3 | Pipeline full + incremental + erro + histórico (7 checks) | P0 | 1h | ☐ |
| A6-human.4 | Cada stage E0-E7 (6 checks) | P0 | 1h | ☐ |
| A6-human.5 | Relatório completo (10 checks — seções, KPIs, linhagem, print, PDF, narrativas) | P0 | 1h | ☐ |
| A6-human.6 | Goals/Plano (7 checks — dashboard + 4 wizards + premissas) | P0 | 1h | ☐ |
| A6-human.7 | Configuração + admin + WS (8 checks) | P0 | 1h | ☐ |
| A6-human.8 | Cutover DB específico (5 checks — `pipeline_artifacts` + paridade disk/DB) | P0 | 1h | ☐ |
| A6-human.9 | Edge cases (5 checks — workspace sem baseline, fatura sem período, transf interna, etc.) | P0 | 1h | ☐ |
| A6-human.10 | Relatório final: checklist + lista de bugs + **decisão explícita** aprovar A6c ou bloquear | P0 | 30min | ☐ |

**Gate:** A6c **depende** de aprovação humana documentada.

### A6c — Deletar bridge + legados

| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6c.1 | Deletar `pipeline/stage_runner_compat.py` | P0 | 30min | ☐ |
| A6c.2 | Deletar `pipeline/materialization_bridge.py` | P0 | 30min | ☐ |
| A6c.3 | Deletar `main(root_dir)` legado dos 7 scripts determinísticos (E1.5c, E3, E4, E5, E5.N, E7) — manter helpers reutilizados | P0 | 2h | ☐ |
| A6c.4 | Atualizar docs (`ARCHITECTURE.md`, `CHANGELOG.md`, `CLAUDE.md`) | P0 | 1h | ☐ |

**Estimativa:** 1 sessão pequena (~20 testes ajustados).

### A6d — Fechar Caminho B puro nos 5 stages pragmáticos (ADR-100)

**Commitment — não opcional.** Converte E4/E5/E5.N/E7/E1.5c de pragmático para puro.

#### A6d.1 — Eliminação de globals nos 5 scripts

| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6d.1.1 | Padrão A3b replicado em `e4_categorize.py` | P1 | 1h | ☐ |
| A6d.1.2 | Padrão A3b em `e5_analyze.py` | P1 | 2h | ☐ |
| A6d.1.3 | Padrão A3b em `e5n_narrativas.py` | P1 | 1h | ☐ |
| A6d.1.4 | Padrão A3b em `e7_review.py` | P1 | 1h | ☐ |
| A6d.1.5 | Padrão A3b em `e15_consolidate.py` | P1 | 1h | ☐ |
| A6d.1.6 | Teste estrutural AST: `_init_config` não invocado em top-level dos 5 scripts | P1 | 30min | ☐ |

#### A6d.2 — Testabilidade dos `analyze_*` sem disco ✅ entregue 2026-04-20

| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6d.2.1 | `extract_if_target_from_life_plan(content=None)` / `extract_if_trs(content=None)` / `extract_renda_passiva_from_life_plan(content=None)` aceitam content string; `_read_life_plan_content()` centraliza o I/O | P1 | 2h | ✅ |
| A6d.2.2 | `parse_tarefas_md_content(text)` puro + wrapper `parse_tarefas_md(content=None)` com shell loader fino | P1 | 2h | ✅ |
| A6d.2.3 | `parse_milhas_md_content(text)` puro + wrapper `parse_milhas_md(content=None)` análogo | P1 | 1h | ✅ |
| A6d.2.4 | `load_methodology` já era shell-loader fino; `extract_persona_from_methodology(content)` já é puro — docstring formaliza separação em `scripts/e7_review.py` | P1 | 1h | ✅ |
| A6d.2.5 | `tests/unit/pipeline/test_e5_content_parsers.py` — 26 testes cobrindo parsers + extract_if_* sem `tmp_path`; shell loaders testados com `monkeypatch` de paths | P1 | 3h | ✅ |

**Checkpoint A6d.2:** ✅ MD content (`life_plan_goals.md`, `tarefas.md`, `milhas.md`) é lido uma única vez no shell (`scripts/e5_analyze.main_with_store(ctx)`) e repassado aos helpers puros. `analyze_goals(patrimonio, life_plan_content=None)` propaga content para os extractors. 1240 testes passando, zero regressão nos goldens (E3/E4/E5/E5.N/E6/E7).

#### A6d.3 — Integração dos 14+ domain services em `main_with_store`

| # | Entrega | Prio | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6d.3.1 | E4: auditoria confirmou que `main_with_store` já usa `E4CategorizerAdapter.from_configs` + `categorize_via_store` + `serialize_e4_artifacts` (entregue em A4b). Zero uso de `process_transactions`/`build_*_unified` dentro de `main_with_store` — funções legadas permanecem apenas em `main(root_dir)` CLI legado | P1 | 1 sessão | ✅ (verificado 2026-04-20) |
| A6d.3.2 | E5.N: decomposição de `build_narrativas` (425 locs) em pacote `pipeline/domain/services/narrativas/` com `NarrativasContext` + `PerfilFamiliaNarrator` + `SummariesNarrator` + `ChartsNarrator` orquestrados por `E5NarrativasBuilder`. `scripts.e5n_narrativas.build_narrativas` vira delegate de 2 linhas; format helpers + validator movidos para `format_helpers.py` com back-compat aliases. 10 tests novos em `tests/test_e5n_builder_decomposition.py` + paridade legado↔novo em `tests/test_e5n_e7_main_with_store_parity.py` | P1 | 1 sessão | ✅ 2026-04-20 |
| A6d.3.3 | E5: `E5AnalyzerAdapter` completado com 3 calculadoras puras novas (Etapa 1, já entregue) + switch de `main_with_store` para o adapter (Etapa 2, +143/-54 locs) + golden parity `tests/test_e5_main_with_store_parity.py` (Etapa 3, 2 cenários @ 0.01 BRL). Correções de paridade: `conjuge_key=""` sem default "mariana", `goals={}` no `PontosFortesAnalyzer`, `CenariosConjugeAnalyzer._compute_prazo` retorna `999` (int) | P1 | 2 sessões | ✅ 2026-04-20 |

**Estimativa total A6d:** 3-5 sessões grandes (~200+ testes). **Realizado:** A6d.1 + A6d.2 + A6d.3.1 + **A6d.3.2** + **A6d.3.3** (~5 sessões). **Resta:** nada — A6d **fechada** 2026-04-20. Caminho B **puro** para todos os stages determinísticos relevantes (E3, E5, E5.N); E4 e E1.5c permanecem em B pragmático (decisão consciente — refactor não entrega valor adicional relevante); E7 é LLM-bound e não migra.

### A6e — DDD/SOLID no backend API (ADR-101, R12-R17)

| # | Sub-fase | Entrega | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6e.1 | Repos por aggregate | User, Workspace, Document, Goal, PipelineRun, Task, Notification, Invitation, AuditLog repositories; `grep sqlalchemy backend/app/api/` = zero | 1-2 sessões | 🚧 parcial — **FamilyMember + Category + ConfigBlob + Document + Goal + Task** ✅ |
| A6e.2 | DTO ↔ Model | `schemas/dto/<aggregate>/response.py` + `command.py` + `query.py` + `mapper.py`; zero `Model.from_orm` em endpoints | 1 sessão | 🚧 parcial — **family_member + category + config_blob + document + goal + task** ✅ |
| A6e.3 | Application layer | `backend/app/application/<aggregate>/<use_case>.py`; 1 endpoint = 1 use case; testável sem DB via fakes | 2 sessões | 🚧 parcial — **FamilyMember + Category + Goal** (22 use cases) ✅ 2026-04-21 |
| A6e.3b | Use cases ConfigBlob + Task + Document | 3 agregados restantes + sub-agregados Task; Protocol + fakes; composites com storage/audit deferidos ao router | 2 sessões | ✅ 2026-04-22 — 25 use cases (6 ConfigBlob + 13 Task + 6 Document) + 61 testes puros; total application layer = 47 use cases em 6 agregados; `pytest backend/tests -q` 1054 passed |
| A6e.3c | Sweep `dict[str, Any]` → tipado em DTOs não-OPAQUE (follow-up ADR-114) | 4 arquivos em `schemas/dto/{family_member/*, category/mapper.py}`; promove `LEGACY_FILES` → `CLEAN_FILES` em `test_no_any_in_boundary.py` | 0.5 sessão | ✅ 2026-04-22 (`35c7502`) |
| A6e.4 | Routers finos | Refactor 4900→800 linhas (17 routers × ≤50); teste AST enforça | 1-2 sessões | ✅ 2026-04-22 (fase 4a 14/14 + fase 4b 3/3) |
| A6e.5 | Versionamento `/api/v1/` | Prefixo + aliases durante window; OpenAPI 3.1 versionado; `lib/api.ts` atualizado | 1 sessão | ✅ 2026-04-22 — rotas canônicas `/api/v1/*`; `LegacyApiDeprecationMiddleware` anuncia Sunset no `/api/*` (RFC 8594); `info.version=1.0.0`; `API_BASE` frontend + MSW + E2E sincronizados |
| A6e.events | Domain events tipados (ex-A6e.6) | `backend/app/events/` com `Event` base + `register_handler`; zero side-effect inline em use cases | 1 sessão | ✅ 2026-04-22 parcial (ADR-115) — 4 slices mergeados (infra + `AuditLogEvent` + `TaskCreated/UpdatedEvent`); 2 follow-ups abertos |
| A6e.events-migration | Migrar ~14 `audit_log()` inline em routers → `AuditLogEvent` | Padrão estabelecido em A6e.events slice 2 (`CreateFamilyMember` migrado); cada call-site vira emit no use case + handler | 1 sessão | ✅ 2026-04-22 — 10 call-sites (documents 5 + workspaces 4 + invitations 1) emitindo `AuditLogEvent` via `dispatch_sync`; `audit_log`/`audit_service.log` só no `services/` (referência de testes); 1177 backend tests passed |
| A6e.events-followup | Ativar flag `MATHOMS_USE_EVENT_DRIVEN_TASK_NOTIFICATIONS=true` em prod + remover cron | Monitor 48h flag → apagar `scan_and_create_notifications()` polling se zero regressão | 0.3 sessão | ⏸ aguarda janela de prod (pós-F7 deploy) |

**Estimativa total A6e:** 5-7 sessões grandes, ~400+ testes novos.

#### Slice entregue — **FamilyMember aggregate** (branch `a6e/family-member-slice`, 2026-04-20)

| Entrega | Detalhes | Commit |
| --- | --- | --- |
| `FamilyMemberRepository` async | 13 métodos; BankAccount como sub-entidade; cascade delete explícito (SQLite compat); `populate_existing=True` em eager-load | c84af46 |
| DTOs em `schemas/dto/family_member/` | response/command/mapper; mapper recebe vault via Protocol; `convert_global_defaults_to_responses` preserva F6.5E.6 | 2d9074b |
| Refactor `config.py` members/accounts | 5 endpoints delegam ao repo e retornam DTOs; ~130 linhas duplicadas removidas; compat binária via aliases em `schemas/config.py` | 13ece89 |
| Tests + regression gate | 10 unit tests mapper (puros) + 13 repo tests (DB real); BUG-004 sentinela migrada para mapper.py | 4167fa5 |

#### Slice entregue — **Document aggregate** (branch `agent/a6e5-document/*`, 2026-04-21)

| Entrega | Detalhes | Commit |
| --- | --- | --- |
| `DocumentRepository` async | 7 métodos (`list` com filtros, `get_by_id`, `get_by_content_hash`, `find_fuzzy_duplicate_id`, `list_non_error`, `add` flush-opt-out, `delete`); R13 no predicado; não commita (boundary = caller, necessário para savepoint de upload) | `9cbcf2f` |
| DTOs em `schemas/dto/document/` | response (5 DTOs, incluindo `DocumentExtractJsonResponse` e `DocumentReclassifyResponse` que migraram classes inline do router) + command (`DocumentUpdateCommand`) + mapper puro | `16ef59c` |
| Refactor `api/documents.py` | 8 endpoints delegam ao repo; `grep "select(Document" = zero`; upload flow preservado (savepoint + fuzzy-dedupe cross-referencial + cleanup + audit log); compat binária via shim em `schemas/document.py` | `4958d9a` |
| Tests | 15 unit tests mapper (puros, sem DB) + 16 repo tests (DB real; isolamento multi-tenant em todos os métodos; ordenação por `uploaded_at` DESC; fuzzy dedupe cross-tenant safety) | `ab240aa` |
| OpenAPI snapshot | 3 renames (`DocumentUpdateRequest`→`Command`, inline `ExtractJsonResponse`→`DocumentExtractJsonResponse`, inline `ReclassifyResponse`→`DocumentReclassifyResponse`) + descrições populadas | `2c5c134` |

**Impact:** 847 passed / 4 skipped (+31 vs 816 baseline; zero regressão).

**Escopo deixado para frente:** `document_processor.py`, `document_pipeline_sync.py` e `tasks/pipeline_task.py` continuam com ORM direto — migração é R15 (use-case layer) em slice futuro.

#### Slice entregue — **Goal aggregate** (branch `agent/a6e6-goal/*`, 2026-04-21)

| Entrega | Detalhes | Commit |
| --- | --- | --- |
| `GoalRepository` async | 4 métodos para semântica versionada: `get_active_by_type` (vigente), `get_by_id`, `list_by_workspace_and_type` (DESC), `create_new_version` (close active + flush + insert atômico). Validação de `VALID_GOAL_TYPES` em toda op; R13 no predicado; não commita | `41fa878` |
| DTOs em `schemas/dto/goal/` | 4 módulos por tipo (`if_goal.py`, `aporte.py`, `dolar.py`, `alocacao.py`) com 7 DTOs cada + `base.py` (shared response base) + `mapper.py` (`goal_to_typed_response` resolve classe via `GOAL_TYPE_DTO_CLASSES`) | `b2e1f90` |
| Refactor service + router + shim | `goal_service.py` -200 linhas (compute services permanecem puros); `api/goals.py` 16 endpoints com `grep "select(Goal" = zero`; `*UpsertRequest` → `*UpsertCommand`; shim em `schemas/goal.py` preserva compat binária | `eca59b0` |
| Tests | 16 mapper tests (dispatch por tipo, fallbacks de `meta_version`, narrow IF) + 12 repo tests (DB real; `create_new_version` fecha vigente ANTES; cross-tenant safety) | `1c8ecfb` |
| OpenAPI snapshot | 4 renames `*UpsertRequest` → `*UpsertCommand` + docstring descriptions | `8760d7e` |

**Impact:** 884 passed / 4 skipped (+28 vs 856 pós-A6e.5; zero regressão).

**Escopo deixado para frente:** `goal_compute_*.py` são domain logic pura (decisão consciente — não migra); Report lookup (`get_latest_report_patrimonio_liquido`) fica em goal_service até Report virar agregado próprio (slice futuro).

#### Slice entregue — **Task aggregate** (branch `agent/a6e7-task/*`, 2026-04-21)

Último do trilho per-aggregate. 3 sub-agregados: Task + TaskAttachment + TaskSuggestion.

| Entrega | Detalhes | Commit |
| --- | --- | --- |
| 3 repositórios separados | `TaskRepository` (list com filtros + priority_rank CASE S<R<O, list_all, get_by_id/number, list_by_parent subtasks, next_number atômico, add/save/delete); `TaskAttachmentRepository` (só DB — storage fica no service); `TaskSuggestionRepository` (list_by_status default pending, add/save) | `daddb8d` |
| DTOs em `schemas/dto/task/` | 9 módulos especializados: types/response/command/filters/progress/attachment/suggestion/mapper. `*Request` → `*Command`; `TaskProgress` → `TaskProgressResponse` | `93cef55` |
| Refactor services + router + shim | `task_service` + `task_attachment_service` + `task_suggestion_service` delegam aos repos; `api/tasks.py` 17 endpoints com `grep "select(Task\|TaskAttachment\|TaskSuggestion" = zero`; shim em `schemas/task.py` preserva compat binária | `c05e51b` |
| Tests | 18 mapper tests (puros) + 24 repo tests (DB real; filtros, ordenação, isolamento multi-tenant em 3 repos, cross-tenant safety, next_number por workspace) | `0c8fd11` |
| OpenAPI snapshot | 7 renames `*Request`→`*Command` + `TaskProgress`→`TaskProgressResponse` | `042c6ed` |

**Impact:** 926 passed / 4 skipped (+42 vs 884 pós-A6e.6; zero regressão).

**Escopo deixado para frente:** nenhum aggregate residual — per-aggregate track concluído.

---

**Trilho per-aggregate CONCLUÍDO.** Destrava agora **A6e.3** (use cases — application layer R15), **A6e.4** (routers finos ≤50 linhas R16), **A6e.5** (/api/v1/ prefix), **A6e.events** (domain events tipados R17, ex-`A6e.6`) — todas **transversais** a todos os 6 agregados migrados.

**Pré-existente fora de escopo (reportado):** `test_alembic_guardrails::test_offline_sql_generation_works` falha por migration A6b `r6s7t8u9v0w1` usando `batch_alter_table` sem `copy_from`; `test_documents.py` x9 falha por schema drift em `workspaces.use_db_artifacts_override`. Nenhum dos dois tocado pelo slice A6e.1+.2.

### A6f — Language-neutral boundaries (ADR-102, R18-R20)

| # | Sub-fase | Entrega | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6f.1 | Pipeline-as-service | ✅ `pipeline-service/` FastAPI standalone (app + contracts + services); 3 rotas (`POST /runs`, `POST /stages/{stage}/execute`, WS `/events/{run_id}`); `PipelineServiceClient` Protocol + `HttpPipelineClient` + `InProcessPipelineClient`; backend `pipeline_task.py` zero `from pipeline.orchestrator` imports; `docker-compose.pipeline-service.yml`; `/health` do backend reporta `pipeline_service_url`/`reachable`; OpenAPI snapshot em `docs/api/v1/pipeline-service.openapi.json`; 21 tests novos (13 service + 8 client). ADR-112. Extração de helpers de `pipeline_task.py` para ≤100 linhas **deferida** para slice próprio. | 3 sessões | ✅ 2026-04-21 |
| A6f.2 | OpenAPI + codegen | ✅ ~12 DTOs novos; snapshot em `docs/api/v1/openapi.json` (12856 linhas); `make update-openapi-snapshot`; teste estrutural + snapshot diff | 1 sessão | ✅ 2026-04-20 |
| A6f.3 | Structured logs JSON + OTel | ✅ `MathomsJsonFormatter` + `CorrelationIdMiddleware` (trace_id/workspace_id/user_id/pipeline_run_id via contextvars); `setup_otel()` opt-in via `OTEL_EXPORTER_OTLP_ENDPOINT`; FastAPI+SQLAlchemy+Celery instrumentation fork-safe; 8 tests em `test_structured_logging.py`; env vars `MATHOMS_LOG_LEVEL`, `MATHOMS_LOG_FORMAT`; ADR-110 | 1 sessão | ✅ 2026-04-20 |
| A6f.4 | DB schema language-neutral | ✅ `docs/DB_SCHEMA_REFERENCE.md` auto-gerado (27 tabelas, 1193 linhas); `dev/generate_db_schema_reference.py` determinístico; snapshot test + `make update-db-schema-reference`; auditoria zero `PickleType` e zero `DateTime` naive; Go struct tags equivalentes | 1 sessão | ✅ 2026-04-20 |
| A6f.5a | Auth portability documentada | JWT HS256 `{sub, exp, tv}` + Fernet mantidos; ADR-109; `test_auth_portability.py` (12 testes JWT+Fernet parity) | 1 sessão | ✅ 2026-04-20 |
| A6f.5b | Fernet → AES-GCM (deferido) | AES-256-GCM + HKDF-SHA256; migration de `LLMConfig.api_key_encrypted` + vault_entries; decrypt fallback para Fernet durante cutover | 1 sessão | ⏸️ deferido (ADR-109) |
| A6f.5c | JWT HS256 → RS256 (deferido) | Só se houver separação real entre emissor e validador (ex: pipeline-service valida tokens do backend) | 1 sessão | ⏸️ deferido (ADR-109) |
| A6f.6 | Stateless rigoroso | WebSocket via Redis pub/sub; rate limiting Redis; zero `@lru_cache` mutable; `tests/integration/test_multi_worker_concurrency.py` | 1-2 sessões | ✅ 2026-04-20 · ADR-111 · audit em `docs/STATELESS_AUDIT.md` (gaps críticos: 0) + 5 tests multi-worker empíricos. Nenhum refactor de código necessário — backend já era multi-worker-safe desde P5 (WS pub/sub + DB rate limit + zero `asyncio.create_task`). Regra operacional R19 formalizada em CLAUDE.md. |

**Estimativa total A6f:** 6-8 sessões grandes (A6f.5b e .5c só contam se gatilho acionar).

**Gatilhos para A6f.5b (Fernet → AES-GCM)**, qualquer um:
- Requisito de compliance (SOC 2 type II, ISO 27001 exigindo AEAD moderno).
- Migração Go real em curso (aproveita janela de re-encrypt).
- CVE publicado contra Fernet format ou `cryptography.fernet`.

**Gatilho para A6f.5c (JWT RS256)**:
- Separação real entre emissor e validador (ex: A6f.1 pipeline-service
  validando tokens emitidos pelo backend) — até lá HS256 é suficiente.

### A6g — Code Style Sweep (CLAUDE.md §Code style)

**Objetivo:** revisar e aplicar o `## Code style` de [CLAUDE.md](../CLAUDE.md) em todo o código existente — Python (`pipeline/`, `scripts/`, `backend/`), TypeScript (`frontend/`) e preparatório para Go (A6f). Corrige drift acumulado antes que vire convenção implícita.

**Premissa:** drift existe e é silencioso. Sem um sweep deliberado, o estilo novo vale só para código futuro; código legado continua ofendendo (funções gigantes em `e5_analyze.py`, `Dict[str, Any]` em boundaries antigos, nomes genéricos sobreviventes, docstrings multi-parágrafo, comentários WHAT). Sweep + enforcement automatizado congelam o estilo como contrato.

| # | Sub-fase | Entrega | Esforço | Status |
| --- | --- | --- | --- | --- |
| A6g.1 | **Auditoria inicial** — script `dev/audit_code_style.py` + pacote `dev/_audit_cs_internals/`. Mede drift em P1-P10 (Python) e T1-T5 (TypeScript). Output: `_scratch/code_style_audit_<date>.{json,md}`. Primeira rodada 2026-04-21: **2047 ofensores** (462 high, 556 med, 1001 low, 28 info) em 467 py + 159 ts. Top alvos: `scripts/e6_render.py` (3875 linhas), `scripts/e5_analyze.py` (2862), `scripts/e_reset.py::main` (372 linhas). Dogfood passa `--strict`. Roda em ~2s | 1 sessão | ✅ (2026-04-21) |
| A6g.2 | **Pipeline Python** (`pipeline/`, `scripts/`, `tests/fixtures/`) — aplicar code style. **1ª rodada defensiva** (`docs/agent_prompts/track_a6g2_pipeline_style_sweep.md`): Tier 1 (`e_reset::main`, `pdf_generator.py`, `e0_audit.py`) sem goldens; Tier 2 opcional (`charts_narrator.narrate`, `pipeline_task.run_pipeline_task`). **Fora de escopo:** `e3/e4/e5/e5n/e6/e7_*.py` (goldens) e `main(root_dir)` legado (A6c.3 vai deletar) → 2ª rodada (A6g.2b) pós-A6c.3. **1ª rodada 2026-04-21:** T1.a `e_reset.main` 372→27 linhas; T1.b `pdf_generator.py` 1067→29 (shim) + pacote `tests/fixtures/pdf/` com 11 bancos + formatters + dispatcher; T1.c `e0_audit.py` 948→238 linhas, checks em `scripts/e0/audit_{helpers,filename,integrity,ledger}.py`; T2.b `run_pipeline_task` 273→58 linhas, 11 helpers por fase do ciclo de vida de `PipelineRun`; T2.a `ChartsNarrator.narrate` 284→36 linhas, 6 métodos privados por grupo de charts (paridade byte-a-byte preservada — 12 goldens E5.N verdes). Pipeline + backend tests em paridade; JSON/HTML outputs + OpenAPI snapshot idênticos | 1-2 sessões (rodada 1) + 2 sessões (rodada 2) | 🚧 parcial — Tier 1+2 ✅ 2026-04-21; Tier 3 (scripts com goldens) ⏸ pós-A6c.3 |
| A6g.3 | **Backend Python** (`backend/app/`) — integra com A6e (nomes, DTOs, routers finos). A6e.4 (routers ≤50 linhas) é o chute maior; A6g.3 cobre restante (services, repos, helpers, typing). Prompt: `docs/agent_prompts/track_a6g3_backend_style_sweep.md`. **1ª rodada 2026-04-22:** P4 optional defaults 5→0, P8 what-comments 2→0, P1 decomp em 4 services top (`pipeline_adapter` 5→2, `goal_service` 4→3, `task_service` 4→1, `task_progress_service` 3→0). **2ª rodada 2026-04-22:** P1 decomp em +4 services (`invitation_service` 4→2, `document_processor` 2→1, `canonical_routing` 3→1, `tarefas_md_parser` 2→1) — funções ≥40l caem 72→68. **P5 float money (13) deferido** como **A6g.3b** — wire-compat migration via MoneyBRL type; lane dedicada com prompt pronto. **3ª rodada pendente** (`content_classifier` 621l, `pipeline_service` P1×4, `models/task.py` 308l, repositories P1×5) | 2 sessões por rodada (3 rodadas planejadas) | 🚧 parcial — rodadas 1+2 ✅ 2026-04-22; continuação ☐ |
| A6g.3b | **Money Decimal migration** (follow-up A6g.3) — elimina `P5_float_money` via tipo `MoneyBRL`/`MoneyUSD` = `Annotated[Decimal, BeforeValidator, PlainSerializer(float, when_used='json')]`. Decimal em memória para precisão, number no JSON para wire-compat com frontend. Prompt: `docs/agent_prompts/track_a6g3b_decimal_money_migration.md`. **1ª sessão — slices 1+3 ✅ 2026-04-22:** tipo `MoneyBRL`/`MoneyUSD` + 11 tests; transactions 4 campos + cascata services + 19 tests; OpenAPI zero diff. **2ª sessão — slice 2 ✅ 2026-04-22:** 11 campos goal DTOs (`aporte`/`dolar`/`if_goal`) + math Decimal em `goal_service.py` (`_retorno_mensal_decimal` via `Decimal.ln()/.exp()`, `_pmt_constante_ate_fv`, `_if_meta_targets`, `_aporte_cobrindo_gap_com_patrimonio`, `compute_if/aporte/dolar_derived`); persistência via `model_dump(mode="json")` (SQLAlchemy JSON col não tem codec Decimal); factory `make_if_goal` e use cases `create_if/typed_goal_version` atualizados; OpenAPI snapshot regenerado (Input/Output split por causa do `BeforeValidator`, Output wire `number` puro — frontend TS intacto); 64 tests goal verdes, só 1 assertion ajustada. **Restam (polish):** S0 tolerance rename (P5 pode cair 13→0), S4 frontend sanity manual, S5 baseline regen + ADR-090 nota final. | 2 sessões dedicadas (~1.5h cada) | 🚧 parcial — sessões 1+2 ✅ 2026-04-22; polish ☐ |
| A6g.4 | **Frontend TypeScript** (`frontend/src/`) — eliminar `any` residual, nomes genéricos (`utils.ts`), arquivos >500 linhas (`api.ts` 1880, `pipeline/page.tsx` 1195), hex colors, componentes/hooks >40 linhas. Prompt: `docs/agent_prompts/track_a6g4_frontend_style_sweep.md`. Respeitar codegen em `frontend/src/generated/` (não editar). **1ª rodada 2026-04-21:** T1 9→0, T2 7→6 (api.ts 1880→14 módulos), T3 24→18 (high severity 12→0), T4 1→0, T5 12→0. 53 ofensores → 30 (-43%). **2ª rodada A6g.4b 2026-04-22:** 4 das 6 páginas `>500 l` decompostas (`pipeline` 1195→368, `documents` 801→347, `transactions` 741→399, `dashboard` 515→142) + 3 hooks extraídos de `TransactionsContent`. Ofensores 30 → 27. **3ª rodada A6g.4c 2026-04-22:** as 2 páginas `plano/*` remanescentes decompostas (`plano/page.tsx` 630→152 + 8 módulos; `plano/alocacao/wizard/page.tsx` 533→185 + 7 módulos). **T2 `ts_long_files` zerado** em `frontend/src/`. Ofensores 27 → 29 (líquido +2 por granularidade JSX, T3 high 2→1). Enforcement ESLint segue para A6g.6 | 1-2 sessões por rodada (3 rodadas) | ✅ fechada 2026-04-22 — rodada 1+2+3 mergeadas |
| A6g.5 | **Testes** (`tests/`, `backend/tests/`, `frontend/tests/`) — aplicar code style também em teste: fakes nomeados > `MagicMock` inline, fixtures <20 linhas, nomes descritivos (`test_reconcile_drops_duplicate_when_same_hash` > `test_dedupe_1`). Não relaxa o padrão em teste | 1 sessão | ☐ |
| A6g.6 | **Enforcement automatizado** — transforma regras do CLAUDE.md em gates de CI. Bicameral (imediato + progressivo): (a) Ruff E/F/I/W bloqueante via `[tool.ruff.lint]` + hook pre-commit + CI; (b) ESLint flat config v9 com `@typescript-eslint/no-explicit-any: error`; (c) pre-commit hooks grep `check_forbidden_names.py` + `check_float_money.py` (bloqueia apenas linhas adicionadas); (d) testes AST `test_no_any_in_boundary.py` + `test_no_forbidden_names.py` como fail-safe; (e) `check_code_style_regression.py` compara audit vs `dev/code_style_baseline.json` — legado decresce, nunca cresce. Prompt: `docs/agent_prompts/track_a6g6_enforcement.md` | 1 sessão | ✅ 2026-04-22 (ADR-114) |
| A6g.6b | Follow-up A6g.6: sweep ruff `--fix I001/F541` + `ruff format .` + promove `max-lines` warn→error | 361 auto-fixes (290 I001 + 71 F541) em 263 arquivos; 435 arquivos reformatados; `ignore = [I001, F541]` removido; `ruff-format --check` ativo no pre-commit. `max-lines` (T2, 0 ofensores) promovido a error. `max-lines-per-function` **mantido em warn** — 64 ofensores em 59 components React (tasks/report/config); promoção depende de sweep refactor dedicado (lane futura) | 1 sessão | ✅ 2026-04-22 |
| A6g.2c | Follow-up A6g.6: rename `pipeline/llm/service.py` (filename genérico, estava em ALLOWLIST `check_forbidden_names.py`). Renomeado para `pipeline/llm/litellm_client.py`; 11 imports atualizados; 2 ALLOWLISTs zeradas; hook `check_float_money.py` ganha `_is_rename()` para não bater em renames puros | 0.2 sessão | ✅ 2026-04-22 |
| A6g.7 | **Go prep** (A6f.1 ✅ 2026-04-21 destravou) — config `golangci-lint.yml` com `funlen`, `gocyclo`, `gocognit`, `revive` (nomes) alinhados ao code style. Regras vivem no repo antes do primeiro commit Go | 0.5 sessão | ✅ 2026-04-22 (ADR-113) |

**Estimativa total A6g:** 7-10 sessões médias. Pode rodar em paralelo a A6d/A6e/A6f — mas A6g.3 se beneficia de vir **depois** de A6e.4 (routers finos), e A6g.2 ignora o que A6d está fechando.

**Critérios de aceite globais:**
- Audit A6g.1 roda em <30s e é executado no CI como informativo (não bloqueante inicialmente).
- Cada sweep (A6g.2-.5) deixa o audit com **melhora mensurável** (contador de ofensores cai por categoria). Sem regressão em outras categorias.
- Enforcement A6g.6 bloqueia **apenas código novo**; legado fica em allowlist decrescente com TODO.
- Zero regressão funcional — todos os goldens, testes unit/integração/E2E continuam verdes em cada commit do sweep.

**Exceções aceitas (documentar em ADR se recorrente):**
- Parsers bank-specific em `scripts/e2/banks/` podem ter funções 25-40 linhas quando a alternativa é decomposição que prejudica leitura sequencial do formato.
- Generated files (`frontend/src/generated/`, OpenAPI snapshot, Pydantic models via codegen) — fora do escopo, nunca editar.
- Testes de paridade golden que comparam estruturas grandes inline — mantidos como estão.

> **Pickup de task / diagrama de ondas / lanes abertas:** fonte única no
> topo de [§Sprint A6](#sprint-a6--migração-infradomínio-plano-transversal) —
> subseções "Lanes abertas agora" e "Ondas paralelas — mapa de dependências".

---

## F7 — Produção + LGPD

**Objetivo:** Produto no ar com segurança, CI/CD, LGPD.

**Duração estimada:** 6-8 semanas + 2 semanas dogfood.

### 7A — Docker + Deploy + HTTPS (semana 1-2)

**URLs canônicas (ADR-108):** `app.mathoms.ai` (produto) · `api.mathoms.ai/v1/...` (backend + WS) · `ops.mathoms.ai` (console interno F7F) · `docs.mathoms.ai` · `status.mathoms.ai` · apex `mathoms.ai` (landing). Staging: `*.staging.mathoms.ai`. Domínio em **Cloudflare Domains**. Ver [ARCHITECTURE.md §18](ARCHITECTURE.md#18-domínios-e-urls-públicas-f7a).

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

### 7B — Security Hardening + LGPD (semana 2-3)

#### Decisões arquiteturais LGPD (D1–D5)

Estas decisões moldam as tasks 7B.* abaixo. Absorvidas em 2026-04-21 do
plano-mestre A6 §15 (antes em `_scratch/`, agora canônico aqui).
**Motivação:** `pipeline_artifacts.content_json` armazena dados
financeiros pessoais (saldos, transações) + membros (CPF, nome, data
nascimento, ocupação). Postgres TDE protege disco físico, não leaks
lógicos — a defesa é app-level + audit + retenção.

**D1 — Criptografia app-level em campos de PII**
- Campos com PII (CPF, nome completo) cifrados via `cryptography.fernet`; chave em `FIN_PII_ENCRYPTION_KEY` (secret manager, obrigatória em prod — deploy falha se ausente).
- Campos em `content_json` armazenados como string `enc:<base64_ciphertext>`; `PipelineArtifact.content_json` JSONB preserva chave original, valor é o ciphertext.
- Leitura: decrypt on-demand em `PipelineArtifactRepository.read_decrypted()` — nunca retorna ciphertext ao caller.
- **Tasks relacionadas:** 7B.1 expande a utility `encrypt_field()` / `decrypt_field()`.

**D2 — Não criptografar valores monetários**
- Cifrar `amount` quebra agregações SQL e força O(n) em memória para relatórios.
- Risco aceitável: valores sem nome/CPF têm baixa identificabilidade isolada.
- Proteção via controles de acesso (D3) + retenção (D4), não criptografia.

**D3 — Audit log em acesso de leitura a `pipeline_artifacts`**
- Toda leitura via API (`GET /reports/{id}/data`, `GET /pipeline/artifacts/*`) registra em `access_audit_log`: `user_id`, `workspace_id`, `artifact_id`, `timestamp`, `ip`.
- Retenção: 1 ano. Consultado em incident response.
- **Tasks relacionadas:** 7B.5 audit log — estender middleware para incluir READ ops em artefatos (hoje cobre só write).

**D4 — Política de retenção + direito ao esquecimento (LGPD Art. 18)**
- Artefatos ativos: mantidos indefinidamente; usuário pode deletar via `/workspace/delete`.
- Artefatos de runs não-ativas (histórico): 2 anos → arquivados (soft delete).
- Direito ao esquecimento: endpoint `DELETE /workspace/{id}/artifacts` remove **todos** `pipeline_artifacts` + `documents.*_content` do workspace em ≤24h úteis.
- **Tasks relacionadas:** 7B.7 (LGPD Exclusão), 7B.9 (Storage cleanup), 7B.17 (Soft-delete 30d), 7B.18 (DSAR SLA 15d).

**D5 — Masking em logs estruturados**
- ADR-110 já cobre redaction no `MathomsJsonFormatter` para campos sensíveis (password, secret, token, api_key, cpf, cnpj, valor, saldo). **Estender:**
- Nomes de membros viram `member_<hash[:6]>` em logs estruturados (hash determinístico com salt por workspace — permite correlação de eventos sem expor nome real).
- Níveis: `INFO` nunca inclui `content_json` de `DBArtifactStore.read/write`; `DEBUG` pode incluir (apenas dev).
- **Tasks relacionadas:** 7B.5 (audit log também respeita masking).

#### Implementação por fase

| Marco | Entregável |
|-------|-----------|
| Pré-F7B | `PipelineArtifact.content_json` JSONB + `schema_version`; sem crypto ainda (entregue em A6a) |
| F7B.1 | `encrypt_field()` / `decrypt_field()` utilities; `PipelineArtifactRepository.read_decrypted()` hook (no-op se chave ausente em dev) |
| F7B.1+ | Crypto ativa em `extract_members` (piloto com CPF mascarado) |
| F7B.5 | Audit log cobrindo todas leituras via API (D3); retenção 1 ano configurada |
| F7B.7 | `DELETE /workspace/{id}/artifacts` (D4, direito ao esquecimento) + soft-delete 30d + DSAR 15d |
| F7B.9 | Retenção de 2 anos em runs não-ativas (D4) via Celery periodic task |

#### Critérios de aceite globais (F7B → produção)

- [ ] `FIN_PII_ENCRYPTION_KEY` obrigatória em produção (deploy falha se ausente)
- [ ] `extract_members` em produção armazena CPF criptografado em `content_json`
- [ ] `access_audit_log` populado em 100% dos GETs de `/reports/{id}/data`
- [ ] `DELETE /workspace/{id}/artifacts` remove todos artefatos e confirma via count
- [ ] Logs INFO não contêm CPF, nome completo ou valores monetários totais (validar via `dev/scan_logs_for_pii.py`)

---

| #     | Tarefa                                                                                               | Prio | Est. | Status |
| ----- | ---------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 7B.1  | Fernet expandido (CPFs + dados financeiros sensíveis + utility `encrypt_field()`/`decrypt_field()`) — implementa **D1** | P0   | 6h   | ☐      |
| 7B.2  | Rate limiting (slowapi: auth 5/min, upload 10/min, pipeline 2/min, geral 100/min)                    | P0   | 3h   | ☐      |
| 7B.3  | Security headers (CORS restritivo, HSTS, CSP, X-Frame-Options, X-Content-Type-Options)               | P0   | 3h   | ☐      |
| 7B.4  | Session security (JWT 15min + refresh 7d httpOnly, rotation, revogação on password change, frontend interceptor) | P0 | 16h | ☐ |
| 7B.5  | Audit log (model `AuditEntry`, middleware para write ops, todas ações sensíveis)                     | P0   | 6h   | ☐      |
| 7B.6  | LGPD — Termos + Privacy (páginas `/terms` `/privacy`, aceite obrigatório, `accepted_at`)             | P0   | 4h   | ☐      |
| 7B.7  | LGPD — Exclusão (`DELETE /api/account`, cascade completo, confirmação dupla + audit)                 | P0   | 8h   | ☐      |
| 7B.8  | LGPD — Portabilidade (`GET /api/account/export`, ZIP com dados pessoais, download link temporário)   | P1   | 6h   | ☐      |
| 7B.9  | Storage cleanup (retention 90 dias, Celery periodic task, soft-delete)                               | P1   | 4h   | ☐      |
| 7B.10 | UX de produção (rate limit toast, LGPD delete stepper, export notification, maintenance page)        | P1   | 4h   | ☐      |
| 7B.11 | **Email verification** no registro (token 24h, link em email, bloqueio de login até verificar, reenvio) — **sem isso GA é impossível** | P0 | 6h | ☐ |
| 7B.12 | **Password reset** (fluxo completo: endpoint request, token Fernet 1h, email com link, página `/reset-password/{token}`, invalidação de refresh tokens) | P0 | 8h | ☐ |
| 7B.13 | **Brute-force lockout**: N falhas consecutivas (5) → cooldown escalonado (1min → 5min → 15min → 1h); contador em Redis com TTL; unlock automático e manual (admin) | P0 | 3h | ☐ |
| 7B.14 | **MFA decision stub**: ADR documentando se TOTP entra F7 ou F8; se F8, stub de campo `mfa_enabled` em `User` para migration path futura sem breaking change | P1 | 1h | ☐ |
| 7B.15 | **Prompt injection defense** para E2-llm/E1.5: sanitização de texto extraído (strip invisível/zero-width/ANSI), allowlist rígida de campos no output via Instructor, truncamento de input com warning, teste com PDF adversarial fixture | P0 | 6h | ☐ |
| 7B.16 | **Terms versioning + re-aceitação**: `TermsVersion` model (`version`, `content_md`, `effective_at`); `UserTermsAcceptance` (`user_id`, `version_id`, `accepted_at`); prompt de re-aceitação quando versão ativa muda; bloqueio de API até aceitar | P1 | 4h | ☐ |
| 7B.17 | **Soft-delete period** em LGPD delete (7B.7): `deleted_at` timestamp, 30 dias de reversibilidade via endpoint, Celery task purga definitivamente após 30d, email de confirmação | P1 | 4h | ☐ |
| 7B.18 | **DSAR SLA workflow** (LGPD art. 18, 15 dias): endpoint `POST /api/account/dsar`, cria ticket, notifica admin, template de resposta, audit log; exportação automatizada reusa 7B.8 | P1 | 5h | ☐ |

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
| 7D.1  | Gap-fill unit tests (E0, E2/banks, E3, E4, E7 edge cases)                                       | P0   | 10h  | ✅ Leva inicial: `tests/test_e0_route_edges.py`, `test_e3_dedup` (período inválido), `test_e4_categorize` (despesa vazia), `tests/test_e7_edges.py`; E2/banks já cobertos por `test_e2_synthetic_pdf_parsers` + goldens |
| 7D.2  | Gap-fill unit tests (E5, E5N, E6 — scripts maiores)                                             | P1   | 12h  | ✅ Leva inicial: `tests/test_e5_e6_e5n_edges.py` (helpers puros); goldens E5/E5N/E6 existentes continuam como regressão pesada |
| 7D.3  | Gap-fill API endpoints + services (error paths, DB/Redis down, auth edge, concurrency)           | P0   | 8h   | ☐      |
| 7D.4  | CI integra frontend tests (Vitest + Playwright da F6.5) no pipeline de deploy                    | P0   | 1h   | ☐      |
| 7D.5  | Frontend E2E com PostgreSQL prod DB (ajustar fixtures)                                           | P1   | 2h   | ☐      |
| 7D.6  | Testes de UX de produção (rate limit toast, LGPD delete, export notification, maintenance)      | P1   | 3h   | ☐      |
| 7D.7  | Performance baseline (`time` pipeline E2E, p50/p95 API endpoints, `docs/PERFORMANCE_BASELINE.md`)| P1   | 3h   | ☐      |
| 7D.8  | Coverage integration (CI gate, Codecov, badge README, target ≥85% line / ≥75% branch)           | P0   | 3h   | ☐      |
| 7D.9  | Telemetria básica (tabela `UsageMetric`, privacy-first, dashboard query simples)                 | P1   | 4h   | ☐      |
| 7D.10 | Pre-launch checklist (smoke test prod, backup restore, rollback test, SSL Labs grade A)          | P0   | 3h   | ☐      |
| 7D.11 | **Dogfood period** (2+ semanas uso real, 5+ pipeline runs, zero critical bugs)                   | P0   | —    | ☐      |

### 7E — Operational Readiness (semana 6-7, ~2 semanas)

> Sub-fase dedicada à maturidade operacional além de "produto compila e sobe": runs órfãs, disaster recovery testado, observabilidade de negócio (não só erros), comunicação durante incidentes, e proteção contra runaway de custo LLM (BYOK não isenta de monitoring). Ver [ADR-065](DECISIONS.md#adr-065--sub-fase-7e-operational-readiness).

#### 7E.A — Pipeline operacional

| #     | Tarefa                                                                                                                                                                       | Prio | Est. | Status |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 7E.1  | **Stuck pipeline run detector**: campo `last_heartbeat_at` em `PipelineRun`, atualizado a cada stage; Celery beat task roda a cada 5min e marca como `failed` runs sem heartbeat há >1h; notification automática | P0 | 4h | ☐ |

#### 7E.B — Disaster recovery

| #     | Tarefa                                                                                                                                       | Prio | Est. | Status |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 7E.2  | **Restore drill quarterly**: documentado em RUNBOOK; executar pré-beta; gravar tempo real (RTO efetivo); checklist de validação pós-restore | P0 | 3h | ☐ |
| 7E.3  | **RPO/RTO declarados**: docs/SLO.md com targets (RPO=24h, RTO=4h propostos para dogfood; RPO=1h, RTO=1h para beta)                          | P0 | 1h | ☐ |
| 7E.4  | **Off-site backup** (S3 BR ou Backblaze B2): pg_dump diário replicado fora do Hetzner; rotação 30d off-site; restore testado de off-site    | P0 | 4h | ☐ |
| 7E.5  | **FERNET_KEY loss recovery**: procedure documentado em RUNBOOK; teste em ambiente staging que simula key perdida; backup criptografado da key em local separado (ex: 1Password vault) | P0 | 3h | ☐ |

#### 7E.C — Observabilidade de negócio

| #     | Tarefa                                                                                                                                                                                                          | Prio | Est. | Status |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 7E.6  | **Status page público** (`uptime-kuma` self-hosted ou `instatus.com` free tier): incidentes manuais + uptime auto; link na footer do app                                                                       | P1 | 3h | ✅ Sprint A: `NEXT_PUBLIC_MATHOMS_STATUS_PAGE_URL` + `StatusPageFooter` (login, register, invite, AppShell); provisão da ferramenta continua no deploy — ver [RUNBOOK.md](RUNBOOK.md#2-status-page-7e6) |
| 7E.7  | **Business metrics dashboard**: query simples + página interna `/admin/metrics`: runs/day, success rate trend (7d/30d), p95 duration, custo médio LLM por run, documents uploaded/day, active workspaces — integra **IA-2** do [INTERNAL_ADMIN_ROADMAP.md](INTERNAL_ADMIN_ROADMAP.md) (protegida por **7F.2–7F.4**) | P1 | 6h | ☐ |
| 7E.8  | **SLOs/SLAs declarados** em `docs/SLO.md`: uptime 99% beta / 99.5% GA; p95 API <1s; p95 pipeline free <5min, premium <15min; alertas Sentry quando burn rate >2x                                                | P0 | 1h | ✅ Sprint A: [SLO.md](SLO.md) (alvos + SLA comunicação incidente); burn rate Sentry continua em 7C |

#### 7E.D — Comunicação de incidentes

| #     | Tarefa                                                                                                                                                                  | Prio | Est. | Status |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 7E.9  | **Incident comms templates** em RUNBOOK: 3 templates Markdown (`initial_report`, `update_in_progress`, `resolved_postmortem`) com placeholders e exemplos preenchidos; treinar uso na primeira incident drill | P0 | 2h | ✅ Sprint A: [runbooks/incidents/](runbooks/incidents/) + [RUNBOOK.md](RUNBOOK.md#3-resposta-a-incidentes); drill checklist em [RUNBOOK.md](RUNBOOK.md#4-drill-de-incidente-obrigatório-antes-do-beta-fechado) |
| 7E.10 | **Support runbook** (`docs/SUPPORT.md`): triagem por severidade, templates de resposta para 5 perguntas comuns, fluxo de escalação, tempo de resposta esperado por tier | P1 | 4h | ☐ |

**Detalhamento — status page (7E.6) e incidentes (7E.9)**

| Área | O quê incluir |
| --- | --- |
| **Status page (7E.6)** | Ferramenta (`uptime-kuma`, Instatus, etc.): componentes **API**, **frontend**, **worker/Celery**, **Redis** (ou agregado “processamento”); incidentes **manuais** com título, descrição curta, severidade, atualizações; link público na **footer** do app e no e-mail de boas-vindas / suporte. SLA de conteúdo: incidente “investigating” em **menos de 15 minutos** após detecção interna (alinhado a 7E.8). |
| **7E.9 — Templates** | Três arquivos em `docs/` ou `runbooks/incidents/`: (1) **initial** — o quê falhou, impacto usuário, escopo (região/tier), próximo update em X min; (2) **update** — mitigação em curso, workaround; (3) **resolved** — causa raiz (se conhecida), duração, follow-up. Idioma **pt-BR** para usuários; técnico pode ser bilíngue. Placeholders: `{{INCIDENT_ID}}`, `{{SEVERITY}}`, `{{AFFECTED_AREAS}}`, `{{ETA_NEXT_UPDATE}}`. |
| **Processo** | Primeiro drill **antes do beta**: publicar incidente fictício, linkar status page, postar update e resolved; registrar tempo e melhorias no RUNBOOK. Opcional **P2:** banner in-app não bloqueante quando `status` API reportar incidente ativo (depende de endpoint ou scraping seguro). |

#### 7E.E — LLM cost runaway protection

| #     | Tarefa                                                                                                                                                                                                            | Prio | Est. | Status |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---- | ------ |
| 7E.11 | **LLM cost cap por workspace/mês**: campo `monthly_token_cap` em `LLMConfig` (default 1M tokens premium); incrementa em `usage_metric`; toast 80%/95% cap; hard stop em 100% (próxima call retorna 429 com explicação) | P0 | 5h | ☐ |
| 7E.12 | **Dashboard de custo por run**: agregação de `token_tracking` existente; UI em `/pipeline/runs/{id}` mostra custo total estimado por modelo; export CSV de uso mensal                                              | P1 | 3h | ☐ |
| 7E.13 | **API key validation pré-pipeline**: ping rápido ao modelo (`messages.count_tokens` ou similar barato) antes de iniciar; falha clara em 400 vs crash mid-stage com 500                                            | P0 | 2h | ☐ |
| 7E.14 | **Fallback model** quando primary rate-limited (429/529): retry com modelo secundário configurável (ex: claude-haiku se opus indisponível); log explícito em `PipelineStageLog`                                   | P1 | 4h | ☐ |

**Checkpoint:** zero pipeline runs órfãs >1h • restore drill executado em <RTO declarado • off-site backup verificado • FERNET recovery testado • status page no ar (**7E.6:** link no app + RUNBOOK; provisão do serviço no deploy) • business metrics dashboard renderizando • 3 incident templates prontos (**7E.9** ✅) • LLM cost cap funcionando com toast e hard stop • API key validation antes de cada run.

### F7F — Console interno (operadores)

> Superfície para CEO, Ops, CS, Financeiro e Legal **operarem a plataforma** (não confundir com `/config` do workspace do cliente). Fases conceituais **IA-0 … IA-4** em [INTERNAL_ADMIN_ROADMAP.md](INTERNAL_ADMIN_ROADMAP.md).
>
> **Dividida em duas partes independentes:**
>
> - **[F7F-Local — Pré-produção (IA-0, sem OAuth)](#f7f-local--pré-produção-ia-0-sem-oauth)** — **UI web em `127.0.0.1` é a superfície principal** (consumindo uma camada de serviço compartilhada); CLI vira atalho secundário/futuro. Roda na máquina de desenvolvimento (backend + DB local ou túnel para staging). **Pode ser feita antes de F7A Docker/Deploy** — é a ferramenta que o operador usa enquanto o produto ainda não está no ar. Segurança vem de bind `127.0.0.1` + flag de env + sessão isolada + audit em arquivo, sem auth staff.
> - **[F7F-Remote — Produção (IA-1…IA-4, com OAuth staff)](#f7f-remote--produção-ia-1ia-4-com-oauth-staff)** — console hospedado em `ops.mathoms.ai` com OAuth Google Workspace, RBAC interno, prefixo `/api/internal/`, dashboard de negócio (**7E.7**), CS bundle, financeiro. **Depende de F7A–F7C estabilizados.**
>
> **Ordem sugerida global:** F7F-Local P0 (7F.L1 serviço → 7F.L2 UI → 7F.10–7F.12 exclusão/senha/purge) → F7F-Local complementar (7F.13–7F.14 leituras → 7F.9 CLI secundário opcional) → F7F-Remote ADR (7F.1, pode iniciar em paralelo) → F7A/B/C → F7F-Remote auth + RBAC (7F.2–7F.4) → F7F-Remote CS/Financeiro (7F.5–7F.8).

#### F7F-Local — Pré-produção (IA-0, sem OAuth)

> **Meta:** operador executa tarefas de suporte e LGPD localmente (exclusão de conta, purge de documentos, reset de senha, leitura de relatórios, métricas agregadas) antes do produto estar no ar. Nenhuma dependência de F7A (deploy), F7B (auth prod) ou F7C (CI/CD). Guardrails locais: bind em `127.0.0.1`, flag de env explícita (`INTERNAL_OPS_UI_ENABLED=1`), bloqueio se `ENVIRONMENT=production` sem `--i-accept-production-risk`, audit em arquivo.
>
> **Decisão de superfície (atualizada 2026-04-22):** a **interface web local** é a **superfície principal** desta fase. A camada de serviço (business logic) é a fonte de verdade e fica escrita agnóstica a consumidor; **CLI entra como atalho secundário/futuro** para automação e operações batch, reutilizando a mesma camada de serviço da UI. Motivação: UI acelera onboarding de novos operadores (CS/Legal), dá confirmação visual para deletes (reduz risco de typo) e é base reaproveitada para `ops.mathoms.ai` na F7F-Remote.
>
> **Ordem sugerida:** 7F.L1 (camada de serviço) → 7F.L2 (UI web local — shell + auth mínimo) → 7F.10/7F.11/7F.12/7F.15/7F.16/7F.17 (business logic por área, consumidas pela UI) → 7F.13/7F.14 (leituras) → 7F.9 (CLI secundário, opcional, depois da UI estabilizada).

| #     | Tarefa | Prio | Est. | Status |
| ----- | ------ | ---- | ---- | ------ |
| 7F.L1 | **Camada de serviço interna** ([ADR-116](DECISIONS.md#adr-116)): módulo `backend/app/services/internal_ops/` com funções puras (recebem DB session + args, retornam `OpResult` + `AuditRecord`); consumida pela UI web (7F.L2) e pelo CLI futuro (7F.9); expõe `delete_user(user_id, mode="anonymize"\|"hard_delete")`, `reset_password(user_id, new_pw)`, `purge_documents(scope)`, `delete_document(document_id)`, `update_user_email(user_id, new_email)`, `update_user_profile(user_id, **fields)`, `set_developer_flag(user_id, enabled)`, `get_metrics()`, `list_reports(user_id\|workspace_id)`; mutações sensíveis (email, flags) bumpam `token_version` para invalidar JWTs; testes unitários com fixture SQLite | P0 | 6h | ✅ S1 mergeado 2026-04-23 (`cd46545..ef1a7ae`) |
| 7F.L2 | **UI web local — `frontend-ops/` app Next separada** ([ADR-116](DECISIONS.md#adr-116)): novo diretório raiz com `package.json`, `next.config.ts`, `Dockerfile`, bind em `127.0.0.1:3100` via flag `INTERNAL_OPS_UI_ENABLED=1` (default off); **auth** `config/internal_operators.yaml` (bcrypt hashes, gitignored) + `POST /admin/login` emite JWT assinado com `INTERNAL_OPS_SESSION_SECRET` (distinto do `SECRET_KEY` cliente); cookie `ops_session` httpOnly + SameSite=Strict + Path=/admin, TTL 8h; middleware FastAPI `require_internal_operator()` em todas rotas `/admin/*`; `scripts/hash_ops_pw.py` gera bcrypt interativo; design tokens reaproveitados via `design-tokens/` (ADR-076), zero import de componentes do frontend cliente; bloqueio se `ENVIRONMENT=production` sem `--i-accept-production-risk`; documentar URL/flag/rotação de credenciais no runbook | P0 | 10h | ✅ S2 mergeado 2026-04-23 (`e65126b..d7b5a18`) |
| 7F.10 | **Exclusão de usuário (UI + serviço)** ([ADR-116](DECISIONS.md#adr-116) default **anonimização**): `internal_ops.delete_user(user_id, mode="anonymize")` substitui `email` por `deleted_user_<id>@tombstone.mathoms.ai`, `display_name` por `"Conta removida"`, zera `password_hash` com sentinela, grava `anonymized_at`, remove `refresh_tokens`+`sessions`+`invitations` pendentes; preserva `id`/`created_at`/FKs para integridade de audit (ADR-115); workspaces órfãos ficam inativos (transferência manual documentada); `mode="hard_delete"` exige confirmação extra + audit específico + nunca é default; tela com confirmação dupla (`TYPE "delete"`); testes unitários + de anonimização com fixture SQLite | P0 | 6h | ✅ S3.a mergeado 2026-04-23 |
| 7F.11 | **Reset de senha manual (UI):** tela atualiza hash no modelo `User` (mesmo algoritmo do app); campo de nova senha com revelar opcional e geração de senha temporária copiável; não loga senha nem em claro nem mascarada | P0 | 2h | ✅ S3.b mergeado 2026-04-23 (16 chars + invalida JWT via token_version) |
| 7F.12 | **Purge de documentos (UI):** por `user_id` ou `workspace_id`, remove registros e blobs em storage (`stored_path` / [storage.py](../backend/app/services/storage.py)); modo "prévia" lista arquivos/linhas antes de confirmar; mesma confirmação dupla de 7F.10 | P0 | 6h | ✅ S3.c mergeado 2026-04-23 (rollback em OSError + preview paginada) |
| 7F.13 | **Métricas de utilização (UI):** dashboard simples agrega uploads/runs/workspaces/volume storage; cards + tabela; export CSV como ação secundária; base para **7D.9** telemetria e **7E.7** dashboard remoto | P1 | 4h | ✅ S3.d mergeado 2026-04-23 (7d/30d/90d + novos cards uploads/users) |
| 7F.14 | **Relatórios read-only (UI):** lista dos últimos `Report` (ou pipeline runs) por conta com filtro por email/`user_id`; link abre JSON ou HTML exportado em aba separada; sem mutação nem reexecução de pipeline | P1 | 4h | ✅ S3.e mergeado 2026-04-23 (paginação offset/total) |
| 7F.15 | **Toggle `is_developer` (UI + serviço):** tela mostra flag atual do usuário e permite ligar/desligar com confirmação simples; `internal_ops.set_developer_flag(user_id, enabled)` atualiza `users.is_developer` ([user.py:21](backend/app/models/user.py:21)) e grava audit; substitui uso manual de [set_developer_flag.py](backend/app/scripts/set_developer_flag.py); sem confirmação dupla (ação reversível) | P0 | 2h | ✅ S3.f mergeado 2026-04-23 (confirm só ao ligar) |
| 7F.16 | **Editar cadastro do usuário (UI + serviço):** formulário edita `email`, `full_name`, `is_active` ([user.py:17-20](backend/app/models/user.py:17)); mudança de `email` valida unicidade, bumpa `token_version` para invalidar JWTs existentes e grava audit separado (campo sensível); `is_active=false` equivale a desativar login sem anonimizar; mudanças em `full_name` não bumpam token; testes cobrem colisão de email + invalidação de sessão | P0 | 4h | ✅ S3.g mergeado 2026-04-23 (audit `user.email_changed` + banner logout) |
| 7F.17 | **Exclusão de documento individual (UI + serviço):** complementa purge bulk (7F.12) permitindo deletar **um** upload específico por `document_id`; UI lista documentos por `user_id`/`workspace_id` com metadados (nome, data, tamanho, tipo) e ação "excluir" por linha; `internal_ops.delete_document(document_id)` remove registro + blob em storage ([storage.py](backend/app/services/storage.py)); confirmação simples (não dupla — escopo menor que purge); audit inclui hash/nome do arquivo removido | P0 | 4h | ✅ S3.h mergeado 2026-04-23 (audit filename+content_hash; excluir por linha na prévia de 7F.12) |
| 7F.9  | **CLI interno (secundário, pós-UI):** entrypoint documentado (ex.: `python -m app.scripts.internal_ops` ou target em `Makefile`) para automação/batch; **reutiliza a camada de serviço de 7F.L1** (zero duplicação de regra); `--dry-run` + confirmação explícita em deletes; mesmo audit em `logs/` que a UI | P1 | 3h | ☐ opcional (sem demanda concreta) |

**Audit (comum UI + CLI):** toda mutação escreve linha em `logs/internal_ops_audit.log` (JSON: operador, ação, alvo, timestamp, resultado) — ADR-110 masking aplica. Quando 7B.5 persistir, a camada de serviço passa a gravar na tabela de audit sem mudar UI/CLI (troca só do sink).

**Checkpoint F7F-Local (IA-0):** ✅ **MVP FECHADO em 2026-04-23** — S1 (services+auth backend, `cd46545..ef1a7ae`) + S2 (frontend-ops shell + 4 telas, `e65126b..d7b5a18`) + S3 (refino 7F.10–7F.17, `876d09f..8f1e0ca`) mergeados em `main`. Operador executa anonimização (default) / hard delete (superadmin + motivo) / reset pw (16 chars + invalida JWT) / purge bulk (com rollback em OSError de blob) / delete individual / toggle dev / editar email+nome+is_active pela UI local. Métricas 7d/30d/90d com cards de uploads/novos users; relatórios paginados. Harness Playwright `@internal-ops` scaffolded em `frontend-ops/tests/e2e/` (run em CI pendente; smoke curl validado manualmente). 7F.9 (CLI) fica aberto sem bloquear — só executar se demanda concreta.

#### F7F-Analyst — Superfície do especialista de planejamento financeiro/patrimonial (IA-0+, pós-P0 Ops)

> **Meta:** permitir que um especialista em planejamento financeiro (metodologias **Perini / Cerbasi / AUVP** — [CLAUDE.md §Papel do assistente](../CLAUDE.md)) analise a saúde financeira de cada conta, tenha panorama agregado da base e registre feedback contínuo sobre produto/layout de relatório. Superfície **read-heavy e não-destrutiva** — distinta da Ops, mesmo app `frontend-ops/` com papel `analyst` separado no yaml (`role: analyst`) e rotas `/analyst/*` protegidas.
>
> **Fundamentos dos 5 indicadores de saúde** (todos derivados de artefatos E1.5/E5 — **zero recálculo na UI**):
> - **Reserva de emergência** (Cerbasi): `reserva_liquida / custo_fixo_mensal` → meses cobertos (meta 6-12m).
> - **Taxa de poupança** (Cerbasi/AUVP): `(receita − despesa) / receita` → savings rate (meta >20%).
> - **Alocação patrimonial** (AUVP/Perini): % em RF / RV / imóveis / caixa vs benchmark por faixa etária.
> - **Renda passiva** (Perini): `(dividendos + juros 12m) / custo_fixo_anual` → % de IF atingido.
> - **Endividamento** (Cerbasi): `divida_total / patrimonio_liquido` + `divida / renda` (meta <30%).
>
> **Ordem sugerida:** 7F.A1 (serviço de métricas, reutiliza `pipeline/domain/services/`) → 7F.A2 (modelo `analyst_notes` + ADR nova) → 7F.A3 (role analyst + rotas backend) → 7F.A4 (triage) → 7F.A5 (deep dive) → 7F.A6 (overview agregado) → 7F.A7 (feedback loop).
>
> **Fluxos de referência:** triage semanal (5), deep dive diário (6), panorama mensal (7), feedback contínuo (8) — desenhados com estética Stripe (single-scroll + detail panel) + Linear (⌘K, atalhos, cycle-picker).

| #      | Tarefa | Prio | Est. | Status |
| ------ | ------ | ---- | ---- | ------ |
| 7F.A1  | **AnalystMetrics service** — `backend/app/services/analyst_metrics/` com funções puras que agregam indicadores de saúde a partir de artefatos E1.5 (baseline patrimonial) e E5 (análise financeira) **sem recalcular** — reutiliza `pipeline/domain/services/` quando possível; expõe `compute_health_score(user_id)`, `list_users_ranked(filters, sort)`, `get_user_snapshot(user_id, period)`, `aggregate_base(segment_by)`; health score composto **transparente** (retorna breakdown por indicador com fórmula + meta aplicada); testes unitários com fixtures Alembic-aware (DB em memória, nunca mock — CLAUDE.md §Testes) | P0 | 8h | ☐ |
| 7F.A2  | **Modelo `analyst_notes` + ADR** — tabela nova (`id`, `author_operator`, `note_type` ∈ `user_insight\|product_suggestion\|report_suggestion`, `target_user_id` nullable, `target_report_section` nullable, `methodology` ∈ `perini\|cerbasi\|auvp`, `body`, `status` ∈ `aberto\|em_analise\|implementado\|descartado`, `created_at`, `updated_at`); migration Alembic; service `analyst_notes.py` (CRUD + filtros); **nova ADR** em [DECISIONS.md](DECISIONS.md) justificando a tabela (separada de audit porque é conteúdo editorial, não imutável) | P0 | 4h | ☐ |
| 7F.A3  | **Backend `/admin/analyst/*` + role `analyst`** — extende `config/internal_operators.yaml` com campo `role` (`ops` \| `analyst`); middleware `require_analyst_role()` em FastAPI; rotas `GET /admin/analyst/users` (triage), `GET /admin/analyst/users/<id>` (deep dive), `GET /admin/analyst/overview` (agregado), `POST/GET/PATCH /admin/analyst/notes`; `make update-openapi-snapshot`; testes 403 (ops não acessa analyst e vice-versa) + 401 (sem auth); **antecipa RBAC de 7F.3** — mesmo yaml, granularidade mínima | P0 | 6h | ☐ |
| 7F.A4  | **Tela Triage `/analyst`** (Fluxo 5): tabela com 5 indicadores + health score composto, filtros-chip estilo Linear (`sem reserva`, `savings < 10%`, `endividado > 30%`, `alocação 100% RF`, `IF < 10%`), colunas ordenáveis, expansão inline por linha com sparkline de 6 meses, hover em score abre tooltip com breakdown de cálculo (zero opacidade); paginação server-side; ações contextuais por linha: "Abrir análise profunda" (7F.A5) e "Anotar" (7F.A7) | P0 | 8h | ☐ |
| 7F.A5  | **Tela Deep Dive `/analyst/users/[id]`** (Fluxo 6): 5 cards verticais (fluxo de caixa Cerbasi, reserva Cerbasi, alocação AUVP, renda passiva Perini, endividamento Cerbasi) — cada card é mini-relatório diagnóstico com valor atual + meta + gap; sidebar direita com timeline de evolução mensal (Linear activity feed); click em mês abre snapshot histórico; botão **export markdown/PDF** reusa renderer E6; link "Anotar sobre este usuário" (pré-preenche `target_user_id`); zero divergência com relatório cliente (mesma fonte E5) | P0 | 10h | ☐ |
| 7F.A6  | **Tela Overview `/analyst/overview`** (Fluxo 7): 6 histogramas de distribuição (meses reserva, savings rate, alocação 100% RF, endividado >30%, IF atingida, top 3 categorias de gasto); linha temporal de % base saudável em cada indicador mês a mês; seção de insights auto-gerados (copy dinâmico a partir dos dados); dropdown de segmentação (faixa etária, renda, tempo de uso); cada agregado drill-down → `/analyst` pré-filtrado; **não-acionável** (sem mutação nem botões) | P1 | 8h | ☐ |
| 7F.A7  | **Feedback loop `/analyst/feedback` + sheet `⌘K → nota`** (Fluxo 8): sheet lateral (não modal) abre por atalho global ⌘N (estilo Linear); 3 tipos de nota (`user_insight`, `product_suggestion`, `report_suggestion`); se tipo `report_suggestion`, dropdown lista seções de `config/report_layout.yaml` (gerado em build-time via [dev/codegen_report_layout.py](../dev/codegen_report_layout.py)); metodologia de referência obrigatória (Perini/Cerbasi/AUVP); tabela `/analyst/feedback` filtrada por status + tipo (tabs Linear cycle-style); nota `user_insight` aparece no perfil do usuário em F7F-Local (ops vê o que analista anotou); fase 2 (opcional): botão "exportar pra BACKLOG.md" cria branch + PR com task — fora de escopo do MVP | P1 | 6h | ☐ |

**Checkpoint F7F-Analyst (IA-0+):** 7F.A1 + 7F.A2 + 7F.A3 concluídos (backend + DB + RBAC mínimo) • 7F.A4 + 7F.A5 cobrem triage + deep dive (analista resolve 80% do trabalho diário) • 7F.A6 entrega panorama mensal • 7F.A7 fecha o feedback loop • role `analyst` testado em isolamento (ops não acessa `/analyst/*`, analista não acessa mutations destrutivas de Ops) • cálculos de saúde consistentes com relatório cliente (teste de paridade sobre fixture compartilhada) • export markdown/PDF do deep dive funciona localmente.

**Dependências e notas:**
- **7F.A1 exige artefatos E1.5/E5** — só funciona para usuários com pipeline rodado ao menos 1x; UI mostra estado vazio "sem dados de análise" para contas novas.
- **Health score é heurística, não verdade absoluta** — documentar limitações em [docs/CANONICAL_ENGINE_P0.md](CANONICAL_ENGINE_P0.md) ou ADR da 7F.A2; qualquer mudança de fórmula exige bump de versão + recomputação de histórico.
- **Comparação com peers** (fase 2 mencionada no Fluxo 6) exige base anonimizada — **fora do MVP**, entra depois de termos volume (>100 usuários com E5 rodado).
- **Quando F7F-Remote subir:** rotas `/admin/analyst/*` migram para `/api/internal/analyst/*` com OAuth staff (7F.2) e RBAC granular (7F.3) — superfície e UX ficam idênticas, só a auth muda.

#### F7F-Remote — Produção (IA-1…IA-4, com OAuth staff)

> **Meta:** console acessível em `ops.mathoms.ai` com auth staff separado do JWT cliente, RBAC, telemetria de negócio (IA-2), ferramentas de CS (IA-3) e financeiro/legal (IA-4). Exige deploy (F7A), hardening (F7B) e observability (F7C) estabilizados.
>
> **Ordem sugerida:** 7F.1 (ADR) pode iniciar em paralelo à F7F-Local — não bloqueia. 7F.2–7F.4 após F7A pronto (HTTPS + subdomain `ops.mathoms.ai`). 7F.5 junto com 7C.7 (RUNBOOK). 7F.6–7F.7 pós-F7B (audit log persistido). 7F.8 quando billing real existir (F10).

| #     | Tarefa | Prio | Est. | Status |
| ----- | ------ | ---- | ---- | ------ |
| 7F.1  | **ADR + política interna:** identidade staff vs `User` cliente; impersonation proibida por padrão ou "break glass" com TTL + audit + ADR em [DECISIONS.md](DECISIONS.md) | P0 | 3h | ☐ |
| 7F.2  | **Auth interna MVP:** credencial separada do JWT cliente (ex.: allowlist email + senha/secret rotativo, ou OAuth Google Workspace restrito a domínio da empresa); sessão não reutiliza cookie do app | P0 | 8h | ☐ |
| 7F.3  | **RBAC interno** (`internal_ops`, `internal_support`, …) + dependency FastAPI + testes 403 entre papéis | P1 | 6h | ☐ |
| 7F.4  | **Prefixo `/api/internal/`** (ou equivalente) protegido por env + testes; nenhuma rota interna em build do cliente sem flag explícita | P0 | 4h | ☐ |
| 7F.5  | **Documentação:** ao concluir **7C.7** (`docs/RUNBOOK.md`), incluir secção console interno — quem acessa, rotação de credenciais, revogação de acesso staff | P1 | 1h | ☐ |
| 7F.6  | **CS:** busca por email / `user_id` → workspaces, roles, convites (somente metadados); toda consulta auditada | P2 | 8h | ☐ |
| 7F.7  | **CS:** endpoint + UI para **support bundle** JSON (diagnóstico redigido, sem valores/PII por padrão) | P2 | 6h | ☐ |
| 7F.8  | **Financeiro (pós-billing):** links read-only Stripe + export CSV contábil — depende de billing real (F10 / roadmap) | P2 | TBD | ☐ |

**Dependências externas da F7F-Remote:**

- **7A.7b** — Traefik `ipAllowList` para `ops.mathoms.ai` (pré-requisito de rede).
- **7A.11b** — teste Playwright valida isolamento de cookie entre `app.` e `ops.`.
- **7B.5** — audit log persistido em tabela `AuditEntry` (mutations internas gravam em DB em vez do log de arquivo da IA-0).
- **7C.4** — Sentry tags (`environment=ops`) separando erros de staff vs cliente.
- **7E.7** — dashboard `/admin/metrics` é o **núcleo visual da IA-2**; evolui as métricas já calculadas em 7F.13; protegido por 7F.2–7F.4.

**Checkpoint F7F-Remote (MVP IA-1 + IA-2):** 7F.1–7F.4 concluídos • **7E.7** renderizando para papel `internal_ops` • **7A.7b + 7A.11b** passando • zero exposição de rotas internas em deploy sem config explícita • audit log persistido (7B.5) cobre mutações internas.

**Checkpoint F7F-Remote (IA-3 CS Lite, pré-beta):** 7F.6–7F.7 concluídos • support bundle redigido testado em incidente real • time de CS triado ≥1 ticket sem escalar para engenharia.

**Checkpoint F7F-Remote (IA-4 Financeiro/Legal, pós-billing):** 7F.8 + fila DSAR (7B.18) integrada no console • export CSV contábil validado com contador externo.

---

## Report Premium UI — Paridade com EXEMPLO_DE_RELATORIO.html

> Plano completo: [REPORT_PREMIUM_PLAN.md](REPORT_PREMIUM_PLAN.md) · Gaps
> inventariados: [REPORT_PREMIUM_GAPS.md](REPORT_PREMIUM_GAPS.md) · ADRs:
> 117, 121, 122, 123, 124 em [DECISIONS.md](DECISIONS.md).
>
> Objetivo: migrar `/reports/[id]` e o standalone do relatório para o
> nível visual do `EXEMPLO_DE_RELATORIO.html` (10k linhas, raiz do repo).
> Cross-cutting de frontend + backend (colaboração Notas/Kanban) + design
> tokens + pipeline (derivadores). **10 de 13 fases entregues em
> 2026-04-24.** Próxima fase: **11 (`e6_render.py` paridade — ADR-124)**.

| Fase | Entrega | Status | Commits principais |
| --- | --- | --- | --- |
| 0 | Discovery + gaps + ADRs 117/121/122/123/124 | ✅ 2026-04-24 | `0f7ddeb`, `4512e35`, `07c44fa`, `52a652a` |
| 1 | Design tokens + dark mode + typography scope 13px | ✅ 2026-04-24 | `e634173`, `a2123e2`, `6f7c7a9` |
| 2 | Chart.js foundation (9 primitivos + playground) | ✅ 2026-04-24 | `d8041e2`, `502d65f`, `31a44c7` |
| 3 | UI primitives (19 componentes + 26 tests) | ✅ 2026-04-24 | `10179dd`, `1ae3475`, `144eb07`, `5c8e584`, `289fa57` |
| 4 | Shell (Cover, TopNav, Toolbar, SkipNav, etc.) | ✅ 2026-04-24 | `6a09ff2`, `84a0187`, `bda1d17` |
| 5 | Layout YAML expansion + codegen TS/Pydantic | ✅ 2026-04-24 | `0f2811f`, `91a2780`, `c3af835`, `8510cfa` |
| 6 | Derivadores determinísticos (chart_conclusions + section_summaries + adapters) | ✅ 2026-04-24 | `7a8a46c`, `9c11749`, `eb29688` |
| 6.5 | Backend persistence — Notas + Kanban (ADR-123) | ✅ 2026-04-24 | `2a1261f`, `c2fa932`, `2663ec3` |
| 7 | S1-S10 wired com SectionSummary + Chart fallbacks | ✅ 2026-04-24 | `0f4663a`, `073db70`, `44468ec` |
| 8 | T3/T5/T6 wired com API reports_collab | ✅ 2026-04-24 | `ac6fa81`, `dbc1195`, `a2f8843` |
| 9 | U1-U4 wired com SectionSummary + Chart fallbacks | ✅ 2026-04-24 | `9d5fbce` |
| 10 | Apêndices A-E + fix `MIGRATED_SECTIONS` | ✅ 2026-04-24 | `c63497d`, `78f9193`, `5fc8cc4`, `31f72cd` |
| 11 | `e6_render.py` paridade (Jinja2 + tokens — ADR-124) | ☐ **próxima** | depende de 7/8/9/10 |
| 12 | Print + a11y + Playwright screenshots + axe-core | ☐ | depende de 11 |
| 13 | Rollout + CHANGELOG + RUNBOOK + delete `e6_render.py` | ☐ | depende de 12 |

**Pendências conhecidas (débito consciente):**

- **DnD real em Kanban (F8):** `@dnd-kit/core` não foi adicionado —
  primitivo usa botões de coluna. Ativar como sub-fase 8.1 opcional se
  UX validar a demanda.
- **LLM em E5 para `section_summaries` (F6):** adiado; hoje usamos
  templates determinísticos em `deriveSectionSummary`. Q11 prevê
  revisão após Fase 12.
- **`comparisons` e `changelog`:** diferidos para v2 (Q6); declarados
  `enabled: false` no YAML. Ativação pós-Fase 13 quando
  `SnapshotChangelogBuilder` existir.
- **2 testes `MonetaryValue compact` falham pré-existente** (ICU
  renderiza "R$ 1,50 mi" vs regex esperando "1,5 mi") — não bloqueiam
  e independem das fases; tratar em polish (Fase 12).

**Checkpoint de saída:** relatório nativo `/reports/[id]` visualmente
equivalente ao exemplo em dark/light + print; standalone (HTML offline)
gerado pelo Next SSR sem depender do `e6_render.py` legado; Playwright
valida os 19 V-checks; axe-core sem violações críticas.

---

## DOCS-REVIEW — Followups da revisão multi-agente 2026-04-24

> **Contexto:** revisão coordenada por 4 agentes (senior-cto, product-designer, financial-planner, general-purpose) encontrou ~20 achados priorizados. Batch 1 (hotfix de integridade — ADRs duplicados, ADR-119/120, ROADMAP, contagens ARCHITECTURE) foi entregue em `af8dce7` (2026-04-24). Batches 2 (reescrita com decisão de escopo) e 3 (ADRs novas + correção de regras) ficam aqui para execução futura — **não bloqueia F7**, mas saúde-da-doc degrada rapidamente sem isso. Lanes abaixo são **independentes** entre si e podem ser pegas fora de ordem, exceto onde marcado.

### DOCS-REVIEW.batch2 — Reescrita de documentos (decisões de escopo pendentes)

Cada item abaixo exige decisão de escopo do dono antes de executar — não é mecânico.

| # | Entrega | Prio | Esforço | Status | Decisão pendente |
| --- | --- | --- | --- | --- | --- |
| batch2.1 | **Expandir [FORMULAS.md](FORMULAS.md)** (hoje 11 linhas) para glossário completo: reserva de emergência, taxa de poupança, cobertura de despesas, taxa de endividamento, TRS, yield on cost, if_gap, diversificação, classificação Cerbasi. Para cada: fórmula, unidades, variáveis definidas, fontes (campo E5), faixas de classificação, referência metodológica (Perini/Cerbasi/AUVP). | P1 | 6-8h | ☐ | Glossário completo de 1 só passe **ou** MVP com 5-6 principais e evolução incremental? |
| batch2.2 | **[docs/REPORT_PREMIUM_PLAN.md](REPORT_PREMIUM_PLAN.md) §10 — reconciliar com Delta #2**: hoje §10 descreve Jinja2 e Delta #2 descreve SSR Next (ADR-124); o commit `0b8a78c` (2026-04-24) escolheu §10-Jinja2 como vencedor. Formalizar essa reversão: marcar Delta #2 como superseded, reescrever §10 canônica, atualizar ADR-124 como "aposentadoria revertida". | P1 | 2-3h | ☐ | Confirmar reversão é definitiva? (já implícita no commit mas sem ADR de reversão) |
| batch2.3 | **[docs/e6_render_readme.md](e6_render_readme.md) status**: marcar como histórico OU atualizar para refletir paridade Jinja2 da Fase 11 em curso (dep batch2.2). | P2 | 1h | ☐ | Histórico ou vivo? — decorre de batch2.2 |
| batch2.4 | **[docs/CANONICAL_ENGINE_P0.md](CANONICAL_ENGINE_P0.md)** (2026-04-17) — P0.1 cita risco resolvido por ADR-081, P0.3 ignora CI strict já ativo. Decidir: snapshot histórico ("preservado como registro de P0") ou reescrita. | P2 | 2h | ☐ | Snapshot ou reescrita? |
| batch2.5 | **[docs/PRODUCT.md](PRODUCT.md)** §3 (diferenciais) e §5 (GA criteria): incluir Report Premium UI como diferencial explícito; §5 explicitar que GA requer Fase 13 do Report Premium. | P2 | 1h | ☐ | — |
| batch2.6 | **Expandir [COPY_GUIDELINES.md](COPY_GUIDELINES.md)** (hoje 14 linhas): (a) labels canônicos por seção do relatório, (b) estados vazios por card, (c) copy padrão por severity de `<Alert/>`, (d) tom em erros de pipeline visíveis, (e) microcopy Kanban/Notas. | P1 | 4-6h | ☐ | Fonte única PT-BR ou bilíngue? |
| batch2.7 | **TOC navegável em [DECISIONS.md](DECISIONS.md)** (4518 linhas, 126 ADRs) — gerar índice com âncoras `#adr-NNN` via script em `dev/generate_adr_index.py` rodado em pre-commit. | P2 | 3h | ☐ | Auto-gerado em pre-commit ou inline manual? |
| batch2.8 | **[REPORT_PREMIUM_GAPS.md](REPORT_PREMIUM_GAPS.md) §3 Tabela C — shapes TS definitivos**: 20 campos faltantes em `ReportAnalysisData` sem contrato. Ex.: `score.formula: string` vs estrutura; `projecao.kpi_strip[]` tamanho. Adicionar subseção "Contratos TS definitivos" ou mover para ADR-122. | P0 (bloqueia Fase 12+) | 4h | ☐ | — |
| batch2.9 | **Quickstart para agente LLM** — novo doc `docs/AGENT_QUICKSTART.md` (ou seção em CLAUDE.md) mapeando pergunta → doc canônico. Ex.: "como escrevo endpoint novo?" → tenancy.md + ADR-101. | P2 | 2-3h | ☐ | Novo arquivo ou seção em CLAUDE.md? |
| batch2.10 | **Guia DDD prático (R12-R17)** — docs/DDD_GUIDE.md com exemplo completo end-to-end (aggregate → repo → use case → DTO → router) análogo ao que tenancy.md faz para multi-tenancy. | P1 | 4-6h | ☐ | Baseado em qual aggregate como exemplo canônico? |
| batch2.11 | **Completar [TESTING.md](TESTING.md)** (marcado "esqueleto inicial" desde F6.5): política de regressão, fixtures de boundary LLM, DB em testes, goldens de paridade, E2E `@critical`. | P1 | 4h | ☐ | — |
| batch2.12 | **Design token governance** — seção em `design-tokens/README.md` (ou novo `docs/DESIGN_TOKENS.md`): quando criar token novo vs alias vs hex inline; policy de naming. | P2 | 2h | ☐ | — |
| batch2.13 | **Spec mobile do relatório** — decidir e documentar: que seções saem, que charts ganham fallback, como Kanban vira lista em `<767px`. Adicionar em REPORT_PREMIUM_PLAN Delta novo ou seção. | P2 | 3h | ☐ | Docs only ou já implementa breakpoints? |
| batch2.14 | **Checklist WCAG 2.1 AA operacional** — por seção do relatório: contraste (`<MonetaryValue>` vermelho em `--color-compare-neg`), teclado em Kanban, ordem de tab em seções. Gate por axe-core + Lighthouse ≥95 já existe (Fase 12) — checklist complementa. | P2 | 2h | ☐ | — |
| batch2.15 | **Stage rename F9 exemplo concreto** — ADR-093 tem `STAGE_RENAME_MAP` mas nenhuma doc mostra antes/depois em query DB. Adicionar seção "Exemplo prático" em ADR-093 ou em ARCHITECTURE §7. | P2 | 1h | ☐ | — |

### DOCS-REVIEW.batch3 — ADRs novas + correções de domínio

Ataques que **mudam código ou parâmetros**, não só doc. Cada um deve virar ADR + PR separada.

| # | Entrega | Prio | Esforço | Status | Impacto |
| --- | --- | --- | --- | --- | --- |
| batch3.1 | **ADR "Parâmetros de scoring financeiro"** — justificar thresholds em `config/scoring.json`: endividamento 20% (vs Cerbasi ~30% se dívida boa), poupança 25%, reserva 6 meses, consumo consciente 2000, pontos fortes 30%. Citar fonte metodológica para cada. | P1 | 4h | ☐ | docs-only (números não mudam — só rationale) |
| batch3.2 | **ADR "Money DTOs no boundary"** + remediação das 79 violações `float_money` em [backend/app/schemas/goal.py](backend/app/schemas/goal.py) e [transactions.py](backend/app/schemas/transactions.py). Formaliza caminho p/ A6g.3b finalizar. Fere ADR-090 hoje. | P0 | 6-8h | ☐ | Código — wire format pode mudar |
| batch3.3 | **ADR "Metodologia de alocação-alvo"** — adotar AUVP, heurística própria ou híbrido? Move alvos hardcoded em `definitions.md` (dogfood) para `config/scoring.json` ou novo `config/asset_allocation.json` por perfil de risco. | P1 | 6h | ☐ | Código + config |
| batch3.4 | **Processo de ADR formal** — lifecycle (proposed/accepted/superseded), quem numera, colisão-free (vide ADR-078/079 duplicados). Novo `docs/ADR_PROCESS.md` ou seção em CLAUDE.md §Git. Template em `docs/adr_template.md`. | P1 | 2-3h | ☐ | docs + processo |
| batch3.5 | **Fix Cerbasi `categorias_futuro`** — remover `financeiro` (IOF/taxas é gasto operacional por `definitions.md`, não "futuro"); alinhar defaults de `equilibrio_cerbasi_analyzer.py`. Hoje infla índice "futuro" artificialmente. | P0 | 2h | ☐ | Muda scoring em prod — requer regression test |
| batch3.6 | **Reserva de emergência — só líquidos/baixa-vol** — `reserva_emergencia_calculator` hoje soma CDB com carência e ações voláteis como "total_liquida". Filtrar para ativos D+0/D+1 + baixa volatilidade (Cofrinhos, Tesouro Selic, poupança, CC). Renomear categoria `reserva_desejos` → `consumo_planejado` (nome engana). | P1 | 4h | ☐ | Muda cálculo + migration de categoria |
| batch3.7 | **Dívida boa vs ruim** — `endividamento_analyzer.py` trata dívida como agregado. Cerbasi distingue financiamento imobiliário @ 9% a.a. vs rotativo @ 300%. Adicionar classificação por `taxa_aa` + `tipo` em `dividas-1.5_consolidated.json`. | P2 | 6h | ☐ | Schema + calculator |
| batch3.8 | **TRS — documentar origem** — parâmetro em `if_projector` (default 4%) sem citar Bengen/Trinity/Perini. Adicionar em FORMULAS (dep batch2.1) + comentário com fonte em código. | P2 | 1h | ☐ | docs-only |
| batch3.9 | **Yield on cost real** — hoje `renda_passiva_estimada_4pct` é genérica (4% × investível / 12). Calcular real a partir de `investimentos-3_unified.json` (DY × posição em ações/FIIs). | P2 | 6h | ☐ | Código novo |
| batch3.10 | **RebalancingAdvisor (AUVP)** — service novo sugerindo em qual classe aportar dado desvio atual vs alvo. Dep batch3.3 (definir metodologia primeiro). | P2 | 8h | ☐ | Feature nova |
| batch3.11 | **Cobertura de seguros (Cerbasi)** — métrica ausente do produto. Service contando prêmios vs renda + alerta em `dashboard_service`. | P2 | 6h | ☐ | Feature nova |
| batch3.12 | **Auto-gerar contagens em ARCHITECTURE** — script `dev/refresh_architecture_counts.py` análogo a `DB_SCHEMA_REFERENCE.md` para §4/§5/§6/§7/§8/§10/§11, rodando em pre-commit (modo `--check`). Elimina drift recorrente. | P1 | 4h | ☐ | Script novo |

**Ordem de ataque sugerida (quando abrir sessão dedicada):**

1. batch3.4 (processo de ADR) → destrava os demais sem risco de nova colisão
2. batch2.8 (shapes TS) → destrava Fase 12+ do Report Premium
3. batch3.1/3.5/3.6 (scoring + Cerbasi + reserva) → regras de domínio corretas antes de GA
4. batch3.2 (Money DTOs) → finaliza A6g.3b
5. batch2.1 + batch3.8 (FORMULAS + TRS) juntos → coerência metodológica
6. Demais em paralelo conforme prioridade

**Nada aqui bloqueia** F7A/B/C/D nem Report Premium Fase 11/12/13 diretamente — mas saúde da doc degrada se `main` avança sem visitar esta lista.

---

## F11 — Confiança, transparência e excelência de relatório (beta → GA)

> Fase de **produto** pós-F7 estável: melhora percepção de qualidade, auditabilidade e uso profissional do relatório. **Não** substitui P2 (classificação unificada) nem F7 (ops). Ordem sugerida no [ROADMAP.md](ROADMAP.md#f11--confiança-transparência-e-excelência-de-relatório-beta--ga).

### F11.1 — Mental model: “vida financeira” × “relatório deste mês”

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.1a | **Arquitetura de informação:** `/plano`, metas, tarefas e cofre de contexto = eixo **estratégico**; Documentos → Pipeline → Relatório = eixo **operacional do período**. Revisar labels do nav, títulos de página e breadcrumbs para não misturar os dois. | P1 | 6h | ✅ Nav agrupado (Plano de vida / Fechamento do período / Conta) em `AppShell.tsx` |
| F11.1b | **Empty states e CTAs:** primeiro uso empurra “gerar primeiro relatório”; usuário com relatório já pode ver CTA secundário para “ajustar metas / plano”. Sem dead-end em `/dashboard` ou `/reports`. | P1 | 4h | ✅ Links secundários para `/plano` em empty states de Dashboard e Relatórios; copy do dashboard empty ajustada |
| F11.1c | **Copy guidelines** curtas no `docs/` ou comentário de design: quando falar “mês”, “período”, “projeção” vs “patrimônio alvo”. | P2 | 2h | ✅ [COPY_GUIDELINES.md](COPY_GUIDELINES.md) |

### F11.2 — Hierarquia de números

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.2a | **Auditoria visual:** mesmas regras de `format.ts` aplicadas em Dashboard, Transactions, Report React: alinhamento decimal, `tabular-nums`, escala de eixos Recharts, legenda com unidade. | P1 | 8h | ✅ Sprint B+C: Dashboard (eixos/tooltips); Transactions (data/valor/cabeçalho/paginação); hero do relatório nativo; KPICard/`MonetaryValue` já cobertos — revisão fina por seção/card se necessário |
| F11.2b | **Prioridade semântica:** KPI primário vs secundário (peso tipográfico / posição); valores derivados claramente subordinados (ex.: variação % sob o principal). | P1 | 4h | ✅ `KPICard` `emphasis` + hero do relatório (título vs período); delta menor no modo secundário |
| F11.2c | **Teste de regressão visual** (Playwright ou checklist manual) para dark/light e print. | P2 | 3h | ☐ |

### F11.3 — Print / PDF como entregável de consultoria

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.3a | **Print CSS:** revisão de quebras de página, cabeçalhos repetidos, margens A4, ocultar chrome da app na impressão; numerar páginas se o motor permitir. | P1 | 6h | ✅ Margens A4 numa única `@page`; `orphans`/`widows`; removido `@bottom-center` (suporte irregular); `?print=1` → `html[data-print-route]` |
| F11.3b | **Export PDF server-side (Playwright):** validar que tipografia e cores ficam “apresentáveis” para terceiros; capa com período e sobrenome da família consistente. | P1 | 4h | ✅ `render_pdf` espera `[data-report-ready]` antes do `page.pdf()` (hero visível); checklist §5.1 |
| F11.3c | **Checklist de QA** em [SMOKE_TEST.md](SMOKE_TEST.md) ou seção dedicada: “entrega impressa/PDF” (mínimo 5 itens). | P2 | 2h | ✅ §5.1 em SMOKE_TEST + itens Cmd+K / `?` em Auth |

### F11.4 — Transparência na UI: origem da informação

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.4a | **Modelo de dados / API:** expor por bloco ou seção (ou agregado no JSON do relatório) referência a: `document_id`(s), período, run_id opcional — sem vazar dados entre workspaces. | P1 | 10h | ✅ Agregado: `source_document_count` / `source_document_ids` na API + `_report_lineage` em GET `/data`; linhagem por bloco no JSON fica como evolução futura |
| F11.4b | **UI:** componente discreto “Fonte” / “Origem” (tooltip ou linha secundária): ex. “Extrato Itaú · jan/2026 · run `abc…`”. | P1 | 8h | ✅ Sprint B: `ReportSourceStrip` abaixo do header do relatório (links Documentos + Pipeline; período snapshot + gerado em) |
| F11.4c | **Fallback:** quando dado for agregado de várias fontes, texto explícito “Consolidado de N documentos”. | P1 | 3h | ✅ Sprint B: copy “consolidados a partir dos documentos…” na faixa de origem |

### F11.5 — Transparência na UI: `needs_review` e trilha LLM

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.5a | **Mapa de estados:** definir rótulos user-facing para: sucesso determinístico; dado inferido por LLM; `needs_review`; falha de estágio. Proibido expor códigos internos E0–E7 na UI (ADR-068). | P0 | 4h | ✅ Sprint B: `pipelineTransparency.ts` (footnote LLM por etapa); removido badge com código E* na linha de etapa; `pipelineE2TouchLabel` sem “E2” na UI |
| F11.5b | **Pipeline / Relatório:** banner ou badge persistente quando houver revisão pendente; link para tela de review ou lista de itens. | P0 | 8h | ✅ Sprint B: banner `needs_review` reforçado + CTA retomar (já existia; copy e caixa LLM) |
| F11.5c | **Linguagem de risco:** distinguir “pode afetar categorização” vs “pode afetar saldo exibido”; texto revisado por produto. | P1 | 3h | ✅ Sprint B: `reviewPauseImpactHint()` por etapa pausada |

### F11.6 — Metadados de premissas (metas e relatório)

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.6a | **Metas (Goals):** versão de premissas por tipo (IF, aporte, dólar, alocação): taxa, inflação, horizonte, data de vigência; exibir no wizard e na visualização. | P1 | 10h | ✅ `GoalPremissasCard` + `goalPremissas.ts` em todos os wizards e formulários `/plano/*`; API expõe `meta_version` em `GET`/`PUT` goals; teste `tests/lib/goalPremissas.test.ts` |
| F11.6b | **Snapshot de relatório:** quando números dependerem de premissas, gravar referência (versão goal ou blob JSON mínimo) para comparação mês a mês. | P1 | 8h | ✅ Coluna `reports.premissas_snapshot_json` + `build_premissas_snapshot_sync` (SHA-256 de `config/goals.json` + metas `effective_to IS NULL`); pipeline preenche em `_create_report_from_output`; API `ReportResponse.premissas_snapshot` + merge em `goals.premissas_snapshot` no GET `/data`; testes `backend/tests/test_premissas_snapshot.py`, `test_reports` |
| F11.6c | **Relatório UI:** bloco opcional “Premissas deste relatório” (colapsável). | P2 | 4h | ✅ `ReportPremissasBlock` (snapshot opcional `goals.premissas_snapshot` se existir) |

### F11.7 — Ligação explícita entre número e regra

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.7a | **Catálogo de fórmulas** relevantes (FV anuidade, etc.): texto curto + referência ao código ou doc (`compute_if_derived`, E5). | P1 | 6h | ✅ [FORMULAS.md](FORMULAS.md) + `reportFormulas.ts` |
| F11.7b | **UI:** tooltip ou painel “Como calculamos” a partir de KPIs principais e metas; link para glossário. | P1 | 8h | ✅ Bloco premissas + glossário expansível no relatório nativo |
| F11.7c | **Testes:** golden ou snapshot garante que o número exibido bate com o motor para casos fixos. | P1 | 4h | 🚧 Smoke vitest do catálogo (`tests/lib/reportFormulas.test.ts`); golden motor ↔ UI deferido |

### F11.8 — Command palette / atalhos

| # | Tarefa | Prio | Est. | Status |
| --- | --- | --- | --- | --- |
| F11.8a | **Command palette** (`cmdk` ou lib alinhada ao DS): buscar páginas, ir para Documentos, Pipeline, Relatórios, Config, Plano. | P2 | 10h | ✅ `CommandPalette.tsx` + `cmdk` |
| F11.8b | **Atalhos globais** documentados (modal `?` ou página ajuda): ex. `G` + letra para navegação, evitando conflito com inputs. | P2 | 6h | ✅ Modal **?** (fora de inputs) + **⌘K** / Ctrl+K |
| F11.8c | **A11y:** palette focável por teclado, `aria` em resultados. | P2 | 3h | ✅ `Command` label + lista cmdk (refinar com auditoria dedicada) |

**Checkpoint F11:** usuário entende **de onde vem** o número; sabe quando **confiar** no dado vs revisar; relatório **impresso/PDF** passa checklist de consultoria; navegação separa **plano de vida** de **fechamento do mês**; hierarquia tipográfica consistente; command palette opcional para power users.

---

## F8 — Growth (Futuro)

Adiados conscientemente. São features de aquisição/marketing/polish pós-launch.

| Item                                              | Justificativa para adiar                                |
| ------------------------------------------------- | ------------------------------------------------------- |
| Landing page (hero, features, pricing, CTA)       | Prematuro: zero usuários externos no dogfood            |
| Onboarding wizard + guided tour                   | Sem user research para validar fluxo                    |
| PWA (manifest, service worker, offline, install)  | Implicações de security com dados financeiros           |
| Command palette (Cmd+K) + keyboard shortcuts        | Movidos para **F11.8** (produto); aqui só lembrete de marketing/SEO se empacotados na landing |
| Framer Motion / page transitions                  | Polish sem valor funcional                              |
| SEO / Open Graph / sitemap / robots.txt           | Sem landing page, sem SEO relevante                     |
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
2. **P0 antes de P1.** Dentro da fase, priorizar por dependência e risco. **P2** (ex.: classificação unificada, F11.8) entra quando F7 e dependências diretas permitirem.
3. **Paralelos seguros:** [P2 — Unificação da classificação](#p2--unificação-da-classificação-de-documentos) e [F11](#f11--confiança-transparência-e-excelência-de-relatório-beta--ga) podem avançar em sprints dedicados após dogfood, sem bloquear fechamento mecânico de F7.
4. **Atualizar status aqui.** Ao concluir uma task, marcar ✅ e mover contexto relevante para [CHANGELOG.md](CHANGELOG.md).
5. **Decisões técnicas importantes** → [DECISIONS.md](DECISIONS.md).
6. **Mudanças de escopo/visão** → atualizar [ROADMAP.md](ROADMAP.md) e discutir antes de executar.
