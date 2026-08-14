---
id: A43.l3
type: lane
title: "Contratos externos minimizados e corpus canônico de compatibilidade"
sprint: A43
plan: PLAN-competitive-pierre
status: planned
priority: P1
branch_slug: a43-l3-contratos-externos-minimizados-e-eval
depends_on: ["[[A43.l1]]"]
adrs: ["[[ADR-090]]", "[[ADR-109]]", "[[ADR-207]]", "[[ADR-319]]"]
tags: [type/lane, sprint/a43, status/planned, priority/p1, area/backend, area/data-contract, area/security]
---

# A43.l3 — Contratos externos minimizados e eval

> **Origem:** [[A43]] · [[PLAN-competitive-pierre]].

## Problema

O objeto interno de relatório é amplo e dinâmico. Entregá-lo a um host externo
vaza campos sem necessidade e convida o modelo a reinterpretar dados canônicos.

## Decisão

Criar DTOs Pydantic externos, separados dos internos, para os três jobs. Cada campo
declara unidade, período, `as_of`, origem, null semantics e limites. Definir junto o
corpus de 10 tarefas, com dois workspaces e dois reports/runs PII-zero.

## Critério de aceite

- JSON Schema versionado; `additionalProperties: false` no boundary.
- Zero CPF/email/nome/filename/documento/raw E5/prompt/token/ID desnecessário.
- Caps de itens/bytes, paginação e truncation explícita.
- Métrica retorna `metric_key`, valor/unidade, período, `as_of`, seção e fontes;
  nenhum cálculo é refeito pela tool.
- Falhas tipadas sem diagnóstico interno; scanner anti-PII/método cobre sucesso e erro.
- Eval: ≥9/10 corretas, 100% das suportadas com fonte, negativas sem overreach.
- Co-design `data-engineer` para contrato e `financial-planner` para semântica.
