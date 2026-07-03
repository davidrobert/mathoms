---
id: A28.l3
type: lane
title: "PGBL: regra de ano-base único — uma recomendação por relatório"
sprint: A28
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: pgbl-ano-base-unico
adrs: []
parallel_with:
  - "[[A28.l4]]"
  - "[[A28.l2]]"
tags:
  - type/lane
  - sprint/a28
  - status/open
  - priority/p0
  - area/e5
---

# A28.l3 — `pgbl-ano-base-unico` (Onda 0 · Must)

## Problema

O dogfood `72883bde` dá **duas recomendações fiscais opostas** no mesmo
relatório:

- `previdencia_pgbl`: "Sem capacidade PGBL restante no ano-base **2024** (teto
  atingido)", `limite_pgbl_anual = 0`, `aporte_mensal = 0`.
- `irpf_kpis`: `pgbl_status = capacidade_disponivel`,
  `pgbl_capacidade_dedutivel_brl = 123.004,52`, `pgbl_aportado = 0`, ano-base
  **2025** — com `ano_base_completude = incompleto` (falta a declaração de um
  dos CPFs presentes em ano anterior).

Raiz: **reconciliação de ano-referência**, não de fórmula — uma seção lê 2024
fechado, outra lê 2025 parcial. O cliente não sabe se tem R$ 123k de espaço
dedutível ou zero. Contradição interna quebra a confiança no relatório inteiro.

## Escopo

1. **T0 — ADR `Proposto` curta de regra de ano-base PGBL** (co-design
   `financial-planner`). Proposta inicial: usar o **ano-base mais recente
   completo** (todas as declarações dos membros presentes); se o mais recente
   for incompleto, degradar com nota explícita ("cálculo sobre 2024; 2025
   incompleto — falta declaração de X") em vez de escolher silenciosamente.
2. Fonte única de ano-base: `previdencia_pgbl` e `irpf_kpis` derivam do mesmo
   campo decidido (provável consolidação em um serviço/campo compartilhado —
   `ano_base_default` vs `ano_base` hoje divergem).
3. Uma única recomendação PGBL por relatório: capacidade, aporte sugerido e
   economia de IR calculados sobre o mesmo ano-base, com a completude declarada.
4. Golden re-snapshot com diff explicado.

## Critério de aceite

- ADR `Proposto` mergeada com a regra de ano-base; flippa `Decidido (A28)` no
  merge da implementação.
- Teste de invariante "**PGBL statement count == 1**": um relatório nunca
  contém `capacidade = 0` e `capacidade > 0` simultaneamente.
- Fixture com ano recente incompleto → cálculo sobre o último completo + nota
  de degradação presente no payload.
- `previdencia_pgbl.*` e `irpf_kpis.pgbl_*` derivam do mesmo ano-base (teste de
  igualdade de fonte).

## Notas

- Paralela com [[A28.l4]] e [[A28.l2]] (campos disjuntos).
- A completude por ano (`anos_completude_por_ano`) já existe no payload — a
  lane decide a **política** e unifica o consumo, não cria detecção nova.

## Owner

Agente da lane; co-design `financial-planner` no T0 (regra de domínio fiscal).
