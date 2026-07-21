---
id: A37.l2
type: lane
title: "Narrativa da síntese decompõe aporte em parcelas R$ 0,00 — guard de distribuição vazia + keys dinâmicas"
sprint: A37
status: shipped
priority: P1
branch_slug: a37-l2-narrativa-sintese-guard
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a37
  - status/shipped
  - priority/p1
  - area/pipeline
---

# A37.l2 — `narrativa-sintese-guard` (PD-01)

## Problema (evidência verificada 2026-07-20 @ c61c1c29)

A narrativa `top5_decisoes` — Prioridade 1 da Síntese (S10), posição de máximo
destaque do relatório — imprime o aporte mensal configurado seguido de uma
decomposição em **4 parcelas de R$ 0,00**. Renderização confirmada verbatim em
`frontend/src/components/report/sections/S10SinteseSection.tsx:35-40` +
`NarrativeChartCard.tsx:83-87`. Persistente (idêntico no run de 18/07).

Causa dupla no gerador determinístico:

1. **Sem guard de vazio:** `_narrate_top5_decisoes`
   (`pipeline/domain/services/narrativas/charts_narrator.py:409-416`) formata a
   divisão incondicionalmente; o Goal `APORTE_MENSAL` do workspace tem
   `inputs.distribuicao = {}` → todos os `.get(..., 0)` viram 0.
2. **Keys de instrumento hardcoded do legado:**
   `scripts/generate_narratives.py:532-535` lê 4 chaves fixas de instrumento —
   mesmo uma distribuição preenchida com **outros** instrumentos renderizaria
   R$ 0,00 silenciosamente. Padrão duplicado em
   `pipeline/domain/services/narrativas/summaries_narrator.py:74-77` (s10).

## Escopo

- Guard de empty-state: distribuição vazia → omitir o parêntese e usar a forma
  já correta da Prioridade 2 ("a distribuir entre as classes sub-representadas").
- Keys dinâmicas: iterar `distribuicao.items()` (rótulo humanizado), sem lista
  fixa de instrumentos. Aplicar nos **dois** pontos (charts + summaries s10).
- Existe padrão de referência no próprio módulo (`_S9_EMPTY`).

## Critério de aceite

- Unit no narrator: (a) distribuição vazia → prosa sem "R$ 0,00" e sem
  parêntese; (b) distribuição com instrumentos arbitrários → todos aparecem
  com valor; (c) golden do payload dogfood atualizado.
- Teste de regressão escrito **antes** do fix reproduzindo o payload atual
  (distribuição vazia → string contém "R$ 0,00" 4×).

## Risco

Baixo — muda só texto de narrativa; nenhum número calculado. Verificar CV9/CV10
(presença de narrativas) continuam verdes.
