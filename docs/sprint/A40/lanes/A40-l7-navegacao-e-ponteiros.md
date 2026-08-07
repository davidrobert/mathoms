---
id: A40.l7
type: lane
title: "Navegação e ponteiros: âncora sem alvo, seção que colapsa, mapa de seções incoerente"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P1
branch_slug: a40-l7-navegacao-e-ponteiros
adrs: ["[[ADR-240]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
  - priority/p1
  - area/frontend
---

# A40.l7 — `navegacao-e-ponteiros` (RV3-04, RV3-05, RV3-15, RV3-28)

> 🔓 **Liberada em 2026-08-07 (decisão do dono)**, no mesmo par que a [[A40.l5]].
> `depends_on` sempre foi vazio; faltava a liberação por-lane. Motivo: é o que
> resta da **KR-C** — a [[A40.l4]] entregou a metade "seção renderiza parágrafo",
> e as âncoras de nav sem alvo são a outra metade do critério (*"0 âncoras de nav
> sem alvo"*). Sem esta lane a KR-C fecha pela metade.
>
> **Não é par de execução com a l5** — as duas tocam `frontend/`, mas em camadas
> distintas (l5: tipos gerados + readers; l7: `ReportShell`/`S9`/`ParecerRisksTable`
> + `report_layout.yaml`). Podem correr em paralelo; quem mergear depois rebaseia.
>
> ⚠️ **Colisão real a vigiar:** a [[A40.l22]] mexe em `S_parecer` e no PDF, e esta
> lane mexe em `ParecerRisksTable.tsx:93` (o rótulo *"de baixa severidade"* que
> mente) — **a l22 estende a caption desse mesmo componente**. Se as duas correrem
> juntas, combine quem toca o arquivo, ou serialize l22 → l7.

## Problema

**Âncora sem alvo (RV3-04).** `S_PROTECAO` tem `enabled: false` com o componente
**entregue e testado** (17 Vitest) e ausente de `MIGRATED_SECTIONS`;
`buildNavGroups`/`tocGroups` (`ReportShell.tsx:107-126,187-207`) **não filtram
`enabled`** ⇒ link morto em **100% dos relatórios**. A [[ADR-240]] §Entrega
registra a fase que criou o componente e **nunca registra o flip** — instância do
padrão "gate mede produção, não consumo".

**Seção que colapsa (RV3-05).** `S9RiscosSection.tsx:87` colapsa a seção inteira
por `data_state == "empty"`, **depois** de imprimir a linha-promessa. O parecer
aponta `§<section_id>` como texto puro → leva a uma seção vazia.

**Mapa incoerente (RV3-28).** `config/report_layout.yaml:356` titula uma seção por
um domínio cujo card vive em **outra**. Julgar ponteiros contra um mapa incoerente
produz falso-positivo — por isso o retítulo vem junto.

**Rótulo que mente (RV3-15).** `ParecerRisksTable.tsx:93` rotula o resto como "de
baixa severidade" enquanto o `extra` inclui severidade média. **No PDF o print CSS
expande tudo**, então o rótulo fica ao lado das linhas que o desmentem — no
artefato que o cliente arquiva. Por isso o painel pediu P2, não P3.

## Escopo

- Filtrar por `enabled` em `buildNavGroups`/`tocGroups` — vale para qualquer seção
  futura, não só esta.
- **Decisão de produto:** ligar `S_PROTECAO` (flag + `MIGRATED_SECTIONS` + case no
  dispatcher + 4 cards + rebaseline de snapshot **e** PDF) **ou** remover a entrada
  de navegação. Não deixar o estado atual, que é o pior dos dois. **Co-owner
  `senior-cto`** para dispatcher/codegen — a lane emperra se o escopo técnico não
  tiver dono.
- S9: empty state **parcial**, não total — renderizar o bundle de proteção mesmo
  sem o bloco de risco.
- Rótulo do disclosure derivado da composição real do `extra`.
- Retítulo da seção incoerente + validador de hospedagem de componente.

## Critério de aceite

- Assert bidirecional: toda entrada de nav/ToC tem seção habilitada e vice-versa.
  **Prova:** flipar uma seção para `enabled: false` sem remover a entrada ⇒ teste
  vermelho (hoje isso passa em 100% dos relatórios).
- Validação **dentro** de `dev/codegen_report_layout.py`: falha antes de emitir os
  gerados, com o `section_id` ofensor na mensagem.
- E2E `@critical`: para todo `a[href^="#"]` do TopNav e do TOC, o alvo existe **e**
  tem altura > 0.
- **Verificação renderizada** — estender
  `frontend/tests/e2e/reports/report-layout.@critical.spec.ts` (já existe e roda em
  CI): para todo `a[href^="#"]` do TopNav e do TOC, o alvo existe **e** tem
  `getBoundingClientRect().height > 0`. Este é **o gate** da âncora saudável — nenhuma
  outra ferramenta emite veredito sobre isso.
