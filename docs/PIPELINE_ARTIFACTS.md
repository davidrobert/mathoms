# Artefatos do pipeline — validação JSON (checklist P1-D3)

> Referência para cobertura de `validate_artifact` e do modo **strict** (`FIN_PIPELINE_SCHEMA_MODE`).

## Schemas em `config/schemas/`

| Schema | Artefato típico | Onde valida após escrita |
| --- | --- | --- |
| `e2_extract.schema.json` | `processed/E2_extracts/*-2_extract.json` | `scripts/e2_extract.py` (`save_result`, exceto `requires_llm_fallback`); `pipeline/stages/e2_llm.py` |
| `e3_reconciled.schema.json` | `processed/E3_reconciled/*-3_reconciled.json` | `scripts/e3_reconcile.py` (após `write_json_atomic` por conta) |
| `e4_unified.schema.json` | `processed/E4_unified/*-4_unified.json` | `scripts/e4_categorize.py` (`save_json`) |
| `e5_analysis.schema.json` | `processed/E5_analysis/analise_financeira-5_analysis.json` | `scripts/e5_analyze.py` (write principal) |
| `baseline_patrimonial.schema.json` | baseline E1.5 | `e4_categorize` (baseline) — validação dedicada pode evoluir |

**Política:** modo default **warn** (`pipeline.json`); CI roda subset com `FIN_PIPELINE_SCHEMA_MODE=strict` nos testes de `validate_artifact`. Stubs E2 só para LLM (`requires_llm_fallback`) não passam por schema para evitar ruído.

## Fixtures golden

Ver [tests/fixtures/pipeline_golden/README.md](../tests/fixtures/pipeline_golden/README.md).

## Artefatos auxiliares (sem JSON schema)

| Artefato | Gerado por | Contrato nos testes |
| --- | --- | --- |
| `logs/qa_log.md` | `e4_categorize.generate_qa_log` | `tests/pipeline_golden_asserts.assert_qa_log_md` (cabeçalhos mínimos) |

**Próximo incremento sugerido**

- Repetir o padrão **layout dedicado + `test_*_synthetic_extracts_transactions`** para bancos do registry que ainda usam só a tabela genérica (ex.: C6, Bradesco, Quinto Andar).

## E2 — sintético e real anonimizado (duas fases)

1. **Fase 1 (em curso): só sintético alinhado ao parser** — `tests/fixtures/pdf_generator.py` + `tests/test_e2_synthetic_pdf_parsers.py`. Objetivo: todo banco relevante do `registry` com `_draw_*` ou tabela genérica suficiente, e asserts de extração onde fizer sentido. **Não** depende de PDF real versionado.
2. **Fase 2 (planejada, após Fase 1): PDF real anonimizado no repositório** — complemento opcional para regressão de **layout fiel** (renderização, quebras de página, ruído de OCR). Requisitos mínimos: redação completa (nome, conta, agência, CPF, valores identificáveis, metadados do PDF); revisão em PR; aderência a `tests/utils/lint_no_real_pii.py` e política do repo; localização (pasta dedicada, naming canônico, um teste por arquivo que rode o mesmo `route_to_parser` / parser). **Não** substitui o sintético no dia a dia do CI — acrescenta camada onde o custo/revisão forem aceitáveis.

## Golden E2 — PDF sintético × registry

- `tests/test_e2_synthetic_pdf_parsers.py`: para cada banco em `scripts/e2/registry.py` (`BANK_MODULES`), PDF gerado + filename canônico → `route_to_parser` → resultado dict (sem exceção). **BTG, Rico, Wise, PicPay, Bank of America, Santander, Itaú, Caixa:** testes dedicados exigem transações + `saldo_final` (`test_btgpactual_*`, `test_rico_*`, `test_wise_*`, `test_picpay_*`, `test_bankofamerica_*`, `test_santander_*`, `test_itau_*`, `test_caixa_*`).
- `tests/fixtures/pdf_generator.py`: **caixa** (14 códigos em `BankCode`); layouts dedicados **BTG**, **Rico**, **Wise**, **PicPay**, **Bank of America**, **Santander**, **Itaú**, **Caixa** (tabela 7 colunas `parse_caixa`) — ver `_draw_btgpactual_movimentacao`, `_draw_rico_extrato`, `_draw_wise_extrato`, `_draw_picpay_extrato`, `_draw_bankofamerica_extrato`, `_draw_santander_extrato`, `_draw_itau_extrato`, `_draw_caixa_extrato`.

