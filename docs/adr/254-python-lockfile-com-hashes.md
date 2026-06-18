---
id: ADR-254
type: adr
title: "Python lockfile com hashes — pip-tools vs uv — Sprint A20"
status: Decidido
phase: A20.l10
date: "2026-05-22"
relates_to:
  - "[[ADR-228]]"
  - "[[ADR-230]]"
  - "[[ADR-248]]"
  - "[[ADR-249]]"
  - "[[ADR-251]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 254"
  - "Python lockfile"
  - "pip-tools vs uv"
  - "requirements lock with hashes"
tags:
  - type/adr
  - status/decidido
  - area/infra
  - area/python
  - area/devops
  - phase/a20
---

## Contexto

Review independente do `sre-devops` (2026-05-22) identificou que **SHA pin de
imagem base ([[ADR-249]]) é placebo parcial sem lockfile com hashes**.
`python:3.12-slim@sha256:...` trava o ponto de partida, mas `pip install -r
requirements.txt` resolve transitivamente — duas builds no mesmo SHA, em dias
diferentes, podem produzir imagens com versões diferentes de `cryptography`,
`sqlalchemy`, `pydantic`, etc.

Estado atual:

| Arquivo | Deps diretas | Hashes? | Lockfile? | Transitive lock? |
|---|---|---|---|---|
| `requirements.txt` (raiz) | ~10 | Não | Não | Não |
| `backend/requirements.txt` | ~30 | Não | Não | Não |
| `requirements-dev.txt` | ~10 | Não | Não | Não |

Implicação concreta:

```
$ pip install "fastapi>=0.115"  # hoje em backend/requirements.txt
# T+0:  fastapi 0.115.4 + starlette 0.41.3 + pydantic 2.9.2
# T+30d (mesmo Dockerfile, mesma base SHA): fastapi 0.115.7 + starlette 0.42.0 + pydantic 2.10.1
# Build A vs build B: deps diferentes, comportamento divergente, postmortem caro.
```

A decisão precisa endereçar: (a) build determinístico bit-a-bit; (b)
compatibilidade com `pip install --require-hashes` no Dockerfile multi-stage
([[ADR-248]]); (c) workflow de update friction-baixo (Dependabot funcional);
(d) lock-in tolerável; (e) velocidade de install em CI matrix de 6 jobs.

## Decisão

**Adotar `pip-tools` para V1** (`pip-compile --generate-hashes`):

- `requirements.in` (raiz) + `backend/requirements.in` viram **sources
  human-edited** com constraints `>=` atuais.
- **Um único `requirements.lock` combinado** (não dois) gerado por `pip-compile
  --generate-hashes --strip-extras requirements.in backend/requirements.in` —
  formato `requirements.txt`-shaped com `--hash=sha256:...` em cada linha.
- Dockerfile ([[ADR-248]]) consome via `pip install --require-hashes -r
  requirements.lock`.
- Pre-commit hook `dev/check_lockfile_sync.py` bloqueia commit com diff em `.in`
  sem diff correspondente em `.lock`.
- CI (jobs de teste) instala das `.in` loose (com dev extras, sem hashes — ver
  §Neutras); `security.yml` audita o `requirements.lock` pinado.
- Dependabot monitora os `.in`; regen do `.lock` é manual (lock combinado
  cross-dir não é auto-regenerado pelo Dependabot — o hook força a regen no PR).
- Update workflow documentado em
  [`docs/reference/runbooks/python_dependencies.md`](../reference/runbooks/python_dependencies.md).

**Desvio do design original (lock único vs. dois locks):** a primeira versão
desta ADR previa `requirements.lock` + `backend/requirements.lock` separados.
A geração empírica revelou `ResolutionImpossible`: `anthropic` é dep
compartilhada (raiz puxa direto; backend puxa via `instructor`/`litellm`), e
locks separados conflitam no range de `jiter` exigido pelo `instructor`. A
resolução **combinada** (ambos `.in` num só `pip-compile`) deixa o resolver
escolher `jiter==0.13.0` satisfazendo os dois. Resultado: 135 pacotes pinados
num lock único, validado installable em `python:3.12-slim` amd64.

