---
id: TRACK-a6e5-v1-prefix
type: track
title: "Track A6e.5 — `/api/v1/` prefix + aliases + OpenAPI versionado"
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

# Track A6e.5 — `/api/v1/` prefix + aliases + OpenAPI versionado

> **Lane ID:** A6e.5
> **Branch prefix:** `agent/a6e5-v1-prefix/*`
> **Depende de:** — (independe de A6e.3; pode rodar em paralelo)
> **Paralelo com:** A6e.3 use cases, A6f.1 pipeline-service, A6g.2 pipeline sweep, A6g.4 frontend sweep — **zero overlap de conteúdo** (esta lane só mexe em registros de prefix + base URL).
> **Conflita com:** qualquer commit em `backend/app/main.py` (hotspot desta lane), `backend/app/core/config.py` (setting `API_PREFIX`), `frontend/src/lib/api/core.ts` (hotspot desta lane). Nenhuma outra lane ativa deve tocar esses 3 arquivos — coordene por §Hotspots se precisar.
> **Onda:** 2
> **Índice de prompts:** [README.md](../../../../README.md)
> **Fonte de verdade:** [ADR-108 URLs canônicas](../../../DECISIONS.md), [ADR-102 R18-R20](../../../DECISIONS.md), [ARCHITECTURE §18](../../../reference/ARCHITECTURE.md), [BACKLOG §A6e](../../../BACKLOG.md)

> **Objetivo:** versionar a API pública do backend sob `/api/v1/` sem quebrar
> clientes existentes. Introduzir alias **deprecated** em `/api/` com
> `Deprecation: true` + `Sunset: <data>` para remoção planejada em F7A.
> OpenAPI passa a declarar `info.version = "1.0.0"` + servidor canônico
> `https://api.mathoms.ai/v1`. Frontend consome `/api/v1/` como default.

---

## Por que esta lane agora

- **ADR-108** já define as URLs canônicas (`api.mathoms.ai/v1/...`). O código ainda registra em `/api/*` — descompasso documentação ↔ runtime.
- **F7A (Docker + HTTPS + reverse proxy)** vai configurar `nginx.conf` com
  `location /api/v1/`. Sem o prefixo versionado no app, F7A precisa
  reescrever rotas no proxy — acopla infra a código.
- **OpenAPI 3.1 versionado** é pré-requisito de ADR-102 R18 (snapshot
  estável) para clients gerados e para o Go service (A6f) consumir com
  contrato congelado.
- **Independente de A6e.3/.4/.6:** esta lane não toca lógica de router;
  só registra cada router duas vezes (canônico + alias). Zero overlap
  com refactors de aggregates em curso.

---

## Regras inegociáveis

Do CLAUDE.md + ADRs:

1. **Não quebrar cliente existente.** `/api/*` continua funcional durante
   toda a transição. Remoção fica para **F7A** (registrada como débito em ADR/backlog).
2. **Alias = mesma função, dois caminhos.** Cada router é registrado 2× em
   `main.py` — uma em `V1_PREFIX` (canônico), outra em `LEGACY_PREFIX`
   (deprecated). Nenhuma duplicação de código de handler.
3. **`Deprecation` + `Sunset` headers** em `/api/*` (legado), via
   middleware pequeno. Data de `Sunset` = data alvo de F7A; se incerta,
   use "TBD F7A" no header e referencie ADR.
4. **OpenAPI `info.version = "1.0.0"`** + `servers: [{url: "/api/v1"}]`
   explícitos em `FastAPI(...)`. Snapshot regenerado e comitado.
5. **Frontend:** `API_BASE = "/api/v1"` em `frontend/src/lib/api/core.ts`.
   Ponto único — não espalhe o prefix por handlers.
6. **Sem quebrar testes.** Se algum teste hardcodou `"/api/foo"`, atualize
   para `settings.API_PREFIX` (padrão) ou para `"/api/v1/foo"` — nunca
   deixe literal duplicado em N testes.
