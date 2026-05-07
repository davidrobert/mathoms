---
id: TRACK-a7-2b-fiscal-market-tables
type: track
title: "Track A7.2b — Tabelas globais `fiscal_parameters` + `market_rates` versionadas"
sprint: A7
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a7
  - status/consumed
---

# Track A7.2b — Tabelas globais `fiscal_parameters` + `market_rates` versionadas

> **Lane ID:** A7.2b
> **Branch prefix:** `agent/a7-2b-fiscal-market-tables/*`
> **Depende de:** A7.0 ✅ mergeada (Protocol já tem stubs `get_fiscal_for_period` / `get_market_rate`).
> **Paralelo com:** A7.1, A7.2a, A7.4.
> **Conflita com:** qualquer commit ativo em `pipeline/domain/services/{previdencia_analyzer,cenarios_conjuge_analyzer,patrimonio_types}.py`, `backend/app/models/`, `backend/app/services/db_config_store.py`, `pipeline/adapters/file_config_store.py`.
> **Onda:** 2 (paralelizável).
> **Plano canônico:** [CONFIG_CUTOVER_PLAN.md §5.2b](../CONFIG_CUTOVER_PLAN.md#§52b-a72b--tabelas-globais-fiscalmarket-versionadas)
> **ADR:** [ADR-135](../DECISIONS.md#adr-135--versionamento-temporal-de-séries-fiscais-e-câmbio) — **G1 obrigatório antes de codar**.
> **Supervisão CTO:** G1 (ADR) · G2 (schema) · G3 (PR pré-merge).

> **Objetivo (1 frase):** transformar `parametros_fiscais.json` e `taxas.json` em tabelas globais versionadas por data; pipeline lê via `ConfigStore` com escopo de período; reproducibilidade histórica garantida.

---

## Por que esta lane

Hoje:
- `parametros_fiscais.json` e `taxas.json` vivem só no disco, sem vigência temporal.
- Atualizar IR/PGBL/INSS para 2026 sobrescreve 2025 → relatório histórico passa a ficar errado.
- São séries de **mercado**, não config de cliente — não pertencem a um workspace.

Esta lane modela como tabelas globais com `effective_from/to`. Pipeline passa a perguntar "quais parâmetros vigentes em <período do relatório>?" — reproducibilidade garantida.

---

## Regras inegociáveis

1. **Money em DECIMAL ou BIGINT cents** ([ADR-090](../DECISIONS.md)) — `lucro_presumido_aliquota` em `DECIMAL(5,4)`; `pgbl_limit_brl_cents`/`inss_ceiling_brl_cents` em `BIGINT`. `MarketRate.rate` em `DECIMAL(20,10)` (câmbio precisa de 4-6 casas).
2. **Cache Redis com invalidação por evento** ([ADR-111](../DECISIONS.md)) — sem `@lru_cache` no read-path. Eventos: `fiscal_parameter.published`, `market_rate.published`.
3. **Pipeline não importa SQLAlchemy** — `previdencia_analyzer` etc recebem `FiscalParameters` via construtor (já existe parâmetro de config tipado em ADR-097/D2).
4. **`pipeline/ports/config_store.py` NÃO é modificado por esta lane** — A7.0 já adicionou os stubs. Se você precisa mudar a assinatura, **pare** e coordene com outras lanes.
5. **Backwards-compatible**: nova migration **adiciona** tabelas + popula via seed; **não** remove `parametros_fiscais.json`/`taxas.json` até A7.5. Esta lane delete os JSONs no commit final **após** validar smoke verde com tabelas DB-first.
6. **Determinismo histórico** — golden test obrigatório para um período de 2025 produz output idêntico ao baseline pré-cutover.

---

## Entregáveis (CONFIG_CUTOVER_PLAN.md §5.2b)

### Schema (Alembic)

```sql
CREATE TABLE fiscal_parameters (
  id UUID PRIMARY KEY,
  year INT NOT NULL,
  ir_brackets JSONB NOT NULL,
  pgbl_limit_brl_cents BIGINT NOT NULL,
  inss_ceiling_brl_cents BIGINT NOT NULL,
  lucro_presumido_aliquota DECIMAL(5,4) NOT NULL,
  effective_from DATE NOT NULL,
  effective_to DATE,
  source TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_fiscal_period ON fiscal_parameters (effective_from, effective_to);

CREATE TABLE market_rates (
  id UUID PRIMARY KEY,
  pair TEXT NOT NULL,
  rate DECIMAL(20,10) NOT NULL,
  observed_at DATE NOT NULL,
  source TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (pair, observed_at)
);
CREATE INDEX idx_market_pair_observed ON market_rates (pair, observed_at DESC);
```

### Backend

1. **Models** (`backend/app/models/fiscal.py` + `backend/app/models/market.py`).
2. **Repositories** (`fiscal_parameter_repository.py`, `market_rate_repository.py`).
3. **Seed** (`backend/alembic/data_migrations/seed_fiscal_2024_2026.py`):
   - Popula `fiscal_parameters` com rows para 2024, 2025, 2026 a partir do conteúdo atual de `config/parametros_fiscais.json` (com `effective_from`/`to` por ano fiscal).
   - Popula `market_rates` com a cotação atual em `config/taxas.json` (data = `today()`, source = "config/taxas.json snapshot 2026-04-26").
4. **`DBConfigStore`** ganha implementação real de `get_fiscal_for_period` e `get_market_rate` (eram `NotImplementedError` em A7.0).
5. **`FileConfigStore`** ganha implementação para os mesmos dois métodos lendo de `config/*.json` — bridge para A7.5.
6. **Cache Redis** (`backend/app/services/fiscal_cache.py`): chave `fiscal:{year}` com TTL 1h + invalidação ativa por evento. Para `market_rates`, cache `market:{pair}:{observed_at}` (immutable após gravado).
7. **API admin (read-only)** — `GET /api/v1/admin/fiscal-parameters`, `GET /api/v1/admin/market-rates`. CRUD completo fica para F7F-Local internal ops; aqui só leitura via curl/admin.

### Pipeline

8. **`pipeline/domain/services/previdencia_analyzer.py`**:
   - Construtor ganha `fiscal: FiscalParameters` (não `Path` nem `dict` — ADR-097 D2).
   - Adapter (em `backend/app/services/pipeline_adapter.py`) resolve via `config_store.get_fiscal_for_period(ctx.period)`.

9. **`pipeline/domain/services/cenarios_conjuge_analyzer.py`**:
   - Construtor ganha `cambio_usd_brl: Decimal` (resolvido via `config_store.get_market_rate("USD/BRL", ctx.report_date)`).

10. **`pipeline/domain/services/patrimonio_types.py`**:
    - Idem para taxas.

### Determinismo

11. **Golden histórico** (`tests/test_e5_fiscal_temporal_golden.py`):
    - Fixture: workspace com período fechado em 2025-Q4.
    - Roda E5 com seed Alembic populado.
    - Compara output byte-a-byte com baseline pré-cutover.
    - **Falha → não merge.**

### Limpeza

12. `git rm config/parametros_fiscais.json config/taxas.json` no commit final desta lane (após smoke verde com tabelas DB-first).

---

## Sequência de commits sugerida

```
1. feat(backend): fiscal_parameters + market_rates models + Alembic (A7.2b · ADR-135)
2. feat(backend): seed_fiscal_2024_2026 data migration (A7.2b)
3. feat(backend): DBConfigStore.get_fiscal_for_period + get_market_rate (A7.2b)
4. feat(pipeline): FileConfigStore.get_fiscal_for_period + get_market_rate (bridge A7.5) (A7.2b)
5. refactor(pipeline): previdencia_analyzer accepts FiscalParameters via constructor (A7.2b)
6. refactor(pipeline): cenarios_conjuge_analyzer accepts MarketRate via constructor (A7.2b)
7. refactor(pipeline): patrimonio_types accepts MarketRate via constructor (A7.2b)
8. test(pipeline): golden temporal fiscal Q4-2025 (A7.2b)
9. feat(backend): Redis cache for fiscal lookups + invalidation (A7.2b)
10. chore(config): rm parametros_fiscais.json + taxas.json after smoke green (A7.2b)
11. docs(a7): A7.2b ✅ + ADR-135 + CHANGELOG
```

---

## Gates de push

```bash
pre-commit run --all-files
pytest tests -q                                       # pipeline incluindo novo golden
pytest backend/tests -q                               # backend incluindo seed test
make smoke                                            # E2E sem parametros_fiscais.json/taxas.json no host
diff <(git show HEAD~1:tests/fixtures/.../e5-2025q4.json) tests/fixtures/.../e5-2025q4.json  # golden idêntico
```

---

## Acceptance gates (CONFIG_CUTOVER_PLAN.md §5.2b)

- [ ] Tabelas + Alembic + seed ✓
- [ ] `DBConfigStore.get_fiscal_for_period` + `get_market_rate` implementados ✓
- [ ] `FileConfigStore` bridge implementado (vivo até A7.5) ✓
- [ ] 3 domain services migrados (previdência, cenários, patrimônio) ✓
- [ ] Cache Redis com invalidação por evento ✓
- [ ] Golden histórico Q4-2025 idêntico ao baseline ✓
- [ ] `parametros_fiscais.json` + `taxas.json` removidos ✓
- [ ] Smoke E2E verde com JSONs ausentes ✓
- [ ] CTO G1 (ADR-135) ✅ + G2 (schema) ✅ + G3 (PR review) ✅

---

## O que NÃO entrega

- UI completa de admin para CRUD de fiscal/market (fica para F7F-Local internal ops).
- Versionamento mid-year intricado (ADR-135 já documenta `FiscalParameterAmbiguous` — esta lane apenas implementa a regra; testes de "duas reformas no mesmo ano" ficam para quando ocorrer).
- Histórico longo de câmbio (mais de 2 anos) — seed apenas com cotação atual; backfill histórico é decisão de produto futura.

---

## Coordenação com outros agentes

- **Disjunto a A7.1** se A7.1 não tocar `previdencia_analyzer`/`cenarios_*`/`patrimonio_types` (não toca — A7.1 é E3/E4/E5 + materialize). Confirme com `git log --oneline origin/main -- pipeline/domain/services/` antes de cada commit.
- **Disjunto a A7.2a** (Decision aggregate toca outros models/api).
- **Disjunto a A7.4** (docs).
- **Hotspot:** `pipeline/ports/config_store.py` (já criado em A7.0 com stubs). **Não modifique a assinatura** — apenas implemente nos adapters. Se assinatura precisa mudar, abra discussão no CHANGELOG `[Unreleased]`.

---

## Rollback

- Revert PR.
- Tabelas Alembic permanecem (não fazem mal vazias).
- JSONs recuperáveis via git history.
- Domain services voltam ao estado pré-cutover.

---

## Estimativa

~2–3 sessões de 2h.
