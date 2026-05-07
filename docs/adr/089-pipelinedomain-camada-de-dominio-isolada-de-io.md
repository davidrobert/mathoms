---
id: ADR-089
type: adr
title: "pipeline/domain/: camada de domínio isolada de I/O"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 089"]
tags:
  - type/adr
  - status/decidido
size_lines: 50
---

# ADR-089 — pipeline/domain/: camada de domínio isolada de I/O

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 5

**Contexto:** Transações, extratos, patrimônio viviam como `dict` genéricos.
Mudar a estrutura de uma transação exigia grep em múltiplos scripts. Lógica
de reconciliação, categorização e análise estava acoplada a I/O de disco —
testar "transações de mesmo valor em ±3 dias são duplicatas" exigia montar
fixtures de arquivo.

**Decisão:** Nova camada `pipeline/domain/`:

```
pipeline/domain/
  models/
    transaction.py     Money, Transaction
    document.py        BankStatement, Investment, InvestmentStatement, BaselinePatrimonial
  services/
    reconciliation_service.py  ReconciliationService(ReconciliationConfig)
    categorization_service.py  CategorizationService(CategorizationRules)
    calculators.py             CashFlowAggregator, PatrimonioCalculator,
                               EmergencyReserveCalculator, FinancialScoreCalculator
```

- **Value objects** (`Money`, `Transaction`, `Investment`, `Baseline`) são
  frozen dataclasses — "modificar" produz novo objeto via
  `dataclasses.replace`. `BankStatement.transactions` é `list` mutável
  restrito ao pipeline de reconciliação (invariante documentado).
- **Services** são **puros** — sem I/O de disco, sem globals. Recebem
  `(config_value_object, input_value_objects)`, retornam output.
- Services NÃO recebem `StageConfig` inteiro (R9 / Interface Segregation):
  `ReconciliationService(ReconciliationConfig)`,
  `CategorizationService(CategorizationRules)`.
- Services são testáveis com `InMemoryArtifactStore` + fixtures de 3 linhas.

**Consequências:**
- ✅ Lógica de domínio testável em isolamento — fixtures não são arquivos.
- ✅ Contrato tipado expõe o modelo mental do domínio financeiro.
- ✅ Extensões futuras (reconciliação multi-moeda, novo tipo de ativo)
  ficam localizadas no domínio.
- ⚠️ Scripts legados (Caminho A) continuam trabalhando com `dict` até migração.

**Arquivos:** `pipeline/domain/**`,
`tests/unit/pipeline/test_domain_money.py`,
`tests/unit/pipeline/test_domain_transaction_document.py`,
`tests/unit/pipeline/test_reconciliation_service.py`,
`tests/unit/pipeline/test_categorization_service.py`,
`tests/unit/pipeline/test_calculators.py`.
