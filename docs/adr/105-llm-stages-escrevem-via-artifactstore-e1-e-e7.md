---
id: ADR-105
type: adr
title: "LLM stages escrevem via ArtifactStore; E1 e E7-review LLM não migram (A6a)"
status: Decidido
phase: "A6a"
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 105"]
tags:
  - type/adr
  - status/decidido
size_lines: 42
---

# ADR-105 — LLM stages escrevem via ArtifactStore; E1 e E7-review LLM não migram (A6a)

**Status:** Decidido (A6a) • **Data:** 2026-04-19

**Contexto:** Antes de A6a, E1.5 e E2-llm escreviam artefatos do pipeline
direto em disco (`.write_text`), bypassando o `ArtifactStore`. Com
`MATHOMS_USE_DB_ARTIFACTS=true`, o pipeline quebraria: E3 buscaria esses
artefatos no DB e não os encontraria. Dois outros LLM stages existem: E1
(produz `family_members.json`, que é config do workspace, não artefato do
pipeline) e E7-review-LLM (produz um JSON de review ad-hoc consumido por
E7-apply; já persiste no path correto via disco).

**Decisao:**
1. E1.5 (`pipeline/stages/e15.py`): troca `out_path.write_text(...)` por
   `store.write("E1.5", "baseline_patrimonial", baseline_json)` → produz
   `baseline_patrimonial-1.5_baseline.json`. E1.5c lê via fallback.
2. E2-llm (`pipeline/stages/e2_llm.py`): troca `out_path.write_text(...)` por
   `store.write("E2-llm", safe_stem, e2_json)`. `_find_unprocessed_docs`
   migrada para `store.list_keys(stage)` em vez de glob de disco.
3. **E1 não migra**: `family_members.json` é configuração do workspace, não
   artefato do pipeline. Escrita em `ctx.members_dir/` é correta.
   > **⚠️ Superseded (2026-04-24) — ver ADR-127:** o output de E1
   > (`members-1b_unified.json`) é de fato artefato de domínio (produto
   > do LLM por execução, não config estática do workspace). E1 passou a
   > persistir via `store.write("E1", "members", ...)`.
4. **E7-review LLM não migra**: o reviewer externo (humano ou automação)
   escreve o arquivo de review; E7-apply já lê via path convencional. Não é
   stage de produção contínua — é input ad-hoc fora do loop determinístico.

**Consequencias:**
- ✅ `MATHOMS_USE_DB_ARTIFACTS=true` pode ser ativado sem quebrar E3→E7.
- ✅ E1.5c lê corretamente via `store.read("E1.5", ...)` (fallback já em A5f).
- ✅ E2-llm: `_find_unprocessed_docs` via `store.list_keys` funciona em modo Disk e DB.
- ✅ Critérios estruturais enforçados por testes (`store.write` presente; `write_text` ausente).
- ⚠️ E1.5: filename em disco mudou de `-1.5_consolidated.json` para `-1.5_baseline.json`
  para novos workspaces. Workspaces existentes com arquivo no caminho antigo continuam
  funcionando (E1.5c lê E1.5c key primeiro → encontra o consolidated existente).
- ⚠️ E7-review LLM: se `MATHOMS_USE_DB_ARTIFACTS=true` e o arquivo de review foi
  escrito via disco, E7-apply pode não encontrá-lo em DB store. Documentado como
  limitação conhecida — review LLM é input ad-hoc, não stage automatizado.
