---
id: A40.l125
type: lane
title: "O gate de elegibilidade do cenário do cônjuge nunca rodou, e o critério de renda dele media um sinal que não existe"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 2201
ship_date: "2026-10-09"
priority: P1
branch_slug: a40-l125-gate-do-cenario-do-conjuge
owner: financial-planner
depends_on: []
adrs: ["[[ADR-167]]", "[[ADR-387]]"]
tags: [type/lane, sprint/a40, status/shipped, priority/p1, area/pipeline]
---

# A40.l125 — `gate-do-cenario-do-conjuge`

> **Origem:** achado medido em 2026-10-09 — a [[ADR-167]] decidiu que
> `should_render_conjuge_scenarios` decide se o bloco `cenarios_conjuge` entra no E5,
> e a função nunca teve chamador em produção (nasceu órfã no #81). Prioridade P1 pelo
> `financial-planner`. Solteiro, família de uma renda e casal 95/5 viam o card
> "Cenários de Estresse — Sem renda do cônjuge" na S3.

## O defeito, já medido

1. **Gate órfão.** O `E5AnalyzerAdapter` calculava o cenário para qualquer workspace com
   data de nascimento do titular e meta IF.
2. **Sinal inexistente.** O gate casava o `nome_curto` com o label de receita, que é o
   valor do mapeamento PJ/CLT do template **global** — saneado na A34.l11 para palavras
   de papel. Ligado como estava, apagaria o cenário de todo casal elegível. A medição
   no dogfood não foi feita por decifração dos artefatos (dado pessoal): a forma do
   label saiu do produtor, do seed e do histórico do seed, com nomes mascarados.
3. **Três predicados de presença no front.** O APP_C checava `labels`; a S3 não checava
   nada — o fallback estático de conclusão sempre tinha texto, então o card aparecia
   com o bloco vazio; o card de aportes decidia "Meta de aporte não configurada" pela
   ausência do cenário.
4. **Validação do E5.N.** Com o bloco vazio, o narrador emitia o chart com conclusão
   vazia e o validador, que o exigia, reprovava o E5.N inteiro. Latente para workspace
   sem data de nascimento; o gate o tornaria regra para todo solteiro.

## Entrega

[[ADR-167]] §Emenda 2026-10-09: `veredito_cenario_conjuge` (cônjuge cadastrado + meta
IF > 0) no adapter, com o veredito logado; `{}` canônico; `readCenariosConjuge` como
fonte única do "o cenário existe"; card de aportes com predicado próprio (aporte
declarado); chart do cenário opcional-mas-completo nas narrativas.

## Critério de aceite

- [x] Solteiro → `cenarios_conjuge: {}`; casal (`papel: conjuge`) com meta IF → bloco
      populado (`tests/test_e5_golden_execution.py`).
- [x] Solteiro: nenhum card do cenário na S3 nem APP_C; nenhum chart do cenário nas
      narrativas (`S3CenariosConjuge.test.tsx`, `test_e5n_s9_empty_state.py`).
- [x] "Meta de aporte não configurada" segue alcançável e deixa de ser afirmada a quem
      declarou aporte. Controle: contra os componentes de `main`, falham exatamente os 3
      casos do defeito.
- [x] O E5.N do solteiro valida (`test_e5n_execution_injects_narrativas`).
- [ ] Casos "1 renda" e "95/5" — **não entregues**: a divisão de renda não é mensurável
      hoje. Deferidos na emenda da [[ADR-167]].

## Deferimentos datados — 2026-10-09

1. **Critérios de renda e magnitude calibrada** — na [[ADR-167]] §Emenda, retomada
   pelo escritor de `protection_income_declarations` ([[ADR-387]]).
2. **Caminho do casal sem rótulo de hipótese** — [[A40.l126]] (P1).
3. **Linha `: {}` no contexto do parecer** — na [[ADR-167]] §Emenda, dono
   `prompt-engineer`.
4. **APP_C entra na classe de âncora morta do índice para solteiro** — já é o
   deferimento 1 da [[A40.l88]] (dono `information-architect`); esta lane só acrescenta
   o caso.
5. **`golden_diff` não exige manifesto para campo monetário removido** —
   `exige_manifesto` cobre delta e anulação; o `{}` desta lane cai nesse ponto cego.
   Dono: `data-engineer`. **Retomada:** na próxima mudança de contrato que remova campo
   monetário do E5.
6. **A baseline das métricas do parecer em print quebra com qualquer mudança de altura
   acima dela.** O recorte é o locator da tabela com a página inteira montada em print e
   tolerância 0,0003; o card que saiu da S3 deslocou a tabela por um valor fracionário e
   dois separadores andaram 1 px (208→209, 362→363), com conteúdo idêntico. Medido no
   #2201: o job visual de `main` passava na mesma base (run 37952398232), esta branch
   reprovava. O "piso de ruído = 0 px" da [[A40.l92]] vale para o mesmo SHA, não para
   mudança de layout acima. Dono: `product-designer` (dono da [[A40.l92]]). **Retomada:**
   na próxima vez que o gate reprovar sem mudança na tabela — ou ao revisar o recorte
   (posição normalizada ou âncora própria).
