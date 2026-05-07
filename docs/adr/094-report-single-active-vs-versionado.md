---
id: ADR-094
type: adr
title: "Report: single-active vs. versionado"
status: Decidido
phase: "single-active para F9; evolução planejada"
date: "2026-04-19"
relates_to: []
supersedes: []
superseded_by: []
aliases: ["ADR 094"]
tags:
  - area/persistence
  - area/pipeline
  - area/report
  - status/decidido
  - type/adr
size_lines: 40
---

# ADR-094 — Report: single-active vs. versionado

**Status:** Decidido (single-active para F9; evolução planejada) • **Data:** 2026-04-19 • **Plano:** §4.5

**Contexto:** Com artefatos migrando para `pipeline_artifacts` (ADR-082),
a coluna `Report.analysis_json_path` (string apontando para arquivo) passa
a ser `Report.artifact_id` (FK opcional para o E5 da run). Re-run do pipeline
cria um novo `PipelineArtifact` E5; precisamos decidir se o Report aponta
para o **novo** (overwrite) ou mantém **histórico versionado**.

**Alternativas:**
1. **Single-active** (escolhida para F9): um relatório ativo por workspace;
   re-run sobrescreve o ponteiro.
2. **Versionado** (iteração futura): nova tabela `ReportVersion` com FK para
   Report + pipeline_run_id; UI pode mostrar múltiplas versões.

**Decisão:** **Single-active** na Fase 4 do plano de migração. Justificativas:

- Simplicidade: Report.artifact_id é a única FK de relatório.
- UI sem decisão "qual versão mostrar" (atual sempre válida).
- Os `PipelineArtifact`s históricos permanecem no banco — não há perda
  de dados, apenas ausência de apresentação.
- Menor peso no DB: um ponteiro ativo por workspace.

**Caminho evolutivo previsto (não este sprint):**

1. Fase 4: single-active entregue.
2. Sprint futuro: introduzir `ReportVersion(report_id, pipeline_run_id, artifact_id, created_at)`
   — todos os dados necessários já existem em `pipeline_artifacts`.
3. Decisão guiada por métrica de produto: % de usuários que consultam
   relatórios anteriores via workarounds (export HTML, screenshots).

**Consequências:**
- ✅ Fase 4 cabe num sprint (~5 dias).
- ✅ UI inalterada — migração transparente para o usuário.
- ⚠️ Histórico só acessível via query/script até ReportVersion existir.
- ❌ Usuários que re-rodam e querem comparar com versão anterior precisam
  exportar HTML antes do re-run (documentado em release notes).
