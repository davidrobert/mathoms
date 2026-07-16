---
id: ADR-340
type: adr
title: "score_version 2.1 — componente de diversificação vira concentração imobiliária invertida (FIN-05)"
status: Proposto
date: "2026-07-15"
relates_to:
  - "[[ADR-328]]"
  - "[[ADR-217]]"
  - "[[ADR-177]]"
  - "[[ADR-145]]"
tags:
  - type/adr
  - status/proposto
  - area/pipeline
  - area/report
  - area/methodology
---

# ADR-340 — `score_version 2.1`: diversificação → concentração imobiliária invertida

> Item **FIN-05** (cluster C1 do dogfood). Sucessora de [[ADR-328]] (`score_version 2.0`,
> plateau da cobertura). Co-design `financial-planner` (2026-07-15). **`Proposto`,
> gated pelo C11-Fase2** — não implementar antes da base canônica de
> `ratios.concentracao_imobiliaria` estar travada.

## Contexto

A componente `diversificacao` do score (peso 1.0, o menor) é um **proxy invertido** —
sob os padrões consagrados de planejamento patrimonial brasileiro, premia o **oposto**
de diversificação. Diagnóstico (`financial-planner` 2026-07-15, sobre
`financial_score_calculator._observed_values`):

1. **Conta consumo ilíquido como diversificação.** `num_cats = sum(1 for c in composicao if valor > 0)`
   sobre 6 buckets de origem inclui **Residência** e **Veículos** — família com casa
   própria + 1 carro ganha **+2 buckets** sem diversificar nada, contra o princípio de
   que ativos ilíquidos/de consumo não são posição de carteira nem geram renda passiva
   (a própria métrica canônica de concentração exclui imóveis — FORMULAS.md §concentração).

2. **Double-count por estado civil (bug de tenancy).** `Investimentos Titular` +
   `Investimentos Cônjuge` são a **mesma carteira partida em 2 CPFs**: um casal ganha
   +1 bucket sobre um solteiro pela **mesma alocação**. Com `range_max=6`, o solteiro
   (bucket cônjuge sempre 0) tem teto estrutural de 5 → **nunca tira 10**, contradizendo
   workspace=família.

3. **Inverte a verdade.** Um investidor disciplinado (aluga, sem carro, 100% em
   carteira financeira bem distribuída por classes) pontua **baixo**; uma família com
   casa + 2 carros + 1 poupança pontua **alto**.

**Drift doc↔código não-detectado** (sintoma de output nunca escrutinado): o
`scoring.json._metodologia` diz "buckets com **≥5% do bruto**" e lista **7**; o código
faz **`> 0`, sem limiar**, sobre **6** buckets. O próprio `scoring.json` já confessa
o problema (rótulo diz "NÃO confundir com diversificação de carteira").

## Decisão

**Aposentar a contagem de buckets de origem. Reancorar a componente em
`ratios.concentracao_imobiliaria` (campo canônico do C11-Fase2), invertido.** Isso
reconcilia FIN-05 com C11 (como o plano pede) e corrige os 3 defeitos de graça — a
métrica de concentração considera **só cat_2** (imóveis de renda), então residência,
veículos e o split de cônjuge **saem naturalmente**.

- Componente **lê** `ratios.concentracao_imobiliaria` (SSOT do C11-Fase2 — **não**
  re-derivar no score calculator).
- `invertido: true`, `range_min: 0`, `range_max: 60`: concentração 0% → nota 10;
  ≥60% → nota 0, linear. Peso 1.0 mantido.
- `nome_display`: "Diversificação Patrimonial (origem)" → "Concentração Imobiliária"
  (semântica muda; copy do card = escopo `product-designer`).
- `SCORE_VERSION → "2.1"` ([[ADR-217]] §D3 — cada versão = fórmula completa; 2 bumps
  após 2.0, custo aceito — o "1 bump" da onda era otimização anti-thrashing).

## Decisões de domínio a travar no co-design (antes do PR)

1. **Piso da nota (`range_max` da inversão): 40% vs 60%.** O alerta binário
   `concentracao_alta` dispara em **40%** (limiar consagrado ≤40% em classe ilíquida) e **continua** como
   flag separada. Mas zerar a *nota* em 40% é duro p/ o ICP-BR (FORMULAS.md admite
   "50%+ em imóveis é norma cultural", range 30–60). **Recomendado: warning em 40%,
   piso da nota em 60%.**
2. **Base do denominador** (líquido/bruto/carteira) — a componente herda a que o
   **C11-Fase2 escolher** (item P2 aberto lá: 63,4% carteira vs 67,2% bruto).

## Gate de sequenciamento (bloqueante)

**2.1 anda DEPOIS/JUNTO do C11-Fase2, nunca antes.** `ratios.concentracao_imobiliaria`
está sendo **construído** pelo C11-Fase2 e sua base ainda está em reconciliação.
Shipar 2.1 antes = score consome campo instável. Esta ADR fica `Proposto` até o
sign-off do C11-Fase2 travar a base; então flippa `Decidido` no PR de 2.1.

## Alternativas consideradas

- **(a) Só excluir residência/veículos do count.** Rejeitada: sobram 4 buckets, 2
  ainda são o split de cônjuge — continua contando origem, não risco; mantém o bug
  de tenancy. Remendo numa métrica mal-especificada.
- **`desvio_max_pct` (diversificação de carteira real, por classe de ativo).** Deferida p/ 3.0/componente
  nova: depende de `alocacao_alvo.v2` setada — **não universal** no ICP. `concentracao_imobiliaria`
  é universal p/ famílias com imóveis.
- **Non-issue (não mexer).** Rejeitada: a componente é direcionalmente perversa e roda
  em toda família; peso 1.0 limita o dano, mas o sinal está invertido.

## Consequências

- **NÃO é flat (ao contrário do 2.0).** Família com alta concentração imobiliária (a
  dogfood ~67% bruto) **cai** — nota da componente ~10→~0 = **~1,0 ponto no score final**
  (peso 1.0/8.0), acima do limiar 0,5 do critério [[ADR-328]]. É a correção *intencional*;
  precisa aterrissar com copy no card + parecer (número ↔ narrativa concordam).
- **Exige `golden_diff` per-família** (como FP-02, e importa mais aqui — não é flat):
  cada família com delta >0,5 rastreada, manifesto 1×.
- **Rippla rename**: `_DIMENSION_LABELS`, `breakdown.dimensao`, `_format_top_drivers`,
  chart-context, referência no parecer — coordenar `product-designer` (label/copy).

## Critério de aceite (4 lentes)

- **Completude:** investidor sem imóvel de renda deixa de ser punido; card/score/parecer
  concordam na narrativa de concentração.
- **Corretude:** nota lê `concentracao_imobiliaria` invertido; residência/veículos/split
  de cônjuge fora do cálculo (herdado do C11).
- **Consistência:** base do denominador == a do C11-Fase2; flag `concentracao_alta` (40%)
  separada do piso da nota (60%).
- **Precisão:** `golden_diff` per-família 1×; `score_version` bumpado 2.0→2.1.
