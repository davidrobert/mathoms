---
id: MOC-sprint-a23
type: moc
title: "Sprint A23 — Data Lineage backbone (walking skeleton)"
aliases: ["A23", "Sprint A23"]
sprint_status: current
date: "2026-06-02"
theme: "data-lineage"
---

# Sprint A23 — Data Lineage backbone (walking skeleton)

> **Status:** `current` — promovida em 2026-06-02, sucedendo [[MOC-sprint-a22]]
> (`paused` com débito). Janela 1 do plano [[PLAN-data-lineage]] (lineage
> fim-a-fim + fonte plugável + extração limpa).
>
> **Plano dono:** [[PLAN-data-lineage]] ([plan/DATA_LINEAGE/_README.md](../../plan/DATA_LINEAGE/_README.md)).

## Resumo

Os bugs caros recentes são "número errado difícil de rastrear" (R$ 811k de
patrimônio inflado — dedup; [[ADR-271]]/[[ADR-246]]/[[ADR-255]]). A A23 ataca a
**confiabilidade rastreável do número**: monta o backbone de **data lineage**
(todo número de alto valor consultável até a fonte + transformações), acoplado à
**fonte plugável** (`SourceAdapter`/`SourceRef` — Open Finance amanhã sem
reescrever downstream) e à **extração limpa** (de-leak de transformação que vaza
nos parsers E2). O lineage é legível por LLM desde o dia 1 (bridge nó→código).

A A23 entrega **apenas as Ondas 0–3 (MVP/skeleton)** — patrimônio líquido
fim-a-fim. F5/F6/F7 (reverso, produto N1/N2, debug substrate completo) abrem
A24.

## Sprint goal

> Equipe localiza a origem do **patrimônio líquido** *sem abrir um único arquivo
> de stage*, via 1 comando CLI, num run canônico — com `check_lineage_sum`
> provando `Σ amount[member_hashes] == value` (cents int) e o mesmo run 2×
> produzindo `_lineage` byte-idêntico. Em paralelo, a fonte vira plugável
> (contrato canônico aditivo) e a extração fica genuinamente pura.

## Gate F0 (bloqueante absoluto)

Nenhuma lane F1+ abre antes de **B1–B8** travados na família de 4 ADR `Proposto`
([[ADR-278]] · [[ADR-279]] · [[ADR-280]] · [[ADR-281]]) + emenda [[ADR-146]].
Detalhes em [[PLAN-data-lineage]] §Blockers de corretude.

## Ondas

```
F0(G0) ──► F1(G1) ──► F2-discovery(G2) ──► F2-slice1 ──► F3-skeleton(G3) ──► [A24: F5 ∥ F6 ∥ F7]
                 └──► F4-evidencia-path ──────────────────┘ (paralelo)
                                          F2-residual ─────┘ (paralelo a F3)
```

- **Onda 0 — Gate:** `A23.l1` (P0) — fechar a família de ADR (B1–B8). **Docs-only**,
  mergeável sem CI verde, mas gate de raciocínio antes de qualquer código.
- **Onda 1 — Contrato aditivo (golden-safe):** começa por **`A23.l2` substrato de
  golden** (diff tool + snapshot do view-model + invariantes de conservação; fecha
  DE-005) **antes** de qualquer rebaseline; depois `natural_key`+moeda+direction
  (B3/B4), `data_source`+`SourceRef`, `amount` decimal (B5),
  `check_extract_no_domain_imports`, runbook de migrations (G-e). Gate G1: goldens
  E3/E4/E5 **+ snapshot do view-model + invariantes** verdes **sem rebaseline**.
- **Onda 2 — De-leak (gargalo) ∥ E5→E6:** discovery dimensionado (gate) → de-leak
  slice1 (com **disciplina de rebaseline**: commit isolado + manifesto justificado
  por valor + 2º revisor; G-c) → residual (∥). `evidencia_path`
  condicional-obrigatório (F4, paraleliza). Antes do merge: **diff de dogfood**
  (dado real do founder, local/gitignored; G-f).
