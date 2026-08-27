---
id: A40.l78
type: lane
title: "Mover código não deixa citação órfã: gate no lado do código, não no do doc"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 1654
ship_date: "2026-08-25"
priority: P2
branch_slug: a40-l78-gate-doc-code-paths
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

# A40.l78 — `gate-citacao-orfa-de-codigo`

> **Aberta em 2026-08-24**, direto do achado **F21** da auditoria r10
> ([[ADR-302]]): o cluster [[ADR-285]] (`services/X.py` →
> `services/<subpkg>/X.py`), declarado *encerrado* na r9, tinha **71 ocorrências
> vivas em 20 paths**. A r9 mediu instâncias nomeadas, não o predicado.

## O problema

Nenhum gate lê path de código escrito em prosa. `check_doc_links` resolve
wikilink; `check_doc_markdown_links` resolve link relativo. Um
`` `backend/app/services/vault.py` `` em backtick é invisível aos dois — e o
caso mais traiçoeiro tem **href certo com texto de link errado** ([[ADR-231]]
`:44`), onde o gate de markdown passa e o leitor humano não.

Consequência medida: toda movimentação de pacote reabre a classe em silêncio, e
cada auditoria de vault a redescobre do zero.

## A decisão: gatear no lado do CÓDIGO

Três desenhos foram medidos antes de escolher. O registro completo está no
docstring de [`dev/check_doc_code_paths.py`](../../../../dev/check_doc_code_paths.py);
o resumo:

| Desenho | Medição | Veredito |
|---|---|---|
| Corpus inteiro (`docs/**`) | **1123 ocorrências** (número da redação original — não reproduziu no fecho, ver §Números re-medidos); o topo são paths mortos **por desenho** (`scripts/e5_analyze.py` renomeado na F9.4, `scripts/e6_render.py` deletado pela [[ADR-129]], `config/goals.json` migrado na A10) | descartado — allowlist do tamanho do problema, e "corrigir" seria revisionismo |
| Diff-based no lado do **doc** (linha adicionada, escopo `adr`+`reference`) | replay sobre 600 commits: **18 disparos, ~10 falsos**. Estreitando para linhas que afirmam existência: **3 disparos, os 3 falsos** | descartado — **zero verdadeiro** |
| Diff-based no lado do **código** (deleção/rename) | replay sobre 400 commits: **2 disparos em 1 commit, zero falso** | **adotado** |

### Por que o lado do doc não podia funcionar

Estrutural, não calibração: **quando o doc é escrito, ele está certo.** A
citação morre depois, no commit que move o código — e nesse commit a linha do
doc não é tocada. Gate diff-based no doc não tem como ver o evento que cria o
defeito. Foi o que a medição do desenho 2 mostrou ao render 3 disparos e
nenhum verdadeiro.

O gate adotado dispara **no instante em que a citação morre**, e para a pessoa
que acabou de mover o código — que é quem tem contexto para escolher entre as
duas saídas legítimas: corrigir o path, ou marcar a linha como histórica.

### Escopo `docs/adr/` + `docs/reference/`

É a superfície "agente lê isto para decidir", e onde estavam **os 20
DOC-BLOCK da r10, sem exceção**. Lane e plano citam arquivo que a própria lane
vai criar — ali path não-resolvido é o estado normal, não defeito. O teste
`test_citacao_so_em_lane_nao_gateia` trava esse limite.

## O que a lane NÃO fecha

Declarado para não virar falso conforto:

- **O acervo histórico.** `--all` reporta **307** citações sem alvo em
  `adr`+`reference` (contagem crua, sem os filtros dos desenhos descartados) e
  sai com **exit 0** de propósito. O gate cobre
  movimentação nova; limpar o acervo é trabalho separado, e boa parte dele
  **não deve** ser limpo (moldura histórica correta).
