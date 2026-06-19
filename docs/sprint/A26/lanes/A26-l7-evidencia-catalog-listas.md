---
id: A26.l7
type: lane
title: "Catálogo de citação cobre folhas de LISTA (fonte única forward↔reverse)"
sprint: A26
plan: PLAN-data-lineage
status: shipped
priority: P1
branch_slug: evidencia-catalog-listas
ship_pr: 662
ship_date: "2026-06-18"
adrs:
  - "[[ADR-279]]"
  - "[[ADR-292]]"
depends_on:
  - "[[A26.l1]]"
parallel_with:
  - "[[A26.l6]]"
tags:
  - type/lane
  - sprint/a26
  - status/planned
  - priority/p1
  - area/data-lineage
  - area/llm
---

# A26.l7 — `evidencia-catalog-listas` (Onda 6 · cobertura de citação · Regime A)

> **Plano:** [[PLAN-data-lineage]] §Onda 6. **Sem gate de tráfego** (Regime A —
> código + eval). Fecha a **raiz comportamental** do incidente [[ADR-292]]: o modelo
> inventava filtros JSONPath porque o catálogo v1 não oferecia path para valores de
> LISTA. Co-design `product-manager` + `data-engineer` 2026-06-17.
> **Recomendada ANTES do flip da [[A26.l2]], mas NÃO bloqueante** — l2 pode flipar
> com `missing_path` fail-open; esta lane sobe a **margem do KR1**, não destrava l2.

## Objetivo

Estender o catálogo de citação ([`parecer_citation_catalog.py`](../../../../backend/app/services/parecer_citation_catalog.py))
para enumerar folhas monetárias escalares de **listas** (`alocacao_por_classe`,
`top_ativos`) via paths indexados `$.lista[idx].subkey`, derivando o conjunto
**forward** (o que o catálogo oferece) da **mesma** capacidade **reverse** que o
verificador (`_walk_segments`) já resolve — fonte única, não podem divergir.

## Motivação

Causa-raiz de cobertura do incidente: o catálogo v1 (`_iter_money_leaf_paths`)
recursa **só em dicts** ("strings/listas ficam fora do v1"), enquanto o verificador
já resolve `[idx]`/`[*]`. O modelo preenche a lacuna *adivinhando* filtros
(`[?(@.classe=='Caixa')]`) — que a [[ADR-292]] coage para `None` (não quebra, mas
perde a citação). Cobrir listas faz o modelo **parar de inventar** porque ganha path
escalar legítimo. Alocação por classe e posição patrimonial individual são
exatamente a evidência de alto valor de um parecer.

## Escopo

- `_iter_money_leaf_paths` recursa em `list` emitindo `$.lista[i].subkey` por item.
  **Contorna o guard `key.isidentifier()`** de `_leaf_paths_for` (índice não é
  identifier — sem branch próprio a recursão de lista é no-op silencioso).
- **Emitir `[idx].subkey` escalar único, NUNCA `[*]` agrupado** ([[ADR-292]]/[[ADR-293]]):
  `[*]` resolve para a lista inteira e `_numeric_leaves`+`any()` maximiza falso-verde.
- **Cap por lista (top-K por valor):** reusar a ordenação desc de `top_ativos`
  (K≈3–5); não estourar `max_entries=30` com lista de 40 ativos. Display inclui o
  `nome`/`classe` para o modelo saber qual item é (label, não path).
- Endereçamento posicional `[idx]` é seguro **inline** (resolve no mesmo run). A
  estabilidade cross-run (chave natural) é da [[ADR-293]]/Onda 6 (só importa ao
  **persistir** edge), fora desta lane.

## Critério de aceite

- Round-trip: todo path emitido por `build_citation_catalog` (incl. `[idx]`) resolve
  `found=True` em `drill.get_e5_jsonpath` (paridade forward↔reverse por construção).
- `[idx].valor` produz exatamente **1 folha** em `_numeric_leaves` (não falso-verde).
- Lista de 40 ativos não estoura `max_entries` (top-K por valor; sem órfão no
  `render_citation_catalog`).
- Eval golden (owner-gated) reduz `whitelist_miss`+`missing_path` vs. baseline da
  [[A26.l6]]. Conforma [[ADR-279]] §E + [[ADR-292]] — **sem ADR nova**.

## Owner

Agente da lane; co-design `data-engineer` (contrato do catálogo) + `prompt-engineer` (eval).
