---
id: ADR-122
type: adr
title: "`chart_conclusions` e `section_summaries` em modo híbrido (template + LLM)"
status: Decidido
phase: "Fase 0"
date: "2026-04-23"
relates_to: []
supersedes: []
superseded_by: ["[[ADR-144]]"]
aliases: ["ADR 122"]
tags:
  - area/llm
  - area/pipeline
  - area/report
  - status/decidido
  - type/adr
size_lines: 46
---

# ADR-122 — `chart_conclusions` e `section_summaries` em modo híbrido (template + LLM)

**Status:** Decidido (Fase 0) • **Data:** 2026-04-23

> **Nota (2026-04-27):** parte LLM (`section_summaries`) parcialmente
> superseded por [ADR-144](#adr-144--section_summaries-llm-driven-em-e5-com-cache--fallback-determinístico-v29)
> — desenho híbrido continua válido (chart_conclusions determinístico,
> section_summaries LLM); D144 fecha lacunas operacionais de cache,
> fallback, telemetry e diferenciação cache-runtime vs ArtifactStore que
> D122 deixou em aberto antes de ADR-111 (stateless rigoroso) e
> ADR-127/128 (contrato ArtifactStore para LLM).

**Contexto:** Cada gráfico do relatório premium fica acompanhado de um
`.chart-conclusion` (leitura curta do que o gráfico mostra) e cada seção
tem uma `.section-summary` no topo. O exemplo tem ~21 charts e ~10 seções
→ 31 textos por relatório. Opções: (a) templates determinísticos —
baratos, previsíveis, mas narrativamente engessados; (b) LLM — ricos,
variáveis, caros e introduzem primeira dependência Anthropic em E5;
(c) input manual do consultor — não escala.

**Decisão:** **Híbrido determinado pelo tipo**:

- **Templates determinísticos** para `chart_conclusions`. Cada chart tem
  regra em `config/prompts/chart_conclusions.yaml` que monta frase a partir
  dos dados do snapshot (ex.: `despesas_doughnut` → "{top_categoria}
  representa {pct}% das despesas recorrentes"). Fallback neutro quando
  dados insuficientes.
- **LLM** para `section_summaries` — 10 textos narrativos por snapshot,
  `temperature=0`, cache Redis por hash `(section_id, snapshot_hash)` com
  TTL 7d. Prompt template em `config/prompts/section_summaries.md`.
  Custo estimado: ~10 chamadas Claude Haiku 4.5 por relatório ≈ $0.01.
- **Fallback:** se Anthropic key ausente ou LLM falhar, cair para template
  determinístico simples ("Seção X — {kpi_principal} em {valor}").

**Consequências:**
- ✅ 70% dos textos (charts) são determinísticos — zero custo, zero latência.
- ✅ 30% narrativos (sections) ganham qualidade editorial real.
- ⚠️ Primeira dependência Anthropic em E5 (até agora só E0/E1 chamavam LLM).
  Exige: Anthropic key no worker Celery, cache Redis, fakes por hash nos testes.
- ❌ Determinismo parcial — mesmo snapshot pode gerar summaries levemente
  diferentes se cache expira; aceito (usuário vê variação < entre snapshots
  diferentes).

Relaciona-se a: ADR-024 (LiteLLM), ADR-025 (BYOK), ADR-117.
