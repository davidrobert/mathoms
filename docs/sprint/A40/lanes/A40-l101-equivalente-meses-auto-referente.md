---
id: A40.l101
type: lane
title: "O conserto da folga deixou `equivalente_meses_poupanca` auto-referente"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l101-equivalente-meses-auto-referente
owner: financial-planner
depends_on: []
adrs: ["[[ADR-422]]"]
tags: [type/lane, sprint/a40, status/open, priority/p1, area/pipeline, area/financial-planning]
---

# A40.l101 — `equivalente-meses-auto-referente`

> **Origem:** `F2` da **U3** ([[REPORT-REVIEWS-active]] §r7) · triagem
> **`REGRESSÃO-DE-CONSERTO`**, confirmada por cético como P1 não-inerte.

## O defeito

A [[A40.l94]] ([[ADR-422]]) consertou a folga mensal — verificado, **segura**. Mas o campo
irmão ficou **auto-referente**: o denominador passou a ser `receita_recorrente − despesa_consumo`,
e o numerador (`total_pontuais_janela`) alimenta o **subtraendo** desse denominador. A leitura de
"quantos meses de poupança este gasto custou" deixa de medir o que o rótulo promete.

> **Precisão 2026-08-30 (medição da lane).** A frase de origem — *"o numerador é 45,4% do
> denominador"* — está **errada como transcrita** e foi corrigida aqui antes de chegar à ADR.
> Os 45,37% são a fração do **subtraendo** (`total_pontuais_janela ÷ despesa_consumo` =
> 394.525,39 ÷ 869.511,63 no run da U3). Do **denominador** (a folga) o numerador mensalizado
> é **33,79%**, e o valor publicado é `P ÷ F` = **4,05**. A palavra certa é *auto-referente*;
> *subconjunto* também cai — ver §Medição.

## O que o cético derrubou

A alegação de que a razão ser **superlinear** é defeito em si **cai** — razão
`gasto ÷ superávit` é a forma legítima de todo indicador tipo dívida/renda. O defeito é o
**polo** e o colapso, não a curvatura.

**Classe:** conserto que fecha o defeito principal e deixa o irmão lendo a base nova. É a
razão de a rodada perguntar por `REGRESSÃO-DE-CONSERTO` explicitamente.

## Medição (2026-08-30)

**O mecanismo é um guard transplantado, e `git show 05561dc0` o mostra.** A guarda
`else 0.0` **não é nova**: ela vem da fórmula anterior, cujo denominador era
`cfg.aporte_mensal` — a meta **declarada** pelo usuário, sempre `≥ 0`, onde `0` significava
*"não configurou"* e `0.0` era um N/A desajeitado porém benigno. A [[ADR-422]] D3 trocou o
denominador por `folga_mensal` — quantidade **medida**, que vai a negativo — e carregou o
guard junto, sem revisão:

| denominador | domínio | o que `≤ 0` significa | `0.0` lê como |
| --- | --- | --- | --- |
| `meta_aporte_mensal` (antes) | meta declarada, `≥ 0` | usuário não configurou meta | N/A benigno |
| `folga_mensal` (depois) | quantidade medida, `∈ ℝ` | a família não poupou nada | **o melhor número no pior mundo** |

**Alcançável fim-a-fim, não só no unit.** Fixture `folga-negativa-3_reconciled.json` por
`run_e3_e4_e5`: `folga_mensal −4.500,00` · `folga_pct −45,0` ·
`taxa_poupanca_recorrente −45,0` · `total_pontuais_janela 30.000,00` ⇒ o campo publica
**`0.0`** e a prosa do E5 **afirma** *"…R$ 30.000,00, equivalentes a 0.0 meses de poupança."*
O mesmo card imprime, lado a lado, "Folga mensal −R$ 4.500,00 / −45% da receita" (honesto) e
"Equiv. meses de poupança 0,0". A família saudável do teste existente publica **3,0**.

