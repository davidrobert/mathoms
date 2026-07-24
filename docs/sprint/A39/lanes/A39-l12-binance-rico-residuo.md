---
id: A39.l12
type: lane
title: "Resíduo não-coberto: verificar escalação honesta do Binance CSV + investigar extração de preview .xlsx (rico)"
sprint: A39
status: shipped
priority: P2
branch_slug: a39-l12-binance-rico-residuo
adrs: []
depends_on: ["[[A39.l1]]"]
tags:
  - type/lane
  - sprint/a39
  - status/shipped
  - priority/p2
  - area/pipeline
  - area/dados
---

# A39.l12 — `binance-rico-residuo` (achado PC-07 · resíduo)

## Problema (certificação 2026-07-23)

Sobra do `não-coberto` após [[A39.l8]] (Itaú fatura) e [[A39.l9]] (RV) fecharem 5
dos 6. O resíduo **não** é problema de classificação (prompt-engineer):

- **`binance_extratoconta .csv`** mapeia p/ `.other` **sem stage consumidor**
  (`maps_to_other_without_pipeline`) → mesmo classificado certo, vira
  `needs_review` corretamente. O que falta é um **parser/stage** consumidor
  (Binance), não um TypeRule. Escalação honesta é o comportamento **correto** hoje.
- **`rico_investimentosposicao .xlsx`** pode ter **lacuna de extração de preview**
  (se `_extract_file_preview` não lê xlsx, nem regex nem LLM-texto funcionam) —
  investigar antes de atribuir a classificação. (A cobertura de conteúdo da
  posição Rico é da [[A39.l9]]; aqui é só a via de preview/classificação.)

## Escopo

- **Verificar** (não necessariamente corrigir) que `classify_document` roteia o
  Binance CSV a **escalação honesta** com razão tipada (`doc_type_sem_pipeline`
  ou equivalente) — teste de contrato; se já correto, documentar e fechar.
- **Investigar** a extração de preview `.xlsx` (rico): se `_extract_file_preview`
  não lê xlsx, é lacuna de extração (afeta [[A39.l9]] também) — reportar e
  encaminhar.
- **Fora de escopo (nota explícita):** parser/stage consumidor de Binance →
  candidato a lane futura (data-engineer/senior-cto). Não inflar A39 com stage
  novo.

## Critério de aceite

- Harness [[A39.l1]]: Binance CSV → `escalado-honesto` (razão tipada), não
  `não-coberto` silencioso — KR-A satisfeito para o resíduo.
- Extração de preview `.xlsx` diagnosticada (lê ou não lê) — resultado
  documentado; se lacuna, encaminhada.
- Nota de escopo do Binance consumer stage registrada (não implementada aqui).

## Risco

Baixo — task de verificação + diagnóstico. O risco é escopo-creep (implementar
stage Binance); mitigado pela nota de fronteira explícita. P2 trailing.

## Nota de execução (2026-07-24) — lane FECHADA

**Binance CSV — verificado + endurecido.** `classify_document` já escalava o
Binance CSV real (`storage/…/binance_extratoconta_202602.csv`) honesto
(`needs_review=True`, não `não-coberto` silencioso), mas **sem razão tipada**: o
conteúdo (colunas de exchange cripto: `sent_currency`/`received_amount`/…) não
casa nenhum TypeRule → `best_type=None`, e o `doc_type_sem_pipeline` só dispara
com `best_type` setado. **Fix mínimo** (anti-silêncio, não domínio/ADR): a via
determinística agora emite `no_doc_type_match` quando nada casa —
`needs_review` sempre auto-descritivo. Teste de contrato sobre o CSV real-shape
(`test_binance_csv_content_escalates_with_typed_reason`).

**Rico `.xlsx` — hipótese REFUTADA.** A "lacuna de extração de preview" não
existe: `_extract_file_preview` lê o xlsx via openpyxl (1462 chars: "Este é o
seu patrimônio"/"Total investido"/tickers). O gap real era TypeRule + instituição
— **fechado pela [[A39.l9]]** (âncora de layout + fallback de instituição por
filename). Guard de regressão adicionado (`test_xlsx_preview_extraction_reads_cells`).

**Fora de escopo (registrado):** parser/stage consumidor de Binance (cripto) é
candidato a lane futura (data-engineer/senior-cto) — A39 não ganha stage novo.

Critério de aceite fechado: Binance → escalado-honesto com razão tipada;
extração `.xlsx` diagnosticada (lê) + documentada; fronteira do consumer Binance
registrada. Sem ADR (verificação + hardening anti-silêncio).
