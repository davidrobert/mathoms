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

## ✅ Parcial entregue em 2026-08-08 — PR #1337 (`ed7b1dc4`)

### A âncora sem alvo (RV3-04) e o gate bidirecional

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

**Verificação renderizada: rodou no CI e me corrigiu.** A 1ª versão do assert
tratava *"âncora sem alvo no DOM"* como defeito único e falhou em **4** ids —
`S4`, `S_IRPF_RENDA`, `S_IRPF_OTIMIZACAO`, `APP_C`. Nenhum é defeito: são seções
**habilitadas** que o `hide-when-empty` ([[ADR-167]]) tira do ar porque a fixture
de mock é esparsa. O assert conflava duas coisas — *"seção que nunca
renderiza"* (defeito) e *"seção que não renderizou desta vez"* (comportamento).
Corrigido: só falha âncora para seção **desligada ou inexistente**; alvo que
existe e mede zero (classe RV3-05) segue falha dura, ali não há desculpa de
hide-when-empty.

**Contexto de execução:** O teste E2E
(`report-layout.@critical.spec.ts`) enumera `a[href^="#"]` das **duas**
superfícies de índice sem depender de estarem abertas — a sidebar nasce
fechada e o drawer só existe em `<lg`, que é o falso-verde apontado no
§Insumos item 1 — e checa alvo existente com `height > 0`, mais uma guarda
contra "zero âncoras encontradas". **Não consegui rodá-lo**: neste worktree
`frontend/node_modules` é symlink para o repo principal e o Turbopack recusa
(*"Symlink [project]/node_modules is invalid"*), então o dev server não sobe.
Typecheck passa; a execução fica para o CI. O §Débito de método desta sprint
**não está satisfeito** por mim neste ponto — está declarado, não contornado.

⚠️ **A baseline visual/print MERGEOU SEM VERIFICAÇÃO — corrigindo o que esta
seção dizia antes.** A redação anterior era *"se o job falhar, a regravação é
esperada"*, o que pressupunha que o job rodaria. **Não rodou:** no #1337
*Frontend visual snapshots* e *Frontend print visual diff* saíram ambos
`skipping` (são opt-in por label, fora do `All checks green`). O TopNav perde a
entrada "2.5", então a faixa do topo **mudou de conteúdo** e nenhuma baseline
foi comparada nem regravada — nem por mim (o Turbopack não sobe neste worktree)
nem pelo CI.

**Follow-up com dono:** rodar os dois jobs num PR com o label `e2e`, **olhar** o
diff e regravar se for só a entrada removida. Regravar sem olhar é o anti-padrão
de #1290. O buraco de fundo — job de verificação que não gateia — está
registrado no §Inventário de follow-up do [[A40]] e é gatilho `sre-devops`.

**Não entrou:** S9 empty state parcial (⛔ pré-requisito não atendido, abaixo,
intocado), rótulo do disclosure em `ParecerRisksTable.tsx:93`, retítulo da S9,
e o `title` derivado do `titleMap` (as 4 divergências YAML↔componente do
§Insumos item 2).

## ✅ Parcial entregue em 2026-08-10 — PR #1355

### Itens 2 e 4, com dois inventários refutados

Fecha o que era construível sem produtor novo. **Só o item 1 (S9) resta**, e o
⛔ dele segue intocado.

> ### ⚠️ Inventário remedido em 2026-08-10 — dois pontos estavam vencidos
>
> | O que a lane afirmava | Medido em 2026-08-10 | Consequência |
> |---|---|---|
> | §Insumos item 2: **4** divergências YAML↔componente (`plano_de_acao`, `APP_B`, `APP_D` + a 2.5 já alinhada) | **6.** Faltavam `APP_A`, `APP_C`, `APP_E` — mas essas três são **só o prefixo** `"Apêndice X — "`, classe diferente das outras | mudou o desenho: o prefixo é convenção a **preservar** e compor, não deriva a eliminar |
> | §Problema RV3-15: *"no PDF o print CSS expande tudo, então o rótulo fica ao lado das linhas que o desmentem"* | ❌ **Falso.** `SParecer.print.css:19-22` tem `details.parecer-details > summary { display: none }` dentro do `@media print` — o rótulo **não existe** no PDF | o dano é na **tela**, e é pior do que o descrito: o leitor lê "de baixa severidade", decide não expandir e **não lê uma Crítica**. Continua P2, por motivo diferente |
>
> **E apareceu um rótulo que de fato mente no PDF, que a lane não citava:** a
> caption imprime `Mostrando 5 de 8 riscos` **acima das 8 linhas**, porque o
> print expande o `<details>`. Está no artefato que o cliente arquiva, sem
> disclosure que o desculpe. Corrigido no mesmo PR.

