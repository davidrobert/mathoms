---
id: A40.l96
type: lane
title: "Tabela de maiores ativos atribui titular a valor que o sistema declara órfão"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P0
branch_slug: a40-l96-titular-atribuido-a-posicao-orfa
owner: data-engineer
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p0
  - area/pipeline
  - area/frontend
  - area/financial-planning
---

# A40.l96 — `titular-atribuido-a-posicao-orfa`

> **Origem:** `RR6-03` da rodada unificada **U2** ([[REPORT-REVIEWS-active]] §r6,
> merge `47970706`). **CONFIRMADO** por cético, com a refutação óbvia derrubada por
> aritmética.

## ⚠️ A direção NÃO está determinada — comece medindo

Esta é a única das lanes de P0 da U2 cujo **alvo do fix** ainda não se sabe.

## O que está medido e é sólido

A tabela de maiores ativos preenche a coluna de titular em **15 de 15** linhas, enquanto o
mesmo relatório publica uma linha explícita de "investimentos sem titular identificado" e
um risco de severidade **Alta** dizendo que ~metade da carteira financeira não tem
titularidade.

A refutação óbvia — *"as posições órfãs não estão entre as 15 maiores"* — é
**aritmeticamente impossível**: as 15 linhas somam **92,7%** da base (confirmado por duas
âncoras independentes, incluindo o rodapé da própria tabela), logo o residual fora do Top 15
é ≤ 7,3%, e a fatia órfã declarada **não cabe nele, por 2,4×**.

A razão entre o financeiro atribuído ao titular no Top 15 e `patrimonio.investimentos_titular`
é **~3,7×**, e o desbalanceamento **não é simétrico** entre os membros ⇒ é um **modelo de
atribuição diferente**, não "as órfãs foram para o titular".

## O que não se sabe, e é a primeira entrega

Pode ser o **roll-up patrimonial** que erra, não a tabela: o Top 15 talvez leia o titular do
extrato/informe — sinal mais rico que o IRPF. Nesse caso o risco Alta e a
`motivo_supressao` da realocação da reserva é que seriam **espúrios**, e o dano **inverte**:
o produto estaria suprimindo prescrição correta por diagnóstico falso.

**Medição discriminante (antes de qualquer fix):** proveniência **por item** do campo titular
no artefato E4 `investimentos` (`_source` + titular por posição), confrontada com a agregação
de `patrimonio.investimentos_titular` / `investimentos_conjuge`. **Nenhum dos dois lados foi
aberto na rodada.**

## Por que é P0 em qualquer direção

É a rota pela qual o aviso retido de titularidade vira **decisão de sucessão errada**. A
prescrição de planejamento sucessório do parecer é a **única** do relatório que não
condiciona à titularidade — e a tabela que a família abre para executá-la é justamente a que
afirma quem é dono de quê. Secundariamente, a reserva por membro herda o mesmo problema.

## Critério de aceite

- A medição discriminante publicada, com veredito de qual lado erra.
- Uma só função de atribuição alimentando as duas superfícies, **ou** as duas declarando
  bases distintas de forma legível.
- Fallback visível na célula quando o titular não é conhecido.
- **Não abra ADR antes de saber a direção.** A lane provavelmente rende dois PRs.

## Já registrado

`PV9-35` (duas tabelas discordam sobre titularidade) — `MEDIÇÃO-DE-CONHECIDO`; o novo é o
quantum e a rota de decisão nomeada (**sucessão**, não alocação).
