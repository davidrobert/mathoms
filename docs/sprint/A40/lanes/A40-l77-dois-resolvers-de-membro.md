---
id: A40.l77
type: lane
title: "Dois resolvers de membro sobre o mesmo baseline: o fix do eixo de ano chegou em um e o cônjuge vale 110k e 0,00 no mesmo payload"
sprint: A40
plan: PLAN-deterministic-authority
status: open
priority: P0
branch_slug: a40-l77-dois-resolvers-de-membro
adrs:
  - "[[ADR-394]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
  - area/financial-planning
---

# A40.l77 — Dois resolvers de membro (DE-10)

> **O primeiro entregável é a decisão, não o código.** Dois resolvers paralelos
> sobre o mesmo baseline é escolha arquitetural — unificar, declarar um
> autoritativo, ou manter os dois com contrato explícito. Co-design
> `data-engineer` + `senior-cto` **antes** de escrever o fix. Copiar
> `anos_base_por_membro` para o segundo resolver fecha o número e deixa a classe
> viva: dois produtores da mesma verdade continuam podendo divergir no próximo fix.

> **Precede o DE-7 e a janela J5.** Corrigir este resolver move `total_financeiro`,
> que é o **denominador** da ressalva de cobertura que o DE-7 vai publicar. Construir
> a linha de cobertura antes calibra limiar, copy e teste contra um número prestes a
> mudar. Ver §Inventário dos achados do r7 sem hospedeiro no [`_README`](../_README.md).

## Problema

O fecho do **RV6-04** ([[A40.l69]], #1578 / [[ADR-394]] §Emenda (c)) corrigiu o eixo
de ano-base em **um** dos dois resolvers de membro. No mesmo payload, a mesma pessoa
tem dois valores:

| Superfície | Resolver | Cônjuge |
| --- | --- | --- |
| `patrimonio.investimentos_conjuge` | `resolve_members` (`patrimonio_resolvers.py`) | `n=9` · **R$ 110.130,67** |
| `total_financeiro` / `tabela_classes` / `top_ativos` | `E5MemberResolver` (`e5_member_resolver.py`) | `n=9` · **R$ 0,00** |

Medido em `207fca00` sobre o run `33514dc4`; `git show --stat 11b90a4e` não lista
`e5_member_resolver.py`.

**O mecanismo, nomeado.** O defeito é do **eixo**, não da pessoa. O ano-base era do
**domicílio** — `_max_value_year` (`patrimonio_types.py:99`) sobre o baseline
inteiro. Com os cônjuges declarando em anos disjuntos, quem não tem item no ano
escolhido cai no fallback e vira `0,00` — a conflação `null`↔`0,00` que a
[[ADR-394]] proíbe um andar acima. O #1578 instalou `anos_base_por_membro`
(`patrimonio_resolvers.py:341`), que dá a cada membro o maior ano que **ele próprio**
declarou. O `E5MemberResolver` **não recebeu nada**: segue importando
`resolve_value_year` (`patrimonio_types.py:111`), que é a função do eixo antigo.

**Consequência visível.** `instituicoes_por_membro` publica **3 instituições dela com
`n_posicoes=9` e valor zero** — a assinatura literal do RV6-04 original, na superfície
que o fecho não alcançou. Os consumidores do resolver não-corrigido são
`InvestimentosClassesAnalyzer`, `TopAtivosAnalyzer` e `InstituicoesPorMembroAnalyzer`,
via `e5_analyzer_adapter.py`.

## Escopo

1. **Co-design da autoridade** — decidir e registrar (emenda à [[ADR-394]] ou ADR
   nova) qual resolver é fonte de verdade do eixo membro→ano, e o que acontece com o
   outro. Sem isso o resto é remendo.
2. **Executar a decisão** nos consumidores do `E5MemberResolver`.
3. **Gate da classe, não da instância** — um teste que falhe quando **qualquer** par
   de superfícies publicar valores diferentes para o mesmo (membro, conceito) no mesmo
   payload. O fix pontual fecha o número de hoje; o gate fecha a família.

## Critério de aceite

- No mesmo payload, cônjuge tem **um** valor: `patrimonio.investimentos_conjuge` e a
  soma de `tabela_classes`/`top_ativos` concordam. Prova por mutação — reverter o fix
  do eixo no resolver corrigido deixa o teste vermelho **nos dois lados**.
- `instituicoes_por_membro` não publica linha com `n_posicoes>0` e valor `0,00` sem
  razão declarada (`sem_haystack`/`sem_match`, vocabulário da [[ADR-406]]).
- O gate da classe existe e **tem chamador** — CI ou pre-commit, não só unit test.
  Precedente negativo na mesma sprint: `scan_view_model_pii` shipou sem chamador e a
  KR-D não fechou (ver [`_README`](../_README.md) §KRs).
- A decisão do item 1 está numa ADR, com o resolver perdedor removido **ou** com o
  contrato dos dois escrito. "Os dois existem e agora concordam" não é desfecho.

## Fora de escopo

- **DE-7** (`nao_atribuidos` = 61% sem linha de cobertura) — arbitrado em 2026-08-21
  para **janela J5 própria**; exige rebaseline de golden, do snapshot do view-model e
  re-derivação de `tests/test_e5_conservation_invariants.py`. Esta lane é o
  pré-requisito dele, não o hospedeiro.
- **DE-8** (top-up IRPF sem quantia declarada) — mesma janela do DE-7.
- **Idempotência do eixo de atribuição** (2 runs, 15 itens divergem) — roteada para a
  [[A42]] pela arbitragem de 2026-08-21.
