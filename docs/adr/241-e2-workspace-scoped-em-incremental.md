---
id: ADR-241
type: adr
title: "E2 (extratos / faturas / LLM fallback) é workspace-scoped — incremental cumulativo correto"
status: Decidido
phase: A17.incremental-correctness
date: "2026-05-21"
relates_to:
  - "[[ADR-080]]"
  - "[[ADR-082]]"
  - "[[ADR-132]]"
  - "[[ADR-212]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 241"
  - "E2 workspace-scoped"
tags:
  - area/pipeline
  - area/persistence
  - area/multitenancy
  - status/decidido
  - type/adr
size_lines: 168
---

# ADR-241 — E2 workspace-scoped em incremental

**Status:** Decidido • **Data:** 2026-05-21 • **Relaciona** [[ADR-080]] (incremental), [[ADR-082]] (`pipeline_artifacts`), [[ADR-132]] (lifecycle scoping), [[ADR-212]] (DB-only artifacts)

## Contexto

O produto promete suporte a **incremental** ([[ADR-080]]): usuário envia 1–N documentos novos e o pipeline reprocessa só o delta. Mas o usuário espera ver o **cumulativo correto** no relatório (todos os meses do período pedido, todos os bancos).

Investigação em relatório real (workspace `Campos`, run `c36c4baf-…`, período 2025-12, 15 informes selecionados) expôs o gap: o relatório saiu com `total_receita: R$ 1.398,60` e `total_despesa: R$ 52.605,96` baseados em apenas **4 transações** de 1 informe IR — o universo real do workspace tem 70+ extratos bancários (Itaú, Santander, Bradesco, C6, Wise, BTG, BankOfAmerica, Rico, Picpay) acumulados em 6 rodadas anteriores. Causa direta:

