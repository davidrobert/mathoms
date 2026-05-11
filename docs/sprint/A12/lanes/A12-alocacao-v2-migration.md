---
id: A12.alocacao-v2
type: lane
title: "Alocação-alvo schema v1→v2 (7 classes AUVP, desvio backend-driven)"
sprint: A12
status: open
aliases: ["A12.alocacao-v2-migration", "A12.ALOCACAO_V2", "A12 alocacao v2"]
priority: P2
depends_on: []
parallel_with: ["[[A12.cat-learning-loop]]"]
adrs_canonical:
  - "[[ADR-141]]"
tags:
  - type/lane
  - sprint/a12
  - status/ready
  - priority/p2
  - area/methodology
  - area/persistence
  - methodology/auvp
---

# A12.alocacao-v2-migration — Alocação-alvo schema v2

> Lane uni-fase (5d eng). ADR canônica: [[ADR-141]] (Proposto, flippa para Decidido no PR de implementação).
> Track: [[TRACK-alocacao-v2-7-classes-migration]].

## Origem

Débito explícito da Fase A entregue em A11 (`AlocacaoAtualVsAlvoCard`, 2026-05-11). Card de relatório S3 calcula desvio em pp client-side agregando 10 buckets canônicos do [[ADR-193]] em 4 buckets v1 — solução pragmática para entregar valor enquanto v2 não está em produção. Lane atual migra para schema v2 (7 classes) com `derived.desvio_*` calculado no backend, eliminando o util client-side.

## Escopo (resumido — detalhe no track)

1. Backend serializer `_serialize_alocacao_goal` emite v2 + `derived.desvio_max_pct` + `derived.desvio_por_classe`.
2. Seed `seed_goals_workspace.py` grava v2 diretamente.
3. Wizard `/plano/alocacao` editor de 7 sliders.
4. Card relatório consome `derived.*` do payload (sem cálculo local).
5. Tombstones do `report_layout.yaml` removidos.
6. Pipeline enforcers de `alocacao_atual`/`alocacao_alvo` reconciliados.
7. Goldens E5N regenerados.
8. ADR-141 flippa Proposto → Decidido (A12.alocacao-v2).

## Pré-requisitos

- Nenhum pré-requisito interno do A12.
- Pode rodar em paralelo com [[A12.cat-learning-loop]].

## Branch prefix

`agent/alocacao-v2/<yyyyMMdd-HHmm>`

## Time-box

5d eng.

## Gate de merge

- Suíte verde (`pytest backend/tests -q`, `pytest tests -q`, `npm test -- --run`).
- Goldens E5N revisados manualmente.
- Co-design `financial-planner` + `product-designer` no wizard (7 sliders).
- Snapshot OpenAPI atualizado se shape de `alocacao_alvo` mudou em endpoint.
- ADR-141 com frontmatter `status: Decidido` + `phase: A12.alocacao-v2`.
