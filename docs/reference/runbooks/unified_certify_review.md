---
id: runbook-unified-certify-review
type: runbook
title: "Runbook — Rodada unificada: ledger-certify + pipeline-review + report-review"
status: ativo
date: "2026-08-25"
relates_to:
  - "[[ADR-416]]"
  - "[[ADR-343]]"
  - "[[ADR-302]]"
  - "[[ADR-347]]"
tags:
  - type/runbook
  - area/pipeline
  - area/dados
  - area/docs
---

# Runbook — Rodada unificada de certificação e revisão

> **Canônica:** [[ADR-416]] (`Proposto` — flippa no fecho do primeiro `U1`).
> **Disciplina de estado durável:** [[ADR-343]]. **Classe:** [[ADR-302]].
> **Owner da execução:** loop principal (não é agente). **Custo:** um run com LLM
> (~25–66 min, perna paga única) + um painel de 5 lentes.

## 1. Objetivo e quando rodar

Encadeia as três skills numa rodada só e produz **um entregável priorizado**, cujas
linhas são roteadas para **três registros**. Não é uma skill nova: é o operador de
composição descrito na [[ADR-416]].

**Roda quando** o dono pede as três juntas; ao fechar uma lane que tocou razão *e*
relatório; ou como cadência periódica de dogfood. **Não roda** para uma pergunta que
uma skill sozinha responde — nesse caso invoque a skill.

**Produz:** a síntese unificada em **dois formatos** — `SINTESE.md` e `SINTESE.html`, ambos
off-git e com valores — mais o dashboard PII-scrubbed como Artifact, e — **num commit só** — três
appends de seção, um por registro, mais os arquivos de lane dos P0 com suas linhas no
`_README` da sprint.

> O *"working em `_scratch/`"* saiu desta lista em 2026-08-30: `rg -c '_scratch' <este
> arquivo>` devolvia **1**, a própria declaração. Nenhuma fase o produzia, nenhuma o lia,
> nenhum critério o checava — era o emissor-sem-leitor que esta rodada persegue no produto,
> dentro do próprio runbook. Trabalho intermediário em `_scratch/` continua permitido; o que
> saiu foi a promessa de entregá-lo.

**Pré-condições:** todas as linhas `FAIL` do §5 F0 zeradas.

## 2. Retomada (leia primeiro)

Se você está retomando uma rodada interrompida:

1. Leia `storage/<uuid>/reviews/U<n>-<data>/_state.json`.
2. **Se `fired_at` está preenchido, o run JÁ foi disparado** — mesmo com `run_id`
   ainda `null`. **Nunca dispare de novo.** Com `run_id` preenchido, anexe-se a ele;
   com `run_id` null, procure o run do workspace com `started_at >= fired_at` e
   **adote-o**. O `run_id` só passa a existir **depois** do disparo — quem o cunha é o
   trigger —, então a janela entre disparar e registrar é real, e é exatamente ela que
   duplica um run de 60 minutos e o gasto de API dele.
3. Retome da primeira fase cujo checkpoint não está `done`.
4. Se `appends` mostra 1 ou 2 dos 3 MOCs escritos, o commit do §5 F5 falhou pela
   metade — **reverta os appends parciais** e refaça os três juntos.

## 3. Fronteira — o que esta rodada NÃO faz

- **Não renumera** nem renomeia código histórico de achado ([[ADR-416]] D3).
- **Não funde registros** e não cruza cadência anti-zumbi: cada MOC re-tria os
  seus `procede-aberto`, nunca os do vizinho.
- **Não substitui as três skills** — elas seguem executáveis isoladamente.
- **Não escreve achado de instância no git** ([[ADR-343]]): valor, nome próprio e
  literal monetário ficam off-git. **Exceção única, declarada:** o arquivo de lane que a F5
  escreve carrega **magnitude derivada** (pontos percentuais, razão, contagem) e âncora
  (`campo.dot.path`, `arquivo:linha`) — sem isso a lane nasce inacionável e a sessão que a
  pega tem de refazer a medição. Literal monetário e nome próprio seguem **proibidos** ali.
- **Não implementa.** É análise: nenhum fix, nenhum PR de correção sai daqui. O
  entregável é diagnóstico priorizado e **lanes abertas e vazias** — a F5 aloca o id e
  escreve o arquivo, e a execução é de outra sessão. Alocar id **não é implementar**: é o
  que impede sessões paralelas de colidirem no mesmo id, que foi o que quase aconteceu no
  `U2` (seis sessões, três alocariam o mesmo).
- **Não certifica a ingestão E0→E2.** Esse é o **piso** da corrente, e a
  `ledger-certify` assume E2 correto. Achado abaixo do piso é roteado para
  [[PARSE-CERTIFY-active]]; se a rodada rotear ≥1, considere `parse-certify` avulsa.

## 4. Estado durável

Arquivo único, no diretório cru da rodada:
`storage/<uuid>/reviews/U<n>-<data>/_state.json`.

```json
{
  "u_id": "U1",
  "workspace": "<uuid>",
  "run_id": null,
  "report_id": null,
  "fired_at": null,
  "phases": {"F0": "done", "F1": "done", "F2": "running"},
  "codes_allocated": {"LC": 13, "PV": 0, "RR": 0},
  "lanes_alocadas": {"A40.l94": "RR6-01", "A42.l14": "LC6-01"},
  "sintese": false,
  "commit_unico": {"LEDGER": false, "PIPELINE": false, "REPORT": false,
                   "LEDGER_U": false, "DEBITO": false, "LANES": false, "SPRINT_GATE": false}
}
```

**Regra write-ahead (a única que não pode sair errada):** grave `fired_at` **antes**
de disparar. O `run_id` não existe nesse instante — o trigger o cunha —, então grave-o
imediatamente **depois**, e deixe a retomada resolver a janela pelo `started_at`
(§2 item 2). A intenção precede o efeito; a retomada lê a **intenção**, nunca o efeito.

**A rodada toca o `main` UMA VEZ.** Um só commit carrega os três appends do §8, a linha do
§9, o débito do §10, e — quando a rodada abre P0 — os arquivos de lane e as linhas do
`_README` da sprint. Nenhuma fase escreve fora dele, **para a rodada nunca existir pela
metade em `main`**.

> **Enunciado pelo commit, não pela fase, e a diferença foi medida.** Até 2026-08-30 este
> parágrafo dizia *"F5 é a única fase que toca o git"* — e isso **já era falso**:
> `git show 47970706 --stat` mostra o commit da F5 do `U2` tocando também o runbook, que é
> **F6**. O invariante que importa sempre foi a **atomicidade do commit**; amarrá-lo a um
> nome de fase o tornava falso a cada fase nova que precisasse escrever, e foi exatamente
> assim que a escrituração de sprint nasceu num segundo commit, **2h25** depois
> (`47970706` 12:48 → `7470aa91` 15:13), deixando o `main` com uma rodada que declarava 6 P0
> sem uma única lane. Re-medir: `git show <merge> --stat`.

## 5. Fases

### F0 — Preflight

**Ação:** do checkout principal, com o venv do repo:

```bash
.venv/bin/python dev/preflight_unified_review.py <email|uuid>
```

**Critério de saída:** exit 0. Cada `FAIL` bloqueia; cada `WARN` vai **declarado**
no cabeçalho do entregável. Os dois `WARN` que mudam o que se pode afirmar:

- `frontend` fora do ar ⇒ sem captura de render ⇒ **`clareza-ux` fica sem cobertura**
  e não pode ser afirmada por inferência de código.
- `instrumento-ledger` ⇒ a P0 nº 1 da rubrica do razão segue sem detector (`LC06`,
  dona [[A42.l3]]). Declare, e rode a sonda de F3.a.

**Se a sessão morrer aqui:** recomece; F0 não tem efeito colateral.

### F1 — Alocação de `U<n>` e do diretório cru

**Ação:** reserve o próximo `U<n>` **no `_state.json`** (menção em prosa não reserva).
A linha do ledger do §9 é git, e por isso entra só na F5 junto com os três appends —
reservar em dois lugares e fases é o preço de a rodada tocar o `main` uma vez só.

Crie `storage/<uuid>/reviews/U<n>-<data>/`, **sem** o `run8`: ele não existe na F1, e
renomear o diretório na F2 quebraria o path que a §2 manda ler na retomada. O `run8`
vive dentro do `_state.json` e nos cabeçalhos das três seções.

**Snapshot de seleção E2** (pré-condição de F3.a, e só vale se tirado agora, antes
do run): grave o mapa `{(stage_canônico, artifact_key) → (id, byte_size)}` das rows
de `pipeline_artifacts` do workspace nos stages E2 + baseline, colapsado para o mais
recente por chave. **Guarde-o em `_state.json`.**

