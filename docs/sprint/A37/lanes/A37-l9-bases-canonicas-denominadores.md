---
id: A37.l9
type: lane
title: "Bases e denominadores canônicos: concentração imobiliária e exposição internacional"
sprint: A37
status: planned
priority: P2
branch_slug: a37-l9-bases-canonicas-denominadores
adrs: ["[[ADR-340]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a37
  - status/planned
  - priority/p2
  - area/dominio
  - area/pipeline
---

# A37.l9 — `bases-canonicas-denominadores` (FIN-07+CTO-09 · CTO-04+PE-05)

> **Co-design `financial-planner` (1 rodada) antes de codar** — a decisão é
> qual base é canônica por métrica e como rotular as demais.

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

- Decidir com `financial-planner`: base canônica de "concentração imobiliária"
  (manter ADR-340) e rótulos das demais ("% do total investido", "% do
  patrimônio bruto"); separar ou rotular imóveis físicos na `tabela_classes`.
- Investigar e fechar o gap de ~R$ 100–130k (ou rotular a diferença).
- Padronizar "exposição internacional": termo + denominador; projetar
  `exposicao_cambial` no manifest do parecer **via [[A37.l1]]** (mesmo bump).
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
