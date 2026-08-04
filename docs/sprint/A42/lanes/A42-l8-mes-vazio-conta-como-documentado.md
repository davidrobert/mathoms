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
parallel_with:
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

> **Depende de [[A40.l15]]**, que é dona do enricher de fluxo, e é **paralela a
> [[A40.l11]]** (unificação dos percentuais de confiança). Escreve o mesmo arquivo que
> a l15 ⇒ serializar. **Na promoção, re-ler a disposição das duas:** se qualquer uma
> estiver `cancelled`, esta lane absorve o escopo e declara a absorção.

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

Interação com a [[ADR-345]] (`Roadmap`): a **exibição** do selo de cobertura ao
usuário é escopo dela, não desta lane. Aqui entra só a **agregação honesta**; a lane
[[A42.l2]] registra o gatilho de retomada da nota.

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
- Snapshot do view-model rebaselinado com manifesto, coordenado com a fila da
  [[A40.l15]].
