---
id: A40.l3
type: lane
title: "Janela canônica: todo número rotulado 12m lê janela_12m"
sprint: A40
plan: PLAN-report-trust
status: planned
priority: P0
branch_slug: a40-l3-janela-canonica-fluxo
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/planned
  - priority/p0
  - area/frontend
  - area/pipeline
---

# A40.l3 — `janela-canonica-fluxo` (RV3-02 · causa-raiz)

## Problema

`fluxo_caixa.janela_12m.*` tem **zero consumidores** em `frontend/src`
(`rg janela_12m frontend/src` → 0). Todo número de fluxo na tela **e no PDF** vem
do bloco de janela `full`, enquanto o valor canônico de 12 meses existe no payload
e nunca é lido.

Consequência visível: o gráfico declara a janela do slice renderizado
(`FluxoMensalChart.tsx:76-92`) e cita agregado de janela `full` na mesma frase. O
`isPrint` força a janela curta, então **o PDF carrega a mesma inconsistência**.

Não é inconsistência a decidir — é **não-conformidade com invariante já escrito**:
a janela canônica para ratios/KPIs já está declarada, e `full` já está restrito a
"apenas com rótulo". Isso muda o custo de fechar (é conformidade, não co-design) e
a guarda (gate de contrato, não ADR nova). RV3-16 e RV3-17 são a mesma violação.

## Escopo

- `FluxoMensalChart.tsx:76-92` — `buildContext` deriva do **slice renderizado** ou
  consome `fluxo_caixa.janela_12m.*` quando a janela é 12m.
- `conclusionUtils.ts:109` — mesma correção, e passa a **rotular** a janela.
- `ConsumoConscienteCard.tsx:45` — consome `total_pontuais_janela` quando
  `janela != full` (hoje `rg total_pontuais_janela frontend/src` → 0).
- Regra geral: **nenhum texto de chart cita agregado de janela diferente da
  renderizada.**

## Critério de aceite

- `rg 'janela_12m' frontend/src` retorna **> 0**.
- Teste de contrato de janela com fixture onde `janela_12m.*` ≠ bloco `full` por
  valor detectável: todo componente cujo rótulo declara 12m exibe o valor de
  `janela_12m`. **Hoje esse teste falharia** — é o sinal de que ele mede o certo.
- **Verificação renderizada obrigatória** (débito de método herdado): conferir a
  legenda no navegador **e** no PDF via `pdftotext`.
- Declarar o sinal esperado do delta — atenção: a correção move a sobra exibida
  **para cima**, não para baixo (a legenda de 44m *subestimava* a sobra dos 12m).

## Guarda anti-regressão

Teste de contrato de janela permanente: fixture com os dois blocos divergentes +
assert por componente rotulado. Impede que a próxima feature volte a ler o
agregado longo por conveniência.
