---
id: PLAN-pipeline-review-r2
type: plan
title: "Pipeline Review r2 — remediação dos achados sistêmicos (run 9d47574c, ws-1b9f2cf5)"
status: in_progress
created_at: 2026-07-27
last_review: 2026-07-27
sprint_origem: A39
sprint_atual: A39
sprints_envolvidas: [A39]
paused_at: null
pause_reason: null
adrs_canonical:
  - "[[ADR-343]]"
relates_to:
  - "[[PLAN-ledger-integrity]]"
tags:
  - type/plan
  - status/in-progress
  - area/pipeline
  - area/backend
---

# Pipeline Review r2 — remediação

> Origem: skill `pipeline-review` ([[ADR-343]]), run `9d47574c` em origin/main #1089,
> registrado em [[PIPELINE-REVIEWS-active]] §r2 (PR #1091). 25 achados sistêmicos
> acionáveis (26 − RV2-01, **parkado por decisão do owner**). Síntese crua + baseline:
> `storage/1b9f2cf5-…/reviews/20260727-1835-9d47574c/` (off-git, PII).

## Princípio de execução (decisão senior-cto)

1. **Conformance-first.** A maioria dos achados é **gap contra ADR já Decidida** — implementar à conformidade, **sem reabrir a decisão** (CLAUDE.md §"não delegue para… mudança que apenas conforma a ADR existente"). Poucos exigem ADR novo.
2. **Colisão-zero.** RV2-02/05/17 (gate/conservação) pertencem ao workstream **ATIVO** [[PLAN-ledger-integrity]] / [[ADR-347]] (A39) + [[ADR-342]] (amendada 2026-07-27), com worktrees vivos. **Não abrir PR concorrente** — registrar como follow-up e sinalizar aos donos.
3. **Ordem:** correção/domínio → contrato → citação (com eval) → UX. Relatório errado corrói confiança antes de qualquer refinamento.

## Ondas

### Onda A — domínio (conformance a ADR decidida)

| Achado | Defeito (âncora) | ADR | Tipo | Status |
|---|---|---|---|---|
| RV2-03 | nota PGBL "teto atingido" sem branch por `PgblStatus` · `previdencia_analyzer.py:168-176` | [[ADR-305]] | conformance | 🚧 em execução |
| RV2-08 | `exposicao_cambial` omite bucket Internacional · `exposicao_cambial_analyzer.py` | [[ADR-193]] · [[ADR-224]] | conformance | aberto |
| RV2-19 | aluguel IRPF vs banco (bases distintas) sem disclosure | [[ADR-306]] | conformance | aberto |
| RV2-26 | `premio_decomposicao` 100% "auto" apesar de apólice multi-bem | — | fix | aberto |
| RV2-21 | `diagnostico_comportamental` sem degradê por cobertura de categorização | — | fix | aberto |
| RV2-15 | `cenarios_conjuge` unidimensional + retorno vs meta | — | fix | aberto |
| RV2-18 | cascata `perfil_incompleto` sem nudge PJ + detecção PJ inconsistente | [[ADR-268]] | fix | aberto |
| RV2-20 | `premissas_economicas` global vazia p/ o período (seed) | — | config | aberto |

### Onda B — contrato do view-model E5 (1 ADR novo + refactor)

| Achado | Defeito (âncora) | ADR | Tipo | Status |
|---|---|---|---|---|
| RV2-06 | money/pct string vs number no E5 | [[ADR-090]] | conformance | aberto |
| RV2-07 | PII como CHAVE de dict em `fluxo_caixa.por_fonte_detalhado` | [[ADR-332]] | conformance + contrato | aberto |
| RV2-12 | `alertas[]` top-level dead field + alertas de imóvel sem surface global | [[ADR-129]] | contrato novo | aberto |
| RV2-14 | `_report_lineage` truncado + ID scheme incompatível | [[ADR-278]] | fix | aberto |
| RV2-22 | `pipeline_run_costs` dead schema (drop) | [[ADR-173]] | cleanup | aberto |

Co-design: `data-engineer` + `product-designer`. ADR novo de **contrato do view-model E5** (money=number, id estável, sem PII-key, shape de alertas).

### Onda C — citação do parecer (sem RV2-01)

| Achado | Defeito (âncora) | ADR | Tipo | Status |
|---|---|---|---|---|
| RV2-10 | riscos citam % na prosa com `ancoras=[]` fora do verify | [[ADR-304]] | extensão (R$→%) | aberto |
| RV2-11 | `evidencia_verification.item_index` out-of-range vs `riscos[]` | [[ADR-293]] | fix | aberto |
| RV2-09 | parecer rotula `receita_pj_pct` como "% da receita" (base trocada) | — | exec-context | aberto |
| RV2-24 | limiar de poupança 30% (parecer) vs 25% (E5) | [[ADR-143]] | fonte única | aberto |
| RV2-25 | `field_request_spurious` p/ `[]` (null-semantics) | — | fix | aberto |

Co-design: `prompt-engineer` + golden eval. **RV2-01 fora** (parkado).

### Onda D — plano de ação & identidade

| Achado | Defeito (âncora) | ADR | Tipo | Status |
|---|---|---|---|---|
| RV2-04 | parecer `sugestoes_*` não consolidam em `tarefas[]` | — | contrato | aberto |
| RV2-13 | identidade de imóvel fragmentada (property_id divergente) | [[ADR-246]] | conformance | aberto |
| RV2-23 | `needs_review` pós-completed sem surface no view-model | — | fix | aberto |

## Coordenado — NÃO abrir PR aqui (workstream ativo)

| Achado | Onde vive | Ação |
|---|---|---|
| RV2-02 | `extract_with_llm` success mascara skip → **[[ADR-342]]** (anti-silêncio E2) | verificar cobertura; se gap, follow-up ao dono do ADR-342/e2-antisilence |
| RV2-05 | CV16/CV17 fora do gate de conservação → **[[ADR-347]]** / [[ADR-330]] / [[ADR-336]] | escopo do gate é decisão A39; propor CV17 no gate como follow-up ao ADR-347 |
| RV2-17 | ledger de contagem E2→E4 → **[[ADR-347]]** (Proposto) / [[PLAN-ledger-integrity]] | já é o escopo do plano ativo — não duplicar |

## Parkado

- **RV2-01** — parecer fabrica métrica sem âncora (`parecer.metricas[]` fora do verify). Parkado por decisão do owner (2026-07-27); reabrir sob demanda.

## Critério de aceite (por onda)

- **Cada fix:** teste de regressão ANTES do fix (bug reproduzido), conformidade ao ADR citado, `pre-commit` verde, sem PII, PR squash com CI verde.
- **Onda B/C:** ADR novo/estendido referenciado no PR, flip `Decidido` no merge; eval golden na Onda C.
- **Coordenado:** zero PR concorrente; follow-ups registrados nos ADRs donos.
