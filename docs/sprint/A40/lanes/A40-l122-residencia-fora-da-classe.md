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

> ⚠️ **2026-10-09 — PR-B mergeado (#2233); a lane segue `in_progress` pelo PR-D.** Os critérios
> 1–4 estão entregues e medidos, e o item 1 do §Deferimento da [[ADR-444]] ficou nesta lane. Ver
> §Execução de 2026-10-09.

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
| PR-0 [#2079](https://github.com/davidrobert/mathoms/pull/2079) | `imovel_valor` nos dois analyzers ([[ADR-431]]) + roteador único `imovel_na_carteira` + config morto fora | ✅ mergeado 2026-10-09 (`574e1290`) |
| PR-A [#2096](https://github.com/davidrobert/mathoms/pull/2096) | expand: schema (enum + `pct` nullable discriminado + `total_imoveis_uso_nao_apurado` + `classificacao_imovel`), TS, leitores null-safe, copy, manifesto do parecer | ✅ mergeado 2026-10-09 (`afe36fdc`), sem o manifesto do parecer ([[ADR-444]] §Correção 2026-10-09) |
| PR-B [#2233](https://github.com/davidrobert/mathoms/pull/2233) | flip: produtor + gate de efeito com mutação + rebaseline | ✅ mergeado 2026-10-09 (`0ab28e9a`) |
| PR-C | superfícies LLM: hint de concentração com ressalva, regime da residência no parecer, exceção no tom da S3, guarda determinística de prescrição, eval do dono — um bump de manifesto ([[ADR-444]] §Deferimento 5) | dividido 2026-10-09: alcance ➜ [[A40.l8]]; guarda e tom da S3 ➜ [[PLAN-report-trust]] §Deferimentos da A40.l122 |
| PR-D | item 1 do §Deferimento da [[ADR-444]]: `uso_pessoal` e `nu_proprietario` fora do ranking ([[ADR-420]] §D1) — o subtítulo do card promete e é falso | aberto, P1 — §Execução de 2026-10-09 |

> **Nota 2026-10-09 ([[A40.l123]], #2117).** Duas peças do PR-C já saem no manifest 2.21.0
> do parecer: o veredito da residência (`status` e `motivo`, com o regime de leitura nos
> hints) e a ressalva da concentração com fatia sem classificação (hint em `ratios`: teto,
> sem prescrição de venda de imóvel). O PR-C parte delas em vez de refazê-las. **Quando o
> PR-B mover** o imóvel de uso não apurado para a linha própria, o trecho do hint de `ratios`
> que chama "imóveis de investimento" de TETO deixa de valer para a linha da tabela —
> revisar no PR-C. A concentração segue teto enquanto o numerador da [[ADR-420]] §D2 não
> mudar.
>
> Do item 5 do §Deferimento da [[ADR-444]], **não** saíram: o `piso` da residência (o
> parecer não recebe o número dela, e `prompt-engineer` + `financial-planner` o julgaram
> redundante com a fatia em % — volta à mesa se a linha própria mudar isso), a exceção de
> tom da S3, a guarda determinística e o eval. O PR-C sobe a próxima MINOR do manifest: o
> "2.20.0 × 2.21.0" do item 5 não existe mais (a 2.21.0 foi da A40.l123, e a `main` já
> passou dela). Ao flipar a [[ADR-444]], reconcilie o item 5 com o que já saiu.

## Critério de aceite

1. Fixture com a residência sem `property_id` e override `residencia_principal` gravado: hoje
   ela é contada como investimento; depois, a tabela e o ranking **não podem afirmar isso** —
   prova por mutação (predicado sempre falso ⇒ vermelho; sempre verdadeiro ⇒ vermelho no
   regime identificado).
2. Matriz de regimes com oráculo tirado do estado de DB da fixture, nunca do veredito.
3. Conservação em centavos: `total = total_financeiro + total_imoveis_investimento` e
   `total + total_imoveis_uso_nao_apurado = Σ tabela`; alocação byte-idêntica.
4. U5 sem número movido; só nomes de item e prosa do insight.

## Execução de 2026-10-09 — o flip entrou, e a lane segue aberta pelo PR-D

- **PR-B [#2233](https://github.com/davidrobert/mathoms/pull/2233) mergeado** (`0ab28e9a`). A [[ADR-444]] fica `Decidido`, com
  §Correção 2026-10-09: o manifesto do parecer não entrou no expand, e o adiado ganha destino.
- **Critérios 1–3:** gate `tests/test_carteira_residencia_gate_adr444.py`, com oráculo do estado
  de DB da fixture, oito regimes, mutação do predicado (sempre verdadeiro e sempre falso) e
  conservação em centavos.
- **Critério 4, re-medido depois do merge** no run `40d1af2a`, com o código de `main`: veredito
  da residência `apurado` com `piso`, predicado falso. Classes e ranking comparados contra o
  predicado forçado a falso (o caminho de antes do flip): 0 de 29 campos movidos. Os 5 imóveis
  do ranking são de uso desconhecido e passam a "Imóvel com uso não apurado"; o #1 é um deles,
  e sob `piso` a prosa do ranking sai sem a linha de diversificação (D5) — medido no narrador
  sobre o mesmo ranking; com `piso` falso, a linha volta.
- **Manifesto de golden drenado** para `[]`. Com os 3 waivers, um PR que tocasse
  `dogfood_view_model.json` sem mover dinheiro saía `exit 1` com 3 órfãs; drenado, `exit 0`.

### Por que a lane não fecha

O item 1 do §Deferimento é do roteador que esta lane possui (`imovel_na_carteira.py`; critério
de admissão 1 da [[MOC-sprint-a42]]). Com a lane fechada, ele só sairia da A40 ou viraria lane
nova, que o critério 2 veda (`product-manager`, 2026-10-09). Medido no mesmo run: 9 imóveis
consolidados, 1 com `property_id`; os overrides `nu_proprietario` (1) e `locado` (4) estão
órfãos e os itens caem no desconhecido. Com a chave de três níveis que a [[A40.l121]] mediu (6
de 6 overrides re-alcançados; só `via_numero` deixa o `nu_proprietario` órfão), ele volta a
casar e sai como "Imóvel de investimento", com peso, no run que abre o contador da cláusula
ONZE. A lane já está na cláusula, e o custo é zero enquanto a l121 espera.

**PR-D.** Antes do código, o `financial-planner` decide se a exclusão vale só no ranking ou na
carteira toda (a segunda move o U5), e o `product-designer` faz a copy do subtítulo do card.
Disjuntor: se a [[A40.l121]] fechar antes, sai só a copy no frontend (via `classificacao_imovel`)
e o resto vai para o [[PLAN-report-trust]] §Deferimentos da A40.l122.

O PR-C e os itens 2–6 do §Deferimento: [[ADR-444]] §Correção 2026-10-09, item 3.
