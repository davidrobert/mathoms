# Artefatos do pipeline — validação JSON

> Referência para cobertura de `validate_artifact` e do modo **strict** (`MATHOMS_PIPELINE_SCHEMA_MODE`).
>
> **Pós-[[ADR-212]] (2026-05-14):** artefatos do pipeline vivem em
> `pipeline_artifacts` (DB); validação é universal via hook pós-write em
> `DBArtifactStore.write` (mapping `SCHEMA_BY_STAGE`). Os paths
> `storage/<ws>/processed/...` documentados abaixo permanecem apenas como
> **convenção histórica de `artifact_key`**; o conteúdo canônico vive no DB.
> (O CLI read-only `scripts/e0_audit.py` que consumia esses paths foi
> deletado em [[ADR-213]].)

## Schemas em `config/schemas/`

| Schema | Stage (descritivo / legacy) | `artifact_key` típico |
| --- | --- | --- |
| `e2_extract.schema.json` | `extract_statements` / `E2` | `<banco>_<doctype>_<periodo>` (stem do doc) |
| `e3_reconciled.schema.json` | `reconcile_transactions` / `E3` | `<banco>_<doctype>_<moeda>_<periodo>` |
| `e4_unified.schema.json` | `categorize_transactions` / `E4` | `despesas` · `receitas` · `patrimonio` |
| `e5_analysis.schema.json` | `analyze_finances` / `E5` | `analise_financeira` |
| `e15_baseline_extract.schema.json` | `extract_baseline` / `E1.5` (+ `E1.5a` per-IRPF · A20.l11) | `baseline_patrimonial` · `irpfdeclaracao_<ano>` |
| `baseline_patrimonial.schema.json` | `consolidate_baseline` / `E1.5c` | `baseline_patrimonial` |
| `e16_irpf_full.schema.json` | `extract_irpf_full` / `E1.6` ([[ADR-157]]) | `irpfdeclaracao_<ano>` |
| `parecer_planejador.schema.json` | `review_finances_holistic` / `E6-parecer` ([[ADR-199]]) | `parecer_planejador` |

**Hook universal de validação:** `DBArtifactStore.write` chama `validate_dict`
após persistir o `content_json`, resolvendo o schema via mapping
`SCHEMA_BY_STAGE` em `backend/app/services/db_artifact_store.py` (vive no
backend, não em `pipeline/` — boundary ADR-212). Stages sem schema registrado
passam sem validação (futuras adições só precisam estender o mapping).

**Política:** modo default **warn** (`pipeline.json`); CI roda subset com
`MATHOMS_PIPELINE_SCHEMA_MODE=strict` nos testes de `validate_artifact`. Stubs
E2 só para LLM (`requires_llm_fallback`) não passam por schema para evitar ruído.

## Fixtures golden

- JSON de pipeline (E2/E3/E4): [tests/fixtures/pipeline_golden/README.md](../../tests/fixtures/pipeline_golden/README.md).
- JSON de **saída LLM** (schemas Pydantic E1 / E1.5 / E1.6 / E2-LLM / informes anuais / CRLV+apólices): [tests/fixtures/llm_golden/README.md](../../tests/fixtures/llm_golden/README.md) + `tests/test_llm_golden.py`. O golden do parecer (E6) não usa JSON em `llm_golden/` — é output canned em `tests/test_parecer_planejador_golden.py`.
- **PDF real anonimizado (Fase 2, opcional):** [tests/fixtures/e2_real_pdf_anon/README.md](../../tests/fixtures/e2_real_pdf_anon/README.md) + `tests/test_e2_real_pdf_regression.py` (pasta pode ficar vazia; cada `*.pdf` adicionado roda `route_to_parser`).

## Artefatos auxiliares (sem JSON schema)

| Artefato | Gerado por | Contrato nos testes |
| --- | --- | --- |
| `logs/qa_log.md` | `categorize_transactions.generate_qa_log` | `tests/pipeline_golden_asserts.assert_qa_log_md` (cabeçalhos mínimos) |

**Próximo incremento sugerido**

- **Fase 2 (opcional):** popular `tests/fixtures/e2_real_pdf_anon/` com PDFs **redigidos** + revisão de PR (scaffold e teste já existem). **LLM:** novos estágios → novo schema + `tests/fixtures/llm_golden/` + `tests/test_llm_golden.py`.

## E2 — sintético e real anonimizado (duas fases)

