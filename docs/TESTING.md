# Testing — Guia de Contribuidor

> **Status:** Esqueleto inicial criado em F6.5 Bootstrap • será completado ao longo de 6.5F.13 conforme as suítes ficam prontas.
>
> **Objetivo:** dar a um contribuidor novo tudo que ele precisa para rodar, escrever, debugar e atualizar testes do Fin — sem chamar ninguém. Onboarding em horas, não dias (ADR-067).

---

## TL;DR

```bash
# Backend (pytest)
source .venv/bin/activate
pip install -r requirements-dev.txt
FIN_FERNET_KEY="NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA=" pytest backend/tests/ -q

# Pipeline (pytest)
FIN_FERNET_KEY="NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA=" pytest tests/ -q

# Frontend unit + integration (Vitest)
cd frontend
npm install
npm test                    # única passada
npm run test:watch          # modo dev
npm run test:coverage       # gera coverage/

# Frontend E2E (Playwright)
cd frontend
npx playwright install      # primeira vez (browsers)
npm run test:e2e            # default chromium
PW_CROSS_BROWSER=1 npm run test:e2e   # 3 browsers em fluxos críticos

# Backend "real" para E2E (Postgres+Redis isolados)
./scripts/test_backend_up.sh
# ... rodar testes ...
./scripts/test_backend_down.sh
```

---

## Estrutura

```
tests/                          # pipeline (E0-E7), pytest
backend/tests/                  # backend FastAPI, pytest async
backend/tests/factories/        # data builders (make_user, make_workspace, ...)
backend/tests/conftest.py       # DB isolation, client/auth_client fixtures

frontend/tests/                 # Vitest (unit + integration)
frontend/tests/setup.ts         # MSW lifecycle, jsdom polyfills
frontend/tests/mocks/           # MSW server + handlers + fixtures
frontend/tests/factories/       # data builders type-safe (frontend)
frontend/tests/e2e/             # Playwright specs
frontend/tests/e2e/helpers/     # auth helper, workspace isolation
frontend/vitest.config.ts
frontend/playwright.config.ts

tests/fixtures/                 # PDFs sintéticos (gerador determinístico)
tests/fixtures/pdf_generator.py # 6.5F.12 — 13 bancos cobertos
tests/regressions/              # 6.5E.8 — 1 test por bug histórico (BUG-NNN)
tests/test_design_tokens_build.py       # F9 — 20 tests (tokens build + parity)
tests/test_report_layout_codegen.py     # F9 — 14 tests (codegen + schema)

frontend/tests/components/report/       # F9 — testes do relatório nativo React
  ReportShell.test.tsx                  # 9 tests (shell + cards)
frontend/tests/lib/reports.test.ts      # F9 — 8 tests (API client)
frontend/tests/hooks/useReportData.test.tsx  # F9 — 6 tests (hook)
```

---

## Como rodar

### Backend

```bash
source .venv/bin/activate
FIN_FERNET_KEY="<chave>" pytest backend/tests/test_<modulo>.py -q
```

**DB isolation strategy:** *recreate-per-test* sobre SQLite in-memory. Documentado em [`backend/tests/conftest.py`](../backend/tests/conftest.py). Cada test vê schema limpo.

### Pipeline

```bash
FIN_FERNET_KEY="<chave>" pytest tests/test_<modulo>.py -q
```

### Frontend (Vitest)

```bash
cd frontend
npm test                              # roda toda suite
npm test -- --reporter=verbose        # output detalhado
npm test path/to/file.test.ts         # arquivo específico
npm test -- -t "nome do test"         # filtra por nome
```

### Frontend (Playwright)

```bash
cd frontend
npx playwright install                # uma vez por máquina
npm run test:e2e                      # default chromium
npm run test:e2e -- --ui              # modo UI (debug visual)
npm run test:e2e -- --headed          # vê o browser rodar
npm run test:e2e -- --debug           # passo a passo

# Cross-browser (3 fluxos críticos em chromium+firefox+webkit)
PW_CROSS_BROWSER=1 npm run test:e2e

# Específico
npm run test:e2e tests/e2e/golden-path.spec.ts
```

---

## Como adicionar test

### Backend

1. Crie `backend/tests/test_<feature>.py`.
2. Use as factories ao invés de construir models à mão:

   ```python
   from backend.tests.factories import make_user, make_workspace, make_member

   async def test_xyz(db):
       user = await make_user(db, email="x@test.com")
       ws = await make_workspace(db, owner=user, family_surname="Silva")
       member = await make_member(db, workspace=ws)
       # ... assert
   ```

