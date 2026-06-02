---
id: MOC-sprint-a23
type: moc
title: "Sprint A23 — Data Lineage backbone (walking skeleton)"
aliases: ["A23", "Sprint A23"]
sprint_status: candidate
date: "2026-06-02"
theme: "data-lineage"
---

# Sprint A23 — Data Lineage backbone (walking skeleton)

> **Status:** `candidate` — criada 2026-06-02. Janela 1 do plano
> [[PLAN-data-lineage]] (lineage fim-a-fim + fonte plugável + extração limpa).
> Promover sobre A18/A19 é decisão do owner; registrada como candidate na fila.
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
- **Onda 1 — Contrato aditivo (golden-safe):** `natural_key`+moeda+direction (B3/B4),
  `data_source`+`SourceRef`, `amount` decimal (B5), `check_extract_no_domain_imports`.
  Gate G1: goldens E3/E4/E5 verdes **sem rebaseline**.
- **Onda 2 — De-leak (gargalo) ∥ E5→E6:** discovery dimensionado (gate) → de-leak
  slice1 → residual (∥). `evidencia_path` condicional-obrigatório (F4, paraleliza,
  independe de F2/F3).
- **Onda 3 — Backbone (walking skeleton):** `_lineage` no `patrimonio_calculator`
  + `lineage_registry` + `LineageResolver` + CLI + gates `check_lineage_refs`/
  `check_lineage_sum`. Depois os outros 3 calculadores.

Lanes F1+ são criadas **sob demanda quando o F0 mergear** (gate serial). Detalhe
de prioridade/ondas em [[PLAN-data-lineage]] §Ondas.

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
