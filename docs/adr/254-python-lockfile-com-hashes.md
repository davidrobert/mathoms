---
id: ADR-254
type: adr
title: "Python lockfile com hashes — pip-tools vs uv — Sprint A20"
status: Decidido
phase: A20.l10
date: "2026-05-22"
amended_at: ["2026-06-18", "2026-08-11", "2026-08-12"]
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

> **Emenda (2026-06-18):** jobs de teste do CI também passaram a instalar do
> lock — ver §"Emenda 2026-06-18 — CI-tests também instala do lock".
>
> **Emenda (2026-08-11):** a key do venv cache passou a incluir a **versão exata
> do interpretador**, e os dois steps de install viraram um só, sempre
> executado (`dev/ci_ensure_venv.sh`) — ver §"Emenda 2026-08-11 — a key do venv
> cache inclui o interpretador".
>
> **Emenda (2026-08-12):** o gatilho do item 3 da emenda anterior **disparou** —
> os test-deps inline rebaixam o lock a cada run (`starlette` 1.3.1→0.52.1) e
> `requirements-test.lock` deixou de ser opcional. Inclui a refutação medida do
> sinal (b) e dois deferimentos datados (composite action; paridade de
> interpretador prod↔CI) — ver §"Emenda 2026-08-12".

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

## Emenda 2026-08-11 — a key do venv cache inclui o interpretador

A emenda de 2026-06-18 fechou o eixo **pacote** (key no hash do `requirements.lock`,
`--require-hashes`, sem `restore-keys`). Faltava o outro: o `.venv` é derivado de
**dois** inputs, e o segundo — o **interpretador** — não estava na key.

`uv venv` grava `.venv/bin/python3` como symlink **absoluto**. Quando a frota de
runners troca de patch do Python (medido em 2026-08-11: `3.13.14` e `3.13.15`
coexistindo em `ubuntu-24.04` na mesma janela de horas), o cache restaura um
`.venv` cujo symlink dangla. O guard de então, `[ -d .venv ]`, via o **diretório**
e não recriava; como `cache-hit == 'true'`, o step que instala o lock era pulado;
o job morria em `Failed to inspect Python interpreter`. Duas branches distintas
caíram junto — não é código, e re-run não resolve (restaura o mesmo cache).

**Decisão:**

1. **Key ganha a versão exata do interpretador** (`steps.setup-python.outputs.python-version`)
   além do hash do lock. Entradas de patch diferente deixam de colidir; o custo é
   no máximo uma entrada extra por lock durante rollout de frota, e colapsa
   sozinha depois.
