---
id: A21.l8
type: lane
title: "LGPD Art.18 — export/deleção (data-subject rights)"
sprint: A21
plan: PLAN-launch-trust
status: open
priority: P0
branch_slug: a21-l8-lgpd-data-subject-rights
depends_on: []
parallel_with:
  - "[[A21.l7]]"
tags:
  - type/lane
  - sprint/a21
  - status/open
  - priority/p0
  - area/seguranca
---

# A21.l8 — LGPD Art.18 export/deleção (data-subject rights)

> **Plano:** [[PLAN-launch-trust]] §F2-G3 (lane OWNED — gap que nenhuma wave do PLATFORM_REVIEW cobre).
> **⚠️ ADR Proposto antes do PR** (contrato de API + política de retenção).

## Contexto

Direito do titular (LGPD Art.18): exportar e deletar seus dados. Sem isto, o
launch é não-conforme para cliente brasileiro. Não está em nenhuma wave do
PLATFORM_REVIEW.

## Escopo

- Rota de **export** — dump estruturado dos dados do titular no workspace.
- Rota de **deleção** — remoção/anonimização respeitando o que a lei exige
  reter (ex.: audit log de l7 vs. dado financeiro do titular).
- Política de retenção declarada (o que apaga, o que anonimiza, o que retém e
  por base legal).

## Critério de aceite

- Rota export/deleção testada (A21-KR6, parte 2).
- Interação com o audit log de l7 resolvida (deleção do titular não apaga o log
  de auditoria — base legal distinta).

## Dependências

- **Sem deps** — pickup imediato. Paralela a l7.
- **ADR Proposto** antes do PR (idealmente co-decidido com o ADR de l7 — ambos
  tocam retenção de dado sensível).
- Puro código/schema — **sem passo humano, sem deploy em prod**.
