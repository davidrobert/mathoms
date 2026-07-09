# P0 — Motor canônico e pipeline (executado)

> **Data:** 2026-05-15
> **Objetivo:** Inventário de duplicação, fronteira motor × adaptadores, estado dos contratos entre estágios e da suíte golden — base para P1 estrutural (pausado / substituído por [PLATFORM_REVIEW](../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md) em 2026-05-06).

---

## 1. Inventário de duplicação / convergência (P0.1)

| Área | Onde está hoje | Risco de drift | Ação recomendada |
| --- | --- | --- | --- |
| **Classificação no upload web** | `backend/app/services/documents/content_classifier.py` (texto + metadados; LLM opcional no fluxo chamador) | Médio vs batch | Manter contrato de saída alinhado ao que o pipeline espera (`doc_type`, `bank_code`, `period`); renomeio físico via `canonical_routing` + `route_documents.build_final_name` |
| **Classificação no pipeline (inbox / E0-route)** | `scripts/route_documents.py` — heurísticas por **nome de arquivo** e roteamento de pastas | Médio vs web | Núcleo unificado em `backend/app/services/documents/document_classification.classify_document` (ADR-081 P2) consumido por upload web e por `route_documents.route_file` quando o pacote backend é importável; CLI isolado mantém fallback legado por nome |
| **Reclassificação manual / correção** | `documents.reclassify` + `canonical_routing.rename_to_canonical` | Baixo | Continua como adaptador sobre o mesmo modelo de classificação |
| **Goals / tasks / membros no E5** | `pipeline_adapter.py` (DB → JSON) — fonte única após cutover [`config/goals.json`](../archive/GOALS_JSON_CUTOVER_PLAN-2026-05-07.md) (Sprint A10, ✅ 2026-05-07) | Baixo | Checklist [ADR-077](../DECISIONS.md#adr-077--pipeline-adapter-como-contrato-de-cutover-cli--web) fechado; arquivos legado removidos |
| **Validação JSON entre estágios** | Hook **universal** pós-write em `DBArtifactStore.write` via `SCHEMA_BY_STAGE` + `scripts/pipeline_common.validate_dict` (ADR-212 PR3a) | Baixo | Mapping em [backend/app/services/storage/db_artifact_store.py](../../backend/app/services/storage/db_artifact_store.py); validações locais legado (ex.: `categorize_transactions.validate_baseline_schema`) coexistem por compat |
| **Saídas LLM** | `pipeline/llm/validators.py` + Pydantic nos stages | Baixo | Fonte única por estágio; manter |
| **Parsers bancários E2** | `scripts/e2/banks/*.py` + registry | Baixo | Único conjunto; novos bancos só aqui |
| **Serialização config DB → disco** | `config_materializer.py` | Baixo | Já coberto por round-trip tests (F6.5E) |
| **Artefatos de pipeline** | `pipeline_artifacts` (DB) via `DBArtifactStore` — caminho único pós-[ADR-212](../adr/212-sunset-mathoms-use-db-artifacts-disk-store-cli.md) | Baixo | `DiskArtifactStore` + flag `MATHOMS_USE_DB_ARTIFACTS` removidos em A12 (2026-05-14); testes injetam `InMemoryArtifactStore` |

**Conclusão:** com ADR-212 + cutover de `config/goals.json` fechados, os dois maiores vetores históricos de drift (dual-store de artefatos e dual-source de config) estão resolvidos. O vetor residual é manter o contrato de saída da classificação alinhado entre `content_classifier` (web) e `route_documents` (CLI fallback).

---

## 2. Fronteira: motor canônico × adaptadores (P0.2)

### Motor canônico (lógica determinística + contratos)

- Estágios em `pipeline/stages/` e implementações em `scripts/` / `pipeline/llm/` que produzem/consomem artefatos versionados em `pipeline_artifacts`.
- Cadeia atual de stages (ver `pipeline.stage_spec.STAGE_REGISTRY` para a fonte de verdade — nomes descritivos pós-F9.2, ADR-093):
  - **E0** `route_documents` + `unlock_documents` (classificação + unlock PDF)
  - **E1** `extract_members` (membros da família · ADR-127)
  - **E1.5** `extract_baseline` → `consolidate_baseline` (baseline patrimonial; `E1.5a` é key de artifact/schema do extract per-IRPF pré-baseline, **não** stage executável do `STAGE_REGISTRY`)
  - **E1.6** `extract_irpf_full` (IRPF completo · [ADR-157](../adr/157-schema-irpf-completo-stage-extract-irpf-full.md))
  - **E2 (informes/comprovantes)** `extract_informe_aluguel` (informe de imobiliária · ADR-216 Onda 0.5b) · `extract_informes_anuais` (informes anuais polimórficos · ADR-238) · `extract_comprovantes_bens` (comprovantes de bem · ADR-239)
  - **E2** `extract_statements` / `extract_invoices` / `extract_with_llm` (parsers bancários + fallback LLM)
  - **E3** `reconcile_transactions`
  - **E4** `categorize_transactions`
  - **E5** `analyze_finances` + `generate_narratives` (E5.N)
  - **E6** `review_finances_holistic` (E6-parecer; artifact `parecer_planejador` · [ADR-199](../adr/199-parecer-planejador-supersede-review-finances.md), Sprint A11/A12) — **substituiu** o renderer HTML standalone que foi descontinuado em [ADR-129](../DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side)
  - **E7** `validate_cross` (cross-validation read-only sobre E5; sem write em `pipeline_artifacts`)
- Dados de política em `config/` (ex.: `pipeline.json`, schemas em `config/schemas/`). Configs operacionais por workspace via `ConfigStore` (DB-first, ADR-134).

### Adaptadores (I/O e ambiente — não duplicam regra de negócio)

| Adaptador | Responsabilidade |
| --- | --- |
| `config_materializer` | Persistência workspace → árvore materializada por tenant |
| `pipeline_adapter` | DB → payloads JSON compatíveis com o pipeline |
| `DBArtifactStore` | Leitura/escrita de `pipeline_artifacts` + validação JSON universal pós-write |
| `storage` / `document_processor` | Upload, paths, unlock, dedupe |
| `pipeline_task` (Celery) | Orquestração assíncrona, retry, logs, WebSocket |
| HTTP (FastAPI) | Auth, tenancy, disparo de runs |

### Orquestração

- **Worker e dev local** executam os **mesmos** entrypoints de estágio (`pipeline.stages.*` → `scripts` com `WorkspaceContext`), evitando fork de lógica. CLI standalone descontinuada em ADR-212 PR1+PR1b.

---

## 3. Contratos entre estágios (P0.3)

| Mecanismo | Estado atual |
| --- | --- |
| `config/pipeline.json` → `schema_validation` | `enabled: true`, **`mode: "warn"`** — invalidação loga aviso e **não bloqueia** o estágio |
| Override | `MATHOMS_PIPELINE_SCHEMA_MODE=strict` \| `warn` — força o modo sem editar `pipeline.json` (`scripts/pipeline_common.py`) |
| Schemas | `config/schemas/*.schema.json` |
| Hook de validação | `DBArtifactStore.write` chama `validate_dict(data, SCHEMA_BY_STAGE[stage])` pós-write — universal por stage canônico (ADR-212 PR3a) |
| Testes de `validate_artifact` | `tests/test_schema_validation.py` (inclui caso strict) |
| Validação LLM | Pydantic/Instructor nos stages |

**Gaps**

1. CI strict já cobre `test_schema_validation.py`; expandir conforme novos schemas entrarem em `SCHEMA_BY_STAGE`.
2. E3–E5: schema + validação pós-write + goldens de execução (`tests/test_e3_golden_execution.py`, `tests/test_e4_golden_execution.py`, `tests/test_e5_golden_execution.py`) — ver [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md).
3. E6 `parecer_planejador`: schema `parecer_planejador.schema.json` ativo; golden mockado entregue nos Atos 1-3.

**Próximo passo:** [PLATFORM_REVIEW/_README.md](../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md) — P1 estrutural foi pausado em 2026-05-06 e substituído por este plano canônico multi-onda (32 tasks, 6 ondas, 138 findings de revisão multi-agente).

---

## 4. Golden / snapshot (P0.4)

| Ativo | Escopo |
| --- | --- |
| `backend/tests/test_golden_pipeline.py` | Workspace + materialize + PDFs sintéticos; **full E0→E5** documentado como deferido (E6 HTML removido em [ADR-129](../DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side); E6 hoje = `parecer_planejador`) |
| `tests/test_llm_golden.py` | Schemas LLM / fixtures |
| E2E Playwright + `seed_completed_run` | Caminho de produto com mock de pipeline |
| `tests/test_schema_validation.py` | Minimal JSON válido vs schema |
| `tests/test_e{3,4,5}_golden_execution.py` + `tests/test_e5n_golden_execution.py` | Goldens de execução por stage |

**Gaps**

1. Golden **por estágio** até E5 (E3→E4→E5→E5.N), incluindo **despesa categorizada**, **baseline patrimonial mínimo**, narrativas (`validate_narrativas`, incl. tenant com cônjuge / chart `ana_cenarios`) e assert de **`logs/qa_log.md`** (`pipeline_golden_asserts`); endurecer goldens por estágio conforme novos requisitos. Render HTML server-side removido em [ADR-129](../DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side) — paridade React validada por Playwright.
2. PDFs sintéticos + registry E2: `tests/test_e2_synthetic_pdf_parsers.py` (filename canônico por banco → `route_to_parser` → parse). Layouts dedicados no `pdf_generator` para **todo** `BANK_MODULES`: extratos com **≥1 transação** e **`saldo_final`** onde aplicável — **C6**, **Bradesco**, **BTG**, **Rico**, **Wise**, **PicPay**, **Bank of America**, **Santander**, **Itaú**, **Caixa** (`test_c6bank_*`, `test_bradesco_*`, `test_btgpactual_*` … `test_caixa_*`). **Quinto Andar** (fatura): **`itens`** + **`total_recebido`** (`test_quintoandar_synthetic_extracts_items`). Smoke texto: `backend/tests/test_golden_pipeline.py::TestSyntheticPDFsAreParseable`. **Fase 1 (registry) só sintética:** fechada para layouts dedicados.
3. LLM: JSONs em `tests/fixtures/llm_golden/` + `tests/test_llm_golden.py` (parse Pydantic, validators, conversores); ver [tests/fixtures/llm_golden/README.md](../../tests/fixtures/llm_golden/README.md). Mocks de runtime: `backend/tests/fixtures/llm_mock.py` — [ADR-070](../DECISIONS.md#adr-070--premium-llm-e2e-mock-default--nightly-real-opt-in).
4. **Fase 2 (opcional):** PDFs reais anonimizados — scaffold `tests/fixtures/e2_real_pdf_anon/` + `tests/test_e2_real_pdf_regression.py`; popular binários redigidos quando fizer sentido — [PIPELINE_ARTIFACTS.md](PIPELINE_ARTIFACTS.md) § *E2 — sintético e real anonimizado* e [_MOC/_generated/SPRINT_CURRENT.md](../_MOC/_generated/SPRINT_CURRENT.md).

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
- [../_MOC/_generated/ADR_INDEX.md](../_MOC/_generated/ADR_INDEX.md) — índice canônico de ADRs (auto-gerado)
- ADRs relevantes: [ADR-013](../DECISIONS.md#adr-013), [ADR-077](../DECISIONS.md#adr-077--pipeline-adapter-como-contrato-de-cutover-cli--web), [ADR-081](../DECISIONS.md#adr-081), [ADR-129](../DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side), [ADR-157](../adr/157-schema-irpf-completo-stage-extract-irpf-full.md), [ADR-199](../adr/199-parecer-planejador-supersede-review-finances.md), [ADR-212](../adr/212-sunset-mathoms-use-db-artifacts-disk-store-cli.md), [ADR-213](../adr/213-sunset-stage-audit-documents.md)
- [../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md](../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md) — sucessor de P1 estrutural (revisão multi-agente Sprint A11)
- [../plan/P1_STRUCTURAL/_README.md](../plan/P1_STRUCTURAL/_README.md) — plano estrutural P1 (status: `paused` desde 2026-05-06)
