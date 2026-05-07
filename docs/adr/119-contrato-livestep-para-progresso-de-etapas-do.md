---
id: ADR-119
type: adr
title: "Contrato `LiveStep` para progresso de etapas do pipeline"
status: Decidido
phase: "A6-ux"
date: "2026-04-23"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 119"]
tags:
  - type/adr
  - status/decidido
size_lines: 121
---

# ADR-119 — Contrato `LiveStep` para progresso de etapas do pipeline

**Status:** Decidido (A6-ux) • **Data:** 2026-04-23

**Contexto:** A infra de progresso em tempo real (WebSocket + `emit_stage_activity`
em `pipeline/live_progress.py` + `publish_stage_activity` em
`backend/app/services/events.py` + `usePipelineWS` no frontend) está madura e
cobre transporte, fallback (polling 2s) e heartbeat de conexão (ADR-030-WS).
O `PipelineStageActivity` em `frontend/src/lib/api/pipeline.ts` já declara os
campos `itemsDone`, `itemsTotal`, `currentItem` — e o `LiveActivityDetail` em
`StageRow.tsx` já renderiza contador `N/M` + sub-barra determinística quando
esses campos vêm populados.

**Problema:** nenhuma stage os popula. Etapas com loop por item (E1, E1.5, E1.5c,
E2-llm) emitem um único `emit_stage_activity` no início com a contagem embutida
na string (`"Lendo declaração IRPF com IA (5 documento(s))…"`) e ficam silenciosas
pelo resto da execução. Consequência operacional observada: E1.5 com 5 IRPFs
rodou 44min sem qualquer atualização visual — usuário não distingue "demorado"
de "travado", e a única ação disponível é cancelar às cegas.

Alternativas consideradas:
- **(A) Cada stage cunha seu próprio schema ad-hoc** — rejeitada: duplicação,
  divergência de nomenclatura, UX inconsistente entre etapas.
- **(B) Um novo transporte/canal dedicado a progress** — rejeitada: transporte
  atual (Redis pub/sub → WS) é suficiente; o gap é contrato de *payload*.
- **(C) Inferir progresso no frontend via deltas de `pipeline_artifacts`** —
  rejeitada: acopla UI ao storage layer, não cobre fases intra-item
  (chamando LLM vs. validando vs. escrevendo), e quebra em stages sem
  materialização 1:1 por item.

**Decisao:** Adotar **`LiveStep`** como contrato único para stages com trabalho
iterativo (loop por documento, por período, por conta). Um helper backend
`pipeline.live_progress.emit_item_progress(...)` encapsula emissão + throttle;
um componente frontend `<LiveStepProgress/>` renderiza o payload de forma
uniforme. Stages sem loop continuam usando `emit_stage_activity` simples.

**Schema do evento `stage_activity` (campos novos, todos opcionais):**

| Campo                     | Tipo     | Semantica                                                                 |
| ------------------------- | -------- | ------------------------------------------------------------------------- |
| `current_item`            | string   | Rótulo estável do item em processamento (ex.: nome do arquivo, período). |
| `items_done`              | int      | Itens concluídos (não inclui o atual em andamento).                      |
| `items_total`             | int      | Total de itens a processar neste run (pós-filtragem incremental).        |
| `phase`                   | string   | Sub-fase intra-item em enum fechado: `preparing`, `awaiting_llm`, `validating`, `persisting`, `finalizing`. |
| `estimated_duration_ms`   | int      | Mediana dos últimos 20 runs bem-sucedidos dessa stage no workspace. Só no primeiro evento da stage. |

**Regras de emissão (backend):**
1. Uma emissão **antes** de iniciar cada item (`items_done=k`, `phase="preparing"`,
   `current_item=<item_k+1>`).
2. Emissão adicional na transição para `awaiting_llm` (chamada LLM é o gargalo
   e tipicamente >80% do wall-time por item).
3. Emissões para `validating`/`persisting` são opcionais — recomendadas se a
   fase dura >1s.
4. **Throttle obrigatório** dentro do helper: no máximo 1 evento por
   `(run_id, stage)` a cada 250ms. Protege Redis em stages com milhares de
   itens (futuro).
5. Último evento da stage: `items_done == items_total`, `phase="finalizing"`.
   O evento terminal (`stage_completed`) já existente continua sendo fonte
   de verdade para conclusão — `LiveStep` é *enquanto roda*.