**Constraint operacional:** o `.lock` **deve** ser gerado em container
`linux/amd64`. Wheels nativos (`uvloop`, `cryptography`, `pydantic-core`,
`playwright`, `numpy`) têm hash por-plataforma; gerar no host Mac arm64 quebra
o `--require-hashes` em CI/build (que rodam amd64).

**`uv` rejeitado para V1** (revisitável em Sprint A22+ se velocidade CI virar
gargalo crítico).

## Alternativas consideradas

### Opção A — `pip-tools` (`pip-compile`) (**adotada**)

- **Maturidade:** 9 anos, padrão de facto na comunidade Python
  (jazzband/pip-tools).
- **Output:** `requirements.txt`-shaped com `--hash=sha256:...` — consumível
  direto por `pip install --require-hashes`. Zero lock-in.
- **Workflow:** `pip-compile --generate-hashes requirements.in →
  requirements.lock`.
- **Velocidade:** install ~5-15s em CI (depende de cache pip).
- **Vendor risk:** zero — output é `requirements.txt` puro.
- **Dependabot:** suporte first-class.
- **Custo:** velocidade install ligeiramente menor que `uv`; `pip-compile`
  inicial em deps grandes (numpy, playwright, otel-*) leva ~30-60s.

### Opção B — `uv` (Astral)

**Rejeitada para V1.**

- **Maturidade:** ~2 anos (2024), backed por Astral (org do `ruff`).
- **Output:** `uv.lock` próprio (TOML estendido, proprietário) **OU**
  `requirements.txt` com `--hash` via `uv pip compile --generate-hashes`.
- **Velocidade:** install ~1-3s em CI (10-50× mais rápido que pip).
- **Vendor risk:** formato `uv.lock` não consumível por pip puro. Modo
  `requirements.txt` mitiga mas perde features (multi-Python, groups).
- **Dependabot:** suporte recente (Q1 2026), ainda em maturação.
- **Churn:** API estável desde 0.4.x mas agita features mensalmente.

**Justificativa da rejeição:** lockfile é peça permanente da infra;
maturidade > velocidade aqui. Sair de `uv.lock` proprietário pra `pip-tools`
no futuro é refactor caro (regenerar todos os locks, atualizar CI, runbooks,
Dependabot config); o inverso (pip-tools → uv) é trivial — mesmo formato
`requirements.txt` consumível por pip. Velocidade install em CI matrix 6 jobs
não é gargalo crítico hoje (~5-15s × 6 = ~30-90s total, vs total job ~5-7min);
revisitar quando build virar gargalo medido.

### Opção C — Migrar para `pyproject.toml [project]` formal

**Rejeitada para V1.** Mudança maior que escopo de A20 — exige refactor de
CI, build wheels, instalação editable. Sem ganho imediato vs
`requirements.in` para resolver P0.5. Mantém-se como FU-4 ([[MOC-sprint-a20]]).

### Opção D — `poetry`

**Rejeitada.** Lock format proprietário (`poetry.lock`), CLI próprio,
filosofia "lockfile primeiro" diferente da convenção `requirements.txt`
da maior parte da comunidade Python. Mathoms não tem ganho compensando o
custo de migração + lock-in.

## Consequências

### Positivas

- **P0.5 resolvido em conjunto** — combinado com [[ADR-249]] (SHA pin de
  base), reprodutibilidade build vira 100% determinística bit-a-bit.
- **Compatível com [[ADR-248]]** Dockerfile multi-stage (`pip install
  --require-hashes` no stage `builder`).
- **Surface de CVE auditável** — Trivy ([[ADR-251]]) reporta exatamente
  quais versões estão no lockfile, sem ambiguidade transitiva.
- **Dependabot funcional** — PRs automáticos com hash regenerado.
- **Zero lock-in** — qualquer ferramenta Python consome `requirements.txt`
  com hashes.

### Negativas

- **Velocidade install em CI marginalmente menor que `uv`** — ~5-15s vs
  ~1-3s. Não materializa como gargalo no perfil atual de uso.
