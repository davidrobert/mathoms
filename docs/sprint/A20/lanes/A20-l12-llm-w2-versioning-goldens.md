---
id: A20.l12
type: lane
title: "LLM Hardening — W2 semver puro + goldens fiscais BR + LLMCallLog SQL"
sprint: A20
plan: PLAN-llm-prompts-hardening
status: planned
priority: P0
branch_slug: a20-l12-llm-w2-versioning-goldens
depends_on:
  - "[[A20.l15]]"
  - "[[A20.l11]]"
parallel_with:
  - "[[A20.l13]]"
  - "[[A20.l14]]"
adrs:
  - "[[ADR-233]]"
  - "[[ADR-261]]"
tags:
  - type/lane
  - sprint/a20
  - status/planned
  - priority/p0
  - area/llm
  - area/observability
---

# A20.L12 — W2 semver puro + goldens fiscais + LLMCallLog SQL (3 PRs)

> **Onda 2 do plano [[PLAN-llm-prompts-hardening]].** Padroniza `PROMPT_VERSION` em semver puro ([[ADR-233]] errata §Migration) + cobre 7 fixtures `informe_previdencia` (público-alvo alta renda PJ) + persiste `confidence`/`needs_review` em SQL (desbloqueia [[A20.l13]] sem depender de [[PLAN-internal-admin]]).

## Objetivo

3 entregas sequenciais:

1. **Padronização**: 5 prompts legados (`apolice-v1.0.0`, `crlv-v1.0.0`, `e16-v1.1.0`, `informe-aluguel-v1.1.0` ou `1.2.0` pós-[[A20.l15]], `informe-prev-v1.0.0`) → semver puro `\d+\.\d+\.\d+`. Migration coordenada de `LLMCallLog.prompt_version` + `pipeline_artifacts.metadata.prompt_version`.
2. **Goldens fiscais**: 7 fixtures `informe_previdencia` cobrindo casos brasileiros típicos do público-alvo (`financial-planner` revisão).
3. **Telemetria SQL**: `LLMCallLog` ganha colunas `confidence` + `needs_review` (W2-T03). Desbloqueia análise SQL imediata.

## Critério de aceite (gate binário falsifiável)

- `dev/check_prompt_version_bumped.py` validando regex estrita `^\d+\.\d+\.\d+$` (errata [[ADR-233]] §Migration). 100% dos prompts.
- 100% dos 9 prompts em `tests/fixtures/llm_golden/` com ≥2 fixtures.
- `LLMCallLog.confidence`/`needs_review` populados em 100% das chamadas LLM pós-migration.
- Snapshot `_archive/llm_call_log_pre_semver_migration_<date>.csv` commitado.
- `pytest tests -q -k "informe_previdencia or e15_baseline or e1_members or e2_llm or e16"` verde.

## Sub-tarefas (3 PRs)

### W2-T01 — Migração para semver puro + errata [[ADR-233]] (~1d)

Migrar 5 prompts legados em PR coordenado:

| Prompt / schema | Versão legada | Versão pós-migration |
|---|---|---|
| `apolice.py` | `apolice-v1.0.0` | `1.0.0` |
| `crlv.py` | `crlv-v1.0.0` | `1.0.0` |
| `e16_irpf_full.py` (schema) | `e16-v1.1.0` | `1.1.0` |
| `informe_aluguel.py` (schema) | `1.2.0` (pós-[[A20.l15]]) | mantém — sem ação |
| `informe_previdencia.py` | `informe-prev-v1.0.0` | `1.0.0` |

Migration Alembic coordenada:

- Snapshot via `dev/snapshot_llm_call_log_history.py --all-legacy` ([[ADR-261]] §Snapshot histórico).
- `LLMCallLog.prompt_version`: regex map `^([\w-]+)-v(\d+\.\d+\.\d+)$ → \2`. Coluna `prompt_version_legacy` (text nullable) preserva original.
- `pipeline_artifacts.metadata.prompt_version`: JSON path UPDATE.
- `dev/check_prompt_version_bumped.py` → modo estrito (sem alternativa `<slug>-v`).
- Errata in-place em [docs/adr/233-prompt-version-format.md](../../../adr/233-prompt-version-format.md) §Migration flipa para `Decidido`.

### W2-T02 — Golden fixtures fiscais BR (~2d)

- **`informe_previdencia` — 7 fixtures** (revisão FP expandiu de 4 para 7):
  - PGBL progressivo (dedução 12% renda tributável).
  - PGBL regressivo (alíquota 35%→10% conforme tempo).
  - VGBL progressivo (raro mas legítimo).
  - PGBL patrocinador (empresa) → `needs_review=true`.
  - **PGBL+VGBL mesmo CPF/seguradora** (alta renda típica — deduz 12% via PGBL, excedente em VGBL).
  - **Regimes mistos PGBL prog + reg no mesmo CPF** (cliente 45-60 anos — aporte pré-2005 em prog).
  - **Portabilidade entre seguradoras no ano-base** (`saldo_01_01 ≠ saldo_31_12_ano_anterior`).
- **`e15_baseline`**: adicionar 2 fixtures (declaração truncada `confidence` baixa, baseline com dependente).
- **`e1_members`**: fixture família 5 membros já criada em [[A20.l15]] T02.
- **`e2_llm`**: fixture com `info_fiscal_anual` (v1.1.0 ADR-242 sem fixture que prova anti-double-counting).
- **`e16_irpf_full`**: 1 fixture "fail gracefully" (declaração truncada, confidence baixo, notes populado).

### W2-T03 — Persistência `confidence`/`needs_review` em `LLMCallLog` (~1d)

Migration Alembic em `backend/alembic/versions/`:

```python
op.add_column("llm_call_log", sa.Column("confidence", sa.Float, nullable=True))
op.add_column("llm_call_log", sa.Column("needs_review", sa.Boolean, nullable=False, default=False))
```

Adapter `litellm_client._record_call_log()` popula via `LLMCallResult` ([[ADR-260]]):

```python
log.confidence = result.confidence
log.needs_review = result.needs_review
```

**Antes do OTLP em [[A20.l13]].** Desbloqueia análise SQL via:

```sql
SELECT prompt_name, prompt_version, AVG(confidence), SUM(needs_review::int)::float / COUNT(*) AS rate
FROM llm_call_log
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY prompt_name, prompt_version;
```

## Coordenação

**Depende de**: [[A20.l15]] (W1α completo — `informe_aluguel` em `1.2.0` antes da migration coordenada) + [[A20.l11]] (W1β completo — `e15_baseline` em `1.1.0`).

**Paralelo a**: [[A20.l13]] (W3 OTLP) e [[A20.l14]] (W4 cross-cutting) — não competem por arquivos.

## Detalhe operacional

Plano canônico: [[PLAN-llm-prompts-hardening]] §W2. ADRs canônicas: [[ADR-233]] errata §Migration + [[ADR-261]] (cache invalidation).

**Capacity estimada**: ~4d eng-time.