1. **Fase 1 (registry coberto): só sintético alinhado ao parser** — `tests/fixtures/pdf_generator.py` + `tests/test_e2_synthetic_pdf_parsers.py`. Cada banco em `BANK_MODULES` tem `_draw_*` + asserts onde aplicável; códigos só em `BankCode` fora do registry continuam na tabela genérica. **Não** depende de PDF real versionado.
2. **Fase 2 (opcional): PDF real anonimizado no repositório** — complemento para regressão de **layout fiel**. **Scaffold:** `tests/fixtures/e2_real_pdf_anon/` + `tests/test_e2_real_pdf_regression.py` (CI verde com pasta vazia). Requisitos para cada binário: redação completa; nome de arquivo canônico para o registry; revisão em PR. **Não** substitui o sintético no dia a dia do CI.

## Golden E2 — PDF sintético × registry

- `tests/test_e2_synthetic_pdf_parsers.py`: para cada banco em `scripts/e2/registry.py` (`BANK_MODULES`), PDF gerado + filename canônico → `route_to_parser` → resultado dict (sem exceção). **C6, Bradesco, BTG, Rico, Wise, PicPay, Bank of America, Santander, Itaú, Caixa:** **≥1** transação + `saldo_final` (`test_c6bank_*`, `test_bradesco_*`, `test_btgpactual_*` … `test_caixa_*`). **Quinto Andar** (fatura aluguel): **`itens`** + **`total_recebido`** (`test_quintoandar_synthetic_extracts_items`) — não usa `transacoes`/`saldo_final`.
- `tests/fixtures/pdf_generator.py`: 14 códigos em `BankCode`; layouts dedicados ao registry incluem **C6** (`_draw_c6_extrato`), **Bradesco** (`_draw_bradesco_extrato`), **BTG**, **Rico**, **Wise**, **PicPay**, **Bank of America**, **Santander**, **Itaú**, **Caixa**, **Quinto Andar** — ver funções `_draw_*` no arquivo.

## Golden de execução E3

Implementado em `tests/test_e3_golden_execution.py`: tenant mínimo + `minimal-extrato-2_extract.json` (com saldos) → `reconcile_transactions.main` → um `*-3_reconciled.json`, asserts + `jsonschema` + `validate_artifact`.

## Golden de execução E4

Implementado em `tests/test_e4_golden_execution.py`: tenant mínimo (`categorization.json` com keyword `PIX` → categoria `renda`) + cópia de `tests/fixtures/pipeline_golden/e3/minimal-conta-3_reconciled.json` em `processed/E3_reconciled/` → `categorize_transactions.main` → sete `*-4_unified.json` + `validate_artifact` em cada arquivo. Cenário **receita + despesa** (`test_e4_execution_mixed_receita_despesa`): fixture `e3/minimal-conta-com-despesa-3_reconciled.json` + keyword `CINEMA` → `lazer`. Cenário **com baseline E1.5** (`test_e4_execution_with_baseline_patrimonial`): `e2/minimal-baseline-1.5_consolidated.json` em `processed/E2_extracts/baseline_patrimonial-1.5_consolidated.json` — `patrimonio-4_unified.json` espelha o baseline; validação desse arquivo com `baseline_patrimonial.schema.json` (não com `e4_unified`, pois o conteúdo é o consolidado).

## Golden de execução E5

Implementado em `tests/test_e5_golden_execution.py`: mesmo fluxo de dados que o golden E4 (E3 fixture → `categorize_transactions.main`) com `config/goals.json` mínimo (`if_meta`, `trs_pct`) e cópias de `scoring.json`, `parametros_fiscais.json`, `taxas.json` do repositório → `analyze_finances.main` → `processed/E5_analysis/analise_financeira-5_analysis.json` + `jsonschema` + `validate_artifact`. Cenário misto: `test_e5_execution_mixed_receita_despesa` (mesma fixture E3 com despesa). Cenário com baseline: `test_e5_execution_with_baseline_patrimonial` — totais de patrimônio batem com o fixture (`dividas[]` com `saldo_31_12` por ano, necessário para o E5 somar dívidas por membro).

### Bloco `investimentos` no E5 JSON

`output["investimentos"]` (escrito por `e5_serialization.build_e5_output`) carrega:

