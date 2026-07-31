---
id: ADR-210
type: adr
title: "Saúde do test suite do CI — gates, telemetria e ciclo de vida"
status: Decidido
phase: "Sprint A12 (test health · CI cost)"
date: "2026-05-14"
amended_at: ["2026-05-19", "2026-07-30", "2026-07-31"]
relates_to:
  - "[[ADR-067]]"
  - "[[ADR-093]]"
  - "[[ADR-114]]"
  - "[[ADR-143]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 210"
  - "Saude test suite CI"
  - "Test health policy"
tags:
  - area/ci
  - area/testing
  - area/devex
  - phase/a12
  - status/decidido
  - type/adr
---

# ADR-210 — Saúde do test suite do CI

> **Emenda (2026-07-30) — camada 4, liveness dos compensadores:** a camada 2
> abaixo removeu o trigger `push: main` e declarou que o job `main-smoke` do
> nightly cobriria o buraco. Em 2026-06-15 o nightly foi desabilitado e a
> cobertura sumiu por 45 dias — este texto seguiu afirmando um controle que
> não existia. Camada 4 (§Adendo 2026-07-30) fecha isso gateando a liveness
> do compensador. **Enquanto o `main-smoke` não estiver vivo, a afirmação de
> que `all-green: skipped = pass` é segura não vale.**

## Contexto

Em 2026-05-14, auditoria do CI achou três anti-padrões custando ~3 min do
tempo de PR sem entregar sinal proporcional:

1. **`tests/unit/pipeline/test_no_legacy_stage_names.py`** — parametrize
   19× repetindo scan completo do repo (helper sem cache), e modo
   soft-fail (`print` em vez de `pytest.fail`) cuja env var de hard-fail
   (`MATHOMS_ENFORCE_STAGE_RENAME`) nunca foi setada em workflow.
   Resultado: ~28 s de CI/PR sem dar sinal de correctness.

2. **bcrypt com 12 rounds** em testes via fixtures `auth_client` +
   `ops_yaml`. Em prod é correto (defesa contra força bruta); em teste
   só atrasa setup. ~30-150 chamadas × 0.5-2 s/call no runner do GH
   Actions = **2-4 min** de overhead em backend-tests.

3. **Migration tests de migrations já executadas em prod** rodando em
   todo PR. `test_close_orphan_goals_migration.py`,
   `test_correct_ir_brackets_deducao_migration.py`,
   `test_stage_rename_migration.py`, `test_a73_seed_migrations.py`
   testam código one-shot que não muda mais após o merge inicial.

