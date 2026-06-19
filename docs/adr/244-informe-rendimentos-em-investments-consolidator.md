---
id: ADR-244
type: adr
title: "InvestmentsConsolidator aceita `tipo_documento=informe_rendimentos` como posição"
status: Decidido
phase: A17.incremental-correctness
date: "2026-05-21"
relates_to:
  - "[[ADR-145]]"
  - "[[ADR-226]]"
  - "[[ADR-241]]"
  - "[[ADR-242]]"
  - "[[ADR-243]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 244"
  - "informe_rendimentos como investments"
tags:
  - area/pipeline
  - status/decidido
  - type/adr
---

# ADR-244 — `informe_rendimentos` é fonte legítima de posição de investimento

**Status:** Decidido • **Data:** 2026-05-21 • **Relaciona** [[ADR-145]] (taxonomia patrimonial), [[ADR-226]] (account resolver), [[ADR-241]] (E2 ws-scoped), [[ADR-242]] (LLM hint), [[ADR-243]] (member resolver)

## Contexto

Em [`pipeline/domain/services/e4_categorizer_adapter.py`](../../pipeline/domain/services/e4_categorizer_adapter.py) o filter `load_investment_positions` aceita posição de investimento somente quando:

```python
tipo ∈ {"investimentosposicao", "carteirarendafixa", "cdbresumo"}
OR tipo_documento == "investment_report" AND data["investimentos"]
```

Esse contrato cobre PDFs de **portfólio** (BTG, Rico) e parsers determinísticos legados. Não cobre **informe de rendimentos** (informe IR anual emitido pelo banco), que é uma **fonte fiscal certificada** de posição em 31/12 do ano-base.

Caso real observado em PR #410 / workspace `Campos`, run `c36c4baf-…`:

- Documento "Informe Itaú 2025_David.pdf" classificado como `investment_report` → `extract_with_llm` extrai como `tipo_documento="informe_rendimentos"` (mapping `map_e0_doc_type_to_document_type`).
- Payload E2-llm contém:
  - `transacoes`: 4 linhas (rendimento bruto/líquido, IRRF, parcela imobiliário)
  - `investimentos`: 4 posições (CDB **R$ 290.000**, conta corrente R$ 0, dívida imobiliária -R$ 205k, dívida cc -R$ 10k)
- Filter rejeita porque `tipo_documento != "investment_report"`.
- Card "Investimentos David Robert" mostrou R$ 317,24 (Binance crypto only) em vez dos ~R$ 700k esperados — perda de R$ 290k de CDB na linha.

ADR-243 (MemberNameResolver) corrigiu uma das duas causas (mismatch de membro). Esta ADR corrige a outra: o filter de aceitação.

## Decisão

Estender o filter em `load_investment_positions` para aceitar **ambos**:

```python
tipo_documento ∈ {"investment_report", "informe_rendimentos"}
  AND data["investimentos"]  (não-vazio)
```

Justificativa:

1. **Semântica fiscal**: informe IR é snapshot certificado de posição em 31/12 — mesma natureza de `investment_report` para fins patrimoniais.
2. **Idempotência**: `informe_rendimentos` segue o mesmo schema `e2_extract.schema.json` que `investment_report` para o campo `investimentos[]` — não há contrato divergente a tratar.
3. **Compatibilidade com [[ADR-243]]**: agora que `MemberNameResolver` normaliza o membro emitido pelo LLM, o `InvestmentsConsolidator` consegue agregar corretamente sob `family_members.key` canônica.

Continua rejeitando `informe_rendimentos` **sem** campo `investimentos` (caso comum de informe que só traz rendimentos, sem posição).

## Alternativas consideradas

- **(a) Criar um novo `tipo_documento="investment_position_from_informe"`** e re-extrair informes via LLM com esse rótulo. Rejeitada: muda contrato com o LLM (cara de testar regressão); o `informe_rendimentos` já carrega a info na fonte.
- **(b) Pipeline parsing-only**: parser determinístico do informe Itaú/Santander que produz `investimentosposicao`. Faz sentido a longo prazo (alinhada com follow-up de ADR-242 sobre eliminação de LLM em docs estáveis), mas é trabalho de outra lane.
- **(c) Aceitar todos os `tipo_documento`** com `investimentos[]` populado. Rejeitada: muito frouxo — `extrato` ou `fatura` com `investimentos` por engano viraria position falsa.

## Consequências

- ✅ **Fix observado**: workspace `Campos` recebe R$ 290k do CDB Itaú em `total_por_membro["david_robert_camargo_ferreira_campos"]`.
- ✅ **Aplica a qualquer banco BR** que emita informe IR com campo `Bens e Direitos` (Itaú, Santander, Caixa, Bradesco, Picpay, Nubank, BrasilPrev, XP). Workspace `Campos` tem 7 informes processados via `extract_irpf_full` + 1 via `extract_with_llm` — todos passam a contar.
- ✅ **Sem mudança de contrato externo**: schema E2 inalterado; só amplia a condição de aceitação no consumer.
- ⚠️ **Risco de double-counting**: o mesmo CDB pode aparecer em (a) informe rendimentos do banco emissor E (b) extrato de posição (`investmentosposicao`) do mesmo CDB. Mitigado pelo dedup existente em `InvestmentsConsolidator.consolidate` por `(instituicao, membro)` — mantém o mais recente por `data_referencia`.

## Gates de regressão

- **T1** — `tests/unit/pipeline/test_e4_categorizer_adapter.py::test_load_investment_positions_accepts_informe_rendimentos` (fixture com Itaú CDB R$ 290k real).
- **T2** — `test_load_investment_positions_skips_informe_rendimentos_without_investimentos` (sem `investimentos[]`, não é posição).
- **T3** — Dogfood pós-merge: workspace `Campos`, regerar relatório dezembro/2025 e validar que `total_por_membro["david_robert_camargo_ferreira_campos"]` ≥ R$ 290.000 (vs. R$ 317 anterior).

## Follow-ups

1. **Parser determinístico de informe rendimentos** (também follow-up da ADR-242): elimina dependência do LLM para o documento mais estável dos bancos BR. Reduz custo + variabilidade.
2. **Dedup explícito de CDB cross-source** (informe IR vs. extrato de posição) — se observarmos duplicação real em produção via telemetria, criar regra de prioridade explícita.
