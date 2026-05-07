---
id: ADR-097
type: adr
title: "Extract-then-refactor: estratégia de decomposição de `e3_reconcile.py`"
status: Decidido
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 097"]
tags:
  - type/adr
  - status/decidido
size_lines: 85
---

# ADR-097 — Extract-then-refactor: estratégia de decomposição de `e3_reconcile.py`

**Status:** Decidido • **Data:** 2026-04-19 • **Plano:** Fase 6 · Sessão A1 · ADR-089 (domain layer)

**Contexto:** `scripts/e3_reconcile.py` tem 1193 linhas com 30+ globals, lógica
bank-specific (faturas, CDBs), validações (saldo, gap temporal, baseline IRPF)
e orquestração misturadas. A estratégia "big-bang rewrite" — reescrever o
`main()` inteiro consumindo `ReconciliationService` — tem risco alto:

1. Bugs sutis em validações bank-specific só aparecem em produção.
2. Golden fixture cobre output final, não cada validator isoladamente.
3. Um sprint inteiro bloqueado sem entregar código testável em memória.

A alternativa — extrair validators/helpers **primeiro**, deixando o `main()`
legado intacto — permite progresso incremental com zero risco de regressão.

**Decisão:** Adotar **extract-then-refactor** como padrão para decomposição de
scripts legados grandes (E3, E4, E5). Ordem de trabalho:

1. **Extract**: mover cada responsabilidade para um domain service puro em
   `pipeline/domain/{models,services}/`, com:
   - Value objects tipados para config (ISP — R9) e warnings estruturados.
   - Testes unitários exaustivos com `InMemoryArtifactStore` (nenhuma fixture de arquivo).
   - Zero mudança em `scripts/e3_reconcile.py::main()` — script legado continua
     rodando via Caminho A (bridge).
2. **Compose**: `E3ReconcilerAdapter` (ou análogo) integra os services extraídos
   — testado end-to-end contra fixtures sintéticas.
3. **Refactor**: quando todos os blocos estiverem extraídos e testados, o
   `main_with_store(config, store)` substitui o legado. Golden fixture valida
   paridade. `MaterializationBridge` desliga para o stage.

**Sessão A1 (2026-04-19)** entregou Extract para E3 — 7 artefatos novos, **92
testes**, zero linha alterada em `e3_reconcile.py::main()`:

| Arquivo | Responsabilidade | Extraído de | Testes |
|---------|------------------|-------------|--------|
| `pipeline/domain/models/bank.py` | `BankCanonicalizer` + `canonicalize_bank()` — índice explícito `normalized_form → canonical_code`, strip acento/espaço/`/&` | `_BANCO_DISPLAY_TO_CANONICAL` dict-global em `_init_config` | 21 |
| `pipeline/domain/services/reconciliation_validators.py` | `SaldoContinuityValidator` (1ª metade de `validate_saldo_and_gaps`) + `TemporalGapDetector` (2ª metade); cada um com `*Config` dataclass ISP; retorna `SaldoGapWarning`/`TemporalGapWarning` estruturados | `validate_saldo_and_gaps()` | 32 |
| `pipeline/domain/services/baseline_validator.py` | `BaselineValidator` — compara `closing_balance` de `BankStatement` contra saldos IRPF 31/12 via `BankCanonicalizer`; value object `BaselineAccountSaldo` com factory `from_baseline_dict` (aceita `members`/`membros`, dict ou list) | `validate_against_baseline()` | 39 |
| `pipeline/domain/services/account_grouper.py` | `AccountGrouper` — skip rules + chave de conta canônica com `account_type_equivalences` | `group_by_account()` + skip logic | — |
| `pipeline/domain/services/statement_preprocessor.py` | `StatementPeriodNormalizer` (sintetiza período para faturas sem `periodo`) + `AnachronicTransactionDropper` (>180d antes do início) | Fatura period adjustment + anachronic guard | — |
| `pipeline/domain/services/e3_reconciler_adapter.py` (estendido) | Integra todos os services acima; `ReconciliationStoreResult` com warnings tipados + acesso dict-like retro-compat | — | — |

**Princípios fixados por esta ADR:**

- **D1. Warnings como dataclasses, não strings.** `SaldoGapWarning(account_key, expected, actual, diff)`
  tem `.format()` para render. Strings fazem parsing reverso em testes.
- **D2. Services não recebem `Path` nem `dict`.** Recebem `list[BankStatement]`
  ou value objects. Conversão `dict → BankStatement` é responsabilidade do
  adapter (`E3ReconcilerAdapter.load_bank_statements_with_warnings`).
- **D3. Config por service, não `StageConfig` inteiro.** Cada validator tem
  seu `*Config` dataclass frozen (ISP). Fixture de teste é uma linha.
- **D4. Zero mudança no script legado durante a fase Extract.** O `main()`
  segue intacto; golden fixture valida na fase Refactor.
- **D5. `E3ReconcilerAdapter` é mutável por injeção.** Todos os collaborators
  têm default seguro (`or default_factory()`), permitindo teste com subset.

**Consequências:**
- ✅ Sessão A1 entregou +92 testes em uma session sem risco de regressão em
  produção (719 pipeline passando, 0 regressão).
- ✅ Padrão reusável para Fases 7 (E4) e 8 (E5).
- ✅ Cada validator tem cobertura granular — bugs aparecem em unit test, não
  em golden fixture rodando 5 minutos.
- ⚠️ Existe uma janela onde services novos **coexistem** com lógica legada no
  script — o adapter é o único consumidor. Durante a janela, mudanças em
  ambos os lados exigem coordenação.
- ❌ Fase Refactor (substituir `main()` legado) ainda não foi feita — esta
  ADR cobre apenas a fase Extract. O golden fixture e o `main_with_store`
  ficam para sessão subsequente.

**Ordem de execução restante para completar Fase 6 (Caminho B):**
1. Implementar `reconcile_account()` equivalente em
   `E3ReconcilerAdapter.reconcile_via_store()` — hoje faz merge simples;
   precisa incorporar lógica fatura-specific legada.
2. Extrair `generate_output_filename()` para `BankCanonicalizer.output_filename(statement)`.
3. Capturar golden fixture do E3 legado em `tests/pipeline/goldens/e3/`.
4. Implementar `main_with_store(config, store)` em `scripts/e3_reconcile.py`.
5. Atualizar `pipeline/stages/e3.py` para não usar `run_legacy_with_bridge_if_db`.
6. Validar: golden fixture passa; zero regressão em 719+ testes.

**Artefatos:** `pipeline/domain/models/bank.py`,
`pipeline/domain/services/{reconciliation_validators,baseline_validator,account_grouper,statement_preprocessor,e3_reconciler_adapter}.py`,
`tests/unit/pipeline/test_{bank_canonicalizer,reconciliation_validators,baseline_validator,account_grouper,statement_preprocessor,e3_reconciler_adapter}.py`.
