---
id: ADR-339
type: adr
title: "Dedup fuzzy de documento inclui o declarante — informes de casal não são duplicata"
status: Proposto
date: "2026-07-15"
relates_to:
  - "[[ADR-238]]"
  - "[[ADR-246]]"
  - "[[ADR-271]]"
tags:
  - type/adr
  - status/proposto
  - area/backend
---

# ADR-339 — Dedup fuzzy de documento inclui o declarante

> Cluster **DE-03** (P3) da onda R2 do [[PLAN-dogfood-report-fix]]. Co-desenho
> `codesign-review-wave` (data-engineer + red-team, 2026-07-15).

## Contexto

A chave de dedup fuzzy de documento é `(workspace_id, doc_type, bank_code, period)`
(`backend/app/services/documents/document_duplicates.py:20`) — **sem o declarante**. Num domicílio
de 2 declarantes (titular + cônjuge) com contas nos mesmos bancos, cada banco emite **dois**
informes anuais 2025 legítimos (um por CPF), com `content_hash` distinto. A chave coarse os trata
como duplicata: **3 informes ficam `needs_review=1` permanentemente** apontando um para o outro.
Não bloqueia (ambos são ingeridos), mas gera ruído de review que nunca resolve.

## Decisão

Incluir um **discriminador de declarante** na desambiguação da chave fuzzy: quando dois docs de
mesmo `(doc_type, bank, period)` têm declarantes distintos, **não** sinalizar duplicata.

- Discriminador = **token não-reversível** do CPF do titular (HMAC ou `member_id`), **nunca** CPF
  em plaintext.
- **Nunca** entra no `content_hash` — que permanece SHA-256 do conteúdo (dedup exato inalterado).
- O discriminador entra na **chave de agrupamento** do `rebuild_fuzzy_duplicate_pointers`
  (`backend/app/services/documents/document_duplicates.py`): `(workspace_id, doc_type, bank_code,
  period, declarante_ref)`.
- Fallback gracioso: docs sem declarante (extratos/faturas) usam `declarante_ref=None` → chave
  idêntica à atual, comportamento preservado.

## Viabilidade de implementação (verificado 2026-07-15)

O `Document` **não carrega** o eixo de declarante hoje: nem coluna, nem em `classification_meta`
(a classificação de conteúdo em `content_classifier.py` não extrai CPF). O único lugar onde o
declarante aparece é `titular_ln_masked` no **artefato E2 extraído** (`extract_informes_anuais.py`),
produzido **depois** do upload/reclassify — enquanto o `rebuild_fuzzy_duplicate_pointers` roda sobre
`list[Document]` **antes/independente** da extração. **Logo, "derivar no rebuild code-only" NÃO é
viável** (a premissa inicial estava errada). DE-03 exige uma **lane de write-path**:

1. Na classificação/ingestão de informe, derivar `declarante_ref = HMAC(cpf_titular)` (chave Fernet
   já disponível no vault; nunca persistir o CPF) e gravar em `classification_meta["declarante_ref"]`.
2. `rebuild_fuzzy_duplicate_pointers` lê `classification_meta.declarante_ref` e o inclui na chave.
3. Backfill dos docs existentes (rebuild uma vez) — sem migration se `declarante_ref` viver em
   `classification_meta` (JSON já existente); coluna dedicada só se um índice por declarante virar
   necessário (migration a head único após DE-01 Fase 2).

Escopo = write-path (ingestão) + read-path (dedup) + backfill + teste de casal. É lane própria,
não fix code-only. Design travado aqui; implementação quando priorizada.

## Rationale

Dois declarantes = dois ativos fiscais legítimos; a chave de identidade precisa do eixo que os
distingue. Segue a lição de "identidade por CPF, não slug" ([[ADR-271]]/kin da [[ADR-246]]) numa
superfície de documento. Token não-reversível respeita o invariante de nunca persistir CPF cru.

## Alternativas consideradas

- **Suprimir o flag quando `content_hash` difere.** Rejeitada: hashes diferentes também ocorrem em
  reprocessamento/OCR variante do mesmo doc — perderia dedup fuzzy legítimo.
- **CPF na chave fuzzy.** Rejeitada: PII persistida; usar HMAC/`member_id`.

## Consequências

- Informes de casal deixam de flagar duplicata (ruído de review resolve).
- Sem migration se `declarante_ref` viver em `classification_meta` (JSON existente); coluna
  dedicada só se um índice por declarante virar necessário (migration a head único após DE-01).

## Critério de aceite (4 lentes)

- **Completude** — os 3 informes de casal do dogfood não ficam `needs_review` por duplicata.
- **Corretude** — dedup fuzzy ainda pega duplicata real (mesmo declarante, mesmo período).
- **Consistência** — `content_hash` inalterado (SHA-256 do conteúdo); dedup exato intacto.
- **Precisão** — discriminador é HMAC/`member_id` (nunca CPF cru, nunca em `content_hash`).
