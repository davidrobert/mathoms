---
id: A38.l9
type: lane
title: "Fatura Itaú Visa/Itaucard sem parser determinístico (100% E2-llm; 1 PDF com texto sem espaços)"
sprint: A38
status: open
priority: P2
branch_slug: a38-l9-fatura-itau-visa-parser
adrs: []
depends_on: []
parallel_with: ["[[A38.l10]]"]
tags:
  - type/lane
  - sprint/a38
  - status/open
  - priority/p2
  - area/pipeline
  - area/dados
---

# A38.l9 — `fatura-itau-visa-parser` (achado #8)

## Problema (evidência verificada 2026-07-22)

Não existe parser determinístico para fatura de cartão Itaú Visa/Itaucard —
o registry Itaú só cobre `faturapaoacucar`. Os 3 exemplares do corpus vão
100% para o E2-llm (custo/latência de tier premium + precisão não garantida
para dezenas de linhas). Agravante: 1 dos 3 PDFs tem camada de texto **sem
espaços** ("Totaldestafatura", "ResumodafaturaemR$") — `extract_text()` cru é
inutilizável nele; `extract_words()` com coordenadas de layout preserva a
separação.

## Escopo

- `parse_itau_fatura` em `scripts/e2/banks/itau.py` + anchor
  `itau_fatura(?!paoacucar)` no `PARSERS` (padrão do registry: anchor
  subtipo-agnóstico).
- Extração via `extract_words()`/layout (robusta ao sub-layout sem espaços):
  transações nacionais e internacionais, `total_fatura`, `vencimento`,
  pagamento anterior.
- Fixtures sintéticas PII-zero dos **2 sub-layouts** (com e sem espaços) +
  teste de regressão antes do fix; cross-check Σtx × total no
  `validate_fatura_result`.
- Se o sub-layout sem espaços se provar inviável deterministicamente, aceite
  alternativo explícito (decisão do painel/pm): esse sub-layout permanece no
  E2-llm **amarrado ao cross-check** — LLM extrai **e** Σ×total confere,
  senão `needs_review` ([[A38.l3]]). Nunca confiar no LLM cru sem checksum.

## Critério de aceite

- Corpus local (harness [[A38.l1]]): 3 faturas Itaú com `n_tx > 0`,
  `total_fatura`/`vencimento` preenchidos e cross-check verde — pelo caminho
  determinístico (ou fallback documentado para o sub-layout sem espaços).
- Zero regressão em `faturapaoacucar` (fixtures existentes) (KR-E).
- Classificação determinística fica a cargo da [[A38.l10]] (paralela); esta
  lane garante o parse dado o nome canônico `itau_fatura_*`.

## Risco

Médio: layout de fatura é o mais denso; mitigação via fixtures dos 2
sub-layouts e cross-check de total obrigatório.
