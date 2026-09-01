---
id: ADR-434
type: adr
title: "Uma convenção de sinal por termo no eixo-valor E3→E4, e a ponte que cruza o número publicado"
status: Decidido
phase: A42
date: "2026-09-01"
relates_to:
  - "[[ADR-426]]"
  - "[[ADR-429]]"
  - "[[ADR-090]]"
  - "[[ADR-279]]"
  - "[[ADR-173]]"
  - "[[ADR-287]]"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/dados
  - sprint/a42
aliases: ["ADR 434", "convencao de sinal do eixo valor", "receitas_abs_cents"]
---

# ADR-434 — Uma convenção de sinal por termo no eixo-valor E3→E4

**Status:** Decidido (A42.l25) • **Data:** 2026-09-01 • **Dono:** `data-engineer`.
Corrige a fórmula do §D2 da [[ADR-426]], cuja tese continua de pé (ver a emenda datada lá).

## Contexto medido (2026-09-01, `ws-1b9f2cf5`, re-derivação in-process)

A linha publicada na rodada **U5** era:

```
E3->E4: count 6928->6928 dups=858 Δvalor=-1998772 cents · … (Δ=1998772 cents)
```

**Dois defeitos independentes, e o segundo produziu um achado falso.**

**(1) Duas expressões concorrentes para o mesmo Δ.** `ledger_certify_core._delta_cents`
calcula `out − in`; `ledger_conservation._value_downgrade` computava `in − out` para o texto.
A mesma linha publicava os dois sinais e a direção do viés era irresolvível a partir da
saída (`LC9-06`). Consequência real: o `LC9-07` da mesma rodada afirmou *"destino > origem
é o único sinal que nenhuma perda produz"* — leu o **detalhe** (positivo) como se fosse o
campo. O campo media destino **menor**, que é exatamente a assinatura de perda. A conclusão
do `LC9-07` sobrevive (não é perda), mas por medição, não pelo sinal que ele citou.

**(2) Quatro termos, duas convenções.** Decomposição termo a termo:

| lado | termo | cents |
| --- | --- | ---: |
| origem | Σ\|valor\| das tx E3 sobreviventes | 2.075.438.094 |
| destino | `despesas.total_geral` | 229.916.766 |
| destino | `receitas.total_geral` | 490.122.659 |
| destino | `transferencias_cents` | 1.079.573.726 |
| destino | `dedup_collapsed_cents` | 273.826.171 |

`transferencias_cents` e `dedup_collapsed_cents` são Σ\|valor\|; `total_geral` é soma
**assinada**. Por balde: despesas resíduo **0**; receitas `Σ|v| − Σv = 1.998.772`, com **48
transações negativas** somando \|v\| = 999.386 — e `2 × 999.386 = 1.998.772` **exato**. O gap
publicado é 100% isso.

**Não é resíduo; é offset constante.** O destino subestimava em `2 × Σ|negativas|`
**sempre**, por construção. Uma perda real desse tamanho publicaria `Δ = 0` com veredito
`conservado`: canal de mascaramento, não confusão cosmética.

**Dois conversores no mesmo eixo.** O produtor usava `cents_int`
(`int(round(float(v)*100))`) e o harness usa `Decimal(str(v))` + `ROUND_HALF_UP`. Divergem
no meio-centavo (`0.575` → 57 vs 58). O resíduo zero de hoje é propriedade do corpus, não
do código.

## Decisão

**D1 — Um produtor único do Δ, com a direção no rótulo.** `dev.ledger_verdicts.delta_cents`
é a única expressão; `DELTA_LABEL = "Δvalor(destino−origem)"` viaja junto do número. Ler o
valor sem conhecer a convenção deixa de ser possível.

**D2 — Os quatro termos do destino são Σ\|valor\|, declarados pelo produtor.** `CashFlow`
ganha `despesas_abs_cents` e `receitas_abs_cents`; ambos viajam em
`despesas._lineage.signals`. Nenhum número de produto é reaproveitado como termo:
`total_geral` continua sendo receita **líquida** de estorno, que é o que o relatório deve
mostrar.

**D3 — A ponte cruza o número publicado.** O produtor declara também
`despesas_negativas_cents` / `receitas_negativas_cents` (Σ\|valor\| das rows com
`valor < 0`), que **não** somam no destino, e o harness assevera, por balde:

