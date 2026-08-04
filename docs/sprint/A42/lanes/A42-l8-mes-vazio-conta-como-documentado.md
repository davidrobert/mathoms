---
id: A42.l8
type: lane
title: "Mês vazio por falha de extração conta como mês documentado"
sprint: A42
status: planned
priority: P1
branch_slug: a42-l8-mes-vazio-conta-como-documentado
adrs:
  - "[[ADR-306]]"
  - "[[ADR-345]]"
depends_on:
  - "[[A40.l15]]"
  - "[[A40.l11]]"
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p1
  - area/pipeline
---

# A42.l8 — `mes-vazio-conta-como-documentado` (PC11, RV4-04, RV4-05, RV4-26, RV4-28, RV4-46, RV4-55)

> **Origem:** [[PARSE-CERTIFY-active]] §r2 2026-08-04 — PC11 (Alto) ·
> [[PIPELINE-REVIEWS-active]] §r4 — RV4-04, RV4-05 (Alto, par de mesmo fix), RV4-26,
> RV4-28, RV4-46, RV4-55.

> **Depende de [[A40.l15]]** (dona do enricher de fluxo — mesmo arquivo) **e de
> [[A40.l11]]** (dona da resolução do vocabulário de confiança e do único consumidor do
> campo de confiança do view-model). A dependência da l11 foi acrescentada em 2026-08-04
> por objeção do `financial-planner`: a **declaração ao usuário** desta lane usa aquele
> campo, e ele hoje é a única chave top-level sem leitor. Ordem: a l11 cria o consumidor →
> esta lane acrescenta a segunda entrada. Se a l11 não vier antes, esta lane **emite a
> banda no payload e não tenta renderizar**. **Na promoção, re-ler a disposição das duas.**

> **Atenção — esta lane invalida uma premissa de lane já shipada.** A [[A40.l3]]
> tratou *qual* janela cada número lê e o *rótulo* impresso; **não** a validade da
> contagem de meses. Se a contagem inclui mês vazio por falha de extração, o rótulo
> "12 meses documentados" está correto na forma e falso no conteúdo. Não é duplicação
> da l3 — é o falso-verde que ela deixou em pé.

## Problema

Quatro causas independentes corrompem o **divisor** de toda média mensal, e o
resultado composto é que o denominador é maior do que os meses realmente observados:

1. **Período com zero transações por falha de extração entra como mês documentado.**
   Dois períodos consecutivos e recentes de uma conta reativada extraem zero
   lançamentos com cerca de vinte candidatas cada, e **escalam corretamente**. Mas em
   modo sem LLM — que é o default do tier gratuito — entram na janela como "mês
   documentado com zero movimento". Isso viola a [[ADR-306]] **de fato sem violar de
   forma**: é o pior dos três estados possíveis, **ausente sem aviso, fantasiado de
   observação**. Escalar é o comportamento correto no E2, mas escalação **não é segura
   quando não há LLM para atender**.
2. **A janela não tem teto na data de análise:** fatia os últimos doze e divide pelo
   tamanho, sobre série sem teto ⇒ slots de meses **não decorridos** entram no divisor.
3. **Universo de meses é a união das pernas de receita e despesa com preenchimento de
   zero** ⇒ mês documentado só numa perna entra no divisor da outra como zero. Causa
   independente da anterior, mesmo fix.
4. **Duas semânticas de lacuna no mesmo divisor:** mês sem nenhuma transação é
   elidido, mês com transação de uma só perna é mantido.

Somam-se dois defeitos de config sem leitor na mesma superfície: o custo essencial lê
apenas uma das duas listas declaradas (deixando um balde inteiro fora do essencial
contra a regra escrita), e há **quatro listas paralelas** de categoria que divergem,
com aporte classificado como transferência patrimonial num bloco e gasto
discricionário noutro.

E um sintoma que é consequência dos itens 2–4, não causa própria (RV4-55): **dois
números diferentes carregam o mesmo rótulo** de cobertura de despesas em meses no mesmo
payload, com fator de cerca de 2× entre eles — porque calculam sobre bases distintas.
Deve **cair junto** com o fix de denominador; se não cair, é sinal de que ainda há uma
terceira base não localizada, e aí vira item próprio.

## Decisão

1. **Mês cuja extração determinística produziu zero lançamentos não conta como mês
   documentado.** Reflete no número de meses da janela; a visão por conta imprime
   "não lido", **nunca zero monetário**. É decisão de **agregação**, não de UI — e é o
   ponto que o §r2 classificou como bloqueante para o tier gratuito.
2. **Teto na data de análise** e **universo de meses observados**, não união com
   preenchimento de zero. Semântica única de lacuna.
