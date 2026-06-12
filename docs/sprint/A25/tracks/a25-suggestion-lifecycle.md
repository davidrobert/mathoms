---
id: TRACK-a25-suggestion-lifecycle
type: track
title: "Track A25 — SUGGESTION_LIFECYCLE F1→F4: supersede-per-run, thesis_key, valores determinísticos, cap/ordering, backfill dogfood"
sprint: A25
plan: PLAN-suggestion-lifecycle
status: consumed
consumed_at: "2026-06-12"
created_at: "2026-06-12"
agent_role: senior-engineer
tags:
  - type/track
  - sprint/a25
  - status/consumed
  - priority/p1
  - area/backend
  - area/llm
  - area/produto
---

# Track A25 — SUGGESTION_LIFECYCLE F1→F4

> ✅ **Consumido em 2026-06-12** — F1 (#622), F2 (#623), F3 (#624) e
> F4 (#626 + follow-up #627 `latest_batch`) squash-merged em `main` com
> CI verde. Backfill **aplicado** no dogfood (owner aprovou "último
> parecer vence" após dry-run heurístico achar 0 duplicatas): 165 → 7
> Pendentes (5 acionáveis, 0 danger; aceite ≤14 ✓), 158 Superseded soft.
> **Pendência operacional** (ver [[PLAN-suggestion-lifecycle]]): gate de
> estabilidade thesis_key ≥90% em 2 runs reais do pipeline.

> **Prompt self-contained.** Você é um engenheiro sênior executando o plano
> [[PLAN-suggestion-lifecycle]] (`docs/plan/SUGGESTION_LIFECYCLE/_README.md`)
> de ponta a ponta. Decisões arquiteturais já estão travadas em [[ADR-290]]
> (B1–B7) — **não reabra**; execute. Cada fase = 1 PR squash-merged em `main`
> com CI verde antes da próxima (exceção: F2 pode rodar em paralelo a F1 se
> houver 2 agentes; em sessão única, ordem F1 → F2 → F3 → F4).

## Contexto (por que isso existe)

O inbox `/acao` do dogfood acumulou **158 Suggestions Pendentes em 12 runs**
do Parecer (E6): sem supersede entre runs, dedup por hash do texto LLM
(re-redigido a cada run) e valores monetários recalculados pelo LLM
(reserva citada de R$ 224k a R$ 540k com escalar exato já computado no E5).
As mesmas pendentes vazam para o relatório (cards "Promover para ação" por
seção + "Próximos passos"), todas live em `status=Pendente`, sem cap.

## Pré-condições (verificar antes de qualquer edit)

1. Plano + ADR-290 estão em `main` (PR #616 mergeado):
   `git fetch origin && ls docs/adr/290-* docs/plan/SUGGESTION_LIFECYCLE/`.
   Se não estiverem, **pare** — gate F0 não fechou.
2. Protocolo de pickup do CLAUDE.md: `git worktree list` +
   `git for-each-ref ... refs/remotes/origin/agent/ | head -15`. Se existir
   branch `agent/sug-supersede-*` ou `agent/sug-lifecycle-*` com commit <24h,
   a lane está tomada.
3. Branch: `git checkout -b agent/sug-lifecycle-f1/<yyyyMMdd-HHmm> origin/main`
   (nova branch por fase).

## Leitura obrigatória (nesta ordem, antes de F1)

1. `docs/plan/SUGGESTION_LIFECYCLE/_README.md` — fases, KRs, riscos, aceite.
2. `docs/adr/290-supersede-per-run-thesis-key-suggestion.md` — B1–B7.
3. `docs/adr/269-task-suggestion-dedup-supersede.md` — padrão irmão (portar o
   **algoritmo**, não o código: tabela/status/índices são diferentes).
4. Código load-bearing:
   - `backend/app/services/planner_review_persistence.py` (L131
     `_existing_dedup_keys`, L224-241 `_persist_suggestions_from_artifact`,
     L335-357 guard `_find_existing_review`)
   - `backend/app/services/parecer_finalization.py:36-40`
     (`compute_suggestion_dedup_key`)
   - `backend/app/models/suggestion.py` (L16-19 docstring **mentiroso** — diz
     UNIQUE parcial; a migration `e9f0a1b2c3d4` prova UNIQUE **full** de 3
     colunas; L44-46 `VALID_SUGGESTION_AGGREGATE_STATUSES`)
   - `backend/app/tasks/pipeline_task.py:110-230` (ADR-269 em
     `task_suggestions` — referência de algoritmo)
   - `pipeline/llm/schemas/parecer_planejador.py:153-168` (`tema_canonico`,
     `section_id`, `ancora_metodologica` — obrigatórios no schema atual)
   - `pipeline/domain/services/reserva_emergencia_calculator.py:113-114`
     (`nivel_6_meses`/`nivel_12_meses` — fonte determinística p/ F2)

## F1 — Estancar o acúmulo (migration + supersede + telemetria)

1. **Migration Alembic reversível**: `suggestions` ganha `thesis_key`
   (String(64), nullable, índice btree não-unique `(workspace_id, thesis_key)`),
   `superseded_at` (DateTime, nullable), `superseded_by_run_id` (String(36),
   nullable). **Sem** `NOT NULL`, **sem** backfill, **sem** UNIQUE sobre
   thesis_key (B2 — unicidade é lógica de service). Test de migration com
   `pytestmark = pytest.mark.migration`.
2. **thesis_key na escrita** (B1): em `parecer_finalization`, computar
   `sha256(workspace_id | tema_canonico | section_id | ancora_metodologica)`
   ao lado do dedup_key; `_build_suggestion` persiste. Campo-fonte ausente →
   `thesis_key=None` → linha fora do supersede (fallback seguro).
3. **Supersede** (B3/B5/B6): dentro de `persist_planner_review`, **após** o
   guard `_find_existing_review` (idempotência run-level já existe — não
   reimplementar `new_keys`). Predicado:
   `status='Pendente' AND origin='llm' AND kind='parecer_planejador' AND
   accepted_decision_id IS NULL AND thesis_key IS NOT NULL AND thesis_key
   NOT IN (teses do run atual) AND superseded_by_run_id != run_atual`.
   Obsoletas → `status='Superseded'` (capitalizado, B2) + timestamps.
   Mesmo thesis_key reaparece → supersede a antiga, insere a nova.
4. **Janela de dismiss** (B4): `Descartada` <90d com mesmo thesis_key não
   recria (reusar `DISMISS_RESPECT_WINDOW_DAYS`).
5. **Contrato** (B7): `VALID_SUGGESTION_AGGREGATE_STATUSES += {'Superseded'}`;
   confirmar guard de `modify_suggestion` (deve exigir `Pendente`);
   `make update-openapi-snapshot` (provável no-op; comitar se diff).
6. **Telemetria no mesmo PR**: log estruturado com `suggestions_created`,
   `suggestions_superseded`, `skipped_dismiss`, `near_dup_candidates`
   (pendentes pré-supersede com mesma `ancora` e dedup_key distinto),
   namespace `mathoms.pipeline.planner_review_persistence`.
7. **Commit separado**: corrigir docstring do modelo (UNIQUE full, não parcial).
8. **Flip ADR-290** para `status: Decidido` + `phase: "A25"` no PR de F1.

**Aceite F1:** 2 chamadas p/ mesmo run não supersedem nada na 2ª; 2 runs
diferentes sobre mesmo E5 → 2º supersede obsoletas, `count(Pendente)` não
cresce; aceita nunca vira Superseded; `origin='deterministic'` intocado;
migration downgrade ok; 4 contadores logados. **Gate de estabilidade:**
thesis_key reaparece idêntico em 2 runs reais p/ ≥90% das teses (rode o
pipeline 2× no dogfood e meça); abaixo de 90%, **pare e reporte** — fallback
`action_slug` (Later do plano) precisa ser antecipado, não improvise.

## F2 — Valores determinísticos (prompt + validação + eval)

1. `config/prompts/parecer_planejador.yaml`: hints imperativos nas seções com
   valores (saude_balanco, independencia_financeira) — citar **exatamente**
   o escalar do payload (`nivel_6_meses`/`nivel_12_meses` e análogos), nunca
   faixa/arredondamento próprio. Bump `PROMPT_VERSION` → `1.4.0`
   (`pipeline/llm/prompts/parecer_planejador.py:6`; hook de PROMPT_VERSION
   enforça).
2. Reforçar regra 11 (ADR-279) em `pipeline/llm/schemas/parecer_planejador.py`:
   `evidencia_path` que resolve escalar numérico → `R$` da prosa deve bater
   (tolerância de arredondamento a milhar) → senão `needs_review`. Whitelist
   de campos-faixa legítimos (mitiga falsos positivos).
3. **Cap de geração** (junto neste PR): instrução "máx. 3 sugestões por
   horizonte, as de maior impacto; não preencha slots com variantes da mesma
   ação" (schema mantém ≤5 hard).
4. Eval golden: fixture sintética **PII-zero** em `tests/` (derivada do padrão
   dogfood, dados inventados); asserts: match de valor ≥98%, zero faixa
   inventada em campo escalar, FP rate do validador medido.
5. Gatilho `prompt-engineer` (Agent tool) **antes** de codar: brief com o
   diff de prompt proposto + plano de eval. 1 rodada de ajuste.

## F3 — Cap de display + ordering (UI `/acao` + relatório)

1. Ordering compartilhado (extrair helper): severidade (danger sempre topo,
   não filtrável) → gate metodológico (proteção/liquidez → dívida → alocação
   → renda → fiscal) → impacto (`amount_brl_cents`) desc; esforço só
   desempate; `info` colapsado por default e **fora** do cap de 12 acionáveis.
2. Superfícies: `/acao` InboxTab + `SuggestionCalloutInline` (cards "Promover
   para ação": ≤3 por seção + link "ver todas em /acao") +
   `SuggestionCalloutSummary` ("Próximos passos": mesmo ordering, só
   acionáveis) — `frontend/src/components/report/sections/SuggestionCallout.tsx`.
3. Gatilho `product-designer` (Agent tool) **antes** de codar: brief com
   wireframe textual do colapso/cap/copy. 1 rodada.
4. Teste de snapshot do ordering com fixture multi-severidade (danger no topo
   independente de filtro). Vitest p/ helper; atualizar testes E2E se tocar
   fluxo `@critical`.

## F4 — Backfill heurístico do dogfood (depende de F1 em main)

1. Script service-layer padrão `internal_ops`
   (`backend/app/services/internal_ops/`, espelhar `pipeline_reset.py`):
   `workspace_id` **obrigatório** (sem default "todos"), `--apply` explícito
   (default dry-run), agrupamento **heurístico** por
   `(section_id, título normalizado)` — linhas antigas não têm
   `tema_canonico` persistido; **não** tente recomputar thesis_key delas.
   Mantém a pendente mais recente do grupo, supersede o resto.
2. Dry-run emite relatório `(grupo → mantém / supersede)` — **apresente ao
   usuário para revisão antes do `--apply`**. Rollback: `Superseded` é soft.
3. Concorrência: não rodar com pipeline ativo no workspace (ou skip
   `created_at` > início do backfill).
4. Runbook curto em `docs/reference/runbooks/` (estrutura: pré-condições,
   dry-run, apply, rollback, verificação).

**Aceite F4:** dogfood `5@5.com` (workspace
`1b9f2cf5-6a19-4d2a-af7a-79d739ddeff6`) cai de 158 para ≤14 pendentes
acionáveis; relatório dry-run revisado; runbook mergeado.

## Protocolo (não negociável)

- **1 PR por fase**, branch `agent/sug-lifecycle-f<N>/<ts>`, Conventional
  Commits referenciando `(ADR-290)`, squash-merge, CI verde. Fase só está
  `done` com merge confirmado em `origin/main`.
- Gates locais antes de cada push: `pre-commit run --all-files` +
  `pytest backend/tests -q` + `pytest tests -q`; se tocar `frontend/`:
  `cd frontend && npm test -- --run`.
- Endpoint JSON novo/alterado → `make update-openapi-snapshot` + commit do diff.
- **Dinheiro nunca é float** (ADR-090); valores em testes/fixtures sempre
  sintéticos (PII-zero).
- Dúvida sobre regra de domínio (valor de reserva, ordering metodológico) →
  `financial-planner` via Agent tool; **não invente**.
- Ao terminar cada fase: atualizar `docs/plan/SUGGESTION_LIFECYCLE/_README.md`
  (checkbox/status da fase) + entrada no `docs/CHANGELOG.md` no padrão Keep a
  Changelog, commit `docs(...)` separado.
- Este track: flip `status: consumed` + `consumed_at` quando F4 mergear.
