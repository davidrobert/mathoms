---
id: ADR-328
type: adr
title: "score_version 2.0 — plateau da cobertura de reserva no alvo do perfil (não premiar over-provisioning)"
status: Proposto
date: "2026-07-12"
relates_to:
  - "[[ADR-217]]"
  - "[[ADR-090]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/report
---

# ADR-328 — `score_version 2.0`: plateau da cobertura de reserva

> Item **C5** do plano [[PLAN-dogfood-report-fix]]. Achado FIN-03 da revisão dogfood.
> Sucessora obrigatória da fórmula travada em [[ADR-217]] §D3 (bump de `SCORE_VERSION`).

## Contexto

O componente `cobertura_despesas` do score dá **nota máxima (10, teto)** a uma
reserva de 25,6 meses — **2,1× a meta de 12 meses** do perfil. O motor já computa
corretamente `reserva_emergencia.avaliacao_liquidity='Excessiva'` (ação:
realocar excedente), mas o score **premia o over-provisioning** e o card de
pontos fortes chama de "no alvo". Isso incentiva entesouramento (~R$ 417k
ociosos) — o oposto do que prescreve o planejamento patrimonial consagrado
(capital ocioso acima da meta deve ser realocado). `SCORE_VERSION = "1.0-legacy"` é constante
única (`financial_score_calculator.py`), e [[ADR-217]] §D3 exige ADR sucessora ao
bump da fórmula.

## Decisão

Bump `SCORE_VERSION` `1.0-legacy → 2.0`, batelando neste mesmo bump os itens de
score correlatos que estão fora deste lote mas colidem na mesma fórmula
(FIN-05 diversificação, FIN-01 input de poupança — coordenados pelo plano [[PLAN-dogfood-report-fix]]).
A mudança desta ADR:

- **Plateau da cobertura:** a nota de `cobertura_despesas` satura em `meses_alvo`
  (12 no perfil), sem bônus acima do alvo. `config/scoring.json` (range de
  cobertura) + `linear_interpolate` passam a clampar no alvo, não em 24.

Fica **fora desta ADR** (conformidade sem decisão nova): reframe do card de
pontos fortes ("excedente realocável ~R$ 417k") e unificação do denominador de
custo essencial entre `fluxo_caixa` e `reserva_emergencia` (bug de consistência).

## Alternativas consideradas

- **Manter nota linear até 24 meses.** Rejeitada: recompensa capital ocioso;
  contradiz a própria `avaliacao_liquidity='Excessiva'`.
- **Penalizar (nota decrescente) acima do alvo.** Rejeitada por ora: plateau é
  suficiente e menos abrupto; penalização exigiria calibração adicional.

## Consequências

- Score deixa de recompensar reserva 2× a meta; deixa de contradizer o flag
  "Excessiva".
- Bump de `score_version` re-baselina os goldens de score **uma vez** (não por
  item — [[PLAN-dogfood-report-fix]] §regra anti-thrashing).

## Critério de aceite (4 lentes)

- **Completude:** card + score + métricas refletem "Excessiva/realocável"; custo essencial unificado.
- **Corretude:** `nota(12) == nota(18) == nota(25,6)` (plateau paramétrico).
- **Consistência:** `pontos_fortes ↔ avaliacao_liquidity ↔ parecer` concordam.
- **Precisão:** plateau explícito em `scoring.json`; `score_version` bumpado; goldens re-baselinados 1×.