3. **Fonte única de categoria** para as quatro listas. **Cuidado com erro de segunda
   ordem:** o fix ingênuo (unificar na lista mais permissiva) muda o percentual
   publicado — declarar o sinal do delta.
4. **Ler as duas listas** declaradas no custo essencial, conforme a regra escrita.

### Piso de publicação — a decisão que faltava (`financial-planner`, 2026-08-04)

Excluir mês **encurta a janela**, e isso não era decisão, era consequência: trocar "12
meses, dois falsos-zero" por "10 honestos" muda o divisor de todo número mensalizado. A
régua abaixo é a decisão de domínio, derivada de dois critérios — *o divisor entra no
número?* e *a família se compromete contra ele?*

| Classe | Exemplos | Piso |
|---|---|---|
| **C1 · razão de mesma janela** (divisor cancela) | taxa de poupança recorrente, percentuais de equilíbrio, share por categoria | **3** |
| **C2 · nível descritivo** | despesa mensal média, receita recorrente, autonomia em meses | **6** |
| **C3 · nível dimensionante** (a família financia ou se compromete) | custo essencial → alvo de reserva, cobertura em meses, folga/capacidade de aporte, projeções | **6**, com correção conservadora enquanto a janela não fecha |

Bandas, **reusando o vocabulário de confiança que já existe** (sem inventar quarta
palavra): janela cheia ⇒ `alta`. Entre o piso de C2 e a janela cheia ⇒ `parcial`: C1 e C2
publicam com a janela **impressa**, C3 publica **com correção conservadora** e rótulo de
provisório. Entre o piso de C1 e o de C2 ⇒ `parcial`, mas **C3 não publica**. Abaixo do
piso de C1 ⇒ `insuficiente`: **nenhuma mensalização publica**, em nenhuma classe — o
relatório mostra os meses documentados e seus totais e diz que a janela é insuficiente.

Por que 3 e 6: **3** é onde variação mês a mês passa a ser observável (com 1 a variância
é indefinida; com 2 existe uma comparação) — abaixo disso "padrão", "recorrente" e
"média" são asserção, não observação. **6** é onde um mês atípico deixa de mover a média
acima de ~20%, é a janela mais curta que contém um ciclo de essencial semestral, e é o
número que a [[A40.l15]] já intuiu — ratificar um threshold que o plano carrega é mais
barato que introduzir um sétimo.

**Score:** publica só se **todos** os componentes passarem o piso da própria classe.
Faltando componente, publique os que passam e **não publique o agregado**.
**Renormalizar peso sobre os componentes disponíveis é proibido** — dropar um componente
ruim *sobe* a média ponderada, o que é Goodhart puro num produto com viés otimista
documentado.

**Postura conservadora, e só de um lado.** C1/C2 publicam o número com a janela impressa
e **suprimem a conclusão** que depende do nível estar certo. C3 usa
`max(média, percentil 75 dos meses observados)` — **não o máximo**, que dimensionaria
alvo absurdo a partir de um outlier e mata adesão. A correção vai **no custo e não na
receita**: duas conservadorias empilhadas multiplicam, zeram a folga e ninguém sabe qual
delas o fez. O **mesmo** valor corrigido alimenta alvo de reserva **e** cobertura em
meses, senão a reconciliação algébrica entre os dois quebra. E a descontinuidade é
declarada: quando a janela fecha, o alvo **cai** — sem microcopy isso lê como
instabilidade da ferramenta.

**Contiguidade gateia afirmação sobre padrão, não sobre nível.** Com o mesmo número de
meses, lacuna no meio é **melhor** para nível (cobre mais do ciclo anual) e **pior** para
trajetória (quebra a série e pode esconder mudança de regime). Logo: bloco contíguo
mínimo de 3 para diagnóstico comportamental, classificação de equilíbrio e qualquer texto
de tendência; médias de nível **não** degradam por contiguidade.

**Recência é estrutural, não predicado:** com a janela ancorada nos meses-calendário
decorridos e teto na data de análise, "meses esparsos ao longo de dois anos" deixa de ser
possível. Aparece em troca a banda baixa por **defasagem** (família cujo último documento
é antigo) — hoje isso publica média de janela cheia sobre dado velho com confiança cheia.
Consequência declarada, não descoberta depois.

**Correção de premissa minha:** eu havia raciocinado que perder meses atípicos
superestimaria o custo. O `financial-planner` mostrou que o sinal é **indeterminado** —
perder um mês de pico tira o gasto do numerador **e** o mês do divisor (subestima),
enquanto um repique que caiu em mês **retido** passa a ser dividido por menos (superestima).
O que o fix garante não é um número mais correto: é a troca de um viés **sistemático,
sempre para baixo e silencioso** por **erro de amostragem, sinal desconhecido e
declarável**. Não afirmar que o número do cliente ficou certo.

