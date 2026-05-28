---
id: A20.l10
type: lane
title: "Docker dev↔prod parity — L10 Python lockfile com hashes (pip-tools vs uv)"
sprint: A20
status: open
priority: P0
branch_slug: a20-l10-python-lockfile
depends_on: []
parallel_with:
  - "[[A20.l2]]"
  - "[[A20.l3]]"
  - "[[A20.l6]]"
adrs_canonical:
  - "[[ADR-254]]"
tags:
  - type/lane
  - sprint/a20
  - status/ready
  - priority/p0
  - area/infra
  - area/python
  - area/devops
---

# A20.L10 — Python lockfile com hashes

> **Onda A** em [[MOC-sprint-a20]] (paralela a [[A20.l2]]/[[A20.l3]]/[[A20.l6]]
> — sem deps cruzadas). Lane infraestrutural que **destrava [[A20.l1]]**
> (multi-stage). Sem lockfile, `pip install` resolve transitivamente — SHA pin
> da imagem base ([[A20.l2]]) é parcial: `python:3.12-slim@sha256:...` trava o
> **ponto de partida**, mas `pip install -r requirements.txt` num `T+1` pode
> resolver `cryptography` ou `sqlalchemy` numa versão transitiva diferente.
> Reprodutibilidade quebrada silenciosamente.

## Objetivo

Adotar **lockfile Python com hashes SHA-256 de wheels** para garantir build
determinístico bit-a-bit. Decisão entre `pip-tools` (padrão maduro) e `uv`
(Astral, 2024 — ~10× mais rápido) materializada em [[ADR-254]]. Migra **ambos**:

- `requirements.txt` (raiz, pipeline — ~10 deps diretas)
- `backend/requirements.txt` (~30 deps diretas)

Resultado: `requirements.lock` + `backend/requirements.lock`, ambos com
`--hash=sha256:...` em toda linha. Dockerfile ([[A20.l1]]) consome via
`pip install --require-hashes --no-index --find-links /wheels` — instalação
rejeita qualquer wheel cujo hash não bate.

## Contexto

Estado atual:

| Arquivo | Deps diretas | Hashes? | Lockfile? | Transitive lock? |
|---|---|---|---|---|
| `requirements.txt` (raiz) | ~10 (pdfplumber, anthropic, jsonschema, numpy...) | Não | Não | Não |
| `backend/requirements.txt` | ~30 (fastapi, sqlalchemy, alembic, celery...) | Não | Não | Não |
| `requirements-dev.txt` | ~10 (pytest, ruff, mypy...) | Não | Não | Não |

Implicação concreta — exemplo real:

```
$ pip install "fastapi>=0.115"  # hoje em backend/requirements.txt
# Em 2026-05-22 → fastapi 0.115.4 + starlette 0.41.3 + pydantic 2.9.2
# Em 2026-06-15 (mesmo Dockerfile, mesma base SHA) → fastapi 0.115.7 + starlette 0.42.0 + pydantic 2.10.1
# Build A vs build B: deps diferentes, comportamento divergente, postmortem caro.
```

Sem lock, **[[A20.l2]] (SHA pin de base) é placebo parcial** — trava 30% da
reprodutibilidade (SO + Python interpreter); 70% (Python deps) continua flutuando.

Paths impactados:
- `requirements.txt`, `backend/requirements.txt` (sources atuais — viram inputs)
- `requirements.lock`, `backend/requirements.lock` (novos, com hashes — viram
  fonte de install)
- `Dockerfile` ([[A20.l1]] — `pip install --require-hashes` no stage `builder`)
- `pyproject.toml` (mantém metadata; sem migração formal pra `[project]`
  agora — débito documentado)
- CI workflow (`.github/workflows/ci.yml`) — install via `pip install
  --require-hashes -r requirements.lock -r backend/requirements.lock` em vez
  de `-r requirements.txt`

## Decisão (escopo de [[ADR-254]])

Build-vs-buy review **obrigatório** entre dois caminhos:

### Opção A — `pip-tools` (`pip-compile`)

- Maturidade: 9 anos, padrão de facto na comunidade Python (jazzband/pip-tools).
- Output: `requirements.txt`-shaped com `--hash=sha256:...` por linha — formato
  consumível direto por `pip install --require-hashes`.
- Workflow: `pip-compile --generate-hashes requirements.in → requirements.lock`.
- Velocidade: install ~5-15s em CI (depende de cache pip).
- Vendor risk: zero — output é `requirements.txt` puro, zero lock-in.
- Dependabot: suporte first-class ao formato `requirements.txt` com hashes.

### Opção B — `uv` (Astral)

- Maturidade: ~2 anos (lançado 2024), backed por Astral (mesma org do ruff).
- Output: `uv.lock` próprio (formato TOML estendido) **OU** `requirements.txt`
  com `--hash` via `uv pip compile --generate-hashes`.