7. **Response models intocados** (ADR-109). Esta lane não mexe em
   schemas nem em handlers; apenas em registry de prefix.
8. **Type hints + comentários existentes preservados** (§Code style).

---

## Estado atual — mapeamento

**Backend — `backend/app/main.py`:**

```python
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(reports_router, prefix=settings.API_PREFIX)
# ... 18 routers no total (linhas 101-120)
```

`settings.API_PREFIX = "/api"` ([backend/app/core/config.py:11](../../../../backend/app/core/config.py:11)).

**Routers registrados (confirme com `grep "include_router" backend/app/main.py`):**

`auth`, `reports`, `vault`, `documents`, `pipeline`, `config`,
`family_members`, `categories`, `llm`, `ws`, `transactions`, `dashboard`,
`notifications`, `audit`, `goals`, `workspaces`, `workspaces_tenant`,
`invitations`, `tasks`, `feature_flags` — **20 routers**.

**FastAPI app:**

```python
app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url=f"{settings.API_PREFIX}/docs",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    # SEM info.version explícito hoje
)
```

**Frontend — `frontend/src/lib/api/core.ts:1`:**

```ts
export const API_BASE = "/api";
```

Consumido por todos os `frontend/src/lib/api/<domain>.ts` via
`import { API_BASE, apiFetch } from "./core"`. **Ponto único.**

**OpenAPI snapshot:** `docs/reference/api/v1/openapi.json` (já vive sob `/v1/` — a
pasta está pronta; o runtime ainda não casa).

**Testes que consomem prefix:**

```bash
grep -rn "\"/api/" backend/tests/ frontend/src/ | wc -l
```

Estime antes de começar — se >30 ocorrências, priorize substituir por
`settings.API_PREFIX` / `API_BASE` em vez de atualizar cada literal.

---

## Alvo estrutural

**`backend/app/core/config.py`:**

```python
class Settings(BaseSettings):
    API_PREFIX: str = "/api/v1"          # canônico (novo default)
    LEGACY_API_PREFIX: str = "/api"      # alias deprecated até F7A
    API_VERSION: str = "1.0.0"           # OpenAPI info.version
    LEGACY_SUNSET_DATE: str = "TBD F7A"  # preenchido quando F7A for agendada
```

**`backend/app/main.py`:**

```python
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    docs_url=f"{settings.API_PREFIX}/docs",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    servers=[{"url": settings.API_PREFIX, "description": "Canonical v1"}],
)

# Middleware adiciona Deprecation/Sunset em respostas do legacy prefix
app.add_middleware(LegacyApiDeprecationMiddleware)

# Canonical
for router in ALL_ROUTERS:
    app.include_router(router, prefix=settings.API_PREFIX)

# Alias deprecated (include_in_schema=False para não poluir OpenAPI)
for router in ALL_ROUTERS:
    app.include_router(
        router,
        prefix=settings.LEGACY_API_PREFIX,
        include_in_schema=False,
    )
```

**Nota sobre `include_in_schema=False`:** o OpenAPI canônico só mostra
`/api/v1/*`. O alias funciona mas não aparece em `/api/v1/openapi.json`.
Quem documenta manual (Postman, curl snippets) migra para `/v1`;
SDK gerado já nasce apontando para o canônico.

**`backend/app/middleware/legacy_deprecation.py`** (novo, ≤40 linhas):

```python
class LegacyApiDeprecationMiddleware(BaseHTTPMiddleware):
    """Adiciona Deprecation + Sunset em respostas do prefix legado.

    RFC 8594 (Sunset) + IETF draft-dalal-deprecation-header.
    Remoção: ADR-108 §F7A.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(settings.LEGACY_API_PREFIX) and \
           not request.url.path.startswith(settings.API_PREFIX):
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = settings.LEGACY_SUNSET_DATE
            response.headers["Link"] = (
                f'<{settings.API_PREFIX}>; rel="successor-version"'
            )
        return response
```

**`frontend/src/lib/api/core.ts`:**

```ts
export const API_BASE = "/api/v1";
```