2. **Um único step de install, sempre executado** (sem `if: cache-hit`), cujo
   predicado **executa** o interpretador em vez de testar presença — `-x` pegaria
   o symlink dangling, execução também pega tar truncado e stdlib faltando.
   Venv inutilizável é apagado, recriado e reinstalado do lock, com `::warning::`
   no log (self-heal silencioso é imposto invisível). A lógica vive em
   `dev/ci_ensure_venv.sh`, consumida pelos 6 call sites — a duplicação de
   *lógica* entre os dois steps antigos foi o que produziu este bug e o de `xlwt`
   (#596).
3. **`uv pip install` do lock em cache-hit são é auditoria, não re-resolução** —
   o lock é lista plana de `==`, sem rede. Se o step passar a imprimir
   `Installed/Uninstalled` a cada run, os test-deps inline estão em conflito com
   o lock, e o `requirements-test.lock` (débito aberto) deixa de ser opcional.

**Prova:** `dev/ci_ensure_venv.sh --self-test` monta venvs e os corrompe de três
formas (symlink dangling, binário removido, diretório vazio), afirmando detecção
+ cura. Provado por mutação: com o predicado antigo (`[ -d ]`) o self-test fica
**vermelho nos 3 casos**. Roda como step do `lint-all` (ADR-210 §camada 4 — job
novo custa 1 min faturado de piso).

**Não muda:** `--require-hashes`, o lock como fonte única, a ausência de
`restore-keys`. Nenhuma dimensão de supply-chain foi afrouxada.

## Emenda 2026-08-12 — o gatilho do item 3 disparou: os extras rebaixam o lock

A emenda de 2026-08-11 (item 3) escreveu a condição: *"se o step passar a
imprimir `Installed/Uninstalled` a cada run, os test-deps inline estão em
conflito com o lock, e o `requirements-test.lock` (débito aberto) deixa de ser
opcional"*. **Ela ocorreu** — medida em cache-HIT, em jobs independentes, e
re-verificada à mão no log do job 93015190283:

```
- starlette==1.3.1     (o que o lock instalou)
+ starlette==0.52.1    (o que os extras rebaixaram)
```

`pytest` sofre o mesmo (9.0.3 → 8.4.2). Mecanismo: a ordem lock → extras
deixa os **extras vencerem** — `"schemathesis<4"` resolve `starlette` um
**major abaixo** do lock, então a suíte roda contra um `starlette` que a
imagem de prod não embarca, e todo run em cache-hit faz o flip-flop
(lock re-sobe, extras re-descem). A antecipação da emenda anterior ("churn/
conflito") subestimou o modo de falha: é **rebaixamento de dependência de
runtime na venv de teste**, não ruído de resolução. O comentário de
`dev/ci_ensure_venv.sh` (§`install_deps`) descrevia a direção invertida
("o lock rebaixaria o que os extras trouxeram") — corrigido junto com esta
emenda.

**Consequência:** `requirements-test.lock` (com hashes, mesma disciplina do
`requirements.lock`) deixa de ser débito confortável. Escopo do remédio,
medido: os 6 extras dos call sites de `dev/ci_ensure_venv.sh`, **mais** os 2
`pip install reportlab` fora do script (`ci.yml` §pdf-smoke, `nightly.yml`
§backup-drill), **mais** o drift de `requirements-dev.txt` (não lista
`pytest-xdist`/`fakeredis`/`schemathesis` — `make setup` produz ambiente
diferente do CI).

**Refutação registrada (para ninguém re-investigar):** o sinal (b) da emenda
anterior — custo do step `Ensure venv` em cache-HIT, limiar ~5s para reabrir a
escolha de desenho — foi medido e **refutado**: mediana 1s (n=14, máx 3s);
cache-MISS custa 4-7s. O desenho não reabre por custo.

**Correção de leitura da "paridade":** a paridade que esta ADR promete entre
CI e Dockerfile é de **versões de pacote** — e, enquanto o
`requirements-test.lock` não existir, nem essa vale para `starlette`/`pytest`
na venv de teste. Interpretador nunca foi paritário: prod builda em
**Python 3.12** (digest-pinado via [[ADR-249]]), os jobs de teste rodam
**3.13**, e o único job que casa o interpretador de prod é o `pip-audit`
(`security.yml`) — exatamente o que nunca importa o código.

### Deferimento datado — composite action dos blocos de venv (2026-08-12)

A lógica de setup vive em `dev/ci_ensure_venv.sh`, mas o **bloco** (setup-python
+ setup-uv + cache + step) está replicado, e o pin SHA do `astral-sh/setup-uv`
aparece **7×** em 4 workflows (`ci.yml` ×3 — o `lint-all` instala uv sem bloco
de venv —, `nightly.yml` ×2, `planner-golden-monthly.yml`, `llm-cross-provider-smoke.yml`).
Extrair composite em `.github/actions/` foi **deferido**: 4 dos 6 sítios de venv
são workflows agendados que o CI de PR não exercita — um composite quebrado
derrubaria todos sem sinal prévio. **Condição de retomada:** o próximo bump que
tiver de tocar o pin (ou a key epoch) nos 7 pontos extrai o composite e valida
os agendados via `workflow_dispatch` (os três têm). Gatilho: `sre-devops`.

### Deferimento datado — paridade de interpretador prod↔CI (2026-08-12)

Decidir se CI converge para 3.12 (paridade com prod) ou prod sobe para 3.13
(forward-compat deliberado) — e, decidido, criar gate que amarre
`ARG PYTHON_BASE` (Dockerfile) × `python-version` (workflows) para a divergência
nunca voltar a ser implícita. Hoje ela não está escrita em lugar nenhum além
desta emenda. Dono: `sre-devops`; se virar invariante, é ADR `Proposto`
própria, não emenda.

## Referências externas

- [pip-tools](https://github.com/jazzband/pip-tools) — `pip-compile`
- [uv](https://docs.astral.sh/uv/) — Astral
- [PEP 665 — lockfile format](https://peps.python.org/pep-0665/) (rejeitada,
  contexto histórico)
- [pip — `--require-hashes` mode](https://pip.pypa.io/en/stable/topics/secure-installs/)
