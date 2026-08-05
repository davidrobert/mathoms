---
id: ADR-363
type: adr
title: "Identidade de código é fato de runtime injetado no deploy, não conteúdo da imagem"
status: Proposto
phase: "A40"
date: "2026-08-05"
amended_at: ["2026-08-05", "2026-08-06"]
relates_to:
  - "[[ADR-362]]"
  - "[[ADR-249]]"
  - "[[ADR-109]]"
  - "[[ADR-112]]"
supersedes: []
superseded_by: []
aliases: ["ADR 363", "MATHOMS_BUILD_SHA", "semvers ornamentais"]
tags:
  - type/adr
  - status/proposto
  - area/ci
  - area/infra
  - phase/a40
---

# ADR-363 — Identidade de código é fato de runtime, não conteúdo da imagem

> **Emenda 2026-08-05 (correção de premissa, não de decisão):** esta ADR foi
> escrita como se houvesse deploy vivo — healthcheck derrubando container,
> `${MATHOMS_BUILD_SHA:?}` bricando *"o próximo deploy"*, plataforma de deploy
> mapeando a variável. **Não existe deploy.** O projeto roda só na máquina do
> dono. As decisões seguem corretas; a urgência e o §Deferido estavam mal
> enquadrados. Ver §Emenda 2026-08-05.

## Contexto

A [[ADR-362]] decide **o que** registrar (`executor_revision`) e **onde**
(`pipeline_stage_logs`). Falta **de onde o valor vem** em cada ambiente — e o
substrato atual é mais pobre do que parece:

- O `Dockerfile` **não tem** `ARG`/`LABEL` de versão.
- **Nenhum** dos 11 workflows em `.github/workflows/` faz `docker build`,
  `buildx` ou push para registry. Não existe pipeline de imagem onde plugar um
  `--build-arg`.
- `docker-compose.prod.yml` dá a **mesma tag mutável** a api, worker e beat,
  com `build:` só no serviço de api.
- `HealthResponse.version` é `str` **required non-nullable** e devolve
  `settings.API_VERSION` (`"1.0.0"`), que é versão de **contrato de API**, não
  de código.

## Decisão

### 1. A revisão entra por `environment:`, com **zero diff no Dockerfile**

`MATHOMS_BUILD_SHA` é variável de **runtime**, mapeada pela plataforma de
deploy a partir do commit implantado. Em CI, `MATHOMS_BUILD_SHA: ${{ github.sha }}`
num bloco `env:` — delta de **jobs** igual a zero (relevante: o orçamento de
Actions desta casa já bloqueou merge por contagem de jobs).

**Por que não `ENV`/`LABEL` no Dockerfile:** `Dockerfile:103` é
`FROM runtime AS playwright` com `apt-get` das libs do Chromium logo abaixo. Um
`ENV` no fim do stage `runtime` muda o digest do pai e **re-executa o apt do
Chromium a cada commit**. "Herda de graça" é falso: herda re-buildando, num
repo que pinou bases por digest ([[ADR-249]]) e usa `--require-hashes`.

Quando houver build de imagem, `org.opencontainers.image.revision` entra por
**flag** (`--label`, aplicada na config da imagem no export) e **nunca** por
instrução `LABEL`.

Corolário: `docker inspect` de uma tag mutável compartilhada não distingue api
de worker, e um `up -d worker` isolado produz conteúdos diferentes sob o mesmo
nome. Só o **runtime** pode dizer quem está rodando — o que também é a razão de
o skew api↔worker ser observável sem machinery nova, via `service_name`
distinto por processo no OTel.

### 2. `/health` ganha campo **novo declarado**; `version` não é sobrecarregado

```python
executor_revision: Optional[str] = None   # campo NOVO
version: str                              # continua settings.API_VERSION
```

