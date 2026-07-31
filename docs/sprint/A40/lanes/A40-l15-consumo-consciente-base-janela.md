---
id: A40.l15
type: lane
title: "Consumo Consciente: card fala em quatro bases temporais; KPI de pontuais na base da janela"
sprint: A40
plan: PLAN-report-trust
status: planned
priority: P2
branch_slug: a40-l15-consumo-consciente-base-janela
adrs: ["[[ADR-306]]"]
depends_on: ["[[A40.l3]]"]
tags:
  - type/lane
  - sprint/a40
  - status/planned
  - priority/p2
  - area/frontend
  - area/pipeline
---

# A40.l15 — `consumo-consciente-base-janela` (spun off da [[A40.l3]])

## Problema

O card "Consumo Consciente" fala em **quatro bases temporais** ao mesmo tempo, e
a [[A40.l3]] só conseguiu **rotular** as bases — não unificá-las:

1. **Gastos pontuais / Equiv. meses de aporte** — `total_pontuais` e
   `equivalente_meses_aporte`, acumulados de **todo o período documentado**.
2. **Folga mensal / Teto sugerido** — derivados pelo E5 da **janela canônica**
   (`ConsumoConscienteCalculator._resolve_janela` lê `fluxo.janela_12m`).
3. **Lista de lançamentos** — `PeriodToggle` próprio, default **3M**, vinda do
   endpoint `/reports/consumo-pontuais`.
4. **Prosa do E5** (`analise`) — fala do **período completo**.

O leitor vê `R$ 250.000,00` de pontuais ao lado de uma folga de `R$ 19.000,00`
por mês, uma lista de 3 meses que não soma nada perto de 250k, e uma frase que
menciona um terceiro escopo. A [[A40.l3]] deixou o card **coerente-e-menos-
acionável**: KPI de pontuais em full ROTULADO (mesma base da prosa), folga
rotulada com a janela. Esta lane resolve a acionabilidade.

## Decisão de escopo que criou esta lane

A [[A40.l3]] chegou a implementar a troca do KPI + os co-changes de E5. O
resultado: lane de "conformidade de frontend, esforço S" virou pipeline +
rebaseline de snapshot + 2 ADRs + CI, e trouxe 4 bloqueantes na revisão — **2
deles instâncias NOVAS de "valor de um bloco sob rótulo de outro"**, que é o
defeito-alvo da própria lane. O gate de shipping veio do `financial-planner`:

> "A troca do KPI só entra junto com os três co-changes de E5. Se eles não
> couberem no mesmo PR, reverta o KPI para `total_pontuais` com rótulo impresso —
> card coerente-e-menos-acionável > card incoerente."

A [[A40.l3]] tomou o fallback. Esta lane é o caminho completo, com revisão e
sinal de delta próprios.

## Análise do `financial-planner` (preservada — não reabrir)

**O parêntese de D6 é load-bearing.** [[ADR-306]] §Decisão D6 diz
`total_pontuais` **(tabela)** segue full-period. O parêntese escopa D6 ao
**inventário histórico**, não ao KPI. E D1 põe `folga` — e tudo que a alimenta —
na família de janela 12m. O KPI de gastos pontuais é o termo que fecha a álgebra
da folga:

```
folga = receita_rec_mensal − (despesa_mensal_media − pontuais_janela / n_meses)
```

Sem o KPI na base da janela, o card não é **reproduzível** pelo leitor: ele não
consegue chegar na folga exibida partindo dos números exibidos. Logo o KPI é
família-D1 e a tabela é agregado histórico (full por D6). **Não é redecisão de
ADR** — é leitura do texto vigente. Registrada como nota de leitura na
[[ADR-306]] pela [[A40.l3]] para o próximo revisor não re-litigar do zero.

**As duas leituras coexistem no card, cada uma com rótulo IMPRESSO.** Remover o
acumulado full seria perda de informação; misturá-los sem rótulo é o defeito.

### Refutação de "número menor esconde o padrão"

