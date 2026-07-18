---
id: ADR-326
type: adr
title: "Colunas denormalizadas reports.score/patrimonio_liquido populadas a partir do artefato E5 (0–10, backfill)"
status: Proposto
date: "2026-07-12"
relates_to:
  - "[[ADR-283]]"
  - "[[ADR-090]]"
tags:
  - type/adr
  - status/proposto
  - area/backend
  - area/data
---

# ADR-326 — População de `reports.score`/`reports.patrimonio_liquido` a partir do E5

> Item **C7** do plano PLAN-dogfood-report-fix. Achados DE-06/ARCH-04 da revisão dogfood 2026-07-11.

## Contexto

`reports.score` e `reports.patrimonio_liquido` são **NULL em 100%** dos relatórios
(59/59 no workspace dogfood). O write-path que cria o `Report`
(`backend/app/tasks/pipeline_task.py::_create_report_from_output`, ~L435) nunca
seta as duas colunas. Porém há **consumidor vivo** que as lê:
`backend/app/services/goal_service.py::get_latest_report_patrimonio_liquido`
filtra `patrimonio_liquido.isnot(None)` — ou seja, o cálculo da meta de IF que
depende do patrimônio atual **lê uma coluna que nunca é escrita** e cai no
fallback silenciosamente. O comentário do modelo (`backend/app/models/report.py`)
ainda descreve `score` como "índice 0–100", mas o `score.valor` real do E5 é
escala **0–10** (ex.: 6,3).

A coluna foi criada por [[ADR-283]] (denormalização para consulta barata); esta
ADR honra o **contrato de população** que ficou pendente.

## Decisão

1. **Popular na criação** — em `_create_report_from_output`, derivar de
   `analysis_content` (já disponível no escopo): `reports.score = score.valor`
   (escala 0–10) e `reports.patrimonio_liquido = Decimal(str(patrimonio.liquido))`
   (`Numeric(18,2)`, dinheiro nunca é `float` — [[ADR-090]]).
2. **Backfill retroativo** — novo modo `--backfill-columns` em
   `backend/app/scripts/backfill_reports_from_artifacts.py` que faz `UPDATE` das
   linhas existentes com coluna NULL, mapeando via `analysis_artifact_id`.
3. **Corrigir a semântica** — comentário do modelo `0–100` → `0–10`.

Escala e mapeamento exatos ficam travados aqui: `score.valor → reports.score`,
`patrimonio.liquido → reports.patrimonio_liquido`.

## Alternativas consideradas

- **(B) Dropar as colunas e reapontar `goal_service` ao artefato E5.** Rejeitada:
  a denormalização é barata, há mais de um leitor potencial, e uma projeção
  populada é mais simples que reescrever o consumidor para desserializar o
  artefato a cada leitura de meta.

## Consequências

- `goal_service` volta a enxergar o patrimônio real → progresso de IF correto em
  3 telas + `/goals/if`.
- Backfill é one-shot; após ele, invariante `COUNT(*) WHERE patrimonio_liquido IS NULL = 0`.
- Enforço de tipo: `report.patrimonio_liquido == Decimal(str(patrimonio.liquido))`
  (teste), sem `float`.

## Critério de aceite (4 lentes)

- **Completude:** ambos construtores (`pipeline_task.py` + `backfill._build_report`)
  populam; backfill cobre os 59 legados; os 4 consumidores enumerados em teste.
- **Corretude:** `report.score == 6,3` (0–10), `patrimonio_liquido` == `Decimal(18,2)` exato.
- **Consistência:** coluna == view-model E5 do mesmo `Report`.
- **Precisão:** `SELECT COUNT(*) ... WHERE patrimonio_liquido IS NULL = 0` pós-backfill; comentário corrigido.
