---
id: A40.l98
type: lane
title: "Base de gasto pontual: quatro eixos de divergência, e o que prescreve é o que menos filtra"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l98-base-dos-pontuais-tres-produtores
owner: financial-planner
depends_on: []
adrs:
  - "[[ADR-422]]"
  - "[[ADR-333]]"
  - "[[ADR-425]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/financial-planning
---

# A40.l98 — `base-dos-pontuais-tres-produtores` (muta E5)

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

> A [[ADR-422]] tirou essa contaminação das prescrições **determinísticas** — a folga não lê
> mais pontuais e o teto deixou de existir. **Mas o parecer ainda a consome:** o exec context
> projeta `total_pontuais` e `total_pontuais_janela` (`parecer_planejador.yaml`), e o modelo
> emite com eles o risco *"gastos pontuais elevados"*, ancorado 3× no campo. Além disso o
> inventário, a prosa e o `equivalente_meses_poupanca` seguem contaminados.
> É P1 e não P0 porque nenhum número **determinístico** publicado se move com ela — não
> porque a contaminação tenha deixado de alcançar conselho.

## Escopo herdado da [[A40.l101]] (2026-08-30, #1848)

A l101 mediu o **par numerador↔denominador** de `equivalente_meses_poupanca` e derrubou a
premissa de que o numerador é subconjunto do subtraendo: são **cinco escapes**. Um já era o
item 1 abaixo; **dois são achados novos** e vêm para cá porque são população do numerador,
não domínio do denominador:

| escape | efeito medido |
| --- | --- |
| `data_corte` é aplicado ao denominador (`enrich(..., data_corte=...)`) e **não** ao numerador — `_dentro_da_janela` não tem limite superior, e `e5_analyzer_adapter.py:764` passa o `despesas` **cru** | numerador e denominador rodam sobre **populações diferentes**: mesmo pontual publica **6,0 ou 12,0** conforme o corte |
| **estorno negativo**: `CashFlowBuilder` líquida por categoria/mês (aceita negativo), o numerador filtra por `valor < consumo_min` | R$ 48k + estorno de −R$ 48k ⇒ denominador inalterado e numerador 48k ⇒ publica **"6,0 meses de poupança" para um gasto que se anulou** |
| `aporte_investimento` no numerador e fora de `despesa_consumo` | **57,14%** do numerador da fixture `pontuais-com-aporte` está fora do subtraendo — é o **item 1** abaixo, com magnitude medida |

Os dois primeiros **não** têm dono antes desta linha. Fechá-los aqui é o que torna o
numerador e o denominador comparáveis; a [[A40.l101]] fechou só o denominador.

## Escopo — os três itens deferidos pela [[A40.l94]]

1. **Aplicar `transfer_categories` ([[ADR-333]]) ao `_collect_candidates`.** Uma aplicação
   que hoje existe em um produtor e falta no outro.
2. **`nao_identificado` não entra em número que prescreve** — regra de domínio **decidida no
   co-design da [[A40.l94]] e não implementada**. Fica no inventário, com o residual impresso
   (contagem + valor), o que de quebra vira porta de entrada do Categorization Learning Loop.
   ⚠️ A regra existe **só em doc** — aqui e na [[A40.l94]] §Deferimento item 2 —, **nunca em
   código**. Cancelar as duas sem reencaminhá-la faz a decisão sumir.
3. **`pontual_mensal`** (o ritmo do pontual) entra **junto com a base limpa**. Nome canônico é
   o da [[A40.l15]], que precede o `provisao_pontual_mensal` do co-design — ver [[ADR-422]].
   Publicá-lo antes da base imprimiria número 57,5% movimentação; emiti-lo sem leitor criaria
   a classe emissor-sem-leitor que a [[A40.l88]] gateia.

## Fora de escopo, declarado

Consertar a **detecção** da transferência do Itaú e das conversões Wise é config de padrões
por workspace (`transferencias_internas`) + `PV9-12`, não fórmula. Esta lane trata do
**filtro** que os produtores aplicam, não da qualidade do detector. Contenção que independe
do detector é o item 2.

## Co-design 2026-08-30 — três especialistas, e a medição reordenou a lane

`financial-planner` + `data-engineer` + `senior-cto` em paralelo. **Três premissas
desta lane caíram na medição**, e o escopo mudou de forma.

### O item 1 estava mal nomeado

A lane dizia: *"aplicar `transfer_categories` ao `_collect_candidates` — uma aplicação
que existe num produtor e falta no outro"*. Medido, isolando cada causa:

| recorte | Δ full | Δ janela |
| --- | --- | --- |
| ex-`transfer_categories` (aporte) | −R$ 190.000,00 | **R$ 0,00** |
| ex-transferência interna **detectada** | **R$ 0,00** | **R$ 0,00** |
| ex-`nao_identificado` | −R$ 348.916,19 | **−R$ 249.374,91** |

A metade "transferência interna" move **zero** porque o **E4 já a aplica**
(`transaction_classifier.py:361`). A metade `transfer_categories` move zero **na
janela** (o aporte é de 2025-07, fora dela). **O item 2 carrega o peso, não o 1.**

### São QUATRO eixos de divergência, sobre DOIS substratos

