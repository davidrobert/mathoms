---
id: ADR-080
type: adr
title: "Pipeline incremental: extrair só docs novos, consolidar full"
status: Decidido
phase: "F7"
date: "2026-04-16"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 080"]
tags:
  - area/llm
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 29
---

# ADR-080 — Pipeline incremental: extrair só docs novos, consolidar full

**Status:** Decidido (F7) • **Data:** 2026-04-16

**Contexto:** Com 96+ documentos, o pipeline reprocessava tudo do zero a cada execução — incluindo etapas caras de LLM (E1, E1.5, E2-llm). Após upload de 1 doc novo, rodar o pipeline completo desperdiçava tempo e custo. O modelo `Document` já tinha `pipeline_last_run_at` (adicionado na sync pós-pipeline), permitindo distinguir docs novos de já processados.

**Alternativas avaliadas:**
1. **Sempre full (status quo)** — simples, mas O(n) no custo/tempo com crescimento de docs.
2. **E0→E7 incremental puro** — processaria só docs novos em todas as etapas. Quebraria E3 (reconciliação cross-period) e E5 (análise consolidada).
3. **Híbrido: E0→E2 incremental + E3→E7 full (escolhida)** — extrai só novos (custo LLM proporcional a novos), consolida sobre todos os extracts (relatório sempre completo).

**Decisão:** Modo incremental (`POST /pipeline/run { incremental: true }`) filtra E0→E2 para docs com `pipeline_last_run_at IS NULL`. E3→E7 sempre rodam full sobre todos os E2_extracts existentes.

**Implementação:**
- `PipelineRun.incremental` (bool) + `incremental_doc_ids` (JSON) — rastreabilidade
- `WorkspaceContext.incremental` + `incremental_doc_paths` — propagação ao orchestrator
- `pipeline/stages/e2.py` — filtragem por stem matching dos stored_paths
- `GET /pipeline/new-doc-count` — endpoint leve para UI
- UI dinâmica: botão primary muda entre "Processar N novo(s)" e "Processar documentos"

**Consequências:**
- ✅ Custo de LLM proporcional a docs novos, não ao total do workspace.
- ✅ E3→E7 full garante reconciliação, categorização e análise sempre completas.
- ✅ Botão "Processar todos" mantido como fallback explícito.
- ⚠️ Se parser E2 for corrigido, extracts antigos ficam desatualizados — mitigado por "Processar todos".
- ⚠️ Stem matching entre stored_path e filename no filesystem pode falhar se renaming E0 for complexo — na prática, uploads web não passam por E0-route.
- ❌ E0 stages (unlock/audit/route) não são filtrados — operam em inbox (CLI flow). No web flow, inbox está vazio e eles fazem no-op naturalmente.
