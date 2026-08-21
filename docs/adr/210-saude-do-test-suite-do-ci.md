---
id: ADR-210
type: adr
title: "Saúde do test suite do CI — gates, telemetria e ciclo de vida"
status: Decidido
phase: "Sprint A12 (test health · CI cost)"
date: "2026-05-14"
amended_at:
  ["2026-05-19", "2026-07-30", "2026-07-31", "2026-08-03", "2026-08-05", "2026-08-08",
   "2026-08-21"]
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

> **Emenda (2026-08-21b) — o gate tem CINCO sinais e o quinto bloqueava merge
> sem estar declarado; e o alerta do próprio vigia apodreceu 21 dias:** varrendo
> os runs de `ci.yml` de 08-05 a 08-21, 19 falhas do step de liveness se dividem
> em 7 `GH` (instrumento mudo), 5 waiver vencido (gate correto) e 7 `S2`
> obsoleta. `GH` não existia no manifesto ("três sinais"), nem na tabela desta
> ADR (quatro), nem no docstring do script — que afirmava o **oposto** do
> código. **Não reabre a decisão** (fail-closed em "não sei medir" segue certo);
> declara o que já bloqueava e conserta o produtor da Issue `ops-watchdog`.
> Detalhe no §Adendo 2026-08-21b.

> **Emenda (2026-08-21) — `S2` reprova PR verde: o watchdog lê `per_page=1` de
> um índice eventualmente consistente:** o gate reprovou o #1548 com
> *"budget-alert.yml: último run há 12d (limite 3d)"* enquanto o workflow estava
> `active` e tinha rodado às 02:25 do mesmo dia — e o mesmo gate passara no
> #1546 90 min antes. A mesma query devolveu **três respostas diferentes em
> minutos** (2026-08-06, 2026-08-14, 2026-08-19). **Não reabre a decisão** — a
> invariante de liveness segue válida e `S2` continua sendo o sinal certo;
> o que está errado é a **medição**. Correção **implementada** em 2026-08-21
> (`per_page=10` + `max`), com a premissa de que a obsolescência é de linha
> medida antes — ver §Adendo 2026-08-21.

> **Emenda (2026-08-08) — o watchdog de duração observa um job só, e o
> "gatilho de 60%" não é avaliável a partir de um run:** o adendo 2026-08-05
> declarou fechado o gap "gatilho de erosão sem emissor" com
> `dev/check_backend_job_duration_drift.py`. Medido agora, `budget-alert.yml`
> o invoca **sem `--job-name`**, então ele roda no default
> `"Backend tests (backend/tests/)"` e observa **um** job — `frontend-checks`
> não tem emissor, e a única forma de avaliar seu gatilho foi arqueologia
> manual em 160 runs via API, o mesmo modo de falha que aquele adendo disse ter
> eliminado. No caminho, a medição derrubou a própria premissa que motivou a
> investigação: `frontend-checks` tem **mediana 6m55s (58% do teto)**, não os
> 9m09s (76%) que o ledger do `ci.yml` citava de um run único perto da cauda.
> **Não reabre a decisão** (o watchdog e a regra do teto seguem válidos);
> corrige o alcance declarado e fixa o método de medição. Detalhe no
> §Adendo 2026-08-08 (b).

> **Emenda (2026-08-08) — a Camada 1 delegava o gate a um label que não podia
> ser aplicado a tempo:** o opt-in por label (`visual`, `print`, `e2e`) só
> funcionava se o label existisse no instante do evento `opened`, porque
> `labeled` não estava em `on.pull_request.types` do `ci.yml` — aplicado
> depois, não redisparava nada e o job ficava `skipping`, verde por omissão.
> `labeled` entra no trigger, com `cancel-in-progress` exceptuado para esse
> evento. **Não reabre a decisão** (o opt-in continua sendo opt-in); torna
> alcançável o que a Camada 1 já assumia como alcançável. Detalhe e custo no
> §Adendo 2026-08-08.

