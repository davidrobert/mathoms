---
id: A23.l3
type: lane
title: "Data Lineage F1 — K4 natural_key como campo de contrato E2 (B3/B4)"
sprint: A23
plan: PLAN-data-lineage
status: shipped
priority: P0
branch_slug: a23-l3-natural-key
adrs:
  - "[[ADR-278]]"
depends_on:
  - "[[A23.l1]]"
  - "[[A23.l2]]"
parallel_with: []
tags:
  - type/lane
  - sprint/a23
  - status/shipped
  - priority/p0
  - area/data-lineage
  - area/pipeline
---

# A23.l3 — K4 `natural_key` como campo de contrato E2 (B3/B4)

> **Plano:** [[PLAN-data-lineage]] · Onda 1 · **abre só após gate F0 ([[A23.l1]])
> e o substrato de golden ([[A23.l2]])**. Conforma à [[ADR-278]] (B3/B4); não reabre
> a decisão. Usa `dev/golden_diff.py` (entregue em [[A23.l2]]) para a paridade K4.

## Objetivo

Promover a chave natural K4 (`compute_transaction_hash`, hoje subproduto interno do
dedup E3) a **campo de contrato do artefato E2**, corrigindo dois defeitos que a
[[ADR-278]] travou:

- **B3** — o hash usa `cents_int(abs(valor))` **sem `moeda` nem `direction`**
  (`_tx_identity.py:115`; sinal só vive em `kind`/`tipo`) e **ingere `float`**
  (viola [[ADR-090]] no wire). Resultado: entrada R$100 colide com saída R$100, e
  BRL colide com USD ao fundir feed+PDF — o gênero do bug R$ 811k.
- **B4** — `natural_key` não pode virar obrigatório de uma vez se nem todo produtor
  E2 emite K4 (fatura/informe podem faltar `titular`/`tipo_conta`). Entra em
  **2 passos** (`nullable` → `obrigatório`); este lane fecha o passo 1 (aditivo) +
  o inventário que diz **onde** o passo 2 é seguro.

A migração de DDL/coluna e o runbook PITR (G-e) ficam em lane separada
(`dl-f1-migration-runbook`); o campo `amount` decimal (B5) em `dl-f1-amount-decimal`.
Este lane toca **só o contrato E2 (schema + produtores) e o hash**.

## Co-design (decisões — `data-engineer` + `senior-cto`, 2026-06-08)

Conforma à [[ADR-278]]; estas são decisões de **implementação** da lane, validadas
pelos especialistas (não reabrem ADR):

- **D1 — API:** `compute_natural_key(inputs: HashInputs) -> NaturalKey` (frozen
  `{hash, hash_version}`) despacha para núcleos privados puros `_hash_v1` / `_hash_v2`.
  `_hash_v1` é o **código atual congelado** (`abs`+`cents_int` float-round **inclusive
  o bug**) — mudá-lo invalidaria hashes já gravados em `pipeline_artifacts`.
  `compute_transaction_hash` vira **shim deprecado** → `_hash_v1` (vive durante a
  janela nullable; removido ao fim de B4). _Rejeitado:_ evoluir
  `compute_transaction_hash` com params opcionais (vira `None`-governed two-behavior).
- **D2 — `direction` = `tipo` normalizado, NÃO o sinal de `amount`.** `_normalize_tipo`
  (`transaction_classifier.py:92-110`) já reconcilia sinal↔tipo e **inverte em fatura**
  (`valor<0 → credito`, estorno). Derivar do sinal cru quebraria dedup de fatura.
  `credito→credit`, `debito→debit`; `valor==0 → credit` (convenção fixa documentada);
  `tipo` vence em divergência. A regra de derivação vira helper **compartilhado** para
  emit e recompute usarem a MESMA função.
- **D3 — paridade por construção:** `HashInputs` frozen é o **único** argumento de
  `compute_natural_key`; dois adapters finos (`inputs_from_document_transaction` para
  emit, `inputs_from_classified_tx` para recompute) só **mapeiam nomes**
  (`account_type`↔`tipo_conta`, `Money`↔`valor`, `member_key`↔`titular`). Normalização
  e quantização vivem **só dentro** do hasher. Elimina a classe "dedup furou em prod
  e ninguém sabe por quê".
