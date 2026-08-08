# Testing — Guia de Contribuidor

> **Objetivo:** dar a um contribuidor novo tudo que ele precisa para rodar, escrever, debugar e atualizar testes do Mathoms AI — sem chamar ninguém. Onboarding em horas, não dias ([[ADR-067]]).

---

## TL;DR

```bash
# Backend (pytest)
source .venv/bin/activate
pip install -r requirements-dev.txt
MATHOMS_FERNET_KEY="NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA=" pytest backend/tests/ -q

# Pipeline (pytest)
MATHOMS_FERNET_KEY="NwHpLJlLGSeC7NIS6gfVdVSYh_pObKqY4G_CwkQ1kuA=" pytest tests/ -q

# Pipeline offline (mesmo orquestrador do worker) — stage individual via CLI
# (A3.cli · ADR-150; artifacts em DB → requer MATHOMS_DATABASE_URL)
python -m pipeline.orchestrator run-stage <stage> \
  --workspace <path> --run-id <id> --workspace-id <id>

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
backend/tests/test_openapi_snapshot.py  # A6f.2 — snapshot diff determinístico (docs/reference/api/v1/openapi.json)
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
tests/fixtures/llm_golden/      # JSONs saída LLM (E1, E1.5, E1.6, E2-LLM, informes anuais, CRLV/apólices) vs `pipeline/llm/schemas`
tests/test_llm_golden.py        # parse + validators + conversores dos JSONs acima
tests/fixtures/e2_real_pdf_anon/  # Fase 2 opcional — PDFs reais redigidos + README
tests/test_e2_real_pdf_regression.py  # `route_to_parser` em cada `*.pdf` da pasta (vazia = no-op)
tests/test_e3_golden_execution.py  # E2 fixture → E3 run → asserts
tests/test_e4_golden_execution.py  # E3 → E4 (+ misto receita/despesa + baseline E1.5)
tests/test_e5_golden_execution.py  # E3→E4→E5 run → analise_financeira + E5 schema (+ misto receita/despesa + baseline E1.5)
tests/test_e5n_golden_execution.py  # E5 + generate_narratives → narrativas; + tenant com cônjuge (`ana_cenarios`)
tests/pipeline_golden_asserts.py  # asserções partilhadas (ex.: qa_log.md)
tests/test_e2_synthetic_pdf_parsers.py  # registry E2 × PDF; todos os bancos com assert dedicado (C6, Bradesco, … Caixa; Quinto Andar fatura)
tests/test_e0_route_edges.py tests/test_e7_edges.py tests/test_e5_e6_e5n_edges.py  # 7D.1/7D.2 — helpers de borda (E0/E7/E5/E6/E5.N)
tests/fixtures/pdf_generator.py # 6.5F.12 — 14 códigos BankCode; registry com `_draw_*` (C6, Bradesco, BTG, … Quinto Andar)
dev/check_pipeline_boundaries.py # P1 — imports proibidos em pipeline/
dev/check_enum_migration_parity.py # A40.l19 · ADR-357 §7 — membro de enum Python ⊆ tipo declarado nas migrations (AST dos dois lados; ler o DB de teste seria auto-referente)
pipeline/cli_run_stage.py     # CLI run-stage do orchestrator (A3.cli · ADR-150)
backend/tests/regressions/      # 6.5E.8 — 1 test por bug histórico (BUG-NNN)
tests/test_design_tokens_build.py       # F9 — 20 tests (tokens build + parity)
tests/test_report_layout_codegen.py     # F9 — 14 tests (codegen + schema)

frontend/tests/components/report/       # F9 — testes do relatório nativo React
  ReportShell.test.tsx                  # 9 tests (shell + cards)
frontend/tests/lib/reports.test.ts      # F9 — 8 tests (API client)
frontend/tests/hooks/useReportData.test.tsx  # F9 — 6 tests (hook)
```

---

