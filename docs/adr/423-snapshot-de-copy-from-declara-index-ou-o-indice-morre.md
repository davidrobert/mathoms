---
id: ADR-423
type: adr
title: "Snapshot de `copy_from` declara `Index` ou o índice morre em SQLite; e o gate de drift passa a enxergar índice"
status: Decidido
phase: A40.l97
date: "2026-08-30"
amended_at: ["2026-08-31"]
relates_to:
  - "[[ADR-187]]"
  - "[[ADR-215]]"
  - "[[ADR-235]]"
  - "[[ADR-238]]"
  - "[[ADR-387]]"
supersedes: []
superseded_by: []
tags:
  - type/adr
  - status/decidido
  - area/persistence
  - area/backend
  - area/testing
aliases:
  - "ADR 423"
  - "copy_from perde índice"
  - "idxrepair0001"
---

# ADR-423 — Snapshot de `copy_from` declara `Index`, ou o índice morre

> Achado durante a auditoria cláusula-a-cláusula da [[ADR-235]] ([[A40.l95]]).
> Co-design `data-engineer`, 2026-08-30. O reparo dos 3 UNIQUE e a extensão do gate
> já estão implementados; esta nota registra a decisão e a convenção.

> **Emenda de medição (2026-08-31, [[A40.l97]]):** a contagem "38 perdidos por
> `copy_from`" e a premissa de D4 ("recriar os ~35 é repor decisão que ninguém
> tomou") **caíram na medição**. São **33** perdidos por `copy_from`; dos 5 restantes,
> 4 são rename e 1 nunca existiu em DB algum. E Postgres **tem** os 30 não-unique
> desde sempre — restaurá-los é paridade, não decisão nova. Ver §Emenda ao pé.

## Contexto

`op.batch_alter_table(..., copy_from=<snapshot>)` sem `recreate=` usa `recreate="auto"`.
`SQLiteImpl.requires_recreate_in_batch` devolve `True` para qualquer operação que não seja
`add_column`/`create_index`/`drop_index` — isto é, **drop + recreate da tabela**. O snapshot
passado em `copy_from` declara colunas, `UniqueConstraint` e `CheckConstraint`; **nunca**
declara `Index`. Logo todo índice nomeado da tabela morre no recreate, em silêncio.

`DefaultImpl.requires_recreate_in_batch` devolve `False`: em Postgres as mesmas migrations
viram `ALTER` nativo e **nada se perde**. O defeito é **SQLite-only** — dev, dogfood e a
suíte de testes. Produção roda Postgres (`config.py` levanta `RuntimeError` se a URL for
sqlite), então nenhum DB de produção foi afetado.

**Medido em 2026-08-30 contra `head`:** 38 índices declarados no model estão ausentes no DB
construído por Alembic, em **13 migrations, todas com `copy_from`** — a intersecção é
perfeita, o padrão é a causa. Três são UNIQUE e derrubam invariante de negócio. Falsificados
por probe comportamental (inserir a 2ª linha colidente):

| Índice | Invariante | Culpada | rev anterior | `head` |
|---|---|---|---|---|
| `workspace_property_overrides.uq_workspace_one_residencia_principal` | 1 residência principal por workspace | `adr235nupropriet1` | RECUSADO | **ACEITO** |
| `report_publications.uq_report_publications_active` | 1 publicação ativa por (workspace, período) | `adr387pr2snap` | RECUSADO | **ACEITO** |
| `institution_catalog.ix_institution_catalog_code` | `code` único | `adr238informes1` | RECUSADO | **ACEITO** |

O de `report_publications` é o mais grave, e **não** é o que originou a investigação: o
read-path faz `scalar_one_or_none()` sobre `unpublished_at IS NULL`, então duas linhas
ativas levantam `MultipleResultsFound` dentro de `is_month_closed_sync` — o predicado de
*"mês fechado imutável"* da [[ADR-187]].

