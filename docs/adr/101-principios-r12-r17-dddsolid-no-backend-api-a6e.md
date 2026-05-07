---
id: ADR-101
type: adr
title: "Princípios R12-R17: DDD/SOLID no backend API (A6e)"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 101"]
tags:
  - type/adr
  - status/decidido
size_lines: 53
---

# ADR-101 — Princípios R12-R17: DDD/SOLID no backend API (A6e)

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** §18 A6e

**Contexto:** O plano P3 original focou em `pipeline/` + `scripts/`.
`backend/app/` seguiu padrões razoáveis de Python profissional, mas não
passou pela disciplina DDD/SOLID do pipeline. Auditoria (2026-04-19) mostra:

| Sintoma | Evidência |
|---|---|
| Routers pesados com lógica inline | `api/config.py` 935 linhas · `api/documents.py` 794 · `api/tasks.py` 481 · `api/goals.py` 468 · `api/pipeline.py` 421 |
| Repositórios quase ausentes | Apenas `PipelineArtifactRepository`; 10+ aggregates com queries SQLAlchemy espalhadas |
| DTOs confundidos com ORM | Endpoints retornam Pydantic espelhando SQLAlchemy |
| Sem camada de use cases | Services organizados por entidade, não por caso de uso |
| API sem versionamento | `/workspaces/...` direto, sem `/v1/` |
| Domain events ad-hoc | Notificações, task_progress inline em múltiplos lugares |

**Decisão:** Adicionar A6e como extensão formal do plano P3, com princípios
**R12–R17** (estendem R9-R11 do pipeline):

- **R12 (ISP no backend)** — endpoints retornam DTO dedicado, não ORM model.
- **R13 (Repositórios por aggregate)** — todo acesso a DB via
  `repositories/<aggregate>_repository.py`; routers não importam SQLAlchemy.
- **R14 (Routers finos)** — ≤50 linhas por router (teste estrutural
  enforça).
- **R15 (Application layer por use case)** — `backend/app/application/`
  com 1 módulo por caso de uso; testável sem DB via fakes.
- **R16 (Versionamento explícito)** — `/api/v1/` prefix; breaking changes
  coexistem em `/v2/`.
- **R17 (Domain events tipados)** — `backend/app/events/` com `Event` base
  + handlers registrados; side-effects desacoplados.

Escopo em 6 sub-fases (A6e.1 Repos → A6e.2 DTOs → A6e.3 Use cases → A6e.4
Routers finos → A6e.5 Versioning → A6e.events Events — renomeada de `A6e.6`
em 2026-04-22 para evitar colisão histórica com o Goal slice do track
per-aggregate). Estimativa: 5-7 sessões grandes, ~400+ testes novos.

**Consequências:**
- ✅ Backend ganha a mesma disciplina do pipeline. Qualquer feature nova
  segue padrão consistente.
- ✅ Repository pattern protege cutover DB — múltiplos backends de storage
  convivem sem fricção.
- ✅ Routers finos + codegen (A6f.2) reduzem bugs de integração frontend.
- ⚠️ Refactor de 4900 linhas de routers — trabalho mecânico mas demorado.
- ❌ Adiciona 2 diretórios novos (`application/`, mais repositories) —
  aumenta mental load para devs novos no repo.

**Relação com A6a-d/f**: independente. Recomendado depois de A6b (cutover
DB) para repository pattern entregar valor máximo.

**Artefatos:** [BACKLOG §A6e](BACKLOG.md#a6e--ddd-solid-no-backend-api-adr-101-r12-r17).