- **D4 — F1 emite + mede, NÃO consome.** E4 continua recomputando v1 enquanto
  `natural_key` é nullable. Consumir o v2 emitido agora mudaria o dedup (v2≠v1) →
  goldens vermelhos. O flip de consumo/versão é coordenado no **passo 2** (fora desta
  lane).
- **D5 — escopo de produtores:** só stages que validam contra `e2_extract.schema.json`
  (`SCHEMA_BY_STAGE`, `db_artifact_store.py:81`). **Informe/CRLV/comprovante ficam
  fora de B4** (schema próprio: `informe_aluguel`, `informe_base`, `crlv`).
- **D6 — terceiro hash (dívida cross-stack):** `backend/app/services/transaction_service.py:17`
  (`generate_transaction_hash`) é incompatível (SHA full, sem cents, sem `tipo_conta`)
  e alimenta `TransactionOverride` (UK) + Categorization Learning Loop. **Fora do
  escopo F1**; registrar linha de backlog — sem migrá-lo, o passo 2 quebra
  sticky-override silenciosamente (cf. incidente histórico membro identity por CPF).

## Escopo

### 1. Hash versionado (B3) — `pipeline/domain/services/_tx_identity.py`
- `HashInputs` (frozen): `data, banco, titular, tipo_conta, valor_cents: int, moeda,
  direction`. `compute_natural_key(inputs) -> NaturalKey`.
- `_hash_v2` ingere **cents int** (ADR-090); conversão `Decimal(str(v))` →
  `.quantize(Decimal("1"), rounding=ROUND_HALF_UP)` **inline** (não `getcontext()`,
  thread-local mutável). `0.575 → 58` determinístico, corrige `int(round(0.575*100))==57`.
- `_hash_v1` = núcleo atual movido sem mudança (congelado); `compute_transaction_hash`
  → shim deprecado.
- `natural_key.hash_version`: **`1`** legado · **`2`** moeda+direction.

### 2. Costura de emissão (B4 passo 1) — write-path comum, NÃO `to_e2_dict`
- ⚠️ `Document.to_e2_dict` (`document.py:177`) **não é produtor E2** — único caller é
  o round-trip do E3 (`e3_reconciler_adapter.py:371`). Produtores reais montam
  `result["transacoes"]` direto.
- `stamp_natural_key(result)` injeta `natural_key` + `direction` por tx no write-path
  comum: parsers determinísticos em `scripts/e2_extract.py:354` e LLM em
  `pipeline/stages/extract_with_llm.py:258`. Lê valor via `Decimal(str(v))` (origem
  é float do parser; conversão canônica estável).
- **Inventário B4** (entregável — tabela na lane): cada produtor → caminho → emite
  K4? → gap. Classe (c) (faltam `banco`/`titular`/`tipo_conta` discriminantes, ex.:
  fatura `titular=None` em `c6bank.py:616`) → **`natural_key=null`, NUNCA hash
  degenerado** (evita falso-colapso).
- **Paridade E2-emit ↔ E4-recompute** (`transaction_classifier.py:353` /
  `cash_flow_builder.py:90`): garantida por D3 (`HashInputs` + adapters). Atenção ao
  default divergente: E2 `tipo = account_type or "extrato"` (document.py:182) vs E4
  `tipo_conta_raw` possivelmente vazio — fechar no adapter.

### 3. Schema (B4 passo 1) — `config/schemas/e2_extract.schema.json`
- `transacoes[].natural_key`: objeto **opcional** `{hash: string, hash_version: int}`
  (`nullable`, não-`required` no passo 1 — aditividade). `additionalProperties:true`
  intocado.
- `transacoes[].direction`: enum `["debit", "credit"]` opcional.
- Quando presente, `hash_version ∈ {1, 2}`. **Não colide com W6-T01** (flip→strict do
  `e5_analysis.schema.json` — arquivo distinto; confirmar antes do merge).

### 4. Testes — paridade K4, determinismo e cobertura
Goldens de paridade (§Verificação F1):
- **(a)** 2 shapes de fonte (mesma tx por dois adapters `inputs_from_*`) → **mesmo hash**.
- **(b)** float `0.575` ↔ `Decimal("0.575")` de borda → **mesmo hash** (drift eliminado).
- **(c)** entrada R$100 ≠ saída R$100 ≠ USD100 (moeda+direction discriminam).

