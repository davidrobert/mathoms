---
id: A40.l126
type: lane
title: "O cenário do cônjuge afirma o que não mediu: a contribuição do cônjuge sai de um label sem membro, e a premissa de 2/3 do aporte não aparece"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l126-cenario-do-casal-rotulado
owner: financial-planner
depends_on: []
adrs: ["[[ADR-167]]", "[[ADR-177]]", "[[ADR-387]]"]
tags: [type/lane, sprint/a40, status/open, priority/p1, area/pipeline]
---

# A40.l126 — `cenario-do-casal-rotulado`

> **Origem:** desmembrada da [[A40.l125]] em 2026-10-09, por decisão do
> `financial-planner` no co-design: a l125 liga o gate da [[ADR-167]] e deixa o caminho
> do **casal** byte-idêntico; esta lane é o rótulo que a decisão de manter o cenário
> para casal com divisão de renda não mensurável exige. Parte da base de código da l125.

## O defeito, já medido

1. **Contribuição do cônjuge sem sinal.** `premissas.salario_conjuge_clt_brl` sai de
   `_extract_salario_conjuge`, que casa `"clt"` e `conjuge_key.title()` no label de
   receita — o label é o valor do mapeamento global do template e não carrega o membro
   ([[ADR-167]] §Emenda 2026-10-09). Em casal o campo publica `0` querendo dizer
   ausência, e o narrador escreve "Atualmente {cônjuge} contribui com R$ 0,00/mês". Sem
   cônjuge, `"" in label` é sempre verdadeiro e o campo pegava o CLT do próprio titular.
2. **Premissa escondida.** O aporte de estresse é o aporte declarado × 0,66
   ([[ADR-177]]), sem relação com a renda real do cônjuge — e o card não diz que é
   hipótese.
3. **Rótulo do card de aportes.** O ramo de fallback do `EstrategiaAporteCard` publica
   o aporte **estressado** sob "Estratégia de Aportes" / "Aporte/mês", sem a base ao
   lado; o teste da [[A40.l100]] chama esse número de aporte declarado.

## Escopo

- `premissas.divisao_renda: "nao_mensurada"` no bloco (mudança de contrato E5 —
  `data-engineer`).
- `salario_conjuge_clt_brl` → `null`; `_extract_salario_conjuge` sai.
- Narrador sem a frase de contribuição quando o valor é ausente, e com o rótulo da
  premissa (copy com `product-designer`; ponto de partida do `financial-planner`:
  "pressupõe ajuste de despesas que preserve 2/3 do aporte; divisão de renda não
  informada").
- Parágrafo "Leitura:" do APP_C e rótulo do card de aportes (`product-designer`).

## Critério de aceite

- Fixture com labels de papel (`"(Cônjuge - CLT)"`) não atribui renda a ninguém.
- Casal sem sinal de renda: bloco presente com `divisao_renda: "nao_mensurada"` e
  nenhuma afirmação de quanto o cônjuge contribui, em S3, APP_C, narrativa e parecer.
- O card de aportes não publica aporte estressado como estratégia de aporte.

> **2026-10-09: critério 3 cumprido por remoção (PR #2242).** O `EstrategiaAporteCard`
> saiu do relatório. O ramo rico nunca teve produtor (desde a ADR-129), e o fallback era o
> único caminho que renderizava, publicando o aporte estressado. O item "rótulo do card de
> aportes" do §Escopo deixa de existir; o parágrafo "Leitura:" do APP_C segue no escopo.
> Os critérios 1–2 seguem abertos. Co-design `product-designer` + `financial-planner`.

## Fora do escopo

Calibrar a magnitude pela renda real (critérios (b)/(c) da [[ADR-167]]): depende do
escritor de `protection_income_declarations` ([[ADR-387]]) — deferimento 1 da emenda.
