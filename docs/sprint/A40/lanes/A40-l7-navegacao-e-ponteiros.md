---
id: A40.l7
type: lane
title: "Navegação e ponteiros: âncora sem alvo, seção que colapsa, mapa de seções incoerente"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P1
branch_slug: a40-l7-navegacao-e-ponteiros
adrs: ["[[ADR-240]]"]
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
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

## ✅ Parcial entregue em 2026-08-08 — a âncora sem alvo (RV3-04) e o gate bidirecional

Fecha a **metade da KR-C** que era construível: *"0 âncoras de nav sem alvo"*.
A lane **segue aberta** — S9, rótulo do disclosure e retítulo não entraram.

**Decisão de produto tomada: remover a entrada de nav, não ligar a seção.**
Das duas opções que o §Escopo autoriza, "ligar `S_PROTECAO`" está **impedida
pelo ⛔ abaixo** — `data.protection_bundle` não tem produtor, então ligar
publicaria "Nenhuma apólice cadastrada" e seis linhas "Ausente" para todo
cliente, inclusive quem cadastrou apólice. Trocar silêncio por afirmação falsa
é pior que o link morto. A entrada volta ao YAML **no mesmo PR** que flipar
`enabled: true`, e o gate novo cobra os dois lados.

**O gate mora dentro do codegen** (`dev/report_layout_nav_targets.py`, chamado
por `codegen_report_layout.build()` **antes** de emitir), como o §Critério de
aceite exige — gerado que já contém o defeito não é gate. É **bidirecional**:

| Mutação | Resultado |
|---|---|
| seção `enabled: false` com link de nav vivo (= RV3-04) | ❌ `NavTargetError` |
| link para id que não é seção nem apêndice | ❌ `NavTargetError` |
| seção habilitada **sem** entrada de nav (direção inversa) | ❌ `NavTargetError` |
| re-inserir exatamente o link de `S_PROTECAO` | ❌ barrado |

Prova de mutação: neutralizar o gate derruba **3** dos 6 testes.

**Achado que muda a polaridade do filtro — `V0` não é seção do YAML.** A
seção "O que mudou" é renderizada pelo shell (`SHELL_SECTION_TITLES`) e
**não tem entrada em `sections`**, por decisão registrada no próprio YAML.
Filtrar nav por *"está no conjunto de habilitadas"* — a leitura literal do
critério — **apagaria V0 do índice**. O filtro correto é por *desligado
explicitamente*. O allowlist `SHELL_RENDERED_SECTIONS` tem paridade com o TSX
travada por teste, para não apodrecer.

**Verificação renderizada: escrita, não executada.** O teste E2E
(`report-layout.@critical.spec.ts`) enumera `a[href^="#"]` das **duas**
superfícies de índice sem depender de estarem abertas — a sidebar nasce
fechada e o drawer só existe em `<lg`, que é o falso-verde apontado no
§Insumos item 1 — e checa alvo existente com `height > 0`, mais uma guarda
contra "zero âncoras encontradas". **Não consegui rodá-lo**: neste worktree
`frontend/node_modules` é symlink para o repo principal e o Turbopack recusa
(*"Symlink [project]/node_modules is invalid"*), então o dev server não sobe.
Typecheck passa; a execução fica para o CI. O §Débito de método desta sprint
**não está satisfeito** por mim neste ponto — está declarado, não contornado.

⚠️ **Baseline visual/print provavelmente precisa de rebaseline deliberado.** O
TopNav perde uma entrada ("2.5"), então a faixa do topo muda de conteúdo. Pelo
mesmo bloqueio acima não pude renderizar para conferir **nem** para regravar —
e regravar baseline sem olhar é o anti-padrão registrado em #1290. Se
*Frontend visual snapshots* falhar, a regravação é esperada, mas **tem de ser
olhada**.

**Não entrou:** S9 empty state parcial (⛔ pré-requisito não atendido, abaixo,
intocado), rótulo do disclosure em `ParecerRisksTable.tsx:93`, retítulo da S9,
e o `title` derivado do `titleMap` (as 4 divergências YAML↔componente do
§Insumos item 2).

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

  > ⛔ **Este passo tem pré-requisito não atendido (medido 2026-08-08).**
  > `data.protection_bundle` **não tem produtor**: o E5 não emite a chave e
  > `get_report_data` não a injeta (só `_report_lineage`, `goals.premissas_snapshot`,
  > `comparisons`, `changelog`, `comparison_periods`). Tirar a S9 do empty state
  > hoje põe no ar `HeroGapProtecaoCard` com *"Nenhuma apólice cadastrada ainda"*
  > e **seis linhas "Ausente"** em `CoberturaSegurosCard` — para todo cliente,
  > inclusive quem cadastrou apólice em `/protecao`. Troca um silêncio por uma
  > afirmação falsa sobre o dado do cliente.
  >
  > A suíte não vê: `S9ProtectionCards.test.tsx` injeta o bundle direto na prop
  > do card; nenhum teste exercita o caminho do payload.
  >
  > **Condição de retomada** ([[ADR-240]] §Deferido): produtor do bundle **e**
  > correção do predicado de dependente em `protection_bundle_populator`
  > (filtra `role == "dependente"` e exclui `role == "filho"`, §Deferido da
  > [[A40.l10]]) — no mesmo PR. Ligar a fonte antes de corrigir o cálculo troca
  > uma afirmação falsa por outra.
  >
  > A afirmação de **ausência de cobertura** já foi unificada sobre
  > `documento ∪ cadastro` em [[ADR-240]] §Emenda 2026-08-08, então a
  > contradição 2.5 ↔ S9 não reaparece quando esta lane ligar a seção 2.5.
