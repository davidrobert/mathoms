---
id: A42.l18
type: lane
title: "A perna de valor da conservação E3→E4 é inerte: `dups` é literal e os dois lados somam `abs()` da mesma população"
sprint: A42
status: shipped
ship_pr: 1870
ship_date: "2026-08-30"
priority: P1
branch_slug: a42-l18-perna-de-valor-e3e4-inerte
owner: data-engineer
depends_on: []
adrs: ["[[ADR-342]]", "[[ADR-347]]", "[[ADR-426]]"]
tags: [type/lane, sprint/a42, status/shipped, priority/p1, area/dados]
---

# A42.l18 — `perna-de-valor-e3e4-inerte`

> **Origem:** `N1` da rodada unificada **U4** ([[LEDGER-CERTIFY-active]] §r8).
> Levantado pela lente de razão, **verificado no produtor pelo loop principal**.
> Classe `saúde-harness`/falso-verde — a que esta sprint existe para matar.

## O defeito

O veredito `conservado` da transição **E3→E4** não pode falhar. Duas provas, ambas no
produtor:

1. **`dev/ledger_conservation.py:265`** passa **`0` literal** no campo `dups` do
   `ConservationResult` da transição E3→E4. A linha **160**, que constrói o
   `ConservationResult` de E2→E3, passa a variável real. O contador de duplicatas dessa
   perna **só pode dar zero**.
2. **`dev/ledger_certify_core.py:244`** (`_classified_cents`) e
   **`dev/ledger_conservation.py:215`** (`_survivor_value_cents`) somam **ambos**
   `abs(valor)` sobre a **mesma população pré-dedup**. O docstring do primeiro declara:
   *"pré-dedup, mesmo conjunto que as tx E3 não-puladas"*.

Logo `Δvalor = 0 ⇒ conservado` é invariante a **(a)** inversão de sinal débito↔crédito e
**(b)** às **858** rows que o dedup do E4 remove. É uma identidade de um conjunto consigo
mesmo, módulo o skip do classificador.

## Por que importa mais do que parece

O veredito desta perna é a **base** de toda a tabela de condicionamento da rodada
unificada. Ao rebaixá-lo durante a `U4`, o braço cego teve de re-executar — e a resposta
**mudou**: 3 alavancas caíram de rebaixadas para **inadmissíveis**, 1 subiu a admissível, e
a forma da justificativa da ação nº 1 migrou de *"vale mais"* para *"é a única
demonstrável sem valor"*. Com nenhum bloco em `conservado`, **nenhuma comparação monetária
entre alavancas é admissível em lugar nenhum do relatório**.

## Critério de aceite

- [x] O campo `dups` da transição E3→E4 recebe a contagem real (`dedup_collapsed`) —
      [[ADR-426]] §D4.
- [x] As duas pernas de valor deixam de somar `abs()` sobre a mesma população: o
      lado-saída passa a ser o **destino declarado pelo produtor** (baldes +
      `transferencias_cents` + `dedup_collapsed_cents`), não uma re-soma da origem —
      [[ADR-426]] §D1/§D2. A metade **sinal** fica declarada por escrito (§Residual).
- [x] **Controle do dedup** (o que discrimina de fato): com a cadeia real, uma row
      duplicada produz `collapsed_cents = 180000`; suprimir a declaração derruba o
      veredito para `coberto-sem-verificação-de-valor`. Contrafactual rodado: o gate
      novo falha 2/4 contra o código pré-fix e **4/4** contra o subconjunto
      "harness corrigido, produtor pré-fix" — as duas metades são conjuntamente
      necessárias. `tests/dev/test_ledger_e3e4_valor_nao_inerte.py`.
- [x] Segundo controle: zerar `dedup_collapsed` no lado destino vira `perda-silenciosa`;
      suprimir `dedup_collapsed_cents` vira `coberto`. O termo é load-bearing **nos dois
      eixos** e agora é verificado. (O número 858 é do run de dogfood da `U4` e não é
      reproduzível fora dele; o que o gate crava é o mecanismo, com o valor exato da
      fixture.)

## Correção do enunciado — o controle de sinal não era satisfazível

> **2026-08-30.** O controle positivo prescrito acima ("inverter o sinal de N débitos;
> se `Δvalor` continuar `0`, o conserto não fechou") **não pode ser satisfeito por uma
> perna de conservação E3→E4**, e a linha original teria condenado qualquer conserto
> correto. Medido: nas **62** transações das fixtures, **nenhuma declara `tipo` no nível
> da tx** — a direção é *derivada do sinal* (`_normalize_tipo`). Não há segunda
> declaração independente para discordar do sinal, então não existe testemunha contra a
> qual uma inversão possa ser detectada. Quando `tipo` existe, o classificador aplica
> `abs(valor)` na despesa e a discordância atravessa sem rastro. Erro de sinal é
> **fidelidade do E3** (perna E2→E3 / `parse-certify`), não conservação desta transição.
> O critério foi substituído pelo controle do **dedup**, que discrimina de verdade.
> Rationale completo em [[ADR-426]] §Consequências.

## Residual declarado (não é silêncio)

A perna **não discrimina sinal**. A fronteira está escrita em três lugares que
envelhecem juntos: comentário de seção em `dev/ledger_conservation.py`, [[ADR-426]]
§Consequências, e o teste
`test_perna_nao_discrimina_sinal_e_a_limitacao_esta_declarada` — que falha se algum dia
a perna passar a discriminar, forçando a emenda da ADR.

## Fora de escopo

Não reabre a decisão de **onde** o veredito é computado ([[A42.l14]]), nem o
`list_keys` run-scoped ([[A42.l7]] / `DE-4`).
