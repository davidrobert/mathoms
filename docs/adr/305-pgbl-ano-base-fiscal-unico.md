---
id: ADR-305
type: adr
title: "PGBL: ano-base fiscal único por relatório — irpf_kpis e previdencia_pgbl colapsam no ano-base default (ADR-266)"
status: Proposto
date: "2026-07-03"
relates_to:
  - "[[ADR-189]]"
  - "[[ADR-236]]"
  - "[[ADR-266]]"
  - "[[ADR-277]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 305"
  - "Ano-base fiscal único"
tags:
  - area/pipeline
  - status/proposto
  - type/adr
  - methodology/cerbasi
  - sprint/a28
---

# ADR-305 — PGBL: ano-base fiscal único por relatório

**Status:** Proposto • **Data:** 2026-07-03 • **Lane:** [[A28.l3]] `pgbl-ano-base-unico` • **Relaciona** [[ADR-266]] (completude tri-state + `pick_default_year`), [[ADR-277]] (previdência ancora no IRPF), [[ADR-189]] (4 estados PGBL), [[ADR-236]] (base PGBL = renda tributável PF)

## Contexto

O relatório dogfood `72883bde` contém duas recomendações fiscais opostas:
`previdencia_pgbl` diz "teto atingido, capacidade 0" lendo o ano-base **2024**
(completo); `irpf_kpis` diz `capacidade_disponivel` de R$ 123k lendo **2025**
(`ano_base_completude = incompleto` — falta a declaração de um CPF da família).

Raiz: reconciliação de ano-referência, não fórmula. `previdencia_pgbl` já usa
`ano_base_default()` ([[ADR-277]] · `_build_capacidade_pgbl`), mas `irpf_kpis`
usa o ano mais recente **disponível** (`anos[-1]` em `_e5_load_irpf_kpis`),
mesmo incompleto. Contradição interna quebra a confiança no relatório inteiro.

## Decisão

**D1 — Ano-base fiscal de reporte é único por relatório**, resolvido por
`pick_default_year` ([[ADR-266]]): o ano-base mais recente `completo`; se
nenhum, o `provisorio` mais recente; se nem isso, o `incompleto` mais recente.
`provisorio` (janela RFB aberta) degrada para o completo anterior por
**instabilidade do dado** (retificadora/pré-preenchida pendente), não por
preferência arbitrária.

**D2 — Consumo unificado.** Todos os KPIs fiscais pontuais (`irpf_kpis.*`:
renda familiar, alíquotas, split trabalho×capital, `pgbl_*`, dedutíveis,
dependentes) e a recomendação `previdencia_pgbl.*` (capacidade, aporte
sugerido, economia de IR) calculam sobre esse mesmo ano-base, resolvido em
**um único ponto** (`resolve_ano_base_fiscal`, domain service). Séries
multi-ano (`evolucao_renda_anos`, `anos_completude_por_ano`,
`anos_disponiveis`) permanecem multi-ano.

**D3 — Degradação explícita, nunca silenciosa.** Quando existe ano-base mais
recente que o escolhido, ambos os payloads carregam **duas notas**
concatenáveis:

- *degradação*: "Cálculo sobre o ano-base 2024; 2025 incompleto — Falta
  declaração de CPF ***.XXX.XXX-** (presente em ano-base anterior)."
- *proxy retrospectivo* (financial-planner, co-design 2026-07-03): a
  capacidade lida do IRPF é retrospectiva — o espaço dedutível de 12% aplica-se
  ao ano-calendário **corrente** (aporte até 31/12 deduz na próxima
  declaração). A renda do último ano completo entra como **proxy** da renda
  recorrente; se a renda corrente diferir, o espaço real muda
  proporcionalmente.

**D4 — Invariante testável.** `previdencia_pgbl` expõe `ano_base: int`;
testes garantem (a) `previdencia_pgbl.ano_base == irpf_kpis.ano_base_default
== irpf_kpis.ano_base`; (b) o relatório nunca contém `capacidade = 0` e
`capacidade > 0` simultaneamente; (c) coerência de estado: aporte sugerido > 0
⇒ `pgbl_status == capacidade_disponivel` no mesmo ano ([[ADR-189]]).

## Não-objetivos

- **Continuidade de regime tributário é assumida, não detectada**: o proxy
  supõe que o regime (completo/simplificado, renda PJ) do ano-base de cálculo
  persiste no ano corrente; mudança de regime não confirmada fica para o
  estado reservado `mudanca_estrutural` ([[ADR-266]]) com confirmação humana.
- Não reabre [[ADR-236]] (base = renda tributável PF) nem os 4 estados de
  [[ADR-189]]; o disclaimer AUVP "capacidade ≠ recomendação" (ADR-189 §Estado
  1) sobrevive intacto.
- Não altera detecção de completude ([[ADR-266]]) — a lane decide política de
  consumo, não detecção nova.

## Alternativas rejeitadas

- **Ano mais recente disponível (status quo do `irpf_kpis`)**: ano parcial de
  casal com CPF faltante subdimensiona a renda tributável familiar e produz
  capacidade/aporte errados (Cerbasi — consolidação familiar).
- **Cada seção escolhe seu ano com disclaimer**: mantém a contradição; leitor
  não reconcilia duas verdades no mesmo relatório fiduciário.

## Consequências

- `_e5_load_irpf_kpis` (scripts/e5_analyze.py) passa de `anos[-1]` para o ano
  resolvido; `ano_base == ano_base_default` por construção.
- `CapacidadePgblIRPF`/`PrevidenciaAnalysis` ganham nota de degradação +
  `ano_base` no payload legado.
- Golden re-snapshot com diff explicado quando o fixture tiver ano recente
  incompleto.

**Co-design:** `financial-planner` aprovou D1–D4 com 3 ajustes incorporados
(nota de proxy retrospectivo; invariante fortalecido com `ano_base_default` e
coerência de `pgbl_status`; não-objetivo de continuidade de regime).
