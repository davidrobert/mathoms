---
id: A40.l47
type: lane
title: "Três números do relatório cuja semântica não bate com o rótulo: taxa de retirada, faixa comportamental e base da reserva"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l47-semantica-de-taxa-faixa-e-base
owner: financial-planner
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/frontend
---

# A40.l47 — `l47-semantica-de-taxa-faixa-e-base`

> **Aberta em 2026-08-12**, da revisão r4 registrada em [[REPORT-REVIEWS-active]]
> §r4 (report `7a7d7115` sobre run `ee124571`). Dono: `financial-planner`.
> Agrupada **por domínio de dono**, não por severidade: os achados aqui precisam
> do mesmo especialista para fechar, e lane com donos distintos não fecha.

## Problema

Três achados de domínio da r4. Nenhum é erro de cálculo — os três são o **rótulo
discordando do que o número mede**, que é pior: o cálculo confere, então nenhum
invariante de conservação acusa.

1. **Taxa de retirada publicada como meta de rentabilidade.** O campo de
   rentabilidade guarda a TRS efetiva (renda passiva ÷ patrimônio gerador) e a
   "meta" ao lado é a premissa de saque do número da IF — não uma meta de
   **retorno**. O parecer leu o payload fielmente e amplificou: emitiu risco de
   severidade alta *"rentabilidade abaixo da meta"* + métrica-alvo. A [[ADR-191]]
   registra as duas taxas **coexistirem**; não autoriza promover uma a meta da
   outra. Consequência de produto: empurra yield-chasing numa carteira em
   acumulação, contra a alocação-alvo publicada no mesmo relatório.
2. **Duas réguas comportamentais no mesmo documento.** As faixas do classificador
   comportamental no código divergem da legenda publicada no apêndice: um rótulo
   que o código emite **não existe** na legenda, e uma faixa da legenda **não
   existe** no código. A família recebe rótulo de topo de escala estando no meio
   da escala que o próprio relatório imprime.
3. **A base da reserva é maior que a carteira exibida.** A composição líquida da
   reserva conta base acima do total da seção de investimentos — a reserva se
   apoia em ativos que a seção nem mostra. E o acoplamento entre "reduzir a classe
   sobre-alocada" e "manter a cobertura" não é divulgado em nenhuma das duas
   superfícies. (Residual de um cluster **refutado** na r4: o "excedente
   inexecutável" caiu, este sobreviveu.)

## Achados cobertos

RV4-13 (Alto) · RV4-15 (Médio) · RV4-18 (Médio). Registro:
[[REPORT-REVIEWS-active]] §r4.

## Escopo

**PR1 — a taxa de retirada deixa de ser meta de retorno.** Decidir, com aval de
domínio, se o campo é renomeado, se a "meta" sai, ou se as duas viram métricas
separadas com rótulo próprio. Exige **emenda datada na [[ADR-191]]** antes do
código: é mudança no que o número afirma. Aceite: o parecer não pode mais emitir
risco de rentabilidade a partir de TRS — teste sobre o manifest.

**PR2 — uma régua só.** Faixas do código e legenda do apêndice passam a derivar da
**mesma fonte**. Aceite: gate que falha se existir rótulo no enforcer sem entrada
na legenda, ou faixa na legenda sem rótulo no enforcer — o gate fecha a classe, não
a instância.

**PR3 — base da reserva declarada.** A superfície declara qual base a cobertura
usa e o que foi excluído (os campos já existem no payload e têm **zero
consumidores**). Aceite: os campos de base e exclusão passam a ter leitor.

## Critério de aceite da lane

Cada um dos três números passa a **declarar sua base na própria superfície**, e
nenhum rótulo afirma uma grandeza diferente da que mede. Divergência que
sobreviver é decisão registrada em ADR, não drift.

## Não-objetivos com rota declarada

Recalcular TRS, cap rate ou cobertura: os cálculos conferem. Mexer na ordenação do
plano — é RV4-13 adjacente mas outro eixo, e a ordenação sem critério encodado
está registrada em RV3-07(b).
