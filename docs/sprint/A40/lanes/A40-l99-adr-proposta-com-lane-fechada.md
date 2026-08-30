---
id: A40.l99
type: lane
title: "Cinco ADRs em Proposto com lane fechada declaram decisão que não está em vigor"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l99-adr-proposta-com-lane-fechada
owner: senior-cto
depends_on: []
adrs:
  - "[[ADR-362]]"
  - "[[ADR-363]]"
  - "[[ADR-385]]"
  - "[[ADR-389]]"
  - "[[ADR-419]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/dominio
---

# A40.l99 — `adr-proposta-com-lane-fechada`

> **Origem:** closeout da [[A40.l94]] (2026-08-30). Ao decidir se a [[ADR-422]] devia flipar
> para `Decidido`, contei a classe em vez de tratar o caso: **11** ADRs de `phase: A40` estão
> em `Proposto`, e **6** têm todas as lanes citantes terminais.

## A premissa que caiu

A proxy óbvia — *"lane `shipped` ⇒ ADR em vigor, é só flipar"* — foi verificada ADR a ADR,
decisão a decisão, contra o código. **Ela é falsa em 5 dos 6 casos.** Uma lane pode shippar
parte da ADR, ou tê-la deferido, e o status `Proposto` estava certo por acidente.

Só a [[ADR-368]] passou e foi flipada no closeout da l94 (snapshot com `parametros_geradores`
versionado, conjunto de inancoráveis, 18 testes determinísticos in-process).

## As cinco, com a decisão que falta

| ADR | Decisão não implementada (medida) |
| --- | --- |
| [[ADR-362]] | **D2 é normativa** — *"qualquer superfície que exiba a revisão exibe também esta ressalva"*. A ressalva existe em **um** sítio (`dev/run_provenance.py`). O colofão do relatório (`ReportSourceStrip.tsx`) e o `/health` exibem a revisão **nua**. E a Emenda 2026-08-06 item 3 diz que o escalar fica `None` sob cobertura parcial; medido, ele devolve a revisão conhecida (`revs[0] if len(revs) == 1`), colapsando só em execução mista |
| [[ADR-363]] | §3(b) `service.version` + `deployment.environment` no Resource do OTel: `otel.py` cria o Resource só com `SERVICE_NAME`. Os dois §Deferido (dono: owner) — `${MATHOMS_BUILD_SHA:?}` no compose de prod e label OCI por revisão — não implementados; o segundo **não é implementável** com a tag mutável atual |
| [[ADR-385]] | D7 diz *"o canonical recomputado não é persistido"* — `dev/dedup_property_identity.py` **grava** sob `--apply`. D5 exige gate anti-truncagem que **não existe**: nada falharia se `descricao_sample` deixasse de ser `Text` |
| [[ADR-389]] | D2 §consumidores: `compute_irrf_mensal` segue lendo `IRRF_TABELA_MENSAL` hardcoded em vez de `ir_brackets_mensal`. D2 diz *"`ir_brackets` morre"* — a coluna segue viva e nullable (contract deferido). D3 exige teste marcado `migration` validando as rows do DB; não existe |
| [[ADR-419]] | D4 §fecho: *"O invariante lê o **artefato E5**, nunca o snapshot do view-model"* — nenhum gate do repo lê `analise_financeira` para este invariante |

## Escopo

Para cada uma, **decidir e executar**: implementar a decisão faltante e flipar, ou **emendar
a ADR** declarando que aquela cláusula fica deferida (com dono e condição), e então flipar o
resto. O que **não** vale é flipar em bloco — seria carimbar como em vigor decisão que não
está, que é exatamente o defeito que a [[ADR-362]] D2 existe para impedir, cometido sobre
ela mesma.

**Não é bookkeeping.** Três das cinco têm cláusula **normativa** violada em superfície de
cliente ou em gate ausente. `Proposto` está descrevendo a realidade melhor do que
`Decidido` descreveria — o defeito é que ninguém sabia disso.

## Fora de escopo

As outras 5 ADRs `Proposto` da A40 ([[ADR-358]], [[ADR-379]], [[ADR-382]], [[ADR-383]] e a
`ADR-386`, sem lane) têm lane viva ou nenhuma — o `Proposto` delas é o estado correto e não
há o que decidir aqui.

## Critério de aceite

- Cada uma das cinco: `Decidido` **com** a decisão em vigor e evidência citada, **ou**
  `Proposto` mantido **com** §Deferimento datado nomeando dono e condição de retomada.
- Nenhuma flipa sem que a evidência por decisão esteja no PR.
- Se sobrar padrão, considerar gate que cruze `status: Proposto` com "todas as lanes citantes
  terminais" e **peça** a justificativa — hoje o silêncio é indistinguível de esquecimento.
