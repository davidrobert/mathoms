# GO_PORT_DEPS — Inventário de dependências do `pipeline-service` para migração Go

> **Status:** referência (não-plano) · **Data inicial:** 2026-04-27 · **Origem:** A1 do tópico "preparar contexto para Go rewrite" (proposto na conversa com CTO)
>
> **Escopo:** dimensionar exatamente o que o shell HTTP em [pipeline-service/](../pipeline-service/) importa do core Python em [pipeline/](../pipeline/), para que o ADR de estratégia de port (Caminho 1/2/3) seja escrito com dados, não especulação.
>
> **ADRs relacionadas:** [ADR-112](DECISIONS.md#adr-112--pipeline-as-service-http-boundary-para-execução-de-stages-a6f1) (HTTP boundary), [ADR-113](DECISIONS.md#adr-113--convenções-go-golangciyml--ci--skeleton-a6g7) (convenções Go), [ADR-102 R18-R20](DECISIONS.md#adr-102--princípios-r18-r20-language-neutral-boundaries-a6f) (language-neutral boundaries), [ADR-111](DECISIONS.md#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6) (stateless rigoroso).

---

## TL;DR

| Métrica | Valor |
| --- | --- |
| **Shell HTTP** (pipeline-service) | **532 LOC** Python em **14 arquivos** |
| **Símbolos importados de `pipeline.*`** pelo shell | **5 distintos** (3 módulos: `context`, `orchestrator`, `stage_spec`) |
| **Imports de `backend.*`** pelo shell | **1** (opcional, `setup_logging`) |
| **Core Python que o shell aciona** | `pipeline/` = **108 arquivos · 17.823 LOC** |
| **Domain services** (`pipeline/domain/`) | **61 arquivos · 13.077 LOC** |
| **Stage runners** (`pipeline/stages/`) | 16 arquivos · 1.561 LOC (são thin wrappers que delegam para `domain/services/` ou `scripts/`) |

**Conclusão operacional:** o shell HTTP é portável em ~600 LOC Go. O domínio (que faz o trabalho real) tem ~17 mil LOC e é o que define se a migração é semanas ou meses.

---

## 1. Imports diretos do shell para `pipeline/`

Comando reproduzível:
```bash
grep -rn "from pipeline\.\|import pipeline\." pipeline-service/app/ --include="*.py"
```

| # | Símbolo | Origem | Consumidor (arquivo:linha) | Papel |
| - | --- | --- | --- | --- |
| D1 | `WorkspaceContext` (dataclass, 200 LOC) | `pipeline.context` | [run_coordinator.py:19](../pipeline-service/app/services/run_coordinator.py:19), [stage_executor.py:37](../pipeline-service/app/services/stage_executor.py:37) | Container de paths + config + run_id. Construído por request, descartado depois. |
| D2 | `_run_stage(ctx, stage) -> StageResult` | `pipeline.orchestrator` | [run_coordinator.py:20](../pipeline-service/app/services/run_coordinator.py:20), [stage_executor.py:18](../pipeline-service/app/services/stage_executor.py:18) | **Hot path.** Wrapper que captura stdout/stderr, OTel span, exit codes, e dispatcha pro runner correto via `_get_stage_runner`. |
| D3 | `LLM_STAGES` (set) | `pipeline.orchestrator` | [run_coordinator.py:20](../pipeline-service/app/services/run_coordinator.py:20) | Set de nomes de stage que envolvem LLM — usado para honrar `skip_llm` na request. |
| D4 | `StageResult` (dataclass) | `pipeline.orchestrator` | testes (`test_stage_execution.py`, `test_run_coordinator.py`) | DTO retornado por `_run_stage`. Apenas testes importam diretamente; produção recebe via `_run_stage`. |
| D5 | `STAGE_REGISTRY` (dict) | `pipeline.stage_spec` ([ADR-093](DECISIONS.md#adr-093--rename-completo-de-identificadores-de-stage-opção-a)) | [api/stages.py:16](../pipeline-service/app/api/stages.py:16), [api/runs.py:20](../pipeline-service/app/api/runs.py:20) | Dict de `StageSpec` — usado para validar que `stage` recebido na request existe. |

**Bonus (`backend/`):**

| # | Símbolo | Origem | Consumidor | Papel |
| - | --- | --- | --- | --- |
| B1 | `setup_logging` | `backend.app.core.logging` | [main.py:60](../pipeline-service/app/main.py:60) | Wire JSON logs ([ADR-110](DECISIONS.md#adr-110--structured-json-logging--opentelemetry-bootstrap-a6f3)). **Opcional** — fallback para `logging.basicConfig` se backend não importável. |

**`B1` é o único acoplamento ao `backend/`.** Já tem fallback. Em Go vira `slog` direto — eliminado naturalmente.

---

## 2. Cadeia transitiva por símbolo

### D1 · `WorkspaceContext` (porta cleanly)

`pipeline/context.py` (200 LOC) é dataclass puro:
- 14 campos `Path` derivados de `root` (sem I/O, só path arithmetic)
- `load_config(name) -> dict` — lê JSON do disco
- `get_artifact_store()` — singleton lazy de `DiskArtifactStore`
- `for_tenant(...)` — factory

**Dependências externas:** `json`, `pathlib`, `dataclasses`. Zero deps de domínio.
**Port em Go:** struct + métodos. ~150 LOC. Trivial.

### D2 · `_run_stage` (o ponto difícil)

`pipeline/orchestrator.py` (381 LOC) chama em runtime, via `_get_stage_runner`:

```python
# orchestrator.py:125-196 — switch sobre o nome do stage
if stage == "reconcile_transactions":
    from pipeline.stages.reconcile_transactions import run
    return run
# ... 16 cases
```

Cada `pipeline/stages/<name>.py` é thin wrapper (17–477 LOC, mediana ~38) que delega para `pipeline/domain/services/` ou para scripts em `scripts/eN_*.py`.

**Stages e suas dependências reais:**

| Stage | LOC wrapper | Núcleo onde mora a lógica |
| --- | --- | --- |
| `unlock_documents` | 17 | `pipeline/domain/services/document_unlocker.py` (não medido) |
| `audit_documents` | 17 | `scripts/e0_audit.py` |
| `route_documents` | 38 | `scripts/e0_route.py` + `backend/app/services/document_classification.py` (LLM) |
| `extract_members` | 178 | `pipeline/domain/services/member_analyzer.py` (286) + LLM |
| `extract_baseline` | 287 | `pipeline/domain/services/patrimonio_*.py` (~1.090) + LLM |
| `consolidate_baseline` | 40 | `scripts/e1_consolidate.py` |
| `extract_with_llm` | 477 | `pipeline/llm/litellm_client.py` (488) + LLM heavy |
| `extract_invoices` | 19 | `scripts/e2_invoices/banks/*.py` |
| `extract_statements` | 19 | `pipeline/domain/services/statement_preprocessor.py` (454) + `scripts/e2_extract.py` |
| `reconcile_transactions` | 18 | `pipeline/domain/services/reconciliation_service.py` (155) + `reconciliation_validators.py` (240) + `source_tier.py` (149) |
| `categorize_transactions` | 38 | `pipeline/domain/services/transaction_classifier.py` (355) + `keyword_matcher.py` (103) |
| `analyze_finances` | 38 | `pipeline/domain/services/{patrimonio,ratios,reserva_emergencia,orcamento}_*.py` (~770) |
| `generate_narratives` | 17 | `pipeline/domain/services/section_summary_generator.py` (391) + LLM (opt) |
| `validate_cross` | 24 (validate_cross.py) | `scripts/e7_review.py` (só crossval pós-A12.X) |
| `review_finances_holistic` | ~250 | LLM-driven — substitui review_finances (ADR-199) |

**Total domain layer transitivamente acionado:** ~13.077 LOC em 61 arquivos.

### D3 · `LLM_STAGES` (set derivado)

`pipeline/orchestrator.py:84-89` — set construído a partir de `STAGE_REGISTRY[*].is_llm`. Sem deps externas além de `STAGE_REGISTRY`. Em Go: const map, ~10 LOC.

### D4 · `StageResult` (dataclass)

`pipeline/orchestrator.py:27-34` — 5 campos (`stage`, `success`, `duration_ms`, `detail`, `error`). Serializado para o wire por Pydantic em [contracts/stages.py](../pipeline-service/app/contracts/stages.py). Em Go: struct + JSON tags, ~15 LOC.

### D5 · `STAGE_REGISTRY` (catálogo de stages)

`pipeline/stage_spec.py` (278 LOC) define:
- `StageSpec` dataclass (id, descriptive_name, is_llm, …)
- `STAGE_REGISTRY: dict[str, StageSpec]` — 16 entradas
- `FULL_ORDER`, `DETERMINISTIC_ORDER` — slices ordenados
- `STAGE_RENAME_MAP`, `resolve_stage_name`, `to_legacy_stage_name` — compat F9.2 ([ADR-093](DECISIONS.md#adr-093--rename-completo-de-identificadores-de-stage-opção-a))

**Sem deps externas além de `dataclasses`.** Port em Go: ~250 LOC, derivar do mesmo input via codegen (ver §5).

---

## 3. Caminho de port — análise quantitativa

### Caminho 1 — Shell-only Go + Python via subprocess

**Porta:**
- [pipeline-service/app/](../pipeline-service/app/) → `services/pipeline-service-go/`
- ~600 LOC Go (api + run_coordinator + event_publisher + contracts)

**Mantém em Python:**
- `pipeline/` inteiro (17.823 LOC) — invocado via `python -m pipeline.orchestrator run-stage <name> --workspace <path>`
- **Pré-requisito ausente:** entry-point CLI no orchestrator (não existe hoje, `_run_stage` só é chamável programaticamente)

**Substitui:**
- `_run_stage` por `exec.Command("python", "-m", "pipeline.orchestrator", ...)` → captura stdout/stderr → parse JSON
- `WorkspaceContext` por struct Go local (não cruza fronteira)
- `STAGE_REGISTRY` por codegen do OpenAPI ou JSON estático regenerável

**Ganha:** binário estático ~15 MB, startup <100ms, deploy unificado, observabilidade `slog` JSON.
**Não ganha:** memória/CPU dos stages (continuam Python). Adiciona overhead `fork+exec` por stage (~50-200ms cold).

### Caminho 2 — Roteador Go + Python worker pool

**Porta:** mesmas ~600 LOC do Caminho 1.
**Adiciona:** Python worker pool externo (Celery, Gunicorn, ou daemon próprio) que mantém processos Python warm, evitando custo de `fork+exec` por stage.
**Trade-off:** complexidade de deployment maior. Ainda tem container Python na infra. Marginal vs. Caminho 1.

### Caminho 3 — Reescrita completa em Go

**Porta:** ~17.823 LOC Python → estimado **~25.000-35.000 LOC Go** (Go é mais verboso para business logic).
**Pontos críticos:**
- `pipeline/llm/litellm_client.py` (488) — LLM client (Anthropic + OpenAI). Equivalente Go: `anthropic-sdk-go` ou HTTP direto.
- `pipeline/domain/services/patrimonio_*.py` (~1.090) — math financeira complexa. Port linha-a-linha com testes de paridade.
- 16 stage runners + parsers (E2 banks, ~8 instituições) — cada um é trabalho próprio.
- Goldens existentes em `tests/test_e*_golden_*.py` viram **regression suite obrigatória** para validar paridade de port.

**Ganha:** sem GIL, footprint pleno, deploy estático puro.
**Custo realista:** sprint dedicado de **3-5 meses** com 1-2 engenheiros. Domain logic exige paridade com goldens (BRL `0.01` tolerance, [ADR-097](DECISIONS.md#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy)).

---

## 4. Riscos por símbolo

| Símbolo | Risco no port | Mitigação |
| --- | --- | --- |
| `WorkspaceContext.load_config` | Lê JSON do disco — se a config schema mudar, Go fica drift | Validar contra `config/schemas/*.schema.json` (já existem) |
| `_run_stage` captura stdout/stderr | Scripts legados em `scripts/eN_*.py` ainda usam `print()` para erros | Caminho 1: parse stderr capturado pelo subprocess. Caminho 3: errors tipados ([CLAUDE.md §Code style › Go](../CLAUDE.md)) |
| `LLM_STAGES` em runtime | Mudança em `STAGE_REGISTRY` propaga para shell — codegen ajuda | Snapshot test de `STAGE_REGISTRY` (já existe via OpenAPI snapshot transitivamente) |
| `StageResult.detail: dict` | Detail é livre — bancos exportam shape próprio | Em Go usar `json.RawMessage` para passar opaque; tipar só no caller que sabe o stage |
| `STAGE_REGISTRY` valores `is_llm` | Boolean per stage — usado para `skip_llm` | Replicar exatamente; teste de paridade contra Python |

---

## 5. Acoplamentos não-import (out-of-band)

Coisas que o shell Go vai precisar replicar **mesmo no Caminho 1**:

1. **Layout de paths** — `WorkspaceContext.__post_init__` define `processed_dir`, `e2_dir`, etc. Convenção compartilhada com Python; tem que ficar idêntica ou o Python via subprocess não acha os arquivos.
2. **Redis pub/sub envelope** — formato em [event_publisher.py:56-70](../pipeline-service/app/services/event_publisher.py:56) (`event`, `run_id`, `timestamp`, `stage`, `status`, `progress_pct`, `error`, `detail`). Backend WebSocket consumer ([backend/app/services/events.py](../backend/app/services/events.py)) espera esse shape exato.
3. **Channel naming** — `pipeline:{run_id}` em [event_publisher.py:72](../pipeline-service/app/services/event_publisher.py:72). Hardcoded; tem que ser idêntico.
4. **OpenAPI contract** — [docs/reference/api/v1/pipeline-service.openapi.json](api/v1/pipeline-service.openapi.json) é fonte de verdade; codegen Go via `oapi-codegen` recomendado ([ADR-113](DECISIONS.md#adr-113--convenções-go-golangciyml--ci--skeleton-a6g7) §Escopo deferido).
5. **OTel span naming** — `pipeline.{stage}` em [orchestrator.py:237](../pipeline/orchestrator.py:237). Em Go, `otel.Tracer("mathoms.pipeline").Start(ctx, "pipeline."+stage)`.

---

## 6. Próximos passos sugeridos (não-decididos)

Ordem recomendada de prep pré-port (referência da conversa que originou este doc):

| # | Ação | Custo | Bloqueia |
| - | --- | --- | --- |
| **A1** | **Este documento** ✓ | feito | A3 |
| A2 | Baseline de footprint (RSS, startup, p50/p99 latência) do `pipeline-service` Python em smoke | 2-3h | A3 |
| A3 | **ADR de estratégia de port** — decidir Caminho 1/2/3 com base em A1 + A2 | 2h | tudo abaixo |
| B1 | Codegen Go via `oapi-codegen` consumindo o OpenAPI | 3-4h | porta de `contracts/` |
| B2 | Contract tests (Schemathesis) contra o pipeline-service atual | 4-6h | confiança no port |
| B3 | CLI entry-point em `pipeline.orchestrator` (`python -m pipeline.orchestrator run-stage …`) | 2h | **pré-requisito do Caminho 1** |
| B4 | Sample anonimizado de tráfego real → golden tests | 3-4h | validação do port |

---

## Reproduzir este inventário

```bash
# 1. Imports diretos
grep -rn "from pipeline\.\|import pipeline\." pipeline-service/app/ --include="*.py"

# 2. Imports de backend
grep -rn "from backend\." pipeline-service/ --include="*.py"

# 3. Tamanho por camada
wc -l pipeline-service/app/**/*.py
wc -l pipeline/stages/*.py
find pipeline/domain -type f -name "*.py" -exec cat {} + | wc -l
find pipeline -type f -name "*.py" | wc -l

# 4. Símbolos públicos do orchestrator
grep -n "^def \|^class \|^LLM_STAGES" pipeline/orchestrator.py
grep -n "^def \|^class \|^STAGE_REGISTRY\|^FULL_ORDER" pipeline/stage_spec.py
```

Atualizar este doc se: (a) shell ganhar import novo de `pipeline.*` ou `backend.*`; (b) shape de `StageResult` mudar; (c) `STAGE_REGISTRY` mudar de cardinalidade.