- Velocidade: install ~1-3s em CI (10-50× mais rápido que pip).
- Vendor risk: **formato `uv.lock`** é proprietário (não consumível por pip
  puro); modo `requirements.txt` mitiga mas perde features (lockfile
  multi-Python, groups).
- Dependabot: suporte recente (Q1 2026), ainda em maturação.
- Churn: API estável desde 0.4.x mas ainda agita features mensalmente.

### Tabela de decisão (preenchida pelo `build-vs-buy` review)

| Critério | Peso | pip-tools | uv |
|---|---|---|---|
| Maturidade comunidade | 3 | | |
| Velocidade install CI | 2 | | |
| Risco lock-in | 3 | | |
| Suporte Dependabot | 2 | | |
| Compatibilidade pip puro (no Dockerfile) | 3 | | |
| Curva de aprendizado equipe | 1 | | |

**Recomendação inicial do PM** (sujeito a revisão pelo `build-vs-buy`):
**`pip-tools` para V1**, com `uv` revisitável em Sprint A22+ se velocidade CI
virar gargalo crítico. Justificativa: lockfile é peça permanente da infra;
maturidade > velocidade aqui; sair de `uv.lock` proprietário pra `pip-tools`
no futuro é refactor caro, o inverso é trivial.

## Escopo IN

- [[ADR-254]] decide tooling (com `build-vs-buy` review formal).
- Cria `requirements.in` (raiz) e `backend/requirements.in` — sources
  human-edited com `>=` constraints atuais.
- Gera `requirements.lock` e `backend/requirements.lock` com `--generate-hashes`.
- Modifica `Dockerfile` (coordenado com [[A20.l1]]) — install via
  `--require-hashes --no-index --find-links /wheels`.
- CI workflow valida: PR que toca `requirements.in` mas não atualiza
  `requirements.lock` falha. Pre-commit hook simples
  (`dev/check_lockfile_sync.py`).
- Documenta update workflow em `docs/reference/runbooks/python_dependencies.md`
  — passo-a-passo "como adicionar dep nova" e "como subir versão de dep existente".
- Dependabot atualizado: monitora `requirements.in` (não `.lock`) — Dependabot
  abre PR no `.in`, hook de CI regenera o `.lock`.

## Escopo OUT

- `requirements-dev.txt` mantém-se sem hashes em V1 — pytest/ruff/mypy só
  rodam em dev/CI, não em prod runtime. Lock vem em Sprint A22+ se justificado.
- Migração formal para `pyproject.toml` `[project]` section com `dependencies
  = [...]` — débito separado; muda CI, build wheels, instalação editable;
  escopo grande, sem ganho imediato vs `requirements.in`.
- `uv pip sync` em runtime (substituir `pip install` no Dockerfile mesmo se
  Opção B vencer) — decisão preservada pra [[ADR-254]]; default é `pip install
  --require-hashes` por compat máxima.
- Multi-platform lockfile (lock separado pra arm64 vs amd64) — Mathoms roda só
  amd64; débito futuro se M-series Mac viver com containers nativos.

## Pré-requisitos rígidos

- [[ADR-254]] mergeada como `Proposto` antes de qualquer commit em
  `requirements.in`/`.lock`.

## Plano de execução em fases

### F1 — Build-vs-buy + ADR-254 (1 dia)

- Invocar `build-vs-buy` com tabela de decisão acima preenchida + 3 PRs de
  referência (1 repo open-source usando `pip-tools`, 1 usando `uv`, 1
  híbrido).
- Escrever [[ADR-254]] como `Proposto` com decisão + alternativas rejeitadas +
  trade-offs.
- PR doc-only — ADR + esta lane referenciada.

### F2 — Lockfile primeiro (sem mudar Dockerfile) (1 dia)

- Renomear `requirements.txt` → `requirements.in` (raiz e `backend/`).
- Rodar `<ferramenta> compile --generate-hashes requirements.in -o
  requirements.lock` em ambos.
- **Commitar `.lock` files** — vira parte do source-of-truth versionado.
- CI continua usando `pip install -r requirements.in` (sem hash) — F2 é
  *additive only*, prepara terreno sem quebrar.

### F3 — CI valida `--require-hashes` (1 dia)

- CI workflow agora roda `pip install --require-hashes -r requirements.lock`
  em job separado paralelo ao job legado.
- Se job hash-only passa em 3 runs consecutivos sem flake, F3 mergeia trocando
  o install legado pelo hashes-only.

### F4 — Dockerfile consome lockfile (coordenado com L1) (1 dia)

- Dockerfile do [[A20.l1]] já espera `requirements.lock` (snippet referenciado
  na lane L1).
- F4 é o PR que faz a troca atômica — Dockerfile + workflow CI commitam juntos.
- Smoke test de build cold (sem cache) para validar.

### F5 — Update workflow + Dependabot (1 dia)

- `docs/reference/runbooks/python_dependencies.md` com:
  - "Adicionar dep nova" — editar `.in`, rodar `compile`, commitar ambos.
  - "Upgrade dep existente" — editar constraint `.in`, rodar `compile
    --upgrade-package <X>`.
  - "Resolver conflict transitivo" — passos de debug.
