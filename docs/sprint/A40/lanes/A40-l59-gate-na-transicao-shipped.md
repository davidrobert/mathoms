---
id: A40.l59
type: lane
title: "A transição para `shipped` ganha gate: ship_pr no frontmatter e PR visível no _README"
sprint: A40
plan: PLAN-report-trust
status: shipped
priority: P2
ship_pr: 1661
ship_date: "2026-08-24"
branch_slug: a40-l59-gate-na-transicao-shipped
owner: information-architect
adrs:
  - "[[ADR-302]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p2
  - area/docs
---

# A40.l59 — `gate-na-transicao-shipped`

> **Aberta em 2026-08-12**, no fechamento da rodada de follow-ups (decisão do
> dono). Origem: o gatilho de promoção que a própria skill `lane-closeout`
> declara — *"se a classe estrutural voltar a escapar depois de N usos, aí sim
> vale promovê-la a gate na **transição** (diff que flipa `status: shipped`) —
> gatear por PR fica verde-falso quando a lane vira 2 PRs"*. O N chegou.

## Problema

A classe "PR mergeado invisível na doc da sprint" escapou o suficiente para
provar que detecção pós-merge não basta:

- No fechamento da [[A40.l7]] (2026-08-11), o `_README` não registrava o #1375 —
  **terceira ocorrência declarada na sprint**, anotada na época como candidata a
  gate.
