---
id: A40.l101
type: lane
title: "O conserto da folga deixou `equivalente_meses_poupanca` auto-referente"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1848
ship_date: "2026-08-30"
priority: P1
branch_slug: a40-l101-equivalente-meses-auto-referente
owner: financial-planner
depends_on: []
adrs: ["[[ADR-422]]"]
tags: [type/lane, sprint/a40, status/shipped, priority/p1, area/pipeline, area/financial-planning]
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
`folga < 0` sobrevive à suíte INTEIRA — **7931 passed** (tudo menos os 46 testes dos dois
arquivos depois reescritos). Só `folga == 0` está gateado — por
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

## Entrega (2026-08-30) — PR #1848, merge `bb716416`

[[ADR-422]] §Emenda 2026-08-30 (`amended_at: ["2026-08-30"]`, que regulariza também a
`Precisão` órfã da mesma data). A aritmética da D3 fica intacta; o que faltava era o
**domínio de definição**.

| decisão | efeito |
| --- | --- |
| **D3.a** | `equivalente_meses_poupanca` é `null` fora do domínio, com `motivo_supressao` irmão — forma da [[ADR-394]] §D7. Contrato **nullable, não ausência** ([[ADR-390]] §D2 reserva ausência para versão de artefato) |
| **D3.b** | o denominador é a folga **publicada** — gatear num número e dividir por outro publicava par irreproduzível |
| **D3.c** | `folga_pct` cai pelo mesmo guard: publicava "0% da receita" para quem queimou caixa |
| **D3.d** | prosa do E5 com ramo próprio (requisito: `TypeError` sem ele) + `motivo_supressao` no manifest do parecer, `manifest_version` 2.8.0 → 2.9.0 |

**Prova de A/B, não de verde:** 9 gates novos reprovam contra o produtor pré-fix; o mutante
que devolve `−99.0` só no ramo `folga < 0` — que sobrevivia à suíte inteira, 7931 passed —
reprova em 3.
`pytest tests -q` 7977 passed. Snapshot de view-model: **+1 linha**, valor não se move.

## Deferimento datado — o polo, 2026-08-30

**O que fica aberto:** com folga publicada de `R$ 0,01` e pontuais de `R$ 30.000,00`, o campo
publica `3.000.000,0` numa célula de KPI.

**Por que não fecha aqui, medido.** As duas rotas caem:

1. **Piso de materialidade** (`folga_pct < ~1%`): `config/scoring.json::thresholds_alertas`
   **não tem** piso de taxa de poupança a reusar — `poupanca_referencia_pct: 25` e
   `pontos_fortes_taxa_poupanca_min_pct: 30` são **alvos**. O limiar seria inventado, que é a
   crítica que a própria [[ADR-422]] D2 fez ao multiplicador `1,15`.
2. **Argumento de ruído**: não se sustenta. A sensibilidade **relativa** é 1:1 em todo o
   domínio — folga `R$ 90,00` e folga `R$ 0,01`, ambas +1%, movem o publicado em 0,99%.
   E o número suprimido seria **verdadeiro e acionável**: `333 meses` = *"irrecuperável ao
   seu ritmo"*, que é o diagnóstico que a família precisa. Suprimir teria o **sinal trocado**.

**Logo o polo é problema de LEGIBILIDADE, não de correção.** Dono: [[A40.l15]] (apresentação
do card de S2), gatilho `product-designer`. **Condição de retomada:** quando a l15 tocar o
KPI de consumo consciente — é a mesma célula.

## Follow-ups nomeados (não entram nesta lane)

| item | dono | por quê |
| --- | --- | --- |
| Rótulo "Equiv. meses de poupança" lê **pretérito**, e a emenda decidiu leitura **prospectiva** | [[A40.l15]] | rótulo do card de S2 é escopo dela; `janela-canonica.@critical.spec.ts:265` protege a fronteira |
| `data_corte` aplicado ao denominador e **não** ao numerador ⇒ populações diferentes (6,0 vs 12,0 medido) | [[A40.l98]] | é base do numerador; achado **novo** desta medição |
| Estorno negativo líquida no denominador e não no numerador ⇒ "6,0 meses" para gasto que se anulou | [[A40.l98]] | idem, achado **novo** |
| `aporte_investimento` no numerador e fora de `despesa_consumo` (57,14% do numerador da fixture) | [[A40.l98]] | é literalmente o item 1 do escopo dela |
| `check_adr_amendment_signal` é cego a "Precisão"/"Atualização" — **4** emendas datadas órfãs de `amended_at`, gate verde | lane de gate | a da [[ADR-422]] foi regularizada aqui; sobram 3 (ADR-132, ADR-159, ADR-260) |
| `check_planner_manifest_coverage` anuncia "Campo NOVO bloqueia" e é **cego a campo que nasce dentro de `$defs`** (`_e5_leaf_paths` não segue `$ref`) — 248 folhas vistas com e sem o campo novo | lane de gate | mesma classe de "o gate mede a patologia errada" |
| `frontend/src/types/report-analysis.ts` não tem gate que o compare ao gerado | lane de gate | a mentira envelhece em silêncio |
| `config/report_spec.md:371,394` ainda cita `equivalente_meses_aporte` e `teto_sugerido`, extintos pela [[ADR-422]] | dívida de closeout da [[A40.l94]] | quem buscar paridade lá reintroduz campo morto |