A objeção intuitiva é que trocar 250k por 96k "esconde" gastos. **Medido, é o
contrário:** na fixture de contrato o full rende `250.000 / 36 = 6,9k/mês` e a
janela rende `96.000 / 12 = 8,0k/mês`. A janela recente é **pior por mês** — o
acumulado full **suaviza a deterioração** ao diluir gastos recentes por 36 meses.
O número maior é o menos alarmante em ritmo, que é a unidade em que a família
decide. O acumulado histórico continua no card, rotulado, para quem quiser o
inventário.

## Co-changes de E5 exigidos (os três)

Sem eles o frontend teria de fazer aritmética monetária de headline, o que
[[ADR-090]] proíbe:

1. **`consumo_consciente.pontual_mensal`** = `pontuais_janela / n_meses` — o
   ritmo, e o termo que literalmente fecha a álgebra da folga.
2. **`consumo_consciente.equivalente_meses_aporte_janela`** =
   `pontuais_janela / aporte_mensal`. `aporte_mensal` é constante entre janelas,
   logo o equivalente é reprojetável — não havia motivo para o KPI ficar full.
3. **`consumo_consciente.analise` reescrita** para declarar as **duas** janelas
   (a prosa era a única superfície que citava um total nu). Corrige de passagem um
   bug pt-BR medido no substrato: `f"R$ {v:,.0f}"` emite **`R$ 2,000`** e
   **`R$ 250,000.00`** (en-US) na frase do card — visível no PDF gerado pela
   [[A40.l3]].

Todos em `pipeline/domain/services/consumo_consciente_calculator.py` +
`to_legacy_dict`, com contraparte em `frontend/src/types/report-analysis.ts`.

## Gate de shipping (herdado do co-design — não flexibilizar)

**Os três co-changes entram no MESMO PR que a troca do KPI.** Se não couberem, o
KPI **fica em `total_pontuais` com rótulo impresso** — estado atual pós-[[A40.l3]].
Card coerente-e-menos-acionável > card incoerente.

## Critério de aceite

- KPI de pontuais e equivalente lidos da janela, **com rótulo impresso** da
  janela; acumulado full permanece no card, rotulado, em superfície própria.
- Ritmo mensal (`pontual_mensal`) exibido ao lado do total da janela.
- Prosa do E5 declara as duas janelas, em formato monetário pt-BR.
- Álgebra da folga **reproduzível** a partir dos números exibidos: teste que
  reconstrói `folga_mensal` a partir de `receita_rec_mensal`,
  `despesa_mensal_media` e `pontual_mensal`.
- Invariante do seletor mantido: `resolveConsumoBases` continua a **nunca** emitir
  par (valor, rótulo) de blocos diferentes — hoje o rótulo histórico é constante
  por construção; com dois pares ele volta a ser derivável e precisa de teste
  dedicado (payload sem `total_pontuais_janela` ⇒ valor full **e** rótulo full).
- Rótulo é **texto impresso**, verificado no PDF com extração de texto
  ([[ADR-306]] §Emenda A40.l3: tooltip não conta).

## Custo que esta lane carrega (declarar no PR)

- **Rebaseline de snapshot obrigatório:** campo novo no view-model E5 quebra
  `backend/tests/test_report_view_model_snapshot.py`. Rodar com
  `MATHOMS_UPDATE_SNAPSHOT=1` na fatia `backend/tests` (~8 min), não na fatia
  `pipeline`.
- **Sinal de delta próprio:** no substrato versionado
  (`backend/tests/snapshots/dogfood_view_model.json`) `total_pontuais == 0` e
  `janela_meses == 1` ⇒ Δ = **0**; a fixture `janela-divergente` move o KPI de
  `R$ 250.000,00` para `R$ 96.000,00` **por construção**. Nenhum dos dois é
  evidência de sinal na base do cliente — declarar o efeito como
  workspace-dependente, com o argumento de ritmo (6,9k/mês vs 8,0k/mês) como
  justificativa de direção, não como medição.
- **Guarda de janela insuficiente:** `janela: "12m"` com `janela_meses: 1` é o
  valor real do substrato. Um KPI de janela sobre 1 mês documentado é ruído;
  avaliar com o `financial-planner` se abaixo de ~6 meses o card deve declarar
  janela insuficiente em vez de exibir o número (espírito de D3 na camada de
  apresentação — hoje não aplicado em nenhum lugar).
