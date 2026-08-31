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

## A decisão que faltava — e a medição que reformulou a pergunta (2026-08-31)

A lane pedia decidir **se ainda queremos os ~35** antes de recriar. Ao medir para decidir,
a premissa da pergunta caiu.

**Instrumento.** Cadeia inteira emitida em dialeto **Postgres** — `alembic upgrade head
--sql` com URL `postgresql+asyncpg`, o que faz `PostgresqlImpl` responder no lugar de
`SQLiteImpl` —, cruzada com o inventário de índices do model (`Base.metadata`) e do SQLite
construído por Alembic. Pareamento por **(tabela, colunas, unique)**, não por nome: é o que
separa ausência de renomeação, e sem ele 5 dos 35 seriam recriados por engano.

| Grupo | N | Fato medido | Destino |
|---|---|---|---|
| **S** — perdido por `copy_from` | 30 | **Postgres tem**; só SQLite perdeu no recreate | `idxrepair0002` |
| **R** — rename | 4 | O DB tem o mesmo índice, mesmas colunas, sem predicado, sob outro nome | nome do **model** alinhado ao de prod — zero DDL |
| **G** — gap real | 1 | `ix_task_suggestions_status`: nenhuma migration jamais o criou | `index=True` sai do model |

**A premissa invertia quem decidiu.** "Recriar todos é repor decisão que ninguém tomou" —
medido, é o oposto: **produção executa essa decisão desde que cada migration rodou** e paga
o custo de write dos 30 hoje. Quem estava fora do combinado era o SQLite, e mantê-lo assim
é o que sustenta a divergência que já contaminou uma decisão de desenho.

**A pergunta legítima sobrevive, mas muda de alvo.** *9 índices em `tasks` valem o write
throughput?* continua valendo — só que é pergunta sobre **prod**, responder "não" implica
`DROP INDEX CONCURRENTLY`, e exige medir uso real (`pg_stat_user_indexes`), que não temos
instrumentado. Vira follow-up, não escopo de um reparo de paridade.

**Falsificação dos 5 que não são ausência.** O pareamento por colunas por si só produziu um
falso rename: `ix_txov_active_workspace` cobre `workspace_id` **mas é parcial**
(`WHERE deleted_at IS NULL`) e não substitui o índice total que o model declara. Só a
leitura do DDL literal separou os 4 renames reais do 1 parcial — que voltou para o grupo S.

**Catraca.** 39 entradas saíram de `KNOWN_PRE_EXISTING_DRIFT` (35 `add_index` + 4
`remove_index`) com **zero drift novo** — o gate confirma que nenhum índice duplicado
entrou. Sobram 2 `add_index` que não são ausência (flag `unique` divergente; índice de
expressão) e 13 `remove_index`.

## Entregue no PR de fecho

- `idxrepair0002` — recria os 30 do grupo S, idempotente por inspector (Postgres já os tem)
  e com ramo `is_offline_mode()`, mesmo padrão da `idxrepair0001`.
- Grupo R: `Index(...)` explícito no model com o nome que prod tem, em
  `TaskSuggestion` e `WorkspaceEconomicAssumptionOverride`. Zero DDL.
- Grupo G: `index=True` removido de `TaskSuggestion.status` — todo read-path é
  workspace-scoped e já usa `ix_suggestions_ws_status`.
- `KNOWN_PRE_EXISTING_DRIFT` limpo; o comentário dos `remove_index` afirmava que eram
  parciais "majoritariamente intencionais" — medido: **10 de 11**, e os 4 renames que a
  redação cobria por engano saíram.
- `DB_SCHEMA_REFERENCE.md` regenerado: ele listava os 4 nomes automáticos, **índices que
  nenhum banco jamais teve**. Pelo motivo que a [[ADR-423]] §Consequências já registra, o
  snapshot dele não podia ter pego — os dois lados vêm do model.
- [[ADR-423]] → `Decidido`, com emenda datada corrigindo a contagem (33, não 38) e a
  premissa de D4, e acrescentando D5 (nome do índice no model é o de prod) e D6 (índice que
  nenhuma migration criou não vira índice novo por default).

## Dry-run no dogfood — critério de aceite nº 5

Rodado 2026-08-31 sobre `mathoms.db` (revisão `adr417cfs`, imediatamente anterior ao
reparo), read-only: **zero colisões nas três**. Ressalva: só duas medem sobre dado real —
`workspace_property_overrides` (6 rows) e `institution_catalog` (42 rows).
`report_publications` tem **0 rows**, então esse terço é vacuamente zero e não prova nada,
pela mesma razão que a ADR já declara do resultado em Postgres.

## Follow-ups nomeados, fora desta lane

- **`planner_review_metadata.ix_planner_review_metadata_pipeline_artifact_id`** aparece em
  `add_index` **e** `remove_index` — é mismatch da flag `unique`, **não** ausência. Triagem
  própria; catalogado com comentário.
- **Gate SQLite↔Postgres.** É a lacuna real por trás desta classe — o gate entregue compara
  model↔SQLite-migrado, nunca os dois engines. Exige PG no CI: decisão de custo do dono.
  A medição desta lane mostra que **metade do caminho é barata**: a cadeia emitida em
  dialeto PG (`upgrade head --sql`) já discrimina, sem banco nenhum. Ela é cega ao que só
  o modo online emite (ramos `is_offline_mode()`, DDL condicionado a inspector), então não
  substitui o gate — mas transforma "exige PG no CI" em "exige PG no CI *para a parte
  online*".
- **Reavaliar os 9 índices de `tasks` em produção** ([[ADR-162]]). Nasce da medição desta
  lane e **não** é dívida dela: é dívida de prod que o reparo tornou visível.
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
