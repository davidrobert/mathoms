---
id: A40.l28
type: lane
title: "Idade-meta do cone é output do modelo, não pergunta da família — e o rótulo do percentil aponta para dois lados"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l28-idade-meta-e-rotulo-do-cone
adrs:
  - "[[ADR-237]]"
  - "[[ADR-219]]"
depends_on: []
parallel_with:
  - "[[A40.l25]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/financial-planning
---

# A40.l28 — `idade-meta-e-rotulo-do-cone`

> **Residual de contrato da `ADR-361` (PR #1162), itens 1 e 2 do §Deferimento.**
> A [[A40.l25]] pegou o item 5 (faixa de 5 pp) e o residual da [[ADR-360]]; estes
> dois ficaram sem destino. São contrato/payload — não dependem de brief de
> design, ao contrário da [[A40.l29]].
>
> `ADR-361` fica sem wikilink até #1162 mergear (`check_doc_links` hard-falha em
> alvo inexistente). Religar é parte do merge dela.
>
> Entra na A40 pela **KR-E** (honestidade da recomendação): as duas faces são
> números que dizem medir uma coisa e medem outra.

## Problema

### 1. `prob_if_ate_idade_meta` mede o modelo contra si mesmo

`e5_analyzer_adapter.py` chama `run_monte_carlo_if(..., idade_meta_if=
if_projection.idade_titular_if)` — a idade-meta é a **saída do projetor
determinístico**, não um alvo que a família declarou. Como
`horizonte_meta = idade_meta_if − idade_titular_atual` é exatamente o prazo
determinístico, a métrica publicada é:

> P(o Monte Carlo bate a data que o card determinístico logo acima imprimiu).

E como `mu_log = log(1+r) − ½σ²`, a mediana simulada fica **estruturalmente**
atrás do determinístico. Medição feita no co-design da `ADR-361`, oito planos
deliberadamente distintos (PV de R$ 300 k a R$ 5 M, meta de R$ 2 M a R$ 20 M,
aporte de R$ 2 k a R$ 30 k):

| PV | meta | aporte/mês | prazo det. | `prob` publicada |
|---|---|---|---|---|
| 500 k | 3 M | 5 k | 18,3a | 41,2% |
| 500 k | 3 M | 15 k | 9,6a | 31,1% |
| 1,5 M | 5 M | 8 k | 14,3a | 42,5% |
| 2 M | 4 M | 3 k | 11,2a | 45,9% |
| 300 k | 10 M | 20 k | 21,6a | 37,8% |
| 5 M | 8 M | 10 k | 6,9a | 38,5% |
| 800 k | 2 M | 2 k | 13,5a | 42,8% |
| 4 M | 20 M | 30 k | 18,0a | 44,1% |

**Amplitude de 14,8 pp entre planos radicalmente diferentes.** É praticamente
constante de modelo, não métrica do cliente — e é publicada como
"~44% de chance de {titular} alcançá-la até os {idade} anos".

A `ADR-361` §Deferimento item 1 registrou isto como **maior que o defeito que
ela corrigiu**. Não existe campo de idade-meta em
`goals.independencia_financeira` (só `if_meta`, `trs_pct`,
`taxa_retirada_segura_pct`, `retorno_real_anual_pct`) — é campo novo.

### 2. `p10` significa o oposto de `p10` no mesmo payload

- `p10_ano_if` = percentil 10 do **tempo** = o décimo mais rápido = **favorável**
- `caminho_p10` = percentil 10 do **patrimônio** = o décimo mais pobre = **adverso**

Mesmo sufixo, orientação oposta, mesmo bloco. A legenda do gráfico já diz
"P10 — cenário adverso" enquanto o campo de ano ao lado quer dizer o contrário.
A `ADR-361` deixou o rename fora de propósito, para não misturar mudança de
contrato com correção estatística — mas o v3.0 circulando com o rótulo ambíguo
fica mais caro de desfazer a cada consumidor novo.

## Escopo

1. **`idade_meta_if` vira input** em `goals.independencia_financeira` (default
   65, editável), com migração de leitura no adapter. Enquanto não houver valor
   declarado, a **única probabilidade honesta é `prob_if_ate_horizonte`** (já
   publicada pela `ADR-361`) — `prob_if_ate_idade_meta` não sai.
2. **Rename** `p10_ano_if`/`p90_ano_if` → `ano_if_cenario_favoravel` /
   `ano_if_cenario_adverso` (e as flags de censura junto), com `mc_version`
   bumpado. Toca payload, `config/schemas/e5_analysis.schema.json`, tipos TS,
   catálogo de citação do parecer e snapshot do dogfood.

## Co-design obrigatório antes de codar

- `financial-planner` — a idade-meta é pergunta de planejamento, não parâmetro
  técnico: default, quem edita, o que acontece no casal com idades diferentes.
- `data-engineer` — rename de campo em contrato v3.0 recém-publicado: bump de
  `mc_version` para 4.0 ou emenda ao 3.0, e o que fazer com artefato já gravado.

## Critério de aceite

- Nenhuma superfície publica `prob_if_ate_idade_meta` medida contra uma
  idade-meta derivada do próprio modelo; teste que falha se o adapter voltar a
  passar `if_projection.idade_titular_if`.
- Grade de ≥6 planos distintos: a `prob` publicada tem amplitude **> 30 pp**
  (hoje é 14,8 pp — se continuar estreita, a métrica ainda não discrimina plano).
- Nenhum campo do payload usa `p10`/`p90` como rótulo user-visible ou de
  contrato; grep de `p10_ano_if` retorna 0 fora de compat de leitura.
- `mc_version` bumpado e a mudança entra na nota de recalibração pendente no
  dono (§Entregas fora de lane).
- Verificação renderizada da S7 (§Débito de método desta sprint) — a lane não
  fecha sobre inferência de código.

## Fora de escopo

- Faixa de 5 pp na probabilidade e `sigma` por perfil — [[A40.l25]].
- Ramos faltantes do `_solve_prazo` — [[A40.l26]].
- Aposentar o ano do MC como manchete, inverter o eixo para "quanto", componente
  de faixa na UI — [[A40.l29]] (dependem de brief de `product-designer`).
