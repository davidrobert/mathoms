---
id: ADR-328
type: adr
title: "score_version 2.0 — plateau da cobertura de reserva no alvo do perfil (não premiar over-provisioning)"
status: Decidido
phase: dogfood-r2.3-fp02
date: "2026-07-12"
decided_at: "2026-07-15"
amended_at: ["2026-07-15"]
relates_to:
  - "[[ADR-217]]"
  - "[[ADR-090]]"
  - "[[ADR-218]]"
  - "[[ADR-333]]"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/report
---

# ADR-328 — `score_version 2.0`: plateau da cobertura de reserva

> Item **C5** do plano PLAN-dogfood-report-fix. Achado FIN-03 da revisão dogfood.
> Sucessora obrigatória da fórmula travada em [[ADR-217]] §D3 (bump de `SCORE_VERSION`).

> **Decidido 2026-07-15 (FP-02) — implementado standalone.** Plateau ancora no
> **`reserva.meses_alvo`** (perfil 6/12/18), não no teto fixo 24; piso 3m; sem
> penalização. `SCORE_VERSION → "2.0"`. **FIN-01 já estava resolvido** (ADR-333,
> input fix, sem bump) e **FIN-05 (diversificação) segue subespecificado** → o
> bump 2.0 **não é o batch coordenado** que a emenda de ratificação previa: é só o
> plateau (FIN-05 entra numa 2.x própria quando co-desenhado). Isso preserva a
> invariante [[ADR-217]] §D3 (cada versão = uma fórmula completa) — 2 bumps
> (2.0 plateau, 2.x FIN-05) em vez de 1, custo aceitável. Golden dogfood: **flat**
> (a família over-provisioned de 25,6m já saturava em 10 no teto 24 e segue em 10
> no plateau — o fix dela é a copy do card, não o número). Ver
> [§ Emenda](#emenda-2026-07-15-fp-02--ratificação-financial-planner).

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
(FIN-05 diversificação, FIN-01 input de poupança — coordenados pelo plano PLAN-dogfood-report-fix).
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
  item — PLAN-dogfood-report-fix §regra anti-thrashing).

## Critério de aceite (4 lentes)

- **Completude:** card + score + métricas refletem "Excessiva/realocável"; custo essencial unificado.
- **Corretude:** `nota(meses_alvo) == nota(meses_alvo × k)` p/ todo `k>1` (plateau paramétrico **no perfil**, não em 12 fixo).
- **Consistência:** `pontos_fortes ↔ avaliacao_liquidity ↔ parecer` concordam; card não declara "consolidada" antes do `meses_alvo` do perfil.
- **Precisão:** plateau explícito em `scoring.json`; `score_version` bumpado; `dev/golden_diff.py` per-família documentado 1× — **zero** família cai >0,5 ponto sem causa rastreada.

## Emenda 2026-07-15 (FP-02) — ratificação `financial-planner`

Co-design `financial-planner` (2026-07-15) **ratificou com ajuste**. Ajustes que
entram na definição de 2.0 antes de flipar para `Decidido`:

1. **Âncora no perfil, não em 12.** O plateau satura em `meses_alvo_por_perfil_renda`
   (`config/scoring.json` já expõe 6/12/18 por `perfil_renda`), com **default seguro
   12** quando o perfil não resolve (caso dogfood class-c). O texto original ("12 no
   perfil") travaria o pj_dominante (alvo correto 18) — sub-avaliaria o buffer de
   renda volátil. A nota nova = `clamp((cobertura − 3) / (meses_alvo − 3) × 10, 0, 10)`.
2. **Piso 3m mantido** (`range_min = 3`; `< 3m` = zona crítica).
3. **Sem penalização acima do plateau** — confirmado. O sinal "excedente realocável"
   pertence ao flag `avaliacao_liquidity='Excessiva'` + card + parecer, **não** ao
   número do score (penalizar seria double-count com `progresso_if` + `taxa_poupanca`).
4. **Direção provada:** para `range_min = 3` fixo e `meses_alvo ≤ 24`, `nota_nova ≥
   nota_antiga` ∀ `cobertura ≥ 3` — **nenhuma família perde** ponto na cobertura; a
   maioria ganha (o teto 24 sub-creditava). A família over-provisioned (25,6m) segue
   clampada em 10 (o "fix" dela é a copy do card, não o número).

**Escopo de implementação — resolvido standalone (2026-07-15).** A premissa da
ratificação era batelar C5 + FIN-05 + FIN-01 numa só 2.0. Ao implementar, o
batch se dissolveu: **FIN-01 já estava resolvido** (ADR-333, correção de *input*
da taxa de poupança — sem bump, pois a taxa é input, não a fórmula) e **FIN-05
(diversificação) segue subespecificado** (nenhuma spec do fix; co-design pendente
— não inventar regra de domínio). Bloquear o plateau ratificado + provado numa
espera indefinida por FIN-05 seria pior. Portanto:

- **2.0 = só o plateau** (`financial_score_calculator._cobertura_component`:
  `range_max = reserva.meses_alvo`, fallback `config.range_max=12`; `scoring.json`
  `cobertura_despesas.range_max 24→12` + `_nota`). Label FP-04
  (`custo_essencial_mensal.metodo → media_12m_documentados`, morto/0-cent) pega
  carona no mesmo PR de `scoring.json`.
- **FIN-05 → `score_version` 2.x própria**, quando co-desenhada. Cada versão
  segue completa e travada ([[ADR-217]] §D3 preservado — 2 bumps, não 1; o "1 bump"
  era otimização anti-thrashing, não invariante).
- Reconciliação [[ADR-218]] (card referencia o mesmo `meses_alvo` do score) fica
  com a lane do card D1/D2 (218 segue `Proposto`; o denominador score-side já é vivo).

`golden_diff` per-família (dogfood): **flat, 0 delta** — só `score_version`
`1.0-legacy→2.0` (cobertura já saturava). Testes: `tests/test_score_canonico.py`
(plateau satura no alvo + prova nota ≥ 1.0-legacy ∀ cobertura).