**Item 4 — a fonte passa a ser única, e o gate é o compilador.** `ReportSection`
perdeu o prop `title` e deriva de `sectionHeading(id)`; o `id` virou união
literal emitida pelo codegen (`LayoutSectionId`). As duas formas do defeito —
`title` hardcoded e id que não existe no layout — são **erro de compilação**.
Gate por construção vale mais que teste: não há onde digitar um heading
divergente.

O prefixo de apêndice é composto **na borda de render**. No `buildTitleMap` (que
alimenta nav e ToC) o título segue **nu** — com o prefixo lá, `shortLabel`
cortaria em `" — "` e os cinco apêndices virariam "Apêndice A", "Apêndice B"…
ao lado do badge que já diz a letra. É a regressão que o `product-designer`
apontou e que a mutação M4 agora trava.

Copy decidida com `product-designer` (as 3 divergências substantivas):

| id | era | virou | por quê |
|---|---|---|---|
| `APP_B` | YAML "Premissas Econômicas" | **"Premissas e Metodologia"** | o título do YAML é o de um **card da própria seção** (`report-inventory.expected.json`), e omitia "Metas Vigentes" + "Pilares Metodológicos" |
| `APP_D` | YAML "Referências e Recursos" | **"Referências e Fontes"** | não há recurso nem link; há referências (pilares) e fontes (lineage) |
| `plano_de_acao` | heading "Plano de Ação" | **YAML vence** | a cauda "— Decisões em Vigor" impede ler o relatório como plano editável; nav não muda (`shortLabel` corta em `" — "`) |

**Item 3 (retítulo da S9) entrou junto** — `"Riscos e Sucessão — Lacunas de
Proteção"`, endossado sem ajuste. Entrou aqui porque puxa o mesmo rebaseline de
snapshot e PDF; separar pagaria duas vezes. **Cascata obrigatória cumprida:**
`config/prompts/section_summaries.yaml` (o `label` é o título que o LLM recebe
para escrever o parágrafo da própria seção) e `config/prompts/parecer_planejador.yaml`
(`title`; o `id: riscos_protecao` é identidade e **não** muda). Sem ela a
divergência só migraria de YAML↔componente para YAML↔prompt.

**Item 2 — copy sozinha não resolvia.** `sorted.slice(5)` é cego à severidade:
com 6 riscos Críticos, o 6º ia para trás do disclosure. Agora **Crítica e Alta
nunca colapsam** e o rótulo é derivado da composição real do conjunto escondido
(`"Ver mais 3 riscos de severidade média e baixa"`). A caption passa a declarar
só o total, que é verdadeiro nas duas mídias.

**Prova de mutação (contada).** Antes desta entrega, mudar o heading de
`APP_B`/`APP_D` derrubava **0** testes — os 154 arquivos da suíte passavam verde
sobre a divergência, que é o sintoma de "a suíte concorda com o bug".

| Mutação | Cai |
|---|---|
| `<ReportSection id="S1_TYPO">` | `TS2322` |
| voltar a passar `title=` | `TS2322` (prop não existe) |
| corte volta a `slice(TOP_LIMIT)` | 1 teste |
| rótulo volta a `"de baixa severidade"` | 2 testes |
| prefixo some do heading | 1 teste |
| prefixo vaza para o mapa do índice | 1 teste |

**Item 5 (baseline) — rodou, e o resultado corrige a leitura da lane.** O PR
carrega `visual`, `print` e `e2e` de propósito. Os dois jobs visuais saíram
**`pass`** — e isso **não** é o mesmo que "a mudança foi verificada":

