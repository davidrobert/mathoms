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

Dependabot monitora os `.in` (ecossistema `pip` em `/` e `/backend`). Como o
lock é **combinado cross-dir**, o Dependabot **não regenera o `.lock`
automaticamente** — ele abre PR subindo o `.in`, e o `dev/check_lockfile_sync.py`
falha no CI até que alguém rode a Tarefa 1 e adicione o `.lock` regenerado ao
PR. Esse é o gate intencional: upgrade major nunca entra sem revalidação.

### `ignore` de redis — teto do kombu (2026-10-09)

As duas entradas `pip` ignoram `redis>=6.5`. Esse é o teto que o `kombu[redis]`
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
- **Triar = fechar à mão**, com comentário apontando o PR do conserto. Não espere
  a próxima run passar: o `S3` reprovaria o `Lint` do próprio PR do conserto (a
  classe do impasse de 2026-10-08). O cron só abre issue **nova** com fato
  posterior ao fechamento — run `failure` criada depois dele, ou o limite de
  "sem run" vencido de novo. Nunca `reopen`: a issue herdaria o `createdAt` e o
  `S3` reprovaria na hora. Com tudo saudável, o cron fecha a issue aberta.
- **Medição falha** (token, API, yml): `::warning title=dependabot-health sem
  medição::` no log, issue intocada, run verde. Zero runs na janela conta como
  instrumento cego, não como dez entradas sem run.
- **Limite:** o aviso "cannot open any more pull requests" só aparece na UI do
  Dependabot. O job sai `success` e o script não o vê.

## Hook de sincronia

`dev/check_lockfile_sync.py` (pre-commit) compara o conjunto de deps diretas
declaradas nos `.in` com as pinadas no `.lock`. Falha se um `.in` declara um
pacote ausente do `.lock` — sinal de que o lock está stale.
