---
id: ADR-120
type: adr
title: "Readers user-facing consultam `ArtifactStore` (DB-first) com fallback disco"
status: Decidido
phase: "A6"
date: "2026-04-23"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 120"]
tags:
  - area/multitenancy
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 76
---

# ADR-120 — Readers user-facing consultam `ArtifactStore` (DB-first) com fallback disco

**Status:** Decidido (A6) • **Data:** 2026-04-23

**Contexto:** Com ADR-118 o default de `MATHOMS_USE_DB_ARTIFACTS` virou
`True`. Todos os writers do pipeline (`pipeline/stages/*.py`) já gravam via
`ctx.get_artifact_store().write(...)` — em produção, só no DB
(`pipeline_artifacts`). Porém múltiplos leitores em `backend/app/services/`
e `scripts/e6_render.py` continuavam apontando direto para
`tenant_root/processed/<dir>/*.json` do disco, herdado da fase
pré-cutover. Resultado: após uma run bem-sucedida, dashboard, lista de
transações, extract-JSON de IRPF e o relatório HTML mostravam dados de
uma run anterior (ou vazios) porque o disco não foi atualizado.

Incidente 2026-04-23: workspace caed2272 com E5 executado (`patrimonio_bruto=4.3M`
no DB) renderizou relatório com patrimônio de `940k` (valor de disco stale
da run free-tier anterior). Mesmo padrão se manifestou em 4 readers user-facing,
cada um descoberto em sequência.

Alternativas avaliadas:
1. **Write-through no writer** (DB + disco em todo stage). Duplica bytes;
   se uma das escritas falha silenciosamente, o bug volta. Acopla writer à
   camada de apresentação.
2. **Remover disco inteiramente** (só DB). Quebra CLI dev, `DiskArtifactStore`
   e workflows que hoje editam JSONs à mão. Rollback do ADR-118 fica inviável.
3. **DB-first no reader com fallback disco** — escolhida.

**Decisao:** Leitores em `backend/app/services/` que historicamente lêem
`tenant_root/processed/<dir>/*.json` passam a chamar o helper único
`backend.app.services.artifact_reader.read_latest_artifact(workspace_id,
stage, key, tenant_root=...)`. O helper consulta `pipeline_artifacts`
primeiro (fonte de verdade pós-ADR-118) e cai para disco somente quando
a linha não existe — fallback limpo para `DiskArtifactStore` em CLI dev
e para workspaces pré-cutover migrando via
`backend/app/scripts/backfill_artifacts_from_disk.py`.

`scripts/e6_render.py` é exceção pragmática: continua lendo disco via
`scripts.pipeline_common`, mas o wrapper em `pipeline/stages/e6.py`
chama `pipeline.stage_materialization.materialize_stages_to_root(...)`
antes do render — espelha os artefatos do store em disco na raiz do
tenant. Wrapper é removível quando E6 migrar para ler via store (Fase 9).

**Regra para código novo:**
- Reader em `backend/app/` lendo artefato do pipeline → **obrigatório**
  via `read_latest_artifact` ou `ArtifactStore` direto.
- `Path(tenant_root) / "processed" / ...` fora de writers e de
  `stage_materialization.py` é bug — gate via code review.
- Writers em `pipeline/stages/*.py` continuam gravando só via
  `ctx.get_artifact_store().write(...)` — nada muda.

**Consequencias:**
- ✅ 4 readers user-facing (dashboard E5, transactions E4,
  IRPF extract E1.5a, sync flag E1.5a) passam a retornar sempre o estado
  mais recente. Protegido por integration test `backend/tests/integration/
  test_db_first_artifact_readers.py` — monta workspace com artefatos só no
  DB, disco vazio, e confirma que todos os 4 readers encontram os dados.
- ✅ Padrão único e testável; adicionar um 5º reader é uma linha
  (`read_latest_artifact(ws, stage=..., key=..., tenant_root=...)`).
- ✅ `DiskArtifactStore` segue funcionando — CLI dev (`scripts/e*.py --help`)
  inalterado.
- ✅ Backfill disco→DB (ADR-082, `backfill_artifacts_from_disk.py`)
  continua operacional; workspaces migrando ainda lêem disco até completar.
- ⚠️ Custo de 1 query `pipeline_artifacts` por reader call (ORDER BY
  `created_at` DESC LIMIT 1). Índice
  `ix_pipeline_artifacts_workspace_stage_key` cobre; latência observada
  <3ms em dev. Se virar hot path, cache por-request é trivial.
- ⚠️ Dois caminhos de leitura (DB + disco) enquanto backfill de workspaces
  pré-cutover não terminar. Remoção do fallback é housekeeping de Fase 9.
- ❌ `scripts/e6_render.py` ainda lê disco — wrapper compensa, mas a
  dívida permanece até E6 migrar para store direto (fora do escopo desta ADR).

Relaciona-se a: ADR-083 (ArtifactStore), ADR-106 (DBArtifactStore por
workspace), ADR-118 (flip do default). Não substitui nenhuma ADR anterior;
complementa ADR-118 fechando o gap de leitores.
