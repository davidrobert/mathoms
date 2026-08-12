---
id: A40.l55
type: lane
title: "Medida de linha no papel: prosa a 100–110 caracteres por linha no A4"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P3
branch_slug: a40-l55-medida-de-linha-no-papel
adrs:
  - "[[ADR-381]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p3
  - area/frontend
  - area/report
---

# A40.l55 — `medida-de-linha-no-papel`

> **Aberta em 2026-08-12**, no fecho da [[A40.l45]] (decisão do dono: os
> follow-ups sem dono viram lanes na A40). A l45 dizia "transferido, sem dono" —
> exatamente o estado que evapora; agora tem lane.

## Problema

Com a caixa A4 de 703px e corpo em 10pt (`report-print.css`), a prosa do PDF —
`SectionSummary`, notas, parecer — sai com **100–110 caracteres por linha**. O
confortável tipográfico é 45–75; o teto usável, ~90. É defeito de
**legibilidade**, não de perda de dado: o PDF de hoje é legível e cansativo, no
artefato que o cliente arquiva e relê.

Origem: parecer do `product-designer` no co-design da [[A40.l45]] (2026-08-11).

## Escopo

Fix candidato do parecer, deliberadamente pequeno: `p, li { max-width: 90ch }`
em `@media print` — **não** duas colunas (o ganho de páginas não paga o risco de
clipping em conteúdo arbitrário, [[ADR-381]] §Alternativas), **não** mexer na
margem física do `pdf_renderer.py` (decisão de página, fonte única).

## Critério de aceite

- [ ] Medir caracteres-por-linha médio da prosa no PDF real (via `pdftotext`)
      antes/depois: mediana ≤ 90 nas seções de prosa.
- [ ] Nenhuma tabela ou grade afetada pela regra (escopo `p, li` apenas) —
      inventário de vazamento da [[A40.l45]] (`overflow-horizontal.@critical`)
      continua verde.
- [ ] PNGs do PDF inspecionados antes de qualquer rebaseline de print.