> **Emenda (2026-08-05) — revisão retroativa `sre-devops` do adendo 2026-08-03,
> fecha `OWNER-GATED-active.md` "Revisão sre-devops da política de CI do
> #1160":** o teto de 20min + a regra "~2× a mediana" seguem aprovados, mas o
> gatilho declarado ("reavaliar quando a mediana passar de 60% do teto") não
> tinha emissor — nada calculava essa mediana automaticamente; a única forma
> de notar a erosão foi arqueologia manual em 56 jobs via API. Fechado por
> `dev/check_backend_job_duration_drift.py`, step novo em `budget-alert.yml`
> (mesmo padrão do watchdog de liveness §camada 4: abre/atualiza/fecha issue
> `ci-duration-drift`, não bloqueia merge). Adicionalmente, medido que o `if:`
> de `backend-tests` reusava o filtro `pipeline` (desenhado para
> `pipeline-tests`, que legitimamente precisa de `tests/**`+`scripts/**`) —
> conflando "mudou biblioteca que o backend importa" com "mudou teste/script
> do pipeline que o backend não toca". Medido por grafo de import real (AST,
> não grep — a 1ª passada por regex subcontou): **4** cruzamentos vivos, dois
> deles em código de **produção**, não só teste — `backend/app/services/storage/{db_artifact_store,artifact_retention}.py`
> importam `scripts.pipeline_common` (módulo compartilhado, já documentado no
> CLAUDE.md), e testes importam `tests.fakes`, `scripts.route_documents` e
> `scripts.e2.{banks,registry}` (parsers de banco). Filtro novo `pipeline_lib`
> restringe `backend-tests` a `pipeline/**` + `config/schemas/**` + os 4 paths
> medidos, com `dev/check_backend_pipeline_coupling.py` gateando drift dos dois
> lados (import novo fora do filtro ⇒ falha; entrada do filtro que ninguém
> importa mais ⇒ falha) — sem esse gate a narrowing repetiria a classe de bug
> que o comentário de `dev_tools` no `ci.yml` já nomeia ("allowlist positiva
> falha ABERTA no próximo módulo novo").

> **Emenda (2026-08-03) — a tabela §Ganhos está vencida:** ela afirma
> `backend-tests ≈ 5min`, número de 2026-05-14. A mediana medida em
> 2026-08-03 é **9,9min** — a suíte cresceu 37,5% em testes desde então. O
> adendo 2026-08-03 re-baseliniza e fixa a regra de dimensionamento do
> `timeout-minutes`. Leia os ganhos daquela tabela como histórico do fix,
> não como estado atual.

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
Os comentários do `ci.yml` continuavam afirmando a cobertura por escrito; essa
metade foi executada em 2026-08-08 (#1293 no bloco `on:` e no job
`frontend-visual`, #1300 no filtro `report:` do job `changes`) e o
`PULL_REQUEST_TEMPLATE.md` saiu junto — nenhum texto do repo alega mais
auto-trigger do gate visual. **A metade do owner segue aberta:** reabilitar
**apenas** o cron diário `30 5 * * *` (~84 min/mês). Enquanto isso, a cobertura
de pixel do relatório existe só nos PRs que lembrarem do label `visual` —
custo medido em 2026-08-07: 10 baselines de seção driftaram ~2-3 meses sem
sinal (#1290). Reabilitar o nightly inteiro
(~480 min/mês, +24%) não é recomendado: entrega janela de até 24h para um defeito
que o gate de PR pega em 2 min. Registrado como follow-up owner-gated em
`docs/sprint/A40/lanes/A40-l3-janela-canonica-fluxo.md`.

## Adendo 2026-08-03 — re-baseline do `backend-tests` e a regra do teto

**Não reabre a decisão.** Executa o item 3 do §Plano de adoção (audit
comparando tempo de CI atual vs baseline) e corrige um número vencido.

### O que aconteceu

O PR #1157 levou 12m16s no `backend-tests` e foi **cancelado por timeout**
(teto 12min). O diff não toca `backend/` — mexe em `dev/`, `tests/`,
`Makefile`, `docs/`. Não é bug de filtro: o job é
`if: backend == 'true' || pipeline == 'true'` e `tests/` cai no filtro
`pipeline`, porque `backend/` importa `pipeline/`. O job devia rodar; o teto
é que estava apertado.

O próprio #1157 subiu o teto para 20min para se desbloquear, e registrou por
escrito que **"por que a suíte dobrou desde maio é investigação separada"**.
Este adendo é essa investigação. Ele não muda o teto — confirma que 20min é
o número certo e diz por quê, que é o que faltava para o bump não ser cego.

### Medição (56 jobs `backend-tests` via API, mai-a-ago por janelas)

| janela | mediana do job |
|---|---:|
| 2026-05-10..20 | 6,33min |
| 2026-06-10..20 | 7,88min |
| 2026-07-10..20 | 9,81min |
| 2026-07-25..08-03 | ~9,9-10,0min (máx. sucesso 10,97min) |

**A causa não é regressão de performance.** Comparando o log de um run de
maio com um de agosto:

| | maio | agosto | Δ |
|---|---:|---:|---:|
| testes | 2192 | 3015 | **+37,5%** |
| passo pytest | 343,8s | 518,2s | +50,7% |
| custo por teste | 0,157s | 0,172s | **+9,6%** |

Os +823 testes vêm de 103 arquivos novos (213 → 314 arquivos) das sprints
A34-A40 — crescimento difuso, sem culpado único. Os ~9,6% de deriva por
teste são o custo de setup por teste (recreate-per-test do SQLite), não um
teste patológico.

**Não há o que otimizar estruturalmente** (medido com `--junit-xml` + `-n 4`,
espelhando o runner de 4 vCPU):

- setup do job ~30s de ~10min; o orçamento **é** o passo pytest
- 432 arquivos empacotados em 4 workers → desbalanço **1,00×**
- arquivo mais pesado 32s contra caminho crítico de 290s ⇒ `--dist loadgroup`
  não pina gargalo
- teste mais lento **2,38s**; os 30 mais lentos somam ~40s de 311s

### Decisão: o teto é detector de *hang*, dimensionado a ~2× da mediana

`timeout-minutes` existe para matar processo travado (deadlock, retry
infinito, espera de rede), não para policiar performance — hang não termina
20% mais devagar, ele não termina. Todos os outros jobs do `ci.yml` já
seguem ~2× ou mais; só o `backend-tests` havia derivado para **1,21×**:

| job | mediana | teto | folga |
|---|---:|---:|---:|
| `backend-tests` (antes) | 9,93min | 12 | **1,21×** |
| `frontend-checks` | 4,68min | 12 | 2,56× |
| `pipeline-tests` | 2,02min | 12 | 5,94× |
| `lint-all` | 2,41min | 5 | 2,07× |

Os 20min que o #1157 já aplicou **ficam** — restauram a convenção. A assimetria
decide: subir o teto custa **0 min faturado** em regime normal (timeout só bila
tempo real); o falso vermelho custa `all-green` stale + merge manual, além de
ensinar o operador a re-rodar job vermelho sem ler.

Confirmação empírica no run do #1160 (que toca `ci.yml` e por isso roda a suíte
**sem** o deselect de `migration`): 3106 testes, passo pytest 10m02s, job
10m51s. Isso é **90% do teto antigo** de 12min contra **54% do novo** — o teto
de 12 teria reprovado esse run também, sem nenhuma relação com o diff.

### Sharding e `pytest-split` — rejeitados pelo custo, coerente com camada 4

Dividir em 2 shards de ~5,5min: `ceil(5,5)×2 = 12` min faturados contra 10
hoje, ⇒ **~+2min por disparo**. O job dispara em **61%** dos runs de CI
(33 de 54 amostrados) ≈ ~550 disparos/mês ⇒ **~+1.100 min/mês** num orçamento
já em 544% de 2.000. É a mesma conta da camada 4 (§Custo: a alavanca é o
número de jobs) e da §Alternativas (B). Reavaliar **se o repo virar público**
(A34 G0) — Actions passa a ilimitado e o argumento de custo evapora, como já
registrado nos gatilhos da camada 2.

### Anti-recorrência: `--durations=25` no passo

A investigação acima custou rodar a suíte local e baixar log de maio para
reconstruir o que o pytest imprime de graça. O passo passa a rodar
`--durations=25`: zero minutos, e a próxima erosão do teto começa com dado
em vez de arqueologia. **Regra para a próxima vez:** se a mediana passar de
12min (= 60% do teto novo), medir por esse output antes de mexer no número —
e só bumpar se o crescimento for de volume, como foi aqui.

### Trade-offs aceitos

1. **Hang no `backend-tests` agora queima 20min em vez de 12.** Evento raro;
   20 min faturados uma vez é mais barato que falso vermelho recorrente.
2. **O teto volta a erodir** (~+1,2min/mês no ritmo atual). Fixo em número
   absoluto, qualquer teto erode; o que muda é haver medição embutida e
   gatilho declarado (mediana > 12min).
3. **Os ~9,6% de deriva por teste não foram atacados.** Abaixo do ruído de
   runner (±2min entre 9,0 e 12,3 na mesma semana); virar projeto de
   otimização de fixture exige sinal maior que esse.

## Adendo 2026-08-08 — o opt-in por label vira alcançável

**Não reabre a decisão.** A Camada 1 escolheu tirar do gate de PR os jobs de
pixel e o E2E com backend real, e trocá-los por opt-in via label. O que este
adendo corrige é que **o opt-in não tinha como ser exercido depois do
`opened`**: `on.pull_request.types` listava `[opened, synchronize, reopened,
ready_for_review]`, então aplicar o label num PR já aberto não emitia evento
algum para o `ci.yml`, e o job seguia `skipping` — verde por omissão. O gate
funcionava só para quem lembrasse do label no segundo exato da criação do PR.
Foi um dos mecanismos que deixaram `report.print.pdf.png` congelada num error
boundary por ~3,5 meses e 10 baselines de seção acumularem drift por 2-3 meses.

### Decisão

1. `labeled` entra em `on.pull_request.types` do `ci.yml`.
2. `concurrency.cancel-in-progress` passa a
   `${{ github.event.action != 'labeled' }}`.

O item 2 não é cosmético. Com `cancel-in-progress: true` incondicional,
aplicar um label com run em voo cancelaria os ~7 jobs — inclusive um
`backend-tests` no minuto 9 de ~10 — e reiniciaria do zero. Minuto cancelado
é faturado e cada reinício ainda paga o piso de 1 min por job; duas labels
seriam dois ciclos. Com a exceção, o run do label fica PENDING e começa quando
o anterior terminar.

### O custo que fica, e por que não dá para pagar menos

Todo label aplicado depois da criação do PR passa a custar **um ciclo de CI
completo** — não só os jobs que o label pede. **Medido no PR #1315** (label
`visual` aplicada 28s depois do `opened`, runs 31257143839 e 31257164016):
**~29 min faturados** no ciclo extra, somando os 9 jobs não-skipados
(`backend-tests` 11,8 · `frontend-checks` 6,9 · `frontend-visual` 4,0 ·
`pipeline-tests` 2,1 · `lint-all` 1,8 · `go-test` 1,5 · `go-lint` 0,4 ·
`changes` 0,2 · `all-green` 0,1). Ou seja: **4 min do job que se queria, ~25 min
de acompanhamento**. É a razão de a orientação continuar sendo abrir o PR já
com o label — e o número que o owner precisa para decidir se a Camada 1 vale
mais que um gate por path filter, dado que a base mensal de Actions já roda
perto do teto default do `budget-alert.yml`.

Fazer o run do label pular os
demais jobs seria mais barato e é **fail-open**: `all-green` aceita `skipped`
nos jobs de que depende, logo um run em que tudo skipa reportaria
`All checks green: success` e sobrescreveria um vermelho legítimo do run
anterior no mesmo SHA (o required check do ruleset olha o último). Aplicar um
label viraria caminho para mergear código quebrado. O run completo é o preço
de não abrir esse caminho.

Três atenuantes medidos: (a) o GH cancela runs PENDING do mesmo grupo quando
outro entra na fila, independente da flag — N labels em sequência custam 1 run;
(b) um `synchronize` posterior engole o pending sem perda, porque o run do push
já enxerga o label em `pull_request.labels`; (c) **não há cascata do labeler
automático** — `actions/labeler@v5` e o size-labeler em `pr-quality.yml`
escrevem com o `GITHUB_TOKEN` default, e evento emitido por ele não dispara
workflow (guard de recursão do GH); além disso `visual`/`print`/`e2e` não estão
em `.github/labeler.yml`, que só define as 10 `area:*` + `dependency`.

### O que este adendo NÃO conserta

`frontend-visual`, `frontend-print-visual` e `frontend-e2e` continuam **fora**
de `all-green.needs` — vermelho neles não bloqueia merge. Rodar é pré-condição
de gatear, não gatear. A medição do §Adendo 2026-07-31 (`frontend-e2e` skipped
em 12/12 runs) tinha duas causas somadas; esta emenda remove uma. Ligar o gate
de fato depende de os jobs terem sinal confiável primeiro — no caso do E2E, dos
17 testes `@critical` vermelhos hoje.

## Adendo 2026-08-08 (b) — o watchdog observa um job, e como medir a série

### O que aconteceu

O ledger de `frontend-checks` no `ci.yml` afirmava que o step `Run Vitest` era
"a terceira medição seguida em que cresce sozinho (1m49s → 3m12s → 3m29s)".
Investigado (PR #1332), o salto não existe — mas o caminho até essa conclusão
expôs dois limites desta ADR.

### Limite 1 — o emissor de drift cobre um job, não a classe

O §Adendo 2026-08-05 fechou `OWNER-GATED` "Revisão sre-devops da política de CI"
constatando que o gatilho "reavaliar quando a mediana passar de 60% do teto"
**não tinha emissor**, e que "a única forma de notar a erosão foi arqueologia
manual em 56 jobs via API". A correção foi `dev/check_backend_job_duration_drift.py`
como step em `budget-alert.yml`.

Medido em 2026-08-08: `budget-alert.yml:285` chama o script **sem `--job-name`**,
e `DEFAULT_JOB_NAME` é `"Backend tests (backend/tests/)"`. O watchdog observa,
portanto, **um** job; `frontend-checks` não tem emissor, e avaliar seu gatilho
custou arqueologia manual em **160 runs** via API — o mesmo modo de falha, no
job seguinte.

E o resultado mostra por que o emissor precisa ser automático: o gatilho de 60%
**não é avaliável a partir de um run**. Medida a duração do job em 40 runs
`success/success`, `frontend-checks` dá **mediana 415s = 6m55s (58% do teto de
12min)**, p25 390s, p75 486s (8m06s, 68%), máx 573s (9m33s, 80%). O ledger do
`ci.yml` afirmava "9m09s · ~24% de folga, abaixo dos ~40% confortáveis" a
partir de **um** run — que teve cache MISS do Chromium e caiu perto da cauda.
Pela mediana a folga é **42%**, dentro da faixa confortável; o aperto é real no
p75 (32%) e na cauda (20%), não na tendência central. Um watchdog com a série
teria dito isso; um humano lendo um run disse o contrário.

O script já é parametrizável (`--job-name`), então o alcance é configuração,
não código. **Estender o watchdog a `frontend-checks` fica deferido**, sem dono
nem data: o `budget-alert.yml` abre/atualiza issue por job e a política de
ruído de N issues concorrentes não foi decidida aqui. Condição de retomada: a
mediana de `frontend-checks` passar de **60% do teto** — o gatilho que esta ADR
já declara, hoje em 58%, ou seja, a um passo — ou o watchdog ganhar agregação
multi-job. Enquanto não for feito, esta ADR **não** afirma cobertura de erosão
para nenhum job além de `backend-tests`.

### Limite 2 — medição de duração exige filtrar por conclusão

Série de step de CI só é legível depois de descartar runs incompletos. Em 160
runs deste repo, **40 não são `success/success` e 39 desses são `cancelled`** —
quase 25% da amostra. `cancel-in-progress` corta o step no meio e o deixa com
36s/51s/125s; misturar cancelado com completo fabrica salto e queda que não
existem. Foi o que produziu a "tendência" do ledger, junto com dois vieses de
leitura: a sequência real era 3m31s → 3m12s → 3m29s (**diminuiu** antes de
subir), e o "1m49s" era de 2026-05-16, copiado verbatim por 12 semanas de
reescritas sem run citado nem re-medição.

Regra que passa a valer para qualquer afirmação de duração nesta ADR e nos
ledgers de `ci.yml`: **mediana + p25/p75 de ≥10 runs `success/success`, nunca
dois pontos**, e toda medição em comentário leva `run <id>` + data. Filtrados,
os 121 runs `success/success` dão mediana 202s, p25–p75 191–210s, e spread de
**83s dentro de um único dia** — o "+17s" flagrado era ~1/5 do ruído do dia.

### Limite 3 — `check_test_health.py` não olha o frontend

O gate da §Decisão 1 varre `test_*.py` (`d.rglob("test_*.py")`) e nunca
inspecionou o Vitest. Nenhum anti-padrão "escapou" dele; o escopo sempre foi
pytest. E o driver de custo do frontend **não é anti-padrão**: o step escala
com o número de ARQUIVOS (cada um monta um jsdom próprio e re-executa
`frontend/tests/setup.ts` inteiro — ~700–840ms de CPU antes de qualquer teste
rodar; a execução dos testes é 24% do custo). De 102 para 153 arquivos, a
custo por arquivo constante (1,26s → 1,32s), a contagem sozinha projeta 194s
contra 202s medidos.

Dividir teste em mais arquivos é boa prática que por acaso custa CI — **gate
seria o instrumento errado**. O que falta é orçamento visível, e ele fica
registrado como número: **~1,3s de wall-clock de CI por arquivo de teste de
frontend, mesmo vazio**. Os dois levers foram medidos e nenhum é config-flip:
`isolate: false` hangea (>9min, estado global do setup não sobrevive a
compartilhar ambiente) e `environment: "node"` quebra 30/30 em `tests/lib/`
porque o setup toca `window.matchMedia` e `Element.prototype` sem guarda
(~5% de ganho se guardado).

## Referências

- CLAUDE.md §Code style › Testes — comandos canônicos e fixtures.
- `.github/workflows/ci.yml` job `changes.outputs.migration` + step
  `Run backend tests` `MARKER_FILTER`.
- `.github/workflows/nightly.yml` job `main-smoke` — safety net Camada 2.
- `.github/workflows/budget-alert.yml` — FinOps guardrail diário.
- `dev/check_test_health.py` — heurísticas e exit codes (escopo: `test_*.py`).
- `dev/check_backend_job_duration_drift.py` — watchdog de erosão; `--job-name`
  default cobre só `backend-tests` (§Adendo 2026-08-08 (b)).
- `.github/workflows/ci.yml` job `frontend-checks` — ledger com a série medida
  do `Run Vitest` e o preço marginal por arquivo de teste.
- `backend/tests/conftest.py` — `_fast_bcrypt_for_tests` fixture.
- ADR-067 — coverage progressivo (frontend).
- ADR-093 — stage rename (origem do soft-fail).
- ADR-114 — code style baseline (lint cycle).
- ADR-143 — methodology = code (princípio análogo: testes ≡ código,
  têm ciclo de vida).

## Adendo 2026-08-21 — `S2` mede o elemento errado

O sinal `S2` ("sem run agendado dentro da janela") resolve a idade do último run
por [`dev/check_scheduled_workflows.py`](../../dev/check_scheduled_workflows.py):

```
repos/{repo}/actions/workflows/{filename}/runs?event=schedule&per_page=1
```

e confia no **primeiro elemento**. Medido em 2026-08-19, chamadas idênticas a
essa query devolveram, em poucos minutos: `2026-08-06`, depois `2026-08-14`,
depois `2026-08-19` (estável na repetição). O índice de runs do GitHub serve
resultado obsoleto de forma intermitente, e `per_page=1` não tem como perceber.

**Efeito observado:** o `lint-all` do #1548 falhou com *"budget-alert.yml:
último run há 12d (limite 3d)"* às 13:08; o `budget-alert.yml` estava `active` e
com run `schedule` bem-sucedido às 02:25 do mesmo dia, e o mesmo gate reportara
`OK (9 workflows agendados)` no #1546 às 11:40. Descartada a hipótese de
workflow recriado: os runs recentes e a query do checker resolvem para o
**mesmo** `workflow_id` (`276754849`).

**Segunda ocorrência, 2026-08-21 — corrobora que a causa é a query, não o workflow.**
O `lint-all` do #1590 (docs-only, sem tocar `.github/`) reprovou com *"stale.yml:
último run há 90d (limite 3d)"*, enquanto `stale.yml` estava `active` e com run
`success` às 06:44 do mesmo dia. **Workflow diferente do #1548**, mesma
patologia — o que descarta hipótese específica de `budget-alert.yml` e aponta
para a query compartilhada. O diagnóstico barato que separa este caso de "waiver
vencido trava o repo": se **só o seu** PR reprova e o diff não toca `.github/`, é
o índice; se **todos** reprovam, é waiver. O #1591 passou no mesmo job minutos
depois. Destravado com `gh run rerun --failed`, **sem escape hatch** — o
`ops-override` que o parágrafo abaixo teme não foi usado, e por isso a causa
sobreviveu ao registro.

**Classe do defeito.** É falso **vermelho**, não falso verde — não fere a
invariante desta camada, que existe contra o falso verde. Mas custa o que o
§Custo tenta economizar: o PR reprova, alguém re-roda, e o caminho barato de
desbloquear é o escape hatch `hotfix`/`ops-override`, que **apaga a causa do
registro** — precedente #1508, contornado sem investigação.

**Correção proposta (não implementada, owner-gated):** pedir uma página pequena
(`per_page=10`) e tomar `max(run_started_at)`, em vez do primeiro elemento. Não
muda a semântica do sinal nem o que ele detecta; só impede que uma cabeça
obsoleta vença a leitura. `S0`/`S1`/`S3` não usam esse endpoint e ficam intactos.

**Implementada em 2026-08-21, com a premissa medida antes.** A correção acima só
funciona se a obsolescência for de **linha** (cabeça velha, resto da página
fresco); se a réplica servisse a **página inteira** velha, `max` não salvaria
nada e o fix nasceria inerte. Medido contra a API real neste dia, no repo:

| Consulta | Amostra | Leituras obsoletas |
|---|---|---|
| `per_page=1`, elemento `[0]` | 130 chamadas (4 workflows) | **2** (`2026-08-06` em `auto-update-prs.yml`; `2026-08-17` em `automerge-watchdog.yml`) |
| `per_page=10`, `max(run_started_at)` | 60 chamadas (2 workflows) | **0** |

A obsolescência é de linha — a premissa se sustenta. As duas leituras sujas
caíram em workflows **diferentes**, o que corrobora a causa compartilhada (a
query) contra hipótese específica de workflow.

**Quarta e quinta ocorrências, 2026-08-21, no mesmo PR (#1568).** Dois runs de CI
distintos acusaram workflows **distintos**: `[S2] stale.yml: último run há 14d
(limite 3d)` (run 32492357488) e `[S2] auto-update-prs.yml: último run há 14d
(limite 2d)` (run 32491419416) — com um `OK` limpo do mesmo gate minutos depois.
Somando #1548 (`budget-alert.yml`) e #1590 (`stale.yml`), são **três workflows
diferentes** flagrados. Um alvo só ainda admitiria "o índice daquele workflow
está ruim"; três alvos e um `OK` intercalado deixam só a query. Por isso o teste
de regressão usa **nome de workflow genérico**: fixar um alvo nomeado fecharia a
instância, não a classe. Regressão em
[`tests/dev/test_check_scheduled_workflows.py`](../../tests/dev/test_check_scheduled_workflows.py):
a fixture é a forma medida (cabeça velha + linhas frescas), e reverter para
`per_page=1`/`runs[0]` derruba 2 dos 5 testes.

**Risco residual declarado:** se algum dia a réplica servir página inteira
obsoleta, `max` volta a ler velho e o falso vermelho reaparece. A amostra de 60
não exclui esse caso — só mostra que ele não ocorreu. O sintoma é idêntico ao já
registrado aqui, e o diagnóstico barato do parágrafo anterior (só o seu PR
reprova + diff não toca `.github/` ⇒ é o índice) continua valendo.

**O que esta correção NÃO fecha — `GH` tem a mesma raiz e continua sem retry.**
`_run()` faz **uma** `subprocess.run` sem retry: falha transiente (5xx, timeout,
rate-limit secundário) devolve `None`, e `_unreachable()` transforma isso em
violação **bloqueante** dentro do CI. É a mesma fraqueza de leitura única que
produziu o `S2` obsoleto, manifestada no outro sinal — e o `max` não faz nada por
ela: melhora *qual elemento* se lê, não *quantas tentativas* se faz. O §Adendo
2026-08-21b abaixo declarou o sinal e mediu 7 ocorrências de `GH` na mesma
janela; o que segue aberto é a **política de leitura** (retry com backoff em
`_run`, ou manter o hard-fail assumido). Quem ler "correção implementada" e
concluir que o gate parou de reprovar PR verde vai se surpreender na primeira
falha transiente de `gh` — este PR se limita ao elemento lido.

## Adendo 2026-08-21b — o quinto sinal, e o vigia que não vigiava a si mesmo

O §Adendo anterior fechou a **medição** do `S2`. Medindo a frequência para
dimensionar o risco, apareceram dois defeitos que ele não cobre.

### O que a varredura mediu

Runs de `ci.yml` entre 2026-08-05 e 08-21 (o cap de 1000 runs da API corta aí;
07-22→08-05 varrida à parte deu **zero**). Frame: `conclusion=failure` **ou**
`run_attempt>1`, jobs lidos com `filter=all` — sem isso, tentativa re-rodada com
sucesso **esconde** a falha, e a arqueologia subconta.

| Categoria | Jobs | Quando | Defeito? |
|---|---|---|---|
| `GH` — `gh` não respondeu | **7** | 08-11, 08-12 (×3), 08-17 (×3) | sim, transitório |
| Waiver vencido (`nightly` + `security`, 08-13) | 5 | 08-14 | **não** — gate correto |
| `S2` leitura obsoleta | **7** | 08-19 (×1), 08-21 (×6) | sim, corrigido no #1603 |

Os 7 `S2` são inequívocos: os quatro workflows acusados estavam `active` com
runs `schedule` densos (`stale.yml` diário às 06:44; `auto-update-prs` e
`automerge-watchdog` a cada ~30min). Acusações de 90d, 14d, 6d e 3d são
impossíveis. Em 08-21 foram 6 falhas contra 68 runs do dia — **~9%**, com um run
acusando dois workflows de uma vez. Não é ocorrência isolada.

### `GH` é o quinto sinal, e bloqueava merge sem decisão escrita

Quando `gh` não responde **dentro do CI**, `_unreachable()` emite violação
bloqueante — de propósito: degradar em silêncio recriaria o fail-open. A
postura está certa e **fica**. O que estava errado é que ninguém decidiu isso
por escrito: o manifesto declarava "três sinais", a tabela §camada 4 declarava
quatro, e o docstring do script afirmava *"offline/sem `gh` degrada para pass
com warning"* — verdadeiro só **fora** do CI, e falso exatamente na questão em
disputa. Um hard-fail em check obrigatório documentado apenas por comentário
inline é a inversão da invariante desta camada ("afirmação que ninguém
verifica"). Agora `GH` está nomeado no manifesto e no docstring.

A mensagem dele também afirmava causa que não tem como saber — *"cheque
permissions do job"* —, **errada em 7 de 7** casos medidos: `_run` descarta
`returncode` e `stderr`, então blip, rate-limit e permissão são
indistinguíveis daqui. Reescrita para declarar o que se sabe e nomear
`gh run rerun --failed` como desbloqueio sancionado. Pelo mesmo motivo, a linha
de resumo do gate parou de oferecer `hotfix`/`ops-override` como terceira opção
de menu: é exceção de **política**, e usá-la para instabilidade de API apaga a
causa do registro (precedente #1508) — que foi como a causa do `S2` sobreviveu
duas ocorrências antes de alguém medir.

### O alerta do vigia apodreceu 21 dias

Medido em 2026-08-21: a Issue `ops-watchdog` **#1122** estava aberta desde
07-31, contendo **apenas** duas linhas `WAIVED` do `nightly.yml` — que a própria
legenda dela classifica como *"informativo, não bloqueia"*.

A causa é o acoplamento entre corpo e gatilho: o step de `budget-alert.yml`
fecha a Issue quando o relatório é vazio, e `render_markdown` renderizava
violações **waived**. Com o waiver do `nightly` válido até 2026-10-15, o
relatório nunca ficava vazio e o auto-close **não podia** disparar. O alerta que
"se auto-resolve para não apodrecer" apodreceu pelo mesmo mecanismo da #642 —
desta vez no próprio vigia.

Corrigido em `_worth_an_issue`: exceção já aceita (`WAIVED`) e instrumento mudo
(`GH`) não abrem nem sustentam Issue. `GH` fica de fora por razão própria —
ruído de API não pode iniciar o relógio de rot do `S3`. Medido antes/depois: o
relatório sai de 2 linhas `WAIVED` para **vazio**, então o próximo run do cron
fecha a #1122.

### Deferido — a entrada `ops-watchdog`, com precondição

Falta cobrar a triagem dessa Issue: entrada `ops-watchdog` com
`max_issue_age_days: 3` sob `budget-alert.yml`. **Não entra nesta leva porque
não pode**: com a #1122 aberta há 21 dias, o gate reprova (`exit=1`, medido), e
como ele roda no próprio PR, **o PR que contém a entrada não consegue mergear a
si mesmo**. A precondição é o filtro acima estar em `main` e o cron ter fechado
a #1122. Dono: próxima sessão que tocar este gate. Condição de retomada:
`gh issue list --label ops-watchdog --state open` vazio.

### Deferido — redistribuir os sinais por escopo (revisão `sre-devops`)

`S0` e waiver vencido são calculados **do disco**, sem `gh`, e são propriedade
**do PR**. `S1`/`S2`/`S3` são propriedade **do repositório** — nenhum PR as
causa nem conserta — e concentram 100% da flakiness: das 14 falhas transitórias
medidas, 7/7 dos `GH` e 6/7 dos `S2` miravam workflows que um gate de PR
restrito ao escopo do PR nem leria. **13 das 14 somem sem uma linha de retry.**

Duas travas que o desenho precisa respeitar, e que a versão ingênua viola:

1. **`budget-alert.yml` é raiz de confiança e fica bloqueante.** Ele é o
   produtor da Issue `ops-watchdog` e está no manifesto por auto-cobertura. Se
   o `S1`/`S2` dele sair do caminho bloqueante: ele morre → o cron não roda →
   a Issue nunca abre → `S3` não vê nada → **o gate passa por construção**. É
   textualmente a consequência #2 do §Adendo 2026-07-30, aplicada ao vigia.
2. **A entrada `ops-watchdog` é pré-requisito, não acessório.** Sem ela, mover
   `S1`/`S2` para o canal de Issue é fail-open puro. É ela que troca veredito
   *instantâneo e flaky* por veredito *datado e durável*.

O retry com backoff, avaliado como correção primária, foi **rebaixado a
endurecimento de transporte** das ~3 chamadas que sobrariam. Ele tem três
pré-condições próprias, medidas: (a) **deadline global** — `timeout=30` × ~25
chamadas dá 750s de pior caso contra o `timeout-minutes: 4` do `lint-all`, hoje
já em 2m04s (52% do teto); (b) ordenar o **waiver antes** da releitura, senão o
"retry só no caminho da violação" dispara em 100% dos runs, porque o `nightly`
desabilitado produz `S1`+`S2` sempre; (c) **classificar** `returncode`/`stderr`,
já que 403-permissão é determinístico e não deve ser re-tentado — e os `GH`
clusterizam (08-12 ×3, 08-17 ×3), padrão compatível com rate-limit secundário,
onde retry cego **piora**.

Condição de retomada declarada: **A34 G0** (repo público). Com Actions
ilimitado, o desenho final não é nem redistribuição nem retry, e sim um **job
próprio, não-required**, rodando `S1`/`S2`/`S3` completos — a restrição que
força tudo isso a caber num step de check obrigatório é o budget.

### Follow-ups menores medidos aqui

- `ci.yml:430` afirma *"observado 44s; 4min dá ~5× buffer"* para o `lint-all`,
  medido em **2m04s**; `ci.yml:519` afirma que o step de liveness *"custa ~2s"*,
  medido em 8-10s. Comentário de custo vencido faz o próximo ajuste de timeout
  partir da premissa errada.
- A legenda de sinais dentro de `budget-alert.yml` precisa **encolher** (não
  crescer): pós-filtro, `WAIVED` e `GH` não podem mais aparecer naquela Issue.
  Fica para a leva que já tocar `.github/workflows/**` — PR que toca esse path
  starva a fila enquanto é cabeça do trem ([[ADR-322]] §Emenda 2026-08-08).
- Falso-vermelho custa mais que um `rerun`: `ci_advance_automerge_train.py`
  tira o PR do trem em `required_workflow_failed`, exigindo novo ciclo de
  re-arme.
