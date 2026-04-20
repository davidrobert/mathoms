# Testing — Guia de Contribuidor

> **Status:** Esqueleto inicial criado em F6.5 Bootstrap • será completado ao longo de 6.5F.13 conforme as suítes ficam prontas.
>
> **Objetivo:** dar a um contribuidor novo tudo que ele precisa para rodar, escrever, debugar e atualizar testes do Mathoms AI — sem chamar ninguém. Onboarding em horas, não dias (ADR-067).

---

## TL;DR

```bash
# Backend (pytest)
source .venv/bin/activate
pip install -r requirements-dev.txt
MATHOMS_FERNET_KEY="NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA=" pytest backend/tests/ -q

# Pipeline (pytest)
MATHOMS_FERNET_KEY="NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA=" pytest tests/ -q

# Pipeline offline (mesmo orquestrador do worker) — tenant com config/ materializado
python -m pipeline.run_dev --root /path/to/storage/<workspace_id>
python -m pipeline.run_dev --root ./tenant --stages E3,E4

# Fronteiras do pacote pipeline/ (sem FastAPI/Celery/SQLAlchemy)
python dev/check_pipeline_boundaries.py --verbose

# Schema JSON strict (mesmo gate do CI)
MATHOMS_PIPELINE_SCHEMA_MODE=strict pytest tests/test_schema_validation.py -q

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

# Reset total da DB + storage + Redis (dev/staging) — ver SETUP.md
# python -m backend.app.scripts.reset_platform --dry-run
```

---

## Estrutura

```
tests/                          # pipeline (E0-E7), pytest
backend/tests/                  # backend FastAPI, pytest async
backend/tests/factories/        # data builders (make_user, make_workspace, ...)
backend/tests/conftest.py       # DB isolation, client/auth_client fixtures
backend/tests/test_premissas_snapshot.py  # F11.6b — snapshot goals.json + metas ativas
backend/tests/test_openapi_response_models.py  # A6f.2 — estrutural: endpoint JSON tem response_model/response_class
backend/tests/test_openapi_snapshot.py  # A6f.2 — snapshot diff determinístico (docs/api/v1/openapi.json)
backend/tests/test_auth_portability.py  # A6f.5a — 12 parity tests JWT HS256 + Fernet (ADR-109)

frontend/tests/                 # Vitest (unit + integration)
frontend/tests/setup.ts         # MSW lifecycle, jsdom polyfills
frontend/tests/mocks/           # MSW server + handlers + fixtures
frontend/tests/factories/       # data builders type-safe (frontend)
frontend/tests/e2e/             # Playwright specs
frontend/tests/e2e/helpers/     # auth helper, workspace isolation
frontend/vitest.config.ts
frontend/playwright.config.ts

tests/fixtures/                 # PDFs sintéticos (gerador determinístico)
tests/fixtures/pipeline_golden/ # P1 — JSON mínimos vs schemas E2/E3/E4
tests/fixtures/llm_golden/      # JSONs saída LLM (E1, E1.5, E2-LLM, E7) vs `pipeline/llm/schemas`
tests/test_llm_golden.py        # parse + validators + conversores dos JSONs acima
tests/fixtures/e2_real_pdf_anon/  # Fase 2 opcional — PDFs reais redigidos + README
tests/test_e2_real_pdf_regression.py  # `route_to_parser` em cada `*.pdf` da pasta (vazia = no-op)
tests/test_e3_golden_execution.py  # E2 fixture → E3 run → asserts
tests/test_e4_golden_execution.py  # E3 → E4 (+ misto receita/despesa + baseline E1.5)
tests/test_e5_golden_execution.py  # E3→E4→E5 run → analise_financeira + E5 schema (+ misto receita/despesa + baseline E1.5)
tests/test_e5n_golden_execution.py  # E5 + e5n_narrativas → narrativas; + tenant com cônjuge (`ana_cenarios`)
tests/test_e6_golden_execution.py  # E4→E5→E6 HTML standalone (template + layout do repo)
tests/pipeline_golden_asserts.py  # asserções partilhadas (ex.: qa_log.md)
tests/test_e2_synthetic_pdf_parsers.py  # registry E2 × PDF; todos os bancos com assert dedicado (C6, Bradesco, … Caixa; Quinto Andar fatura)
tests/test_e0_route_edges.py tests/test_e7_edges.py tests/test_e5_e6_e5n_edges.py  # 7D.1/7D.2 — helpers de borda (E0/E7/E5/E6/E5.N)
tests/fixtures/pdf_generator.py # 6.5F.12 — 14 códigos BankCode; registry com `_draw_*` (C6, Bradesco, BTG, … Quinto Andar)
dev/check_pipeline_boundaries.py # P1 — imports proibidos em pipeline/
pipeline/run_dev.py           # P1 — CLI offline (orchestrator)
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
MATHOMS_FERNET_KEY="<chave>" pytest backend/tests/test_<modulo>.py -q
```

