---
id: A38.l15
type: lane
title: "parse_c6bank não extrai o layout C6 Global (USD/EUR internacional): 0 tx com 56–199 linhas"
sprint: A38
status: planned
priority: P1
branch_slug: a38-l15-c6-global-parser
adrs: []
depends_on: ["[[A38.l14]]"]
tags:
  - type/lane
  - sprint/a38
  - status/planned
  - priority/p1
  - area/pipeline
  - area/dados
---

# A38.l15 — `c6-global-parser` (certificação do workspace 5@5.com, 2026-07-23)

## Problema (certificação empírica 2026-07-23)

`parse_c6bank` só entende o layout **BRL** (`extratoconta` — funciona: 553 tx,
80 tx). Os ~10 extratos de **conta internacional C6 Global (USD/EUR)** do
dono retornam **0 transações** apesar de terem **56–199 linhas datadas reais**
cada. O subtipo já classifica certo (`extratocontaglobalusd`/`eur` conf 1.0) e
roteia — falta a **extração** do layout internacional.

Sequenciada **após** a [[A38.l14]]: aquele PR já transforma esses docs de
perda-silenciosa em **escalação honesta** (E2-llm/needs_review); esta lane
faz a escalação virar **dado determinístico real** (o sleeve internacional
volta ao patrimônio no Free tier, sem custo de LLM).

## Escopo (decisões do painel encodadas)

- Extração line-based do layout C6 Global USD/EUR em `parse_c6bank`
  (`scripts/e2/banks/c6bank.py`), adaptada às linhas em US$/€ — mesmo padrão
  do BRL. Reporta `raw_rows_detected` (contrato da [[A38.l14]]).
- **Landmine de locale (financial-planner — mede antes de codar):** o parse
  de saldo em `c6bank.py:523` faz
  `.replace(".","").replace(",",".")` (convenção **BR**). Se o layout Global
  usa formato **US** (`1,234.56`), esse replace **inverte o valor (~100×)** —
  mesma classe do bug Wise, por locale. **Confirmar a convenção decimal do
  layout Global e detectar por subtipo.** Gate anti-locale: **conservação em
  moeda original** (`saldo_ini + Σtx == saldo_fim` em cents de USD/EUR,
  tolerância zero) — caso negativo escala.
- **Moeda original + câmbio downstream** (guard-contra-Wise): emitir
  transações e saldo na moeda original (USD/EUR); `moeda` carimbada no result
  **e** na tx/saldo; conversão para BRL é downstream via `market_rates`
  (tipo `moeda_estrangeira` no E3), no rate da **data de fechamento do
  período** (consistente com a valoração IRPF).
- **Meses vazios não zeram o extrato** (invariante saldo≠fluxo da l14): mês
  sem movimento = fluxo 0 naquele mês, saldo carrega; conta inteira sem
  movimento = dormente com `saldo_final` preservado.
- Fixture sintética PII-zero multi-mês (meses vazios + meses com movimento),
  USD e EUR.

## Critério de aceite

- Fixture C6 Global (USD e EUR): 100% das linhas de transação extraídas;
  conservação em **moeda original** fecha em cents (gate anti-locale); caso
  de locale invertido **escala**.
- Corpus local (harness [[A38.l1]]): os ~10 C6 Global saem de escalação
  (pós-l14) para extração completa; `moeda` = USD/EUR (nunca BRL — KR-D).
- Re-certificação do workspace: os C6 Global contribuem saldo real ao bucket
  "Caixa + Moeda Estrangeira", card de exposição cambial e ao "atual" da meta
  de dolarização (que deixa de ler ~0%).
- Regressão zero: layout BRL do C6 (`extratoconta`) byte-idêntico (golden);
  demais parsers intocados (KR-E).

## Fora de escopo (follow-up)

- **Dupla contagem baseline↔extrato (financial-planner):** IRPF 31/12
  (`bens_direitos`) e o extrato C6 Global carregam o mesmo ativo internacional.
  **Verificar primeiro** se o branch `has_current_positions`
  (`patrimonio_calculator.py:418`)
  já supersede o snapshot IRPF da mesma conta (instituição+conta+moeda) quando
  há extrato E3 — se sim, é assertion de aceite; se o caixa FX do baseline
  entra por campo distinto, é dedup explícito (candidata a lane própria, não
  abrir ADR sem confirmar).
- Conservação WARN mista bradesco/c6bank BRL (gap≥10k em alguns extratos) —
  deep-dive por banco (over/under-count vs semântica de saldo).
- CDB c6bank/bradesco/btg em PDF (fora do escopo [[A38.l12]]) — permanecem
  E2-llm por ora.

## Risco

Médio: toca o parser de maior volume do workspace (41 docs C6). Mitigação:
golden do layout BRL intocado, conservação em moeda original como gate
empírico, e a [[A38.l14]] já garante que qualquer falha residual **escala**
em vez de sumir.
