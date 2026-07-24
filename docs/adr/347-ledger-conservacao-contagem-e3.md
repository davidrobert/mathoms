---
id: ADR-347
type: adr
title: "Ledger de conservação de contagem de transações no E3 (declarar toda remoção/exclusão)"
status: Proposto
phase: A39
date: "2026-07-24"
relates_to:
  - "[[ADR-342]]"
  - "[[ADR-090]]"
  - "[[ADR-097]]"
  - "[[ADR-111]]"
  - "[[ADR-302]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/dados
---

# ADR-347 — Ledger de conservação de contagem de tx no E3

**Status:** Proposto (A39) · **Data:** 2026-07-24 · **Lane:** Ledger Integrity (Onda A, P1)

> **Proposto** — abre o contrato de conservação de **contagem** de transações no E3
> antes do PR de implementação (política P0/P1). Origem: certificação
> `ledger-certify` ([[ADR-302]]) — [[LEDGER-CERTIFY-active]] §r2 LC02. Estende a
> [[ADR-342]] (conservação de **saldo** no E2) para a dimensão de **contagem** no
> E3. **Revisado por painel** (data-engineer + senior-cto): a partição inicial era
> incompleta (só remoções tx-level pós-load) e o denominador contraditório
> (anachronic dupla-subtraído). Este documento incorpora as correções bloqueantes.
> Flippa para `Decidido` no merge do PR3 (flip HARD). Tamanho >150 linhas
> justificado: contrato multi-canal com âncora de medição + prova de exaustividade.

## Contexto

A certificação re-derivou E3 in-process no ws de dogfood: **6224** tx no E2 →
**5724** survivors + **142** `transacoes_duplicadas_removidas` declaradas ⇒ **356 tx
removidas SEM declaração** (6224 − 2 anachronic − 5724 − 142 = 356). O número que a
skill reportou como "214" estava **errado** (dupla-subtração) — a aritmética correta
é 356, e reproduzi-la é pré-condição do flip HARD.

A remoção acontece por **múltiplos canais**, verificados no código, hoje
não-declarados — dois deles são **perda de dado real, não só de auditabilidade**:

**Tx-level (removem tx dentro de um statement que carregou):**
- **`undated_drop`** — `from_e2_dict` dropa tx sem `data` em silêncio
  ([`document.py:130-131`](../../pipeline/domain/models/document.py) `else: continue`).
  **Perda real.**
- **`anachronic`** — dropper de tx anacrônica; já emite `AnachronicTransactionWarning`
  com `dropped_count` (consumível).
- **`intra_statement_dedup`** — `_dedup` por statement
  ([`reconciliation_service.py:145-155`](../../pipeline/domain/services/reconciliation_service.py))
  retorna a lista filtrada **sem reportar a contagem**.
- **`cross_file_dedup`** — merge cross-file
  ([`e3_reconciler_adapter.py:388-402`](../../pipeline/domain/services/e3_reconciler_adapter.py))
  só declara com `len(stmts)>1`.

**Statement-level (o extrato inteiro sai; só `outcome.skipped += 1`, que conta
artefato, não tx — não produz artefato E3):**
- **`undated_statement_drop`** — data string não-ISO ⇒ `from_e2_dict` **levanta** ⇒
  `except Exception` bare ([`e3_reconciler_adapter.py:289-292`](../../pipeline/domain/services/e3_reconciler_adapter.py))
  dropa o statement inteiro. **Perda real, silenciosa.**
- **`period_skip`** — `StatementPeriodNormalizer.skip` (`:270-272`).
- **`empty_institution`** — `EmptyInstitutionWarning` (`:294-299`), declarado via warning.
- **`non_tx_type`** — `grouper.should_skip` (`:261-263`; IRPF/posições — classe
  explícita "não-tx", legítima).
- **`llm_stub`** — `requires_llm_fallback` (`:252-257`): as tx voltam pelo artefato
  full do `extract_with_llm` ⇒ **armadilha de dupla-contagem no denominador**, não
  perda; **excluído** do total.

