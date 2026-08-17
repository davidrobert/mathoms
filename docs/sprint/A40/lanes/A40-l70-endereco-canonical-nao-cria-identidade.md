---
id: A40.l70
type: lane
title: "endereco_canonical=None não cria identidade: match por titular+código ou needs_review"
sprint: A40
plan: PLAN-deterministic-authority
status: open
priority: P1
branch_slug: a40-l70-endereco-canonical-nao-cria-identidade
owner: data-engineer
adrs:
  - "[[ADR-215]]"
  - "[[ADR-246]]"
  - "[[ADR-274]]"
  - "[[ADR-324]]"
  - "[[ADR-385]]"
  - "[[ADR-392]]"
depends_on: []
parallel_with:
  - "[[A40.l66]]"
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/backend
---

# A40.l70 — `a40-l70-endereco-canonical-nao-cria-identidade`

> Aberta em 2026-08-17 na Onda 4 do [[PLAN-deterministic-authority]] (item
> 4b-i / RV6-13). **Não espera a [[A40.l66]]**: o 0c (2026-08-17) confirmou
> que o buraco está aberto em `main`, e cada run continua mintando row. Nasce
> `open` porque não tem dependência pendente. A reconciliação das órfãs já
> mintadas é 4b-ii, dono da [[TRACK-property-identity-cross-era]].

## Problema

Falhada a cascata de match,
[`db_property_identity_resolver.py:44`](../../../../backend/app/services/db_property_identity_resolver.py)
chama `_insert_row` **incondicionalmente**. Não há ramo que inspecione
`endereco_canonical is None` para abortar, levantar ou marcar `needs_review`.
A prova de que o INSERT é *desenhado* para aceitar canonical ausente está na
linha 68 — `low_confidence=lookup.endereco_canonical is None`: o campo existe
para **carimbar** a ausência, não para recusá-la.

No enricher
([`property_identity_enricher.py:44`](../../../../pipeline/domain/services/property_identity_enricher.py)),
o único early-continue é sobre `titular_key`/`codigo_rfb`; o retorno de
`canonicalize` não é checado e o `None` entra direto no `PropertyLookupKey`.

O fake
[`InMemoryPropertyIdentityResolver`](../../../../pipeline/adapters/in_memory_property_identity_resolver.py)
repete o vício: com canonical ausente, **pula o dedup** e sempre anexa row
nova (`:29-48`). O 4º nível da [[ADR-385]] nunca foi portado para ele.

Medido no 0c (três caminhos, incluindo lente adversarial):

- Write-path real com `PRAGMA foreign_keys=ON`: descrição que canonicaliza
  para `None` ⇒ identidade criada, `endereco_canonical` NULL, `low_confidence=1`,
  **sem exceção e sem `needs_review`**. O `commit()` da linha 80 é eager —
  a row sobrevive a `session.rollback()`.
- Regrowth: um imóvel, três IRPFs, variação de grafia (espaço à direita,
  caixa) ⇒ **3 identidades**. É o mecanismo que repõe órfãs depois de
  qualquer sweep.
- O piso da [[ADR-385]] §Decisão 4 **não fecha isto por desenho**. O 4º
  nível casa `codigo_rfb` + `descricao_sample` **byte-exata**; a própria ADR
  o chama de "piso para a classe futura, não o fix do passivo". A classe
  `TestLowConfidenceInserts` afirma o INSERT como correto.

Ano **não** entra na chave ([[ADR-274]]): é atributo. A [[ADR-324]] §Emenda
já revogou a premissa que isto estava fechado.

## Escopo

1. Em `match_or_create` (DB **e** InMemory): se `endereco_canonical is None`
   **e** a cascata não casou, **não** chamar `_insert_row`. Sem match →
   `needs_review` no item (warning tipado [[ADR-097]] D1 + [[ADR-272]]),
   `property_id=None`, resto do documento extraído.
2. Match residual permitido sem canonical: `(titular_key, codigo_rfb)` +
   **corroboração de valor**. Ano é atributo, nunca chave. Sem corroboração
   → mesmo caminho `needs_review`, sem mintar.
3. Enricher: se `canonicalize(descricao)` devolve `None`, **não** monta
   lookup que força INSERT; propaga `endereco_canonical=None` +
   `low_confidence=True` + `property_id` só se o match residual casou.
4. Flip de `TestLowConfidenceInserts`: o INSERT deixa de ser o veredito
   correto. Os testes passam a afirmar "0 row nova + `needs_review`" (ou
   match residual quando titular+código+valor corroboram).

## Enforcement

WARN-first ([[ADR-357]]/[[ADR-358]]). Default: declara + `needs_review`,
**nunca** aborta o run e **nunca** minta identidade sem canonical. Taxa de
disparo medida sobre os payloads r5+r6 e **declarada na ADR `Proposto`
antes de qualquer flip**. Kill-switch de 1 env var (volta ao INSERT
carimbado `low_confidence`), provado por teste. Sem janela de rebaseline
monetário — não disputa J1/J2.

## Critério de aceite

- **Prova por mutação:** descrição que `canonicalize` mapeia para `None` ⇒
  0 row nova em `property_identity` **e** o item sai com `needs_review`.
  Sem a mutação, o teste nomeia o mecanismo sem exercitá-lo.
- Fixture de regrowth (1 imóvel × 3 IRPFs, grafia variante) ⇒ **1**
  identidade (match residual) **ou** 0 + `needs_review` — nunca 3.
- `InMemoryPropertyIdentityResolver` e `DBPropertyIdentityResolver`
  obedecem a **mesma** regra (teste de paridade no fake).
- `TestLowConfidenceInserts` deixa de afirmar INSERT; o XPASS estrito
  força a remoção do marker.
- ADR `Proposto` **antes** do PR de implementação (id alocado na escrita,
  a partir de 392 — 390 está no #1494, 391 reservado pela sessão da
  [[A40.l66]]); flipada para `Decidido` no merge.
- Taxa de disparo r5+r6 escrita na ADR. Zero valor monetário no golden
  E5 muda por esta lane — se algum snapshot tocar identidade, commit de
  rebaseline isolado com sinal ↑/↓/=.

## Fora de escopo

- Reconciliação / poda das órfãs já persistidas (4b-ii) →
  [[TRACK-property-identity-cross-era]] + `dev/backfill_property_supersession.py`,
  **só após** re-consolidação limpa pós-Onda 1.
- Roteamento ativo vs. passivo → [[A40.l66]].
- Cobertura de investimentos por membro (3a/3b) — superfície distinta;
  não abrir PR nela.
- Cache/pin de extração → depois da Onda 1 (§Anti-decisões do plano).
