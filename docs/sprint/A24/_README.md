---
id: MOC-sprint-a24
type: moc
title: "Sprint A24 — Data Lineage: extração limpa + walking skeleton"
aliases: ["A24", "Sprint A24"]
sprint_status: current
date: "2026-06-09"
theme: "data-lineage"
---

# Sprint A24 — Data Lineage: extração limpa + walking skeleton

> **Status:** `current` — promovida em 2026-06-09, sucedendo [[MOC-sprint-a23]]
> (`done`, Ondas 0–1 entregues). Esta é a **fase de RISCO** do plano
> [[PLAN-data-lineage]]: o de-leak da extração (toca goldens E2/E3/E4 + dedup
> [[ADR-246]]/[[ADR-271]]) e o walking skeleton do lineage. Recortada em sprint própria
> (decisão product-manager 2026-06-09) para isolar o perfil de risco da fundação
> aditiva já estável em A23.
>
> **Plano dono:** [[PLAN-data-lineage]] ([plan/DATA_LINEAGE/_README.md](../../plan/DATA_LINEAGE/_README.md)).

## Resumo

A23 entregou o contrato aditivo (golden-safe, zero rebaseline). A A24 exerce o RISCO
que A23 não tocou: **mover transformação que vaza na extração** (`tipo_lancamento`,
`numero_conta_norm` — [[ADR-280]]) e **montar o backbone de lineage** field-level
([[ADR-279]]) até o walking skeleton (patrimônio líquido localizável por 1 comando).
Inclui a malha de verificação E5→E6 (`evidencia_path`, paralela e independente).

**Achado da revisão de risco (senior-cto + data-engineer, 2026-06-09):** o de-leak em
si é **cirúrgico, não sistêmico** — `tipo_lancamento` é dead-downstream (zero
consumidores em `pipeline/`/`backend/`; morre no dict E2) e `numero_conta_norm` já é
re-normalizado em todo consumidor (`document.from_e2_dict` fallback). **O risco real
está na rede de rebaseline**, não em mover os campos. Daí os blockers F2-B/F2-DB (§Gate
G2) endurecem o substrato ANTES do primeiro rebaseline.

## Sprint goal

> **G3 — walking skeleton:** equipe localiza a origem do **patrimônio líquido** *sem
> abrir um único arquivo de stage*, via 1 comando CLI, num run canônico — com
> `check_lineage_sum` provando `Σ amount[member_hashes] == value` (cents int) e o
> mesmo run 2× produzindo o **view-model snapshot byte-idêntico** (não o payload E2
> bruto — F2-B8). KR mensurável: **KR2 1/6** (patrimônio líquido fim-a-fim).

## Gate G2 — blockers da F2 (de-leak), travados antes do 1º rebaseline

Revisão multi-agente (senior-cto boundary + data-engineer contrato/dados, 2026-06-09).
Detalhe canônico em [[PLAN-data-lineage]] §"Blockers da F2". Resumo dos P0:

| # | Blocker | Resolução |
|---|---------|-----------|
| **F2-DB7** | invariantes de conservação não cobrem decomposição por categoria (Goodhart: mover tx entre categorias mantém totais e passa) | +invariante `Σ categoria == total` (despesa/receita, cents int) em `test_e5_conservation_invariants` |
| **F2-DB6** | `ManifestEntry` (`golden_diff.py`) não carrega justificativa | estender com `reason` (file:line) + `adr` obrigatórios |
| **F2-DB5** | `check_golden_rebaseline_isolation.py` não existe | criar (golden + código de produção no mesmo commit → falha) — antes do 1º rebaseline |
| **F2-DB1/B5** | remover campo quebra contrato fechado [[ADR-283]]; gate pega import, não regex inline | enforcement por **ausência-de-campo** (`test_e2_contract_no_methodological_fields`) + remover do schema na mesma PR + ampliar gate com `account_normalization` |
| **F2-DB2** | reshape do hint `{value,origin,confidence}` é breaking em 3 superfícies | **DEFERIDO** — F2 só anexa `origin=llm_extract` flat (mín. aditivo); objeto aninhado é follow-up |

## Ondas (mapeamento de fase)

```
A24:  F2-discovery(G2) ──► F2-deleak-account-norm ──► F3-skeleton-patrimonio(G3) ──► F3-resto
                      └──► F2-deleak-tipo-lancamento (∥) ──┘
                      └──► F4-evidencia-path (∥, independe de F2/F3) ──────────────┘
```

- **F2 (de-leak):** discovery (gate, blast radius **sobre dogfood** — fixtures não
  exercitam os campos, F2-DB8) → re-fatiado **por vazamento** (F2-B6): `deleak-account-norm`
  (no-op de golden + amplia gate) e `deleak-tipo-lancamento` (delete/contrato). Substrato
  endurecido primeiro (F2-DB5/6/7).
- **F3 (walking skeleton):** `_lineage` no `patrimonio_calculator` + `lineage_registry`
  + `LineageResolver` + CLI + `check_lineage_refs`/`check_lineage_sum`. Depois os outros
  calculadores (G3 → KR2 1/6).
- **F4 (∥ independente):** `evidencia_path` condicional-obrigatório no validator Pydantic
  ([[ADR-279]] §E) — pode abrir já.

## Estado atual

F2 + F4 entregues em 2026-06-09/10 (zero rebaseline — de-leak confirmado cirúrgico). Lanes criadas em 2026-06-09 (co-design `senior-cto` + `data-engineer` p/ F2;
`prompt-engineer` + `data-engineer` p/ F4 — decisões registradas em cada lane):

| Lane | Slug | Status | Dep |
|---|---|---|---|
| [[A24.l1]] | `dl-f2-discovery` (gate G2 + substrato F2-DB5/6/7) | ✅ shipped (#578) | — |
| [[A24.l4]] | `dl-f4-evidencia-path` (∥ independente) | ✅ shipped (#580) | — |
| [[A24.l2]] | `dl-f2-deleak-account-norm` | ✅ shipped (#585) | l1 |
| [[A24.l3]] | `dl-f2-deleak-tipo-lancamento` | ✅ shipped (#586) | l1 |
| [[A24.l5]] | `dl-f3-skeleton-patrimonio` (G3) | in_progress | l2+l3 ✅ |
| [[A24.l6]] | `dl-f3-skeleton-resto` | blocked | l5 |

Prompt de orquestração:
[agent_prompts/orchestrator_a24_f2f3.md](../../agent_prompts/orchestrator_a24_f2f3.md).

## KRs da janela

- **KR2 1/6** — patrimônio líquido com lineage fim-a-fim + `check_lineage_sum` verde (atingido em G3).
- Processo: tempo de localização "número errado → função" cai de E0→E5 manual para 1 comando CLI.
