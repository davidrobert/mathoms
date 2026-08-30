---
id: A40.l86
type: lane
title: "Duas fontes decidem se uma folha é dinheiro: o format declarado no manifest e o palpite pelo nome do campo"
sprint: A40
plan: PLAN-deterministic-authority
status: open
priority: P2
branch_slug: a40-l86-duas-fontes-de-monetariedade
adrs:
  - "[[ADR-279]]"
  - "[[ADR-296]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/llm
  - area/pipeline
---

# A40.l86 — Duas fontes de monetariedade (follow-up da [[A40.l83]])

> **O manifest declara; o catálogo adivinha.** Quando discordam, o efeito não é erro
> visível: é folha R$ que o modelo vê no corpo e não consegue citar — e o prompt manda
> literalmente não ancorar o que não está no catálogo.

## O fato

Duas respostas independentes para "esta folha é dinheiro?":

1. **Declarada** — `config/prompts/parecer_planejador.yaml` diz `format: brl` no campo.
   É o que decide se o corpo imprime `R$`.
2. **Adivinhada** — `_MONEY_KEY_TOKENS` em `parecer_citation_catalog.py` casa substring
   no **nome** do campo. É o que decide se a folha entra no catálogo de citação.

Medido no E5 real do run `d0f6260a` (A40.l83), elas discordam em 3 campos:

| path | manifest | `_is_money_key` | desfecho |
|---|---|---|---|
| `$.patrimonio.investimentos_nao_atribuidos` | `brl` | não casava | resolvido no #1714 adicionando o token `investimento` |
| `$.fluxo_caixa.janela_12m.transferencia_patrimonial` | `brl` | não casa (`patrimonial` ≠ `patrimonio`) | **inancorável** |
| `$.consumo_consciente.teto_sugerido` | `brl` | não casa (`teto` fora da lista) | **inancorável** — ⚠️ campo **extinto** do contrato em 2026-08-29 ([[ADR-422]] D2 · #1828); a linha fica como medição datada do run, mas o ofensor não existe mais |

O token `investimento` foi adicionado com raio medido (+6 entries, todas monetárias) —
mas isso é remediar instância, não classe. A próxima folha `brl` cujo nome não casar
nenhum dos ~28 tokens reabre o mesmo buraco, em silêncio.

## Por que não é "adicione mais tokens"

`_is_money_key` tem **dois consumidores**, e eles querem coisas diferentes:

- `_is_money_leaf` → inclusão no catálogo (quer o conjunto declarado pelo manifest);
- `ancora_format_hint` → dispatch de formatação no finalize ([[ADR-296]]) (quer o
  formato da folha, que o manifest também declara).

Ambos estão reimplementando, por heurística de nome, um fato que o manifest **já
declara por campo**. A lista de tokens ainda carrega o veto `_NON_MONEY_MARKERS`
(`pct`, `count`, `qtd`…), que existe só para desfazer falsos-positivos da própria
heurística.

## Armadilhas

**O catálogo é BRL-only por construção** (`_entry_for` → `format_value(v, "brl")`), e
isso é decisão vigente, não descuido — valor em US$ não tem rota de âncora e a
[[ADR-304]] §"evidência inflada" trata US$ na prosa como fabricação. Consumir o `format`
declarado sem filtrar por moeda arrastaria folha `usd` para dentro do catálogo.

**Nem toda folha citável vem do manifest.** O catálogo caminha o E5 inteiro
(`_iter_money_leaf_paths`), não só o projetado — por desenho, para o modelo poder citar
conceito que o corpo não imprime. Trocar a heurística pela declaração **encolheria** o
catálogo ao conjunto projetado. A saída provável é união: declarado ∪ adivinhado, com o
declarado tendo precedência no `format_hint`.

**`ancora_format_hint` tem ordem carregada de precedente** — `prob` vence `reserva` em
`prob_reserva_ideal`, `nivel_N_meses` é R$ e não meses. Trocar a fonte sem preservar
essas resoluções reabre o dogfood `72883bde`.

## Escopo

| peça | superfície |
|---|---|
| fonte declarada | leitor que extrai `path → format` do manifest (existe parcialmente em `declared_fields`) |
| união e precedência | `parecer_citation_catalog._is_money_leaf` + `ancora_format_hint` |
| gate | folha `format: brl` projetada no manifest e ausente do catálogo construído reprova |

## Critério de aceite

**Corretude** — `transferencia_patrimonial` vira citável sem que nenhum token novo seja
adicionado à heurística.

> **Emenda 2026-08-30 ([[ADR-422]] D2 · #1828).** O critério pedia também `teto_sugerido`,
> que **saiu do contrato do E5** — o catálogo só emite entry para folha presente no payload,
> então essa metade era **mecanicamente insatisfazível**. Os ofensores medidos caem de 2 para
> 1. A tabela de medição acima é snapshot do run `d0f6260a` e **não** se reescreve ([[ADR-343]]);
> ganhou só a anotação de extinção.

**Consistência** — um único produtor responde "esta folha é dinheiro?"; a heurística por
nome sobrevive apenas como fallback para folha **não projetada**, com essa condição
declarada no código.

**Prova por mutação** — remover um `format: brl` do manifest tem de derrubar o gate
novo; adicionar folha `brl` projetada e ausente do catálogo também.

**Precisão** — `_NON_MONEY_MARKERS` encolhe ou ganha justificativa por entrada: veto que
existe para desfazer falso-positivo da própria heurística é dívida da heurística.

## Rastro

Follow-up da [[A40.l83]] §Fecho, residual 1. Medições no corpo do #1714 (raio do token
`investimento`) e no `_comment` de `dev/snapshots/parecer_ancorabilidade.json`.
