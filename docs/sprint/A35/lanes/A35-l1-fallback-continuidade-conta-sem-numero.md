---
id: A35.l1
type: lane
title: "fallback da cadeia de continuidade quando número de conta não extrai + sinal auditável (ADR-310 emenda)"
sprint: A35
plan: null
status: open
ship_pr: null
ship_date: null
priority: P1
branch_slug: a35-l1-continuity-accountless-fallback
adrs: ["[[ADR-310]]"]
depends_on: []
parallel_with: []
tags:
  - type/lane
  - sprint/a35
  - status/open
  - priority/p1
  - area/pipeline
  - area/domain
---

# A35.l1 — `continuity-accountless-fallback` (o gap genuíno volta a aparecer)

## Problema

`ContinuityAccountKey` (`pipeline/domain/services/reconciliation_validators.py`)
inclui `account_number_norm` desde a A32.l4 ([[ADR-310]]). Quando um
extrato não tem número de conta extraído (`account_number_norm is None`),
ele vira "conta diferente" dos extratos numerados da MESMA conta → as
cadeias se separam → o `SaldoContinuityValidator`/`TemporalGapDetector`
nunca comparam os dois lados → gap de continuidade **genuíno** deixa de
ser sinalizado. Caso real confirmado pelo owner (issue
[#860](https://github.com/davidrobert/mathoms/issues/860)): conta rico
com buraco abr–jun/2026 invisível (extrato `95b3d36e` sem número,
`da48e34d` com número — mesma conta). Ver [[MOC-sprint-a35]] §Diagnóstico.

## Escopo (decisão do co-design 2026-07-08 — operacionalize, não redecida)

1. **Emenda datada na [[ADR-310]]** (não ADR nova). `amended_at:
   ["2026-07-08"]` no frontmatter + blockquote de sinal no topo (padrão
   ADR-027) + seção `## Emenda 2026-07-08 — coalescência de cadeia por
   número de conta ausente`. A emenda declara: (i) a escada de resolução
   (Tier 1 resolver, Tier 2 intra-run `count==1`); (ii) que o fallback é
   **interino** e será absorvido pelo `SourceRef.kind` ([[ADR-278]] §B7)
   junto com a chave; (iii) a aposta assimétrica (falso negativo de gap >
   falso positivo de fusão sinalizada). Docs-only → parte do PR de impl.
2. **Helper compartilhado `_partition_chains`** em
   `reconciliation_validators.py`, consumido por `SaldoContinuityValidator`
   E `TemporalGapDetector` (mata a duplicação atual de particionamento).
   `_chain_key` permanece **puro** por-statement. `AccountGrouper` **não
   muda**.
3. **Coalescência (só `not is_fatura`):**
   - **Tier 1** — se um `AccountResolver` (ADR-226) estiver disponível no
     contexto: statement sem número → grau `fallback_bank` herda a conta
     única cadastrada; `ambiguous` (2+ cadastradas) isola. Se o cadastro
     não estiver acessível na stage sem encanamento novo, **declare a
     fronteira** e entregue o Tier 2 (o dogfood não tem cadastro — Tier 1
     não é exercível pelo caso real; não construir encanamento
     especulativo).
   - **Tier 2 (fecha o #860)** — dentro do grupo `(banco, membro, tipo,
     moeda)`, se `|{account_number_norm distintos não-nulos}| == 1`, os
     statements com `account_number_norm is None` coalescem na cadeia
     numerada (sobrevivente canônico fixo = a chave numerada). `>= 2`
     números distintos → **não** coalesce (isola). Todos `None` → agrupam
     entre si (comportamento atual preservado).
4. **Sinal auditável obrigatório** — toda coalescência emite
   `SaldoChainMemberInferred` (frozen dataclass com `.format()`, padrão
   `FaturaExcludedFromSaldoChain`, ADR-097 D1) exposto no
   `ReconciliationStoreResult`/retorno do detector — **sem número de
   conta cru** (dado sensível; `describe()` já omite). Nunca coalesce em
   silêncio.
5. **Determinismo (ADR-111):** predicado set-based + sobrevivente
   canônico fixo (nunca `next(iter(...))` sobre dict sem ordenar);
   resolução computada por grupo antes do `_sort_key`, função pura, sem
   global mutável.
6. **Rebaseline via `dev/golden_diff.py` + manifesto** (ADR-310 §5, padrão
   A23.l2) se algum golden de continuidade mudar contagem; cada delta
   justificado item-a-item.

## Critérios de aceite

1. Emenda ADR-310 no PR (frontmatter `amended_at` + blockquote + seção
   datada); `_generated/` regenerado.
2. **Detecção restaurada (KR1):** teste de regressão do caso rico —
   grupo com 1 número + 1 statement sem número → coalescem, gap
   abr–jun/2026 re-sinalizado (fixture sintética PII-zero em
   `tests/fixtures/pipeline_golden/dogfood/`).
3. **Não-fusão / anti-regressão l4 (KR2):** (a) grupo com 2 números
   distintos + 1 sem número → não coalesce; (b) poupança sem número
   **nunca** casa com CC sem número (o `account_type` canônico segura);
   (c) nenhum dos 39 falsos positivos F1–F4 da A32.l7 reaparece.
4. **Sinal sempre (KR3):** toda coalescência emite
   `SaldoChainMemberInferred`; teste negativo garante que statement sem
   número nunca some da observabilidade (espelha o teste negativo da l4
   para `FaturaExcludedFromSaldoChain`).
5. **Determinismo:** mesma entrada em duas ordens de inserção → mesma
   `ContinuityAccountKey` sobrevivente + mesmos warnings;
   `backend/tests/integration/test_multi_worker_concurrency.py` verde.
6. `pytest tests -q` verde; `dev/check_pipeline_boundaries.py` verde
   (helper em `pipeline/`, zero import de framework);
   `tests/test_e5_conservation_invariants.py` verde. PR mergeado em `main`
   com CI verde.
7. **Gate (medição real):** re-run do workspace dogfood mostra o gap
   genuíno do rico de volta com selo `documento_faltando` e **nada** dos
   39 falsos de volta (before/after no §Gate desta sprint).

## Arquivos load-bearing

| Arquivo | Papel |
|---|---|
| `pipeline/domain/services/reconciliation_validators.py` | `_chain_key` (126), `_partition` (297), `TemporalGapDetector.detect` (369), `FaturaExcludedFromSaldoChain` (192) como padrão de sinal |
| `pipeline/domain/services/account_resolver.py` | `AccountResolver.resolve` (grau `fallback_bank`/`ambiguous`) — Tier 1 |
| `pipeline/domain/services/account_grouper.py` | `AccountKey` (54), `key_for_statement` (196) — **não tocar** (escopo de dedup) |
| `pipeline/domain/models/document.py:158` | `account_number_norm` — origem do campo que falha silencioso |
| `tests/unit/pipeline/test_saldo_continuity_account_key.py` | Suite a estender |
| `dev/golden_diff.py` | Manifesto de rebaseline (ADR-310 §5) |
| `docs/adr/310-chave-canonica-conta-continuidade-saldo.md` | Alvo da emenda |
