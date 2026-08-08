---
id: MOC-sprint-a40
type: moc
title: "Sprint A40 — Report trust: o dado que entrou tem de chegar ao usuário"
aliases: ["A40", "Sprint A40"]
sprint_status: current
date: "2026-07-30"
date_target: "2026-08-17"
theme: "report-trust"
---

# Sprint A40 — Report trust (revisão do relatório entregue, 2026-07-30)

> **Status:** `current` (aberta 2026-07-30; **Onda 0 em `open`** desde 2026-08-03 — ver §Ondas). **Continuação declarada** de [[PLAN-report-trust]]
> (`sprint_origem: A28`) — não é plano novo. A tese daquele plano ("o relatório
> não pode afirmar precisão que os dados não sustentam") é exatamente o que esta
> rodada mediu; as lanes daqui entram lá com `sprint_atual: A40`.

> **Origem:** skill `report-review` sobre o report `7a7e9333` (run `573a54a7`,
> pré-existente) do workspace dogfood, 2026-07-29 — registro em
> [[REPORT-REVIEWS-active]] §r3, 33 achados sistêmicos. **Nenhum stage foi
> re-executado**: o objeto é o artefato entregue. Cru + valores off-git em
> `storage/<uuid>/reviews/2026-07-29-573a54a7/`.

> **Revisão do sprint (painel 2026-07-30 — pm, senior-cto, data-engineer,
> product-designer, prompt-engineer, financial-planner):** 39 decisões, **33
> objeções**, 41 guardas. O painel **corrigiu o achado P0 antes da lane abrir** e
> reordenou duas prioridades. Correções incorporadas abaixo (§Decisões do painel).

## Tese

A A39 provou que o dado **entra** certo. A A40 prova que o dado que entrou
**chega ao usuário** — sem duplicar, sem sumir na renderização, e sem afirmar
mais do que a cobertura sustenta.

26 dos 33 achados são defeitos de **entrega**, não de cálculo: consumidor lê
chave que o emissor não emite, janela trocada, seção que colapsa depois de
prometer conteúdo, PII interpolada no render. O sinal decisivo é que a
conservação do razão fecha em **tol-zero (105/105 grupos)** — procedência e
comando de re-medição em [[REPORT-REVIEWS-active]] §r3 — e ainda assim existe
duplicação material medida — **o gate vigente mede a camada errada**.

## KRs

| KR | Métrica | Como se mede |
|---|---|---|
| **KR-A · Contrato de leitura** | Leituras órfãs conhecidas **5 → 0** *e* existe gate que hard-falha quando a sexta aparece | `dev/check_view_model_contract.py` (novo) cruzando schema E5 × tipos do frontend × readers Python. Prova do gate: fixture com chave órfã ⇒ EXIT≠0 |
| **KR-B · Não-duplicação do razão** | Duplicação cross-grupo **não-explicada = 0** no corpus dogfood | Check cross-grupo em `dev/certify_ledger_local.py`. Baseline congelado pela [[A40.l1]] **antes** de qualquer fix. Anti-Goodhart: ocorrências whitelisted contadas em **linha separada**, nunca somadas ao numerador |
| **KR-C · Entrega visível** | Nº de seções que **renderizam** parágrafo == nº de seções com narrativa **emitida** (hoje **0 de 16**) *e* 0 âncoras de nav sem alvo | Teste de render (Vitest/RTL) sobre payload golden + assert bidirecional nav↔seções em `ReportShell.tsx`. CV9 redefinido para medir **entrega**, não geração |
| **KR-D · PII zero no entregue** | 0 violações no view-model; critério 4 da [[ADR-337]] existe e é executável | Gate de PII sobre o view-model. Fixture sintética com identificador de terceiro + matrícula + endereço ⇒ bloqueio no CI |
| **KR-E · Honestidade da recomendação** | 0 recomendações no topo do plano cuja premissa o próprio payload contesta, sem pendência pareada | Predicado determinístico `premissa → campo E5` em teste sobre payload golden |

**KR rejeitado deliberadamente:** cobertura (`N% dos achados fechados`) — mede
burn-down, não valor, e trataria abreviação `k`/`M` como equivalente a dupla
contagem. Também rejeitado KR de percepção: em dogfood com N=1 o time É o
usuário, e viraria carimbo.

## Gate de saída e encerramento (decisão do dono, 2026-08-03)

Até 2026-08-03 esta sprint **não tinha critério de encerramento**: o frontmatter
declarava só `date: "2026-07-30"` (criação) e as 6 ocorrências de "gate de saída"
no arquivo eram **todas ponteiro** para [[PLAN-report-trust]] — zero seção
própria. Duas consequências medidas: "antes do fim da sprint" não tinha referente,
e o tripwire da [[A40.l21]] (*"se a [[A40.l18]] escorregar >1 sprint, reverta a
l21"*) não era avaliável. **Esta seção é o host que faltava** (fecha a §Pendência
de decisão nº 7).

**Critério substantivo — herdado, não novo.** A A40 encerra quando o
[§Gate de saída do dogfood](../../plan/REPORT_TRUST/_README.md) de
[[PLAN-report-trust]] fica verde: 2 re-runs completos consecutivos (E0→E6 +
parecer + revisão do dono) com zero ocorrência nas 6 classes, nenhum P0/P1 novo
aberto nesses 2 re-runs, e os gates de owner da [[A28]] executados. Não se
duplica o gate aqui — duplicar criaria duas fontes de verdade sobre a mesma
condição de parada.

**Cláusula de reinício do contador — [[A40.l2]] (2026-08-06).** O flip do enforce de
colapso cross-documento muta o E3 **a montante de todo run E0→E6**, logo **zera** o contador
de 2 re-runs consecutivos — pelo mesmo argumento que recusou fundir a [[A42]] na A40. Por
isso: **o contador de 2 re-runs só inicia depois que a [[A40.l2]] estiver terminal** — flip
mergeado, ou flip declarado não-entregue. Sem esta cláusula, se o flip mergear com o contador
em 1/2, alguém decide na hora se recomeça; é a pior decisão possível, tomada sob pressão de
`date_target`.

**§Estado dos KRs — obrigação de leitura honesta.** Se o flip escorregar, a **KR-B é
reportada não atingida**. É proibido ler as 261 ocorrências como "explicadas" por estarem
**medidas** na sombra: medir não é corrigir, e contar sombra como explicação é Goodhart contra
o anti-Goodhart escrito no próprio KR.

**Insumo declarado do 1º re-run (2026-08-05).** A revisão do dono no primeiro dos
2 re-runs entra com **dois checklists na mão**, não em leitura livre: (1) o
§Checklist bloqueante da [[A40.l4]] — os 7 clusters, com atenção aos 3 fixes da
remediação final que nunca passaram por verificação renderizada (DAS em silêncio
no `s8`, `s4` sem contagem, CV9 com `summary_suppressed_by`); (2) o §Residual
medido da mesma lane. Isto **não** adiciona cláusula ao gate de
[[PLAN-report-trust]] — as 6 classes são enunciadas sobre propriedade, nunca sobre
lane, e transformá-las em checklist de lane produziria gate satisfazível por não
construir a superfície. É insumo operacional da execução do gate, e vive aqui.

**Data-alvo: `2026-08-17`** (`date_target` no frontmatter; precedente de campo é
o `closed:` da [[MOC-sprint-a33]], único de 35 MOCs de sprint a datar
encerramento). É **alvo, não compromisso**: existe para dar aritmética ao
tripwire, não para forçar corte.

> **Premissa da data, explicitada porque não foi medida.** O contador de 2 re-runs
> só pôde iniciar quando a [[A40.l16]] aterrissou (`0f8c3b18`, #1159, 2026-08-03) —
> antes dela o run não completava. Daí duas semanas de janela de gate. A cadência
> histórica **não** foi usada como base e contradiz esse número: medido no flip de
> `sprint_status: done` das últimas 5 sprints fechadas, o span foi de 0 a 2 dias
> (A35 0 · A33 1 · A38 1 · A37 2), contra 26 lanes ainda abertas aqui. Usar a
> cadência daria data indefensável; usar o gate dá uma verificável. **Sobrescrever
> é uma linha no frontmatter** — a decisão do dono foi a *forma* (gate + data), não
> este valor.

**Tripwire da [[A40.l21]], agora com gatilho computável.** Se **o writer** da
[[A40.l18]] (o **PR2**) não tiver mergeado até `date_target`, a l21 é revertida —
os read sites de `partial_failure` são dead code pelos critérios do próprio repo
enquanto nenhum writer o emite. Owner do gatilho: quem fizer o pickup seguinte
após a data. Antes desta seção, "1 sprint" não tinha referente e o tripwire era
prosa em 3 lugares e mecanismo em nenhum.

> **Qualificação de 2026-08-06, medida.** A l18 passou a entregar em 2 PRs e o
> **PR1 já mergeou** (`4620cc04`, #1242): ele adiciona `PipelineStageStatus.degraded`
> e o gate de paridade, mas **não emite `partial_failure`** — o status segue
> inalcançável em produção. Lido ao pé da letra, o predicado original ("a l18
> mergeou") já estaria satisfeito por um merge que não destrava nada, e o
> tripwire ficaria verde medindo a camada errada. O que arma o tripwire é o
> **writer**, não a lane.

> **Tripwire DESCARREGADO em 2026-08-07 — não é mais avaliável na `date_target`.**
> O writer da [[A40.l18]] mergeou (`b8460274`/#1258) e, no mesmo dia, o produtor do
> desfecho retido também (`039c1b6d`/#1278, PR2 da [[A40.l20]]). Com isso: (a) os
> read sites de `partial_failure` da [[A40.l21]] deixaram de ser dead code — há
> writer; (b) a amarra de reverter o PR1 da [[A40.l20]] junto com a l21 se
> extingue, porque a l20 é terminal. **Nada a fazer na `date_target` por este
> tripwire.** Fica registrado em vez de apagado: um tripwire que some sem dizer
> que foi desarmado é indistinguível de um que ninguém avaliou.

**O que esta seção deliberadamente não faz:** não fixa "nada sai da A40" (decisão
separada do dono, 2026-08-03, e mantida) nem transforma a data em critério de
corte. Lane que atravessar a data segue na sprint; o que a data governa é o
tripwire.

**E na `date_target`, a decisão é promoção individual — não fusão de sprint (2026-08-05).**
A pergunta "colocar a [[A42]] inteira dentro da A40" foi avaliada com painel
(`product-manager`, `information-architect`, `senior-cto`) e recusada. O motivo é
mecânico e vale registrar aqui, porque é **sobre esta seção**: os dois gates de saída são
adversariais — toda lane A42 muta E0→E4, upstream de todo run E0→E6, então cada merge da
A42 **zeraria o contador de 2 re-runs consecutivos** desta sprint, enquanto o gate da A42
exige rodar instrumentos cuja função é abrir achado novo (o que a cláusula "nenhum P0/P1
novo nesses 2 re-runs" proíbe). A sprint fundida só fecharia quando a A42 já estivesse
pronta — e 12 lanes a mais tornariam a `date_target` ficção, matando o único gatilho
computável do tripwire da [[A40.l21]]. Se a A40 não fechar até `2026-08-17`, a saída é
**promover lane individual** da A42 por consumidor datado (precedente [[A40.l24]],
promovida da [[A41]] assim), não fundir. Registro em [[MOC-sprint-a42]] §Gatilho de
promoção a `current`.

## Lanes (32)

Critério de agrupamento: **arquivo compartilhado** (evita merge-hell entre
branches `agent/*` paralelas) **e** risco compartilhado.

**Convenção da coluna Título:** é **rótulo curto**, não o título canônico — este
é o `title` do frontmatter da lane. Medido em 2026-08-05: 1 das 31 coincide
literalmente. Divergência de redação aqui **não** é defeito; divergência de
`priority` ou de `depends_on` é.

| Lane | Título | Prio | depends_on | Achados |
|---|---|---|---|---|
| [[A40.l1]] | Instrumento: detector de duplicação cross-grupo + baseline congelado | P0 | — | débito de método r3 #4 (habilita l2) |
| [[A40.l2]] | Identidade de lançamento cross-documento (`tipo_conta` + `titular`) | **P0 Crítico** | l1 | RV3-01, RV3-30 · **[[ADR-354]]** |
| [[A40.l3]] | Janela canônica: todo número rotulado 12m lê `janela_12m` | P0 | — | RV3-02, RV3-16, RV3-17 |
| [[A40.l4]] | Entrega de narrativas de seção + re-triagem do que passa a aparecer | P0 | — | RV3-03, **RV3-33 (7 inertes)** |
| [[A40.l5]] | Codegen do view-model + gate de contrato (mata a classe) | P1 | — | RV3-09, RV3-26, RV3-12, RV3-22 |
| [[A40.l6]] | Cards de imóvel e dívida: PII cartorial + contrato + zero-como-valor | P1 | l5 | RV3-06, RV3-12, RV3-27 |
| [[A40.l7]] | Navegação e ponteiros: âncora sem alvo, seção que colapsa, mapa incoerente | P1 | — | RV3-04, RV3-05, RV3-15, RV3-28 |
| [[A40.l8]] | Cobertura do manifest do parecer (dado renderizado inalcançável) | P1 | — | RV3-08 |
| [[A40.l9]] | Materialização de config run-scoped (input zerado silenciosamente) | **P1** | — | RV3-11 |
| [[A40.l10]] | Ordem do plano + pendências do dono | P1 | l9 | RV3-07, RV3-10, **RV4-02** (P0, admitido 2026-08-04) |
| [[A40.l11]] | Cobertura e incerteza na tela | P2 | l3, l4 | RV3-13, RV3-14, RV3-29 · flip [[ADR-353]] |
| [[A40.l12]] | Classificação incompleta distorce KPI | P1 | l1 | RV3-20, RV3-21 · flip [[ADR-351]] |
| [[A40.l13]] | Copy e design system | P2 | l4 | RV3-23, RV3-24, RV3-25 |
| [[A40.l14]] | Limpeza de órfãos e schema morto | P3 | — | RV3-32 + handoff A39 |
| [[A40.l15]] | Consumo Consciente: KPI de pontuais na base da janela (+3 co-changes E5) + base do texto do donut e do chart mês a mês | P2 | l3 | spun off da l3 (mudança de domínio; exige rebaseline de snapshot) |
| [[A40.l16]] | Desescalar `number_in_prose`: defeito de forma para de apagar conselho e de derrubar o run | **P0** | — | incidente `2ded7aab` · emenda **[[ADR-304]]** + **[[ADR-358]]** |
| [[A40.l17]] | Custo e cache no caminho `needs_review` do parecer | P1 | — | incidente `2ded7aab` |
| [[A40.l18]] | Criticidade de stage: add-on advisory não veta o entregável | **P0** | l21 | incidente `2ded7aab` · **[[ADR-357]]** |
| [[A40.l19]] | Migration do drift de enum de status (4 valores) | P1 + gate de deploy | — | **[[ADR-357]]** §7 |
| [[A40.l20]] | `PlannerReview` representa gerado-e-retido (destrava a UI) | **P0** | l18 ✅ | **[[ADR-366]]** `Decidido` — eixo próprio, **sem** emenda na [[ADR-204]] |
| [[A40.l21]] | Leitores tolerantes a `partial_failure` (reader-first) | **P0** | — | **[[ADR-357]]** §Consequências |
| [[A40.l22]] | Superfície de degradação no relatório + PDF | **P0** | l20 | fatia premium da F11.5 · **bloqueador do beta** (6ª classe do gate de saída) |
| [[A40.l23]] | Gate: ADR citada em prosa resolve para arquivo (reserva de ID é invisível) | P2 | — | classe exposta pela **[[ADR-345]]** |
| [[A40.l24]] | Asserção "0 LLM" do gate F2 passa a medir no boundary do SDK | P1 | — | promovida da [[A41]] · [[ADR-355]] · [[PLAN-go-shell]] |
| [[A40.l25]] | Honestidade do cone de IF: precisão de exibição + `sigma` como premissa auditada | P1 | — | residual de [[ADR-360]] §Def. 1 + [[ADR-361]] §Def. 5 · KR-E |
| [[A40.l26]] | Cobertura do solver de prazo IF (aporte 0 com retorno > 0 converge) | P2 | — | [[ADR-360]] §Def. 6-7, abertos *pelo* #1158 · co-design `financial-planner` |
| [[A40.l27]] | Órfão de dispatch: varredura de beat, `cancel` de `resuming`, read path de `failure_reason` | P1 | l19 | residual de **[[ADR-359]]** §Def. 1-3 · #1154 |
| [[A40.l28]] | Idade-meta do cone é output do modelo + rótulo `p10`/`p90` aponta para dois lados | P1 | — | [[ADR-361]] §Def. 1-2 · contrato, sem brief · KR-E |
| [[A40.l29]] | Editorial do ano de IF: dois anos concorrentes, eixo em "quando", faixa sem componente | P2 | — | [[ADR-361]] §Def. 4/6/7 + RV3-14 · **começa por brief de `product-designer`** · KR-E |
| [[A40.l30]] | Ancorabilidade do exec context: o invariante que o #1004 furou sem teste vermelho | P1 | — | causa viva pós-[[A40.l16]] · **instrumento, US$ 0** · gateia a [[A40.l8]] · co-design `prompt-engineer` |
| [[A40.l31]] | Gerador ancora em vez de digitar: correção guiada pelo mecanismo | P2 | l30 | par da l30 · **gasta** (re-eval ~US$ 26, owner-gated) · `planned` |
| [[A40.l32]] | Proveniência do executor: qual código computou este run | P1 | — | promovida da [[A42]] · [[ADR-362]] · [[ADR-363]] · instrumento, sem custo de API |

## Predicado do campo `status` de lane (decisão do dono, 2026-08-03)

Fecha a §Pendência de decisão nº 1. O predicado não é invenção desta sprint: é o
que o **consumidor** já faz e o que o **vault** já pratica, escrito.

**Quem lê `status`.** Um consumidor de máquina, um só:
[`dev/_sprint_current_renderer.py:27`](../../../dev/_sprint_current_renderer.py)
declara `LANE_STATUS_OPEN = {"ready", "open", "in_progress"}` — apenas esses três
aparecem em [`SPRINT_CURRENT.md`](../../_MOC/_generated/SPRINT_CURRENT.md), a
superfície canônica de pickup (`ready` não existe no enum do schema de lane;
`open` é o valor operante). Logo o predicado tem de ser sobre **elegibilidade de
pickup** — não sobre "alguém pegou", não sobre "a onda abriu".

**O predicado.**

- **`open`** ⇔ a lane pode ser pega **e terminada** agora: todo `depends_on` está
  terminal (`shipped`/`cancelled`) **ou** a lane declara **amarra explícita de
  entrega parcial**.
- **`blocked`** ⇔ liberada, mas retida por bloqueador declarado — com o motivo em
  blockquote no topo do arquivo. Convenção já vigente: das 8 lanes `blocked` do
  vault, [[A26.l5]] é o precedente de bloqueio por **lane irmã** e F12.2–F12.8 de
  bloqueio por **gate externo**.
- **`planned`** ⇔ escopo escrito, **não liberado**. A liberação é **por lane, sob
  demanda**, na ordem declarada em §Ondas — não por onda inteira.
- **`in_progress`** ⇔ branch/PR aberta. **`shipped`/`cancelled`** ⇔ terminal.

**Verdito aplicado** (medido no frontmatter das 29 lanes em `33bb0710`, via
`yaml.safe_load` — regex de `depends_on` erra a forma inline):

| classe | n | lanes | veredito |
|---|---|---|---|
| terminal | 5 | l1, l3, l4, l16, l24 | coerente |
| `open`, deps terminais | 1 | l2 | coerente |
| `open`, sem `depends_on` | 9 | l9, l17, l19, l21, l23, l25, l26, l28, l29 | coerente |
| `open`, dep pendente **com** amarra parcial | 1 | l27 | **coerente** pela 2ª cláusula — a amarra está escrita na lane (entrega itens 2–5, declara o item 1 não-entregue) |
| `planned`, dep pendente | 2 | l6, l10 | coerente |
| `planned`, liberação pendente | 8 | l5, l7, l8, l11, l12, l13, l14, l15 | coerente sob liberação por-lane |
| `open`, dep pendente **sem** amarra | 2 | **l18, l22** | **incoerente → `blocked`** |
| `open`, dep pendente, relação contestada | 1 | l20 | **retida** — ver abaixo |

A [[A40.l30]] e a [[A40.l31]], abertas depois desta medição, nascem conformes:
l30 `open` sem `depends_on`; l31 `planned` com dep pendente (`l30`) — coerente nos
dois eixos, e é o primeiro caso da sprint em que `planned` foi escolhido **pelo
predicado**, não por herança de nascimento.

**O que mudou de fato: duas lanes.** [[A40.l18]] (dep [[A40.l21]] `open`) e
[[A40.l22]] (dep [[A40.l20]] `open`) passam a `blocked`. Nenhuma decisão nova —
é o frontmatter passando a concordar com o que §Ondas já declara em 3 lugares. Era
**a armadilha medida**: quem fizesse pickup pela ordem óbvia de `SPRINT_CURRENT`
pegava a l18, e shipar o writer antes do reader entrega *"um run com banner
vermelho e botão de reprocessar: pior que hoje"*. Com o flip, a l21 fica a
primeira P0 pegável da Onda 3 — que é o que a sprint quer.

**A [[A40.l20]] fica `open`, agora com amarra escrita — não é mais cheque em
aberto.** A §Pendência nº 2 foi resolvida em 2026-08-05 **contra a prosa**: a
dependência da [[A40.l18]] é de **código** (mesmo hunk de `pipeline_task.py`),
não de vocabulário. `depends_on` fica; o que muda é a lane declarar entrega
parcial em 2 PRs, o que a mantém `open` pela **2ª cláusula** deste predicado
(precedente [[A40.l27]]). `parallel_with` foi **rejeitado**: declararia
paralelismo que o diff não sustenta.

**`blocked` deixa de ter zero uso nesta sprint** — eram 0 de 29 contra 8 no
resto do vault, o sinal de que o campo não codificava dependência. Prioridade
**não** muda: `blocked` diz "ainda não pegável", não "menos importante"; l18 e
l22 seguem P0.

> **Delta 2026-08-06 — o predicado tem custo de manutenção, e ele apareceu.** A
> tabela acima é medição datada em `33bb0710`; não a reescreva. O que mudou: a
> [[A40.l21]] mergeou em `c8239386` (#1232) e, com o `depends_on` da [[A40.l18]]
> satisfeito, o `blocked` dela virou **stale** — ninguém flipa o campo no merge da
> dependência, então a lane sumiu do `SPRINT_CURRENT` justamente quando ficou
> pegável. É o modo de falha simétrico ao que o predicado nasceu para matar:
> antes, `open` mentia para cima (armadilha de pickup); agora `blocked` mente para
> baixo (lane P0 invisível). Flipada para `in_progress` no pickup de 2026-08-06.
> Reforça o §"Sem gate, isto é convenção e não garantia" acima — o gate derivável
> de `depends_on` + `status` pega **os dois** sentidos, e continua não roteado.

> **Delta 2026-08-07 — os DOIS sentidos falharam no mesmo dia, e isso fecha o
> argumento do gate.** A [[A40.l18]] mergeou (`b8460274`/#1258, PR2) e ficou
> `open` por 4h; a [[A40.l22]] teve seu bloqueador satisfeito em 06/08 (o **PR1**
> da [[A40.l20]], `0301f7a0`/#1250) e ficou `blocked` por um dia. Uma mentia para
> cima, a outra para baixo — **as duas P0**, as duas invisíveis ou fantasma no
> `SPRINT_CURRENT`, e nenhuma detectada por leitura do vault: as duas só
> apareceram numa varredura que cruzou `status` do frontmatter com commits de
> `origin/main`. Corrigidas em 2026-08-07.
>
> O §Delta de 2026-08-06 já havia previsto o sentido `blocked`; a novidade é a
> **simetria**, e ela é o que converte "convenção" em dívida datada: três
> instâncias em dois dias, todas no mesmo campo, todas por flip manual que
> ninguém faz no merge. O gate derivável de `depends_on` + `status` pega os dois
> sentidos em ~10 linhas. **Continua não roteado** — candidato segue [[A40.l23]].

> **Liberação 2026-08-07 — [[A40.l5]] e [[A40.l7]] passam a `open`.** Primeira vez
> nesta sprint que a **1ª cláusula** do predicado (`planned` ⇒ liberação por-lane,
> sob demanda) é exercida como decisão explícita em vez de herança de nascimento.
> A tabela de veredito acima é medição datada em `33bb0710` e **não se reescreve**;
> o que muda é que a linha *"`planned`, liberação pendente | 8"* passa a valer 6.
>
> **Critério de escolha, para o próximo par não ser arbitrário:** as duas foram
> escolhidas por serem as **únicas donas de KR sem lane pegável** — l5 é a única
> dona da KR-A e a porta da [[A40.l6]] (KR-D); l7 é a metade não-entregue da KR-C.
> Sem elas, a A40 podia fechar pelo §Gate de saída com **2 de 5 KRs jamais
> tocados** — e KR não atingido por decisão é legítimo, por esquecimento de
> liberação não é. As outras 6 `planned` seguem represadas **de propósito**.
>
> Pendência substantiva da l5 resolvida no mesmo ato: o gate de consumo **não**
> alarga `filter.frontend` (registro completo na própria lane). Consequência que
> o PR tem de honrar: `check_view_model_contract.py` nasce **hook de pre-commit**,
> onde `any_code: '**'` o faz rodar em todo PR — se nascer sob `frontend/`, herda
> o filtro e a decisão vira falsa.

**Sem gate, isto é convenção e não garantia** — mesma família da lição registrada
na emenda da [[ADR-111]] (*afirmação de audit sem gate é dívida*). O predicado do
`open` é derivável de `depends_on` + `status`, portanto gateável em ~10 linhas; a
cláusula de amarra parcial exige campo novo no schema, que é gatilho
`information-architect`. Candidato natural a hospedar: [[A40.l23]], que já é a
lane de gate de referência de doc e já é candidata a absorver o gate de
autorreferência da §Pendência nº 12. **Não roteado nesta passada.**

## Ondas

**Onda 0 — parar a sangria** ([[A40.l16]], [[A40.l17]]) — ✅ **completa
2026-08-03** (l16 em `0f8c3b18`/#1159, l17 em `c17b2122`/#1183): a precedência
sobre a Onda 1 deixa de reter qualquer lane. Aberta 2026-08-03 pelo
incidente do run `2ded7aab`. **Precede a Onda 1 e não é negociável**, por um
motivo estrutural e não de gravidade: a Onda 1 é "medir antes de mexer", e medir
exige **run que completa**. Com 87,5% dos runs afetados sob o prompt vigente 2.2.0
e uma fração falhando, o baseline da l1 e a re-rodada de gate de toda onda posterior medem um
pipeline que não entrega — e o §Gate de saída do dogfood de [[PLAN-report-trust]],
que exige 2 re-runs completos consecutivos, **não pode nem iniciar o contador**.
A l16 é S (uma linha em `_HARD_LAYERS` + bump de versão de verificação + o
saneamento de PII do caminho de exceção que o próprio critério de aceite dela
exigia — ver [[A40.l16]] §Decisão 6) e independente. A l17 é cortável.

**Onda 1 — medir antes de mexer** ([[A40.l1]], [[A40.l3]], [[A40.l4]], [[A40.l9]]) —
✅ **completa 2026-08-03**: a l9 (a última) shipou em #1187 + #1188.
A l1 é instrumento: congela o baseline **sobre `origin/main`** antes de qualquer
mutação — lição da A39 (baseline pós-mutação mede o próprio fix). A l3 fecha três
achados com esforço S e risco baixo. A l9 sobe para cá porque é **pré-requisito de
RV3-07** e porque é reincidência de um "FIXADO" falso.

**Onda 2 — corrigir com o instrumento pronto** ([[A40.l2]], [[A40.l5]], [[A40.l7]],
[[A40.l8]], [[A40.l12]]). A l2 só abre depois da l1: sem detector, o fix fecha
verde sem prova. A l5 vem **antes** das lanes de correção individual de contrato —
senão cada uma é fixada uma vez e volta a divergir.

**[[A40.l30]] entra como instrumento que gateia esta onda** (aberta 2026-08-03,
co-design `prompt-engineer`). Não é Onda 0 — a Onda 0 é "parar a sangria" e sua
não-negociabilidade era *"medir exige run que completa"*, o que a [[A40.l16]] já
entregou. Não flutua livre como l25-l29, porque tem **consumidor datado dentro da
Onda 2**: a [[A40.l8]] projeta `context_section` no corpo orçado, que é
exatamente a mutação que passou verde em #1004 sem nenhum teste vermelho. Amarra:
**a l8 não mergeia sem o item 2 da l30** — mesmo precedente
instrumento-antes-de-mutação que esta seção já declara para l1 → l2. A
[[A40.l31]] (o fix, que gasta) fica **fora das ondas** e `planned`, atrás do
diagnóstico da l30.

**Onda 3 — degradação honesta** (na ordem reader-first que esta seção declara:
[[A40.l21]], [[A40.l18]], [[A40.l19]], [[A40.l20]], [[A40.l22]]). Fecha a classe que o
incidente expôs: contrato de criticidade de stage, `partial_failure` alcançável, e
o retido declarado na tela. É a §Frente 4 de [[PLAN-report-trust]] — leia lá a
tese, os KRs (KR-0..KR-3), o tripwire T1 e os guardrails G1/G2.

> **Estado da Onda 3 em 2026-08-06.** [[A40.l21]] ✅ `c8239386` (#1232) ·
> [[A40.l19]] ✅ `c9688111` (#1241) · [[A40.l18]] **PR1** ✅ `4620cc04` (#1242),
> **PR2 (o writer) pendente** · [[A40.l20]] e [[A40.l22]] não iniciadas.
> A l19 subiu de posição na execução por ser **pré-condição dura** do PR2 da
> l18 (`degraded` precisa existir no tipo do DB antes de qualquer `INSERT`), e o
> gate que ela trouxe usa direção-subconjunto, o que tornou a ordem
> l19 → l18 segura em todo instante. Com ela em `main`, o item 1 da [[A40.l27]]
> também destravou.

> **Estado da Onda 3 em 2026-08-07** (o snapshot acima é datado — **não o reescreva**).
> [[A40.l18]] **PR2** ✅ `b8460274` (#1258) — o writer que faltava · [[A40.l20]] ✅
> `0301f7a0` (#1250, PR1, 06/08) + `039c1b6d` (#1278, PR2, 07/08), `shipped` ·
> [[A40.l22]] `open`, **a única P0 pegável da onda**. Com o PR2 da l20 em `main`, o
> `depends_on` da l22 ficou **terminal** e o `open` dela deixou de se apoiar na 2ª
> cláusula do §Predicado.

> **Estado da Onda 3 em 2026-08-08** (os dois snapshots acima são datados —
> **não os reescreva**). [[A40.l22]] entregou a **superfície de degradação** em
> #1277, e segue `in_progress`: em 07/08 ela recebeu do PR2 da [[A40.l20]] a
> **copy por código de ausência** (4 códigos de 404 + free tier), que o #1277 não
> cobre e cuja escolha de palavra é do dono. **A Onda 3 não fecha terminal por
> esse item.** Do §Critério de aceite da l22, a perna de PDF é
> **parcial** — a ressalva do banner chega à camada de texto do PDF, a nota da
> seção não, por truncagem **pré-existente** do export (nenhum `<h2>` de seção
> chega ao PDF hoje). Não é defeito da l22 e não tem lane; o ponto de retomada
> está marcado como `test.fixme` em `print.@critical.spec.ts`. O teste com humano
> (n=1) segue owner-gated.

**Ordem interna, e nenhuma das três é estética:**

- **[[A40.l21]] antes de [[A40.l18]]** (reader-first). Os **7** read sites de
  `partial_failure` no frontend são código morto hoje — o status existe no union
  type e no `format.ts`, mas nenhum writer o emite. Corrigi-los primeiro é PR
  coeso e de risco zero. Shipar o writer primeiro entregaria um run que produziu
  relatório com banner vermelho de falha e botão de reprocessar: **pior que hoje**.
  Amarra: se o **writer** da l18 (PR2) escorregar >1 sprint, **reverta a l21** —
  é dead code pelos nossos próprios critérios. Custo e receita do revert em
  [[A40.l21]] §Amarra de reversão: o comando **já não aplica limpo** pós-#1242, e
  o PR carrega 5 correções de UX em statuses **vivos**, a re-landar em PR próprio.
- **[[A40.l20]] entrega em 2 PRs** (corrigido 2026-08-05): o PR1 (contrato do
  desfecho retido) mergeia em paralelo à [[A40.l18]] contra o vocabulário da
  [[ADR-357]] `Proposto`; o PR2 (o wire-up em `pipeline_task.py`) fica **atrás do
  merge** dela, porque medido em 2026-08-05 reescreve as mesmas linhas
  (`:1192-1193`, `:1329`, `:1180-1200`). A formulação anterior ("depende da
  decisão, não do merge") tratava a dependência como de vocabulário —
  falsificada. Amarra: o PR1 é revertido com a [[A40.l21]] se o **writer** da
  l18 (PR2) não mergear até `date_target`.
- **[[A40.l19]] em PR próprio** — migration não mistura com feature.

**Esta onda precede a Onda 4 por conflito de arquivo, não por prioridade.** A
[[A40.l22]] toca as mesmas superfícies do relatório que [[A40.l11]] e
[[A40.l13]]; pelo critério de agrupamento desta sprint ("arquivo compartilhado,
evita merge-hell"), a l22 vai primeiro e as duas rebaseiam sobre ela.

**Fora de onda — [[A40.l24]] · ✅ `9b7d330e` (#1157), 2026-08-03.** Promovida da
[[A41]] pelo critério de **consumidor datado**: o [[TRACK-f2-cutover]] declara que
nada mais avança sem o dono rodar `make go-parity`, e a asserção "0 invocação
LLM" do Tier-1 era vacuamente verde. Não é tema report-trust e não compartilhou
arquivo com nenhuma lane daqui — não deslocou escopo.

O que ficou medido: a asserção tinha sido **invertida** por #1151 —
`requires_llm_fallback` só é escrito quando a visão da Caixa **falha**, então o
gate reprovava o braço sem credencial (zero chamada) e aprovava o que fez chamada
paga; como o `_go-on-native` injeta a key só no braço Go, o veredito ficava
invertido **entre os braços**. Trocado por **impedir** em vez de detectar
(`LLM_FREE=1` apaga a credencial dos dois braços, marcador verificado na saída do
`make`), com prova de mutação nos dois sentidos. Detalhe e a correção de premissa
da lane (medir no boundary do SDK é inalcançável no harness) no §Entregue dela.

> **Pendência com o dono, não fechada pelo PR:** o critério "run com
> `skip_llm=True` sobre o corpus do dogfood ⇒ 0 chamadas ao SDK e 0 rows novas em
> `LLMCallLog`" exige a stack local e **não foi executado** — a lane subiu a
> `shipped` com a prova de mutação (unit) e sem a prova ao vivo. Registrado em
> [`OWNER-GATED-active.md`](../../_MOC/OWNER-GATED-active.md) §1; a asserção
> mordendo de verdade só se confirma no 1º `make go-parity` do dono.

**Onda 4 — o que depende das anteriores** ([[A40.l6]], [[A40.l10]], [[A40.l11]],
[[A40.l13]], [[A40.l14]], [[A40.l15]], [[A40.l23]]). A l15 entra aqui — estava na
tabela e fora das ondas desde que nasceu (spun off da l3, 2026-07-31): depende da
l3 (shipada), é P2, e toca as mesmas superfícies de relatório que l11/l13, logo
rebaseia sobre a [[A40.l22]] pela mesma regra de arquivo-compartilhado. **Mover é
decisão do dono** — coloquei onde o critério declarado da sprint a coloca, não por
preferência.

**[[A40.l26]] também fica fora das ondas** (aberta 2026-08-03): carrega o
residual determinístico que o #1158 abriu ao fechar o §Def. 5 — `_solve_prazo`
não implementa os ramos `aporte == 0, r > 0` e `r == 0, aporte > 0`, que
convergem (~35 anos no dogfood). É P2 e não P0 porque o custo é **informação
retida**, não falsa: o #1158 já trocou a sentinela por ausência. Toca
`if_projector.py`, disjunto da l25 (`if_monte_carlo.py`) — paralelas.

**[[A40.l25]] fica fora das ondas, por definição** (aberta 2026-08-03): é o
residual das §Entregas fora de lane, cujo código já está em `main` ou em PR
aberta. Não compartilha arquivo com nenhuma onda — `if_monte_carlo.py` +
superfícies de exibição de S7 — e depende só de #1162 aterrissar. Sequenciá-la
dentro de uma onda seria acoplar sem motivo. Como l24: roda em paralelo.

**[[A40.l28]] e [[A40.l29]] seguem o critério da l25** (abertas 2026-08-03):
mesmo residual, mesma dependência de #1162 aterrissar, fora das ondas pelo mesmo
motivo. São **disjuntas por camada** — a l28 é contrato (payload, schema,
catálogo, tipos) e a l29 é exibição (S7, narrador, componente) — então as três
rodam em paralelo entre si e com a l26. A l29 é a única com **passo 0 que não é
código**: sem o brief de `product-designer` ela fica parada, e foi por isso que a
l25 a empurrou para fora em vez de absorvê-la.

**[[A40.l27]] é residual pelo mesmo critério, mas NÃO flutua livre** (aberta
2026-08-03): `depends_on: [[A40.l19]]`, que está na Onda 3. O `resuming` ausente do
tipo `pipelinerunstatus` no DB entra em **predicado de query** na varredura de
órfão — é a mesma quebra-armada-no-cutover que a l19 existe para pagar. Logo:
paralela a tudo, **exceto** que o item 1 dela não pode mergear antes da l19. Amarra
declarada na lane: se a l19 escorregar, ela entrega os itens 2-5 e **declara o item
1 como não-entregue**, em vez de shipar predicado que quebra em Postgres.
Colocação e escopo são sugestão do critério declarado da sprint — ver §Pendências
de decisão nº 10.

**Precedência de corte:** nunca cortar [[A40.l16]] nem [[A40.l18]]. Cortáveis, em
ordem: [[A40.l17]], marcador em `/reports` (já fora de escopo), dead-letter (já
fora, por gatilho). **Nada sai da A40** — decisão do dono, 2026-08-03: a onda 0 e
a onda 3 entram por cima do escopo existente, sem despejar lane P2/P3 para A41.

**A ordem não segue a coluna de severidade, e isso é deliberado.** O painel
apontou que a severidade desta rodada não é insumo confiável de sequenciamento: os
7 `CONFIRMADO` são confiáveis, os **37 `PARCIAL` carregam inflação desconhecida**
(débito de método #3 da própria r3 — zero refutado em 36 clusters). A ordem aqui é
por **"alcança o usuário na configuração atual"**, e começa pelo que foi **medido**.

## Estado da Onda 1 (2026-08-03) — o que shipou e o que a Onda 0 não invalida

Três lanes da Onda 1 estão em `main`, entregues **antes** da Onda 0 existir
(ela nasceu em 2026-08-03, do incidente `2ded7aab`):

| Lane | Commit | O que ficou medido |
|---|---|---|
| [[A40.l1]] | `92a91884` (#1118) | 261 colisões cross-grupo · Σ 81.288.000 cents · baseline congelado off-git · **8 ratchets, 4 re-confirmados manualmente** (4 só com a prova do implementador — ver [[A40.l1]] §Fechamento, residual 4) |
| [[A40.l3]] | `b12aff30` (#1124) | `janela_12m` passa de 0 consumidores a leitura por seletor único; rótulo impresso (tooltip não sai no PDF) |
| [[A40.l4]] | `6c5d9814` (#1139) | precedência de 3 fontes declarada ([[ADR-356]]); 7 → 12 seções entregando parágrafo |


**A precedência da Onda 0 sobre a Onda 1 é real, e não retroage sobre o baseline
da l1.** O argumento da Onda 0 é que medir exige run que completa. Isso vale para
todo gate que dependa de **run com parecer** — inclusive o §Gate de saída do
dogfood de [[PLAN-report-trust]], que não pode iniciar o contador de 2 re-runs
consecutivos antes da [[A40.l16]]. Mas a medição da l1 é
`dev/certify_ledger_local.py`, que é **read-only, sem Celery e sem LLM**: re-deriva
E3+E4 in-process sobre o E2 persistido. O caminho que o incidente quebrou (parecer
→ `needs_review` → `success: False` → zero linha em `reports`) **não participa**
dessa medição. As 261 seguem válidas como baseline de KR-B.

O que **não** foi cumprido nas três: a re-triagem bloqueante da l4 (os 7 achados
inertes verificados contra output renderizado) **rodou 2× e bloqueou nas 2**; a
**3ª passada, pós-remediação final, não rodou** (limite de gasto) e a lane mergeou
assim por decisão do dono. O risco ficou delimitado — s4 entrega sem contagem, s8
sem DAS, s9 suprimido, `s3` desligado depois (#1144) — mas os 3 fixes finais não
foram verificados no render. Cronologia precisa em [[A40.l4]] §Fechamento;
disposição em §Pendências de decisão nº 4 (resolvida 2026-08-05: não-cumprido,
subsumido pelo gate de saída, com o checklist como insumo declarado).

## Entregas fora de lane (2026-08-03)

Trabalho que **shipou dentro da janela desta sprint sem lane própria** — nasceu de
gate/achado, não do backlog dos 33. Registrado aqui porque a §Lanes não o cobre e
sem isso a sprint fecharia dizendo menos do que entregou.

| Entrega | Commit | ADR | O que ficou medido |
|---|---|---|---|
| Determinismo do cone de IF | `35acc75e` (#1156) | **[[ADR-360]]** `Proposto` | Cone era sorteado da entropia do SO (0,7% de diferença entre runs com input idêntico). Seed passa a ser constante de modelo + guard de boundary; `n` 10k→50k (dispersão 2,4%→1,2% a 85 ms); proveniência (`mc_version`/`seed_usado`/`n_simulacoes_usado`) no artefato; schema do bloco fechado. Mediu que **subir `n` não compra reprodutibilidade** (0,2% sobra a 1 M) |
| Sentinela de não-convergência | `7107b956` (#1158) | — | `prazo_anos_realista` não projetável emitia 999, somado à idade virava `idade_meta_usada: 1040` em path citável formatado como "anos". Passa a emitir ausência com motivo. Fecha o item 5 do §Deferimento da [[ADR-360]] |
| Percentil censurado do cone | `790c1c5f` (#1162) | **[[ADR-361]]** | `Pk` do ano de IF saía da base **dos sobreviventes** (otimista, e mais otimista quanto pior o plano) enquanto `prob` usava `n` cheio. Passa a quantil na base cheia com censura declarada por percentil; corrige também o truncamento de `int(np.percentile)`. `mc_version` → `3.0` |

**O que sobra dos três** está na [[A40.l25]], [[A40.l26]], [[A40.l28]] e
[[A40.l29]] — não em §Deferimento de ADR, que é invisível ao `SPRINT_CURRENT`.
**A [[A40.l28]] fechou em 2026-08-07** (#1267/#1268/#1269, [[ADR-369]]): os itens
1 e 2 do §Deferimento da [[ADR-361]] saíram do papel. Sobram a [[A40.l25]]
(faixa de 5 pp, `sigma` por perfil), a [[A40.l26]] (`_solve_prazo`) e a
[[A40.l29]] (manchete/eixo/faixa na UI).

> **Correção de cobertura — 2026-08-03.** A l25 e a l26 cobriam 3 dos 7 itens do
> §Deferimento da [[ADR-361]]: o item 5 (faixa de 5 pp) e o residual da
> [[ADR-360]]. Os outros quatro estavam **descritos e sem destino** — exatamente
> o estado que esta seção existe para impedir. Roteados agora: **l28** leva os
> dois de contrato (idade-meta como input, rename do rótulo) e **l29** leva os
> três editoriais, que a própria l25 declarou fora de escopo por dependerem de
> brief. O item 3 (sentinela 999) tinha sido fechado pelo #1158.

### Órfão de dispatch (gate de paridade Go, não report-trust)

Gatilho distinto dos três acima: rodar `make go-parity` ([[TRACK-f2-cutover]]) com
Redis fora do ar. Registrado na mesma seção porque a natureza é idêntica — shipou
na janela da sprint, sem lane.

| Entrega | Commit | ADR | O que ficou medido |
|---|---|---|---|
| Dispatch falha alto + compensação por caller | `9d30dc2d` (#1154) | **[[ADR-359]]** `Decidido` | `make pipeline-run` com broker fora saía **exit 0** e deixava o run `pending` para sempre, trancando o workspace via `ux_pipeline_runs_ws_active` com "Cancele ou **aguarde**". O fallback em `threading.Thread(daemon=True)` **duplicava execução** (`.delay()` e a escrita de `celery_task_id` no mesmo `try`; `running` não é terminal para `_mark_run_started`). Deletado; compensa quem fez a ação forward (`trigger` marca `failed`, `resume` **reverte** restaurando `paused_at_stage`); `UPDATE` condicional + `rowcount` pareado com a guarda da [[ADR-297]]; `celery_task_id` pré-gerado **antes** do enqueue; cura no ponto de bloqueio (write no Postgres — funciona com Redis fora); 503 + `Retry-After` |
| Gate estático de primitiva non-stateless | `9d30dc2d` (#1154) | emenda **[[ADR-111]]** | `STATELESS_AUDIT` §5 afirmava "`threading.Thread` — nenhum resultado em app code" desde 2026-04-20 e a afirmação era **falsa na data em que foi escrita** (o thread existia desde 2026-04-14). Não houve drift: nada a verificava. `dev/check_stateless_primitives.py` é **AST**, não grep — grep acusa `category_cache.py:3`, cuja docstring *afirma a ausência*, e confunde o `create_task` do agregado Tarefas com `asyncio.create_task` |

**O que sobra** está na [[A40.l27]]. **Consequência para outra lane:** a [[A40.l19]]
passa a ter **dois** consumidores (a [[ADR-357]] §7 e a varredura da l27) — se ela
escorregar, os dois param.

**Lição transferível registrada na emenda da [[ADR-111]]:** afirmação de audit sem
gate é dívida, não garantia. Mesma família do §Débito de método herdado da r3, no
fim deste arquivo.

**Owner-gated destas entregas** (também em [[OWNER-GATED]]): flip da [[ADR-360]] e
da [[ADR-361]] `Proposto` → `Decidido`; **nota one-shot de recalibração** no
primeiro relatório pós-merge (seed + `n` + censura deslocam todo o bloco de IF, e
sem a nota a leitura racional de "IF em 2040" virar 2041 é "meu plano piorou");
**re-rodar o Tier-1** do gate F2 (`make go-parity WS=<dogfood> RUNS=2`) para
confirmar 0 diff residual no controle Py↔Py sem allowlist para o cone.

> **Ampliação da nota one-shot — [[A40.l28]] (2026-08-07), registrada, não
> executada.** A [[ADR-369]] deslocou o bloco de IF uma terceira vez, e desta vez
> a mudança é de **semântica**, não de calibração: a probabilidade deixou de medir
> P(o modelo bater a própria data) e passou a medir P(cumprir o prazo que a
> família declarou). Consequências para a nota especificada em [[ADR-360]] §Nota
> one-shot: (a) o gatilho tem de disparar também para `mc_version` `"3.0"` e
> `"4.0"`, não só ausente/`"2.0"`; (b) o par "ano antigo → ano novo" **não basta**
> — o número da probabilidade muda por motivo diferente do ano, e para muitos
> planos ele vai **cair** (o alvo declarado costuma ser mais curto que o
> determinístico); (c) o elemento 2 da nota ("a variação é sempre no sentido de
> corrigir para mais conservador") **não vale** para esta terceira mudança: aqui a
> probabilidade pode subir ou descer conforme a folga do plano. Sem essa ressalva,
> a nota afirmaria monotonia que a [[ADR-369]] quebra. Escrever a nota continua
> owner-gated; esta entrada existe para que ela não seja escrita com a
> especificação de duas mudanças atrás.

## Decisões do dono — A40.l18 (2026-08-06)

Três perguntas que o painel de co-design da [[A40.l18]] classificou como
não-delegáveis. **Todas respondidas na mesma sessão**, com a recomendação
aceita nos três casos. O detalhe e o mecanismo ficam na lane (§Decisões do
dono); aqui fica o registro de que foram feitas e quando, para que o §Gate de
saída não as reabra por esquecimento.

1. **Honestidade na tela em run degradado — metade negativa agora.** O PR2 da
   l18 suprime o `CleanBar` (que hoje **afirma** "sem pendências que afetem a
   leitura deste relatório", inclusive no PDF); a ressalva positiva fica com a
   [[A40.l22]]. Recusado segurar o PR2 até a l22 — ela depende do PR1 da
   [[A40.l20]] e estouraria a `date_target`, revertendo a [[A40.l21]] já em `main`.
2. **Detecção de degradação — card em `/admin/metrics` + cadência do dono.**
   Sentry fica para a próxima janela (segue OWNER-GATED). Recusado
   explicitamente "só log estruturado".
3. **Tolerância de conservação — follow-up com ADR própria**, fora do PR2. Ver
   [[A40.l18]] §Follow-ups nomeados, item 1: `patrimonio_composicao_diff_pct_max: 5`
   deixa passar R$ 150k–400k não explicados num patrimônio de R$ 3–8M, e os dois
   únicos checks de tolerância zero (CV16/CV17) estão fora do conjunto que pausa.

Estas **não** entram em [[OWNER-GATED]] pelo mesmo critério da §Pendências
abaixo: aquele registro é de gates estratégicos entre planos, e higiene de
sprint diluiria o sinal dele.

## Pendências de decisão (2026-08-03)

Doze perguntas de **higiene interna desta sprint** — **12 resolvidas** (nº 1, nº 7,
nº 9 em 2026-08-03; nº 10 em 2026-08-04 pela [[A42]]; nº 6 e nº 11 em 2026-08-05
pelo #1197; nº 2, 3, 4, 5, 8 e 12 em 2026-08-05 por decisão do dono, delegada e
aplicada nesta passada), **0 abertas**. Deliberadamente **não** entram
em [[OWNER-GATED]]: aquele registro é de gates estratégicos entre planos
(licença, flip de cutover, LGPD), e misturar higiene de sprint diluiria o sinal
dele. Cada item traz o que foi **medido** sobre `origin/main` (`a1e70223`) e
termina em pergunta — nenhuma decisão embutida.

**1. Qual é o predicado do campo `status` de lane?** — ✅ **RESOLVIDA 2026-08-03.**
Predicado escrito e aplicado em §Predicado do campo `status` de lane (2 flips:
l18 e l22 → `blocked`). O diagnóstico abaixo fica como registro do que foi medido.

O campo não deriva de regra declarada e está **anti-correlacionado** com dependência
satisfeita. Medido no frontmatter das 24 lanes:

- **Mesma onda, mesmo `depends_on`, `status` diferente** — [[A40.l2]] (`open`) e
  [[A40.l12]] (`planned`) estão as duas na Onda 2 e dependem as duas só de
  [[A40.l1]], que está `shipped`. Segundo par: [[A40.l14]] (`planned`) e
  [[A40.l23]] (`open`), as duas na Onda 4, as duas sem `depends_on`.
- **8 lanes com todas as deps satisfeitas estão `planned`** (l5, l7, l8, l11, l12,
  l13, l14, l15) enquanto **3 lanes com dep não satisfeita estão `open`** (l18
  depende de l21 `open`; l20 de l18 `open`; l22 de l20 `open`).
- O enum do schema admite `planned` · `open` · `in_progress` · `blocked` ·
  `shipped` · `cancelled`. **`blocked` não é usado por nenhuma das 24.**

`status` significa "dep satisfeita", "onda aberta", "alguém pegou", ou nada
verificável? Se houver predicado, quem o deriva e quando?

**2. A [[A40.l20]] pode abrir PR antes de a [[A40.l18]] mergear?** — ✅
**RESOLVIDA 2026-08-05: sim para o PR1, não para o PR2** — e a prosa é que estava
errada, não o frontmatter. Medido em `backend/app/tasks/pipeline_task.py`: o
desfecho retido do parecer retorna `success: False` (`_needs_review_return`), e
nesse ramo o código (a) rolla a sessão de artifact (`:1329`), (b) só chama
`_persist_planner_review_if_applicable` dentro de `if result.success`
(`:1192-1193`) e (c) grava `failed` + `failed_at_stage` (`:1180-1200`) — as três
são o diff da l18. A dependência **não** é de vocabulário; é de hunk. Logo:
`depends_on` mantido, `parallel_with` **rejeitado**, e a lane passa a declarar
entrega parcial em 2 PRs (l20 §Sequência de entrega). Efeito em cadeia: a
[[A40.l22]] continua `blocked`, mas o gatilho dela passa a ser o **PR1** da l20 —
sem isso a superfície que torna a 6ª classe do gate satisfazível ficaria atrás de
l21→l18→l20→l22 (4 merges) e a `date_target` mataria o único bloqueador de fato
do beta. O diagnóstico abaixo fica como registro do que foi medido.

A prosa afirma que sim em **3 lugares** (`_README` linha da l20 na tabela de lanes ·
`_README` §Ondas ordem interna · [[A40.l20]] blockquote de abertura, e um 4º em
[[PLAN-report-trust]]), sempre na forma "depende da *decisão*, não do *merge*". O
frontmatter da l20 declara `depends_on: ["[[A40.l18]]"]`, que é a única relação de
dependência do schema — `parallel_with` existe e é usado por 6 das 29 ([[A40.l24]] →
[[TRACK-f2-cutover]], [[A40.l25]] → [[A40.l11]], [[A40.l26]] e [[A40.l28]] →
[[A40.l25]], [[A40.l27]] → [[A40.l21]], [[A40.l29]] → [[A40.l25]]+[[A40.l28]]),
mas não expressa "depende da decisão". Qual das duas leituras
vale para quem pega a lane: a prosa ou o frontmatter?

**3. A tabela de evidência da emenda da [[ADR-304]] tem 8 linhas — o denominador 9 é
o quê?** — ✅ **RESOLVIDA 2026-08-05: o denominador 9 estava errado; não existe 9º
run.** A emenda original da [[ADR-304]] (#1142) rotulou a tabela de 8 linhas como
"9 runs consecutivos" e derivou "8/9" e "89%". O #1159 ([[A40.l16]] · Onda 0) **já
tinha reescrito** a emenda com a janela persistida completa (19 runs,
2026-07-10 → 07-31; sob o prompt 2.2.0: 8 runs, 7 afetados = 87,5%, 6 apagaram 15
itens; janela inteira: 7 runs apagando / 16 itens) e corrigido [[ADR-304]],
[[ADR-296]], [[ADR-358]], [[PLAN-report-trust]] §Frente 4 e [[A40.l16]] — a
pendência foi medida contra a versão pré-#1159. Resíduos textuais corrigidos no
#1216: [[A40.l22]] ("durar 9 runs" → 7 runs / 16 itens sem detecção) e
[[PLAN-report-trust]] §Fora de escopo ("série de 9 runs" → 19). **Não** confundir
com o ~89% de violação de citação (32/36, n=3) de [[A26.l1]] — métrica distinta e
correta. O diagnóstico abaixo fica como registro.

Medido na tabela (linhas 127-134 do arquivo da ADR): **8 linhas de dado**; **7 de 8
(87,5%)** têm `number_in_prose` > 0; **6 de 8 (75%)** tiveram item apagado (a linha
de 2026-07-31 é o run que falhou, com `—` na coluna de apagados). E **7 documentos**
afirmam "9 runs" / "8 de 9" / "89%": [[ADR-304]], [[ADR-296]], [[ADR-358]],
[[PLAN-report-trust]], este `_README`, [[A40.l16]] e [[A40.l22]]. O run do incidente
`2ded7aab` **já é** a 1ª linha da tabela. Falta uma 9ª linha que existe e não foi
tabulada, ou o denominador 9 — e os 89% derivados dele — está errado?

**4. A re-triagem bloqueante da [[A40.l4]] conta como critério cumprido?** — ✅
**RESOLVIDA 2026-08-05: não conta.** Verificação não-rodada aceita como cumprida é
exatamente a classe "gate verde medindo a camada errada" que esta sprint existe
para matar — a lane fica registrada como **critério parcialmente cumprido**, sem
reabrir status (`shipped` = PR mergeado, e mergeou). **E não nasce work-item
novo:** os alvos nomeados da 3ª passada já foram decompostos em itens adotados
(contagem de imóveis → [[A40.l6]]; DAS e PD-20 → [[A40.l12]]; rótulo da
[[ADR-306]] → [[A40.l11]], #1197), e o que sobra — "os três fixes da remediação
final se sustentam no output renderizado?" — é **subsumido pelo §Gate de saída e
encerramento**: qualquer remanescente `agora-visível-e-errado` aparece como
ocorrência das 6 classes ou como P0/P1 novo nos 2 re-runs, e as duas cláusulas
travam o gate. **Subsunção só é real com insumo declarado** — ver a linha nova em
§Gate de saída e encerramento; sem ela, "subsumido" seria esperança, não
mecanismo. O diagnóstico abaixo fica como registro.

Cronologia medida e agora escrita na lane: rodou **2×** e **bloqueou nas 2**; a 1ª
achou C29 e C32 `agora-visível-e-errado`; a 2ª achou C32 resolvido e provado por
mutação, C29 ainda errado (o DAS *recolhido* que substituiu a estimativa também era
falso) e **2 contradições novas** (`s4` com 6 imóveis contra 4 na seção; CV9 contando
7 de 7 com o render entregando 6); a **3ª passada, pós-remediação final, não rodou**
(limite de gasto). "Rodou 2×, bloqueou 2×, corrigido, 3ª passada não rodou" satisfaz
o critério de aceite, ou a lane precisa da passada final antes de fechar de fato?

**5. A [[ADR-356]] flippa para `Decidido (A40.l4)` ou fica `Proposto` com o motivo
escrito?** — ✅ **RESOLVIDA 2026-08-05: flip, com emenda datada.** Código em `main`
desde `6c5d9814` (#1139); `Proposto` com código shipado é a classe RV3-04 que esta
sprint cataloga. A emenda registra (a) que o critério de aceite da lane foi
parcialmente cumprido e que o residual é portado pelo §Gate de saída e
encerramento (§Pendência nº 4) e (b) a troca de dono do §Deferimento do `s1`,
l5 → [[A40.l6]] (fecha o "Relacionado" da §Pendência nº 6). O diagnóstico abaixo
fica como registro.

Medido: `status: Proposto` no arquivo; [[A40.l4]] (a lane que a implementa) está
`shipped` em `6c5d9814` (#1139). O CLAUDE.md §"Política operacional" diz que o PR de
implementação flippa a ADR no merge — mas o critério de aceite da lane não foi
integralmente cumprido (nº 4 acima). Flip agora, ou `Proposto` com o motivo do
não-flip registrado no próprio arquivo?

**6. Os 4 residuais que a [[A40.l4]] roteou para "lane própria" ficam na A40?** —
✅ **RESOLVIDA 2026-08-05.** Absorvida pela resolução da Pendência 11 (mesma
triagem, mesmo PR) — ver lá o destino item a item. Resultado: 3 dos 4 adotados em
lanes vivas ([[A40.l6]], [[A40.l12]] ×2); o 4º ("Base da cascata") não tinha dono
vivo nem materialidade medida e saiu da A40 por disposição explícita ([[REPORT-REVIEWS-active]]).
O diagnóstico abaixo fica como registro do que foi medido.

Medido na §Residual da lane — 14 linhas, das quais **4** têm `Dono` = "lane própria":

1. **`s3` contradiz a tabela da própria S3** — 3 categorias no parágrafo, 2 classes
   na tabela (`lane própria (gate financial-planner)`).
2. **`perfil_familia.right` publica `n_imoveis`** — a contagem que o `s4` deixou de
   afirmar; contradição cross-seção com a tabela da S4.
3. **PD-20 — a meta de TRS não é configurável** — `PassiveIncomeConfig.trs_meta_pct`
   nunca é lido pelo `RatiosCalculator`.
4. **Base da cascata** — `receita_bruta = receita_pj_anual` em vez de
   `FinanceiroPJSnapshot.receita_bruta_total_anual` ([[ADR-238]]).

Uma 5ª linha tem disposição distinta ("lane pós-re-medição do balde": reintroduzir
DAS no `s8` e `das_simples` em `despesas_impostos` depois de re-medir o balde com o
matcher de `69a2fad4`). Esses ficam na A40 — e então precisam de lane, contra as 24
atuais — ou viram disposição explícita de não-fazer na §Fora do sprint?

**Relacionado — ✅ RESOLVIDO 2026-08-05:** o `s1` publicando "residência própria
de R$ 0,00" **move** da [[A40.l5]] para a [[A40.l6]]. Critério: classe
zero-como-valor (RV3-27) é escopo declarado da l6; a regra já está decidida em
[[ADR-356]] §D7 e o arquivo é `summaries_narrator.py` (pipeline), disjunto do
entregável da l5 (codegen + gate de contrato de frontend) — o campo tem consumidor
e o zero é genuíno, logo não é leitura órfã. Manter na l5 decidiria a política de
zero-como-valor em dois lugares. Registrado em [[ADR-356]] §Emenda 2026-08-05, no
§Itens adotados da l6 e no §Escopo herdado da l5 (como ponteiro).

**7. Onde mora o tripwire de revert da [[A40.l21]], e quem é o owner?** —
✅ **RESOLVIDA 2026-08-03.** Host = §Gate de saída e encerramento (novo); gatilho =
`date_target` do frontmatter; owner = quem fizer o pickup seguinte após a data. O
diagnóstico abaixo fica como registro.

A amarra "se a [[A40.l18]] escorregar >1 sprint, reverta a [[A40.l21]]" está em **3
lugares de prosa** (`_README` §Ondas · [[A40.l21]] §Decisão · [[PLAN-report-trust]])
e em **nenhum mecanismo**: este `_README` não tem seção própria de gate de saída nem
de DoD — todas as menções a "gate de saída" fora desta seção (tabela de lanes,
§Ondas, §Estado da Onda 1) são ponteiro para [[PLAN-report-trust]] §Gate de saída do
dogfood — e o frontmatter da sprint declara `date: "2026-07-30"` sem data de fim. Sem
data de fim, "escorregar >1 sprint" não é avaliável. Qual artefato hospeda o
tripwire, com que gatilho, e sob qual owner?

**8. Vale acrescentar o path off-git ao lado de cada número medido?** — ✅
**RESOLVIDA 2026-08-05: vira convenção, com host único e escape de ponteiro.** A
regra mora em [[REPORT-REVIEWS-active]] §Convenção de rastreamento, cláusula 5 —
não nesta seção (que morre com a sprint) e não replicada nos 4 MOCs de skill
(cópia em 2 hosts ⇒ migra para ADR). Escopo do retrofit: **apenas os números
listados abaixo**, sem varredura. Aterrissados no #1216: "105/105 grupos" em
[[REPORT-REVIEWS-active]] §r3 (comando + síntese congelada) com ponteiro na
§Tese; "25m23s e US$ 1,5655" em [[PLAN-report-trust]] §Incidente de origem
(query de re-medição); "8 ratchets" em [[A40.l1]] §Fechamento residual 4 (as 8
alavancas coladas do #1118; a partição 4/8 declarada não-re-derivável). O
diagnóstico abaixo fica como registro.

Números que circulam na sprint sem caminho de re-medição para o próximo agente:

- **"261 colisões · Σ 81.288.000 cents"** (§Estado da Onda 1 e [[A40.l2]]) —
  **resolvido 2026-08-05:** o path exato do dump (mascarado) está em [[A40.l1]]
  §Fechamento; antes só havia o destino genérico `storage/<uuid>/certify/`.
- **"105/105 grupos"** (§Tese, [[A40.l1]], [[ADR-354]], [[REPORT-REVIEWS-active]],
  [[SPRINTS-active]]).
- **"25m23s e US$ 1,5655"** do run `2ded7aab` ([[A40.l16]], [[PLAN-report-trust]]).
- **"8 ratchets"** ([[A40.l1]], [[A40.l2]]) — o corpo do #1118 enumera as 8
  alavancas de mutação, mas `tests/unit/pipeline/test_cross_group_ratchet.py`
  tem **26** testes e nenhuma partição de 8: não dá para re-derivar dos nomes de
  teste quais 4 foram re-confirmados manualmente (ver [[A40.l1]] §Fechamento,
  residual 4).

Número sem path força o próximo agente a re-medir do zero ou a confiar. Anexar o
path off-git virá convenção da sprint, ou fica caso a caso?

**9. A precedência não-negociável da Onda 0 bloqueia a [[A40.l9]]?** —
✅ **RESOLVIDA 2026-08-03: não bloqueava**, por três fundamentos medidos, e a
questão morreu duas vezes. (1) `dev/golden_diff.py` é differ puro sobre
`dev/n.py` (stdlib, *"puro/stateless (ADR-111)"*) — sem Celery, sem LLM, sem
DB; não roda nada. (2) Os goldens comparados não vêm de run vivo: as fixtures
de `tests/fixtures/pipeline_golden/dogfood/` são commitadas e o snapshot do
view-model se reproduz *"sem DB"* (rebaseline via `MATHOMS_UPDATE_SNAPSHOT=1`).
(3) De todo modo a Onda 0 completou **antes** de a l9 abrir PR (l16 #1159 +
l17 #1183) — a precedência já não retinha nada. A isenção do §Estado da Onda 1
para a l1 valia para a l9 *a fortiori*: o instrumento da l1 ao menos lê DB; o
da l9 nem isso. A l9 shipou em #1187 + #1188. O diagnóstico abaixo fica como
registro.

A [[A40.l9]] é a única lane da Onda 1 que não shipou (`status: open`, sem
`depends_on`). O §Estado da Onda 1 escreveu a isenção **só para a medição da
[[A40.l1]]** — `dev/certify_ledger_local.py` é read-only, sem Celery e sem LLM. O
critério de aceite da l9 são 3 casos em
`backend/tests/test_tributario_run_scoped_inputs.py` **mais** conferência de delta
`↑` por `dev/golden_diff.py`. A l9 está isenta pelo mesmo argumento da l1, ou o
golden_diff a amarra a um run completo — e portanto à [[A40.l16]]?

**10. A [[A40.l27]] entra na A40 ou é despejada para a [[A41]]?** —
✅ **RESOLVIDA 2026-08-04 pelo §Critério de admissão da [[A42]]**, que declara
fechar esta pendência. A regra geral que faltava está escrita lá em 5 cláusulas
com precedência: destino é **quem já possui o arquivo ou a superfície** (tie-break
primário); a **A40 admite apenas por adoção** depois de 2026-08-03 — nada nasce
lane nova nela, *mesmo sendo P0*, com exceção única e nomeada de P0 que alcança o
usuário, sem dono de arquivo em lane viva, e cuja espera se mede em semanas; a
**A42 admite por camada** (ingestão, razão, contrato de store, instrumento);
**plano temático vivo tem precedência sobre sprint**; e o que não passa recebe
disposição explícita no MOC da skill. Aplicado à pergunta concreta: a l27 fica na
A40, porque `depends_on: l19` já está aqui e nenhuma outra lane viva possui o
arquivo. O diagnóstico abaixo fica como registro.

Aberta pelo critério declarado desta sprint (residual de §Entregas fora de lane +
`depends_on: l19`, que já está aqui). Contra: o gatilho é [[PLAN-go-shell]], não os
33 achados da r3. A favor: o resíduo inclui o **único estado inescapável do
sistema** (órfão em `resuming`: fora do predicado de `fin.detect_stuck_runs`,
`cancel_pipeline_run` recusa, `is_run_active` sempre `True`), e a decisão que o
expõe já está `Decidido` em `main`. A regra vigente do dono (*"nada sai da A40"*,
2026-08-03) foi escrita para escopo **existente** — vale para lane nascida depois?
Se a resposta for A41, mover é uma linha.

**Padrão que emergiu sem ser decidido:** as lanes l24 em diante entraram por
gatilho que **não é** report-trust, cada uma com justificativa própria e nenhuma
com regra comum. Vale declarar um critério de admissão para a próxima sprint, ou
seguir caso a caso?

**Colisão de id de lane, medida nesta sessão:** esta lane foi renumerada **duas
vezes** (l25 → l26 → l27) porque #1167 e #1170 alocaram os ids em paralelo enquanto
o PR estava aberto. É a mesma classe que o CLAUDE.md já documenta para ADR ("nunca
reserve ID; reserve o trabalho") — id de lane também é recurso global monotônico
cuja alocação só é real na escrita. Vale um gate, ou a taxa de colisão é aceitável?

## Decisões do painel (correções incorporadas)

**1. O mecanismo do P0 estava errado — corrigido antes de abrir a lane.**
Três especialistas, independentemente: `normalize_banco` (`_tx_identity.py:75`) já
faz lowercase + strip-accents **antes** do hash, em `_hash_v1` e `_hash_v2`. A
caixa de `banco` **não** fura o `transaction_hash` — fura a chave de grupo. Os
carriers reais são `tipo_conta` (vocabulário `extrato` vs `extratoconta`, que
`normalize_tipo_conta` só lowercaseia) e `titular` vazio. **A duplicação medida não
muda; a causa sim.** Escrita como estava, a lane shiparia um no-op e fecharia
verde. Âncora corrigida no [[REPORT-REVIEWS-active]].

**2. O fix não pode morar na fórmula do hash.** `_hash_v1` está **congelado**
([[ADR-278]] D1) e `_hash_v2` é a chave de dedup **e** de re-ancoragem de override.
Mudar os inputs de v2 órfãna override do usuário — regressão user-facing pior que a
duplicação. Daí a sequência da [[A40.l2]]: **medir → conter → corrigir a montante →
re-ancorar → quarentenar**, sem tocar `_hash_v2`.

**3. Os 7 achados "inertes" eram um evento de embarque de regressão.** Estavam
`não-acionável`, mas são inertes **porque a [[A40.l4]] os bloqueia** — e a l4 é P0
desta sprint. No instante em que fechar, sete defeitos chegam ao usuário de uma vez,
por um PR correto. Reclassificados para `procede-bloqueado · depends_on A40.l4`, com
re-triagem item-a-item como **critério de aceite bloqueante** da l4.

**4. Padrão transversal não registrado: os gates do repo medem produção, não
consumo.** Três instâncias na mesma rodada — RV3-04 (ADR entregue sem registro do
flip), RV3-03 (CV9 verde medindo geração), RV3-13 (campo sem consumidor). É o
invariante violado por trás da metade dos achados, e a razão de a [[A40.l5]]
(codegen + gate de contrato) ser a alavanca estrutural da sprint.

**5. Viés direcional agregado.** Quatro defeitos independentes empurram o relatório
na **mesma direção otimista**: principal como renda recorrente, cobertura na janela
mais lisonjeira, dupla contagem inflando receita, prazo de IF impresso como fato.
Erro aleatório se distribui; erro sistemático numa direção é assinatura de
mecanismo. **Cada PR que altera número exibido declara o sinal esperado do delta**
(`↑`/`↓`/`=`) e `dev/golden_diff.py` confere — divergência entre declarado e medido
bloqueia o merge.

**6. Prioridade invertida, corrigida.** RV3-11 (l9) era P2 abaixo de RV3-07 (P1) que
**depende dele**: o gatilho do CTA que RV3-07 quer construir depende de
`receita_pj_anual > 0`, que RV3-11 zera. Promovido a P1 e ordenado à frente.

**7. Aceitação indevida na revisão original.** Eu havia fechado RV3-31 (duas taxas
de retirada) como refutado, "aceite cumprido nas duas superfícies". O
`financial-planner` mostrou que RV3-31 e RV3-26 se contradizem na mesma tabela: uma
das superfícies lê chave inexistente e cai em **default hardcoded** — o aceite foi
verificado contra uma constante, não contra o payload. Os números coincidem **por
acidente**. RV3-31 vira `procede-fechado-em RV3-26` ([[A40.l5]]).

**8. Os "3 dados que faltam" eram 1.** O `regime` já é derivável de documento
ingerido (`FinanceiroPJSnapshot.regime_declarado` é computado e nunca consultado), e
`dependentes.count = 0` é **observação**, não ausência. Só a taxa da dívida é ask
genuíno. Tratar os três como iguais produziria um wizard perguntando o que o sistema
já sabe — queimando a única janela de atenção do dono no item de menor valor.

## Inventário de follow-up da sessão de 2026-07-30/08-03

Auditoria do próprio trabalho: tudo que a execução de [[A40.l1]], [[A40.l3]],
[[A40.l4]] e [[A40.l16]] produziu como follow-up, e **se tem destino**. A
convenção desta sprint é que um item ou tem lane, ou tem disposição escrita —
item que tem só descrição evapora no fim da sprint.

| Follow-up | Onde está | Tem destino? |
|---|---|---|
| Texto do donut e do chart mês a mês (base ex-aporte vs bruto) | [[A40.l15]] | **lane** |
| `s3` — o que a abertura da S3 afirma sobre a carteira | [[A40.l15]] | **lane** |
| Predicado de carrier 1 largo demais (par conta/poupança do mesmo banco colide) | [[A40.l2]] §Residual | **lane** |
| Assimetria `banco` vs `tipo_conta` na partição | [[A40.l2]] §Residual | **lane** |
| Re-medir o balde `das_simples` pós-`69a2fad4` e reintroduzir o DAS no `s8` | [[A40.l4]] §Residual | **item adotado** — [[A40.l12]] |
| `perfil_familia.right` publica `n_imoveis` (contradição cross-seção) | [[A40.l4]] §Residual | **item adotado** — [[A40.l6]] |
| PD-20 — meta de TRS não é configurável (`trs_meta_pct` nunca lido) | [[A40.l4]] §Residual | **item adotado** — [[A40.l12]] |
| Sufixo de changelog ([[ADR-148]]) não renderiza em seção nenhuma | [[A40.l4]] §Residual | **fora da A40** — [[PLAN-snapshot-changelog-v3]] §Residual W3 (o ponteiro para A40.l5 nunca aterrissou lá) |
| Base da cascata — `receita_bruta = receita_pj_anual` em vez de `FinanceiroPJSnapshot.receita_bruta_total_anual` | [[A40.l4]] §Residual | **fora da A40** — [[REPORT-REVIEWS-active]] (materialidade não medida) |
| ~~Regressão de contexto do gerador~~ → **ancorabilidade do exec context** (#1004) | [[A40.l30]] (instrumento) + [[A40.l31]] (fix) | **lane** |
| **Pontos cegos do `dev/check_pipeline_log_pii.py`** | *nada* | ver §Fora do sprint |
| **`banco` vazio em 20 grupos `extrato`** | *nada* | ver §Fora do sprint |
| Obrigação de rótulo da [[ADR-306]] cumprida em **5 de 8** blocos com chave `janela` (correção final, 2026-08-05: os "2 de 8" e "4 de 8" anteriores estavam errados — `orcamento_prospectivo` conta, porque tem base declarada em texto impresso pela prosa do produtor, mesmo sem vir do campo `janela`; só `equilibrio_cerbasi`, `passive_income` e `reserva_emergencia` — tooltip não conta, [[ADR-306]] §Emenda A40.l3 — não cumprem) | [[A40.l3]] §Handoff | **item adotado** — [[A40.l11]] |
| **Prosa crua de operador sai por `GET /pipeline/runs/{id}`** — `stage_logs.output_summary` serializa o dict inteiro sem allowlist; no ramo de sigilo o `reason` carrega o próprio termo §13, e o gate de acesso é só `get_current_workspace` | [[A40.l20]] §Achados (lane terminal) | **sem lane** — correção provável: allowlist de chaves no `PipelineStageLogResponse`. Aberto no fecho do PR2 (#1278) |
| **`riscos_truncados` é 4ª subtração silenciosa** (cap ≤12), fora de todo contador | [[A40.l20]] §Achados (lane terminal) | **sem lane** |
| **Job `frontend-e2e` não gateia** — opt-in pelo label `e2e` **e** fora do `All checks green`; PR com E2E vermelho mergeia (medido: #1278) | — | **sem lane** — candidata natural [[A40.l23]] (lane de gates). Aberto em 2026-08-07 |
| **Step de notificação do `frontend-e2e` dá 403** (`actions/github-script` → `issues.createComment` sem `permissions`) — roda `if: failure()`, vira o `##[error]` mais visível e **mascara a causa real** | — | **sem lane** — o mínimo correto é `pull-requests: write`; em `workflow_dispatch` precisa de guard, porque `context.issue.number` é `undefined` |

**Era a de maior consequência da lista, e agora tem lane — com o nome corrigido.**
A [[A40.l16]] mede que o enforcement ficou dormente sob o prompt 2.1.0 (9,1% em 11
runs) e saltou a 87,5% em 8 runs sob 2.2.0, com densidade de âncoras caindo de 9
para 5 e tokens monetários em prosa subindo de 0 para 3,5. A l16 remove o
**amplificador**; a causa segue viva.

**Mas não é "regressão do gerador"** — co-design `prompt-engineer`, 2026-08-03. O
diff de #1004 (`85860f79`) em `pipeline/llm/prompts/parecer_planejador.py` são **14
linhas**, e são só a regra de recovery de eviction mais o bump de versão: nenhuma
regra de ancoragem mudou, a persona não foi tocada. O que mudou foi o **input** —
`parecer_distiller.py` levou 158 linhas no mesmo commit ([[ADR-341]] D1-D4).
Medido in-process sem LLM: os tokens `R$` que o modelo **vê** no corpo dobraram
(9,0 → 18,0) e o conjunto **ancorável** ficou igual (29 folhas, cap 30). O nome
antigo convidava a reescrever persona e a não medir nada.

Roteado em **duas** lanes, com corte em **US$ 0 | US$ 26**: [[A40.l30]] é
instrumento (denominador, invariante de ancorabilidade, re-medição retroativa dos
19 runs — tudo sem geração nova) e [[A40.l31]] é o fix, que gasta e fica atrás do
diagnóstico. Lane única ficaria infechável, não por misturar medir com mudar, mas
por **depender de sessão do dono no meio**.

## Pendências de decisão — itens 11-12 (2026-08-03)

**11. Os follow-ups sem destino viram lane nesta sprint, ou disposição explícita
de não-fazer?** — ✅ **RESOLVIDA 2026-08-05.** A ancorabilidade do exec context já
tinha ido para [[A40.l30]]+[[A40.l31]] em 2026-08-03. Os **5** que restavam foram
triados pela mesma regra que a A42 já formalizou em `main` (§Critério de admissão,
`ecfa760f` #1193 · `3dbc558b` #1194): **destino é quem já possui o arquivo ou a
superfície** — nenhum nasce lane nova na A40. Resultado, item a item:

| Item | Destino | Por quê |
|---|---|---|
| DAS ausente no `s8`/`despesas_impostos` | **item adotado — [[A40.l12]]** | mesmo arquivo/risco de KPI distorcido por balde incompleto |
| `perfil_familia.right` publica `n_imoveis` desatualizado | **item adotado — [[A40.l6]]** | contradição cross-seção, mesma classe de "zero-como-valor" que a l6 já cobre |
| PD-20 — meta de TRS não configurável | **item adotado — [[A40.l12]]** | mesmo arquivo (`e5_analyzer_adapter.py`) do item 1, risco diferente — **não** agrupado na mesma tarefa (arquivo compartilhado ≠ risco compartilhado) |
| Sufixo de changelog (ADR-148) não renderiza | **fora da A40** — [[PLAN-snapshot-changelog-v3]] §Residual W3 | é resíduo daquele plano (`W3-T05` entregou o default em forma reduzida); o ponteiro "A40.l5" nunca aterrissou no §Escopo da l5 — atribuição sem mecanismo, mesma classe que a emenda da [[ADR-111]] já nomeou |
| Rótulo da [[ADR-306]] — **3** blocos sem rótulo válido (não 2, não 4 — ver correção no §Inventário acima) | **item adotado — [[A40.l11]]** | l11 já é dona de "rótulo de escopo"; deps (l3, l4) já `shipped` |

Nenhum dos 5 justificava lane nova: a cláusula de exceção da A42 (P0 que alcança o
usuário, sem dono vivo, com espera medida em semanas) não se aplica a nenhum —
todos são P1/P2/P3 de superfície. Só a "Base da cascata" (item 4 da Pendência 6,
que este item 11 absorve) não tinha dono vivo **e** não tinha materialidade
medida — saiu da A40 por disposição explícita, registrada em [[REPORT-REVIEWS-active]]
como residual pós-r3: mede o delta entre `receita_pj_anual` e
`receita_bruta_total_anual` no corpus dogfood antes de decidir lane (delta
material) ou `aceito-wontfix` (delta imaterial). "Sem dono vivo + sem
materialidade medida" é o único caso desta lista que qualifica como "esquecimento
evitado por disposição", não por adoção.

**12. Autorreferência em `depends_on`/`parallel_with` vira gate, ou fica no olho
do revisor?** — ✅ **RESOLVIDA 2026-08-05: vira gate, absorvida pela [[A40.l23]]
§Escopo adotado item 1 e entregue antecipadamente no PR #1216** — registro
canônico no arquivo da lane. A [[A40.l27]] entrou em `main` declarando
`depends_on: [[A40.l27]]` e `parallel_with: [[A40.l27]]` — find-replace de
renumeração trocou os wikilinks pelo próprio id. **Duas correções factuais ao
diagnóstico original:** (a) o mecanismo não era "`check_doc_links` pergunta se o
alvo resolve" — aquele gate **nunca vê o frontmatter** (o strip apaga antes de
extrair wikilinks), então aresta para id **inexistente** também passa nos cinco
gates — buraco maior, agora nomeado como item 1b da l23, ainda aberto; (b) o
custo real foi ~34 linhas no estilo do módulo, não ~10 (segue longe do P2 de
500). O gate cobre também `supersedes`/`superseded_by` e alias/anchor; prova de
mutação em `tests/test_doc_graph_gates.py`. Id duplicado (rabo da §Pendência 10)
**já tinha gate** em `check_doc_links` — pinado por teste no mesmo PR; a
renumeração 2× da l27 não foi falha de gate (ele disparou no rebase), é problema
de **alocação**, que o `former_ids` (l23 item 3) audita.

## Fora do sprint (disposição explícita)

- **RV3-19** (métrica do parecer fabricável) — já tem dono ativo com co-design em
  [[PLAN-pipeline-review-r2]] §Onda C; a medição da r3 mostra **10/10 valores
  conferindo** (fabricação *possível*, não *realizada*). Abrir lane paralela criaria
  duas fontes de verdade no mesmo arquivo. **Nota do `prompt-engineer`:** o bloqueio
  declarado lá (dep. catálogo KPI curado) é artefato da enforcement escolhida — com
  *drop-field* em vez de *drop-item* (padrão que o repo já adotou em [[ADR-294]]) a
  fabricabilidade fecha sem o catálogo. Isso **destrava** a fila serializada atrás
  dele; registrar no plano r2, não aqui.
- **Raízes de RV3-18** ([[ADR-246]], identidade de imóvel) e **RV3-22**
  ([[ADR-090]], string em campo numérico) — permanecem em [[PLAN-pipeline-review-r2]];
  a A40 absorve só as facetas user-facing ([[A40.l6]], [[A40.l5]]).
- **RV3-31** — refutado; sem gatilho próprio (ver §Decisões nº 7).
- **Rota alternativa ao choke-point LLM** ([[A41.l2]] E0 · [[A41.l3]] Caixa ·
  [[A41.l4]] gate de ausência de rota) — deferida na [[A41]] `candidate` por
  decisão da [[ADR-355]] §Escopo, **não** é para atacar antes do fim da A40. Só a
  [[A40.l24]] veio para cá, pelo consumidor datado. A l3 exige ADR `Proposto`
  (`senior-cto` + `prompt-engineer`) antes de dimensionar, e carrega uma
  **restrição de ordem** achada em 2026-08-03: `extract_with_llm` pula PDF
  escaneado sem entrar em `processed` **nem** em `errors` (stage reporta
  `success: True`), então deletar o call-site da Caixa antes de fechar esse gap
  troca "conta some no Tier-1" por "conta some em todo tier, sem sinal".
- **Pontos cegos do `dev/check_pipeline_log_pii.py`** — achado ao fechar a
  [[A40.l16]], e é o que explica por que o vazamento de valor monetário em log
  sobreviveu 4 semanas: (a) o escopo é só `pipeline/**`
  (`PIPELINE_DIR.rglob("*.py")`), e os três loggers `mathoms.llm.*` do parecer vivem
  em `backend/app/services/**`; (b) valida interpolação na *message* assumindo que
  `extra=` é redigido por chave — mas `"error"` e `"reason"` não casam nenhum
  substring de `SENSITIVE_FIELD_SUBSTRINGS`. O mesmo padrão `extra={"error": str(exc)}`
  pode existir em outros services, hoje sem gate. **Fora da A40 por tema** (é
  hardening de gate de log, não report-trust) e **não roteado** — precisa de dono.
  Gatilho `sre-devops`. Registrar em [[PLAN-launch-trust]] ou sprint de governança;
  a [[A41]] é a candidata natural, já que a tese dela é fechar rota alternativa ao
  choke-point de LLM.
- **`banco` vazio em 20 grupos `extrato`** — medido ao levantar o vocabulário de
  `tipo_conta` para o alias-map da [[A40.l2]]: dos 135 grupos E3 do corpus dogfood,
  20 têm `banco` vazio (chave começando por `_`). Não é questão de alias — é defeito
  de extração a montante, e é o mesmo carrier que aparece nos 30 grupos "só no
  persistido" do drift medido pela [[A40.l1]]. **Fora da A40 por camada** (E0→E2, não
  entrega do relatório): pertence a [[PLAN-data-lineage]] ou a uma rodada de
  `parse-certify`. Não roteado.
- **Sufixo de changelog ([[ADR-148]]) não renderiza em seção nenhuma** — residual da
  [[A40.l4]], fecha a Pendência 11 (2026-08-05). É defeito de [[PLAN-snapshot-changelog-v3]]
  (`W3-T05` entregou o default em forma reduzida — ids de métrica que não casam
  `section_id` de layout), não da A40. **Fora da A40 por origem** — precisa de
  entrada datada com dono e condição de retomada em
  [`_README`](../../plan/SNAPSHOT_CHANGELOG_V3/_README.md) desse plano (fora do
  escopo deste PR).
- **Base da cascata** — `receita_bruta = receita_pj_anual` em vez de
  `FinanceiroPJSnapshot.receita_bruta_total_anual` ([[ADR-238]]) — residual da
  [[A40.l4]], fecha a Pendência 11 (2026-08-05). Dono do arquivo é a [[A40.l9]]
  (`shipped`); [[PLAN-tributario-pj]] está `done`. **Fora da A40 por falta de dono
  vivo e de materialidade medida** — mudança de cálculo exigiria emenda a
  ADR-236/238 antes de qualquer código. Registrado em [[REPORT-REVIEWS-active]]
  como residual pós-r3: entra na próxima re-triagem com uma medição de entrada
  (delta entre as duas fontes no corpus dogfood); delta material ⇒ abre lane com a
  emenda; delta imaterial ⇒ `aceito-wontfix`.

## Infra de CI tocada durante a sprint (não são lanes)

Três correções de CI e uma investigação, achadas ao entregar a [[A40.l24]]. Não
têm lane porque não são escopo report-trust e não competem por capacidade — mas
ficam registradas para não virarem mudança órfã de política:

| O que | Estado | Por quê |
|---|---|---|
| `backend-tests` `timeout-minutes` 12 → 20 | ✅ `9b7d330e` (#1157) | A política declarada no job ("2× tempo observado", de maio a ~7:30) erodiu para **1,15×**: medido nos 6 PRs de 2026-08-03, 9m02s–10m21s contra teto de 12. Reprovou o #1157 duas vezes por variância de runner, com diff que não alcança o job. Teto não muda custo de Actions (cobrança é por minuto consumido). |
| Investigação "por que a suíte dobrou" (5-8min em maio → 9-10min) | ✅ `1d16f1b4` (#1160) · adendo 2026-08-03 na [[ADR-210]] | **Era volume, não regressão** — então o bump acima não mascarava nada. Medido em 56 jobs: mediana 6,33 → 7,88 → 9,81 → 9,93min (mai→ago). A suíte foi de **2192 para 3015 testes** (+37,5%, 103 arquivos novos das sprints A34-A40) com custo por teste subindo só **9,6%** (0,157 → 0,172 s). Nada a otimizar: setup do job é ~30s de ~10min, o packing dos 432 arquivos em 4 workers dá desbalanço **1,00×**, arquivo mais pesado 32s contra caminho crítico de 290s, teste mais lento 2,38s. Sharding/`pytest-split` **rejeitado** com a conta (~550 disparos/mês × ~+2min faturados ≈ **+1.100 min/mês** num orçamento a 544%), coerente com §Custo da camada 4. Fecha a §Ganhos vencida (afirmava `≈5min`, de 2026-05-14) |
| Label cosmético fora do caminho de merge | ✅ `76b32d3a` (#1161) · regra na emenda 2026-08-03 da [[ADR-320]] | `Apply size label` era action **Docker** no mesmo job que `Validate PR title`, que é required check: i/o timeout do Docker Hub em `alpine:3.15` bloqueou merge do repo inteiro. **`continue-on-error` não resolveria** — o runner builda a imagem num passo *sintetizado antes* dos passos declarados, que por isso não carrega o atributo; medido no job 91695493843: `Build …→ failure` no step 2 e `Validate PR title → skipped` no step 4. Fix real = tirar Docker do caminho (script `gh` inline). O pin por SHA cobre o código da action, não a base da imagem dela, e o hook `docker-sha-pin` não alcança Dockerfile de terceiro. |

**A erosão volta.** O teto cresce ~+1,2min/mês no ritmo atual, e teto fixo em
número absoluto sempre erode — o que mudou é que a medição agora é embutida
(`--durations=25` no passo, custo zero em minutos) e o gatilho é declarado:
**mediana > 12min** (60% do teto de 20) ⇒ ler a tabela do log antes de mexer no
número, e só bumpar se o crescimento for de volume. Sem isso, o próximo agente
repete a arqueologia que este ciclo custou (rodar a suíte local com
`--junit-xml` + baixar log de um run de maio).

**Dois resíduos desta investigação, nenhum com lane** (não são report-trust e
não competem por capacidade, mas ficariam órfãos):

| Resíduo | Estado | Por quê importa |
|---|---|---|
| Revisão `sre-devops` da mudança de política de CI **não foi feita** | ⏳ **owner-gated** — ver [[OWNER-GATED]] | O CLAUDE.md §Protocolo de delegação lista "Política CI/CD … FinOps" como **gatilho obrigatório** de `sre-devops`. O #1160 mudou política de um job que é required check e escreveu numa ADR a regra de dimensionamento (~2× da mediana), **e mergeou sem essa revisão** — a sessão rodou sob instrução de não invocar subagente sem pedido explícito. Risco baixo no diff (comentário + flag de reporte + adendo de doc; a mudança de teto foi do #1157), mas a **regra de política** entrou sem o especialista. **Mesmo caso no #1161** (2ª sessão, mesma instrução): trocou action de terceiro por script `gh` no job required e escreveu regra de política na emenda da [[ADR-320]] ("Docker action vedada em job required"), também sem `sre-devops`. Decisão do dono: passar retroativo nos dois ou aceitar |
| Mudança em `ci.yml` custa ~5 runs de CI para mergear | 📌 registrado, sem ação | `ci.yml` está em **todos** os path filters (por sanity contra regressão de filtro), então qualquer diff nele dispara a suíte completa; e o ruleset `main-protection` tem `strict_required_status_checks_policy: true`, então cada commit que entra em `main` durante a janela força re-run. Com main recebendo 6 commits em ~1h20 (multi-sessão), o #1160 pagou **5 ciclos completos** para um diff de 24 linhas + doc. Num orçamento a 544%, a lição operacional é **agrupar mudanças de `ci.yml`** num PR só, em janela de main parada — não shipar uma por vez |

## Achado novo do painel (fora dos 33)

> **Terceiro botão que mente, mesma classe, achado no co-design da [[A40.l30]]
> (2026-08-03):** `narrative_hints_global` em `config/prompts/parecer_planejador.yaml`
> é **config morta** — `ManifestData` não tem o campo e `load_manifest` não lê a
> chave; as regras chegam ao modelo pela persona e pelo `_CATALOG_INSTRUCTION`.
> Não é defeito vivo, é botão sem fio. Entra nesta mesma lane, mesmo owner.

`max_total_input_tokens` e `max_tool_iterations` no manifest do parecer são **teto
declarativo**: parseados e nunca enforçados. Qualquer raciocínio de custo/latência
apoiado neles é infundado — o único teto vivo é `max_exec_context_bytes`. Manter um
teto que não trava é pior que não ter, porque induz revisão a assumir proteção
inexistente. Severidade Médio/P2, owner `prompt-engineer` → entra na [[A40.l8]].

## Achados da construção do harness de captura (2026-07-30)

Ao instrumentar a verificação renderizada, o caminho de produção de PDF revelou
**dois defeitos independentes que quebravam o download do cliente** — ambos com
prova vermelho/verde contra o frontend real, ambos **corrigidos** na mesma passada:

1. **`token_version` não propagava** em `download_pdf.py`. `create_access_token`
   nasce na versão 0; todo usuário que já invalidou sessões está em ≥ 1, então o
   token efêmero era rejeitado com 401 e o endpoint devolvia **HTTP 500**.
2. **Header `Authorization` não passa pelo gate client-side.** O gate de
   `/reports/[id]` lê o token de `localStorage`; `render_pdf` só injetava o header,
   então a página redirecionava para `/login` e o `wait_for_function` estourava —
   **mesmo com token válido**. Confirmado isoladamente: com token válido e sem
   semear `localStorage`, `ready=false`; semeando, `ready=true`.

Regressão coberta por `backend/tests/test_pdf_auth_contract.py`, incluindo um teste
de contrato que falha se alguém renomear a chave de auth no cliente.

**Efeito colateral útil:** o harness confirmou o **RV3-04 por medição** — 31 âncoras
de navegação, 1 sem alvo (`found: false, height: 0`). O achado deixou de ser
inferência de código. A [[A40.l7]] mantém o gate; a ferramenta só observa.

## ADRs

Estado lido do campo `status:` de cada arquivo em `docs/adr/` em **2026-08-08** —
não do que a lane prometeu. A tabela cobre as ADRs que o frontmatter `adrs:` das
31 lanes referencia, mais a [[ADR-278]] (que nenhuma lane referencia: é a nota de
que ela **não** é superseded), as abertas por §Entregas fora de lane e as
emendadas por §Infra de CI tocada durante a sprint.

| ADR | Estado | Lane | Escopo |
|---|---|---|---|
| **[[ADR-354]]** | `Proposto` (aberta em #1114) · flip a `Decidido` no merge da [[A40.l2]] | [[A40.l2]] | Identidade de transação (K4) exclui atributos de proveniência do documento |
| [[ADR-337]] | `Decidido` · emenda na [[A40.l6]] | [[A40.l6]] | Critério 4 (gate de PII no view-model) não existe |
| [[ADR-351]] | `Proposto` · flip na [[A40.l12]] | [[A40.l12]] | Retorno de principal não é renda recorrente |
| [[ADR-353]] | `Proposto` · flip na [[A40.l11]] | [[A40.l11]] | Confiança do diagnóstico — **bloqueado** até o campo-portador ter consumidor |
| [[ADR-357]] | `Decidido (A40.l18)` · **emendada** 2026-08-07 — flip quitado no PR2 da [[A40.l20]] (#1278), por decisão do dono: a condição (merge do **writer**, `b8460274`/#1258) já estava cumprida e a lane `shipped` | [[A40.l18]], [[A40.l19]], [[A40.l20]], [[A40.l21]] | Criticidade de stage e degradação do run — add-on advisory não veta o entregável. **A mais carregada da sprint: 4 lanes** |
| **[[ADR-366]]** | `Decidido (A40.l20)` · **emendada** 2026-08-07 (flip no merge do PR2, #1278; a emenda registra **4** correções que a execução fez ao texto) | [[A40.l20]], [[A40.l22]] | Desfecho da geração do parecer é eixo próprio — `status` segue sendo publicação. O membro `retido` ganhou produtor no #1278; antes era inalcançável |
| [[ADR-358]] | `Proposto` | [[A40.l16]], [[A40.l30]], [[A40.l31]] | Enforcement em produção exige budget de produção — e KR no plano onde ele age. A l30 fecha os defeitos **nº 2** (gate medido num plano, aplicado em outro — `_DENSITY_FLOOR`) e **nº 3** (detector inspeciona 3 campos dos 8+) que a ADR nomeia |
| **[[ADR-341]]** | `Decidido` (A37.l1) · a [[A40.l30]] **estende**, não reabre | [[A40.l30]], [[A40.l31]] | Contrato do exec context do parecer. D1-D4 são exatamente o que #1004 mudou (cap 8192→16384, 6→10 seções, hints fora do corpo) — e o que dobrou a superfície monetária que o modelo vê sem ampliar a ancorável |
| [[ADR-296]] | `Decidido` (A26.l9) | [[A40.l30]], [[A40.l31]] | Citação determinística: LLM emite `(claim, path, rótulo)` e o pipeline renderiza o valor. É a ADR cuja densidade mediana **11** foi medida no holdout sintético — o número que **não** deve ser confundido com o `5` do dogfood |
| [[ADR-356]] | `Decidido (A40.l4)` · **emendada** 2026-08-05 (registro do flip + dono do deferimento do `s1`) | [[A40.l4]] (`shipped`) | Precedência declarada do parágrafo de seção e CV9 como medida de entrega. Flip feito com o residual da re-triagem nomeado e portado pelo §Gate de saída e encerramento |
| [[ADR-355]] | `Decidido` | [[A40.l24]] | Intenção "sem LLM" do run é propagada até o stage, não só até a lista de stages |
| **[[ADR-360]]** | `Proposto` · flip pendente no dono | — (fora de lane, #1156) · residual em [[A40.l25]] e [[A40.l26]] | Seed do cone Monte Carlo é constante de modelo versionada, não entropia do SO. Rejeita seed derivado do input por quebrar monotonicidade em patrimônio/aporte |
| **[[ADR-361]]** | `Proposto` · flip pendente no dono | — (fora de lane, #1162) · residual em [[A40.l25]], [[A40.l28]] e [[A40.l29]] | Percentil de tempo-até-o-evento só é publicável como ano se a taxa de sucesso o define — censura declarada na base cheia |
| [[ADR-359]] | `Decidido` | — (fora de lane, #1154/#1155) | Dispatch assíncrono falha alto e quem cria estado pendente compensa |
| [[ADR-304]] | `Decidido` · emendada 2026-08-03 | [[A40.l16]] | Pureza monetária da prosa do parecer; a emenda revoga a doutrina `==0` da §2 |
| [[ADR-345]] | `Roadmap` | [[A40.l23]] | Propagação do taint E2→E5 e selo de qualidade no read-path — adoção deferida; expôs a classe de reserva-de-ID invisível |
| [[ADR-306]] | `Decidido` | [[A40.l15]] | Base temporal de mensalização no E5 — janela canônica 12m + rótulo por bloco |
| [[ADR-240]] | `Decidido` | [[A40.l7]] | Card `S_PROTECAO` no relatório (pilar de proteção patrimonial) |
| [[ADR-204]] | `Decidido` · **sem** emenda — falsificado no fecho da [[A40.l20]] (#1278): a [[ADR-366]] resolveu por eixo próprio (`outcome`), e `status` ficou intocado | [[A40.l20]] | Imutabilidade do parecer pós-publicação; §D1 é quem fixa o vocabulário de `PlannerReview.status` |
| **[[ADR-359]]** | `Decidido` (#1154/#1155) | — (fora de lane) · residual em [[A40.l27]] · 2º consumidor da [[A40.l19]] | Dispatch assíncrono falha alto; quem cria estado pendente compensa. **Supersede** a cláusula de fallback da [[ADR-014]], que contradizia o corpo dela |
| [[ADR-111]] | `Decidido` · **emendada** 2026-08-03 (correção factual, não mudança de decisão) | — | Stateless rigoroso. A afirmação "0 `threading.Thread` em app code" nasceu falsa em 2026-04-20; o enforcement passa a ser par (comportamento + `dev/check_stateless_primitives.py`) |
| [[ADR-210]] | `Decidido` · **emendada** 2026-08-03 (re-baseline, não mudança de decisão) | — (§Infra de CI, #1160) | Saúde do test suite do CI. A §Ganhos afirmava `backend-tests ≈ 5min` desde 2026-05-14 e a mediana medida é **9,9min**; o adendo fixa a regra de dimensionamento do `timeout-minutes` (~2× da mediana; teto é detector de *hang*, não policial de performance) e rejeita sharding com a conta. Mesma família da emenda da [[ADR-111]]: **texto afirmando estado que não valia mais** |
| [[ADR-320]] | `Decidido` · **emendada** 2026-08-03 (limite de garantia, não mudança de decisão) | — (§Infra de CI, #1161) | Hardening de CI/CD. A decisão 2 (SHA-pin das 4 actions de terceiro, [[A34.l14]]) pina o *código* da action, **não a imagem base** que uma action Docker builda em runtime — `CodelyTV/pr-size-labeler` fazia `FROM alpine:3.15` sem digest e derrubou um required check. A emenda veda `runs.using: docker` em job required e registra por que não há gate automático (o hook da [[ADR-249]] não alcança Dockerfile de terceiro). Mesma família da [[ADR-210]]: **garantia mais estreita do que o texto sugeria** |
| [[ADR-278]] | `Decidido` · **não** superseded | — | `_hash_v1` congelado; a A40 não cria `_hash_v3` |
| **[[ADR-365]]** | `Proposto` (aberta em #1243, **no mesmo PR da implementação**) · flip a `Decidido` **deferido para o PR de fecho da [[A40.l10]]**, por decisão do dono em 2026-08-06 — condição: verificação **renderizada**. Precedente de que o flip é do dono: [[ADR-361]] §Emenda | [[A40.l10]] | Elegibilidade e proveniência da premissa de uma recomendação são **eixos ortogonais**; retido sai do ranking mas é **declarado** por classe de motivo (6ª classe do §Critério de done do [[PLAN-report-trust]]). Origem: `pontos_urgentes` não lia `gap_qualitativo`, e o item de seguro de vida disparava para 100% dos workspaces sem apólice de pessoa — inclusive titular solteiro sem dependente econômico |

## Débito de método herdado da r3

A própria rodada que originou este sprint registrou 5 furos de processo. Três já
viraram regra na skill `report-review`; dois viram trabalho aqui:

- **Conservação por grupo não detecta duplicação entre grupos** → [[A40.l1]].
- **Ninguém renderizou tela nem PDF** → toda lane de `clareza-ux` desta sprint
  exige **uma passada de verificação renderizada** (navegador ou `pdftotext`) no
  critério de aceite. Sem isso, a lane fecha sobre inferência de código.
