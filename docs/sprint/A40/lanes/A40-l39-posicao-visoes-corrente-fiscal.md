---
id: A40.l39
type: lane
title: "Posição por instituição: o header '31/12' mente para 10 de 16 linhas — separar visão corrente da fiscal"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P1
branch_slug: a40-l39-posicao-visoes-corrente-fiscal
adrs:
  - "[[ADR-238]]"
  - "[[ADR-245]]"
  - "[[ADR-376]]"
  - "[[ADR-382]]"
depends_on: ["[[A40.l38]]"]
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
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

## PR-a entregue — 2026-08-12 (PR #1399)

Plumbing mecânico no lugar: linhas de `posicao_31_12` e `CaixaDetalhe`
carregam `data_referencia` (`YYYY-MM-DD`, fim de período — 31/12/ano_base nas
linhas de informe, inclusive quando o override adota o informe),
`data_referencia_precisao` e `id` estável. `Posicao3112Row` extraído para
`types/posicao-31-12.ts`. Zero mudança de número.

## PR-b — spec de UI recebida (`product-designer`, 2026-08-12)

Duas metades commitáveis: (A) `PosicaoCorrenteCard` — coluna `Em` com
`<time>`, badge de defasagem em faixas de meses fechados usando
`color-mix(...)` + par `-on-tint` **no mesmo `className`** (a forma `/15` é
invisível ao `check_tint_contrast`), nudge agregado, coluna `Fonte`
condicional, `table-fixed`, deleta o `InformeVenceuNudge`; (B)
`FechamentoFiscalCard` em `S_IRPF_RENDA` — CNPJ formatado como identificador
até a [[A40.l40]] resolver o nome, CBE **fora** do `<details>` sazonal, total
travado por parágrafo de não-aditividade, `<details>` forçado aberto no print.

**Dois bloqueadores achados pela spec, a resolver no PR-b:**

1. `IrpfRendaSection` retorna `null` sem `irpf_kpis` — workspace com informe e
   sem IRPF perderia o card fiscal **e o alerta CBE** (obrigação legal).
   Relaxar o guard para `kpis || fechamentoRows.length > 0`.
2. A footnote PTAX 31/12 **não pode** ficar no S1 pós-split: o S1 converte
   saldos correntes. Falta confirmar qual taxa o pipeline usa nas linhas
   correntes em ME antes de escrever a footnote nova.

Âncora temporal única (defasagem e sazonalidade contra a data de geração do
relatório, nunca `Date.now()`) e `md:` inativo no print (703px) são restrições
do PR-b.