- `.github/dependabot.yml` atualizado — `package-ecosystem: pip`,
  `directory: /` e `directory: /backend`, target `requirements.in`.
- Hook GH Actions: PR do Dependabot dispara workflow que regenera `.lock` e
  pusha amend no mesmo branch.

### F6 — Sunset legacy + comunicação (0.5 dia)

- Deleta linhas em README/SETUP que referenciam `requirements.txt` antigo.
- Anúncio interno: "agora dev local instala via `pip install --require-hashes
  -r requirements.lock`".

## Critério de aceite

1. `pip install --require-hashes --no-index --find-links /wheels -r
   requirements.lock` instala todas as deps sem erro num container Python
   3.12-slim limpo.
2. `python -c "import fastapi, sqlalchemy, anthropic, playwright, pdfplumber,
   numpy"` termina exit 0 após install.
3. PR de teste: subir versão de `fastapi>=0.115` pra `>=0.116` em
   `requirements.in`, rodar `compile`, verificar que `requirements.lock`
   agora tem `fastapi==0.116.<X>` e que `pip install --require-hashes`
   instala exatamente essa versão.
4. PR de prova de hash mismatch: editar manualmente um hash em
   `requirements.lock`, rodar `pip install --require-hashes` → install
   **falha** com mensagem clara (não silencioso).
5. Hook `dev/check_lockfile_sync.py` bloqueia commit que tem diff em
   `requirements.in` sem diff correspondente em `requirements.lock`.

## Definition of Done

- [ ] [[ADR-254]] promovida `Proposto → Decidido (A20.L10)` no PR de F4.
- [ ] `requirements.in` + `requirements.lock` + `backend/requirements.in` +
      `backend/requirements.lock` em `main`.
- [ ] Dockerfile multi-stage ([[A20.l1]]) instala via `--require-hashes` —
      confirmado no PR de L1 que esta lane está mergeada antes do merge de L1.
- [ ] CI rodando hash-only install em 3 runs consecutivos sem flake.
- [ ] Runbook `python_dependencies.md` em `docs/reference/runbooks/`.
- [ ] Dependabot config atualizada e validada num PR de teste (subir versão
      minor de `httpx`, Dependabot deve abrir PR; hook deve regenerar `.lock`).
- [ ] README + SETUP atualizados pra refletir novo workflow.
- [ ] Pre-commit hook `check_lockfile_sync.py` registrado em
      `.pre-commit-config.yaml` e verde em `pre-commit run --all-files`.

## Riscos top 3

1. **CI quebra em transitive deps** — primeira geração do lockfile pode revelar
   conflito mascarado (ex.: `sqlalchemy 2.0.x` quer `greenlet>=3.0`, mas alguma
   dep nossa fixa `greenlet<3`). Mitigação: F2 mantém install legado em
   paralelo, F3 só troca quando hash-only passa estável; conflito vira pin
   explícito em `.in` e regeneramos.
2. **uv churn (se Opção B vencer)** — formato `uv.lock` pode mudar entre
   0.5.x e 0.6.x; PR semestral de migração. Mitigação preferida: escolher modo
   `requirements.txt` com hashes (não `uv.lock` nativo), mantendo opção de
   sair pra pip-tools sem refactor.
3. **pip-tools mais lento em CI** — `pip-compile` em deps grandes (numpy,
   playwright, otel-*) leva ~30-60s. Mitigação: rodar `compile` só quando
   `.in` muda (workflow conditional); install em si (que é o hot path) usa
   `pip install --require-hashes` que é rápido.

## Métricas

- Tempo de `pip install --require-hashes` em CI cold (target: <30s).
- Número de transitive deps fixadas (proxy de reprodutibilidade — esperado
  ~150-200 deps no lock vs ~40 deps no source).
- Build determinístico verificável: build da mesma SHA em 2 runners diferentes
  produz imagens com layer `pip install` idêntica (`docker history --no-trunc`).
- Tempo médio de PR de upgrade de dep (Dependabot → merge): meta <3 dias.

## Especialistas pre-PR

- **`build-vs-buy`** (obrigatório, blocking) — escolha pip-tools vs uv via
  [[ADR-254]]. Briefing: tabela de decisão acima + 3 PRs de referência +
  perfil de uso Mathoms (CI matrix 6 jobs, dev local em Mac M-series + Linux,
  prod em Coolify amd64 single-host).
- **`sre-devops`** (obrigatório, após decisão) — review da integração
  Dockerfile + Dependabot + CI gating. Foco em: blast radius de hash mismatch
  em prod, rollback path se lockfile corrompido, propagação de CVE crítico via
  hash pin.

## Detalhe operacional

Track prompt em [`../tracks/a20-l10-python-lockfile.md`](../tracks/a20-l10-python-lockfile.md) (criado 2026-05-29; pós-F3/ADR-182 tracks vivem em `docs/sprint/<X>/tracks/`).
