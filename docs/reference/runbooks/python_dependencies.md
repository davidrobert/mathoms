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
| CI — jobs de teste (`ci.yml`, `nightly.yml`, etc.) | `requirements.in` + `backend/requirements.in` | `uv pip install` (loose, inclui dev extras) |
| CI — `security.yml` pip-audit | `requirements.lock` | auditoria de versões pinadas (precisa) |
| Dev local | `requirements-dev.txt` (via `make setup`) | `pip install -e . -r requirements-dev.txt` |

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
