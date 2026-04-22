# Track A6e.4 — Routers finos (17 routers × ≤50 linhas)

> **Lane ID:** A6e.4
> **Branch prefix:** `agent/a6e4-thin-routers/*`
> **Depende de:** A6e.3 ✅ (FamilyMember+Category+Goal use cases em main); **A6e.3b** (ConfigBlob+Document+Task) é pré-requisito **apenas** para fase 4b.
> **Paralelo com:** A6e.3b, A6e.5, A6e.events, A6g.2, A6g.4, A6g.7 — zero overlap **se** respeitar a lista de arquivos por fase abaixo.
> **Conflita com:** commits simultâneos em `backend/app/api/*.py` por outras lanes. A6e.5 só toca `main.py` (registry) e não o corpo dos routers — coexistir é seguro com rebase. A6e.events emissão de eventos **dentro** dos routers: evitar (eventos vivem em use cases).
> **Onda:** 2
> **Índice de prompts:** [README.md](README.md)
> **Fonte de verdade:** [ADR-101 R15/R16 (routers finos)](../DECISIONS.md), [ADR-109 response_model](../DECISIONS.md), [CLAUDE.md §Code style](../../CLAUDE.md#code-style), [BACKLOG §A6e](../BACKLOG.md)

> **Objetivo:** converter os 17 routers HTTP do backend para o padrão
> **1 endpoint = delegação a 1 use case**, reduzindo de ~4661 para ~850
> linhas (17 × ≤50). Handlers viram 3-8 linhas: valida dependência via
> `Depends`, chama use case, retorna DTO. Exception handling global
> traduz erros de domínio para HTTP. Adicionar teste AST que enforça
> o limite. **Escopo bifurcado:** fase **4a** (14 routers, pickable agora)
> + fase **4b** (3 routers pipeline-adjacentes, aguarda A6e.3b).

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

## Fase 4a — Pickable agora (14 routers)

**Pré-requisitos:** A6e.3 ✅ + A6f.1 ✅ (ambos em main).

### Routers alvo (14)

| Router | Hoje | Target | Handlers | Estratégia |
|---|---|---|---|---|
| `goals.py` | 444 | ≤80 | 23 | Use cases já existem; mover `_author_names`/`_with_author` p/ `application/goal/_author_enrichment.py` |
| `pipeline.py` | 428 | ≤80 | 10 | Usar `HttpPipelineClient` (A6f.1 slice 2) — router vira proxy fino |
| `workspaces.py` | 375 | ≤60 | 8 | Extrair `workspace_use_cases` (create/list/update/delete/switch) em `application/workspace/` |
| `reports.py` | 363 | ≤60 | 9 | Use cases `generate_report`, `list_reports`, `get_report_html/pdf` em `application/report/` |
| `transactions.py` | 226 | ≤50 | 6 | Use cases `list/update/reconcile_transaction` em `application/transaction/` |
| `llm.py` | 176 | ≤50 | 7 | Use cases `configure_llm`, `test_llm_connection` em `application/llm_config/` |
| `family_members.py` | 151 | ≤50 | — | **Já thin (A6e.3)** — revisar só se helpers ficaram no router |
| `invitations.py` | 131 | ≤50 | 2 | Use cases `create_invitation`, `accept_invitation` em `application/invitation/` |
| `notifications.py` | 110 | ≤40 | 3 | Use cases `list/mark_read` em `application/notification/` |
| `ws.py` | 100 | ≤50 | 2 | WebSocket: lógica vai p/ `application/realtime/subscribe_workspace.py` |
| `categories.py` | 87 | — | — | **Já thin (A6e.3)** |
| `vault.py` | 80 | ≤40 | 3 | Use cases `rotate_key`, `get_status` em `application/vault/` |
| `auth.py` | 72 | ≤40 | 3 | Use cases `login`, `refresh_token`, `logout` em `application/auth/` |
| `audit.py` | 69 | ≤40 | 1 | Use case `list_audit_events` em `application/audit/` |
| `feature_flags.py` | 68 | ≤40 | 2 | Use cases `get_flag`, `set_flag` em `application/feature_flags/` |
| `dashboard.py` | 61 | ≤40 | 3 | Use cases `get_summary`, `get_metrics` em `application/dashboard/` |

**Total 4a:** 2780 → ~770 linhas. Criação de use cases onde ainda não existem (9 aggregates novos: workspace, report, transaction, llm_config, invitation, notification, realtime, audit, feature_flags, dashboard, vault, auth).

### Sequência de commits (4a)

**Commit 1 — `goals.py`** (maior ganho, use cases existem):
- Mover `_author_names`/`_with_author` para `backend/app/application/goal/_author_enrichment.py` (helper interno, `_` prefix).
- Cada handler ≤8 linhas. 444 → ≤80.
- `refactor(backend): thin goals router — 444→<80 (A6e.4 slice 1)`

**Commit 2 — `pipeline.py`** (usa A6f.1 client):
- Handler chama `HttpPipelineClient.start_run(...)` / `.get_status(...)` / `.cancel(...)`.
- Logic de retry/backoff fica no client, não no router.
- `refactor(backend): thin pipeline router via HttpPipelineClient — 428→<80 (A6e.4 slice 2)`

**Commits 3-N — Aggregate simples** (workspaces, reports, transactions, llm, invitations, notifications, vault, auth, audit, feature_flags, dashboard, ws):
- **1 commit por aggregate**. Se aggregate é CRUD trivial (ex.: feature_flags = get/set), use cases podem ser finas (5-10 linhas cada). Não force ceremony onde não agrega.
- Padrão: criar `backend/app/application/<aggregate>/` com use cases (nome específico, não `manage_*`), criar `backend/tests/application/<aggregate>/` com fakes + testes puros, reescrever router.
- Ordem por tamanho (maior primeiro): workspaces → reports → transactions → llm → invitations → notifications → ws → vault → auth → audit → feature_flags → dashboard.

**Commit N+1 — Exception handlers globais**:
- `backend/app/core/exception_handlers.py` (novo ou ampliar existente): mapeia `NotFoundError`, `ConflictError`, `ValidationError`, `ForbiddenError` para HTTP.
- Registra em `main.py` via `app.add_exception_handler(...)`.
- Remove `try/except HTTPException` duplicado dos routers (grep reveals todos).
- `refactor(backend): global domain exception handlers (A6e.4 slice N)`

**Commit N+2 — Teste AST** (enforçamento):
- `backend/tests/architecture/test_routers_thin.py` — parseia cada `backend/app/api/*.py`, para cada `async def endpoint`, conta statements; falha se `> 15`.
- Também valida que nenhum `backend/app/api/*.py` importa `sqlalchemy` ou `session` diretamente.
- `test(architecture): AST enforcement de routers finos — ≤15 stmts/handler, sem SQLAlchemy (A6e.4)`

**Commit N+3 — Docs** (hotspot, ≤5 min):
- `docs/CHANGELOG.md [Unreleased]`: A6e.4 4a — 14 routers reescritos, Xk linhas → Yk.
- `docs/BACKLOG.md`: A6e.4 ⏸ → 🚧 parcial (4a done, 4b pendente).
- ADR-114 opcional: "thin routers + domain exception handlers".

### Gate 4a

- `wc -l backend/app/api/*.py` — cada um dos 14 ≤target da tabela.
- `pytest backend/tests/ -q` zero regressão (target: 926+ testes passing).
- `pytest backend/tests/application/ -q` verde em <10s (sem DB).
- `pytest backend/tests/architecture/test_routers_thin.py -q` verde.
- `make update-openapi-snapshot` — diff só em descrições/renames de schema; zero path/method/response_model mudou.
- `grep -rn "session.commit\|select(" backend/app/api/` zero hits (exceto comentários).
- `grep -rn "try:" backend/app/api/ | wc -l` ≤5 (só casos irreductíveis tipo upload streaming).

---

## Fase 4b — Aguarda A6e.3b (3 routers pipeline-adjacentes)

**Pré-requisito:** A6e.3b ✅ (use cases de ConfigBlob + Document + Task em main).

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

### 4a
- [ ] 14 routers listados na tabela ≤ target de linhas.
- [ ] `backend/app/application/<aggregate>/` existe para 11+ aggregates novos (workspace, report, transaction, llm_config, invitation, notification, realtime, audit, feature_flags, dashboard, vault, auth).
- [ ] `backend/app/core/exception_handlers.py` registra ≥4 handlers globais.
- [ ] `backend/tests/architecture/test_routers_thin.py` existe e passa.
- [ ] `grep -rn "session.commit\|\.execute(select" backend/app/api/` = 0.
- [ ] `pytest backend/tests/ -q` — zero regressão, ≥950 testes.
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

- `agent/a6e3b-use-cases-rest/*` (quando iniciar) — **hotspot direto** em `documents.py`, `tasks.py`, `config.py`. Sua fase 4b aguarda essa lane mergear.
- `agent/a6e5-v1-prefix/*` — toca `backend/app/main.py` (registry de routers) + `core/config.py`. **Overlap potencial** em `main.py` (você adiciona `app.add_exception_handler`). Resolva: commite exception handlers em arquivo separado (`backend/app/core/exception_handlers.py`), registre em `main.py` com 1-2 linhas. A6e.5 registra routers; convivem.
- `agent/a6e-events/*` — events vivem em `backend/app/events/` + emitidos de **use cases**, não routers. Zero overlap com seus commits de router. Overlap potencial em `backend/app/application/*/` se A6e.events adiciona emissão de evento em use case que você criou — rebase e concatene.
- `agent/a6g2-pipeline-style/*` — `scripts/`, `pipeline/`, `tests/fixtures/`. Zero overlap.
- `agent/a6g3-backend-style/*` (quando iniciar pós-A6e.4) — `backend/app/services/`, `backend/app/repositories/`. A6g.3 aguarda você; sem conflito.
- `agent/a6g4-frontend-style/*` — frontend. Zero overlap.
- `agent/a6g7-go-prep/*` — Go infra. Zero overlap.

**Hotspots compartilhados:**

```bash
git fetch origin
git log -5 --oneline origin/main -- \
  backend/app/main.py \
  backend/app/api/goals.py \
  backend/app/api/pipeline.py \
  backend/app/application/
```

Se A6e.5 ou A6e.events mergearam hotspot <30min, espere 2min, anuncie seu slice, commite **no mesmo turno** (≤5min).

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
