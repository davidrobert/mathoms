---
id: ADR-079
type: adr
title: "Content-first classification no upload web"
status: Decidido
date: "2026-04-15"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 079"]
tags:
  - area/llm
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 23
---

# ADR-079 — Content-first classification no upload web

**Status:** Decidido • **Data:** 2026-04-15 • Supersedes D16 (parcialmente — D16 vale para CLI) • Nota: renumerado de ADR-075 (duplicado) para ADR-079

**Contexto:** O upload web classificava documentos pelo nome do arquivo (via `e0_route.classify_by_name`). Na prática, bancos brasileiros exportam PDFs/CSVs com nomes arbitrários ou genéricos (ex: `document.pdf`, `export_20260415.csv`). Resultado: ~65% dos uploads caíam no tipo "Outro".

**Alternativas avaliadas:**
1. **Filename regex (status quo)** — funciona no pipeline CLI onde o E0-route renomeia antes, mas inútil para uploads web crus.
2. **Sempre LLM** — precisão ~98%, custo ~$0,005/doc, latência +2s por upload, dependência de API key.
3. **Content-regex + LLM fallback (escolhida)** — regex sobre texto extraído (pdfplumber/openpyxl) cobre ~85% com confidence 1.0; LLM só para os ~15% ambíguos.

**Decisão:** Upload web classifica por **conteúdo extraído**, ignorando filename. Pipeline de 3 camadas: content-regex (confidence >= 0.8) → LLM fallback (>= 0.7) → `needs_review=true`.

**Consequências:**
- ✅ Precisão estimada ~97% com LLM ativo (era ~35% com filename).
- ✅ Filename não importa — drag-and-drop de qualquer export bancário funciona.
- ✅ `needs_review` flag permite fluxo humano-no-loop para casos ambíguos.
- ✅ Fuzzy dedupe (por `doc_type+bank_code+period`) complementa o exact dedupe por hash.
- ⚠️ Requer `anthropic` SDK + `ANTHROPIC_API_KEY` no env do backend. Sem a key, degrada para regex-only (~85%).
- ⚠️ Imagens (JPG/PNG) não podem ser classificadas por content-regex — vão direto para `needs_review`. OCR/vision é work futuro.
- ❌ Soft FK em `possible_duplicate_of_id` (sem constraint real) por limitação de alembic offline mode em SQLite. Dangling pointers são harmless — o JOIN retorna empty.
