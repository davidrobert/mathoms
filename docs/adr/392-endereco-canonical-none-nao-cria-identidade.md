---
id: ADR-392
type: adr
title: "endereco_canonical=None não minta PropertyIdentity; match residual é único (titular, código)"
status: Decidido
phase: A40.l70
date: "2026-08-17"
amended_at: ["2026-08-17"]
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
>
> ⚠️ **Emendada em 2026-08-17** — o D1 abaixo ganhou uma condição: a row
> candidata precisa ser ela própria sem canonical. Ver §Emenda no fim.

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

## Emenda 2026-08-17 — a row candidata também precisa estar sem canonical

O D1 acima guardou o caso `≥2 hits` ("dois apartamentos no mesmo código RFB")
e deixou passar o caso `1 hit` em que **essa única row é um imóvel já
identificado**. Como `codigo_rfb` é o código de **categoria** da RFB (11 =
bens imóveis), o par `(titular_key, codigo_rfb)` casa com todo imóvel da
pessoa: quem tem um apartamento tem exatamente 1 hit, e qualquer item novo
sem canonical o reivindicava.

O efeito não parava na identidade. O enricher copia `endereco_canonical` da
row casada para o item; com os dois carregando `exemplo 100`, o dedup do
E1.5c fundia as duas entradas. **Medido em 2026-08-17** sobre o payload r6
(`tests/test_e15c_golden_execution.py`): o financiamento de −200k
desapareceu dentro do apartamento de 600k, sobrando só um `_dedup_warning`
`valor_divergente`, e o patrimônio líquido saiu **200k a maior** (600k
observado contra 400k declarado).

**Emenda ao D1:** o hit residual só vale se a row viva também tiver
`endereco_canonical IS NULL`. Row com canonical própria é imóvel conhecido —
item sem endereço não tem evidência de ser ele. Sem hit válido, vale o
default da ADR: `None`, `needs_review` e o item segue no documento com
`property_id` nulo.

Regressão provada por mutação nos dois resolvers (D3 continua valendo). Não
altera o D2 nem o kill-switch. O roteamento ativo↔passivo desse item segue
sendo escopo da [[A40.l66]] — esta emenda só devolve o item ao balanço.
