---
id: TRACK-a20-l9-smoke-e2e
type: track
title: "Track A20.L9 — Smoke E2E em compose (gate de fechamento do sprint)"
lane: "[[A20.l9]]"
sprint: A20
status: ready
created_at: "2026-05-29"
agent_role: sre-devops
tags:
  - type/track
  - sprint/a20
  - status/ready
  - priority/p0
  - area/infra
  - area/test
  - area/ci
---

# Track A20.L9 — Smoke E2E em compose (gate final)

> **Lane canônica:** [[A20.l9]] (fluxo de 9 steps, escopo IN/OUT, critério de aceite, riscos, DoD).
> · **ADR canônica:** nenhuma própria — fecha [[ADR-228]] §G3 (gates operacionais A20).
> · **Branch prefix:** `agent/a20-l9-smoke-docker-e2e/*`
> · **Gate de fechamento** — **depende rigidamente de [[A20.l1]] + [[A20.l4]] + [[A20.l5]] + [[A20.l6]] mergeadas**.
>
> ⚠️ **BLOQUEADA — não executável até L1+L4+L6 (Dockerfile multi-stage + GHCR + compose dev) mergeadas. L4/L5 dependem de confirmação externa do owner** (ver [[A20.l4]]). Pickup só quando o pré-requisito rígido estiver verde em `main`.

## Briefing

Script `tests/integration/test_smoke_docker_e2e.sh` valida paridade dev↔prod end-to-end em container: sobe `docker-compose.dev.yml` → seed dogfood → login JWT → upload fixture sintética (extrato+IRPF+apólice) → run pipeline E0→E5 → render relatório React headless → export PDF Playwright → assert PDF >50KB + hash determinístico → tear down idempotente. Roda em GH Actions Linux **semanal + manual** ao fechar sprint. Falha em qualquer step = sprint não fecha.

## Pré-flight (documentar no PR)

```bash
git fetch origin && git worktree list
git log origin/main --oneline | grep -iE 'a20-l1|a20-l4|a20-l6'   # pré-reqs mergeados
ls docker-compose.dev.yml                          # L6 entregou
docker compose -f docker-compose.dev.yml config    # compose válido
ls tests/integration/fixtures/docker_e2e/ 2>/dev/null
```

## Execução (resumo — detalhe em [[A20.l9]])

1. `tests/integration/test_smoke_docker_e2e.sh` self-contained (9 steps), `MATHOMS_LLM_MOCK=true` p/ reprodutibilidade.
2. Fixture sintética anonimizada em `tests/integration/fixtures/docker_e2e/` (sem PII; docstring de origem sintética).
3. Workflow `.github/workflows/smoke-docker-e2e.yml` (weekly cron + `workflow_dispatch`).
4. Assertions: PDF >50KB, hash determinístico em 3 runs, queries de validação no DB, tear down `docker-compose down -v` idempotente.
5. Atualizar [SMOKE_TEST_HUMAN](../../../reference/SMOKE_TEST_HUMAN.md) — smoke automatizado complementa (não substitui) validação humana de UX.
6. **Closure do sprint:** marcar todos os DoD do [[MOC-sprint-a20]], medir TTFR final, consolidar [CHANGELOG](../../../CHANGELOG.md), flip [[MOC-sprint-a20]] `candidate → done` em [[SPRINTS-active]], atualizar [[ADR-228]] §G3.

## Especialistas pre-PR

- **`sre-devops`** (obrigatório) — script + workflow + tear down idempotência + mitigação de flakiness CI.
- **`product-manager`** (obrigatório) — critério de fechamento do sprint (DoD do MOC); valida que A20 está completo antes do flip `done`.

## Definition of Done

Ver [[A20.l9]] §"Definition of Done". Resumo: PR em `main` CI verde; workflow `smoke-docker-e2e.yml` ativo (1ª run semanal verde); SMOKE_TEST_HUMAN atualizada; closure check do MOC completo; [[MOC-sprint-a20]] `done`; [[ADR-228]] §G3.

## Ligações

- **Lane:** [[A20.l9]] · **Sprint MOC:** [[MOC-sprint-a20]] · **Gates:** [[ADR-228]] §G3
- **Upstream (rígido):** [[A20.l1]] (multi-stage), [[A20.l4]] (GHCR), [[A20.l5]] (Trivy scan), [[A20.l6]] (compose dev).
