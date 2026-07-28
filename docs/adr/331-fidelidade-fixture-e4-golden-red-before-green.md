---
id: ADR-331
type: adr
title: "Fidelidade fixture↔E4 (por_fonte real) + golden red-before-green"
status: Decidido
phase: dogfood Frente 2
date: "2026-07-14"
relates_to:
  - "[[ADR-330]]"
  - "[[ADR-090]]"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/backend
---

# ADR-331 — Fidelidade fixture↔E4 + golden red-before-green

> Item **C7-golden** (P0/P1) do plano PLAN-dogfood-report-fix §"As 4 qualidades como gates verificáveis" → **Corretude** (golden red-antes-de-green).
> Achado da revisão dogfood — razão-raiz **CTO-03**: o golden do view-model assume um agregado `por_fonte.receita_pj` que o E4 real nunca emite, deixando o CI cego à classe B (shape de `por_fonte` + derivadas de perfil de renda).

## Contexto

O snapshot golden `backend/tests/snapshots/dogfood_view_model.json` é **derivado** — gerado rodando o pipeline E3→E4→E5 sobre a fixture dogfood em `tests/pipeline_golden_substrate.py` (A23.l2, `test_report_view_model_snapshot.py`). A config de renda da fixture é monolítica (`income_keywords={"receita_pj": [...]}`), então o E4 produz uma **única** chave `receita_pj` em `por_fonte` (`dogfood_view_model.json:333`) e as derivadas `perfil_renda="pj_dominante"` / `receita_pj_pct="100.000000"` (linhas 687-688).

Num run real, o classifier PJ ([[ADR-236]]) discrimina a renda PJ nas 5 labels de `PJ_LABELS` (`transaction_classifier_pj.py:25-27`: `pro_labore`, `lucros_distribuidos`, `das_simples`, `folha_pj`, `iss`) — **nunca** um agregado `receita_pj`. O consumidor `reserva_emergencia_calculator.py:200-202` lê exatamente `por_fonte.get("receita_pj")`; sobre o shape real ele lê **0**, colapsando `receita_pj_pct` e `perfil_renda`. A fixture, por não exercitar a discriminação PJ, cimenta um shape que o produtor não emite e **mascara o bug do consumidor** — CI verde sobre defeito de produção.

## Decisão

**D1 — Fidelidade de shape.** A fixture dogfood e as fixtures E5 devem produzir `por_fonte` no shape real do E4: as 8 chaves canônicas (5 labels PJ + CLT + demais origens), **incluindo `lucros_distribuidos`** e **sem** o agregado `receita_pj`. A enumeração canônica de `por_fonte` vive no contrato da [[ADR-330]].

**D2 — Fonte G1 do conjunto de categorias.** O conjunto fechado é a **união** de `IncomeOriginResolver.known_categories()` (`income_origin_resolver.py:168`) + `PJ_LABELS` (`transaction_classifier_pj.py:25-27`) + o catálogo de despesa ([[ADR-137]]) — código vivo, não lista hardcoded.

**D3 — Guard anti-drift.** Teste que falha se a fixture carregar qualquer chave de `por_fonte` ausente do contrato E4 (schema da [[ADR-330]]). Renomear/remover chave no E4 sem atualizar a fixture quebra o guard, não passa silencioso.

**D4 — Red-before-green (shape).** O snapshot recebe um caso que **falha pré-fix** dos clusters de defeito A/B/C1 da revisão e **passa pós-fix**, cobrindo `perfil_renda` + `receita_pj_pct` sobre o shape corrigido de 8 chaves. Escopo do snapshot: **shape**, não conservação numérica.

## Rationale

Golden fiel ao contrato > golden conveniente. Um golden que "passa sempre" é ruído, não sinal — o custo de manter a fixture alinhada ao E4 real (D1/D3) é o preço de o CI enxergar a classe B. Ancorar o conjunto em G1 (D2) evita drift silencioso quando uma origem nova entra em `known_categories()` ou `PJ_LABELS`. Dinheiro permanece cents int / `Decimal` no snapshot, zero float ([[ADR-090]]).

## Alternativas consideradas

- **Manter o agregado `receita_pj` na fixture.** Rejeitada: cimenta um shape que o E4 não emite — é a própria razão-raiz CTO-03.
- **Golden estático editado à mão.** Rejeitada: perde a garantia "run 2× byte-idêntico" do substrato A23.l2 e desacopla do E4. O golden deve ser derivado do pipeline com fixtures que exercitem os caminhos reais.
- **Um só teste cobrindo shape + conservação.** Rejeitada (correção da verificação): conservação (identidade de aporte) é competência de `tests/test_e5_conservation_invariants.py` (tolerância zero, cents int), com fixture que inclua a transação de aporte — ver [[ADR-333]]. O snapshot dogfood **não** testa conservação; cobre só `perfil_renda`/`receita_pj_pct` (shape).

## Consequências

- **Rebaseline coordenado.** `dogfood_view_model.json` é golden **mutável e compartilhada**: os clusters C8/C11/C3/C5 também rebaselinam. Serializar via **um único manifesto** de `dev/golden_diff.py` (entradas `golden|path|old_cents|new_cents|adr|rationale|ref`) em ordem coordenada — nunca rebaseline paralelo (colisão de bytes).
- **A troca TRS 4→5 é config de fixture, não regressão de código.** Se a decisão de domínio #1 do plano fixar TRS canônica em 5%, o novo valor de `dogfood_view_model.json:if_trs` vem de editar `_DEFAULT_GOALS["independencia_financeira"]["trs_pct"]` (`pipeline_golden_substrate.py:17`, hoje `4.0`) — mudança de **insumo**, **fora** do red-before-green. Registrar a entrada de manifesto como `rationale: config-fixture`.
- **Bump:** nenhum. Não muda wire nem schema E5; só alinha fixture + goldens ao contrato da [[ADR-330]].
- **Entregue (dogfood Frente 2):** D1 (fixture emite `lucros_distribuidos`, código E4 real) + D4 (golden `dogfood_view_model.json` rebaselinado; `perfil_renda` permanece `pj_dominante`, ganha bloco `receita_por_natureza`). **Follow-up:** D3 (guard automático anti-drift que falha se a fixture carregar chave de `por_fonte` ausente do contrato E4) fica para lane subsequente — a fidelidade está garantida agora; o guard previne regressão futura.

## Critério de aceite (4 lentes)

- **Completude:** `rg` zero-hit de `por_fonte.get('receita_pj'` na fixture; guard D3 enumera todas as chaves do contrato E4.
- **Corretude:** snapshot falha pré-fix (A/B/C1) e passa pós-fix; cents int / `Decimal` exato, zero float ([[ADR-090]]).
- **Consistência:** conjunto de categorias da fixture == G1 (`known_categories()` + `PJ_LABELS` + catálogo de despesa); rebaseline de C7/C8/C11/C3/C5 num só manifesto ordenado.
- **Precisão:** guard cita `slot + dot.path + chave ofensora`; TRS 4→5 registrada como `config-fixture`, não `value_delta` de código.
