---
id: A28.l2
type: lane
title: "TRS efetiva com numerador/denominador do mesmo universo + guardrail de sanidade (ADR-191)"
sprint: A28
plan: PLAN-report-trust
status: shipped
ship_pr: 754
ship_date: "2026-07-03"
priority: P0
branch_slug: trs-universo-consistente
adrs:
  - "[[ADR-191]]"
parallel_with:
  - "[[A28.l4]]"
  - "[[A28.l3]]"
tags:
  - type/lane
  - sprint/a28
  - status/shipped
  - priority/p0
  - area/e5
---

# A28.l2 — `trs-universo-consistente` (Onda 0 · Must · nunca cortar)

## Problema

O dogfood `72883bde` exibe **TRS efetiva de 22,63% a.a.** — impossível e
perigosa. Raiz: numerador = renda passiva anual (R$ 326k, dominada por R$ 284k
de **dividendos de distribuição de lucro da própria PJ do titular** ≈
remuneração de trabalho, não yield de carteira); denominador =
`patrimonio_gerador_brl` (R$ 1,44M = **só imóveis geradores**). Universos
diferentes. O valor propaga para `ratios.rentabilidade_pct` e para a cobertura
Perini.

**Maior potencial de decisão errada do relatório:** o cliente lê "minha
carteira rende 22,6%, estou quase na IF" e **desacelera aporte** — enquanto o
Monte Carlo do mesmo relatório diz probabilidade de IF de 31%. O relatório se
autocontradiz e o parecer E6 não flagou (não há check de sanidade — um
planejador humano teria parado em "yield de 22,6% em imóvel? impossível").

## Escopo

1. **Separar distribuição de lucros da PJ do titular** do yield de carteira no
   numerador (`passive_income.renda_passiva_por_fonte_brl`): dividendos de
   posições de investimento, JCP, aplicações, aluguéis e exterior contam;
   distribuição da empresa operacional do titular sai (ou é explicitamente
   rotulada como linha separada, fora da TRS).
2. **Casar o denominador com o numerador** (ADR-191): se o numerador inclui
   dividendos de ações, o denominador inclui a carteira de ações — não só
   imóveis. Meta-âncora permanece 5% a.a. (ADR-191 §D5, não Trinity 4%).
3. **Guardrail de sanidade determinístico no E5** (fonte única — [[A28.l11]]
   apenas consome): TRS calculada > ~8% a.a. → campo
   `ratios.rentabilidade.status = "suspeito"` + flag "revisar composição";
   **nunca publicar silencioso**.
4. Reconciliar exibição: "renda passiva estimada 4%" (7,4k/mês) vs "observada"
   (27,2k/mês) no bloco goals — declarar o que cada uma é ou remover uma.
5. Golden re-snapshot com diff explicado.

## Critério de aceite

- Teste de invariante de universo consistente: toda fonte no numerador tem a
  classe correspondente no denominador (fixture sintética com dividendo PJ →
  excluído/rotulado).
- TRS resultante plausível no dogfood (<~8% a.a.) OU `status="suspeito"`
  presente no payload — nunca um número aberrante sem flag.
- `ratios.rentabilidade_pct` e cobertura Perini derivam da TRS corrigida.
- Sem ADR nova — conforma [[ADR-191]]; se o guardrail >8% evoluir para regra de
  domínio nova, mini-ADR na hora (não antecipar).
- Golden re-snapshot; `pytest tests -q` + `pytest backend/tests -q` verdes.

## Notas

- O flag `status="suspeito"` desta lane é o sinal que a [[A28.l11]] projeta ao
  exec-context do parecer (hint "não construa recomendação sobre TRS quando
  status=suspeito") — **não duplicar o guardrail no E6**.
- Paralela com [[A28.l4]]/[[A28.l3]] (campos disjuntos).

## Owner

Agente da lane; `financial-planner` já validou a definição (numerador de
carteira; distribuição PJ ≠ yield) na revisão de origem.
