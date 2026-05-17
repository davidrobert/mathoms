---
id: MOC-sprint-a10
type: moc
title: Sprint A10 — goals.json cutover final
aliases: ["A10", "Sprint A10"]
sprint_status: done
---

# Sprint A10 — `goals.json` cutover final (proposta 2026-05-06)

> **Status:** done — 9/9 lanes em `main` (PRs #104, #107, #108, #113, #116, #117, #118, #119, #122) entregues 2026-05-07.

## Resumo

Fechar o último frente da migração `config/*.json` → DB-first iniciada em A7, eliminando `goals.json` (arquivado) como fonte de dados em runtime e migrando as 18 chaves residuais para `Decision`/`Risk` aggregates, rules-as-code, ou deleção (dead data ADR-168).

ADR-077 §"Contrato de cutover" fechado por ADR-180 (A10.6) + ADR-181 (A10.8). `config/goals.json` é path proibido em `dev/check_forbidden_paths.py`. Débito de 7 meses encerrado.

**Plano canônico (arquivado):** [docs/archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md](../../archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md) — 10 seções, 9 lanes em 4 ondas, 5 ADRs propostos (ADR-177 a ADR-181).

**ADRs decididos:** ADR-177 (rules-as-code consolidation `goals.json`), ADR-178 (`Risk` aggregate), ADR-179 (`Decision` schema extension), ADR-180 (StageConfig bundle + cutover, **supersedes** parcial ADR-077), ADR-181 (`forbidden_paths` + delete archived).

**Especialistas G0:** `senior-cto` ✅ + `financial-planner` ✅ (consultados 2026-05-06).

**Princípios não-negociáveis:** (P1) ADR-077 checkbox marcado ao fim; (P2) `pipeline/**` não importa SQLAlchemy/FastAPI; (P3) money sempre Decimal/cents (ADR-090); (P4) goldens E5/E5.N verdes byte-a-byte salvo PR de reset dedicado e justificado; (P5) ADR `Proposto` antes de PR de implementação (ADR-138); (P6) tenancy correta — `seed_goals_workspace.py` sem hardcode de `family_surname`; (P7) `_archive/.../goals.json` deletado, não re-arquivado.

## Por que esta sprint existiu

Sprint A7 (entregue 2026-04-27) era "config cutover" e atacou 5 JSONs + `decisions.md` + `docs/methodology/`, **mas bypassou `config/goals.json`** — apenas arquivado em `_archive/pre-f8-cutover-2026-04-15/`. `pipeline_task.py:78-86` ainda materializava `goals.json` físico em runtime para os scripts E5/E5.N lerem via filesystem; o card "Top 5 Decisões de Impacto" (S10) renderizava string hardcoded vinda do arquivo arquivado, ignorando o `Decision` aggregate. ADR-077 tinha checkbox aberto há 7 meses sobre "100% cobertura de campos lidos por E5/E5.N/E6". Esta sprint fechou o débito.

## Lanes

Ver [lanes.md](lanes.md) (tabela histórica) ou [`lanes/`](lanes).

## Waves

Mapa de dependências em [waves.md](waves.md) — 4 ondas: Onda 0 (ADRs Propostos) → Onda 1 (cleanup paralelo) → Onda 2 (aggregate work) → Onda 3 (pipeline cutover) → Onda 4 (cutover final bloqueante).

**Esforço estimado:** ~10 dias trabalho ativo. Wall-clock ~5-7 dias com 2-3 agentes paralelos. **Real:** sprint convergida em ~2 dias calendário (2026-05-06 a 2026-05-07).

## Definition of Done

```bash
# Checks finais (todos retornam verde)
test ! -f _archive/pre-f8-cutover-2026-04-15/config/goals.json
grep "config/goals.json" dev/check_forbidden_paths.py
grep -r "_materialize_adapter_configs" backend/app/ | wc -l   # = 0
grep -r "goals.json" backend/app/tasks/ | wc -l              # = 0
grep "PLANNING_CONTEXT" backend/app/models/goal.py | wc -l    # = 0
grep "class Risk" backend/app/models/risk.py                  # encontra
pytest tests -q && pytest backend/tests -q && pre-commit run --all-files
```

ADR-077 checkbox `Fechado por ADR-180` marcado; ADR-177 a ADR-181 todos `Decidido`.
