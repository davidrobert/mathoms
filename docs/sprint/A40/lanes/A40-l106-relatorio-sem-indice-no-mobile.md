---
id: A40.l106
type: lane
title: "O relatório não emite índice de seção algum no mobile: rolagem longa sem navegação, enquanto o desktop emite o índice completo"
sprint: A40
status: open
priority: P2
branch_slug: a40-l106-relatorio-sem-indice-no-mobile
owner: product-designer
depends_on: []
adrs: []
tags: [type/lane, sprint/a40, status/open, priority/p2, area/frontend]
---

# A40.l106 — `relatorio-sem-indice-no-mobile`

> **Origem:** `RR8-01` da rodada unificada **U4** ([[REPORT-REVIEWS-active]] §r8).
> **Verificado pelo loop principal**, sobre a captura de render real das duas viewports.

## O defeito

Na viewport de **1280px**, logo após o breadcrumb, o relatório emite o próprio índice de
seções (`VISÃO GERAL · O que mudou · Perfil da Família · 1 Patrimônio · 2 Fluxo de Caixa ·
2.5 Seguros · 3 Investimentos · DETALHES · 4 Real Estate · 7 Independência Financeira ·
8 Carga Tributária PJ · 8.1 …`). Na de **390px**, o mesmo breadcrumb é seguido
**diretamente pela capa**. Zero entradas de índice, num documento de **32.728 px**.

## Falseamento tentado, e por que ele não derruba o achado

Procurei nomes de seção nos primeiros 3.000 caracteres do dump mobile e achei 4 — mas são
**cabeçalhos encontrados ao rolar**, não entradas de índice; a comparação por faixa de
linha entre os dois dumps desfaz a ambiguidade. E o **shell do app** (notificações, plano,
ação, documentos, pipeline) é **byte-idêntico** nas duas viewports, então o que falta é
especificamente a navegação **do relatório**.

## Critério de aceite

- [ ] A viewport mobile oferece navegação de seção — índice, sumário colapsável ou
      equivalente.
- [ ] **Controle:** o dump linearizado de 390px passa a conter as entradas de índice, e a
      comparação de faixa de linha com o de 1280px deixa de divergir na região do índice.

## Fora de escopo

A faixa sticky de navegação ([[A40.l104]]) é comportamento de faixa **existente**; esta
lane é sobre a lista de seções **não existir** no mobile.
