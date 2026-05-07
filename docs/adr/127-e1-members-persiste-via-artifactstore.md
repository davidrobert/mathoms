---
id: ADR-127
type: adr
title: "E1 members persiste via ArtifactStore"
status: Decidido
date: "2026-04-24"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 127"]
tags:
  - area/multitenancy
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 54
---

# ADR-127 — E1 members persiste via ArtifactStore

**Status:** Decidido • **Data:** 2026-04-24

**Contexto:**
ADR-083 estabeleceu o `ArtifactStore` como única via de persistência de
artefatos de domínio; ADR-118 virou o default de `MATHOMS_USE_DB_ARTIFACTS`
para `True`. Quase todas as stages (E1.5, E2, E3, E4, E5, E7) já passam pelo
store — mas E1 ficou para trás: `pipeline/stages/e1.py` escrevia
`members-1b_unified.json` direto em `ctx.members_dir` via
`Path.write_text()`, fora do backend DB e fora do `MaterializationBridge`.

Consequências do legacy path:
- Workspaces com `use_db_artifacts=True` não tinham o artefato E1 no DB.
- `DBArtifactStore`/bridge não enxergavam `members` — qualquer consumidor
  que viesse a ler por `store.read("E1", "members")` obteria `None`.
- E1 era a única exceção de stage de domínio escrevendo em disco.

**Decisão:**
1. Registrar `"E1"` em `_STAGE_TO_DIR` (`"members"`) e `_STAGE_TO_SUFFIX`
   (`"-1b_unified.json"`) em `pipeline/artifact_store.py`. Layout em disco
   passa a ser `<root>/processed/members/members-1b_unified.json` (padrão
   dos demais stages, consistente com `MaterializationBridge`).
2. `pipeline/stages/e1.py`: substituir `out_path.write_text(...)` por
   `ctx.get_artifact_store().write("E1", "members", family_json)`. Remover
   import `json` (sem mais serialização manual) e `members_dir.mkdir`
   (store cria o diretório sob demanda ou persiste em DB).
3. `output_file` no dict de retorno passa a ser string literal
   `"members-1b_unified.json"`, desacoplada do `Path`.

**Consequências:**
- ✅ E1 ganha paridade com demais stages: `MaterializationBridge` funciona
  gratuitamente (mapping resolve dir+suffix); workspaces com DB-backed
  store registram o artefato no banco.
- ✅ Nenhum consumidor downstream lê `members-1b_unified.json` de disco
  (members canônico vem de `config/family_members.json`, carregado por
  `ctx.load_config`), então a mudança de layout é segura.
- ⚠️ **TODO (separado):** `scripts/e_reset.py` protege E1 por
  whitelist de path em disco (linhas 244, 677, 684). Com artefato em DB,
  a proteção precisa estender-se à linha `pipeline_artifacts` de
  `(workspace_id, stage="E1", artifact_key="members")`. Fora do escopo
  desta ADR — exige análise do fluxo de `e_reset` com DB.
- ⚠️ Caminho em disco muda de `<root>/members/` para
  `<root>/processed/members/` quando `DiskArtifactStore` é usado.
  Aceitável porque o único consumidor do arquivo em disco era o teste
  `test_llm_stages_per_stage.py`, já migrado.

**Arquivos críticos:**
- `pipeline/artifact_store.py` (mapping)
- `pipeline/stages/e1.py` (write via store)
- `tests/unit/pipeline/test_artifact_stores.py`,
  `tests/test_llm_stages_per_stage.py` (cobertura)
