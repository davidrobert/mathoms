---
id: A27.l3
type: lane
title: "A cobertura de lineage é medida contra a fixture e não contra a produção: quatro raízes monetárias ficam fora do universo do gate"
sprint: A27
status: open
priority: P1
branch_slug: a27-l3-cobertura-de-lineage-medida-contra-a-fixture
owner: data-engineer
depends_on: []
adrs: ["[[ADR-281]]"]
tags: [type/lane, sprint/a27, status/open, priority/p1, area/dados]
---

# A27.l3 — `cobertura-de-lineage-medida-contra-a-fixture`

> **Origem:** `PV13-12` da rodada unificada **U5** ([[PIPELINE-REVIEWS-active]] §r13).
> Sucessora da [[A27.l2]], que **entregou** o gate com controle positivo — o defeito é no
> **universo**, não no mecanismo.

## O defeito

O gate fixa o conjunto de raízes monetárias sobre o payload da **fixture** de dogfood:
**14** raízes. O payload **real** deste run tem **18**. As **4 raízes a mais ficam fora do
universo do gate** — não são medidas como descobertas, e não contam como descobertas.

Efeito no número publicado: a cobertura sai **36%**; medida sobre o universo real é
**28%**. O viés é **otimista**, e cresce sozinho: raiz nova entra na produção sem entrar no
denominador.

## Por que não invalida a A27.l2

O controle positivo dela é real e o mecanismo funciona. O que esta lane conserta é o
**sujeito da medição** — exatamente a distinção que a [[A42.l14]] estabeleceu para
conservação. O gate mede bem o que decidiu medir; decidiu medir a fixture.

## Critério de aceite

1. O universo de raízes é **derivado do payload sob medição**, não de constante.
2. Raiz monetária presente na produção e ausente do universo do gate **reprova** (é o sinal
   que hoje não existe).
3. O número publicado de cobertura declara o denominador e sua origem.
4. Re-medição sobre este run: a cobertura publicada cai ao valor real, e a queda é
   registrada como correção, não regressão.
