---
id: A37.l6
type: lane
title: "Labels de categoria snake_case cruas nas superfícies do relatório — mapa único + humanize fallback"
sprint: A37
status: open
priority: P1
branch_slug: a37-l6-labels-categoria-humanizadas
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a37
  - status/open
  - priority/p1
  - area/frontend
---

# A37.l6 — `labels-categoria-humanizadas` (PD-03 + PD-08)

## Problema (evidência verificada 2026-07-20 @ c61c1c29)

1. **Orçamento Prospectivo (PD-03):**
   `frontend/src/components/report/cards/OrcamentoProspectivoCard.tsx:120`
   renderiza `{CATEGORY_LABELS[key] ?? key}` — o mapa (l.15-33) não contém
   `lazer`, `das_simples`, `folha_pj`, `aporte_investimento`, então a tabela
   exibe snake_case cru ao lado de categorias bem rotuladas.
2. **Gastos Pontuais (PD-08):** o endpoint copia `tx.categoria` cru para o DTO
   (`backend/app/application/report/consumo_pontuais.py::_to_item`) e
   `ConsumoConscienteCard.tsx:111` imprime verbatim — **toda** linha da lista
   mostra código (`nao_identificado`, `lazer_viagens`, …).
3. O humanizador já existe no repo e não foi aplicado:
   `DespesasDoughnutChart.tsx:25,47` (mapa + `humanize()`), duplicado do mapa
   do card de orçamento.

## Escopo

- Extrair **um** módulo de labels de categoria (mapa + `humanize(key)` como
  fallback) e consumir nos 3 pontos (orçamento, doughnut, gastos pontuais).
- Completar o mapa com as 4 chaves faltantes; fallback nunca exibe `_`.
- Decidir camada: humanizar no frontend (preferido — o código de categoria é
  contrato estável da API) e manter o DTO cru.

## Critério de aceite

- Unit (Vitest): para toda key presente no payload dogfood das duas superfícies,
  o label renderizado não contém `_` nem inicia minúscula-código (KR-B).
- Teste de regressão antes do fix (as 4 keys atuais → cru).
- Zero duplicação: os dois mapas antigos importam do módulo único.

## Risco

Baixo — só camada de apresentação; snapshot tests do relatório atualizados no
mesmo PR.
