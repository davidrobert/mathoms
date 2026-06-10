---
id: A24.l1
type: lane
title: "Data Lineage F2 — discovery do de-leak + substrato de rebaseline endurecido"
sprint: A24
plan: PLAN-data-lineage
status: in_progress
priority: P0
branch_slug: dl-f2-discovery
adrs:
  - "[[ADR-280]]"
  - "[[ADR-279]]"
depends_on: []
parallel_with: ["[[A24.l4]]"]
tags:
  - type/lane
  - sprint/a24
  - status/in-progress
  - priority/p0
  - area/data-lineage
  - area/pipeline
---

# A24.l1 — `dl-f2-discovery` (GATE da F2)

> **Plano:** [[PLAN-data-lineage]] · Onda 2 (F2). Gate G2 — nenhuma lane `dl-f2-deleak-*`
> abre antes desta fechar. Conforma à [[ADR-280]] e aos blockers F2-B/F2-DB do plano;
> não reabre. Co-design `senior-cto` + `data-engineer` registrado em 2026-06-09.

## Objetivo

(a) Classificar TODOS os consumidores de `tipo_lancamento`/`numero_conta_norm`
(F2-B1) + enumerar variantes por banco (F2-B2). (b) **Endurecer o substrato de
rebaseline ANTES do 1º rebaseline** (F2-DB5/6/7 — guard-rail G-c). (c) Blast
radius empírico: strip dos campos → re-run → **zero `value_delta`** (F2-DB8).

## Discovery — classificação de consumidores (F2-B1, ground truth verificado)

| Campo | Consumidor | file:line | Classe |
|---|---|---|---|
| `tipo_lancamento` | writers parsers C6/Caixa/Santander | `scripts/e2/banks/c6bank.py:253,438,714-720,913` · `caixa.py:183,217,335` · `santander.py:772` | parser-interno |
| `tipo_lancamento` | testes de parser | `tests/test_c6bank_pdf_parser.py` | teste-only |
| `tipo_lancamento` | fixture de schema | `tests/test_schema_validation.py:195` | teste-only |
| `tipo_lancamento` | contrato E2 | `config/schemas/e2_extract.schema.json:36` | contrato (sai na l3, mesma PR — F2-DB1) |
| `tipo_lancamento` | K4 | `pipeline/domain/services/e2_natural_key.py:59` | comentário — confirma que NÃO alimenta hash |
| `numero_conta_norm` | **o leak**: `finalize_e2_result` importa `account_normalization` | `scripts/e2/common.py:393-399` (chamado por `scripts/e2_extract.py:166`) | domínio→extração (remove na l2) |
| `numero_conta_norm` | fallback re-normalizador | `pipeline/domain/models/document.py:158` | domínio downstream — **re-deriva**, não depende do campo |
| `numero_conta_norm` | fixture | `tests/unit/pipeline/test_bank_statement_account_number.py:29` | teste-only |

**Zero consumidores de domínio downstream que dependam do valor emitido pela
extração** — de-leak é cirúrgico (achado da revisão 2026-06-09 confirmado).

