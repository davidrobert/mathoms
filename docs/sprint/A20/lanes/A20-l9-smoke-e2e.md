---
id: A20.l9
type: lane
title: "Docker dev↔prod parity — L9 Smoke E2E em compose (login + relatório + PDF)"
sprint: A20
status: blocked
priority: P0
branch_slug: a20-l9-smoke-docker-e2e
depends_on:
  - "[[A20.l1]]"
  - "[[A20.l4]]"
  - "[[A20.l5]]"
  - "[[A20.l6]]"
parallel_with: []
adrs_canonical: []
tags:
  - type/lane
  - sprint/a20
  - status/blocked
  - priority/p0
  - area/infra
  - area/test
  - area/ci
---

# A20.L9 — Smoke E2E em compose (gate de fechamento)

> **Gate final** de [[MOC-sprint-a20]] — bloqueia fechamento do sprint.
> Validação empírica de paridade dev↔prod end-to-end. Status `blocked` até
> que L1, L4, L5, L6 mergeiem.

## Resumo

Script `tests/integration/test_smoke_docker_e2e.sh` que executa fluxo
completo em container:

1. Sobe `docker-compose.dev.yml`
2. Seed user dogfood + workspace mínimo
3. Login via API (JWT)
4. Upload de fixture sintética (extrato + IRPF + apólice)
5. Trigger pipeline run (E0 → E5)
6. Render relatório React headless
7. Export PDF via Playwright
8. Valida PDF >50KB + assina hash
9. Tear down

Roda em GH Actions Linux runner como job **semanal** + gate manual ao fechar
sprint. Falha em qualquer step = sprint não fecha.

## Escopo IN

- Script `tests/integration/test_smoke_docker_e2e.sh` self-contained.
- Workflow `.github/workflows/smoke-docker-e2e.yml` rodando weekly + manual
  trigger.
- Fixture sintética em `tests/integration/fixtures/docker_e2e/` (extrato + IRPF
  + apólice anonimizados — sem PII).
- Validação de output: PDF >50KB, hash determinístico, assertions em log do
  pipeline.
- Documentação em [SMOKE_TEST_HUMAN](../../../reference/SMOKE_TEST_HUMAN.md) como complemento (humano
  valida UX, smoke valida funcional).
- Tear down idempotente (rodar 2× consecutivamente sem erro).

## Escopo OUT

- E2E em prod compose (`docker-compose.prod.yml`) — exigiria env real com
  Fernet/JWT, perigoso em CI. Usa `dev.yml` estendido.
- `docker-compose.ci.yml` dedicado — gap 4 senior-cto adiado.
- Múltiplos workspaces, multi-user, concorrência — V2.
- Performance benchmark (latency, throughput) — só funcional.

## Pré-requisitos rígidos

- [[A20.l1]] mergeada (Dockerfile multi-stage funciona).
- [[A20.l4]] mergeada (imagens em GHCR ou buildadas localmente).
- [[A20.l5]] mergeada (Trivy scan rodou nas imagens usadas).
- [[A20.l6]] mergeada (`docker-compose.dev.yml` existe).
- Fixture sintética validada (não PII, não real).

## Critério de aceite

1. Script `test_smoke_docker_e2e.sh` verde em GH Actions (Linux x86_64) em
   <15min wall-clock.
2. PDF gerado tem >50KB (assertion explícito).
3. Hash do PDF determinístico entre 3 runs consecutivos (provando que
   render é reprodutível dado mesma fixture + mesma SHA de imagem).
4. Workspace + uploads + pipeline state corretos no DB (queries de validação
   no script).
5. Tear down limpo: `docker-compose down -v` + remove fixture residual.
6. Re-run consecutivo do script sem erro (idempotência).

## Definition of Done

- [ ] PR mergeado em `main` com CI verde.
- [ ] Workflow `smoke-docker-e2e.yml` ativo, primeira run semanal verde.
- [ ] [SMOKE_TEST_HUMAN](../../../reference/SMOKE_TEST_HUMAN.md) atualizada — smoke automatizado
      complementa, não substitui, validação humana de UX.
- [ ] **Sprint A20 closure check:** todos os DoD do MOC marcados, métrica
      TTFR final medida e registrada, [CHANGELOG](../../../CHANGELOG.md) consolidada.
- [ ] [[MOC-sprint-a20]] flippado `candidate → done` em
      [[SPRINTS-active]].
- [ ] [[ADR-228]] §G3 atualizada (operational gates A20).

## Riscos top 3

1. **Flakiness em CI** — pipeline E0→E5 com LLM calls pode ser flaky. Mitigação:
   fixture usa LLM cached fixtures ou mock (`MATHOMS_LLM_MOCK=true` env);
   reproducibilidade rigorosa.
2. **Tempo de wall-clock >15min em CI** — Postgres + Alembic + seed + pipeline
   + render + PDF é uma sequência longa. Mitigação: paralelizar steps quando
   possível; cache de imagem GHCR; medir baseline e otimizar gargalo.
3. **Fixture vaza dado real** — risco de PII em fixture. Mitigação: review
   manual + lint hook (`dev/check_pii_in_fixtures.py`); cada fixture com
   docstring "anonimizada de fonte sintética / pública".

## Especialistas pre-PR

- **`sre-devops`** (obrigatório) — review do script + workflow + tear down
  idempotência.
- **`product-manager`** (obrigatório) — review do critério de fechamento do
  sprint (DoD em §"Definition of Done"); valida que A20 está completo.

## Detalhe operacional

Track prompt em [`../tracks/a20-l9-smoke-e2e.md`](../tracks/a20-l9-smoke-e2e.md) (criado 2026-05-29; pós-F3/ADR-182 tracks vivem em `docs/sprint/<X>/tracks/`).
