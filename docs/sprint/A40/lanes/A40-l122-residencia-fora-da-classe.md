---
id: A40.l122
type: lane
title: "A casa da família entra na carteira de investimentos quando a residência não é apurada: tabela de classes e ranking falham ABERTO"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P1
branch_slug: a40-l122-residencia-fora-da-classe
owner: data-engineer
depends_on: []
adrs: ["[[ADR-444]]", "[[ADR-439]]", "[[ADR-433]]", "[[ADR-420]]", "[[ADR-412]]"]
tags: [type/lane, sprint/a40, status/in-progress, priority/p1, area/pipeline, area/financial-planning]
---

# A40.l122 — `residencia-fora-da-classe`

> **Origem:** elo 5 da cadeia da [[A40.l113]], confirmado na medição de 2026-09-01 e nunca
> roteado; a [[ADR-439]] o declarou "Fora desta ADR". Desdobramento aberto em 2026-10-08.

## O defeito

`investimentos_classes_analyzer` e `top_ativos_analyzer` decidiam "é a residência?" só por
`pid in residencia_property_ids`. Imóvel sem `property_id`, ou sem override, caía em "Imóveis
Investimento" — inclusive a casa. Falha **aberta**, ao contrário do `patrimonio`, que a
[[ADR-439]] tornou honesto. Regimes vivos: a residência perde o id no run (era `1.4.1` do
E1.5a, [[A40.l121]]) e o workspace que nunca a marcou (default de workspace novo).

## O que está medido (run `40d1af2a`, só traços)

| eixo | resultado |
|---|---|
| residência no run | tem `property_id` + override ⇒ excluída; o defeito é **latente** aqui |
| contrafactual: só a residência perde o id | `total` ×1,555 · `total_imoveis_investimento` ×1,742 · Renda Fixa `pct` 22,70 → 14,60 · casa **#1 do ranking**, 35,7%, "Imóvel de investimento" + "considere diversificação" |
| `total_financeiro` e `nao_classificado_pct` no contrafactual | razão 1,0000 e 5,61 nos dois lados |
| desconhecidos com valor vs. residência | nenhum com razão 1,0 ou 0,5 — a classe não contém a casa neste run |

⚠️ **Premissa recebida e refutada.** O registro da [[A40.l113]] atribuía a este elo
`total_financeiro` encolhendo e `nao_classificado_pct` subindo 3,93 → 5,61 pp "sem o numerador
crescer". A base dos dois já exclui imóvel físico (A37.l9); o 5,61 do U5 tem outra causa.

Dos três analyzers do enunciado, `instituicoes_por_membro` **não** era afetado: recebia o set e
nunca o lia (conta todo imóvel, por paridade com o legado). O `MemberAnalyzer` tem o mesmo
padrão e não roda em produção.

## Decisão

[[ADR-444]] (`Proposto`): com a residência `nao_apurado` (os quatro motivos, `sem_valor`
incluso), imóvel de classificação desconhecida entra **com valor e sem peso** na linha "Imóveis
com uso não apurado"; nenhuma prescrição de diversificação recai sobre o que pode ser a
residência (item sem peso, ou desconhecido sob `piso`); o resíduo `apurado` + `piso` (cota do
cônjuge sem id) é declarado no schema e no parecer.

## Entregas

| PR | conteúdo | estado |
|---|---|---|
| PR-0 [#2079](https://github.com/davidrobert/mathoms/pull/2079) | `imovel_valor` nos dois analyzers ([[ADR-431]]) + roteador único `imovel_na_carteira` + config morto fora | aberto |
| PR-A | expand: schema (enum + `pct` nullable discriminado + `total_imoveis_uso_nao_apurado` + `classificacao_imovel`), TS, leitores null-safe, copy, manifesto do parecer | — |
| PR-B | flip: produtor + gate de efeito com mutação + rebaseline | — |
| PR-C | superfícies LLM: hint de concentração com ressalva, regime da residência no parecer, exceção no tom da S3, guarda determinística de prescrição, eval do dono — um bump de manifesto ([[ADR-444]] §Deferimento 5) | — |

> **Nota 2026-10-09 ([[A40.l123]], #2117).** Duas peças do PR-C já saem no manifest 2.21.0
> do parecer: o veredito da residência (`status` e `motivo`, com o regime de leitura nos
> hints) e a ressalva da concentração com fatia sem classificação (hint em `ratios`: teto,
> sem prescrição de venda de imóvel). O PR-C parte delas em vez de refazê-las. **Quando o
> PR-B mover** o imóvel de uso não apurado para a linha própria, o trecho do hint de `ratios`
> que chama "imóveis de investimento" de TETO deixa de valer para a linha da tabela —
> revisar no PR-C. A concentração segue teto enquanto o numerador da [[ADR-420]] §D2 não
> mudar.

## Critério de aceite

1. Fixture com a residência sem `property_id` e override `residencia_principal` gravado: hoje
   ela é contada como investimento; depois, a tabela e o ranking **não podem afirmar isso** —
   prova por mutação (predicado sempre falso ⇒ vermelho; sempre verdadeiro ⇒ vermelho no
   regime identificado).
2. Matriz de regimes com oráculo tirado do estado de DB da fixture, nunca do veredito.
3. Conservação em centavos: `total = total_financeiro + total_imoveis_investimento` e
   `total + total_imoveis_uso_nao_apurado = Σ tabela`; alocação byte-idêntica.
4. U5 sem número movido; só nomes de item e prosa do insight.