Variantes de `tipo_lancamento` por banco (F2-B2): C6 CSV (título da coluna:
"Entrada PIX", "Saída PIX", "Pagamento", "Outros gastos", "Entradas", …) ·
C6/Santander fatura ("pagamento", "anuidade", "estorno", "iof") · Caixa
(`_classify(historico)`: "Saída PIX | Entrada PIX | Devolução PIX | Saída
TED/Transferência | Entrada TED/Transferência | Pagamento Boleto | Saque |
Depósito | Tarifa Bancária | Encargos Bancários | Salário | Transferência |
Outros").

## Escopo (entregas de código)

| # | Item | Decisão de co-design |
|---|---|---|
| 1 | **F2-DB7** — invariantes por categoria em `tests/test_e5_conservation_invariants.py` | `cents(round(Σ despesas_por_categoria, 2)) == cents(despesa_total)`; idem `por_fonte`↔`receita_total`; + `receita_total == receita_recorrente + receita_one_time`. **Reproduzir o `round(Σ,2)` do E4 (`e4_categorize.py:862,888`) antes de cents** — senão ±1 cent flaky com ≥2 categorias. Validar empiricamente nos 4 `_CASES` antes de cimentar. NÃO inventar invariante sobre recorrente-por-categoria (depende de `is_one_time_income` por transação). |
| 2 | **F2-DB6** — `ManifestEntry` (`dev/golden_diff.py`) + `ref` (file:line) + `adr` + `rationale` obrigatórios | Nomes alinham ao header já documentado em `rebaseline_manifest.yaml:18-29` (não inventar `reason`). `ref` casa `\S+:\d+`, `adr` casa `^ADR-\d+$`; `load_manifest` fail-fast com valor ofensor + shape esperado. Metadados FORA da chave de `_match_entry` (match continua por `(path, old_cents, new_cents)`). Manifesto está vazio (`[]`) — migração trivial. |
| 3 | **F2-DB5** — `dev/check_golden_rebaseline_isolation.py` (novo) | Granularidade **por COMMIT** (é o que viabiliza G-c: PR misto com commit de rebaseline isolado passa; commit misturando golden+produção falha). Name-only (paths), nunca conteúdo. Classe golden = `tests/fixtures/pipeline_golden/**` (inclui o manifesto — viajam juntos). Classe produção = `pipeline/**`, `scripts/**`, `backend/app/**` MENOS `tests/**`, `docs/**` e `config/schemas/**` (schema é contrato — mudar schema+golden no mesmo commit é legítimo, é o próprio fluxo F2-DB1). Modo pre-commit (staged) + modo CI (`git rev-list base..head`, check por commit). |
| 4 | **F2-DB8** — blast radius | Fixture dogfood sintética NÃO exercita os campos hoje (falso conforto) → **adicionar `tipo_lancamento` (variantes reais por banco) + `numero_conta_norm`** aos `e2_extracts` da fixture, incluindo um `numero_conta_norm` que DIFERE do que `document.from_e2_dict:158` re-normalizaria (prova independência real). Strip+rerun (E2→E5 via `run_dogfood_pipeline`) = prova **one-shot** do discovery (resultado documentado aqui, não vira teste por-PR — ADR-210). Guarda permanente = invariantes (item 1) + grep-gate estático `dev/check_no_leak_field_consumers.py` (novo reader de `tipo_lancamento`/`numero_conta_norm` em `pipeline/**`/`backend/**` → exit 1). |
| 5 | Dogfood real (G-f) | Step humano local/gitignored (SMOKE_TEST_HUMAN), não pytest: diff de números antes/depois das PRs l2/l3 sobre o workspace real. Veredito zero `value_delta` exigido antes do merge das deleak-*. |

## Resultado do blast radius (preencher no fechamento da lane)

- [ ] Strip `tipo_lancamento` + `numero_conta_norm` → E3 byte-idêntico (tese "cirúrgico")
- [ ] golden_diff E4/E5 pós-strip: zero `value_delta`
- [ ] Qualquer delta = consumidor oculto = **blocker** (reabrir discovery)

## Critério de aceite

- Invariantes por categoria verdes nos 4 casos (`minimal`, `mixed`, `baseline`, `divergent`).
- `load_manifest` rejeita entrada sem `ref`/`adr`/`rationale` com mensagem valor-ofensor.
- `check_golden_rebaseline_isolation`: commit golden+produção → exit 1; commit golden+manifesto → OK; commit golden+schema → OK; registrado em pre-commit + CI.
- `check_no_leak_field_consumers` verde hoje; reader sintético → exit 1.
- Fixture dogfood exercita os 2 campos; strip+rerun documentado com zero delta.
- `pre-commit run --all-files` + `pytest tests -q` verdes.

## Não-escopo

- Mover código de extração (`tipo_lancamento`/`numero_conta_norm`) → l2/l3.
- Tocar `e2_extract.schema.json` → l3 (mesma PR do delete, F2-DB1).
- ADR nova — conforma a [[ADR-279]]/[[ADR-280]] + plano (G-c é estratégia de teste).

## Owner

Orquestrador A24 com co-design `data-engineer` + `senior-cto` (2026-06-09).