- **Lane e plano.** Fora de escopo por desenho, ver acima.
- **Citação em prosa que nunca teve alvo** (a [[ADR-255]] declarava "entregue
  em #429" um teste que jamais existiu). Nenhum evento de código dispara nesse
  caso — só auditoria pega.
- **Link markdown sem backtick.** `_docs_citing` casa ``` `path` ```; um
  `[texto](../../backend/app/x.py)` cujo texto não é o path é invisível.
  Medido no fecho (2026-08-27): **291** citações nessa forma em `adr`+`reference`
  fora de `archive`, **0 órfãs hoje** — a classe é latente, não viva. (O caso
  da [[ADR-231]] `:44`, citado no §O problema, **é** coberto: o path está em
  backtick *dentro* do texto do link.)
- **`docs/_MOC/`.** O `DOC_SCOPE` é `docs/adr/` + `docs/reference/`. A célula
  F21 da auditoria r10 enumera `sprint 45 · plan 3 · _MOC 1` além de
  `adr 21 · reference 1` — o gate alcança **22 das 71** ocorrências (31%). Lane
  e plano estão fora **por desenho** (§Escopo acima); `_MOC` não é nem um nem
  outro, e ficou fora sem decisão.
- **CI não reprova por este gate.** O hook roda em `lint-all` via
  `pre-commit run --all-files`, e nesse caminho o índice está vazio: o gate lê
  `git diff --cached`, não acha nada e passa. Medido:
  `pre-commit run doc-code-paths --all-files` → `Passed` com
  `git diff --cached --name-status | wc -l` = 0. O enforcement real é **local,
  no instante do commit** — que é onde o desenho quis que ele estivesse, mas
  não é um gate de merge.

## Entregue

- [`dev/check_doc_code_paths.py`](../../../../dev/check_doc_code_paths.py) —
  gate + modo `--all` de auditoria (consumível pela camada 1 da skill
  `audit-vault`).
- Hook `doc-code-paths` no pre-commit, com `always_run: true` **de propósito**:
  o pre-commit não passa path deletado na lista de staged (o `diff-filter`
  exclui `D`), então um `files:` de código nunca dispararia na deleção pura —
  justamente o caso que cria citação órfã. Custa ~70ms quando não há deleção.
- [`tests/test_check_doc_code_paths.py`](../../../../tests/test_check_doc_code_paths.py)
  — **10** casos em repo git sintético, fim-a-fim (6 no #1654, 4 no fecho).
  Mutações plausíveis verificadas: ignorar rename derruba
  `test_rename_nomeia_o_destino`; incluir `docs/sprint/` no escopo derruba
  `test_citacao_so_em_lane_nao_gateia`; `--since` cair no índice derruba
  `test_since_ve_o_commit_que_o_indice_ja_esqueceu`; backtick deixar de ser
  exigido derruba outros dois (§Fecho).

## Fecho — 2026-08-27

O #1654 entregou o gate; o fecho achou **três coisas que o critério de aceite
exigia e não estavam de pé**, e as três foram corrigidas antes de flipar.

### 1. A saída histórica que a mensagem anunciava era inexequível

O gate imprimia *"deixe como está e marque a linha como histórico"*. Marcar não
suprimia nada — a linha da [[ADR-196]] **já dizia** `(removido pela [[ADR-375]])`
e seguia sendo acusada:

```
$ python3 dev/check_doc_code_paths.py --since '6c68723a^'
`frontend/src/components/report/cards/PrevidenciaPgblCard.tsx` foi deletado, mas é citado em:
    docs/adr/196-reconciliacao-cards-pgbl-s7-irpf.md
EXIT=1
$ sed -n '56p' docs/adr/196-*.md
`frontend/…/PrevidenciaPgblCard.tsx` (removido pela [[ADR-375]])
```

Quem deletasse código citado só tinha duas saídas reais: apagar o nome
(revisionismo, que o próprio gate desaconselha) ou `--no-verify` (proibido).

**Corrigido pela mensagem, não por allowlist.** A regra que já era a semântica
do gate passou a ser dita: **o backtick é a afirmação de que o path existe
hoje**; menção histórica sai do backtick e mantém o nome. Não abre escotilha —
não existe marcador que silencie o gate, só uma forma de escrever que não é
citação. Pinado em `test_citacao_fora_do_backtick_e_a_saida_historica`.

### 2. `--since` carregava 100% da evidência do critério 1 e não tinha teste

```
$ grep -c -- '--since' tests/test_check_doc_code_paths.py   → 0   (antes)
$ grep -c -- '--all'   tests/test_check_doc_code_paths.py   → 0   (antes)
```

Três casos novos, e a mordida verificada por mutação:

| mutação | teste que cai |
| --- | --- |
| `--since` cai de volta no `git diff --cached` | `test_since_ve_o_commit_que_o_indice_ja_esqueceu` |
| `_docs_citing` deixa de exigir backtick | `test_link_markdown_sem_backtick_nao_e_visto` **e** `test_citacao_fora_do_backtick_e_a_saida_historica` |

A suíte foi de 6 para 10 casos.

### 3. Números re-medidos

| onde | dizia | mede hoje |
| --- | --- | --- |
| §O que a lane NÃO fecha | 306 órfãs no acervo | **307** |
| tabela de desenhos / docstring | 1123 ocorrências no corpus | **não reproduz**: 1214 com `archive`, 913 sem — nenhuma leitura dá 1123, e o harness que produziu o número não existe no repo |

O 1123 fica registrado como número **não-reproduzível**, não corrigido para
1214: ele sustenta uma decisão de desenho (*"allowlist do tamanho do
problema"*) que continua verdadeira nas duas leituras, e reescrevê-lo daria
falsa precisão a uma medição que ninguém consegue repetir.

## Deferimento — 2026-08-27 · dono: `information-architect`

Duas ampliações ficam fora, com condição de retomada:

1. **Alcançar a forma link-markdown** (291 citações, 0 órfãs hoje).
   *Retomar quando:* aparecer a 1ª órfã nessa forma — mede-se com o mesmo
   token do `_audit_all` trocando o delimitador de backtick por `](…)`.
2. **Estender `DOC_SCOPE` a `docs/_MOC/`** (a 71ª ocorrência da F21 que o gate
   não alcança). *Retomar quando:* a F21 for reavaliada na próxima rotação da
   `audit-vault` — **enquanto isso a célula F21 continua `procede-aberto`**,
   porque fechá-la deixaria as 49 ocorrências fora de escopo sem registro
   nenhum.

Fora deste deferimento por decisão: **gatear em CI com `--since origin/main`**.
Mudaria a política de merge e é gatilho de `sre-devops`; o desenho da lane pôs
o enforcement no commit de propósito. Registrado no §O que a lane NÃO fecha
como limite, não como dívida.

## Critério de aceite

- [x] Gate reproduz o caso histórico real (`--since 6c68723a^` acusa os dois
      cards que a [[ADR-196]] citava).
- [x] Suíte verde e mordendo (mutação plausível derruba teste).
- [x] FP medido **antes e depois** — exigência de [[ADR-302]] §armadilha 9.
- [x] O que o gate não cobre está declarado nesta lane, não implícito.