## Golden de execução E3

Implementado em `tests/test_e3_golden_execution.py`: tenant mínimo + `minimal-extrato-2_extract.json` (com saldos) → `e3_reconcile.main` → um `*-3_reconciled.json`, asserts + `jsonschema` + `validate_artifact`.

## Golden de execução E4

Implementado em `tests/test_e4_golden_execution.py`: tenant mínimo (`categorization.json` com keyword `PIX` → categoria `renda`) + cópia de `tests/fixtures/pipeline_golden/e3/minimal-conta-3_reconciled.json` em `processed/E3_reconciled/` → `e4_categorize.main` → sete `*-4_unified.json` + `validate_artifact` em cada arquivo. Cenário **receita + despesa** (`test_e4_execution_mixed_receita_despesa`): fixture `e3/minimal-conta-com-despesa-3_reconciled.json` + keyword `CINEMA` → `lazer`. Cenário **com baseline E1.5** (`test_e4_execution_with_baseline_patrimonial`): `e2/minimal-baseline-1.5_consolidated.json` em `processed/E2_extracts/baseline_patrimonial-1.5_consolidated.json` — `patrimonio-4_unified.json` espelha o baseline; validação desse arquivo com `baseline_patrimonial.schema.json` (não com `e4_unified`, pois o conteúdo é o consolidado).

## Golden de execução E5

Implementado em `tests/test_e5_golden_execution.py`: mesmo fluxo de dados que o golden E4 (E3 fixture → `e4_categorize.main`) com `config/goals.json` mínimo (`if_meta`, `trs_pct`) e cópias de `scoring.json`, `parametros_fiscais.json`, `taxas.json` do repositório → `e5_analyze.main` → `processed/E5_analysis/analise_financeira-5_analysis.json` + `jsonschema` + `validate_artifact`. Cenário misto: `test_e5_execution_mixed_receita_despesa` (mesma fixture E3 com despesa). Cenário com baseline: `test_e5_execution_with_baseline_patrimonial` — totais de patrimônio batem com o fixture (`dividas[]` com `saldo_31_12` por ano, necessário para o E5 somar dívidas por membro).

## Golden de execução E5.N

Implementado em `tests/test_e5n_golden_execution.py`: mesmo cenário mínimo que o golden E5 (helper `_build_e5_workspace` — evita depender de `pytest_plugins` entre módulos) → `e4_categorize.main` → `e5_analyze.main` → `e5n_narrativas.main` → `analise_financeira-5_analysis.json` passa a incluir `narrativas` (`perfil_familia`, `summaries`, `charts`). O teste chama `validate_narrativas` **antes** do `finally` que repõe os globals do `e5n_narrativas` (o chart dinâmico `{cônjuge}_cenarios` depende de `family_members.json` do tenant). Segundo cenário: **`test_e5n_execution_narrativas_with_conjuge_chart`** — membro com `papel: conjuge` → presença de `ana_cenarios` em `narrativas.charts`.

## Golden de execução E6

Implementado em `tests/test_e6_golden_execution.py`: após E4 e E5, `scripts.e6_render.render_report(root_dir=…)` com `config/templates/report_template.html`, `report_layout.yaml`, `cenarios.json`, `institutions.json` copiados do repositório → `output/relatorio_financeiro_YYYYMMDD.html` (HTML standalone; validações internas `validate_report` no render). **Correção de robustez:** `e6_render` cria `output/` com `mkdir(parents=True)` antes de gravar o HTML (tenants novos sem pasta `output/`).
