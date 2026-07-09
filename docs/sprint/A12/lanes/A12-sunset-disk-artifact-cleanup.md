---
id: A12.sunset-disk-artifact
type: lane
title: "Sunset DiskArtifactStore + flag MATHOMS_USE_DB_ARTIFACTS + CLI standalone"
sprint: A12
status: shipped
aliases: ["A12.sunset-disk", "A12.SUNSET_DISK_ARTIFACT"]
priority: P1
depends_on: []
parallel_with: ["[[A12.cat-learning-loop]]", "[[A12.alocacao-v2]]"]
adrs_canonical:
  - "[[ADR-212]]"
tags:
  - type/lane
  - sprint/a12
  - status/shipped
  - priority/p1
  - area/backend
  - area/pipeline
  - area/ops
---

# A12.sunset-disk-artifact — Sunset DiskArtifactStore + flag + CLI

> Lane multi-PR (5 PRs sequenciais). **Plano canônico:** [[ADR-212]] —
> a ADR é o plano (5 PRs, gates, riscos, mitigações). Esta lane é o
> índice de execução; **não duplique conteúdo da ADR**.
> Track operacional: [sunset-disk-artifact](../tracks/sunset-disk-artifact.md).

## Origem

[[ADR-212]] (Proposto, mergeada em main 2026-05-14). Cutover DB-only do
`ArtifactStore` está estável há >1 ano ([[ADR-118]] flippou default em
2026-04-23); flag `MATHOMS_USE_DB_ARTIFACTS=false` nunca foi acionada em
produção. ADR-212 remove ~500 LoC líquidos (DiskArtifactStore + 30+
branches `if use_db_artifacts:` + flag + override DB + CLI standalone do
pipeline) e desbloqueia [[ADR-211]] lane 3 (`prepare_pipeline_config_dir`).

## Sequência (5 PRs)

| # | PR | Effort | Gate principal |
|---|---|---|---|
| 1 | **PR2** — remove `MATHOMS_WORKSPACE_ROOT` setdefault em `backend/app/{main,worker,tasks/pipeline_task}.py` | ~0.5d | `make dev` sobe limpo; suíte verde; `grep -rn MATHOMS_WORKSPACE_ROOT backend/` = 0 |
| 2 | **PR1** — deleta `__main__` de `e0_route/e0_unlock/e2_extract`; deleta `e_reset.py` extraindo `reset_workspace_from_stage` em `backend/app/services/internal_ops/pipeline_reset.py`; mantém `e0_audit.py` | ~1d | `grep -rn "if __name__" scripts/` retorna só `e0_audit.py`; service-layer com teste unitário sob `InMemoryArtifactStore` |
| 3 | **PR1.5** — runbook `docs/reference/runbooks/pipeline_rollback.md` (snapshot + revert + downgrade + decision tree) | ~0.5d | Runbook revisado pelo oncall; procedure exercitada em staging |
| 4 | **PR3** — deleta `DiskArtifactStore` + branches `isinstance` + fallback reader + `backfill_artifacts_from_disk.py` + `dev/compare_disk_vs_db.py`; `WorkspaceContext.__init__` exige `artifact_store`; refactor goldens E3/E4/E5 com `InMemoryArtifactStore`; hook JSON-schema pós-write em `DBArtifactStore` | ~2-3d | `grep -rn DiskArtifactStore` = 0; goldens verdes; integration tests verdes; **canary 10%/72h obrigatório** |
| 5 | **PR4** — Alembic drop `workspaces.use_db_artifacts_override` com guard pre-check + `batch_alter_table`; remove `USE_DB_ARTIFACTS` de settings; arquiva `runbooks/cutover.md` | ~0.5d | `grep -rn USE_DB_ARTIFACTS` = 0; migration up/down/up testada |

**Ordem obrigatória:** PR2 → PR1 → PR1.5 → soak 1 semana em staging
→ PR3 → PR4. Total ~5d eng em ~3 semanas calendário ([[ADR-212]] §OQ3).

## Branch prefix

`agent/sunset-disk-artifact-pr<N>/<yyyyMMdd-HHmm>` por PR
(ex.: `agent/sunset-disk-artifact-pr2/20260515-1400`).

## Gates de promoção entre PRs

- Cada PR mergeia em `main` independente (revertível via `git revert`).
- Suíte verde (`pytest backend/tests -q`, `pytest tests -q`).
- Pre-commit verde (`pre-commit run --all-files`).
- Goldens E3/E4/E5 verdes após PR3 (sob `InMemoryArtifactStore`).
- **PR3 não pode subir antes de PR1.5** (runbook é pré-requisito sre-devops P0).
- **PR3 exige canary 10%/72h** antes de roll-out 100%.