Suíte adicional (recomendação `senior-cto`):
- `test_abs_value_collapses_sign` (`test_tx_identity.py:261`) **vira** →
  `test_v2_sign_distinguishes_direction` (pos≠neg).
- `test_v1_frozen` — `_hash_v1` para inputs fixos retorna hash literal de produção
  (congela contrato com DB histórico).
- `test_emit_recompute_parity` — mesmo lançamento lógico pelos dois adapters →
  hash idêntico; **inclui caso fatura-estorno** (`valor<0`, `tipo_conta="fatura…"`,
  onde sinal e tipo discordam).
- `test_hash_v2_deterministic_under_rounding_context` — roda em `localcontext()` com
  `ROUND_DOWN`; hash não muda (prova rounding inline ganha do contexto global).

Cobertura para destravar o passo 2 (recomendação `data-engineer`):
- Log estruturado no write-path: `{stage, key, tx_total, tx_with_natural_key,
  tx_null_natural_key}` (com `workspace_id`+`run_id`).
- Teste-invariante na fixture dogfood: toda tx de stage E2 determinístico tem
  `natural_key` não-nulo **exceto** a lista classe-(c) explícita. Quando a lista
  esvazia → cobertura 100% → passo 2 destrava.

Aditividade (G1): goldens E3/E4/E5 + view-model snapshot + invariantes ([[A23.l2]])
**verdes sem rebaseline** — garantido por D4 (v2 emitido mas **não consumido** em F1).

## Critério de aceite

- `compute_natural_key(HashInputs)` puro/stateless ([[ADR-111]]); núcleo ingere
  cents int, nunca float; `_hash_v1` congelado (v1 resolvível); rounding inline.
- Paridade K4 (a)/(b)/(c) verde; `test_abs_value_collapses_sign` migrado; `test_v1_frozen`,
  `test_emit_recompute_parity` (incl. fatura-estorno), determinismo sob contexto — verdes.
- Inventário B4 documentado (tabela produtor → caminho → classe a/b/c → valida `e2_extract`?);
  informe/CRLV declarados fora de B4; passo 2 com alvo claro + gate de cobertura pronto.
- Schema E2 aceita `natural_key {hash, hash_version}` + `direction` opcionais; **válido
  em strict** (`MATHOMS_PIPELINE_SCHEMA_MODE=strict pytest tests -q -k e2` verde — W6-T01).
- Dívida D6 (terceiro hash `transaction_service.py`) registrada como linha de backlog.
- Goldens E3/E4/E5 + view-model + invariantes verdes **sem rebaseline** (G1).
- `dev/check_pipeline_boundaries.py` verde (`_tx_identity.py` sem import de framework).
- CI verde; PR squashed em `main`.

## Owner sugerido

`data-engineer` (contrato E2 + inventário de produtores + estratégia 2-passos) —
co-design com `senior-cto` (API do hash + paridade emit↔recompute + determinismo).
**Co-design registrado** (D1–D6 acima, 2026-06-08).

## Inventário B4 (executado — 2026-06-08)

**12 produtores de `transacoes` que validam `e2_extract.schema.json`** (alvo B4),
todos cobertos pela costura `stamp_natural_key` no write-path comum:

| Produtor | Caminho de write | Vocabulário | titular None? | Classe |
|---|---|---|---|---|
| 11 parsers determinísticos (bankofamerica, bradesco, btg, c6bank, caixa, itau, picpay, rico, santander, wise) — extratos | `e2_extract.py:354` via `make_result_template` | `banco`/`titular`/`tipo_conta` | raro (detect falha) | A |
| Faturas (c6bank, itau, santander) | idem | idem, `titular=None` explícito | **sim** (`c6bank.py:616`, `itau.py:573`, `santander.py:505`) | C → `natural_key=null` |
| LLM fallback (`E2-llm`) | `extract_with_llm.py:258` | `instituicao`/`membro`/`tipo_documento` (fallback na costura) | possível | A/B |

