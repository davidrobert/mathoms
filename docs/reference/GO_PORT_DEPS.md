# GO_PORT_DEPS — Inventário de dependências do `pipeline-service` para migração Go

> **Status:** referência (não-plano) · **Data inicial:** 2026-04-27 · **Última atualização:** 2026-07-02 (revisão de consistência da emenda ADR-150 — números re-medidos, `DiskArtifactStore` deletado por ADR-212, `STAGE_REGISTRY` 16→18) · **Origem:** A1 do tópico "preparar contexto para Go rewrite" (proposto na conversa com CTO)
>
> **Escopo:** dimensionar exatamente o que o shell HTTP em [pipeline-service/](../../pipeline-service/) importa do core Python em [pipeline/](../../pipeline/), para que o ADR de estratégia de port (Caminho 1/2/3) seja escrito com dados, não especulação.
>
> **ADRs relacionadas:** [ADR-112](../DECISIONS.md#adr-112--pipeline-as-service-http-boundary-para-execução-de-stages-a6f1) (HTTP boundary), [ADR-113](../DECISIONS.md#adr-113--convenções-go-golangciyml--ci--skeleton-a6g7) (convenções Go), [ADR-102 R18-R20](../DECISIONS.md#adr-102--princípios-r18-r20-language-neutral-boundaries-a6f) (language-neutral boundaries), [ADR-111](../DECISIONS.md#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6) (stateless rigoroso).

---

## TL;DR

| Métrica | 2026-04-27 | **2026-07-02** |
| --- | --- | --- |
| **Shell HTTP** (pipeline-service) | 532 LOC / 14 arquivos | **565 LOC / 15 arquivos** |
| **Símbolos importados de `pipeline.*`** pelo shell | 5 distintos | **5 distintos (inalterado)** — `context`, `orchestrator`, `stage_spec` |
| **Imports de `backend.*`** pelo shell | 1 (opcional, `setup_logging`) | **1 (inalterado)** — mas ver §5.6: A3.store opção (a) adiciona `DBArtifactStore` |
| **Core Python que o shell aciona** | 108 arquivos · 17.823 LOC | **218 arquivos · 38.348 LOC** (~2,2×) |
| **Domain services** (`pipeline/domain/`) | 61 arquivos · 13.077 LOC | **135 arquivos · 26.446 LOC** (~2×) |
| **Stage runners** (`pipeline/stages/`) | 16 arquivos · 1.561 LOC | **18 stages · 3.082 LOC** (thin wrappers que delegam para `domain/services/` ou `scripts/`) |

**Conclusão operacional:** o shell HTTP segue portável em ~600 LOC Go — a fronteira fina **sobreviveu 2 meses de crescimento 2× do domínio** sem ganhar import novo. O domínio agora tem ~38 mil LOC: a estimativa de Caminho 3 da ADR-150 (3-5 meses para 17,8k LOC) está subdimensionada — proporcionalmente, **6-10 meses** — o que reforça Caminho 1 como default.

**Acoplamento novo pós-ADR-212 (não existia no inventário original):** artefatos são DB-only (`pipeline_artifacts` via `DBArtifactStore`); qualquer executor fora do processo Celery precisa de injeção de store — ver §5.6 e emenda 2026-07-02 da [ADR-150](../adr/150-estrategia-de-port-go-do-pipeline-service.md) (pré-requisito A3.store).

---

## 1. Imports diretos do shell para `pipeline/`

Comando reproduzível:
```bash
grep -rn "from pipeline\.\|import pipeline\." pipeline-service/app/ --include="*.py"
```

| # | Símbolo | Origem | Consumidor (arquivo:linha) | Papel |
| - | --- | --- | --- | --- |
| D1 | `WorkspaceContext` (dataclass, 200 LOC) | `pipeline.context` | [run_coordinator.py:19](../../pipeline-service/app/services/run_coordinator.py:19), [stage_executor.py:37](../../pipeline-service/app/services/stage_executor.py:37) | Container de paths + config + run_id. Construído por request, descartado depois. |
| D2 | `_run_stage(ctx, stage) -> StageResult` | `pipeline.orchestrator` | [run_coordinator.py:20](../../pipeline-service/app/services/run_coordinator.py:20), [stage_executor.py:18](../../pipeline-service/app/services/stage_executor.py:18) | **Hot path.** Wrapper que captura stdout/stderr, OTel span, exit codes, e dispatcha pro runner correto via `_get_stage_runner`. |
| D3 | `LLM_STAGES` (set) | `pipeline.orchestrator` | [run_coordinator.py:20](../../pipeline-service/app/services/run_coordinator.py:20) | Set de nomes de stage que envolvem LLM — usado para honrar `skip_llm` na request. |
| D4 | `StageResult` (dataclass) | `pipeline.orchestrator` | testes (`test_stage_execution.py`, `test_run_coordinator.py`) | DTO retornado por `_run_stage`. Apenas testes importam diretamente; produção recebe via `_run_stage`. |
| D5 | `STAGE_REGISTRY` (dict) | `pipeline.stage_spec` ([ADR-093](../DECISIONS.md#adr-093--rename-completo-de-identificadores-de-stage-opção-a)) | [api/stages.py:16](../../pipeline-service/app/api/stages.py:16), [api/runs.py:20](../../pipeline-service/app/api/runs.py:20) | Dict de `StageSpec` — usado para validar que `stage` recebido na request existe. |

**Bonus (`backend/`):**

| # | Símbolo | Origem | Consumidor | Papel |
| - | --- | --- | --- | --- |
| B1 | `setup_logging` | `backend.app.core.logging` | [main.py:60](../../pipeline-service/app/main.py:60) | Wire JSON logs ([ADR-110](../DECISIONS.md#adr-110--structured-json-logging--opentelemetry-bootstrap-a6f3)). **Opcional** — fallback para `logging.basicConfig` se backend não importável. |

**`B1` é o único acoplamento ao `backend/` em código hoje.** Já tem fallback. Em Go vira `slog` direto — eliminado naturalmente. **Caveat 2026-07-02:** a resolução do A3.store (ver §5.6) adiciona um segundo acoplamento — `DBArtifactStore` — que é **hard** (sem ele nenhum stage lê/grava artefato pós-ADR-212).

---

## 2. Cadeia transitiva por símbolo

### D1 · `WorkspaceContext` (porta cleanly, com uma pegadinha nova)

`pipeline/context.py` (252 LOC) é dataclass puro:
- campos `Path` derivados de `root` (sem I/O, só path arithmetic)
- `load_config(name) -> dict` — lê JSON do disco
- `get_artifact_store()` — **pós-ADR-212 PR3b, raise `RuntimeError` se `artifact_store` não foi injetado** (o lazy-default de `DiskArtifactStore` foi deletado). Backend Celery injeta `DBArtifactStore` por-stage ([pipeline_task.py](../../backend/app/tasks/pipeline_task.py), `_open_artifact_session`); o modo HTTP do pipeline-service **não injeta** — está latentemente quebrado (ver ADR-150 emenda 2026-07-02, item 3)
- `for_tenant(...)` — factory (não injeta store)

**Dependências externas:** `json`, `pathlib`, `dataclasses`. Zero deps de domínio.
**Port em Go:** struct + métodos. ~150 LOC. Trivial — mas o executor (Go ou Python subprocess) precisa resolver a injeção de store (A3.store) antes de qualquer stage rodar.

### D2 · `_run_stage` (o ponto difícil)

`pipeline/orchestrator.py` (365 LOC) chama em runtime, via `_get_stage_runner`:

```python
# orchestrator.py — switch sobre o nome do stage em _get_stage_runner
if stage == "reconcile_transactions":
    from pipeline.stages.reconcile_transactions import run
    return run
# ... 18 cases
```

Cada `pipeline/stages/<name>.py` é thin wrapper (17–518 LOC, mediana ~40) que delega para `pipeline/domain/services/` ou para scripts em `scripts/eN_*.py`.

**Stages e suas dependências reais (18 stages, medido 2026-07-02):**

| Stage | LLM | LOC wrapper | Núcleo onde mora a lógica |
| --- | --- | --- | --- |
| `unlock_documents` | | 17 | `pipeline/domain/services/document_unlocker.py` |
| `route_documents` | | 38 | `scripts/e0_route.py` + `backend/app/services/document_classification.py` |
| `extract_members` | ✓ | 206 | `pipeline/domain/services/member_analyzer.py` |
| `extract_baseline` | ✓ | 359 | `pipeline/domain/services/patrimonio_*.py` |
| `consolidate_baseline` | | 40 | `scripts/e1_consolidate.py` |
| `extract_irpf_full` | ✓ | 308 | E1.6 — IRPF completo (ADR-157) |
| `extract_informe_aluguel` | ✓ | 185 | informes de imobiliária (ADR-216) |
| `extract_informes_anuais` | ✓ | 451 | informes anuais PF/PJ/previdência (ADR-238) |
| `extract_comprovantes_bens` | ✓ | 496 | apólices/CRLV (ADR-239) |
| `extract_invoices` | | 19 | `scripts/e2_invoices/banks/*.py` |
| `extract_statements` | | 19 | `pipeline/domain/services/statement_preprocessor.py` + `scripts/e2_extract.py` |
| `extract_with_llm` | ✓ | 518 | `pipeline/llm/litellm_client.py` (482) + LLM heavy |
| `reconcile_transactions` | | 18 | `pipeline/domain/services/reconciliation_service.py` + validators + `source_tier.py` |
| `categorize_transactions` | | 38 | `pipeline/domain/services/transaction_classifier.py` + `keyword_matcher.py` |
| `analyze_finances` | | 38 | `pipeline/domain/services/{patrimonio,ratios,reserva_emergencia,orcamento}_*.py` |
| `generate_narratives` | | 17 | `pipeline/domain/services/section_summary_generator.py` + LLM (opt) |
| `validate_cross` | | 24 | `scripts/e7_review.py` (só crossval) |
| `review_finances_holistic` | ✓ | 211 (`parecer_planejador.py`) | LLM-driven — parecer do planejador (ADR-199) |

**Total domain layer transitivamente acionado:** 26.446 LOC em 135 arquivos (era 13.077/61 em 2026-04).

**Nota [[ADR-205]]:** os 8 stages LLM acima **permanecem Python em qualquer caminho de port** — pré-compromisso Decidido; Go só é candidato para o shell e, hipoteticamente, stages CPU-bound.

### D3 · `LLM_STAGES` (set derivado)

`pipeline/orchestrator.py` — set construído a partir de `STAGE_REGISTRY[*].is_llm` (8 stages LLM hoje). Sem deps externas além de `STAGE_REGISTRY`. Em Go: const map, ~10 LOC.

### D4 · `StageResult` (dataclass)

`pipeline/orchestrator.py:28-33` — 5 campos (`stage`, `success`, `duration_ms`, `detail`, `error`), shape inalterado desde 2026-04. Serializado para o wire por Pydantic em [contracts/stages.py](../../pipeline-service/app/contracts/stages.py). Em Go: struct + JSON tags, ~15 LOC.

### D5 · `STAGE_REGISTRY` (catálogo de stages)

`pipeline/stage_spec.py` (376 LOC) define:
- `StageSpec` dataclass (name, reads, writes, is_llm, tier, …)
- `STAGE_REGISTRY: dict[str, StageSpec]` — 18 entradas
- `FULL_ORDER`, `DETERMINISTIC_ORDER` — slices ordenados
- `STAGE_RENAME_MAP`, `resolve_stage_name`, `to_legacy_stage_name` — compat F9.2 ([ADR-093](../DECISIONS.md#adr-093--rename-completo-de-identificadores-de-stage-opção-a))

**Sem deps externas além de `dataclasses`.** Port em Go: ~300 LOC, derivar do mesmo input via codegen (ver §5).

---

## 3. Caminho de port — análise quantitativa

### Caminho 1 — Shell-only Go + Python via subprocess

**Porta:**
- [pipeline-service/app/](../../pipeline-service/app/) → `services/pipeline-service-go/`
- ~600 LOC Go (api + run_coordinator + event_publisher + contracts)

**Mantém em Python:**
- `pipeline/` inteiro (38.348 LOC) — invocado via `python -m pipeline.orchestrator run-stage <name> --workspace <path>`
- **Pré-requisitos ausentes:** (1) A3.store — o subprocess precisa injetar `DBArtifactStore` via `DATABASE_URL` (artefatos são DB-only pós-ADR-212); (2) A3.cli — entry-point CLI no orchestrator (não existe hoje, `_run_stage` só é chamável programaticamente). Ordem e detalhes na emenda 2026-07-02 da [ADR-150](../adr/150-estrategia-de-port-go-do-pipeline-service.md)

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

**Porta:** ~38.348 LOC Python → estimado **~50.000-70.000 LOC Go** (Go é mais verboso para business logic). *(Re-medido 2026-07-02 — o domínio dobrou desde a estimativa original de 25-35k.)*
**Pontos críticos:**
- `pipeline/llm/litellm_client.py` (482) — LLM client. **Bloqueado por [[ADR-205]]:** stages LLM (8 de 18) permanecem Python em qualquer cenário — Caminho 3 "puro" não existe mais; seria híbrido por definição.
- `pipeline/domain/services/patrimonio_*.py` — math financeira complexa. Port linha-a-linha com testes de paridade.
- 18 stage runners + parsers (E2 banks, ~8 instituições) — cada um é trabalho próprio.
- Goldens existentes em `tests/test_e*_golden_*.py` viram **regression suite obrigatória** para validar paridade de port.

**Ganha:** sem GIL, footprint pleno, deploy estático puro (apenas nos stages não-LLM).
**Custo realista:** sprint dedicado de **6-10 meses** com 1-2 engenheiros (era 3-5 meses para metade do LOC atual). Domain logic exige paridade com goldens (BRL `0.01` tolerance, [ADR-097](../DECISIONS.md#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy)).

---

## 4. Riscos por símbolo

| Símbolo | Risco no port | Mitigação |
| --- | --- | --- |
| `WorkspaceContext.get_artifact_store` | **Raise `RuntimeError` sem injeção (ADR-212 PR3b)** — executor remoto sem store quebra no primeiro stage que lê/grava artefato (19 call-sites). O modo HTTP do pipeline-service sofre disso hoje | A3.store (ADR-150 emenda 2026-07-02): injetar `DBArtifactStore` do backend, sessão-por-stage + teste de integração exercitando stage real via HTTP |
| `WorkspaceContext.load_config` | Lê JSON do disco — se a config schema mudar, Go fica drift | Validar contra `config/schemas/*.schema.json` (já existem) |
| `_run_stage` captura stdout/stderr | Scripts legados em `scripts/eN_*.py` ainda usam `print()` para erros | Caminho 1: parse stderr capturado pelo subprocess. Caminho 3: errors tipados ([CLAUDE.md §Code style › Go](../../CLAUDE.md)) |
| `LLM_STAGES` em runtime | Mudança em `STAGE_REGISTRY` propaga para shell — codegen ajuda | Snapshot test de `STAGE_REGISTRY` (já existe via OpenAPI snapshot transitivamente) |
| `StageResult.detail: dict` | Detail é livre — bancos exportam shape próprio | Em Go usar `json.RawMessage` para passar opaque; tipar só no caller que sabe o stage |
| `STAGE_REGISTRY` valores `is_llm` | Boolean per stage — usado para `skip_llm` | Replicar exatamente; teste de paridade contra Python |

---

## 5. Acoplamentos não-import (out-of-band)

Coisas que o shell Go vai precisar replicar **mesmo no Caminho 1**:

1. **Layout de paths** — `WorkspaceContext.__post_init__` define `processed_dir`, `e2_dir`, etc. Convenção compartilhada com Python; tem que ficar idêntica ou o Python via subprocess não acha os arquivos.
2. **Redis pub/sub envelope** — formato em [event_publisher.py:56-70](../../pipeline-service/app/services/event_publisher.py:56) (`event`, `run_id`, `timestamp`, `stage`, `status`, `progress_pct`, `error`, `detail`). Backend WebSocket consumer ([backend/app/services/events.py](../../backend/app/services/events.py)) espera esse shape exato.
3. **Channel naming** — `pipeline:{run_id}` em [event_publisher.py:72](../../pipeline-service/app/services/event_publisher.py:72). Hardcoded; tem que ser idêntico.
4. **OpenAPI contract** — [docs/reference/api/v1/pipeline-service.openapi.json](api/v1/pipeline-service.openapi.json) é fonte de verdade; codegen Go via `oapi-codegen` recomendado ([ADR-113](../DECISIONS.md#adr-113--convenções-go-golangciyml--ci--skeleton-a6g7) §Escopo deferido).
5. **OTel span naming** — `pipeline.{stage}` no `_TRACER.start_as_current_span` de [pipeline/orchestrator.py](../../pipeline/orchestrator.py). Em Go, `otel.Tracer("mathoms.pipeline").Start(ctx, "pipeline."+stage)`.
6. **Artefatos DB-only (ADR-212, adicionado 2026-07-02)** — `pipeline_artifacts` (Postgres) via `DBArtifactStore` é o único caminho de leitura/escrita de artefatos; `DiskArtifactStore` foi deletado. O executor remoto precisa de `DATABASE_URL` + injeção de store por-stage (A3.store), reusando a classe `backend.app.services.db_artifact_store.DBArtifactStore` — reimplementar perderia o hook de validação `SCHEMA_BY_STAGE` + crypto no `write()`. **Isso muda a narrativa do §1:** se A3.store adotar a opção recomendada, `setup_logging` (B1) deixa de ser o único acoplamento ao `backend/` — `DBArtifactStore` vira o segundo, e este é hard (não-opcional). Unicidade de escrita: constraint `uq_pipeline_artifacts_run_stage_key` (`pipeline_run_id, stage, artifact_key`). Fallbacks de leitura workspace-scoped (ADR-241) e run-pinado (ADR-291) exigem acesso direto ao DB — inviabilizam transportar artefatos pelo contrato HTTP.

---

## 6. Próximos passos sugeridos (não-decididos)

Ordem recomendada de prep pré-port (referência da conversa que originou este doc):

| # | Ação | Custo | Bloqueia |
| - | --- | --- | --- |
| **A1** | **Este documento** ✓ | feito (refresh 2026-07-02) | A3 |
| **A2** | Baseline de footprint ✓ ([PERFORMANCE_BASELINE.md](PERFORMANCE_BASELINE.md), 2026-04-27) | feito | A3 |
| **A3** | **ADR de estratégia de port** ✓ ([ADR-150](../adr/150-estrategia-de-port-go-do-pipeline-service.md), Roadmap — Caminho 1 default, deferido) | feito | tudo abaixo |
| **A3.store** | **Boundary de artefatos do executor remoto pós-ADR-212** (ADR `Proposto` própria + fix do modo HTTP + teste de integração) | 1 sessão | **primeiro pré-requisito do Caminho 1** (emenda 2026-07-02) |
| B1 | Codegen Go via `oapi-codegen` consumindo o OpenAPI | 3-4h | porta de `contracts/` |
| B2 | Contract tests (Schemathesis) contra o pipeline-service atual | 4-6h | confiança no port |
| B3 | CLI entry-point em `pipeline.orchestrator` (`python -m pipeline.orchestrator run-stage …`) — inclui injeção de `DBArtifactStore` via `DATABASE_URL` | 3h | pré-requisito do Caminho 1 (= A3.cli da ADR-150) |
| B4 | Sample anonimizado de tráfego real → golden tests | 3-4h | validação do port |

**Nota:** nenhum gatilho da ADR-150 está ativo (2026-07-02) — A3.store/B1-B4 só arrancam quando um gatilho disparar ou na revisita agendada (2027-Q2 / 100 workspaces pagantes).

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