- **Workflow de update mais ritual** — adicionar dep nova exige editar `.in`
  + rodar `pip-compile` + commitar ambos. Mitigado por documentação
  (`python_dependencies.md`) e Dependabot automatizando o caso comum
  (upgrade de versão).
- **`pip-compile` inicial em deps grandes** — ~30-60s para gerar
  `requirements.lock`. Mitigado por rodar só quando `.in` muda.

### Neutras

- **`requirements-dev.txt` permanece sem hashes em V1** — pytest/ruff/mypy
  rodam só em dev/CI; lock vem em A22+ se justificado.
- **`uv` revisitável em A22+** se velocidade install virar gargalo medido.

## Validação

Critérios em [[A20.l10]] §"Critério de aceite" (5 critérios). Resumo:

1. `pip install --require-hashes -r requirements.lock` instala todas deps sem
   erro em container Python 3.12-slim limpo.
2. PR de prova de hash mismatch falha com mensagem clara (não silencioso).
3. Hook `check_lockfile_sync.py` bloqueia commit `.in` sem `.lock`.
4. Subir versão `fastapi>=0.115 → >=0.116` em `requirements.in` + rodar
   `pip-compile` regenera `.lock` com versão correta.
5. Build determinístico verificável: build da mesma SHA em 2 runners diferentes
   produz layer `pip install` com hash idêntico (`docker history --no-trunc`).

## Migração

Sequência em fases (detalhada em [[A20.l10]] §"Plano de execução em fases"):

1. **F1** — Decisão `build-vs-buy` formal + ADR-254 mergeada como `Proposto`.
2. **F2** — Renomear `requirements.txt → requirements.in`, gerar `.lock` com
   `--generate-hashes`. CI continua usando legacy.
3. **F3** — CI roda hash-only install paralelo; após 3 runs estáveis, troca.
4. **F4** — Dockerfile ([[A20.l1]]) consome `.lock` via `--require-hashes`.
5. **F5** — Runbook + Dependabot config.
6. **F6** — Sunset legacy + comunicação.

## Riscos

- **CI quebra em transitive deps** — primeira geração revela conflito
  mascarado. Mitigação: F2 mantém install legado em paralelo.
- **`pip-compile` lento em deps grandes** — mitigação: rodar só quando `.in`
  muda (workflow conditional).
- **Dependabot regenera `.lock` mal** — mitigação: hook GH Actions revalida
  no PR; review humano em update major.

## Métricas

Ver [[A20.l10]] §"Métricas":
- Tempo `pip install --require-hashes` em CI cold: <30s
- Número de transitive deps fixadas: ~150-200 (vs ~40 diretas)
- Build determinístico verificável entre runners: 100%
- Tempo médio Dependabot → merge: <3 dias

## Emenda 2026-06-18 — CI-tests também instala do lock

A decisão original cobria build prod (`Dockerfile`) e pip-audit, mas os **jobs de
teste do CI** (`ci.yml`, `nightly.yml`, smoke, monthly) seguiam instalando dos
`.in` loose (`uv pip install -r requirements.in`) com cache key só no hash dos
`.in`. Isso reabriu o gap que esta ADR fecha para prod: o venv cacheado congelava
transitivas antigas; ao limpar o cache, o re-resolve pegou releases novas e uma
transitiva quebrou o registro de routers (backend-tests vermelho repo-wide). **Fix:**
CI-tests agora instala `uv pip install --require-hashes -r requirements.lock` (paridade
com o Dockerfile), cache key no hash do **lock**, **sem `restore-keys`** no bloco venv
(o fallback de prefixo restaurava venv de lock divergente). Detalhe operacional no
runbook [python_dependencies.md](../reference/runbooks/python_dependencies.md).

## Referências externas

- [pip-tools](https://github.com/jazzband/pip-tools) — `pip-compile`
- [uv](https://docs.astral.sh/uv/) — Astral
- [PEP 665 — lockfile format](https://peps.python.org/pep-0665/) (rejeitada,
  contexto histórico)
- [pip — `--require-hashes` mode](https://pip.pypa.io/en/stable/topics/secure-installs/)
