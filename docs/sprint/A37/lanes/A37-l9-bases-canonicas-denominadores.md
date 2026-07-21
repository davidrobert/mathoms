---
id: A37.l9
type: lane
title: "Bases e denominadores canônicos: concentração imobiliária e exposição internacional"
sprint: A37
status: planned
priority: P2
branch_slug: a37-l9-bases-canonicas-denominadores
adrs: ["[[ADR-340]]"]
depends_on: ["[[A37.l1]]"]
tags:
  - type/lane
  - sprint/a37
  - status/planned
  - priority/p2
  - area/domain
  - area/pipeline
---

# A37.l9 — `bases-canonicas-denominadores` (FIN-07+CTO-09 · CTO-04+PE-05)

> **Decisões de domínio já colhidas** (revisão do sprint por `financial-planner`,
> 2026-07-20) — ver Escopo. Co-design remanescente: só a investigação do gap
> tabela×patrimônio.

## Problema (evidência verificada 2026-07-20 @ c61c1c29)

1. **Três "concentrações imobiliárias" (FIN-07/CTO-09):**
   `ratios.concentracao_imobiliaria` ≈60% (base carteira produtiva, SSOT
   [[ADR-340]] — a que o parecer usa, correto pós-R3.1);
   `investimentos.tabela_classes` ≈63% (base `investimentos.total`, que mistura
   imóveis físicos com ativos financeiros); doughnut ≈67% (base patrimônio
   bruto, `generate_narratives.py:392`). Cada número está certo na sua base; o
   leitor vê três valores para "concentração em imóveis" sem rótulo de base.
2. **Gap real entre superfícies de investimentos:** comparações congruentes
   entre `patrimonio.investimentos_titular+conjuge` e a parcela financeira da
   `tabela_classes` divergem em ~R$ 100–130k (verificado com caixa↔caixa
   alinhado) — investigar o produtor da tabela (inclusão/exclusão de classes)
   e fechar a ponte, ou documentar a diferença com rótulo.
3. **Exposição internacional (CTO-04/PE-05):** o parecer rotula "1,53% da
   carteira financeira", mas 1,53% é a classe Internacional sobre a carteira
   **produtiva** (inclui imóveis); sobre a financeira seria ~3,6%; e
   `exposicao_cambial.pct_investivel_financeiro` (2,16%) é um terceiro
   conceito (caixa em moeda estrangeira). `exposicao_cambial` não está no
   manifest do parecer.

## Escopo

- Concentração: manter a base da [[ADR-340]] (carteira produtiva) — **não
  reabrir**; rotular as demais superfícies ("% do total investido" na
  `tabela_classes`; "% do patrimônio bruto" no doughnut); separar ou rotular
  imóveis físicos na `tabela_classes`.
- **Pesos de classe de alocação** (internacional, RF, RV, FII) medem-se sobre
  `investivel_financeiro` (rótulo "carteira financeira") — nunca sobre base que
  inclui imóvel físico (subestima toda classe financeira sistematicamente).
- **Internacional ≠ cambial** — dois conceitos, dois números: alocação
  internacional (ativos internacionais ÷ investível financeiro) vs exposição
  cambial (posições em moeda estrangeira, `pct_investivel_financeiro`).
  Numerador E denominador diferem; não fundir num denominador único.
- Investigar e fechar o gap de ~R$ 100–130k (ou rotular a diferença).
- Padronizar "exposição internacional": termo + denominador; projetar
  `exposicao_cambial` no manifest do parecer em bump **próprio, sequenciado
  depois** da [[A37.l1]] (nunca commit cruzado entre lanes).
- Scalars do manifest ganham rótulo de base onde ambíguo (ex.: "efetiva
  (blended)" para alíquota — cobre o resíduo de PE-06/CTO-05).

## Critério de aceite

- Cada métrica de concentração/exposição renderizada declara sua base no
  rótulo (unit de template + snapshot).
- Parecer de run fresco não usa "carteira financeira" para número calculado
  sobre outra base (checagem no eval golden).
- Gap tabela×patrimônio: fechado (diferença = 0 documentada por construção) ou
  rotulado com decomposição explícita.

## Risco

Médio: mexe em rótulos consumidos por golden/snapshot (atualizar juntos);
dependência leve da [[A37.l1]] para o manifest — sequenciar depois dela.
