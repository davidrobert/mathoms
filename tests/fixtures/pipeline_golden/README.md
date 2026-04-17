# Fixtures golden (P1)

JSONs mínimos versionados para **validação de schema** e regressão documental.

| Arquivo | Schema | Uso |
| --- | --- | --- |
| `e2/minimal-extrato-2_extract.json` | `e2_extract.schema.json` | Extrato mínimo com `periodo` + `transacoes` |
| `e2/minimal-baseline-1.5_consolidated.json` | `baseline_patrimonial.schema.json` | Baseline E1.5 mínimo: `patrimonio_por_ano` + `dividas[]` com `saldo_31_12` (E5 agrega dívidas por membro a partir da lista) |
| `e3/minimal-conta-3_reconciled.json` | `e3_reconciled.schema.json` | Conta reconciliada (estrutura `reconcile_account`) |
| `e3/minimal-conta-com-despesa-3_reconciled.json` | `e3_reconciled.schema.json` | Mesmo + uma despesa (débito) para goldens E4/E5 com fluxo misto |
| `e4/minimal-receitas-4_unified.json` | `e4_unified.schema.json` | Ramo `periodo` + `total_geral` |

Atualizar estes arquivos quando o schema canônico mudar (diff revisado no PR).

**E2 / PDFs:** o alinhamento filename → parser está em `tests/test_e2_synthetic_pdf_parsers.py`; o gerador central é `tests/fixtures/pdf_generator.py` (layouts dedicados para **todo** o `scripts/e2/registry.py` — **C6**, **Bradesco**, **BTG**, **Rico**, **Wise**, **PicPay**, **Bank of America**, **Santander**, **Itaú**, **Caixa**, **Quinto Andar**). **Fase 2 opcional:** PDFs reais anonimizados — ver [PIPELINE_ARTIFACTS.md](../../../docs/PIPELINE_ARTIFACTS.md) § *E2 — sintético e real anonimizado*.

**Execução:** o fluxo E2→E3 com assert está em `tests/test_e3_golden_execution.py` (usa `e2/minimal-extrato-2_extract.json` + saldos escritos no teste). Cenário receita+despesa: `test_e4_golden_execution.test_e4_execution_mixed_receita_despesa` e `test_e5_golden_execution.test_e5_execution_mixed_receita_despesa`. Narrativas E5.N no JSON de análise: `tests/test_e5n_golden_execution.py` (inclui cenário com cônjuge para o chart `ana_cenarios`).