**Fora desta lane, com deferimento datado:** a correção certa para repique anual é
**anualizá-lo** em vez de deixar a janela decidir o peso dele — isso muda a fórmula
vigente do custo essencial e exige decisão própria.

Interação com a [[ADR-345]] (`Roadmap`): a **exibição** do selo é escopo dela. Aqui entra
a **agregação honesta** e a **decisão de publicar ou não** — que mora no **payload, nunca
no frontend**: métrica abaixo do piso sai **ausente + irmão com o motivo** (forma já
precedente no repo), nunca nulo sem checar o consumidor, porque o ramo de ausência já
existe nesse código e às vezes fabrica default. Se cada consumidor reimplementar o piso,
reproduzimos em três lugares o defeito dos "três percentuais para o mesmo conceito".

**O que o usuário vê: nenhum selo novo.** Com 98 de 128 documentos carregando alguma
reserva, selo novo é ruído. Um selo por conceito por tela — resolver o campo de confiança
existente como **pior das duas entradas** (cobertura de categorização × cobertura
temporal) **nomeando a causa**; **uma** linha agregada no bloco de premissas, **texto
impresso e não tooltip** (o PDF é o artefato que a família leva ao contador); e ressalva
por seção **só onde a banda mudou o output**. Selo onde nada mudou é decoração — é o que
produz fadiga.

**Governança:** isto é **regra nova**, não precisão de regra existente — a política
vigente decide o divisor, nunca piso de publicação nem dimensionamento conservador. Abre
**ADR própria** `Proposto` + emenda datada na cláusula do divisor apontando para ela +
tabela de bandas na referência de fórmulas.

## Critério de aceite

- Nenhum KPI de janela de doze meses inclui período cujo zero veio de falha de
  extração; o número de meses da janela reflete a exclusão.
- Visão por conta imprime "não lido" para esses períodos; **nenhum zero monetário**.
- Teste com mês não decorrido na série ⇒ não entra no divisor.
- Teste com mês documentado só numa perna ⇒ semântica única, declarada.
- Grep prova fonte única de categoria; o percentual publicado que **inverte** sob a
  lista declarada tem o delta declarado no golden.
- **Delta de todo número exibido declarado** (`↑`/`↓`/`=`) — esta lane move
  denominador, logo move quase todo número mensalizado. Rebaseline silencioso é
  reprovação.
- **Banda derivada, não julgada:** o payload emite meses decorridos na janela,
  documentados, e maior bloco contíguo; a banda é função **só** desses três. Teste por
  tabela nos cinco pontos de fronteira.
- **Piso por classe enforçado no produtor:** cada métrica mensalizada declara sua classe
  numa lista única, com teste anti-órfã (métrica mensalizada sem classe declarada ⇒
  falha). Abaixo do piso ⇒ chave **ausente + motivo**. **Nenhum consumidor reimplementa o
  piso** — provado por busca, não por inspeção.
- **Sem renormalização de peso no score:** teste que prova que dropar componente **não**
  sobe o número.
- **Predição testável, que vale como detector:** o fix move **níveis**, não razões de
  mesma janela. Esperado `↑` em despesa média, custo essencial e alvo de reserva; `↓` em
  cobertura e autonomia; **`=` em taxa de poupança recorrente e nos percentuais de
  equilíbrio**. Se uma razão de mesma janela se mover, é **achado** — ou existe uma
  segunda base não localizada (é o próprio RV4-55 desta lane), ou o mês fantasma não
  contribuía zero, o que seria extração **parcial** e não falha total. Não tratar como
  ruído de rebaseline.
- **Medir o divisor isolado primeiro:** o item de config desta lane também sobe o custo
  essencial. Juntos, não se sabe se o denominador foi consertado.
- **Contrato com o parecer:** métrica suprimida sai **ausente do exec-context** do stage
  de parecer, com o motivo presente, e a persona não mensaliza por conta própria a partir
  da série crua. Há histórico de fabricação de métrica ali — sem esta cláusula o E5
  suprime e o E6 republica.
- **O substrato versionado cai na banda mais baixa** e o snapshot vai mostrar cards
  suprimidos e score não publicado. Isso vai **parecer** regressão: declarar antes. E
  **não calibrar o piso para o snapshot ficar verde** — é a forma mais barata de Goodhart
  aqui.
- Snapshot do view-model rebaselinado com manifesto, coordenado com a fila da
  [[A40.l15]].
