---
id: MOC-sprint-a23
type: moc
title: "Sprint A23 — Data Lineage backbone (walking skeleton)"
aliases: ["A23", "Sprint A23"]
sprint_status: done
date: "2026-06-02"
theme: "data-lineage"
---

# Sprint A23 — Data Lineage: contrato aditivo + fonte plugável

> **Status:** `done` — A23 entregou as **Ondas 0–1** (gate F0 + contrato aditivo)
> 100% em `main`: 7 lanes de contrato ([[A23.l1]]/[[A23.l2]]/[[A23.l3]]/[[A23.l5]]/
> [[A23.l6]]/[[A23.l7]]/[[A23.l8]]) + [[A23.l4]] (D6) slices 1–3. Gates G0/G1 verdes
> **sem rebaseline** (aditividade provada). Transição `current → done`; corrente passa
> a [[MOC-sprint-a24]]. A fase de RISCO (F2 de-leak + F3 walking skeleton + F4
> evidencia_path) foi recortada para uma sprint própria — ver [[MOC-sprint-a24]]
> (decisão de corte: product-manager 2026-06-09, isola perfil de risco da fundação
> aditiva já estável).
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

A A23 entregou **apenas as Ondas 0–1 (gate F0 + contrato aditivo)** — fundação
golden-safe. As Ondas 2–3 (de-leak + walking skeleton) foram recortadas para
[[MOC-sprint-a24]] (fase de risco isolada); F5/F6/F7 (reverso, produto N1/N2, debug
substrate completo) para [[MOC-sprint-a25]].

## Sprint goal (entregue)

> **Contrato aditivo + fonte plugável prontos, golden-safe.** O artefato E2 vira
> contrato canônico endurecido (`natural_key` v2, `amount` decimal, `direction`,
> `source_ref`), a origem é plugável (`data_source`/`SourceRef` + FK DB), e o critério
> de pureza de extração está travado por gate — tudo **sem rebaseline** (G1).
>
> O goal de localização do patrimônio líquido (G3 / walking skeleton) foi recortado
> para [[MOC-sprint-a24]] (fase de risco).

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
- **Onda 2 — De-leak (gargalo) ∥ E5→E6:** → **recortada para [[MOC-sprint-a24]]**
  (fase de risco isolada).
- **Onda 3 — Backbone (walking skeleton):** → **recortada para [[MOC-sprint-a24]]**.

Detalhe de prioridade/ondas + mapeamento onda→sprint em [[PLAN-data-lineage]] §Ondas.

## Estado atual (atualizado 2026-06-09)

| Lane | Escopo | Status | PR |
|------|--------|--------|----|
| [[A23.l1]] | F0 — gate das 4 ADR (B1–B8) + emenda [[ADR-146]] | ✅ shipped | — (docs) |
| [[A23.l2]] | `dl-f1-golden-substrate` — `golden_diff` + view-model snapshot + invariantes (fecha DE-005) | ✅ shipped | #552 |
| [[A23.l3]] | `dl-f1-natural-key` — K4 v2 (moeda+direction+hash_version), B3/B4 passo 1 | ✅ shipped | #553 |
| [[A23.l5]] | `dl-f1-data-source` — tabela `data_source` + `data_source_id` + `SourceRef` ([[ADR-278]]); `SourceAdapter` + FK DB adiados | ✅ shipped | #564 |
| [[A23.l6]] | `dl-f1-amount-decimal` — campo `amount` decimal ao lado de `valor` (B5) | ✅ shipped | #567 |
| [[A23.l7]] | `dl-f1-extract-check` — `check_extract_no_domain_imports` (critério [[ADR-280]]) | ✅ shipped | #568 |
| [[A23.l8]] | `dl-f1-migration-runbook` — runbook PITR das migrations + FK DB (G-e) | ✅ shipped | #569 |
| [[A23.l4]] | D6 — alinhar 3º hash (`TransactionOverride`) ao K4 v2 ([[ADR-282]]); slices 1–3 (expand aditivo) | 🚧 in_progress (P0) — slices 1–3 ✅ | #556/#562/#563 ✅ |

**Onda 0 fechada; Onda 1 (contrato aditivo) COMPLETA** (7/7 lanes de contrato shipped:
[[A23.l1]]/[[A23.l2]]/[[A23.l3]]/[[A23.l5]]/[[A23.l6]]/[[A23.l7]]/[[A23.l8]]; +[[A23.l4]]
D6, P0, slices 1–3 ✅, slices 4–5 cutover/M2 → A24). Os prompts de orquestração da onda
foram arquivados em [agent_prompts/archive/](../../agent_prompts/archive/). Ondas 2–3
(de-leak + backbone) abrem agora que o contrato aditivo está fechado.

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
flip→strict do PLATFORM_REVIEW W6-T01 ([PLAN-platform-review](../../archive/PLATFORM_REVIEW_PLAN-2026-07-08.md)) — coordenar para
dois agentes não colidirem no schema.
