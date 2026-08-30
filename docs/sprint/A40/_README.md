---
id: MOC-sprint-a40
type: moc
title: "Sprint A40 — Report trust: o dado que entrou tem de chegar ao usuário"
aliases: ["A40", "Sprint A40"]
sprint_status: current
date: "2026-07-30"
date_target: "2026-09-05"
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
> reordenou duas prioridades. Correções incorporadas em [`_HISTORY`](_HISTORY.md)
> §Decisões do painel.

> **O histórico mora em [`_HISTORY`](_HISTORY.md) desde 2026-08-14.** Pendência
> resolvida, entrega feita, painel encerrado e snapshot datado saíram daqui — 479
> linhas, sem perder uma. Este arquivo passa a conter só o que **governa decisão
> de hoje**: tese, KRs, gate de saída, tabela de lanes, predicado de `status`,
> ondas, disposições de fora-do-sprint e os inventários de roteamento ainda
> consultados. Motivo medido: o `_README` foi de 195 linhas (2026-07-30) a 1692
> (2026-08-13), **8,7× em 14 dias**, e toda pergunta sobre a sprint pagava os
> ~40k tokens inteiros. **Para saber se uma lane é pegável agora, não leia este
> arquivo** — rode `python3 dev/lane_pickup.py <id>`; ele cruza o frontmatter
> com worktree e branch vivos, que é o que este texto não sabe.

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
| **KR-A · Contrato de leitura** | ~~Leituras órfãs conhecidas **5 → 0**~~ → **2 → 0** (remedido, ver nota) *e* existe gate que hard-falha quando a próxima aparece | `dev/check_view_model_contract.py` (novo) cruzando schema E5 × tipos do frontend × readers Python. Prova do gate: fixture com chave órfã ⇒ EXIT≠0 |
| **KR-B · Não-duplicação do razão** — 🔴 **NÃO ATINGIDA** (2026-08-26, ver §Declaração final) | Duplicação cross-grupo **não-explicada = 0** no corpus dogfood | **Modo entregue** de `dev/certify_ledger_local.py --entregue --run <id>` (E3 persistido daquele run). A sombra (default, E2→E3 com enforce omitido) **não pontua**. Baseline congelado pela [[A40.l1]] **antes** de qualquer fix. Anti-Goodhart: whitelist em **linha separada**; cortadas do colapso **não** entram em explicadas |
| **KR-C · Entrega visível** | Nº de seções que **renderizam** parágrafo == nº de seções com narrativa **emitida** (hoje **0 de 16**) *e* 0 âncoras de nav sem alvo | Teste de render (Vitest/RTL) sobre payload golden + assert bidirecional nav↔seções em `ReportShell.tsx`. CV9 redefinido para medir **entrega**, não geração |
| **KR-D · PII zero no entregue** | 0 violações no view-model; critério 4 da [[ADR-337]] existe e é executável | Gate de PII sobre o view-model. Fixture sintética com identificador de terceiro + matrícula + endereço ⇒ bloqueio no CI |
| **KR-E · Honestidade da recomendação** | 0 recomendações no topo do plano cuja premissa o próprio payload contesta, sem pendência pareada | Predicado determinístico `premissa → campo E5` em teste sobre payload golden |