O quarto eixo é o **threshold**: `backend/app/api/reports.py::list_consumo_pontuais`
**não passa** `threshold`, então a lista cai no `_DEFAULT_THRESHOLD = Decimal("2000")`
hardcoded, enquanto o KPI lê `scoring.json::thresholds_alertas.consumo_consciente_min`.
Ambos valem 2000 e **coincidem por acaso** — editar o `scoring.json` os separa em
silêncio, e **nenhum teste falha**. ⚠️ Teste de igualdade aqui é **vazio**: o gate tem
de mover o scoring para 2500 e provar que as duas superfícies se movem.

E os dois lados leem substratos diferentes — lista do **DB**
(`load_filtered_transactions`), KPI do artefato **E4** (`despesas.dados`). Conserto num
lado não alcança o outro.

### A cobertura da base é 36,8%, não "57,5% de contaminação"

Os dois números são coisas diferentes e a lane os misturava: **63,2%** da janela
(R$ 249.374,91) é `nao_identificado` — **não medido**; os R$ 226.886,65 (57,5%) são a
fatia que a revisão **conseguiu identificar** como movimentação dentro desse balde. O
resto é genuinamente desconhecido.

### Decisões (não reabrir)

- **Definição canônica tem 4 cláusulas**, 3 de **natureza** (idênticas nos três
  produtores) e 1 de **escopo** (temporal, legitimamente plural e já rotulada). A
  exclusão de natureza é a **união** `transfer_categories ∪ detector` — hoje cada
  produtor tem metade da regra certa. Rótulo resolve ambiguidade de escopo; **não**
  conserta lançamento que não devia estar na base.
- **`GastoPontualPolicy`** frozen em `pipeline/domain/services/`, injetada nos três, com
  **dois conjuntos nomeados e deliberadamente NÃO iguais**: `transferencia_patrimonial`
  ([[ADR-333]], entra em `despesa_consumo` ⇒ move `folga_mensal`/`taxa_poupanca`) e
  `nao_consumo_pontual` (superset, sai só da base do pontual). ⚠️ **Fundir os dois não é
  refactor, é mudança de número** — e `transferencia_familiar` é plausivelmente consumo.
  Fusão é decisão do `financial-planner`, fora desta lane.
- **Veredito por item**, enum fechado (`incluido | transferencia_por_categoria |
  transferencia_detectada | recorrente | nao_identificado`) — sem ele o residual não tem
  como ser atribuído por causa.
- **Regra do `nao_identificado` + cobertura + supressão:** [[ADR-425]].
- **`LC6-06` não ganha espelho** e **não** tenta separar juros de amortização (nada em
  `financiamentos` carrega o split; inferir é adivinhação dentro de taxa de poupança,
  a classe que gerou a [[ADR-422]]). O produtor vivo da terceira taxa **não foi
  localizado** no schema nem no frontend — o candidato restante é o exec context do
  parecer derivando de `receita_total`/`despesa_total` full. **Nomear o produtor é o
  primeiro passo**; o conserto é de escopo (parar de publicar/projetar), não de fórmula.

### Sequência — 4 PRs, um conjunto de exclusão por PR

| PR | escopo | delta | rebaseline |
| --- | --- | --- | --- |
| **PR1** | `GastoPontualPolicy` + threshold fonte única + fiação nos 3, **conjuntos inalterados** | **zero por construção** | nenhum — golden inalterado **é** o gate |
| **PR2** | aplica `transferencia_patrimonial` ao `_collect_candidates` | −R$ 190.000 no full | golden + snapshot + `manifest_version` |
| **PR3a** | objeto `base_pontuais` + **leitor no mesmo PR** | impresso por motivo | golden + snapshot + manifest |
| **PR3b** | `nao_identificado` sai da base publicável ([[ADR-425]] D1) | = `excluidos[nao_identificado].valor` | golden + snapshot + manifest |

**O que saiu desta lane para a [[A40.l102]]** (corte pelo eixo *muta E5* × *não muta*):
o `LC6-07` (dedup, que é do E3 e mede-primeiro), a declaração impressa do que cada
superfície exclui, e os dois cards de S2 herdados da [[A40.l15]]. Eles não disputam a
janela de mutação de E5 e podem ir em paralelo.

PR1 é o que torna o resto atribuível: sem ele, o delta do PR2 mistura "mudou o conjunto"
com "mudou a fiação". PR2 e PR3 **não** viajam juntos — dois conjuntos, um golden, delta
inatribuível. `manifest_version` do parecer sobe em PR2, PR3a e PR3b, **um bump por PR**:
`total_pontuais*` muda de valor sem mudar de nome e o cache tem TTL de 7 dias.

**`pontual_mensal` sai desta lane** — entra depois, sob o mesmo `motivo_supressao`.
Publicá-lo antes cria emissor com leitor **errado**, pior que emissor-sem-leitor.

### Fixture precisa discriminar CADA causa

Estender `pontuais-com-aporte-3_reconciled.json` para ter uma row por motivo (aporte,
transferência detectável, `nao_identificado`, pontual legítima) + anti-vacuidade no molde
do `test_fixture_discrimina_folga`: **cada bucket de `excluidos` não-zero na fixture**,
senão o gate passa sobre um mundo que não exercita o termo em disputa.

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
