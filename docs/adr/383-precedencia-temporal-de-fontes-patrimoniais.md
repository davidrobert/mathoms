---
id: ADR-383
type: adr
title: "Precedência temporal de fontes patrimoniais: data-alvo → proximidade sem look-ahead → qualidade, sobre fontes inteiras"
status: Proposto
phase: A40.l41
date: "2026-08-12"
relates_to:
  - "[[ADR-238]]"
  - "[[ADR-274]]"
  - "[[ADR-346]]"
  - "[[ADR-376]]"
  - "[[ADR-382]]"
  - "[[ADR-097]]"
supersedes: []
superseded_by: []
aliases: ["ADR 383", "frescor cross-pool", "precedência temporal"]
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/financial-planning
---

# ADR-383 — Precedência temporal de fontes patrimoniais

## Contexto

O PL prefere "posições atuais" (E4) por **membro inteiro** com fallback IRPF
(`_compute_investimentos`), e [[ADR-346]] compara recência só **dentro** do
pool de reports. Nenhuma regra confronta pools: no dogfood, a posição E4
"CDB C6" de R$ 206.491,70 (`data_referencia` 2025-03-31) vence o IRPF
31/12/2025 (R$ 2.404,00) por default — overcount provável de ~R$ 204k no
bruto (~5,1%), propagando para líquido, investível, IF e composição.
Hierarquias de qualidade sem eixo temporal produzem o bug invertido (IRPF
de 2024 venceria extrato de ontem).

Co-design 2026-08-11/12: `financial-planner` (hierarquia bifurcada por tipo
de quantidade; nunca ativo-a-ativo), `senior-cto` (grão = fonte inteira;
faseamento observacional→flip), `data-engineer` (contrato de datas; veto a
flip no PR que introduz o árbitro).

## Decisão

1. **Ordem lexicográfica de precedência**, por célula de comparação:
   1º **data-alvo** da visão (corrente = hoje; fiscal = 31/12/AAAA);
   2º **proximidade da data-alvo sem look-ahead** (elegível sse
   `data_referencia <= alvo`); 3º **qualidade como desempate**, bifurcada
   por tipo de quantidade:
   - *valor de posição/ativo*: IRPF entregue > informe certificado >
     report de posição > derivado de extrato > estimativa própria;
   - *saldo de caixa/conta*: **extrato reconciliado** > informe 31/12 >
     linha cash de report > estimativa ([[ADR-376]] — a conciliação carrega
     garantia de conservação que as demais não têm).
2. **[[ADR-238]] D4 ("declaração entregue vence informe") vale dentro da
   mesma data-alvo** — é regra de qualidade, não de tempo. Sem esta
   cláusula, D4 e esta ADR se contradizem em silêncio.
3. **Grão do árbitro = fonte inteira**, nunca ativo isolado: unidades
   E4 `(instituição, membro, data_ref, total_fonte)` × IRPF
   `(instituição, membro, ano, valores_31_12[ano])` × informe
   `(cnpj_emissor, titular, ano_base, saldo_31_12)`. O árbitro nunca
   desmonta um documento — a coerência intra-documento de [[ADR-346]] fica
   preservada por construção, e o veto do `financial-planner` (carteira
   Frankenstein) é satisfeito estruturalmente.
4. **Datas:** `data_referencia` sempre `YYYY-MM-DD` (fim de período),
   normalizada **no produtor**; `data_referencia_precisao`
   (`dia|mes|desconhecida`). `desconhecida` **nunca vence** — só é usada
   quando é a única fonte da célula. Data inferida do documento é carimbada
   (`data_referencia_origem: "inferida"`) e perde empate contra explícita.
5. **Faseamento por efeito** (não por classe): PR observacional — o árbitro
   roda, emite veredito em campo novo + warnings tipados
   ([[ADR-097]] D1, sem valor monetário persistido) na superfície de
   degradação, e o PL **não muda** (teste afirma); relatório
   veredito×atual por (instituição, membro, classe) sobre o dogfood real;
   só então o PR de flip consome o veredito, com rebaseline isolado. A lane
   não fecha no observacional.
6. **Rótulo de agregado:** consolidado de datas mistas nunca leva data
   única — "datas por linha (mais antiga: X)"; sinal na superfície de
   degradação quando o leque de datas passa de ~1 trimestre (desvio de
   alocação perde significado; sinaliza, não bloqueia).

## Consequências

- Lane A40.l41 (dois PRs). Decisão de produto pendente antes do flip:
  posições da fonte não adotada saem de `top_ativos` ou ganham marca
  "fonte não adotada" (`product-designer` + `financial-planner`).
- O deferimento "poupança/PJ no PL corrente" ([[ADR-376]]) é retomado aqui:
  a célula caixa dessas contas passa a ter dono explícito na hierarquia.
- Warnings de contradição alimentam o mesmo contador exibido no
  `ReportDataQualityBanner` — warning só em log não existe.
