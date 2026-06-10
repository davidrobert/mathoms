---
id: ADR-279
type: adr
title: "Lineage field-level inline (_lineage) + índice reverso artifact_lineage_edge"
status: Decidido
phase: "A23 · F0"
date: "2026-06-02"
relates_to:
  - "[[ADR-216]]"
  - "[[ADR-090]]"
  - "[[ADR-111]]"
  - "[[ADR-241]]"
  - "[[ADR-271]]"
  - "[[ADR-255]]"
supersedes: []
superseded_by: []
aliases: ["ADR 279", "lineage field-level", "artifact_lineage_edge"]
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/data-lineage
---

# ADR-279 — Lineage field-level inline (_lineage) + índice reverso artifact_lineage_edge

**Status:** Decidido (A23 · F0) • **Data:** 2026-06-02 • **Relaciona** [[ADR-216]], [[ADR-090]], [[ADR-111]], [[ADR-241]], [[ADR-271]], [[ADR-255]].

> Camada B do plano [[PLAN-data-lineage]]. Gate F0 — **resolve B6, B8**.
> Decisão fechada; lanes de implementação conformam.

**Contexto:** validar/debugar um número exige hoje arqueologia stage-a-stage; o lineage existente (`backend/app/services/report_lineage.py::lineage_payload`) é coarse (run → documentos). Queremos lineage declarativo field-level inline no `content_json` (cabe via `additionalProperties:true`, generaliza `real_estate.componentes_calculo` da [[ADR-216]] D9), forward via `LineageResolver` stateless, e reverso via tabela derivada. **Rejeitado `TracedValue`** (reescreveria a aritmética float dos calculadores, arrisca [[ADR-090]]/[[ADR-111]]).

**Decisão:**
- Bloco `_lineage` inline: `{value (Decimal string), label, transform, rule_ref, edge_type, signals, member_hashes, inputs}`. Invariantes: zero timestamp/UUID, `inputs` sorted, `value` espelhado (gate em cents int), folha = `data_source_id`/`SourceRef[]`.
- `LineageResolver` read-only, stateless ([[ADR-111]]) — nós `dangling`/`no_lineage`, nunca exceção.
- Tabela `artifact_lineage_edge` derivada/rebuildável via stage terminal `materialize_lineage`; `rule_ref` como coluna TEXT; índices `(workspace_id, rule_ref)` e `(workspace_id, source_document_id)`.
- **B6:** `materialize_lineage` faz `DELETE` cross-run — janela de retenção = **último run por workspace (N=1)** ([[ADR-241]] matou o GC implícito de `pipeline_artifacts`; edges field-level multiplicam ~10-100×, e a tabela é rebuildável). Diff de regressão (`lineage_diff`) usa o `_lineage` inline, não a edge table — então N=1 não prejudica debug histórico. Revisar N se a query de impacto reversa precisar de mais runs.
- **B8:** `member_hashes` = K4 sobreviventes pós-dedup, resolver ancora lookup ao `run_id` do agregado (não most-recent workspace-scoped). Gate `check_lineage_sum`.
- `_lineage` declarado em `e5_analysis.schema.json` antes/junto do flip→strict (PLATFORM_REVIEW W6-T01).
- **Guard-rails de regressão (revisão multi-agente 2026-06-03; estratégia de teste, não arquitetura — sem ADR nova):** como snapshot prova `≠` e não `correto`, o número se protege por **(a)** `dev/golden_diff.py` valor-a-valor em cents int + **snapshot do view-model** de `/reports/[id]/data` com asserção de completude `monetary_fields ⊆ snapshot` (fecha o débito **DE-005**); **(b)** invariantes de conservação por balde (`patrimônio == Σcategorias − dívidas`) que sobrevivem ao rebaseline; **(c)** disciplina de rebaseline — `check_golden_rebaseline_isolation` (golden + código no mesmo commit → falha) + manifesto justificado por valor + 2º revisor. Lane `dl-f1-golden-substrate` ([[A23.l2]]) entrega (a)/(b) **antes** de F2 tocar golden. Pixel/visual **não** é gate de F2/F3 (subpixel não pega R$1.2M→R$1.2M+100) — só na F6 (UI nova). Detalhe em [[PLAN-data-lineage]] §Guard-rails de regressão.

**Consequências:**
- ✅ Todo número de alto valor fica rastreável até a fonte (forward via `LineageResolver`) e a fonte fica rastreável até os números que dependem dela (reverso via `artifact_lineage_edge`). Generaliza o `componentes_calculo` ([[ADR-216]] D9) para todo agregado de decisão.
- ✅ Aditivo no `content_json` (`additionalProperties:true`) — F1 não rebaselina; F3 grava `_lineage` nos calculadores E5 (rebaseline E5 esperado, **auditável** via `golden_diff` + manifesto justificado, G-c).
- ⚠️ `_lineage` precisa estar declarado em `e5_analysis.schema.json` **antes/junto** do flip→strict (PLATFORM_REVIEW W6-T01) — dependência cross-plano a coordenar.
- ⚠️ Determinismo do payload garantido por gate (zero timestamp/UUID, `inputs` sorted, run 2× byte-idêntico, `value` espelhado em cents int + `check_lineage_sum`) + snapshot do view-model (G-a/G-b).
- ⚠️ `artifact_lineage_edge` é derivada/rebuildável (retenção N=1) — **não** fonte primária; reconstruível por `materialize_lineage`. MCP prod + índice reverso por `rule_ref` deferidos até o loop de debug fechar sobre goldens (F7).
- ℹ️ **Nota F4 (A24.l4):** a camada 3 da citação verificada E5→E6 confere **magnitude** (match em cents exato ou meia-casa-significativa para prosa abreviada), não semântica — colisão de valor entre paths distintos é resíduo aceito.