**Por que passou três meses invisível.** Três schemas coexistem e nenhum gate comparava os
dois que importam: o do **model** (`Base.metadata.create_all`, que a suíte usa e que ainda
declara os índices), o do **SQLite migrado** (dev/dogfood, que os perdeu) e o do **Postgres
migrado** (prod, intacto). `TESTING.md` faz do SQLite o *stand-in* de produção — logo toda
medição local de invariante era inválida por construção. E o defeito já **se propagou para
uma decisão de desenho**: `db_property_supersession_writer` recusou acrescentar um guard
citando *"verificado — o cenário não é nem semeável em teste"*, verificação que rodou sob
`create_all`.

**O gate que devia pegar já existia e jogava fora exatamente o diff que importa.**
`test_alembic_guardrails.py::test_no_drift_between_models_and_migrations` já roda
`command.upgrade(head)` + `compare_metadata`, mas o reducer `_diff_signature` caía em
`return None` para `add_index`/`remove_index`, sob o comentário *"alto ruído em SQLite"*.

## Decisão

### D1 — Convenção: snapshot de `copy_from` declara `Index`, ou a tabela perde os índices

Toda migration que passe `copy_from=` declara no snapshot **também** os `Index` da tabela.
Não é preferência de estilo: é a diferença entre a tabela sobreviver ao recreate com os
índices e sem eles. Vale para índice parcial (`sqlite_where`/`postgresql_where`) igual.

### D2 — O gate de drift enxerga índice; `add_index` é ausência e vira hard-fail

`_diff_signature` passa a emitir assinatura para `add_index` e `remove_index`, com sufixo
`:unique` quando aplicável. `add_index` significa *"o model declara e o DB migrado não tem"*
— é a direção da perda. `remove_index` é a direção oposta (índice parcial criado por
migration que o model não declara) e é majoritariamente intencional; fica catalogado.

**Estender o reducer existente, não criar teste novo.** O upgrade completo já roda e custa
~1,3 s; o custo marginal é ~zero. E `test_alembic_guardrails.py` **não tem `pytestmark`** —
o `ci.yml` declara que ele *"NÃO é gated — sempre roda"*. Um teste novo sob
`pytest.mark.migration` não rodaria no PR que mexe só no model, que é exatamente o furo.

**A/B que prova que ele discrimina** (contra a revisão anterior ao reparo, não `git stash`):
3 signatures não catalogadas, **as três UNIQUE, zero ruído** → vermelho; com o reparo → 0,
verde.

### D3 — Reparo forward-only dos 3 UNIQUE, idempotente, abortivo

`idxrepair0001` recria os três. **Forward-only**: editar `adr235nupropriet1` in-place não
conserta DB já migrado — precisaria do reparo de qualquer forma, virando dois mecanismos
para um defeito — e o snapshot `_overrides_table` é compartilhado com o `downgrade()` de lá.

**Idempotente por inspector**, e a razão não é DB novo: é que **Postgres já tem os índices**
e `op.create_index` puro falharia com *"already exists"*. Em modo offline (`--sql`) o
inspector não existe (`MockConnection` levanta `NoInspectionAvailable`), então o DDL sai sem
pre-check — quem revisa SQL offline é humano, e o pre-check roda no apply.

**Aborta, não deduplica.** Escolher *qual* linha sobrevive é decisão de domínio, e migration
que muta linha em silêncio é inauditável. Precedente no próprio repo: o `downgrade` da
`adr235nupropriet1` levanta `RuntimeError` com o UPDATE a rodar.

**`downgrade()` é no-op declarado**, não `IRREVERSIBLE`: nada se perde na ida, e incluí-lo em
`IRREVERSIBLE_MIGRATIONS` degradaria o roundtrip completo de `test_migrations_are_idempotent`
para o ramo parcial.

### D4 — Os ~35 não-unique ficam catalogados, com lane própria

