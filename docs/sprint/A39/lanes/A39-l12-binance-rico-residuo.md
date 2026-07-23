---
id: A39.l12
type: lane
title: "Resíduo não-coberto: verificar escalação honesta do Binance CSV + investigar extração de preview .xlsx (rico)"
sprint: A39
status: planned
priority: P2
branch_slug: a39-l12-binance-rico-residuo
adrs: []
depends_on: ["[[A39.l1]]"]
tags:
  - type/lane
  - sprint/a39
  - status/planned
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
