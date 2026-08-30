---
id: A42.l18
type: lane
title: "A perna de valor da conservação E3→E4 é inerte: `dups` é literal e os dois lados somam `abs()` da mesma população"
sprint: A42
status: open
priority: P1
branch_slug: a42-l18-perna-de-valor-e3e4-inerte
owner: data-engineer
depends_on: []
adrs: ["[[ADR-342]]", "[[ADR-347]]"]
tags: [type/lane, sprint/a42, status/open, priority/p1, area/dados]
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

- [ ] O campo `dups` da transição E3→E4 recebe a contagem real, ou a perna declara
      explicitamente que não a mede (e o veredito passa a `coberto-sem-verificação`).
- [ ] As duas pernas de valor deixam de somar `abs()` sobre a mesma população, **ou** o
      veredito declara por escrito que não discrimina sinal nem dedup.
- [ ] **Controle positivo obrigatório:** inverter o sinal de N débitos numa fixture E3 e
      re-rodar. Se `Δvalor` continuar `0`, a perna segue inerte e o conserto não fechou.
- [ ] Segundo controle: remover `dedup_collapsed` do lado destino e verificar se o veredito
      vira `perda-silenciosa` por exatamente 858 — se não virar, o termo é load-bearing e
      não-verificado.

## Fora de escopo

Não reabre a decisão de **onde** o veredito é computado ([[A42.l14]]), nem o
`list_keys` run-scoped ([[A42.l7]] / `DE-4`).
