---
id: TRACK-a11-w2-t06-stage-to-suffix-descriptive
type: track
title: "W2-T06 — _STAGE_TO_SUFFIX cobre keys descritivas (paridade legacy ↔ descritivo)"
lane: "[[A11.w2]]"
sprint: A11
plan: PLAN-platform-review
status: ready
created_at: "2026-05-20"
agent_role: data-engineer
tags:
  - type/track
  - sprint/a11
  - status/ready
  - area/pipeline
  - phase/a11
---

# Track — W2-T06 _STAGE_TO_SUFFIX cobre keys descritivas

> **Lane ID:** A11.W2 · Task T06
> **Branch prefix:** `agent/platform-review-w2-t06/<yyyyMMdd-HHmm>`
> **Severidade:** P1 · **Effort:** S
> **Owner agent:** data-engineer
> **Deps:** nenhuma; segue [[ADR-093]] (janela compat F9.2→F9.6) + [[ADR-213]] (`_STAGE_TO_DIR` deletado).
> **Paralelo com:** W2-T02 (security headers), W2-T04 (heartbeat), W2-T05 (prompt version).
> **Destrava:** W6-T03 (F9.4/F9.5/F9.6 stage rename cleanup).

## Contexto que você DEVE ler antes de agir

1. `CLAUDE.md` (raiz) — §"Concluído" · §"Pipeline não importa framework" · §"Cadência de commit defensiva" · §"Antes de pegar uma task do BACKLOG" · §"Convenções de naming de artefatos" · §"Stage identifiers — F9.2+ usa nomes descritivos (ADR-093)".
2. `docs/adr/093-*.md` — janela de compat F9.2 → F9.6 (legacy vs descritivo).
3. `docs/adr/213-*.md` — `_STAGE_TO_DIR` deletado; `_STAGE_TO_SUFFIX` sobrevive como source-of-truth de 3 usos atuais (E3 `source_document`, E4 `_source`, E3 `generate_legacy_filename`).
4. `docs/sprint/A11/_README.md` — DoD code-complete.
5. `docs/archive/PLATFORM_REVIEW_PLAN-2026-07-08.md` §[W2-T06] — AC: cobertura completa + teste de paridade contra `STAGE_RENAME_MAP`.
6. Arquivos relevantes:
   - `pipeline/artifact_store.py` (onde vive `_STAGE_TO_SUFFIX`)
   - `pipeline/stage_spec.py` (onde vive `STAGE_RENAME_MAP` e `STAGE_REGISTRY`)
   - `tests/unit/pipeline/test_artifact_stores.py`

## Estado de entrada (2026-05-20)

- W1 ✅ + W2-T03 ✅ + W2-T01 PR #359 + W2-T02/T04/T05 em paralelo.
- W2-T06 destrava W6-T03 (F9.4/F9.5/F9.6 cleanup).
- CLAUDE.md já documenta que `_STAGE_TO_SUFFIX` é o source-of-truth. Tabela de keys ↔ sufixos está em §"Convenções de naming de artefatos".

## Pickup checks obrigatórios

```bash
git fetch origin
git worktree list
git for-each-ref --sort=-committerdate \
  --format='%(committerdate:iso) %(refname:short)' \
  refs/remotes/origin/agent/ | head -15
```

Procure `agent/platform-review-w2-t06-*`. Disjunto de T02 (worktree `crazy-borg-f27ed8`), T04, T05.

## Branch + ordem

1. `git checkout -b agent/platform-review-w2-t06/<yyyyMMdd-HHmm> origin/main`
2. **Delegação obrigatória**:
   - `data-engineer` — escopo de mapping contracts entre stages legacy ↔ descritivo. Brief mínimo: pedir confirmação de que todas as keys descritivas precisam entry em `_STAGE_TO_SUFFIX` (ou subset mais restrito). **NÃO peça código.**
3. **Não cria ADR nova** — segue [[ADR-093]] (janela de compat) + [[ADR-213]] (`_STAGE_TO_DIR` deletado).

## Implementação

- `pipeline/artifact_store.py::_STAGE_TO_SUFFIX`:
  - Auditar contra `STAGE_REGISTRY` / `STAGE_RENAME_MAP` em `pipeline/stage_spec.py`. Toda key em `STAGE_RENAME_MAP.values()` (descritiva) deve ter entry equivalente à key legacy correspondente.
  - Ex.: se `STAGE_RENAME_MAP["E3"] = "reconcile_transactions"` e `_STAGE_TO_SUFFIX["E3"] = "-3_reconciled"`, então `_STAGE_TO_SUFFIX["reconcile_transactions"] = "-3_reconciled"`.
  - Padrão de tabela está documentado em CLAUDE.md §"Convenções de naming de artefatos" — use como referência cruzada.

## Tests

- `tests/unit/pipeline/test_artifact_stores.py` — adicionar teste que itera `STAGE_RENAME_MAP.items()` e assert que ambos (legacy + descritivo) têm mesmo sufixo em `_STAGE_TO_SUFFIX`.
- Garantir que entries dead-code documentadas (`-5n_narrativas`, `-7_crossval`) **permanecem** (CLAUDE.md §"Convenções de naming" explicita que são dead code de write mas ficam no mapping).

## Validação obrigatória pré-push

```bash
python3 -m pre_commit run --all-files
pytest tests -q --ignore=tests/integration
pytest backend/tests -q --ignore=backend/tests/integration
python3 dev/check_code_style_regression.py
python3 dev/check_pipeline_boundaries.py  # garante isolamento
```

## Commit + PR

```bash
git commit -m "refactor(pipeline): W2-T06 — _STAGE_TO_SUFFIX cobre keys descritivas (Sprint A11.W2)"
git push origin agent/platform-review-w2-t06/<yyyyMMdd-HHmm>
gh pr create --base main --title "..." --body "..."
gh pr merge <N> --squash --auto
```

Corpo: cite [[ADR-093]] + [[ADR-213]], explique paridade legacy ↔ descritivo. Após merge: update Index PLAN W2-T06 → done. **W6-T03 fica destravada** — anote no NEXT UP do PLAN.

## Anti-padrões a evitar

- ❌ Remover entries legacy (`"E3"`, `"E4"` etc.) — janela de compat F9.2 → F9.6 ainda ativa. [[ADR-093]] explícita.
- ❌ Tocar `pipeline/stage_spec.py` `STAGE_RENAME_MAP` (escopo de W6-T03, não T06).
- ❌ Tocar `backend/app/services/db_artifact_store.py` `SCHEMA_BY_STAGE` (esse é outro mapping; T06 só toca `_STAGE_TO_SUFFIX`).
- ❌ Esquecer entries dead-code (`-5n_narrativas`, `-7_crossval`) — ficam no mapping mesmo sendo dead code (documentado em CLAUDE.md).
- ❌ Push direto em `main`; auto-merge squash via Ruleset.

## Critério de fim

- PR aberto com CI rodando OU mergeado.
- W2-T06 marcado done no Index PLAN.
- W6-T03 destravada (atualizar NEXT UP do PLAN).
- Teste de paridade itera `STAGE_RENAME_MAP` e valida cobertura completa.