1. `DBArtifactStore.list_keys(stage)` retorna chaves workspace-wide (~80 E2 keys visíveis).
2. `DBArtifactStore.read(stage, key)` filtra por `pipeline_run_id` atual; só os 2 E2 novos desta rodada retornam payload — todos os outros devolvem `None`.
3. Fallback workspace-wide em [`_WORKSPACE_SCOPED_STAGES`](../../backend/app/services/storage/db_artifact_store.py#L82) hoje cobre só E1.x (members, baseline, IRPF, informe_aluguel, informes_anuais). E2/E3/E4/E5 estão explicitamente fora, conforme [[ADR-132]] (decisão tomada antes de incremental ser fluxo principal).
4. E3 (reconcile) lê todos os E2 via `list_keys` mas só carrega os do run atual — 2 statements → 1 conta com 4 transações.
5. E4, E5 propagam o universo subdimensionado; relatório fica errado em fluxo, categorias, taxa de poupança, investimentos atuais, caixa.

[[ADR-132]] decide acertadamente que **datasets de referência** (baseline IRPF, family_members) devem sobreviver a runs que não os reprocessam. A premissa "E2 é per-run derivado" não bate com a realidade observada: **E2 é per-documento idempotente** — cada `artifact_key` ≈ `{hash}_{banco}_{tipo}_{periodo}` corresponde a um documento individual; extrair o mesmo PDF/CSV duas vezes produz o mesmo payload. Se o usuário não re-uploadou aquele documento, a extração antiga continua válida.

E3/E4/E5 são diferentes: têm invariantes **cross-account** (dedup de transações, saldo continuity entre extratos contíguos do mesmo banco, fatura sintetizada [[ADR-097]] D2, consolidação por membro). Não podem ser "mais recente por key" — precisam recomputar sobre o universo completo a cada run.

## Decisão

**Promover os 6 nomes de E2 a workspace-scoped em [`_WORKSPACE_SCOPED_STAGES`](../../backend/app/services/storage/db_artifact_store.py#L82):**

```python
# Legado (F9.2 compat)
"E2-extratos", "E2-faturas", "E2-llm",
# Descritivo equivalente (F9.2+)
"extract_statements", "extract_invoices", "extract_with_llm",
```

`read("E2-*", key)` faz fallback ao mais recente do workspace (já implementado em `_get_latest_in_workspace`). Mais-recente-por-`(workspace_id, stage, artifact_key)` por `created_at DESC` resolve dedup entre runs.

**E3/E4/E5 permanecem run-scoped e recomputam o universo a cada run.** Em incremental, eles agora **conseguem ler** todos os E2 do workspace (via fallback) e produzem outputs cumulativos coerentes. Cada run grava seus próprios E3/E4/E5 com `pipeline_run_id` atual — preserva invariantes cross-account.

**Telemetria de fallback**: `DBArtifactStore.read` loga em nível `info` com structured fields (`workspace_id`, `stage`, `artifact_key`, `source_run_id_origin`) **somente quando** o fallback workspace-wide entra em ação. Sem custo no caminho quente (mesmo número de queries); detecta drift quando consumidor frequente lê via fallback (sinal de que stage virou efetivamente workspace-scoped na prática).

**Índice composto** `(workspace_id, stage, artifact_key, created_at DESC)` — sem ele, `_get_latest_in_workspace` faz sort O(N) por chamada. Adicionado na mesma migration que entrega a ADR (defesa em profundidade contra latência em workspaces grandes).

## Alternativas consideradas

- **(a) Promover E3 também a workspace-scoped.** Rejeitada: E3 tem invariantes cross-account (dedup, saldo continuity) que dependem de ver todos os extratos de **um run consistente**. Mais-recente-por-key congelaria dedup parcial entre runs — bug silencioso difícil de detectar.
- **(b) Orquestrador copia forward E2 antigos.** Funcionaria mas duplica payloads em cada rodada (~50 KB × N rodadas) e exige lógica de "copy-forward" no orchestrator. A solução workspace-scoped não duplica payloads e é localizada na camada de leitura.
- **(c) Validate-on-read estrita.** Adiar — política preferida (data-engineer + senior-cto) é tratar breaking change de schema E2 como **migration explícita** que reescreve histórico, não `fail-soft` no read. Política Alembic, não defensive parsing.

## Consequências

- ✅ **Fix imediato**: relatórios em incremental refletem cumulativo correto. Workspace `Campos` (caso observado) passa a enxergar os 70+ extratos.
- ✅ **Sem mudança em E3/E4/E5**: invariantes cross-account preservados. Custo de recomputação aceitável (~30s para 80 E2 no workspace `Campos`).
- ✅ **Sem migration estrutural**: índice composto é additive, sem alteração de schema.
- ✅ **Telemetria detecta drift**: log no fallback expõe consumidores que dependem da feature, facilitando futura migration de scope.
- ⚠️ **Crescimento da tabela**: `pipeline_artifacts` deixa de ter GC implícito ("artifacts de runs antigas eram inalcançáveis"). Em workspace ativo, todo E2 de toda run histórica fica vivo (mesmo doc → row nova a cada re-upload). Política de retenção/GC vira **débito explícito** — ver §Follow-ups.
- ⚠️ **Custo de E3/E4/E5 em incremental**: hoje custa ~30s para 80 extratos. Workspaces com 500+ docs podem chegar a 3–5min — possível conflito com Celery `soft_time_limit` default (300s). Pré-flight com sre-devops é follow-up obrigatório antes de habilitar incremental em workspaces grandes.
- ⚠️ **Schema drift de E2**: artefato vN−1 quando consumidor espera vN. Hoje `e2_extract.schema.json` é estável (mudanças sempre additive nos últimos 6 sprints). Política: **breaking change de schema E2 → migração que reescreve histórico** (mesmo padrão do Alembic). Não fail-soft no read.
- ❌ **Não cobre stage `extract_informes_anuais`**: já está em `_WORKSPACE_SCOPED_STAGES` ([[ADR-238]]); sem impacto aqui.

## Gates de regressão

**T1 — Unit em `backend/tests/test_db_artifact_store.py`.** Estender `test_workspace_scoped_stages_fall_back_cross_run` para incluir as 6 keys de E2. Atualizar `test_run_scoped_stage_does_not_fall_back` para asseverar apenas E3/E4/E5 (não E2).

**T2 — Unit do telemetry log**. Garantir que `read()` que cai no fallback emite log estruturado com fields requeridos (`stage`, `artifact_key`).

**T3 — Integração em `backend/tests/integration/test_e2_incremental_carryforward.py` (novo).** Seed workspace com 10 E2 em run A (full). Cria run B com `incremental=True` re-extraindo 2 docs novos. Assert: `E3 do run B` produz reconcilia 12 statements (10 carry-forwarded + 2 novos); `E4 totais` cobre todas as transações.

**T4 — Paridade com full rerun.** Mesmo workspace, comparar (a) full rerun com 12 docs vs (b) incremental sobre baseline 10 + 2 novos. Asserir igualdade (com tolerância 0.01 BRL monetária) em `E5.patrimonio.liquido`, `E5.fluxo_caixa.receita_total`, `E5.fluxo_caixa.despesa_total`.

## Follow-ups (débito registrado, não bloqueia merge)

1. **GC superseded E2** — política de retenção (manter N versões mais recentes por `(ws, stage, key)`; soft-delete ou hard-delete versões antigas com `created_at < threshold`). Implementação fora desta lane; rastreado em `docs/archive/PLATFORM_REVIEW_PLAN-2026-07-08.md` §W6 (storage hygiene).
2. **Backfill `schema_version`** — coluna existe mas está NULL em todas as rows. `DBArtifactStore.write` passa a popular sempre. Migration backfilla rows existentes com a versão atual de cada stage. Fora desta lane.
3. **Celery `soft_time_limit` em incremental** — coordenar com sre-devops sobre chunking de E3 por conta (`pipeline.domain.services.e3_reconciler_adapter` já agrupa por `(banco, conta, moeda)`) e/ou aumento de timeout. Fora desta lane.
4. **`extract_with_llm` enum estrito em `categoria_sugerida`** — ADR-242 (paralela) consome o campo; enum estrito vira follow-up quando o vocabulário consolidar (evita quebrar artifacts antigos com `categoria_sugerida=null|""`).