- `tabela_classes`: agregação por classe de ativo (saída de `InvestimentosClassesAnalyzer`).
- `total`: soma da carteira.
- `top_ativos`: ranking dos ≤15 maiores ativos individuais (saída de `TopAtivosAnalyzer`, companion de A5b). Cada item: `{posicao, nome, classe, membro, instituicao, valor, pct_carteira, tipo_origem}`. Item fechado por `additionalProperties:false` no schema; enums em `classe` (6 valores) e `tipo_origem` (`investimento`/`imovel`). Coerente com `tabela_classes` por consumir o mesmo `bens_por_membro` que o aggregator de classes. Consumido pelo card `Top15AtivosCard` em S3 (frontend) e por `_find_top_asset` em `generate_narratives.py` para narrativa do chart.
- `instituicoes_por_membro`: lista de `{membro, instituicoes[]}` com instituições de investimento agrupadas (saída de `InstituicoesPorMembroAnalyzer`). Capitalizadas e dedup; `additionalProperties:false` no item; `uniqueItems:true` na lista de instituições. Mesmo `bens_por_membro` das outras agregações.
- `n_imoveis_total`: contagem total de imóveis em `bens_por_membro` (residência + investimento). Paridade com o legado `_extract_top_institutions`. Consumido por `summaries_narrator`, `charts_narrator` e `perfil_familia_narrator` via `M['n_imoveis']`.

### Bloco `cenarios_conjuge` no E5 JSON (ADR-166 + ADR-167)

`output["cenarios_conjuge"]` (escrito por `e5_serialization.build_e5_output`,
populado por `CenariosConjugeAnalyzer.to_legacy_dict()` em
`pipeline/domain/services/cenarios_conjuge_analyzer.py`):

- `labels: list[str]`, `aportes: list[float]`, `prazos_if: list[float]`,
  `anos_if: list[int]` — vetores paralelos por cenário (atualmente fixo
  em 1 cenário "Sem renda do cônjuge").
- `idade_<titular_key>_if: list[int]` — chave dinâmica
  (titular_key vem de `family_members`); declarada via
  `patternProperties` no schema. Sem upper bound — sentinela legada
  `prazo=999` propaga para idade>120.
- `premissas: object` com `meta_if`, `investivel_atual`,
  `retorno_real_anual_pct`, `aporte_base`, `fator_reduzido`,
  `salario_<conjuge_key>_clt_brl`.
- `cenarios: list[object]` — cada item tem `nome`, `aporte_mensal`,
  `prazo_if_anos`, `ano_if`, `resumo` (obrigatórios em strict) +
  `idade_<titular_key>` (chave dinâmica via `patternProperties`).
- Eligibility gate (ADR-167) emite `{}` quando workspace não-elegível
  (solteiro / 1 renda / casal sem meta IF / casal 95-5). Schema aceita
  o objeto vazio.

Declarado formalmente em
[config/schemas/e5_analysis.schema.json](../../config/schemas/e5_analysis.schema.json)
desde W1-T08 (PLATFORM_REVIEW_PLAN, 2026-05-06). Modo `warn` ativo;
cutover `strict` é W6-T01.

## Golden de execução E5.N

Implementado em `tests/test_e5n_golden_execution.py`: mesmo cenário mínimo que o golden E5 (helper `_build_e5_workspace` — evita depender de `pytest_plugins` entre módulos) → `categorize_transactions.main` → `analyze_finances.main` → `generate_narratives.main` → `analise_financeira-5_analysis.json` passa a incluir `narrativas` (`perfil_familia`, `summaries`, `charts`). O teste chama `validate_narrativas` **antes** do `finally` que repõe os globals do `generate_narratives` (o chart dinâmico `{cônjuge}_cenarios` depende de `family_members.json` do tenant). Segundo cenário: **`test_e5n_execution_narrativas_with_conjuge_chart`** — membro com `papel: conjuge` → presença de `ana_cenarios` em `narrativas.charts`.

## Produção do relatório (pós-[ADR-129](../DECISIONS.md#adr-129--descontinuação-completa-do-renderer-html-server-side))

Não há mais stage E6 nem HTML standalone gerado pelo pipeline. O fluxo
de produção do relatório é:

1. **E5** (e opcionalmente E5.N + E6-parecer) escreve
   `processed/E5_analysis/analise_financeira-5_analysis.json` —
   validado pelo `e5_analysis.schema.json`.
2. `backend/app/services/pipeline_task._create_report_from_output`
   cria o row `Report` no DB a partir desse JSON
   (`analysis_artifact_id` aponta via FK para `pipeline_artifacts.id` —
   ADR-131 substituiu o ponteiro de filesystem `analysis_json_path`).
3. O relatório é renderizado **on-demand** pela rota React
   `/reports/[id]` consumindo `GET /reports/{id}/data`.
4. O único export server-side é **PDF via Playwright**
   ([backend/app/services/pdf_renderer.py](../../backend/app/services/pdf_renderer.py))
   sobre essa mesma rota.

A pasta `output/` em `storage/<workspace>/` ficou vestigial após a
remoção do renderer standalone — consumidores foram extintos junto
com `e6_render.py` (fatia 3) e `pipeline/stages/e6.py` (fatia 2).
