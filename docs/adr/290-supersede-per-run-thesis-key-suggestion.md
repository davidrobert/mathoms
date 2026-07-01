---
id: ADR-290
type: adr
title: "Supersede-per-run + thesis_key para Suggestion origin=llm (parecer) — extensão de ADR-269 ao aggregate Suggestion"
status: Decidido
phase: "A25"
date: "2026-06-12"
relates_to:
  - "[[ADR-153]]"
  - "[[ADR-199]]"
  - "[[ADR-208]]"
  - "[[ADR-269]]"
  - "[[ADR-279]]"
supersedes: []
superseded_by: []
aliases: ["ADR 290", "suggestion supersede", "thesis_key"]
size_lines: 105
tags:
  - type/adr
  - status/decidido
  - area/backend
  - area/llm
---

# ADR-290 — Supersede-per-run + thesis_key para `Suggestion` `origin=llm`

**Status:** Decidido (A25) • **Data:** 2026-06-12 •
**Plano:** [[PLAN-suggestion-lifecycle]]

## Contexto

Auditoria do workspace dogfood (2026-06-12): 158 `Suggestion` Pendentes
acumuladas em 12 runs do parecer (E6). Causas:

1. `_persist_suggestions_from_artifact` insere se `dedup_key` inédito e
   **nunca supersede** pendentes de runs anteriores — `_existing_dedup_keys`
   protege apenas retry do mesmo run (mesmo gap que [[ADR-269]] descreveu e
   corrigiu para `task_suggestions`).
2. `compute_suggestion_dedup_key` = `sha256(ws | ancora | acao[:100])` — o LLM
   re-redige a ação a cada run → chave nova → near-duplicates coexistem
   (5 variantes de "reserva de emergência" com valores de R$ 224k a R$ 540k).

O parecer não foi desenhado acumulativo — é dívida: nasceu antes de ADR-269
e nunca recebeu o supersede. A `Suggestion` `origin=llm` é semanticamente
efêmera ("último parecer vence"), distinta da determinística regra-based
(ciclos separados já reconhecidos em ADR-269 §d).

## Decisões (B1–B7)

- **B1 — thesis_key.** Nova coluna `thesis_key` (nullable, indexed
  não-unique) = `sha256(workspace_id | tema_canonico | section_id |
  ancora_metodologica)` — campos obrigatórios no schema atual do parecer,
  estáveis entre runs, independentes de redação e valor. Computada na
  escrita (`_build_suggestion`). Campo ausente (artifact antigo/schema
  futuro) → `thesis_key = NULL` → comportamento atual (sem supersede da
  linha).
- **B2 — status `Superseded`** (capitalizado, alinhado a `Pendente`/`Aceita`;
  **não** o lowercase de `task_suggestions`). Terminal, fora do inbox ativo,
  recuperável (soft). Colunas `superseded_at` + `superseded_by_run_id`.
  **Correção de premissa:** `uq_sugagg_ws_dedup_status` é UNIQUE **full** de
  3 colunas (migration `e9f0a1b2c3d4`), não parcial como afirma o docstring
  do modelo. **Não** criar UNIQUE sobre `thesis_key` — unicidade de tese é
  garantida pela lógica de supersede no service (padrão ADR-269), não por
  constraint física. Docstring incorreto corrigido em commit separado.
- **B3 — Proteção fiduciária.** Predicado de supersede:
  `status='Pendente' AND origin='llm' AND kind='parecer_planejador' AND
  accepted_decision_id IS NULL AND thesis_key NOT IN (teses do run atual)`.
  Aceitas/Modificadas/Descartadas nunca entram no conjunto superseable
  (histórico é sagrado, ADR-136).
- **B4 — Janela de dismiss.** `Descartada` há <90 dias com mesmo
  `thesis_key` não recria (reusa `DISMISS_RESPECT_WINDOW_DAYS`).
- **B5 — Separação de ciclos.** Supersede restrito a
  `origin='llm', kind='parecer_planejador'`. Suggestions determinísticas
  regra-based mantêm ciclo de vida atual.
- **B6 — Idempotência run-level.** Supersede vive dentro de
  `persist_planner_review`, **após** o guard `_find_existing_review`
  (retry do mesmo run não re-supersede — proteção que o módulo já tem;
  não reimplementar o mecanismo `new_keys` de `task_suggestions`).
  Defesa em profundidade: filtrar `superseded_by_run_id != run_atual`.
- **B7 — Contrato API.** `VALID_SUGGESTION_AGGREGATE_STATUSES` ganha
  `Superseded`; `SuggestionResponse.status` é `str` livre (OpenAPI
  provavelmente sem diff; rodar `make update-openapi-snapshot` e comitar
  se houver). Use cases `accept`/`dismiss`/`modify` já exigem `Pendente` →
  `Superseded` fica terminal por construção.

## Alternativas rejeitadas

- **Normalização agressiva do dedup_key** (strip números/stemming): paliativo
  — texto LLM continua variando; ADR-269 já rejeitou para `task_suggestions`.
- **Embedding similarity / LLM judge no persist:** custo+latência em hot path
  de escrita sem atacar a raiz; com supersede-per-run, variantes nunca
  coexistem. Fica como V2 se `thesis_key` se mostrar instável
  (fallback estrutural: `action_slug` de vocabulário fechado).
- **UNIQUE parcial sobre thesis_key:** mexer em constraint existente em prod
  tem blast radius desnecessário; lógica de service basta (ADR-269 provou).

## Consequências

- Inbox `/acao` converge para o parecer mais recente (fonte de verdade única);
  histórico auditável via status `Superseded`.
- Migration reversível: `ADD COLUMN` ×3 nullable + índice btree; downgrade
  dropa. Sem backfill na migration — backfill dogfood é script
  `internal_ops` heurístico separado (linhas antigas não armazenam
  `tema_canonico`; ver [[PLAN-suggestion-lifecycle]] F4).
- Telemetria por run (`created`/`superseded`/`skipped_dismiss`/
  `near_dup_candidates`) entra no mesmo PR do supersede.