## Riscos principais (referência [[ADR-212]] §Riscos identificados)

| Risco | P | Mitigação resumida |
|---|---|---|
| Rollback rápido morre | P0 | PR1.5 + snapshot DB pré-deploy + canary 10%/72h |
| Bug em DBArtifactStore sem escape hatch | P0 | Goldens DB-only + integration test multi-worker ([[ADR-111]]) + canary |
| Goldens E3/E4/E5 quebram em CI no PR3 | P0 | Refactor de fixtures **incluído no escopo do PR3** |
| Workspaces com `use_db_artifacts_override=TRUE` legados | P0 | Guard `SELECT count(*) > 0 → raise` no `upgrade()` do PR4 |
| Validação JSON-schema perdida em E1-LLM | P0 | Hook pós-write universal em `DBArtifactStore.write` (PR3) |

Lista completa em [[ADR-212]] §Consequências e §Riscos identificados.

## Out-of-scope ([[ADR-212]] §Não-objetivos)

- Endpoint HTTP `POST /admin/workspaces/{id}/reset` — service-layer
  criado no PR1; endpoint fica em
  [INTERNAL_ADMIN](../../../plan/INTERNAL_ADMIN/_README.md) pós-IA-1.
- Deletar `prepare_pipeline_config_dir` — [[ADR-211]] lane 3,
  desbloqueada por PR1 desta lane.
- Política de retenção de `pipeline_artifacts` — débito em
  [PLATFORM_REVIEW](../../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md); trigger
  10GB ou 1M rows.

## Definition of Done

- ☑ PR2 ([#262](https://github.com/davidrobert/mathoms/pull/262)) — `MATHOMS_WORKSPACE_ROOT` setdefault removido.
- ☑ PR1 ([#263](https://github.com/davidrobert/mathoms/pull/263)) — CLI standalone de e0_route/e0_unlock/e2_extract deletada.
- ☑ PR1b ([#265](https://github.com/davidrobert/mathoms/pull/265)) — `reset_workspace_from_stage` extraído + `e_reset.py` deletado (1406 LoC).
- ☑ PR1.5 ([#264](https://github.com/davidrobert/mathoms/pull/264)) — runbook `pipeline_rollback.md` criado.
- ☐ Soak ≥7d em staging — gate operacional pós-PR3b (não bloqueia merge; condiciona roll-out 100%).
- ☑ PR3a ([#266](https://github.com/davidrobert/mathoms/pull/266)) — hot-path DBArtifactStore hard-wired; dev scripts deletados.
- ☑ PR3b ([#267](https://github.com/davidrobert/mathoms/pull/267)) — DiskArtifactStore class deletada; WorkspaceContext raise; goldens refatorados.
- ☑ PR4 — Alembic drop coluna + remove flag + arquiva runbook (este PR).
- ☑ [[ADR-212]] flippada `Proposto` → `Decidido (A12.sunset-disk-artifact)` neste PR4.
- ☑ [[ADR-118]] + [[ADR-106]] confirmadas com `superseded_by: [[ADR-212]]` (declaração bidirecional em 2026-05-14).
- ☑ [[ADR-083]] §Contexto bullet 1 marcada como obsoleta no corpo da ADR-212 (supersedure parcial documentada).
- ☑ [[ADR-120]] fallback de disco removido (PR3b deletou `_read_from_disk`).
- ☐ Canary 10%/72h em staging antes de roll-out 100% (sre-devops P0).

## Status (reconciliação 2026-07-08)

Lane **entregue em `main`** entre 2026-05-13 e 2026-05-15 (PRs #262-#268 +
docs #264/#269/#270/#272); [[ADR-212]] `Decidido (A12.sunset-disk-artifact)`.
`DiskArtifactStore` não existe mais no código — DB-only é invariante
documentado em CLAUDE.md §"ArtifactStore é DB-only". Os 2 gates operacionais
de staging (soak 7d, canary 10%/72h) nunca foram registrados como executados;
o cutover está operante em produção desde então sem incidente registrado —
gates considerados superados pelo tempo em produção, não bloqueiam o `shipped`
(a própria DoD os marca como "não bloqueia merge"). Frontmatter estava stale
(`open`) desde a pausa da sprint ([[ADR-234]]); reconciliado nesta data.