## Tenancy isolation

Duas suítes complementares protegem multi-tenant:

- [backend/tests/test_multi_tenant_isolation.py](../../backend/tests/test_multi_tenant_isolation.py)
  — domínio-a-domínio. Para cada agregado (members, categories,
  documents, vault, pipeline runs, reports, transactions, LLM config,
  notifications), seeda 2 workspaces com dados distintos e prova que
  endpoints autenticados como user A nunca devolvem payload de user B.

- [backend/tests/integration/test_tenancy_isolation.py](../../backend/tests/integration/test_tenancy_isolation.py)
  — estrutural. Roda 3 gates:
  1. **Fuzz por path-param**: itera todas as rotas
     `/api/v1/workspaces/{workspace_id}/...` e tenta acesso cross-tenant;
     toda response ≠ 403/404/410/409/405/400 (sem 200) é vazamento.
  2. **AST scan**: toda função decorada `@router.get/post/...` que
     declara parâmetro `workspace_id` precisa ter
     `Depends(get_current_workspace)` (ou `require_*role` derivado).
     Whitelist de exceções em `_TENANCY_EXEMPTIONS` (sunset endpoints
     ADR-129/154 que sempre retornam 410).
  3. **Path-id cross-tenant**: GET `/documents/{id}/extract-json` de
     user B autenticado como A retorna 403/404 — nunca 200.

Quando adicionar endpoint novo `/workspaces/{workspace_id}/...`:
- A dependência `Depends(get_current_workspace)` é obrigatória.
- O AST scan vai falhar sem ela; o fuzz vai falhar com 200.
- Para sunset (410-only), some o nome em `_TENANCY_EXEMPTIONS`.

LGPD self-service (`/api/v1/me/data-export*`, `/me/delete-request`) tem
suíte dedicada em [backend/tests/test_lgpd_self_service.py](../../backend/tests/test_lgpd_self_service.py)
— inclui audit trail, TTL de download, cooldown de export, soft-then-hard
delete via cron e rejeição cross-tenant do `request_id`.

---

## Como rodar

### Backend

```bash
source .venv/bin/activate
MATHOMS_FERNET_KEY="<chave>" pytest backend/tests/test_<modulo>.py -q
```

**DB isolation strategy:** *recreate-per-test* sobre SQLite in-memory. Documentado em [`backend/tests/conftest.py`](../../backend/tests/conftest.py). Cada test vê schema limpo.

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

**Regra de uso ([[ADR-089]] + [[ADR-212]]):**
- Testes de `ReconciliationService`, `CategorizationService` e calculadoras
  (`CashFlowAggregator`, `PatrimonioCalculator`, etc.) **devem usar
  `InMemoryArtifactStore` injetado explicitamente** — sem fixtures de arquivo.
  `WorkspaceContext.get_artifact_store()` levanta `RuntimeError` se store
  não foi injetada ([[ADR-212]] PR3b).
- Testes de integração que validam round-trip DB usam `DBArtifactStore` +
  sync fixture factory (ver [backend/tests/test_db_artifact_store.py](../../backend/tests/test_db_artifact_store.py)).
- `DiskArtifactStore` **foi deletado** em [[ADR-212]] PR3b — não existe em testes nem em código de produção.

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
paridade contra `scripts/reconcile_transactions.py::main()` — esse golden vem na
Sessão A2 quando `main_with_store(config, store)` for introduzido. Aqui
só validamos comportamento do `E3ReconcilerAdapter` (Caminho B foundation).

**Guardrails de migração** (CI):
- `tests/unit/pipeline/test_no_legacy_stage_names.py` — bloqueia reintrodução
  de identificadores `"E3"`, `"E5"`… em código de produção (pós-Fase 9).
  Default soft-fail; ativar `MATHOMS_ENFORCE_STAGE_RENAME=1` para hard-fail.
