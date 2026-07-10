---
id: A36.l1
type: lane
title: "Boundary-lint proíbe `backend` + inverter escritas de domínio no pipeline"
sprint: A36
status: planned
priority: P1
branch_slug: a36-l1-boundary-lint-backend
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a36
  - status/planned
  - priority/p1
  - area/pipeline
  - area/ci
---

# A36.l1 — `boundary-lint-backend` (ARQ-02 · ARQ-01)

## Problema

A dependência circular `pipeline ↔ backend` sobreviveu **quatro auditorias**
porque o fitness function que deveria guardar a fronteira **não a guarda**:
`dev/check_pipeline_boundaries.py:21` só proíbe `fastapi`, `celery` e
`sqlalchemy` — **não** `backend`. Um `from backend.app.services...` novo num
stage passa **verde** no gate de merge (`.github/workflows/ci.yml:360`).

Sinks de escrita de domínio que hoje importam o backend direto (a inverter):

- `pipeline/stages/extract_comprovantes_bens.py:192` — `vehicle_upsert`
- `pipeline/stages/extract_comprovantes_bens.py:223` — `apolice_reconciliation`
- `pipeline/stages/parecer_planejador.py:171` — `parecer_orchestrator`

Entry-points **legítimos** (inversão de entry-point, não a mexar — devem entrar
num allowlist, não ser refatorados):

- `pipeline/cli_run_stage.py` — injeta a session no boundary
- `pipeline/live_progress.py:28,60` — bridge de eventos

O incidente de write-lock em prod (2026-05-22, comentado em
`extract_comprovantes_bens.py:191,221`) já foi mitigado por reuso de
`store.session` ([[ADR-256]]); esta lane fecha a **origem** (a fronteira não
enforçada), não só o sintoma.

## Escopo

1. Adicionar `"backend"` a `FORBIDDEN_ROOTS` em `dev/check_pipeline_boundaries.py`.
2. Introduzir mecanismo de **allowlist por arquivo** no lint (hoje inexistente,
   ~10 linhas): pular `cli_run_stage.py` e `live_progress.py` com motivo
   declarado. `_violations_in_file` passa a consultar o allowlist.
3. Rodar o lint → vai acusar os 3 sinks de domínio. Inverter cada um: expor a
   operação de escrita atrás de uma **port injetada no `WorkspaceContext`**
   (mesmo padrão do `ArtifactStore`), em vez de `from backend...` no stage.
4. ADR curta registrando a decisão sobre `parecer_planejador` (inverter vs
   allowlistar — é orquestração de entry-point ou domínio?).

**Fora de escopo:** refatorar os entry-points legítimos; mexer no mecanismo de
session/UoW (já resolvido em [[ADR-256]]).

## Critérios de aceite

- `python3 dev/check_pipeline_boundaries.py` acusa qualquer `from backend...`
  novo em `pipeline/**`.
- Os 3 sinks atuais estão **invertidos** (port injetada) ou no allowlist com
  motivo explícito — sem `from backend...` solto em stage.
- CI verde legítimo (não por allowlist dos sinks de domínio).
- Uma PR de teste que adicione `from backend.app.services import x` num stage
  **falha** o gate.

> **Ordem numa PR só:** o passo 1 deixa o CI vermelho até o passo 3 terminar.
> Fazer 1–4 na mesma PR, ou allowlistar temporariamente os sinks e abrir a
> inversão como follow-up rastreado.

**Esforço:** S (lint) + M (inversão). **Origem:** auditoria r4 (ARQ-02, ARQ-01).
