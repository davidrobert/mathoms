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
- Preferir **derivar no rebuild** (code-only, sem migration). Se exigir coluna persistida
  (`declarante_ref`), migration alembic sequenciada a um head único **após** a de DE-01.
- Fallback gracioso: docs sem declarante (extratos/faturas) mantêm o comportamento atual.

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
- Sem migration se derivar no rebuild; senão 1 migration após DE-01 (head único).

## Critério de aceite (4 lentes)

- **Completude** — os 3 informes de casal do dogfood não ficam `needs_review` por duplicata.
- **Corretude** — dedup fuzzy ainda pega duplicata real (mesmo declarante, mesmo período).
- **Consistência** — `content_hash` inalterado (SHA-256 do conteúdo); dedup exato intacto.
- **Precisão** — discriminador é HMAC/`member_id` (nunca CPF cru, nunca em `content_hash`).