- `tests/unit/pipeline/test_stage_spec.py` — garante `STAGE_RENAME_MAP`
  exaustivo e bijetivo.
- `tests/unit/pipeline/test_artifact_stores.py::test_legacy_descriptive_parity`
  — todo par `(legacy, descritivo)` de `STAGE_RENAME_MAP` que produz artifact
  tem ambas as keys em `_STAGE_TO_SUFFIX` com o mesmo sufixo (o antigo
  `test_materialization_bridge.py::TestMappingsComplete` foi deletado com
  `_STAGE_TO_DIR` em [[ADR-213]]).

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

**Onde vivem:**
- `frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts-snapshots/` — 28 PNGs: estratégico (S1–S3, S7–S10) + apêndices (APP_A, APP_B, APP_D, APP_E) + cover + as 2 variantes de `S_parecer` (`parcial`, `retido`), cada um em light + dark. Linux-only via job `frontend-visual` (suffix `-linux.png`).
- `frontend/tests/e2e/reports/__snapshots__/` — print PDF baseline.

> **O spec tem 32 testes mas só 28 baselines.** `S4` e `APP_C` estão nas listas
> do spec e **não** produzem PNG: a fixture `medium` não as faz montar
> (`real_estate` ausente; `cenarios_conjuge` é `{}` — a chave existe, só vazia —
> e sem `programa_milhas`), então as duas retornam `null` por hide-when-empty e
> caem no skip. Não é buraco acidental: está declarado em
> `SECTIONS_NOT_IN_MEDIUM_FIXTURE`, e qualquer OUTRA seção que não monte
> **falha** em vez de pular verde (PR #1295). `S4` segue coberta
> estruturalmente pelo `sections.fixtures.smoke.visual.spec.ts` em 4 fixtures;
> `APP_C` não tem cobertura em teste algum.

> **A contagem acima envelhece.** Ela já esteve errada nas duas direções ao mesmo
> tempo: dizia 48 quando havia 52, e os 52 incluíam 20 baselines órfãs de modos
> removidos (Tático/ADR-151, USA/ADR-168) que nada comparava —
> `--update-snapshots` reescreve o que os testes produzem e **nunca poda o
> resto**. Removidas no PR #1292 (T\*/U\*) e #1295 (`S4`/`APP_C`, que eram de
> abril, de quando a fixture ainda ligava as seções). **O mecanismo que as
> deixou apodrecer continua vivo:** nada cruza PNG em disco com teste existente,
> então um modo removido no futuro produz órfãs de novo sem sinal. Ao mexer
> aqui, confira com `ls <dir> | wc -l` em vez de confiar no número escrito.

### O gate de inventário é o irmão em texto — leia-o antes de rebaselinar

