---
id: ADR-335
type: adr
title: "Autonomia financeira (ex-cobertura_despesas_meses) exclui imóvel ilíquido e separa da reserva de emergência"
status: Decidido
date: "2026-07-14"
relates_to:
  - "[[ADR-142]]"
  - "[[ADR-215]]"
  - "[[ADR-090]]"
  - "[[ADR-217]]"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
---

# ADR-335 — Autonomia financeira exclui imóvel ilíquido

> Cluster **E1** (P1) da re-review dogfood 2026-07-13 · [[PLAN-dogfood-report-fix]].
> Decisão de domínio adjudicada pelo `financial-planner` (2026-07-14), endossada pelo owner.

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
