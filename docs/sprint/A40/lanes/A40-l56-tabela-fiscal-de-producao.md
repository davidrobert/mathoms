---
id: A40.l56
type: lane
title: "A tabela fiscal de produção: a row é internamente inconsistente e nenhum golden a atravessa"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l56-tabela-fiscal-de-producao
owner: data-engineer
adrs:
  - "[[ADR-375]]"
  - "[[ADR-135]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/db
---

# A40.l56 — `tabela-fiscal-de-producao`

> **Aberta em 2026-08-12**, no fechamento da rodada de follow-ups (decisão do
> dono). Nasceu `l50` e foi renumerada no mesmo dia: o #1409 tomou o id em
> paralelo — instância viva da classe que a [[A40.l59]] fecha. Origem: co-design e execução do PR1/PR2 da [[A40.l34]] (§Emenda da
> [[ADR-375]]). Dono: `data-engineer` — os dois itens moram no contrato de
> `fiscal_parameters` e no substrato golden, o mesmo especialista fecha ambos.
> Prioridade herdada da severidade na origem; o `product-manager` repriorisa no
> planejamento se discordar.

## Problema

Dois achados medidos em 2026-08-11/12, sobre o mesmo objeto — a tabela
progressiva de IR que **produção** consome ([[ADR-135]]):

**1. A row de `fiscal_parameters` é internamente inconsistente, e isso bloqueia
a [[ADR-375]] D5.** `deducao_brl_cents` guarda a parcela a deduzir **mensal**
contra faixas **anuais** — mismatch auto-declarado como FLAG na migration
`e1f2a3b4c5d6` (linhas 28-37: *"o primeiro consumidor decide entre (a) reescalar
parcelas para anual ou (b) reescalar brackets para mensal"*). Medido:

- Usar a parcela crua numa fórmula anual erra **R$ 4.195,84** numa base de
  R$ 40.000/ano (faixa de 15%).
- **E o ×12 não fecha**: anualizando, a tabela fica contínua a ≤ R$ 0,05 em três
  fronteiras e abre degrau de **R$ 11,04** em R$ 26.963,20. `upper_brl_cents[0]`
  (R$ 26.963,20) e `deducao_brl_cents[1]` (anualizada ÷ 0,075 = R$ 27.110,40)
  vêm de **vintages diferentes** — nenhuma das duas opções da FLAG resolve.

A economia diferencial `IR(base) − IR(base − aporte)` (D5) **não é
implementável** antes de a row ser reconciliada. Foi por isso que o PR2 da l34
parou na ausência, sem publicar a diferencial.

**2. Nenhum teste de golden atravessa o construtor de produção.**
`PrevidenciaConfig.from_fiscal_parameters` só roda quando `ctx.config_store`
existe ([`analyze_finances.py:2191`](../../../../scripts/analyze_finances.py) e
`:2237`) — e em **todo** caminho de teste ele é `None`. O substrato golden
exercita `from_fiscal` (dict legado) via `write_e5_config(irpf_faixas=...)`. O
falsy-zero do PR1 (#1383) foi corrigido **às cegas do golden**: só unit test
cobre o construtor que produção usa.

## Escopo

1. **Decidir o vintage oficial** da tabela (faixas + parcelas do mesmo
   ano-calendário) — validação de valores é gatilho de `financial-planner`;
   forma da migration é de `data-engineer`.
2. Migration corretiva sobre os 3 anos seedados (2024-2026), com a decisão da
   FLAG registrada onde a FLAG mora.
3. **Teste de continuidade da tabela**: `IR(limite)` pela faixa de baixo ==
   `IR(limite)` pela de cima, a ≤ R$ 0,05, em **toda** fronteira — o teste que
   teria acusado o mismatch no seed original.
4. Fake de `config_store` no substrato golden (ou fixture equivalente) para
   **≥1 execução golden atravessar `from_fiscal_parameters`** com `ir_brackets`
   reais.
5. Declarar o desbloqueio do D5 à [[A40.l34]] (nota datada na [[ADR-375]]).

## Critério de aceite

- Continuidade provada em toda fronteira da tabela vigente, por teste que roda
  em todo PR.
- **Prova por mutação no construtor de produção**: reintroduzir o falsy-zero em
  `from_fiscal_parameters` derruba ≥1 teste que passa pelo caminho golden — hoje
  derruba **zero** goldens.
- A [[ADR-375]] ganha a nota datada de desbloqueio do D5, e a [[A40.l34]] é
  citada como consumidora.

## Colisão declarada

Nenhuma com o PR3 da [[A40.l34]] (hospedagem/frontend). A migration toca
`backend/alembic/versions/` — verificar head antes de abrir.
