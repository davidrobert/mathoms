---
id: A38.l2
type: lane
title: "parse_itau perde ~50% das transações do layout 2026 do extrato PDF"
sprint: A38
status: open
priority: P0
branch_slug: a38-l2-parse-itau-layout-2026
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a38
  - status/open
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
  (`data lançamentos valor (R$) saldo (R$)`) e despachar para estratégia nova;
  o caminho `extract_tables()` atual **permanece** para os layouts que ele já
  atende (Personnalité e demais fixtures existentes). Dispatch, não
  substituição.
- **Estratégia nova por linhas de texto**: parse de `extract_text()` linha a
  linha (`dd/mm/yyyy descrição valor [saldo]`), tratando `SALDO DO DIA` como
  âncora de saldo (não transação) e descontinuidades de página.
- **Fixture sintética PII-zero** reproduzindo o layout 2026 (multi-página,
  com linhas `SALDO DO DIA`, aplicação automática com "CDB" na descrição,
  débitos e créditos) + **teste de regressão antes do fix**.
- **Conservação como invariante do teste**: no fixture, Σtx entre duas âncoras
  `SALDO DO DIA` consecutivas == Δsaldo (cents, tolerância zero); e a global
  `saldo_inicial + Σtx == saldo_final`. Validar/ajustar a semântica atual de
  `saldo_inicial` (primeiro `SALDO DO DIA`) para que a invariante feche.

## Critério de aceite

- Fixture sintética do layout 2026: **100% das linhas** extraídas + as duas
  conservações acima verdes.
- Corpus local (harness [[A38.l1]]): **74/74, 65/65, 23/23** e conservação
  zero nas 3 amostras (KR-A).
- Fixtures existentes do `parse_itau` (layout antigo) **byte-idênticas** no
  output; `n_tx ≥ baseline` em todos os docs Itaú do corpus (KR-E).
- Rotina de roteamento intocada (`^itau_extratoconta` continua casando).

## Risco

Médio-alto (parser de maior volume do produto). Mitigação: dispatch aditivo,
fixture do layout antigo intocada, gate manual do harness antes do merge.
