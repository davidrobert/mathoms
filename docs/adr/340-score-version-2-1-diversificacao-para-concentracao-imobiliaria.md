---
id: ADR-340
type: adr
title: "score_version 2.1 — componente de diversificação vira concentração imobiliária invertida (FIN-05)"
status: Decidido
phase: dogfood-c11-fin05
date: "2026-07-15"
decided_at: "2026-07-16"
amended_at: ["2026-07-16", "2026-08-29", "2026-10-08", "2026-10-09"]
relates_to:
  - "[[ADR-145]]"
  - "[[ADR-235]]"
  - "[[ADR-328]]"
  - "[[ADR-420]]"
  - "[[ADR-217]]"
  - "[[ADR-177]]"
  - "[[ADR-145]]"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/report
  - area/methodology
---

# ADR-340 — `score_version 2.1`: diversificação → concentração imobiliária invertida

> **Emenda 2026-10-09 (A40.l124 §Deferimento 6 · co-design `financial-planner` +
> `prompt-engineer`):** a RL-7 passa a ter **uma régua**, a do validador e do ponto urgente
> determinístico: acima de 50% o parecer escreve **"Média"**, nunca abaixo; acima de 75%,
> **"Alta"** — "Crítica" só com reserva abaixo da meta ou dívida cara. **Supera** a frase da
> §Emenda 2026-07-16 *"~60% é 'Alta'"*, escrita antes de a máquina ter rótulo na faixa. Nenhum
> limiar se move. Ver [§Emenda](#emenda--uma-régua-para-a-severidade-da-rl-7-2026-10-09).

> **Emenda 2026-10-08 ([[A40.l92]] · co-design `financial-planner`):** a meta *"abaixo de
> 50%"* lê-se **até 50%** — o limiar é o último valor conforme e o alerta dispara em `> 50`,
> como sempre disparou no agregador, na RL-7 e no `RiskTrigger`. A prosa "abaixo de" é a
> origem provável do `<` que o catálogo de KPI publicava. Nenhum número desta nota muda. Ver
> [§Emenda](#emenda--o-limiar-é-o-último-valor-conforme-2026-10-08).

> **Emenda 2026-08-29 (retratação de fato · [[A40.l95]] · `RR6-02` da rodada U2):** a frase
> *"a métrica de concentração considera **só cat_2 (imóveis de renda)**"* na §Decisão é **falsa** —
> a [[ADR-145]] §2 define cat_2 como geradores **+** não-geradores, nomeando `nu_proprietario`.
> Da trava do co-design *"numerador = cat_2 completo (imóvel vago/especulação é ainda mais
> ilíquido)"*, a metade **`especulacao` fica ratificada**; a metade **"cat_2 completo" está em
> revisão** pela [[ADR-420]] (`Proposto`), que decide o numerador por **rebalanceabilidade**.
> Ver [§Emenda de retratação](#emenda--retratação-de-fato-e-metade-da-trava-2026-08-29).
> **Nada mais desta nota muda:** os thresholds, `invertido`/`range`/peso, o rename do
> `nome_display`, o `SCORE_VERSION 2.1` e a base = carteira produtiva seguem governando.

> **Emenda 2026-07-16 (Onda R3.1 · co-design `financial-planner`):** as superfícies de
> **risco** (parecer + alerta do card) que ainda não citavam o SSOT foram repontadas —
> ver [§Emenda](#emenda--superfícies-de-risco-repontadas-ao-ssot-2026-07-16). Severidade em
> ~60% é **"Alta", não "Crítica"** (reservada a ≥75%, zona RL-7); meta **abaixo de 50% da
> carteira produtiva** (não "≤40%"), direcional via aporte. `investimentos.tabela_classes`
> é **composição** (base total investido), grandeza distinta do risco de iliquidez (base
> carteira) — a narrativa de risco cita sempre `ratios.concentracao_imobiliaria`.

> Item **FIN-05** (cluster C1 do dogfood). Sucessora de [[ADR-328]] (`score_version 2.0`,
> plateau da cobertura). Co-design `financial-planner` + `data-engineer` (2026-07-15/16).
> **Decidido (`score_version 2.1`)** — este PR implementa C11-Fase2 (campo canônico
> `ratios.concentracao_imobiliaria`) **e** FIN-05 (score) juntos, base carteira.
>
> **Decisões travadas no co-design da base (2026-07-16):** denominador = **carteira
> produtiva** (`investivel_financeiro + cat_2`, FIXA — o `data-engineer` provou que
> líquido é instável >100% e bruto reintroduz a perversão da residência); numerador =
> **cat_2 completo** (imóvel vago/especulação é ainda mais ilíquido); thresholds
> recalibrados (âncora real 5@5.com = **60%**): alerta 50, `spread_critico` co-threshold
> 45, **RL-7 hard-block 75**, piso da nota **85**. Campo canônico em `ratios.` (sempre
> presente; `real_estate.concentracao_pct` vira alias). SSOT de fórmula:
> `compute_concentracao_imobiliaria_pct`.
>
> **Follow-up (débito documentado):** o fixture sintético do golden
> (`tests/fixtures/pipeline_golden/dogfood/`) tem residência=veículos=0 → carteira≡bruto
> nele (não distingue as bases). A exclusão residência/veículos é verificada pelo teste
> do helper (`test_concentracao_imobiliaria::test_residencia_e_veiculos_fora_do_denominador`);
> enriquecer o fixture com casa+carro (pra o `golden_diff` distinguir carteira de bruto)
> fica como follow-up de representatividade.

## Contexto

A componente `diversificacao` do score (peso 1.0, o menor) é um **proxy invertido** —
sob os padrões consagrados de planejamento patrimonial brasileiro, premia o **oposto**
de diversificação. Diagnóstico (`financial-planner` 2026-07-15, sobre
`financial_score_calculator._observed_values`):

1. **Conta consumo ilíquido como diversificação.** `num_cats = sum(1 for c in composicao if valor > 0)`
   sobre 6 buckets de origem inclui **Residência** e **Veículos** — família com casa
   própria + 1 carro ganha **+2 buckets** sem diversificar nada, contra o princípio de
   que ativos ilíquidos/de consumo não são posição de carteira nem geram renda passiva
   (a própria métrica canônica de concentração exclui imóveis — FORMULAS.md §concentração).

2. **Double-count por estado civil (bug de tenancy).** `Investimentos Titular` +
   `Investimentos Cônjuge` são a **mesma carteira partida em 2 CPFs**: um casal ganha
   +1 bucket sobre um solteiro pela **mesma alocação**. Com `range_max=6`, o solteiro
   (bucket cônjuge sempre 0) tem teto estrutural de 5 → **nunca tira 10**, contradizendo
   workspace=família.

3. **Inverte a verdade.** Um investidor disciplinado (aluga, sem carro, 100% em
   carteira financeira bem distribuída por classes) pontua **baixo**; uma família com
   casa + 2 carros + 1 poupança pontua **alto**.

**Drift doc↔código não-detectado** (sintoma de output nunca escrutinado): o
`scoring.json._metodologia` diz "buckets com **≥5% do bruto**" e lista **7**; o código
faz **`> 0`, sem limiar**, sobre **6** buckets. O próprio `scoring.json` já confessa
o problema (rótulo diz "NÃO confundir com diversificação de carteira").

## Decisão

**Aposentar a contagem de buckets de origem. Reancorar a componente em
`ratios.concentracao_imobiliaria` (campo canônico do C11-Fase2), invertido.** Isso
reconcilia FIN-05 com C11 (como o plano pede) e corrige os 3 defeitos de graça — a
métrica de concentração considera **só cat_2** (imóveis de renda), então residência,
veículos e o split de cônjuge **saem naturalmente**.

- Componente **lê** `ratios.concentracao_imobiliaria` (SSOT do C11-Fase2 — **não**
  re-derivar no score calculator).
- `invertido: true`, `range_min: 0`, `range_max: 60`: concentração 0% → nota 10;
  ≥60% → nota 0, linear. Peso 1.0 mantido.
- `nome_display`: "Diversificação Patrimonial (origem)" → "Concentração Imobiliária"
  (semântica muda; copy do card = escopo `product-designer`).
- `SCORE_VERSION → "2.1"` ([[ADR-217]] §D3 — cada versão = fórmula completa; 2 bumps
  após 2.0, custo aceito — o "1 bump" da onda era otimização anti-thrashing).

## Decisões de domínio a travar no co-design (antes do PR)

1. **Piso da nota (`range_max` da inversão): 40% vs 60%.** O alerta binário
   `concentracao_alta` dispara em **40%** (limiar consagrado ≤40% em classe ilíquida) e **continua** como
   flag separada. Mas zerar a *nota* em 40% é duro p/ o ICP-BR (FORMULAS.md admite
   "50%+ em imóveis é norma cultural", range 30–60). **Recomendado: warning em 40%,
   piso da nota em 60%.**
2. **Base do denominador** (líquido/bruto/carteira) — a componente herda a que o
   **C11-Fase2 escolher** (item P2 aberto lá: 63,4% carteira vs 67,2% bruto).

## Gate de sequenciamento (bloqueante)

**2.1 anda DEPOIS/JUNTO do C11-Fase2, nunca antes.** `ratios.concentracao_imobiliaria`
está sendo **construído** pelo C11-Fase2 e sua base ainda está em reconciliação.
Shipar 2.1 antes = score consome campo instável. Esta ADR fica `Proposto` até o
sign-off do C11-Fase2 travar a base; então flippa `Decidido` no PR de 2.1.

## Alternativas consideradas

- **(a) Só excluir residência/veículos do count.** Rejeitada: sobram 4 buckets, 2
  ainda são o split de cônjuge — continua contando origem, não risco; mantém o bug
  de tenancy. Remendo numa métrica mal-especificada.
- **`desvio_max_pct` (diversificação de carteira real, por classe de ativo).** Deferida p/ 3.0/componente
  nova: depende de `alocacao_alvo.v2` setada — **não universal** no ICP. `concentracao_imobiliaria`
  é universal p/ famílias com imóveis.
- **Non-issue (não mexer).** Rejeitada: a componente é direcionalmente perversa e roda
  em toda família; peso 1.0 limita o dano, mas o sinal está invertido.

## Consequências

- **NÃO é flat (ao contrário do 2.0).** Família com alta concentração imobiliária (a
  dogfood ~67% bruto) **cai** — nota da componente ~10→~0 = **~1,0 ponto no score final**
  (peso 1.0/8.0), acima do limiar 0,5 do critério [[ADR-328]]. É a correção *intencional*;
  precisa aterrissar com copy no card + parecer (número ↔ narrativa concordam).
- **Exige `golden_diff` per-família** (como FP-02, e importa mais aqui — não é flat):
  cada família com delta >0,5 rastreada, manifesto 1×.
- **Rippla rename**: `_DIMENSION_LABELS`, `breakdown.dimensao`, `_format_top_drivers`,
  chart-context, referência no parecer — coordenar `product-designer` (label/copy).

## Critério de aceite (4 lentes)

- **Completude:** investidor sem imóvel de renda deixa de ser punido; card/score/parecer
  concordam na narrativa de concentração.
- **Corretude:** nota lê `concentracao_imobiliaria` invertido; residência/veículos/split
  de cônjuge fora do cálculo (herdado do C11).
- **Consistência:** base do denominador == a do C11-Fase2; flag `concentracao_alta` (40%)
  separada do piso da nota (60%).
- **Precisão:** `golden_diff` per-família 1×; `score_version` bumpado 2.0→2.1.

## Emenda — superfícies de risco repontadas ao SSOT (2026-07-16)

A lane C11/FIN-05 criou o SSOT `ratios.concentracao_imobiliaria` (base carteira) e o
propagou a card, score e RL-7, mas **duas superfícies de risco ficaram fora** (dogfood
revisitado 2026-07-16, cluster CTO-01/FP-02/PE-05/PD-03):

1. **Alerta do card** (`real_estate_metrics_aggregator.compute_alertas`) dizia "…% **do
   patrimônio**" enquanto o KPI ao lado já dizia "…% da carteira produtiva" —
   auto-contradição no mesmo card. **Corrigido (R3.1):** "da carteira produtiva" +
   percentual em pt-BR (vírgula), alinhado a `scoring.json` e `FORMULAS.md §216`.
2. **Parecer (LLM)** cita `investimentos.tabela_classes[imóveis].pct` (~63%, base **total
   investido**, que inclui imóveis como uma classe) e o publica como risco "Crítica" com
   meta "≤40%". **A repontar (R3.3):** o hint do prompt deve ancorar o risco em
   `ratios.concentracao_imobiliaria` (SSOT); `tabela_classes` é **composição**, não risco.

**Decisões de domínio travadas no co-design (`financial-planner`):**

- **Severidade.** Em ~60% (entre alerta 50 e hard-block 75) a concentração é **"Alta"**,
  não "Crítica" — "Crítica" fica reservada a ≥75% (zona RL-7). A linguagem do parecer não
  pode descalar em relação aos tiers da máquina.
- **Meta.** **Abaixo de 50% da carteira produtiva**, direcional via **aporte**
  (rebalanceamento), sem exigir liquidação de imóvel. O "≤40%" era o limiar pré-ADR-340.
- **`tabela_classes` × concentração de risco.** São computadas em substratos de agregação
  distintos (`InvestimentosClassesAnalyzer` sobre `bens_por_membro` vs
  `PatrimonioCalculator` cat_2) e podem divergir alguns pp. Para a Onda R3 a decisão é
  **rotular as duas grandezas distintas** e fazer o **risco** citar o SSOT.

**Débito documentado (follow-up):** unificar a **fonte de valuation** de cat_2 entre os dois
substratos (para o row de imóveis de `tabela_classes` reconciliar ao SSOT ao centavo, não só
por rótulo) exige co-design `data-engineer`/`senior-cto` — fica como follow-up de precisão,
fora do escopo da R3.

**Docs reconciliados:** `config/schemas/e5_analysis.schema.json` (`real_estate.concentracao_pct`
description: base carteira, alerta >50). `FORMULAS.md §152/§182/§216` já estavam corretos.

## Emenda — retratação de fato, e metade da trava (2026-08-29)

Medido no run `79a61e33` (dogfood, rodada U2), identidades fechando ao centavo:
`cat_2 = imoveis_geradores + imoveis_nao_geradores`, e `investivel_efetivo =
investivel_financeiro + imoveis_geradores`. Logo o denominador desta métrica é
`investivel_efetivo + imoveis_nao_geradores` — agregado que **nenhuma outra superfície
publica** —, e o numerador soma um imóvel que `real_estate.excluded_properties` exclui do
cap rate com o motivo literal *"não gera caixa nem está disponível para venda livre"*.
Publicado 50,62%; sem ele, 49,08%, contra limiar 50,0 com operador `<`: **o veredito inverte**.

**O que se retrata.** A §Decisão afirma que *"a métrica de concentração considera **só cat_2**
(imóveis de renda), então residência, veículos e o split de cônjuge saem naturalmente"*. A
primeira metade é falsa por definição da [[ADR-145]] §2. A segunda vale **apenas em workspace
onde alguém rotulou**: `split_imoveis_with_overrides` só reconhece cat_1 com override
**explícito** `residencia_principal`, e no regime default a residência principal cai em cat_2.
O golden do repo é a demonstração — `imoveis_geradores = 0` e cat_2 inteiro em não-geradores.

**O que continua valendo, e por que registrar isso importa.** `especulacao` no numerador é
**ratificado**, por duas rotas independentes: metodologicamente é alocação escolhida com saída
possível (o custo de renda zero é exatamente o que o KPI deve doer), e estruturalmente o motor
já a trata como investimento — `INVESTMENT_CLASSIFICATIONS` a contém e `_CLASSIFICATIONS_GERADORAS`
não. Sem esta linha, o próximo leitor supõe que a trava caiu inteira e reabre `especulacao`.

**O que a decisão desta nota não sofre.** A escolha do numerador não era carga do fato falso: a
trava se justifica por **iliquidez** e o saneamento do FIN-05 se justifica por cat_1/split de
cônjuge — nenhuma das duas conclusões depende de "de renda". A [[ADR-420]] reabre a cláusula por
um eixo que **esta nota nunca examinou** (rebalanceabilidade), não por erro de raciocínio dela.

**Por que emenda e não supersedure.** Sem a cláusula do numerador esta nota ainda governa oito
decisões vivas. Supersedure aqui é file-level e diria "pule isto" sobre todas. A regra de fronteira
está escrita na [[ADR-420]] §Alternativas (D).

**O limiar 50 não se move** — a procedência dele é doutrinária (a banda 40–60 em que as
referências do produto divergem legitimamente entre si, estabilidade contra diversificação),
não função do numerador. O que precisa de reconciliação é o rationale de
`FORMULAS.md` §219, que sustenta o 50 por um argumento de magnitude de base.

## Emenda — o limiar é o último valor conforme (2026-10-08)

A §Emenda de 2026-07-16 escreveu a meta como *"abaixo de 50% da carteira produtiva"*, e o
catálogo de KPI publicou `operador: "<"`. Em 50,00 exato o catálogo afirmava violação
enquanto o agregador (`> 50`), a RL-7 e o `RiskTrigger` (`<=`) diziam conforme — e com o
veredito que a [[A40.l92]] publica na tabela do parecer, a superfície contradiria o canal de
risco sobre o mesmo payload. A doutrina é a da [[ADR-399]] §Emenda 2026-10-08: o limiar é o
último valor conforme, nas duas direções. A meta lê-se **até 50%**; o limiar 50, o
`spread_critico` 45 e a RL-7 em 75 não se movem.

## Emenda — uma régua para a severidade da RL-7 (2026-10-09)

Origem: A40.l124 §Deferimento 6. Medido em `main` `00fbd15e`, quatro lugares davam a
severidade da concentração sobre o mesmo `ratios.concentracao_imobiliaria`:

| lugar | o que dizia |
|---|---|
| REGRA 14 do system prompt (RL7) | `> 60%` ⇒ "Alta"; "entre 40% e 60%, Média basta"; alerta estruturado ⇒ "Alta" |
| validador (`_severidade_exigida_concentracao`) | piso "Média" acima de 50, piso "Alta" acima de 75 |
| hint "Severidade da concentração" do manifest | "≥50% é ALTA"; "em ~60% escreva 'Alta'" |
| ponto urgente determinístico ([[A40.l90]]) | "Média" em (50,75], "Alta" acima |

O #981 (C11-Fase2) trasladou o validador para a base carteira e não tocou a REGRA 14,
contra o changelog do próprio módulo do prompt; a hint veio da §Emenda 2026-07-16 desta nota.

**Decisão (`financial-planner`):**

1. **Faixa (50,75]: "Média", nunca abaixo** — alvo e piso coincidem. Com o uso pessoal fora
   do numerador ([[ADR-420]]), a divergência legítima na faixa é entre aluguel como renda
   passiva e diversificação por classe; a estabilidade da moradia só pesa onde o imóvel não tem
   classificação, e ali o número já é teto. Acima de 75 as três referências convergem.
2. **Acima de 75: "Alta"**, o topo da escala do ponto urgente. **"Crítica" só com agravante de
   liquidez que o E5 já sinaliza** — reserva abaixo da meta ou dívida cara: patrimônio ilíquido
   sem colchão é o caminho da perda (venda forçada, crédito caro). Na faixa, o agravante entra
   no risco de reserva ou de dívida, cujo remédio é mais rápido.
3. **A cláusula "alerta estruturado ⇒ Alta" sai do prompt** — devolvia o acoplamento a
   `real_estate.alertas` que o #981 tirou do validador (e o manifest nem projeta esse campo).
4. **Meta: até 50% da carteira produtiva, via aporte, sem exigir venda.** É o alvo que o
   catálogo publica ([[ADR-399]]); outro número na prosa contradiz a tabela do mesmo relatório.
   "Sem exigir" não é proibir: acima de 75 a venda gradual pode aparecer como alternativa,
   nunca como P0 e nunca com imóvel sem classificação.

**O que esta emenda supera.** A frase da §Emenda 2026-07-16 *"em ~60% (entre alerta 50 e
hard-block 75) a concentração é 'Alta'"*. Ela foi escrita quando a faixa não tinha rótulo
determinístico, e pôs o alvo um degrau acima do piso. Desde a [[A40.l90]] o ponto urgente
publica "Média" sobre o mesmo payload — e o princípio daquela emenda, *"a linguagem do parecer
não pode descalar em relação aos tiers da máquina"*, é exatamente o que agora aponta para
"Média". Dois rótulos para o mesmo fato custam mais que um degrau de nuance; a nuance perto de
75 vai na prosa, não no rótulo.

**Justificativa reancorada.** A "banda 40–60 em que as referências divergem" — na §Emenda
2026-08-29 desta nota, em [[ADR-420]] §D4 (que chama o 50 de "ponto médio" dela) e em
`FORMULAS.md` §219 — é a escala da RL7 1.4 **na base antiga**. Na base carteira a faixa de
divergência é (50,75], e o 50 é a **borda inferior** dela, não o ponto médio. Nenhum limiar se
move; corrige-se a leitura, que levava de volta a "Alta" em ~60%.

**O que se perde.** Com alvo igual ao piso, a margem vai a zero: "Baixa" na faixa vira
`conselho_vedado`. Por isso a REGRA 14 diz "nunca abaixo", e o tema do risco passa a cobrir o
argumento de iliquidez — `Liquidez` está fora dos temas da RL-7 e bloqueava com a severidade
certa.

**Onde a régua vive.** O validador é a fonte (`RL7_LIMIAR_EXIGE_MEDIA_PCT`,
`RL7_LIMIAR_EXIGE_ALTA_PCT`; predicado intocado, `RED_LINES_VERSION` fica). Declaram-na a
REGRA 14 (`PROMPT_VERSION` 2.6.0) e a hint (manifest 2.22.0); o ponto urgente já era pareado
por `test_degraus_pareados_com_a_red_line`. `tests/test_parecer_rl7_regua_unica.py` mede a
escada no predicado e cobra dos dois textos limiar, fronteira exclusiva e rótulo-piso, com um
inventário que reprova uma terceira cópia — 11 mutantes, 11 mortos.

**Medido — sonda LLM antes do merge** (pedida pelos dois especialistas, autorizada pelo dono;
US$ 7,77). Nove fixtures sintéticas do HOLDOUT com eixo imóvel × {59,97; 70; 75,01}%, temp 0,
com o ponto urgente real injetado em cada E5: RL-7 em **0/27**; risco no tema certo em
**27/27**; "Crítica" na faixa em **0/18**; meta "40%" em **0/27**. A severidade máxima no tema
bateu o alvo em **23/27** — os quatro desvios são "Alta" a 70%, um degrau acima: o validador
aceita, o ponto urgente contradiz. A 59,97 deu 9/9 "Média" nas mesmas fixtures, então o desvio
depende do nível, não da família. Uma geração caiu no fallback de infra (erro de conexão, custo
0) e disparou RL-7 sobre parecer vazio; repetida, saiu limpa. Quem acompanhar a taxa de RL-7
por `prompt_version` precisa separar esses fallbacks, ou a série mede a rede e não o prompt.

### Deferimento datado — calibração perto do degrau de 75 (2026-10-09)

**Dono:** `prompt-engineer` + `financial-planner`. O `prompt-engineer` atribui o desvio ao
texto da faixa ter só piso ("Média, nunca abaixo"): o modelo usa o espaço acima perto do
degrau seguinte, enquanto a faixa de cima, que tem teto explícito, acertou 9/9. A troca
candidata é "nunca abaixo" → "em toda a faixa". Ela **não foi sondada**: o dono preferiu
mergear o texto medido a pagar outra rodada. **Retomada:** o próximo bump que tocar a RL7 leva
a troca e re-sonda os níveis 70 e 75,01. Qualquer "Média" a 75,01 reprova o texto, porque ali
vira hard-block. Fica pendente também classificar os riscos secundários "Baixa" que apareceram
no tema em 7 das 27 gerações: se forem a mesma concentração com dois rótulos, é defeito de
coerência. O instrumento desta sonda não guardou títulos; o da próxima guarda.