> `X_abs_cents == to_cents(X.total_geral) + 2 × X_negativas_cents`

Isso preserva — e fortalece — a propriedade que a [[ADR-426]] §D2 valorizava. O eixo não
precisa **somar** o número publicado; precisa **cruzá-lo**. A relação entre a declaração e o
número do relatório deixa de ser suposição implícita e vira equação verificada sobre a mesma
população. Ponte rompida ⇒ `coberto-sem-verificação-de-valor` (WARN-first do §D3 da
[[ADR-426]] preservado: nunca sobe a `perda-silenciosa` por convenção de sinal).

**D4 — Um conversor por campo no eixo.** `_soma_cents` e `_collapsed_cents` passam a usar
`decimal_cents` ([[ADR-090]]), o mesmo `Decimal(str(v))` do harness. **Não** se tocam as
linhas que alimentam `valor_cents` da identidade K4 — mudariam hash ([[ADR-287]]).

**D5 — O delta é publicado bruto por termo, além do líquido.** Líquido sozinho é cancelável.

**D6 — Fail-closed sem backfill.** Artefato sem `despesas_abs_cents` **ou**
`receitas_abs_cents` ⇒ `coberto-sem-verificação-de-valor`. A fórmula antiga **não** volta
como fallback: ela publica um Δ enviesado e cancelável, e "medido com viés" é pior que "não
medido" — a tese da própria [[ADR-426]]. Custo aceito: os runs da janela #1870→hoje perdem
cobertura do eixo.

## Consequências

- **Imunidade à [[ADR-429]].** Quando o estorno virar despesa assinada negativa,
  `despesas.total_geral` deixa de ser Σ\|valor\| pelo mesmo mecanismo que hoje quebra
  receitas. Com D2 o eixo não muda de forma: `despesas_abs_cents` já é o termo, e
  `despesas_negativas_cents` já sustenta a ponte. Sem D2, o eixo morreria de novo — em
  silêncio, mudando de valor e não de forma.
- **As 48 receitas negativas são evidência de produção para a [[ADR-429]]**, que hoje só tem
  fixture. Roteado, não consertado aqui: o `PAGAMENTO EFETUADO`/estorno virar receita é
  regra de domínio, dona a [[A40.l102]].
- **Chave de cache do parecer intacta.** As chaves novas ficam fora de
  `_CONFERENCIA_SIGNAL_KEYS` ([[ADR-173]] hard-stop, [[ADR-426]] §D5 sem emenda).
- **Sem mudança de schema.** `_lineage.signals` é `additionalProperties: {type: string}` e é
  metadata por [[ADR-279]]; enumerar as chaves criaria obrigação de bump sem ganho.
- **Custo.** Quatro campos int-como-string por run (~80 bytes). Forward-only.

## Aberto, declarado

`dev/golden_diff` classifica folha `*_cents` como **monetária** por marcador de nome, e
`to_cents("229916766")` daria `22.991.676.600`. Vale desde o #1870 para
`dedup_collapsed_cents`; esta nota **amplia de 2 para 6** as chaves na condição. Não foi
consertado aqui de propósito — o conserto certo é tratar `_lineage.` como namespace
não-monetário, o que é escopo próprio. Sem efeito sobre número publicado.

## Alternativas rejeitadas

- **Somar com sinal os dois lados.** Já rejeitada pela [[ADR-426]]; em fatura a convenção
  inverte e o check viraria falso-positivo por banco. Esta nota faz o oposto: `abs` em
  **todos** os termos.
- **Harness deriva `abs` de `total_geral + 2 × negativas`.** Aritmeticamente equivalente,
  mas o harness passaria a *derivar* em vez de ler declaração (contra o §D1 da [[ADR-426]]),
  usando justamente a identidade que deveria estar checando. Circular. Com D2+D3 a mesma
  informação está publicada — como **check**, não como definição.
- **Harness re-somar os baldes serializados.** Reintroduz a auto-referência que a
  [[ADR-426]] removeu.
- **Mudar `receitas.total_geral` para Σ\|valor\|.** Mudaria número publicado ao usuário:
  receita deixaria de ser líquida de estorno. Fora de escopo e errado.
