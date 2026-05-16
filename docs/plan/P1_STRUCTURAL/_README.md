---
id: PLAN-p1-structural
type: plan
title: P1 — Plano estrutural (motor canônico + pipeline offline)
status: paused
created_at: 2026-04-17
last_review: 2026-05-07
sprint_origem: null
sprint_atual: null
sprints_envolvidas: []
paused_at: 2026-05-06
pause_reason: Substituído por PLAN-platform-review (revisão multi-agente 2026-05-06).
adrs_canonical: []
tags:
  - type/plan
  - status/paused
---

# P1 — Plano estrutural (motor canônico + pipeline offline)

> **Escopo:** apenas decisões **estruturais** (pacotes, runners, CI, fronteiras). Regras de negócio novas ficam fora deste documento.
> **Pré-requisito:** [CANONICAL_ENGINE_P0.md](../../reference/CANONICAL_ENGINE_P0.md)
> **Status geral:** **concluído** (2026-04-17) — melhorias incrementais (mais goldens, `validate_artifact` em cada write) continuam no [BACKLOG.md](../../BACKLOG.md).

---

## 1. Objetivos

1. Um **único grafo de imports** para lógica de pipeline consumida por worker, testes e ferramentas locais.
2. **Runner offline** reproduzível no laptop (deterministic stages + mocks LLM opcionais).
3. **CLI fina** (sem regra de negócio) apenas como fachada do runner.
4. **CI** que falhe em artefatos inválidos quando política strict estiver ativa.

---

## 2. Fase A — Layout de pacotes e fronteiras

| Decisão | Proposta | Status |
| --- | --- | --- |
| Pacote canônico | `pipeline/` como único pacote de estágios importável; `scripts/` como implementação dos wrappers (ADR-013) | ✅ Mantido |
| Imports proibidos | `pipeline/**/*.py` não importa `fastapi`, `celery`, `sqlalchemy` | ✅ Verificado por `dev/check_pipeline_boundaries.py` + teste em `tests/test_run_dev_smoke.py` |
| Backend | Importa `pipeline.stages.*` apenas; sem duplicar E2–E5 em `api/` | ✅ Política documentada |

**Critério de aceite:** diagrama unidirecional `api/tasks → pipeline → scripts` — ver [ARCHITECTURE.md](../../reference/ARCHITECTURE.md) §7.

---

## 3. Fase B — Runner offline

| Componente | Entrega | Status |
| --- | --- | --- |
| CLI | `python -m pipeline.run_dev --root <tenant> [--stages … \| --from-stage …]` | ✅ `pipeline/run_dev.py` |
| LLM | `--include-llm` desliga skip dos estágios LLM (alinhado ao orchestrator) | ✅ |
| Testes | Smoke + tenant vazio | ✅ `tests/test_run_dev_smoke.py` |

---

## 4. Fase C — CLI fina

| Item | Status |
| --- | --- |
| Novo entrypoint de dev não duplica regra — delega ao orchestrator | ✅ `run_dev.py` |
| Produto = web; CLI = engenharia | ✅ Documentado em ARCHITECTURE / TESTING |

---

## 5. Fase D — Contratos e CI strict

| Etapa | Status |
| --- | --- |
| D1 `MATHOMS_PIPELINE_SCHEMA_MODE` | ✅ (P0) |
| D2 Job CI strict | ✅ `.github/workflows/ci.yml` — passo *Pipeline JSON schema strict* |
| D3 Checklist de artefatos | ✅ [PIPELINE_ARTIFACTS.md](../../reference/PIPELINE_ARTIFACTS.md) |

---

## 6. Fase E — Expansão golden

| Entrega | Status |
| --- | --- |
| Diretório `tests/fixtures/pipeline_golden/` | ✅ E2 + E3 + E4 mínimos |
| Testes jsonschema | ✅ `tests/test_pipeline_golden_fixtures.py` |
| E3 schema + fixture estática | ✅ `e3_reconciled.schema.json` + golden mínimo |
| E3 execução golden (E2→E3) | ✅ `tests/test_e3_golden_execution.py` |
| E4 execução golden (E3→E4) | ✅ `tests/test_e4_golden_execution.py` |
| E5 execução golden (E4→E5) | ✅ `tests/test_e5_golden_execution.py` |
| Baseline E1.5 em golden E4/E5 | ✅ fixture `e2/minimal-baseline-1.5_consolidated.json` + testes `*_with_baseline_patrimonial` |
| E6 execução golden (E5→HTML) | ❌ removido em [ADR-129](../../DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side) (2026-04-25) — `test_e6_golden_execution.py` deletado junto com `pipeline/stages/e6.py` |
| QA log (`logs/qa_log.md`) em goldens E4/E5 | ✅ `tests/pipeline_golden_asserts.py` |
| E5.N execução golden (E5→narrativas) | ✅ `tests/test_e5n_golden_execution.py` (validação antes do reset de globals; cenário cônjuge cobre `ana_cenarios`) |
| E2 PDF × registry (smoke parse) | ✅ `tests/test_e2_synthetic_pdf_parsers.py` — todos os `BANK_MODULES` com `_draw_*` + testes (`test_c6bank_*`, `test_bradesco_*`, `test_btgpactual_*` … `test_caixa_*`, `test_quintoandar_*`) |
| LLM JSON × schemas Pydantic | ✅ `tests/fixtures/llm_golden/` + `tests/test_llm_golden.py` — [README](../../../tests/fixtures/llm_golden/README.md) |
| E2 PDF real anonimizado (fase 2) | ☐ Binários opcionais; scaffold ✅ | `tests/fixtures/e2_real_pdf_anon/` + `tests/test_e2_real_pdf_regression.py` — [PIPELINE_ARTIFACTS.md](../../reference/PIPELINE_ARTIFACTS.md) § *E2 — sintético e real anonimizado*; [BACKLOG.md](../../BACKLOG.md) |

---

## 7. Ordem de execução (histórico)

1. A → D2 → B → E → C (conforme planejado; entregue na mesma leva).

---

## 8. Riscos

| Risco | Mitigação |
| --- | --- |
| Refactor grande quebra Celery | Mudanças em fatias; paridade de fixture |
| Strict quebra runs legados | Fixtures mínimas + job só em `test_schema_validation.py` |

---

## Referências

- [CANONICAL_ENGINE_P0.md](../../reference/CANONICAL_ENGINE_P0.md)
- [PIPELINE_ARTIFACTS.md](../../reference/PIPELINE_ARTIFACTS.md)
- [ARCHITECTURE.md](../../reference/ARCHITECTURE.md) §7
- [DECISIONS.md](../../DECISIONS.md) ADR-013, 075, 077
