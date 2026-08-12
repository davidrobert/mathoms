---
id: ADR-382
type: adr
title: "Posição por instituição tem duas visões — corrente (datada por linha) e fechamento fiscal 31/12"
status: Proposto
phase: A40.l39
date: "2026-08-12"
relates_to:
  - "[[ADR-238]]"
  - "[[ADR-245]]"
  - "[[ADR-376]]"
  - "[[ADR-383]]"
  - "[[ADR-384]]"
supersedes: []
superseded_by: []
aliases: ["ADR 382", "visões corrente e fiscal", "fechamento 31/12"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/frontend
  - area/financial-planning
---

# ADR-382 — Posição por instituição tem duas visões: corrente e fechamento fiscal 31/12

## Contexto

O card `posicao_informe_31_12` (S1) mistura, sob o header "Valor em 31/12",
linhas de informe (snapshot 31/12/ano-base) com linhas de extrato cujo valor
é o saldo **atual** do último extrato reconciliado (no dogfood: até
2026-08-11). A mesma conta aparece duas vezes sem vínculo (Itaú CC informe
R$ 0,00 + extrato R$ 5.156,06). A regra "informe vence extrato D+1"
([[ADR-238]] D5) é letra morta em produção: `_period_in_janela_d1` roda
sobre o **último** extrato da conta e nunca dispara em workspace com
extratos correntes.

Parecer `financial-planner` (2026-08-11, convergente nas três metodologias
de referência do produto):
**um balanço tem uma data**; o 31/12 é marco, não linha da fotografia
corrente. Desvio % vs alocação-alvo calculado sobre datas mistas é inválido
por construção. Arbitragem `senior-cto`: separadas as visões, a heurística
D+1 perde a razão de existir.

## Decisão

1. **Toda visão declara uma data-alvo.** A pergunta muda de "qual saldo
   vence" para "qual visão a linha povoa".
2. **S1 — visão corrente.** O card vira "Posição por Instituição e Moeda":
   só posição corrente (extratos reconciliados, [[ADR-376]]), com
   `data_referencia` visível por linha e sinal de defasagem. Sem linha de
   informe; sem linha de total.
3. **Bloco fiscal — "Fechamento de 31/12/AAAA"** na seção **Renda Anual e
   Impostos** (conciliação factual; "Otimização Tributária" é prescritiva e
   misturar convida a ler divergência como oportunidade fiscal). Fonte 100%
   fiscal (informe + IRPF); **zero linha derivada de extrato**. O alerta CBE
   migra junto — a obrigação é aferida legalmente em 31/12. Total permitido
   apenas aqui (data única).
4. **`_period_in_janela_d1` deixa de existir como regra de negócio.** Se
   sobreviver, as visões não se separaram de fato. Emenda datada na
   [[ADR-238]] (D5 parcial) acompanha esta ADR.
5. **[[ADR-245]] mantida.** O fallback de caixa ME do baseline IRPF continua
   povoando a visão corrente quando é a única fonte — com data (31/12 do
   ano-base) e proveniência visíveis na linha. Removê-lo zeraria o
   patrimônio em ME desses workspaces, que é pior.
6. **Agregado nunca rotulado com data única** quando as linhas têm datas
   distintas — rótulo "datas por linha (mais antiga: X)". Nenhuma tabela
   mistura datas sem coluna de data.
7. **Sem visão pareada** (linha única com colunas 31/12 × atual) até a
   identidade institucional por chave forte ([[ADR-384]]) casar as contas —
   join errado que *afirma* "mesma conta" é pior que o artefato atual.
8. **O marco anual de patrimônio (régua de IF, múltiplo do custo de vida)
   não fica no bloco fiscal.**
   O snapshot fiscal cobre só quem emitiu informe (sem imóvel, veículo,
   banco sem informe) — usá-lo como marco subestimaria sistematicamente. O
   marco correto é o patrimônio consolidado recalculado com data-alvo
   31/12 ([[ADR-383]]); o bloco fiscal é evidência de auditoria, não medida.

## Consequências

- Split em dois PRs na lane A40.l39: PR-a (plumbing `data_referencia` + `id`
  por linha — mecânico) e PR-b (split visual + realocação do CBE), com spec
  de UI do `product-designer`.
- Gate "header ≡ conteúdo": card que declara data fixa só renderiza linhas
  daquela data — o dogfood atual reprova; o desenho novo passa.
- Critério pré-PR-b: todo ativo hoje listado só por informe no card precisa
  ter representação no patrimônio por outra fonte (o buraco PicPay foi
  fechado pela [[ADR-376]] antes desta).
- O bruto muda onde a janela D+1 casava (nenhum caso no dogfood atual).
