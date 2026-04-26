# Track A7.0 — `ConfigStore` protocol + adapters

> **Lane ID:** A7.0
> **Branch prefix:** `agent/a7-0-config-store/*`
> **Depende de:** — (lane fundacional)
> **Paralelo com:** **NENHUMA lane A7** (bloqueia toda Onda 2). Pode rodar em paralelo a lanes de outros sprints (A6.events-followup, F7F-Analyst, Report v2.E.*) desde que respeite hotspots.
> **Conflita com:** qualquer commit ativo em `pipeline/stage_config.py`, `pipeline/ports/`, `backend/app/services/config_materializer.py`.
> **Onda:** 1 (única lane da Onda 1)
> **Plano canônico:** [CONFIG_CUTOVER_PLAN.md §5.0](../CONFIG_CUTOVER_PLAN.md#§50-a70--configstore-protocol--adapters)
> **ADR:** [ADR-134](../DECISIONS.md#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend) — **DEVE estar em estado Decidido antes da primeira linha de código** (gate G1).
> **Supervisão CTO:** G1 antes de codar · G2 antes de Alembic (n/a aqui — sem schema novo) · G3 pré-merge.

> **Objetivo (1 frase):** introduzir `ConfigStore` como protocol read-only em `pipeline/ports/`, com 2 adapters (`FileConfigStore` legado + `DBConfigStore` produção), injetado via `StageConfig`. **Zero call-sites migrados** nesta lane.

---

## Por que esta lane primeiro

Toda a Sprint A7 depende de uma boundary única para ler config. Sem ela, A7.1/A7.2a/A7.2b fariam migrações independentes (cada lane criando sua própria abstração) e a Onda 4 (cleanup) viraria refactor de 4 padrões diferentes. A7.0 é fundação: cria o Protocol + adapters, mas **não migra ninguém**. Lanes da Onda 2 ficam livres para migrar seus call-sites usando o Protocol pronto.

---

## Regras inegociáveis

Do CLAUDE.md + ADRs:

1. **Pipeline não importa framework** (CLAUDE.md §Regras críticas, [ADR-097](../DECISIONS.md)): `pipeline/**/*.py` não importa `fastapi`/`celery`/`sqlalchemy`. Enforçado por `dev/check_pipeline_boundaries.py`. Protocol em `pipeline/ports/` + adapter SQLAlchemy em `backend/app/services/`.
2. **Stateless rigoroso** ([ADR-111](../DECISIONS.md#adr-111--stateless-rigoroso-em-backendapp-e-pipeline-a6f6)): zero `@lru_cache`/`@functools.cache`/`cached_property` no read-path. `FileConfigStore` pode cachear em construtor (singleton lazy idempotente, padrão R19) — registrar em [STATELESS_AUDIT.md](../STATELESS_AUDIT.md).
3. **Money nunca é float** ([ADR-090](../DECISIONS.md)): tipos retornados pelo Protocol que carregam dinheiro usam `Decimal` (`amount`, `rate`) ou `int64` cents (`brl_cents`).
4. **Funções 4-20 linhas, arquivos ≤500, nomes específicos** (CLAUDE.md §Code style).
5. **Sem `Dict[str, Any]` cross-boundary** — métodos do Protocol retornam dataclasses tipadas (`CategorizationConfig`, `FamilyMembersConfig`, …), nunca `dict`.
6. **DeprecationWarning com data** (P6 do plano): `FileConfigStore.__init__` emite warning citando A7.5 como remoção.
7. **Preserve comentários existentes** em qualquer arquivo refatorado.

---

## Estado atual — arquivos críticos

| Arquivo | Linhas | Função |
|---|---|---|
| `pipeline/stage_config.py` | ~120 | `StageConfig` dataclass — recebe campo novo `config_store` |
| `backend/app/services/config_materializer.py` | ~250 | `serialize_*` + `materialize_config` — **NÃO TOCAR nesta lane** |
| `backend/app/repositories/config_blob_repository.py` | ~180 | `ConfigBlobRepository` (já existe; reutilizar) |
| `pipeline/artifact_store.py` | — | Protocol `ArtifactStore` — **referência arquitetural**, mesmo padrão |
| `tests/fakes/` | — | Fakes já existem para `ArtifactStore`; criar `InMemoryConfigStore` aqui |

---

## Sequência de commits sugerida

### Commit 1 — Tipos de domínio
```
feat(pipeline): add typed config dataclasses (A7.0)
```
- `pipeline/domain/types/config.py` — dataclasses frozen para todos os 7 retornos do Protocol:
  - `CategorizationConfig` (tree de categorias + keywords)
  - `FamilyMembersConfig` (members + bank_member + workspace meta)
  - `InstitutionsCatalog` (mapa code → InstitutionDef)
  - `ReportLayout` (sections + components)
  - `TransferConfig` (recipients + patterns)
  - `FiscalParameters` (stub — usado em A7.2b)
  - `MarketRate` (stub — usado em A7.2b)
- Tipos derivam dos schemas Pydantic já existentes em `backend/app/schemas/dto/*` quando possível (mapear, não duplicar).

### Commit 2 — Protocol
```
feat(pipeline): add ConfigStore protocol (A7.0 · ADR-134)
```
- `pipeline/ports/config_store.py` — `class ConfigStore(Protocol)` + 7 métodos.
- Docstring 1 linha por método.
- Stubs `get_fiscal_for_period`/`get_market_rate` retornam `FiscalParameters`/`Decimal` mas adapters levantam `NotImplementedError("populated in A7.2b")` — assinatura travada agora para A7.2b não tocar Protocol.

### Commit 3 — FileConfigStore (legado)
```
feat(pipeline): add FileConfigStore adapter (legacy, deprecated A7.5)
```
- `pipeline/adapters/file_config_store.py` — lê de `PROJECT_DIR / "config"`.
- `__init__` emite `warnings.warn("FileConfigStore is deprecated and will be removed in A7.5", DeprecationWarning, stacklevel=2)`.
- Implementa **somente** `get_categorization`, `get_family_members`, `get_institutions`, `get_report_layout`, `get_transfer_config`. Stubs A7.2b raise.
- Cache de leitura em `__init__` (lazy load idempotente; OK por R19) — registrar em STATELESS_AUDIT.md.

### Commit 4 — DBConfigStore (produção)
```
feat(backend): add DBConfigStore adapter (A7.0 · ADR-134)
```
- `backend/app/services/db_config_store.py` — recebe `db: Session` no construtor.
- Delega aos repositórios já existentes (`ConfigBlobRepository.get_by_workspace(...)` etc).
- Stubs A7.2b raise.

### Commit 5 — `StageConfig` aceita `ConfigStore`
```
feat(pipeline): StageConfig.config_store with FileConfigStore default (A7.0)
```
- `pipeline/stage_config.py` — campo novo `config_store: ConfigStore` com default factory `FileConfigStore`.
- **Nenhum call-site usa ainda** — só defaultado.

### Commit 6 — Fake + testes
```
test(pipeline): InMemoryConfigStore fake + Protocol tests (A7.0)
```
- `tests/fakes/in_memory_config_store.py` — fake nomeado, ImplementaConfigStore, recebe dict no construtor.
- `tests/test_config_store_protocol.py` — testes de Protocol shape (`isinstance(FileConfigStore(), ConfigStore)`).
- `backend/tests/test_db_config_store.py` — adapter integra com fixture SQLAlchemy.
- 2 testes de domain service refatorados para usar `InMemoryConfigStore` em vez de monkeypatch (escolher 2 simples; mais migrações ficam para A7.1).

### Commit 7 — Documentação
```
docs(a7): mark A7.0 ✅ + STATELESS_AUDIT entry for FileConfigStore
```
- BACKLOG: status A7.0 ☐ → 🚧 G3 → ✅ (após CTO).
- CHANGELOG `[Unreleased]`: bullet "A7.0 ConfigStore protocol entregue (ADR-134)".
- STATELESS_AUDIT: nova entrada §2 documentando `FileConfigStore` como singleton lazy idempotente.

---

## Gates de push

Antes de qualquer `git push origin main`:

```bash
pre-commit run --all-files
pytest tests -q
pytest backend/tests -q
make smoke               # ou comando equivalente em Makefile
git fetch origin && git rebase origin/main
pytest backend/tests -q  # re-roda pós-rebase (CLAUDE.md §Git)
```

Falha em qualquer gate → não pusha. Corrige primeiro.

---

## Acceptance gates (CONFIG_CUTOVER_PLAN.md §5.0)

- [ ] Protocol em `pipeline/ports/config_store.py` ✓
- [ ] `FileConfigStore` adapter funcional + DeprecationWarning ✓
- [ ] `DBConfigStore` adapter funcional ✓
- [ ] `StageConfig.config_store` campo opcional com default ✓
- [ ] `InMemoryConfigStore` fake disponível em `tests/fakes/` ✓
- [ ] **Zero call-sites migrados** (`grep -rn "ConfigStore" pipeline/ scripts/ backend/` = só protocol + 2 adapters + testes) ✓
- [ ] `pytest tests -q && pytest backend/tests -q` verdes ✓
- [ ] `dev/check_pipeline_boundaries.py` passa ✓
- [ ] `make smoke` verde ✓
- [ ] CTO G1 (ADR-134) ✅ + G3 (PR review) ✅

---

## O que NÃO entrega

- Migração de qualquer call-site existente (fica para A7.1).
- Implementação de `get_fiscal_for_period` / `get_market_rate` (fica para A7.2b — métodos viram `NotImplementedError`).
- Remoção de `materialize_config` (fica para A7.5).
- UI nova ou endpoint novo (lane é puro backend/pipeline boundary).

---

## Coordenação com outros agentes

- **Bloqueia toda Onda 2 A7.** Avise no CHANGELOG `[Unreleased]` quando começar e quando terminar — outras lanes esperam.
- **Não conflita** com A6.events-followup, F7F-Analyst, Report v2.E.*. Hotspot único: `BACKLOG.md` + `CHANGELOG.md` (protocolo §Hotspots do CLAUDE.md).
- **CTO supervision:** G1 (ADR-134 mergeada) é pré-requisito. Se ADR-134 ainda está draft, **pare** e peça para o orquestrador invocar `senior-cto` para revisar.

---

## Rollback

`git revert <merge-commit>` apaga Protocol + adapters + tipos. Ninguém depende ainda — revert é seguro.

---

## Estimativa

~1.5–2 sessões de 2h. Trabalho é mais arquitetura/typing do que código pesado.