> ### ⚠️ O gate de pixel não consegue ver retítulo de seção (medido 2026-08-10)
>
> `sections.snapshots.visual.spec.ts` usa `maxDiffPixelRatio: 0.025` — 2,5% da
> área da **seção inteira**. O `<h2>` da S9 mudou de *"Riscos e Proteção —
> Seguros Críticos"* para *"Riscos e Sucessão — Lacunas de Proteção"*, e a
> baseline `S9-{light,dark}-visual-linux.png` **passou sem diff acusado**: o
> heading é uma faixa fina no topo de uma seção alta, muito abaixo do limiar.
>
> A tolerância foi calibrada para não perseguir antialiasing de canvas
> (`chart.js`), e o comentário do arquivo declara a intenção — *"captura
> mudanças estruturais (ex.: +35px de altura = 7% diff em S1)"*. **Mudança de
> texto não é mudança estrutural sob essa métrica.** Consequência: o job de
> snapshot **não gateia copy de heading**, e afirmar "verificado porque o
> visual passou" seria falso.
>
> Isto **aprofunda** o §Follow-up do #1337, que atribuía o buraco a *"o job não
> rodou"*. Rodando, ele ainda não vê a classe de mudança que esta lane produz.
> Gatilho `sre-devops`, junto do item já registrado no §Inventário de follow-up
> do [[A40]].

