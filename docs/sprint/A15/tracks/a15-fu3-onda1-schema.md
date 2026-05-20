---
id: TRACK-a15-fu3-onda1-schema
type: track
title: "Track A15 FU-3 Onda 1 — Schema + repos + models (Debt + property_market_value)"
sprint: A15
plan: PLAN-imovel-financiado
status: ready
created_at: "2026-05-20"
consumed_at: null
agent_role: data-engineer
tags:
  - type/track
  - sprint/a15
  - status/ready
  - area/db
  - area/backend
  - area/persistence
---

# Track A15 FU-3 Onda 1 — Schema + repos + models

> **Lane:** Sprint A15 · **Plano canônico:**
> [PLAN-imovel-financiado](../../../plan/IMOVEL_FINANCIADO/_README.md) §Onda 1
> · **ADR canônica:** [[ADR-227]] §D1 + §D2
> · **Branch prefix:** `agent/a15-fu3-onda1-schema/*`
> · **Pré-requisito externo:** [[ADR-227]] mergeada em `main` ([PR #338](https://github.com/davidrobert/mathoms/pull/338), commit `fe13713`) ✅
> · **Bloqueia:** Onda 2 (backfill — script lê tabelas criadas aqui) + Onda 3 (calculator — adapter lê via repos) + Onda 4 (API — endpoints CRUD)

## Briefing

Persistência base para FU-3 ([[ADR-227]] §D1 + §D2). **Onda 1 não introduz comportamento novo no runtime** — apenas tabelas, modelos, repos, DTOs. Workspace sem rows → calculator e UI continuam com comportamento atual (gate de paridade).

Duas tabelas novas em uma única revision Alembic:

1. **`debt`** ([[ADR-227]] §D1) — agregado de passivo persistido, FK opcional a `family_members` (`ON DELETE SET NULL`) + FK opcional a `property_identity` (`ON DELETE RESTRICT` contra órfão silencioso). Enum `tipo` com 6 valores brasileiros (`financiamento_imobiliario`, `consignado`, `cdc`, `cartao_rotativo`, `rotativo`, `outro`). `saldo_devedor_cents BIGINT` (ADR-090: int cents, nunca float). Suporta migration idempotente via partial unique index `(workspace_id, migration_source_key) WHERE source='baseline_irpf_migration'`. CHECK constraint `chk_debt_identity` exige ao menos uma de `family_member_id`, `property_id`, `descricao` NOT NULL.

2. **`property_market_value`** ([[ADR-227]] §D2) — versionada append-only, 1 row por declaração (usuário corrige criando entry com `valuation_date` atual, não UPDATE). Custo storage trivial (~50 rows/workspace/decade). `superseded_by_id UUID NULL` permite marcar erro sem deletar. Constraint `UNIQUE (property_id, valuation_date)` evita duplicata acidental no mesmo dia.

**Sem mudança runtime.** Calculator, EndividamentoAnalyzer, RealEstateMetrics permanecem inalterados nesta onda. Goldens E5 não mexem.

## Critério de aceite (do plano §Onda 1)

- [ ] Migration Alembic up/down idempotente (`backend/alembic/versions/<hash>_adr227_debt_property_market_value.py`).
  - `upgrade()`: 2× `CREATE TABLE` + índices + CHECK constraints.
  - `downgrade()`: 2× `DROP TABLE` limpo.
  - Test: `cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head`.
- [ ] Models SQLAlchemy novos:
  - `backend/app/models/debt.py` — classe `Debt`.
  - `backend/app/models/property_market_value.py` — classe `PropertyMarketValue`.
  - Exportados em `backend/app/models/__init__.py`.
- [ ] Repos thin:
  - `backend/app/repositories/debt_repository.py` — `get_by_id`, `list_for_workspace`, `list_for_property`, `create`, `update`, `delete`, `bulk_create_from_migration`.
  - `backend/app/repositories/property_market_value_repository.py` — `latest_by_property`, `list_for_property`, `create`, `supersede`.
- [ ] Pydantic DTOs:
  - `backend/app/schemas/dto/debt/{command,response}.py` — `DebtCreate`, `DebtUpdate`, `DebtResponse`.
  - `backend/app/schemas/dto/property_market_value/{command,response}.py` — `PropertyMarketValueCreate`, `PropertyMarketValueResponse`.
- [ ] Testes unit cobrindo:
  - CRUD básico em ambos os repos.
  - CHECK constraints: `chk_debt_tipo`, `chk_debt_source`, `chk_debt_pct_atribuicao`, `chk_debt_identity`, `chk_pmv_source`, `chk_pmv_confidence`.
  - UNIQUE constraints: `uq_property_valuation_date`, `uq_debt_migration_source` (partial).
  - FK behavior: `ON DELETE CASCADE` (workspace), `ON DELETE SET NULL` (family_member), `ON DELETE RESTRICT` (property — deve raise IntegrityError quando há Debt vinculada).
- [ ] Paridade fixture existente: `pytest backend/tests -q` verde.
- [ ] Goldens E5 inalterados: `pytest tests -q` verde.
- [ ] `python3 dev/build_db_schema_reference.py` rodado e [docs/reference/DB_SCHEMA_REFERENCE.md](../../../reference/DB_SCHEMA_REFERENCE.md) regenerado.
- [ ] `pre-commit run --all-files` verde.

## Arquivos esperados

**Novos:**

- `backend/alembic/versions/<hash>_adr227_debt_property_market_value.py`
- `backend/app/models/debt.py`
- `backend/app/models/property_market_value.py`
- `backend/app/repositories/debt_repository.py`
- `backend/app/repositories/property_market_value_repository.py`
- `backend/app/schemas/dto/debt/__init__.py`
- `backend/app/schemas/dto/debt/command.py`
- `backend/app/schemas/dto/debt/response.py`
- `backend/app/schemas/dto/property_market_value/__init__.py`
- `backend/app/schemas/dto/property_market_value/command.py`
- `backend/app/schemas/dto/property_market_value/response.py`
- `backend/tests/repositories/test_debt_repository.py`
- `backend/tests/repositories/test_property_market_value_repository.py`
- `backend/tests/models/test_debt_constraints.py`
- `backend/tests/models/test_property_market_value_constraints.py`

**Editados:**

- `backend/app/models/__init__.py` — export `Debt`, `PropertyMarketValue`.
- `docs/reference/DB_SCHEMA_REFERENCE.md` (auto-gerado).

## Decisões já fechadas (do co-design 2026-05-19)

- **1 revision única** para 2 tabelas — atômico, single rollback se algo der errado em staging.
- **`ON DELETE RESTRICT`** em `Debt.property_id` (não `SET NULL` do briefing original) — consenso `senior-cto` + `data-engineer`. Órfão silencioso é classe inteira de bug invisível em fintech (`investivel_efetivo` infla sem aviso). UX explícita ("Desvincule o débito antes") vence bug silencioso. Modal de exceção permite UPDATE para `property_id=NULL` antes do DELETE em casos legítimos (vendeu imóvel mas refinanciou debt).
- **`saldo_devedor_cents BIGINT`** + `parcela_mensal_cents BIGINT` (ADR-090) — proibido `float`; cents inteiro no DB, `Decimal` em Python no boundary.
- **Versionada append-only** em `property_market_value` (`data-engineer`) — histórico vale custo storage trivial (~50 rows/workspace/decade). `superseded_by_id` permite marcar erro sem deletar.
- **`migration_source_key`** persistido (não logado) — permite re-conciliar se descobrir bug na migration. Custo: 1 varchar por row.
- **`percentual_atribuicao_imovel`** (sugestão `product-designer`) — cobre co-propriedade familiar com debt no nome de 1 cônjuge. Default 100% quando `property_id` declarado; rateio é override consciente. CHECK constraint garante 0 < pct ≤ 100.
- **Enum `tipo` com `cartao_rotativo` separado de `rotativo` desde V1** — cartão tem comportamento diferente em E5 (categorização Cerbasi anti-rotativo). Schema evolution de enum é caro depois.
- **CHECK constraint `chk_debt_identity`** — evita row órfã sem nenhuma identidade (sem membro, sem property, sem descrição).
- **Índice composto `(workspace_id, property_id, valuation_date DESC)`** em `property_market_value` — resolve `latest_by_property` sem ORDER BY caro. Use `DISTINCT ON` no Postgres, `ROW_NUMBER` no SQLite.
- **Sem cascade de delete em Debt→workspace via row órfã** — `ON DELETE CASCADE` no `workspace_id` ainda apaga tudo quando workspace é deletado (consistência com pattern do repo).

## Testes (comandos exatos)

```bash
cd backend && alembic upgrade head && alembic downgrade -1 && alembic upgrade head
pytest backend/tests/test_alembic.py -q
pytest backend/tests/repositories/test_debt_repository.py -q
pytest backend/tests/repositories/test_property_market_value_repository.py -q
pytest backend/tests/models/test_debt_constraints.py -q
pytest backend/tests/models/test_property_market_value_constraints.py -q
pytest backend/tests -q                          # paridade geral
pytest tests -q                                  # goldens E5 inalterados
python3 dev/build_db_schema_reference.py
pre-commit run --all-files
```

## Riscos

- **R1** — FK `Debt.property_id` com `ON DELETE RESTRICT` pode bloquear delete de workspace via cascade. **Não bloqueia:** `Debt.workspace_id` tem `ON DELETE CASCADE` (path superior). Quando workspace é deletado, `Debt` é apagado antes do `PropertyIdentity`, então RESTRICT não dispara. Test integration cobre.
- **R2** — Partial unique index em SQLite pode comportar diferente do PostgreSQL. Use `sqlite_where` + `postgresql_where` na declaração SQLAlchemy (pattern de `WorkspacePropertyOverride` em [`backend/app/models/property_identity.py`](../../../../backend/app/models/property_identity.py)).
- **R3** — `BIGINT cents` em SQLite é `INTEGER` (64-bit max via NUMERIC affinity). Para R$ 100M (1e10 cents), cabe folgado em INTEGER64. Test sanity: roundtrip de R$ 999.999.999,99 (~1e10 cents).
- **R4** — `CHECK constraint chk_debt_identity` falha se tentar criar Debt sem nenhuma identidade — comportamento desejado. UI/API garante pelo menos `descricao` em Onda 4.

## Ligações

- Plano canônico: [PLAN-imovel-financiado](../../../plan/IMOVEL_FINANCIADO/_README.md) §Onda 1
- ADR canônica: [[ADR-227]] §D1 + §D2
- Sprint MOC: [[MOC-sprint-a15]]
- Onda 2 (próximo): [a15-fu3-onda2-backfill](a15-fu3-onda2-backfill.md) — script de backfill consome tabelas criadas aqui
- Pattern reuso: [`backend/app/models/property_identity.py`](../../../../backend/app/models/property_identity.py) (partial unique index pattern)
- ADRs relacionados: [[ADR-090]] (cents), [[ADR-097]] (DTOs tipados), [[ADR-215]] (PropertyIdentity FK target), [[ADR-225]] (codigo_rfb invariante — Debt referencia UUID, não codigo_rfb)