Não entram no reparo. São performance, e a lane deve **primeiro decidir se ainda os quer**:
9 índices em `tasks` é custo de write throughput que ninguém reavaliou desde a [[ADR-162]].
Recriá-los sem decidir é repor decisão que ninguém tomou. Ficam em
`KNOWN_PRE_EXISTING_DRIFT`, cuja catraca **falha** se um drift catalogado for corrigido e
não removido da lista — a lane é forçada a limpar ao entregar.

## Alternativas consideradas

**(A) Teste novo só para `workspace_property_overrides`.** Rejeitada: cobre 2 dos 38 e deixa
12 migrations culpadas passarem.

**(B) Gate estático em `dev/` detectando `copy_from` sem `Index`.** Rejeitada: não veria a
classe "índice nunca criado por migration alguma", o snapshot é montado por helper
parametrizado (análise estática de `Index` ali é frágil), e é desnecessária — a medição
dinâmica que já rodava achou 13/13 dos ofensores.

**(C) Editar as 13 migrations in-place.** Rejeitada — ver D3.

## Consequências

- **Nenhum dado de produção foi afetado** e nenhuma remediação de prod é necessária. As
  queries de colisão rodam no dogfood SQLite; em Postgres o resultado é vacuamente zero.
- A premissa "SQLite é stand-in de prod" volta a valer para índice, que é onde ela estava
  quebrada. Não vira garantia geral — o gate compara model↔SQLite-migrado, não
  SQLite↔Postgres.
- `DB_SCHEMA_REFERENCE.md` afirmava a existência dos três; a afirmação passa a ser
  verdadeira. O snapshot test dele **não podia** ter pego o drift: compara `generate()`
  (que introspecciona `Base.metadata`) com o arquivo — os dois lados vêm do model.

## Critério de aceite (PR de `Decidido`)

1. Os 3 UNIQUE presentes no DB construído por Alembic, e o probe comportamental **RECUSA**
   a 2ª linha colidente nos três.
2. A/B do gate: vermelho na revisão anterior ao reparo com as 3 signatures e **zero ruído**;
   verde com o reparo. Construído por `command.upgrade(cfg, "<rev-anterior>")` — `git stash`
   não desfaz commit e o controle sai falso.
3. `pytest backend/tests/test_alembic_guardrails.py -q` verde, incluindo
   `test_offline_sql_generation_works` (o pre-check por inspector quebra em modo offline).
4. `pytest backend/tests -q` completo — o reducer é compartilhado pelos 4 testes do arquivo.
5. Dry-run das três queries de colisão no dogfood antes de qualquer deploy.

## Não-objetivos

- ~~Recriar os ~35 índices não-unique~~ — **feito em 2026-08-31** (`idxrepair0002`),
  ver §Emenda. O que permanece fora é reavaliar se **produção** ainda quer os 9
  índices de `tasks`: é pergunta sobre prod, exige `DROP INDEX CONCURRENTLY`, e não
  cabe num reparo de paridade.
- `planner_review_metadata.ix_planner_review_metadata_pipeline_artifact_id` — aparece em
  `add_index` **e** `remove_index`: é mismatch da flag `unique`, não ausência. Triagem própria.
- Gate comparando SQLite↔Postgres. É a lacuna real por trás desta classe, e exige ambiente
  PG no CI — decisão de custo do dono, não desta nota.
- `property_market_value.idx_pmv_lookup` — índice de expressão; o próprio alembic emite
  *"Generating approximate signature"*. Limitação irredutível, catalogada.


## Emenda — a medição de 2026-08-31 reformula D4 e corrige duas afirmações (A40.l97)

A lane fechou pela via que D4 mandava: **decidir antes de recriar**. A medição feita
para decidir derrubou a premissa da própria D4.

### O que foi medido

