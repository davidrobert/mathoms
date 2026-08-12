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
| `Dockerfile` (build de imagem prod) | `requirements.lock` | `pip install --require-hashes` |
| CI — jobs de teste (`ci.yml`, `nightly.yml`, smoke, monthly) | `requirements.lock` | `uv pip install --require-hashes` (paridade com prod) + test-deps inline (reportlab/xlwt/pytest-cov/pytest-xdist/fakeredis) |
| CI — `security.yml` pip-audit | `requirements.lock` | auditoria de versões pinadas (precisa) |
| Dev local | `requirements-dev.txt` (via `make setup`) | `pip install -e . -r requirements-dev.txt` |

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

## Hook de sincronia

`dev/check_lockfile_sync.py` (pre-commit) compara o conjunto de deps diretas
declaradas nos `.in` com as pinadas no `.lock`. Falha se um `.in` declara um
pacote ausente do `.lock` — sinal de que o lock está stale.