Investigação também revelou pelo menos um teste explicitamente marcado
como **descartável após cutover** (`backend/tests/test_decisions_migrator.py`,
docstring: "Após a Sprint A7.5, este arquivo + o migrator podem ser
removidos juntos") que sobreviveu meses além do prazo — Sprint A7 foi
entregue em 2026-04-27.

A raiz é organizacional: não há **gate** no fluxo de adicionar teste
que pergunte "esse teste vai dar sinal proporcional ao custo?", nem
**ciclo de vida** para remover testes que perderam função (cutover,
deprecation, soft-fail permanente, migration one-shot).

## Decisão

Adotar política de **saúde do test suite** em três camadas:

### 1. Gate de adoção — `dev/check_test_health.py` (pre-commit + CI)

Script novo bloqueia commit quando detecta anti-padrões catalogados:

| Anti-padrão | Detecção | Sugestão automática |
|---|---|---|
| Parametrize que recomputa helper caro | Helper sem args/sem param na chamada + helper faz I/O ou loop | `@functools.lru_cache` no helper, OU despararametrizar |
| Soft-fail sem hard-fail-env ativo no CI | `os.environ.get('MATHOMS_*')` em path de fail + env não está em `.github/workflows/` | `@pytest.mark.skipif(os.getenv(...) != '1')` |
| Migration test sem marker | `test_*_migration.py` ou import de `alembic.versions.*` sem `@pytest.mark.migration` | Adicionar `pytestmark = pytest.mark.migration` |
| Test pós-cutover órfão | Docstring com `Após a Sprint <id>` cujo cutover já passou | Deletar arquivo + código testado |
| bcrypt prod-grade em test | `bcrypt.hashpw(...)`/`bcrypt.gensalt()` em test individual e conftest sem `_fast_bcrypt_for_tests` | Adotar o fixture autouse session-scope |

Heurísticas conservadoras (falsos negativos OK; falsos positivos custam
crédito do gate). Allowlist via padrão `@functools.lru_cache` no source
do helper, fixture `_fast_bcrypt_for_tests` em `backend/tests/conftest.py`,
e `@pytest.mark.skipif` sobre o env var.

### 2. Marker `migration` + path filter — opt-in para migration tests

`pyproject.toml [tool.pytest.ini_options]` registra marker `migration`.
Testes de migration one-shot recebem `pytestmark = pytest.mark.migration`.
`.github/workflows/ci.yml` step `Run backend tests`:

```yaml
MARKER_FILTER='-m "not migration"'
if [ "${{ needs.changes.outputs.migration }}" = "true" ]; then
  MARKER_FILTER=""
fi
eval pytest backend/tests/ ... $MARKER_FILTER
```

Filtro `migration` no path-filter cobre `backend/alembic/versions/**`,
`backend/alembic/env.py`, `backend/tests/test_*_migration.py`,
`backend/app/models/**`. PR que toca esses paths roda a suíte completa
(sem deselect); PR de feature pura roda só não-migration.

`test_alembic_guardrails.py` (drift schema↔model + idempotência) **não**
recebe o marker — é gate permanente, sempre roda.

### 3. Fixture session-scoped `_fast_bcrypt_for_tests` — bcrypt rounds=4

`backend/tests/conftest.py` adiciona fixture autouse session-scoped que
monkeypatcha `bcrypt.gensalt` para retornar salt com `rounds=4` (mínimo
do bcrypt). Asserts de auth verificam **emparelhamento** hash↔senha; o
work-factor real é responsabilidade do prod (testado por
`test_password_hashing_uses_bcrypt_with_min_rounds` em
`test_auth.py` quando existe).

## Consequências

### Ganhos quantificados (CI ubuntu-latest, observados em 2026-05-14)

| Fix | Antes | Depois | Δ |
|---|---:|---:|---:|
| Fix #1 (cache `_find_occurrences`) — pipeline-tests | 1m16s | ~48s | −28s |
| Fix #2 (bcrypt rounds=4) — backend-tests | 8m19s | ~5min (est.) | **−3min** |
| Fix #3 (migration deselect) — backend-tests | ~20s extra/PR | 0s em PRs não-migration | −20s |
| Removal `test_decisions_migrator.py` | ~0.5s | 0 | −0.5s |

**Total estimado**: tempo de CI por PR típico cai de **~8m30s → ~5m**,
sem perder cobertura real.

### Custos

- **Manutenção do checker** (`dev/check_test_health.py`): ~200 linhas,
  testes futuros podem detectar padrões novos. Baixo overhead.
- **Risco de falso-negativo no marker `migration`**: PR que aplica
  migration mas esquece de tocar `backend/alembic/versions/` deixaria
  o teste pular silenciosamente. Mitigação: filter cobre também
  `backend/tests/test_*_migration.py` (mexer no teste re-ativa).
- **bcrypt rounds=4 em test não testa força do hash em prod**: aceito.
  O teste de força (que `hash_password` usa `bcrypt` com ≥12 rounds em
  ambiente real) deve ser ADR-decoupled — vive em smoke test contra
  staging, não em unit test. Adicionar como follow-up se ainda não
  existe.

### Não-decisão / out of scope

- Não migrar bcrypt para argon2 em prod (decisão maior, fora desta ADR).
- Não eliminar a redundância repository↔use_case↔API (mantém debug
  localizado; auditar caso-a-caso é tarefa de outro track).
- Não cobrir frontend (Vitest local 16s não é caminho crítico).

## Alternativas consideradas

### A) Manter status quo + investir só em hardware do runner

CI runner `ubuntu-latest-large` (4 vCPU → 16 vCPU). Custaria ~$0.064/min
extra × ~5000 min/mês = **$320/mês** sem corrigir as causas. Rejeitada:
dinheiro mascara a dívida técnica.

### B) Job separado para migration tests (não marker)

GH Actions job `backend-migration-tests` gated por path filter.
Equivalente em ganho mas adiciona um job ao gate `all-green`, um cache
extra, e duplicação do setup. Marker `+ if`-step é mais idiomático e
reaproveita o setup já pago pelo `backend-tests`.

### C) Marker progressivo, sem hard-fail no checker

Versão "warning-only" do `check_test_health.py`. Rejeitada: padrões
detectáveis devem virar gate; warnings ignorados são código morto
de processo.

## Plano de adoção

1. **PR único** (este): Fix #1 + Fix #2 + Fix #3 + checker + ADR.
2. **Follow-up curto**: catalogar mais anti-padrões conforme aparecem em
   `check_test_health.py`. Cada padrão novo justificado em commit
   message com link para issue/PR onde foi descoberto.
3. **Audit semestral** (sre-devops + product-manager): comparar tempo
   de CI atual vs baseline ADR-210; revisar markers; remover testes
   pós-cutover detectados pelo checker.

## Adendo 2026-05-19 — Camada 2: FinOps de triggers do CI

### Contexto adicional

Após as 3 camadas de saúde do test suite (acima), medição empírica em 30
runs sucessivas mostrou que o gargalo de custo **não é mais o tempo do
job individual** (backend-tests caiu para ~316s média; lint+pipeline+
frontend somam <270s adicionais), e sim a **duplicação por evento**:

- Cada PR mergeado dispara **2 runs full do CI**: 1× `pull_request` +
  1× `push: main` (após squash).
- O run pós-merge é **redundante** pois:
  - Repository Ruleset `main-protection` exige `All checks green`
    pré-merge — squash linear de PR verde não muda resultado.
  - Sem deploy/release tied ao push:main neste repo (CD não existe).
  - `concurrency.cancel-in-progress: true` + auto-merge `--auto` já
    cobrem corrida entre PRs sequenciais.

Custo medido: PR backend+pipeline típico = **428s billable** × 2 = **856s
por merge**. Cortar o run pós-merge devolve ~50% do consumo de minutos.

### Decisão (Camada 2)

Remover `push: branches: [main]` do `ci.yml`. Substituir cobertura por
**1 job consolidado `main-smoke` em `nightly.yml`** rodando diariamente
às 05:30 UTC (= 02:30 BRT) que re-executa os 4 gates (lint, pipeline,
backend, frontend-checks) contra HEAD de `main`. Janela máxima de
detecção de drift: ~24h, aceitável para solo-dev project sem CD.

Complementar:

- **Cache de `~/.cache/pre-commit`** no job `lint-all` — invalida em
  mudança de `.pre-commit-config.yaml`; economiza ~25-30s/PR no setup
  dos hooks (clone de cada repo de hook + install).
- **Remoção do step explícito `ruff check .`** no `lint-all` — `pre-commit`
  já roda os hooks `ruff` + `ruff-format`. Saving ~3-5s/PR sem perda
  de cobertura.
- **Issue auto-aberta** em falha de `main-smoke` agendado, com label
  `main-smoke-fail` (idempotente: 1 issue aberta por vez).

Gates de cron separados em `nightly.yml` evitam que o smoke noturno
dispare jobs pesados (Lighthouse, cross-browser, visual-full) — cada job
filtra por `github.event.schedule` explícito.

### Ganhos esperados

| Categoria | Antes | Depois | Δ |
|---|---:|---:|---:|
| Minutos por PR mergeado (backend+pipeline) | 14,3 min (2 runs × 7,1) | 7,1 min (1 run) | **−50%** |
| Lint job (com pre-commit cache hit) | 66s | ~36s | −30s |
| Lint job (cache miss) | 66s | ~63s | −3s |
| Cobertura de drift pós-merge | contínua (push:main) | diária (main-smoke 05:30 UTC) | janela +24h |

Combinado: **~52% de redução** no consumo mensal de minutos do CI,
mantendo a Camada 1 (visual em nightly) e a Camada 0 (saúde do test
suite). Budget alert (`.github/workflows/budget-alert.yml`) continua
ativo como guardrail.

### Trade-offs aceitos

1. **Drift cross-cutting que escapa do PR só é detectado em ≤24h.** Risco
   real é baixo: gate de PR já valida contra `origin/main` rebasado
   (CLAUDE.md §"Pre-push drift check"); `cancel-in-progress` impede
   corrida. Se algum dia a janela virar dor, restaurar `push: main` é
   1 linha.
2. **Badge "verde em main" no GitHub atrasa até 24h.** Aceito para
   single-dev project sem visitantes externos no repo dependendo do
   sinal contínuo.
3. **Workflow de release futuro** (release.yml) precisaria disparar o
   gate explícito via `workflow_call`/`workflow_dispatch` ao invés de
   confiar no push-trigger. Quando CD entrar, ajustar.

### Reverter (se Camada 2 virar dor)

```diff
 on:
+  push:
+    branches: [main]
   pull_request:
     branches: [main]
     types: [opened, synchronize, reopened, ready_for_review]
```

E remover/no-op o job `main-smoke` de `nightly.yml`. Mudança totalmente
reversível em 1 PR.

## Adendo 2026-07-30 — Camada 4: liveness dos compensadores

### O que aconteceu

Em 2026-06-15 o `nightly.yml` foi `disabled_manually`. Ficou 45 dias fora do
ar. Nesse período a camada 2 deste documento continuou afirmando, por escrito,
que o `main-smoke` cobria a remoção do `push: main`. Não cobria.

O desligamento não foi dano colateral dos jobs pesados, como pareceu à
primeira vista: dois dos três últimos runs agendados falharam **no próprio
`main-smoke`**, no step "Pipeline tests". Os crons já eram mutuamente
exclusivos por `github.event.schedule`, então visual/e2e nunca poderiam ter
derrubado o smoke. O acoplamento real é outro — **um `state: disabled` no
nível do workflow mata os 6 jobs de uma vez**, e o nightly hospedava não só o
smoke, mas o drill de backup ([[ADR-228]] G2) e o `lineage-eval`.

Três consequências que só ficaram visíveis na investigação de 2026-07-30:

1. **Classe de mudança sem teste algum.** `all-green` aceita `skipped`, e
   `backend-tests` roda `-m "not migration"` em PR. O `main-smoke` era o único
   lugar onde a suíte rodava sem filtro. Sem ele não é "janela de detecção de
   +24h" — é cobertura zero para PR que não bate path filter.
2. **Gate convertido em no-op.** `dev/check_lineage_eval_gate.py` só bloqueia
   se existir Issue `lineage-eval-fail` aberta; quem abre essa Issue é o job
   `lineage-eval` do nightly. Produtor morto ⇒ Issue nunca abre ⇒ o gate passa
   por construção, afirmando cobertura que não houve. **Fail-open silencioso.**
3. **Alerta que apodrece.** A Issue #642 abriu automaticamente em 2026-06-14,
   como projetado, e seguia aberta 46 dias depois. Pior: a trava anti-duplicata
   fazia toda falha nova ser silenciada com "issue já aberta". O mecanismo de
   alerta funcionou; o que falhou foi não haver nada que cobrasse a triagem.

Não é a primeira vez — #638/#647 já haviam tratado uma desativação anterior
pelo mesmo motivo. Reincidência pede remoção de causa estrutural, não religar.

### Decisão (Camada 4)

**Invariante:** remover um gate em troca de um compensador agendado só é
permitido se a **liveness do compensador for ela mesma gateada**. Sem isso,
"temos cobertura noturna" é afirmação que ninguém verifica — e o custo do erro
é falso verde, que é pior que vermelho.

Materializa em `.github/scheduled-workflows.yml` (manifesto declarativo dos 9
workflows agendados, incluindo o `budget-alert.yml` que hospeda o próprio
watchdog) + `dev/check_scheduled_workflows.py`, com quatro sinais:

| Sinal | Detecta | Por que existe |
|---|---|---|
| `S0` | manifesto ≠ `.github/workflows/*.yml` | senão o manifesto apodrece como apodreceu este texto |
| `S1` | workflow não-`active` | o que aconteceu em 06-15 |
| `S2` | sem run agendado dentro da janela | cron que parou, auto-disable por 60d de inatividade, YAML inválido |
| `S3` | Issue de alerta além do limite de idade | teria disparado em 2026-06-21, **antes** do botão ser apertado |

`S2` mede run **iniciado**, não bem-sucedido: falha já tem canal próprio
(Issue), e duplicar alerta treina o operador a ignorar os dois.

**Dois call-sites, classes de trigger distintas.** Gate de PR (step em
`lint-all`) pega o modo de falha observado — o dono seguiu mergeando até #1117
com o detector off; o primeiro PR após 06-15 teria falhado. Cron diário (steps
em `budget-alert.yml`) pega o resíduo: repo quieto e PR docs-only, já que
`lint-all` é `if: any_code`. Ambos são **steps em jobs existentes**, nunca jobs
novos — ver §Custo.

**Waiver datado.** Exceção declarada com `until:` no manifesto degrada as
violações da entrada para warning; vencido o prazo, o waiver **ele mesmo** vira
hard-fail. A exceção não pode apodrecer como apodreceu a Issue que ela cobre.
Escape hatch por label `hotfix`/`ops-override`, senão o PR que conserta o drift
não mergeia.

**A Issue `ops-watchdog` fecha sozinha** quando o report volta vazio. Alerta
que se auto-resolve não apodrece.

### Custo: a alavanca é o número de jobs, não a duração

A medição de 2026-07-30 (julho, 4.587 runs) reordenou o que importa:

| workflow | runs | min/run | min/mês |
|---|---:|---:|---:|
| CI | 914 | 7,5 | 6.837 |
| Security | 917 | 1,4 | 1.320 |
| Auto-update PR branches | 1.055 | 1,0 | 1.055 |
| PR Quality | 924 | 1,0 | 924 |
| Auto-merge watchdog | 646 | 1,0 | 646 |
| **total** | | | **~10.880** (544% de 2.000) |

Quatro workflows marcam exatamente **1,0 min/run** porque o GitHub arredonda
cada job para 1 minuto: os dois pollers rodam em 14s e são cobrados como 60.
Juntos somam 3.945 min/mês — quase 2× o orçamento — para poucos minutos de
computação real. O nightly inteiro custa ~690 min (6%): **desligá-lo cortou 6%
do gasto e 100% da rede de segurança.** Por isso a camada 4 entra como step em
job existente, nunca como job novo.

### Gatilhos objetivos para reabrir a camada 2

Reverter para `push: main` **não** é a resposta ao incidente: cobriria 1 dos 6
jobs (não o drill de DR, não o visual, não o lineage-eval) e trocaria um custo
medido por um problema que continua. Reabrir a decisão quando:

- **repo virar público (A34 G0)** — Actions passa a ser ilimitado e o argumento
  de custo, que é a única razão da camada 2, evapora; ou
- **≥3 drifts/mês em `main`** que passaram pelo gate de PR (drift real, não
  flake) — aí a janela de 24h virou dor mensurável.

### Trade-offs aceitos

1. **PR docs-only não roda o gate** (`lint-all` é `if: any_code`). Coberto pelo
   cron diário. Alternativa — job próprio sempre-on — custaria ~900 min/mês,
   mais que o nightly inteiro.
2. **`S3` não cobre label sem `max_issue_age_days`.** `ci-budget` é crônica por
   design (o workflow reescreve o corpo a cada run); idade ali não é abandono.
3. **Waiver pode ser renovado indefinidamente por um operador determinado.** É
   exceção auditável em git, não impedimento — o objetivo é tornar a decisão
   visível e datada, não impossível.

## Adendo 2026-07-31 (A40.l3) — terceira classe de asserção de render, e uma premissa vencida

**Não reabre a decisão.** A Camada 1 tirou do gate de PR (a) baselines de pixel
OS-dependentes e (b) E2E com backend real. A perna de render admitida pela
A40.l3 não é nenhuma das duas: **sem baseline**, sem Postgres/Redis/Celery/
alembic, fixture mockada (`mockReportPage`), 8 testes (contados com
`npx playwright test <spec> --project=chromium --list`, não estimados). É uma
**terceira classe** — "asserção de render sem baseline nem serviços" — que a ADR
não enumerou.

**Custo — o que foi medido e o que não foi.** Medido local: os 8 testes rodam em
**4,5 s** (5 workers) contra um `next dev` já quente. **Não medido:** o custo em
CI, que é dominado por `playwright install` (cacheado) e pelo primeiro compile do
Turbopack na rota de relatório. A estimativa de trabalho é ~2 min por PR que toca
`changes.outputs.report`, dentro do caminho crítico existente
(`backend-tests`, 9-10 min) ⇒ latência percebida ≈ inalterada. O `timeout-minutes`
do job subiu 7 → 12 para não esconder hang real. **Reavaliar com número real de
CI no primeiro PR que dispare o step** — a base mensal de Actions já está perto do
teto default de `budget-alert.yml` e uma estimativa errada aqui é caro.

**Admitida por path filter, não por label.** Entra como *step* do job
`frontend-checks` gateado por `needs.changes.outputs.report`, e não como job
novo: `frontend-checks` já está em `all-green.needs`, logo o gate bloqueia merge
sem tocar o ruleset. O erro da Camada 1 a evitar aqui é delegar gate a memória
humana — medido: `frontend-e2e` (label `e2e`) ficou **skipped em 12/12** runs
recentes e **não** está em `all-green.needs`, então vermelho lá não impede merge.

**Restrição de ambiente que o step tem de respeitar.** `frontend-checks` é
node-only (sem `setup-python`). O `webServer` do Playwright roda `npm run dev`,
que dispara o lifecycle `predev` → `codegen:check` → `python3
design-tokens/build.py` — ou seja, o step **falharia sempre** sem intervenção. O
step passa `PLAYWRIGHT_WEB_SERVER_COMMAND=npx next dev --turbopack`, que não passa
pelo lifecycle npm; os artefatos de codegen são versionados
(`frontend/src/generated/`, `frontend/src/styles/tokens.css`) e o drift deles já é
gateado pelo pre-commit no job `lint`. Alternativas descartadas: `setup-python` +
deps só para o `--check` (paga setup em todo PR de frontend para verificar o que
outro job já verifica) e `npm run build && npm run start` (o `prebuild` chama o
**mesmo** codegen, e o build completo custa mais que o gate).

**Premissa vencida (não corrigida por este adendo).** A rede de compensação que
a Camada 1 (`frontend-visual-full` em nightly, janela ≤24h + issue automática) e
a Camada 2 (`main-smoke`, que substituiu o `push: main` removido do `ci.yml`)
prometem **não existe desde 2026-06-15**: o workflow `Nightly` está
`disabled_manually`, com os últimos runs agendados em failure em 2026-06-14/15.
`ci.yml:36-37` continua afirmando por escrito que o `main-smoke` cobre o drift.
Ou o owner reabilita **apenas** o cron diário `30 5 * * *` (~84 min/mês), ou a
ADR e o comentário param de alegar cobertura. Reabilitar o nightly inteiro
(~480 min/mês, +24%) não é recomendado: entrega janela de até 24h para um defeito
que o gate de PR pega em 2 min. Registrado como follow-up owner-gated em
`docs/sprint/A40/lanes/A40-l3-janela-canonica-fluxo.md`.

## Referências

- CLAUDE.md §Code style › Testes — comandos canônicos e fixtures.
- `.github/workflows/ci.yml` job `changes.outputs.migration` + step
  `Run backend tests` `MARKER_FILTER`.
- `.github/workflows/nightly.yml` job `main-smoke` — safety net Camada 2.
- `.github/workflows/budget-alert.yml` — FinOps guardrail diário.
- `dev/check_test_health.py` — heurísticas e exit codes.
- `backend/tests/conftest.py` — `_fast_bcrypt_for_tests` fixture.
- ADR-067 — coverage progressivo (frontend).
- ADR-093 — stage rename (origem do soft-fail).
- ADR-114 — code style baseline (lint cycle).
- ADR-143 — methodology = code (princípio análogo: testes ≡ código,
  têm ciclo de vida).
