---
id: A21.l3
type: lane
title: "Contrato EntityDedup (Protocol + runner compartilhado)"
sprint: A21
plan: PLAN-launch-trust
status: planned
priority: P1
branch_slug: a21-l3-entity-dedup-contract
depends_on:
  - "[[A21.l1]]"
  - "[[A21.l2]]"
parallel_with: []
tags:
  - type/lane
  - sprint/a21
  - status/planned
  - priority/p1
  - area/pipeline
---

# A21.l3 — Contrato EntityDedup (Protocol + runner)

> **Plano:** [[PLAN-launch-trust]] §F1-O2.
> **⚠️ ADR Proposto antes do PR** (refactor estrutural de 2 serviços de produção).

## Contexto

`imoveis_dedup.py` (387 linhas) e `investimentos_dedup.py` (263 linhas)
implementam o **mesmo algoritmo** — o header do segundo diz literalmente
*"Espelha imoveis_dedup com duas divergências de domínio"*. A próxima entidade
(dívida, veículo, previdência) copiaria um terceiro espelho. Drift garantido.

## Escopo

- `pipeline/domain/services/entity_dedup.py` com `EntityDedupPolicy` (Protocol)
  + `run_entity_dedup(items, policy) -> DedupOutcome` + `DedupOutcome`/`DedupWarning`.
- `imoveis_dedup` e `investimentos_dedup` reescritos como **policies** (~30
  linhas cada) sobre o runner — **sem mudar comportamento**.
- Esboço do contrato em [[PLAN-launch-trust]] §F1-O2.

## Critério de aceite

- Suíte INV-1..8 (l1) + golden fn/fp (l2) **continuam verdes** após o refactor
  — a rede de segurança é o que prova que a extração não mudou comportamento.
- Zero mudança em `fn_rate`/`fp_rate` vs. baseline pré-refactor.

## Fronteira de escopo

- **Filtro PF×PJ ([[ADR-268]]) NÃO entra no contrato.** `detect_pj_suffix`
  é **pré-filtro de não-pessoa** (decide o que *é* entidade), não regra de
  dedup (decide se duas entidades são a mesma). O runner `run_entity_dedup`
  opera só sobre PFs já filtradas. INV-9 vive em l1; o contrato de l3 não o
  absorve.

## Dependências e risco

- Depende de l1 + l2 (a rede tem que estar verde **antes** do refactor).
- **Risco:** refactor de código de produção correto. Mitigação: l1+l2 são o
  gate real que abre F3 — se l3 escorregar, vira A22 sem perder os gates.
- **ADR Proposto** antes do PR de implementação.
