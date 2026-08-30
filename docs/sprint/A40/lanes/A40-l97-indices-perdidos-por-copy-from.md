---
id: A40.l97
type: lane
title: "Índices perdidos por `copy_from`: 3 UNIQUE derrubaram invariante e o gate de drift era cego a índice"
sprint: A40
plan: PLAN-report-trust
status: in_progress
priority: P0
branch_slug: a40-l97-indices-perdidos-por-copy-from
owner: data-engineer
depends_on: []
adrs:
  - "[[ADR-187]]"
  - "[[ADR-235]]"
  - "[[ADR-423]]"
tags:
  - type/lane
  - sprint/a40
  - status/in-progress
  - priority/p0
  - area/persistence
  - area/backend
---

# A40.l97 — `indices-perdidos-por-copy-from`

> **Origem:** achado colateral da auditoria cláusula-a-cláusula da [[ADR-235]] feita na
> [[A40.l95]], 2026-08-30. Não é sobre nu-propriedade — a `adr235nupropriet1` é só a
> primeira das **13** migrations culpadas. Co-design `data-engineer`. Decisão em
> [[ADR-423]] (`Proposto`).

## O fato, medido

`batch_alter_table(copy_from=<snapshot>)` sem `recreate=` faz **drop + recreate** da tabela
em SQLite (`SQLiteImpl.requires_recreate_in_batch` → `True`), e o snapshot nunca declara
`Index`. **38 índices** do model estão ausentes no DB construído por Alembic, em 13
migrations, **todas** com `copy_from` — intersecção perfeita.

Em Postgres `DefaultImpl` devolve `False`: as mesmas migrations são `ALTER` nativo e
**nada se perdeu**. Produção não foi afetada.

**Três UNIQUE derrubavam invariante de negócio**, falsificados por probe comportamental
(inserir a 2ª linha colidente é RECUSADO na revisão anterior e ACEITO em `head`):

| Índice | Invariante | Culpada |
|---|---|---|
| `uq_workspace_one_residencia_principal` | 1 residência principal / workspace | `adr235nupropriet1` |
| `uq_report_publications_active` | 1 publicação ativa / (ws, período) | `adr387pr2snap` |
| `ix_institution_catalog_code` | `code` único | `adr238informes1` |

O de `report_publications` é o mais grave e **não** é o que originou a investigação: o
read-path usa `scalar_one_or_none()` sobre `unpublished_at IS NULL` ⇒ duas linhas ativas
levantam `MultipleResultsFound` em `is_month_closed_sync`, o predicado de "mês fechado
imutável" ([[ADR-187]]).

## Por que ficou invisível três meses, e o que isso custou

Três schemas coexistem: **model** (`create_all`, que a suíte usa e que ainda declara os
índices), **SQLite migrado** (dev/dogfood, que os perdeu) e **Postgres migrado** (prod,
intacto). Nenhum gate comparava os dois primeiros, e `TESTING.md` faz do SQLite o
*stand-in* de prod — logo toda medição local de invariante era inválida por construção.

**O defeito já contaminou uma decisão de desenho.** `db_property_supersession_writer:82`
recusou acrescentar guard citando *"verificado em 2026-08-11 — o cenário não é nem semeável
em teste"*. A verificação rodou sob `create_all`; sob o DB migrado era semeável. A conclusão
estava certa por acidente.

**E o gate que devia pegar já rodava o upgrade completo** e jogava fora exatamente o diff
que importa: `_diff_signature` caía em `return None` para `add_index`, sob o comentário
*"alto ruído em SQLite"*.

## Entregue neste PR

- `idxrepair0001` — reparo forward-only dos **3 UNIQUE**, idempotente por inspector
  (Postgres já os tem), abortivo com query acionável em caso de colisão, `downgrade()` no-op
  declarado. Probe comportamental pós-reparo: **RECUSADO** nos dois casos testáveis.
- `_diff_signature` passa a emitir `add_index`/`remove_index`, com sufixo `:unique`.
  **A/B, contra a revisão anterior ao reparo (não `git stash`):** vermelho com as 3
  signatures e **zero ruído**; verde com o reparo.
- 37 `add_index` + 17 `remove_index` catalogados em `KNOWN_PRE_EXISTING_DRIFT`.
- Comentário de `db_property_supersession_writer` corrigido.

## Falta — e a primeira coisa é uma decisão, não código

**Os ~35 índices não-unique NÃO devem ser recriados sem decisão.** São performance, e a
lane decide primeiro **se ainda os quer**: 9 índices em `tasks` é custo de write throughput
que ninguém reavaliou desde a [[ADR-162]]; 5 em `suggestions`, 4 em `protections`. Recriar
todos é repor decisão que ninguém tomou.

Gatilho `data-engineer` para a decisão; em Postgres a recriação pediria `CONCURRENTLY`.

A catraca já força o fecho: o teste **falha** se um drift catalogado for corrigido e não
removido de `KNOWN_PRE_EXISTING_DRIFT`.

## Follow-ups nomeados, fora desta lane

- **`planner_review_metadata.ix_planner_review_metadata_pipeline_artifact_id`** aparece em
  `add_index` **e** `remove_index` — é mismatch da flag `unique`, **não** ausência. Triagem
  própria; catalogado com comentário.
- **Gate SQLite↔Postgres.** É a lacuna real por trás desta classe — o gate entregue compara
  model↔SQLite-migrado, nunca os dois engines. Exige PG no CI: decisão de custo do dono.
- **`property_market_value.idx_pmv_lookup`** — índice de expressão; o alembic emite
  *"Generating approximate signature"*. Limitação irredutível, catalogada.
- **`adr239apolice`** afirma no docstring "seed idempotente por `code` (UNIQUE)" e o
  `upgrade()` faz `SELECT` + filtro em Python. Comportamento sobrevive; só o docstring é
  falso. Polish.

## Critério de aceite

O de [[ADR-423]] §Critério de aceite. Com uma adição para o fecho da lane: o dry-run das
três queries de colisão **no dogfood** antes de qualquer deploy — em Postgres o resultado é
vacuamente zero e não prova nada.

## Amarra

Não muta E3/E5 — `backend/alembic/`, `backend/tests/` e um comentário em `backend/app/`.
**Não entra na cláusula de reinício** do contador de 2 re-runs da A40, que segue em 0/2 e
governado pelas quatro lanes já nomeadas no `_README`.
