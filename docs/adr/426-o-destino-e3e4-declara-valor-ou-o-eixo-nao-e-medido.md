---
id: ADR-426
type: adr
title: "O destino E3→E4 declara valor, ou o eixo-valor não é medido"
status: Decidido
phase: A42
date: "2026-08-30"
amended_at: ["2026-09-01"]
relates_to:
  - "[[ADR-434]]"
  - "[[ADR-347]]"
  - "[[ADR-342]]"
  - "[[ADR-255]]"
  - "[[ADR-279]]"
  - "[[ADR-173]]"
  - "[[ADR-090]]"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/dados
  - sprint/a42
aliases: ["ADR 426", "conservacao de valor E3-E4", "dedup_collapsed_cents"]
---

# ADR-426 — O destino E3→E4 declara valor, ou o eixo-valor não é medido

> ⚠️ **Emendada em 2026-09-01 ([[A42.l25]]).** A **fórmula** do §D2 caiu: somar
> `total_geral` dos dois baldes misturava duas convenções de sinal entre os quatro termos
> e o destino saía `2 × Σ|receitas negativas|` menor **sempre**. A tese (D1/D3/D4/D5)
> continua de pé. Ver §Emenda no fim e a [[ADR-434]].

**Status:** Decidido (A42.l18 · #1870 `cfaf3f38`) • **Data:** 2026-08-30 • **Dono:** `data-engineer`.
Estende ao E3→E4 a tese que a [[ADR-347]] §Dec-6 já fixou para o E2→E3.

## Contexto medido (2026-08-30)

A perna de valor da transição E3→E4 do `ledger-certify` **não podia falhar**. Duas
causas independentes, ambas no produtor:

1. `dev/ledger_conservation.py` passava **`0` literal** no campo `dups` do
   `ConservationResult` de E3→E4 — a perna E2→E3, na mesma função, passava a
   variável real. O contador de duplicatas desta perna só podia dar zero.
2. `_classified_cents` (harness) e `_survivor_value_cents` (harness) somavam
   **ambos** `abs(valor)` sobre a **mesma população pré-dedup**. `Δvalor = 0` era
   identidade de um conjunto consigo mesmo, não medição.

Medição na fixture golden (`tests/fixtures/pipeline_golden/dogfood/`): Σ|classified|
pré-dedup = **7500,00**; soma dos baldes = **4500,00**. Os **3000,00** que o dedup do
E4 colapsou eram invisíveis ao veredito, que dizia `conservado`.

Controle positivo com a cadeia real (classificador → `CashFlowBuilder` →
`conferencia_signals`): duplicar uma row inflava **os dois lados igualmente** e `Δ`
continuava `0`.

## Decisão

**D1 — O produtor declara o valor do destino.** `DedupReport` ganha
`collapsed_cents` (Σ |valor| das rows removidas) e `CashFlow` ganha
`transferencias_cents` (Σ |valor| pós-dedup das transferências, que não têm balde
serializado com total). Ambos viajam em `despesas._lineage.signals` como
`dedup_collapsed_cents` / `transferencias_cents`. É a mesma forma de prova que a
[[ADR-347]] §Dec-6 adotou para o E2→E3 via `remocoes[*].valor_cents`.

**D2 — O harness lê a declaração; não re-soma a origem.** O lado-saída passa a ser
`despesas.total_geral + receitas.total_geral + transferencias_cents +
dedup_collapsed_cents`. É a soma que o relatório mostra, produzida por outro código
que não o da origem — não uma segunda passada sobre a mesma lista.

**D3 — Ausência de declaração é `coberto-sem-verificação-de-valor`.** Artefato
pré-ADR-426 não tem os dois sinais: o eixo-valor fica **não medido**, nunca
"mediu e deu zero". Mantém-se o WARN-first da política anterior — divergência de
valor nunca sobe a `perda-silenciosa`, para não fabricar P0 por convenção de sinal.

**D4 — `dups` da perna E3→E4 recebe `dedup_collapsed`.** O campo passa a ter o mesmo
significado das duas pernas.

**D5 — Os sinais novos ficam fora de `_CONFERENCIA_SIGNAL_KEYS`.** O whitelist do E5
é o que impede a chave de cache do parecer de mudar ([[ADR-173]] hard-stop). O
artefato E4 declara; o E5 não propaga.

## Consequências

**O que a perna passa a discriminar:** valor removido pelo dedup do E4 e não
declarado; tx que classifica mas não entra em balde; distorção de magnitude no
balde (classe do bug ISO 100× de r5/M28); categoria contada duas vezes.

**O que a perna NÃO discrimina — e por que não é conservável aqui.** Erro de
**sinal** já presente no E3 e propagado fielmente pelo E4. Medido: **nenhuma**
transação das fixtures declara `tipo` no nível da tx (0 de 63 (medido 2026-08-31)) — a direção é
*derivada do sinal* por `_normalize_tipo`. Não existe segunda declaração independente para
discordar do sinal. Quando `tipo` existe, o classificador aplica `abs(valor)` na
despesa e a discordância atravessa sem rastro. Isso é **fidelidade do E3** — perna
E2→E3 e `parse-certify` —, não conservação desta transição.

> O controle positivo prescrito pela [[A42.l18]] ("inverter o sinal de N débitos;
> se `Δ` continuar `0`, o conserto não fechou") **não é satisfazível** por uma perna
> de conservação E3→E4, pelo motivo acima. O critério foi corrigido na lane; o
> controle que discrimina de fato é o do **dedup**, e esse a perna passou a exercer.

**Estado intermediário é pior que hoje.** Corrigir só o harness, sem a declaração do
produtor, derruba **todo** veredito para `coberto` sem ganho de discriminação
(verificado: 4/4 testes do gate falham nesse subconjunto). As duas metades são
conjuntamente necessárias — mesma advertência de faseamento da [[ADR-347]].

**Custo.** Dois campos int por run no artefato `despesas`. Zero mudança de
comportamento no relatório: nenhum consumidor lê os sinais novos.

## Alternativas rejeitadas

- **Declarar a perna inerte por escrito e parar** (o "ou" do critério da lane).
  Rejeitada: deixaria a tabela de condicionamento da rodada unificada sem nenhum
  bloco em `conservado`, e nenhuma comparação monetária entre alavancas seria
  admissível em lugar nenhum do relatório — custo alto para um conserto barato.
- **O harness recomputar o dedup** para achar o valor removido. Rejeitada: o harness
  reimplementaria o produtor e reintroduziria a auto-referência que esta ADR remove.
- **Somar sinal (não `abs`) dos dois lados.** Rejeitada: em fatura a convenção
  inverte (`_normalize_tipo`), e o check viraria falso-positivo por banco.

## Emenda 2026-09-01 — a fórmula do §D2 estava enviesada, e a tese sobrevive

Medido em `ws-1b9f2cf5` (re-derivação in-process, reproduz a linha publicada na **U5**):
o destino somava `despesas.total_geral + receitas.total_geral + transferencias_cents +
dedup_collapsed_cents`, mas os dois primeiros são somas **assinadas** e os dois últimos são
Σ|valor|. Com **48 receitas negativas** no corpus (Σ|v| = 999.386 cents), o destino saía
`2 × 999.386 = 1.998.772` cents menor — exatamente o Δ publicado, 100% explicado.

Não era resíduo: era **offset constante**, logo uma perda real do mesmo tamanho publicaria
`Δ = 0` e o veredito diria `conservado`.

**O que muda:** a fórmula do §D2. Os quatro termos passam a ser Σ|valor| declarados pelo
produtor, e o número publicado (`total_geral`) deixa de ser **termo** para virar o alvo de
uma **ponte verificada** (`abs == assinado + 2 × negativas`) — o que preserva, e fortalece,
a propriedade que este §D2 queria: o eixo cruza o que o relatório mostra.

**O que NÃO muda:** D1 (o produtor declara), D3 (ausência é não-medido), D4 (`dups`), D5
(fora de `_CONFERENCIA_SIGNAL_KEYS`). A §Alternativas rejeitadas também segue válida — a
[[ADR-434]] faz o **oposto** de "somar com sinal os dois lados": põe `abs` em todos.

Decisão completa, com a ponte e o conversor único: [[ADR-434]].
