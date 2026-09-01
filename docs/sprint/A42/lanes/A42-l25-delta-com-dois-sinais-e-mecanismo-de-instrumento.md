---
id: A42.l25
type: lane
title: "A mesma linha do razão publica o delta com dois sinais opostos, e o sinal observado é o único que nenhuma perda de pipeline produz"
sprint: A42
status: open
priority: P1
branch_slug: a42-l25-delta-com-dois-sinais-e-mecanismo-de-instrumento
owner: data-engineer
depends_on: []
adrs: ["[[ADR-416]]"]
tags: [type/lane, sprint/a42, status/open, priority/p1, area/dados]
---

# A42.l25 — `delta-com-dois-sinais-e-mecanismo-de-instrumento`

> **Origem:** `LC9-06` + `LC9-07` da rodada unificada **U5**
> ([[LEDGER-CERTIFY-active]] §r9). Sucessora direta da [[A42.l18]], que **ligou** a perna
> de valor: o número que ela destravou é o objeto desta lane.

## O que a linha publica

Na transição E3→E4, o campo `Δvalor` sai **negativo** e o detalhe da **mesma linha** sai
**positivo**, porque `dev/ledger_conservation.py:220` calcula `value_in - value_out`
apenas para o texto. **A direção do viés é irresolvível a partir da saída** — dois leitores
honestos da mesma linha chegam a conclusões opostas, e foi o que aconteceu no painel desta
rodada.

## E o delta provavelmente NÃO é perda

O sinal observado — destino **maior** que origem — é **o único que nenhuma perda de
pipeline produz**: perda encolhe o destino. Dois mecanismos candidatos, ambos de
instrumento:

- **Dois parsers para o mesmo campo.** O agrupador lê `"1.234"` como mil duzentos e trinta
  e quatro; a origem lê como um vírgula dois três quatro — fator **1000×** num subconjunto.
- **Quatro termos com duas convenções de sinal.** O delta é **líquido de opostos**, então
  compensações silenciosas cancelam parcelas que deveriam somar.

## Por que não é P0

Nada aqui muda número publicado ao usuário — é **instrumento**. Mas enquanto o sinal for
ambíguo, a perna de valor destravada pela [[A42.l18]] **não sustenta veredito**, e o razão
volta a `coberto-sem-verificação-de-valor` na prática.

## Critério de aceite

1. Um único produtor do delta; campo e detalhe **impossíveis** de divergir (mesma
   expressão, não duas).
2. Convenção de sinal declarada por termo, e o delta publicado **bruto por termo** além do
   líquido.
3. Um parser por campo, com o contrafactual: string ambígua no formato brasileiro produz o
   mesmo valor nos dois lados.
4. Controle positivo: mutação de 1 centavo em 1 termo move o delta em 1 centavo, com sinal
   correto — hoje isso não é verificável.