`is_duplicate` (`:100-110`) é conservador (mesma moeda, |Δvalor|≤tol, |Δdata|≤tol,
**descrição idêntica**) ⇒ perda em massa improvável; risco = cauda longa (dois
lançamentos legítimos idênticos ≤3d). **Consequência de produto** (financial-planner):
se uma remoção for tx única, despesa/receita subestima → **taxa de poupança inflada
+ reserva subdimensionada** (não auto-corrige, verificável pelo cliente). Por isso
**bloqueia beta fechado até as remoções serem auditáveis** — de-block é
auditabilidade, não dedup perfeito.

## Decisão

Ledger de conservação de **contagem**, forward-only, WARN-first, int cents tol-zero
([[ADR-090]]). Instância do meta-princípio **anti-silêncio de transformação**: *toda
transformação que remove/altera contagem ou valor declara o delta estruturalmente*
(a [[ADR-342]] é a instância de **extração**/saldo no E2; esta é a de **dedup/drop**
no E3; E4/E5 herdam o padrão em vez de re-derivar).

1. **Âncora de medição única.** `tx_carregadas` = `len(transacoes)` **logo após a
   normalização de período, ANTES do `undated_drop`/`from_e2_dict` e ANTES do
   anachronic dropper**. Todos os canais ficam **abaixo** dessa âncora ⇒ nenhum
   dupla-subtraído. `tx_carregadas` é **serializado no artefato E3** (self-certifying;
   dispensa join E2+E3 no read-path).
2. **`_dedup` context-free.** `_dedup` retorna `(kept, count, valor_cents)` — **não**
   decide o `canal`. O **caller** tagueia: `_reconcile_group` → `intra_statement_dedup`;
   o merge do adapter (`e3_reconciler_adapter.py:401`, re-wire) → `cross_file_dedup`.
3. **`DedupRemoval` carrega `proven: bool`** (source-ref/`source_document` idêntico
   no par removido), **computado no momento do dedup** ([[ADR-097]] D1). Remoção
   **não-provada** → `ReviewReason`/`needs_review`. **Measure-then-emit:** no PR2
   conta-se a fração de não-provadas por run; só emite `needs_review` de fato após o
   dogfood provar a taxa de falso-positivo (disciplina WARN-first da [[ADR-342]]).
4. **Partição por artefato E3 (tx-level):** `remocoes = {undated_drop, anachronic,
   intra_statement_dedup, cross_file_dedup}`, cada uma `{count, valor_cents}`.
   `transacoes_duplicadas_removidas` **preservado** = soma das duas partições de dedup.
5. **Ledger `exclusions` a nível de run (statement-level):** os canais que não
   produzem artefato E3 (`undated_statement_drop`, `period_skip`, `empty_institution`,
   `non_tx_type`) são contados (`len(data["transacoes"])` em cada skip-site — hoje só
   `outcome.skipped += 1`) e projetados em `outcome.review_reasons` (que **já fluem**),
   **sem tabela nova** ([[ADR-111]]). `llm_stub` **excluído** do denominador (dupla-contagem).
6. **Igualdades (int cents, tol-zero):**
   - Por artefato: `tx_carregadas == transacoes_total + Σ remocoes[*].count`.
   - Por workspace (agregado **live-only**, respeitando o invariante de read-path
     [[ADR-342]] §Dec-3 — nunca soma artefato superseded/stale): `Σ_E2_tx ==
     Σ survivors + Σ remocoes_tx_level + Σ exclusions_statement_level` (excl. `llm_stub`).
   - Valor espelha em cents.
7. **Schema aditivo-opcional → HARD.** `remocoes` opcional/nullable no PR1; `required`
   no flip. `SCHEMA_BY_STAGE` ([`db_artifact_store.py:158-159`](../../backend/app/services/storage/db_artifact_store.py))
   **já mapeia** `E3`/`reconcile_transactions` (write não é passthrough — verificado).

## Faseamento (contrato — estado intermediário pior-que-hoje é perda silenciosa)