6. Frontend nunca infere `items_total` — só backend conhece o escopo pós-
   filtro incremental (ADR-080).

**Regras de renderização (frontend — `<LiveStepProgress/>`):**
1. **Linha 1:** `<Item X> de <Y>` monoespaçado + nome do `current_item`
   truncado com tooltip. Sem item, omitir linha 1.
2. **Linha 2:** sub-barra `h-1`. Progresso = `(items_done + phaseWeight) / items_total`
   com `phaseWeight ∈ [0, 1)` fixo por fase (`preparing=0.1`, `awaiting_llm=0.4`,
   `validating=0.8`, `persisting=0.95`, `finalizing=1.0`). Determinística,
   nunca recua.
3. **Linha 3:** micro-status do `phase` (tabela fixa de mensagens PT-BR —
   sem criatividade por-stage) + dot pulsante.
4. **Heartbeat por-stage:** `useStallWarning` estendido para guardar
   `lastActivityByStage`. Se `now - lastActivityByStage[stage] > max(180s, 2×estimated_duration_ms / items_total)`,
   dot pulsante vira ícone âmbar + tooltip "Sem sinal há X — [Cancelar]".
5. **Estimativa honesta:** se `elapsed > estimated_duration_ms`, mostrar
   `44m / ~15m est.` em cinza. Transparência explícita de desvio da mediana.

**Consequencias:**
- ✅ Usuário distingue "travado" de "lento": contador muda, barra enche, fase
  roda, heartbeat por-stage delata silêncio real — sem precisar abrir logs.
- ✅ Mesmo componente em todas as stages: zero carga cognitiva ao navegar
  entre etapas; zero código UI específico por-stage.
- ✅ Enum fechado de `phase` evita drift de mensagens entre devs ("Consultando
  IA…" vs "Chamando LLM…" vs "Processando com IA…").
- ✅ Throttle no helper é a única política de rate-limit — impossível esquecer
  em site de emissão.
- ⚠️ Stages precisam conhecer `items_total` antes do loop — trivial para loops
  baseados em listas materializadas (`docs_with_text`), exige cuidado em
  geradores/streams (preferir materializar primeiro, aceitar O(n) extra).
- ⚠️ `estimated_duration_ms` vindo da mediana pode ser enganoso em workspaces
  novos (sem histórico). Regra: omitir o campo até termos ≥3 runs
  bem-sucedidos; frontend só mostra a comparação quando o campo vem.
- ⚠️ Enum `phase` é um contrato público — adicionar valor novo é
  *breaking change* do lado do frontend (precisa de `phaseWeight` + mensagem).
  Expansão passa por nova ADR ou sub-seção aqui.
- ❌ Emissores que hoje põem a contagem na `message` (texto livre) precisam
  migrar — migração faseada (E1.5 primeiro, demais em sequência), não
  big-bang. Durante transição, frontend tolera eventos antigos (campos
  ausentes = UI degrada ao comportamento atual).

**Implementação — saga de migração concluída em 2026-04-25.** Todas as 9
stages com loop iterativo emitem `emit_item_progress`:
`extract_baseline` (E1.5, `3bc9d25`), `extract_statements`+`extract_invoices`
(E2, `09858df`, compartilham `scripts/e2_extract.py`), `extract_members`
(E1) + `consolidate_baseline` (E1.5c) em `3d819db`, `categorize_transactions`
(E4) + `analyze_finances` (E5) em `2a6d5e5`, `extract_with_llm` (E2-llm,
`56d8c42` — concorrência via `ThreadPoolExecutor` + `Lock` em counter
compartilhado), `reconcile_transactions` (E3, `e6e9ebd` — primeira lane que
instrumenta domain adapter via kwarg `pipeline_run_id`), `route_documents`
(E0, `26225b1`). Stages rápidas (`unlock_documents`, `audit_documents`,
`validate_cross`, `apply_review`) ficam sem emit intencionalmente — wall-time
<500ms torna preparing+finalizing engolidos pelo throttle de 250ms. Zero
callers de `emit_stage_activity` antigo em `pipeline/` ou `scripts/` —
contrato antigo permanece exposto em `pipeline/live_progress.py` apenas
para backward-compat de testes; remoção é candidata a cleanup futuro.

Relaciona-se a: ADR-030-WS (transporte), ADR-080 (modo incremental — define o
universo de `items_total`), ADR-076 (design system — tokens do componente).
Não substitui nenhuma ADR anterior.
