---
id: A27.l2
type: lane
title: "A cobertura do grafo de lineage não é medida por gate nenhum, e o eval fecha o laço sobre o próprio registro"
sprint: A27
status: open
priority: P2
branch_slug: a27-l2-cobertura-de-lineage-sem-gate
owner: data-engineer
depends_on: []
adrs: ["[[ADR-281]]"]
tags: [type/lane, sprint/a27, status/open, priority/p2, area/dados]
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

`lineage_debug_whitelist()` tem **8 campos**, que expandem para 241 paths concretos mas
vivem sob **5 raízes**. Contra o **payload** publicado (42 chaves de topo): **37 (88%)** sem
rastro. Contra o **schema** do E5 (38 raízes declaradas): **~87%**. Dizer "as raízes do E5"
sem dizer qual é o vício que esta lane existe para consertar.

**Efeito na rodada unificada:** é por isso que 37 dos 42 blocos saem `sem-veredito` na
tabela de condicionamento — a cegueira é do **registro de lineage**, não falta de balde.
Regra ternária em [[LEDGER-CERTIFY-active]] §r6 §10.

## Critério de aceite

- [ ] Existe um **KR de cobertura** = raízes com nó ÷ raízes do payload, com o denominador
      vindo do **payload publicado**, nunca do registro.
- [ ] **Controle positivo:** acrescentar raiz ao E5 sem entrada no registro ⇒ a métrica
      **cai** e/ou o gate reprova. Hoje ambos ficam verdes.
- [ ] O eval deixa de derivar `expected` do registro que ele avalia.

## Nota de materialidade

**Inerte para o usuário hoje:** o selo de proveniência por campo
(`_lineage.fields` → popover no valor monetário) está atrás de flag com default `False`,
ausente do `flags_json` do workspace de dogfood. O custo vivo é interno — localização de
número — e é o que a [[ADR-281]] existe para baratear.
