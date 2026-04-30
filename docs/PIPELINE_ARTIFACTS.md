# Artefatos do pipeline — validação JSON (checklist P1-D3)

> Referência para cobertura de `validate_artifact` e do modo **strict** (`MATHOMS_PIPELINE_SCHEMA_MODE`).

## Schemas em `config/schemas/`

| Schema | Artefato típico | Onde valida após escrita |
| --- | --- | --- |
| `e2_extract.schema.json` | `processed/E2_extracts/*-2_extract.json` | `scripts/e2_extract.py` (`save_result`, exceto `requires_llm_fallback`); `pipeline/stages/e2_llm.py` |
| `e3_reconciled.schema.json` | `processed/E3_reconciled/*-3_reconciled.json` | `scripts/e3_reconcile.py` (após `write_json_atomic` por conta) |
| `e4_unified.schema.json` | `processed/E4_unified/*-4_unified.json` | `scripts/e4_categorize.py` (`save_json`) |
| `e5_analysis.schema.json` | `processed/E5_analysis/analise_financeira-5_analysis.json` | `scripts/e5_analyze.py` (write principal) |
| `baseline_patrimonial.schema.json` | baseline E1.5 | `e4_categorize` (baseline) — validação dedicada pode evoluir |
| `e16_irpf_full.schema.json` | `processed/E2_extracts/*-1.6_irpf_full.json` (E1.6 / `extract_irpf_full`) | `pipeline/stages/extract_irpf_full.py` via `validate_e16_output` (anti-PII + reconcile cross-field, ADR-157) |

**Política:** modo default **warn** (`pipeline.json`); CI roda subset com `MATHOMS_PIPELINE_SCHEMA_MODE=strict` nos testes de `validate_artifact`. Stubs E2 só para LLM (`requires_llm_fallback`) não passam por schema para evitar ruído.

## Fixtures golden

- JSON de pipeline (E2/E3/E4): [tests/fixtures/pipeline_golden/README.md](../tests/fixtures/pipeline_golden/README.md).
- JSON de **saída LLM** (schemas Pydantic E1 / E1.5 / E2-LLM / E7-review): [tests/fixtures/llm_golden/README.md](../tests/fixtures/llm_golden/README.md) + `tests/test_llm_golden.py`.
- **PDF real anonimizado (Fase 2, opcional):** [tests/fixtures/e2_real_pdf_anon/README.md](../tests/fixtures/e2_real_pdf_anon/README.md) + `tests/test_e2_real_pdf_regression.py` (pasta pode ficar vazia; cada `*.pdf` adicionado roda `route_to_parser`).

## Artefatos auxiliares (sem JSON schema)

| Artefato | Gerado por | Contrato nos testes |
| --- | --- | --- |
| `logs/qa_log.md` | `e4_categorize.generate_qa_log` | `tests/pipeline_golden_asserts.assert_qa_log_md` (cabeçalhos mínimos) |

**Próximo incremento sugerido**

- **Fase 2 (opcional):** popular `tests/fixtures/e2_real_pdf_anon/` com PDFs **redigidos** + revisão de PR (scaffold e teste já existem). **LLM:** novos estágios → novo schema + `tests/fixtures/llm_golden/` + `tests/test_llm_golden.py`.

## E2 — sintético e real anonimizado (duas fases)

1. **Fase 1 (registry coberto): só sintético alinhado ao parser** — `tests/fixtures/pdf_generator.py` + `tests/test_e2_synthetic_pdf_parsers.py`. Cada banco em `BANK_MODULES` tem `_draw_*` + asserts onde aplicável; códigos só em `BankCode` fora do registry continuam na tabela genérica. **Não** depende de PDF real versionado.
2. **Fase 2 (opcional): PDF real anonimizado no repositório** — complemento para regressão de **layout fiel**. **Scaffold:** `tests/fixtures/e2_real_pdf_anon/` + `tests/test_e2_real_pdf_regression.py` (CI verde com pasta vazia). Requisitos para cada binário: redação completa; nome de arquivo canônico para o registry; revisão em PR. **Não** substitui o sintético no dia a dia do CI.

## Golden E2 — PDF sintético × registry

- `tests/test_e2_synthetic_pdf_parsers.py`: para cada banco em `scripts/e2/registry.py` (`BANK_MODULES`), PDF gerado + filename canônico → `route_to_parser` → resultado dict (sem exceção). **C6, Bradesco, BTG, Rico, Wise, PicPay, Bank of America, Santander, Itaú, Caixa:** **≥1** transação + `saldo_final` (`test_c6bank_*`, `test_bradesco_*`, `test_btgpactual_*` … `test_caixa_*`). **Quinto Andar** (fatura aluguel): **`itens`** + **`total_recebido`** (`test_quintoandar_synthetic_extracts_items`) — não usa `transacoes`/`saldo_final`.
- `tests/fixtures/pdf_generator.py`: 14 códigos em `BankCode`; layouts dedicados ao registry incluem **C6** (`_draw_c6_extrato`), **Bradesco** (`_draw_bradesco_extrato`), **BTG**, **Rico**, **Wise**, **PicPay**, **Bank of America**, **Santander**, **Itaú**, **Caixa**, **Quinto Andar** — ver funções `_draw_*` no arquivo.

