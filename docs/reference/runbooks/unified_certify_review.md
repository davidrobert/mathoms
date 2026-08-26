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

**Produz:** um `SINTESE.md` unificado (off-git, com valores), um working em
`_scratch/`, e três appends de seção — um por registro — num commit só.

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
  literal monetário ficam off-git.
- **Não implementa.** É análise: nenhum fix, nenhum PR de correção sai daqui. O
  entregável é diagnóstico priorizado e candidatos a lane.
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
  "appends": {"LEDGER": false, "PIPELINE": false, "REPORT": false}
}
```

**Regra write-ahead (a única que não pode sair errada):** grave `fired_at` **antes**
de disparar. O `run_id` não existe nesse instante — o trigger o cunha —, então grave-o
imediatamente **depois**, e deixe a retomada resolver a janela pelo `started_at`
(§2 item 2). A intenção precede o efeito; a retomada lê a **intenção**, nunca o efeito. F5 é a **única** fase que toca o git e é a **última** — os três appends
num commit só, para a rodada nunca existir pela metade em `main`.

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
reservar em dois lugares e fases é o preço de a F5 ser a única fase que toca o git.

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

Rode **antes** de qualquer lente. `X5` primeiro: se ele falha, todos os outros
estão atribuindo números ao run errado.

| # | Predicado | Falha significa |
|---|---|---|
| **X5** | Todo stage que `pipeline_stage_logs` declara `completed` tem ≥1 row em `pipeline_artifacts` com `pipeline_run_id == <run novo>`; e `review_snapshot.provenance.execucao_mista` é verdadeiro se algum stage consumiu artefato de outro run | A proveniência declarada é **falsa**. O lookup de já-processado é workspace-scoped, não run-scoped |
| **E2** | O mapa de seleção de F1 é **idêntico** ao pós-run | O corpus do razão mudou sob os pés da medição. Guarde com "nenhum run em status não-terminal no momento de F1" |
| **X1** | Por grupo: `tx_carregadas` sombra == persistido (**C1**); `executor_revision` do run == HEAD (**C2**); e a diferença de `transacoes_total` é **exatamente** a diferença do canal `cross_document_collapse` de `remocoes`, com os demais canais idênticos (**C3**, tol-zero) | O run cortou ou reteve rows que **nenhum canal declarado explica** — perda silenciosa, que é o que o ledger da [[ADR-347]] existe para tornar impossível |
| **X2** | O E4 re-derivado a partir do E3 **persistido do run** bate com o E4 persistido, em cents, por `(balde, categoria, mês)` | Categorizador não-determinístico, **drift de regra aprendida**, ou E4 estagnado vazando pelo workspace-latest. Pin obrigatório: contagem de `transaction_overrides` antes e depois |
| **X3** | **Vetorial**: para todo mês e balde, a série do view-model == `fluxo_mensal_detalhado`, em cents; e a soma dos meses == o total do balde | Escalar fecha e vetor não fecha ⇒ **deslocamento sum-preserving**. É a classe que a rodada inteira existe para pegar |
| **X3b** | `consolidacao_cross_documento.meses[]` bate, mês a mês, com a soma dos `remocoes[].cross_document_collapse.meses` dos E3 do run | O relatório **declara** um colapso diferente do que o razão executou |
| **X4** | Todo literal monetário do parecer, em cents, pertence ao conjunto de cents do E5 do mesmo run, ou deriva de fórmula declarada | Número ancorado pelo modelo, não pelo dado |

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

### F5 — Três appends, um commit

A **única** fase que toca o git, e a última. Escreva as três seções no formato do §8,
adicione as linhas ao ledger do §9, e **commite os três juntos**. Atualize `appends`
no `_state.json` só depois do commit.

### F6 — Débito de método

Registre no §10 os furos do **encadeamento** (os que não são de nenhuma das três
skills). Os furos que são de uma skill vão para o §Débito de método do MOC dela.

### F7 — Fecho

Resuma no chat, PII-scrubbed. Se o volume justificar, gere um dashboard navegável
como Artifact, sempre PII-scrubbed. Congele o diretório cru como baseline do próximo
`--compare`.

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
> Cru + síntese com valores: storage/<uuid>/reviews/U<n>-<data>/ (off-git).
> Cobertura: matriz 7×3 — <n> células sem cobertura, com motivo.

| Código | Dimensão | Severidade | Prioridade | Veredito | Disposição | Trilha |
|---|---|---|---|---|---|---|
```

O título `## rN — …` **não** muda de forma: é âncora durável e é o que as skills
leem para re-triar.

## 9. Ledger de rodadas unificadas

Allocator de `U<n>` — escrever a linha **é** reservar. Não é registro: não tria, não
tem disposição, não tem cobertura.

| U | Data | ws8 | run8 | Seções | PR | Estado |
|---|---|---|---|---|---|---|
| **U1** | 2026-08-26 | `1b9f2cf5` | `c97b97c2` | LEDGER §r5 · PIPELINE §r9 · REPORT §r5 | (esta PR) | fechada |

## 10. Débito de método (cross-cutting)

Append-only, datado. Só o que é furo **do encadeamento** — furo de uma skill vai para
o MOC dela.

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

## 11. Gates antes do commit

```bash
python3 dev/validate_frontmatter.py
python3 dev/check_doc_filename_id.py
python3 dev/check_doc_links.py
python3 dev/build_doc_index.py --check
pre-commit run --all-files
```

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
