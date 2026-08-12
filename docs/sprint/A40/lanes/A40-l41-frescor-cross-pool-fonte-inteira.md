---
id: A40.l41
type: lane
title: "Frescor cross-pool: posição stale de 2025-03 vale R$ 206k no bruto contra IRPF 31/12/2025 de R$ 2,4k"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P1
branch_slug: a40-l41-frescor-cross-pool-fonte-inteira
adrs:
  - "[[ADR-346]]"
  - "[[ADR-383]]"
depends_on: ["[[A40.l42]]"]
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p1
  - area/pipeline
  - area/financial-planning
---

# A40.l41 — `frescor-cross-pool-fonte-inteira`

> **Aberta em 2026-08-11.** Parecer `financial-planner` (hierarquia bifurcada
> por tipo de quantidade; granularidade nunca ativo-a-ativo) + `senior-cto`
> (grão = **fonte inteira**; faseamento observacional→flip) + `data-engineer`
> (contrato de datas; veto a flip no mesmo PR).

## Problema

O PL prefere "posições atuais" por **membro inteiro** com fallback IRPF
([patrimonio_calculator.py:290-347](../../../../pipeline/domain/services/patrimonio_calculator.py));
[[ADR-346]] compara recência só **dentro** do pool de reports. Nada confronta
pools: a posição E4 "CDB C6 Bank" de R$ 206.491,70 (`data_referencia`
2025-03-31) vence o IRPF 31/12/2025 (R$ 2.404,00) por default — overcount
provável de ~R$ 204k no bruto (~5,1%).

## Entregável

1. **ADR Proposto** (precedência temporal): ordem lexicográfica **data-alvo →
   proximidade sem look-ahead → qualidade no empate**; hierarquia de
   qualidade bifurcada (posição: IRPF > informe > report > derivado-de-extrato;
   caixa: extrato > informe > report); [[ADR-238]] D4 vale dentro da mesma
   data-alvo; `desconhecida` nunca vence (só quando única fonte); data
   inferida é carimbada (`data_referencia_origem: "inferida"`) e perde empate.
2. **Árbitro com grão de fonte inteira** — novo domain service; unidades:
   E4 `(instituição, membro, data_ref, total_fonte)` × IRPF
   `(instituição, membro, ano, valores_31_12[ano])` × informe
   `(cnpj_emissor, titular, ano_base, saldo_31_12)`. Nunca desmonta fonte
   (coerência intra-documento de [[ADR-346]] preservada por construção).
   Config por value object (`PrecedenciaConfig`); warnings tipados sem valor
   monetário persistido (padrão [[ADR-097]] D1 + LGPD).
3. **PR-a observacional (efeito zero):** árbitro roda, emite veredito em
   campo novo + warnings na superfície de degradação ([[A40.l22]]); PL não
   muda (teste afirma). Relatório por (instituição, membro, classe) da
   diferença veredito×atual no dogfood real.
4. **PR-b flip:** consumo do veredito; rebaseline isolado com manifesto.
   Gate de saída declarado no PR-a — a lane **não fecha** no observacional.

## Critério de aceite

- PR-a: `investimentos_titular/conjuge` e `bruto` idênticos (golden byte-a-byte
  nos campos monetários); warnings emitidos com
  `(instituição, membro, classe, data adotada, data descartada, motivo)`.
- PR-b: C6 renda fixa cai para a fonte mais fresca; delta do bruto medido e
  justificado linha a linha no manifesto.
- Decisão de produto registrada antes do PR-b: o que acontece com
  `top_ativos` da fonte não adotada (`product-designer` +
  `financial-planner`).
- Datas: `data_referencia` sempre `YYYY-MM-DD` no produtor; gate rejeita
  `YYYY-MM`/`YYYYMM`/int.

## PR-a (observacional) entregue — 2026-08-12 (PR #1419)

`fonte_precedencia_arbiter` compara fontes inteiras por célula
(instituição, membro) na ordem data-alvo → proximidade sem look-ahead →
qualidade; publica veredito + contradições em `patrimonio.frescor_fontes`
(sem valor monetário) e **não altera** nenhum número do PL — contrato com
teste próprio sobre o caso real do dogfood (C6 2025-03-31 × IRPF 31/12/2025).

**Gate de saída para o PR-b** (o observacional não fecha a lane): relatório
veredito×atual por célula sobre o dogfood real, decisão de produto sobre
`top_ativos` da fonte não adotada (`product-designer` + `financial-planner`),
e só então o flip do consumo com rebaseline isolado e manifesto.