3. Para endpoints autenticados, use `auth_client` ou crie token via `make_user(db) + create_access_token(user.id)`.
4. Para multi-tenant (6.5B.12): crie 2 workspaces com `make_workspace` e teste vazamento.

### Frontend (Vitest)

1. Crie `frontend/tests/<feature>.test.ts(x)`.
2. Use factories para data type-safe:

   ```ts
   import { makeUser, makeMember, makeRun } from "../factories";

   const u = makeUser({ email: "x@test.com" });
   ```

3. Para mockar API custom no test:

   ```ts
   import { server } from "../mocks/server";
   import { http, HttpResponse } from "msw";

   server.use(
     http.get("/api/dashboard", () => HttpResponse.json({ ... }))
   );
   ```

### Frontend (Playwright)

1. Crie `frontend/tests/e2e/<fluxo>.spec.ts`.
2. Use o auth helper:

   ```ts
   import { test, expect } from "@playwright/test";
   import { ensureLoggedIn } from "./helpers/auth";

   test("dashboard", async ({ page, request }, info) => {
     await ensureLoggedIn(page, request, info);
     await page.goto("/dashboard");
     await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();
   });
   ```

3. Tag fluxos críticos com `@critical` para rodarem em cross-browser:

   ```ts
   test("upload completo @critical", async ({ page }) => { ... });
   ```

---

## Como debugar falha em CI

**F6.5F.9 — artifacts disponíveis no GH Actions run:**

| Artifact                       | Onde baixar                                  | Conteúdo                                            | Retention |
| ------------------------------ | -------------------------------------------- | --------------------------------------------------- | --------- |
| `playwright-report`            | Aba "Actions" → run → Artifacts              | HTML report + vídeo + trace em cada test falhado   | 30 dias   |
| `backend-coverage`             | Mesmo lugar                                  | `coverage.xml` + `htmlcov/` (line coverage HTML)    | 14 dias   |
| `frontend-vitest-results`      | Mesmo lugar                                  | `vitest-results.xml` (JUnit) para integration CI    | 14 dias   |

**Passo a passo ao debugar:**
1. Abrir o run falhado em GH Actions.
2. Baixar `playwright-report` (ZIP).
3. Abrir `index.html` → clicar no test vermelho.
4. Ver:
   - **Screenshot pós-falha** — estado da UI no momento do erro
   - **Vídeo** — replay do test inteiro
   - **Trace** — timeline clicável com network + DOM snapshots (usar `npx playwright show-trace trace.zip`)
5. Reproduzir localmente com o mesmo input antes de fix.

**Unit test falhando só em CI (não local):**
- Provável causa: dependency order / flaky / timezone difference.
- Rodar com `TZ=UTC npm test` local para ver se é TZ.
- Aplicar quarentena (ver "Flaky test policy" abaixo) enquanto investiga.

---

## Flaky test policy — F6.5F.8

**Philosophy:** tests flaky matam confiança no CI. Em vez de suprimir silenciosamente, temos processo explícito.

### Playwright retries

- **CI:** `retries: 2` (em `playwright.config.ts`) — test flaky retenta até 2x
- **Local:** `retries: 0` — flakiness aparece imediato no dev loop

### Quarentena

Se test é legitimamente flaky e bloqueia merge:

```ts
// Em vez de deletar ou suprimir, anote explicitamente:
test.skip(true, "flaky: TODO BUG-XXX — race com WS reconnect");

test("upload real", async ({ page }) => {
  // ...
});
```

Gera sinal claro para quem vê o test listado como "skipped".

### Report semanal

CI pode rodar workflow `nightly-flaky-report.yml` (a criar) que lista tests com `test.skip(true, "flaky: ...")`. Issues auto-geradas por flaky >2 semanas sem fix.

---

## Como atualizar snapshot (visual regression) — F6.5F.10

**Política:** snapshots são artefatos versionados. Mudança em snapshot = mudança visual intencional. Requer revisão manual.

### Workflow

```bash
# 1. Rodar local com --update-snapshots (revisar o diff ANTES)
cd frontend
npm run test:e2e -- --update-snapshots tests/e2e/<spec>.visual.spec.ts

# 2. Inspecionar os PNG novos
ls -la tests/e2e/__snapshots__/

# 3. Commitar os snapshots JUNTO com o código da mudança visual
#    (não em PR separado; revisor precisa do contexto)
git add tests/e2e/__snapshots__/
git add src/components/<mudança>
git commit -m "feat(design): <mudança visual> + snapshots atualizados"
```

### PR template checkbox

Toda PR que altera `tests/e2e/__snapshots__/` deve marcar:

```markdown
- [ ] Snapshots atualizados são **intencionais** (change visual esperada)
- [ ] Incluí screenshot do diff na descrição do PR (antes/depois)
- [ ] Testei em light + dark mode local
```

### CODEOWNERS

`.github/CODEOWNERS` requer review de designer (ou founder) para mudanças em snapshots:

```
/frontend/tests/e2e/__snapshots__/ @davidrobert
```

---

## Premium tier LLM em E2E — F6.5F.11 (ADR-070)

**Default (PR checks):** LiteLLM mockado. Custo $0. Rápido.

```python
# backend/tests/fixtures/llm_mock.py expõe `mock_llm_service()` que retorna
# outputs Pydantic válidos por stage (E1, E1.5, E2-llm, E7-review).
# Usado via dependency override em integration tests + E2E default.
```

**Nightly opt-in:** `nightly-e2e-real-llm.yml` (scheduled cron, a criar em follow-up):

```yaml
on:
  schedule:
    - cron: "0 3 * * *"  # 03:00 UTC diário
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  PW_REAL_LLM: "1"
```

Validates:
- Breaking changes do SDK Anthropic/OpenAI (pegos em <24h)
- Rate limit / quota behavior
- Token counting real

Se nightly falha: issue auto-gerada. Cost cap no CI secret: <$10/mês esperado.

Ver [ADR-070](DECISIONS.md#adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in) para rationale.

---

## FAQ

**Q: Por que tests/ pipeline e backend/tests/ separados?**
A: Pipeline é package Python independente (pode ser usado standalone); backend é FastAPI que orquestra. Cada um tem suas dependências e sua infra de teste.

**Q: Por que MSW e não jest.mock?**
A: MSW intercepta no nível de fetch/XHR — testa o código real de `lib/api.ts` em vez de stubs. Mais perto do comportamento real, menos chance de drift.

**Q: Por que recreate-per-test e não transactions+rollback?**
A: Ver docstring de [`backend/tests/conftest.py`](../backend/tests/conftest.py). TL;DR: SQLite in-memory é instantâneo (~5ms) e isolation é trivial; otimizações são prematuras.

**Q: Posso commitar PDFs reais como fixture?**
A: **Não.** Use o gerador sintético em `tests/fixtures/pdf_generator.py`. Lint custom (6.5D.7) bloqueia CPF real em fixtures.

**Q: Test flaky, o que faço?**
A: 1) tente reproduzir local com `--repeat-each=10`. 2) se confirmado, quarentena via `test.skip(true, "flaky: TODO BUG-XXX")` e abra issue. 3) **não suprima silenciosamente**.

---

## Tabela de comandos

| Ação                               | Comando                                                    |
| ---------------------------------- | ---------------------------------------------------------- |
| Backend test único                 | `pytest backend/tests/test_x.py::test_y -q`                |
| Backend test com print             | `pytest backend/tests/test_x.py -s`                        |
| Backend coverage                   | `pytest backend/tests/ --cov=backend.app --cov-report=html` |
| Pipeline test                      | `pytest tests/test_x.py -q`                                |
| Frontend unit                      | `cd frontend && npm test`                                  |
| Frontend coverage                  | `cd frontend && npm run test:coverage`                     |
| Frontend E2E (chromium)            | `cd frontend && npm run test:e2e`                          |
| Frontend E2E (cross-browser)       | `PW_CROSS_BROWSER=1 npm run test:e2e`                      |
| Frontend E2E debug                 | `npm run test:e2e -- --debug`                              |
| Sobe stack de teste (pg+redis)     | `./scripts/test_backend_up.sh`                             |
| Reset DB de teste                  | `./scripts/test_backend_up.sh --reset`                     |
| Derruba stack                      | `./scripts/test_backend_down.sh`                           |

---

## Ver também

- [`docs/BACKLOG.md#f65--frontend-testing--qa`](BACKLOG.md#f65--frontend-testing--qa) — tasks de F6.5
- [`docs/DECISIONS.md#adr-063--hardening-fintech-em-sub-fase-65d`](DECISIONS.md#adr-063--hardening-fintech-em-sub-fase-65d) — ADR de hardening fintech
- [`docs/DECISIONS.md#adr-064--backend-hardening-em-sub-fase-65e`](DECISIONS.md#adr-064--backend-hardening-em-sub-fase-65e) — ADR de backend hardening
- [`docs/DECISIONS.md#adr-067--test-infrastructure-em-sub-fase-65f`](DECISIONS.md#adr-067--test-infrastructure-em-sub-fase-65f) — ADR de test infrastructure