> ⚠️ **O denominador da KR-A era falso — remedido em 2026-08-08 (#1336).** Dos 4
> achados que a [[A40.l5]] listava, **dois não existiam** no momento da medição:
> RV3-26 já estava corrigido e RV3-17 não é leitura órfã (`total_pontuais` é
> lido de propósito, D6; o órfão é o inverso e pertence à [[A40.l15]]). Restavam
> **2**, ambas fechadas no #1336. **A KR-A não fecha com isso**: falta o gate,
> que é o outro termo do "e" — e o gate especificado depende de tipar o schema
> E5 primeiro (ver §Estado da Onda 2).
>
> **Atualização 2026-08-17:** o gate **passou a existir** (a l5 shipou), mas com
> **cobertura menor que a especificada** — 2 das 5 fixtures do §Critério de
> aceite da [[A40.l5]] não têm artefato. **A conclusão acima segue valendo pelo
> mesmo motivo, com fato novo.** Detalhe e pendência do dono: §Estado da Onda 2
> em 2026-08-17. Registrado aqui porque fechar a sprint
> citando "5 → 0" contaria dois itens inexistentes.

> ✅ **KR-D fecha (2026-08-24, #1673).** Fixture cartorial sintética ⇒ EXIT≠0 em
> `Pipeline tests (tests/)`, que está em `all-green.needs` — o termo literal da KR.
> Três gates independentes cobrem a classe, cada um com prova por mutação. O painel
> "não fecha" de 2026-08-24 e sua resolução foram para
> [`_HISTORY`](_HISTORY.md#kr-d-de-não-fecha-a-fecha-2026-08-24) — a medição estava
> certa **pelo motivo errado**, e isso vale registro. Detalhe em [[A40.l6]] §Fecho.

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

> ### ⚠️ Contador em 0/2 — a rodada unificada `U2` (2026-08-29) abriu 6 P0 novos
>
> O §Gate de saída exige **2 re-runs completos consecutivos** com *"nenhum P0/P1 novo aberto
> nesses 2 re-runs"*. A `U2` ([[REPORT-REVIEWS-active]] §r6 · [[PIPELINE-REVIEWS-active]] §r10 ·
> [[LEDGER-CERTIFY-active]] §r6, merge `47970706`) **foi** um re-run completo E0→E6 + parecer +
> revisão, e abriu **6 P0**. O `U1` (2026-08-26) também abriu P0. **O contador está em 0, não
> em 1 nem em 2** — registrado aqui porque a leitura de "gate de saída" sem esta linha sugere
> proximidade que não existe.
>
> **Quatro dos seis entram na cláusula de reinício abaixo (cinco desde 2026-08-30), pelo argumento mecânico
> da [[A40.l2]]** — não por gravidade, e sim porque **mutam E3/E5 a montante de todo
> run**: [[A40.l94]] (folga mensal · E5), [[A40.l95]] (numerador da concentração ·
> E5), [[A42.l15]] (identidade de investimento · E3/E1.5c — **não** canonicalização:
> essa rota foi vetada por medição em 2026-08-29, ver a lane) e, **desde
> 2026-08-29**, [[A40.l96]] (titularidade das posições · E4/E5 — ver o parágrafo
> seguinte). É a mesma extensão que a l34 e a l35 receberam em 2026-08-11. **O
> contador de 2 re-runs só inicia depois de as quatro estarem terminais.**
>
> **Extensão 2026-08-30 — são CINCO.** A [[A40.l98]] muta `total_pontuais`/
> `total_pontuais_janela` no E5 (base do gasto pontual, [[ADR-425]]) e **não estava
> nomeada aqui** — o mesmo modo de falha que a nota de 2026-08-11 corrigiu para a
> [[A40.l96]]: lane que muta E5 e é invisível à cláusula faz o contador iniciar cedo e
> um re-run inteiro ser desperdiçado. A [[A40.l102]] (superfície + dedup) **não** entra:
> o split de 2026-08-30 cortou exatamente por esse eixo, e ela não muta E5.
>
> A [[A40.l94]] já é terminal (`shipped`, #1828), então a extensão não adia nada que já
> estivesse pronto — nomeia o que faltava.
>
> ~~[[A40.l96]] fica **fora** da cláusula até a medição discriminante dizer de que lado está o
> defeito: se o erro for de render, não muta E5.~~ **Medição feita 2026-08-29
> ([[A40.l96]] §Medição): não é de render.** O defeito está no consolidator E4
> (`membro` por posição) e propaga para E4 **e** E5 — `investimentos_titular`,
> `investimentos_nao_atribuidos`, `atribuicao_investimentos`, a supressão da
> reserva e o parecer inteiro. **A l96 ENTRA na cláusula**, ao lado da
> [[A40.l94]], da [[A40.l95]] e da [[A42.l15]] — são **quatro**, não três.

**Cláusula de reinício do contador — [[A40.l2]] (2026-08-06).** O flip do enforce de
colapso cross-documento muta o E3 **a montante de todo run E0→E6**, logo **zera** o contador
de 2 re-runs consecutivos — pelo mesmo argumento que recusou fundir a [[A42]] na A40. Por
isso: **o contador de 2 re-runs só inicia depois que a [[A40.l2]] estiver terminal** — flip
mergeado, ou flip declarado não-entregue. Sem esta cláusula, se o flip mergear com o contador
em 1/2, alguém decide na hora se recomeça; é a pior decisão possível, tomada sob pressão de
`date_target`.

> **✅ Condição satisfeita em 2026-08-11 — #1368.** A [[A40.l2]] está `shipped` e o flip foi
> **executado**, não só mergeado: run sombra `7acf0e47` → flag ligada (preflight passou,
> `reprovadas=[]`) → run enforce `bce49a91`, com **453 rows cortadas**. O E3 mudou (6256 →
> 5803 txs) e o E5 registrou o efeito (receita R$ 3.453.166,51 → R$ 2.802.646,11, **−18,8%**,
> contra os +19% que a KR-B estimava). **O contador de 2 re-runs consecutivos pode iniciar.**

> ### ⚠️ Estendida em 2026-08-11 — a [[A40.l34]] e a [[A40.l35]] entram na mesma cláusula
>
> Pelo argumento **mecânico** da l2, não por gravidade: as duas mutam o **E5**, a
> montante de todo run E0→E6. A l34 muda a base do limite PGBL publicado (sinal
> `↓`); a l35 liga cinco insumos hoje zerados no bundle de proteção.
>
> **O contador de 2 re-runs só inicia depois que a l2, a l34 e a l35 estiverem
> terminais** — entregues, ou declaradas não-entregues. Iniciar antes mede um
> relatório que a sprint ainda vai mudar.

> **Correção de co-design em 2026-08-13 — a condição terminal não mudou.** A
> l35 foi decomposta em [[A40.l61]] fail-closed → [[A40.l62]] fontes/snapshot →
> l35 ativação. As pré-lanes são dependências transitivas, mas **l35 continua
> sendo o terminal exigido**; l61 não liga a S9 nem altera o relatório entregue.
>
> Ressalva que a cláusula não previa: os dois runs usaram `SKIP_LLM=1`, então **o parecer não
> rodou** (`review_finances_holistic: skipped`; as narrativas **rodaram**). O relatório
> pós-colapso não serve parecer velho — o resolver é run-scoped ([[A40.l9]]), logo devolve
> **ausência**. **O primeiro dos 2 re-runs tem de ser com LLM**, senão o contador conta sobre
> relatório sem E6. Custo sob o hard-stop da [[ADR-173]].
>
> **A KR-B não é declarada por este flip.** Re-medida em 2026-08-11, a métrica literal (numerador
> cross-grupo do `certify_ledger_local`) **segue 261**: o instrumento re-deriva o E3 a partir do
> E2 em sombra e é cego ao enforce por construção. O que mudou é o E3 persistido e o E5. Item
> com dono no §Residual da [[A40.l2]].
>
> **Emenda 2026-08-17 — a régua ganhou modo entregue.** `--entregue --run <id>` lê o E3
> persistido daquele run, categoriza sem reconcile e pontua a KR só nessa linha
> (`[numerador KR-B · E3 persistido run <id>]`). A sombra permanece o default e passou a
> se chamar `[sombra · enforce omitido]`. Fechar a KR ainda exige entregue=0 **e** sombra>0
> no mesmo corpus (anti-vacuidade).
>
> **Medição 2026-08-17** no run `7b64b6c7` (r6, `cortadas=47`, `retido_por_override=0`,
> cobertura fecha nos dois modos): sombra **317** · entregue **7** (todas carrier-shaped).
> Anti-vacuidade ok (sombra>0). KR-B **não atingida**. Não se troca a métrica; triagem
> das 7 fica para quem retomar. O baseline 261 da l1 era o cru de 2026-07-30 — o
> numerador sombra andou com o corpus.

> ### 🔴 Declaração final — 2026-08-26, rodada unificada **U1** ([[ADR-416]])
>
> **KR-B: NÃO ATINGIDA. O número tem piso, e o piso agora tem procedência.**
>
> Medição no run `c97b97c2` ([[LEDGER-CERTIFY-active]] §r5), sombra e entregue no mesmo
> processo, `cobertura=OK` nos dois: **sombra 317 · entregue 7**. Anti-vacuidade satisfeita
> (sombra > 0). O critério exige `entregue = 0`.
>
> **O que a U1 acrescenta às medições anteriores é a causa, não o número.** As 7 já haviam
> sido contadas em 2026-08-17 e a triagem ficou "para quem retomar". O `LC5-01` fez a triagem
> e ela não é sobre as ocorrências — é sobre o **remediador**: colapsador e detector derivam
> `direction` de funções distintas. O detector usa o balde E4
> (`dev/ledger_cross_group.py`); o colapsador passa `tipo=None` a `derive_direction`
> (`pipeline/domain/services/cross_document_collapser.py`), contra o contrato escrito em
> `pipeline/domain/services/_tx_identity.py` (*"não derivar do sinal cru: fatura inverte"*).
> O bloco de paridade do próprio harness imprime o veredito: **`só no detector 7 ⚠️ PONTO
> CEGO`**. As 7 do numerador **são** exatamente esse conjunto.
>
> **Atribuição fechada em 2026-08-26** ([[LEDGER-CERTIFY-active]] §r5): a divergência de
> `direction` é **7/7** nas ocorrências do numerador e **1.591 de 4.296 rows (37,0%)** no
> corpus transacional do run. O piso não é um acidente de sete linhas — é um mis-chaveamento
> sistemático de mais de um terço das rows.
>
> **Consequência dura: rodar o colapsador até convergir não move o número.** O residual não
> está bloqueado por falta de entrada de whitelist; está bloqueado porque o único mecanismo de
> remediação da camada não enxerga a classe. O alvo do fix deixa de ser whitelist e passa a
> ser **paridade de chave** — e isso muta E3.
>
> **Por que as 7 NÃO são classificadas como explicadas.** A opção foi considerada e é
> inexecutável, por duas razões independentes:
>
> 1. **O anti-Goodhart escrito acima proíbe.** Contar ocorrência como explicada por ter sido
>    *medida* é o movimento que este mesmo §Estado veta desde 2026-08-11. Nomear o mecanismo
>    é medir melhor, não corrigir.
> 2. **O harness rejeita mecanicamente.** As 7 são `carrier-shaped`, e
>    `dev/ledger_cross_group.py:268` torna o carrier *"INALCANÇÁVEL pela whitelist por
>    construção — erro, não warning"*: a entrada levanta `ValueError`. Não existe redação de
>    whitelist que feche esta KR sem o fix.
>
> **Roteamento do fix: [[A42]], não A40.** Corrigir a paridade muta E3, a montante de todo run
> E0→E6, logo **zeraria o contador de 2 re-runs** — exatamente o argumento que recusou fundir
> as duas sprints. O achado está carimbado no rito de abertura da A42 (§`ledger-certify` r5),
> onde estreita o escopo da [[A42.l5]] e falsifica a atribuição de fecho da [[A42.l10]].
>
> **Efeito no encerramento da A40:** a sprint pode fechar **sem** a KR-B, com ela declarada
> não atingida e o fix roteado. O que **não** é aceitável é fechá-la relatando a KR-B como
> atingida, ou silenciando o piso. O contador de 2 re-runs segue governado pelas outras
> cláusulas — a KR-B deixa de ser condição de parada e vira dívida com endereço.

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

**Data-alvo: `2026-09-05`** — ~~`2026-08-17`~~, movida em 2026-08-26 no commit que
abriu as quatro lanes da rodada unificada **U1** (ver §Fora do sprint). Manter data
vencida enquanto se abre lane nova esvazia o único gatilho computável do tripwire da
[[A40.l21]]. (`date_target` no frontmatter; precedente de campo é
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

> ### Estado do contador em 2026-08-24 — **0 de 2**, e não por atraso
>
> As três condições terminais da cláusula de reinício estão satisfeitas ([[A40.l2]],
> [[A40.l34]], [[A40.l35]] em `shipped`), então o contador **podia** iniciar desde
> 2026-08-11. Ele não iniciou porque o critério tem um segundo termo — *"nenhum P0/P1
> novo aberto nesses 2 re-runs"* — e o r7 (2026-08-18, triagem datada 2026-08-21)
> abriu **DE-7**, **DE-8**, **DE-9**, **DE-10**, **CTO-7** e **CTO-8**. Três são P0.
>
> **Consequência operacional — o r8 não é o próximo passo.** `DE-1` e `DE-2` estão em
> `remediado — fecha por medição no r8`, logo o r8 é **necessário**; mas disparado com
> o **DE-10** vivo ele remede o mesmo P0 (cônjuge valendo `110.130,67` num resolver e
> `0,00` no outro, no mesmo payload) e o contador continua em 0. Ordem: fechar o
> DE-10 ([[A40.l77]]), depois disparar. Re-run é instrumento de **prova**, não de
> diagnóstico — rodá-lo antes de remediar custa igual e não move o gate.
>
> Registrado aqui porque a nota de 2026-08-11 acima termina em *"o contador de 2
> re-runs consecutivos pode iniciar"* e, lida sozinha, sugere que ele iniciou.

> **A condição foi satisfeita — e o r8 virou pré-requisito, não sucessor
> (2026-08-24).** O DE-10 fechou ([[A40.l77]] `shipped`, [[ADR-410]] `Decidido`).
> A ordem acima autoriza disparar, e medindo o corpus a coisa fica mais dura que
> "autorizado": **o artefato E5 mais recente é de 2026-08-18**, e o #1550, o #1578
> e os 4 PRs da l77 mergearam em 19/08 e 24/08. Ou seja, **nenhum artefato do
> corpus foi produzido por código pós-fix** — todo E5 armazenado mede um eixo que
> não existe mais.
>
> Consequência para o §Inventário abaixo: o **DE-7** não tem substrato para ser
> medido. Seu número (`nao_atribuidos` = 61% da soma dos baldes) não se verifica
> contra o run `33514dc4`, que publica `nao_atribuidos: 0,00` e
> `cobertura_investimentos: []` — porque é anterior ao #1550, e a chave vazia
> (`total_por_membro = {"": 642.744,79, "david_…": 300.444,46}`, **68,1%**) ainda
> era absorvida pelo titular. Recomputar com o código de hoje produziria projeção,
> não medição ([[A40.l77]] §Ataque A0 pegou a mesma confusão).
>
> **Portanto o r8 precede o DE-7**, e não o contrário: ele é a única forma de
> obter um número medível para o achado. Vale para o DE-8 pelo mesmo motivo.
## Lanes (101 no disco · 101 nesta tabela — ver nota ao fim)

Critério de agrupamento: **arquivo compartilhado** (evita merge-hell entre
branches `agent/*` paralelas) **e** risco compartilhado.

**Convenção da coluna Título:** é **rótulo curto**, não o título canônico — este
é o `title` do frontmatter da lane. Medido em 2026-08-05: 1 das 31 coincide
literalmente. Divergência de redação aqui **não** é defeito; divergência de
`priority` ou de `depends_on` é.

> **O limite dessa licença, medido em 2026-08-12 (#1423):** rótulo curto é
> *abreviação* do título da lane, não *outro assunto*. A linha da [[A40.l33]] dizia
> "Cache de citação por conteúdo, não por posição" — tema de lane nenhuma — enquanto
> o arquivo dela é contraste de texto sobre tint. Foi escrita de memória (#1372) com
> o arquivo já em disco, e sobreviveu a 4 passadas de sincronia porque todas
> contaram **linhas** em vez de cruzar com o `title` da fonte. Quando esta tabela e
> o frontmatter divergirem em *assunto*, a fonte é o frontmatter. Cruzamento:
>
> ```
> python3 - <<'EOF'
> import re, pathlib
> rows = {}
> for lid, label in re.findall(r"^\| \[\[A40\.(l\d+)\]\] \| ([^|]+?) \|",
>                              pathlib.Path("docs/sprint/A40/_README.md").read_text(), re.M):
>     rows.setdefault(lid, label)   # 1ª ocorrência = esta tabela; a 2ª é a da §Onda 1
> for f in sorted(pathlib.Path("docs/sprint/A40/lanes").glob("*.md")):
>     fm = f.read_text().split("---")[1]
>     lid = re.search(r"^id: A40\.(l\d+)", fm, re.M).group(1)
>     title = re.search(r'^title: "?(.+?)"?$', fm, re.M).group(1)
>     if lid in rows and title[:25].lower() not in rows[lid].lower():
>         print(f"{lid}: tabela={rows[lid][:45]!r} vs fonte={title[:45]!r}")
> EOF
> ```
>
> O `setdefault` importa: sem ele os ids da §Onda 1 (l1, l3, l4) rendem 3 falsos
> positivos fixos, e lista que grita lobo é lista que alguém desliga. O corte em 25
> chars é heurística e ainda lista ~13 abreviações legítimas junto com o defeito
> real: serve para **triagem humana** — cada linha é uma pergunta ("isto é
> abreviação ou outro assunto?"), nunca um veredito. Quando a [[A40.l59]] entregar o
> gate de `ship_pr`, este cruzamento é candidato natural a entrar junto.

| Lane | Título | Prio | depends_on | Achados |
|---|---|---|---|---|
| [[A40.l1]] | Instrumento: detector de duplicação cross-grupo + baseline congelado | P0 | — | débito de método r3 #4 (habilita l2) |
| [[A40.l2]] | Identidade de lançamento cross-documento (`tipo_conta` + `titular`) | **P0 Crítico** | l1 | RV3-01, RV3-30 · **[[ADR-354]]** |
| [[A40.l3]] | Janela canônica: todo número rotulado 12m lê `janela_12m` | P0 | — | RV3-02, RV3-16, RV3-17 |
| [[A40.l4]] | Entrega de narrativas de seção + re-triagem do que passa a aparecer | P0 | — | RV3-03, **RV3-33 (7 inertes)** |
| [[A40.l5]] | Codegen do view-model + gate de contrato (mata a classe) | P1 | — | RV3-09, RV3-26, RV3-12, RV3-22 |
| [[A40.l6]] | Cards de imóvel e dívida: PII cartorial + contrato + zero-como-valor | P0 | l5 | `shipped` #1673 (2026-08-24) · o gate de PII passa a chavear no VALOR, não no nome do campo; `endereco_display` só publica canonical que passa nele; redação também na LEITURA; verificação renderizada em DOM + PDF · [[ADR-337]] §Emenda 2026-08-24 · 2 itens fora de escopo declarados no §Fecho (RV3-27 origem ⇒ [[ADR-385]]; `descricao_sample` no console) |
| [[A40.l7]] | Navegação e ponteiros: âncora sem alvo, seção que colapsa, mapa incoerente | P1 | — | RV3-04, RV3-05, RV3-15, RV3-28 |
| [[A40.l8]] | Cobertura do manifest do parecer (dado renderizado inalcançável) | P1 | — | RV3-08 |
| [[A40.l9]] | Materialização de config run-scoped (input zerado silenciosamente) | **P1** | — | RV3-11 |
| [[A40.l10]] | Ordem do plano + pendências do dono | P1 | l9 | RV3-07, RV3-10, **RV4-02** (P0, admitido 2026-08-04) |
| [[A40.l11]] | Cobertura e incerteza na tela | P2 | l3, l4, l35 | RV3-13, RV3-14, RV3-29 · flip [[ADR-353]] |
| [[A40.l12]] | Classificação incompleta distorce KPI | P1 | l1 | RV3-20, RV3-21 · flip [[ADR-351]] |
| [[A40.l13]] | Copy e design system | P2 | l4 | RV3-23, RV3-24, RV3-25 |
| [[A40.l14]] | Limpeza de órfãos e schema morto | P3 | — | RV3-32 + handoff A39 |
| [[A40.l15]] | Consumo Consciente: KPI de pontuais na base da janela (+3 co-changes E5) + base do texto do donut e do chart mês a mês | P2 | ❌ **cancelada** | spun off da l3 (mudança de domínio; exige rebaseline de snapshot) · **CANCELADA 2026-08-30 por absorção** — 3 das 4 premissas morreram (`teto_sugerido` extinto, co-change 2 entregue sob outro denominador e outro nome, co-change 3 shipado no #1828); o que resta é da [[A40.l98]] (base/ritmo) e da [[A40.l102]] (cards de S2) · ⚠️ a obrigação de **remover o `CARDS_DA_L15`** das duas guardas foi transferida à [[A40.l102]] — esquecê-la deixa a guarda cega para sempre, e o assert de não-vácuo fica verde depois |
| [[A40.l16]] | Desescalar `number_in_prose`: defeito de forma para de apagar conselho e de derrubar o run | **P0** | — | incidente `2ded7aab` · emenda **[[ADR-304]]** + **[[ADR-358]]** |
| [[A40.l17]] | Custo e cache no caminho `needs_review` do parecer | P1 | — | incidente `2ded7aab` |
| [[A40.l18]] | Criticidade de stage: add-on advisory não veta o entregável | **P0** | l21 | incidente `2ded7aab` · **[[ADR-357]]** |
| [[A40.l19]] | Migration do drift de enum de status (4 valores) | P1 + gate de deploy | — | **[[ADR-357]]** §7 |
| [[A40.l20]] | `PlannerReview` representa gerado-e-retido (destrava a UI) | **P0** | l18 ✅ | **[[ADR-366]]** `Decidido` — eixo próprio, **sem** emenda na [[ADR-204]] |
| [[A40.l21]] | Leitores tolerantes a `partial_failure` (reader-first) | **P0** | — | **[[ADR-357]]** §Consequências |
| [[A40.l22]] | Superfície de degradação no relatório + PDF | **P0** | l20 | `shipped` (#1301 · `cc957413`) · superfície #1277 · PDF #1287 · chrome #1289 · teste humano n=1 owner-gated |
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
| [[A40.l33]] | Contraste de texto sobre tint da própria cor: fecha a classe e gateia por medição | P1 | — | ✅ **shipped 2026-08-13** em **5 PRs** (#1320 · #1323 · #1432 · **#1434** · **#1436**) · [[ADR-372]] · **ataque 2026-08-13 (#1432)**: a classe não estava fechada — o gate media 1 das 3 sintaxes de tint e 7 call-sites reprovavam AA (1,86:1 entre eles, o mesmo número que a ADR publicou como sendo o defeito); emenda na ADR + §Aberto com 3 achados adjacentes medidos · §Deferido tem 3 itens datados; o nº 3 (`report_palette` espelha o mockup ou o uso? [[ADR-117]] na mesa) é o que a [[A40.l46]] item 2 executa · **prioridade corrigida em 2026-08-13**: a tabela dizia P2 e o frontmatter (fonte do `SPRINT_CURRENT`) diz P1 — era a única divergência das 33 linhas · **título corrigido em 2026-08-12 (#1423)**: a linha dizia "Cache de citação por conteúdo, não por posição", assunto de nenhuma lane — foi escrita de memória no #1372 quando o arquivo `A40-l33-contraste-texto-sobre-tint.md` já existia · **fecho 2026-08-27** (#1754): 5 critérios re-exercitados por mutação (3 call-sites revertidos nomeiam ratio/tema/par; os 2 eixos de staleness do `NAMED_PAIRS` falham fechado) e **4 números da lane não reproduziram** — 6→7 pares `-on-tint`, 27→37 pares medidos, 24→27 órfãos de `report_palette`, e o `4,18:1` do §Deferido 1 (que **invertia** o gatilho de retomada) → **4,584:1**, medido por duas implementações independentes e idêntico no blob do #1323, logo nunca reproduziu |
| [[A40.l34]] | Base do limite PGBL: duas seções publicam 12% sobre bases incompatíveis | **P0** | — | `shipped` (#1448 · `6c68723a`) · Card B é dono único do limite; S7 virou nota e S8 reteve base/estado sem duplicar 12% · [[ADR-375]] `Decidido` · resíduos roteados para [[A40.l56]] (✅ shipped #1483), [[A40.l37]] e [[A40.l57]] · exceção da cláusula 2 (ver §Fora do sprint) |
| [[A40.l35]] | Bundle de proteção sobre insumos reais (ativação final da S9) | P1 | l62 | `shipped` (#1476 · `549695b1`) · S9 lê o snapshot · ITCMD/EUA `missing_data` sem cenário · [[A40.l11]] é consumidora |
| [[A40.l36]] | Double-count potencial na base da cascata da S8 (pró-labore 2×) | P1 | — | ✅ **shipped 2026-08-18** (#1491 · `a04fb00f`) · achado do co-design da [[A40.l34]] 2026-08-11 · **medido em 2026-08-17**: base +82,8% (318k vs 174k), teto PGBL 38.160 vs 20.880 · **o registro ficou 9 dias atrás do código** — a lane seguia `open` sem `ship_pr`, no `SPRINT_CURRENT` como trabalho disponível, e o flip estava roteado pela [[A40.l65]] §Ataque item 5 sem nunca ser executado; é o ponto cego declarado do `check_lane_transition` (`C1` só alcança lane que **declara** `ship_pr`) · **fecho 2026-08-27**: mutação sobre `_compute_layers` prova que o teste morde (12 passed → 8 failed) · o fecho achou que a **[FAQ canônica](../../reference/FAQ_cascata_fiscal_pj.md) ainda publicava a fórmula do double-count** em bloco cercado e no presente — a página que o usuário lê para conferir o número, sem lane viva que a nomeasse — e que a [[ADR-236]] mantinha o nome/composição revogados em **3 seções vigentes** (§D2, §D3, §D5), corrigidos por §Emenda 2026-08-27 · 2 abertos com dono, ambos de **gate ausente**: a junção real das duas fontes (`_assemble_input`) aceita o double-count de volta sem nada ficar vermelho (medido: 38 passed sob mutação), e o copy do card não tem teste |
| [[A40.l37]] | A tabela de IR tem três fontes, e uma é hardcoded contra a [[ADR-135]] | P2 | l34 | achado do co-design da [[A40.l34]] 2026-08-11 · `open`, desbloqueada pelo #1448 (resolver comum em `main`) |
| [[A40.l38]] | Caixa canônico: denylist de instituição suprime R$ 89k do bruto e a conservação não vê | **P0** | — | `shipped` (#1391) · [[ADR-376]] · linha adicionada em 2026-08-12 (#1415) — o PR de origem não atualizou a tabela |
| [[A40.l39]] | Posição por instituição: o header "31/12" mente para 10 de 16 linhas — separar visão corrente da fiscal | P1 | l38 | `open` (era `in_progress` sem branch remota) · aberta pelo #1381 · [[ADR-382]] `Proposto` (#1401) · PR-a mergeado #1399 · bloqueadores do PR-b resolvidos #1424 · linha adicionada em 2026-08-12 (#1415) · **PR-b não começou** · §Aberto de 2026-08-27 (#1754): a lane recebeu **3 itens roteados e nunca registrados** — o **P0 do rodapé de PTAX** da [[A40.l50]] (roteado 2026-08-14, com o veto a *converter tudo pela PTAX de 31/12*: a linha de extrato tem data errada **e** taxa errada) e 2 da [[A40.l63]], que está **`shipped`** e não executa mais · os 3 campos do #1399 estão **inertes** (`row.id` 0 usos; `data_referencia` só em declaração de tipo; `posicao_31_12` ausente do `e5_analysis.schema.json`) e o `id` não vira natural key porque `_NATURAL_KEYS` testa `fonte` antes · **`posicao_31_12` tem 0 itens no snapshot do dogfood** — o split precisa do substrato de golden antes, não depois |
| [[A40.l40]] | Identidade institucional por CNPJ-raiz: o matcher informe↔extrato casa 0 de 6 por nome livre | P1 | — | `shipped` (#1404) · [[ADR-384]] `Decidido` (flip corrigido no lane-closeout) · linha adicionada em 2026-08-12 (#1415) |
| [[A40.l41]] | Frescor cross-pool: posição stale de 2025-03 vale R$ 206k no bruto contra IRPF 31/12/2025 de R$ 2,4k | P1 | l42 | `open` (era `in_progress` sem branch remota) · aberta pelo #1381 · [[ADR-383]] `Proposto` (#1401) · PR-a observacional mergeado #1419 · linha adicionada em 2026-08-12 (#1415) · **o PR-b não começou e está inimplementável como escrito** (§Aberto 2026-08-27, #1754): o árbitro joga posição sem dono no balde do **titular** (`membro_default=titular_key`), contra o `patrimonio_calculator` que manda `nao_atribuido`, *nunca* titular ([[ADR-394]] §D8) — e o produtor emite mesmo o vazio · `pool_atual_por_celula` é constante `"posicoes_atuais"` contra os 3 valores publicados uma chave acima · o golden traz 1 célula só de IRPF e `contradicoes: []`, então o caso C6 que abriu a lane **não é exercitado** · warnings só em log, o que a [[ADR-383]] `:90` proíbe · o flip muta E5 ⇒ entra na janela de rebaseline compartilhada (`l91 → l89 → l90`) |
| [[A40.l42]] | Safra IRPF errada: baseline pegajoso — E1.5c re-consolida o próprio output do run anterior e ignora o E1.5 fresco | P1 | — | `shipped` (#1395) · aberta pelo #1381 · título e arquivo mudaram no #1421 (a raiz não era ordenação lexicográfica) · linha adicionada em 2026-08-12 (#1415) |
| [[A40.l43]] | Card A Família: a coluna direita repetia o hero, e o validador exigia que ela existisse | P1 | — | `shipped` `849e372b` (#1386) · achado do parecer de design · emenda [[ADR-356]] (regra: o narrador não publica valor nem juízo) · fecha por remoção o item de `n_imoveis` da [[A40.l6]] e a classe da [[A40.l15]] · transfere p/ [[A40.l29]] |
| [[A40.l44]] | Janela interativa pré-computada: o cliente para de ser um segundo motor de agregação | **P0** | — | `shipped` (#1462 · `8d07c4fb`) · [[ADR-377]] `Decidido` · 6 PRs (#1397/#1396/#1398/#1449/#1456/#1462) |
| [[A40.l46]] | Resíduos do bloco de identidade (perfil): baseline de print não provada + variant `feature` sem o DNA do mockup | P2 | ❌ **cancelada** | aberta 2026-08-12 no fecho do #1382 · coleta os 2 achados sem dono da investigação do overlap · item 2 executa o deferimento da [[A40.l33]] §3 ([[ADR-117]] na mesa) · admissão retro-registrada 2026-08-12 (§Fora do sprint) · **CANCELADA 2026-08-30 com roteamento** — nenhum dos 2 itens é trabalho de lane: baseline de pixel do PDF → [[A40.l10]] (pendência do dono; regeneração é `workflow_dispatch`, e a lane passou 18 dias `open` esperando ato que não vem de agente); variant sem DNA do mockup → [[A40.l13]] · débito aceito: a página 1 do PDF segue não provada em Linux |
| [[A40.l47]] | Três números cuja semântica não bate com o rótulo: taxa de retirada, faixa comportamental e base da reserva | P1 | — | `shipped` `5d3bb01b` (#1459) · PR1 `ae2b2453` (#1452) · dono `financial-planner` · emenda datada [[ADR-191]] §D6: `goals.trs_pct` é taxa de **saque** — a emenda de 2026-07-15 a atribuía ao card como yield-alvo, e era ela que registrava a promoção do RV4-13 · 3 gates provados por mutação · 2 deferidos com dono (chave `yield_alvo_pct` → `financial-planner`; fixture da divergência base-vs-carteira → `data-engineer`) |
| [[A40.l48]] | Polaridade de comparação é fixa por métrica, mas cobertura de reserva não é monotônica no alvo | P2 | — | aberta 2026-08-12 (#1411, r4) · dono `data-engineer` · linha adicionada nesta passada |
| [[A40.l49]] | Parecer: rótulo de evidência derivado do root do path + dois guardrails que não podem disparar | P1 | — | `shipped` (#1487 · `cb9253eb`) · pairing contra `citation_labels`, não o root · MC por S7+lemma · ano no motivo não é SPURIOUS · emenda [[ADR-296]] · RV4-11/14/17 fechados · RV5-02 fora |
| [[A40.l50]] | Abertos da investigação de exposição cambial: inventário verificado do que não foi atacado | P1 | — | aberta 2026-08-12 · resíduo do #1393 (`d1b7c97c`) · 18 achados sobreviveram a refutação adversarial, 2 refutados · contém **P0 fora do card** (`consolidate_baseline` re-consolida run anterior; rodapé PTAX afirma conversão que não houve) · 5 questões de domínio sem dono · [[ADR-379]] bloqueada por dependência de ordem |
| [[A40.l45]] | Clipping horizontal em caixa ≤700px: o dado saía do relatório sem rastro (mobile 390 · A4 703) | P1 | — | `shipped` `70407cc3` (#1387) · [[ADR-381]] · gate novo `overflow-horizontal.@critical` provado por mutação · residuais → [[A40.l53]] [[A40.l54]] [[A40.l55]] · auditoria de fechamento (2026-08-12/13) achou o fix do `ReportCard` não-commitado em #1387 (checkout apagou o edit); fix real em `9ab41aff` (#1429) |
| [[A40.l51]] | Follow-ups órfãos da [[A40.l43]] — o que o co-design achou na vizinhança e ninguém ataca | P1 (proposta) | — | aberta 2026-08-12 a pedido do dono · lane de **registro**: cada item com medição citada + fix mínimo, para não evaporar no fim da sprint · prioridade/onda são gatilho de `product-manager` |
| [[A40.l53]] | Gate visual de seções cego: a **captura** reinicia o desenho do chart, e o mesmo defeito imprimia o gráfico pela metade no PDF | P1 | — | `shipped` `8934b00d` (#1453) · aberta 2026-08-12 no fecho da [[A40.l45]] · **vizinha, não duplicata, da [[A40.l46]] item 1** (aquela é o job de PRINT/página 1; esta, o de snapshots por seção) · o ataque **refutou o diagnóstico de origem**: não é "S2 flaky 5–6% intra-commit" (sem throttle dão 0,000% em 11 pares) nem "6 baselines podres" (as de 08-12 foram refeitas pelo #1384 1h depois) — cada `screenshot` zera a largura do canvas e o Chart.js redesenha, então o gate de estabilidade perseguia o próprio rastro · fix: `prefers-reduced-motion` (10,485% → 0,000%) + captura do PDF amarrada ao fim do desenho · gate novo `chart-determinismo.@critical` sem baseline e sem label, provado por mutação nas 2 direções · 7 baselines rebaselinadas com origem nomeada · método de triagem `actual`×`actual` em `TESTING.md` |
| [[A40.l54]] | `hidden md:block` entrega ao papel a variante mobile: varredura + gate ([[ADR-381]] D1) | P2 | — | ✅ **shipped 2026-08-18** (#1516) · aberta 2026-08-12 · eram **4** call-sites com perda de dado (não 2): `alocacaoCardParts`, `CoberturaSegurosCard`, `Top15AtivosCard` e `IrpfDedutiveisAplicadosCard` — todos convertidos para `sm:`/`print:` · gate `dev/check_hidden_md_on_paper.py` + hook `hidden-md-on-paper` + sonda de perda tela→PDF como spec permanente (`print-text.@critical.spec.ts`) · **o registro ficou 9 dias atrás do código** — instância da classe que a [[A40.l59]] gateia · **fecho 2026-08-27** (#1754): 3 critérios verificados por execução e **3 limites do gate declarados** (polaridade **invertida** em `max-md:`; `lg:`/`xl:` invisíveis; allowlist isenta o **arquivo**, e `ReportShell.tsx` hospeda o `<article>`) |
| [[A40.l55]] | Medida de linha no papel: 100–110 cpl na prosa do A4 | P3 | — | aberta 2026-08-12 · polish de legibilidade; fix candidato `max-width: 90ch` em `@media print` |
| [[A40.l56]] | A tabela fiscal de produção: row internamente inconsistente e nenhum golden a atravessa | P1 | — | `shipped` em 6 PRs (#1469 · #1470 · #1473 · #1475 · #1479 · **#1483**) · desbloqueou [[ADR-375]] D5 para `AC ≤ 2025` e a [[A40.l64]] · [[ADR-389]] `Proposto` · nasceu `l50`, renumerada no dia (o #1409 tomou o id em paralelo) |
| [[A40.l57]] | O parecer lê o contrato antigo do bloco PGBL: guardrail FP-04 morto e âncora que resolve `null` | P2 | — | aberta 2026-08-12 · handoff da [[A40.l7]] **agravado pelo PR2 da [[A40.l34]]** (#1394) · dono `prompt-engineer` · sobe a P1 se dogfood mostrar retenção espúria |
| [[A40.l58]] | `schema_validation` warn → strict — o PR5 que a [[A40.l5]] declarou como outra lane | P2 | [[A40.l5]] ✅ | ✅ **`shipped` 2026-08-24** em 7 PRs (#1650 · #1656 · #1664 · #1665 · #1667 · fecho **#1668** · re-roteamento #1670) · [[ADR-409]] `Decidido` · **o flip NÃO é entregável de lane** ([[ADR-284]] §Não-decisões: é operacional) — os 4 critérios pediam estar *pronto*, e o go/no-go virou comando (`dev/measure_schema_drift.py --gate`, exit code, sobre o corpus) em vez de agregação de log que nenhum sink coleta · drift medido: **11,8% dos artefatos violam o próprio schema** · 2 deferimentos datados, dono `data-engineer`: contrato do stub de fallback do E2 (classe [[ADR-407]]) e re-derivar `baseline_patrimonial` (declara 5 de 13 chaves do payload real — maior risco de produto) · aberta 2026-08-12, `open` desde 08-17 |
| [[A40.l59]] | A transição para `shipped` ganha gate: `ship_pr` no frontmatter e PR visível no `_README` | P2 | — | aberta 2026-08-12 · executa o gatilho de promoção da skill `lane-closeout` (3ª ocorrência + 10 lanes fora desta tabela **na medição de 2026-08-12**; re-medido em 2026-08-24 pelo §Ataque da lane: **1** — a l77) · **atacada 2026-08-24** (#1648: só o §Ataque, +98 linhas) · **`shipped` 2026-08-24** (#1661: §Escopo/§Critério corrigidos por medição, gate de coerência no escopo, `dev/check_lane_transition.py` + hook `lane-transition`, e 2 falhas-abertas da skill `lane-closeout` consertadas) · dono `information-architect` |
| [[A40.l60]] | Conselho de seguro: cobertura recomendada sem ressalva fiduciária + string que afirma invalidez sem fonte | P1 | — | aberta 2026-08-12 no fecho da sessão S6/FP-010 (#1379/#1390) · funde 2 achados verificados (mesmo produtor, mesma classe fiduciária) · KR-E · **PR1 ✅ #1480 (`49c1cb3c`, 2026-08-15) — 3 superfícies + gate `check_coverage_disclaimer` + emenda [[ADR-192]]**; segue `open` pelo **PR2** (separar vida×invalidez), cuja amarra caiu quando a [[A40.l35]] shipou (#1476) — a rota de "declarar não-entregue" fechou · nasceu `l50`, passou por `l58`, renumerada 2× em rebase (ids tomados em `main`) |
| [[A40.l61]] | ProtectionBundle fail-closed: ausência não vira zero/False | P1 | — | `shipped` (#1443 · `0a343302`) · mitigação do split da l35 · não liga a S9 |
| [[A40.l62]] | Fontes canônicas + ProtectionComputationSnapshotV1 | P1 | l61 | `shipped` (#1471 · #1474 · `5cc4a02f`) · [[ADR-387]] `Decidido` · não liga a S9 |
| [[A40.l63]] | Conversão ME→BRL não registra proveniência: taxa hardcoded indistinguível de real, saldo BRL rotulado USD | P1 | ✅ | aberta 2026-08-15 no co-design do P0 nº 2 da [[A40.l50]] · [[ADR-390]] `Decidido` · escopo shipado no #1494 (2026-08-17) **sem flip de `status`** — 7 dias `open` com o trabalho em `main` · #1658 mediu o entregue (funil era campo opcional; ratchet pegava 3/10) · fecho no #1671 (§Fecho da lane) · §4/§7 do ataque → [[A40.l50]] |
| [[A40.l64]] | Redutor da Lei 15.270/2025 + IRPFM: a economia de PGBL não pode ser publicada para AC2026 | P1 | l56 ✅ | **✅ shipped 2026-08-25 (#1722)** · PR1 #1501 (recusa) · **PR2 #1672** (diferencial do D5) · **#1689** (economia zero não prescreve) · **PR3 #1703** (contrato do redutor + [[ADR-414]] bruto×base) · **PR4 #1715** (detector do IRPFM) · **#1722** flipa AC2026 para `regime_completo: true` · o flip é seguro porque NÃO liga tudo: com 2+ declarantes a base é soma familiar e a economia sairia superestimada, então `base_familiar_nao_particionada` retém ali · §Deferimento do DOU CAIU por medição (o R$ 1,08 era construção da norma; o clamp do art. 11-A absorve) |
| [[A40.l65]] | Base do PGBL perdeu a âncora de declarante: o ano já é o eleito, e a base é a do titular | P1 | — | **✅ shipped 2026-08-25 (#1711)** · §Escopo 1 **#1672** (ano eleito, fim dos dois resolvedores) · §Escopo 3 **#1690** (ano de proveniência + ramos de degradação deixam de ser mudos) · §Escopo 2+4 **#1711** (âncora de titular, base sai do vencedor do dedup, gate de coerência) · âncora vai para a **S8**, não para o card do E5: a variante do E5 exigiria mover o Card B, agregação vedada pelo §Fora de escopo · limite declarado: a máscara guarda 2 dígitos (~1% de colisão com 2 declarantes) |
| [[A40.l66]] | Seam extração/consolidação: o fato decide ativo vs. passivo, o rótulo do LLM vira hint | **P0** | — | aberta 2026-08-17 na Onda 0 do [[PLAN-deterministic-authority]] · FK `plan:` distinta do resto da sprint (exceção do §Critério de admissão da [[A42]]) · RV6-01/02/03 · **`shipped` 2026-08-18** em 5 PRs (#1520 [[ADR-394]] · #1521 contrato · #1522 seam · #1523 cauda · #1524 cap) · o ataque prévio (#1510/#1518) mostrou que os degraus 1–2 mediam 0% e que o critério passava com o catálogo inerte — a hierarquia entregue põe `secao` em primeiro |
| [[A40.l67]] | Guarda de publicação no E5: nenhum balde publica negativo, e o schema deixa de aceitá-lo | **P0** | l66 | ✅ **shipped 2026-08-18** (#1529 · #1531 · #1534 · #1536 · #1537) · 1d (guarda de sinal, com o split derivado de cat_2 que a redação literal deixaria passar) + 1e (schema) · o flip strict saiu para [[A40.l58]] — critério temporal que esta lane não podia executar |
| [[A40.l68]] | Balanço de stage fan-out: documento que some não pode sair como sucesso | P1 | — | aberta 2026-08-17 na Onda 0 do [[PLAN-deterministic-authority]] · RV6-10 · `open` (liberada pelo dono 2026-08-18) · [[ADR-393]] `Decidido` (emendada 2026-08-19 e 2026-08-24) · **2a** (#1526), **`.xls`** (#1655), **2b** (#1657), **D3/D5** (#1663) · §Ataque + §Fecho 2026-08-24 · **paralela desde o dia 0**, não disputa janela de rebaseline · [[A42.l4]] não amplia |
| [[A40.l69]] | Cobertura de investimentos por membro: zero apurado não é o mesmo que não apurado | **P0** | l66, l67 | ✅ **shipped 2026-08-19** (#1538 · #1541 · #1542 · #1550 · **#1578**) · RV6-04 · 3a (cobertura em 3 estados + balde `null`) e 3b (token, não substring + balde não-atribuído) · J4 fechada sem `value_delta` · a varredura foi entregue por **token normalizado**, não match exato — exato derrubava a resolução (medido) · o **#1578** é o PR que tornou o 3a alcançável: sem ele o predicado media o contêiner e `nao_apurado` era inatingível (0/114) |
| [[A40.l70]] | `endereco_canonical=None` não cria identidade: match por titular+código ou `needs_review` | P1 | — | `shipped` (#1508 · `0f35fbf3`) · [[ADR-392]] · 4b-i / RV6-13 · 4b-ii fica na track |
| [[A40.l71]] | Predicado único da composição patrimonial: o donut e a tabela decidem o negativo explicitamente | P1 | — | aberta 2026-08-17 · item 7e da Onda 7 do [[PLAN-deterministic-authority]], FK `plan:` para [[PLAN-report-trust]] (casa das lanes de render) · RV6-23 · `shipped` (#1511 · `50033dae`) · enabler sem copy, mergeou antes da l72 · gate v1 era cego (casava mesma linha), trocado por leitor único |
| [[A40.l72]] | Guarda de contrato no render: o relatório deixa de fechar 100% sobre payload que viola invariante | P1 | l66 | aberta 2026-08-17 · item 7a da Onda 7 do [[PLAN-deterministic-authority]], FK `plan:` para [[PLAN-report-trust]] · RV6-16 · **`open` desde 2026-08-18** (a l66 shipou, e o warning tipado existe) |
| [[A40.l73]] | Produtor do bundle de proteção lê a fonte documental, e o `gap_qualitativo` reconcilia com os dependentes do IRPF | P1 | — | aberta 2026-08-19 · item **3c inteiro** da Onda 3 do [[PLAN-deterministic-authority]], por autorização explícita do dono (fora do MVP declarado) · PD-4 / RV6-20 · [[ADR-395]] `Decidido` · `parallel_with` [[A40.l60]] (dormente; divisão de arquivos declarada na lane) · **`shipped` 2026-08-19** (#1549 · #1554 · #1560 · #1564 · #1576) |
| [[A40.l74]] | Stage com dois produtores, schema 1:1: apólice validava contra o schema de veículo, e o mapa mentia em três lugares | P1 | — | aberta 2026-08-21 · fecha a metade apólice do problema cujo lado CRLV saiu em #1599 · [[ADR-407]] `Proposto` + emenda datada em [[ADR-239]] §D8 · descobriu 2 consumidores extras do 1:1 (`_schema_version_token` carimbava row de apólice com hash de schema de veículo; `check_artifact_read_keys` lê o mapa por `ast.literal_eval`) · follow-up de `e4_unified` endereçado a [[A40.l58]] · **`shipped` 2026-08-21** (#1604) |
| [[A40.l75]] | O gate de drift do MSW existe, está fora do CI e compara errado: a [[ADR-069]] afirma uma proteção que nunca rodou | P2 | — | aberta 2026-08-21 · achado da camada 2 do `lane-closeout` no fecho do #1618 (que declarou 129 requests órfãs do MSW em 7 arquivos) · `msw-lint.mjs` existe desde 2026-04-22, **fora do CI**, e contra o snapshot commitado devolve 219/219 + 75/75 — 100% falso-positivo, porque `normalizeUrl` não remove o prefixo `${API}` que o próprio comentário promete remover · 3 defaults pré-escopo de workspace sobrevivem em `handlers.ts` |
| [[A40.l76]] | A FK de proveniência do E2 nunca foi populada: o tombstone erra 630 rows e duas ADRs descrevem uma aresta vazia | P1 | — | aberta 2026-08-21 · `document_id` NULL em **16.292/16.292** (re-medido) · [[ADR-408]] `Proposto` (#1607) decide o fix em co-design `data-engineer` + `senior-cto`; [[ADR-311]] emendada com o alcance real do D1 · gate da lacuna já em `main` (#1600, `xfail(strict=True)` que se auto-remove quando a FK popular) · 4 peças em ordem dura: guard de colisão → FK por porta → backfill → predicado |
| [[A40.l77]] | Dois resolvers de membro sobre o mesmo baseline: o fix do eixo de ano chegou em um e o cônjuge vale 110k e 0,00 no mesmo payload | P0 | ✅ **#1684** | **shipped 2026-08-24** em 4 PRs (#1669 → #1676 → #1677 → #1684) sob a [[ADR-410]] (`Decidido`): produtor único de membro, injetado, com os 3 resolvers mortos enterrados e 3 gates no payload (**D4 parcial, D5 e D6 não executados** — [[ADR-410]] §Emenda 2026-08-24, dono `data-engineer` na J5) · aberta 2026-08-24 (#1643) como DE-10 do r7 · medido **na fixture sintética de 2 membros** (não em produção — não há artefato pós-fix; ver a nota do r8 acima): `total_financeiro` 900.000 → **1.010.000**, `investimentos_conjuge` 0,0 → **110.000** · **zero rebaseline** de golden ou snapshot · **destrava o DE-7** |
| [[A40.l78]] | Mover código não deixa citação órfã: gate no lado do código, não no do doc | P2 | — | ✅ **shipped 2026-08-25** (#1654) · achado **F21** da auditoria r10 ([[ADR-302]]) — cluster [[ADR-285]] reaberto com 71 ocorrências. Polaridade escolhida por medição: doc-side deu 3 disparos e **zero** verdadeiro; code-side deu 2 e zero falso · **o fecho (#1754) achou 3 coisas que o critério de aceite exigia e não estavam de pé**: a saída histórica que a mensagem anunciava era **inexequível** (a linha da [[ADR-196]] já dizia *removido pela ADR-375* e seguia acusada — marcar sem tirar o backtick não suprime nada; corrigido pela mensagem, sem allowlist, e pinado em teste), o modo `--since` carregava 100% da evidência do critério 1 **sem um teste sequer** (suíte 6→10, mordida provada por mutação), e 2 números foram re-medidos (306→**307**; o **1123** do corpus **não reproduz** em leitura nenhuma — 1214 com `archive`, 913 sem) · não-coberturas agora declaradas: link markdown sem backtick (**291** citações, 0 órfãs hoje), `docs/_MOC/` fora do `DOC_SCOPE`, e **CI não reprova por este gate** (sob `--all-files` o índice é vazio ⇒ no-op) · §Deferimento com dono `information-architect` |
| [[A40.l79]] | A recusa do regime fiscal é fail-open: sem row do ano o default republica | P1 | **shipped** #1750 | aberta 2026-08-24 no ataque às l64/l65 (#1659) · **fechada 2026-08-26**: a causa raiz era de VOCABULÁRIO — as duas implementações do `ConfigStore` levantavam exceções diferentes e o pipeline não pode importar nenhuma (ADR-089), então o `except Exception` era a única coisa possível · `FiscalParametersAusentes` vive no port e a ausência vira recusa com motivo próprio, distinto de `regime_fiscal_incompleto` · o clamp da fixture caiu (§Escopo 4) |
| [[A40.l80]] | Denominador amputado: metade da carteira financeira não tem dono, o investível a exclui e o bruto a inclui no mesmo arquivo | P0 | ✅ **34 PRs** #1702 #1705 #1710 #1713 #1727 #1735 #1741 #1742 #1757 #1768 #1769 #1774 #1780 #1781 #1782 #1783 #1784 #1785 #1788 #1790 #1794 #1795 #1799 #1800 #1801 #1802 #1803 #1804 #1805 #1806 #1807 #1808 #1811 #1835 | aberta 2026-08-24 · cluster do §r8 (RV8-02/03/04/06/10) · [[ADR-412]] `Proposto` + 2 emendas datadas · **o defeito está corrigido e o relatório publica o intervalo**; critério de aceite **2 fechados, 2 parciais, 1 refutado** — o gate de Completude achou defeito no primeiro uso (a concentração dividia por 73M e nenhuma base publicada continha esse valor; 6ª base `carteira_produtiva_fixa`, número-neutra) e cobre **4 de 4** razões após o #1785 (autonomia + piso); a 4ª (cambial) fechou depois de unificar o numerador — E5 e card divergiam 12,0% × 2,0%, e o card passou a **consumir** o artefato (#1794/#1795), porque rótulo de base declara denominador e não conserta numerador; a Precisão corrigiu duas declarações falsas no #1769; a lane fecha com **4 dos 5 eixos** e a Prova de fecho **3 de 4**: o critério original segue refutado (C16) e o **P3 vai a §Deferimento datado com pré-requisito medido** — a §D7 promete supressão em 6 vereditos e está ligada em 1, com 2 grandezas em código morto, então o gate '≥3 pela mesma causa' nasceria verde — P1 paridade de numerador (#1794), P2 frescor mata prescrição (#1803) e P4 zero labels com régua no manifest inteiro (#1808). O **P3 está refutado como escrito** e tem pré-requisito nomeado: a §D7 promete `cobertura_incompleta` suprimindo 6 vereditos e está ligada em **1**, com duas grandezas em código morto — o gate '≥3 pela mesma causa' nunca dispararia, e escrito contra o dogfood nasceria verde. Os critérios **estavam redigidos de forma inexequível** (§Correções 2026-08-27, C11–C15): a Completude que a lane pedia a [[ADR-412]] §Consequências já refutava por escrito, e o closeout #1758 a reinscreveu; `motivo` colide com a XOR de `kpi_targets[]`; a Prova de fecho nomeia superfície que a §D5 proíbe. Quem pegar o PR4 lê §Correções antes · **três teses da abertura foram REFUTADAS pela medição e emendadas**: o eixo é domiciliar × por-pessoa, não composição × runway (§D0); abrir o enum de `membro` foi **rejeitado** — quebra leitor antigo lendo artefato novo e publica pessoa que não existe (§D5); e a banda cambial vai para `indeterminado`, **não** amarelo — `tier` é constante desde o #1568 (§Emenda E2) |
| [[A40.l81]] | Diagnóstico sem canal de saída: o stage que não pausa entrega razão no artefato e ela não chega nem à tabela nem ao usuário | P0 | ✅ **#1697** | **shipped 2026-08-25** sob a [[ADR-411]] (`Proposto`): sink em todo desfecho, colheita em qualquer posição, `locator` na chave da row, e a tabela ganha o **primeiro leitor** (`compare_reviews`) · **a lane tinha a causa pela metade** — remedido, são **43 de 46 ocorrências perdidas (6,5% de cobertura)**, não 4, e o `detail` do `consolidate_baseline` não tem bloco `validation` nenhum, então mover o sink sozinho colheria **zero** para o stage que deu origem ao achado · gate medido por mutação (sink só na pausa reprova 5/6; colheita só no topo, 3/6) · **2 deferimentos com dono** ([[ADR-411]]): superfície de usuário para aviso-sem-pausa (owner) e a poda por stage que não alcança a tabela (`data-engineer`, achado no closeout — `reset_workspace_from_stage` preserva o run e deixa a row com ponteiro morto) · **closeout 2026-08-25** (#1699): ADR flipada para `Decidido` e 1 número corrigido (10 rows, não ~8) · **fechada por medição 2026-08-25** (run determinístico `7164ddee`): A/B no mesmo corpus diferindo só no código do worker — **0 → 5 rows** de stages que ENTREGARAM (Σocc 32), `locator` 7/7, total 7 rows/Σ37 contra 2/Σ3 · RV8-09 do §r8 → `procede-fechado` · a medição achou e corrigiu um defeito (o re-harvest sobrescrevia o `locator` do item) e o eixo de VOLUME do deferimento de retenção ficou **refutado** (7 rows/run) · **limite declarado no 2º closeout**: o fix do `locator` foi commitado 7min DEPOIS do run, e nenhum run rodou desde — o eixo do locator está provado por teste unitário, não por execução (o predicado de fecho não depende dele) · aberta 2026-08-24 · RV8-09 do §r8 · **primeiro da fila**: é o que torna RV8-01/RV8-19 observáveis sem outra revisão manual · re-medido: 4 razões no artefato do `consolidate_baseline`, 0 rows na tabela (as 2 da tabela vêm do único stage que pausou) · não é `_drop_unknown_codes` — os códigos estão na allowlist · **três armadilhas**: a tabela é write-only (consertar só a escrita repete RV8-17/RV8-12), as razões têm duas formas e o sink só lê a de topo, e o gate óbvio é cego pela mesma metade · ordem da [[ADR-404]] é restrição dura |
| [[A40.l82]] | Um default de grupo RFB decide a classe de 13% da carteira, com confiança plena e sem sinal | P0 | ✅ **#1698** | **shipped 2026-08-25** · **RV8-01 do §r8**, o achado nº 1 · origem [[A40.l77]] §RV8-01 (aquela lane registra a regressão, esta conserta; a l77 não reabre) · medido: 11 de 61 posições migram `Fundos`→`Renda Fixa` com `autoridade: keyword` e zero `review_reason` — R$ 174.636,71 (13,1%) pós-resolver, R$ 323.936,08 (16,6%) sobre itens crus · `tipo` sai da entry + 5 marcas de gestora saem do default **e** de `config/scoring.json` (só do default seria no-op) · gate comportamental com mutação nas duas direções · Σ preservado (194.647.320 cents) · **no fechamento, achado que inverte um §Fora de escopo desta lane**: a contenção **subavalia** a reserva da cônjuge em R$ 25.337,34 — a `poupanca` dela vinha de ramo de **evidência** e `tipo` era o único portador; dá janela ao `tipo_proveniencia` ([[ADR-400]] §"A contenção tem custo medido") · **não foi para a J5** — modo de falha oposto ao do DE-7 (redistribui vs. soma) |
| [[A40.l83]] | Parecer cego em três eixos: não recebe a incerteza, não consegue citar o que recebe, e o guardrail inverte o diagnóstico | P0 | ✅ **#1716** | **shipped 2026-08-25** · **RV8-05+RV8-07+RV8-16 do §r8**, em 5 PRs (#1707 semente do catálogo · #1709 KPI de densidade · #1712 guardrail 4-vias + emenda [[ADR-206]] · #1714 projeção da incerteza · #1716 drift `warn`→`fail`) · **ancorabilidade no E5 real 0/36 → 32/37 (86,5%)**, piso era 80% · `field_requests_spurious` **2 → 0** aferido por replay do audit do r8, e os 2 pedidos voltam ao output · semear custa **zero** (0%→52,8% no orçamento intacto); subir bytes sem semear compra 25% a 3,1× · **3 correções ao enunciado**: o remédio do RV8-07b (gate no golden mensal) não serve — esse eval **nunca rodou**, sem secret, 4 runs pulando com `success` e baselines vazias (owner-gated); o RV8-05b era pior que `warn`, era **inerte** (`git diff HEAD` é vazio sob `--all-files`); e o joelho de `max_bytes` **anda** com o manifest (2400→81,1% após a projeção; 2600 devolve 86,5%) · **armadilha central nomeada, não fechada**: o corpus do gate lê 92,9% contra 86,5% de produção e reverter a semente custa 7,2pp ali contra 86,5pp em produção → [[A40.l85]] · residual de duas fontes de monetariedade → [[A40.l86]] |
| [[A40.l84]] | O invariante é declarado global em comentário e enforçado num só ponto de entrada: run completa sobre review que ninguém aprovou | P0 | — | aberta 2026-08-25 · RV8-08 do §r8 · guard de `pending` só em `resume_run.py:21-33`; `pipeline_service` não consulta `stage_reviews` · medido: os 2 pares `(completed, pending)` do DB são o r7 e o r8, e o r7 é o **baseline de compare** do r8 · o runbook documenta o contorno como ação operacional · **escopo inclui** dar à skill uma ação de aprovação, senão o fix quebra em silêncio e o operador contorna por caminho pior · **✅ `shipped` 2026-08-27 (#1771)** · [[ADR-404]] §Emenda 2026-08-27 · o predicado sai da camada HTTP para `stage_review_gate.py` e é consultado na **mesma sessão** do `UPDATE` (contar numa e flipar noutra era TOCTOU) · **a rota do §r8 estava incompleta em dois pontos**: `_finalize_run` não é o único escritor de `completed` (`_mark_run_completed` grava direto quando o stage pausado é o último do `FULL_ORDER` — medido por execução), e *recusar* ali converteria "ninguém decidiu" em "morreu" pelo `on_failure`, então ele **re-estaciona** · `DELIVERING_STATUSES` é tupla LISTADA e há teste de **escopo** provando que `(failed, pending)` sobrevive — é o que impede o próximo refactor de morder o resíduo sancionado da [[ADR-417]] D3 · predicado `NOT IN (approved, edited)`, não `== pending` · **a afirmação global falsa estava em 5 sítios**, um deles a *justificativa* de um gate, o que inverteu o custo da alternativa "corrigir para a verdade menor" · skill ganhou `resolve_pause.py` (3 saídas pela rota; a 1ª execução real pagou 3 defeitos que revisão de código não pegaria) · as 2 rows históricas **anotadas, não backfilladas**, congeladas por id em `dev/check_par_completed_pending.py` (mede QUAIS, não quantos; banco vazio é WARN) · 4 abertos com dono no §Aberto, o 1º medido no harness: `resume_run` responde **500** em falha de dispatch |
| [[A40.l85]] | O gate de ancorabilidade roda sobre um corpus que não consegue reproduzir o colapso que ele existe para pegar | P1 | — | aberta 2026-08-25 no fecho da [[A40.l83]] · o mesmo instrumento dá **92,9%** no corpus sintético e **86,5%** no E5 real; antes do fix dava 39,3% contra **0%** · a causa é cardinalidade: onde produção tem **31** linhas de endividamento e **28** de reserva, o corpus tem **2** e **4** — e são as duas raízes que consomem o catálogo, logo o colapso é estruturalmente irreproduzível ali · medido: reverter a semente custa **86,5pp** em produção e **7,2pp** no sintético, e o delta do sintético ENCOLHEU (era 53,6pp) quando o orçamento subiu · **armadilha**: `make_workspace_e5` tem raio de 11 arquivos, incluindo golden e PII scan |
| [[A40.l86]] | Duas fontes decidem se uma folha é dinheiro: o format declarado no manifest e o palpite pelo nome do campo | P2 | — | aberta 2026-08-25 no fecho da [[A40.l83]] · `format: brl` declarado no manifest vs `_MONEY_KEY_TOKENS` casando substring de nome · discordam em 3 campos medidos no E5 real: `investimentos_nao_atribuidos` (resolvido no #1714 com token novo), `transferencia_patrimonial` (segue inancorável) e `teto_sugerido` (**extinto do contrato** em 2026-08-29 pela [[ADR-422]] D2 ⇒ os ofensores vivos caem de 2 para 1) · adicionar token remedia instância, não classe · **armadilha**: o catálogo é BRL-only por construção e caminha o E5 inteiro, não só o projetado — trocar heurística por declaração ENCOLHERIA o catálogo |
| [[A40.l87]] | A pausa não tem porta de saída, e o botão que o produto já oferece devolve 409 há quatro meses | P1 | ✅ **#1740 · #1743** | aberta 2026-08-26 no desbloqueio do preflight da [[runbook-unified-certify-review]] · admissão retro-registrada (§Fora do sprint), precedente [[A40.l46]] · [[ADR-417]] `Proposto` em co-design `product-manager` + `senior-cto` (convergentes) · **a decisão de produto já existia**: `NeedsReviewCard.tsx:63` oferece "Cancelar execução" desde **2026-04-21** e o backend responde 409 — o comentário que diz "é decisão de produto" entrou 3 meses depois · dois falsos-verdes pinam a crença (teste do card assere fiação, não desfecho; `test_detect_undispatched_runs.py:243` assere a exclusão) · **o buraco é executor duplo, não só orfanamento**: `_flip_run_to_resuming` não checa run ativo e a pausa é invisível ao índice e ao fast-path · 2 PRs em ordem dura (porta → bloqueio); o índice parcial **não muda** ([[A40.l27]] é precedente) · `parallel_with` [[A40.l84]] com partição declarada — o predicado dela é `(completed, pending)`, **nunca** "terminal + pending", senão morde o resíduo sancionado  · **`shipped` 2026-08-26** em 2 PRs sob a [[ADR-417]] (`Decidido`): #1740 a porta (tupla + tabela exaustiva de saídas + guarda de terminalidade no `action_review`) e #1743 a pré-condição (409 no trigger nomeando as saídas + guarda de executor concorrente no resume + coluna `cancelled_from_status` + card da pausa sobrevivendo ao reload) · **o D4 foi refutado por medição DENTRO da lane**: a 1ª redação derivava o descarte de `paused_at_stage`, que ninguém zera — reescrito in place (a ADR era `Proposto`, nunca vigorou) com §Alternativa refutada carregando as 3 medições · 5 mecanismos, 5 mutações, todas reprovando · **índice parcial NÃO muda** (D5 §Deferimento, dono `data-engineer`: a migração quebraria hoje no dogfood) · aviso de colisão de predicado escrito DENTRO da [[A40.l84]]|
| [[A40.l88]] | Consumidor ausente no entregue: o produto emite a ressalva, a seção e o aviso — e nenhum dos três chega ao leitor | P0 | ✅ **#1755** | **shipped 2026-08-27** · os três achados fechados + gate de polaridade inversa (`check_emitter_without_reader`, 3 direções, no pre-commit) · **a §refutação da própria lane era falsa**: o `return null` da `:18` é guarda de *shape*, e `compute_protecao` devolve o bloco completo com prêmio 0,00 para workspace sem apólice (medido) — a [[A40.l7]] estava certa no mérito e errou só o campo que citou (`protection_bundle`, que é da S9) · flip autorizado pelo dono **com** `temCoberturaContratada` · **o gate reprovou a própria lane**: `<ul hidden>` não é sobreponível (`[hidden]` é `!important` de UA), mesma classe do `--details-open` inerte uma camada abaixo → `hidden print:flex` · o gate nasceu com 2 falsos-verdes que a construção mediu (`gated.notas_metodologicas`; `pkg.version` **em comentário**) · o fix do RR5-03 quase reintroduziu a classe pela paridade tripla de `section_id` → `SECOES_SEM_ANCORA` · **critério meio atendido**: o índice filtra por `enabled` estático, não por render — âncora morta na fixture vai de `{S4, APP_C}` para `{S4, APP_C, S_PROTECAO}` ([[ADR-167]], classe pré-existente) · **print intacto, nenhuma baseline de print muda** · **closeout 2026-08-27**: o §follow-ups dizia "com dono" e não nomeava nenhum (CLOSE-BLOCK) — os 3 viraram §Deferimentos datados com dono e condição de retomada, o waiver do gate deixou de apontar para a própria lane fechada, e as 3 linhas do §r5 da [[REPORT-REVIEWS-active]] foram reconciliadas — a de RR5-03 ainda **ensinava a premissa falsa** · **render puro, não zera o contador** · onda 1 |
| [[A40.l89]] | Wiring do catálogo de alvo: o produtor suprime o limiar por falta de procedência e o parecer o republica | P0 | ✅ **#1770 → #1772 → #1779** | **retomada do §Deferimento D3**, não locus novo · fecha a metade `metricas[]` do RR5-02 (o braço do plano de ação foi para a [[A40.l90]], #1773) · o catálogo virou leitor único do alvo publicado; o modelo emite `metrica_key` e **não pode** emitir alvo/observado/rótulo; órfão perde o comparador e mantém o sinal; artefato congelado coberto por **supressão na leitura**, sem backfill · **o #1779 é hotfix de 7 defeitos que os dois primeiros introduziram** — 2 P0 do autor (crash sobre E5 anterior ao #1770, *depois* de pagar o LLM; e gate cuja whitelist saía dos próprios paths que ia testar, logo inalcançável), 2 P0 achados pela sessão da l90 (procedência `goal_declarado` mentida sobre doutrina do `scoring.json`; `limiar_canonico` publicado sobre medida que o produtor suprimiu), 3 P1 · **delta de golden `↓`** (`exposicao_cambial.limiar` 1000 → null) · painel de 2026-08-28 fecha **COM RESSALVA**: 6 residuais com dono **e rota**, + 5 achados novos (N1 `operador="<="` da alocação RF; N2 gate de versão não cobre `config/prompts/*.yaml`) |
| [[A40.l92]] | A trilha de progresso ignora a polaridade do operador e enche conforme a métrica piora | P0 | — | aberta 2026-08-28 pelo painel de fecho da [[A40.l89]] · **pré-existente, agravada**: a barra agora visualiza `limiar_canonico` com procedência, não alvo do LLM · medido: `taxa_endividamento` 45% contra `≤ 20%` ⇒ **trilha 100% cheia numa violação de 25pp** · diagnóstico é de **contrato**, não CSS — `operador` existe no `KpiTarget` e não viaja no wire, e a regex do front come o glifo · **não muta E5** ⇒ fora da janela de rebaseline · co-donos `product-designer` + `data-engineer` |
| [[A40.l90]] | A superfície determinística de risco tem quatro regras hard-coded e não lê o catálogo canônico de limiar | P0 | ✅ **#1812 → #1813 → #1814 → #1815 → #1816** | aberta 2026-08-26 pela **U1** · PV9-06 · **FECHADA COM RESSALVA 2026-08-29** · dois ataques medidos antes de executar (#1766/#1767, #1810) refutaram 4 afirmações do próprio atacante e reescreveram o §Escopo, que era inexecutável em 3 pontos e falso num 4º · [[ADR-419]] `Proposto` (#1812) + emenda [[ADR-191]] §D6 (#1815, corrige a **contagem** do Aceite: eram 3 consumidores, não 2) · gatilho vira registro tipado com `kpi_key`, invariante **por chave** (a forma existencial passava com o defeito inteiro presente) + gate estático de cobertura, ambos provados por mutação · concentração ganha regra nos degraus 75/50 **reusados** da red-line, pareados por teste no gatilho E na severidade · `trs_target_pct` cai com a regra que o lia · **ressalva:** gradação da reserva segue no §Deferimento (dono `financial-planner`; a [[ADR-367]] fica fora porque seu §D3 é frontend, e só o lado do pipeline criaria contradição cross-superfície) |
| [[A40.l91]] | A meta de independência é composta pela fórmula bruta e consumida nos slots líquidos | P0 | ✅ **#1753** | aberta 2026-08-26 pela **U1** · PV9-16 · **cabeça da janela de rebaseline** da onda 2 · muta E5 · **medida 2026-08-27: derivada** (resíduo R$ 0,00 contra a identidade bruta no `derived_json`; nenhum dos 5 inputs a declara) · **a pergunta binária da lane era estreita**: descontar a renda passiva OBSERVADA seria dupla-contagem — o `patrimonio_gerador` que a produz é **93,10%** de `investivel_efetivo`, e os 4,68 pp de ganho viriam inteiros de contar o mesmo ativo duas vezes · **o que decide é o par numerador↔meta, não a fórmula**, e o numerador é governado por `imoveis_no_if` · com o toggle `true` (o run da U1) o número publicado está **certo**; com `false` — o **default** desde a [[ADR-223]], 6 dos 7 workspaces medidos e `set_at` nulo em 7/7 — cat_2 sai do numerador e a meta não se move: meta **+9,56%**, progresso **−1,74 pp**, gap **×1,119** · imagem espelhada do anti-dupla-contagem da [[ADR-142]], que existia só na `description` de um schema **candidato** · [[ADR-418]]: uma base só (`compor_meta_if`), termo **ternário** (`None` não-medi ≠ `0.0` medi-e-não-há), base publicada em dados (`if_meta_base`/`if_meta_bruta`, enum `BaseDaMetaIF`) · `CV5` deixa de ser tautologia (afirmava identidade entre dois campos em que o 2º deriva do 1º — `info`/`passed` em todo run, sem poder falhar) · **3 vazamentos da base única achados na revisão do próprio fix**: o cone Monte Carlo mirava a bruta, `if_pct` devolvia 0% com meta zerada (contradizendo gap e prazo) e toggle ausente virava zero medido · **delta de golden `=`** — o dogfood está em `imoveis_no_if = true`, o rebaseline do snapshot é de forma (2 chaves), nenhum valor muda · **co-design `financial-planner` (autorizado pelo dono) achou um bloqueante no próprio fix**: o predicado lia o toggle e não a exclusão real, e o balde `alugueis` é residual (carrega carnê-leão PF→PF, inclusive renda de trabalho autônomo) — família SEM imóvel de renda veria a meta cair, **invertendo** o sinal do defeito para superdeclaração, que a [[ADR-223]] nomeia como o erro mais caro. Invisível ao CI: o dogfood está no regime onde o ramo é inerte · 4 correções com teste (gate de exclusão real · líquido em vez de bruto · `if_pct = null` em vez de 100% na meta clampada · piso lendo a mesma base) · a [[ADR-142]] §Decisão **já decidia** isso desde 2026-04-27 — a [[ADR-418]] liga o produtor que faltava, não decide metodologia nova · **`shipped` 2026-08-27** |
| [[A40.l93]] | Alvo publicado cujo observado o parecer nunca lê, e o comparador que isso mascarava | P0 | ✅ **#1796** | aberta 2026-08-28 para executar o §Fecho da [[A40.l89]], que fechou **com ressalva** · **quatro ondas**: (1) `check_prompt_version_bumped` passa a cobrir `config/prompts/*.yaml` por lista **declarada** com igualdade de conjunto — o critério é "a `version` entra em chave de cache que não hasheia o prompt", não o diretório; junto, o gate deixa de **falhar aberto** com ref irresolvível (N2) · (2) folha `derived.renda_fixa_atual_pct` em ponto fixo (R2) **e** `alocacao_renda_fixa` vira **órfã por decisão de domínio** (N1) — o `financial-planner` recusou a rota `|atual−alvo|` contra 2pp que o prompt da lane propunha, porque `SEVERITY_ALINHADO_MAX_PP` é piso de *acionabilidade* ([[ADR-400]]) e a [[ADR-141]] §item 10 difere a calibração relativa; `unidade`/`operador` viram enum; `limiar` sai do classificador monetário · (3) `diagnostico_confianca` no enum de `get_e5_section` + manifest 2.6.0 + backfill de 2.4.0/2.5.0 (R1) · (4) gate de path legível + **morte** da `_RESOLUCAO_DIVIDA_DECLARADA` · **delta de golden `=`** — re-medido, corrige o `↓` que o painel previa: o dogfood não tem `goals.alocacao_alvo`, o ramo é **inerte** no workspace medido (padrão da [[A40.l91]]); o único rebaseline de valor é de **representação** (4 `limiar` de cents int para string) · medido também: o parecer é chamada **single-shot** (`LLMService.call` não tem `tools`), logo a whitelist é resolver server-side e a Onda 3 não amplia superfície do modelo · 7 follow-ups com dono · **shipped 2026-08-28** |
| [[A40.l94]] | Folga mensal reclassifica gasto pontual realizado como sobra recuperável | P0 | ✅ **#1828** | aberta 2026-08-29 do `RR6-01` da rodada unificada **U2** · identidade fechada ao centavo: `folga_mensal × 12 == poupança 12m + pontuais 12m`, e os dois percentuais de "quanto sobra" dividem o **mesmo** denominador divergindo em **19,4 pp** — a diferença é exatamente `total_pontuais_janela` · **alcança o usuário**: quem dimensiona aporte pela folga dimensiona 27% acima do que a poupança sustenta, e a maior das duas sobras é a que prescreve · ~~§Sequência: consertar a folga sozinha move o número para outro valor errado~~ **trava DISSOLVIDA em 2026-08-29 (#1828 `05561dc0` · [[ADR-422]] D1)**: a folga deixou de ler pontuais, então contaminar a base não pode mais movê-la — e no dogfood o aporte estava **fora** da janela (`janela_12m.despesas_por_categoria.aporte_investimento == 0,0`), logo nunca a moveu naquele corpus · a base segue contaminada e é da [[A40.l98]] (aberta 2026-08-30 do `LC6-05`), que herdou os 3 itens deferidos · entrega **parcial por desenho**: `teto_sugerido` extinto, `equivalente_meses_aporte` → `equivalente_meses_poupanca` · **entra na cláusula de reinício do contador** (muta E5) |
| [[A40.l95]] | Numerador da concentração imobiliária inclui bem que o motor declara não-gerador | P0 | in_progress | aberta 2026-08-29 do `RR6-02` da **U2**; **medida e re-enunciada** no mesmo dia ([[ADR-420]] `Proposto`, #1826) · o numerador soma a nu-propriedade que `real_estate.excluded_properties[1]` exclui com o motivo literal "não gera caixa nem está disponível para venda livre"; sem ela o KPI vai de 50,62% para **49,08%**, abaixo do limiar 50,0 com operador `<`, e **58,9% dela decide o cruzamento** · desarma ponto urgente, risco Alta do parecer, alerta de real estate e KPI vermelho — **o score NÃO cai** (7,438 → 7,463, arredonda 7,4 nos dois; a redação anterior desta linha prometia queda de componente com peso 12,5%) · **o corte não é `geradores`:** o discriminador é rebalanceabilidade, `especulacao` fica e `uso_pessoal` sai · **a [[A40.l80]] NÃO é dona** — medido no ataque: o §Escopo dela nomeia denominador, e trocar o numerador reabriria o ramo que a [[ADR-412]] §E5 fechou; um item volta para lá (declarar o numerador, o C14 dela deslocado um campo) · ⚠️ **bloqueada por fixture:** nenhum golden do repo tem `imoveis_geradores > 0` · **entra na cláusula de reinício** (muta E5) |
| [[A40.l96]] | Tabela de maiores ativos atribui titular a valor que o sistema declara órfão | P0 | in_progress · PR1 [#1823](https://github.com/davidrobert/mathoms/pull/1823) | aberta 2026-08-29 do `RR6-03` da **U2** · a tabela preenche titular em **15/15** linhas enquanto o mesmo relatório publica que ~metade da carteira financeira não tem titularidade; a refutação óbvia ("as órfãs não estão entre as maiores") é **aritmeticamente impossível** — as 15 linhas somam 92,7% da base, e a fatia órfã não cabe no residual por 2,4× · ~~⚠️ direção não determinada~~ · **MEDIDA 2026-08-29 (PR1, zero produção)** e por uma **terceira via**: as duas hipóteses caem — o roll-up está certo ([[ADR-412]] §D3) e o Top 15 lê `fonte: irpf_bens`, sendo o **extrato** o lado sem titular (`itau`/`rico` emitem `titular: None`) · **o sinal existe e morre entre o E1 e o E4**: o artefato E1 `members` traz `banco_membro` (11 instituições) e `contas[]` (18) — incluindo as 3 órfãs — mas o E4 lê o `family_members.json` materializado de `bank_accounts`, tabela com **0 rows no banco inteiro** · somam-se `AccountResolver` marcando `ambiguous` por **cardinalidade de contas** e não por divergência de membro (`itau`/`rico` têm 2 contas cada, **ambas do mesmo membro**), e a saída do resolver entrando **sem** canonicalização ([[ADR-243]]) · **contrafactual sobre os 8 subconjuntos** (corrigido no closeout 2026-08-29 — a redação anterior, "qualquer subconjunto próprio deixa o número idêntico", era **falsa**): 5 dos 6 próprios não-vazios são inertes, mas **`{D1,D3}` move para 46,25% órfão / ~33,3% publicado — e segue acima do `piso_pct: 1.0`**, logo parece progresso com as 8 superfícies acesas; só `{D1,D2,D3}` leva a 0,13% / ~0,10% ⇒ risco Alta, `prescricao_realocacao_suprimida`, confiança *"insuficiente"* e a ação P1 *"reconciliar a titularidade"* (inexecutável pela família) são **espúrios** — 8 superfícies · **o argumento aritmético do achado cai como mecanismo** (as duas porcentagens têm denominadores distintos), a conclusão sobrevive por outra rota · **entra na cláusula de reinício** — muta E4 e E5 · PR2 exige co-design `data-engineer` + `financial-planner` antes da ADR |
| [[A40.l97]] | Índices perdidos por `copy_from`: 3 UNIQUE derrubaram invariante e o gate de drift era cego a índice | P0 | in_progress | aberta 2026-08-30 como **colateral** da auditoria da [[ADR-235]] na [[A40.l95]] · `batch_alter_table(copy_from=)` faz drop+recreate em SQLite e o snapshot nunca declara `Index`: **38 índices** do model ausentes no DB migrado, em 13 migrations, todas com o padrão · 3 UNIQUE derrubavam invariante, entre eles `uq_report_publications_active`, cujo read-path usa `scalar_one_or_none()` ⇒ `MultipleResultsFound` no predicado de mês fechado ([[ADR-187]]) · **Postgres nunca perdeu** (`DefaultImpl` não recria) — é SQLite-only, logo dev/dogfood/suíte · reparo dos 3 UNIQUE e extensão do gate **entregues** ([[ADR-423]] `Proposto`); falta **decidir** se os ~35 não-unique ainda são desejados · **não** entra na cláusula de reinício (não muta E3/E5) |
| [[A40.l98]] | Base de gasto pontual tem três produtores com filtros disjuntos, e o que prescreve é o que menos filtra | P1 | open | aberta 2026-08-30 no closeout da [[A40.l94]], que a nomeou como dona dos 3 itens deferidos e apontava para uma lane **inexistente** · do `LC6-05` da **U2**, com `LC6-06`/`LC6-07` roteados junto · **re-medição:** o registro dizia "uma aplicação, dois pontos" e são **três** produtores — enricher (`{aporte_investimento}`), a **lista** do card (`consumo_pontuais.py`, que aplica `InternalTransferDetector`) e o **KPI** (`_collect_candidates`, que não aplica nenhum dos dois): lista e KPI do mesmo card filtram coisas diferentes, e o que prescreve é o que menos filtra · no dogfood **57,5%** da base da janela é movimentação patrimonial em `nao_identificado` (R$ 194.886,65 para outro banco do titular + R$ 32.000 em conversões Wise) · **P1 e não P0** porque a [[ADR-422]] tirou a contaminação das prescrições **determinísticas** (folga, teto) — mas o parecer segue recebendo `total_pontuais` no exec context e emitindo risco com ele · carrega a regra de domínio *"`nao_identificado` fora de numerador que prescreve"*, decidida em co-design e existente **só em doc** (aqui e na [[A40.l94]] §Deferimento), **nunca em código** |
| [[A40.l99]] | Cinco ADRs em `Proposto` com lane fechada declaram decisão que não está em vigor | P3 | open | aberta 2026-08-30 no closeout da [[A40.l94]] · a proxy *"lane `shipped` ⇒ é só flipar a ADR"* foi verificada decisão a decisão contra o código e é **falsa em 5 de 6** · [[ADR-368]] passou e já flipou; [[ADR-362]] (D2 normativa violada no colofão e no `/health`), [[ADR-363]] (Resource do OTel sem `service.version`), [[ADR-385]] (D7 diz que não persiste e o script persiste), [[ADR-389]] (`compute_irrf_mensal` ainda hardcoded) e [[ADR-419]] (invariante não lê o artefato E5) **não** · **não é bookkeeping**: 3 das 5 têm cláusula normativa violada em superfície de cliente ou gate ausente |
| [[A40.l100]] | Cartão "NECESSÁRIO" publica a renda-alvo, não o aporte que o motor calcula | P0 | ✅ **#1845** | aberta 2026-08-30 do `RR7-01` da rodada unificada **U3** · ~~o PMT correto já existe e aparece em 5 superfícies~~ **premissa falsa, medida na entrega**: o único produtor de PMT do repo é `goal_service.compute_if_derived` (agregado Goal, rota `/plano`); as superfícies do relatório publicam o aporte **declarado** (`aporte_mensal_usado`, `cenarios_conjuge.premissas.aporte_base`), zerado no dogfood, e o `IFProjector` resolve **prazo** a partir do aporte ([[ADR-373]]), nunca o inverso — nem computável ali · o núcleo segura e fica **mais forte**: as 3 superfícies que usam o rótulo (`/plano/meta-if`, wizard, `IFHeroCard`) leem o PMT real, então o cartão era mesmo o único fora da cadeia · ⚠️ o critério de aceite proposto pela lente **não discrimina** — neste workspace o goal declarado e o PMT coincidem, então "batem" passa nas duas implementações; ~~exige fixture em que difiram~~ **entregue** com três valores distintos (renda-alvo `333.333` · declarado `20.000` · PMT `42.111`) e contrafactual verificado **em subconjuntos** · o bloco **saiu** em vez de ser rerrotulado: o `S7Stat` já publica o mesmo número com o nome certo, e a presença incondicional dele tornava **inalcançável** o estado honesto "Meta de aporte não configurada" · **não muta E5** (só frontend) |
| [[A40.l101]] | Conserto da folga deixou `equivalente_meses_poupanca` auto-referente | P1 | ✅ **#1848** | aberta 2026-08-30 do `RR7-02` da **U3** · triagem **REGRESSÃO-DE-CONSERTO** · **mecanismo: guard TRANSPLANTADO** — o `else 0.0` vinha da fórmula anterior, cujo denominador era a meta DECLARADA (`≥ 0`, `0` == "não configurou"); sobre a `folga_mensal`, quantidade MEDIDA que vai a negativo, `≤ 0` passou a significar "a família não poupou nada" e `0,0` é o MENOR valor da régua — **o pior mundo publicava o melhor número**, e a prosa do E5 o AFIRMAVA · ~~o numerador é 45,4% do denominador~~ os 45,37% são do **subtraendo**; do denominador é 33,79% · ~~subconjunto~~ **5 escapes medidos**, 2 deles achados novos roteados à [[A40.l98]] · entrega: [[ADR-422]] §Emenda 2026-08-30 (`null` + `motivo_supressao`, `folga_pct` pelo mesmo guard, denominador = folga publicada, prosa com ramo próprio, `manifest_version` 2.9.0) · **9 gates reprovam pré-fix** e o mutante do ramo `folga < 0` (que sobrevivia à suíte inteira, 7931 passed) reprova em 3 · polo **deferido com dono** ([[A40.l15]]): piso de materialidade rejeitado por medição |
| [[A40.l102]] | Superfície do gasto pontual: dedup do par publicado sob promessa de unicidade + o que cada superfície declara excluir | P2 | open | aberta 2026-08-30 no **split da [[A40.l98]]** (co-design `financial-planner` + `data-engineer` + `senior-cto`), cortado pelo eixo **muta E5 × não muta** — esta **não** muta, logo não disputa a janela do contador · **`LC6-07` re-enunciado:** o registro dizia "dois pares, mesma data" e as duas metades são falsas (as datas diferem em 1 dia, e é **um** par — o segundo candidato são beneficiários distintos) · ⚠️ a primeira medição foi sobre **código morto** (`deduplicate_transactions`, cujo único chamador `reconcile_account` não tem chamador; `tests/test_e3_dedup.py` a mantinha verde) — no caminho vivo o par falha em **cinco** cláusulas, em dois mecanismos com cegueiras complementares · **measure-first, sem enforce**: super-dedup destrói row e órfã override, e não há discriminante positivo (`saldo_apos` emitido por 0 dos 13 parsers) · herda de [[A40.l15]] a obrigação de **remover o `CARDS_DA_L15`** — esquecer deixa a guarda cega para sempre |
| [[A40.l103]] | O recorte da baseline da capa media a nav — e era o único gate sobre os números-manchete | P2 | `in_progress` | aberta 2026-08-30 na investigação da drift de `cover-{light,dark}` em `main` (fechada pela [[A40.l100]] · **#1850**) · o `clip` do teste `cover (hero)` era **page-level** e a nav é `sticky; top:0`, então a "baseline da capa" media nav + `sidebar-toc` + conteúdo pós-header — o `<header data-report-cover>` era ~⅓ da imagem, e o chip `2.5` da [[A40.l88]] a reprovou com bbox inteiramente **dentro da nav** · **2 medições que ninguém tinha**: (a) o `<section id="sumario-executivo">` (Patrimônio Líquido, Investível, Reserva, Taxa de Poupança, IF, Score) **não tem gate nenhum** — fora de `STRATEGIC_SECTIONS`, sem `data-report-section` e ausente do inventário da [[ADR-370]] —, coberto só pelo acidente do recorte, então estreitar sem repor derrubaria o único gate sobre os números-manchete; (b) o render é **determinístico** (2 dispatch do mesmo SHA, 28/28 byte-idênticas), o que **refuta** a hipótese de instrumento bi-estável e o comentário do helper que afirma ~1-2% de não-determinismo de canvas · reproduzido à mão: `S-parecer-retido-dark` tem 5 versões e **2 hashes de pixel** alternando, cada transição acusando 9,58% que o realinhamento `dy=±1` zera — a métrica de razão amplifica reflow de 1px em imagem curta · **6 achados roteados** com motivo de não caberem: gate por paths-filter (custo medido **zero**, mas muda o veredito do `all-green` e exige emenda à [[ADR-210]] §Camada 1), varredura periódica (**não construir** — já existe em `nightly.yml`, morta por waiver datado do dono; é o item 1.4 do [[PLAN-ci-trust]]), buraco do inventário, métrica de razão, ledger de proveniência (**não** copiar `dev/golden_diff.py`: o pilar do commit isolado **inverte** em binário) e encolhimento do ativo |
| [[A40.l104]] | A trilha sticky promete 20 alvos e entrega 10 em 1280px, 0 no telefone | P1 | ✅ **#1860** | aberta 2026-08-30 como achado colateral da drift de baseline da capa (#1850, que só rebaselina) · **pré-existente e independente** — não é regressão da [[A40.l88]], o chip `2.5` só piorou ~48px · a trilha é a navegação **primária por decisão declarada** (`useReportTocOpen` tem `DEFAULT_OPEN=false` e o docstring diz que o ToC é opt-in), e some com `S10`, `S_parecer` e `plano_de_acao` em 1280px · medido: conteúdo da trilha é **constante em 873px** (data-independente, vem do YAML), e **não existe largura < 1602px em que os 20 caibam** · o máximo é **18, nunca 20** — `V0` e `perfil` não têm `num` e renderizam como alvos de 12px **em branco** em toda largura · **alargar 960→1024 REMOVE 5 alvos** (o sidebar do AppShell come 224px em `lg:`) · em **≤454px a trilha tem 0px de caixa**, a página não rola horizontal e não há índice alternativo (`aside` é `lg:`, botão é `md:`) ⇒ candidato a **WCAG 1.4.10 Reflow** · teclado alcança os 20 e trackpad rola, mas **roda vertical de mouse não rola a trilha** e `scrollbarWidth:none` apaga a única pista · colateral: entre **768–1023px** o botão "Mostrar índice" é visível, clicável e **no-op** (aside monta com largura 0) · `overflow-horizontal` é cego por **dois** motivos (escopo fora do `<article>` + `dentroDeRolavel` isenta rolável na tela) · **remédio não decidido** — medição já elimina `density` mais agressivo e colapso de rótulo de grupo · ⚠️ **rebaixada P1→P2 em 2026-08-30**: a premissa mais forte era **falsa** — `FloatingNav` está montado e serve um FAB de índice em ≤1023px que abre `<dialog>` **modal** com os **20** alvos (medido a 320/390/768/1000/1023, Esc fecha), e ≥1024px o toggle→`aside` funciona ⇒ **não existe largura sem rota**, cai o enquadramento 1.4.10 e cai a análise de "segunda porta" · **sobrevivem**: a trilha não se declara parcial (10/20 em 1280), os 2 chips sem tinta, **2.4.7** (20 alvos focáveis numa caixa de 0px abaixo de 455px) e o no-op 768–1023 — que fica **mais nítido**, pois ali o FAB entrega e o toggle mente, e o docstring do `FloatingNav` diz que a divisão pretendida é `lg` ⇒ desalinhamento de 1 linha · **entregue `a18c608e`**: a implementação achou **3 defeitos que o achado não via**, e o maior reenquadra a lane — o **scroll-spy da faixa nunca funcionou** (12 pontos do documento a 1600px, zero chips `data-active`), e como o compacto só expande o rótulo do ATIVO, a faixa era 18 números sem palavra alguma, sempre; o índice tinha o mesmo defeito para quem VOLTA, porque o estado é persistido (controle: abrir com `toc-open=true` mata o spy dele igual) · também: eleição lia só quem MUDOU no disparo (faixa dizia S2, índice S8) e `scrollIntoView` em container `sticky` rola o DOCUMENTO (`scrollTo(1500)` → 7px, quebrando o FAB "voltar ao topo") · **o gate quase nasceu decorativo**: escrito sem `@critical`, não rodaria em PR nenhum (render gate filtra por tag; job E2E é opt-in por label), e "faixa e índice concordam" passava por coincidência até a banda virar constante compartilhada |

> **Contador vs. disco — re-medido por SCRIPT em 2026-08-12** (não à mão: a contagem
> manual errou 3 vezes no mesmo dia, porque a sprint abriu 12 lanes em ~20h).
> `ls docs/sprint/A40/lanes/*.md` dá **59**; esta tabela lista **59** — sincronizada
> em 2026-08-12 (#1415). As **l47/l48/l49** (achados da r4, #1411) entraram na
> passada do fechamento dos follow-ups, junto com l56–l59; as **6 restantes**
> (**l38** caixa canônico #1391 · **l39** posição corrente/fiscal · **l40**
> identidade institucional CNPJ raiz · **l41** frescor cross-pool · **l42** ·
> **l44** janela declarada #1397/#1398) entraram no #1415, com prioridade e status
> lidos do frontmatter de cada arquivo. A **l45** já havia entrado junto com as
> lanes que os follow-ups dela originaram (l53–l55). A **l60** entrou nesta
> passada, já sincronizada.

> **Re-medição 2026-08-13:** `ls docs/sprint/A40/lanes/*.md` dá **61** e esta
> tabela lista **61**. As novas l61/l62 são pré-requisitos do mesmo destino da
> l35, não expansão temática. DAG: [[A40.l61]] → [[A40.l62]] → [[A40.l35]].
>
> **Quem fechar a sprint tem de resolver isto:** lane fora desta tabela é invisível
> ao **encerramento administrativo** (flip `sprint_status: done` + contador de
> lanes). A direção lane→tabela vira gate na [[A40.l59]].

> **Re-medição 2026-08-24 (closeout da [[A40.l59]]):** disco **76**, tabela **76**.
> A [[A40.l77]] (P0, aberta pelo #1643 no mesmo dia) estava fora — só numa tabela
> de roteamento do §Inventário do r7 —, e o cabeçalho declarava `75 · 75`. Duas
> notas sobre o dano, medidas agora e que **corrigem a redação acima**: (a) a lane
> **não** ficou invisível ao pickup — `SPRINT_CURRENT.md` e `dev/lane_pickup.py` a
> resolvem pelo frontmatter, inclusive detectando ocupação; o dano é mesmo só o
> encerramento administrativo; (b) o `check_lane_counter` da skill `lane-closeout`
> **não pegou** — o `LANE_COUNT_RE` exige `## Lanes (N)` e este cabeçalho tem
> texto dentro dos parênteses, então `match is None` e o check **falha aberto**.
> Corrigido no mesmo PR da lane.
>
> *Correção de atribuição, 2026-08-12 (#1415):* a redação anterior dizia que "o
> §Gate de saída lê esta tabela" — **não lê**. O §Gate de saída é enunciado sobre
> as 6 classes e a propriedade das superfícies; amarrá-lo a esta tabela o tornaria
> satisfazível por higiene de doc, que é o modo de falha que a própria sprint
> persegue. Re-medir com:
>
> ```
> ls docs/sprint/A40/lanes/*.md | wc -l
> rg -No '^\| \[\[A40\.l[0-9]+\]\]' docs/sprint/A40/_README.md | sort -u | wc -l
> ```
>
> **Re-medição 2026-08-28 (abertura da [[A40.l93]]):** disco **92**, tabela **92**.
> O cabeçalho declarava `91 · 90` e **a segunda metade estava errada em `origin/main`**:
> a tabela já listava **91** ids únicos. Alguém acrescentou linha sem mexer no cabeçalho,
> e nada pega isso — o `check_lane_counter` da skill `lane-closeout` compara o número
> declarado contra o **disco**, não contra a própria tabela, então subdeclarar a tabela
> passa calado. Corrigido aqui para `92 · 92`; a falha do check fica registrada e não é
> desta lane resolver. Os comandos de re-medição abaixo continuam válidos.

> *O `sort -u` não é enfeite (corrigido no #1415):* este arquivo tem **duas**
> tabelas cuja linha começa com `| [[A40.lN]]` — esta e a das lanes da Onda 1 já em
> `main` (§Onda 1: l1, l3, l4). Sem ele o comando devolvia **3 a mais** que o número
> de lanes, e não batia com o que esta nota afirmava. Para saber **quais** faltam,
> em vez do total — que é a pergunta acionável:
>
> ```
> comm -23 <(rg -No '^id: A40\.l[0-9]+' docs/sprint/A40/lanes/*.md | sed 's/.*A40\.//' | sort -u) \
>          <(rg -No '^\| \[\[A40\.l[0-9]+\]\]' docs/sprint/A40/_README.md | sed 's/.*A40\.//;s/\]\]//' | sort -u)
> ```
>
> **Corolário de processo — 8 colisões de id numa sessão** (l38→l41→l43 na [[A40.l43]];
> l46→l47→l50→l51 numa; as lanes de follow-up da [[A40.l45]] nasceram l50–l52 e
> aterrissaram l53–l55; e as desta passada nasceram l50/l51, foram para l54/l55 e
> aterrissaram **l56–l59** — duas colisões seguidas, a segunda já com o teto medido
> em `origin/main`, porque o #1414 mergeou no intervalo entre a medição e o push).
> "Próximo id livre" medido na **tabela** mente enquanto ela estiver defasada; e PR
> aberto não reserva id. Meça no **disco** e cruze com títulos **e arquivos** de PR
> aberto, imediatamente antes do push:
>
> ```
> rg -N '^id: A40\.l' docs/sprint/A40/lanes/*.md | sed 's/.*A40\.l//' | sort -n | tail -1
> gh pr list --state open --limit 40 --json title -q '.[].title' | rg -o 'A40\.l[0-9]+'
> ```

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
> sentidos em ~10 linhas. ~~**Continua não roteado** — candidato segue [[A40.l23]].~~
> **Atualizado 2026-08-09: a [[A40.l23]] shipou (#1334) e NÃO absorveu isto** — os
> quatro gates dela são outros, e ela declara "nada sobra do escopo". Estado real:
> o sentido `blocked` **com todas as deps `shipped`** existe desde o #1343 como
> check *advisory* (`check_stale_blocked` em
> `.claude/skills/lane-closeout/references/check_closure.py`), **não como gate**.
> Falta o sentido inverso e a promoção a gate. **Sem dono.**

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
`information-architect`. ~~Candidato natural a hospedar: [[A40.l23]], que já é a
lane de gate de referência de doc e já é candidata a absorver o gate de
autorreferência da §Pendência nº 12.~~ **Não roteado nesta passada.**

> **Atualizado 2026-08-09.** A [[A40.l23]] shipou em #1334 com **quatro** gates —
> nenhum é este — e declara "nada sobra do escopo da lane". O candidato natural
> deixou de existir: **este item está sem dono**. Metade do predicado (`blocked`
> com todas as deps `shipped`) roda hoje como check advisory do `lane-closeout`
> (#1343); o que falta é o sentido inverso **e** virar gate. A cláusula de amarra
> parcial segue exigindo campo novo no schema — gatilho `information-architect`.

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
[[A40.l8]], [[A40.l12]], [[A40.l61]], [[A40.l62]], [[A40.l35]]). A l2 só abre depois da l1: sem detector, o fix fecha
verde sem prova. A l5 vem **antes** das lanes de correção individual de contrato —
senão cada uma é fixada uma vez e volta a divergir.

> **Estado da Onda 2 em 2026-08-08.** [[A40.l5]] e [[A40.l7]] shipparam **parcial**
> e seguem `in_progress` — cada uma parou num bloqueio **medido**, escrito na
> própria lane:
>
> - **[[A40.l5]] — `845a4041` (#1336).** Fechou as **2** leituras órfãs reais
>   (regra de reserva morta em produção + tabela de dívidas publicando vazio).
>   Duas descobertas que a sprint precisa herdar: o inventário da lane estava
>   **vencido** (ver KR-A abaixo) e o **codegen especificado não é construível**
>   — 10 dos 35 blocos do schema E5 são `object` sem `properties`, inclusive os
>   3 onde os achados moram. Pré-requisito antes de retomar: tipar esses blocos
>   (contrato entre stages ⇒ gatilho `data-engineer`).
>
> **Co-design da [[A40.l5]] rodou em 2026-08-10** (sem código; §Co-design da
> lane). Três correções que a sprint herda: (1) "10 blocos opacos" erra nos
> dois sentidos — a superfície real é **11**, porque há 4 **arrays sem
> `items`** que desligam o `tsc` igual a `Record<string, unknown>`; (2) o
> **snapshot de dogfood não serve como fonte de tipo escalar** (`_normalize`
> converte float não-monetário em string quantizada), então tipar por ele
> criaria a mesma classe da lane na dimensão *tipo*; (3) o gate `schema × TS`
> precisa de uma **terceira perna** — `schema × produtor`, via golden de
> execução em `strict` —, senão os dois lados ficam sincronizados e errados.
> Ordem de trabalho PR0–PR5 registrada na lane, com o flip `warn → strict`
> isolado em PR próprio (blast radius = run de cliente).
>
> **PR0 ✅ #1363 · PR1 ✅ #1371 (2026-08-11).** O PR1 fechou os **4 arrays sem
> `items`** (4 → 0) e levou os opacos de 9 → **7**, com cada `items` vindo do
> **produtor** (o PR0 mediu que 3 dos 4 vêm vazios no corpus — tipar por
> observação inventaria contrato). O achado maior foi outro: **o golden de
> execução nunca validou schema** — `pipeline.json` era `{}`, `enabled` caía em
> `False` e `validate_dict` short-circuitava para `True`. O `assert` era verde
> vacuoso desde sempre, e só apareceu porque apertar o schema **não derrubava
> teste nenhum**. Com isso a lane ganhou a **terceira perna do gate**
> (`schema × produtor`) que o co-design exigia.
> - **[[A40.l7]] — `ed7b1dc4` (#1337).** Fechou a âncora de nav sem alvo
>   (RV3-04) com gate bidirecional dentro do `codegen_report_layout`. Decisão de
>   produto tomada: **remover a entrada de nav**, não ligar `S_PROTECAO` — ligar
>   publicaria "Nenhuma apólice cadastrada" para todo cliente, inclusive quem
>   cadastrou. Seguem abertos: S9 empty state (⛔ sem produtor de
>   `protection_bundle`), rótulo do disclosure, retítulo da S9 e o `title`
>   derivado do `titleMap`.

> **✅ [[A40.l7]] `shipped` em 2026-08-11 — #1375.** Fecha o RV3-28 na metade de
> **nome**: a S8 passa de *"Previdência — PGBL e Fiscalidade"* para **"Carga
> Tributária PJ — Regime e Base Dedutível"**, com cascata em 6 pontos (YAML,
> prompt do parágrafo da seção, fallback determinístico, 2 cross-links, docstring).
> **Não moveu o card de PGBL** — a S8 já hospeda o `PgblBlock`, e mover poria duas
> bases contraditórias a 200px de distância. Grep de regressão: 0 ocorrências do
> título antigo. **S9 → [[A40.l35]]** e **hospedagem do RV3-28 → [[A40.l34]]**.

> **Estado da Onda 2 em 2026-08-10** (o snapshot acima é datado — **não o
> reescreva**). Segunda parcial da [[A40.l7]]; a [[A40.l5]] não avançou nesta
> data além do co-design (ver o §Deferimento datado dela).
>
> - **[[A40.l7]] — #1355.** Fechou os itens 2 e 4: `ReportSection` perdeu o
>   prop `title` e o `id` virou união literal do codegen, então **as duas
>   formas do defeito são erro de compilação** — gate por construção, não por
>   teste. Retítulo da S9 entrou junto, com cascata nos dois prompts. Lane
>   segue `in_progress` (só o S9 empty state resta, e o ⛔ dele é intocado).
>   **Duas correções que a sprint herda:** as divergências YAML↔componente
>   eram **6**, não 4; e a premissa *"no PDF o rótulo fica ao lado das linhas
>   que o desmentem"* é **falsa** — `SParecer.print.css` esconde o
>   `<summary>` no print, então o dano do RV3-15 é na tela. O rótulo que de
>   fato mentia no PDF era outro (`Mostrando 5 de 8 riscos` acima de 8 linhas
>   impressas), e foi corrigido no mesmo PR.

> **Estado da Onda 2 em 2026-08-13 — split da proteção.** O co-design refutou a
> premissa de wiring simples: E5 não tem renda ativa líquida mensal nem situs EUA,
> e o adapter live quebraria a fotografia do Report. A sequência vigente é
> **[[A40.l61]] `in_progress` → [[A40.l62]] `blocked` → [[A40.l35]] `blocked`**.
> A l61 fecha o dano latente sem ligar a superfície; a l35 continua sendo o
> terminal que habilita a S9 e o contador de re-runs.

> **Estado da Onda 2 em 2026-08-14 — closeout da mitigação.** A [[A40.l61]]
> shippou no #1443 (`0a343302`), a [[A40.l62]] passou a `open` e a
> [[A40.l35]] permanece `blocked`. O DAG vigente é **l61 `shipped` → l62 `open`
> → l35 `blocked`**; a S9 continua desligada até o snapshot run-scoped.

> **Estado da Onda 2 em 2026-08-15 — snapshot na `main`.** A [[A40.l62]]
> shippou (#1471 fontes + #1474 snapshot, `5cc4a02f`). O DAG vigente é
> **l61 `shipped` → l62 `shipped` → l35 `in_progress` (#1476)**. A S9
> continua desligada até a l35 mergear; o GET já não consulta estado live.

> **Estado da Onda 2 em 2026-08-15 — S9 ligada.** A [[A40.l35]] shippou
> (#1476 · `549695b1`). DAG **l61/l62/l35 `shipped`**. A S9 consome o
> snapshot; empty total só sem insumo real. l2 + l34 + l35 estão terminais —
> o contador de 2 re-runs E0→E6 (o primeiro com LLM) pode iniciar.

> **Estado da Onda 2 em 2026-08-17 — a [[A40.l5]] fecha e a Onda 2 fica sem lane
> `in_progress`.** Correção de status, não entrega nova: a l5 ficou 3 dias
> `in_progress` depois de o **PR3 (#1450, o último a mergear)** fechar o plano
> PR0–PR4. `ship_pr: 1450`, `ship_date: 2026-08-14`. O PR5 nunca foi dela — é a
> [[A40.l58]], que por isso saiu de `blocked` para `open` no mesmo dia.
>
> **O termo "e existe gate" da KR-A foi verificado, não presumido — e o
> resultado é parcial.** `dev/check_view_model_contract.py` está no
> `.pre-commit-config.yaml` com `always_run: true`, sai `EXIT=0` em `main`, e
> **falha por mutação** com violações tipadas (`OPAQUE_READER`, ratchet de bloco
> opaco, schema citado inexistente) provadas em
> `tests/test_view_model_contract_gate.py`. A perna do `tsc` também é real:
> `frontend/src/generated/report-analysis.ts` existe.
>
> **⚠️ 2 das 5 fixtures do §Critério de aceite da l5 não têm artefato**
> (verificado em 2026-08-17 por busca em `dev/` + `tests/`): a **(2)** —
> renomear `cobertura_meses`→`meses_cobertura` só no consumidor, que
> *reproduz o RV3-09 exatamente* — e a **(3)** — allowlist com razão escrita
> (não há mecanismo de allowlist). O gate fecha a classe *"reader lê bloco
> opaco"*, que é a **precondição** da leitura órfã, não a leitura órfã em si.
>
> **Logo: a KR-A não é declarada fechada aqui.** O primeiro termo (órfãs → 0)
> fechou no #1336; o segundo tem gate real mas cobertura menor que a
> especificada. Fechar a KR citando "o gate existe" repetiria a classe que a
> própria KR-A denuncia — afirmação sem a medição que ela mesma exige.
> **Pendência do dono:** aceitar a cobertura atual e fechar a KR-A, ou rotear as
> 2 fixtures. Não vira lane nova por conta própria (§Triagem de fecho recusou
> lane catch-all).
>
> Toda a Onda 2 está terminal: **l2, l5, l7, l35, l61, l62 `shipped`**; l6, l8 e
> l12 seguem `planned` (liberação por-lane, decisão do dono).

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

> **[[A40.l30]] ✅ `shipped` 2026-08-07 — `5988c703` (#1262, PR3).** Drift de
> ancoragem + re-medição das 66 execuções + [[ADR-368]]. O parágrafo acima é o
> estado de 2026-08-03 e fica como registro. A amarra *"a l8 não mergeia sem o item
> 2 da l30"* está **cumprida** pelo lado da l30. Entrega não estava citada aqui até
> 2026-08-09.

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

> **Apêndice 2026-08-15.** A [[A40.l22]] `shipped`. A copy por código de
> ausência fechou no #1301 (`cc957413`) no mesmo 08-08; o `in_progress` ficou
> stale. A perna de PDF que este snapshot chamava de parcial fechou no #1287
> (`a5ad5eae`) — o `test.fixme` virou assert em `print-text.@critical.spec.ts`.
> Teste humano n=1 continua owner-gated. `dedupeBySemanticKey` volta para a
> [[A40.l10]].

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

> **[[A40.l23]] ✅ `shipped` 2026-08-08 — `058f190f` (#1334).** Quatro gates de
> integridade do grafo de doc, cada um nascendo verde sobre a vault viva e com
> prova de mutação: ADR-em-prosa resolve para arquivo (fecha a **classe** que a
> [[ADR-345]] fechou na instância) · aresta de frontmatter resolve · coerência
> `path ↔ sprint` · `former_ids`. **Nada sobra do escopo da lane** — o item
> "job `frontend-e2e` não gateia", roteado a ela em 2026-08-07, foi
> **explicitamente recusado** e re-roteado (ver §Inventário de follow-up).

**[[A40.l26]] também fica fora das ondas** (aberta 2026-08-03; **`shipped` em
2026-08-09 pelo #1339 · [[ADR-373]]** — o residual que ela não fechou foi
transferido para a [[A40.l25]] §Carga herdada, porque lane `shipped` some do
`SPRINT_CURRENT`): carregava o
residual determinístico que o #1158 abriu ao fechar o §Def. 5 — `_solve_prazo`
não implementa os ramos `aporte == 0, r > 0` e `r == 0, aporte > 0`, que
convergem (~35 anos no dogfood). É P2 e não P0 porque o custo é **informação
retida**, não falsa: o #1158 já trocou a sentinela por ausência. Toca
`if_projector.py`, disjunto da l25 (`if_monte_carlo.py`) — paralelas.

**[[A40.l32]] também fica fora das ondas** (promovida da [[A42]] em 2026-08-05;
**`shipped` em 2026-08-08 pelo #1335 · [[ADR-362]] · [[ADR-363]]**): proveniência
do executor — qual código computou este run. Instrumento, sem custo de API. O
#1335 fechou a lane **rodando a medição por mutação que ela própria exigia** (três
mutações, dois buracos achados), e entregou `dev/run_provenance.py` + cobertura em
`tests/dev/test_run_provenance.py`. Limite declarado na lane, não silenciado: o
join da [[ADR-371]] (§Limite a declarar, 2026-08-08).

**[[A40.l25]] fica fora das ondas, por definição** (aberta 2026-08-03): é o
residual das §Entregas fora de lane, cujo código já está em `main` ou em PR
aberta. Não compartilha arquivo com nenhuma onda — `if_monte_carlo.py` +
superfícies de exibição de S7 — e depende só de #1162 aterrissar. Sequenciá-la
dentro de uma onda seria acoplar sem motivo. Como l24: roda em paralelo.

> **Estado em 2026-08-08 — `6b1076e7` (#1338), parcial, segue `in_progress`.**
> Critério de corte declarado na lane: **entra o que corrige procedência, fica o
> que muda número exibido**. Entraram os itens 2 e 3 — séries do cone fora do
> catálogo de citação **por decisão** (antes era acidente de predicado) e
> `sigma_procedencia` no payload + schema E5, com `_SIGMA_POR_PERFIL` (dead
> code) deletado. **Nenhum número publicado mudou** — o snapshot do view-model
> mudou 1 linha, conferida. Segue aberto o item 1 (probabilidade em faixa de
> 5 pp + paridade Py↔TS), `sigma_anual` vindo de `premissas_economicas` e a
> verificação renderizada da S7: os três mudam valor impresso e por isso
> dependem da nota de recalibração re-especificada ([[ADR-369]]).

> **Estado em 2026-08-10 — #1356, segunda parcial, segue `in_progress`** (o
> snapshot acima é datado — **não o reescreva**). Entrou **a nota de
> recalibração**, que era o bloqueio comum de *todos* os itens restantes: com
> ela em `main`, o item 1, o `sigma_anual` e a §Carga herdada da [[A40.l26]]
> deixam de estar individualmente bloqueados. **Nenhum número publicado mudou**
> e o snapshot do view-model não moveu — a nota é injetada na resposta da API,
> não no artefato E5.
>
> **A sprint herda duas coisas.** (1) Os ajustes obrigatórios eram **quatro**,
> não os três que a lane enumerava: o `product-designer` mediu que o par
> ano-antigo→ano-novo é **confundido dado↔modelo** — entre dois relatórios
> mudam o modelo E os dados da família —, então a nota nunca afirma nada sobre
> a carteira do cliente, nem a negação disso. (2) O gatilho não pode ser lista
> de versão: virou **ledger declarado por major**, com gate que avermelha em
> bump sem entrada. Especificação vigente em [[ADR-360]] §Emenda 2026-08-10 —
> a de 2026-08-05 está vencida.

> **Estado em 2026-08-10 (2ª parcial do dia) — #1360.** (Citado como `#1359` até
> 2026-08-13; #1359 é PR da [[A40.l2]]. A lane já havia corrigido a proveniência
> em 2026-08-11 e este índice ficou com o número errado — sincronia de índice
> conta linha, não verdade.) Ao medir o item 1, saiu
> um defeito que a lane não conhecia: o **parágrafo do narrador e a legenda do
> cone discordavam sobre o mesmo campo** em 45 dos 50 001 desfechos possíveis
> ("2%" contra "3%", no mesmo relatório). Os dois declaravam paridade em
> docstring e nunca haviam sido comparados. Gate novo é **hook de pre-commit
> sem filtro de path** — o par vive nos dois stacks e nenhum filtro cobre as
> duas direções (precedente: §Decisão do dono da [[A40.l5]]).
>
> Fechada também uma **chave órfã criada pela 1ª parcial**: `sigma_procedencia`
> era emitido sem nenhum leitor, então a legenda afirmava a volatilidade como
> se fosse calibrada à carteira em 100% dos relatórios. É a classe da KR-A
> nascendo dentro de outra lane — vale como aviso à sprint.
>
> **Co-design `financial-planner` destravou o item 3:** agregação `Σwσ` com
> pesos do alvo declarado, porque é **limite superior demonstrável** e não
> estimativa. A alternativa de correlação zero foi refutada por medição —
> devolve ~11,3% para carteira agressiva, o mesmo número da constante. O
> defeito atual **não é o nível, é a invariância**: o intervalo real dos alvos
> declaráveis é ~2%–18% e todo mundo recebe 11%. Exige emenda datada na
> [[ADR-219]] D4 (abortar contradiz "omite a classe ou usa default").
>
> **Passo 2 fechado em 2026-08-10 — #1364.** [[ADR-374]] nasce `Proposto` com a
> fórmula, e a [[ADR-219]] D4 ganhou **emenda datada**: a frase *"omite a classe
> ou usa default conservador documentado"* estava errada e **nenhum run a
> exercitou**, porque o σ do MC não vinha daquela tabela. Não move número — o que
> destrava é o passo 3 (agregação + `mc_version` 6.0), e o que impede é o passo 3
> ser escrito contra uma D4 que diz o contrário. **Flip de `Proposto` →
> `Decidido` é do dono:** a fórmula muda a largura do cone de toda a frota.

> **Flip executado em 2026-08-11 — #1366 (bloqueio) + #1369 (aprovação).** O dono
> autorizou condicionado à aprovação do `financial-planner`, que **bloqueou na 1ª
> revisão**: não por infidelidade de redação — os sete números conferiram — e sim
> porque dois achados mudavam o que a ADR afirma. **Imóvel de renda está no pool
> simulado e o alvo não o descreve** (publicaria 1,80% contra limite real de 5,08%
> — cone 2,8× mais **estreito**, concentrado no ICP aluguel + carteira defensiva),
> e a **incoerência μ/σ**: a largura passa a refletir o alvo e o centro não. Saíram
> D9 (peso observado para imóvel), D10 (σ do snapshot, `as_of` = data de
> referência) e a quinta declaração de D8. A 2ª revisão achou um defeito **novo,
> introduzido pelo conserto do primeiro** — a precondição de D1 redigida como
> *"cobrir o pool"* é falsa para família com cripto material. **A sprint herda a
> lição:** revisão que aprova tem de re-caçar o que o conserto introduziu, não só
> conferir se o achado original fechou.

> **Estado em 2026-08-13 — #1433, parcial, segue `in_progress`** (os snapshots
> acima são datados — **não os reescreva**). Ao medir o substrato do passo 3
> apareceu um defeito vivo na **entrega anterior desta própria lane**: a faceta
> `ano_cone` da nota do #1356 **nunca renderizou**, porque o leitor buscava
> `p50_ano_if` — chave que o rename de `mc_version` 4.0 aposentou. O componente
> `FacetaAnoCone` estava inalcançável e o número que motiva a nota era o único
> calado. **Nenhum número publicado mudou.**
>
> **A sprint herda três coisas.** (1) O gate `dev/check_artifact_read_keys.py`
> declarava cobrir todo leitor de `application/` e **não cobria** payload que
> chega por `.content_json` — o falha-fechado nunca disparou para o único leitor
> sem contrato declarado. Furo fechado + `ARTIFACT_CONTRACT_BLOCO` para chave de
> bloco lida de parâmetro. (2) **Instrumento pode ficar cego pelo próprio fix:** a
> primeira tentativa roteou a chave por helper e a mutação saiu **verde**, porque o
> gate só enxerga literal em `.get()`. (3) O §Deferimento da [[ADR-374]] foi
> **verificado e está correto** (classe com `effective_to` vencido vira
> `effective_from: null`, então o diff dispara), mas sozinho **super-dispara** —
> com σ em `fallback_codigo` em 100% dos runs, avisaria "revisamos o modelo" a quem
> não teve cone movido. A refinação (causa ∧ efeito) é emenda a ADR `Decidido`
> sobre o que a família é informada ⇒ **gatilho de `financial-planner`**, não feita
> nesta sessão. **O passo 3 segue bloqueado por essa decisão**, como a ADR mandou.

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

> **[[A40.l27]] ✅ `shipped` 2026-08-07 — `cd6fde12` (#1265, PR2).** `failure_reason`
> no read path + runbook de run travado ([[ADR-172]]). O parágrafo acima é o estado
> de 2026-08-03 e fica como registro. Entrega não estava citada aqui até 2026-08-09.

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

> Movida para [`_HISTORY`](_HISTORY.md) em 2026-08-14 — registro fechado, não governa decisão de hoje.

## Entregas fora de lane (2026-08-03)

> Movida para [`_HISTORY`](_HISTORY.md) em 2026-08-14 — registro fechado, não governa decisão de hoje.

## Decisões do dono — A40.l18 (2026-08-06)

> Movida para [`_HISTORY`](_HISTORY.md) em 2026-08-14 — registro fechado, não governa decisão de hoje.

## Pendências de decisão (2026-08-03)

> Movida para [`_HISTORY`](_HISTORY.md) em 2026-08-14 — registro fechado, não governa decisão de hoje.

## Decisões do painel (correções incorporadas)

> Movida para [`_HISTORY`](_HISTORY.md) em 2026-08-14 — registro fechado, não governa decisão de hoje.

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
| **Job `frontend-e2e` não gateia** — opt-in pelo label `e2e` **e** fora do `All checks green`; PR com E2E vermelho mergeia (medido: #1278) | — | **sem lane, e agora sem candidata** — a [[A40.l23]] shipou em #1334 e **recusou** absorvê-lo: é política de CI (gatilho `sre-devops`), não gate de grafo de doc. Reaberto sem dono em 2026-08-08. **Evidência nova a favor de atacá-lo:** no #1337 os jobs *Frontend visual snapshots* e *Frontend print visual diff* saíram `skipping` e a mudança **mergeou com a baseline visual nunca verificada** — o mesmo buraco, em outro job |
| ~~**Step de notificação do `frontend-e2e` dá 403**~~ (`actions/github-script` → `issues.createComment` sem `permissions`) — rodava `if: failure()`, virava o `##[error]` mais visível e **mascarava a causa real** | — | **FECHADO** — #1283 (`04278c9d`, 2026-08-08): `permissions: {contents: read, pull-requests: write}` no job + `continue-on-error` (PR de fork recebe token read-only **independente** do bloco, e o step é diagnóstico, não gate). O guard de `workflow_dispatch` que esta linha pedia **já existia** — o `if:` do step sempre teve `&& github.event_name == 'pull_request'`, então `context.issue.number` nunca chega `undefined` ali. Verificado no runner: step verde e comentário entregue |
| **O PDF exportado não contém as últimas seções nem NENHUM título de seção** — `pdftotext -layout` sobre o PDF do harness (geometria de `pdf_renderer.py`: A4, margens 15/12/15/12mm) devolve 0 ocorrências de `"Parecer do Planejador"`, `"Síntese Estratégica"` e `"Apêndice"`, e 0 da nota da S_parecer; com `paperHeight: 300in` o MESMO run traz a nota, os pontos fortes e o diagnóstico. Em media screen as 14 seções têm altura > 0 e sob `emulateMedia({media:"print"})` a nota é visível — logo **não é `display:none`**, é paginação/paint do `printToPDF` | [[A40.l22]] §Blockquote (`test.fixme` marca a retomada em `print.@critical.spec.ts`) | **PR em voo** — #1287 (*"o PDF exportado volta a conter todas as seções"*), aberto por esta medição. Enquanto não mergear, é o que torna a perna de PDF do §Critério de aceite da l22 **parcial**. Medido 2026-08-07/08 |
| **A baseline do `frontend-print-visual` é um screenshot de CRASH** — `report.print.pdf.png` (2026-04-27) é o error boundary do React ("Algo deu errado ao renderizar esta página"), não um relatório. O gate nunca comparou relatório com relatório e é **fail-open**: se o relatório voltar a crashar do mesmo jeito, o job fica verde. Os 94.472px de divergência de hoje são crash-vs-relatório, **não** drift | — | **PR em voo** — #1290 (*"rebaselina 10 snapshots de seção com drift"*). Medido 2026-08-08 no fecho do #1277 |
| **Gate `Frontend visual snapshots` está cego** — S2 varia 5,1–6,3% entre as 3 tentativas do MESMO commit (tolerância 2,5%) e `main` puro reprova em 6 baselines (controle 2× via dispatch). Escondeu uma regressão real da própria l45 atrás do ruído | [[A40.l45]] §Follow-up | **lane** — [[A40.l53]] (decisão do dono 2026-08-12: follow-ups da l45 viram lanes na A40) |
| **`hidden md:block` entrega ao papel a variante mobile** ([[ADR-381]] D1) — 2 call-sites sobrevivem por acidente; o próximo some do PDF sem erro | [[A40.l45]] §Fora de escopo | **lane** — [[A40.l54]] |
| **Medida de linha no papel** — 100–110 cpl na prosa do A4 (confortável: 45–75) | [[A40.l45]] §Fora de escopo (estava "transferido, sem dono" — o estado que evapora) | **lane** — [[A40.l55]] |
| **Índices `_generated/` são contenção global + IDs sequenciais colidem sob paralelismo** — 8 renumerações de ID e 8 rebases entre a l45 e a abertura destas lanes (2026-08-11/12) | [[A40.l45]] (execução) | **§Pendências de decisão item 13** — política de repo, owner-gated |
| ~~**Race no readiness do backend no `frontend-e2e`**~~ — o step "Start backend" fazia `sleep 5` fixo + UMA tentativa de `curl -sf /health`; quando a importação da app passava desse orçamento o job morria com "backend não subiu" e o Playwright **não rodava nenhum teste** (medido 2× consecutivas no #1277; o artefato `backend-logs` mostra uvicorn e celery subindo com sucesso). Mecanismo distinto da linha "não gateia" acima: ali o job não bloqueia; aqui ficava vermelho **sem carregar informação de teste** | — | **FECHADO** — #1283 (`04278c9d`, 2026-08-08), co-design `sre-devops`. Deadline em **wall-clock** (90s HTTP / 120s worker), não contagem de voltas: cada `/health` custa até ~2,5s porque o handler faz `celery inspect(timeout=2.0)` embutido, então `seq 1 60` contrataria 60s e entregaria ~180s. Mensagem ramifica por `kill -0` do PID ("morreu" vs. "vivo, não respondeu em Ns") com `tail` do log **do subsistema certo**, e o caminho feliz imprime o elapsed. **Além do pedido:** espera o worker Celery por `celery inspect ping` ([[ADR-252]] D4, mesmo probe do compose) — nada o verificava, e ele é pré-requisito de `pipeline.run`; sem isso o atraso do worker não somia, virava `toBeVisible` timeout no meio do Playwright. Deliberadamente **não** gateia no `status` do `/health` (ver linha nova abaixo). **O run de verificação reproduziu a corrida: 8s** — o `sleep 5` teria matado aquele run também |
| **`GET /health` reporta `status: "degraded"` em toda chamada** — `executor_revision` entrou nos checks (`backend/app/main.py:304`) sem entrar no set `informational` (`:360`), e nunca é a string `"ok"`; em CI recebe `MATHOMS_BUILD_SHA`. **Nenhum teste assere o agregado** — é por isso que é invisível. Efeito colateral não decidido da implementação da [[ADR-363]] (a ADR não menciona o agregado), não dívida ambiente | — | **sem lane** — blast radius zero hoje (healthchecks do compose usam só HTTP 200; nada consome `status`), mas é fail-open no único sinal sumarizante do endpoint. Fix é indivisível em 3: `informational |= {"executor_revision"}` + teste do agregado (sem ele a armadilha se re-arma no próximo campo) + emenda datada na [[ADR-363]]. Descoberto em 2026-08-08 no #1283, que por isso gateia em HTTP 200 + `inspect ping` |
| **`frontend-e2e` tem 17 testes `@critical` vermelhos** — com o probe do #1283 consertado o job voltou a *rodar*, e o resultado é 17 failed / 49 passed / 7 skipped (run 31247625227): `tab-order.@critical.spec.ts` não acha `aria-label="Tema do relatório"` no shell, `vault.spec.ts` não acha a mensagem de retry-unlock, entre outros | — | **sem lane** — é a **pré-condição** da linha "não gateia" acima: não se liga um gate com 17 vermelhos, então promover o job a required depende desta triagem, não do inverso. #1283 tornou o vermelho *legível*; não o resolveu. Medido 2026-08-08 |
| **O filtro `report` do `changes` não cobre os specs** — `frontend/src/components/report/**` está listado, mas `frontend/tests/e2e/**` não; PR que toque **só** o spec não dispara o step bloqueante `Report render gate`, que é onde a A40.l3 e a A40.l22 puseram os gates de render/print | — | **sem lane** — medido 2026-08-08 |
| ~~**O opt-in por label era inalcançável depois do `opened`**~~ — `labeled` não estava em `on.pull_request.types`, então label aplicado depois **não redisparava o CI**: o job ficava `skipping`, verde por omissão. O gate de pixel só funcionava para quem lembrasse do label no segundo exato da criação do PR — um dos mecanismos que deixaram `report.print.pdf.png` congelada num error boundary por ~3,5 meses e 10 baselines de seção driftarem 2-3 meses | — | **FECHADO** — #1315 (`0d4fca9f`, 2026-08-08) + #1322 (última instância de texto vencido, no comentário do filtro `report`). `labeled` no trigger **+** `cancel-in-progress: ${{ github.event.action != 'labeled' }}`: sem a exceção, aplicar label com run em voo cancelaria os ~7 jobs (incluindo `backend-tests` no minuto 9 de ~10) e reiniciaria do zero. **Verificado no vivo, no próprio PR**: run do `opened` deu `frontend-visual: skipped` e o run do `labeled`, `success`, com o run original **não** cancelado — o que também prova que `github.event.pull_request.labels` chega no payload de `labeled` e nenhum `if:` precisou mudar. **Custo medido: ~29 min faturados por label pós-criação**, dos quais 4 são do job desejado; o resto é acompanhamento e é o preço de não ser fail-open (um run que skipasse os demais jobs faria `all-green` reportar `success` e **sobrescrever** um vermelho legítimo no mesmo SHA). Registrado na [[ADR-210]] §Adendo 2026-08-08 |
| **"Rodar" ainda não é "gatear" — e agora vale para os três jobs** | — | **sem lane** — extensão da linha "`frontend-e2e` não gateia" acima, que media só o E2E: `frontend-visual` e `frontend-print-visual` **também** estão fora de `all-green.needs`, logo vermelho neles não bloqueia merge. Até o #1315 as duas causas se somavam (o job nem rodava); agora sobra só esta. Promover qualquer um a required continua dependendo da triagem dos 17 `@critical` vermelhos (linha acima) no caso do E2E, e de decisão de custo nos de pixel (~29 min/label medidos). Aberto em 2026-08-08 · **corrigido em 2026-08-14 (#1463)**: a premissa venceu — os dois jobs de pixel **entraram** em `all-green.needs` em 2026-08-12 (`ci.yml` §`all-green`, com o comentário datado). O que continua verdadeiro é mais estreito: o loop **aceita `skipped`**, então o gate só morde quem aplicou o label; PR sem o label segue envelhecendo a baseline em silêncio — mecânica que deixou o `frontend-print-visual` vermelho em `main` de 2026-08-12 (#1400) a 2026-08-14 (#1458) sem bloquear merge nenhum. Ilustração medida: o #1453 levava `visual`, **não** `print`, então o job foi `skipped` nele e o merge passou com a regressão viva. Promover a required de verdade = tirar o `if:` de label, não mexer no `needs` |

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

## Inventário de follow-up da sessão de 2026-08-11/12 — [[A40.l43]]

Mesma convenção da seção acima: **um item ou tem lane, ou tem disposição escrita.**
O co-design da l43 (`prompt-engineer` + `financial-planner` + `product-designer`,
escalado ao `senior-cto`) produziu achados vizinhos ao escopo. Os com dono foram
roteados; o resto foi para a [[A40.l46]], aberta a pedido do dono para que nenhum
evapore. **Fronteira com a [[A40.l46]]** (mesma data, do fecho do #1382): ela prova o
gate de print; o item §I4 da [[A40.l51]] conserta o insumo das fixtures.

**Elevado a P1 depois da medição:** 3 itens são defeito em **número ou prosa já
entregues ao usuário**, não débito de forma. A verificação rodou 4 lentes e refutou 2
achados alegados (registrados como §Fantasmas na lane, para ninguém reabrir).

| Follow-up | Onde está | Tem destino? |
|---|---|---|
| **Score de endividamento com sinal INVERTIDO no default** — `invertido=False` no código vs `true` no `scoring.json`; medido: endiv 5% → nota **0,0**, endiv 50% → nota **10,0**. Alcançável por 3 call sites, um deles `backend/app/services/score_reader.py` | [[A40.l51]] §C1 | **lane** — fix é 1 char, mas muda score: gatilho `financial-planner` |
| **`R$ 2,000` / `R$ 36,000` — separador de milhar dos EUA em prosa entregue** (`consumo_consciente.analise`, `previdencia_pgbl.nota` no snapshot do view-model). Em pt-BR lê "R$ 2" | [[A40.l51]] §C2 | **lane** |
| **`.replace(",", ".")` na prosa inteira corrompe pontuação** — `suggestion_rules.py:574`; medido: *"da meta IF**.** mas a renda"*, 5 vírgulas gramaticais destruídas | [[A40.l51]] §C3 | **lane** |
| **A causa-raiz que a l43 diagnosticou foi removida PELA METADE** — o validador ainda exige as **10** summaries não-vazias (`format_helpers.py:244-251`), e 4 delas são órfãs: o gate **obriga a fabricar prosa** para chaves que nenhuma superfície lê. Mesma regra, mesmo arquivo | [[A40.l51]] §C4 | **lane** — autocrítica da l43; destrava o fix dos landmines |
| `renda_passiva.conclusion` imprime "Faltam R$ **-**X/mês" (subtração sem guarda de sinal) e o percentual não é clampado — **entregue** na S7 | [[A40.l51]] §I7 | **lane** — plausível, **não observado**; medir antes de escrever a copy |
| Landmines de veredito sem limiar em chave **não entregue**: `s2` "endividamento controlado" (o produtor gated já existe e é entregue) · `top15_ativos` "Concentração em poucos ativos" · `patrimonio_doughnut.context` · `carteira_diversificacao_frase` com n=1 | [[A40.l51]] §I8 | **lane** — preferir deleção a reescrita; depende do §C4 |
| Drift de comentário deixado pela própria l43 — `format_helpers.py:87` cita 3 call sites, 2 não existem mais | [[A40.l51]] §I9 | **lane** |
| Parágrafo do filho: "do casal" incondicional (falso p/ titular solteiro) · 2º filho **desaparece** · juízo sucessório incondicional · idade omitida · membro `dependente` **invisível** | [[A40.l51]] §I1 | **lane** — inclui fechar o falso-verde do gate da l43, que mede 3 literais e não pega "peça central" |
| `fmt_currency` contra COPY_GUIDELINES §4 (`k`/`M`, sinal, NBSP, piso de compactação) — **72 call sites** e **6 formatadores independentes**, incl. `dashboard_service._fmt_brl` com separador US | [[A40.l51]] §I2 | **lane própria** — e a §4 precisa de emenda para "prosa gerada", que hoje manda o impossível |
| `taxa_endividamento`: `scoring.json` declara "% renda mensal comprometida" mas a fórmula é `dívidas/patrimônio bruto`; `FORMULAS.md` sem linha | [[A40.l51]] §I3 | **lane** — docs-only, não-breaking (nenhum consumidor lê `unidade`) |
| 5 das 6 fixtures E2E têm o contrato morto — estados vazios do bloco de identidade nunca vistos em baseline | [[A40.l51]] §I4 | **lane** |
| Heading order h1→h3→h2 + Sumário Executivo sem heading (gate axe é `critical+serious`, `heading-order` é `moderate`) | [[A40.l51]] §I5 | **lane** |
| 6 lanes fora da tabela §Lanes (l38–l42, l44) — o §Gate de saída lê a tabela | [[A40.l51]] §I6 | **lane** (contador corrigido em #1405; a tabela, não) |
| Substrato declarado de plano de vida — feature que o pedido original queria | [[A40.l51]] §F1 | **lane** — exige ADR `Proposto` com gatilho **PII**, e depende do §Escopo 2 da l29 |
| `perfil_familia.right` publica `n_imoveis` (contradição cross-seção) | [[A40.l6]] | **quitado por remoção** — o aceite "fonte única" ficou insatisfazível; a l6 mantém só o lado da S4 |
| Política de diversificação/concentração — o que a S3 afirma sobre a carteira | [[A40.l15]] | **lane** — a l43 mediu que os publicadores **entregues** foram a zero; a política segue da l15 |
| Premissas de IF (TRS, retorno real, meta em R$, aporte-meta) sem superfície nenhuma no relatório | [[A40.l29]] §Escopo 2 | **lane** — `financial-planner` classificou como *requisito de leitura*, não redundância ([[ADR-306]] §D2) |
| Forma do ramo de prazo ausente na S7 (preservar ao reescrever o §Escopo 1) | [[A40.l29]] | **lane** — a declaração de ausência já foi transferida em `849e372b`; a l29 não pode reintroduzir `fmt_num` cru |
| `parcela_mensal`/`taxa_juros` sem valor numérico · branch `block` da RL2 inalcançável | `docs/sprint/A26/tracks/taxa-divida-numerica.md` | **track existente** (`ready`, P2) — **não** abrir item novo; as citações da track estão desatualizadas e a evidência que o painel citou é dead code |
| `custo_medio_pct_aa` sem produtor mata o branch carry-trade | [[ADR-367]] + `rule-ordem-do-plano-por-irreversibilidade` | **já documentado** |

## Inventário de achados órfãos da sessão de 2026-08-11/12 (S6/FP-010 + fix de CI)

Fecho da sessão que entregou #1379 (âncora S6→S9 + gate de vocabulário), #1390
(remoção da `rule_seguros_insuficientes`, FP-010) e #1385 (venv cache carrega o
interpretador). Cada achado foi **re-verificado contra `main` em 2026-08-12**
(9 verificadores independentes; 2 enunciados corrigidos, 1 sinal refutado) e
triado pela regra da §Pendência 11: **destino é quem já possui o arquivo ou a
superfície** — só 1 qualifica na exceção (P1 user-facing sem dono vivo) e
nasceu lane.

| Achado (enunciado corrigido) | Onde está | Destino |
|---|---|---|
| Conselho de cobertura sem ressalva fiduciária fora dos cards da S9 (card `pontos_urgentes`, narrativa `_S9_GAP_VIDA`, card `disclaimers` do APP_E sem componente) + string afirma *invalidez* com predicado só de *vida* | [[A40.l60]] | **lane** — funde os 2; PR1 ✅ #1480 · PR2 **deixou de ter amarra** quando a [[A40.l35]] shipou (#1476): virou exigível, não dispensável |
| Os extras de test-deps **rebaixam o lock a cada run** (`starlette` 1.3.1→0.52.1, `pytest` 9.0.3→8.4.2, medido em cache-HIT): o gatilho do item 3 da emenda 2026-08-11 disparou e `requirements-test.lock` deixou de ser opcional | [[ADR-254]] §Emenda 2026-08-12 | **emenda datada** — doença e remédio no mesmo lugar (registrar separado garantiria que ninguém pegasse a cura) |
| Custo do `Ensure venv` em cache-HIT (sinal b da emenda 2026-08-11) | [[ADR-254]] §Emenda 2026-08-12 | **refutado por medição** — mediana 1s (n=14, máx 3s); MISS 4-7s. Registrado para ninguém re-investigar |
| Composite action para os blocos de venv (7 sítios do pin `setup-uv` em 4 workflows) | [[ADR-254]] §Deferimento datado | **deferido com gatilho** — "próximo bump do pin"; a condição vivia só no corpo do PR #1385, o modo de falha que custou a re-investigação do #658 |
| Prod builda em Python 3.12 (digest-pinado) e os jobs de teste rodam 3.13; o único job que casa interpretador com prod é o pip-audit — que nunca importa o código. Três docs afirmam "paridade com o Dockerfile" sem qualificar | [[ADR-254]] §Deferimento datado | **deferido com dono** (`sre-devops`) + qualificação das 3 afirmações no mesmo PR |
| `SuggestionCalloutInline` montado em 2 de 12 seções habilitadas — o caso vivo é a **S3** (2 regras determinísticas ativas, nenhum hospedeiro); a premissa original (S9) venceu com a remoção FP-010 | [[PLAN-suggestion-lifecycle]] §Deferimentos datados | **deferido no plano dono da superfície** + correção da afirmação vencida ("S3 sozinha renderiza 71 cards") |
| `GATE_BY_SECTION` sem gate de sincronia mapa↔layout ao habilitar seção (enunciado original "falha aberta em GATE_DEFAULT" estava **invertido** — o default 6 é deliberado, documentado e pinado por teste); decisão pendente só sobre S4 | [[PLAN-suggestion-lifecycle]] §Deferimentos datados | **deferido no plano dono da superfície** (P3) |
| `data.protection_bundle` da S9 calcula sobre zeros / não chega ao payload | [[A40.l35]] (`open`, P1) + [[ADR-240]] §Deferido | **já tinha dono** — ponteiro, nada novo (enunciado "sem produtor" estava errado: o produtor existe) |
| [[ADR-199]] afirma que o cross-linking via `SuggestionCalloutInline` "é automático nas seções fonte" (medido: 2 de 12) | [[ADR-199]] §Emenda 2026-08-12 | **emenda datada** — afirmação falsa em ADR Decidida orienta agente errado |

## Pendências de decisão — itens 11-12 (2026-08-03)

## Pendências de decisão — itens 11-13 (2026-08-03; item 13 em 2026-08-12)

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

**13. Os índices `docs/_MOC/_generated/` commitados são ponto de contenção
global, e IDs sequenciais colidem sob paralelismo — muda a política, ou
absorve-se o custo?** — aberta 2026-08-12, evidência das execuções da
[[A40.l45]] e desta própria curadoria: **8 renumerações de ID** (ADR
376→377→378→379→381; lane l38→l43→l45; e as lanes de follow-up nasceram
l50→l53) e **8 rebases**, porque todo PR que cria lane/ADR reescreve os mesmos
4 arquivos gerados, e `main` recebe commits mais rápido do que um ciclo de CI
completa. O rabo da §Pendência 12 já nomeou a alocação como problema; isto é a
medição da escala. Opções, sem decisão embutida: (a) gerar os índices **no CI**
em vez de commitá-los (muda [[ADR-182]]); (b) merge driver `ours` +
regeneração obrigatória no pre-commit (mantém o arquivo, mata o conflito);
(c) manter como está e padronizar o custo — alocar ID **depois do último
rebase, imediatamente antes do push**, lendo o teto de `origin/main` **e dos
PRs abertos** (`git ls-tree` + `gh pr list`), nunca do `ls` local. A (c) já é
prática registrada em memória de agente; elevá-la a texto do CLAUDE.md §ADRs
inverte o conselho atual de "abrir PR cedo para reservar o ID", que sob
paralelismo é contraproducente. **Owner-gated**: qualquer opção muda política
de repo.

> **Marcador de fato, 2026-08-24 — a opção (b) não faz o que o texto acima
> supõe.** O texto de 2026-08-12 fica: é o registro da medição da escala. O que
> mudou é conhecimento, não decisão. **Merge driver é client-side**: o
> `update-branch` do trem (`PUT /pulls/{n}/update-branch`) e o squash rodam no
> servidor do GitHub, que não lê `.gitattributes` do repo para driver
> customizado. Medido: `.gitattributes` **não existe** aqui, e o driver `ours`
> exigiria `git config merge.ours.driver true` **por clone** — que o CLAUDE.md
> §Git proíbe ao agente configurar. Logo (b) cobriria só o rebase local de quem
> rodou o config, não o caminho onde a fila trava. Não medi qual fração dos
> conflitos vem de cada caminho.
>
> Metade do custo que esta pendência mede **já foi paga** por outra via: o
> #1674 tirou o contador agregado dos índices, e a colisão que restava nos
> gerados era 3 de 4 arquivos por contador. Sobra o `DOC_STATS.md`, que é 100%
> agregado — não é reformável, só removível. A decisão entre (a), (b), (c) ou
> "fica como está" segue **owner-gated**, agora com o custo de (b) conhecido.

## Fora do sprint (disposição explícita)

> ### Admissão retro-registrada — [[A40.l88]], [[A40.l89]], [[A40.l90]], [[A40.l91]], 2026-08-26
>
> Quatro lanes abertas pela rodada unificada **U1** ([[ADR-416]]), todas **P0 que alcança o
> usuário** e nenhuma com dono de arquivo em lane viva — dentro da cláusula de exceção, ao
> contrário da [[A40.l87]]. A alternativa era a [[A42]], e o **critério de admissão dela as
> exclui por escrito**: entra ingestão, razão, contrato de store ou instrumento de
> certificação, *"fora dessas quatro não entra, ainda que seja P0"*. Render e E5 estão fora.
> Pôr as quatro lá exigiria emendar o critério da A42 — trade pior que admitir aqui.
>
> **A `date_target` foi movida no mesmo commit** (2026-08-17 → 2026-09-05). Abrir quatro
> lanes sobre uma data vencida há nove dias transformaria o único gatilho computável do
> tripwire da [[A40.l21]] em ficção — que é o argumento que a própria [[A42]] usa contra a
> fusão. Custo declarado, não escondido.
>
> **Moeda do contador de 2 re-runs:** a [[A40.l88]] é render puro e **não zera**; as outras
> três mutam E5 e zeram. Por isso a l88 é onda 1, e as demais compartilham **uma** janela de
> rebaseline, na ordem l91 → l89 → l90.


> ### Admissão retro-registrada — [[A40.l87]], 2026-08-26
>
> Lane **P1**, logo **fora** da cláusula de exceção (que cobre só P0 que alcança
> o usuário). Entra pelo precedente de admissão retro-registrada da [[A40.l46]],
> e o custo fica declarado aqui.
>
> **Por que não coube em lane existente.** A cláusula 1 (*destino é quem possui a
> superfície*) apontaria para a [[A40.l84]], que é dona do vizinho
> `resume_run.py`. Recusado: são skills e arquivos disjuntos (invariante de
> backend vs. superfície de produto + copy), a l84 já carrega 4 pontos de decisão
> abertos, e — decisivo — as duas produzem pares `(status_de_run, pending)` que
> **se refutam se escritos como uma coisa só**. A amarra correta não é fundir: é
> uma ADR para as duas ([[ADR-417]] D3) e `parallel_with` com partição declarada.
>
> **Custo declarado:** nenhum atraso ao gate de saída. A lane não disputa janela
> de rebaseline (não toca número publicado) e é **pré-condição de instrumento** —
> sem ela, cada pausa do dogfood custa uma escrita manual no DB e contamina a
> janela de re-run do §Gate de saída.


> ### Uso da exceção da cláusula 2 da [[A42]] — [[A40.l34]], 2026-08-11
>
> A [[A42]] §Critério de admissão cláusula 2 exige registrar o **custo** quando
> uma lane entra na sprint corrente pela exceção. Registrado: a **l34** é P0 que
> alcança o usuário, nenhuma lane viva possui `previdencia_analyzer.py`, e a
> espera pela promoção da A42 é **circular** — a A42 só promove com `A40 → done`,
> e a A40 **não pode ir a `done` com este achado aberto**, porque "Limite PGBL
> (12%)" publicado em duas seções sobre bases incompatíveis é ocorrência da 2ª
> classe do §Critério de done do [[PLAN-report-trust]] (*contradição
> cross-seção*).
>
> Consequência declarada: **admitir a l34 não atrasa o gate de saída — é
> pré-condição dele.** A `date_target` escorrega, e isso custa zero
> mecanicamente: o único gatilho computável que ela governava (tripwire da
> [[A40.l21]]) foi descarregado em 2026-08-07.
>
> A **l35** entra pela cláusula 1 (o destino é quem possui a superfície): a
> [[ADR-240]] §Deferido já nomeava a [[A40.l7]] como dona, e a A42 **não pode**
> admiti-la — a cláusula 3 admite por camada (ingestão / razão / store /
> instrumento) e a l35 é E5 + entrega de relatório.

> ### Retro-registro de admissão — [[A40.l46]], 2026-08-12
>
> A l46 nasceu na A40 em 2026-08-12 (#1407) **sem registrar admissão**, e não cabe
> na exceção da cláusula 2 da [[A42]] §Critério de admissão: ela é **P2**, e a
> exceção exige P0 que alcança o usuário. As outras portas também não a acolhiam —
> a cláusula 3 não admite baseline de print em nenhuma das 4 camadas da A42, e
> nenhuma lane viva possuía a superfície (l22 e l45, as donas naturais, já
> shiparam). Fica registrada como **desvio consciente, não como precedente**: o
> custo mecânico é zero (P2, fora das ondas, sem tocar `pipeline/**` — não zera o
> contador de re-runs do §Gate de saída), e o que este registro compra é a cláusula
> 2 continuar significando alguma coisa. Lane nova na A40 sem registro de admissão
> é desvio **visível**, não prática. Próximo resíduo sem dono segue as cláusulas
> 4–5 (plano temático vivo ou disposição explícita), não este atalho.

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

### Disposição dos follow-ups do fechamento — 2026-08-12

Rodada pedida pelo dono: *todo follow-up aberto que não está numa lane nem sendo
atacado ganha rota registrada*. Regra aplicada: **trabalho** vira lane
específica agrupada por dono (precedente l46–l49 do mesmo dia); **decisão** vira
pendência nomeada; **owner-gated** fica documentado na origem. Nenhum item vira
lane-coletora — item com dono de mentira é o que reaparece como PR corretivo.

| Item | Origem | Rota |
|---|---|---|
| Row de `fiscal_parameters` inconsistente (`deducao_brl_cents` mensal × faixa anual) — bloqueia [[ADR-375]] D5 | co-design [[A40.l34]] | **[[A40.l56]]** (P1) |
| Nenhum golden atravessa `from_fiscal_parameters` (produção) | crítico do PR1 da l34 | **[[A40.l56]]** (mesmo dono, mesmo objeto) |
| Parecer lê o contrato antigo do bloco PGBL (FP-04 morto · âncora `null` · resumo S8 · título do bucket) | handoff [[A40.l7]] + PR2 da l34 | **[[A40.l57]]** (P2, gatilho de subida declarado) |
| `schema_validation` warn → strict | [[A40.l5]] §PR5 ("outra lane") | **[[A40.l58]]** (`open` desde 2026-08-17 — a l5 shipou) |
| "PR mergeado invisível no `_README`" (3ª ocorrência) + 10 lanes fora da tabela (2026-08-12; **1** em 2026-08-24) | fecho da l7 · nota do §Lanes | **[[A40.l59]]** (gate na transição) |
| Faixa marginal: base de cálculo ou rendimento bruto? | co-design interrompido (limite de gasto) | **decidido na emenda 2026-08-13 da [[ADR-375]]** (D6: faixa sobre base de cálculo; teto sobre rendimento bruto) e shippado no #1448 · consumidor restante: [[A40.l37]] |
| `dev/golden_diff.py` fora de hook e de CI | crítico do PR1 da l34 | **pendência de decisão do dono**: wire como gate ou declarar ferramenta manual — hoje a prosa de lanes o cita como se gateasse |
| Vault key dos 55 E5 reais · `frontend-e2e` seed/auth · [[ADR-374]] §Deferimento | várias | **owner-gated**, documentados na origem — sem mudança |

O que **não** entrou aqui por já ter rota: [[A40.l36]]/[[A40.l37]] (lanes desde
2026-08-11), os PRs 2–4 da [[A40.l5]], a §Carga herdada da [[A40.l25]], e o PR3
da [[A40.l34]] (shipped #1448 · `6c68723a`).

## Infra de CI tocada durante a sprint (não são lanes)

> Movida para [`_HISTORY`](_HISTORY.md) em 2026-08-14 — registro fechado, não governa decisão de hoje.

## Achado novo do painel (fora dos 33)

> Movida para [`_HISTORY`](_HISTORY.md) em 2026-08-14 — registro fechado, não governa decisão de hoje.

## Achados da construção do harness de captura (2026-07-30)

> Movida para [`_HISTORY`](_HISTORY.md) em 2026-08-14 — registro fechado, não governa decisão de hoje.

## ADRs

Estado lido do campo `status:` de cada arquivo em `docs/adr/` em **2026-08-08** —
não do que a lane prometeu. A tabela cobre as ADRs que o frontmatter `adrs:` das
31 lanes referencia, mais a [[ADR-278]] (que nenhuma lane referencia: é a nota de
que ela **não** é superseded), as abertas por §Entregas fora de lane e as
emendadas por §Infra de CI tocada durante a sprint.

| ADR | Estado | Lane | Escopo |
|---|---|---|---|
| **[[ADR-354]]** | `Proposto` (aberta em #1114) · flip a `Decidido` no merge da [[A40.l2]] | [[A40.l2]] | Identidade de transação (K4) exclui atributos de proveniência do documento |
| [[ADR-337]] | `Decidido` · **2 emendas** na [[A40.l6]] (`amended_at` 2026-08-19, 2026-08-24) | [[A40.l6]] `shipped` #1673 | ~~Critério 4 (gate de PII no view-model) não existe~~ → **existe e é executável**. A 1ª emenda escreveu o critério; a 2ª corrigiu-o: o predicado chaveia no **valor**, não no nome do campo, e a redação roda também na **leitura** (artefato já gravado) |
| [[ADR-351]] | `Proposto` · flip na [[A40.l12]] | [[A40.l12]] | Retorno de principal não é renda recorrente |
| [[ADR-353]] | `Proposto` · flip na [[A40.l11]] | [[A40.l11]] | Confiança do diagnóstico — **bloqueado** até o campo-portador ter consumidor |
| [[ADR-357]] | `Decidido (A40.l18)` · **emendada** 2026-08-07 — flip quitado no PR2 da [[A40.l20]] (#1278), por decisão do dono: a condição (merge do **writer**, `b8460274`/#1258) já estava cumprida e a lane `shipped` | [[A40.l18]], [[A40.l19]], [[A40.l20]], [[A40.l21]] | Criticidade de stage e degradação do run — add-on advisory não veta o entregável. **A mais carregada da sprint: 4 lanes** |
| **[[ADR-366]]** | `Decidido (A40.l20)` · **emendada** 2026-08-07 (flip no merge do PR2, #1278; a emenda registra **4** correções que a execução fez ao texto) | [[A40.l20]], [[A40.l22]] | Desfecho da geração do parecer é eixo próprio — `status` segue sendo publicação. O membro `retido` ganhou produtor no #1278; antes era inalcançável |
| [[ADR-358]] | `Proposto` | [[A40.l16]], [[A40.l30]], [[A40.l31]] | Enforcement em produção exige budget de produção — e KR no plano onde ele age. A l30 fecha os defeitos **nº 2** (gate medido num plano, aplicado em outro — `_DENSITY_FLOOR`) e **nº 3** (detector inspeciona 3 campos dos 8+) que a ADR nomeia |
| **[[ADR-341]]** | `Decidido` (A37.l1) · a [[A40.l30]] **estende**, não reabre | [[A40.l30]], [[A40.l31]] | Contrato do exec context do parecer. D1-D4 são exatamente o que #1004 mudou (cap 8192→16384, 6→10 seções, hints fora do corpo) — e o que dobrou a superfície monetária que o modelo vê sem ampliar a ancorável |
| [[ADR-296]] | `Decidido` (A26.l9) | [[A40.l30]], [[A40.l31]] | Citação determinística: LLM emite `(claim, path, rótulo)` e o pipeline renderiza o valor. É a ADR cuja densidade mediana **11** foi medida no holdout sintético — o número que **não** deve ser confundido com o `5` do dogfood |
| [[ADR-356]] | `Decidido (A40.l4)` · **emendada** 2026-08-05 (registro do flip + dono do deferimento do `s1`) | [[A40.l4]] (`shipped`) | Precedência declarada do parágrafo de seção e CV9 como medida de entrega. Flip feito com o residual da re-triagem nomeado e portado pelo §Gate de saída e encerramento |
| **[[ADR-417]]** | `Proposto` (aberta em co-design, **antes** do PR de implementação) · flip a `Decidido` no merge do **PR2**, não do PR1 — até o trigger recusar, a decisão está pela metade | [[A40.l87]] | Toda pausa tem saída terminal sancionada, e abandonar é decisão de **run**, não de review. Reverte uma cláusula lateral da [[ADR-359]] (a exclusão de `needs_review` de `CANCELLABLE_STATUSES`) sem supersedê-la; sanciona o par `(cancelled, pending)` que a [[A40.l84]] **não** pode proibir |
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
| [[ADR-356]] | `Decidido (A40.l4)` · **emendada 2 ×**: 2026-08-05 (flip + dono do deferimento do `s1`) e **2026-08-11** (#1386) | [[A40.l4]], [[A40.l43]] | A 2ª emenda **remove uma chave entregue** (`perfil_familia.right`) e a regra do validador que a exigia não-vazia — regra que proibia silêncio e por isso **selecionava** veredito incondicional ("— saudável" com endividamento de qualquer tamanho). Escreve a regra que fica: o narrador de `perfil_familia` não publica valor monetário nem juízo qualitativo. Precedente de que matar chave entregue não exige ADR nova: o desligamento do `s3` pela [[A40.l15]] |

## Débito de método herdado da r3

> Movida para [`_HISTORY`](_HISTORY.md) em 2026-08-14 — registro fechado, não governa decisão de hoje.

## Inventário de achados órfãos do closeout da [[A40.l69]] (2026-08-21)

A lane fechou `shipped` hospedando 6 achados numa seção `### Aberto, com dono` —
título que `check_closure.py` **não** reconhece como deferimento (`DEFER_HEADING_RE`
casa `deferi|fora de escopo|pendênc|em aberto|…`, e não `aberto, com dono`). O gate
deu **0 achados estruturais** sobre 6 itens órfãos: verde de instrumento cego.

| Achado | Onde estava | Destino |
| --- | --- | --- |
| 68 % do balde do titular vindo de chave vazia (R$ 642.744,79 de R$ 943.189,25 — re-medido 2026-08-21, 3/3 runs) | l69 §Aberto | **P0 · lane própria proposta** — superfície criada pela própria l69, maior em massa que o defeito de origem |
| Golden sem domicílio de 2 membros (classe invisível ao CI por construção) | l69 §Ataque | **P1 · primeiro PR da lane proposta** — habilita o critério das demais |
| Kill-switch da cobertura restaura só metade | l69 §Aberto | [[PLAN-deterministic-authority]] §Deferimentos datados |
| Colapso cross-ano 26→9 no consolidador | l69 §Aberto | idem, **gateado por re-medição** (o número é de 08-12 e decide a prioridade) |
| Trava do cônjuge dependente + válvula declarada | [[ADR-394]] §Emenda (c), `dono: [[A40.l69]]` | idem — dono era a lane que fechou |
| Copy de `null` na narrativa | l69 §Aberto, roteada para 7e | **[[A40.l51]]**, que já hospeda a classe — o 7e ([[A40.l71]]) fechou 1 dia **antes** de o defeito existir, e a copy é pipeline, não render |

**Ponteiro, não item novo:** o regex cego é da [[A40.l59]], que já move a metade
estrutural do `check_closure` para hook. Acrescentar `aberto` ao alternador exige
medir falso-positivo antes (`aberto` é palavra comum, e o CLOSE-BLOCK-05 tem
orçamento declarado de ≤20 %).

## Decisão dos abertos da [[A40.l69]] — 2026-08-21 (3 especialistas + arbitragem)

`senior-cto`, `financial-planner` e `data-engineer` decidiram em paralelo; a
arbitragem fechou os conflitos (protocolo anti-loop). Duas medições feitas antes
de acioná-los mudaram a natureza de dois itens.

| # | item | prioridade | destino |
| --- | --- | --- | --- |
| 1 | **Truncagem silenciosa no E1.5a** — 23 elegíveis, 10 processados, 13 descartados calados; o 12º é a declaração da cônjuge (`ano_base` 2024, 38 bens). É a causa dos **R$ 188.123,73**, e **não** o consolidador | **P0** | deferimento de 2026-08-17 (E1.5a × E1.6, `senior-cto`) — **sem lane nova**; rota corrigida e ADR-394 §Emenda (d) |
| 2 | **`investivel_financeiro` perdeu `nao_atribuido`** — R$ 642.744,79 (68 %) saem do denominador de IF, exposição cambial e concentração imobiliária | **P0** | **lane nova, janela J5 própria** — 3/3 concordam no mérito; **não hoje** |
| 3 | **Idempotência do eixo de atribuição** — 2 runs, mesmo corpus, 15 itens divergem (`titular` × `mariana_…`) | P1 | triagem do dono → lane própria (A42) |
| 4 | Linha de cobertura de **atribuição** (grão domicílio) + 3º termo em `motivo_supressao_e5` | P1 | mesma lane do item 2, PR posterior |
| 5 | Kill-switch: `valor_publicavel` consulta `cobertura_enforcement_ligado()` | P1 | deferimento existente, carona no próximo PR do arquivo |
| 6 | Trava do cônjuge dependente | P2 | deferida; **texto corrigido** — o E1.6 carrega `contribuinte.natureza`/`dependentes`, o bloqueio era de leitura, não de dado |
| 7 | Válvula declarada · fixture de 2 membros como lane · copy de `null` | não-fazer | válvula deferida · fixture é **critério de aceite** dos itens 1 e 2, não lane · copy na [[A40.l51]] |

### O item 2 é regressão ainda não observada

`nao_atribuidos` entra em `_compute_bruto` e na `composicao`, mas **não** em
`investivel_financeiro`. Nenhum run executou pós-#1550 (`cobertura_investimentos`
é `[]` em 6/6 artefatos E5 do corpus), então o dano ainda não apareceu — e aparece
inteiro no próximo run. Excluir dinheiro do domicílio de um agregado do domicílio
porque o **membro** é desconhecido é erro de categoria: é o espelho do pecado que
a §D8 corrigiu.

**Não foi feito hoje por decisão da arbitragem**, não por falta de mérito: exige
rebaseline de golden, do snapshot do view-model e re-derivação de
`tests/test_e5_conservation_invariants.py` — janela própria, que o PR do produtor
não pode dividir.

### O plano não reabre

Nem ondas, nem gate de saída, nem critério de done. O trabalho executa sob
mecanismos que o próprio plano já escreveu, e dois tiveram a condição satisfeita
nesta sessão — a re-medição que o §Deferimento de 2026-08-21 exigia foi cumprida,
e ela mudou o arquivo-alvo.

## Inventário dos achados do r7 sem hospedeiro (2026-08-24)

O r7 fechou triagem em 2026-08-21 com **6 achados novos** — DE-7, DE-8, DE-9,
DE-10, CTO-7, CTO-8 — e **nenhum** tem arquivo de lane. `grep` pelos 6 ids sobre
os 75 arquivos de `lanes/` devolve zero. Isso não é opinião sobre prioridade: é o
fato de que `SPRINT_CURRENT` deriva de frontmatter e `lane_pickup` cruza
frontmatter com branch, então **achado sem lane é invisível ao pickup**. As lanes
abertas na noite da triagem (l75, l76) vêm de outra origem e não cobrem nenhum deles.

| Achado | Prio | Destino | Base |
| --- | --- | --- | --- |
| **DE-10** — dois resolvers divergem no mesmo payload | P0 | **[[A40.l77]]** — ✅ **shipped 2026-08-24** (#1684) | único P0 do r7 **sem destino nenhum** quando roteado; fechado sob a [[ADR-410]]. O DE-7 destrava: o denominador que ele publica mudou |
| **DE-7** — `nao_atribuidos` = 61% sem linha de cobertura | P0 | **já arbitrado** — §Decisão dos abertos da [[A40.l69]], item 2: *lane nova, janela J5 própria; não hoje* | ponteiro, **não** decisão nova: 3 especialistas + arbitragem decidiram hoje. Falta só o arquivo, na janela |
| **DE-8** — top-up IRPF sem quantia declarada | P1 | mesma janela do DE-7 | o próprio §r7 acopla: *"publicar a quantia por membro, e o invariante do DE-7 passa a fechar nos 45"* |
| **DE-9** — `cobertura_investimentos[].frescor` com zero consumidores | P1 | **triagem do dono** | sem home derivável. Família "afirmar sem qualificar" (a mesma do RV6-04); campo existe para o gate e não para o leitor |
| **CTO-7** — kill-switch de retenção não deixa rastro | P1 | **triagem do dono — pronto para pegar** | o §r7 já dimensiona: `validation.gates_desligados: [...]` não toca `e5_analysis.schema.json`, nem `dogfood_view_model.json`, nem o codegen, logo **não disputa superfície** com #1591/#1568/#1573 |
| **CTO-8** — colisão de ID desta onda | P2 | **ponteiro** para [[A40.l59]] + triagem — *marcador 2026-08-24: a l59 §78-83 declara os escopos **distintos** (alocação de id × registro do entregue) e o §Escopo entregue não tem item de id; o destino real é a §Pendência 13, owner-gated* | (b) e (c) da onda r7 já corrigidos; o residual é a tag `status/<lc>` **sem gate** — `build_doc_index.py` lê o campo `status:` e nunca confere a tag, e 7 ADRs desincronizam. Os 5 de lanes alheias ficam registrados, não varridos |

### RV7-05 foi re-ancorado, não fechado (medido 2026-08-24)

O §r7 lista o **RV7-05** como P0 `procede-aberto`. A medição diz que a instância
nomeada **já não existe**: o #1569 (`dfd561b9`, mergeado 2026-08-21) tocou
exatamente o arquivo que o achado cita, e `RealEstateYieldCard.tsx:205` renderiza
`imovelDisplayLabel(im)` — não mais `descricao` crua.

O que **sobra** do RV7-05 é a metade que o próprio achado nomeia — *"gate sobre
payload real"*, com a observação de que *"baseline visual usa fixture sintética e
não alcança"* — e ela coincide, termo a termo, com os **dois critérios abertos da
[[A40.l6]]**:

1. `scan_view_model_pii` não tem chamador (nem CI, nem pre-commit, nem stage);
2. não existe spec renderizada assertando ausência em `body.innerText()` **e** no
   PDF — a infra existe (`frontend/tests/e2e/helpers/report-pdf.ts`), o teste não.

**Disposição:** o residual vive na [[A40.l6]], que segue `in_progress` com razão.
Não é lane nova. **Esta é a única re-classificação de severidade deste inventário**
— se o dono discordar, o caminho é reverter a célula do §r7 e abrir lane própria;
o resto da tabela é roteamento, não julgamento.
