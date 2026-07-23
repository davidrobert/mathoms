---
id: A38.l2
type: lane
title: "parse_itau perde ~50% das transações do layout 2026 do extrato PDF"
sprint: A38
status: shipped
ship_date: "2026-07-23"
ship_pr: 1020
priority: P0
branch_slug: a38-l2-parse-itau-layout-2026
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a38
  - status/shipped
  - priority/p0
  - area/pipeline
  - area/dados
---

# A38.l2 — `parse-itau-layout-2026` (achado #1 — o P0 do sprint)

## Problema (evidência verificada 2026-07-22)

`scripts/e2/banks/itau.py::parse_itau` extrai transações via
`page.extract_tables()` do pdfplumber. No layout 2026 do extrato PDF de conta
corrente ("extrato conta / lançamentos", cabeçalho
`data lançamentos valor (R$) saldo (R$)`), a detecção de tabela **fragmenta as
linhas**: por página, o texto tem 19–27 linhas de transação, mas as tabelas
entregam só 9–14 linhas datadas. Medição nas 3 amostras do corpus local:
**34/74, 32/65 e 12/23** linhas capturadas; conservação
`saldo_inicial + Σtx == saldo_final` falha por ordem de ≥R$10k. As linhas
perdidas incluem **receitas recorrentes (SISPAG, REND PAGO APLIC)** e
pagamentos de fatura — fluxo e relatório saem errados **sem nenhum aviso**
(o gate anti-silêncio é a [[A38.l3]]; esta lane corrige a extração).

## Escopo

- **Detecção de layout**: identificar o layout 2026 pelo cabeçalho de colunas
  (`data lançamentos valor (R$) saldo (R$)`), **normalizado** (lowercase +
  whitespace colapsado + sem acento) antes do match, e despachar para
  estratégia nova; o caminho `extract_tables()` atual **permanece** para os
  layouts que ele já atende (Personnalité e demais fixtures existentes).
  Dispatch, não substituição — o header do layout **antigo** entra como caso
  negativo na fixture (mudança de header não roteia old→new em silêncio).
- **Estratégia nova por linhas de texto**: parse de `extract_text()` linha a
  linha (`dd/mm/yyyy descrição valor [saldo]`), tratando `SALDO DO DIA`/
  `SALDO ANTERIOR` como **âncora de saldo, nunca transação** (assert de
  fixture — trap nº1), descontinuidades de página, e **BRL-only** (linha
  forex/USD não é capturada como tx).
- **Fixture sintética PII-zero** reproduzindo o layout 2026 (multi-página,
  com linhas `SALDO DO DIA`, aplicação automática com "CDB" na descrição,
  débitos e créditos, e um dia com múltiplas tx entre duas âncoras) +
  **teste de regressão antes do fix**.
- **Conservação como invariante do teste**: no fixture, Σtx entre duas âncoras
  `SALDO DO DIA` consecutivas == Δsaldo (cents, tolerância zero); e a global
  `saldo_inicial + Σtx == saldo_final`. **Confirmar a semântica do primeiro
  `SALDO DO DIA`** (antes ou depois da 1ª tx do dia) — off-by-one aqui produz
  Δ igual à 1ª tx, o falso-break clássico. Per-dia é assert de fixture;
  produção gateia só a global ([[A38.l3]]).
- **Classificação das linhas recuperadas (decisão do painel/financial):**
  entre os ~50% recuperados há transferências internas (`PAGTO FATURA
  ITAUCARD`, `APLICACAO CDB`) e rendimento de aplicação (`REND PAGO APLIC`) —
  não podem ser somadas cegas como despesa/receita. O aceite valida que o
  fluxo downstream (netting de `transferencias_internas`, categorização E4)
  as trata: medir taxa de poupança e renda passiva pré/pós no corpus — o fix
  de completude não pode distorcer os números para o outro lado.

## Critério de aceite

- Fixture sintética do layout 2026: **100% das linhas** extraídas + as duas
  conservações acima verdes.
- Corpus local (harness [[A38.l1]]): **74/74, 65/65, 23/23** e conservação
  zero nas 3 amostras (KR-A).
- Fixtures existentes do `parse_itau` (layout antigo) **byte-idênticas** no
  output — golden commitado do output da fixture antiga com diff assertado,
  não "eyeball"; `n_tx ≥ baseline` em todos os docs Itaú do corpus (KR-E).
- Rotina de roteamento intocada (`^itau_extratoconta` continua casando).

## Risco

Médio-alto (parser de maior volume do produto). Mitigação: dispatch aditivo,
fixture do layout antigo intocada, gate manual do harness antes do merge.