**Fora de B4** (schema próprio, não `e2_extract`): `quintoandar` (`itens`,
`informe_aluguel.schema.json`), `extract_informes_anuais` (`informe_base`),
`extract_comprovantes_bens` (`crlv`). Confirmado em `SCHEMA_BY_STAGE`
(`db_artifact_store.py:81`).

**Cobertura medida** (log no write-path): `with_key/tx_total` por artefato. Gap
residual do passo 1 = faturas classe-c (titular ausente). Passo 2
(nullable→obrigatório) destrava quando a lista classe-c esvaziar (resolver titular
de fatura) — gate de cobertura == 100%.

**Risco de paridade para o passo 2** (não bloqueia F1 por D4): `tipo_conta` no E2
(`tipo` default `"extrato"` / `"fatura…"`) vs `tipo_conta_raw` no E4 — fechar o
mapeamento exato de string antes de o E4 consumir o `natural_key` v2.

## D6 — dívida cross-stack (fora do escopo F1)

`backend/app/services/transaction_service.py:17` (`generate_transaction_hash`):
SHA-256 **full** (não `[:16]`), ordem de campos distinta, sem `tipo_conta`, ingere
`valor` string crua. Alimenta `TransactionOverride` (UK `workspace_id,
transaction_hash`) + Categorization Learning Loop. **Não migra nesta lane** — mas
sem alinhá-lo ao K4 v2, o passo 2 quebra sticky-override silenciosamente.

> **Decisão:** [[ADR-282]] (Proposto). **Implementação:** [[A23.l4]] (slices 1–3 em
> A23; cutover + M2 destrutiva em A24). O passo 2 (flip dedup E4→v2) fica **bloqueado**
> até o cutover da [[ADR-282]] + dogfood de reancoragem verde. Estado por-slice vive
> na [[A23.l4]] — não duplicar aqui.

## Entregue (status: shipped — PR #553, commit `7b7a4028`, 2026-06-08)

- **`pipeline/domain/services/_tx_identity.py`** — `_hash_v1` congelado (shim
  `compute_transaction_hash`) + `_hash_v2` (cents int via `Decimal`, moeda+direction,
  ROUND_HALF_UP inline) + `HashInputs`/`build_hash_inputs` + `derive_direction`
  (espelha `_normalize_tipo`) + `compute_natural_key`/`NaturalKey`.
- **`pipeline/domain/services/e2_natural_key.py`** — `stamp_natural_key` na costura do
  write-path comum (`scripts/e2_extract.py:354` + `pipeline/stages/extract_with_llm.py:258`),
  cobre vocabulário determinístico e LLM; faturas sem titular → `natural_key=null`
  (classe-c); log de cobertura `with_key/tx_total`.
- **`config/schemas/e2_extract.schema.json`** — `transacoes[].natural_key {hash,
  hash_version}` + `transacoes[].direction` opcionais (válidos em strict).
- **`tests/unit/pipeline/test_natural_key_v2.py`** — paridade (a/b/c), `test_v1_frozen`,
  `test_v2_frozen`, `test_v2_sign_distinguishes_direction`, `test_emit_recompute_parity`
  (incl. fatura-estorno), determinismo sob `localcontext`, anti-drift
  `derive_direction↔_normalize_tipo`, estampagem.
- **Aditividade (G1) confirmada:** goldens E3/E4/E5 + view-model snapshot + invariantes
  verdes **sem rebaseline** (v2 emitido mas não consumido, D4).

**Pendente (fora desta lane, registrado):** passo 2 de B4 (nullable→obrigatório) gated
por cobertura 100% (faturas resolverem titular) **e** pela dívida D6 — cuja decisão é
[[ADR-282]] (Proposto); implementação da migration de `TransactionOverride` é
pré-requisito do flip de consumo no E4.

## Não-escopo (lanes irmãs)

- DDL `data_source` / coluna `data_source_id` / `SourceRef` → `dl-f1-data-source`.
- Campo `amount` decimal ao lado de `valor` (B5) → `dl-f1-amount-decimal`.
- Migration dry-run + runbook PITR (G-e) → `dl-f1-migration-runbook`.
- Passo 2 (natural_key `nullable` → `obrigatório`) → depende do inventário desta lane;
  executado quando todos os produtores emitirem K4.
