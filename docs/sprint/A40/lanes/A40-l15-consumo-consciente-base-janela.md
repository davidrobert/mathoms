---
id: A40.l15
type: lane
title: "Consumo Consciente: KPI de pontuais na base da janela + texto de base do donut e do chart mês a mês"
sprint: A40
plan: PLAN-report-trust
status: cancelled
priority: P2
branch_slug: a40-l15-consumo-consciente-base-janela
adrs: ["[[ADR-306]]"]
depends_on: ["[[A40.l3]]"]
tags:
  - type/lane
  - sprint/a40
  - status/cancelled
  - priority/p2
  - area/frontend
  - area/pipeline
---

# A40.l15 — `consumo-consciente-base-janela` (spun off da [[A40.l3]])

> **Emenda 2026-08-30 ([[A40.l94]] · [[ADR-422]] · #1828) — três premissas desta lane
> venceram, e uma delas tornava o critério de aceite insatisfazível.**
>
> 1. A **álgebra da folga** que a §Análise preserva ("não reabrir") foi **superada**: a folga
>    não tem mais termo de pontuais ([[ADR-306]] §D6 traz o aviso no ponto da fórmula).
> 2. O **co-change 2** foi entregue sob outro nome e outro denominador —
>    `equivalente_meses_poupanca` = `total_pontuais_janela ÷ folga_mensal`. O
>    `aporte_mensal` que ele propunha como denominador foi **rejeitado por medição**
>    ([[ADR-422]] D3: meta editável pelo usuário ⇒ diagnóstico não-auditável; fator 4,9×).
> 3. O **co-change 3** (prosa declarando as duas janelas) já **shippou** no #1828.
>
> `teto_sugerido` **não existe mais**. O que resta desta lane é a pergunta de base temporal
> do KPI de pontuais (D6 vs D1) e o texto dos dois cards de S2 — não a álgebra.

## Escopo herdado da [[A40.l101]] (2026-08-30, #1848)

A l101 deu **domínio de definição** ao `equivalente_meses_poupanca` (`null` fora dele, com
`motivo_supressao`) e deixou aqui duas coisas que são **apresentação do card de S2**, não
aritmética do produtor:

1. **O polo, e por que não foi fechado lá.** Com folga publicada de `R$ 0,01` e pontuais de
   `R$ 30.000,00` o campo publica `3.000.000,0` numa célula de KPI. As duas rotas de
   fechamento caíram **por medição**: (i) `config/scoring.json::thresholds_alertas` **não tem**
   piso de taxa de poupança a reusar — `poupanca_referencia_pct: 25` e
   `pontos_fortes_taxa_poupanca_min_pct: 30` são **alvos** —, logo o limiar seria inventado, a
   mesma crítica que a [[ADR-422]] D2 fez ao multiplicador `1,15`; (ii) a sensibilidade
   **relativa** é 1:1 em todo o domínio (folga `R$ 90,00` e `R$ 0,01`, ambas +1%, movem
   0,99%), então não há argumento de ruído, e o número suprimido seria **verdadeiro e
   acionável** — `333 meses` = *"irrecuperável ao seu ritmo"*. Suprimir teria o **sinal
   trocado**. Sobra **legibilidade**: 7 dígitos num slot de KPI. Gatilho `product-designer`.
2. **O rótulo lê pretérito e a fórmula é prospectiva.** "Equiv. meses de poupança" e
   *"equivalentes a X meses de poupança"* leem *"quanto este gasto consumiu"* — a leitura
   **retrospectiva**, que a [[ADR-422]] §Emenda 2026-08-30 **rejeitou** (sob ela o único
   denominador coerente é `folga + P/n`, que é numericamente a folga pré-[[ADR-422]], ao
   centavo). A forma decidida é conversão de unidade à taxa **observada**; o rótulo tem de
   dizer "poupança **atual**", sem verbo de reposição. A prosa do ramo suprimido já saiu
   assim; o rótulo do card é escopo desta lane.

**Condição de retomada:** ao tocar o KPI de consumo consciente — é a mesma célula dos dois
itens. `frontend/tests/e2e/reports/janela-canonica.@critical.spec.ts:265` é a fronteira que
protege esta lane e reprova quem mexer no par sem passar por ela.

## Escopo herdado da [[A40.l3]] no fechamento (2026-07-31)

Além da base do KPI de pontuais (que criou esta lane), a [[A40.l3]] transferiu o
**texto de conclusão/contexto de dois cards de S2**. Motivo: cinco rodadas
tentaram fechar o par (valor, rótulo) desses textos e todas produziram
inconsistência nova, porque a causa é estrutural — os dois citam bases
legitimamente distintas ([[ADR-333]] ex-aporte vs bruto de todo o período) e
**escolher qual base cada texto declara é decisão de domínio**, que é o objeto
desta lane. Os três defeitos vão **medidos**, para não serem re-descobertos:

1. **Donut: a rosca desenha 50,0%, a conclusão do mesmo card imprime 43%.**
   Medido na fixture `janela-divergente`: Moradia = 414.000 de 828.000 de consumo
   na janela renderizada (ex-aporte) ⇒ **50,0%** da geometria do donut. A
   conclusão vem de `deriveChartConclusion("despesas_doughnut")`, que lê
   `fluxo_caixa.despesas_por_categoria` (bloco full, **com** aporte):
   558.000 / 1.296.000 ⇒ **43,1%**, renderizado "43%". Dois números para a mesma
   pergunta, no mesmo card. Decidir aqui: o percentual acompanha o desenho
   (janela, ex-aporte) ou o rótulo acompanha a base full.
2. **`ReceitaDespesaMensalChart`: conclusão mensaliza a série inteira sem rótulo
   e emite uma SEGUNDA taxa de poupança.** Medido no DOM e no PDF: "Receita média
   de R$ 42.667/mês e despesa média de R$ 36.000/mês. Taxa de poupança de 15.6%."
   — ao lado do card irmão que declara a janela canônica de 12m, e com a taxa
   canônica ex-aporte (25,0%) já impressa no hero. O contexto do mesmo card
   agrega 36 meses declarando apenas "Série temporal mensal (36 meses)".
   **Armadilha medida:** a versão que a l3 chegou a escrever ("Janela exibida —
   12 meses (…): receitas de … e despesas totais de …") rotula **a janela
   exibida** sobre um agregado que não é da janela quando `despesa_datasets`
   falta — nesse ramo o card exibe "despesas (R$ 0)" e "Taxa de poupança de
   100.0%". Não reaproveitar aquela versão sem re-medir o ramo degradado.
3. **A fixture escondia a divergência** — `despesa_datasets` usava o label
   `"Aporte em investimentos"`, que `isAporteInvestimentoKey` não casa e o
   produtor nunca emite (`fluxo_caixa_enricher.py:404` ⇒ `"Aporte
   Investimento"`). Com o label errado o aporte entrava no donut e os dois totais
   coincidiam. **Já corrigido em `main`**: esta lane herda a fixture fiel, e é ela
   que torna o defeito 1 visível.

Infraestrutura já entregue pela l3 e consumível aqui, sem reabrir decisão:

- `DespesasDoughnutChart` expõe `{rows, fonte, aporteExcluido}` no MESMO objeto
  que carrega as fatias (`fonte: "janela" | "agregado"`), para o rótulo nascer da
  expressão que somou os valores em vez de ser inferido. **Nenhum texto lê esses
  campos hoje.**
- `janelaLabel.ts` (`describeJanelaEscopo`/`describeJanelaEm`/`janelaBadgeLabel`)
  e o seletor `fluxoJanela.ts` — com a regra de que **sem `janela_meses` o texto
  não cita contagem** (`?? 12` era contagem fabricada).
- Guarda de seção com `CARDS_DA_L15` excluindo nominalmente estes dois cards em
  `janelaCanonica.contract.test.tsx` e em `janela-canonica.@critical.spec.ts`.
  **Ao fechar esta lane, remover as duas exclusões** — o assert de "exclusão não é
  vácuo" fica verde mesmo depois, então ninguém será avisado automaticamente.

## Problema

O card "Consumo Consciente" fala em **quatro bases temporais** ao mesmo tempo, e
a [[A40.l3]] só conseguiu **rotular** as bases — não unificá-las:

1. **Gastos pontuais** — `total_pontuais`, acumulado de **todo o período documentado**.
   (~~`equivalente_meses_aporte`~~ migrou para a janela em 2026-08-29, [[ADR-422]] D3.)
2. **Folga mensal / Equiv. meses de poupança** — derivados pelo E5 da **janela canônica**
   (`ConsumoConscienteCalculator._resolve_janela` lê `fluxo.janela_12m`).
   (~~Teto sugerido~~ extinto do contrato, [[ADR-422]] D2.)
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

1. **`consumo_consciente.pontual_mensal`** = `pontuais_janela / n_meses` — o ritmo.
   ⚠️ **não é mais "o termo que fecha a álgebra da folga"** (a folga não o lê desde a
   [[ADR-422]] D1); segue valendo como ritmo exibível. Este é o **nome canônico** do campo,
   e prevalece sobre o `provisao_pontual_mensal` que o co-design da [[A40.l94]] propôs.
   Entrega vai com a [[A40.l98]], junto com a base limpa.
2. ~~**`consumo_consciente.equivalente_meses_aporte_janela`** = `pontuais_janela / aporte_mensal`~~
   — ✅ **entregue em 2026-08-29 sob outro nome e outro denominador**:
   `equivalente_meses_poupanca` = `total_pontuais_janela ÷ folga_mensal`. O `aporte_mensal`
   foi **rejeitado por medição** ([[ADR-422]] D3): é meta editável pelo usuário, então o
   diagnóstico se movia sem nada acontecer no mundo.
3. ✅ **entregue no #1828** — **`consumo_consciente.analise` reescrita** para declarar as **duas** janelas
   (a prosa era a única superfície que citava um total nu). Corrige de passagem um
   bug pt-BR medido no substrato: `f"R$ {v:,.0f}"` emite **`R$ 2,000`** e
   **`R$ 250,000.00`** (en-US) na frase do card — visível no PDF gerado pela
   [[A40.l3]].

Todos em `pipeline/domain/services/consumo_consciente_calculator.py` +
`to_legacy_dict`, com contraparte em `frontend/src/types/report-analysis.ts`.

## Herdado da A40 (2026-07-31) — abertura da S3: o que afirmar sobre a carteira

A entrega do `s3` foi **desligada** (`summary_source: null`), não corrigida. O
parágrafo afirmava *"diversificada entre N categorias de ativos"* contando
`patrimonio.composicao` — baldes patrimoniais, um deles **por membro** — enquanto
a tabela da própria seção conta `investimentos.tabela_classes`. No corpus
dogfood: **3 vs 2**.

**Não é número errado, é conceito errado.** Trocar a fonte para a tabela não
resolve: com 2 classes a afirmação honesta é **concentrada**, não diversificada —
o que **inverte o sinal da frase**, de tranquilização para alerta. É o quinto caso
do viés otimista que o painel registrou na decisão nº 5.

O que esta lane decide (gatilho `financial-planner`):

- A partir de quantas classes uma carteira é diversificada? Concentração
  **dentro** da classe conta?
- A abertura da S3 deve falar de carteira (dado de `investimentos`) — falar de
  composição patrimonial ali seria conteúdo da S1 no lugar errado.
- Se a resposta honesta for "concentrada", a frase passa a ser achado, não
  descrição — e isso muda o que a seção comunica.

Observação lateral: um dos baldes de `patrimonio.composicao` chama-se
`Investimentos <nome de pessoa>`. Se esse rótulo chegar a texto renderizado, é
nome próprio no relatório — a classe que a [[A40.l4]] fechou. Confirmado que o
snapshot git-tracked não carrega dado de família.

> **Medição de 2026-08-11 (da [[A40.l43]]) — o desligamento do `s3` não tinha
> fechado a classe.** `carteira_diversificacao_frase` /
> `categorias_ativos_sufixo` tinham **3 call sites**, e desligar o destino do `s3`
> deixou vivo o que de fato chegava ao leitor:
>
> | call site | estado antes de 2026-08-11 |
> | --- | --- |
> | `summaries_narrator.py` (`s3`) | desligado por esta lane (`summary_source: null`) |
> | `charts_narrator.py` (`patrimonio_doughnut.context`) | inerte — a S1 usa `getConclusion` derivado (deferimento [[ADR-356]] §D5) |
> | `perfil_familia_narrator.py` (`right`) | **ENTREGUE**, no card logo abaixo do hero |
>
> A l38 removeu a chave `perfil_familia.right` inteira, então a frase morre **por
> consequência** e o total de publicadores entregues vai a **zero**. A l38 não
> introduziu afirmação substituta sobre diversificação/concentração: a política
> continua sendo desta lane, exatamente como as perguntas acima a formulam.
>
> **O que isso muda para esta lane:** o eixo "corrigir ou desligar o `s3`" perdeu
> urgência de contenção — nada afirma mais diversificação ao usuário — e virou a
> pergunta de produto pura ("o que a S3 deve afirmar sobre a carteira?"). Se a
> resposta for "nada", `carteira_diversificacao_frase` fica **órfã inteira** e o
> destino é a [[A40.l14]] (remoção de helper sem consumidor).

## Gate de shipping (herdado do co-design — não flexibilizar)

**Os três co-changes entram no MESMO PR que a troca do KPI.** Se não couberem, o
KPI **fica em `total_pontuais` com rótulo impresso** — estado atual pós-[[A40.l3]].
Card coerente-e-menos-acionável > card incoerente.

## Critério de aceite

- KPI de pontuais e equivalente lidos da janela, **com rótulo impresso** da
  janela; acumulado full permanece no card, rotulado, em superfície própria.
- Ritmo mensal (`pontual_mensal`) exibido ao lado do total da janela.
- Prosa do E5 declara as duas janelas, em formato monetário pt-BR.
- ~~Álgebra da folga reproduzível a partir de `receita_rec_mensal`, `despesa_mensal_media`
  e `pontual_mensal`~~ — **vencido em 2026-08-29**: a identidade vigente é
  `folga_mensal = receita_recorrente_mensal − despesa_consumo_mensal` ([[ADR-422]] D1), já
  gateada por `test_folga_mensal_nao_soma_pontual_realizado`. Escrever o teste antigo
  **reprovaria** nesse gate. O que sobra aqui é a reprodutibilidade do
  `equivalente_meses_poupanca` a partir do par (pontuais da janela, folga) exibido no card.
- Invariante do seletor mantido: `resolveConsumoBases` continua a **nunca** emitir
  par (valor, rótulo) de blocos diferentes — hoje o rótulo histórico é constante
  por construção; com dois pares ele volta a ser derivável e precisa de teste
  dedicado (payload sem `total_pontuais_janela` ⇒ valor full **e** rótulo full).
- Rótulo é **texto impresso**, verificado no PDF com extração de texto
  ([[ADR-306]] §Emenda A40.l3: tooltip não conta).
- **Donut:** o percentual da conclusão e a proporção **desenhada** citam a mesma
  base, com rótulo — hoje 43% impresso sobre uma fatia de 50,0% (ver §Escopo
  herdado). Se as bases forem mantidas distintas de propósito, cada número traz a
  sua, com substantivos que não colidam.
- **`ReceitaDespesaMensalChart`:** nenhum texto do card mensaliza sem rótulo, e S2
  não emite taxa de poupança própria (a canônica é a do hero). Medir os dois ramos
  — com e **sem** `despesa_datasets`.
- **Guarda:** `CARDS_DA_L15` removido de `janelaCanonica.contract.test.tsx` e de
  `janela-canonica.@critical.spec.ts`, devolvendo os dois cards à varredura de
  seção. Sem isso a lane fecha com a guarda cega justamente nos cards que ela
  tocou.

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

## Cancelamento por absorção — 2026-08-30

`cancelled`, não `shipped`: nada aqui foi entregue **por esta lane**. Três das quatro
premissas morreram e a quarta mudou de dono.

| item original | desfecho |
| --- | --- |
| KPI de pontuais na base da janela | → [[A40.l98]] (base + política única) |
| co-change 1 `pontual_mensal` | → [[A40.l98]], mas **fora do primeiro lote** ([[ADR-425]] D3) |
| co-change 2 `equivalente_meses_aporte_janela` | ✅ **entregue** no #1828 sob outro nome e outro denominador; o `aporte_mensal` que ele propunha foi **rejeitado por medição** ([[ADR-422]] D3) |
| co-change 3 prosa das duas janelas | ✅ **entregue** no #1828 |
| `teto_sugerido` | **extinto** do contrato ([[ADR-422]] D2) |
| texto dos dois cards de S2 | → [[A40.l102]] |

Manter aberta criaria **duas fontes sobre o mesmo card** — que é o defeito que esta lane
existia para consertar.

> ### ⚠️ Obrigação transferida — [[A40.l102]]
>
> Esta lane é dona do `CARDS_DA_L15`, que exclui nominalmente dois cards de
> `frontend/tests/components/report/janelaCanonica.contract.test.tsx` e de
> `frontend/tests/e2e/reports/janela-canonica.@critical.spec.ts`.
>
> **Cancelar sem remover as exclusões deixa a guarda cega para sempre**, e o assert de
> "exclusão não é vácuo" fica **verde depois** — ninguém é avisado. A remoção é critério
> de aceite da [[A40.l102]], escrito lá explicitamente.
