---
id: ADR-335
type: adr
title: "Autonomia financeira (ex-cobertura_despesas_meses) exclui imóvel ilíquido e separa da reserva de emergência"
status: Decidido
date: "2026-07-14"
amended_at: ["2026-07-16", "2026-08-28"]
relates_to:
  - "[[ADR-142]]"
  - "[[ADR-215]]"
  - "[[ADR-090]]"
  - "[[ADR-217]]"
  - "[[ADR-333]]"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
---

# ADR-335 — Autonomia financeira exclui imóvel ilíquido

> **Emendada 2026-08-28** ([[A40.l80]] · [[ADR-412]] §D7): a autonomia deixa de ser um
> número e passa a ser **intervalo declarado** — medida sobre a base cheia, piso sobre a
> base com titular identificado, com a base de cada ponta nomeada em campo. Ver §Emenda 2.

> Cluster **E1** (P1) da re-review dogfood 2026-07-13 · PLAN-dogfood-report-fix.
> Decisão de domínio adjudicada pelo `financial-planner` (2026-07-14), endossada pelo owner.

> **Emenda 2026-07-16 (Onda R3.4 · CTO-04 · co-design `financial-planner`):** o
> **denominador** da autonomia passa a ser o **consumo mensal ex-aporte**
> (`despesa_consumo`, [[ADR-333]]), não `despesa_mensal_media` (que incluía o aporte).
> Ver [§Emenda](#emenda--denominador-ex-aporte-cto-04-2026-07-16). Esta ADR corrigiu o
> *numerador* (investível ex-imóvel) em 2026-07-14 mas deixara o denominador bruto.

## Contexto

O relatório expõe **duas** métricas de "meses de cobertura" sob rótulos confundíveis:

1. **Reserva de emergência** — `saude_financeira.reserva_emergencia.cobertura_meses` =
   `reserva_liquida ÷ custo_essencial_mensal` = **25,6** neste perfil.
2. **`ratios.cobertura_despesas_meses`** = `investivel_efetivo ÷ despesa_mensal_media` =
   **18,52** (`ratios_calculator.py:264-268`). É renderizada como o ponto-forte
   **"Colchão Patrimonial"** (`pontos_fortes_analyzer.py:221-229`, emitido só
   `if not reserva_emitida`, i.e. quando a reserva < 6 meses).

Três defeitos, além da colisão de rótulo:

- **Numerador emprestado da IF.** `investivel_efetivo` (cat_3+4+5+6 **+ cat_2 imóveis**
  quando `imoveis_no_if=true`, [[ADR-142]]/[[ADR-215]] §6) existe para medir progresso de
  IF — horizonte de décadas, iliquidez tolerável. Usá-lo num KPI de autonomia/liquidez
  (horizonte de choque) é empréstimo indevido.
- **Contradição de veredicto.** A robustez do "Colchão" vem *inteiramente* do imóvel
  concentrado ilíquido — enquanto o relatório marca essa concentração como risco **Alto**.
  Dois componentes dão veredictos opostos sobre o mesmo fato.
- **Vazamento de toggle.** Como `investivel_efetivo` é toggle-dependente, o KPI muda
  quando o usuário liga "contar aluguéis na IF" — uma decisão de IF infla silenciosamente
  uma métrica de autonomia.

## Decisão

Manter **dois conceitos distintos**, com nomes e fórmulas honestos:

1. **Reserva de emergência** — **inalterada**: `reserva_liquida ÷ custo_essencial` = 25,6.
2. **Autonomia financeira** — renomear `ratios.cobertura_despesas_meses` →
   `ratios.autonomia_financeira_meses` e **trocar o numerador** para o **investível
   financeiro** (cat_3+4+5+6, **sem** cat_2 imóvel ilíquido) ÷ despesa mensal total.
   Efeito de brinde: fica **toggle-independente**. Alias deprecated do campo antigo por 1
   ciclo no view-model.
3. `investivel_efetivo` permanece **intocado** como numerador da IF (`progresso_if`) — lá
   o imóvel legitimamente conta.

Denominadores diferentes (essencial vs total de vida) são **justificáveis**: sobrevivência
vs manutenção de padrão são conceitos distintos. O que corrige a confusão é o **naming**,
não forçar denominadores iguais.

## Rationale

As três metodologias de referência convergem: **valor de imóvel ilíquido não é colchão**
— buffer de sobrevivência é liquidez imediata; imóvel de investimento é capital gerador
(pertence à IF), e caixa é *sleeve* distinto de imóveis. Um "colchão" cuja robustez é o
próprio ativo concentrado ilíquido premia justamente o risco de alocação que o relatório
sinaliza. Renda de imóvel quitado é resiliência real, mas vive na **renda passiva** e no
*sizing* da reserva (perfil rentista → `meses_alvo` maior) — creditar o valor do ativo
**e** o aluguel seria dupla contagem.

## Alternativas consideradas

- **Manter imóvel no numerador + caveat "se liquidar".** Rejeitada: o caveat **não
  sobrevive à sumarização** do parecer/narrativa (mesma lição do gate TRS "suspeito",
  [[ADR-191]]) — o headline inflado permanece.
- **Descontinuar o KPI.** Rejeitada: o conceito "runway do patrimônio financeiro" é útil e
  distinto da reserva de emergência.
- **Forçar as duas ao mesmo denominador.** Rejeitada: apaga a distinção sobrevivência ×
  padrão de vida; o naming basta.

## Consequências

- O número **cai** para esta família (base ilíquida sai) — **feature, não regressão**:
  realinha o KPI à mensagem de concentração. O badge "robusto" pode parar de emitir para
  perfis concentrados — correto (não devem ganhar selo de robustez sobre base ilíquida).
- Requer expor/derivar o **investível financeiro** (cat_3+4+5+6) se ainda não estiver no
  payload de patrimônio. **Verificado no impl:** `patrimonio.investivel_financeiro` já
  existe (`PatrimonioCalculator`), sem derivação nova.
- **Score — sem bump de `score_version`.** O componente `cobertura_despesas` lê
  `reserva.cobertura_meses` no caminho primário (**inalterado**); só o *fallback*
  (reserva ausente) lê o ratio. O fallback hoje já é um proxy de runway patrimonial
  (`investivel_efetivo/despesa`), então E1 apenas o torna financeiro-only — **refinamento
  de input, não de fórmula/peso** ([[ADR-217]] §D3 exige bump só para fórmula/peso). O
  score do dogfood é byte-idêntico (reserva presente domina). Fallback migra para
  `autonomia_financeira_meses` com alias defensivo por 1 ciclo.
- Bump: **schema e5 aditivo** (campo novo + alias deprecated) — batelar no PR de schema da
  onda. `Decimal` exato ([[ADR-090]]).

## Critério de aceite (4 lentes)

- **Completude** — nenhum KPI/ponto-forte de "colchão/autonomia" cita número que inclua
  valor de imóvel ilíquido; `rg` zero-hit de `cobertura_despesas_meses` lendo
  `investivel_efetivo`.
- **Corretude** — golden red-before-green: `autonomia_financeira_meses` cai de 18,52 para
  o valor financeiro-only nesta fixture; `investivel_efetivo`/`progresso_if` **inalterados**.
- **Consistência** — autonomia e o flag de concentração nunca dão veredictos opostos sobre
  a mesma base; dois campos, dois nomes (`reserva_emergencia.cobertura_meses` ×
  `ratios.autonomia_financeira_meses`); nenhum texto de usuário chama ambos de "cobertura".
- **Precisão** — independência de toggle: flip de `imoveis_no_if` **não** altera
  `autonomia_financeira_meses` (teste liga/desliga assere igualdade). Sem dupla contagem de
  aluguel (numerador de autonomia × renda passiva).

## Emenda — denominador ex-aporte (CTO-04, 2026-07-16)

A decisão original (2026-07-14) trocou o **numerador** para `investivel_financeiro`
(ex-imóvel), mas manteve o **denominador** em `despesa_mensal_media = despesa_total ÷ 12`,
que **inclui o aporte** (`transferencia_patrimonial`). Autonomia mede runway de liquidez —
"quantos meses o patrimônio financeiro sustenta a família se a renda parar". No choque de
renda a família **para de aportar** (aporte é transferência patrimonial voluntária, não
queima de subsistência — [[ADR-333]]); incluí-lo no denominador **subestimava** o runway.

**Decisão (co-design `financial-planner`):** denominador = **consumo mensal ex-aporte**
(`despesa_consumo ÷ n_meses`). `despesa_consumo` já exclui só a transferência
**discricionária/interrompível**; **financiamento** (essencial, não-transferência)
permanece no denominador. Payload legado sem `despesa_consumo` cai em `despesa_total`
(back-compat, sem regressão).

- **Sem bump de `score_version`:** autonomia entra no score apenas como **fallback**
  (reserva ausente); trocar o denominador do fallback é refinamento de input, não de
  fórmula/peso ([[ADR-217]] §D3). No dogfood a reserva domina → score inalterado.
- **Escopo travado:** a hipótese "aporte cessa 100% no choque" vale enquanto o
  `transfer_set` ([[ADR-333]]) contiver só aporte discricionário. Expandi-lo para item
  semi-contratual (previdência contratada, consórcio) **reabre** a base do denominador.
- **Golden:** `autonomia_financeira_meses` **sobe** (denominador menor); delta rastreado
  no rebaseline isolado. Nenhum ponto-forte "colchão robusto" pode reativar indevidamente.

## Emenda 2 — a autonomia vira intervalo declarado ([[A40.l80]], 2026-08-28)

A [[ADR-412]] §D7 exigia esta emenda ao flipar para `Decidido`, e ela é o registro do que
a [[A40.l80]] entregou.

**O que muda.** Metade da carteira financeira pode não ter titular identificado, e o
numerador da autonomia (`investivel_financeiro`) a inclui. Publicar um número só afirmaria
fôlego sobre dinheiro cujo dono ninguém apurou. A autonomia passa a publicar **três
campos**: a medida (`autonomia_financeira_meses`, base `carteira_financeira_familia`), o
extremo conservador (`piso_autonomia_financeira_meses`, base
`carteira_com_titular_identificado`) e o divisor que ambos usaram
(`autonomia_denominador_mensal_brl`). **O spread é o diagnóstico.**

**Por que o extremo inferior é o conservador aqui:** a autonomia autoriza *gastar* o
fôlego. Errar para mais convida a família a consumir reserva que talvez não seja dela —
por isso o veredito se avalia no piso, e a **prescrição dimensionada** (quanto realocar)
morre quando o spread cruza o degrau acionável ([[ADR-412]] §Emenda E4). A **medida nunca
morre** (§E3).

**O denominador desta emenda não muda** — segue `despesa_consumo ÷ n_meses` da emenda de
2026-07-16. O que muda é que ele passa a ser **publicado**: recompô-lo a partir de
`fluxo_caixa` erra no fallback de `_resolve_window` (sem `janela_12m`, `n_meses` vira 0 e
a despesa sai de outro nó), e o gate de cobertura de base precisa fechar dentro do bloco.

**Sem bump de `score_version`** pelo mesmo motivo da emenda anterior: autonomia entra no
score só como fallback, e declarar base é número-neutro.
