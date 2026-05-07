# P0 — Motor canônico e pipeline (executado)

> **Data:** 2026-04-17
> **Objetivo:** Inventário de duplicação, fronteira motor × adaptadores, estado dos contratos entre estágios e da suíte golden — base para P1 estrutural.

---

## 1. Inventário de duplicação / convergência (P0.1)

| Área | Onde está hoje | Risco de drift | Ação recomendada |
| --- | --- | --- | --- |
| **Classificação no upload web** | `backend/app/services/content_classifier.py` (texto + metadados; LLM opcional no fluxo chamador) | Médio vs batch | Manter contrato de saída alinhado ao que o pipeline espera (`doc_type`, `bank_code`, `period`); renomeio físico via `canonical_routing` + `e0_route.build_final_name` |
| **Classificação no pipeline (inbox / E0-route)** | `scripts/e0_route.py` — heurísticas por **nome de arquivo** e roteamento de pastas | Médio vs web | Evoluir para API única de classificação no núcleo (ver [plan/P1_STRUCTURAL/_README.md](plan/P1_STRUCTURAL/_README.md)); até lá, documentar duas entradas (fila web vs pasta `data/`) |
| **Reclassificação manual / correção** | `documents.reclassify` + `canonical_routing.rename_to_canonical` | Baixo | Continua como adaptador sobre o mesmo modelo de classificação |
| **Goals / tasks / membros no E5** | `pipeline_adapter.py` (DB → JSON) vs arquivos legado sob feature flags | Baixo pós-cutover | Fechar checklist [ADR-077](DECISIONS.md#adr-077--pipeline-adapter-como-contrato-de-cutover-cli--web); eliminar dual-source |
| **Validação JSON entre estágios** | `scripts/pipeline_common.validate_artifact` + validações locais (ex.: `e4_categorize.validate_baseline_schema`) | Baixo | Centralizar política de validação; ver §3 |
| **Saídas LLM** | `pipeline/llm/validators.py` + Pydantic nos stages | Baixo | Fonte única por estágio; manter |
| **Parsers bancários E2** | `scripts/e2/banks/*.py` + registry | Baixo | Único conjunto; novos bancos só aqui |
| **Serialização config DB → disco** | `config_materializer.py` | Baixo | Já coberto por round-trip tests (F6.5E) |

**Conclusão:** o principal vetor de inconsistência **não é CLI vs web no worker** (mesmos wrappers), e sim **duas entradas de classificação** (conteúdo no upload vs nome no E0-route) e **dual-source** de config até cutover completo. Priorizar unificação de classificação e adapter 100%.

---

## 2. Fronteira: motor canônico × adaptadores (P0.2)

### Motor canônico (lógica determinística + contratos)

- Estágios em `pipeline/stages/` e implementações em `scripts/` / `pipeline/llm/` que produzem/consomem artefatos versionados.
- Parsers E2, reconciliação E3, categorização E4, análise E5, checks E7-crossval, review/apply E7. Stage E6 (renderer HTML standalone) **removido em [ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side)** — relatório é renderizado on-demand pela rota React `/reports/[id]` + export PDF via Playwright.
- Dados de política em `config/` (ex.: `pipeline.json`, `categorization`, schemas em `config/schemas/`).

### Adaptadores (I/O e ambiente — não duplicam regra de negócio)

| Adaptador | Responsabilidade |
| --- | --- |
| `config_materializer` | Persistência workspace → árvore materializada por tenant |
| `pipeline_adapter` | DB → payloads JSON compatíveis com o pipeline legado |
| `storage` / `document_processor` | Upload, paths, unlock, dedupe |
| `pipeline_task` (Celery) | Orquestração assíncrona, retry, logs, WebSocket |
| HTTP (FastAPI) | Auth, tenancy, disparo de runs |

### Orquestração

- **Worker e dev local** devem executar os **mesmos** entrypoints de estágio (`pipeline.stages.*` → `scripts` com `WorkspaceContext`), evitando fork de lógica.

---

## 3. Contratos entre estágios (P0.3)

| Mecanismo | Estado atual |
| --- | --- |
| `config/pipeline.json` → `schema_validation` | `enabled: true`, **`mode: "warn"`** — invalidação loga aviso e **não bloqueia** o estágio |
| Override | `MATHOMS_PIPELINE_SCHEMA_MODE=strict` \| `warn` — força o modo sem editar `pipeline.json` (`scripts/pipeline_common.py`) |
| Schemas | `config/schemas/*.schema.json` |
| Testes de `validate_artifact` | `tests/test_schema_validation.py` (inclui caso strict) |
| Validação LLM | Pydantic/Instructor nos stages |

**Gaps**

1. **Job CI** com strict já roda em `test_schema_validation.py`; expandir conforme novos goldens.
2. E3–E5: schema + validação pós-write + goldens de execução (`tests/test_e3_golden_execution.py`, `tests/test_e4_golden_execution.py`, `tests/test_e5_golden_execution.py`) — ver [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md).

**Próximo passo:** [plan/P1_STRUCTURAL/_README.md](plan/P1_STRUCTURAL/_README.md) (job CI + política strict seletiva).

---

## 4. Golden / snapshot (P0.4)

| Ativo | Escopo |
| --- | --- |
| `backend/tests/test_golden_pipeline.py` | Workspace + materialize + PDFs sintéticos; **full E0→E5** documentado como deferido (E6 removido em [ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side)) |
| `tests/test_llm_golden.py` | Schemas LLM / fixtures |
| E2E Playwright + `seed_completed_run` | Caminho de produto com mock de pipeline |
| `tests/test_schema_validation.py` | Minimal JSON válido vs schema |

**Gaps**

1. Golden **por estágio** até E5 (E3→E4→E5→E5.N), incluindo **despesa categorizada**, **baseline patrimonial mínimo**, **`test_e5n_golden_execution`** (narrativas + `validate_narrativas`, incl. tenant com cônjuge / chart `ana_cenarios`) e assert de **`logs/qa_log.md`** (`pipeline_golden_asserts`); endurecer goldens por estágio conforme novos requisitos. (Render HTML/E6 removido em [ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side) — paridade React validada por Playwright.)
2. PDFs sintéticos + registry E2: `tests/test_e2_synthetic_pdf_parsers.py` (filename canônico por banco → `route_to_parser` → parse). Layouts dedicados no `pdf_generator` para **todo** `BANK_MODULES`: extratos com **≥1 transação** e **`saldo_final`** onde aplicável — **C6**, **Bradesco**, **BTG**, **Rico**, **Wise**, **PicPay**, **Bank of America**, **Santander**, **Itaú**, **Caixa** (`test_c6bank_*`, `test_bradesco_*`, `test_btgpactual_*` … `test_caixa_*`). **Quinto Andar** (fatura): **`itens`** + **`total_recebido`** (`test_quintoandar_synthetic_extracts_items`). Smoke texto: `backend/tests/test_golden_pipeline.py::TestSyntheticPDFsAreParseable`. **Fase 1 (registry) só sintética:** fechada para layouts dedicados.
3. LLM: JSONs em `tests/fixtures/llm_golden/` + `tests/test_llm_golden.py` (parse Pydantic, validators, conversores); ver [tests/fixtures/llm_golden/README.md](../tests/fixtures/llm_golden/README.md). Mocks de runtime: `backend/tests/fixtures/llm_mock.py` — [ADR-070](DECISIONS.md#adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in).
4. **Fase 2 (opcional):** PDFs reais anonimizados — scaffold `tests/fixtures/e2_real_pdf_anon/` + `tests/test_e2_real_pdf_regression.py`; popular binários redigidos quando fizer sentido — [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md) § *E2 — sintético e real anonimizado* e [BACKLOG.md](BACKLOG.md).

---

## 5. Checklist P0

| Item | Status |
| --- | --- |
| P0.1 Inventário | Feito (§1) |
| P0.2 Fronteira motor × adaptadores | Feito (§2) |
| P0.3 Contratos documentados + gaps | Feito (§3) |
| P0.4 Golden existente + gaps | Feito (§4) |

---

## Referências

- [ARCHITECTURE.md](ARCHITECTURE.md) — Pipeline stages, services, execução offline
- [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md) — checklist de validação por artefato
- [DECISIONS.md](DECISIONS.md) — ADR-013, 075, 077, 079, 080
- [plan/P1_STRUCTURAL/_README.md](plan/P1_STRUCTURAL/_README.md) — fase estrutural P1 (concluída)
