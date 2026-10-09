---
id: runbook-python-dependencies
type: runbook
title: "Runbook — Dependências Python (pip-tools lockfile com hashes)"
status: ativo
date: "2026-05-29"
relates_to:
  - "[[ADR-254]]"
  - "[[ADR-249]]"
  - "[[ADR-248]]"
tags:
  - type/runbook
  - area/infra
  - area/python
  - area/devops
---

# Runbook — Dependências Python

> Fonte de verdade da decisão: [[ADR-254]] (pip-tools `--generate-hashes`).
> Este runbook é o **passo-a-passo operacional** para adicionar, atualizar e
> regenerar dependências Python do Mathoms.

## Modelo de arquivos

| Arquivo | Papel | Editável à mão? |
|---|---|---|
| `requirements.in` | Deps diretas do **pipeline** (pdfplumber, anthropic, numpy…) com constraints `>=` | ✅ sim |
| `backend/requirements.in` | Deps diretas do **backend web** (fastapi, sqlalchemy, celery, alembic…) | ✅ sim |
| `requirements.lock` | **Lock combinado** (raiz + backend) com `--hash=sha256:...` em toda linha — fonte do build determinístico | ❌ NÃO — gerado |
| `requirements-dev.txt` | Extras de dev/test (pytest-cov, reportlab) — **sem hashes** em V1 | ✅ sim |

**Decisão-chave (desvio do design original de [[ADR-254]]):** existe **um único
`requirements.lock` combinado**, não dois (`requirements.lock` +
`backend/requirements.lock`). O motivo é que `anthropic` é dep compartilhada
(a raiz puxa direto; o backend puxa via `instructor`/`litellm`), e resolver os
dois `.in` em locks separados produz `ResolutionImpossible` por causa do range
de `jiter` exigido pelo `instructor`. A resolução combinada deixa o resolver
escolher uma versão de `jiter` que satisfaz ambos. ADR-254 §Decisão foi
atualizada para refletir isso.

## Onde cada artefato é consumido

| Consumidor | Arquivo | Modo |
|---|---|---|
| `Dockerfile` (build de imagem prod) | `requirements.lock` | `pip install --require-hashes` — **Python 3.12** (digest-pinado) |
| CI — jobs de teste (`ci.yml`, `nightly.yml`, smoke, monthly) | `requirements.lock` | `dev/ci_ensure_venv.sh` (`uv pip install --require-hashes`) + test-deps inline (reportlab/xlwt/pytest-cov/pytest-xdist/fakeredis/`schemathesis<4`) — **Python 3.13**. A paridade com prod é de **versões de pacote**, não de interpretador — e os extras **rebaixam o lock** (`starlette` 1.3.1→0.52.1 a cada run) até existir `requirements-test.lock` ([[ADR-254]] §Emenda 2026-08-12) |
| CI — `security.yml` pip-audit | `requirements.lock` | auditoria de versões pinadas (precisa) — **Python 3.12**, o único job que casa o interpretador de prod (e não executa código) |
| Dev local | `requirements-dev.txt` (via `make dev-bootstrap`, `Makefile:588`; `make onboard` o embute) | `pip install -e . -r requirements-dev.txt` — **não** lista `pytest-xdist`/`fakeredis`/`schemathesis`: ambiente local ≠ CI até o `requirements-test.lock` unificar |

> **Por que CI usa o lock (não os `.in`):** até 2026-06-18 o CI-tests instalava
> dos `.in` loose (`>=`) com cache key só no hash dos `.in`. Resultado: o venv
> cacheado congelava transitivas resolvidas há meses; quando o cache era
> evictado/limpo, o `uv pip install -r requirements.in` re-resolvia para releases
> novas e uma transitiva quebrou o registro de routers (backend-tests vermelho
> repo-wide). Fix: CI instala do `requirements.lock` pinado (`--require-hashes`),
> cache key no hash do **lock**, **sem `restore-keys`** (o fallback de prefixo
> restaurava venv de lock divergente — a armadilha). test-deps puros
> (reportlab/xlwt/pytest-cov/pytest-xdist/fakeredis) seguem inline (fora do lock);
> pinar via `requirements-test.lock` é débito aberto.

