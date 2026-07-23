---
id: A38.l7
type: lane
title: "Fatura Santander Unique layout 2026: classificação conf 0.0 + parser sem total/vencimento"
sprint: A38
status: open
priority: P1
branch_slug: a38-l7-faturaunique-layout-2026
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a38
  - status/open
  - priority/p1
  - area/backend
  - area/pipeline
---

# A38.l7 — `faturaunique-layout-2026` (achado #7)

## Problema (evidência verificada 2026-07-22)

O layout 2026 da fatura do cartão Santander Unique identifica o produto como
"UNIQUE MASTERCARD" — a string "SANTANDER UNIQUE" **nunca aparece adjacente**
(entre elas ficam nome do titular e nº do cartão). A TypeRule `faturaunique`
exige exatamente essa adjacência → **conf 0.0** nos 3 exemplares do corpus
(a `faturasantander` também falha: o texto não contém "BANCO SANTANDER"; e a
genérica falha pelo gap sem DOTALL — [[A38.l10]]). Forçando o nome canônico,
`scripts/e2/banks/santander.py::parse_santander_unique` extrai as 9 transações
mas **`total_fatura=None` e `vencimento=None`** — os regexes de total e
vencimento são do layout antigo, e sem total o `validate_fatura_result` não
tem como cross-checar Σtx.

## Escopo

- **TypeRule**: aceitar o layout 2026 — required composto tipo
  `UNIQUE\s+MASTERCARD` + contexto santander (ex.: "fatura do seu cartão
  SANTANDER"), preservando o required atual como alternativa (layout antigo e
  CSV continuam casando).
- **Parser**: extrair `total_fatura` ("Total a Pagar" + valor na vizinhança) e
  `vencimento` (data ao lado) do layout 2026; manter os regexes antigos como
  alternativa.
- Ativar o cross-check existente do `validate_fatura_result` (Σ lançamentos ×
  total) para o layout novo — alinhar semântica (total inclui saldo
  anterior/pagamentos? documentar no teste com fixture).
- Fixture sintética PII-zero do layout 2026 + teste de regressão antes do fix.
- **Sequência obrigatória (decisão do painel/financial):** TypeRule e
  total/vencimento+cross-check saem **no mesmo PR** — shippar só a
  classificação rotearia fatura de parse parcial para o relatório com cara
  certificada, recriando o erro silencioso que o sprint mata. O total é o
  análogo do gate anti-silêncio no cartão ([[A38.l3]] cobre fatura no
  contrato).

## Critério de aceite

- Corpus local (harness [[A38.l1]]): 3 faturas Unique classificam
  `faturaunique` determinístico (conf ≥ 0.85) e parseiam com `total_fatura` e
  `vencimento` preenchidos + cross-check de soma ativo (KR-B).
- Fixtures Santander existentes (fatura CSV, extrato XLS/PDF) verdes (KR-E).

## Risco

Baixo-médio: required novo não pode casar fatura de outro banco que mencione
Mastercard — co-ocorrência com marcador santander é obrigatória no pattern.
