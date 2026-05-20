---
id: TRACK-a11-w2-t04-stuck-runs-heartbeat
type: track
title: "W2-T04 — Stuck-runs detector + last_heartbeat_at"
lane: "[[A11.w2]]"
sprint: A11
plan: PLAN-platform-review
status: ready
created_at: "2026-05-20"
agent_role: sre-devops
tags:
  - type/track
  - sprint/a11
  - status/ready
  - area/backend
  - area/ops
  - phase/a11
---

# Track — W2-T04 Stuck-runs detector + last_heartbeat_at

> **Lane ID:** A11.W2 · Task T04
> **Branch prefix:** `agent/platform-review-w2-t04/<yyyyMMdd-HHmm>`
> **Severidade:** P0 · **Effort:** S
> **Owner agent:** sre-devops
> **Deps:** [[ADR-172]] (`Proposto`) — flip para `Decidido (Sprint A11.W2)` no merge do PR.
> **Paralelo com:** W2-T02 (security headers), W2-T05 (prompt version gate), W2-T06 (stage suffix).
> **Destrava:** Wave 3 inteira (após Wave 2 fechar).

## Contexto que você DEVE ler antes de agir

Em ordem:

1. `CLAUDE.md` (raiz) — atenção especial: §"Concluído" · §"Subagentes especializados" · §"Antes de pegar uma task do BACKLOG" · §"Cadência de commit defensiva" · §"Pipeline não importa framework" · §"ADRs → docs/adr/" · §"Política operacional — ADR Proposto antes de PR P0/P1" · §"Stateless rigoroso".
2. `docs/adr/172-stuck-runs-detector.md` (ou slug equivalente — `rg "stuck-runs" docs/adr/`) — ADR-172 `Proposto`. **Esta ADR vira `Decidido (Sprint A11.W2)` no merge do seu PR.**
3. `docs/sprint/A11/_README.md` — DoD code-complete pós-[[ADR-228]].
4. `docs/plan/PLATFORM_REVIEW/_README.md` §[W2-T04] — files_touched + acceptance_criteria oficiais.
5. Arquivos relevantes:
   - `backend/app/models/pipeline_run.py` (model + enum)
   - `backend/app/tasks/pipeline_task.py` (stage execution)
   - `backend/app/tasks/celery_beat_schedule.py` (beat tasks)
   - `backend/alembic/versions/` (padrão de migration mais recente)

## Estado de entrada (2026-05-20)

- W1 ✅ 8/8 + W2-T03 ✅ + W2-T01 PR #359 aberto/mergeando.
- W2-T02 em paralelo (worktree `crazy-borg-f27ed8` — NÃO toque).
- W2-T05 e W2-T06 em paralelo (worktrees separados).
- 11-12/32 done. W2-T04 destrava Wave 3 (T01 LLM budget, T03 JWT, T04 Fernet, T05 prompt injection) após Wave 2 fechar.
- ADR-172 (`Proposto`) já tem decisão arquitetural — você implementa, não redesenha.

## Pickup checks obrigatórios

```bash
git fetch origin
git worktree list  # detecta agentes locais sem commit ainda
git for-each-ref --sort=-committerdate \
  --format='%(committerdate:iso) %(refname:short)' \
  refs/remotes/origin/agent/ | head -15
```

Procure conflito com `agent/platform-review-w2-t04-*`. Worktree `crazy-borg-f27ed8` está em W2-T02 — disjunto, não toque.

## Branch + ordem

1. `git checkout -b agent/platform-review-w2-t04/<yyyyMMdd-HHmm> origin/main`
2. **Não precisa criar ADR nova** — ADR-172 já está em `Proposto`. No PR de implementação, ela vira `Decidido (Sprint A11.W2)` via update do frontmatter no mesmo commit ou em PR doc-only de closure.
3. **Delegação obrigatória** (CLAUDE.md §"Protocolo de delegação"):
   - `sre-devops` — owner principal (heartbeat strategy + Celery beat timing + observabilidade).
   - `data-engineer` em paralelo se mudança em `PipelineRun` schema afetar consumidores (vai ler `pipeline_artifacts` correlacionados?).
   - Brief mínimo: contexto W2-T04 + premissas + recomendação inicial. **NÃO peça código** — peça decisão/refino.

## Implementação

Files-touched (do PLAN):

- `backend/alembic/versions/<NOVO>_pipeline_runs_heartbeat.py` — NOVO, adiciona coluna `last_heartbeat_at` (timestamp) em `pipeline_runs`. Use `pytestmark = pytest.mark.migration` no teste correspondente (CLAUDE.md §"Saúde do test suite (ADR-210)").
- `backend/app/models/pipeline_run.py` — adicionar `Mapped[Optional[datetime]] last_heartbeat_at`.
- `backend/app/tasks/pipeline_task.py` — em `_record_stage_result` (ou equivalente no start de cada stage), atualizar `pipeline_run.last_heartbeat_at = utcnow()`.
- `backend/app/tasks/celery_beat_schedule.py` — adicionar entry `fin.detect_stuck_runs` agendada a cada 5min.
- `backend/app/tasks/<NOVO>.py` — task que faz scan: runs com `status=running` E `last_heartbeat_at < now - threshold` → marca `status=failed`, `failure_reason='heartbeat_timeout'`, cria `Notification`, emite métrica/log estruturado `mathoms.pipeline.stuck_run_detected`.
- Threshold default 15min (configurável via env). Documente em ADR-172 no momento do flip Decidido.

## Tests

- `backend/tests/test_pipeline_run_heartbeat.py` (NOVO) — assert que stage start atualiza `last_heartbeat_at`.
- `backend/tests/test_detect_stuck_runs.py` (NOVO) — assert que:
  - run com heartbeat recente NÃO é marcado failed
  - run sem heartbeat acima do threshold É marcado failed
  - Notification criada
  - run já em estado terminal NÃO é tocado
- `pytestmark = pytest.mark.migration` no teste da migration.

## Validação obrigatória pré-push

```bash
python3 -m pre_commit run --all-files
pytest backend/tests -q --ignore=backend/tests/integration
pytest tests -q --ignore=tests/integration
python3 dev/check_code_style_regression.py  # apenas melhorias OK
```

## Commit + PR

```bash
git commit -m "feat(backend): ADR-172 W2-T04 — stuck-runs detector + last_heartbeat_at (Sprint A11.W2)"
git push origin agent/platform-review-w2-t04/<yyyyMMdd-HHmm>
gh pr create --base main --title "..." --body "..."
gh pr merge <N> --squash --auto
```

No mesmo PR ou follow-up doc-only: flip ADR-172 `Proposto` → `Decidido (Sprint A11.W2)` + section "Closure" referenciando PR + marcar W2-T04 done no Index `docs/plan/PLATFORM_REVIEW/_README.md`.

## Anti-padrões a evitar

- ❌ Threshold hardcoded sem env config.
- ❌ Task de detect rodando sem idempotência (re-run não pode marcar runs já failed).
- ❌ Pular ADR closure (Proposto → Decidido no merge).
- ❌ Push direto em `main`; auto-merge squash via Ruleset.
- ❌ Esquecer regression check style (`dev/check_code_style_regression.py`).
- ❌ Estado in-memory para tracking de runs (CLAUDE.md §"Stateless rigoroso") — tudo no DB.

## Critério de fim

- PR aberto com CI rodando OU mergeado.
- ADR-172 flippada para `Decidido (Sprint A11.W2)`.
- W2-T04 marcado done no Index do PLAN.
- CLAUDE.md §Cadência respeitada (commit antes de devolver turno).
