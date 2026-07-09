---
id: ADR-245
type: adr
title: "`caixa_moeda_estrangeira` cai para baseline IRPF quando E3 não traz USD/EUR"
status: Decidido
phase: A17.incremental-correctness
date: "2026-05-21"
relates_to:
  - "[[ADR-145]]"
  - "[[ADR-157]]"
  - "[[ADR-241]]"
  - "[[ADR-244]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 245"
  - "Caixa ME fallback IRPF"
tags:
  - area/pipeline
  - status/decidido
  - type/adr
---

# ADR-245 — Fallback baseline IRPF para `caixa_moeda_estrangeira`

**Status:** Decidido • **Data:** 2026-05-21 • **Relaciona** [[ADR-145]] (taxonomia patrimonial), [[ADR-157]] (IRPF full), [[ADR-241]] (E2 ws-scoped), [[ADR-244]] (informe rendimentos)

## Contexto

`E5AnalyzerAdapter._load_caixa_from_e3` ([pipeline/domain/services/e5_analyzer_adapter.py:743](../../pipeline/domain/services/e5_analyzer_adapter.py)) carrega o card "Caixa e Moeda Estrangeira" lendo **saldo_final** dos artifacts E3 reconciliados. Quando o workspace **não tem extrato bancário em USD/EUR reconciliado** mas tem **saldo declarado em informe IR**, o card fica zerado.

Caso real (workspace dogfood, run `c36c4baf-…`):

- Baseline IRPF 2024 (E1.5c) contém:
  - `"DEPOSITO EM MOEDA NACIONAL DECORRENTE DE MOEDA ESTRANGEIRA - U$ 5.000,00"` → R$ 25.000,00
  - `"DEPOSITO EM MOEDA ESTRANGEIRA DOLAR (PAIS: EXTERIOR)"` → R$ 500,00
- E3 nessa run incremental: 2 artifacts (BRL + USD) com `saldo_final=0` (vieram do informe rendimentos do banco, não de extrato de conta) → nenhuma conta estrangeira reconciliada.
- Card "Caixa e Moeda Estrangeira": **R$ 0,00** — perde R$ 25.500,00 visível no IRPF.

Pós-[[ADR-241]] (E2 ws-scoped), runs futuras vão reconciliar extratos USD/EUR de corretora internacional que o workspace tenha. Mas:

1. Nem todo workspace tem extrato ME reconciliado.
2. Mesmo com extrato, há cenários onde o saldo do informe (auditado) é mais confiável que o saldo bancário (período pode estar incompleto, fatura processando, etc.).
3. O informe IR é **fonte fiscal certificada** com valor consolidado em R$ — não precisa câmbio.

## Decisão

Estender `_load_caixa_from_e3` com parâmetro `baseline: dict | None`. **Quando o iterador E3 não encontra nenhuma conta em USD/EUR** (`has_foreign_in_e3 == False`), agregar items de moeda estrangeira do baseline IRPF via helper puro `_extract_me_caixa_from_baseline`.

Detecção heurística (procura em `baseline.investimentos_consolidados[].descricao`):

```
keywords_generic:  "moeda estrangeira", "deposito em moeda nacional decorrente"
keywords_usd:      "dolar", "u$", "us$", "usd"
keywords_eur:      "euro", "eur"
```

Item identificado:
- `valor_brl = valores_31_12[ano_mais_recente]` (IRPF já consolida em R$)
- `moeda` inferida pelas keywords (default: USD — mais comum em IRPF BR)
- `tipo = "moeda_estrangeira_irpf"` (distingue de E3 reconciled na UI)

Caller (`analyze_via_store`) passa `patrimonio_raw` (lido de E4 patrimonio) como `baseline`.

## Limitações conhecidas (trade-offs aceitos)