Uma linha. Resto dos `lib/api/*.ts` já usa `API_BASE`, sem literal.

---

## Passos — sequência sugerida

### Passo 1 — Backend settings + registry (1 commit)

1. Editar `backend/app/core/config.py` com 4 novos fields (`API_PREFIX`,
   `LEGACY_API_PREFIX`, `API_VERSION`, `LEGACY_SUNSET_DATE`).
2. Refatorar `backend/app/main.py` para registrar cada router 2×.
   Extrair tupla `ALL_ROUTERS` antes do loop (≤25 linhas; se passar,
   mova para `backend/app/api/__init__.py` com `__all__`).
3. Adicionar `version=` e `servers=` no `FastAPI(...)`.
4. `pytest backend/tests/ -q` — tests esperados verdes (devem usar
   `settings.API_PREFIX` ou TestClient sem prefix literal).
5. Se tests quebram por literal `"/api/foo"`: substitua por
   `f"{settings.API_PREFIX}/foo"`. Preserve intent do teste.

**Commit 1:** `feat(backend): register routers under /api/v1 with legacy /api alias (A6e.5)`

### Passo 2 — Deprecation middleware (1 commit)

1. Criar `backend/app/middleware/legacy_deprecation.py` (≤40 linhas).
2. Registrar em `main.py` com `app.add_middleware(...)`.
3. Teste em `backend/tests/middleware/test_legacy_deprecation.py`:
   - `GET /api/v1/health` → sem `Deprecation` header.
   - `GET /api/health` → `Deprecation: true` + `Sunset: TBD F7A` + `Link: </api/v1>; rel="successor-version"`.
4. Verificar que CORS + outras middlewares não são afetadas.

**Commit 2:** `feat(backend): Deprecation+Sunset headers on legacy /api prefix (A6e.5)`

### Passo 3 — OpenAPI snapshot regenerado (1 commit)

1. `make update-openapi-snapshot` — diff esperado:
   - `info.version: "0.1.0"` → `"1.0.0"`
   - `servers: [...]` aparece com `/api/v1`
   - Paths canônicos aparecem sob `/api/v1/*` (mudança em massa)
   - **Nada** sob `/api/` nas paths (alias excluído via `include_in_schema=False`)
2. Validar OpenAPI: `jq '.info.version' docs/reference/api/v1/openapi.json` → `"1.0.0"`.
3. `pytest backend/tests/test_openapi_snapshot.py -q` deve passar após o
   commit (o teste valida que runtime == snapshot).

**Commit 3:** `chore(api): regenerate openapi.json under /api/v1 with info.version=1.0.0 (A6e.5)`

### Passo 4 — Frontend aponta para /v1 (1 commit)

1. Editar `frontend/src/lib/api/core.ts`: `API_BASE = "/api/v1"`.
2. `grep -rn "\"/api/" frontend/src/` — se aparecer literal fora de
   `core.ts`, é bug preexistente: substitua por `API_BASE` no mesmo
   commit. Se for teste Playwright ou MSW handler, ajuste para usar
   constante importada ou o novo prefix.
3. `cd frontend && npm test -- --run` + `npm run test:e2e` — verde.
4. Se MSW (`frontend/src/mocks/`) tem handlers hardcoded `/api/...`,
   ajuste para `/api/v1/...` ou para `API_BASE`.

**Commit 4:** `feat(frontend): point API_BASE to /api/v1 (A6e.5)`

### Passo 5 — Docs hotspot (≤5min, 1 commit)

1. `docs/CHANGELOG.md [Unreleased]` — bloco A6e.5: rotas canônicas em
   `/api/v1`, alias `/api` deprecated, OpenAPI v1.0.0, frontend migrado.
2. `docs/BACKLOG.md` — Lanes abertas: `A6e.5 ☐ aberta` → `✅ entregue
   <data>`. Atualizar sumário "Restante" no topo do Sprint A6.
3. `docs/reference/ARCHITECTURE.md §18` — confirmar que URLs estão sincronizadas
   com runtime. Se diverge, corrija.