Diff de PNG não é revisável em PR, e é por isso que **rebaselinar é a saída
natural quando um componente desaparece**: a baseline só encolhe e nada nomeia o
que saiu. Foi assim que o card "Alocação · Atual vs Alvo" ficou ~3 meses fora do
relatório (#906 → congelado no #1290) e que a baseline do PDF congelou um error
boundary por 3,5 meses.

[[ADR-370]] fecha a classe com `report-inventory.@critical.spec.ts` +
`report-inventory.expected.json`: conjunto de cards por seção, em texto, varrido
da estrutura do DOM. Card que some **falha por nome**. (Contagem de propósito não
escrita aqui — o JSON é a fonte, pelo mesmo motivo da ressalva de contagem acima.)

Use-o como instrumento de atribuição: **se o inventário não mudou, a diferença de
pixel é estilo/layout, não conteúdo.** Se mudou, o diff diz qual card.

Duas regras que não são convenção, são mecânica:

- **`MATHOMS_UPDATE_INVENTORY=1` só ACRESCENTA.** Card novo é regenerável; card
  que sai exige **apagar a linha à mão**, e a linha apagada aparece no diff. Sem
  isso o arquivo seria a baseline PNG em texto — um comando que lava perda de
  cobertura. O modo update também reprova remoção, para não dar verde local e
  vermelho no CI.
- **A fixture `medium` é superfície completa.** *"A fixture não tem o dado"* não
  é justificativa para card ausente — é exatamente o defeito de origem. Ausência
  legítima é remoção de produto, justificada no PR.

Roda no step `Report render gate` de `frontend-checks` (dentro de
`all-green.needs`), **sem label e sem path filter** — ao contrário do gate de
pixel, que é opt-in por label.

### Por que **não** rodar local em macOS

`sections.snapshots.visual.spec.ts` está documentado:
> _Atualização: ... em CI Linux, nunca local em macOS — pixel rendering diverge._

Font hinting + antialiasing + chart.js canvas variam entre Darwin e Linux mesmo no mesmo Chromium. Baselines geradas em macOS quebram CI Linux e vice-versa.

### Workflow correto (`workflow_dispatch`)

```bash
# 1. Estar numa branch agent/* com a mudança visual já commitada e pushada.
git push origin agent/<slug>/<ts>

# 2. Disparar regen em runner Linux:
gh workflow run CI \
  --repo davidrobert/mathoms \
  --ref agent/<slug>/<ts> \
  -f run_visual=true \
  -f update_visual_baselines=true

# 3. Aguardar conclusão (~5-7min). O job termina `success` — se falhar,
#    é falha REAL, leia o log.
#    (Este doc afirmava até 2026-08-08 que `failure` era "esperado" com
#    --update-snapshots. Nunca foi intencional: o step `Locate generated
#    baselines (debug)` rodava `find frontend/tests` já dentro de
#    `frontend/`, saía 1 em path inexistente e derrubava o job DEPOIS de
#    o Playwright passar. Corrigido no #1277.)
gh run view <run-id> --json conclusion --jq .conclusion

# 4. Baixar artefato:
gh run download <run-id> \
  --repo davidrobert/mathoms \
  --name report-visual-baselines-generated \
  --dir /tmp/baselines

# 5. Identificar baselines mudadas (não copiar tudo às cegas):
SRC=/tmp/baselines/e2e/reports/sections.snapshots.visual.spec.ts-snapshots
DST=frontend/tests/e2e/reports/sections.snapshots.visual.spec.ts-snapshots
for f in $SRC/*.png; do
  n=$(basename $f)
  cmp -s "$f" "$DST/$n" 2>/dev/null || echo "CHANGED: $n"
done

# 6. Copiar SÓ as que mudaram (o passo 5 já as nomeou) e commitar JUNTO
#    com o código da mudança visual:
for n in <lista-do-passo-5>; do cp "$SRC/$n" "$DST/$n"; done
git status --short   # tem de listar exatamente as do passo 5
git add $DST/
git commit -m "test(visual): refresh N baselines pós-<mudança>"
```

**Antes do `git add`, abra os PNGs e olhe.** Um `--update-snapshots` verde não
prova nada sobre o conteúdo: ele grava o que existe, inclusive uma tela de erro.
A baseline do PDF ficou 3,5 meses sendo um screenshot do error boundary
("Algo deu errado ao renderizar esta página"), commitada em 2026-04-27 sem
ninguém abrir o arquivo — o gate comparava crash contra relatório e teria ficado
**verde** se o relatório voltasse a crashar do mesmo jeito.

**Justifique cada PNG no corpo do PR** — qual commit mudou o quê. Sem isso, um
PR de rebaseline é laundering de drift: ele apaga a evidência de uma regressão
com a mesma keystroke que apaga a de uma mudança intencional. Para atribuir sem
depender do olho, diff estrutural linha-a-linha (assinatura grayscale grosseira +
`difflib.SequenceMatcher`) aponta as bandas inseridas/removidas e resiste ao
antialiasing do canvas do chart.js.

**Abra o PR já com o label `visual`.** `labeled` não está em
`on.pull_request.types` do `ci.yml`, então label aplicado depois **não redispara
o CI**: o job fica `skipping` e o PR passa por omissão — o gate não valida a
baseline que você acabou de trocar.

### A baseline do PDF é uma família à parte

`frontend/tests/e2e/reports/__snapshots__/report.print.pdf.png` **não** sai pelo
fluxo acima: é outro job (`frontend-print-visual`), outro input de dispatch e
outro artefato. Trocar `run_visual` por `run_print` no comando de cima não
funciona — são flags distintas.

```bash
gh workflow run CI --ref agent/<slug>/<ts> \
  -f run_print=true -f update_print_baseline=true
gh run download <run-id> --name report-print-baseline-generated --dir /tmp/pdf
cp /tmp/pdf/report.print.pdf.png frontend/tests/e2e/reports/__snapshots__/
```

Depois de commitar, **rode o job outra vez sem `update_print_baseline`**
(`-f run_print=true` sozinho). Com a flag ligada o spec grava e retorna verde
sem comparar nada: um run verde de regeneração não prova que a baseline nova
passa no gate — só que ela foi escrita.

> **O rosa da capa na baseline não é o produto.** O job converte o PDF com
> `pdf-to-png-converter` (pdfjs), que não resolve o gradiente do cover nem
> `background-clip: text`: a capa sai magenta e o subtítulo "Pessoal e
> Patrimonial" some. Verificado em 2026-08-08 passando o **mesmo** PDF por
> pdfjs e por Poppler (`pdftoppm -png`) — o segundo sai correto, azul-marinho e
> com subtítulo. A baseline é fiel ao que o instrumento vê, que é o que o diff
> compara. Se quiser inspecionar o PDF de verdade, use `pdftoppm`, não o PNG do
> artefato.

Este gate compara **só a primeira página**, por pixel. Conteúdo ausente da
página 12 é invisível para ele — foi assim que o export truncou por meses. Quem
cobre conteúdo é `print-text.@critical.spec.ts` (camada de texto via
`pdftotext`), que roda no CI default dentro do step `Report render gate`.

### Tolerância — `maxDiffPixelRatio` proporcional

Spec usa `maxDiffPixelRatio: 0.025` (2.5%) em vez de `maxDiffPixels` absoluto. Razão: chart.js canvas tem variance natural de 1-2% entre runs no mesmo runner Linux (antialiasing de paths, tooltip positioning, font hinting). Threshold absoluto de 200px (~0.007% em S2) gerava flake crônico.

**Cuidado ao combinar com `maxDiffPixels` absoluto:** Playwright usa `Math.min(absoluto, ratio×area)`. O piso absoluto anula o ratio em imagens grandes. Use **só** ratio.

### Layout PR + regen no MESMO PR (anti-débito)

PRs que alteram dimensões/layout do `<article>` do report devem:
1. Fazer a mudança em código.
2. Disparar `workflow_dispatch` com `update_visual_baselines=true` na mesma branch.
3. Commitar os baselines refreshed no mesmo PR.

Anti-padrão histórico (#147, #148, #150, #151, #153, #155, #169, #160): cada um disse "snapshot precisará ser regenerado em CI" e mergeou sem fazer. Resultado: gate visual ficou crônicamente vermelho em main, e PRs subsequentes herdaram débito que não introduziram. PR #174 (2026-05-10) fechou ~24 baselines de drift acumulado.

### Hooks/cards consumidores de API — guard obrigatório

Hooks que fazem `setX(resp.X)` sem guard quebram o relatório inteiro via ErrorBoundary quando shape parcial chega (mock incompleto, backend degradado, retorno parcial em alta carga). Padrão correto:

```ts
setSuggestions(Array.isArray(resp?.suggestions) ? resp.suggestions : []);
```

Já aplicado em `useSuggestions`/`useDecisions` (PR #165). Aplicar a todo hook novo que consume lista do backend.

### PR template checkbox

Toda PR que altera `frontend/tests/e2e/reports/*-snapshots/` deve marcar:

```markdown
- [ ] Baselines refreshed via `workflow_dispatch` em runner Linux (não local em macOS)
- [ ] Diff contra baselines anteriores é **intencional** (change visual esperada)
- [ ] Refresh está no MESMO PR da mudança visual (não follow-up)
- [ ] Testei mentalmente light + dark
```

### CODEOWNERS

`.github/CODEOWNERS` requer review de designer (ou founder) para mudanças em snapshots:

```
/frontend/tests/e2e/reports/*-snapshots/ @davidrobert
```

---

## Premium tier LLM em E2E — F6.5F.11 (ADR-070)

**Default (PR checks):** LiteLLM mockado. Custo $0. Rápido.

**Fixtures em disco (pipeline):** [tests/fixtures/llm_golden/README.md](../../tests/fixtures/llm_golden/README.md) — um JSON por estágio LLM; `pytest tests/test_llm_golden.py` valida schemas e conversores (CI já roda via `pytest tests/`).

```python
# backend/tests/fixtures/llm_mock.py expõe `mock_llm_service()` que retorna
# outputs Pydantic válidos por stage (E1, E1.5, E2-llm).
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

Ver [ADR-070](../DECISIONS.md#adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in) para rationale.

---

## FAQ

**Q: Por que tests/ pipeline e backend/tests/ separados?**
A: Pipeline é package Python independente (pode ser usado standalone); backend é FastAPI que orquestra. Cada um tem suas dependências e sua infra de teste.

**Q: Por que MSW e não jest.mock?**
A: MSW intercepta no nível de fetch/XHR — testa o código real de `lib/api.ts` em vez de stubs. Mais perto do comportamento real, menos chance de drift.

**Q: Por que recreate-per-test e não transactions+rollback?**
A: Ver docstring de [`backend/tests/conftest.py`](../../backend/tests/conftest.py). TL;DR: SQLite in-memory é instantâneo (~5ms) e isolation é trivial; otimizações são prematuras.

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
| Inventário de cards (só ACRESCENTA) | `cd frontend && MATHOMS_UPDATE_INVENTORY=1 npx playwright test tests/e2e/reports/report-inventory.@critical.spec.ts --project=chromium` |
| Sobe stack de teste (pg+redis)     | `./scripts/test_backend_up.sh`                             |
| Reset DB de teste                  | `./scripts/test_backend_up.sh --reset`                     |
| Derruba stack                      | `./scripts/test_backend_down.sh`                           |

---

## Critérios de aceite por fase da migração A6

Checklist canônico de gates de teste para cada fase do Sprint A6
(migração infra+domínio). Usado como referência durante PR review de
qualquer slice; cópia viva do que foi sendo entregue em `CHANGELOG` e
validado em CI. Origem: plano mestre de migração A6 §7 (absorvido aqui
em 2026-04-21).

### Infra — Fase 1.5 (StageSpec + orchestrator limpo)

- [ ] `validate_full_order(FULL_ORDER)` passa sem exceção
- [ ] `validate_full_order` falha com `AssertionError` se um stage é inserido depois do seu consumidor
- [ ] `test_materialization_bridge_mappings_complete` passa (todos os stages em `_STAGE_TO_DIR` e `_STAGE_TO_SUFFIX`)
- [ ] E2-faturas processa apenas faturas; E2-extratos processa apenas extratos (flags corretas)
- [ ] `import scripts.pipeline_common` sem `FIN_WORKSPACE_ROOT` não levanta `SystemExit`

### Infra — Fases 2-4 (DBArtifactStore + cutover) — **encerradas pós-[[ADR-212]] (2026-05-14)**

> Histórico preservado para contexto. Gates fechados; `DiskArtifactStore` /
> `MaterializationBridge` / flag `MATHOMS_USE_DB_ARTIFACTS` / coluna
> `use_db_artifacts_override` foram removidos. Rollback do cutover:
> [runbooks/pipeline_rollback.md](runbooks/pipeline_rollback.md).

- [x] `DBArtifactStore` round-trip preserva dados exatos (read ∘ write = identity)
- [x] Sessão SQLAlchemy injetada no `__init__`; store nunca cria sessão própria
- [x] Celery task: commit só após run completa; sem sessão órfã em caso de exception
- [x] Pipeline E2→E5 produz E5 íntegro no DB (golden em `tests/test_e{3,4,5}_golden_execution.py`)
- [x] [[ADR-212]] PR3b removeu `DiskArtifactStore`; PR4 removeu flag + coluna override
- [x] `document_pipeline_sync.py` sem regex em nome de arquivo
- [x] Modo incremental usa `pipeline_last_run_at IS NULL`
- [x] `DBArtifactStore.write()` recebe `document_id` FK correto
- [x] Todos os parsers em `scripts/e2/banks/*.py` retornam `BankStatement` (não `dict`)
- [x] Extract stages distintos com UNIQUE constraint independente
- [x] Reset destrutivo virou service-layer (`backend/app/services/internal_ops/pipeline_reset.py`)
- [x] `GET /reports/{id}/data` lê do DB via `artifact_id` ([[ADR-131]])
- [x] Validação JSON-schema universal via hook pós-write em `DBArtifactStore.write` ([[ADR-212]] PR3a)

### Domínio — Fase 5 (Money + dataclasses)

- [ ] `Money.brl("0.1") + Money.brl("0.2") == Money.brl("0.3")` (sem erro de float)
- [ ] `Money(amount=0.1)` levanta `TypeError` (ADR-090)
- [ ] `Money.of(0.1, "BRL")` levanta `TypeError` (factory também rejeita float)
- [ ] `Money.of("1", "JPY").amount == Decimal("1")` (0 casas — respeita `CURRENCY_PRECISION`)
- [ ] `Money.of("1.234", "BRL").amount == Decimal("1.23")` (2 casas, quantização)
- [ ] `Money(amount=Decimal("1"), currency="XYZ")` levanta `ValueError` (moeda não registrada)
- [ ] Round-trip: `Transaction.from_dict(t.to_dict()) == t`
- [ ] `dataclasses.replace(t, category=c)` funciona; nenhum uso de `Transaction(**{**t.__dict__, ...})`
- [ ] `InvestmentStatement` e `BankStatement` são value objects: `frozen=True`, testáveis sem disco
- [ ] Property-based tests em `Money` passam (soma associativa, sem drift acumulado)

### Domínio — Fases 6/7 (Reconciliation + Categorization services, ISP)

- [ ] `ReconciliationService(ReconciliationConfig(...)).reconcile(statements)` sem I/O de disco (ADR-089)
- [ ] Service NÃO importa `StageConfig` (teste estático: grep em `reconciliation_service.py`)
- [ ] Testes unitários cobrem: duplicata exata, duplicata por proximidade (±3 dias), transferência interna, gap temporal
- [ ] Fixture de teste: `ReconciliationConfig(tolerance_days=3, ...)` em uma linha (sem mock de StageConfig)
- [ ] Testes de integração do stage usam `InMemoryArtifactStore` — sem fixtures de arquivo
- [ ] `CategorizationService(CategorizationRules(...)).categorize(transactions)` sem disco
- [ ] Golden: output novo == output legado (mesmo workspace de referência)

### Domínio — Fase 8 (FinancialAnalyzer decomposto)

- [ ] Cada uma das 6 calculadoras tem testes unitários independentes (sem disco, sem globals)
- [ ] `financial_analyzer.main(config, store)` sem disco
- [ ] `StageConfig.from_context(ctx)` produz objeto imutável; mutação levanta `ValidationError` (Pydantic frozen)
- [ ] `StageConfig.empty()` disponível para testes que não precisam de config real
- [ ] Sprint timebox respeitado: cada sprint ≤ 4 semanas com calculadora completa e testada
- [ ] Golden: output novo == output legado

### Domínio — Fase 9 (stage renaming completo, pós-A6d)

- [ ] `test_rename_map_covers_all_legacy_names` passa antes de qualquer rename
- [ ] `test_rename_map_targets_exist_in_registry` passa
- [ ] `test_rename_map_is_bijective` passa
- [ ] `test_migration_upgrade_renames_all_known_stages` passa
- [ ] `test_migration_downgrade_restores_legacy_names` passa
- [ ] `test_no_legacy_stage_name_in_code` passa para todos os nomes legados
- [ ] `alembic upgrade head` → `alembic downgrade -1` sem erro
- [ ] Backup do banco criado antes da migration em produção
- [ ] Grep de sobrevivência retorna zero ocorrências para identificadores legados (incluindo `.md` files)
- [ ] `pipeline/stages/` e `scripts/` contêm apenas arquivos com novos nomes descritivos
- [ ] `MaterializationBridge` removido (zero usos confirmados por grep antes de remover)
- [ ] `_init_config()` global removido de todos os scripts (zero chamadas confirmadas)
- [ ] CLAUDE.md sem menções a `e*_` como convenção de naming de stage
- [ ] `docs/reference/ARCHITECTURE.md` reflete estado final (stages com novos nomes)
- [ ] ADR-093 formalizado em `docs/DECISIONS.md`
- [ ] Zero regressão em CI

### Métricas de sucesso — fim de Fase 4 (marco infra)

| Métrica | Meta |
|---------|------|
| `processed/` criados em novas runs web | 0 |
| Regex de nome de arquivo em `document_pipeline_sync.py` | 0 ocorrências |
| Sessões SQLAlchemy sem `close()` ou context manager | 0 |
| Testes de protocolo `ArtifactStore` passando | 100% |
| Tempo de CI (suite completa) | ≤ baseline atual × 1.5 |
| Golden fixtures passando (E2→E5) | 100% |
| Workspaces em produção com `use_db_artifacts=True` | ≥ 1 (piloto) |

### Métricas de sucesso — fim de Fase 9 (marco domínio)

| Métrica | Meta |
|---------|------|
| Identificadores legados (`"E2"`, `"E3"`, etc.) em código Python | 0 |
| Identificadores legados em valores de DB (`pipeline_artifacts.stage`) | 0 |
| `float` em cálculos monetários (`pipeline/domain/`) | 0 |
| Cobertura de testes em `pipeline/domain/` | ≥ 80% |
| Cobertura de testes em services (Reconciliation, Categorization, FinancialAnalyzer) | ≥ 80% |
| Scripts com `_init_config()` global | 0 |
| Tempo médio de pipeline E2→E5 (benchmarked) | ≤ baseline ± 5% |
| `MaterializationBridge` usos | 0 |

---

## Ver também

- [`docs/BACKLOG.md#f65--frontend-testing--qa`](../BACKLOG.md#f65--frontend-testing--qa) — tasks de F6.5
- [`docs/DECISIONS.md#adr-063--hardening-fintech-em-sub-fase-65d`](../DECISIONS.md#adr-063--hardening-fintech-em-sub-fase-65d) — ADR de hardening fintech
- [`docs/DECISIONS.md#adr-064--backend-hardening-em-sub-fase-65e`](../DECISIONS.md#adr-064--backend-hardening-em-sub-fase-65e) — ADR de backend hardening
- [`docs/DECISIONS.md#adr-067--test-infrastructure-em-sub-fase-65f`](../DECISIONS.md#adr-067--test-infrastructure-em-sub-fase-65f) — ADR de test infrastructure
