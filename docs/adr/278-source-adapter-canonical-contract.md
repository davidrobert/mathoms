---
id: ADR-278
type: adr
title: "SourceAdapter + SourceRef + data_source + contrato canônico E2 v3"
status: Decidido
phase: "A23 · F0"
date: "2026-06-02"
relates_to:
  - "[[ADR-255]]"
  - "[[ADR-212]]"
  - "[[ADR-090]]"
  - "[[ADR-146]]"
  - "[[ADR-226]]"
  - "[[ADR-241]]"
  - "[[ADR-271]]"
supersedes: []
superseded_by: []
aliases: ["ADR 278", "SourceAdapter", "SourceRef"]
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/data-lineage
  - area/persistence
---

# ADR-278 — SourceAdapter + SourceRef + data_source + contrato canônico E2 v3

**Status:** Decidido (A23 · F0) • **Data:** 2026-06-02 • **Relaciona** [[ADR-255]], [[ADR-212]], [[ADR-090]], [[ADR-146]], [[ADR-226]], [[ADR-241]], [[ADR-271]].

> Camada A do plano [[PLAN-data-lineage]]. Gate F0 — **resolve B1, B3, B4, B5, B7**.
> Decisão fechada; lanes de implementação (F1+) conformam, não reabrem.

**Contexto:** o pipeline já é hexagonal na fonte (`N adapters → artefato E2 → `reconcile_transactions` agnóstico`), mas o contrato não está nomeado como porta nem isolado de extração. Integrar Open Finance / agregador exige uma porta `SourceAdapter` e uma referência de fonte (`SourceRef`) que generalize o `document_id` (hoje único elo de origem, `backend/app/models/pipeline_artifact.py`, FK `ON DELETE SET NULL`) — folha estável do lineage ([[ADR-279]]). A chave natural K4 (`compute_transaction_hash`, `pipeline/domain/services/_tx_identity.py:100`) é source-independent, mas é subproduto interno do dedup E3 e tem dois defeitos para virar contrato: usa `cents_int(abs(valor))` **sem moeda nem sinal** (`:115`; sinal só em `kind`) e ingere `float` (viola [[ADR-090]] no wire).

**Decisão:**
- **Porta:** `SourceAdapter` Protocol + `SourceRef` discriminated union (`{kind:"document", document_id}` | `{kind:"feed", provider, account_id, sync_id}`) em `pipeline/domain/ports/source.py`. Parsers `scripts/e2/banks/*` são os primeiros adapters; feed Open Finance é adapter futuro em `backend/app/services/` (fala HTTP — boundary proíbe em `pipeline/`).
- **Contrato canônico = artefato E2 endurecido** (`e2_extract.schema.json` v3, **não** `CanonicalLedgerRecord` paralelo): `natural_key {hash, hash_version}` obrigatório, `amount` decimal string ([[ADR-090]]), `source_ref`, `direction` (`debit`/`credit`). `additionalProperties:true` preserva compat. Posição de investimento = 2º contrato canônico (chave `tipo|instituicao|descricao_norm`, [[ADR-271]]).
- **`data_source`** (folha generalizada, **sem FK polimórfica**): `(id, workspace_id FK CASCADE, kind, institution_code, external_account_ref, display_name, created_at)`, unique `(workspace_id, kind, institution_code, external_account_ref)`. `pipeline_artifacts.data_source_id` nullable FK **`ON DELETE SET NULL`**; `document_id` permanece (folha mais fina).
- **B1 (tie-break):** `SourcePrecedencePolicy` reusa só a **hierarquia de tier** de `pick_winner` (`source_tier.py:134`) e substitui o desempate `extracted_at` (`:147`, não-determinístico) por **`(tier, kind-priority, alfabético por artifact_key)`** — alinhado ao survivor estável da [[ADR-255]]. Formaliza a emenda da [[ADR-146]]; muda o tie-break atual do reconciler → rebaseline E3 esperado.
- **B3 (K4 cross-source):** `compute_transaction_hash` ganha `moeda` + `direction` e passa a ingerir `Decimal`/cents (não float). `natural_key.hash_version`: `1` = legado atual; `2` = com moeda+direction. Sem isso, entrada R$100 colide com saída R$100 e BRL com USD ao fundir feed+PDF.
- **B4 (migração K4):** `natural_key` entra **2-passos** (`nullable` → `obrigatório`). O inventário dos produtores E2 (`store.write("E2"...)`; fatura/informe podem faltar `titular`/`tipo_conta`) **roda em F1** (`dl-f1-natural-key`) — F0 fixa a *estratégia*, não executa o inventário.
- **B5 (amount decimal):** `amount` decimal **ao lado** de `valor` na janela de migração; inventário de leitores de `transacoes[].valor` (E3 reconciler, `cents_int`, dedup) em F1; gate `Decimal(amount)==Decimal(str(valor))` enquanto ambos coexistem; só então deprecar `valor`. Nunca num passo.
- **B7 (saldo-continuity):** `SaldoContinuityValidator` (`reconciliation_validators.py:86`, statement-level, agrupa por `_account_key`) filtra por `SourceRef.kind` — só a série autoritativa `document` (extrato oficial) vira saldo-âncora; o feed reconcilia valor/rótulo da linha via `SourcePrecedencePolicy`, **não** entra na série de continuidade.

**Consequências:**
- ✅ Fonte plugável por ~1 migração + endurecimento de contrato, sem stage novo, sem refactor de E3. Feed Open Finance amanhã = "implemente um adapter que emite o contrato".
- ✅ Lineage ganha a folha generalizada (`SourceRef`/`data_source_id`) no mesmo PR — migra o schema de origem uma vez.
- ⚠️ Mudança de tie-break (B1) altera output do reconciler em empates → **rebaseline E3 isolado** (G-c) com manifesto justificado.
- ⚠️ Migração online: `data_source` + `data_source_id` via `ADD COLUMN NULL`; `CREATE INDEX CONCURRENTLY` **fora de transação Alembic** (`autocommit_block`/`postgresql_concurrently=True`) + asserção em `test_alembic_guardrails`; backfill idempotente `kind='document'` para artefatos E2 com `document_id`. Runbook G-e em F1.
- ⚠️ `valor`→`amount` é migração de 2 fases ([[ADR-090]]); drop de `valor` só após cutover de leitores confirmado.