- Nos PRs seguintes da [[A40.l34]] (#1377, #1383, #1394) o registro só não
  falhou porque foi feito **preemptivamente, por disciplina** — que é
  exatamente o que um gate existe para não depender.
- Em 2026-08-12, a nota do §Lanes do `_README` mede **10 lanes no disco fora da
  tabela** (l38–l42, l44, l45 nomeadas; l47–l49 abertas pelo #1411 sem linha) —
  a mesma classe, na direção lane→tabela.

O custo é conhecido e está medido no cabeçalho da skill: ~2,5 PRs corretivos de
doc por semana entre 2026-06 e 2026-08, porque a pergunta foi feita **depois**
do merge.

### Caso de origem medido em 2026-08-17 — a variante que o escopo atual não pega

A avaliação de pickup da A40 achou **3 lanes** cujo `status` divergia de `main`.
Duas delas são a classe já descrita — no estado **em que foram encontradas**, e
as três já corrigidas no **#1497**: [[A40.l5]] estava `in_progress` com PR0–PR4
mergeados; [[A40.l60]] estava `open` com o PR1 entregue no #1480 sem constar. A
terceira é **uma variante que o gate desta lane, como escopado, não alcança**:

**[[A40.l58]] ficou `blocked` 3 dias depois de a dep fechar.** O gate desta lane
dispara no diff que flipa `status: shipped` — mas aqui **o diff que precisava
existir nunca foi escrito**: ninguém abriu a l58 para nada. O evento não é uma
transição malfeita; é uma **transição ausente**. Gate sobre diff não vê o
arquivo que não mudou.

**Por que ninguém percebeu.** O
[`_sprint_current_renderer`](../../../../dev/_sprint_current_renderer.py) faz o
que deve: dá seção própria ao `blocked` (`:44`) e imprime a dep pendente. A
linha publicada era **`⛔ dep pendente: A40.l5 (in_progress)`** — coerente
consigo mesma, porque a l5 **também** estava stale. **Dois status stale se
mascaram mutuamente**, e o painel fica internamente consistente e globalmente
falso. Nenhuma leitura do painel desfaz; só cruzar frontmatter × PRs de `main`.

**Consequência para o escopo desta lane** — a decidir no co-design, não aqui:
o par natural do gate de transição é um **gate de coerência**, que não olha
diff e sim estado: *"toda lane `blocked` cujo `depends_on` está terminal"* e
*"toda lane não-terminal cujo `branch_slug` tem PR mergeado"*. O primeiro é
barato (`dev/lane_pickup.py` já computa terminalidade de dep). O segundo é a
mesma consulta que esta lane já precisa fazer para achar o `ship_pr`.

> **Relação com a §Pendência 13** (aberta em `main` pelo #1414, mesmo dia): aquela
> é sobre **alocação de id** sob paralelismo e é *owner-gated* (muda política de
> repo). Esta é sobre **registro do que já foi entregue**. Escopos distintos, mas
> a mesma raiz — 4 arquivos gerados como ponto de contenção global. Se a opção (b)
> da pendência 13 (merge driver + regeneração no pre-commit) for escolhida, o hook
> desta lane monta no mesmo lugar.

## Escopo

> ⚠️ **Corrigido por medição em 2026-08-24 — leia o §Ataque antes do pickup.**
> O item 1 tem o predicado **errado** (`_README` sozinho; o certo é
> `_README` ∪ `_HISTORY` — §Ataque §3) e o item 2 cita um número que hoje é
> outro (§Ataque §6). O texto abaixo fica: é o co-design de 2026-08-12, não um
> snapshot a reescrever. O §Escopo **efetivo** é este mais o item 4 abaixo.

Hook de pre-commit disparado **pela transição**, não pelo PR:

1. Diff que flipa `status:` de uma lane para `shipped` exige, no mesmo commit:
   `ship_pr` e `ship_date` no frontmatter, **e** o PR citado presente no
   `_README` da sprint correspondente.
2. Diff que **cria** arquivo de lane exige a linha correspondente na tabela
   §Lanes do `_README` — fecha a direção que produziu as 10 órfãs.
3. O hook **não** re-implementa a `lane-closeout`: o julgamento semântico
   (números, consistência, precisão) continua na skill; o gate cobre só a
   metade estrutural que `check_closure.py` já sabe checar, movida para
   **antes** do commit.
4. **(2026-08-24)** Gate de **coerência** — não olha diff, olha estado. Entra
   nesta lane porque é o único dos dois mecanismos que alcança o caso de origem
   do §Problema (§Ataque §1). Metade `depends_on` **já existe** e está em
   pre-commit (`dev/check_lane_status_predicate.py`, os dois sentidos); o que
   falta é o cruzamento **lane não-terminal × entrega já em `origin/main`**, que
   é o que deixou a [[A40.l5]] `in_progress` com PR0–PR4 mergeados e, por
   tabela, mascarou o `blocked` da [[A40.l58]]. Só a metade **offline**
   (hermética, sobre `git log origin/main`) — cruzamento que exija rede é
   **não-objetivo declarado**, pelo precedente de fragilidade medido em
   `dev/check_scheduled_workflows.py` (leitura de API obsoleta trava o repo).

## Critério de aceite

> ⚠️ **Três destes critérios foram corrigidos por medição em 2026-08-24**
> (§Ataque §1/§3/§4/§5). Itens afetados marcados `⚠️ corrigido`. O item da prova
> retroativa mandava reproduzir um caso que o §Ataque provou **verde sob o
> próprio gate** — critério inexecutável governando o pickup.

- ⚠️ **corrigido** — **Prova retroativa por amostra medida**, não por anedota: o
  §Ataque §2 mede **23 de 42** transições da A40 que seriam barradas. Reproduzir
  contra o hook **≥1 caso nomeado de cada eixo** — `ship_pr` ausente no commit do
  flip (l71/#1511, que trazia o número só no título do commit) e PR não citado
  (l19/#1241, hoje na linha 732 do `_README`) — citando entrada e veredito.
- ⚠️ **corrigido** — **Casos negativos declarados, cada um com rota nomeada.**
  (i) l7/#1375 **não dispara** e não deve: é transição **ausente**, classe do
  §Escopo item 4 (coerência). (ii) As **6 lanes self-closing** (`ship_pr` == PR
  do próprio flip) **não podem** disparar — rota é a sequência prescrita abaixo.
  Caso negativo sem rota nomeada é como gate fecha sintaxe e deixa a classe viva.
- **Predicado pinado, nos dois eixos** — o §Ataque §3 e §6 mostram que os
  predicados naturais **discordam em casos vivos**. Declarar por escrito:
  citação do PR vale em `_README` **∪** `_HISTORY` (senão o gate pune o
  `split_sprint_history.py`, que o CLAUDE.md manda rodar); e a presença da lane
  é **linha na tabela §Lanes**, não menção em qualquer lugar do `_README`.
- Polaridade certa ([[ADR-302]] e a lição da sprint): o gate **impede** o
  estado ruim de entrar, não o detecta depois — provado por **mutação nos dois
  sentidos** (planta a violação: vermelho; corrige: verde).
- ⚠️ **corrigido** — **Superfície declarada.** O §Ataque §5 mede que o CI só
  roda `pre-commit run --all-files`, onde `git diff --cached` volta vazio: gate
  de transição **passa vazio no CI** e vive só na máquina de quem commita.
  Declarar qual é a entrega — local-only assumido, ou step de CI com
  `--from-ref`. Sem essa linha, "polaridade certa" afirma prevenção sobre
  mecanismo que talvez não rode.
- Gate na transição, nunca por PR — lane que vira 2 PRs não pode dar verde
  falso.
- ⚠️ **corrigido** — Falso-positivo declarado: flip de `status` em rebase/revert
  tem escape documentado (a mesma classe do `--no-verify` proibido: corrigir a
  causa, nunca bypassar). **E a classe medida no §Ataque §4** — a lane que fecha
  a si mesma: no 1º commit local o `ship_pr` ainda não existe (sai do
  `gh pr create`). Não é impossível, é **ordenação forçada** — commitar o flip
  **depois** de abrir o PR; 2 das 6 fizeram exatamente isso. A sequência
  prescrita entra na mensagem de erro do hook, senão o gate é descoberto por
  quem bate nele.

## Colisão declarada

> ⚠️ **Corrigido em 2026-08-24 (§Ataque §7).** O caminho é `.claude/skills/
> lane-closeout/references/check_closure.py`, e ele é **pós-merge por
> construção** (`resolve_from_pr`/`_merge_sha` partem de um PR já mergeado). No
> sentido pre-commit não há PR de onde resolver: o compartilhável são os
> **predicados**, nunca a resolução.

`check_closure.py` (da skill) e o hook novo compartilham a definição da metade
estrutural — extrair os **predicados** para módulo comum em vez de duplicar.

## Ataque (2026-08-24) — medido antes do pickup

Método: as 42 transições da A40 que declaram `ship_pr` foram rodadas contra o
predicado do §Escopo 1, reconstruindo a árvore no commit que introduziu
`status: shipped` (`git show <flip>:<arquivo>`). Os casos retroativos do
§Critério foram reproduzidos um a um.

### 1. O caso-bandeira do §Problema não é reproduzível — e não por acaso

**[[A40.l7]]/#1375 fica verde sob este gate nos dois instantes.** Medido:

- `#1375` (`29087eb1`) **não tocou `docs/sprint/A40`** — nem o arquivo da lane,
  nem o `_README`. Não houve flip de `status`. Gate de transição não dispara:
  não existe diff de transição.
- `#1376` (`34de8f14`), o PR corretivo, flipou `status: shipped` **e** inseriu
  `#1375` no `_README` no mesmo commit (`grep -c` no `_README`: 0 antes, 1
  depois). Sob o §Escopo 1 esse commit **passa**.

O caso citado como origem da lane é, na verdade, a **variante de transição
ausente** que a própria lane isola no caso da [[A40.l58]]. Isso reordena o
escopo: o gate de coerência descrito como *"par natural"* não é
complemento — é **o único dos dois que pega o caso-bandeira**. O §Escopo,
como está, entrega um gate que não teria evitado o evento que o motivou.

### 2. A classe do §Escopo 1 está viva — 23 de 42 transições seriam barradas

| Eixo | Transições | Exemplos |
| --- | --- | --- |
| Passam | 19 | — |
| `ship_pr` ausente no commit do flip | 13 | l1 #1118 · l16 #1159 · l18 #1258 · l71 #1511 |
| PR não citado no `_README`/`_HISTORY` | 10 | l19 #1241 · l27 #1265 · l56 #1483 · l69 #1578 |

Spot-checks contra formato de citação (o predicado não é artefato de `grep`):
`#1241` está ausente do `_README` no commit do flip e hoje vive na linha 732;
a l71 flipou em #1517 com o número **no título do commit** (*"shipped #1511"*)
e sem o campo no frontmatter — que só entrou em #1533.

**55% é piso, não teto.** A medição roda sobre commits **squashados** de `main`
— a visão permissiva, onde flip e `ship_pr` de PRs distintos aparecem juntos.
O hook roda por commit local, antes do squash.

### 3. `_README` é o denominador errado (conflito com política mandatória)

O §Escopo 1 exige o PR *"presente no `_README` da sprint"*. Medido na A40: **24
números de PR vivem só no `_HISTORY`**, e 4 lanes `shipped` (l1 #1118, l3 #1124,
l4 #1139, l28 #1269) têm o `ship_pr` citado **apenas lá**. Não é desleixo — é o
`split_sprint_history.py` que o CLAUDE.md **manda** rodar, e que o
`check_sprint_readme_size.py` cobra. Gate que só olha `_README` pune a política
e cria incentivo a inflar o arquivo que outro gate pune. **O predicado é
`_README` ∪ `_HISTORY`.**

### 4. Falso-positivo não declarado: a lane que fecha a si mesma

O §Critério declara escape só para rebase/revert. Falta a classe medida: **6 das
42 têm `ship_pr` == o PR do próprio flip** (l2 #1368, l20 #1278, l23 #1334,
l24 #1157, l26 #1339, l32 #1335). No primeiro commit local o número **ainda não
existe** — sai do `gh pr create`. Não é impossível, é **ordenação forçada**
(commitar o flip depois de abrir o PR): 2 das 6 fizeram exatamente isso. As
outras 4 seriam barradas. O escape precisa estar no §Critério, com a sequência
prescrita — senão o gate é descoberto por quem bate nele.

### 5. O gate não existe no CI

O único caminho de enforcement no CI é `pre-commit run --all-files`
([ci.yml:503](../../../../.github/workflows/ci.yml)); **nenhum workflow usa
`--from-ref`/`--to-ref`**. O precedente da casa para gate de diff é
`dev/check_float_money.py`, que lê `git diff --cached` — vazio sob
`--all-files` ⇒ **passa vazio no CI**. Um gate de transição herda isso: roda só
na máquina de quem commita, em worktree que pode nem ter `pre-commit install`.
Decisão a tomar no co-design, não a descobrir depois: ou se aceita gate
local-only (e o §Critério diz isso), ou entra um step de CI com `--from-ref`.

### 6. O §Escopo 2 está certo — mas o predicado decide o veredito

Direção lane→tabela, medida hoje: **as 10 órfãs de 2026-08-12 foram fechadas**
(#1497 e seguintes). Mas a classe tem **instância viva de 2 dias**: a
[[A40.l77]], criada pelo #1643 em 2026-08-24, **não tem linha na tabela §Lanes**
— só numa tabela de roteamento do §Inventário do r7 (linha 1426). E o cabeçalho
da §Lanes ainda declara **"75 no disco · 75 nesta tabela"** com 76 no disco: o
contador à mão drifta junto.

Os dois predicados naturais **discordam no único caso vivo**: *"id aparece no
`_README`"* dá 76/76 limpo (gate no-op); *"id tem linha na tabela §Lanes"*
acusa a l77. Pinar qual é o predicado é parte do escopo, não detalhe de
implementação — e a l77 é o caso de teste pronto.

> **Fecho da instância, 2026-08-24 (mesma sprint, algumas horas depois).** O
> closeout desta lane fechou os dois: a l77 ganhou linha na tabela §Lanes e o
> cabeçalho virou `76 · 76`. As duas frases acima seguem no presente **porque
> descrevem o estado medido no ataque** — reproduzível em
> `git show 7ed61f04:docs/sprint/A40/_README.md`. O predicado escolhido foi o
> estrito (linha de tabela), e é o que o `check_creation` implementa.

### 7. Correções ao §Colisão

`check_closure.py` (461 linhas) **é pós-merge por construção**: `resolve_from_pr`
e `_merge_sha(pr)` resolvem lanes a partir de um PR **já mergeado**. No sentido
pre-commit não há PR de onde resolver. O compartilhável são os **predicados**,
nunca a resolução — "extrair para módulo comum" subestima o corte. Some-se que
`dev/_lane_table_parsers.py` já existe (hoje só consumido pelo
`migrate_lanes_tables.py`) e resolve a metade de parsing do §Escopo 2.

Número desatualizado no cabeçalho da skill: as `shipped` sem `ship_pr` são
**134**, não ~159 (backfill parcial desde então).

## Entrega (2026-08-24)

`dev/check_lane_transition.py` + `dev/_lane_closure_predicates.py`, no pre-commit
como `lane-transition`. Três checagens, todas provadas por **mutação nos dois
sentidos** (planta a violação: vermelho; restaura: verde) e por 15 testes em
`tests/dev/test_check_lane_transition.py`:

| | O quê | Superfície |
| --- | --- | --- |
| **T1** | flip para `shipped` exige `ship_pr` + `ship_date` **e** o PR no registro | diff staged — **local-only** |
| **T2** | lane nova exige **linha de tabela** no `_README` | diff staged — **local-only** |
| **C1** | lane não-terminal cujo `ship_pr` já está mergeado em `origin/main` | estado — **vale também no CI** |

### Superfície declarada — a resposta ao §Critério

O §Ataque §5 mediu que o CI só roda `pre-commit run --all-files`, onde
`git diff --cached` volta vazio. **T1 e T2 herdam isso e são enforcement local,
declarado — não gate de merge.** C1 não: lê o estado da vault inteira, então é a
única das três que vale nos dois lugares. Foi por isso que o par transição +
coerência entrou junto: sem C1 a lane entregaria só mecanismo que o CI não vê.

Nenhum step novo de CI com `--from-ref` — decisão consciente: a superfície de
Actions é orçamento (a sprint está a 544% do teto) e C1 já dá cobertura de merge
para a metade que importa.

### Deferimento datado — a metade que exige rede · dono: `information-architect`

O caso-bandeira ([[A40.l7]]/#1375) **não é alcançado por nenhuma das três**, e
isso está declarado no docstring do módulo em vez de disfarçado: no instante do
defeito a lane não tinha `ship_pr` nem flip, e o único vínculo entre PR e lane era
o **id no assunto do commit**. Medido: esse sinal tem 38/42 de recall na A40, mas
dispara falso em commit que apenas MENCIONA a lane (o #1643 diz *"abre a l77"*) —
não serve como gate duro. Fechar essa metade exige cruzar branch↔PR pela API.

**Condição de retomada:** quando existir fonte hermética de "PR mergeado desta
branch" (hoje não existe — squash-merge não deixa a branch como ancestral), ou
quando a classe reincidir ≥3× com o C1 já em `main`. Enquanto isso, gate
obrigatório que depende de rede **pisca**: o `check_scheduled_workflows` travou
todo merge do repo em 2026-08-24 lendo réplica obsoleta com HTTP 200. O limite
está registrado em [[ADR-413]] §Limite declarado.

### Achado colateral — a camada 1 da skill falhava aberta

`check_lane_counter` nunca acusou o contador errado da A40 porque
`LANE_COUNT_RE` exigia `## Lanes (N)` e o cabeçalho real tem texto dentro dos
parênteses ⇒ `match is None` ⇒ `return []`. Corrigido no mesmo PR; provado por
mutação. Era a razão de a camada 1 dar verde sobre `75 · 75` com 76 no disco.

## Re-medição do closeout (2026-08-25) — o gate está segurando em produção

Os números do §Ataque são de **2026-08-24** e ficam: são o retrato que motivou a
lane. Re-medidos um dia depois, com o gate já em `main`:

| | passa | barra |
| --- | --- | --- |
| As **44** transições da A40 **anteriores** ao gate (`6d3721ee`) | 19 | **25** |
| As **5** transições **posteriores** | **5** | **0** |

A classe não morreu por si — ela continuou produzindo até o gate entrar (de 42
transições em 08-24 para 49 em 08-25, e de 23 para 25 barradas). Depois do gate,
**nenhuma** transição nova deixou de carregar o registro: l6 (#1673), l63 (#1671),
l68 (#1663), l77 (#1684), l81 (#1697).

O `C1` (coerência) roda limpo na vault viva: **0 achados** — nenhuma lane
não-terminal declara `ship_pr` já mergeado.

## Verificação do §Critério (2026-08-25) — item a item contra `main`

Fecho da lane. Cada critério conferido no que está mergeado, não no que a lane
afirma.

| Critério | Onde vive em `main` | ✓ |
| --- | --- | --- |
| Prova retroativa **por amostra**, ≥1 caso por eixo | `test_flip_sem_ship_pr_acusa_caso_a40_l71` (#1511, número só no assunto do commit) e `test_flip_com_pr_nao_citado_acusa_caso_a40_l19` (#1241) | ✅ |
| Casos negativos **com rota nomeada** | `test_caso_bandeira_l7_nao_dispara_e_isso_e_declarado` e `test_self_closing_na_ordem_prescrita_passa` | ✅ |
| Predicado pinado nos **dois** eixos | `sprint_record` lê `_README` ∪ `_HISTORY`; `test_mencao_em_prosa_nao_substitui_linha_de_tabela` fixa o eixo estrito | ✅ |
| Polaridade por **mutação nos dois sentidos** | as 3 checagens plantadas e restauradas no repo real durante a entrega; `doc-index-self-test` idem | ✅ |
| **Superfície declarada** (local-only × CI) | §Entrega §Superfície: `T1`/`T2` local-only por lerem `git diff --cached`; `C1` vale no CI | ✅ |
| Gate na **transição**, nunca por PR | `check_lane_transition.py` não recebe PR: lê o diff staged e o estado | ✅ |
| Falso-positivo declarado + **self-closing** | a sequência prescrita (`gh pr create` → flip com `ship_pr`) está na **mensagem de erro** do hook, não só na doc | ✅ |

**Defeito encontrado neste fecho, e corrigido aqui:** o heading
`## Critério de aceite` **sumiu no `6d3721ee`** — foi o meu próprio edit, que
substituiu o bloco e não repôs a linha do heading. Os critérios ficaram órfãos
dentro do §Escopo por um dia. Medido: `grep -c '^## Critério de aceite'` dá 1 em
`7ed61f04` e 0 em `6d3721ee`. Gate nenhum pega heading que some — nem a camada 1,
que rodou verde duas vezes sobre este arquivo.
