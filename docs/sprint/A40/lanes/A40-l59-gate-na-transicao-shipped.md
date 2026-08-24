---
id: A40.l59
type: lane
title: "A transição para `shipped` ganha gate: ship_pr no frontmatter e PR visível no _README"
sprint: A40
plan: PLAN-report-trust
status: open
priority: P2
branch_slug: a40-l59-gate-na-transicao-shipped
owner: information-architect
adrs:
  - "[[ADR-302]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/open
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

## Critério de aceite

- **Prova retroativa**: os casos históricos (l7/#1375; as lanes órfãs do #1411)
  teriam sido barrados — reproduzir cada um contra o hook e citar o resultado.
- Polaridade certa ([[ADR-302]] e a lição da sprint): o gate **impede** o
  estado ruim de entrar, não o detecta depois.
- Gate na transição, nunca por PR — lane que vira 2 PRs não pode dar verde
  falso.
- Falso-positivo declarado: flip de `status` em rebase/revert tem escape
  documentado (a mesma classe do `--no-verify` proibido: corrigir a causa,
  nunca bypassar).

## Colisão declarada

`dev/check_closure.py` (da skill) e o hook novo compartilham a definição da
metade estrutural — extrair a checagem para módulo comum em vez de duplicar.

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

### 7. Correções ao §Colisão

`check_closure.py` (461 linhas) **é pós-merge por construção**: `resolve_from_pr`
e `_merge_sha(pr)` resolvem lanes a partir de um PR **já mergeado**. No sentido
pre-commit não há PR de onde resolver. O compartilhável são os **predicados**,
nunca a resolução — "extrair para módulo comum" subestima o corte. Some-se que
`dev/_lane_table_parsers.py` já existe (hoje só consumido pelo
`migrate_lanes_tables.py`) e resolve a metade de parsing do §Escopo 2.

Número desatualizado no cabeçalho da skill: as `shipped` sem `ship_pr` são
**134**, não ~159 (backfill parcial desde então).
