---
id: A42.l24
type: lane
title: "Três checks meus publicam verde sobre população em que a falha é impossível por construção — e um deles exclui justamente o stage sob suspeita"
sprint: A42
status: open
priority: P1
branch_slug: a42-l24-check-cujo-denominador-torna-a-falha-impossivel
owner: senior-cto
depends_on: []
adrs: ["[[ADR-416]]"]
tags: [type/lane, sprint/a42, status/open, priority/p1, area/dados]
---

# A42.l24 — `check-cujo-denominador-torna-a-falha-impossivel`

> **Origem:** `LC9-04` + `LC9-05` + `LC9-10` da rodada unificada **U5**
> ([[LEDGER-CERTIFY-active]] §r9). **Achado do instrumento contra si mesmo**, na mesma
> classe que a [[A42.l21]] e o `LC8-01` da rodada anterior.

## Os três

1. **X4 (ancoragem do parecer) é falso-verde.** Dos 10 literais monetários do parecer,
   **9** vivem num campo que o **backend** preenche copiando `path → valor` do **mesmo
   payload** que o check relê. **Órfão é impossível por construção.** A superfície
   monetária **autoral do modelo** é **n=1**. Publiquei `FECHA ✅ n=10/10` sobre um
   denominador em que 9 de 10 não podiam falhar.
2. **X5 (proveniência de execução) examina 17 de 18 stages** — `n_esperado=17` — e o
   excluído é o stage em `needs_review` que **constrói o payload que carrega a regressão
   desta rodada**. O check consertado para *"poder sair verde"* sai verde **ignorando
   exatamente o stage sob suspeita**.
3. **Teto de iterações de ferramenta é medido sobre população distinta do emissor:** o run
   registra **19** contra teto **6** — estourado **3,2×** sem alarme — porque as 19 são
   carimbos do backend e **zero** foram iniciadas pelo modelo. Emissor e teto contam coisas
   diferentes.

## O eixo, e por que a lane é de saúde-harness

O anti-vácuo do runbook exige `n_comparado` **e** `n_esperado`, e os três **publicam os
dois** — o guard funciona. O que ele não pega é **denominador tautológico**: população
grande, verdadeira, e incapaz de exibir a falha. `n_esperado` alto **parece** cobertura.

## Critério de aceite

1. Cada check declara, junto do par `n_comparado`/`n_esperado`, **quantos elementos da
   população poderiam exibir a falha**. Zero ⇒ `INAPLICÁVEL`, nunca ✅.
2. X4 mede **só** prosa autoral; com `n=1` o veredito é `INAPLICÁVEL`, e isso é resultado.
3. X5 fecha sobre **todos** os stages logados, ou nomeia a exclusão **no veredito** — não
   no denominador.
4. O teto de iterações compara a população que o emissor conta.
5. Controle positivo por check: mutação que **deve** reprovar, e reprova.