- **PR1** — `tx_carregadas` na âncora + `DedupRemoval{proven}` + `_dedup` retorna
  contagem + `ReconciliationStoreResult.removals` + contagem nos skip-sites
  statement-level + `remocoes`/`tx_carregadas` **aditivo-opcional** no schema. Sem
  serializar exclusions / sem HARD.
- **PR2** — serializar `remocoes` por grupo + `exclusions` em `review_reasons` +
  telemetria de conservação (namespace `mathoms.*`, **só contagens/pct, zero PII**,
  espelha a emenda K4 da [[ADR-287]]) + `needs_review` measure-then-emit. **WARN** se
  a igualdade não fecha.
- **PR3** — flip **HARD tol-zero** sobre o **resíduo** `tx_carregadas − transacoes_total
  − Σ canais_declarados`. Gate do flip = **teste de completude** (abaixo) verde **e**
  igualdade fecha por **≥1 run/sprint consecutivo com 0 resíduo** no ws de dogfood.
  `remocoes` vira `required`. **Sem piso de materialidade** (mascararia o P0).

## Invariantes testáveis (a implementação DEVE cravar)

1. **Igualdade de contagem por artefato:** `tx_carregadas == transacoes_total +
   Σ remocoes.count` (tol-zero).
2. **Igualdade de workspace:** `Σ_E2 == survivors + Σremoções_tx + Σexclusions`
   (excl. `llm_stub`) — reproduz o 356 da certificação.
3. **Teste de exaustividade (gate do HARD):** fixture que **injeta cada canal**
   (undated tx, bad-date statement, period-skip, empty-inst, non-tx, intra-dedup,
   cross-dedup, anachronic) e asserta **resíduo == 0**. Depois disso, resíduo ≠ 0 **é**
   um canal novo não-instrumentado = bug real ⇒ tol-zero correto.
4. **Não-degradação:** diff dogfood de `despesas`/`receitas`/`patrimonio_liquido`
   pré/pós = **zero**; `tests/test_e3_golden_execution.py` verde.
5. **`proven`/`needs_review`:** remoção sem source-ref idêntico ⇒ `proven=false` ⇒
   `ReviewReason`; idempotência 2×==1×.
6. **Agregado live-only:** fixture com artefato E3 **superseded** + live da mesma key
   ⇒ agregado NÃO soma o superseded (modo de falha da [[ADR-342]]).
7. **Compat:** `transacoes_duplicadas_removidas == intra_statement_dedup +
   cross_file_dedup` (count e valor).

## Consequências

- Conservação de contagem passa a ser **provável a partir do artefato** (tx-level) +
  **auditável por run** (statement-level via `review_reasons`); a `ledger-certify`
  sobe de `coberto-sem-verificação` para `conservado` quando fecha; resíduo
  não-explicado vira P0 acionável.
- Expõe **dois bugs de perda real** já latentes (`undated_drop` tx-level +
  `undated_statement_drop` via `except` bare) — que hoje somem sem sinal. Corrigi-los
  (ou convertê-los em `needs_review`) entra no escopo do PR2.
- Custo: campos novos por artefato E3 (pequenos) + contagem nos skip-sites. Sem
  backfill; artefatos antigos legíveis (campos opcionais).

## Alternativas rejeitadas

- **Contar só o merge (status quo):** deixa intra-statement + os 2 drops silenciosos
  de data — exatamente o gap medido.
- **Piso de materialidade no gate HARD:** mascararia o P0 (uma tx única removida = perda
  real). O gate certo é exaustividade (invariante 3) + tol-zero sobre o resíduo.
- **Medir `carregadas` pós-anachronic:** dupla-subtrai o canal anachronic ⇒ igualdade
  nunca fecha. Âncora tem de ser pré-drop.
- **Tabela de ledger no DB:** agregado tx-level é derivável do read-path (live-only) e
  o statement-level cabe em `review_reasons` — não criar estado novo ([[ADR-111]]).
- **Dropar tx ambígua sem review:** viola anti-silêncio ([[ADR-342]]); cauda longa
  (lançamentos legítimos idênticos) exige `needs_review`.
