---
id: ADR-412
type: adr
title: "Derivado versionado é derivado de contrato, e derivado versionado não carrega valor agregado"
status: Decidido
phase: A40.l59
date: "2026-08-25"
relates_to:
  - "[[ADR-076]]"
  - "[[ADR-109]]"
  - "[[ADR-182]]"
  - "[[ADR-322]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 412"
  - "derivado versionado é derivado de contrato"
tags:
  - type/adr
  - status/decidido
  - area/docs
---

# ADR-412 — Derivado versionado é derivado de contrato, e derivado versionado não carrega valor agregado

## Contexto

O repo versiona artefato derivado em três lugares, sob o mesmo padrão declarado —
"gera, commita, e um snapshot test gateia o gerador":

| Derivado | Entrada | Muda quando |
| --- | --- | --- |
| `frontend/src/generated/report-layout.ts` ([[ADR-076]]) | `config/report_layout.yaml` | o **contrato de layout** muda |
| snapshot OpenAPI ([[ADR-109]]) | os `response_model` dos endpoints | o **contrato HTTP** muda |
| `docs/_MOC/_generated/**` ([[ADR-182]]) | **a vault inteira** | qualquer nota muda |

Os dois primeiros mudam num evento raro e significativo. O terceiro muda numa
fração grande dos commits — e daí sai um custo que o padrão não previu, medido em
2026-08-24 na fila de auto-merge: `main` recebe ~7-9 merges/hora contra ciclos de
CI de ~7 min, e todo PR que toca `docs/**` regenera os mesmos arquivos.

Dois modos de falha, e o segundo é o caro:

1. **Conflito.** Dois PRs que mexem em notas distintas colidem no derivado. Visível,
   e o custo é rebase.
2. **Lost update silencioso.** Quando os dois lados **incrementam o mesmo contador**,
   ambos escrevem o mesmo valor novo, o git aceita o merge **sem conflito**, e o
   número resultante está errado. Só o `--check` pega, 7 minutos depois, no CI.

O modo 2 não é hipótese: foi reproduzido em harness e é o que motiva esta ADR. Um
derivado que **conflita** apenas atrasa; um derivado que **mergeia limpo e mente**
corrompe.

## Decisão

**D1 — Derivado só é versionado se for derivado de contrato.** Se a entrada é um
contrato (schema, config declarativa, assinatura de API), versione e gateie com
snapshot. Se a entrada é o corpus inteiro — e portanto muda a cada commit —, o
snapshot deixa de ser gate e vira ponto de contenção.

**D2 — Derivado versionado não carrega valor agregado.** Contagem, soma e escalar
cujo valor é função do corpus inteiro **não entram** em arquivo versionado. O número
é sempre derivável da lista que ele resume; a lista merge por linha, o número não.
Vale para cabeçalho (`## Open (18)`), linha-resumo (`- Lanes: 44 done · 7 …`) e
escalar de rodapé (`N notas indexadas`).

**D3 — Derivado cujo conteúdo é 100% agregado não é reformável: é removível.**
Cortar as tabelas e manter o arquivo preserva o escalar e não fecha nada. Foi o
caso do `DOC_STATS.md`.

**D4 — Quando um derivado deixa de ser versionado, o gate migra do snapshot para o
self-test do gerador.** O snapshot prova que o *arquivo* está em sync; o self-test
prova que o *renderer* está certo. Sem snapshot, o `--check` não tem o que comparar,
e o self-test passa a ser o único gate — logo ele tem de estar wirado **antes** da
remoção, não depois.

## Consequências

### Positivas

- A classe silenciosa (D-2) morre por construção: sem agregado, não há lost update.
- O merge de linha do git resolve sozinho os casos disjuntos, que são a maioria.
- O sinal editorial sobrevive: "quais status existem" é mais útil que "quantos", e
  não colide.

### Negativas

- Perde-se a leitura "tamanho da vault num relance". Mitigado: a §Sprints do
  `DOC_STATS.md` foi realojada na coluna `status` do `INDEX.md`, que já tinha 36
  linhas `MOC-sprint-*` vazias — 1:1, derivado da própria nota, sem agregado.
- Um gate novo (`doc-index-self-test`) passa a rodar. Custo medido: 0,066 s, dentro
  do `lint-all` já pago.

### Limite declarado

Isto **não** fecha a contenção inteira. Sobra a **adjacência de linha-de-item**: duas
notas novas que caem lado a lado na mesma tabela ordenada conflitam por natureza do
merge de linha, não por agregado. Medido no `INDEX.md`, e registrado como
`xfail(strict=True)` em `tests/dev/test_generated_index_merge_contention.py` — se
alguém resolver a adjacência, o teste avisa em vez de mentir verde.

Também **não** cobre `docs/sprint/<X>/_README.md`, que é hotspot editorial escrito à
mão. O instrumento ali é o `dev/split_sprint_history.py`, que já existe.

## Alternativas consideradas

**Merge driver via `.gitattributes`.** Rejeitada por medição, não por gosto: driver é
**client-side**. O `update-branch` do trem ([[ADR-322]]) e o squash rodam no servidor
do GitHub, que não lê driver customizado do repo — e o driver `ours` exigiria
`git config merge.ours.driver true` por clone, que o CLAUDE.md §Git proíbe ao agente
configurar. Cobriria só o rebase local de quem rodou o config, não o caminho onde a
fila trava.

**Desversionar `docs/_MOC/_generated/**` inteiro.** Rejeitada: 26 referências a
`SPRINT_CURRENT.md` e 18 a `ADR_INDEX.md` em `*.md`, mais o protocolo do CLAUDE.md
que manda o agente ler esses arquivos — inclusive em worktree onde eles não
existiriam. O custo de navegação supera o ganho de contenção para os índices que
são, de fato, listas.

**Manter e absorver.** Rejeitada pelo modo de falha 2: absorver conflito é uma
decisão defensável; absorver corrupção silenciosa não é.

## Validação

- Harness de contenção sobre os 13 gerados, com dois PRs concorrentes sobre a mesma
  base: antes, `DOC_STATS.md` mergeia limpo e diverge da regeneração verdadeira;
  depois, os 12 restantes ficam verdes.
- Prova por mutação nos dois sentidos: reverter os renderers faz `SPRINT_CURRENT.md`
  e `PLAN_PROGRESS.md` reprovarem; restaurar deixa verde.
- O `doc-index-self-test` provado por mutação: quebrar `_format_lanes_line` reprova.
