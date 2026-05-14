---
id: A12.sunset-disk-artifact
type: lane
title: "Sunset DiskArtifactStore + flag MATHOMS_USE_DB_ARTIFACTS + CLI standalone"
sprint: A12
status: open
aliases: ["A12.sunset-disk", "A12.SUNSET_DISK_ARTIFACT"]
priority: P1
depends_on: []
parallel_with: ["[[A12.cat-learning-loop]]", "[[A12.alocacao-v2]]"]
adrs_canonical:
  - "[[ADR-212]]"
tags:
  - type/lane
  - sprint/a12
  - status/open
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
  [PLATFORM_REVIEW](../../../plan/PLATFORM_REVIEW/_README.md); trigger
  10GB ou 1M rows.

## Definition of Done

- ☐ PR2 mergeado em `main` com CI verde.
- ☐ PR1 mergeado; `reset_workspace_from_stage` com teste unitário sob `InMemoryArtifactStore`.
- ☐ PR1.5 mergeado; runbook revisado pelo oncall.
- ☐ Soak ≥7d em staging entre PR1.5 e PR3 (sem alertas em `mathoms.pipeline`).
- ☐ PR3 mergeado; canary 10%/72h concluído sem regressão; goldens verdes.
- ☐ PR4 mergeado; coluna `workspaces.use_db_artifacts_override` removida; `USE_DB_ARTIFACTS` removido de settings; `docs/reference/runbooks/cutover.md` arquivado em `docs/archive/cutover-YYYY-MM-DD.md`.
- ☐ [[ADR-212]] flippada `Proposto` → `Decidido (A12.sunset-disk-artifact)` no PR4.
- ☐ [[ADR-118]] + [[ADR-106]] confirmadas com `superseded_by: [[ADR-212]]` (já declarado bidirecional em 2026-05-14).
- ☐ [[ADR-083]] §Contexto bullet 1 marcada como obsoleta no corpo da ADR-212 (supersedure parcial documentada).
- ☐ [[ADR-120]] atualizada — fallback de disco descrito como removido.
