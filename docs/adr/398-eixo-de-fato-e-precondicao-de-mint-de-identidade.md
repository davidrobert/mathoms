---
id: ADR-398
type: adr
title: "Eixo decidido por fato é precondição de mint de identidade de imóvel"
status: Decidido
phase: r7/DE-6
date: "2026-08-19"
relates_to:
  - "[[ADR-215]]"
  - "[[ADR-246]]"
  - "[[ADR-272]]"
  - "[[ADR-324]]"
  - "[[ADR-334]]"
  - "[[ADR-385]]"
  - "[[ADR-392]]"
  - "[[ADR-394]]"
supersedes: []
superseded_by: []
aliases:
  - "secao e precondicao de mint"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/persistence
---

# ADR-398 — Sem fato de eixo, não se minta identidade

> **Decidido em 2026-08-19** na remediação do **DE-6** (P0) do §r7 de
> [[PIPELINE-REVIEWS-active]]. Estende a hierarquia de autoridade da
> [[ADR-394]] D1 ao write-path de identidade; não altera a regra de canonical
> da [[ADR-392]], que continua valendo a jusante.

## Contexto

O r7 publicou duas entradas em `real_estate.excluded_properties[]` cuja
descrição começa por "DIVIDA - CREDITO IMOBILIARIO", com `property_id` mintado,
`classification: "desconhecido"` e o CTA "usuário precisa rotular em
Configurações". Rotular põe um **passivo** no patrimônio bruto como **ativo**.

A [[ADR-394]] D1 instalou a autoridade do eixo no `consolidate_baseline`:
`secao` → sinal → `categoria_hint`. O mint de `PropertyIdentity`, porém, não
recebe nada disso — ele minta qualquer entrada que chegue a
`imoveis_consolidados`. O eixo, para efeito de identidade, voltava a ser
decidido por keyword.

### O que a medição diz

No corpus do run `33514dc4` (87 itens): `secao` cobre **87/87** (81
`bens_direitos`, 6 `dividas_onus`), as 6 dívidas têm valor **positivo** — como o
prompt 1.3.0 manda transcrever — e **2 delas trazem `categoria_hint: "imovel"`**.
Com `secao` presente, o roteamento da ADR-394 já as manda para `dividas` e o
mint nem é alcançado.

O buraco está onde `secao` **falta**. O campo é opcional em
`e15_baseline_extract.schema.json` (ADR-261 Tier 3: 766 artefatos históricos não
o carregam e o modo incremental os reagrega). Reproduzido em fixture sintética:
item com saldo devedor positivo e hint `"imovel"`, sem `secao`, entra em
`imoveis_consolidados`, soma ao `total_bens` e é mintado. Pior — quando a
descrição do financiamento canonicaliza para o **mesmo endereço** do imóvel
financiado, o passivo não ganha identidade nova: ele **casa com a identidade do
próprio imóvel**, e o dedup da [[ADR-246]] em seguida o absorve. É a classe da
§Emenda da [[ADR-392]] reaberta por outra porta.

## Decisão

**D1 — o consolidador carimba quem decidiu o eixo; o mint obedece.** Toda
entrada de `imoveis_consolidados` leva `eixo_autoridade`
(`secao`|`catalogo`|`sinal`|`hint`, o vocabulário de `ClassificationAuthority`).
`enrich_imoveis_with_property_ids` recusa o mint quando o eixo ATIVO veio do
hint: `property_id` nulo, `endereco_canonical` nulo (é chave de dedup, não pode
vazar do imóvel para o passivo), `needs_review` e `review_reason`
`domain.property_identity_eixo_por_hint` ([[ADR-272]], fora de `BLOCKING_CODES`).

O eixo ATIVO só nasce de `secao` ou de `hint` — o sinal é veto que nunca promove
a ativo e o catálogo refina subtipo, nunca eixo (ADR-394 D1/D2). Logo "sem fato"
significa exatamente "quem decidiu foi o rótulo do LLM".

**D2 — a precondição é escopada ao que a fonte pode oferecer.** O carimbo
`secao_disponivel` diz se a declaração de origem (grão `(membro, ano)`, que é o
grão de um E1.5a) emitiu `secao` em algum item. Só aí o fato é exigível. Exigi-lo
onde nunca existiu não fecharia o eixo: **apagaria `property_id` de todo imóvel
do corpus pré-`secao`** — medido, 17 testes de integração de dedup/identidade
reprovam, e com eles iriam o dedup, os overrides do dono e a seção de imóveis.

Consequência aceita e nomeada: numa declaração inteiramente legada o mint segue
autorizado, e a exposição do DE-6 permanece **naquele regime**. Ela é coberta
(a) pelo `review_reason` `EixoDecididoPeloHint` que o consolidador já emite e
(b) pelo D3 abaixo, que não depende de quando a identidade nasceu.

**D3 — identidade que nenhum baseline vivo reivindica não vira imóvel.**
`populate_real_estate` projetava **toda** row viva de `property_identity`, sem
consultar o baseline do run: fechar o mint não desfaz o dano já persistido. A
projeção passa a exigir que o `property_id` esteja em
`imoveis_consolidados[].property_id` do run **ou** que o dono tenha rotulado a
row (`workspace_property_overrides`). Sem baseline não há autoridade para
comparar e o filtro fica inerte.

Medido no corpus de dogfood, com e sem o filtro no mesmo harness:
`excluded_properties` é o **único** campo do payload que muda (6 → 2). `imoveis`,
`valor_total_imoveis`, `cap_rate`, `concentracao_pct`, `componentes_calculo`,
`spreads` e `alertas` idênticos — as 4 rows podadas nunca tiveram valor no
baseline e, sem override, jamais foram `investment`.

## Consequências

- `baseline_patrimonial.schema.json` ganha `eixo_autoridade` e
  `secao_disponivel` (opcionais) no item de `imoveis_consolidados`.
- Vocabulário de `review_reason` ganha `domain.property_identity_eixo_por_hint`
  (enum Python + array do `review_reason.schema.json`).
- O invariante `imoveis ∩ excluded == ∅` da [[ADR-334]] §3 **continua não
  aplicado** — o D3 reduz o conjunto excluído, não fecha a interseção. Segue
  rastreado como RV4-10.
- As 4 identidades sem canonical que já estão no DB não se podam aqui. Elas são
  **inalcançáveis** pelo resolver (o match residual da ADR-392 D1 exige row
  única e há 2 por `(titular, codigo_rfb)`) e agora invisíveis ao relatório;
  a reconciliação é higiene de DB e depende de decisão do dono
  ([[TRACK-property-identity-cross-era]] §Reconciliação).
