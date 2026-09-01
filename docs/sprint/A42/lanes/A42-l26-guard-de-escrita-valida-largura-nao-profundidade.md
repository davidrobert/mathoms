---
id: A42.l26
type: lane
title: "O guard de escrita do E4 passa com zero erros e não mede profundidade: item vazio, campo lixo e número-como-string atravessam"
sprint: A42
status: open
priority: P1
branch_slug: a42-l26-guard-de-escrita-valida-largura-nao-profundidade
owner: data-engineer
depends_on: []
adrs: ["[[ADR-212]]"]
tags: [type/lane, sprint/a42, status/open, priority/p1, area/dados]
---

# A42.l26 — `guard-de-escrita-valida-largura-nao-profundidade`

> **Origem:** `PV13-13` da rodada unificada **U5** ([[PIPELINE-REVIEWS-active]] §r13).
> Sucessora da [[A42.l19]], cujo conserto **segura** — e cuja medição revelou o limite.

## O que está medido

O balde de patrimônio agora **resolve e valida com 0 erros** — a [[A42.l19]] entregou. Mas
o contrato re-derivado tem `required` e `additionalProperties: false` **só na raiz**: o
item de `imoveis_consolidados` sai com `required` nulo, então **item vazio `{}`, campo não
previsto e número serializado como string atravessam** a validação.

## Por que importa nesta rodada especificamente

A regressão de identidade de imóvel que a [[A40.l113]] descreve **passou por este guard**.
O guard não é cego a ela por acidente de configuração: ele **não olha o grão do item**, que
é exatamente onde a identidade mora. Um guard que valida largura declara cobertura que não
tem — mesma classe de [[A42.l24]].

## Critério de aceite

1. `required` e `additionalProperties` no **item**, não só na raiz.
2. Tipo numérico enforçado (número-como-string reprova).
3. Contrafactual medido por caso: item vazio, campo lixo, num→str — **os três reprovam**
   contra o código pré-mudança, e passam depois.
4. O guard publica **em que profundidade** validou; "0 erros" sem grão declarado não é
   veredito.