4. `docs/reference/RUNBOOK.md` (se mencionar `/api/` bare) — adicione nota de
   deprecação.
5. Considerar **ADR-112** (ou número vago seguinte) documentando a
   decisão "aliás legado até F7A" — opcional mas recomendado.

**Commit 5:** `docs(a6e.5): register v1 API versioning + legacy sunset (A6e.5)`

---

## Critérios de aceite (binários)

- [ ] `curl -I http://localhost:8000/api/v1/health` retorna 200, **sem** `Deprecation` header.
- [ ] `curl -I http://localhost:8000/api/health` retorna 200 + `Deprecation: true` + `Sunset: ...` + `Link: </api/v1>; rel="successor-version"`.
- [ ] `jq '.info.version' docs/reference/api/v1/openapi.json` = `"1.0.0"`.
- [ ] `jq '.servers[0].url' docs/reference/api/v1/openapi.json` = `"/api/v1"`.
- [ ] `jq '[.paths | keys[] | select(startswith("/api/") and (startswith("/api/v1") | not))] | length' docs/reference/api/v1/openapi.json` = `0` (alias não aparece no snapshot).
- [ ] `grep -rn "\"/api\"" backend/app/ frontend/src/ | grep -v "LEGACY\|test_legacy\|api/v1"` = 0 (nenhum hardcode bare `/api` sobrou fora do alias).
- [ ] `grep -n "API_PREFIX\b" backend/app/main.py` usa `settings.API_PREFIX` (nenhum literal `/api` no registry).
- [ ] `pytest backend/tests/ -q` zero regressão.
- [ ] `pytest backend/tests/test_openapi_snapshot.py -q` verde.
- [ ] `cd frontend && npm test -- --run` zero regressão.
- [ ] `cd frontend && npm run test:e2e` fluxos `@critical` verdes contra o novo prefix.
- [ ] `make update-openapi-snapshot` foi rodado **após** os 4 commits de código; diff comitado no Commit 3.
- [ ] Nenhum arquivo off-limits foi tocado (listado em §Coordenação).
- [ ] `pre-commit run --all-files` passa.
- [ ] `CHANGELOG.md` + `BACKLOG.md` refletem status final.

---

## Rollback criteria — ABORTE se

- Algum teste de contrato (Playwright, Vitest de integração) falha em
  >2 fluxos e o fix exige tocar `api/<domain>.ts` fora de `core.ts`
  (sinal de vazamento de prefix).
- `make update-openapi-snapshot` mostra schemas ou response models
  deletados (não deveriam mudar — só `info.version`, `servers`, `paths`).
  Se schema sumiu, algo mais mexeu no router.
- Reverse proxy de staging (se existir em `nginx/` ou `docker-compose`)
  aponta para `/api/` e quebraria sem atualização coordenada com F7A —
  pare, anuncie, planeje com F7A.
- Lane A6e.3 ou A6f.1 mergeou mudança em `backend/app/main.py` entre o
  seu `git fetch` e o `git push` — rebase, re-rode testes.

Em rollback: `git reset --hard origin/main` na branch local, anuncia,
abre issue com o ponto que travou.

---

## Anti-patterns a evitar

- **Substituir `/api` por `/api/v1` via `sed` em massa.** Tests e
  docstrings têm contextos ambíguos (URLs externas, exemplos). Revise
  cada hit.
- **Remover o alias `/api` neste slice.** Remoção é F7A — esta lane só
  introduz versionamento sem quebrar nada.
- **Middleware que inspeciona body ou muda response em mais de header.**
  `LegacyApiDeprecationMiddleware` é 3 headers em response; se você se
  pegar fazendo mais, está no escopo errado.
- **Mudar `API_VERSION` de string para tuple ou Enum.** Mantenha string
  SemVer — OpenAPI `info.version` espera string.
- **Versionar por header (`Accept: application/vnd.mathoms.v1+json`).**
  ADR-108 escolheu prefix URL; não introduza segunda via.
