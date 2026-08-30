---
id: ADR-424
type: adr
title: "SQL só-SQLite numa migration quebra a cadeia em Postgres; o gate é `upgrade head` contra PG no fecho required"
status: Proposto
date: "2026-08-30"
relates_to:
  - "[[ADR-154]]"
  - "[[ADR-210]]"
  - "[[ADR-320]]"
  - "[[ADR-384]]"
  - "[[ADR-423]]"
supersedes: []
superseded_by: []
tags:
  - type/adr
  - status/proposto
  - area/persistence
  - area/backend
  - area/ci
aliases:
  - "ADR 424"
  - "GLOB em migration"
  - "migrations-postgres"
---

# ADR-424 — SQL só-SQLite numa migration quebra a cadeia em Postgres

> Achado em 2026-08-30 a partir de um falso-vermelho da [[A40.l100]] (PR #1845,
> frontend-only). Fix e gate implementados no mesmo PR desta nota.

## Contexto

`alembic upgrade head` **falhava em Postgres desde o PR #1404** ([[ADR-384]], A40.l40,
2026-08-12). Produção é PG — `backend/app/core/config.py` levanta
`RuntimeError("DATABASE_URL must not use sqlite in production")` —, então a cadeia de
migrations não completava em produção a partir daquela revisão.

Três defeitos da mesma classe, **SQL válido em SQLite e inválido em Postgres**:

| Revisão | SQL | Erro em PG | Caminho |
| --- | --- | --- | --- |
| `adr384cnpjraiz` | `GLOB` no CHECK de `cnpj_raiz` | `PostgresSyntaxError` | upgrade |
| `adr414flip` | `SET regime_completo = 1` em coluna `boolean` | `DatatypeMismatchError` | upgrade |
| `adr378expira` | `rowid` no dedup | `UndefinedColumnError` | downgrade |

O segundo estava **escondido atrás do primeiro**: CI para no primeiro erro, então nenhuma
execução jamais o revelou. Só apareceu ao rodar a cadeia contra PG real depois de
consertar o `GLOB`.

### Por que ficou invisível por ~18 dias

1. A suíte roda em SQLite, onde os três são válidos — a classe já registrada em
   "model ≠ SQLite migrado ≠ PG".
2. Dos três call-sites de `alembic upgrade head` em CI, **nenhum estava vivo e obrigatório**:
   `frontend-e2e` é opt-in por label (`skipped` em 25/25 runs recentes) e os dois de
   `nightly.yml` estão `disabled_manually` desde 2026-06-15.
3. `backend/tests/test_alembic_guardrails.py` **documenta a lacuna no próprio docstring**
   ("o que este arquivo NÃO testa: que as migrations rodam corretamente em PostgreSQL —
   cobrir em F7"). A cobertura foi deferida e esquecida.

`copy_from` **não** é o veículo, ao contrário do que a hipótese inicial supunha: em PG o
batch não recria a tabela, e o `GLOB` chega via `ALTER TABLE ... ADD CONSTRAINT` normal.
A família é a da [[ADR-423]] só no sentido de "migration escrita olhando SQLite".

## Decisão

**D1 — Conserto in loco, não migration de reparo.** Migration nova não ajuda: a cadeia
nunca *chega* nela em PG. Não há estado a reparar, porque nenhum banco PG pode ter passado
por essas revisões; bancos SQLite existentes mantêm a expressão antiga, semanticamente
idêntica.

**D2 — Ramificar por dialeto quando não existe forma portátil.** `cnpj_raiz` usa
`~ '^[0-9]{8}$'` em PG e `GLOB` de 8 dígitos em SQLite, via `op.get_context().dialect.name`
(precedente em 10+ migrations). **Não** existe meio-termo portátil aqui:
`NOT LIKE '%[^0-9]%'` é **vacuidade silenciosa** — nenhum dos dois motores tem classe de
caractere em `LIKE`, e o predicado aceita `'1234567a'` (medido). Onde a forma portátil
existe de fato — `true`/`false` em vez de `1`/`0`, `ROW_NUMBER()` em vez de `rowid` — use
a portátil e não ramifique.

**D3 — O gate é `alembic upgrade head` contra Postgres em job required.** Job
`migrations-postgres` em `ci.yml`, path-filtrado pelo output `migration` já existente,
dentro de `all-green` e do registro da [[ADR-320]]. É o caminho que produção percorre.

**D4 — Gate estático offline foi considerado e descartado.** Varrer o SQL emitido por
`alembic upgrade head --sql` com o parser real do PostgreSQL acha o `GLOB` (medido: 643
statements, 1 falha). Mas `adr414flip` emite **só um comentário** em modo offline, então o
gate ficaria **verde e cego** exatamente onde morava o segundo defeito — pior que gate
ausente. Serve como ferramenta de investigação, não como gate.

## Consequências

- Custo: ~1 job de CI (container PG + `pip install`) nos PRs que tocam
  `backend/alembic/versions/**`, `backend/app/models/**` ou `ci.yml`.
- O job **não** fecha quatro eixos, declarados no comentário dele: `downgrade` completo
  (há barreira intencional da [[ADR-154]] M3 e um bug pré-existente de índice do lado
  SQLite), drift model↔schema em PG (`alembic check` acusa ~40 diferenças pré-existentes),
  banco **populado** (roda sobre DB vazio), e o que o modo offline esconde.
- Dois achados pré-existentes ficam **abertos** e fora do escopo desta nota: o drift de
  ~40 itens do `alembic check` em PG, e o `ValueError: No such index: 'ix_sugagg_ws_thesis'`
  no downgrade de `adr290supersede` em SQLite.

## Verificação

PostgreSQL 16.14 real (`postgres:16-alpine`, imagem do CI): `upgrade head` rc=0, 130
migrations; CHECK enforçada e não-vacua; downgrade/re-upgrade rc=0. SQLite: rc=0 nos dois
sentidos. A/B na mesma máquina com o comando do job — pré-fix (`c9be1bf9`) rc=1
`syntax error at or near "GLOB"`, pós-fix rc=0. Suítes: `backend/tests` 3679 passed,
`tests/` 7977 passed, `test_alembic_guardrails.py` 4 passed.
