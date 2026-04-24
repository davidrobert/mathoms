# Mathoms AI — Roadmap

> Visão de alto nível das fases do projeto. Atualizar mensalmente ou ao mudar de fase.
>
> **Última atualização:** 2026-04-24
> **Fase atual:** F9 concluída • **Sprint transversal A6**: Onda 2 ✅ (A6e.3/.4/.5/.events · A6f.1) + A6b.flip ✅ (ADR-118) + A6-ux.livestep ✅ (ADR-119) + A6-readers.dbfirst ✅ (ADR-120) + A6g.3b ✅ + A6g.6/6b ✅ + A6g.7 ✅; A6g.3 em rodada final • **Report Premium UI**: 10/13 fases ✅ (F0-F10 em `main`); Fase 11 (`e6_render.py` paridade via ADR-124) próxima • **F7F-Local**: MVP fechado (ADR-116) • Status de sessão + lanes abertas em [BACKLOG §Sprint A6](BACKLOG.md#sprint-a6--migração-infradomínio-plano-transversal) (fonte única) • F7 (Produção + LGPD + Ops) agendada após A6g.3 final + Fase 12/13 do Report Premium.

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
| **6.5** | Testing & Hardening (FE+BE) | ✅ Concluída | Vitest + RTL + MSW + Playwright — **438 tests** (94 backend + 344 frontend) em ~25s. Hardening fintech (axe 0 critical, property-based BRL, visual reg. infra, resilience, security smoke, CPF mod-11+lint PII, error boundary, focus mgmt). Backend hardening (6 serializers round-trip, alembic guardrails, golden pipeline, concurrency). Multi-tenant isolation (27 tests, 0 leaks). WS real com fakeredis. Anti-regression bank (24 tests). Test infrastructure completa (factories, isolation, docker-compose.test, synthetic PDFs, pipeline mock fixtures, MSW lint, LLM mock). CI GH Actions (7 jobs). SMOKE_TEST.md 70+ checks. 7 ADRs novas (062-064, 067-071). |
| **7**   | Produção + LGPD + Ops    | ☐ Planejada  | VPS+Docker+Traefik, LGPD completo, auth flows (email verify/pwd reset/brute-force), prompt injection defense, operational readiness (DR testado, business metrics, incident comms, LLM cost cap), CI/CD, dogfood validado |
| **8**   | Goals & Tasks + Cutover CLI→Web | ✅ Concluída | Goals versionados (IF + APORTE_MENSAL + DOLARIZACAO + ALOCACAO_ALVO + PLANNING_CONTEXT em F8.5), Tasks como entidade de 1ª classe (CRUD + dependencies + suggestions + attachments + progress%), Pipeline adapter (DB→JSON), Feature flags, Worker beat, Snapshot imutável no relatório, Celery beat diário scan-deadlines. **~146 testes, 7 ADRs (072-075, 077, 079), 5 migrations, 20 tenant models, 9 services, ~42 endpoints, 10 componentes React, 11 rotas frontend**. Cutover reversível via feature flags. ADR-072/073/074/075/077/079. |
| **9**   | Relatório Nativo React + Workspace Sharing + Design System | ✅ Concluída | **Relatório:** render React nativo (18 seções, 13 cards, 8 charts Recharts, deep-links, scroll-spy, print CSS A4, PDF Playwright). E6 vira exportador standalone. **Design System:** tokens.json → CSS unificado (ADR-076), codegen YAML→TS/Pydantic. **Sharing:** 3 roles, convites SHA-256/TTL 72h, forced logout, viewer banner, workspace switcher. **113 testes novos (56 BE + 23 FE + 20 tokens + 14 codegen), 3 ADRs (076-078), 3 migrations.** |
| **10**  | Growth & Aquisição | ☐ Futuro (pós-GA) | Landing, SEO, billing, digest — ver § F10 |
| **11**  | Confiança, transparência, excelência de relatório | ☐ Beta → GA | Origem dos dados, LLM/needs_review, premissas, hierarquia numérica, print/PDF consultoria, mental model plano × mês — ver § F11 |

**Épicos transversais (não são fases numeradas):** [P2 classificação de documentos](BACKLOG.md#p2--unificação-da-classificação-de-documentos) (motor); **P0/P1 motor canônico** (§ *Motor canônico e pipeline* abaixo) concluído; expansão incremental de goldens/PDF continua junto a **7D.1**.

---

## Status detalhado por fase

### F0-F6.5 — Concluídas ✅

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
| F6.5 | 71    | 1 dia concentrado | +438 (94 backend + 344 frontend) + 7 ADRs |
| F8   | —     | 1 sessão concentrada | +~146 backend + 12 lint. 6 ADRs (072-075, 077). 5 migrations |
| F9   | —     | 1 sessão concentrada | +113 tests (56 BE + 23 FE + 20 tokens + 14 codegen). 3 ADRs (076-078). 3 migrations. 50 componentes report, design tokens, codegen, PDF Playwright |

Para detalhes do que foi entregue, ver **[CHANGELOG.md](CHANGELOG.md)**.

Para tasks específicas já feitas e ainda pendentes por sub-fase, ver **[BACKLOG.md](BACKLOG.md)**.

---

### F6.5 — Testing & Hardening ✅

**Objetivo:** Rede de segurança completa antes de produção: testes em todas as camadas (unit/integration/E2E), hardening fintech-específico (frontend + backend), anti-regression bank, e infraestrutura de teste profissional para sustentar após o launch.

**Duração real:** 1 dia concentrado (2026-04-15), executado em 6 blocos pela ordem do CTO (foundation-first, não a ordem documentada A→B→C→D→E→F).

**Entregas (resultado final):**
- **438 tests** passando em ~25s (94 backend pytest + 344 frontend Vitest)
- **~25 E2E Playwright specs** (Golden Path + 8 fluxos críticos), 13 tagged @critical para cross-browser
- **7 ADRs** novas: [ADR-062](DECISIONS.md#adr-062--frontend-testing-em-fase-dedicada-65), [ADR-063](DECISIONS.md#adr-063--hardening-fintech-em-sub-fase-65d), [ADR-064](DECISIONS.md#adr-064--backend-hardening-em-sub-fase-65e), [ADR-067](DECISIONS.md#adr-067--test-infrastructure-em-sub-fase-65f), [ADR-069](DECISIONS.md#adr-069--msw-sync-strategy-manual--lint-ci-não-codegen), [ADR-070](DECISIONS.md#adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in), [ADR-071](DECISIONS.md#adr-071--playwright-workspace-isolation-email-unique-por-worker)
- **Multi-tenant isolation:** 27 tests paramétricos — 0 vazamentos entre workspaces
- **Anti-regression bank:** 24 tests backend cobrindo BUG-001..015 + 11 bugs operacionais do dogfood
- **6 serializers** com round-trip green (anti-BUG-015)
- **Concurrency test `materialize_config`** com 10 workspaces simultâneos (fork pool safe)
- **axe-core** 0 violations critical/serious — 2 a11y violations reais corrigidas no source
- **Property-based BRL** via fast-check (edge cases, round-trip, separadores)
- **CPF mod-11** gerador determinístico + lint anti-PII (7 CPFs reais substituídos)
- **Synthetic PDFs** para 14 códigos (`BankCode`) via `tests/fixtures/pdf_generator.py` (reportlab)
- **Pipeline mock fixtures** (`seed_completed_run`) + `--real-pipeline` opt-in
- **LLM mock fixtures** por stage (E1, E1.5, E2-llm, E7-review) — [ADR-070](DECISIONS.md#adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in)
- **Error boundary** em toda page via layout wrap
- **CI workflow** GH Actions (7 jobs + all-green gate + PR comment + retention 30d)
- **`.github/CODEOWNERS`** protegendo snapshots, migrations, ADRs
- **`docs/SMOKE_TEST.md`** 13 seções, 70+ checks (LGPD, multi-tenant, BUG-015/007/ADR-068 regressions)
- **`docs/TESTING.md`** contributor guide completo (flaky policy, snapshot review, debug CI, LLM mock)

**Por que entre F6 e F7 (decisão mantida):** separação garantiu que testes e hardening foram pré-requisito do deploy, não afterthought. 2 violations a11y reais + 2 vazamentos de PII via fallback + 10 falhas pré-existentes em tests backend descobertos durante a fase.

**Scaffolds ativáveis em CI (não bloqueiam close da fase):** visual regression baseline, nightly real LLM E2E, Lighthouse gate, bundle-size gate, contract-check gate, MSW lint CI, flaky report semanal.

Detalhes completos: **[BACKLOG.md#f65--frontend-testing--qa](BACKLOG.md#f65--frontend-testing--qa)** — todos os 6 blocos documentados com arquivos + número de tests + achados.

---

### F8 — Goals & Tasks + Cutover CLI→Web ✅

**Objetivo:** Dar ao produto capacidade de (1) o usuário configurar sua meta de Independência Financeira via wizard interativo, (2) gestão de backlog de tarefas fora do relatório (módulo de 1ª classe), (3) eliminar dependência de arquivos `config/goals.json` e `config/tarefas.md` via pipeline adapter + DB como fonte de verdade.

**Fases internas:**

| Sub-fase | Foco | Entregas |
|---|---|---|
| F8.0 | Fundação multi-tenancy | 4 ADRs (072-075), WorkspaceMember, `get_current_workspace`, tenancy lint AST-based + baseline (6 legados), docs/tenancy.md, CI job |
| F8.1 | Metas IF | Goal model versionado, `compute_if_derived` (FV anuidade), wizard 4 passos, seed Ferreira Campos (paridade 7.2M), `/plano` + `/plano/meta-if` |
| F8.2 | Plano de Ação | Task/TaskSuggestion/TaskAttachment models, tarefas.md parser (43 tasks, 5 deadline types, dep #19→#18), 3 views (priority/deadline/category), drawer, form, sugestões 1-click, widget dashboard |
| F8.3 | Integrações profundas | Task↔Goal linking, % executado (BRL parser + match transactions), snapshot imutável no Report, anexos CRUD (upload/download/delete), feature flags workspace-level (4 flags) |
| F8.4 | Cutover CLI→Web | Pipeline adapter (materializa payloads antes do run), E5.N hook → TaskSuggestion, PLANNING_CONTEXT goal type (cobertura 100% do goals.json), worker beat diário, scripts de paridade + cutover automatizado, ADR-077 |
| F8.5 | Multi-tenant Goals completo | API+UI para APORTE_MENSAL, DOLARIZACAO, ALOCACAO_ALVO (12 endpoints, 6 páginas React, dashboard `/plano` multi-goal), `create_goal_version` genérica, resiliência E6 (fallback + banner CTA), ADR-126 |

**Números:**
- **~146 testes** novos (goals: 32, tasks: 48, integrações: 45, adapter: 9, lint: 12)
- **6 ADRs**: [072](DECISIONS.md#adr-072) multi-tenancy, [073](DECISIONS.md#adr-073) goals versionados, [074](DECISIONS.md#adr-074) tasks 1ª classe, [075](DECISIONS.md#adr-075) cutover faseado, [077](DECISIONS.md#adr-077) adapter contrato
- **5 migrations Alembic** encadeadas: workspace_members → goals → tasks → report_snapshot → feature_flags
- **20 tenant models** detectados pelo lint AST
- **9 services** novos: goal, task, task_suggestion, task_notification, task_progress, task_attachment, report_tasks_snapshot, feature_flags, pipeline_adapter
- **11 rotas frontend**: /plano, /plano/meta-if[/wizard], /plano/aportes[/wizard], /plano/dolarizacao[/wizard], /plano/alocacao[/wizard], /plano-de-acao, /plano-de-acao/sugestoes
- **4 JSON schemas** canônicos: goal.if, goal.aporte_mensal, goal.dolarizacao, goal.alocacao_alvo

**Sequência operacional de cutover** (pós-deploy):
```bash
python -m backend.app.scripts.seed_if_goal_ferreira_campos --apply
python -m backend.app.scripts.seed_tasks_ferreira_campos --apply
python -m backend.app.scripts.seed_goals_full_ferreira_campos --apply
python -m backend.app.scripts.validate_adapter_parity
python -m backend.app.scripts.cutover_execute --apply
```

---

### F9 — Relatório Nativo React + Workspace Sharing + Design System ✅

**Objetivo:** (1) Substituir o iframe do relatório por render React nativo consumindo E5 JSON via API, (2) unificar identidade visual site × relatório via design tokens, (3) permitir compartilhamento multi-user do workspace.

**3 vertentes paralelas:**

| Vertente | Foco | Entregas |
|---|---|---|
| Report React | Render nativo de 18 seções | 50 componentes (shell + 13 cards + 8 charts + 9 sections), lotes A–H, deep-links, scroll-spy, print CSS A4, mode via URL `?mode=` |
| Design System | Identidade visual unificada | `tokens.json` (fonte única), `build.py` (CSS para frontend + E6), codegen YAML→TS/Pydantic, pre-commit hooks |
| Workspace Sharing | Multi-user com roles | WorkspaceInvitation, 3 roles (owner/member/viewer), forced logout, AcessosTab, workspace switcher, viewer banner |

**Backend:** 3 migrations (analysis_json_path, invitations, token_version), 5 endpoints novos (/data, /download.html, /download.pdf, invitations CRUD), PDF server-side Playwright.

**Números:** 113 testes novos, 3 ADRs (076-078), 3 migrations, 50 componentes report React.

---

### Motor canônico e pipeline (P0 / P1) — em paralelo ao F7

Trabalho técnico para **uma fonte de verdade** na lógica E0–E7, **testes offline** no laptop e **gates de schema** no CI. Não substitui fases numeradas; encaixa antes/alongside **7D.1** (gap-fill pipeline) e consolida ADR-013 / 075 / 077.

| Entrega | Documento / código | Status |
| --- | --- | --- |
| P0 — inventário, fronteira motor × adaptadores, contratos, gaps golden | [docs/CANONICAL_ENGINE_P0.md](CANONICAL_ENGINE_P0.md) | Concluído |
| P1 — runner offline, fronteiras de import, CI strict, goldens mínimos, checklist artefatos | [docs/P1_STRUCTURAL_PLAN.md](P1_STRUCTURAL_PLAN.md), [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md) | Concluído |
| Override `MATHOMS_PIPELINE_SCHEMA_MODE` em `validate_artifact` | `scripts/pipeline_common.py` | Concluído |
| `python -m pipeline.run_dev` | `pipeline/run_dev.py` | Concluído |
| Lint fronteiras `pipeline/` | `dev/check_pipeline_boundaries.py` | Concluído |

**Próximo passo (incremental):** (1) **PDFs reais anonimizados** (opcional) — scaffold em `tests/fixtures/e2_real_pdf_anon/` + `tests/test_e2_real_pdf_regression.py`; falta commitar binários redigidos. Ver [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md) § *E2 — sintético e real anonimizado* e [BACKLOG.md](BACKLOG.md). (2) **LLM:** [tests/fixtures/llm_golden/README.md](../tests/fixtures/llm_golden/README.md) + `tests/test_llm_golden.py`; novos estágios → estender schemas no mesmo padrão ([CANONICAL_ENGINE_P0.md](CANONICAL_ENGINE_P0.md) §4 item 3).

**Epic P2 (2026-04-17):** **P2.1–P2.5 entregues** — módulo único `document_classification`, ADR-081, testes de paridade nome canônico, UI de incerteza em Documentos; upload, reclassify e E0-route (com backend) compartilham o mesmo classificador; **P2.5** log estruturado `fin.classification_telemetry`. Ver [BACKLOG.md](BACKLOG.md#p2--unificação-da-classificação-de-documentos).

---

### F7 — Produção + Security + LGPD + Operational Readiness (próxima)

**Objetivo:** Levar o Mathoms AI a produção com a menor superfície de risco possível, fluxos de auth completos para suportar usuários reais, e maturidade operacional para sobreviver ao primeiro incidente.

**Duração estimada:** 8-10 semanas (5 sub-fases + 2 semanas de dogfood validado)

**Sub-fases:**

| Sub-fase | Foco                                                                                                                                                              | Duração    |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| 7A       | Docker + Deploy + HTTPS (VPS Hetzner, Traefik, Let's Encrypt via **DNS-01 Cloudflare**, subdomínios `app/api/ops/docs/status.mathoms.ai`, ADR-108) | 1-2 sem    |
| 7B       | Security + LGPD + Auth (Fernet expandido, rate limit, JWT refresh, audit, termos versionados, **email verification, password reset, brute-force lockout, prompt injection defense, soft-delete, DSAR**) | 3-4 sem    |
| 7C       | CI/CD + Observabilidade (GH Actions, Sentry, logs, uptime)                                                                                                        | 1-2 sem    |
| 7D       | Quality Gate + Launch Readiness (gap-fill, baseline perf, checklist)                                                                                              | 2-3 sem    |
| 7E       | **Operational Readiness** (stuck-run detector, restore drill, off-site backup, FERNET recovery, status page, business metrics, SLOs, incident comms templates, support runbook, LLM cost cap, API key validation, fallback model) | ~2 sem     |
| 7F       | **Console interno** — dividido em duas partes: **F7F-Local** (IA-0, pré-produção): UI web em `127.0.0.1` + camada de serviço, sem OAuth staff; executa exclusão de conta, purge de documentos, reset de senha, leitura de relatórios e métricas localmente; CLI é atalho secundário/futuro. **F7F-Remote** (IA-1…IA-4, produção): `ops.mathoms.ai` com OAuth Google Workspace, RBAC interno, `/api/internal/*`, dashboard de negócio (**7E.7**), CS bundle, financeiro. Ver [INTERNAL_ADMIN_ROADMAP.md](INTERNAL_ADMIN_ROADMAP.md). | F7F-Local: paralelo a Onda 2-3 (independente de 7A/B/C) · F7F-Remote: paralelo a 7D–7E |
| Dogfood  | 2+ semanas de uso real antes de beta                                                                                                                              | 2+ sem     |

**Deploy target:** VPS Hetzner CX32 (4 vCPU, 8GB, ~$8/mo) + Docker Compose + PostgreSQL + Traefik. DNS em **Cloudflare** (domínio `mathoms.ai` registrado lá). Backup off-site em S3 BR ou Backblaze B2.

**URLs públicas (ADR-108):**
- **Produto:** `app.mathoms.ai` · **API:** `api.mathoms.ai/v1/...` · **Console interno:** `ops.mathoms.ai` (F7F-Remote, IP allowlist + MFA); **pré-produção:** UI web em `127.0.0.1` com flag de env (F7F-Local, IA-0, sem OAuth)
- **Docs:** `docs.mathoms.ai` · **Status:** `status.mathoms.ai` · **Landing:** `mathoms.ai` (apex)
- **Staging:** `*.staging.mathoms.ai` · **Dev local:** `localhost:3000`/`localhost:8000`
- Multi-tenancy via path: `app.mathoms.ai/w/<workspace-slug>/...` (subdomain-per-tenant reservado para enterprise tier)

**Progressão pós-F7:**

| Estágio     | Quem                                  | Gate de passagem                                                                    |
| ----------- | ------------------------------------- | ----------------------------------------------------------------------------------- |
| **Dogfood** | founder                               | Zero pipeline failures em 5 runs consecutivos. Uptime >99%. Zero critical bugs      |
| **Beta**    | Família + 2-3 convidados (5 users)    | Onboarding sem suporte. Latência p95 <1s. Nenhum dado corrompido. LGPD verificado   |
| **GA**      | Público                               | Landing page + demo mode + billing (se aplicável). Suporte básico                   |

Detalhes das tasks: **[BACKLOG.md#f7](BACKLOG.md#f7--produção--lgpd)** · Console interno (operadores): **[INTERNAL_ADMIN_ROADMAP.md](INTERNAL_ADMIN_ROADMAP.md)** + **[BACKLOG.md#f7f](BACKLOG.md#f7f--console-interno-operadores)** · **Status page + incidentes (7E.6 / 7E.9):** ver [BACKLOG.md#7ec--observabilidade-de-negócio](BACKLOG.md#7ec--observabilidade-de-negócio) e § detalhamento após tabela 7E.D.

---

### F10 — Growth & Aquisição (pós-launch, Futuro)

Adiado conscientemente: são features de **aquisição / marketing** que não fazem sentido no estágio dogfood/beta. Incluídas para referência futura.

| Prioridade | Item | Notas |
| --- | --- | --- |
| P1 | Landing page + onboarding wizard + guided tour | Depende de pesquisa com usuários beta |
| P2 | PWA (service worker, install, offline seguro) | Segurança e superfície de dados sensíveis |
| P2 | SEO / Open Graph / sitemap | Depende de landing |
| P1 | Email digest notifications | Requer serviço de e-mail + templates |
| P1 | Demo mode (workspace fictício read-only) | Também útil a **F11** (onboarding sem medo) |
| P1 | Billing real (Stripe) | BYOK cobre Premium até GA |
| P2 | Report comparison (side-by-side, deltas) | Requer histórico de relatórios no uso real |

**Command palette / atalhos:** entregue em produto (**F11.8**): **⌘K** / Ctrl+K + modal **?** — ver [BACKLOG](BACKLOG.md#f11-8--command-palette--atalhos).

---

### F11 — Confiança, transparência e excelência de relatório (beta → GA)

Objetivo: **baixa fricção cognitiva**, **confiança em dados e em LLM**, e **entrega visual digna de consultoria** — sem substituir F7 (produção) nem o epic de **classificação unificada** (P2 no backlog).

| # | Tema | Entregas resumidas | Prio |
| --- | --- | --- | --- |
| F11.1 | **Mental model: “vida financeira” × “relatório deste mês”** | Rotas e IA claras: `/plano` e metas = configuração de longo prazo; fluxo Documentos → Pipeline → Relatório = ciclo mensal. Copy, navegação primária/secundária, empty states que não misturam os dois modos. | P1 |
| F11.2 | **Hierarquia de números** | Padrão único de tipografia e alinhamento (KPI, tabelas, gráficos, relatório): decimais BRL, sinal de fluxo, escala em eixos; auditoria Dashboard + Transaction Explorer + Report React + tokens. | P1 |
| F11.3 | **Print / PDF como entregável de consultoria** | Refino de `@media print`, capa, margens A4, quebras de página, fontes embed/sistema; export PDF/HTML com aparência “documento para terceiros”; checklist de QA visual. | P1 |
| F11.4 | **Transparência: origem da informação** | Por seção ou bloco: qual documento / período / estágio alimenta o número (linhagem resumida; link para Documentos ou run quando aplicável). | P1 |
| F11.5 | **Transparência: `needs_review` e trilha LLM** | Linguagem consistente: quando o dado é inferido, revisão humana pendente, ou validado; CTAs para revisão; sem jargão de estágio E* na UI (ADR-068). | P0 |
| F11.6 | **Metadados de premissas (metas + relatório)** | Campos ou bloco explícito: taxas, inflação, horizonte, cenário base; **F11.6b:** snapshot persistido (`premissas_snapshot_json` + API / merge no `/data`) para comparar mês a mês. | P1 |
| F11.7 | **Número ↔ regra** | Tooltips ou painel “Como calculamos”: ligação do KPI ao motor (ex.: FV de anuidade na meta IF); glossário mínimo. | P1 |
| F11.8 | **Command palette / atalhos** | `cmdk` (ou equivalente): busca de rotas, ações (novo upload, rodar pipeline); atalhos documentados e não conflitantes com o browser. | P2 |

Detalhamento por task: **[BACKLOG.md#f11--confiança-transparência-e-excelência-de-relatório-beta--ga](BACKLOG.md#f11--confiança-transparência-e-excelência-de-relatório-beta--ga)**.

**Sprint B (2026-04-17):** F11.5 (banner `needs_review`, notas LLM por etapa, sem códigos E* na linha de etapa; rótulo de toque E2 sem “E2” na UI), F11.4b–c (`ReportSourceStrip` + período/gerado em), fatia de F11.2 (eixos/tooltips do dashboard com `tabular-nums`).

**Sprint C (2026-04-17):** F11.4a no nível do relatório — `pipeline_run_id` na API, link e deep link para Pipeline; F11.2a — `tabular-nums` / `font-mono` em Transactions (tabela + paginação) e hero do relatório nativo.

**Sprint D (2026-04-17):** P2.5 (telemetria de classificação); conclusão F11.4a agregada (`source_document_ids` / `_report_lineage`); F11.2b; F11.7 + F11.6c; F11.3c checklist + F11.3a/b em progresso; F11.1 nav + empty states + [COPY_GUIDELINES](BACKLOG.md); F11.8 cmdk. **Atualização:** F11.6b (snapshot de premissas no relatório) e leva inicial **7D.1 / 7D.2** (testes unitários de borda E0/E3/E4/E7 e E5/E5N/E6). Próximo: F11.6a (premissas nas metas na UI), linhagem por seção se necessário, golden F11.7c.

**Ordem sugerida (histórico):** F11.5 → F11.4 → F11.2 → F11.7 → F11.6 → F11.3 → F11.1 → F11.8 — **Sprint D** executou o tail desta fila + P2.5.

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
| F6.5     | ~90%      | ~80%        | ✅ **438 tests** (94 backend + 344 frontend). lib/ ≥80% (utils/format/export/usePipelineWS 97-100%). Multi-tenant 0 leaks. 24 anti-regression tests. |
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
| R10 | Serializers DB→pipeline perdem campos silenciosamente (BUG-015 class) | Alto | ~~Alta~~ Baixa | ✅ F6.5E | Round-trip tests para 6 serializers + golden file pipeline + 4 tests anti-regressão BUG-015 |
| R11 | Migration aplicada em DB errada por cwd ambíguo | Alto    | ~~Média~~ Baixa | ✅ F6.5E   | Caminho absoluto em alembic.ini (%(here)s) + guard em env.py rejeita SQLite relativo + doc SETUP.md |
| R12 | LLM BYOK consome budget do user descontroladamente | Médio  | Alta            | ⏳ F7E      | Cost cap mensal por workspace + toast 80%/95% + hard stop 100%                            |
| R13 | Pipeline run "running" para sempre (worker morto) | Médio  | Média           | ⏳ F7E      | Heartbeat + Celery beat detector marca como failed >1h sem heartbeat                       |
| R14 | Prompt injection em PDF malicioso vaza dados via LLM | Alto | Baixa-Média    | ⏳ F7B      | Sanitização texto extraído + allowlist output + fixture PDF adversarial                   |
| R15 | FERNET_KEY perdida em prod = todos os secrets ilegíveis | Crítico | Baixa         | ⏳ F7E      | Backup criptografado off-site (1Password vault) + procedure testado em staging            |
| R16 | Backup Hetzner perdido junto com DC (incêndio/falha) | Crítico | Muito baixa    | ⏳ F7E      | Off-site backup S3/B2 BR + restore drill quarterly                                        |
| R17 | GA bloqueado por falta de email verify/password reset | Alto | Certa          | ⏳ F7B      | Auth flows completos em 7B.11-13 antes do Beta abrir                                       |
| R18 | Multi-tenant data leak entre workspaces (endpoint esquece filtro) | Crítico | ~~Média~~ Baixa | ✅ F6.5B | 27 tests paramétricos cobrem 9 domínios de endpoints — 0 vazamentos confirmados |
| R19 | 250+ tests viram débito técnico sem infra de teste sustentável | Alto | ~~Alta~~ Baixa | ✅ F6.5F | 438 tests sustentados por factories (backend+FE) + DB isolation + MSW sync + TESTING.md + CODEOWNERS |

---

## Sprint transversal A6 — Migração infra+domínio (pós-F9)

**ADRs formalizadoras**: 097-111 em [DECISIONS.md](DECISIONS.md) ·
**Arquitetura alvo + motivação**: [ARCHITECTURE §17](ARCHITECTURE.md).

**Fonte única de status, sessões pendentes, lanes abertas e diagrama de
ondas paralelas**: [BACKLOG.md §Sprint A6](BACKLOG.md#sprint-a6--migração-infradomínio-plano-transversal).
ROADMAP cobre apenas a visão de fases e timeline macro — não duplique
status de sessão aqui (vira drift).

**Resumo (snapshot 2026-04-24)**:
- **Entregues ✅:** A5a-A5f · A6a-c · A6d · A6e.3/.4/.5/.events · A6f.1/.2/.3/.4/.5a/.6 · A6g.1/.3b/.5/.6/.6b/.7 · A6b.flip (ADR-118) · A6-ux.livestep (ADR-119) · A6-readers.dbfirst (ADR-120).
- **Parcial 🚧:** A6g.3 (backend style sweep — rodadas finais).
- **Lanes abertas agora:** ver tabela em [BACKLOG §Lanes](BACKLOG.md). Confirme com `git worktree list` + `git for-each-ref --sort=-committerdate refs/remotes/origin/agent/`.
- **Caminho crítico (serial):** A6g.3 final → F7A → F7B → F7D+dogfood → GA. Report Premium Fase 11 (`e6_render.py` paridade) + Fase 12 (polish/a11y) + Fase 13 (rollout) correm em paralelo com F7.

**Após A6**: sprints dedicados §15 (LGPD) e §16 (Observabilidade) —
incorporados ao escopo de F7 (Produção + LGPD + Ops).

---

## Timeline geral estimada

| Período              | Milestone                                        |
| -------------------- | ------------------------------------------------ |
| Q1 2026              | F0-F4 ✅ (Core → LLM)                            |
| Q2 2026 (Abr)        | F4.5, F5, F6, F6.5, F8, F9 ✅ — feature-complete pré-produção + **Plano transversal A5a-A5e concluído** (Fase 8 do plano de migração infra+domínio) |
| Q2-Q3 2026 (Mai-Jul) | **Sprint A6** (A5f · A6a-c · A6b.5 · A6-human) → cutover DB validado + teste humano + bridge removido → **A6d/A6e/A6f em paralelo** |
| Q3 2026              | F7 (Produção + LGPD + Ops, integrando §15 LGPD + §16 Observabilidade do plano) → Dogfood → Beta fechado |
| Q3-Q4 2026           | Beta → F11 (confiança / transparência) → preparação GA + F10 (Growth) |
| 2027+                | GA + features de growth                          |

---

## Como priorizamos

- **P0** — Bloqueante. Sem isso a fase não entrega valor.
- **P1** — Importante. Sem isso funciona, mas falta qualidade/completude.
- **P2** — Nice-to-have. Pode postergar para próxima fase ou sprint.

Ver [BACKLOG.md](BACKLOG.md) para priorização detalhada por task.
