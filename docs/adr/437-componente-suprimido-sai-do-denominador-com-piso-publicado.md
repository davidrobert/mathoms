---
id: ADR-437
type: adr
title: "Componente suprimido sai do denominador do score, com piso publicado"
status: Decidido
date: "2026-09-02"
supersedes: []
tags: [type/adr, status/decidido, area/financial-planning, area/pipeline]
---

# ADR-437 — Componente suprimido sai do denominador do score, com piso publicado

> ⚠️ **Escrita no fecho da [[A40.l114]], depois do merge do #1961 — não antes.** O CLAUDE.md
> exige ADR `Proposto` antes do PR em task P0 com escopo arquitetural, e isso não foi feito:
> a decisão nasceu no co-design com o `financial-planner`, foi para o código e só o
> `lane-closeout` a pegou contradizendo a [[ADR-217]]. O registro fica aqui como está, e a
> falha de processo fica declarada em vez de apagada.

## Contexto

A [[ADR-217]] §D2 decidiu, e continua governando, que **componente sem dado não
re-normaliza**:

> Componente sem dado **não** re-normaliza. Score natural fica menor enquanto não houver
> dado — é **feature**, não bug: incentiva onboarding.

O caso que ela tinha em mãos é `cobertura_seguros` com `status: absent_normalized`: dado que
**o usuário não declarou**. A penalidade é um incentivo de onboarding, e o usuário pode
agir sobre ela.

A [[A40.l114]] encontrou um caso diferente. `endividamento.total_dividas` saiu **zero** com
quatro financiamentos listados na mesma página, e `taxa_endividamento` recebeu **nota 10,0**
— a máxima — com peso de 18,8% do score. O dado existia nos documentos que a família já
entregou; o pipeline é que não conseguiu lê-lo.

## Decisão

### D1 — `suprimido` é um terceiro estado, e não é `absent_normalized`

`status: "suprimido"` significa **o dado existe e não foi apurado**, distinto de
`absent_normalized` (*"o usuário não declarou"*). O componente sai com `nota: null` e
`valor: null` — nunca nota neutra: em componente **invertido**, `5,0` afirma
"endividamento intermediário", que é o zero disfarçado com outra sintaxe.

### D2 — o peso do suprimido sai do denominador

Penalizar por dado que o **produto** não conseguiu ler não incentiva onboarding: o usuário
não tem ação disponível. A régua da [[ADR-217]] §D2 continua valendo para
`absent_normalized`; ela **não** se estende a `suprimido`.

### D3 — a supressão não pode subir o score, e o `piso` é o que garante isso

Sai publicado `score.piso` — o score renormalizado com **todo** componente suprimido em
nota `0` (extremo conservador, forma do `piso_autonomia_financeira_meses` · [[ADR-412]] §D7).
A **classificação** deriva de `min(valor, piso)`.

Sem D3, a D2 fabricaria o vício que ela existe para matar: ausência de dado **elevaria** o
número publicado, e "endividamento não apurado" compraria a faixa "Bom". Medido na
[[A40.l114]]: com o componente suprimido, `valor` renormalizado dá **6,8** ("Bom") e o piso
dá **5,6** ("Regular") — a faixa publicada é a do piso.

### D4 — o componente permanece visível na tabela

Com `nota: null` e peso normalizado `0` no breakdown. Sumir a linha esconderia o defeito
exatamente onde o leitor confere ([[ADR-394]] §Emenda · [[ADR-431]] §D4).

## Alternativas consideradas

- **Nota neutra (5,0).** Rejeitada: em componente invertido é uma **afirmação** sobre o
  patrimônio da pessoa — pune a família sem dívida e premia a muito endividada. É o zero
  disfarçado, exatamente o que a [[ADR-431]] proíbe.
- **Manter a penalidade natural da [[ADR-217]] §D2.** Rejeitada para este estado: o usuário
  não tem ação disponível sobre um passivo que o pipeline não leu. Continua valendo para
  `absent_normalized`.
- **Renormalizar sem publicar o piso.** Rejeitada: é a D2 sem a D3, e nessa forma a
  supressão sobe o score.

## Consequências

- `score.piso` é campo novo no contrato do E5 (`e5_analysis.schema.json`), e
  `componentes[].nota`/`valor` passam a aceitar `null`, com `suprimido` no enum de `status`.
- O snapshot do view-model rebaselinou por **adição** — duas chaves, zero valores alterados.
- Quem lê `score.valor` sem ler `score.piso` perde a ressalva. A classificação já carrega o
  piso, então o leitor que mostra só a faixa está correto por construção.
- **Fora do escopo:** `absent_normalized` e `absent_penalized` seguem exatamente como a
  [[ADR-217]] §D2 os definiu. Esta ADR acrescenta um estado; não redefine os dois.
