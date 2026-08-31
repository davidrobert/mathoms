---
id: A27.l2
type: lane
title: "A cobertura do grafo de lineage não é medida por gate nenhum, e o eval fecha o laço sobre o próprio registro"
sprint: A27
status: shipped
ship_pr: 1872
ship_date: "2026-08-30"
priority: P2
branch_slug: a27-l2-cobertura-de-lineage-sem-gate
owner: data-engineer
depends_on: []
adrs: ["[[ADR-281]]"]
tags: [type/lane, sprint/a27, status/shipped, priority/p2, area/dados]
---

# A27.l2 — `cobertura-de-lineage-sem-gate`

> **Origem:** `PV12-02` da rodada unificada **U4** ([[PIPELINE-REVIEWS-active]] §r12).
> Roteada para a **A27** e não para a A42 porque o produtor é o **grafo de lineage**, tese
> desta sprint — não o instrumento de certificação.

## O defeito, em duas metades que se sustentam

1. **O gate é existência pura.** `dev/check_lineage_refs.py` verifica que a ref importa e
   que a ADR existe. Não tem noção alguma de **cobertura**.
2. **O eval fecha o laço sobre si mesmo.** `tests/lineage_eval/cases.py::build_cases`
   devolve 29 casos que cobrem **4 `entry_field` distintos** (são famílias × mutações, não
   amplitude); a raiz de endividamento está no registro com **zero** caso; e
   `expected_rule_ref` sai de `LINEAGE_RULE_REFS[rule_id]["ref"]`, com o teste asseverando
   `expected ⊆ registry`.

**Consequência:** acrescentar raiz nova ao E5 **sem** entrada no registro não move métrica
nenhuma — nem o gate, nem a accuracy. É gate que só pode dar verde.

## O denominador, com a população nomeada

> **Remedido 2026-08-30 na execução — os números do enunciado não reproduzem.** As `42
> chaves de topo` são de um run fora do git; na fixture dogfood determinística o payload tem
> **32**. Pior que a divergência: **o denominador estava errado de espécie**. Contar as 42/32
> raízes cruas põe `narrativas`, `alertas`, `data_analise` e `tarefas` no denominador — prosa
> e metadado que nunca terão rastro. Isso dá um teto inalcançável, e **KR que não pode chegar
> a 100% é KR que ninguém persegue**. O `~87%` herdado é verdadeiro e inútil.

O denominador que a lane entrega é **raiz que publica dinheiro**, discriminada por
`golden_diff.is_monetary` — o único predicado do repo que classifica campo **sem consultar o
registro**, que é o que mantém numerador e denominador independentes.

| Medida (fixture dogfood, 2026-08-30) | Valor |
| --- | --- |
| Raízes do payload que publicam dinheiro | **14** |
| Raízes com nó em `_lineage.fields` | **5** |
| **Cobertura** | **5/14 = 35,7%** |
| Raízes monetárias sem rastro | 9 — `cenarios_conjuge`, `consumo_consciente`, `equilibrio_cerbasi`, `exposicao_cambial`, `goals`, `if_monte_carlo`, `orcamento_prospectivo`, `passive_income`, `ratios` |

O denominador é **dependente de workspace** (flag/cobertura mudam as raízes emitidas), então
o KR fica ancorado na **fixture determinística**, não num run: é gate, não telemetria.

**Correção à metade 2 do enunciado.** "A raiz de endividamento está no registro com zero
caso" é verdade e é **estreita**: são **4 dos 8** `rule_id` sem caso nenhum
(`endividamento.total_dividas`, `fluxo_caixa.fluxo_liquido`, `fluxo_caixa.janelas`,
`patrimonio.bruto`). E o laço era mais frouxo do que o enunciado diz — os 29 casos
exercitam **4 refs distintos** contra **6** no registro, porque refs são **compartilhados**
entre `rule_id` (`patrimonio.liquido` e `.bruto` citam o mesmo enforcer).

**Efeito na rodada unificada:** é por isso que 37 dos 42 blocos saem `sem-veredito` na
tabela de condicionamento — a cegueira é do **registro de lineage**, não falta de balde.
Regra ternária em [[LEDGER-CERTIFY-active]] §r6 §10.

## Critério de aceite

- [x] Existe um **KR de cobertura** = raízes com nó ÷ raízes do payload, com o denominador
      vindo do **payload publicado**, nunca do registro. — `dev/lineage_coverage.py`;
      **5/14 = 35,7%** travado em `dev/snapshots/lineage_coverage_baseline.json`. O gate
      compara **conjunto**, não contagem: raiz renomeada não passa por compensação.
- [x] **Controle positivo:** acrescentar raiz ao E5 sem entrada no registro ⇒ a métrica
      **cai** e/ou o gate reprova. Hoje ambos ficam verdes. — `test_lineage_coverage.py`.
      Falsificado ponta-a-ponta: injetada raiz monetária na fixture do gate novo, ele foi a
      **vermelho**; revertido, volta a verde. A assimetria com `check_lineage_refs` é
      **estrutural, não testável** — aquele gate recebe o `registry`, nunca o payload, logo
      não existe mutação de payload que ele possa enxergar. (Um teste chamado "inerte à mesma
      mutação" asseveraria mutação que nunca aplica; foi removido no closeout, e o verde dele
      sobre o registry real já é coberto por `test_check_lineage_refs_green_on_real_registry`.)
- [x] O eval deixa de derivar `expected` do registro que ele avalia. — `cases._EXPECTED_REFS`
      literal + cross-check por `rule_id`. Falsificado: apontar `patrimonio.liquido` para
      outro enforcer reprova o novo assert e passa **verde** na forma derivada.

## O que esta lane NÃO fecha

Os 9 blocos monetários sem rastro **continuam sem rastro** — a lane entrega a **medida** e o
**gate**, não a cobertura. O KR nasce em 35,7% de propósito: é o número que torna a dívida
contável e impede que ela cresça calada. Fechar cada raiz é trabalho de emissor
(`e5_lineage.py` + entrada no registro), dimensionável agora que existe denominador.

## Nota de materialidade

**Inerte para o usuário hoje:** o selo de proveniência por campo
(`_lineage.fields` → popover no valor monetário) está atrás de flag com default `False`,
ausente do `flags_json` do workspace de dogfood. O custo vivo é interno — localização de
número — e é o que a [[ADR-281]] existe para baratear.
