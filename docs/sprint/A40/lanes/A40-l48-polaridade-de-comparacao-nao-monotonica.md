---
id: A40.l48
type: lane
title: "Polaridade de comparação é fixa por métrica, mas cobertura de reserva não é monotônica no alvo"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l48-polaridade-de-comparacao-nao-monotonica
owner: data-engineer
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p2
  - area/pipeline
---

# A40.l48 — `l48-polaridade-de-comparacao-nao-monotonica`

> **Aberta em 2026-08-12**, da revisão r4 registrada em [[REPORT-REVIEWS-active]]
> §r4 (report `7a7d7115` sobre run `ee124571`). Dono: `data-engineer`.
> Agrupada **por domínio de dono**, não por severidade: os achados aqui precisam
> do mesmo especialista para fechar, e lane com donos distintos não fecha.

## Problema

`comparisons[].direction_positive` é um campo **por métrica** e está correto para
as métricas monotônicas. Em cobertura de reserva de emergência ele está errado por
construção: subir é bom **abaixo** do alvo e é custo de oportunidade **acima**
dele. O relatório da r4 celebrou um aumento de cobertura com seta de melhora na
seção "O que mudou" — que é a primeira que a família lê — e três seções depois
classificou a mesma reserva como excessiva e prescreveu reduzi-la.

O dano é de ancoragem, não de número: quem lê o delta primeiro registra a
deterioração como progresso e chega à prescrição já ancorado no sinal oposto.

## Achados cobertos

RV4-16 (Médio). Registro: [[REPORT-REVIEWS-active]] §r4.

## Escopo

**PR1 — polaridade derivada do alvo, não do campo.** Para métrica com alvo, o
sinal do delta passa a depender da posição relativa ao alvo, não de uma constante.
Métrica genuinamente monotônica não muda de comportamento.

**Aceite:** fixture que cruza o alvo nos dois sentidos ⇒ o sinal inverte no ponto
certo · **mutação que volta a polaridade para constante derruba o teste** ·
nenhuma métrica monotônica muda de sinal (regressão sobre o snapshot).

## Critério de aceite da lane

Nenhuma métrica com alvo publica seta de melhora para movimento que a própria
superfície prescreve reverter.

## Não-objetivos com rota declarada

Rever quais métricas entram em `comparisons`, ou o texto do card de reserva
(clareza-ux, dono `product-designer`). A base temporal da comparação é
[[ADR-306]] e não muda aqui.
