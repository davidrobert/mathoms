---
id: TRACK-a6e4-thin-routers
type: track
title: "Track A6e.4 — Routers finos (17 routers × ≤50 linhas)"
sprint: A6
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a6
  - status/consumed
---

# Track A6e.4 — Routers finos (17 routers × ≤50 linhas)

> **Lane ID:** A6e.4
> **Branch prefix:** `agent/a6e4-thin-routers/*`
> **Depende de:** A6e.3 ✅ + A6e.3b ✅ (todos os 8 aggregates com use cases em main: audit, category, config_blob, document, family_member, goal, task + base). **Fase 4b destravada.**
> **Paralelo com:** A6e.events, A6g.2, A6g.6 — zero overlap **se** respeitar a lista de arquivos por fase abaixo.
> **Conflita com:** commits simultâneos em `backend/app/api/*.py` por outras lanes. A6e.events emissão de eventos **dentro** dos routers: evitar (eventos vivem em use cases).
> **Onda:** 2
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:** [ADR-101 R15/R16 (routers finos)](../DECISIONS.md), [ADR-109 response_model](../DECISIONS.md), [CLAUDE.md §Code style](../../CLAUDE.md#code-style), [BACKLOG §A6e](../BACKLOG.md)

> **Objetivo:** converter os 17 routers HTTP do backend para o padrão
> **1 endpoint = delegação a 1 use case**, reduzindo de ~4661 para ~850
> linhas (17 × ≤50). Handlers viram 3-8 linhas: valida dependência via
> `Depends`, chama use case, retorna DTO. Exception handling global
> traduz erros de domínio para HTTP. Adicionar teste AST que enforça
> o limite. **Escopo bifurcado:** fase **4a** (14 routers) + fase **4b**
> (3 routers pipeline-adjacentes, agora destravados por A6e.3b ✅).

---

## ⚠️ Estado atual — LEIA ANTES DE COMEÇAR (2026-04-22)

### Já feito em slice anterior (NÃO refazer)

Commits em `origin/main`:
- `9608058` — **goals.py** 444→333 (23 handlers thin + helpers em `application/goal/_author_enrichment.py`)
- `579aabc` — **audit.py** 69→47 (1 handler thin + `application/audit/`)
- `3327986` — **test AST criado** em `backend/tests/architecture/test_routers_thin.py` com `THIN_ROUTERS={audit, categories, dashboard, family_members, goals}` e regra `max 15 stmts/endpoint`
- `b600231` — CHANGELOG + BACKLOG "2/14 thin routers + AST enforcement"

Progresso: **2/14 slices feitos.**

### Já existente no repo (reuse; não recriar)

- **Application layer aggregates em `backend/app/application/`:** `audit/`, `base/`, `category/`, `config_blob/`, `document/`, `family_member/`, `goal/`, `task/` (8 diretórios). **Todos os use cases da A6e.3 + A6e.3b estão em main** — este slice consome deles nos respectivos routers.
- **Exception handlers globais em `backend/app/main.py:88-98`:** `NotFoundError → 404`, `ConflictError → 409`, `DomainValidationError → 422`. Routers novos **não precisam** `try/except` para esses; apenas propagam.
- **Test AST** `backend/tests/architecture/test_routers_thin.py` — enforce `≤15 stmts/endpoint` + `sem select(...)` + `sem session.commit()` para cada router em `THIN_ROUTERS` set. **Expandir o set** conforme refatora.

### Ambiguidade histórica do ID `(A6e.4)`

5 commits de **2026-04-20** com tag `(A6e.4)` referem ao **ConfigBlob per-aggregate slice** (track anterior), NÃO a esta lane transversal:
```
f48f06b backend(repos): ConfigBlobRepository async (A6e.4 — ADR-101)
f2b0319 backend(dto): config_blob DTOs (A6e.4 — ADR-101)
840b74c backend(api): config.py usa ConfigBlobRepository + DTOs (A6e.4 — ADR-101)
eaa6370 test(backend): ConfigBlob DTO mapper + repository (A6e.4 — 33 testes)
1d7562f docs(api): openapi snapshot — rename schemas ConfigBlob (A6e.4)
```

Filtre com `git log --grep "A6e.4 slice"` para ver **só** commits desta lane transversal. Use em commit messages **desta lane**: `(A6e.4 slice N)` ou `(A6e.4 — slice N)` — sem esses tokens você cai na ambiguidade.

---

---

## Por que esta lane agora

- **A6e.3 ✅** entregou use cases para 3 aggregates (FamilyMember, Category, Goal) + routers finos para family_members.py (151) e categories.py (87). Falta **goals.py** (444 linhas apesar de use cases extraídos — helpers locais `_author_names`, `_with_author` ainda inflam).
- **A6f.1 ✅** extraiu `HttpPipelineClient`. `pipeline.py` (428 linhas) agora pode virar proxy fino.
- **Routers CRUD simples** (`auth`, `vault`, `notifications`, `ws`, `audit`, `feature_flags`, `dashboard`) já estão <110 linhas mas não seguem o padrão thin — uniformizar agora evita inconsistência permanente.
- **Desbloqueia A6g.3** (backend sweep) e **A6g.6** (enforcement com teste AST).
- **Pré-requisito de F7A**: reverse proxy + rate limiting por rota exige handlers previsíveis; cada handler carregar ORM query + tradução HTTP + business rule duplicada impede instrumentação via decorator.

---

## Regras inegociáveis

Do CLAUDE.md + ADR-101 R15/R16:

1. **1 endpoint = 1 handler = 1 chamada de use case.** Handler típico: 3-8 linhas (extrair `current_workspace`, montar `Command`, chamar `await use_case(...)`, retornar). Max 15 linhas — se passa, mover para use case.
2. **Zero lógica de negócio em router.** `select(...)`, `session.commit()`, `if role == "admin"` (autorização), formatação de resposta derivada de agregação — tudo em service/use case, não em handler.
3. **Response model explícito (ADR-109).** `response_model=FooResponse` obrigatório em endpoints JSON; `response_class=...` para arquivos. Preservar intocado.
4. **Exception handling global.** `NotFoundError → 404`, `ConflictError → 409`, `ValidationError → 422` — registrados via `@app.exception_handler(...)` em `main.py`, **não** `try/except HTTPException` espalhado em cada endpoint.
5. **Dinheiro nunca é `float`** (ADR-090). Se encontrar `Decimal` vazando de repo direto, reporte em commit separado — não misture.
6. **Funções 4-20 linhas, arquivos ≤500 (target ≤50 para router)**. Helpers de router (ex.: `_author_names` em goals.py) movem para use case ou service — router não carrega utilidades.
7. **Type hints obrigatórios** + **preserve comentários existentes** (§Code style).
8. **`include_in_schema=False` apenas em debug/admin.** Não esconder endpoints produtivos do OpenAPI.
9. **Shim binário**: nenhum handler é removido — apenas reescrito. Path + method + query params + response shape idênticos. Se quebrar contrato, é fora deste scope (abrir ADR).

---

## Fase 4a — 12 routers restantes (pickable agora)

**Pré-requisitos:** A6e.3 ✅ + A6e.3b ✅ + A6f.1 ✅ (todos em main).

### Routers — estado atual (tamanhos **vivos** verificados em `backend/app/api/*.py`)

| Router | Hoje | Target | Handlers | Status | Estratégia |
|---|---|---|---|---|---|
| `goals.py` | **333** | — | 23 | ✅ **slice 1 feito** (`9608058`) | `_author_enrichment.py` em `application/goal/` |
| `audit.py` | **47** | — | 1 | ✅ **slice 2 feito** (`579aabc`) | `application/audit/` criado |
| `family_members.py` | 151 | — | 9 | ✅ **já thin** (A6e.3) | — |
| `categories.py` | 87 | — | 5 | ✅ **já thin** (A6e.3) | — |
| `dashboard.py` | 61 | — | 3 | ✅ **naturalmente thin** (já em `THIN_ROUTERS`) | — |
| `pipeline.py` | 428 | ≤80 | 10 | ☐ **pendente** | Usar `HttpPipelineClient` (A6f.1) — proxy fino |
| `workspaces.py` | 375 | ≤60 | 8 | ☐ **pendente** | `application/workspace/` (CRUD + switch) |
| `reports.py` | 363 | ≤60 | 9 | ☐ **pendente** | `application/report/` |
| `transactions.py` | 226 | ≤50 | 6 | ☐ **pendente** | `application/transaction/` |
| `llm.py` | 176 | ≤50 | 7 | ☐ **pendente** | `application/llm_config/` |
| `invitations.py` | 131 | ≤50 | 2 | ☐ **pendente** | `application/invitation/` |
| `notifications.py` | 110 | ≤40 | 3 | ☐ **pendente** | `application/notification/` |
| `ws.py` | 100 | ≤50 | 2 | ☐ **pendente** | `application/realtime/` (WebSocket) |
| `vault.py` | 80 | ≤40 | 3 | ☐ **pendente** | `application/vault/` |
| `auth.py` | 72 | ≤40 | 3 | ☐ **pendente** | `application/auth/` (login/refresh/logout) |
| `feature_flags.py` | 68 | ≤40 | 2 | ☐ **pendente** | `application/feature_flag/` |

**Fase 4a: 12 routers pendentes** para thin. Total atual desses 12 = 2500 → target ~690 linhas.

**Aggregates de application/ a criar (11 novos):** workspace, report, transaction, llm_config, invitation, notification, realtime, vault, auth, feature_flag, + outro conforme padrão da lane.

### Sequência de commits (4a) — a partir do estado atual

**Slice convention:** todo commit cita `(A6e.4 slice N)` para desambiguar dos 5 commits históricos de 2026-04-20 com `(A6e.4)` soltos.

**Slices 1-3 já feitos** (em main): goals (`9608058`), audit (`579aabc`), test AST (`3327986`).

**Slice 4+ — 1 commit por router pendente**, ordem sugerida por tamanho:

1. **`pipeline.py`** (428 → ≤80) — usa `HttpPipelineClient` (A6f.1). Handler chama `client.start_run(...)` / `.get_status(...)` / `.cancel(...)`. Logic de retry no client.
2. **`workspaces.py`** (375 → ≤60) — CRUD + switch.
3. **`reports.py`** (363 → ≤60) — generate/list/get_html/get_pdf.
4. **`transactions.py`** (226 → ≤50) — list/update/reconcile.
5. **`llm.py`** (176 → ≤50) — configure/test_connection.
6. **`invitations.py`** (131 → ≤50) — create/accept.
7. **`notifications.py`** (110 → ≤40) — list/mark_read.
8. **`ws.py`** (100 → ≤50) — WebSocket subscribe.
9. **`vault.py`** (80 → ≤40) — rotate_key/status.
10. **`auth.py`** (72 → ≤40) — login/refresh/logout.
11. **`feature_flags.py`** (68 → ≤40) — get/set.

**Padrão de cada slice:**
- Criar `backend/app/application/<aggregate>/` (se não existe) com use cases em arquivos curtos (nome específico: `list_workspaces`, não `manage`).
- Criar `backend/tests/application/<aggregate>/` com fakes + testes puros (sem DB).
- Reescrever router: cada handler ≤15 statements (teste AST enforça).
- **Adicionar nome do router ao `THIN_ROUTERS` set** em `backend/tests/architecture/test_routers_thin.py` — enforce imediato após refactor.
- Remover `try/except` duplicado no router: os 3 handlers globais já em `main.py:88-98` cobrem `NotFoundError` / `ConflictError` / `DomainValidationError`.
- Commit message: `refactor(backend): thin <router> — N→M (A6e.4 slice N)`

**Não precisa mais commit dedicado para:**
- ~~Exception handlers globais~~ — **já existem** em `backend/app/main.py:88-98`.
- ~~Test AST inicial~~ — **já existe**; slices apenas expandem `THIN_ROUTERS` set.

**Commit final (4a) — Docs** (hotspot, ≤5 min):
- `docs/CHANGELOG.md [Unreleased]`: A6e.4 fase 4a completa — 14/14 routers thin, X linhas → Y.
- `docs/BACKLOG.md`: linha A6e.4 → "🚧 parcial (4a ✅, 4b pendente)" ou "✅" se fase 4b fizer no mesmo slice.
- ADR-114 opcional: só se padrão de use cases novos se desviou das ADRs 101/109 (provável que não).

### Gate 4a

- `wc -l backend/app/api/*.py` — cada um dos 14 ≤target da tabela.
- `pytest backend/tests/ -q` zero regressão (target: 926+ testes passing).
- `pytest backend/tests/application/ -q` verde em <10s (sem DB).
- `pytest backend/tests/architecture/test_routers_thin.py -q` verde.
- `make update-openapi-snapshot` — diff só em descrições/renames de schema; zero path/method/response_model mudou.
- `grep -rn "session.commit\|select(" backend/app/api/` zero hits (exceto comentários).
- `grep -rn "try:" backend/app/api/ | wc -l` ≤5 (só casos irreductíveis tipo upload streaming).

---

## Fase 4b — DESTRAVADA (3 routers pipeline-adjacentes)

**Pré-requisito:** A6e.3b ✅ **mergeada 2026-04-22** — use cases de ConfigBlob + Document + Task em main (`application/config_blob/`, `application/document/`, `application/task/` existem).

### Routers alvo (3)

| Router | Hoje | Target | Handlers | Bloqueio |
|---|---|---|---|---|
| `documents.py` | 769 | ≤100 | 10 | Precisa use cases `upload_document`, `reclassify_document`, `list_documents`, `delete_document`, `get_document_preview` em `application/document/` |
| `tasks.py` | 487 | ≤80 | 19 | Precisa use cases de Task + subaggregates (Budget, Goal linkage) em `application/task/` — A6e.7 entregou 3 sub-agregados no DTO mas use cases ainda não |
| `config.py` | 464 | ≤80 | 18 | Precisa use cases de ConfigBlob (institutions, llm_providers, reconciliation) em `application/config_blob/` |

**Total 4b:** 1720 → ~260 linhas.

### Sequência de commits (4b)

Mesmo padrão de 4a. 1 commit por router após use cases de A6e.3b existirem. Gate idêntico + mede redução numérica no CHANGELOG.

### Gate 4b

- 17 de 17 routers ≤50-100 linhas (conforme tabela).
- Total `wc -l backend/app/api/*.py` ≤1200 linhas (target original 850; 1200 é slack para casos complexos documentados).
- `backend/app/application/` cobre **todos** os 13 aggregates operacionais.
- Teste AST do 4a passa também nos 3 novos.

---

## Critérios de aceite consolidados (binários)

### 4a (estado atual: 2/14 feitos)
- [x] goals.py ≤target — ✅ (`9608058`)
- [x] audit.py ≤target — ✅ (`579aabc`)
- [x] `backend/tests/architecture/test_routers_thin.py` existe — ✅ (`3327986`)
- [x] Exception handlers globais em `backend/app/main.py:88-98` — ✅ pré-existente (NotFoundError, ConflictError, DomainValidationError)
- [ ] 11 routers restantes da fase 4a ≤ target de linhas.
- [ ] `backend/app/application/<aggregate>/` existe para 11 aggregates novos (workspace, report, transaction, llm_config, invitation, notification, realtime, vault, auth, feature_flag + 1).
- [ ] `THIN_ROUTERS` set cobre todos os 14 routers da fase 4a.
- [ ] `grep -rn "session.commit\|\.execute(select" backend/app/api/` = 0.
- [ ] `grep -rn "try:" backend/app/api/` ≤5 (só upload/streaming; hoje baseline = 24 — limpar conforme refatora).
- [ ] `pytest backend/tests/ -q` — zero regressão, ≥988 testes (baseline pós-A6e.3b).
- [ ] OpenAPI snapshot diff apenas em descrição/ordem; zero breaking.
- [ ] `pre-commit run --all-files` passa.

### 4b
- [ ] `documents.py`, `tasks.py`, `config.py` ≤target.
- [ ] `backend/app/application/document/`, `task/`, `config_blob/` cobrem todos os endpoints.
- [ ] Total `wc -l backend/app/api/*.py` ≤1200.
- [ ] Goldens de upload (`tests/fixtures/upload/*`) verdes.
- [ ] `docs/BACKLOG.md` A6e.4 → ✅.

---

## Rollback criteria — ABORTE se

- `pytest backend/tests/ -q` regredindo >10 testes pós-refactor de qualquer router individual.
- OpenAPI snapshot mostra path removido, response_model deletado, ou mudança de status code — significa quebra de contrato; reverter o slice.
- Refactor de router exige alterar schema DB (ex.: flag derivada que era calculada em handler vira coluna) — **fora do escopo**, abrir ADR.
- A6e.3b merge introduz DTO incompatível com handler existente antes de 4b começar — rebase, re-avaliar use cases.
- Conflict cascata: A6g.3 backend sweep começou em `backend/app/services/` que seu use case importa, e renames quebram build — pare, coordene ou adie seu commit.

Em rollback: `git reset --hard origin/main` na branch local, anuncia, deixa slice em issue com pickup notes.

---

## Anti-patterns a evitar

- **Handler com 20+ linhas "porque o DTO é grande".** DTO grande → mover validação custom para use case. Handler fica apenas com plumbing.
- **Use case que retorna `dict`.** Sempre Response DTO (Pydantic) tipado. Router sem conversão.
- **`try/except HTTPException` no handler.** Erros de domínio → exception handler global. Handler só faz `return await use_case(...)`.
- **Criar use case anêmico só para atingir o target.** Ex.: `get_audit_events_use_case` que é 1-line `return await repo.list(...)`. Aceitável, mas nome reflete intent (`list_audit_events_for_workspace`), não `get_X`.
- **Reescrever handler + adicionar feature no mesmo commit.** Thin é refactor; feature é commit separado. Mistura = impossível de revisar/reverter.
- **Esquecer `response_model`** durante thinning — ADR-109 quebra build via `test_openapi_response_models.py`.
- **Mover helper de router (`_author_names`) para `backend/app/services/` genérico.** Se é helper de Goal, vive em `application/goal/_author_enrichment.py` (visibilidade via `_`). Não expanda service layer sem motivo.
- **Tocar `documents.py`/`tasks.py`/`config.py` antes de A6e.3b.** Sem use cases, você acaba reimplementando-os no router — anti-ADR-101.
- **Mover lógica de autorização para router** ("só admin pode deletar"). Autorização é domínio — use case checa + `ForbiddenError`.

---

## Coordenação com outros agentes

Lanes ativas ou recentemente mergeadas (confirme com `git worktree list` + `git for-each-ref`):

- `agent/a6e-events/*` — events vivem em `backend/app/events/` + emitidos de **use cases**, não routers. Zero overlap com seus commits de router. Overlap potencial em `backend/app/application/*/` se A6e.events adiciona emissão de evento em use case que você criou — rebase e concatene.
- `agent/a6g2-pipeline-style/*` — `scripts/`, `pipeline/`, `tests/fixtures/`. Zero overlap.
- `agent/a6g6-enforcement/*` — `pyproject.toml`, `.pre-commit-config.yaml`, CI config. Pode mexer em `backend/tests/architecture/` adicionando testes irmãos (`test_no_any_in_boundary.py`, `test_no_forbidden_names.py`) — não em `test_routers_thin.py`. Zero overlap real.
- `agent/a6g3-backend-style/*` (quando iniciar pós-A6e.4) — `backend/app/services/`, `backend/app/repositories/`. A6g.3 aguarda você; sem conflito.

**Lanes já mergeadas** (baseline):
- A6e.3 ✅, A6e.3b ✅ — 8 aggregates em `backend/app/application/`.
- A6e.5 ✅ — `/api/v1/` prefix; não afeta esta lane.
- A6f.1 ✅ — `HttpPipelineClient` pronto para usar em `pipeline.py`.
- A6g.4 ✅, A6g.5 ✅, A6g.7 ✅.

**Hotspots compartilhados:**

```bash
git fetch origin
git log -5 --oneline origin/main -- \
  backend/app/main.py \
  backend/app/api/ \
  backend/app/application/ \
  backend/tests/architecture/test_routers_thin.py
```

Se A6e.events mergeou hotspot <30min, espere 2min, anuncie seu slice, commite **no mesmo turno** (≤5min). **Branch stale** `agent/a6e4-thin-routers/20260422-2020` sem atividade desde 08:20 de 2026-04-22 — você pode retomá-la (`git checkout` + continuar) ou criar branch nova partindo de `origin/main`.

**Sync periódico (sessão >1h):**

```bash
git fetch origin && git log --oneline HEAD..origin/main
# se CLAUDE.md, ADRs, ou application/ mudaram, releia antes de continuar
```

**Cadência de commit (defensiva):**
- Commite cada slice (1 router) assim que handler + use case + teste verdes. Nunca acumule 3 routers em 1 commit — rebase vira impossível.
- Se sessão vai pausar mid-slice (router parcialmente thinned), commit `chore(wip)` antes de fechar.

---

## O que esta lane NÃO entrega (explicitar no CHANGELOG)

- **Domain events tipados** — A6e.events. Use cases novos deste slice não emitem eventos (ainda).
- **`/api/v1/` prefix** — A6e.5, em andamento paralelo. Esta lane preserva o prefix atual.
- **Authorization policies declarativas** — futuro; use case chama `_assert_can_write(workspace, user)` hoje.
- **Rate limiting por rota** — F7B. Esta lane apenas cria handlers previsíveis para permitir decorator/middleware.
- **Migração de schema DB** — nenhum campo derivado vira coluna neste escopo.
- **Performance tuning** (N+1 queries, caching) — A6g.3 backend sweep.
- **Enforcement ESLint/ruff automatizado** — A6g.6. Aqui só o teste AST dentro de `backend/tests/architecture/`.

---

## Referências

- [ADR-101](../DECISIONS.md) — R15 application layer (use cases), R16 thin routers
- [ADR-109](../DECISIONS.md) — response_model obrigatório
- [ADR-112](../DECISIONS.md) — pipeline-as-service (fornece `HttpPipelineClient`)
- [BACKLOG §A6e](../BACKLOG.md) — status da sprint e lanes
- Slice modelo de thin router: [backend/app/api/family_members.py](../../backend/app/api/family_members.py) (151 linhas, padrão A6e.3 slice 1)
- Slice modelo de use case: [backend/app/application/family_member/create_family_member.py](../../backend/app/application/family_member/create_family_member.py)
- Prompts paralelos: [track_a6e3](track_a6e3_use_cases.md), [track_a6e5](track_a6e5_v1_prefix.md), [track_a6f1](track_a6f1_pipeline_service.md), [track_a6g2](track_a6g2_pipeline_style_sweep.md), [track_a6g4](track_a6g4_frontend_style_sweep.md)