**O polo e o salto.** Com pontuais de R$ 15.000: folga R$ 0,01 → **1.500.000,0**;
folga R$ 0,00 → **0,0**. Um centavo de despesa separa +1,5 M de 0.

**`0.0` é três mundos disjuntos** — sem gasto pontual (bom), sem poupança nenhuma (o pior),
e razão `< 0,05` arredondada (irrelevante). O `?? "—"` de `ConsumoConscienteCard.tsx:73`
**nunca dispara**, porque o produtor jamais emite `None`.

**O ramo `folga < 0` é inteiramente cego.** Mutante que devolve `−99.0` só quando
`folga < 0` sobrevive à suíte (153 passed). Só `folga == 0` está gateado — por
`test_zero_quando_folga_nao_positiva`, o único teste do repo sobre o polo, e ele **assere o
defeito**.

**Nenhuma fixture do repo separava os dois mundos** (5 payloads com `consumo_consciente`,
todos com `folga > 0`) — um gate escrito contra elas nasceria verde, o modo de falha exato do
`RR6-07`. Daí a fixture nova vir **antes** do gate.

### A auto-referência é estrutural, mas o numerador **não** é subconjunto do subtraendo

`d(denominador)/d(numerador) = −1/n` exatamente: numerador e denominador saem da mesma lista
`by_kind['despesa']` do `CashFlowBuilder` (`e5_analyzer_adapter.py:591` e `:764` recebem o
**mesmo** objeto `despesas`). Forma fechada `(P₀+X)/(F₀−X/n)`; amplificação medida vs
denominador fixo: 1,31× em X=12k · 4× em 48k · 256× em 90k.

Mas há **cinco escapes medidos** — o numerador vaza do subtraendo nos dois sentidos:

| escape | efeito medido |
| --- | --- |
| `aporte_investimento` entra no numerador e sai de `despesa_consumo` | o **mesmo** dinheiro publica 6,0 ou 12,0 só por categoria; **57,14%** do numerador da fixture `pontuais-com-aporte` está fora do subtraendo |
| `data_corte` é aplicado ao denominador e **não** ao numerador (`_dentro_da_janela` não tem limite superior) | numerador e denominador rodam sobre **populações diferentes** — 6,0 vs 12,0 |
| threshold R$ 2.000 · `recurrent_categories` | denominador se move, numerador não |
| estorno negativo | −48k líquida no denominador e não no numerador ⇒ publica "6,0 meses" para gasto que se anulou |

Os escapes de **base** são da [[A40.l98]] (o `aporte_investimento` é literalmente o item 1 do
escopo dela). O `data_corte` e o estorno são achados **novos** desta medição.

### Efeito de nível, longe do polo

No run da U3 o campo publica **4,05** onde o contrafactual "poupança que existiria sem os
pontuais" daria **3,03** — **1,338×** —, a `folga_pct` **57%**. Ou seja: a auto-referência não
é só um defeito de fronteira. Se isso é defeito ou é a leitura correta depende de qual
pergunta o campo responde (reposição prospectiva vs custo retrospectivo) — decisão de domínio.

⚠️ E o denominador contrafactual `F + P∩C/n` é **numericamente a `folga_mensal` pré-[[ADR-422]]**,
ao centavo (130.179,78 no dogfood; resíduo zero nas duas fixtures). Adotá-lo devolveria à
página, como denominador implícito recuperável, exatamente o número que a [[ADR-422]] matou.

### Materialidade — lacuna honesta

Não há medição de **quantos workspaces reais** estão hoje em `folga ≤ 0`. Os 69 artefatos E5
do `mathoms.db` estão cifrados (Fernet) e não foram decifrados — é dado financeiro real de
família; os payloads em texto claro no disco são todos pré-[[ADR-422]]
(`equivalente_meses_aporte`). O regime é **estruturalmente alcançável** (provado fim-a-fim);
sua frequência em produção fica aberta.