1. **Possível double-count com `_investimentos_from_irpf`** quando `titular_val == 0` (fallback IRPF puro em [`PatrimonioCalculator._compute_investimentos`](../../pipeline/domain/services/patrimonio_calculator.py)). Nesse cenário, items ME aparecem **simultaneamente** em `caixa_moeda_estrangeira` E em `investimentos_titular`. **Cenário raro** — exige (a) zero posições atuais E (b) ME no baseline IRPF. Telemetrar via `fonte_investimentos == "irpf"` E `caixa_detalhes` contendo `tipo_moeda_estrangeira_irpf` simultaneamente. Resolver em lane separada (ver Follow-ups).

2. **Heurística de keyword pode pegar falso-positivo** (ex.: "FUNDO EURO X" como FII brasileiro). Mitigação: requer keyword genérica `"moeda estrangeira"` OU keyword específica de moeda — não basta só "euro" / "dolar" sozinho num nome de fundo. Conjunto observado em informes BR é restrito; ampliar se telemetria mostrar mais variações.

3. **Inferência de moeda é aproximada** quando descrição diz só "MOEDA ESTRANGEIRA" sem citar USD/EUR. Default USD (mais comum em IRPF BR — contas no exterior). Item já está em BRL no IRPF, então o erro de moeda só afeta o label exibido, não o total.

## Alternativas consideradas

- **(a) Não fazer fallback — exigir extrato reconciliado.** Status quo. Rejeitada: deixa R$ 25k visíveis no IRPF mas invisíveis no card "Caixa". Confunde o usuário ("eu tenho USD declarado, por que não aparece?").
- **(b) Reclassificar ME em ``baseline_normalizer`` (origem)** — separar items ME do `investimentos_consolidados` para um campo `caixa_me_consolidado` dedicado. Mais limpo mas exige migration de schema do baseline E1.5c + revalidar todos consumers de `investimentos_consolidados`. Trabalho maior; aguarda lane dedicada.
- **(c) Sempre somar baseline ME ao E3 ME** (sem condicional). Rejeitada: garantia de double-count quando ambas as fontes têm ME.

## Consequências

- ✅ **Fix observado**: workspace dogfood card "Caixa e Moeda Estrangeira" passa de R$ 0,00 para ~R$ 25.500 (= R$ 25.000,00 + R$ 500,00) quando E3 não tem extrato USD reconciliado.
- ✅ **Aplica automaticamente** a qualquer workspace com informe IR contendo seção "Bens e Direitos" código 02 com depósito em ME.
- ✅ **Sem mudança de contrato**: helper puro stateless; só amplia o output do `_load_caixa_from_e3` em caso específico.
- ⚠️ **Trade-off conhecido** com `_investimentos_from_irpf` em cenário de fallback IRPF puro — registrado nesta ADR §Limitações.

## Gates de regressão

- **T1** — `tests/unit/pipeline/test_e5_analyzer_adapter.py::TestMoedaEstrangeiraFallback` (6 testes):
  - `test_extract_me_caixa_picks_usd_deposit` — fixture com 2 items sintéticos
  - `test_extract_me_caixa_handles_eur` — EUR também
  - `test_extract_me_caixa_skips_non_me_items` — não pega CDB/ações genéricas
  - `test_extract_me_caixa_skips_zero_values` — items zerados (vendidos)
  - `test_load_caixa_fallback_kicks_in_when_no_foreign_in_e3` — E3 BRL only + baseline ME = fallback fires
  - `test_load_caixa_no_fallback_when_e3_has_foreign` — E3 USD reconciliado → baseline ignorado

- **T2** — Dogfood pós-merge: workspace dogfood deve mostrar `caixa_moeda_estrangeira >= R$ 25.000` no card.

## Follow-ups

1. **Reclassificar ME no `baseline_normalizer`** (alternativa b acima): separar items ME do `investimentos_consolidados` para um campo dedicado. Elimina o trade-off de double-count permanentemente. Lane dedicada — exige cuidado com consumers.
2. **Telemetria** para detectar cenários de double-count em produção (logger estruturado quando `fonte_investimentos="irpf"` + `caixa_detalhes` contém `moeda_estrangeira_irpf`).
3. **Refinar heurística de keyword** se telemetria mostrar falsos positivos (ex.: "FUNDO RENDIMENTO DOLAR HEDGE" — fundo BR com nome ambíguo).
