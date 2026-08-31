---
id: A40.l109
type: lane
title: "A lista do card lê o artefato mais recente sob um relatório pinado e imutável"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l109-lista-le-latest-sob-relatorio-pinado
owner: data-engineer
depends_on: []
adrs:
  - "[[ADR-347]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/backend
  - area/frontend
---

# A40.l109 — `lista-le-latest-sob-relatorio-pinado`

> **Origem:** co-design do item 2 da [[A40.l102]] (2026-08-30, `financial-planner` +
> `data-engineer` + `senior-cto`). O achado é do `data-engineer`; **verificado de forma
> independente** antes de abrir esta lane. Não é da l102 (que trata de *declaração*, e
> isto sobrevive a qualquer declaração) nem da [[A40.l98]] (cujo eixo é o *filtro*).

## O defeito

O card Consumo Consciente mistura, na mesma tela, dois artefatos de runs potencialmente
**diferentes**:

| peça | fonte | pinagem |
| --- | --- | --- |
| KPI + declaração de base | `report.analysis_artifact` (`backend/app/application/report/get_report_data.py:49`) | **pinado** ao run do relatório, via FK `reports.analysis_artifact_id` |
| tabela de pontuais | `read_latest_artifact(...)` (`backend/app/services/transaction_service.py:63,66`) | **o mais recente do workspace no instante do request** |

E o endpoint não tem como ser pinado — `GET /workspaces/{ws}/reports/consumo-pontuais`
(`backend/app/api/reports.py:82-87`) recebe `period`, `anchor_date`, `workspace`, `db`, e
**nenhum `report_id` ou `run_id`**; a `ConsumoPontuaisResponse` também não devolve
nenhum.

**Consequência:** abrir `/reports/<id_antigo>` depois de um run novo mostra o KPI do run N
com a lista do run N+1, sem nada no wire que permita ao leitor, ao teste ou ao agente
notar. O PDF carrega os dois lado a lado.

Isso lê **em volta** da imutabilidade que a [[ADR-347]] e o `ReportPublication` pinado com
`RESTRICT` existem para garantir: o relatório publicado é imutável, e esta lista não é.

## Por que P1 e não P0

Nenhum número **determinístico publicado** se move sozinho — é preciso um run novo entre a
publicação e a leitura. Mas o dano é silencioso, atinge relatório já entregue ao cliente, e
o discriminador já está no payload: `_report_lineage.pipeline_run_id`. A comparação está a
um campo de distância e não é feita.

## Escopo

1. `ConsumoPontuaisResponse` carrega o `pipeline_run_id` do artefato E4 efetivamente lido.
2. O card não renderiza a lista quando esse id diverge de `_report_lineage.pipeline_run_id`
   — degradação declarada, nunca silenciosa.
3. Decidir o contrato de leitura: **rota de relatório pode ler `latest`?** Vale para as
   outras rotas que o façam, não só esta. Merece **ADR `Proposto` antes do PR de
   implementação** (P1 com escopo de contrato de API, política do CLAUDE.md). Não reserve
   id de ADR em prosa — aloque na escrita.

## Fora de escopo

A divergência de **população** entre lista e KPI (a lista inclui `nao_identificado`, o KPI
não) é da [[A40.l102]] item 2 — é sobre *declaração*, e persiste mesmo com os dois lados
lendo o mesmo run.

## Critério de aceite

- Teste com **dois** runs E4 no mesmo workspace e um relatório pinado no primeiro: a lista
  recusa render (ou declara a divergência). Sem o segundo run o teste é vácuo.
- O `run_id` aparece na resposta e é o do artefato lido, não o do relatório — provar com
  fixture em que os dois diferem.