- **Onda 3 — Backbone (walking skeleton):** `_lineage` no `patrimonio_calculator`
  + `lineage_registry` + `LineageResolver` + CLI + gates `check_lineage_refs`/
  `check_lineage_sum`. Depois os outros 3 calculadores.

Lanes F1+ são criadas **sob demanda quando o F0 mergear** (gate serial). Detalhe
de prioridade/ondas em [[PLAN-data-lineage]] §Ondas.

## Estado atual (atualizado 2026-06-08)

| Lane | Escopo | Status | PR |
|------|--------|--------|----|
| [[A23.l1]] | F0 — gate das 4 ADR (B1–B8) + emenda [[ADR-146]] | ✅ shipped | — (docs) |
| [[A23.l2]] | `dl-f1-golden-substrate` — `golden_diff` + view-model snapshot + invariantes (fecha DE-005) | ✅ shipped | #552 |
| [[A23.l3]] | `dl-f1-natural-key` — K4 v2 (moeda+direction+hash_version), B3/B4 passo 1 | ✅ shipped | #553 |
| `dl-f1-data-source` | tabela `data_source` + `data_source_id` + `SourceRef`/`SourceAdapter` ([[ADR-278]]) | 🔜 a criar (P0, central) | — |
| `dl-f1-amount-decimal` | campo `amount` decimal ao lado de `valor` (B5) | 🔜 a criar | — |
| `dl-f1-extract-check` | `check_extract_no_domain_imports` (critério [[ADR-280]]) | 🔜 a criar | — |
| `dl-f1-migration-runbook` | runbook PITR das migrations (G-e) | 🔜 a criar (após data-source) | — |
| [[A23.l4]] | D6 — alinhar 3º hash (`TransactionOverride`) ao K4 v2 ([[ADR-282]]); slices 1–3 (expand aditivo) | 🚧 in_progress (P0) — slice 1/3 ✅ | slice 1 #556 ✅ |

**Onda 0 fechada; Onda 1 em andamento** (3/7 lanes de contrato shipped; +[[A23.l4]]
D6, P0, em andamento). As 4 lanes de contrato restantes têm prompt de orquestração
self-contained em
[agent_prompts/orchestrator_a23_onda1_lanes.md](../../agent_prompts/orchestrator_a23_onda1_lanes.md)
(ordem, dependências, co-design por lane, guard-rails de aditividade G1). Ondas 2–3
(de-leak + backbone) abrem após a Onda 1.

**Dívidas/follow-ups conhecidos:**
- **D6** (dívida da [[A23.l3]]): `generate_transaction_hash` (`transaction_service.py`)
  incompatível com K4 v2 → decisão em [[ADR-282]] (Proposto); implementação em [[A23.l4]]
  (slices 1–3 aditivos em A23; cutover + M2 destrutiva em A24). Corrige bug **vivo** de
  orfanização de override (drift de sufixo PIX) **e** é pré-requisito do passo 2 de B4.
- **Passo 2 de B4** (`natural_key` nullable→obrigatório): gated por cobertura 100%
  (faturas resolverem titular) + cutover da [[A23.l4]] (slices 4–5 em A24).

## KRs da janela

- **KR2 (parcial):** 1/6 agregados de decisão (patrimônio líquido) com lineage
  fim-a-fim + `check_lineage_sum` verde.
- **Processo:** tempo de localização da origem de um número cai de "abrir E0→E5
  manual" para "1 comando CLI" (cravar baseline qualitativo no kickoff).
- KR1 (`localization_accuracy@node ≥85%`) e KR3 (`tool_iterations_p95 ≤6`) são de
  fim de plano (A24, F7) — a suite de injeção e a telemetria nascem lá.

## ADR Proposto antes do PR

Toda a Onda 0 é ADR `Proposto` (4 ADR + emenda). Lanes P0 de F1+ tocam escopo
arquitetural (schema DB, migration, contrato canônico) — cobertas pelo gate F0.

## Dependência cross-plano

`_lineage` precisa estar declarado em `e5_analysis.schema.json` **antes/junto** do
flip→strict do PLATFORM_REVIEW W6-T01 ([[PLAN-platform-review]]) — coordenar para
dois agentes não colidirem no schema.
