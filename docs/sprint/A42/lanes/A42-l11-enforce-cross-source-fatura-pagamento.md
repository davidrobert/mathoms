---
id: A42.l11
type: lane
title: "Enforce do checksum cross-source: fatura contra o débito de pagamento no extrato"
sprint: A42
status: planned
priority: P1
branch_slug: a42-l11-enforce-cross-source-fatura-pagamento
adrs:
  - "[[ADR-350]]"
  - "[[ADR-347]]"
depends_on:
  - "[[A40.l2]]"
tags:
  - type/lane
  - sprint/a42
  - status/planned
  - priority/p1
  - area/pipeline
---

# A42.l11 — `enforce-cross-source-fatura-pagamento` (PC07)

> **Origem:** [[PARSE-CERTIFY-active]] §r1, re-priorizado ↑ P2→P1 no §r2 2026-08-04 —
> PC07. [[ADR-350]] segue `Proposto`; existe apenas o PR de medição (measure-only).

> **Depende de [[A40.l2]]**, que injeta o colapsador cross-documento no mesmo
> adaptador de reconciliação onde este validador é injetado. Dois injetores no mesmo
> ponto de composição ⇒ serializar. **Na promoção, re-ler a disposição da l2**; se
> `cancelled`, esta lane absorve o ponto de injeção e declara a absorção.

## Problema

Fatura de cartão e o débito de pagamento dessa fatura no extrato são a **mesma saída
contável vista de dois documentos**. Sem reconciliá-los, o gasto pode ser contado
duas vezes entre documentos.

O que faz esta lane subir de prioridade não é o double-count — é que ela é a
**testemunha independente** que resolve o problema da [[A42.l9]]. Para os 31
documentos cujo total impresso é derivado das próprias linhas, não existe checksum
intra-documento não-tautológico possível. O débito de pagamento no extrato é uma
testemunha **out-of-band**, gratuita e determinística: já está no corpus, não custa
chamada de LLM, e é o único fechamento disponível para essa classe.

E o sub-produto é de **domínio, não de QA**: quando o pagamento é **menor** que a
soma dos lançamentos, isso indica **crédito rotativo ou parcelamento** — hoje
invisível no relatório, e o passivo mais caro do mercado brasileiro. O
`financial-planner` chegou a essa testemunha de forma independente ao avaliar a
materialidade das lacunas de verificação, o que é a razão registrada da
re-priorização.

**Estado medido pelo PR de medição:** o casamento é por data com tolerância de poucos
dias e valor em cents, **não por descrição** — o débito de pagamento no extrato não
tem rótulo estável. Live: quase todos os pares casaram; um ficou sem contraparte.

## Decisão

1. **Detecção de divergência** (hoje só existe "casou" e "faltando"): distinguir
   `mismatch` de ausência de contraparte.
2. **Contrato de completude de compras** pela cadeia pagamento ↔ fatura do ciclo
   anterior, que exige o total do ciclo impresso — disponível apenas em parte do
   corpus; declarar a cobertura, não presumi-la.
3. **Isolar o escopo de pagamento** no parser que hoje o conflaciona com estornos.
   **Isto muda um campo monetário** ⇒ exige revisão de `financial-planner` antes do
   merge, não depois.
4. **Emitir o sinal de domínio** quando pagamento < soma: é achado de rotativo, e o
   destino é o relatório (endividamento), não um aviso de qualidade de dado. O desenho
   da superfície é fora desta lane.
5. **Flipar a [[ADR-350]] para `Decidido`** no merge.

Measure-then-emit ([[ADR-347]]): o gate só endurece depois de um período de corpus sem
falso-positivo. Não inverter a ordem.

## Critério de aceite

- `mismatch` distinguido de ausência de contraparte, com código próprio.
- Cobertura da cadeia de completude **declarada** (quantos ciclos têm total impresso),
  não presumida — declarar cobertura parcial é o requisito, não atingir 100%.
- Escopo de pagamento isolado de estornos, com **aprovação explícita de
  `financial-planner`** registrada no PR (muda campo monetário).
- Zero falso-positivo no corpus antes de qualquer endurecimento de gate; o período de
  observação é declarado.
- Sinal de rotativo emitido como achado de domínio, não como aviso de QA.
- [[ADR-350]] flipada para `Decidido` no merge, com a emenda de escopo se o desenho
  final divergir do `Proposto`.
