---
id: ADR-104
type: adr
title: "E1.5c em Caminho B pragmático (Sessão A5f)"
status: Decidido
phase: "A5f"
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 104"]
tags:
  - type/adr
  - status/decidido
size_lines: 26
---

# ADR-104 — E1.5c em Caminho B pragmático (Sessão A5f)

**Status:** Decidido (A5f) • **Data:** 2026-04-19

**Contexto:** Após A5e, E1.5c era o único stage determinístico fora do
Caminho B — usava `stage_runner_compat` + `MaterializationBridge` no wrapper
`pipeline/stages/e15c.py`. A consolidação de baseline é um script simples
(lê JSON, enriquece com chaves consolidadas, grava de volta), sem domain
services adicionais a extrair — candidato natural ao padrão pragmático já
adotado em E4/E5/E5.N/E7.

**Decisao:** Aplicar Caminho B pragmático (padrão ADR-097/A4b, ADR-099/A5d):
`main_with_store(ctx)` reutiliza `consolidate()` legado; wrapper limpo sem
bridge. `main(root_dir)` legado coexiste para CLI direto e testes existentes.

**Consequencias:**
- ✅ 7 de 7 stages determinísticos no Caminho B — `stage_runner_compat`
  sem clientes vivos em `pipeline/stages/`.
- ✅ Caminho A6c (remoção definitiva do bridge) desbloqueado assim que
  A6a+A6b+A6-human concluídos.
- ✅ Paridade comprovada por golden (cenários `itens[]` e `declarations[]`).
- ⚠️ `_init_config` e globals de módulo permanecem — remoção em A6d.1.
- ⚠️ Bridge e `stage_runner_compat` **não são removidos** aqui; aguardam
  A6a (LLM stages) + A6b (cutover DB) + A6-human (validação end-to-end).
