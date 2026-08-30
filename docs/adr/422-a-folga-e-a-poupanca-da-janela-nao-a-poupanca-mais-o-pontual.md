---
id: ADR-422
type: adr
title: "A folga é a poupança da janela, não a poupança mais o gasto pontual realizado"
status: Decidido
phase: A40
date: "2026-08-29"
amended_at: ["2026-08-30"]
relates_to:
  - "[[ADR-306]]"
  - "[[ADR-333]]"
  - "[[ADR-090]]"
  - "[[ADR-161]]"
supersedes: []
aliases: ["ADR 422", "folga mensal", "consumo consciente"]
tags:
  - type/adr
  - status/decidido
  - area/e5
  - area/dominio
  - sprint/a40
---

# ADR-422 — A folga é a poupança da janela

**Status:** Decidido (A40.l94 · #1828 `05561dc0`) • **Data:** 2026-08-29 • Co-design
`financial-planner` no **planejamento**. Emenda [[ADR-306]] §D6 no termo de
pontuais; consome a separação de [[ADR-333]].

## Contexto

`consumo_consciente.folga_mensal` era, literalmente:

```
pontual_mensal              = pontuais_janela / n_meses
despesas_recorrentes_mensal = despesa_mensal_media − pontual_mensal
folga_mensal                = receita_rec_mensal − despesas_recorrentes_mensal
teto_sugerido               = despesas_recorrentes_mensal × 1,15
```

que se reduz a **`folga_mensal ≡ poupança_mensal + pontual_mensal`**. O gasto
pontual **realizado** voltava ao numerador como sobra recuperável.

A consequência é que a mesma página publicava **dois** "quanto sobra" sobre o
**mesmo** denominador — `fluxo_caixa.janela_12m.receita_recorrente`, que é
idêntico a `equilibrio_cerbasi.componentes.base` — sem rótulo que os
distinguisse:

| superfície | número | valor no dogfood |
| --- | --- | --- |
| hero (`HeroKpiGrid`) | `ratios.taxa_poupanca_recorrente_pct` | **57,32%** |
| card S2 (`ConsumoConscienteCard`) | `consumo_consciente.folga_pct` | **76,70%** |

19,4 pp de divergência, e a diferença é **exatamente** `total_pontuais_janela`.
A ponte é identidade derivável, não coincidência do corpus:

```
folga_mensal − poupança_mensal ≡ (pontuais_janela − transferencia_patrimonial) / n_meses
```

Verificada em dois payloads: dogfood (`130.179,78 − 97.302,65 = 32.877,13 ==
394.525,39/12`, resíduo de R$ 0,01) e a fixture `pontuais-com-aporte`
(`15.000,00 − 14.250,00 = 750,00 == (21.000 − 12.000)/12`, resíduo zero).

**A soma fecha dos dois lados**, então nenhum invariante de conservação via o
defeito — é a classe *sum-preserving* que a rodada unificada existe para pegar,
e ela alcançou o usuário: **a maior das duas sobras é a que prescreve**
(`teto_sugerido` sai da mesma subtração, e o parecer ancora conselho de
contenção nela). Quem dimensiona aporte pela folga compromete, todo mês, a
provisão inteira dos gastos pontuais — e quebra o aporte no primeiro evento.

Origem: `RR6-01` ([[REPORT-REVIEWS-active]] §r6, rodada U2). Medição-de-conhecido
de `PV9-13`; o que é novo é a identidade fechada ao centavo.

### Por que [[ADR-306]] §D6 não basta

D6 decidiu a fórmula acima e chamou-a de *"folga mensal reconciliável"*. Ela
consertou uma **mistura de base** real (pontuais full-period ÷ denominador 12m) e
**não se pronunciou** sobre duas perguntas distintas: se somar o pontual de volta
é certo, e se a base de pontuais é consumo. A reconciliação que D6 pediu foi
implementada como teste — e o teste reconstruía a fórmula defeituosa, sobre
fixtures com `total_pontuais_janela == 0`: **teste e código compartilhavam a
crença errada, e o termo em disputa nunca era exercitado**.

## Decisão

**D1 — A folga é a poupança da janela.**

```
folga_mensal = receita_recorrente_mensal_12m − despesa_consumo_mensal_12m
```

A base é `despesa_consumo` ([[ADR-333]]), não a despesa bruta: com a bruta, o
aporte da janela reintroduz a divergência por outro termo (`− transferencia/n`),
e a folga pode ficar **abaixo** da poupança. Com D1, o invariante
`|folga_mensal − taxa_poupança × receita_recorrente| ≤ ε` vale **por construção**.

Rejeitada a alternativa "manter os dois com rótulo impresso", que era a
ferramenta certa para o problema errado: rótulo resolve **ambiguidade de
escopo** (foi o que a [[A40.l3]] fez, e funcionou). Aqui os dois números têm a
mesma base temporal e o mesmo denominador — o conflito é de **veredito**, e
rotular dois vereditos incompatíveis publica os dois.

Rejeitada também a variante "só o pontual discricionário volta": `nao_identificado`
é a categoria-lixo default, e ela cairia em "discricionário" — a regra
classificaria como cortável exatamente o que não é consumo (57,5% da janela do
dogfood).

**D2 — `teto_sugerido` sai do contrato.** Três defeitos independentes: (i)
prescrevia R$ 45.519,51 contra despesa real de R$ 72.459,30/mês — 37% abaixo do
que a família gasta, e teto inalcançável é o mecanismo nº 1 de abandono de
orçamento na literatura de referência do domínio; (ii) o rótulo dizia "consumo" e o número era
`recorrente × 1,15`, incluindo moradia, impostos e folha PJ; (iii) o
multiplicador `1,15` não tem origem declarada em lugar nenhum. Rebasá-lo para
consumo produziria `72.459,30 × 1,15 = 83.328,20`, isto é *"gaste até 15% a mais
do que já gasta"* — permissivo a ponto de ser vazio. Um número que só pode ser
inalcançável ou vazio não é teto. Teto de verdade é escopo do
`OrcamentoProspectivoCard`, que já é a superfície de tetos; duplicá-lo repetiria
esta doença.

> ⚠️ **Emendada em 2026-08-30 ([[A40.l101]]).** A fórmula abaixo fica intacta; o que
> faltava era o **domínio de definição**. Fora dele o campo publica `null`, nunca `0,0`.
> Ver §Emenda 2026-08-30 no fim desta nota.

**D3 — `equivalente_meses_aporte` → `equivalente_meses_poupanca`.**

```
equivalente_meses_poupanca = total_pontuais_janela ÷ folga_mensal
```

O anterior media o estoque **full-period** contra o aporte **declarado**
(`goals.aportes.meta_aporte_mensal`): duas bases, e um denominador **editável
pelo usuário** — um número de diagnóstico que se move sem que nada tenha
acontecido no mundo não é auditável. No dogfood o fator de inflação era **4,9×**
(46,1 meses onde a poupança realizada sustenta 4,1), e o próprio aporte de
R$ 190.000 contava como 9,5 "meses de aporte" dentro do numerador.

Numerador e denominador saem da **mesma** janela — trocar só o denominador
recriaria a mistura de base que a [[ADR-306]] existe para matar. Atribuição do
delta: só denominador = 9,5; só numerador = 19,7; **ambos = 4,1**. A comparação
com a meta declarada pertence ao plano de ação, onde meta é o objeto, não ao card
de diagnóstico.

**D4 — A prosa do E5 declara as duas janelas.** `analise` era a única superfície
que citava um total **nu**.

## Consequências

- `folga_pct == taxa_poupanca_recorrente` por construção. O par deixa de ser dois
  vereditos e passa a ser um, medido em duas unidades.
- **Nenhum consumidor de score muda**: o score já lia
  `ratios.taxa_poupanca_recorrente_pct` — o número **conservador**. Quem lia o
  inflado era o card e o parecer, isto é, as superfícies que **prescrevem**.
- `manifest_version` do parecer sobe (2.7.0 → 2.8.0) e **cobra a frota**: a
  `folga_mensal` mudou de VALOR sem mudar de nome, e o cache tem TTL de 7 dias.
- No dogfood: folga R$ 130.179,78 → R$ 97.302,65; `folga_pct` 76,70 → 57,32;
  equivalente 46,1 → 4,1 meses.

### O que esta ADR NÃO conserta — e por que isso não muda o sinal

A base de `total_pontuais` continua contaminada (`LC6-05`): no dogfood, 57,5% da
janela é movimentação patrimonial — uma saída de R$ 194.886,65 nomeando outro
banco do próprio titular e R$ 32.000 em conversões BRL→USD, todas caídas em
`nao_identificado` porque o `InternalTransferDetector` não as pegou. Há **três**
definições disjuntas de "gasto pontual" em produção:

| produtor | exclui |
| --- | --- |
| `FluxoEnricherConfig.transfer_categories` ([[ADR-333]]) | `aporte_investimento` |
| `consumo_pontuais.py::_is_pontual` (a **lista** do card) | transferência interna detectada + 3 categorias |
| `ConsumoConscienteCalculator._collect_candidates` (o **KPI**) | nenhum dos dois |

Sob a fórmula anterior essa contaminação era **fatal**, porque entrava na prescrição
**determinística**. Sob D1 ela não alcança mais folga nem teto — o teto não existe mais.
Por isso a ordem é esta e não a inversa, e por isso o conserto da base é lane própria, com
delta atribuível a uma causa só.

> **Precisão 2026-08-30 (closeout).** Uma versão anterior deste parágrafo dizia que a
> contaminação passa a degradar *"apenas números descritivos"*. É largo demais: o
> **parecer** segue recebendo `total_pontuais` e `total_pontuais_janela` no exec context
> (`parecer_planejador.yaml`) e emite com eles o risco *"gastos pontuais elevados sem
> política de consumo consciente formalizada"* — que **é** prescrição, ancorada 3× no
> campo contaminado. O que D1 garante é que nenhuma prescrição **determinística** a
> consome; a prescrição do LLM ainda consome. Dono: [[A40.l98]].

**Não** foi emitido campo novo para o ritmo do pontual (`pontual_mensal` — nome da
[[A40.l15]], que precede o `provisao_pontual_mensal` do co-design e prevalece por ser
o primeiro a nomear o mesmo campo): publicá-lo hoje seria imprimir um número cuja base é 57,5%
movimentação — ou, se emitido sem leitor, criar exatamente a classe
emissor-sem-leitor que a [[A40.l88]] gateia. Ele entra junto com a base limpa.

## Emenda 2026-08-30 — o equivalente tem domínio de definição, e fora dele publica `null` (A40.l101)

Origem: `RR7-02` ([[REPORT-REVIEWS-active]] §r7, rodada **U3**), triagem
`REGRESSÃO-DE-CONSERTO`.

**O defeito era uma guarda transplantada.** A D3 trocou o denominador e carregou junto o
`else 0.0` da fórmula anterior, sem revisá-lo. Sob o denominador antigo o guard era
inofensivo; sob o novo ele inverte o sinal do campo:

| denominador | domínio | o que `≤ 0` significa | `0.0` lê como |
| --- | --- | --- | --- |
| `meta_aporte_mensal` (pré-D3) | meta **declarada**, `≥ 0` | usuário não configurou meta | N/A benigno |
| `folga_mensal` (D3) | quantidade **medida**, `∈ ℝ` | a família não poupou nada | **o menor valor da régua no pior mundo** |

Medido fim-a-fim (`tests/fixtures/pipeline_golden/e3/folga-negativa-3_reconciled.json`):
folga `−R$ 4.500,00/mês`, `folga_pct −45,0`, `total_pontuais_janela R$ 30.000,00` ⇒ o campo
publicava **`0,0`** e a prosa do E5 **afirmava** *"equivalentes a 0.0 meses de poupança"* —
byte-idêntico ao mundo sem gasto pontual algum, e melhor que os `3,0` da família saudável.
O ramo `folga < 0` era **inteiramente cego**: mutante que devolvia `−99.0` só nele sobrevivia
à suíte inteira. `0,0` colapsava **três** mundos disjuntos, e o `?? "—"` do card nunca
disparava porque o produtor jamais emitia `None`.

**D3.a — o equivalente é `null` fora do domínio de definição.** A aritmética da D3 fica
**intacta**; declara-se onde ela é publicável. Forma canônica da [[ADR-394]] §D7
(`investimentos_cobertura.valor_publicavel`): *"`None` e não `0,0`: um zero publicado é uma
afirmação sobre o patrimônio da pessoa, e o sistema não a mediu"*. O par
`motivo_supressao: str | None` acompanha, na forma `<causa_slug>: <detalhe>`
(`folga_nao_positiva: …`), precedentes `alocacao_alvo_deviation` e
`supressao_por_atribuicao`. Contrato: `["number","null"]` + propriedade nova — **nullable, não
ausência**: a ausência de chave está reservada pela [[ADR-390]] §D2 para *versão de artefato*,
e omitir degradaria o `golden_diff` de `value_delta` para `removed`/`new`.

**D3.b — o denominador é a folga PUBLICADA.** Gatear por `round(folga, 2)` e dividir pela
folga crua publica um par que o leitor não recompõe (medido: folga crua `R$ 0,014` publicava
denominador `R$ 0,01` e razão `2.142.857,1`, contra `3.000.000,0` de quem refizesse a conta).

**D3.c — `folga_pct` cai pelo mesmo guard.** Não é campo vizinho por acaso: é o **mesmo**
transplante, no mesmo bloco, três linhas acima. Com receita recorrente nula e folga de
`−R$ 14.500,00`, ele publicava `0.0` e o card imprimia *"0% da receita"* — "empatou" para
quem queimou caixa. Passa a `null`. Consequência aritmética verificada: sempre que
`receita_recorrente ≤ 0` a folga também é `≤ 0`, então um único `motivo_supressao` cobre os
dois campos.

**D3.d — a prosa do E5 tem ramo próprio, e isso é requisito.** Com o campo suprimido,
`_build_analise` levantava `TypeError` no `:.1f` — o conserto ingênuo abortaria o stage. Mais
importante: sem o ramo, o `—` do card viraria **ausência nua**, que lê como *"não se aplica"*
— o modo de falha do `RR6-21`. A prosa passa a declarar o déficit. Pelo mesmo motivo o
manifest do parecer projeta `motivo_supressao` (`on_null: skip` apagaria a linha do
equivalente e a supressão viraria **silêncio** exatamente no pior mundo); `manifest_version`
sobe **2.8.0 → 2.9.0**.

### A pergunta que o campo responde é PROSPECTIVA

Decidido por eliminação, com o `financial-planner` (dono declarado da [[A40.l101]]): sob a
leitura **retrospectiva** — *"quantos meses de poupança este gasto consumiu"* — o denominador
correto é a poupança que existiria **sem** o gasto, `folga + P/n`. E `folga + P/n` é
**numericamente a `folga_mensal` pré-[[ADR-422]]**, ao centavo (R$ 130.179,78 no dogfood;
resíduo zero nas duas fixtures). Uma leitura cujo único denominador coerente é a grandeza que
esta ADR acabou de matar é a leitura errada. Sob a leitura **prospectiva** — conversão de
unidade à taxa de poupança **observada** — a fórmula da D3 fica de pé byte a byte.

Corolário: a chamada "inflação auto-referente" de **1,338×** medida no run da U3 (publica
4,05 onde o contrafactual daria 3,03, a `folga_pct` 57%) **não é defeito** — é a distância
entre duas perguntas diferentes. O resíduo real é de **numerador** (contaminação da base) e é
da [[A40.l98]].

### Alternativas rejeitadas

**Denominador contrafactual `folga + P∩C/n`** — rejeitado por medição, não por gosto. Além de
ser a folga pré-ADR-422 (acima), ele devolve à página um "segundo quanto sobra" como
**denominador implícito recuperável**: na fixture do repo, `21.000 ÷ 1,4 = R$ 15.000,00`
contra a folga publicada de `R$ 14.250,00` — 75,00% vs 71,25% da receita, a forma do `RR6-01`
em escala menor. Nenhum invariante existente o veria: a mutação passa `8 passed`. Daí o gate
novo `test_o_denominador_publicado_e_a_folga_publicada`, que vigia a **grandeza** e não o
campo.

**Piso de materialidade para fechar o polo** (suprimir também com `folga_pct` abaixo de ~1%)
— rejeitado por medição. (i) `config/scoring.json::thresholds_alertas` **não tem** piso de
taxa de poupança a reusar (`poupanca_referencia_pct: 25` e
`pontos_fortes_taxa_poupanca_min_pct: 30` são **alvos**), então o limiar seria inventado — a
mesma crítica que a **D2** desta ADR fez ao multiplicador `1,15`. (ii) O argumento de ruído
**não se sustenta**: a sensibilidade **relativa** é exatamente 1:1 em todo o domínio — a
`folga` de `R$ 90,00` e a de `R$ 0,01`, ambas movidas em +1%, movem o publicado em 0,99%.
(iii) O número suprimido seria **verdadeiro e acionável**: folga de `R$ 90,00/mês` contra
`R$ 30.000,00` de pontual dá `333 meses`, isto é *"irrecuperável ao seu ritmo atual"* — que é
o diagnóstico que a família precisa. Suprimi-lo teria o sinal trocado.

O que sobra do polo é **legibilidade**: `folga = R$ 0,01` publica `3.000.000,0` numa célula de
KPI. É problema de apresentação, não de correção, e fica **deferido com dono** na
[[A40.l101]] §Deferimento.

### Consequências

- `equivalente_meses_poupanca == 0.0` passa a significar **exatamente uma** coisa: nenhum
  gasto pontual relevante na janela. O dogfood está nesse mundo, então o snapshot de
  view-model **não muda de valor** — muda em **1 linha**, o `motivo_supressao: null`.
- **Forward-only.** `ReportPublication` pina o artefato original (`ondelete=RESTRICT` +
  `immutable_hash`) e nada é recomputado: relatório publicado antes do fix mantém o `0,0`.
  Reescrever artefato publicado seria o defeito maior ([[ADR-187]], mês fechado é imutável).
- A mudança **afrouxa** o contrato nos dois eixos (união de tipo + propriedade opcional sob
  `required: []`), logo é não-breaking: payload antigo segue validando e renderizando.
- **Rótulo pendente.** "Equiv. meses de poupança" e *"equivalentes a X meses de poupança"*
  leem **pretérito**, isto é, a leitura (b) que esta emenda rejeitou. O rótulo do card é da
  [[A40.l15]] e vai nomeado para lá; a prosa do ramo suprimido já não usa verbo de reposição.