### F2 — Disparo e coleta

**Ação:** grave `fired_at` + `run_id`, **depois** dispare. Poll até terminal com o
predicado dos quatro status terminais (o snippet está no `SKILL.md` da
`pipeline-review`). **Só `completed` é verde** ([[ADR-416]] D2).

Depois: pegue o `report_id` do run, rode `collect_review_inputs.py` para o
diretório cru, e re-tire o **snapshot de seleção E2 pós-run**.

**Critério de saída:** run `completed`, `report_id` diferente do baseline, insumos
coletados, os dois snapshots E2 no `_state.json`.

**Se a sessão morrer aqui:** §2 item 2.

### F3 — Medição e julgamento

#### F3.a — Cross-checks determinísticos, nesta ordem

Rode **antes** de qualquer lente. `X5` primeiro: se ele acusa **ofensor**, todos os
outros estão atribuindo números ao run errado. Se acusa **vencida**, o defeito é do
instrumento (dispensa desatualizada) e as outras lentes seguem válidas — desde a
[[A42.l21]] o `X5` distingue os dois, e pode sair verde.

| # | Predicado | Falha significa |
|---|---|---|
| **X5** | Todo stage que `pipeline_stage_logs` declara `completed` **sem** row em `pipeline_artifacts` do run cai numa causa **nomeada**: zero trabalho declarado (`skipped: true` **ou** `total_processed: 0` — o repo usa as duas grafias, e os mesmos stages alternam conforme a saída), `writes=∅`, escrita sob a key de **outro** stage, ou read-only. As duas últimas são **dispensas declaradas** e cross-checadas contra a fonte a cada execução. O que sobra é **ofensor**; e `review_snapshot.provenance.execucao_mista` é verdadeiro se algum stage consumiu artefato de outro run | **Ofensor** = a proveniência declarada é **falsa** (o lookup de já-processado é workspace-scoped, não run-scoped). **Vencida** = a dispensa deixou de valer (a fonte ganhou writer, mudou de alvo, ou o stage passou a escrever sozinho) ⇒ o instrumento está desatualizado, não o run. **Corrigido na [[A42.l21]] ([#1906](https://github.com/davidrobert/mathoms/pull/1906)):** o predicado antigo — *todo `completed` tem ≥1 row* — marcava **4** stages benignos em **todo** run sob um rótulo só, logo **só podia sair vermelho** e não informava nada. Medido no histórico completo pós-conserto: **103 `FECHA` · 21 `DIVERGE` · 5 `INAPLICAVEL`**. Instrumento: `dev/unified_xchecks.py <ws> <run> x5` |
| **E2** | Em **três eixos**, não um: **composição** (o conjunto de chaves é idêntico) · **conteúdo** (`byte_size` idêntico nas unidades **re-derivadas**) · **procedência** (`id` mudou ⇒ este run reescreveu; `id` igual ⇒ unidade **herdada** de outro run) | Composição divergente = o corpus mudou sob os pés da medição. Conteúdo divergente = mesma população, unidade re-extraída com bytes diferentes. **O denominador do conteúdo é run-scoped** — unidade herdada não podia variar e infla o verde. Medido no `U4`: 135/171 mudaram `id` por re-extração e 34 eram herdadas, logo o predicado antigo (identidade de `(id, byte_size)`) era **insatisfazível** e só podia sair vermelho. Instrumento: `dev/unified_e2_snapshot.py --compare`, exit 1 = composição, 2 = conteúdo |
| **X1** | Por grupo: `tx_carregadas` sombra == persistido (**C1**); `executor_revision` do run == HEAD (**C2**); e a diferença de `transacoes_total` é **exatamente** a diferença do canal `cross_document_collapse` de `remocoes`, com os demais canais idênticos (**C3**, tol-zero) | O run cortou ou reteve rows que **nenhum canal declarado explica** — perda silenciosa, que é o que o ledger da [[ADR-347]] existe para tornar impossível |
| **X2** | O E4 re-derivado a partir do E3 **persistido do run** bate com o E4 persistido, em cents, por `(balde, categoria, mês)` | Categorizador não-determinístico, **drift de regra aprendida**, ou E4 estagnado vazando pelo workspace-latest. Pin obrigatório: contagem de `transaction_overrides` antes e depois |
| **X3** | **Vetorial**: para todo mês e balde, a série do view-model == `fluxo_mensal_detalhado`, em cents; e a soma dos meses == o total do balde | Escalar fecha e vetor não fecha ⇒ **deslocamento sum-preserving**. É a classe que a rodada inteira existe para pegar |
| **X3b** | `consolidacao_cross_documento.meses[]` bate, mês a mês, com a soma dos `remocoes[].cross_document_collapse.meses` dos E3 do run | O relatório **declara** um colapso diferente do que o razão executou |
| **X4** | Todo literal monetário **autoral do modelo** — não o carimbado pelo backend — pertence, em cents, ao conjunto de cents do E5 do mesmo run, ou deriva de fórmula declarada | Número ancorado pelo modelo, não pelo dado. ⚠️ **O denominador é a metade difícil:** medido no `U5`, **9 de 10** literais vivem em `riscos[*].ancoras[].valor_renderizado`, que `stamp_ancora_values` preenche copiando `path → valor` do **mesmo** payload que o check relê ⇒ órfão **impossível por construção**, e o `FECHA ✅ n=10/10` publicado era vazio. A superfície autoral é **n=1** ⇒ o veredito honesto é `INAPLICÁVEL`. Dona [[A42.l24]] |
| **X6** | **Diff escalar do payload publicado** contra o da rodada anterior: para todo escalar numérico presente nos dois, o valor é idêntico **ou** o movimento tem causa declarada. Publique o par `n_moveram`/`n_comparado` | Nada aqui é opcional porque **os outros seis podem fechar enquanto metade do relatório muda**: no `U5`, X2/X3/X3b/X5/E2 e a sonda **todos fecharam** e **95 de 400** escalares se moveram, com `patrimonio.bruto` **−48,1%** sobre corpus documental idêntico. Os demais checks medem conservação **entre stages** e proveniência **de execução**; nenhum mede o **publicado contra o publicado**. Instrumento: **pendente de promoção** — até então, `flat()` recursivo sobre os dois `report_data.json` das rodadas (§10, item 1 de 2026-09-01) |

**Comandos do razão.** A sombra (pré-colapso, `collapse_enforce` omitido por
obrigação do gate AST) e o entregue (E3 persistido do run pinado) rodam no mesmo
processo:

```bash
.venv/bin/python dev/certify_ledger_local.py <workspace> --entregue --run <run_id>
```

Critério declarado da KR-B: fecha com **`entregue=0` e `sombra>0` no mesmo run**.

**Armadilha de leitura:** `_count_diffs` deriva a contagem de `transacoes_total +
transacoes_duplicadas_removidas` e **ignora `remocoes`**. Sob enforce, o bloco de
drift grita "fresco != persistido" em quase todo grupo colapsado — isso é o efeito
**pretendido**. Não escale.

**Override de veredito (LC05), exatamente dois baldes.** O catch-all
`_non_ledger_verdict` procura `dados`/`apolices`/`composicao` e devolve `coberto`:

| balde | leitura correta |
|---|---|
| `patrimonio` | **`não-verificável`** — o payload é o baseline normalizado, sem nenhum dos três containers |
| `fluxo_mensal_detalhado` | **`não-verificável`** — usa `meses_ordenados`, e a glosa "fora do grão transacional" é falsa: é a mesma população classificada |
| `seguros` | **não rebaixe** — o catch-all acha `apolices` e conta certo |
| `pontos_milhas` | **não rebaixe** — é stub declarado do E4. O achado melhor é que o balde nunca é populado |

Nenhum balde do conjunto cego pode sair do entregável com veredito ≠ `não-verificável`.

**Sonda da P0 nº 1** (não reimplementa a [[A42.l3]]): sobre `investimentos_consolidados`
e `imoveis_consolidados` do `patrimonio` persistido, emita **denominadores primeiro** —
`D1` nº de itens · `D2` itens com id nulo · `D3` `len(itens) − len({id não-nulo})` ·
`D4` censo de `_dedup_warning` por tipo. **Fail-closed:** `D3 == 0` só é legível se
`D2 == 0`; com id nulo material o eixo é `não-verificável`. `D3 > 0` é **candidato**
(vai ao cético — produtos distintos do mesmo tipo/instituição são soma legítima);
`D4 > 0` é achado **reportável direto**: é dúvida que o próprio produtor declara e
que nenhum instrumento superficializa hoje.

**Nota do modo entregue:** `_rederive_entregue` semeia **só E3**, sem baseline — logo
`patrimonio` é omitido e `seguros` cai no placeholder. **Ausência estrutural, não
perda patrimonial.**

#### F3.b — Painel de 5 lentes, eixo primário declarado

Uma mensagem, cinco chamadas. Cada lente recebe **≤4 arquivos** e o resultado de
F3.a. **Proíba explicitamente `storage/` e a leitura de `.json` de payload** — é
assim que um painel inteiro morre afogado em dezenas de MB.

| Lente | Eixo primário | Rubricas que ela possui |
|---|---|---|
| `data-engineer` | razão | conservação E3+E4, dupla contagem, contratos de stage |
| `financial-planner` | materialidade | fronteira de categoria, solidez financeira |
| `prompt-engineer` | parecer | precisão, ancoragem, custo/latência das stages LLM |
| `product-designer` | superfície | `clareza-ux` **sobre a captura de render** |
| `senior-cto` | invariante | gates silenciosos, saúde de execução, cross-cutting |

**Ordem de julgamento** (de baixo para cima na cadeia de derivação). Regra-mãe:
*nenhuma pergunta que contenha "certo/correto/preciso" sobre um número é respondida
antes de o veredito do razão estar na mesa.*

| Antes do veredito | Bloqueadas até o veredito |
|---|---|
| **Q3** usabilidade · **Q7** falta algo · **Q1** parte estrutural · **Q5** completude · **Q8** | **Q2** número exibido · **Q4** metodologias · **Q1** parte causal · **Q5** correção · **Q6** · **toda** a dimensão `solidez-financeira` |

**Screen barato**, rodado aqui e roteado ao razão: a coerência aritmética entre a
folga mensal declarada e o gap de reserva declarado. Incoerência ali é o sinal mais
barato de defeito sum-preserving **que alcançou o usuário**.

#### F3.c — Braço cego, com trava

Roda **uma vez** para a rodada. Recebe a **tabela de condicionamento** —
`balde/grupo · veredito · estado cross-grupo · defeito de classe aberto · sinal do
viés · magnitude medida` — e **não** recebe a prosa dos achados nem recomendação de
rodada anterior.

1. Declare, para cada alavanca, a tripla `(balde/grupo, veredito, campo do payload)`
   — caminho **e** valor. Alavanca sem tripla não entra no entregável.
2. **Não dimensione contra o produtor.** Campo ausente, nulo, sentinela, ou
   superfície que imprime "não se aplica" para o regime ⇒ alavanca **inadmissível**,
   retirada, não rebaixada. Prefira sempre o campo que a superfície imprime.
3. Base `conservado` **sem** defeito de classe aberto ⇒ número pontual.
4. Base `conservado` **com** defeito de classe aberto mapeado ⇒ **só banda**, com o
   sinal do viés explícito; **sustente a direção apenas se ela sobreviver ao extremo
   pior**. Se inverte, a alavanca é `indeterminado-por-viés` e inelegível a nº 1.
5. Base `coberto-sem-verificação-de-valor` ⇒ dimensione por **contagem/estrutura**,
   nunca por valor.
6. Base `não-verificável` ou `perda/dupla-contagem-silenciosa` ⇒ não dimensione e
   não use como desempate; emita como **`condicionada`** — direção declarada, sizing
   ausente, **e a medição que a destrava**. Condicionada nunca é nº 1, mas conta.
7. Carimbe cada argumento de ordenação com `novo` · `vivo` · `refutado-em-rN`.
   **Premissa `refutado-em-rN` não desempata**, nem como reforço.
8. Se nenhuma alavanca ficar elegível a nº 1, a resposta de **Q6** é
   `ordenação indeterminada — razão não libera sizing`, com a lista de medições que a
   liberariam. Isso é resposta válida; silêncio não é.

**Por que 4 e 7 são as regras que importam:** são os dois modos que já reprovaram —
base `conservado` com defeito sum-preserving vivo, e premissa reciclada de rodada
anterior como desempate.

#### F3.d — Céticos, em lote

Um cético **por lote de ~5 achados**, nunca um por achado: o piso de herança de
contexto por subagente torna o fan-out por item mais caro que o trabalho. Cada um
devolve veredito (`CONFIRMADO`/`PARCIAL`/`REFUTADO`), severidade corrigida, triagem
(`NOVO`/`JÁ-CONHECIDO`/`MEDIÇÃO-DE-CONHECIDO`) e `inerte_para_usuario`.

**Taxa de `REFUTADO` igual a zero é tripwire do método.** Cético que não refutou
declara **qual medição faria a refutação**.

#### F3.e — Crítico de completude

Roda **uma vez**. Audita o processo desta rodada: qual célula da matriz do §F4 ficou
fraca, que `CONFIRMADO` se apoia em evidência fraca, que refutação foi escopada e
vendida como total, e **qual verificação barata de 1 comando fecharia o claim
pivotal**. Rode essa verificação e reporte, mesmo que ela derrube achado seu.

**Critério de saída de F3:** ≥1 claim pivotal fechado por medição.

### F4 — Clusterização e roteamento

Funda por `(dimensão, âncora, regra)`. **Gate de cobertura em matriz — dimensão ×
registro, 7 × 3:** cada célula reivindicada por ≥1 lente **ou** declarada sem
cobertura com motivo escrito. Célula vazia e silenciosa reprova a fase.

Depois, roteie cada linha pelo §6. **Toda linha sai com `registro` preenchido e
cardinalidade 1.**

### F5 — O entregável, a escrituração, e **um commit só**

**Ordem obrigatória. Os dois primeiros passos são off-git; o terceiro é o único que
toca o `main`.**

**1 · Escreva a síntese, nos dois formatos.** Em
`storage/<uuid>/reviews/U<n>-<data>/`: `SINTESE.md` **e** `SINTESE.html`. É o entregável que
o §1 declara, e o **único** lugar onde valor, nome próprio e literal monetário podem estar.

> **Os dois, sempre — não "se o volume justificar".** O `.md` é a fonte auditável e diffável;
> o `.html` é o que se **lê**, e a leitura é o que faz a rodada ser consumida em vez de
> arquivada. Antes de 2026-08-30 o HTML era condicional, e o resultado medido foi que o `U1`
> e o `U3` não o tiveram até alguém perguntar por ele — a mesma patologia do próprio
> `SINTESE.md` antes de a F5 o produzir. Condicional que depende de o executor achar que
> "o volume justifica" é auto-declarado, e regra auto-declarada não pega (§10, fecho do `U3`). Conteúdo mínimo: vitais do run · a condição declarada **enumerada**
· as 8 perguntas de produto respondidas · os cross-checks **com valores** · a tabela
priorizada · a verificação dos fechados da rodada anterior · o índice do diretório cru.
Marque `sintese: true` no `_state.json`.

> **Por que ele vem primeiro.** As três seções git são o **recorte PII-scrubbed** dele.
> Escrever o recorte antes do todo convida a inventar o todo depois — e foi o que aconteceu:
> no `U2` o `SINTESE.md` só nasceu quando o dono perguntou *"onde está o relatório?"*, horas
> após o commit. O `U1` o escreveu; o `U2` não, **e a diferença foi acaso, não processo**,
> porque nenhuma fase o pedia. O §8 agora aponta para o **arquivo**, não para o diretório:
> quem pula commita afirmação falsa em três MOCs, verificável com `ls`.

**2 · Escriture o que a rodada faz com a sprint** — só se a rodada abriu P0:

> **Compute `P` antes de alocar, pela §6.1** — os quatro predicados, com a evidência na
> linha. Alocar lane sobre prioridade **julgada** foi o que produziu 2 `P1` numa rodada e 12
> na seguinte, e uma tripla contagem do mesmo defeito no `U5`. As três cláusulas que mais
> mordem aqui: cadeia de `P0` **não** promove (a raiz herda a lane), falso-verde de
> instrumento é `P1` **sempre**, e magnitude vive em `move decisão` — nunca em `alcança`.


- **Aloque os ids de lane**, gravando-os em `lanes_alocadas` no `_state.json` (mesmo padrão
  do `codes_allocated`), e **escreva os arquivos de lane + a linha na tabela do `_README`**.
  Menção em prosa não reserva. Sem a linha na tabela o `dev/check_lane_transition.py`
  recusa o commit e a lane fica invisível ao encerramento administrativo.
- **Registre o efeito no gate de saída da sprint**, no `_README` da sprint — nomeie
  **arquivo e seção**, não uma relação. Sprint cujo gate exige *"N re-runs consecutivos sem
  P0/P1 novo"* tem o contador **zerado** por esta rodada, que é por construção um re-run
  completo. Verifique também a **cláusula de reinício**, se houver: achado que muta E3/E5 a
  montante de todo run entra nela e empurra o início do contador.
- **Se decidir não alocar**, escreva a recusa no **cabeçalho das três seções do §8**, na
  linha `Escrituração:` — é o único endereço que existe, e sem ele a válvula é satisfazível
  por silêncio.
- **Não aloque número de ADR.** É o outro id global monotônico e ele colide entre sessões
  paralelas (medido: `ADR-420`, `421` e `422` nasceram no mesmo dia, em três commits, pelas
  sessões que o `U2` despachou). A alocação é da sessão que executa a lane; a linha do
  append **não cita número de ADR**.

**3 · Um commit só.** Três seções (§8) + linha do ledger (§9) + débito de método (§10) +
arquivos de lane + linhas do `_README`. Rode `python3 dev/build_doc_index.py` **antes** do
`--check` do §11 — a lane nova churna `_generated/`. Atualize `commit_unico` no
`_state.json` **depois** do commit.

> **A escrituração mora aqui, e não numa fase posterior, por medição.** No `U2` ela virou um
> segundo commit 2h25 depois, sem estado durável e sem regra de reversão; a §2 não sabia
> retomá-la, e as seis lanes chegaram aos appends por **backfill** (`#1829`, `#1831`,
> `#1832`, `#1833`), reeditando snapshot datado que o próprio `LC6-01` declara evidência.

### F6 — Débito de método

Registre no §10 os furos do **encadeamento** (os que não são de nenhuma das três
skills). Os furos que são de uma skill vão para o §Débito de método do MOC dela.

### F7 — Fecho (git-free)

Resuma no chat, PII-scrubbed. **Publique o dashboard como Artifact** — derivado do
`SINTESE.html` da F5, **sempre PII-scrubbed**: sem valor monetário, sem nome próprio, sem
identificador de posição; âncora é código de achado. Congele o diretório cru como baseline do
próximo `--compare`. **Nada aqui toca o git** — se você chegou na F7 com escrita pendente, a
F5 não fechou.

> **Dois artefatos, dois regimes de dado, e a distinção não é opcional.** O `SINTESE.html`
> mora em `storage/` e carrega os valores; o Artifact é hospedado e carrega só a estrutura do
> achado. Publicar o primeiro seria vazar o workspace; não publicar o segundo é entregar uma
> rodada que ninguém lê.

#### Critério de aceite da rodada

**Esta é a fonte**; a `SKILL.md` resume e aponta para cá. Cada caixa nomeia o que a
verifica — caixa auto-declarada sem verificador é a doença que a rodada persegue.

| | critério | verifica-se com |
|---|---|---|
| ☐ | Run `completed` — **nunca** `partial_failure` | status no DB |
| ☐ | `SINTESE.md` **e** `SINTESE.html` escritos | `check_sintese_anterior` do preflight audita os **dois** na rodada seguinte |
| ☐ | Dashboard publicado como Artifact, PII-scrubbed | a URL vai no resumo do chat |
| ☐ | Matriz 7×3 sem célula silenciosa | célula vazia tem motivo escrito |
| ☐ | Toda linha com `registro` e cardinalidade 1 | §6 |
| ☐ | Taxa de `REFUTADO` > 0 | placar dos céticos |
| ☐ | ≥1 claim pivotal fechado por medição | mesmo que derrube achado da rodada |
| ☐ | Zero literal monetário e zero nome próprio nas três seções | leitura humana |
| ☐ | Débito de método registrado no §10 | — |
| ☐ | Escrituração feita **ou** recusa escrita na linha `Escrituração:` do §8 | `n/a` se a rodada não abriu P0 |

**E as oito regras que o `U2` produziu no §10 são critério, não prosa** — a versão anterior
desta lista as deixava de fora, e por isso teria aprovado a rodada que as pariu, com os seis
auto-defeitos dentro:

| | regra do §10 (2026-08-29) |
|---|---|
| ☐ | Todo check de presença/ausência **importa o nome do produtor** ou publica controle positivo que dispara |
| ☐ | Todo cross-check publica `n_comparado` **e** `n_esperado`; zero ⇒ `INAPLICÁVEL`, nunca ✅ |
| ☐ | Instrumento rebaixado marca as linhas dele `STALE` e a F3.c **recusa** rodar com `STALE` na entrada |
| ☐ | Célula da matriz distingue `reivindicada` de `respondida`; reprova em `reivindicada ∧ ¬respondida` |
| ☐ | A lista de fechados vem do `git log <executor_anterior>..<executor_deste_run>`, **não do MOC** |
| ☐ | Carimbo `sem-veredito` é **ternário**, decidido pela whitelist de lineage |
| ☐ | Antes de re-triar achado herdado, `rg` a dimensão nas lanes da sprint |
| ☐ | Varredura de superfície no grão de **componente**, não de seção |

**Toda medição publicada no runbook traz o comando que a reproduz** (§10, `U1` item 4).
Blockquote sem comando é afirmação que a próxima rodada não pode falsificar — e no `U2` foi
assim que quatro afirmações falsas entraram neste arquivo.

## 6. Roteamento de achado

| A causa-raiz do defeito está em… | Registro |
|---|---|
| Reconciliação, categorização, identidade de lançamento, dedup de posição | [[LEDGER-CERTIFY-active]] (`LC*`) |
| Execução do run, telemetria, contrato de stage, gate silencioso, custo | [[PIPELINE-REVIEWS-active]] (`PV*`) |
| View-model, renderer, manifest do parecer, layout, copy, regra de domínio publicada | [[REPORT-REVIEWS-active]] (`RR*`) |
| Classificação, roteamento ou parse de documento (E0→E2) | [[PARSE-CERTIFY-active]] — abaixo do piso desta rodada |

**Desempate: onde o defeito se conserta (o produtor)**, não onde ele aparece.

- **Um defeito com um sintoma** ⇒ registra no produtor. O sintoma vira **ponteiro**
  no outro MOC, com `triagem: MEDIÇÃO-DE-CONHECIDO` e o código do dono. Nunca três
  linhas para o mesmo defeito visto em três telas.
- **Dois defeitos** ⇒ duas linhas, códigos próprios, referência cruzada.
- **Achado de produto que o razão explica** não abre linha nova no razão: vira
  **evidência de materialidade** anexada à linha `LC` existente.
- **Achado migrado** leva o **código original** e disposição `movido de <MOC> §rN`, e
  **não rearma** o relógio anti-zumbi.

### Forma da linha condicionada

Seis campos obrigatórios. Sem o quarto, **não é achado** — é requisição de medição,
e vai para a fila do razão, não para o placar de produto.

`afirmação · base (balde + veredito + defeito aberto) · sinal e magnitude do viés ·
o que sobrevive ao pior extremo · o que NÃO se afirma · medição que resolve +
gatilho de re-medição`

Linha cuja conclusão **inverte** sob o viés entra como `indeterminado-por-viés`, com
severidade **do que seria se verdadeira** e prioridade **da medição que a destrava** —
nunca `Baixo` por falta de certeza.

### 6.1 Prioridade é DERIVADA, não julgada

**O problema que isto resolve, medido.** Entre o `U4` e o `U5` a contagem de `P1` foi de
**2 para 12** sobre rodadas comparáveis, e parte do salto não estava no mundo: no `U4`,
*"a cobertura de lineage não é medida por gate nenhum"* recebeu **P2**; no `U5`,
*"o gate existe mas mede a fixture"* recebeu **P1** — e o primeiro é **pior**. Nada escrito
explicava a diferença; só a ordem em que foram vistos. Coluna que ninguém consegue
recalcular depois **não é prioridade, é humor**.

**A saída não é uma régua melhor: é parar de julgar.** `Prioridade` passa a ser **função
de quatro predicados medidos**, cada um com resposta binária e evidência obrigatória na
própria linha. Quem discorda de uma prioridade discute **um predicado**, não a impressão
geral.

| # | Predicado | Verdadeiro quando… | Evidência que a linha DEVE trazer |
|---|---|---|---|
| **A** | **alcança** | o defeito está num campo do payload publicado ou na superfície que a família lê — **medido**, não inferido do código | `campo.dot.path` ou `#Sx` + o valor observado |
| **R** | **reproduz** | o defeito está demonstrado **neste** corpus/run, não deduzido do desenho | run + o par observado (antes/depois, ou o valor contra o esperado) |
| **F** | **falsifica** | torna **falsa uma afirmação sobre o patrimônio/finanças da família**: número errado, contradição publicada, ausência afirmada como fato. **Não** basta confundir, navegar mal ou rotular de forma ambígua | a afirmação publicada + por que é falsa |
| **M** | **move decisão** | a afirmação falsa empurra uma decisão patrimonial concreta — amortizar × investir, realocar, aportar, prazo de IF, sucessão | a decisão nomeada + a direção do empurrão |

```
P0 = A ∧ R ∧ F ∧ M
P1 = A ∧ R ∧ F ∧ ¬M
   ∨ instrumento cujo VERDE é falso (medido)
   ∨ exposição de PII no publicado
P2 = A ∧ R ∧ ¬F                      (degrada a leitura, não falsifica)
   ∨ ¬R                              (exposição estrutural, sem incidência neste corpus)
   ∨ instrumento cujo VERMELHO é falso, ou incompleto sem ser falso
P3 = ¬A, com a decisão de NÃO abrir lane escrita na própria linha
```

**Três cláusulas, e cada uma existe por um erro cometido:**

1. **Estar na cadeia causal de um P0 NÃO promove.** A raiz e os elos intermediários
   registram-se no **produtor** (§6) e **herdam a lane do P0** — não ganham prioridade
   própria. No `U5` eu dei `P1` à raiz da Cadeia A e `P0` à sonda que a revelou, além do
   `P0` da própria cadeia: **três prioridades para um defeito**.
2. **Instrumento falso-verde é `P1` sempre**, mesmo sem alcançar o usuário — é o que
   **impede achar** `P0`. Falso-**vermelho** é `P2`: custa atenção, não esconde nada.
3. **Magnitude entra em `M`, nunca em `A` ou `F`.** Número publicado errado é errado; se o
   valor é pequeno, o efeito é `P1` em vez de `P0` — **não** `P3`.

**A régua NÃO substitui `Severidade`.** `Severidade` descreve o defeito (`Crítico`/`Alto`/
`Médio`/`Baixo`) e continua sendo julgamento do revisor; `Prioridade` passa a ser
computada. Quando as duas divergem — `Médio` com `P0`, `Crítico` com `P2` — a linha
**declara por quê**; é sinal útil, não erro.

#### Contrafactual medido (2026-09-01) — reclassificação das 43 linhas do `U4` e do `U5`

Não é *"a regra parece boa"*. Rodei-a contra as duas rodadas **antes** de escrevê-la, e a
**primeira versão reprovou**: sem o predicado `F`, `A ∧ R` promovia quase todo achado de
relatório a `P1`, porque essencialmente todos alcançam e reproduzem. O `F` é o que separa
*tornar falso* de *piorar a leitura*, e só existe porque o contrafactual o exigiu.

| efeito | linhas |
|---|---|
| **inalteradas** | 27 de 43 |
| **resolve a inconsistência que motivou a regra** | `PV12-02` sobe a `P1` (falso-verde) e encontra `PV13-12`, que já era `P1` — as duas passam a concordar |
| **acha inconsistência DENTRO do `U5`** | `PV13-09` (elogia e alerta a mesma reserva) sobe a `P0`, igualando-se a `RR9-04` (afirma e nega o mesmo imóvel) — mesma forma, letras diferentes |
| **desfaz a tripla contagem da Cadeia A** | `PV13-01` e `LC9-10` viram **ponteiros** da [[A40.l113]], sem prioridade própria |
| **rebaixa 4 do `U5`** | `LC9-06`, `LC9-07` (instrumento ambíguo, não falso-verde), `PV13-11`, `PV13-14` (confundem, não falsificam) → `P2` |
| **promove o que estava parado** | `RR8-04` sai de `P3` para `P1`: é número publicado **errado**, reproduzindo há **três rodadas**, parado por magnitude pequena — que agora pertence a `M` |

**O número que responde à pergunta:** sob a regra, `P1` fica **4 no `U4` contra 6 no `U5`**
— não 2 contra 12. O que sobra de diferença é real: o `U5` teve mais dois instrumentos
falso-verdes e um agrupamento de `P0` que o `U4` não teve.

**LIMITE DECLARADO.** `F` e `M` não são mecânicos como `A` e `R`: exigem ler a afirmação
publicada e nomear a decisão. A régua **estreita** a discricionariedade a dois predicados
com evidência obrigatória — não a elimina. E ela **não reclassifica retroativamente** lane
já arquivada: registro entregue é evidência datada. Divergência achada em rodada anterior
vira **nota**, nunca reescrita.

## 7. Namespace de códigos

`LC*` razão · `PV*` execução · `RR*` produto. O prefixo é o do **registro de
destino**, não o da lente que levantou ([[ADR-416]] D3).

Antes do primeiro uso de um prefixo novo, confirme que está livre:

```bash
rg -o '\b(PV|RR)-?[0-9]+\b' docs/
```

Código anterior a `U1` **não é renomeado** e é citado **qualificado**:
`RV4-07 (PIPELINE §r6)`. O par `(registro, rodada)` desambigua; o dedup dos
registros é `(dimensão, âncora, regra)` e nunca dependeu do código.

## 8. Formato dos três appends

Cabeçalho idêntico nas três seções, mudando só qual `§rN` é "este":

```
## r<N> — ws-<uuid8>-<AAAA-MM-DD>

> Rodada unificada **U<n>** · [[LEDGER-CERTIFY-active]] §r<a> · [[PIPELINE-REVIEWS-active]] §r<b> · [[REPORT-REVIEWS-active]] §r<c> (este).
> Run `<run8>` · executor `<sha8>` · preflight: <n> WARN declarados.
> Cru + síntese com valores: storage/<uuid>/reviews/U<n>-<data>/SINTESE.md (off-git).
> Escrituração: <lanes alocadas, ou a recusa e o motivo, ou `n/a — rodada sem P0`>.
> Cobertura: matriz 7×3 — <n> células sem cobertura, com motivo.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
```

O título `## rN — …` **não** muda de forma: é âncora durável e é o que as skills
leem para re-triar.

**Duas colunas que o runbook não definia:**

- **`Trilha`** — o id da lane que executa o achado, ou `sem lane — <motivo>`. Preenchida no
  commit único da F5; até 2026-08-30 ela não tinha definição aqui (só em
  [[LEDGER-CERTIFY-active]]) e no `U2` as seis lanes chegaram por backfill.
- **`Escrituração:`** no cabeçalho — o endereço da recusa da F5 passo 2. Sem ele a válvula
  *"ou declare que não vai"* não tinha onde ser declarada, e um gate satisfazível por
  silêncio é o que a rodada caça no produto.

## 9. Ledger de rodadas unificadas

Allocator de `U<n>` — escrever a linha **é** reservar. Não é registro: não tria, não
tem disposição, não tem cobertura.

A coluna `PR` recebe o **número** no fecho — `(esta PR)` apodrece assim que a PR mergeia, e
com a rodada num commit só ela volta a ter um referente único. `Estado ∈ {fechada, fechada
com ressalva (<caixas do §5 F7 que não fecharam>)}`: o `U2` foi registrado `fechada`
reprovando ≥2 caixas, porque o vocabulário não tinha o segundo valor.

| U | Data | ws8 | run8 | Seções | PR | Estado |
|---|---|---|---|---|---|---|
| **U1** | 2026-08-26 | `1b9f2cf5` | `c97b97c2` | LEDGER §r5 · PIPELINE §r9 · REPORT §r5 | (esta PR) | fechada |
| **U2** | 2026-08-29 | `1b9f2cf5` | `79a61e33` | LEDGER §r6 · PIPELINE §r10 · REPORT §r6 | 1820 | fechada com ressalva (E2, escrituração fora do commit) |
| **U3** | 2026-08-30 | `1b9f2cf5` | `3a5b9c7d` | LEDGER §r7 · PIPELINE §r11 · REPORT §r7 | (esta PR) | fechada com ressalva (E2 reprova; `REPORT × solidez` nula) |
| **U4** | 2026-08-30 | `1b9f2cf5` | `7d860f0b` | LEDGER §r8 · PIPELINE §r12 · REPORT §r8 | 1866 | fechada |

## 10. Débito de método (cross-cutting)

Append-only, datado. Só o que é furo **do encadeamento** — furo de uma skill vai para
o MOC dela.

- **2026-08-30 (fecho do `U4`) — sete furos, e os três primeiros são do mesmo osso: o denominador.**
  **Sete furos, e os três primeiros são do mesmo osso: o denominador.**

  1. **O predicado do E2 deste runbook era insatisfazível, e nenhuma das 3 rodadas
     anteriores o notou.** O §5 F1/F2 exige identidade de `{(stage,key) → (id, byte_size)}`
     entre o mapa pré e o pós-run. Medido: um run completo **re-extrai e cunha `id` novo em
     135 de 171 unidades** ⇒ o predicado literal **só pode sair vermelho**. Foi assim que o
     `U3` "publicou `E2 ✅` sobre um predicado que reprova" — ele lia, corretamente, o eixo de
     conteúdo, enquanto o texto exigia mais. **Regra: o veredito do E2 é sobre COMPOSIÇÃO
     (conjunto de chaves) + CONTEÚDO (`byte_size`) + PROCEDÊNCIA (`id`), com exit code por
     eixo.** O runbook §5 F1/F2 deve ser reescrito; até lá, o instrumento é a fonte.

  2. **E a minha primeira correção dele estava errada — do mesmo jeito.** Ao separar
     composição de conteúdo, chamei `id` de "ruído esperado". `id` é o **único**
     discriminador entre unidade **re-derivada por este run** e **herdada de outro**: das
     171, **34 são `extract_with_llm` herdadas de 11 runs distintos** e não podiam variar.
     Meu "conteúdo estável" tinha **denominador tautológico em 20%** — a mesma doença que a
     guarda anti-vácuo que eu **acabara de escrever** persegue nos cross-checks. Achado pela
     lente de invariante, não por mim. **Regra: denominador de conteúdo é run-scoped, e
     quem publica `n/N` declara de que população é o `N`.**

  3. **Dois números circulam para "as raízes do E5" e eu publiquei um sem dizer qual.**
     **42** é o número de chaves de topo do **payload**; **38** é o de raízes do **schema**.
     Ambos verdadeiros, populações diferentes. O cético corrigiu. **Regra: nomear a
     população junto do número, sempre — é literalmente o remédio que o `RR5-11` prescreve
     para o produto, e o método falhou nele primeiro.**

  4. **Instrumento que mora fora da árvore é instrumento não-gateado, e isso é medível.** Ao
     promover os cross-checks de `storage/` para `dev/` (pagando o item 2 do §10 do `U3`),
     eles passaram pelo `code-style-baseline` **pela primeira vez na vida** e reprovaram
     (P1 +4, P9 +1). Um instrumento que nunca fora linted vinha pontuando a saúde do
     código. **Regra: a promoção para `dev/` é parte do débito, não um extra — e o gate que
     ela destrava é evidência, não incômodo.**

  5. **Rodar o instrumento promovido de dentro de um worktree mede o nada, em silêncio.**
     `_PROJECT_ROOT` deriva da localização do módulo: o `mathoms.db` do worktree tem 4 KB e
     zero tabelas, e o `.env` não existe lá (o Fernet falha alto — esse pelo menos falha).
     **Regra: `procedencia()` imprime o DB resolvido antes de qualquer número, e o pin é
     `MATHOMS_DATABASE_URL` absoluto + `MATHOMS_FERNET_KEY` explícito.**

  6. **Rebaixar instrumento na F3.d obriga a re-executar a F3.c — e desta vez a resposta
     MUDOU.** A regra é do `U1` (item 3), foi repetida pelo `U2` (item 3) e **violada** por
     ele. Aqui a perna de valor do razão caiu **depois** de a F3.c ter rodado; a tabela foi
     re-emitida (v2) e o braço cego re-executado. Resultado medido: **3 alavancas caíram de
     rebaixadas para inadmissíveis, 1 subiu a admissível, o nº 1 mudou e a forma da
     justificativa migrou de "vale mais" para "é a única demonstrável sem valor"**. É a
     prova empírica de que **anotar a refutação não basta** — a v1 fica preservada como
     `_STALE`, não como veredito.

  7. **A taxa de duplicação de achado de produto foi de ~2/3, e ela é o sinal, não o ruído.**
     Dos meus 5 candidatos de prior art, **5 já estavam registrados**; no lote C do cético,
     **4 de 6**, e **três deles mediam MENOS do que o registro existente já media**. Um
     corpus revisado 4 vezes não devolve achado novo de produto na mesma taxa — devolve
     **denominador** para achado que já existe. **Regra: a rodada que não distingue "novo" de
     "medição de conhecido" infla o próprio placar e faz o gate de saída da sprint parecer
     mais longe do que está.**

  **Corolário sobre contagem por proxy** (atravessa 6 e 7): contei rodapé de `confiança`
  como proxy de bloco de risco e **quase confirmei um achado falso** ("nem o PDF alcança os
  12 riscos"). A presença do **título** refuta: tela 5/12, print **12/12**, PDF **12/12**. O
  cético do lote C bateu no mesmo modo de falha de forma independente. **Proxy de contagem
  exige validação contra a entidade antes de virar veredito.**
- **2026-08-30 (fecho do `U3`) — a rodada mede a distância do PRODUTO ao HEAD e nunca a do
  INSTRUMENTO.** Três medições desta rodada, todas minhas:
  1. **O instrumento que pontua a KR-B mudou entre os dois runs e eu publiquei "idêntico".**
     A regra nº 5 acima — que **eu escrevi no fecho do `U2`** — fixa o pathspec
     `pipeline backend scripts config frontend/src`. O instrumento vive em `dev/` e em
     `storage/`, e **nenhum dos dois está lá**. Um commit reescreveu `certify_entregue`
     justamente para fechar um falso-verde no modo que pontua a KR-B, e a comparação
     atravessou isso em silêncio.
     **Regra:** o `git log` do intervalo roda **duas vezes** — produto e **instrumento**
     (`dev .claude/skills`) — e a linha do instrumento é **obrigatória** no cabeçalho.
     Nenhum "idêntico" pode ser publicado atravessando mudança de instrumento sem dizê-lo.
  2. **Copiei o instrumento do diretório da rodada anterior e herdei a versão pré-conserto.**
     O `xchecks.py` do `U2` congelou na versão de antes das correções que a própria `U2` fez
     nele; o X2 comparou **zero** células em 2 baldes e o X3 reportou 647 divergências de
     rótulo. **A guarda anti-vácuo não rodou porque o arquivo que a contém não era o que foi
     copiado** — a caixa foi satisfeita lendo o runbook, não executando-o.
     **Regra:** antes do X5, emita `(sha256 do executável, sha256 da fonte canônica)` para
     cada instrumento que a rodada vai rodar. Divergência **aborta**. E o corolário
     estrutural: **instrumento executável não mora no diretório da rodada** — ele vai para
     `dev/` (versionado, diffável, gateado) e o `_state.json` guarda `instrumento_sha`.
  3. **Ao "propagar o conserto" eu sobrescrevi o baseline congelado da rodada anterior.**
     Os dois `xchecks.py` ficaram com o mesmo mtime; os números do §r6 já não são
     reproduzíveis com o instrumento que os produziu. É a patologia que o `LC6-01` declara e
     que a política de `_HISTORY` proíbe. **Regra: diretório de rodada é imutável depois do
     fecho.** Conserto de instrumento avança o `dev/`; nunca retro-edita rodada passada.
  4. **`E2 ✅` foi publicado sobre um predicado que REPROVA.** O runbook define o mapa como
     `{(stage,key) → (id, byte_size)}` e exige **identidade**; duas unidades mudaram conteúdo.
     Li o delta 1→2 como ruído. **Regra:** o veredito do E2 é sobre o mapa **inteiro**, e
     `byte_size` alterado em unidade que alimenta balde rebaixado condiciona o veredito dele.
  5. **O gate de cobertura conta a célula, e o mecanismo migra de célula.** O `U2` flagrou
     `REPORT × correção`; a regra virou caixa; e no `U3` a **mesma** patologia apareceu em
     `REPORT × solidez-financeira`, nula e não declarada. **Regra:** a caixa não é por célula
     nomeada — é *"toda dimensão bloqueada pela ordem de julgamento devolve
     `BLOQUEADA(<veredito que falta>)`"*, em qualquer célula.
  6. **Cinco das oito regras do `U2` reprovaram em artefatos escritos depois da correção.**
     As que têm **verificador executável** pegaram (a F5 num commit só, o
     `check_sintese_anterior`); as que viraram **prosa numerada** não. Regra sem verificador
     é documentação, e esta rodada é a medição disso.
- **2026-08-29 (fecho do `U2`) — seis furos, e quatro deles são o MESMO furo.** A rodada
  cometeu seis auto-defeitos de instrumento e o crítico de completude generalizou-os em
  regras. As duas primeiras são as que mais custam:
  1. **Nome de chave tirado da prosa do achado, não da declaração do produtor.** Quatro
     dos seis auto-defeitos são isto: `vehicle_id`/`veiculo_id`, `itens`/`dados`,
     `YY/MM`/`YYYY-MM`, `components:`/`charts:`. O quinto quase aconteceu com o rótulo
     de uma seção (`"Notas metodológicas"` vs a string que o componente realmente emite).
     **Regra:** todo check que decide por presença/ausência de chave ou rótulo **importa o
     nome do produtor** (`from <módulo> import <constante>`, `yaml.safe_load(...).keys()`,
     a string literal do `.tsx`) **ou publica um controle positivo que dispara**. Check sem
     controle positivo sai `INAPLICÁVEL` — nunca ✅ e nunca achado.
  2. **Meça o denominador antes de imprimir o veredito.** Duas das três correções da F3.a
     não foram erro de valor, foram **vácuo silencioso**: o X2 comparou zero células em 2
     de 3 baldes e imprimiu ✅; o X3 comparou interseção vazia e imprimiu 647 divergências.
     **Regra:** todo cross-check publica `n_comparado` **e** `n_esperado` na mesma linha do
     veredito; `n_comparado == 0` ou `< n_esperado` é `INAPLICÁVEL`, com o par impresso. A
     guarda anti-vácuo é do **formato de saída**, não de cada check.
  3. **Rebaixar instrumento invalida a tabela de condicionamento por construção.** O item 3
     do `U1` mandava re-rodar o condicionamento quando um cross-check cai. Esta rodada
     **violou a própria regra**: o X1 caiu para "não mede o artefato entregue" **depois** da
     F3.a, e a tabela — que deriva `conservado (parcial)` do mesmo instrumento — nunca foi
     re-emitida. **Regra:** a tabela carrega `instrumento + versão` por linha; rebaixar o
     instrumento marca as linhas dele `STALE`, e a F3.c **recusa** rodar com linha `STALE`
     na entrada. Anotar a refutação não basta — o `U1` já disse isso, e a prova de que não
     bastou é esta rodada.
  4. **O gate de cobertura conta reivindicante, não resposta.** `REPORT × correção` passou
     verde sem poder ter sido respondida: a ordem de julgamento a bloqueia até o veredito do
     razão, e o veredito é `sem-veredito` em 24 de 35 blocos. **Regra:** a célula tem **dois**
     estados — `reivindicada` e `respondida` — e a F4 reprova em `reivindicada ∧ ¬respondida`.
     Lente bloqueada devolve `BLOQUEADA(<veredito que falta>)`, que é resposta válida;
     silêncio não é.
  5. **A lista de "abertos" do brief vem do MOC, e o MOC atrasa o diff.** Entraram **33
     commits** em código de produto entre o executor do run anterior e o deste; o brief nomeou
     **7** consertos. Pelo menos 5 achados declarados ABERTOS já tinham fix mergeado — e um
     "aberto" mal classificado faz a lente **descartar** o sinal como re-descoberta, que é a
     troca exatamente errada (um "fechado que não segura" é achado de alta prioridade).
     **Regra:** a lista de fechados **não vem do MOC** — vem de
     `git log --format='%h %s' <executor_anterior>..<executor_deste_run> -- pipeline backend scripts config frontend/src`,
     cruzada por âncora com os `procede-aberto`. Achado cuja âncora apareça no
     `git diff --name-only` do intervalo entra na classe **"verifique se o conserto segura"**.
     Extensão do item 12 do `U1`, que só cobria o `main` andando **durante** a rodada.
  6. **"Não medido pelo razão" foi lido como "sem instrumento", e a disposição foi para a
     lane errada.** O carimbo `sem-veredito` foi repetido 24 vezes atribuindo a cegueira ao
     razão. Medido: `lineage_debug_whitelist()` tem **8 campos**, e **26 das 31 raízes E5
     consumidas (84%) não têm rastro nenhum** — os blocos são cegos porque o **registro de
     lineage** para em 8 campos, não porque falte balde. Consequência: 21+ linhas ficaram
     penduradas numa lane cujo desenho (registry chaveado em **baldes do E4**) não pode
     fechá-las; e 2 caíram por regra da própria tabela, porque as raízes **traçam**.
     **Regra:** antes de carimbar um bloco `sem-veredito`, rode a whitelist de lineage sobre
     as raízes que ele consome. O carimbo é **ternário**: `traça e a base tem veredito` ⇒
     herda · `traça e a base é cega` ⇒ `não-verificável`, dono da base · `não traça` ⇒ o
     defeito é do **registro de lineage**, e a dona é a lane de lineage.
  7. **Antes de publicar re-triagem de achado herdado, `rg` a dimensão nas lanes da sprint.**
     A rodada gastou uma medição para redescobrir — e quase publicou como novidade — algo que
     uma lane `shipped` em `main` já havia medido e cuja seção nomeia o produtor real. Lane
     entregue carrega medição que o registro ainda não absorveu.
  8. **A varredura de superfície foi aberta e não fechada, e no grão errado.** A coluna
     "reivindicada por" ficou vazia no artefato em disco, e o inventário foi de **18 seções**
     enquanto o layout declara **60 componentes** dentro delas. A costura do `U1` era de
     seção; a de **componente** continua aberta e não foi sequer inventariada. E um artefato
     coletado (`anchors.json`, com altura por seção) **nunca foi lido por ninguém** — uma
     seção com 4% da altura da maior é o sinal mais barato de "habilitada e vazia".
- **2026-08-26 (fecho do `U1`) — doze furos do encadeamento, achados pelo crítico de
  completude.** Os quatro primeiros são de instrumento e os dois últimos são da *forma* de
  rodar em painel:
  1. **Condição declarada exige enumeração.** A rodada escreveu "procede sobre 6 avisos
     retidos" e **não enumerou os 6** no brief das lentes. Eu os havia medido e não os
     passei adiante. Condição que não se enumera não se desconta — todo veredito de
     `solidez-financeira` ficou condicionado a um conjunto anônimo.
  2. **A tabela de condicionamento é chaveada pelo consumidor, não pelo produtor.** Ela teve
     7 linhas — os baldes do E4 — enquanto toda decisão da rodada é tomada sobre os blocos do
     E5. Medido: a maioria das âncoras verificadas do parecer repousa em base sem veredito ou
     explicitamente não-dimensionável, e mesmo assim gerou prescrição publicada. O furo do
     bloco de proteção não foi lapso; foi consequência estrutural. **Linha = bloco do extrato
     de decisão; bloco sem linha ⇒ `sem-veredito`, e alavanca ancorada nele é inelegível a
     nº 1 por default.**
  3. **Refutar instrumento reabre o condicionamento.** Um dos cross-checks caiu como defeito
     de produto e virou defeito do instrumento, e a tabela que usava esse achado como defeito
     aberto de um balde — e dele derivava o sinal do viés — **nunca foi re-rodada**. A regra
     de sobrevivência ao pior extremo rodou contra um extremo sem fonte. Não basta anotar a
     refutação.
  4. **Toda medição publica seu comando.** O brief entregou sete resultados e zero caminhos
     de re-medição, sobre um run cujo próprio `run_meta` declara reprodutibilidade não
     garantida. Isso torna os achados irrefutáveis pelo próximo revisor — o oposto de
     evidência.
  5. **Superfície cronometrada e descartada não é superfície observada.** O PDF foi capturado
     e só os dumps de texto foram disponibilizados às lentes; a viewport mobile teve captura
     de imagem e **nenhum** dump de texto, ficando integralmente não observada.
  6. **Particionar por lente cria costura, e a costura é onde a evaporação acontece.** A
     pergunta "qual é a ação nº 1" foi roteada para uma lente, e a superfície de plano de ação
     caiu entre duas — ninguém a leu, e ela continha a resposta. Uma review de relatório lê a
     página de cima a baixo e bate nisso na primeira passada. **Conserto: varredura explícita
     "nenhuma lente reivindicou isto" sobre a superfície renderizada, antes de fechar a matriz.**
  7. **Inventário de ação é plural.** Antes de responder "qual a nº 1", listar todos os
     inventários que a superfície publica e reconciliá-los. A rodada respondeu pelo menor.
  8. **Regra de admissibilidade é filtro, não peso.** Procedência nula retira a alavanca;
     nenhum argumento *a fortiori* a traz de volta. Uma lente aplicou a regra errada.
  9. **Verificador auto-declarado mede o denominador dele.** O fechamento de ancoragem cobriu
     cerca de metade dos numerais reais, porque o schema não permite âncora em vários campos.
  10. **Suíte de checks com severidade constante não é gate** (PIPELINE §r9 PV9-04).
  11. **Contador de guardrail só é evidência se o mecanismo estiver vivo** (PV9-05).
  12. **Re-medir a distância para `main` no fecho, não só no preflight.** O `main` andou 5
      commits durante a rodada e um deles **fechou um achado** que já havia sido reportado
      como aberto. O `run_meta` declarava o desvio e nada foi condicionado a ele. O gate
      imprime `git log --oneline <executor>..origin/main` — nomeia o delta em vez de contá-lo
      — e achado cuja âncora caia em `git diff --name-only` do intervalo sai marcado
      `re-verificar contra HEAD`.
- **2026-08-26 (F0–F2 do `U1`).** Três defeitos deste runbook só apareceram ao
  executá-lo, e os três são da mesma família — **regra escrita sem exercitar o
  relógio**: o write-ahead mandava gravar um id que ainda não existe; a F1 mandava
  escrever no git numa fase que a F5 declara ser a única a tocar o git; e o nome do
  diretório embutia um `run8` desconhecido na F1, quebrando o path da retomada.
  Corrigidos acima. **Runbook não exercitado é hipótese**, e a primeira execução é
  parte da entrega, não a validação dela.
- **2026-08-26 (limpeza de pré-condição do `U1`).** Havia **dois** runs pausados, e o
  check `run-em-voo` mostra só o mais recente — encerrar um deixaria o outro. Pior: um
  run em `needs_review` **não tem porta de saída** (`cancel_pipeline_run` recusa por
  desenho e as ações de produto só retomam, gastando LLM), então foi preciso escrever
  `cancelled` pela ORM. Mesma patologia que a [[A40.l27]] consertou para `resuming`.
- **2026-08-26 (gate `sync-main` over-bloqueia).** O gate reprovou o disparo do `U1`
  porque o checkout estava 1 commit atrás de `origin/main` — e o delta era **um único
  arquivo em `dev/`**, que o pipeline não importa. O predicado mede *distância*; o que
  importa é se os commits ausentes tocam `pipeline/`, `backend/`, `scripts/` ou
  `config/`. Disparado com desvio **declarado e medido** no `_state.json`. Refinar o
  predicado é candidato a lane; enquanto não for, todo override vai declarado.
- **2026-08-25 (preparação, antes do `U1`).** O guard de run em voo da
  `pipeline-review` filtrava um literal inexistente e omitia dois status não-terminais;
  o predicado de poll omitia um status terminal. Ambos consertados derivando do enum.
  A lição que fica para o encadeamento: **um defeito no launcher não aparece como
  falha — aparece como rodada que mediu a coisa errada.**

- **2026-09-01 (fecho do `U5`) — seis furos, e o primeiro é o mais caro que o encadeamento já achou em si.**

  1. **Nenhum cross-check desta rodada percebeu que metade do relatório mudou.** X2, X3,
     X3b, X5, E2 e a sonda LC06 **todos fecharam** — e, no mesmo run, **95 de 400**
     escalares numéricos do payload publicado se moveram, com `patrimonio.bruto` caindo
     **48,1%** sobre corpus documental idêntico. Os checks medem **conservação entre
     stages** e **proveniência de execução**; nenhum mede **o payload publicado contra o da
     rodada anterior**. A varredura que achou (diff escalar campo-a-campo do view-model
     entre duas rodadas) **não está no runbook**. **Regra: a F3.a passa a exigir o diff
     escalar do payload publicado contra o baseline da rodada anterior, com o par
     `n_moveram`/`n_comparado` publicado.** Custa um comando e é o sinal mais forte da
     rodada inteira. Precedente da doença: um conjunto de checks internamente consistente
     pode ser **globalmente cego**, porque todos partilham o mesmo eixo.

  2. **Atribuição de mecanismo herdada de comentário de código não é medição.** Publiquei,
     na primeira versão da síntese, que o zero da dívida vinha de `safe_float` sobre objeto
     por ano em `patrimonio_resolvers.py:219/:225`, *"com a leitura correta na linha 567"* —
     herdado do comentário em `endividamento_analyzer.py:138`, que nomeia
     `_total_dividas_for` como *"defeito vivo"*. **Errado nas duas metades:** o objeto por
     ano já existia no run anterior, quando o número saía **certo**, e a linha 567 é a
     **ofensora**, não a leitura correta. O comentário é verdadeiro sobre um defeito
     **dormente**. **Regra: atribuição de mecanismo exige A/B entre os dois runs no
     produtor** — comentário verdadeiro pode descrever caminho que não dispara.

  3. **A síntese em HTML pode corromper em silêncio, e uma rodada publicou assim.** O `U4`
     tem **20** marcadores `**` vazados e **5** parágrafos truncados no
     `SINTESE.html`, porque converteu **linha a linha**: cada linha de um parágrafo com
     wrap virou um `<p>` e o negrito que abria numa linha fechava na seguinte. `U2` e `U3`
     estão limpos ⇒ é regressão, não padrão. **Regra: o conversor junta as linhas do
     parágrafo antes do inline e ASSERE, antes de publicar, ausência de `**` e de
     `<p>` terminado em meia frase.** No `U5` esse guard **reprovou na primeira execução** e
     pegou defeito real: uma linha de wrap começando com `#1/#2` foi lida como título
     (ATX exige espaço depois das cerquilhas).

  4. **Cruzar lane irmã ANTES de alocar, e o ganho é grande.** Dois dos achados de
     superfície eram (a) **reincidência** de lane com fix mergeado — o guard de seção, cuja
     correção trocou um literal por outro — e (b) **reprodução esperada** de 4 lanes que
     seguem `open`. Sem o cruzamento seriam 5 achados novos; com ele são **1 reincidência
     com achado novo embutido** (o teste importa a própria constante ⇒ cego por construção)
     **+ 4 ponteiros**. O sinal de que você precisa cruzar: o achado tem número redondo e
     nenhuma lane citada.

  5. **Achado que mora em memória de sessão não é re-triado por rodada nenhuma.** O
     zeramento da dívida foi medido em 2026-08-19 e a recomendação *"abrir lane P0"* ficou
     na memória do executor. **Doze dias depois não havia lane nem linha em MOC** — `rg` não
     o encontrava. Ele só voltou porque o mesmo executor lembrou. **Regra: medição que
     recomenda lane entra no MOC da família na mesma sessão, mesmo sem lane** — a linha
     `sem lane · decisão: <motivo>` é o mínimo, e é o que torna o item re-triável.

  6. **`rg -r` é REPLACE, terceira ocorrência.** `rg -rn '<padrão>'` é lido como
     `-r n` e **reescreve o match por "n"** na saída: um campo `$.fluxo_caixa.janela`
     apareceu como `$.njanela`, e uma varredura de `"ano_referencia"` devolveu `n` no lugar
     do nome. **Regra: nunca `-r` em busca exploratória.** O sintoma é output com um `n`
     solitário onde devia haver o termo buscado.

## 11. Gates antes do commit

```bash
python3 dev/build_doc_index.py --inline # REGENERA — a lane nova churna _generated/
python3 dev/validate_frontmatter.py
python3 dev/check_doc_filename_id.py
python3 dev/check_doc_links.py
python3 dev/build_doc_index.py --check  # só agora o verificador
pre-commit run --all-files
```

Quando a F5 escreve lane, **três gates específicos a julgam** e vale conhecê-los antes de
apanhar deles: `dev/check_lane_transition.py` (exige linha na tabela do `_README` — foi o
que recusou o commit no `U2`), `dev/check_lane_status_predicate.py` (o `status` deriva de
`depends_on`) e o `doc-fk` (as arestas de frontmatter resolvem).

E a leitura humana que nenhum gate faz: **zero literal monetário, zero nome próprio**
nas três seções; âncora é `campo.dot.path` ou `arquivo:linha`, nunca um valor; o
título do achado é um **defeito**, não um dado.

## 12. Referências

- [[ADR-416]] — canônica desta rodada · [[ADR-343]] — estado durável · [[ADR-302]] —
  classe skill · [[ADR-347]] — canais autoritativos de remoção · [[ADR-173]] —
  hard-stop de budget · [[ADR-342]] — anti-silêncio.
- Registros: [[LEDGER-CERTIFY-active]] · [[PIPELINE-REVIEWS-active]] ·
  [[REPORT-REVIEWS-active]] · [[PARSE-CERTIFY-active]].
- Skills: [`ledger-certify`](../../../.claude/skills/ledger-certify/SKILL.md) ·
  [`pipeline-review`](../../../.claude/skills/pipeline-review/SKILL.md) ·
  [`report-review`](../../../.claude/skills/report-review/SKILL.md).
- Preflight: [`dev/preflight_unified_review.py`](../../../dev/preflight_unified_review.py).
- Forma do que a F5 escreve: `docs/_schemas/note-lane.schema.json` (frontmatter da lane) ·
  `docs/sprint/<X>/_README.md` (tabela + gate de saída) ·
  [`dev/lane_pickup.py`](../../../dev/lane_pickup.py) ·
  [`dev/check_lane_transition.py`](../../../dev/check_lane_transition.py).
