---
id: A40.l54
type: lane
title: "`hidden md:block` entrega ao papel a variante mobile: varredura dos call-sites e gate da classe (ADR-381 D1)"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l54-hidden-md-block-no-papel
adrs:
  - "[[ADR-381]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/frontend
  - area/report
---

# A40.l54 — `hidden-md-block-no-papel`

> **Aberta em 2026-08-12**, no fecho da [[A40.l45]] (decisão do dono: os
> follow-ups sem dono viram lanes na A40). A [[ADR-381]] D1 fixou a regra; esta
> lane executa a varredura que a l45 declarou fora de escopo.

## Problema

A caixa de página A4 tem **703px**, então `md:` (768px) **nunca casa no PDF** —
todo `hidden md:block` escrito como "isto é a variante desktop" entrega ao papel
a variante mobile, e o próximo call-site sem par mobile completo **some do PDF
sem erro e sem gate**.

Estado medido em 2026-08-11 (parecer do `product-designer` + verificação por
`pdftotext` na l45):

- `alocacaoCardParts.tsx` (`DesktopTable`/`MobileStack`) e
  `CoberturaSegurosCard.tsx`: a tabela desktop **não existe no PDF** hoje. O
  dado sobrevive porque a variante mobile carrega valor/atual/alvo/desvio —
  **por acidente, não por desenho**. São as colunas "Classe/Desvio (pp)" e
  "Status/Vigência" que a sonda de perda tela→PDF da l45 listou como ausentes.
- ~21 wrappers `overflow-x-auto` no relatório: no papel viravam clip silencioso
  até o `report-print.css` da l45 devolver `overflow: visible` — a quebra por
  rótulo cobre a classe, mas ninguém mediu tabela a tabela se todas cabem.

## Escopo

1. Inventariar todo `hidden md:block` / `md:hidden` / `hidden sm:*` sob
   `frontend/src/components/report/` e classificar cada um: a variante que o
   papel recebe carrega **todo** o dado da outra?
2. Converter os divergentes para o idioma da [[ADR-381]]: `sm:` como divisor
   papel/telefone, `@media print` para o que o papel faz de diferente.
3. Gate da classe: a sonda de perda tela→PDF da l45 (comparar frases visíveis
   do `<article>` com a camada de texto do `pdftotext`) vira spec permanente —
   derivada do DOM, não lista de componentes, com âncora anti-fail-open.

## Critério de aceite

- [ ] Inventário com veredito por call-site commitado na lane (tabela).
- [ ] O PDF real contém as colunas hoje ausentes (`Classe`, `Desvio (pp)`,
      `Status`, `Vigência`) — verificado por `pdftotext`, não por emulação.
- [ ] Provado por mutação: um `hidden md:block` novo sem par completo deixa o
      gate vermelho.
