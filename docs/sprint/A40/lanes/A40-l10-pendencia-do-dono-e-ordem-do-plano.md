---
id: A40.l10
type: lane
title: "Ordem do plano com critério encodado + pendências acionáveis do dono"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l10-pendencia-do-dono-e-ordem-do-plano
adrs: []
depends_on: ["[[A40.l9]]"]
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/produto
---

# A40.l10 — `pendencia-do-dono-e-ordem-do-plano` (RV3-07, RV3-10, RV4-02)

## Problema

A revisão concluiu, para "a principal recomendação é a certa?": **direção sim,
ordenação indeterminada**. Três causas:

1. **A maior alavanca declarada está fora do ranking** — bloqueada por perfil
   tributário incompleto, e **sem nenhuma pendência acionável** que peça o dado.
2. **Nenhum critério de ordenação está encodado.** A ordem sai do julgamento de
   dois braços que compartilham a mesma persona. Sob "prazo legal primeiro", outro
   item venceria.
3. **A premissa da recomendação nº 1 é contestada pelo próprio payload** (RV3-10):
   o gap cita dependentes menores enquanto o bloco estruturado conta zero. A
   narrativa nomeia um filho; nenhum campo o conta.

**Correção do painel (§Decisões nº 8):** os "3 dados que faltam" eram **1**. O
regime já é derivável de documento ingerido (`FinanceiroPJSnapshot.regime_declarado`
é computado e nunca consultado) e a contagem de dependentes zero é **observação**,
não ausência. Só a taxa da dívida é ask genuíno. Um wizard perguntando os três
queimaria a única janela de atenção do dono no item de menor valor.

## Escopo

> **Item P0 admitido em 2026-08-04 (RV4-02, [[PIPELINE-REVIEWS-active]] §r4).** A
> primeira decisão da fila é **descartada** da única seção que responde "o que fazer":
> o cabeçalho de aporte ocupa "Prioridade 1" incondicionalmente e a fila é enumerada a
> partir do segundo item, então a decisão registrada pelo dono não chega ao leitor — e
> duplica quando outra decisão da fila também é de aporte. Âncoras:
> `charts_narrator.py:417-433` (descarte) e `S10SinteseSection.tsx:16-17` (render
> confirmado). Entra **como item desta lane, não como lane nova**: é a mesma superfície
> (ordenação do plano + S10) e o mesmo dono, e o critério de aceite abaixo já exige que
> recomendação não-computável nunca desapareça sem rastro. Admissão pela cláusula 1 do
> §Critério de admissão da [[A42]] (destino é quem já possui a superfície).
> **Nota de execução:** ler o diff de #1188 antes de começar — a [[A40.l9]] mexeu na
> materialização adjacente. Esta lane flipou `planned → open` e `P2 → P1` na mesma
> admissão, já que a dependência [[A40.l9]] shipou.


- Enum `elegibilidade` no item do plano de ação, avaliado no builder, com docstring
  co-localizado (methodology-as-code).
- Consultar o regime declarado em vez de perguntar.
- Pendência acionável **só** para a taxa da dívida.
- Critério de ordenação **encodado e auditável**.

## Critério de aceite

- KR-E: fixture com contagem de dependentes zero + regra que cita dependentes
  menores ⇒ item marcado `refutada_por_payload` e **ausente** do plano renderizado.
- Fixture com regime ausente ⇒ item não some em silêncio: vira pendência com CTA.
- Recomendação não-computável **nunca** desaparece sem rastro.