- Rótulo do disclosure derivado da composição real do `extra`.
- Retítulo da seção incoerente + validador de hospedagem de componente.

## Insumos entregues pelo PR #1286 (2026-08-08)

O PR corrigiu o título da 2.5, que atribuía metodologia a uma marca de curso e
por isso violava §13.1 (título novo: **`"Seguros — Cobertura Contratada"`**;
o anterior está registrado em COPY_GUIDELINES §13.2 e em [[ADR-240]] §Emenda).
Ao medir, produziu quatro achados que **caem nesta lane**. Não foram tratados lá
para não abrir branch paralela sobre `report_layout.yaml`/`ReportShell`.

1. **A âncora sem alvo (RV3-04) é pior do que "link morto": entrega copy.** Como
   `buildNavGroups`/`tocGroups` não filtram `enabled`, o título de uma seção
   desligada **chega renderizado ao cliente** — foi por aqui que a marca vazou.
   Medido: 0 ocorrências no `innerText` desktop, mas **visível a 390px** com o
   drawer do `FloatingNav` aberto. Consequência para o critério de aceite: o
   assert de altura `> 0` **não pega** esse caso, porque as duas superfícies de
   índice nascem fechadas (sidebar por `useReportTocOpen`; drawer só em `<lg`).
   Para gatear de fato, use `textContent` da subárvore do `<dialog>`/`nav`, ou
   monte o cenário mobile.

2. **A deriva YAML↔componente é classe, não instância.** Além da 2.5 (alinhada
   pelo #1286), divergem hoje: `plano_de_acao` (YAML "Plano de Ação — Decisões em
   Vigor" vs componente "Plano de Ação"), `APP_B` ("Premissas Econômicas" vs
   "Apêndice B — Premissas e Metodologia") e `APP_D` ("Referências e Recursos" vs
   "Apêndice D — Referências e Fontes"). O TOC diz uma coisa e o heading diz
   outra, no mesmo scroll. **Fix durável:** `ReportSection` deriva `title` do
   `titleMap` do LAYOUT em vez de cada seção hardcodar — mata as 4 de uma vez e é
   o "validador de hospedagem de componente" já no escopo.

3. **Retítulo da S9 é o resíduo do #1286, e a cauda é que sai.** Com a 2.5 virando
   "Seguros", a S9 ("Riscos e Proteção — **Seguros Críticos**") reintroduz a
   colisão pela cauda. Recomendação do `financial-planner`, não executada:
   `"Riscos e Sucessão — Lacunas de Proteção"`. Eixo honesto — 2.5 = *o que você
   tem contratado*; S9 = *o que falta e o que acontece na transmissão* (sucessão/
   ITCMD já mora lá, [[ADR-192]] D3). Mexer na S9 puxa rebaseline de snapshot **e**
   de PDF, que o #1286 não devia carregar.

4. ~~**Antes de ligar `enabled: true`, resolva a contradição de evidência.**~~
   **✅ Resolvido em 2026-08-08** — [[ADR-240]] §Emenda "cobertura tem duas
   fontes". A afirmação de ausência passou a ser decidida sobre
   `documento ∪ cadastro`; o KPI B declara escopo e cala o veredito de faixa
   quando a soma é sabidamente parcial. **Esta lane não precisa mais tratar
   disso antes do flip.**

   Duas correções ao que este item afirmava: (a) a S9 **não** dizia "coberto" —
   `data.protection_bundle` não tem produtor, então ela não dizia nada (ver o ⛔
   no §Escopo acima, que é o que sobra desta pendência); (b) a manifestação que
   **já chegava ao cliente** não era nenhuma das duas seções, e sim
   `pontos_urgentes`, corrigida no mesmo PR.

   Segue em aberto a nota lateral do `product-designer`: o `gap_qualitativo`
   mede "o que falta", que é o eixo declarado da S9 — decidir se continua
   hospedado na 2.5 é escolha de produto desta lane, agora sem risco de
   contradição factual.

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