## ⚠️ Constraint crítico: gerar o lock SEMPRE em container linux/amd64

**NUNCA rode `pip-compile` no host Mac (arm64).** Wheels com extensão nativa
(`uvloop`, `cryptography`, `pydantic-core`, `playwright`, `numpy`) têm hashes
**diferentes por plataforma**. Um lock gerado em arm64 falha o
`--require-hashes` no build/CI (que rodam linux/amd64), com mensagem de hash
mismatch. O Docker daemon precisa estar UP.

## Tarefa 1 — Regenerar o lockfile (após editar qualquer `.in`)

```bash
docker run --rm --platform linux/amd64 -v "$PWD":/work -w /work python:3.12-slim bash -c "
  pip install -q pip-tools
  pip-compile --quiet --generate-hashes --strip-extras \
    --output-file=requirements.lock \
    requirements.in backend/requirements.in"
```

- `--strip-extras`: remove sufixos `[extra]` (ex.: `uvicorn[standard]`) que o
  `--require-hashes` não aceita; as deps do extra entram resolvidas mesmo assim.
- A ordem dos `.in` no comando não altera o resultado (resolução é conjunta).

## Tarefa 2 — Validar o lock antes de commitar

```bash
docker run --rm --platform linux/amd64 -v "$PWD":/work -w /work python:3.12-slim bash -c "
  apt-get update -qq && apt-get install -y -qq build-essential >/dev/null
  pip install --no-cache-dir --require-hashes -r requirements.lock
  python -c 'import fastapi, sqlalchemy, celery, anthropic, litellm, instructor, pdfplumber, numpy, playwright, asyncpg, psycopg, cryptography; print(\"all core imports OK\")'"
```

Esperado: `all core imports OK` e exit 0. Warnings de botocore do LiteLLM são
benignos.

## Tarefa 3 — Adicionar uma dependência nova

1. Edite `requirements.in` (pipeline) ou `backend/requirements.in` (web),
   adicionando a linha com constraint `>=`.
2. Rode **Tarefa 1** (regenerar) + **Tarefa 2** (validar).
3. Commite `.in` **e** `.lock` no mesmo commit (o hook
   `dev/check_lockfile_sync.py` bloqueia `.in` sem `.lock` correspondente).

## Tarefa 4 — Atualizar versão de uma dependência

1. Suba o constraint no `.in` (ex.: `fastapi>=0.115` → `fastapi>=0.116`), **ou**
   force re-resolução total com `--upgrade`:
   ```bash
   docker run --rm --platform linux/amd64 -v "$PWD":/work -w /work python:3.12-slim bash -c "
     pip install -q pip-tools
     pip-compile --quiet --generate-hashes --strip-extras --upgrade \
       --output-file=requirements.lock requirements.in backend/requirements.in"
   ```
2. Valide (Tarefa 2) e commite ambos.

## Falha: venv cacheado com interpretador ausente

**Assinatura** (jobs `Pipeline tests` / `Backend tests` falhando em 20-40s):

```
error: Failed to inspect Python interpreter from active virtual environment at `.venv/bin/python3`
  Caused by: Python interpreter not found at `/home/runner/work/mathoms/mathoms/.venv/bin/python3`
```

**Não é código.** O `.venv` é derivado de **dois** inputs — o `requirements.lock`
e o **interpretador** — e até 2026-08-11 a cache key só codificava o primeiro.
`uv venv` grava `.venv/bin/python3` como symlink **absoluto** para o interpretador
do runner; quando a frota troca de patch (ex.: 3.13.14 → 3.13.15), o cache
restaura um `.venv` cujo symlink dangla. O antigo guard `[ -d .venv ]` via o
diretório e não recriava; com `cache-hit == 'true'` o install do lock era pulado,
e o job morria no primeiro `uv pip install`.

**Diagnóstico em 1 comando** — compare o `created_at` do venv com a versão do
interpretador nas entradas `setup-uv-*`:

```bash
gh api "repos/davidrobert/mathoms/actions/caches?per_page=100" \
  --jq '.actions_caches[] | select(.key|startswith("venv-")) | [.id,.ref,.created_at,.last_accessed_at] | @tsv'
```

