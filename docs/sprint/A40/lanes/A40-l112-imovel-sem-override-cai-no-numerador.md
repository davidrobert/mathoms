---
id: A40.l112
type: lane
title: "Imóvel sem classificação nenhuma entra no numerador da concentração pelo `else`, e reclassificar um deles move o KPI de 82 para 0"
sprint: A40
status: open
priority: P2
branch_slug: a40-l112-imovel-sem-override-cai-no-numerador
owner: data-engineer
depends_on: []
adrs: ["[[ADR-420]]", "[[ADR-412]]", "[[ADR-215]]"]
tags: [type/lane, sprint/a40, status/open, priority/p2, area/dados, area/pipeline]
---

# A40.l112 — `imovel-sem-override-cai-no-numerador`

> **Origem:** §Follow-up da [[A40.l95]], que carregou o item sem lane id desde 2026-08-29
> e o **roteou para cá** ao fechar. Classe **distinta** da l95: captura, não metodologia.

## O defeito

`split_imoveis_alocacao_vs_fora` e `split_imoveis_with_overrides` só reconhecem
classificação vinda de **override explícito**. Imóvel sem override nenhum cai no `else`
dos dois splitters — e o `else` não distingue *"classificado como algo que fica"* de
*"nunca foi classificado"*.

Consequência no numerador da concentração ([[ADR-420]] §D1): o não-classificado entra.
Isso é o **lado conservador** e está certo como default (§D2 — ausência de rótulo não
compra verde num KPI de risco), mas é conservador **sem dizer que é**: o leitor recebe um
percentual sem ressalva sobre a fatia que ninguém classificou.

**Medido no golden em 2026-09-01**, rodando o pipeline nos quatro regimes:

| regime | concentração |
|---|---|
| corrente (4 dos 5 imóveis classificados) | 77,19% |
| **default** — nenhum override | **82,19%** |
| corrente + o apartamento vira `residencia_principal` | 65,79% |
| default + um vira `residencia_principal` | 75,93% |

No regime default o **numerador inteiro** é fatia não-classificada, e um clique de UI
move o KPI em **6,3 pp** (82,19 → 75,93) sem que nada na tela diga que ele era desse
jeito.

> ⚠️ **Correção do enunciado recebido da [[A40.l95]].** A afirmação *"reclassificar um
> imóvel move 82,19 → **0,00**"*, herdada dela, não reproduz. Isso era verdade do golden **anterior ao #1904**, que
> tinha **um único** imóvel: tirá-lo de cat_2 zerava numerador e denominador. Com os cinco
> de hoje o efeito é 6,3 pp, não 82. Herdei o número sem re-medir sob a fixture nova — o
> defeito procede, a magnitude não era essa.

## O que NÃO é

Não é o corte metodológico — esse a [[ADR-420]] §D1 decidiu e a [[A40.l95]] entregou.
Não é o piso de cobertura do §D2, que está deferido atrás do flip da [[ADR-353]] e é
sobre **suprimir prescrição**, não sobre capturar estado.

## Escopo proposto

- **Estado ternário** em vez de binário: `classificado | não-classificado | irrelevante`,
  no molde de [[ADR-412]] §D2 (`Papel` ternário) — o `else` deixa de ser catch-all.
- **Cobertura publicada**: que fatia de cat_2 não tem classificação, ao lado do KPI.
- Critério de aceite próprio, incluindo a fixture que **discrimina** os três estados —
  a lição que a [[A40.l95]] pagou três vezes.

## ⚠️ Prevalência em produção é NÃO-MEDIDA

A evidência é fixture sintética. O dogfood real tem os 6 imóveis classificados, e o
`INVESTMENT_CLASSIFICATIONS` do card já concorda com o numerador nesse corpus
(`tests/unit/pipeline/test_paridade_numerador_e_contagem_do_card.py`). Registre como
**exposição estrutural**, não como incidência — dimensionar antes de priorizar.

## Critério de aceite

- Os três estados são distinguíveis no payload, e a fixture os separa dois-a-dois.
- A fatia não-classificada de cat_2 é publicada, não inferida.
- Mutação que devolve o `else` a catch-all deixa o gate vermelho.