Cadeia inteira emitida em dialeto **Postgres** (`alembic upgrade head --sql` com URL
`postgresql+asyncpg`, que faz `PostgresqlImpl` responder no lugar de `SQLiteImpl`),
cruzada com o inventário de índices do model (`Base.metadata`) e do SQLite construído
por Alembic. O pareamento é por **(tabela, colunas, unique)**, não por nome — é o que
separa ausência de renomeação.

| Grupo | N | Fato medido |
|---|---|---|
| **S** — perdidos por `copy_from` | 30 | Criados por migration; **Postgres tem**, SQLite perdeu no recreate |
| **R** — rename | 4 | O DB tem o mesmo índice, mesmas colunas, sem predicado, sob **outro nome** |
| **G** — gap real | 1 | `ix_task_suggestions_status`: **nenhuma** migration jamais o criou |

Somados aos 3 UNIQUE da `idxrepair0001`, os perdidos por `copy_from` são **33**, não 38.

### Correção 1 — "a intersecção é perfeita, o padrão é a causa" era larga demais

A afirmação vale para 33. Para os 5 do grupo R+G, `copy_from` **não** é a causa: eles
nunca existiram sob o nome que o model declara, em DB algum. A tabela deles ter sido
tocada por uma migration com `copy_from` é coincidência, não mecanismo. A frase
descrevia corretamente o padrão e superestimava sua extensão em 5.

### Correção 2 — D4 invertia quem tomou a decisão

D4 dizia: *"recriá-los sem decidir é repor decisão que ninguém tomou"*. Medido, é o
oposto — **produção executa essa decisão desde que cada migration rodou** e paga o
custo de write deles hoje. Quem estava fora do combinado era o SQLite. Portanto:

- Restaurar os 30 é **paridade com prod**, não decisão nova, e é o que fecha a
  divergência que já contaminou uma decisão de desenho (§Contexto).
- A pergunta legítima que D4 formulava — *9 índices em `tasks` valem o write
  throughput?* — continua aberta, mas **muda de alvo**: é sobre produção, e
  respondê-la "não" implica `DROP INDEX CONCURRENTLY` em Postgres. Follow-up
  nomeado, fora desta nota.

### D5 — o nome do índice no model é o nome que prod tem

Onde a migration nomeou o índice à mão e o model usa o nome automático de
`index=True`, o autogenerate acusa **ausência de um índice que existe** — para sempre,
porque nenhum DDL resolve. A correção é alinhar o **model** ao nome do DB (`Index(...)`
explícito), nunca renomear em prod. Aplicado a `ix_suggestions_workspace_id` e
`ix_ws_econ_override_{workspace_id,classe_auvp,effective_from}`. Zero DDL, zero risco.

### D6 — índice que nenhuma migration criou não vira índice novo por default

`ix_task_suggestions_status` só existia na intenção do `index=True`. Todo read-path de
`TaskSuggestion.status` é workspace-scoped e já usa `ix_suggestions_ws_status`; um
índice avulso em `status` seria custo de write para query que não existe — e uma query
por `status` sem `workspace_id` seria violação de tenancy. O `index=True` saiu do model.

### Critério de aceite nº 5 — dry-run no dogfood

Rodado 2026-08-31 sobre `mathoms.db` (revisão `adr417cfs`, imediatamente anterior ao
reparo), read-only: **zero colisões nas três**. Ressalva de honestidade: só duas medem
sobre dado real — `workspace_property_overrides` (6 rows) e `institution_catalog`
(42 rows). `report_publications` tem **0 rows**, então esse terço é vacuamente zero e
não prova nada, exatamente como esta nota já dizia do resultado em Postgres.

### Follow-up que nasce desta emenda

**Reavaliar os 9 índices de `tasks` em produção** ([[ADR-162]]). Não é dívida deste
reparo — é dívida de prod que o reparo tornou visível. Exige `CONCURRENTLY` e medição
de uso real (`pg_stat_user_indexes`), que não temos instrumentado.
