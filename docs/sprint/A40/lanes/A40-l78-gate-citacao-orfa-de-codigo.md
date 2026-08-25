---
id: A40.l78
type: lane
title: "Mover código não deixa citação órfã: gate no lado do código, não no do doc"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P2
branch_slug: a40-l78-gate-doc-code-paths
owner: information-architect
adrs:
  - "[[ADR-302]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
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
| Corpus inteiro (`docs/**`) | **1123 ocorrências**; o topo são paths mortos **por desenho** (`scripts/e5_analyze.py` renomeado na F9.4, `scripts/e6_render.py` deletado pela [[ADR-129]], `config/goals.json` migrado na A10) | descartado — allowlist do tamanho do problema, e "corrigir" seria revisionismo |
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

- **O acervo histórico.** `--all` reporta **306** citações sem alvo em
  `adr`+`reference` (contagem crua, sem os filtros dos desenhos descartados) e
  sai com **exit 0** de propósito. O gate cobre
  movimentação nova; limpar o acervo é trabalho separado, e boa parte dele
  **não deve** ser limpo (moldura histórica correta).
- **Lane e plano.** Fora de escopo por desenho, ver acima.
- **Citação em prosa que nunca teve alvo** (a [[ADR-255]] declarava "entregue
  em #429" um teste que jamais existiu). Nenhum evento de código dispara nesse
  caso — só auditoria pega.

## Entregue

- [`dev/check_doc_code_paths.py`](../../../../dev/check_doc_code_paths.py) —
  gate + modo `--all` de auditoria (consumível pela camada 1 da skill
  `audit-vault`).
- Hook `doc-code-paths` no pre-commit, com `always_run: true` **de propósito**:
  o pre-commit não passa path deletado na lista de staged (o `diff-filter`
  exclui `D`), então um `files:` de código nunca dispararia na deleção pura —
  justamente o caso que cria citação órfã. Custa ~70ms quando não há deleção.
- [`tests/test_check_doc_code_paths.py`](../../../../tests/test_check_doc_code_paths.py)
  — 6 casos em repo git sintético, fim-a-fim. Duas mutações plausíveis
  verificadas: ignorar rename derruba `test_rename_nomeia_o_destino`; incluir
  `docs/sprint/` no escopo derruba `test_citacao_so_em_lane_nao_gateia`.

## Critério de aceite

- [x] Gate reproduz o caso histórico real (`--since 6c68723a^` acusa os dois
      cards que a [[ADR-196]] citava).
- [x] Suíte verde e mordendo (mutação plausível derruba teste).
- [x] FP medido **antes e depois** — exigência de [[ADR-302]] §armadilha 9.
- [x] O que o gate não cobre está declarado nesta lane, não implícito.
