---
id: ADR-392
type: adr
title: "endereco_canonical=None não minta PropertyIdentity; match residual é único (titular, código)"
status: Decidido
phase: A40.l70
date: "2026-08-17"
relates_to:
  - "[[ADR-097]]"
  - "[[ADR-215]]"
  - "[[ADR-272]]"
  - "[[ADR-274]]"
  - "[[ADR-324]]"
  - "[[ADR-357]]"
  - "[[ADR-385]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 392"
  - "nao mintar identidade sem canonical"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/persistence
  - phase/a40-l70
---

# ADR-392 — Sem canonical, não se cria identidade

> **Decidido em 2026-08-17** no PR da [[A40.l70]] (4b-i / RV6-13). O 0c do
> [[PLAN-deterministic-authority]] mediu o buraco aberto em `main`.

## Contexto

`DBPropertyIdentityResolver.match_or_create` chama `_insert_row` sempre que a
cascata falha. `low_confidence=lookup.endereco_canonical is None` **carimba**
a ausência e minta. O fake InMemory faz o mesmo. Uma grafia variante por IRPF
produz N identidades para o mesmo imóvel. O 4º nível da [[ADR-385]] (amostra
byte-exata) não fecha a classe — a ADR o chama de piso, não de fix.

## Decisão

**Sem `endereco_canonical`, o resolver não insere.** Devolve a row viva se a
cascata ou o match residual casar; senão `None`. O enricher marca o item
`needs_review` e segue o documento.

### D1 — Match residual = unicidade `(titular_key, codigo_rfb)`

A tabela não guarda valor. Corroboração possível sem migration: **exatamente
uma** row viva com o mesmo par. 0 ou ≥2 hits ⇒ `None` (ambíguo: dois
apartamentos no mesmo código RFB). Ano é atributo ([[ADR-274]]), nunca chave.

### D2 — WARN-first, não aborta

Código `domain.property_identity_uncanonical` ([[ADR-272]]), **fora** de
`BLOCKING_CODES`. Default: declara + `needs_review`. Kill-switch
`MATHOMS_PROPERTY_MINT_WITHOUT_CANONICAL=1` restaura o INSERT carimbado
`low_confidence` (prova por teste). Sem rebaseline monetário.

### D3 — Os dois resolvers obedecem a mesma regra

`InMemoryPropertyIdentityResolver` não é atalho. Paridade testada.

## Taxa de disparo (r5+r6)

A classe dispara quando `canonicalize(descricao)` é `None` **e** não há row
única `(titular, código)`. Medição no corpus dogfood fica no PR (payloads
cifrados off-git). Sem essa taxa o default já é o lado seguro (não mintar);
o kill-switch cobre regressão operacional.

## Consequências

- `match_or_create` passa a `Optional[PropertyIdentityRecord]`.
- `TestLowConfidenceInserts` deixa de afirmar INSERT.
- Órfãs já persistidas **não** se podam aqui (4b-ii / track).
