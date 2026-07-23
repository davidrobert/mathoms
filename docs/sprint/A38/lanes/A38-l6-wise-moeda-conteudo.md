---
id: A38.l6
type: lane
title: "Wise: moeda decidida por filename (USD vira BRL sem LLM) + período range por extenso"
sprint: A38
status: shipped
ship_date: "2026-07-23"
ship_pr: 1022
priority: P1
branch_slug: a38-l6-wise-moeda-conteudo
adrs: []
depends_on: []
tags:
  - type/lane
  - sprint/a38
  - status/shipped
  - priority/p1
  - area/pipeline
  - area/dados
---

# A38.l6 — `wise-moeda-conteudo` (achados #6 + #10b)

> **Primeiro P1 da W1 (decisão do painel/financial):** o erro USD→BRL é
> invisível ao gate de conservação da [[A38.l3]] (a conservação fecha na
> unidade errada; Wise deriva `saldo_inicial`, então o gate é no-op) e infla
> dolarização/patrimônio numa direção que **lisonjeia** o usuário — gera
> recomendação de alocação ativamente errada. Não sequenciar atrás de
> [[A38.l4]]/[[A38.l5]].

## Problema (evidência verificada 2026-07-22)

1. **Moeda por filename:** `scripts/e2/banks/wise.py::parse_wise` decide a
   moeda por `"usd" in filename.lower()`. A TypeRule genérica `extratoconta`
   (a que casa o extrato Wise por regex) **não emite subtipo de moeda**, então
   o nome canônico sai `wise_extratoconta_<período>` e o extrato **USD é
   parseado como BRL**. Corrupção direta de câmbio, fluxo e patrimônio
   (valores USD somados 1:1 em BRL). Hoje a correção depende do LLM fallback
   (conf 0.7 < 0.8) acertar o subtipo no `final_name` — correção por sorte,
   não por contrato.
2. **Período:** `period_extractor` devolve `2025` para o range por extenso
   "22 de julho de 2025 … 22 de julho de 2026" — o nome canônico dos dois
   extratos Wise (USD e BRL) colide no período, alimentando o falso-positivo
   de fuzzy-dupe ([[A38.l11]]).

## Escopo

- **Parser**: `parse_wise` detecta a moeda pelo **conteúdo** ("Extrato em
  USD" / "Extrato em BRL", presente na 1ª página) com filename como mero
  fallback; `moeda`/`tipo` do resultado refletem o conteúdo. **Moeda
  indeterminada escala** (contrato [[A38.l3]]) — nunca default BRL
  silencioso.
- **TypeRule determinística**: nova regra (priority < genérica) para
  "Extrato em USD/BRL" estilo Wise emitindo `extratocontausd`/
  `extratocontabrl` — os anchors de roteamento E2 são subtipo-agnósticos
  (`^wise_extratoconta` casa ambos), zero mudança no registry.
- **`period_extractor`**: range de datas por extenso →
  `YYYYMM_YYYYMM` (ex.: `202507_202607`).
- Testes de regressão antes do fix (fixture sintética de extrato Wise USD e
  BRL, com datas por extenso).

## Critério de aceite

- Corpus local (harness [[A38.l1]]): extrato Wise USD → `moeda=USD`,
  `tipo=extratocontausd`, período `202507_202607` **sem LLM** (KR-B/KR-D);
  BRL idem com `brl`.
- `n_tx` dos dois docs ≥ baseline (17/7); continuidade da coluna de saldo do
  extrato USD auditada (as 2 quebras observadas na certificação explicadas —
  header de página vs transação real).
- Fixtures Wise existentes verdes (KR-E).

## Risco

Baixo-médio: TypeRule nova precisa não roubar extratos globais de outros
bancos (`extratocontaglobalusd` etc. têm priority 25 — validar ordem com o
corpus de classification).
