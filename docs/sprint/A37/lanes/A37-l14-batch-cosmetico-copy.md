---
id: A37.l14
type: lane
title: "Batch cosmético de copy/labels + decisão de agrupamento do aporte no doughnut"
sprint: A37
status: planned
priority: P2
branch_slug: a37-l14-batch-cosmetico-copy
adrs: ["[[ADR-333]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a37
  - status/planned
  - priority/p2
  - area/frontend
  - area/pipeline
---

# A37.l14 — `batch-cosmetico-copy` (PD-02/06/07/10/11/12) — prioridade operacional P3

> Frontmatter marca P2 por limite do schema; tratar como **cauda** (W3).
> Todos evidenciados na revisão de 2026-07-20 @ c61c1c29.

## Itens

1. **PD-02:** título "Top 5 Decisões de Impacto"
   (`S10SinteseSection.tsx:37`) com 3 decisões — título neutro ou contagem
   derivada do `length`.
2. **PD-06:** pluralização de sistema "3 apólice(s) vigente(s)" em
   `pontos_urgentes[].impacto` (gerado no backend) — pluralizar corretamente.
3. **PD-07:** copy expõe rota interna "/plano" e o termo "workspace"
   (narrativas s9/bubble_riscos) — linguagem de produto ("tela Plano de Ação",
   "este relatório").
4. **PD-10 (decisão `financial-planner`):** aporte a investimento aparece como
   3ª maior fatia do doughnut de "Despesas por Categoria"
   (`despesa_datasets`) — semanticamente é poupança ([[ADR-333]]: aporte =
   transferência). Decidir: excluir do doughnut ou fatia separada "Poupança/
   Aporte"; **não** mexer em `despesa_total` (conservação intocada).
5. **PD-11:** `cenarios_conjuge[].resumo` com formato monetário US
   ("R$ 13,200") — corrigir o gerador ou remover o campo se morto (nenhum
   componente o lê hoje).
6. **PD-12:** narrativa s6 (câmbio) enumera contas hardcoded e omite a
   terceira conta USD → soma não fecha (`generate_narratives.py:197-217`).
   **Dead data** (s6 não renderiza; seção queimada por design) — corrigir a
   enumeração dinâmica ou remover a narrativa morta.

## Critério de aceite

- Cada item com unit/snapshot próprio; PD-10 com decisão registrada (nota na
  ADR-333 ou nova ADR curta) antes do código.
- Zero regressão de conservação (CVs verdes) — os itens são de apresentação.

## Risco

Baixo. PD-10 é o único com dimensão de domínio — gate: decisão antes de código.
