---
id: ADR-260
type: adr
title: "Telemetria LLM por prompt_version — labels compostos em LLMCallLog SQL + OTLP"
status: Proposto
phase: A20.W2 + A20.W3
date: "2026-05-22"
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-110]]"
  - "[[ADR-233]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 260"
  - "LLM telemetry"
  - "Confidence telemetry"
tags:
  - area/llm
  - area/observability
  - area/pipeline
  - status/proposto
  - type/adr
---

# ADR-260 — Telemetria LLM por prompt_version: SQL + OTLP com labels compostos

**Status:** Proposto • **Data:** 2026-05-22 • **Relaciona** [[ADR-081]] (threshold 0.7/0.8), [[ADR-110]] (logging estruturado + OTLP), [[ADR-233]] (formato semver puro).

> **Nota de estado (audit r6, 2026-07-03):** camada 2 **implementada** —
> colunas SQL `confidence`/`needs_review` em
> `backend/app/models/llm_call_log.py:42-43` (A20.l12, PR #720). Camadas 1
> (`LLMCallResult` em `pipeline/llm/litellm_client.py` segue sem
> `confidence`/`needs_review`) e 3 (OTLP `mathoms.llm.confidence`)
> **pendentes**; nenhum consumer popula `confidence` ainda.
>
> **Atualização (audit r7, 2026-07-09):** camada 3 (OTLP `mathoms.llm.*`)
> **shipou** — `mathoms.llm.confidence`/`needs_review` + labels
> `prompt_name`/`prompt_version`/`model` em `backend/app/core/llm_metrics.py`
> (A33.l7, #834). Resta só a camada 1 (`confidence` em `LLMCallResult`). Flip
> Proposto→Decidido é decisão do owner.

## Contexto

Padrão canônico do Mathoms é regex→LLM→`needs_review` ([[ADR-081]]): LLM com `confidence < 0.8` escala; `< 0.7` marca `needs_review=true`. **Thresholds são teoria sem dado empírico em produção** — não há telemetria que mede distribuição de confidence por prompt em dogfood.

Estado atual (verificado em `pipeline/llm/litellm_client.py:69-86`):

- `LLMCallResult` captura `tokens_in`, `tokens_out`, `cost_estimate_usd`, `duration_ms`, `retries_used`, `cost_known`. **Não captura `confidence` nem `prompt_version`**.
- `LLMRunSummary` agrega tokens/custo/duração; nenhuma dimensão por prompt.
- `LLMCallLog` (modelo SQL `backend/app/models/llm_call_log.py`) tem coluna `prompt_version: String(40)` mas **não tem `confidence` nem `needs_review`**.
- OTLP em `backend/app/core/otel.py` ([[ADR-110]]) exporta `mathoms.*` mas não tem métricas por prompt.

Sem essa instrumentação:

- **Calibração de threshold é cega**: 0.7/0.8 podem estar mal-calibrados em produção sem ninguém detectar.
- **Drift por bump não tem dado**: bump de `PROMPT_VERSION` (`1.0.0 → 1.1.0`) pode degradar qualidade silenciosamente.
- **Custo por prompt não é dimensionado**: `LLMRunSummary` agrega tokens mas não diz qual prompt domina o custo.
- **Cap do `parecer_planejador` (≤12 riscos) é arbitrário**: não há contagem de quantas vezes o LLM gera >12 e é truncado.

Revisão paralela do plano [[PLAN-llm-prompts-hardening]] em 2026-05-22 (`data-engineer` + `senior-cto`) decidiu:

1. **Persistência SQL precede OTLP** — `LLMCallLog` ganha colunas `confidence` + `needs_review` antes de emit OTLP. Desbloqueia análise SQL imediata sem depender de dashboard `ops.mathoms.ai` (plano [[PLAN-internal-admin]]).
2. **Labels compostos `{prompt_name, prompt_version}`** — slug embutido em `PROMPT_VERSION` é redundância. [[ADR-233]] já decidiu semver puro (`1.0.0`); coordenada de dimensão vem do label `prompt_name` ("e15_baseline", "parecer_planejador"), não da string.
3. **Pipeline NÃO emite OTLP** — boundary [CLAUDE.md] §"Pipeline não importa framework". `pipeline/llm/` retorna `LLMRunSummary` agregado; emit OTLP fica em `backend/app/services/document_processor.py` (ou orchestrator stage runner).

## Decisão

**Telemetria em 3 camadas:**

### 1. `LLMCallResult` aditivo — captura `confidence`/`prompt_*`/`needs_review`

Adicionar campos a [pipeline/llm/litellm_client.py:69](../../pipeline/llm/litellm_client.py:69) `LLMCallResult` (aditivo, não-breaking):

```python
@dataclass
class LLMCallResult:
    # ... campos existentes ...
    prompt_name: str | None = None       # label dimensão ("e15_baseline", ...)
    prompt_version: str | None = None    # label tempo ("1.0.0")
    confidence: float | None = None      # lido do output Pydantic
    needs_review: bool = False           # confidence < 0.7 ou flag explícita
    cache_hit: bool = False              # se LiteLLM expõe; senão drop campo
```

Helpers `_extract_confidence(output) -> float | None` via `getattr(output, "confidence", None)`. Helper `_extract_needs_review(output)` lê `output.needs_review` quando schema declara, senão computa `confidence < 0.7`.

### 2. `LLMCallLog` SQL — colunas `confidence` + `needs_review` (W2-T03)

Migration Alembic adiciona:

```python
confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

`prompt_version` já existe (String(40)). Adapter `litellm_client._record_call_log()` popula via `LLMCallResult` pós-W3-T01.

Desbloqueia análise SQL imediata:

```sql
SELECT prompt_name, prompt_version,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY confidence) AS p50,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY confidence) AS p95,
       SUM(CASE WHEN needs_review THEN 1 ELSE 0 END)::float / COUNT(*) AS needs_review_rate
