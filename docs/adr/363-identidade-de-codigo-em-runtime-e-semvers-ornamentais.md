---
id: ADR-363
type: adr
title: "Identidade de código é fato de runtime injetado no deploy, não conteúdo da imagem"
status: Proposto
phase: "A40"
date: "2026-08-05"
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
