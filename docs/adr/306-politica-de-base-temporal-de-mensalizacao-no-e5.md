---
id: ADR-306
type: adr
title: "Política de base temporal de mensalização no E5 — janela canônica 12m + rótulo de janela por bloco"
status: Proposto
date: "2026-07-03"
relates_to:
  - "[[ADR-191]]"
  - "[[ADR-090]]"
  - "[[ADR-161]]"
aliases: ["ADR 306", "base temporal E5", "janela 12m canônica"]
tags:
  - type/adr
  - status/proposto
  - area/e5
  - sprint/a28
---

# ADR-306 — Política de base temporal de mensalização no E5

**Status:** Proposto (A28.l4) • **Data:** 2026-07-03 • Co-design
`financial-planner` + `senior-cto` (2026-07-03). Relaciona [[ADR-191]]
(custo essencial), [[ADR-090]] (money), [[ADR-161]] (suggestions Cerbasi/Perini).

## Contexto

O payload E5 mensaliza sobre **duas bases sem rótulo** com valores 2× diferentes:
headline usa média full-period (40 meses no dogfood `72883bde`, diluída por meses
de 2023-24 com cobertura documental parcial — despesa 44,2k/mês) enquanto
`fluxo_caixa.janela_12m` mede 81,4k/mês. Consequências: reserva dimensiona pela
base diluída (cobertura superestimada); cobertura Perini oscila ~61%↔~33% conforme
a base; `consumo_consciente.folga_mensal` mistura bases (pontuais full-period ÷
janela 12m); Cerbasi classifica "Gastador" (97,5% presente) no mesmo relatório que
celebra 28% de poupança — aportes não contam como "futuro". FORMULAS.md tinha
três regras fragmentadas (reserva "trimestral" nunca implementada; ratios 12m;
headline full-period).

## Decisão

**D1 — Famílias de métrica e base canônica.**

| Família | Base | Rótulo `janela` |
|---|---|---|
| Ratios/KPIs, score, reserva, Perini (denominador), Cerbasi, folga | **Janela 12m** — últimos 12 meses **documentados** | `"12m"` |
| Agregados históricos (fluxo top-level, orçamento, charts) | Full-period, permitido **apenas rotulado** | `"full"` |
| Mensalizações fiscais (renda passiva, TRS — numerador Perini) | Ano-base IRPF ÷ 12 | `"irpf_<ano>"` |
| Valores mensais por natureza (`parcela_mensal`, `aporte_mensal`, `aporte_mensal_usado`) | Não são mensalização de série | **isentos** |

**D2 — Rótulo de janela por bloco (dois campos).** Todo dict do payload com campo
mensalizado derivado de série temporal carrega chaves irmãs `janela` (tipo
conceitual, vocabulário fechado acima) e `janela_meses` (int — meses documentados
reais; honestidade quando a janela conceitual tem menos dados, ex.: `janela: "12m",
janela_meses: 8`). Invariante testado em pipeline: campo `*mensal*` fora da lista
de isenção (frozenset com justificativa inline + assert anti-órfã) ⟹ `janela` no
mesmo dict. Schema `e5_analysis` exige `janela` em `fluxo_caixa`.

**D3 — Cobertura documental parcial no denominador.** Denominador conta apenas
**meses documentados** (presentes na série E4) — gap de calendário nunca entra como
zero. Política: mês abaixo de cobertura mínima sai do denominador; v1 operacionaliza
cobertura mínima como "mês presente na série" (proxy — a matriz conta×mês de E3
necessária para detecção fina é follow-up, par com [[A28.l9]]/[[A28.l8]]).
`janela_meses` expõe a contagem real para o banner de qualidade.

**D4 — Reserva de emergência** consome `janela_12m` (não mais a média full-period).
`despesa_mensal_media` da janela é **ponte transitória**: [[A28.l1]] troca para
`despesa_mensal_essencial` da **mesma janela** (FORMULAS.md §Reserva). 12m vence
"trimestral" (FORMULAS.md corrigida): sazonais essenciais (IPTU/IPVA/educação/13º
de mensalista) são despesa recorrente real; trimestral subdimensionaria a reserva.

**D5 — Cerbasi presente/futuro sobre renda, com poupança como "futuro".**
Base = janela 12m. `pct_futuro = (gasto_futuro_12m + poupança_12m) / base`;
`pct_presente = gasto_presente_12m / base`; poupança = `max(0, receita_recorrente_12m
− despesa_total_12m)` (residual — **fallback**; aporte observado de primeira classe
é follow-up quando E4 expuser); `base = gasto_presente + gasto_futuro + poupança`
(== renda recorrente no superávit; == despesa total no déficit; pcts somam 100).
Faixas inalteradas (≥30 Investidor, ≥20 Equilibrado, ≥10 Endividado consciente).
Mudança **intencional e não-versionada** de `pct_presente`/`pct_futuro` in-place —
o valor antigo (% sobre despesa, poupança invisível) era erro metodológico, não
contrato. Payload ganha `componentes` (gasto_presente, gasto_futuro, poupança,
base) para explicabilidade.

**D6 — Folga mensal reconciliável.** Gastos pontuais do cálculo da folga restritos
à janela 12m; `folga_mensal = receita_recorrente_mensal_12m −
(despesa_mensal_media_12m − pontuais_janela/n)` — derivável algebricamente da base
canônica (teste de reconciliação). `total_pontuais` (tabela) segue full-period.

**D7 — Perini com bases mistas declaradas.** Cobertura = renda passiva mensal
(`irpf_<ano>`) ÷ despesa essencial (`12m`). Mistura aceita; rótulos obrigatórios
nos dois blocos + `defasagem_meses` já exposto modula confiança do parecer.

**D8 — Consumidores da base diluída corrigidos.** Reserva (D4),
`suggestion_rules::sugere_diversificar_renda_passiva` (prioridade invertida —
lia top-level antes da janela) e Cerbasi (D5). `_lineage` **não muda**: rastreia
totais full-period por design (rastreabilidade da soma, não mensalização).

## Consequências

- Golden re-snapshot único e explicado (dev/golden_diff.py) — antes de [[A28.l1]]
  re-snapshotar (evita duplo rebaseline). Invariantes de conservação intocados
  (identidades sobre totais).
- Goldens/eval do parecer que asserem rótulo Cerbasi antigo re-baseline no mesmo PR.
- UI nunca exibe duas mensalizações sem rótulo — render do badge é escopo [[A28.l9]].
- Follow-ups: aporte observado como componente "futuro" de primeira classe;
  cobertura fina conta×mês no denominador; migração do orçamento prospectivo
  para janela 12m.

## Alternativas rejeitadas

- **Janela trimestral para reserva** — perde sazonais essenciais; reatividade vira
  alerta separado, não base.
- **Rótulo `"<N>m"` dinâmico único** — colapsa tipo conceitual e contagem; força
  parsing de string. Dois campos (`janela` + `janela_meses`) resolvem.
- **`_janelas` metadata central no root** — descola o contrato do dado; frágil a
  rename; UI/LLM consomem por caminho direto.
- **Campos novos `pct_futuro_v2` + deprecação** — perpetua o valor errado para
  consumidor não-migrado; ambiguidade pior que correção.
- **Gap de calendário como zero no denominador** — reintroduz a diluição que
  originou o bug.
