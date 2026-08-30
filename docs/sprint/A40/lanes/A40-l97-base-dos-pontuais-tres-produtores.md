---
id: A40.l97
type: lane
title: "Base de gasto pontual tem três produtores com filtros disjuntos, e o que prescreve é o que menos filtra"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l97-base-dos-pontuais-tres-produtores
owner: financial-planner
depends_on: []
adrs:
  - "[[ADR-422]]"
  - "[[ADR-333]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/financial-planning
---

# A40.l97 — `base-dos-pontuais-tres-produtores`

> **Origem:** `LC6-05` ([[LEDGER-CERTIFY-active]] §r6, rodada **U2**) + §Deferimento datado
> da [[A40.l94]] (2026-08-29). Aberta 2026-08-30 porque aquele deferimento apontava para
> "a lane da base dos pontuais", que **não existia** — destino fantasma, invisível aos gates.

## O defeito

Existem **três** produtores de "gasto pontual" em produção, com filtros **disjuntos**:

| produtor | exclui | superfície |
| --- | --- | --- |
| `FluxoEnricherConfig.transfer_categories` ([[ADR-333]]) | `aporte_investimento` | taxa de poupança, `despesa_consumo` |
| `consumo_pontuais.py::_is_pontual` | transferência interna (`InternalTransferDetector`) + 3 categorias | a **lista** do card |
| `ConsumoConscienteCalculator._collect_candidates` | **nenhum dos dois** — só `recurrent_categories` | o **KPI** do card, a prosa do E5 e a âncora do parecer |

Lista e KPI do mesmo card filtram coisas diferentes. O que **prescreve** é o que menos filtra.

**Medido no dogfood** (janela 12m, `total_pontuais_janela` = R$ 394.525,39): R$ 194.886,65
saem do C6Bank nomeando outro banco do próprio titular e R$ 32.000 são conversões BRL→USD
na Wise — **57,5% da base** é movimentação patrimonial, toda caída em `nao_identificado`
porque o detector não a pegou. E `aporte_investimento` é R$ 190.000 de `total_pontuais`
(20,6%), que o parecer cita como âncora do risco "gastos pontuais elevados".

> A [[ADR-422]] tirou essa contaminação de toda superfície que **prescreve** (a folga não
> lê mais pontuais, e o teto deixou de existir). O que resta contaminado é **descritivo**:
> o inventário, a prosa e o `equivalente_meses_poupanca`. É por isso que esta lane é P1 e
> não P0 — ver [[ADR-422]] §"O que esta ADR NÃO conserta".

## Escopo — os três itens deferidos pela [[A40.l94]]

1. **Aplicar `transfer_categories` ([[ADR-333]]) ao `_collect_candidates`.** Uma aplicação
   que hoje existe em um produtor e falta no outro.
2. **`nao_identificado` não entra em número que prescreve** — regra de domínio **decidida no
   co-design da [[A40.l94]] e não implementada**. Fica no inventário, com o residual impresso
   (contagem + valor), o que de quebra vira porta de entrada do Categorization Learning Loop.
   ⚠️ Esta regra existe hoje em **um único sítio** (este). Se a lane for cancelada sem
   reencaminhá-la, a decisão some.
3. **`pontual_mensal`** (o ritmo do pontual) entra **junto com a base limpa**. Nome canônico é
   o da [[A40.l15]], que precede o `provisao_pontual_mensal` do co-design — ver [[ADR-422]].
   Publicá-lo antes da base imprimiria número 57,5% movimentação; emiti-lo sem leitor criaria
   a classe emissor-sem-leitor que a [[A40.l88]] gateia.

## Fora de escopo, declarado

Consertar a **detecção** da transferência do Itaú e das conversões Wise é config de padrões
por workspace (`transferencias_internas`) + `PV9-12`, não fórmula. Esta lane trata do
**filtro** que os produtores aplicam, não da qualidade do detector. Contenção que independe
do detector é o item 2.

## Critério de aceite

- Uma só definição de "gasto pontual", consumida pelos três produtores — ou, se as três forem
  legitimamente distintas, cada uma **declara** o que exclui, na superfície que a publica.
- Teste que a base exclui `transfer_categories` **e** transferência interna detectada, sobre
  fixture que contenha as duas coisas (a `pontuais-com-aporte-3_reconciled.json` da
  [[A40.l94]] já traz aporte dentro da janela — falta transferência interna).
- O residual `nao_identificado` é **impresso** com contagem e valor onde a base aparece.
- Delta declarado por causa: quanto move por excluir aporte, quanto por excluir transferência.

## Herdado por roteamento (2026-08-30)

`LC6-06` (aporte e amortização em `despesa_total` na janela cheia ⇒ uma **terceira** taxa de
poupança publicada) e `LC6-07` (dois pares duplicados na lista de pontuais, sob cabeçalho que
afirma "contamos cada um uma vez só") são da mesma família de base e ficam com esta lane.
`LC6-03` já tem gatilho próprio ([[ADR-321]]) e **não** entra aqui.