Trocar o **valor** de `version` por algo nullable — proposta que parecia ter
"diff vazio no snapshot" — devolveria HTTP 500 quando a env não estivesse
setada, e o healthcheck de prod é `curl -fsS .../health || exit 1` a cada 10s:
**derrubaria o container**. `model_config = ConfigDict(extra="allow")` não
salva, porque o campo declarado é que é required.

O snapshot OpenAPI **move** ⇒ `make update-openapi-snapshot` commitado no mesmo
PR ([[ADR-109]]).

### 3. Observabilidade: log estruturado e OTel

`executor_revision` em **todo** record do `MathomsJsonFormatter` (injetado por
construtor, sem global) e `service.version` + `deployment.environment` no
`Resource` do OTel. Atribuição de incidente se faz sobre o `ERROR` das 3h, não
sobre a linha de boot — por isso o campo vai em todo record, não só no evento
de run.

### 4. Os quatro semvers do repo são **ornamentais**; um está **morto**

Ficam declarados como tais, com rótulo no mapa de identificadores
(§4.2 de `docs/reference/ARCHITECTURE.md`), para que ninguém os leia como
identidade de código:

| Identificador | O que é | Estado |
|---|---|---|
| `settings.API_VERSION` | contrato de API | ornamental (não muda com o código) |
| versão em `pyproject` | metadado de pacote | ornamental |
| versão em `frontend/package.json` | metadado de pacote (bumpado por PR de dependência) | ornamental |
| `const version` do serviço Go | literal compilado | ornamental — `-ldflags -X` **não alcança `const`** |
| `report_version` de `config/pipeline.json` | versão de layout de relatório | **morto**: `required` no schema, zero leitores, consumidores eram templates do renderer descontinuado pela [[ADR-129]] |

## Deferido

**Dono: owner.** Só depois de `MATHOMS_BUILD_SHA` estar setada na plataforma de
deploy:

- `${MATHOMS_BUILD_SHA:?}` no compose de prod e fail-fast de boot em ambiente
  de produção. Mergear **antes** brica o próximo deploy, porque
  `.env.prod.example` já traz `MATHOMS_ENVIRONMENT=production`.
- Label OCI + tag imutável por revisão — depende de existir build de imagem em
  CI, hoje inexistente.

**Dono: senior-cto.** Caminho Go (`const version` → `var` + `-ldflags -X`): só
quando o serviço entrar em produção; mudar hoje quebra o teste do servidor, o
espelho Python e o gate de paridade.

**Revisar em 2026-09-15.**

## Consequências

- Fases que não dependem do deploy (dev e CI) entregam valor **sem** tocar
  Dockerfile, compose de prod ou workflow de release.
- Enquanto a env não estiver em produção, a revisão é `NULL` lá — e o read-path
  da review, que é dev/dogfood, **não promete** atribuição de release em
  produção. Prometer antes seria repetir o `"1.0.0"` com roupa nova.
- Quem sobe `uvicorn`/`celery` à mão, ou usa Docker em dev (onde `.git` não é
  montado), produz `desconhecido`. Aceito **porque a linha aparece em
  destaque**, nunca falta.
- O valor é falsificável: nada impede uma env copiada de outro ambiente. As
  defesas são indiretas (sufixo `-dirty`, preflight comparando o processo vivo
  com o HEAD). O inimigo é o esquecimento, não o adversário.

## Emenda 2026-08-05 — não existe deploy; a única fonte que importa é o Makefile

O projeto roda **exclusivamente na máquina do dono**, em dogfood e
desenvolvimento. Não há produção, staging, nem registry. `docker-compose.prod.yml`
é arquivo no repo, não sistema em execução.

### O que sobrevive, e fica mais simples

