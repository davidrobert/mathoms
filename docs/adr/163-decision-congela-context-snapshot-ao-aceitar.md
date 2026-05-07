---
id: ADR-163
type: adr
title: "Decision congela `context_snapshot` ao aceitar Suggestion"
status: Decidido
phase: "Onda 8"
date: "2026-05-04"
relates_to: ["[[ADR-136]]", "[[ADR-153]]", "[[ADR-161]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 163"]
tags:
  - area/persistence
  - methodology/auvp
  - methodology/cerbasi
  - methodology/perini
  - status/decidido
  - type/adr
size_lines: 47
---

# ADR-163 — Decision congela `context_snapshot` ao aceitar Suggestion

**Status:** Decidido (Onda 8) • **Data:** 2026-05-04 • **Relaciona** [ADR-136](#adr-136--decision-aggregate-event-sourced-com-supersede-chain), [ADR-153](#adr-153--suggestion-aggregate-direção-e--onda-5-proposal-imutável--state-machine-simples), [ADR-161](#adr-161--regras-canônicas-de-suggestion-v2-cerbasiauvpperini-completos).

**Contexto:** Race condition temporal: Suggestion gerada em fevereiro com `progresso_if=42%` aceita em maio quando o KPI virou 48%. Decision referencia Suggestion fevereiro mas decisão foi tomada com base no contexto de fevereiro — depois fica perdido qual era o estado quando a decisão foi tomada. Usuário lê DecisionCard em julho e não consegue auditar "o que estava acontecendo quando a decidi?".

**Decisão:** Ao aceitar uma Suggestion (`accept_suggestion` use case), a Decision criada recebe um campo `context_snapshot: JSONB` populado com KPIs do **relatório que originou a Suggestion** (não estado atual do workspace) — congelando o "porquê" da decisão.

**Schema:**

```json
{
  "patrimonio_brl": 1234567.89,
  "if_progress_pct": 42.0,
  "trs_pct_when_decided": 4.5,
  "report_id": "rep-abc",
  "report_period": "2026-02"
}
```

**Sub-decisões:**

1. **Origem dos dados:** lê do `report.analysis_artifact.content_json` referenciado em `suggestion.report_id`. Se `report_id` é `NULL` (Suggestion legada) ou snapshot não tem o KPI → campo fica `null` no JSON, não bloqueia aceitação.

2. **Schema `context_snapshot`** é JSONB **não-validado** por Pydantic — payload evolui livre conforme novos KPIs entram no relatório. Apenas chaves "padronizadas" (acima) são consumidas pela UI; chaves desconhecidas ficam disponíveis para auditoria via API mas não são exibidas.

3. **Migration `e0f1a2b3c4d5_adr162_163`**: adiciona `decisions.context_snapshot JSONB nullable` (no mesmo migration que os campos `target_*` do ADR-162 — ambos tocam `decisions` e foram aplicados juntos). Decisions pré-migration ficam `NULL` — UI degrada para "contexto não capturado".

4. **Não congela TUDO do snapshot.** Apenas KPIs editoriais relevantes (5-7 campos). Snapshot bruto (~24 campos top-level) seria payload pesado e maioria irrelevante para auditoria.

5. **DecisionCard exibe "Decidida com base em: Patrimônio R$ 1,2M, IF 42%, TRS 4.5%"** no expand quando `context_snapshot` popula. Esses são os valores **frozen** — não os atuais.

**Consequências:**

- ✅ Auditoria temporal: Decision sempre carrega o "porquê" original. Útil para revisões trimestrais e supersede chain (ADR-136).
- ✅ Mínimo overhead — JSONB com 5 campos numéricos é <100 bytes. Sem índice (não consultado por valor).
- ✅ Backward-compatible: NULL para Decisions legadas; UI degrada graciosamente.
- ⚠️ Suggestion sem `report_id` → snapshot vazio. Aceitável (Suggestion editada manualmente sem origem rastreável).
- ⚠️ Schema JSONB livre exige cuidado em consumo: UI/API precisa lidar com chaves ausentes. Compensado pela exibição opt-in (só mostra se field existir).
- ❌ Não captura state derivado de outros aggregates (Tasks, Notes) — fora do escopo MVP.

**Follow-ups:**

1. Snapshot enrichment quando Decision é editada (não só na aceitação) — caso usuário re-decide com novo contexto. Defer para Onda 9.
2. Diff visual "Decidida com base em X% / Hoje está Y%" — comparativo automático entre `context_snapshot.if_progress_pct` e Goal vigente. Requer cross-aggregate query, defer.
