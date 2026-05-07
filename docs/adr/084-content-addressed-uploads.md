---
id: ADR-084
type: adr
title: "Content-addressed uploads"
status: Decidido
date: "2026-04-18"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 084"]
tags:
  - area/persistence
  - status/decidido
  - type/adr
size_lines: 34
---

# ADR-084 — Content-addressed uploads

**Status:** Decidido • **Data:** 2026-04-18 • **Plano:** Fase 0

**Contexto:** Antes: `stored_path` usa o nome canônico
(`itau_extratoconta_202603-0_original.pdf`). Dois uploads distintos com nome
canônico idêntico (mesmo tipo + banco + período) sobrescreveriam o arquivo —
a deduplicação por `content_hash` já impedia salvar o mesmo hash duas vezes,
mas o upload legítimo de um **documento diferente** com o mesmo nome canônico
não era distinto no disco.

**Decisão:** Prefixar `stored_path` com os primeiros 12 hex do `sha256` do
conteúdo:

    itau_extratoconta_202603-0_original.pdf
    → a3f9c1b4d2e8_itau_extratoconta_202603-0_original.pdf

Aplicado em `scripts/e0_route.build_final_name` e
`backend/app/services/canonical_routing`. Migration
`o3p4q5r6s7t8_backfill_stored_path_content_hash` é **documentação-only**:
não renomeia arquivos existentes (risco desnecessário) — apenas novos uploads
adquirem o prefixo. Reclassificação de documento naturalmente aplica.

**Consequências:**
- ✅ Dois documentos diferentes com mesmo nome canônico ficam em paths distintos.
- ✅ `content_hash` do DB é consistente com o prefixo do path (auditável).
- ⚠️ Path visível ao usuário em logs tem um prefixo "enigmático" — aceitável (UI esconde).
- ❌ Documentos legados mantêm formato antigo — rename retroativo não é feito.

**Arquivos:** `scripts/e0_route.py`, `backend/app/services/canonical_routing.py`,
`backend/alembic/versions/o3p4q5r6s7t8_*.py`,
`backend/tests/test_content_addressed_upload.py`.