| Decisão | Estado após a emenda |
|---|---|
| `MATHOMS_BUILD_SHA` é variável de **runtime** | **Confirmada, e agora trivialmente** — sem imagem publicada, não há outro lugar de onde tirar |
| **Zero diff no Dockerfile** | **Confirmada e reforçada** — não há build de imagem em CI para receber `--build-arg` |
| Fonte única real | **`dev/build_info.py` (sem flag) resolvido uma vez por invocação do `make` (`BUILD_SHA :=`) e pinado no env de cada processo LANÇADO** — api, ops-api e os 5 launches de worker — mais `${{ github.sha }}` no CI. Estes são os **dois** ambientes que existem. **`pipeline-run` NÃO é fonte:** aquele processo só faz `apply_async` e sai; quem escreve a coluna é o worker, com a revisão do *seu* launch |
| `/health` ganha campo novo em vez de trocar `version` | **Confirmada, urgência rebaixada** — ver abaixo |
| 4 semvers ornamentais + `report_version` morto | Inalterada |

### O `/health`: risco latente, não incêndio

O texto dizia que trocar o valor de `version` *"derrubaria o container"*, no
presente. Correção: `HealthResponse.version` é de fato `str` required
non-nullable, e o `curl -fsS` de fato mora em `docker-compose.prod.yml` — mas
**esse compose não está rodando em lugar nenhum**. O defeito é real e latente; a
decisão (campo novo, não sobrecarregar `version`) continua certa **pela restrição
de tipo**, que não depende de deploy. O que era "fatal" passa a "correto e sem
pressa".

### O §Deferido estava mal enquadrado

Não é *"owner-gated esperando o dono setar uma variável"*. É **não aplicável até
existir deploy**. A diferença importa: a formulação anterior punha na fila do dono
uma ação que não tem onde acontecer, e foi exatamente com base nela que eu
instruí o dono a configurar variável numa plataforma que ele não usa.

Reclassificado — **nada aqui está na fila de ninguém**; tudo re-entra quando (e se)
houver deploy:

- `${MATHOMS_BUILD_SHA:?}` no compose de prod + fail-fast de boot.
- Label OCI + tag imutável por revisão.
- Atribuição de incidente a release.

**`deployment.environment` e `service.version` no OTel também saem da fila:**
o OTel é opt-in por `OTEL_EXPORTER_OTLP_ENDPOINT` e a variável não está no
`.env.example` — hoje não há coletor escutando, então instrumentar isso entrega
zero. Volta junto com o deploy.

O caminho Go permanece deferido pelo motivo original (`-X` não alcança `const`),
que é independente desta emenda.

### O que fica no lugar

Um único ambiente a servir: **o local**. Isso promove o que era F2 — o preflight
que compara a revisão do **processo vivo** com o HEAD antes de disparar o run — a
peça de maior valor da lane, porque o incidente que ela impede (worker stale
servindo código velho, que invalidou uma rodada de 74 achados) é **local** e já
aconteceu. E o preflight **não depende de migration nenhuma**.

## Emenda 2026-08-06 — correções apontadas por auditoria adversarial

Auditoria de 53 agentes sobre o código entregue (32 achados confirmados de 48
julgados). O que esta ADR afirmava errado:

- **`--export` nunca existiu.** A tabela da emenda anterior citava
  `dev/build_info.py --export`; o script resolve a revisão sem flag. Corrigido
  na própria tabela.
- **`pipeline-run` não é fonte de proveniência.** Aquele processo dispara
  `apply_async` e termina; os dois INSERTs que escrevem a coluna rodam **dentro
  do worker**, com a revisão do launch *do worker*. O pin ali era decorativo e
  foi removido.
- **A cobertura era 1 de 5 launches de worker.** Os outros 4 (incluindo o
  overlay Go, que mata o worker pinado e relança) produziam stage log com
  revisão NULL, e o preflight então mandava reiniciar um worker recém-subido —
  o que desligava o overlay. Todos pinados.
- **`--check-roots` é morto por construção** e não tinha chamador: o
  `sys.path.insert(0, _ROOT)` no topo do próprio script faz os dois imports
  resolverem sob a mesma raiz, então o aviso nunca dispara. A afirmação de que
  "avisa no launch" (ADR-362 §5) fica **retirada**; o mecanismo real de
  detecção é o preflight, que compara o processo vivo com o HEAD.