**A verificação renderizada existe — é a camada de TEXTO, não a de pixel.**
`print-text.@critical.spec.ts` (*"todo título de seção renderizado na tela chega
ao PDF"*) roda no *Report render gate* dentro de **Frontend checks**, que é
required, e passou com os títulos novos. É ela que satisfaz o §Débito de método
para os headings, não o snapshot. Continuo **sem** conseguir rodar Playwright
neste worktree (`node_modules` é symlink, o Turbopack recusa) — a execução foi
do CI.

**O E2E de fluxo pegou um spec meu que o worktree não alcançava:**
`parecer-degradacao.@critical.spec.ts:93` fixava a caption antiga. Corrigido no
mesmo PR. O job `frontend-e2e` acusou **outras** falhas — `category-overrides`,
`plano-*`, `property-finance`, `protection-cadastro`, `learning_loop`,
`drill-down` — em telas que este PR não toca. **Não afirmo que sejam
pré-existentes:** o job é opt-in por label e não há execução recente em `main`
para comparar, então a única leitura honesta é *"desconhecido, e o histórico não
permite decidir"*. Registrado como follow-up nº 7 abaixo.

**Não entrou:** item 1 (S9 empty state) — o ⛔ abaixo é o mesmo, intocado.

> ### ⚠️ O RV3-28 foi endereçado pela metade — registrado no closeout
>
> O título desta lane nomeia RV3-28, e o §Parcial acima era **silencioso**
> sobre ele. Fechado: a incoerência de **título** (heading e índice derivam da
> mesma fonte; APP_B/APP_D/S9 retitulados). **Aberto, e é o núcleo do achado:**
> a incoerência de **hospedagem**. Re-medido em 2026-08-10:
>
> ```
> S8 | "Previdência — PGBL e Fiscalidade" | cards: []
> S7 | "Independência Financeira — …"     | cards: ['previdencia_pgbl']
> ```
>
> `PrevidenciaPgblCard` renderiza em `S7IndependenciaSection.tsx:103`. A seção
> titulada pelo domínio **não hospeda o card** — que é exatamente o que o
> achado descreve, e o que o §Escopo chama de *"validador de hospedagem de
> componente"*. **Dono: esta lane.** Não confundir com o `title` derivado do
> LAYOUT, que fecha a deriva de **nome**, não a de **lugar**.

### Follow-ups nomeados (com dono e condição de retomada)

1. **`§{section_id}` chega cru ao cliente** (`ParecerRisksTable`: `§S9`,
   `§S_IRPF_RENDA`). Numa lane chamada "navegação e **ponteiros**", é o ponteiro
   menos legível do relatório, e o padrão contrário já existe em
   `ParecerAncoraChips` ([[ADR-296]]). O `titleMap` desta lane é o insumo. **P3**,
   `product-designer` — não entrou para não expandir escopo de um PR que já
   move 4 headings.
2. **`"Real Estate"` viola COPY_GUIDELINES §9** (inglês cru). Pior: `shortLabel`
   descarta a parte em português e **mantém** a inglesa no TopNav. **P3**,
   `product-designer`.
3. **Pilares metodológicos duplicados** entre APP_B (prosa) e APP_D (tabela).
   **Condição de retomada:** ao remover a tabela duplicada, retitular APP_D para
   `"Fontes e Rastreabilidade"` **no mesmo PR** — titular hoje para um estado
   futuro é o erro que o ⛔ da S9 evita.
4. **Corpo do prompt da S9** (`section_summaries.yaml`, "mapeia riscos
   prioritários (vida, invalidez, sucessório…)") pede alinhamento leve ao novo
   eixo. Só o `label` foi sincronizado aqui — o corpo é gatilho
   `prompt-engineer`, não carona deste PR.
5. **`CoberturaSegurosCard` segue hospedado na S9** sob um título que agora diz
   "Lacunas". Tolerável enquanto a 2.5 está desligada. **Condição de retomada:**
   ao ligar `S_PROTECAO`, decidir no mesmo PR se a tabela sai da S9 — senão duas
   seções mostram a mesma tabela sob títulos opostos.
6. `docs/plan/REPORT_PREMIUM/EXEMPLO_DE_RELATORIO.html` segue com os títulos
   antigos. Precedente do #1286: a paridade daquele mockup é visual/estrutural,
   não lexical.
7. **`frontend-e2e` acusa 8+ falhas em telas fora deste PR** (`/config`,
   `/plano`, `/protecao`, dashboard, learning loop). O job é opt-in por label e
   **não há execução recente em `main`** para servir de baseline, então não dá
   para decidir se são pré-existentes. **Condição de retomada:** rodar o job uma
   vez em `main` (workflow_dispatch) e comparar; se forem pré-existentes, o
   achado é que o gate `@critical` está vermelho e ninguém vê — mesma classe do
   §Follow-up do #1337. Gatilho `sre-devops`.

## 🔀 Duas transferências escritas — 2026-08-11 (closeout)

Decisão do `product-manager` ao abrir as lanes novas. **Sem estas duas linhas a
l7 é infechável**, e o §Escopo abaixo continua reivindicando trabalho que já tem
outro dono.

| O que sai | Para onde | Por quê |
|---|---|---|
| **S9 empty state parcial** + o ⛔ inteiro | **[[A40.l35]]** | O §Deferido da [[ADR-240]] já trocou de dono (2026-08-11). Precedente de spin-off: [[A40.l15]] ← [[A40.l3]] |
| **Metade de HOSPEDAGEM do RV3-28** | **[[A40.l34]]** | "Mover o card de PGBL para a S8" pressupõe que o card deve existir com a base atual — e **é a l34 que decide isso** |

> ### ⚠️ O ⛔ do §Escopo abaixo está VENCIDO — leia a [[A40.l35]]
>
> Ele afirma que `data.protection_bundle` *"não tem produtor"*. **Falso, medido
> em 2026-08-11:** o produtor existe (`populate_protection_bundle` →
> `protection_bundle_adapter` → `build_protection_bundle_sync`). O que ele faz é
> **calcular sobre zeros** — 5 zeros e 2 `False` hardcoded, incluindo
> `gross_estate_brl_cents`, então o **ITCMD também sai R$ 0**. Rodando o
> calculator real: `gap = R$ 0` hoje contra **R$ 4.500.000** com renda plumbada.
>
> A conclusão prática do ⛔ **não muda** (não ligar a S9 agora); o diagnóstico
> sim, e é ele que a l35 herda.

**O que resta nesta lane:** o RV3-28 na metade de **nome** — retítulo da S8 para
`"Carga Tributária PJ — Regime e Base Dedutível"` (copy do `product-designer`) +
os 2 cross-links + a cascata nos prompts. Feito isso, a l7 fecha `shipped`: os 4
bullets do §Critério de aceite são sobre âncora de nav, e os 4 já foram
satisfeitos por #1337 e #1355.

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
baixa severidade" enquanto o `extra` inclui severidade média. ~~**No PDF o print CSS
expande tudo**, então o rótulo fica ao lado das linhas que o desmentem — no
artefato que o cliente arquiva.~~ Por isso o painel pediu P2, não P3.

> ⚠️ **A frase riscada é falsa** — medido 2026-08-10, ver §Parcial acima. O
> print **esconde** o `<summary>`. O achado continua P2 porque o dano é na
> **tela** (o leitor não expande e não lê uma Crítica), e porque a caption
> — essa sim — mentia no PDF.

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

   > ⚠️ **Eram 6, não 4** — medido 2026-08-10 (§Parcial acima). `APP_A`, `APP_C`
   > e `APP_E` também divergiam, mas **só pelo prefixo** `"Apêndice X — "`, que
   > é convenção a preservar. Entregue em #1355: o prop `title` deixou de
   > existir, e o prefixo passou a ser composto na borda de render.

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
