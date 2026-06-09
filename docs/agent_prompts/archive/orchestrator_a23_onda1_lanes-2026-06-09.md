# Orquestração — A23 Data Lineage · Onda 1 (4 lanes irmãs restantes)

> **⚠️ Parcialmente superado.** `dl-f1-data-source` foi entregue como **[[A23.l5]]** (#564,
> em `main`). As 3 lanes restantes (`dl-f1-amount-decimal`, `dl-f1-extract-check`,
> `dl-f1-migration-runbook` — esta última agora também materializa o FK DB deferido da
> A23.l5) seguem em [`orchestrator_a23_onda1_restante.md`](orchestrator_a23_onda1_restante.md),
> que é a instância **corrente**. Mantido aqui por histórico do co-design das 4 lanes.

> Instância do [_TEMPLATE_orchestrator.md](_TEMPLATE_orchestrator.md) para fechar a
> **Onda 1 (F1 — contrato aditivo)** do plano [DATA_LINEAGE](../plan/DATA_LINEAGE/_README.md).
> A23.l1 (gate F0), A23.l2 (substrato de golden, #552) e A23.l3 (`dl-f1-natural-key`
> B3/B4, #553) já estão em `main`. Restam 4 lanes de contrato:
> `dl-f1-data-source`, `dl-f1-amount-decimal`, `dl-f1-extract-check`,
> `dl-f1-migration-runbook`. A dívida D6 da A23.l3 ganhou decisão em [[ADR-282]]
> (Proposto) e implementação própria na lane **[[A23.l4]]** (`a23-l4-override-hash-k4-parity`,
> slices 1–3 aditivos em A23; slice 1 ✅ #556) — **fora do escopo deste prompt**.
>
> ⚠️ **Numeração:** este prompt referencia as 4 lanes de contrato pelo
> **`branch_slug`** (`dl-f1-*`), não por `A23.l{n}` — o número `A23.l4` já está
> ocupado pela lane override-hash/D6. Ao criar os arquivos de lane, use os próximos
> ids sequenciais livres (`A23.l5`–`A23.l8`); a fonte de verdade do estado é
> [`docs/sprint/A23/_README.md`](../sprint/A23/_README.md) §Estado atual.
>
> **Uso:** copie o bloco abaixo no início da sessão. O orquestrador respeita as
> convenções de [CLAUDE.md](../../CLAUDE.md) e delega aos especialistas de
> [`.claude/agents/`](../../.claude/agents/).
>
> **Quando arquivar:** quando as 4 lanes estiverem `shipped` em `main`. Mover para
> [`archive/`](archive/) com data.

---

```
Continue a Onda 1 da sprint A23 (Data Lineage) do Mathoms AI — as 4 lanes irmãs
restantes da Onda 1 (F1: contrato aditivo). Fatie em branches/PRs próprios.

## Onde estamos (já mergeado em main — NÃO refazer, NÃO clobberar)
- Gate F0 FECHADO: ADR-278/279/280/281 Decididas. Plano PLAN-data-lineage in_progress.
- A23.l1 (F0 ADR gate) ✅ · A23.l2 (substrato de golden, #552) ✅ — USE
  dev/golden_diff.py + backend/tests/test_report_view_model_snapshot.py +
  tests/test_e5_conservation_invariants.py para paridade/aditividade.
- A23.l3 (dl-f1-natural-key, B3/B4, #553) ✅ JÁ MERGEADA. Entregou:
  - pipeline/domain/services/_tx_identity.py: _hash_v1 CONGELADO (não tocar) +
    _hash_v2 (cents int via Decimal, moeda+direction) + HashInputs +
    build_hash_inputs + derive_direction + compute_natural_key/NaturalKey.
  - pipeline/domain/services/e2_natural_key.py: stamp_natural_key na costura do
    write-path comum (scripts/e2_extract.py:354 + pipeline/stages/extract_with_llm.py:258).
  - config/schemas/e2_extract.schema.json: ADICIONOU transacoes[].natural_key
    {hash,hash_version} + transacoes[].direction (opcionais). ⚠️ NÃO sobrescreva
    esses campos ao editar o schema — só ADICIONE amount ao lado.
  - Dívida D6 (backend/app/services/transaction_service.py:17 generate_transaction_hash,
    hash incompatível que alimenta TransactionOverride + learning loop): a DECISÃO está
    na ADR-282 (docs/adr/282-override-identity-natural-key-v2.md, Proposto) — a
    implementação da migration é pré-requisito do PASSO 2 de B4, NÃO é desta onda.
    Se tocar D6/passo-2, CONFORME à ADR-282 (não reabra).

## Leia primeiro (canônico — não confie só neste prompt)
1. CLAUDE.md (raiz) — regras, code style (funções ≤20 linhas, docstring 1 linha;
   o gate dev/check_code_style_regression.py é exigente), git/PR, delegação.
2. docs/plan/DATA_LINEAGE/_README.md — §Arquitetura camadas A/B, §Ondas (tabela
   Onda 1), §Guard-rails (G-e), §Verificação F1/F2, blocker B5, ADR-280.
3. docs/adr/278-source-adapter-canonical-contract.md (data_source SEM FK polimórfica,
   data_source_id nullable ON DELETE SET NULL, B5 amount 2-fases) +
   docs/adr/280-extract-transform-cut-criterion.md (critério Extract|Transform).
4. docs/sprint/A23/lanes/A23-l3-natural-key.md — ESPELHE o formato (frontmatter,
   co-design, inventário, critério de aceite) ao criar as lanes novas.

## As 4 lanes (crie docs/sprint/A23/lanes/A23-l{5,6,7,8}-*.md espelhando A23.l3 — branch_slug `dl-f1-*`)

ORDEM/DEPENDÊNCIAS:
- dl-f1-data-source (P0, CENTRAL — faça primeiro): tabela `data_source`
  (id, workspace_id FK CASCADE, kind, institution_code, external_account_ref,
  display_name, created_at; unique (workspace_id,kind,institution_code,external_account_ref))
  + coluna pipeline_artifacts.data_source_id nullable FK ON DELETE SET NULL
  (document_id PERMANECE) + SourceRef discriminated union + SourceAdapter Protocol
  em pipeline/domain/ports/source.py (NOVO). Migration Alembic: ADD COLUMN NULL +
  CREATE INDEX CONCURRENTLY (fora de transação: autocommit_block /
  postgresql_concurrently=True) + backfill idempotente kind='document' para artefatos
  E2 com document_id. ⚠️ pipeline/** NÃO importa sqlalchemy — SourceRef/SourceAdapter
  são tipos de domínio puros; o adapter DB vive em backend/app/services/.
- dl-f1-amount-decimal (B5, paralelo a data-source): campo `amount` decimal string
  (ADR-090) ao lado de `valor` em transacoes[] do contrato E2 (additive ao
  e2_extract.schema.json — ADICIONE, preserve natural_key/direction da l3).
  Inventário de TODOS os leitores de transacoes[].valor (E3 reconciler, cents_int,
  dedup). Gate Decimal(amount)==Decimal(str(valor)) enquanto coexistem; NÃO deprecar
  valor nesta onda. Sem DDL (amount vive no content_json).
- dl-f1-extract-check (ADR-280, paralelo): dev/check_extract_no_domain_imports.py
  (NOVO) — extração (scripts/e2/banks/*, extract_baseline, extract_irpf_full) ∌
  imports de category_template / *_dedup / ConfigStore. Estende validate_full_order.
  Rotula consolidate_baseline (E1.5c) como Transform. NÃO mover código ainda (de-leak
  é F2); este lane só TRAVA o critério de pureza com o gate. Espelhe
  dev/check_pipeline_boundaries.py como padrão.
- dl-f1-migration-runbook (G-e, DEPOIS de data-source): runbook
  docs/reference/runbooks/data_lineage_migrations.md (4 migrations: data_source,
  data_source_id, artifact_lineage_edge [F3, futura], 2-fases amount/natural_key)
  com janela PITR + rollback por fase + asserção CONCURRENTLY/autocommit_block em
  backend/tests/.../test_alembic_guardrails. Documenta a migration que a l4 criar.

## Inegociáveis
- Dinheiro nunca float (ADR-090); stateless (ADR-111); pipeline/** não importa
  fastapi/celery/sqlalchemy (dev/check_pipeline_boundaries.py). CI VERDE antes do
  merge. Concluído = PR squashed em main com CI verde (docs-only não espera CI).
- ADITIVIDADE (G1): contrato aditivo, NÃO consumir ainda → goldens E3/E4/E5 +
  view-model snapshot + invariantes de conservação VERDES SEM REBASELINE. Prove com
  dev/golden_diff.py. Se algo exigir rebaseline, parou — reavalie (é sinal de que não
  é aditivo).
- Migration online segura: ADD COLUMN NULL, CREATE INDEX CONCURRENTLY fora de transação,
  backfill idempotente. Testar em modo strict: MATHOMS_PIPELINE_SCHEMA_MODE=strict.
- Co-design ANTES de codar (eles revisam SEU design, não redecidem ADR):
  - data-source → data-engineer (schema/migration/backfill/índices) + senior-cto
    (SourceRef union + SourceAdapter port). Migration → sre-devops (CONCURRENTLY/PITR).
  - amount-decimal → data-engineer (inventário de leitores + gate de paridade B5).
  - extract-check → senior-cto (boundary gate, padrão check_pipeline_boundaries).
  - migration-runbook → sre-devops (runbook/PITR/rollback) + information-architect
    (forma do runbook) + data-engineer (conteúdo da migration).

## Antes de começar
- git fetch origin && git worktree list && git for-each-ref --sort=-committerdate
  refs/remotes/origin/agent/ | head  (confirme que ninguém está em dl-f1-data-source/
  amount-decimal/extract-check/migration-runbook)
- Crie UMA branch por lane: agent/dl-f1-data-source/<yyyyMMdd-HHmm> a partir de
  origin/main (idem amount-decimal/extract-check/migration-runbook). Não misture
  lanes no mesmo PR.
- Comece por data-source (central). amount-decimal/extract-check podem rodar em
  paralelo. migration-runbook só depois da migration da data-source existir. Anuncie
  cada operação git. Comece lendo as fontes e propondo plano + co-design por lane.
```
