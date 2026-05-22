---
id: A20.l13
type: lane
title: "LLM Hardening — W3 telemetria OTLP mathoms.llm.* por prompt_version"
sprint: A20
plan: PLAN-llm-prompts-hardening
status: planned
priority: P1
branch_slug: a20-l13-llm-w3-telemetry
depends_on:
  - "[[A20.l12]]"
parallel_with:
  - "[[A20.l14]]"
adrs:
  - "[[ADR-260]]"
  - "[[ADR-110]]"
tags:
  - type/lane
  - sprint/a20
  - status/planned
  - priority/p1
  - area/llm
  - area/observability
---

# A20.L13 — W3 telemetria OTLP `mathoms.llm.*` (1 PR)

> **Onda 3 do plano [[PLAN-llm-prompts-hardening]].** Emit OTLP com labels compostos `{prompt_name, prompt_version}` ([[ADR-260]]). Dashboard `ops.mathoms.ai` é follow-up no plano [[PLAN-internal-admin]] — não bloqueia esta lane.

## Objetivo

Estender `LLMCallResult` ([pipeline/llm/litellm_client.py:69](../../../../pipeline/llm/litellm_client.py:69)) com `prompt_name`/`prompt_version`/`confidence`/`needs_review`/`cache_hit` (campos aditivos). Emit OTLP fica em `backend/app/services/document_processor.py` (boundary respeitado — pipeline retorna `LLMRunSummary`, backend instrumenta).

Calibra threshold 0.7/0.8 ([[ADR-081]]) com dado empírico de produção em vez de teoria.

## Critério de aceite (gate binário falsifiável)

- `LLMCallResult` ganha 5 campos opcionais (aditivo, não-breaking).
- OTLP histograms `mathoms.llm.confidence{prompt_name, prompt_version, model}` emitidos em produção (dogfood).
- 6 métricas OTLP novas/extends:
  - `mathoms.llm.confidence` (histogram).
  - `mathoms.llm.needs_review_total` (counter).
  - `mathoms.llm.cache_hit_total` (counter, **condicional**: confirmar se LiteLLM expõe sinal; senão drop).
  - `mathoms.llm.tokens_in/tokens_out/cost_usd` (extends — adicionar labels `prompt_*` aos counters existentes em [[ADR-110]]).
  - `mathoms.llm.parecer.riscos_truncados` (counter, do `parecer_planejador` quando >12).
- SQL query exemplo retorna ≥1 row por prompt em últimos 7 dias.
- Pipeline **NÃO** importa `backend.app.core.otel` (boundary respeitado).
- `pytest backend/tests -q -k "otel or telemetry"` verde.

## Sub-tarefas (1 PR)

### W3-T01 — Estender `LLMCallResult` + emit OTLP no consumer backend (~2d)

Mudanças em `pipeline/llm/litellm_client.py:69`:

```python
@dataclass
class LLMCallResult:
    # ... campos existentes ...
    prompt_name: str | None = None
    prompt_version: str | None = None
    confidence: float | None = None
    needs_review: bool = False
    cache_hit: bool = False  # condicional
```

Helpers em `pipeline/llm/`:

- `_extract_confidence(output) -> float | None` via `getattr(output, "confidence", None)`.
- `_extract_needs_review(output)` lê `output.needs_review` ou computa `confidence < 0.7`.

Pipeline retorna `LLMRunSummary` agregado (sem emit OTLP). Emit OTLP fica em **`backend/app/services/document_processor.py`** (ou orchestrator stage runner) que consome o summary pós-chamada:

```python
# backend/app/services/document_processor.py
from backend.app.core.otel import meter

llm_confidence = meter.create_histogram("mathoms.llm.confidence")
llm_needs_review = meter.create_counter("mathoms.llm.needs_review_total")
# ... outras métricas

# Após call LLM:
for call in run_summary.calls:
    llm_confidence.record(call.confidence, attributes={
        "prompt_name": call.prompt_name,
        "prompt_version": call.prompt_version,
        "model": call.model,
    })
    if call.needs_review:
        llm_needs_review.add(1, attributes={
            "prompt_name": call.prompt_name,
            "prompt_version": call.prompt_version,
        })
```

Caso especial `parecer_planejador`: counter `mathoms.llm.parecer.riscos_truncados` quando LLM gera >12 riscos e orchestrator trunca.

## Coordenação

**Depende de**: [[A20.l12]] (W2-T03 — `LLMCallLog.confidence`/`needs_review` em SQL). Sem W2-T03, OTLP emit não tem ground truth para comparar.

**Paralelo a**: [[A20.l14]] (W4 cross-cutting) — não competem por arquivos.

## Detalhe operacional

Plano canônico: [[PLAN-llm-prompts-hardening]] §W3. ADRs canônicas: [[ADR-260]] (telemetria por prompt_version) + [[ADR-110]] (padrão `mathoms.*`).

**Capacity estimada**: ~2d eng-time.
