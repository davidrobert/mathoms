---
id: A42.l3
type: lane
title: "Harness de certificação: falso-verde para dentro"
sprint: A42
status: planned
priority: P1
branch_slug: a42-l3-harness-falso-verde-para-dentro
adrs:
  - "[[ADR-302]]"
depends_on: []
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p1
  - area/ci
  - area/pipeline
---

# A42.l3 — `harness-falso-verde-para-dentro` (LC05, LC06, PC13, RV4-17, RV4-18, RV4-45)

> **Origem:** [[LEDGER-CERTIFY-active]] §r4 2026-08-04 — LC05, LC06 (ambos Alto,
> classe `[skill]`) · [[PARSE-CERTIFY-active]] §r2 — PC13 · [[PIPELINE-REVIEWS-active]]
> §r4 — RV4-17, RV4-18, RV4-45. Adota também o resíduo declarado da [[A39.l6]]
> (traço positivo do checksum, já emitido e nunca lido).

## Problema

As ferramentas de certificação — as que existem para provar que o pipeline fecha —
dão verde sem medir. Cinco instâncias da mesma classe:

1. **Veredito catch-all com default otimista.** O classificador de balde do razão é
   um catch-all cujo default é "coberto": conta containers que aqueles baldes não
   usam, imprime "0 itens · coberto" com o payload completo em mãos, e a glosa "fora
   do grão transacional" é **factualmente falsa** para um dos baldes. Carimba
   `coberto` sobre a dimensão que carrega **62,5% do peso do score**.
2. **A P0 nº 1 da própria rubrica nunca foi exercitada** em quatro rodadas: o check
   que roda varre um balde de população e vetor **diferentes** do agregado que a
   rubrica diz cobrir.
3. **Traço já emitido e nunca lido.** O sinal positivo de checksum de investimento é
   declarado no schema e escrito pelo produtor; o harness não o lê. Onze documentos
   ficam presos em `coberto-sem-verificação` por **observabilidade**, não por falta
   de checksum. E "sinal presente → ausente" é des-certificação invisível ao ratchet.
4. **Perna de volume do gate anti-regressão morta:** busca uma folha que não existe
   no view-model, recebe vazio, e o guard torna o check inalcançável.
5. **Auditoria de paridade fail-open** sem variável de ambiente, comparando dois
   sinks alimentados pelo **mesmo** hook — "não consegui medir" é indistinguível de
   "medi e passou". Mesma forma: o registro durável descarta o contexto estruturado
   do log, então avisos de drift chegam como eventos idênticos e cegos.

## Decisão

O princípio único: **"não consegui avaliar" é um estado, não um sucesso.**

- **Registry explícito** `{balde → checker | não-verificável(motivo)}` com default
  **`não-verificável`**. Balde novo sem checker declarado aparece como lacuna, não
  como aprovação. Estender o drift (hoje só na camada de reconciliação) para
  contagem por balde da camada de categorização — **guard que fecha a classe**, não a
  instância.
- **Invariantes de saída** para a P0 nº 1, não reimportação dos módulos de dedup
  (reimportar seria tautologia: o check passaria porque usa o mesmo código que
  deveria auditar). Invariantes sobre o agregado publicado, com **partição de
  julgabilidade** declarada e prova por mutação.
- **Ler os traços que já existem** (checksum de investimento) e dar-lhes rank no
  ratchet, para que "presente → ausente" falhe o `--compare`.
- **Reparar a perna de volume** do gate, ou removê-la declarando que a perna de
  drift de valor cobre o caso — o que não pode continuar é perna morta que parece viva.
- **Exit code próprio para indeterminado** na auditoria de paridade, e preservar o
  contexto estruturado no registro durável.

## Critério de aceite

- **Prova por mutação em cada um dos cinco:** remover o input do check ⇒ **exit
  ≠ 0**. Hoje quatro dos cinco produzem verde nessa condição (medido no §r4 e no §r2).
  Este é o critério central da lane; sem ele, "consertei o harness" não é verificável.
- Balde sem checker declarado ⇒ veredito `não-verificável(motivo)`, nunca `coberto`.
  Teste que adiciona um balde fictício e exige que ele **não** apareça como coberto.
- A P0 nº 1 da rubrica passa a ter check que a exercita sobre o agregado correto,
  com a partição de julgabilidade escrita.
- `--compare` falha quando o sinal positivo de checksum desaparece de um documento
  que o tinha.
- Nenhum check novo que dependa de variável de ambiente para morder: se a condição
  não está satisfeita, o resultado é `indeterminado` com exit próprio — não `pass`.
- **KR-B da sprint só é mensurável depois desta lane.** É a razão pela qual ela está
  na Onda 1 e não depois dos fixes que ela deveria vigiar.
