---
id: A28.l1
type: lane
title: "reserva de emergência conforme FORMULAS.md: custo essencial + liquidez estrita + meses_alvo por perfil"
sprint: A28
plan: PLAN-report-trust
status: in_progress
priority: P0
branch_slug: reserva-formula-canonica
adrs: []
depends_on:
  - "[[A28.l4]]"
tags:
  - type/lane
  - sprint/a28
  - status/in-progress
  - priority/p0
  - area/e5
---

# A28.l1 — `reserva-formula-canonica` (Onda 0 · Must · depois de l4)

## Problema

A reserva de emergência do dogfood `72883bde` **viola o contrato escrito** em
[FORMULAS.md](../../../reference/FORMULAS.md) §Reserva — dois erros compostos,
ambos empurrando para "Excessiva / 31,6 meses":

- **Denominador errado:** usa `despesas_mensais = 44.192` (despesa **total**,
  na base diluída de 40 meses) em vez de `custo_essencial_mensal` (média
  trimestral das 9 categorias canônicas de `scoring.json:reserva_emergencia.
  _base_calculo` + impostos não-PJ).
- **Numerador errado:** `composicao_liquida.total_liquido = 1.396.385` conta
  **todo o investível financeiro** (investimentos dos dois titulares — incluindo
  ações/FII/exterior — + caixa em moeda estrangeira) como reserva. Reserva é
  liquidez imediata de baixo risco (caixa + RF pós D+0/D+1); carteira produtiva
  não é reserva.
- **Alvo errado:** avalia contra 6/12 meses; para perfil **PJ-dominante** o
  alvo canônico é **18 meses** (FORMULAS.md §Reserva-alvo).

Risco fiduciário direto: o parecer E6 herdou o erro e recomenda "realocar o
excedente da reserva" — induz o cliente a desmobilizar posição de longo prazo
achando que é caixa parado.

## Escopo

1. Denominador = `custo_essencial_mensal` (9 categorias canônicas + impostos
   não-PJ), na base temporal decidida pela ADR da [[A28.l4]].
2. Numerador = `reserva_liquida_disponivel` com filtro de liquidez/risco
   estrito; caixa ME só entra se finalidade explícita = reserva (o parecer já
   pede a finalidade — comportamento correto, manter).
3. `meses_alvo` por composição de renda (CLT 6 · mista 12 · PJ-dominante 18);
   `avaliacao_liquidity` ("Excessiva"/"Adequada"/...) relativa ao alvo **do
   perfil**, não a 12 meses fixos.
4. Alinhar o componente `cobertura_despesas` do score (peso 1.5) e o ponto
   forte "Colchão Patrimonial" à mesma definição (hoje exibem 31,6 e 27,4 para
   "a mesma" cobertura).
5. Golden re-snapshot único (pós-l4), com diff explicado.

## Critério de aceite

- Cobertura recalculada = `reserva_liquida_disponivel ÷ custo_essencial_mensal`;
  teste de invariante: ações/FII/exterior **excluídos** do numerador.
- "Excessiva" só quando cobertura > alvo do perfil; fixture dogfood
  (PJ-dominante) avalia contra 18 meses.
- Nenhum campo da reserva exibe duas coberturas divergentes (31,6 vs 27,4);
  ponto forte deduplicado ou reconciliado.
- `tests/test_e5_conservation_invariants.py` +
  `backend/tests/test_report_view_model_snapshot.py` verdes com rebaseline
  explicado no PR.
- Sem ADR nova — conforma FORMULAS.md §Reserva (bug-fix de conformidade).

## Notas

- **Depende de [[A28.l4]]** (base temporal do denominador) — não abrir PR de
  re-snapshot antes do merge da l4.
- Par com [[A28.l2]]: juntas eliminam as duas piores induções de decisão errada
  do relatório.

## Owner

Agente da lane; sem co-design obrigatório (conformidade a contrato escrito) —
`financial-planner` já validou a definição na revisão de origem.
