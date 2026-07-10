---
id: ADR-325
type: adr
title: "Fronteira pipeline↔backend enforçada por gate + allowlist declarativo"
status: Proposto
phase: A36.l1a
date: "2026-07-10"
relates_to:
  - "[[ADR-089]]"
  - "[[ADR-256]]"
  - "[[ADR-324]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/ci
---

# ADR-325 — Fronteira `pipeline↔backend` enforçada por gate + allowlist

**Status:** Proposto (A36.l1a) • **Data:** 2026-07-10 • **Relaciona** [[ADR-089]] (pipeline/domain isolado de I/O — tightening), [[ADR-256]] (UoW/session que mitigou o incidente de origem), [[ADR-324]] / ADR-215 (padrão de port injetada no `WorkspaceContext`)

> **Proposto — flippa `Decidido` no PR da Parte B** (inversão dos 3 sinks). A Parte A (gate + allowlist) já enforça a regra; a decisão de *como* tratar cada sink (inverter vs allowlist) é executada na Parte B.

## Contexto

A dependência `pipeline → backend` é proibida por convenção (CLAUDE.md §"Pipeline não importa framework") mas **não era enforçada**: `dev/check_pipeline_boundaries.py` só bloqueava `fastapi`/`celery`/`sqlalchemy`. Um `from backend.app.services...` novo num stage passava **verde** no gate de merge — a fitness function tinha um buraco que **sobreviveu quatro auditorias** (achado ARQ-02 da r4).

Offenders atuais (`from backend` em `pipeline/**`): dois de **composition root** (`cli_run_stage.py`, `live_progress.py` — injetam session/eventos) e dois **sinks de domínio** (`extract_comprovantes_bens.py` → vehicle_upsert/apolice; `parecer_planejador.py` → parecer_orchestrator). O incidente de write-lock em prod (2026-05-22) que motivou parte disso **já foi mitigado** por reuso de `store.session` ([[ADR-256]]); o valor aqui é fechar a **origem** (fronteira não enforçada) e impedir regressão, não o sintoma.

## Decisão

1. **`backend` entra em `FORBIDDEN_ROOTS`** do gate. Qualquer `from backend...`/`import backend` em `pipeline/**` falha, no CI **e** no pre-commit.
2. **Allowlist declarativo por arquivo** (`_BACKEND_ALLOWLIST`: path → motivo). Não é escape hatch: (a) exime só o root `backend` — frameworks seguem proibidos até em arquivo allowlistado; (b) **entrada não-exercida falha o gate** (stale-entry guard) → o allowlist só **encolhe**.
3. **Critério reutilizável de allowlist-vs-inverter:** *cabeia o boundary* (composition root: monta session, bridge de eventos) → **allowlist permanente**; *cruza de dentro do domínio* (stage alcança lateralmente um serviço backend) → **inverter** via port injetada no `WorkspaceContext` (padrão `PropertySupersessionWriter` [[ADR-324]] / família `llm_*` hooks).
4. **`parecer_orchestrator` → inverter, não allowlistar.** É stage de domínio (E6) que cruza para um serviço backend com budget/telemetria — mesma classe dos hooks `llm_*` já injetados; allowlistar admitiria a violação que a ADR fecha.
5. **Faseamento.** **Parte A** (esta): add `backend` + allowlist (2 permanentes + 2 temporários com `TODO A36.l1-B`) + hook de pre-commit — deixa o CI verde e a guarda de regressão ativa já. **Parte B** (follow-up): inverter os 3 sinks (1 PR por sink), removendo cada entrada do allowlist; flippa esta ADR para `Decidido`.

## Consequências

- Regressão de fronteira é pega no commit local e no merge — não na próxima auditoria (resposta operacional ao MAT-03).
- Allowlist visível e auditável; as 2 entradas temporárias são dívida rastreada (tag `TODO A36.l1-B`) que o stale-guard força a remover ao inverter.
- Preservar hooks de budget/telemetria ([[ADR-173]]) ao inverter o parecer — regressão silenciosa aqui é cara.

## Alternativas rejeitadas

- **Lazy import dentro de função:** o gate é AST-walk e pega lazy imports também — não é atalho.
- **Allowlistar todos os 4 offenders permanentemente:** legitimaria a violação de domínio que a ADR existe para fechar; os sinks devem inverter.
- **Não enforçar (status quo):** é exatamente o buraco que sobreviveu 4 auditorias.