**DB isolation strategy:** *recreate-per-test* sobre SQLite in-memory. Documentado em [`backend/tests/conftest.py`](../backend/tests/conftest.py). Cada test vê schema limpo.

### Pipeline

```bash
MATHOMS_FERNET_KEY="<chave>" pytest tests/test_<modulo>.py -q
```

### Testes unitários de domínio — `tests/unit/pipeline/`

Desde a migração infra + domínio (ADRs 082-091), a camada
`pipeline/domain/` é testável **sem disco e sem banco** via
`InMemoryArtifactStore`. Exemplos:

```bash
# Roda apenas os domain tests (rápido, sem DB)
pytest tests/unit/pipeline/ -q

# Testes específicos do Money / Decimal invariants
pytest tests/unit/pipeline/test_domain_money.py -q

# ReconciliationService com fixture de 3 linhas
pytest tests/unit/pipeline/test_reconciliation_service.py -q
```

**Regra de uso (ADR-089):**
- Testes de `ReconciliationService`, `CategorizationService` e calculadoras
  (`CashFlowAggregator`, `PatrimonioCalculator`, etc.) **devem usar
  `InMemoryArtifactStore`** — sem fixtures de arquivo.
- Testes de integração que verificam paridade DB ↔ Disk usam
  `DBArtifactStore` + sync fixture factory (ver
  [backend/tests/test_db_artifact_store.py](../backend/tests/test_db_artifact_store.py)).
- `DiskArtifactStore` **não é usado** em testes automatizados — apenas em
  CLI dev.

**Pattern** — fixture típica de domain service:

```python
from pipeline.artifact_store import InMemoryArtifactStore
from pipeline.domain.models import Money, Transaction, BankStatement
from pipeline.domain.services import ReconciliationConfig, ReconciliationService

def test_reconciliation_removes_exact_duplicates():
    cfg = ReconciliationConfig(tolerance_days=3)
    svc = ReconciliationService(cfg)
    stmt = BankStatement(
        institution="itau", member_key="david",
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
        currency="BRL",
        transactions=[
            Transaction(date(2026, 1, 5), "MERCADO", Money.brl("-100")),
            Transaction(date(2026, 1, 5), "MERCADO", Money.brl("-100")),  # dup
        ],
    )
    out = svc.reconcile([stmt])
    assert len(out[0].transactions) == 1
```

**Goldens E3** — fixtures sintéticas em `tests/pipeline/goldens/e3/`
(Sessão A1 da Fase 6):

```bash
pytest tests/unit/pipeline/test_e3_reconciler_adapter.py -q
```

Cada golden é um JSON autocontido com:
- `description` — o que o cenário cobre.
- `e2_extracts` — lista de `{stage, key, payload}` para `store.seed`.
- `baseline` (opcional) — payload de E1.5c.
- `institutions` — `banco_canonical` para `BankCanonicalizer`.
- `expected` — contagens (`statements_loaded`, `artifacts_written`,
  `output_keys`, `*_warnings_count`) para asserts.

Cenários atuais cobrem dedup cross-file em extratos sobrepostos, síntese
de período em fatura sem `periodo` (`data_vencimento` → tx dates), e
diff de saldo IRPF vs `closing_balance` em 31/12. Estes goldens **não** são
paridade contra `scripts/e3_reconcile.py::main()` — esse golden vem na
Sessão A2 quando `main_with_store(config, store)` for introduzido. Aqui
só validamos comportamento do `E3ReconcilerAdapter` (Caminho B foundation).

**Guardrails de migração** (CI):
- `tests/unit/pipeline/test_no_legacy_stage_names.py` — bloqueia reintrodução
  de identificadores `"E3"`, `"E5"`… em código de produção (pós-Fase 9).
  Default soft-fail; ativar `MATHOMS_ENFORCE_STAGE_RENAME=1` para hard-fail.
- `tests/unit/pipeline/test_stage_spec.py` — garante `STAGE_RENAME_MAP`
  exaustivo e bijetivo.
- `tests/unit/pipeline/test_materialization_bridge.py::TestMappingsComplete`
  — `_STAGE_TO_DIR`/`_STAGE_TO_SUFFIX` cobrem todos os stages relevantes.

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

   test("plano (home)", async ({ page, request }, info) => {
     await ensureLoggedIn(page, request, info);
     await page.goto("/plano");
     await expect(page.getByRole("heading", { name: /meu plano/i })).toBeVisible();
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

**Fixtures em disco (pipeline):** [tests/fixtures/llm_golden/README.md](../tests/fixtures/llm_golden/README.md) — um JSON por estágio LLM; `pytest tests/test_llm_golden.py` valida schemas e conversores (CI já roda via `pytest tests/`).

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
A: **Não** sem anonimização completa e revisão. Padrão: gerador sintético em `tests/fixtures/pdf_generator.py`. Lint custom (6.5D.7) bloqueia CPF real em fixtures. **Segunda fase (planejada):** PDFs reais **anonimizados** versionados, com processo documentado em [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md) — só depois de concluída a cobertura sintética por banco-alvo.

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