- **Criar `/api/v2` preventivamente.** v2 nasce quando houver breaking
  change real. YAGNI.
- **Esquecer MSW/fixtures no frontend.** Se `frontend/src/mocks/` tem
  handler `/api/foo`, ele vira 404 silencioso após a mudança. Teste E2E
  não pega, unit test com MSW sim.

---

## Coordenação com outros agentes

Em paralelo a você, lanes ativas (2026-04-21):

- `agent/a6e3-use-cases/*` — toca **conteúdo** de `api/family_members.py`,
  `api/categories.py`, `api/goals.py`. **Zero overlap** com `main.py` ou
  `core/config.py`. Se A6e.3 cria router novo (`api/family_members.py`
  já existe, mas pode adicionar rotas), o registry em `main.py` já os
  pega via `include_router` — não precisa adicionar novo import a menos
  que ela crie módulo novo. Sync antes do push final.
- `agent/a6f1-pipeline-service/*` — pode tocar `api/pipeline.py` e
  possivelmente `main.py` se reestruturar registro. **Hotspot real.**
  Antes do push, `git log -5 --oneline origin/main -- backend/app/main.py`;
  se A6f.1 mergeou, rebase.
- `agent/a6g2-pipeline-style/*` — pipeline sweep em `scripts/`. **Zero
  overlap.**
- `agent/a6g4-frontend-style/*` — frontend sweep. **Overlap possível**
  em `frontend/src/lib/api/core.ts` se ele tocar tipos ou eslint nessa
  região. Check antes do commit 4: `git log -5 --oneline origin/main
  -- frontend/src/lib/api/core.ts`.

**Hotspots compartilhados (além dos usuais):**

```bash
git fetch origin
git log -5 --oneline origin/main -- \
  backend/app/main.py \
  backend/app/core/config.py \
  frontend/src/lib/api/core.ts \
  docs/reference/api/v1/openapi.json
```

Se qualquer um dos 4 mudou <30min atrás por outra lane, espere 2min,
anuncie, commite **no mesmo turno** (≤5min).

**Sync periódico (sessão >1h):**

```bash
git fetch origin && git log --oneline HEAD..origin/main
```

Se `CLAUDE.md`, ADRs, ou `ARCHITECTURE.md §18` mudaram, releia antes
de continuar — política de URLs pode ter evoluído.

---

## O que esta lane NÃO entrega (explicitar no CHANGELOG)

- **Remoção do alias `/api/*`** — F7A (quando reverse proxy estiver
  pronto e métricas de tráfego mostrarem zero clientes no legado).
- **`/api/v2/*`** — não existe; YAGNI até haver breaking change.
- **Versionamento por header** — ADR-108 escolheu prefix URL;
  fechado.
- **Gateway/reverse proxy config** — nginx/traefik ficam em F7A.
- **Clientes SDK gerados** (TS/Python/Go) — F7C/F7D. Esta lane entrega
  o OpenAPI **estável** que habilita codegen futuro.
- **Deprecation em response body** (JSON warning field) — apenas
  headers. Response shape fica intocado (ADR-109).

---

## Referências

- [ADR-108](../../../DECISIONS.md) — URLs canônicas (api.mathoms.ai/v1)
- [ADR-102](../../../DECISIONS.md) — R18-R20 language-neutral (OpenAPI snapshot)
- [ARCHITECTURE §18](../../../reference/ARCHITECTURE.md) — domínios + URLs
- [BACKLOG §A6e](../../../BACKLOG.md) — status da sprint
- [RFC 8594](https://www.rfc-editor.org/rfc/rfc8594) — Sunset HTTP header
- [IETF draft-dalal-deprecation-header](https://datatracker.ietf.org/doc/draft-ietf-httpapi-deprecation-header/) — Deprecation header
- Prompts paralelos: [track_a6e3](a6e3-use-cases.md), [track_a6f1](a6f1-pipeline-service.md), [track_a6g2](a6g2-pipeline-style-sweep.md), [track_a6g4](a6g4-frontend-style-sweep.md)