## Golden de execução E3

Implementado em `tests/test_e3_golden_execution.py`: tenant mínimo + `minimal-extrato-2_extract.json` (com saldos) → `e3_reconcile.main` → um `*-3_reconciled.json`, asserts + `jsonschema` + `validate_artifact`.

## Golden de execução E4

Implementado em `tests/test_e4_golden_execution.py`: tenant mínimo (`categorization.json` com keyword `PIX` → categoria `renda`) + cópia de `tests/fixtures/pipeline_golden/e3/minimal-conta-3_reconciled.json` em `processed/E3_reconciled/` → `e4_categorize.main` → sete `*-4_unified.json` + `validate_artifact` em cada arquivo. Cenário **receita + despesa** (`test_e4_execution_mixed_receita_despesa`): fixture `e3/minimal-conta-com-despesa-3_reconciled.json` + keyword `CINEMA` → `lazer`. Cenário **com baseline E1.5** (`test_e4_execution_with_baseline_patrimonial`): `e2/minimal-baseline-1.5_consolidated.json` em `processed/E2_extracts/baseline_patrimonial-1.5_consolidated.json` — `patrimonio-4_unified.json` espelha o baseline; validação desse arquivo com `baseline_patrimonial.schema.json` (não com `e4_unified`, pois o conteúdo é o consolidado).

## Golden de execução E5

Implementado em `tests/test_e5_golden_execution.py`: mesmo fluxo de dados que o golden E4 (E3 fixture → `e4_categorize.main`) com `config/goals.json` mínimo (`if_meta`, `trs_pct`) e cópias de `scoring.json`, `parametros_fiscais.json`, `taxas.json` do repositório → `e5_analyze.main` → `processed/E5_analysis/analise_financeira-5_analysis.json` + `jsonschema` + `validate_artifact`. Cenário misto: `test_e5_execution_mixed_receita_despesa` (mesma fixture E3 com despesa). Cenário com baseline: `test_e5_execution_with_baseline_patrimonial` — totais de patrimônio batem com o fixture (`dividas[]` com `saldo_31_12` por ano, necessário para o E5 somar dívidas por membro).

## Golden de execução E5.N

Implementado em `tests/test_e5n_golden_execution.py`: mesmo cenário mínimo que o golden E5 (helper `_build_e5_workspace` — evita depender de `pytest_plugins` entre módulos) → `e4_categorize.main` → `e5_analyze.main` → `e5n_narrativas.main` → `analise_financeira-5_analysis.json` passa a incluir `narrativas` (`perfil_familia`, `summaries`, `charts`). O teste chama `validate_narrativas` **antes** do `finally` que repõe os globals do `e5n_narrativas` (o chart dinâmico `{cônjuge}_cenarios` depende de `family_members.json` do tenant). Segundo cenário: **`test_e5n_execution_narrativas_with_conjuge_chart`** — membro com `papel: conjuge` → presença de `ana_cenarios` em `narrativas.charts`.

## Produção do relatório (pós-[ADR-129](DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side))

Não há mais stage E6 nem HTML standalone gerado pelo pipeline. O fluxo
de produção do relatório é:

1. **E5** (e opcionalmente E5.N + E7-review/apply) escreve
   `processed/E5_analysis/analise_financeira-5_analysis.json` —
   validado pelo `e5_analysis.schema.json`.
2. `backend/app/services/pipeline_task._create_report_from_output`
   cria o row `Report` no DB a partir desse JSON
   (`analysis_artifact_id` aponta via FK para `pipeline_artifacts.id` —
   ADR-131 substituiu o ponteiro de filesystem `analysis_json_path`).
3. O relatório é renderizado **on-demand** pela rota React
   `/reports/[id]` consumindo `GET /reports/{id}/data`.
4. O único export server-side é **PDF via Playwright**
   ([backend/app/services/pdf_renderer.py](../backend/app/services/pdf_renderer.py))
   sobre essa mesma rota.

A pasta `output/` em `storage/<workspace>/` ficou vestigial após a
remoção do renderer standalone — consumidores foram extintos junto
com `e6_render.py` (fatia 3) e `pipeline/stages/e6.py` (fatia 2).