FROM llm_call_log
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY prompt_name, prompt_version
ORDER BY prompt_name, prompt_version;
```

### 3. OTLP `mathoms.llm.*` com labels compostos (W3-T01)

Emit em `backend/app/services/document_processor.py` (ou orchestrator) após cada chamada LLM:

| Métrica | Tipo | Labels |
|---|---|---|
| `mathoms.llm.confidence` | histogram | `prompt_name`, `prompt_version`, `model` |
| `mathoms.llm.needs_review_total` | counter | `prompt_name`, `prompt_version` |
| `mathoms.llm.cache_hit_total` | counter (condicional) | `prompt_name`, `prompt_version` |
| `mathoms.llm.tokens_in` | counter (extend) | `prompt_name`, `prompt_version`, `model` |
| `mathoms.llm.tokens_out` | counter (extend) | `prompt_name`, `prompt_version`, `model` |
| `mathoms.llm.cost_usd` | counter (extend) | `prompt_name`, `prompt_version`, `model` |
| `mathoms.llm.parecer.riscos_truncados` | counter | `prompt_version` (apenas `parecer_planejador`) |

`tokens_in/out/cost_usd` já existem em [[ADR-110]] mas sem labels `prompt_*` — extender, não substituir.

## Implicações

- **Migration Alembic**: 2 colunas em `llm_call_log` (aditivo, nullable + default). Rollback simples.
- **3 helpers em `pipeline/llm/litellm_client.py`**: `_extract_confidence`, `_extract_needs_review`, `_record_call_log` extend.
- **1 ponto de emit OTLP novo** em `backend/app/services/document_processor.py`.
- **6 métricas OTLP novas** (5 extends + 1 nova `parecer.riscos_truncados`).
- **Dashboards downstream**: SQL query desbloqueada imediato; dashboard `ops.mathoms.ai` é follow-up no plano [[PLAN-internal-admin]] (não bloqueia esta ADR).

## Alternativas consideradas

**A. Embutir `prompt_name` no `prompt_version` (ex.: `e15-v1.0.0`).** Rejeitado: [[ADR-233]] decidiu semver puro 2026-05-20 por motivo de grep histórico + comparação exata em testes. Label OTLP composto resolve sem alterar o formato.

**B. OTLP-only (sem SQL).** Rejeitado pelo `data-engineer`: dashboard `ops.mathoms.ai` depende de [[PLAN-internal-admin]] que pode demorar. Persistir em `LLMCallLog` desbloqueia análise via SQL em horas vs. semanas.

**C. Pipeline emite OTLP direto.** Rejeitado: viola boundary [CLAUDE.md] §"Pipeline não importa framework". Pipeline retorna `LLMRunSummary`; backend instrumenta.

**D. Capturar `cache_hit` sem verificar LiteLLM.** Condicionado: incluir campo no `LLMCallResult` apenas se LiteLLM expõe sinal de cache hit (verificar antes do PR; senão drop).

## Referências

- Plano canônico: [[PLAN-llm-prompts-hardening]] §W2-T03 + §W3-T01.
- [[ADR-110]] padrão `mathoms.*` para métricas/logs estruturados.
- [[ADR-081]] threshold 0.7/0.8 para `needs_review`.
- [[ADR-233]] formato canônico `PROMPT_VERSION` semver puro.