Se houver entrada `setup-uv-…-3.13.X-pruned` com X diferente entre a criação e o
último acesso do venv, é este caso.

**Remediação (ordem importa):**

1. Delete as entradas **por id** (`gh cache delete <key>` por chave pode pegar só
   uma quando o mesmo key existe em refs diferentes):
   ```bash
   gh api -X DELETE repos/davidrobert/mathoms/actions/caches/<id>
   ```
2. **Só depois** re-rode: `gh run rerun <run_id> --failed`.

> **Re-run sozinho NÃO resolve** — restaura o mesmo cache. Foi o que fez o
> incidente de 2026-06-18 (#658) custar duas rodadas de investigação. Deletar
> **não** salva job já em voo (ele já restaurou); cancele e re-dispare esses.
> **Não delete as entradas `setup-uv-*`** — estão sadias, e removê-las encarece
> cada rebuild com re-download de wheels.

**Fix estrutural (2026-08-11, PR de `dev/ci_ensure_venv.sh`):** a key passou a
incluir a versão exata do interpretador (`steps.setup-python.outputs.python-version`)
e os dois steps de install viraram um só, sempre executado, cujo predicado
**executa** o interpretador em vez de testar presença. Um venv restaurado
inutilizável é apagado, reconstruído e reinstalado do lock, com `::warning::`
no log. Se esse warning aparecer mais de ~2×/semana, a key ainda está incompleta
— reabra a investigação.

## Dependabot

Dependabot monitora os `.in` (uma entrada `pip`, em `/`, cobre os dois). Como o
lock é **combinado cross-dir**, o Dependabot **não regenera o `.lock`
automaticamente** — ele abre PR subindo o `.in`, e o `dev/check_lockfile_sync.py`
falha no CI até que alguém rode a Tarefa 1 e adicione o `.lock` regenerado ao
PR. Esse é o gate intencional: upgrade major nunca entra sem revalidação.

### `ignore` de redis — teto do kombu (2026-10-09)

A entrada `pip` ignora `redis>=6.5`. Esse é o teto que o `kombu[redis]`
(via `celery[redis]`) impõe. Sem o `ignore`, o updater pergunta primeiro se
`redis==<último>` resolve. A resposta é não, mas o pip 26.2.1 do updater não
consegue provar: ele desce o `wrapt` até o sdist 1.13.3, cujo build quebra, e o
job inteiro sai `failure` ("Dependabot can't resolve your Python dependency
files"). Foi o estado de 2026-08-31 a 2026-10-09.

- **Quando mexer:** `tests/dev/test_dependabot_redis_ceiling.py` lê o teto do
  kombu instalado pelo lock. No PR que regenerar o lock com outro kombu, ele
  reprova se o teto mudou: ajuste o `versions`, ou apague o `ignore` se o teto
  sumiu.
- **Job do Dependabot vermelho:** rode `gh run view <id> --log`. A tabela
  "Dependencies failed to update" nomeia a dependência. O comando que falhou é
  o `pip-compile -v ... -P <dep>` dela.
- **Reprodução:** use o pip do updater, não o local. A versão está em
  `python/helpers/requirements.txt` do `dependabot-core`, no SHA da imagem
  `dependabot-updater-pip:<sha>` que o log imprime. Com pip 24/25, o mesmo
  `.in` dá `ResolutionImpossible` em menos de 1 min, o que o Dependabot trata
  como `update_not_possible` (verde).

### Uma entrada pip e a família opentelemetry (2026-10-09)

Uma entrada `pip` só, em `/`, cobre `requirements.in` e `backend/requirements.in`:
o log do updater roda `pip-compile ... backend/requirements.in`. A `/backend` saiu
em 2026-10-09. Ela ficou sem job de 07-28 a 10-09 e, no primeiro job, duplicou os
PRs da `/` (#2103≡#2104, #2105≡#2108) e partiu a família opentelemetry entre as
duas (#2101 na `/backend`, #2102 na `/`). O `open-pull-requests-limit` da `/`
subiu de 5 para 8, porque ela passou a cobrir os dois `.in`.

A família `opentelemetry-*` é acoplada por `==`. O sdk 1.Y pede `api==1.Y`, e a
instrumentation 0.Xb pede `semantic-conventions==0.Xb`, que o sdk também pina.
Por isso o núcleo (1.x: api, sdk, exporter) e o contrib (0.Xb:
instrumentation-*) sobem juntos. Um membro sozinho com piso novo pede uma
combinação que o lock não tem, e grupos `pip` por `patterns` nunca produziram PR
agrupado neste repo.

- **Sentinelas:** só `opentelemetry-api` (1.x) e
  `opentelemetry-instrumentation-fastapi` (0.Xb) recebem version update. Os
  outros cinco membros são `ignore` por `update-types`, então security update
  continua abrindo para eles. `tests/dev/test_dependabot_otel_sentinels.py`
  exige uma sentinela por trilha: membro novo no `.in` sem `ignore` reprova.
- **PR da sentinela:** não mergeie sozinho. No mesmo PR, ou num lote humano,
  suba os pisos de **todos** os membros das duas trilhas para a release nova, um
  piso só por trilha, e regenere o lock (Tarefa 1) com `-P` em cada pacote
  `opentelemetry-*` do lock, diretos e transitivos (13 no #2143). No #2143, foi
  preciso `click<8.2` no container, porque com click ≥8.2 o pip-tools escreve um
  `--no-index` falso no header.

### Saúde das entradas do Dependabot (issue `ops-dependabot-red`)

O workflow dinâmico do Dependabot (`dynamic/dependabot/dependabot-updates`) não
tem canal de falha. A entrada pip `/` saiu `failure` de 2026-08-31 a 2026-10-09,
e pip `/backend` e github_actions `/` passaram de 07-28 a 10-09 sem run
agendada — nada no repositório viu. `dev/ci_dependabot_health.py` roda no cron
diário do `budget-alert.yml` e mantém **uma** issue `ops-dependabot-red`, com
`S3` de 10 dias no `.github/scheduled-workflows.yml`. Vale para todas as
entradas, não só as `pip`.

- **Fonte:** as entradas vêm do `.github/dependabot.yml`; as runs, de
  `actions/workflows/<id>/runs?event=dynamic` (últimos 90 dias). Run de entrada
  agendada se chama `pip in /. - Update #N`; rebase de PR traz ` for <deps>` e é
  ignorado. A raiz vira `/.` e o ecossistema usa o nome interno (`npm` →
  `npm_and_yarn`, `github-actions` → `github_actions`, `gomod` → `go_modules`),
  medido em 2026-10-09 sobre 395 runs.
- **vermelho:** as 2 últimas runs concluídas da entrada são `failure` (uma só
  pode ser instabilidade do registry). Diagnóstico: "Job do Dependabot vermelho"
  na subseção acima.
- **sem run:** a última run é mais velha que o limite do `schedule.interval`
  (daily 3 · weekly 10 · monthly 40 dias). Em `network/updates`, *Check for
  updates* na entrada: entrada que nunca completou job deixa de ser agendada.
  Mudar o `dependabot.yml` também dispara todas.
- **sem correspondência:** nenhuma run casa com a entrada, ou o ecossistema / o
  intervalo não tem medição. Vira linha na issue, nunca pass calado. Ecossistema
  novo sem tradução reprova antes, em `tests/dev/test_ci_dependabot_health.py`.
- **PR parado:** PR do Dependabot aberto há mais de 5 dias, contados pela cadeia
  de substituição (subseção abaixo). A linha traz as vagas ocupadas da entrada e
  marca **lotada** quando elas chegam ao `open-pull-requests-limit`.
- **Triar = fechar à mão**, com comentário apontando o PR do conserto. Não espere
  a próxima run passar: o `S3` reprovaria o `Lint` do próprio PR do conserto (a
  classe do impasse de 2026-10-08). O cron só abre issue **nova** com fato
  posterior ao fechamento: run `failure` criada depois dele, o limite de "sem
  run" vencido de novo, PR cruzando os 5 dias, ou a entrada de um PR deixado
  aberto lotar. Nunca `reopen`: a issue herdaria o `createdAt` e o `S3`
  reprovaria na hora. Issue nova aberta por outro sinal repete o achado já
  triado com _(triado em <data>)_. O cron fecha a issue aberta quando só restam
  achados triados, ou nenhum, e o comentário diz qual sinal zerou.
- **Medição falha** (token, API, yml): `::warning title=dependabot-health sem
  medição::` no log, issue intocada, run verde. Zero runs na janela conta como
  instrumento cego, não como dez entradas sem run.
- **Limite:** o aviso "cannot open any more pull requests" só aparece na UI do
  Dependabot. O job sai `success` e o script não o lê. A ocupação de vagas do
  sinal "PR parado" é uma aproximação: conta os PRs abertos da entrada, inclusive
  os de security update, que têm limite próprio de 10. O erro cai do lado barato,
  no máximo uma issue a mais.

### PR do Dependabot parado

Vale para todo ecossistema, não só `pip`. Fechar PR do Dependabot vira ignore
implícito da release, e por isso o `stale.yml` isenta esses PRs pela label
`dependabot` (#2147; o stale fechou #2006–#2015 em 2026-09-29). Isento, o PR que
ninguém mergeia fica aberto para sempre: ocupa uma vaga do
`open-pull-requests-limit` (8 no `pip`, 3 no `frontend-ops`, 5 nos demais) e
trava calado os version updates da entrada. O pip é o caso típico, porque o PR
nasce vermelho até alguém regenerar o `.lock`.

- **Idade é da cadeia, não do PR.** A cada release nova o Dependabot fecha o PR e
  abre outro ("Superseded by #N"). O `next` passou por #2025, #2037 e #2039 em 9
  dias, e os dois últimos tinham menos de 2 dias cada. O
  `dev/ci_dependabot_stuck_prs.py` liga os elos pela mesma entrada, a mesma
  dependência (branch sem versão nem hash de grupo) e um fechamento sem merge a
  até 5 min da criação do substituto. Medido: de −50s a +6s. Merge quebra a
  cadeia. `multi-<hash>` nunca vira cadeia. Quando o Dependabot reestrutura a
  branch (dep avulsa vira `multi-…` ou grupo), a idade é subestimada, nunca
  superestimada.
- **Por que 5 dias:** o cron roda às 02:00 UTC e o Dependabot às segundas, 09:00
  UTC. PR aberto na run cruza 5 dias no sábado e o aviso sai no domingo, antes da
  run seguinte. Com 7, o aviso chegaria depois dela. PR saudável mergeou em até
  1,3 dia nos 99 medidos. Contrafactual: o lote de 09-07 teria avisado em 09-13,
  16 dias antes de o stale fechá-lo.
- **Saídas** (escolha uma, e então feche a issue):
  1. **Merge.** No pip, rode a Tarefa 1 no próprio PR do Dependabot.
  2. **Lane de migração**, para major que pede trabalho (ex.: vite 6→8,
     typescript 6→7). O PR pode ficar aberto enquanto sobrar vaga.
  3. **`ignore` no `.github/dependabot.yml`**, com data e condição de retomada no
     comentário (padrão do `ignore` de redis acima). Só depois feche o PR.
- **Nunca** só fechar o PR nem comentar `@dependabot ignore`. As duas coisas viram
  ignore fora do git, o mesmo defeito que o stale causou.
- **PR deixado aberto é triagem válida enquanto sobra vaga.** Ele volta à issue
  se a entrada lotar depois do fechamento, porque aí passa a travar update.
- **PR sem entrada** no `dependabot.yml` (hoje `go_modules`, que só recebe
  security update) também vira linha, com vagas "n/d". Security update parado é
  o mais grave da lista.
- **Medição falha** (lista de PRs vazia em 90 dias, ou cortada no `--limit`):
  `::warning::` e issue intocada, igual ao resto do script.

## Hook de sincronia

`dev/check_lockfile_sync.py` (pre-commit) compara o conjunto de deps diretas
declaradas nos `.in` com as pinadas no `.lock`. Falha se um `.in` declara um
pacote ausente do `.lock` — sinal de que o lock está stale.
