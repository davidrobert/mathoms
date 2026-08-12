---
id: A40.l39
type: lane
title: "Posição por instituição: o header '31/12' mente para 10 de 16 linhas — separar visão corrente da fiscal"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l39-posicao-visoes-corrente-fiscal
adrs:
  - "[[ADR-238]]"
  - "[[ADR-245]]"
  - "[[ADR-376]]"
depends_on: ["[[A40.l38]]"]
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/pipeline
  - area/frontend
  - area/financial-planning
---

# A40.l39 — `posicao-visoes-corrente-fiscal`

> **Aberta em 2026-08-11.** Parecer `financial-planner`: um balanço tem uma
> data; o 31/12 é marco, não linha da fotografia corrente. Co-design
> `senior-cto` + `data-engineer` (2026-08-11).

## Problema

O card `posicao_informe_31_12` (S1) mistura 6 linhas de informe 31/12/2025 com
10 linhas de extrato com saldo **atual** (até 2026-08-11) sob o header "Valor
em 31/12" ([PosicaoInformeCard.tsx:86](../../../../frontend/src/components/report/cards/PosicaoInformeCard.tsx)).
A mesma conta aparece 2× sem vínculo (Itaú CC informe R$ 0,00 + extrato
R$ 5.156,06; Wise BRL idem). A regra "informe vence extrato D+1"
([[ADR-238]] D5) é letra morta: a janela roda sobre o **último** extrato da
conta e nunca dispara em workspace com extratos correntes.

## Entregável

Dois PRs + ADR:

- **PR-a (mecânico, sem mudança de número):** propaga `data_referencia`
  (`YYYY-MM-DD`, fim de período) + `data_referencia_precisao` + `id` estável
  (`{codigo}:{moeda}:{fonte}:{ano_base}`) até as linhas de
  `posicao_31_12`/`caixa_detalhes`. Sem bloco novo no payload — **renomear e
  migrar** o produtor existente, nunca criar segundo produtor (veto
  `data-engineer`).
- **ADR (Proposto antes do PR-b):** visões corrente×fiscal; emenda datada na
  [[ADR-238]] (D5 parcial — `_period_in_janela_d1` deixa de existir como
  regra de negócio); destino explícito da [[ADR-245]] (fallback ME
  permanece, com data e proveniência por linha).
- **PR-b (split visual):** S1 vira "Posição por Instituição e Moeda" só com
  posição corrente + coluna de data + sinal de defasagem; bloco
  "Fechamento de 31/12/AAAA" (informe + IRPF, zero extrato) na seção
  **Renda Anual e Impostos**, levando o alerta CBE. Spec de UI:
  `product-designer` (pendente — bloqueado por limite de spend em
  2026-08-11; obrigatório antes do PR-b).

## Critério de aceite

- Header ≡ conteúdo: card que declara data fixa só renderiza linhas daquela
  data (o dogfood atual **reprova**; o novo desenho passa).
- Nenhuma tabela mistura datas sem coluna de data; nenhuma tabela de datas
  mistas exibe total.
- CBE continua ancorado no agregado 31/12 após a realocação.
- Leitor tolerante a artefato antigo (mutação por remoção das chaves novas
  sobre view-model + contexto do parecer). Alinhar com [[A40.l5]]
  (`check_view_model_contract`) antes do PR-a.
- PR-a: goldens/snapshot idênticos exceto campos aditivos (sem `value_delta`
  monetário no manifesto).
