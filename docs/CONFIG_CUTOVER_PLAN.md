# Plano — Cutover de `config/` para DB multi-tenant (Sprint A7)

> **Status:** 🚧 em andamento (2026-04-27) — Onda 1 ✅ (A7.0) · Onda 2 fechada (A7.1 ✅ + A7.2a ✅ + A7.2b ✅ + A7.4 ✅) · **A7.6 aberta** (rules-as-code: dissolve `docs/methodology/` que A7.4 introduziu como solução incompleta — gate G1 pendente) · Onda 3 destravada (A7.3 abre após A7.1) · Onda 4 (A7.5 cleanup) bloqueada.
> **Audiência:** agentes LLM em paralelo (Onda 2 com até 4 agentes simultâneos) + supervisor CTO (humano ou agente `senior-cto`).
> **Premissa central:** o produto **continua operando em produção** entre cada onda. Nenhum passo pode quebrar smoke E2E ou bloquear geração de relatório de workspace existente.
> **Referências:** [BACKLOG.md §Sprint A7](BACKLOG.md#sprint-a7--config-db-cutover-cli-legacy-removal), [DECISIONS.md ADR-134..138](DECISIONS.md#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend), [CLAUDE.md §Regras críticas](../CLAUDE.md#regras-críticas-invariantes-do-repositório).

---

## §1 Sumário executivo

A versão CLI inicial usava `config/*.json` + `*.md` como única fonte de verdade — mono-cliente, mono-workspace. O produto multi-tenant atual herdou esses arquivos parcialmente: 3 deles (`categorization`, `family_members`, `report_layout`) já têm DB+API+UI; outros 8 ainda vivem no disco. Nenhum dos 11 está **realmente** desacoplado: o pipeline ainda lê de `config/` direto, ou indiretamente via `materialize_config()` (DB → disco → leitura).

A meta da Sprint A7 é fechar esse cutover, separando os arquivos em três naturezas distintas (cliente / mercado / metodologia), sem quebrar nenhum workspace existente, e remover `config/` no final.

**Escopo:** 11 arquivos.

| Arquivo | Natureza | Destino |
|---|---|---|
| `family_members.json` | Cliente | DB+API+UI ✅ → ler via `ConfigStore` (A7.1) |
| `categorization.json` | Cliente + Produto (taxonomia base) | Split em catalog + override (A7.3) |
| `institutions.json` | Produto (catalog) + Cliente (subset usado) | Catalog global; subset já em `BankAccount` (A7.3) |
| `report_layout.yaml` | Produto (template) | DB+API ✅ → ler via `ConfigStore` (A7.1); UI editor é decisão de produto futura |
| `decisions.md` | **Cliente** ⚠️ contém valores BRL reais | Entidade `Decision` event-sourced (A7.2a) |
| `parametros_fiscais.json` | Mercado (séries temporais) | Tabela global versionada por ano (A7.2b) |
| `taxas.json` | Mercado (séries temporais) | Tabela global versionada por data (A7.2b) |
| `definitions.md` | **Híbrido** (60% cliente em DB · 25% universal · 15% duplica CLAUDE.md) | A7.4 ✅ moved → A7.6 dissolve: ~80% drop (já em DB ou duplica), ~20% docstrings + ADR-139/140 |
| `regras_composicao_patrimonial.md` | **Híbrido** (regras universais 7-bucket + exemplos cliente) | A7.4 ✅ moved → A7.6 dissolve: docstring no classifier `cash_flow_builder` + ADR-140 |
| `source_hierarchy.md` | **Híbrido** (hierarquia universal + bancos cliente) | A7.4 ✅ moved → A7.6 dissolve: docstring em `income_origin_resolver` + ADR-141; banco→tier vai p/ DB `BankAccount.source_tier` |
| `milhas.md` | **Híbrido** (método de valuation universal + programas cliente) | A7.4 ✅ moved → A7.6 dissolve: método em docstring `parse_milhas_md` + ADR-142; programas migram p/ `storage/<ws>/notes/milhas.md` (gitignored) — débito técnico p/ A8.1 (`MileageProgram` DB entity) |

**Resultado final pós-A7:** zero arquivos em `config/` (diretório removido); pipeline lê tudo via `ConfigStore` (DB-first); séries fiscais/câmbio versionadas por data; entidade `Decision` substitui markdown editorial; `docs/methodology/` deletado (path proibido); regras universais vivem em docstrings + ADRs co-localizados com o código que enforce.

---

## §2 Diagnóstico — 11 arquivos (estado em 2026-04-26)

| Arquivo | DB | API | UI | Pipeline lê | Multi-tenant | Sensibilidade PII |
|---|:---:|:---:|:---:|---|:---:|---|
| `family_members.json` | ✅ | ✅ | ✅ | 🟡 disco (via `materialize_config`) | ✅ | nomes da família |
| `categorization.json` | ✅ | ✅ | ✅ | 🟡 disco (via `_init_config`) | ✅ | — |
| `report_layout.yaml` | ✅ | ✅ | ❌ codegen YAML→TS | 🟡 disco (codegen + materialize) | ✅ | — |
| `institutions.json` | ✅ | ✅ (read) | ❌ | 🟡 seed | ✅ | — |
| `decisions.md` | ❌ | ❌ | ❌ | 📄 ref (não parseado) | ❌ global | ⚠️ valores BRL |
| `parametros_fiscais.json` | ❌ | ❌ | ❌ | ✅ direto | ❌ global | — |
| `taxas.json` | ❌ | ❌ | ❌ | ✅ direto | ❌ global | — |
| `definitions.md` | ❌ | ❌ | ❌ | 📄 ref | ❌ global | — |
| `regras_composicao_patrimonial.md` | ❌ | ❌ | ❌ | 📄 ref | ❌ global | — |
| `source_hierarchy.md` | ❌ | ❌ | ❌ | 📄 ref | ❌ global | — |
| `milhas.md` | ❌ | ❌ | ❌ | 📄 ref | ❌ global | — |

**Riscos confirmados antes do plano:**

- **R1 — Materialização disco-side:** `serialize_*` em `backend/app/services/config_materializer.py` escreve cópia em `config/` antes de E5/E6 lerem. Janela de race + dois sources of truth.
- **R2 — `decisions.md` viola política de PII:** valores reais em BRL (R$117.430, R$30k/mês) versionados em git. CLAUDE.md §Regras críticas proíbe.
- **R3 — Séries fiscais sem vigência:** se IR/PGBL mudarem, relatórios históricos passam a usar parâmetros do ano errado.
- **R4 — `categorization` mistura template + override:** edição global pelo dev sobrescreve customização do workspace, ou customização do workspace impede update do template.

---

## §3 Princípios de execução

### P1 — Produto não para entre ondas
Cada onda fechada **deve** deixar smoke E2E verde em `main`. Nenhum step pode "deixar pra arrumar depois". Se um cutover é incompatível com legado, a onda implementa **bridge** (read-path duplo) e a remoção do legado vai para a onda seguinte.

### P2 — Pipeline não importa framework
`pipeline/**` continua sem importar SQLAlchemy/FastAPI (CLAUDE.md §Regras críticas). `ConfigStore` é definido como `Protocol` em `pipeline/ports/config_store.py`; adapter DB vive em `backend/app/services/db_config_store.py`. Pipeline injeta via `StageConfig`.

### P3 — Stateless rigoroso (ADR-111)
Caches de leitura vão para Redis (`SET NX + TTL`), nunca `@lru_cache` no processo. Se uma tabela global é hot-path (ex.: `FiscalParameter` lido em todo `e5_analyze`), invalidação é via evento (`fiscal_parameter.published`) — nunca TTL "esperançoso" com janela de inconsistência.

### P4 — Money nunca é float (ADR-090)
`Decision.amount_brl` em `int64` cents OR `Money` Pydantic. `FiscalParameter.ir_brackets` em string decimal no wire.

### P5 — One ADR per decisão estrutural, antes de codar
ADRs 134–138 escrevem-se **antes** das lanes correspondentes começarem. CTO assina antes de qualquer commit de código. Lane sem ADR mergeada = lane bloqueada.

### P6 — Bridges têm prazo
Toda compat layer (FileConfigStore, materialize_config, fallback disco) tem **DeprecationWarning** + entrada em [STATELESS_AUDIT.md](STATELESS_AUDIT.md) ou §6 deste plano com data de remoção. Janela máxima: até A7.5.

### P7 — Reversível sempre que possível
Cada lane fecha com PR atômico, mergeada via fast-forward em `main`. Rollback = `git revert <merge-commit>`. Schema migrations Alembic são **adicionar coluna nullable + populate + flip** — nunca DROP COLUMN no mesmo PR que adiciona uso.

---

## §4 Mapa de ondas + paralelismo

```
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 1 — Fundação (1 lane, BLOQUEANTE — sem paralelismo)              ║
╠═══════════════════════════════════════════════════════════════════════╣
║  A7.0  ConfigStore protocol + adapters                                 ║
║         pipeline/ports/config_store.py (Protocol)                      ║
║         pipeline/adapters/file_config_store.py (legacy, deprecation)   ║
║         backend/app/services/db_config_store.py (DB-first)             ║
║         StageConfig.config_store: ConfigStore                          ║
║   Aceita: zero call-sites migrados; novo Protocol existe; testes       ║
║   verdes; smoke E2E sem regressão.                                     ║
╚═══════════════════════════════════════════════════════════════════════╝
                              │ A7.0 mergeada em main
                              ▼
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 2 — Cutover paralelizável (até 4 agentes simultâneos)             ║
╠═══════════════════════════════════════════════════════════════════════╣
║  A7.1   Cutover materialize_config → ConfigStore                       ║
║          (categorization, family_members, report_layout, institutions, ║
║           transfer_configs)                                            ║
║          Branch: agent/a7-1-cutover-materialize/*                      ║
║          Toca: pipeline/stages/*, scripts/e[345]*.py,                  ║
║                backend/app/services/config_materializer.py             ║
║                                                                        ║
║  A7.2a  Decision aggregate                                             ║
║          Tabelas: decisions, decision_events                           ║
║          Endpoints: /v1/workspaces/{id}/decisions                      ║
║          UI: tela "Plano de Ação" no relatório (S? em report_layout)   ║
║          Migrator one-shot: dev/migrate_decisions_to_db.py             ║
║          Branch: agent/a7-2a-decision-aggregate/*                      ║
║          Toca: backend/app/{models,application/decisions,api},         ║
║                frontend/src/components/report/sections/Decisions/      ║
║                                                                        ║
║  A7.2b  Tabelas globais fiscal/market versionadas                      ║
║          Tabelas: fiscal_parameters, market_rates                      ║
║          Seed Alembic: data_migrations/seed_fiscal_2024_2026.py        ║
║          ConfigStore extension: get_fiscal_for_period(period)          ║
║          Branch: agent/a7-2b-fiscal-market-tables/*                    ║
║          Toca: backend/app/{models,services/db_config_store},          ║
║                pipeline/domain/services/{previdencia,cenarios}*        ║
║                                                                        ║
║  A7.4   Metodologia → docs/methodology/   (paralelo a tudo,            ║
║          NÃO depende de A7.0; pode rodar em qualquer momento)         ║
║          Move: definitions.md, regras_composicao_patrimonial.md,       ║
║                source_hierarchy.md, milhas.md (parte método)           ║
║          Toca: docs/methodology/*, refs em scripts/e5/e7 (comentário)  ║
║          Branch: agent/a7-4-methodology-docs/*                         ║
╚═══════════════════════════════════════════════════════════════════════╝
                              │ A7.1 mergeada em main
                              ▼
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 3 — Catalog/Override (1 lane, depende de A7.1)                    ║
╠═══════════════════════════════════════════════════════════════════════╣
║  A7.3  Catalog + override resolver para categorization + institutions  ║
║         Tabelas: category_templates, workspace_category_overrides;     ║
║                 institution_catalog (drop config/institutions.json)    ║
║         Resolver: resolve_categories(workspace) = template ⨁ overrides ║
║         Branch: agent/a7-3-catalog-override/*                          ║
╚═══════════════════════════════════════════════════════════════════════╝
                              │ A7.1 + A7.2a + A7.2b + A7.3 + A7.4 mergeadas
                              ▼
╔═══════════════════════════════════════════════════════════════════════╗
║ ONDA 4 — Cleanup final (1 lane, BLOQUEANTE)                            ║
╠═══════════════════════════════════════════════════════════════════════╣
║  A7.5  Remoção de FileConfigStore + materialize_config + config/       ║
║         git rm config/{categorization,family_members,institutions,     ║
║                      report_layout,decisions,parametros_fiscais,       ║
║                      taxas,definitions,regras_*,source_hierarchy,      ║
║                      milhas}.{json,md,yaml}                            ║
║         dev/check_forbidden_paths.py bloqueia config/* novo            ║
║         pipeline/adapters/file_config_store.py removido                ║
║         backend/app/services/config_materializer.py removido           ║
║         Branch: agent/a7-5-cleanup/*                                   ║
╚═══════════════════════════════════════════════════════════════════════╝
```

**Paralelismo dentro de Onda 2:**
- A7.1, A7.2a, A7.2b, A7.4 são **disjuntos por arquivo**. Cada um toca pastas diferentes (ver "Toca:" acima). Quatro agentes podem rodar simultaneamente.
- Hotspot único: `docs/BACKLOG.md` e `docs/CHANGELOG.md`. Aplicar protocolo de hotspot do CLAUDE.md (anunciar, commit ≤5min).

**Bloqueios duros:**
- A7.0 → A7.1 (ConfigStore precisa existir antes de migrar leitores).
- A7.1 → A7.3 (catalog/override só faz sentido depois que leitor é DB-first).
- (A7.1 + A7.2a + A7.2b + A7.3 + A7.4) → A7.5 (não remove arquivos antes de todos os leitores migrarem).

---

## §5 Ondas detalhadas

### §5.0 A7.0 — ConfigStore protocol + adapters

**Onda 1 · 1 lane · ~1.5–2 sessões · agentes paralelos = 1 (bloqueante).**

**Objetivo:** introduzir `ConfigStore` como protocol read-only em `pipeline/ports/`, com dois adapters concretos (DB-first e disco-legacy), injetado via `StageConfig`. **Zero call-sites migrados nesta lane** — só o protocol e os adapters. Testes verdes; smoke E2E verde.

**Entregáveis:**

1. `pipeline/ports/config_store.py` — Protocol tipado:
   ```python
   class ConfigStore(Protocol):
       def get_categorization(self, workspace_id: str) -> CategorizationConfig: ...
       def get_family_members(self, workspace_id: str) -> FamilyMembersConfig: ...
       def get_institutions(self) -> InstitutionsCatalog: ...
       def get_report_layout(self, workspace_id: str) -> ReportLayout: ...
       def get_transfer_config(self, workspace_id: str) -> TransferConfig: ...
       def get_fiscal_for_period(self, period: PeriodKey) -> FiscalParameters: ...  # stub p/ A7.2b
       def get_market_rate(self, pair: str, observed_at: date) -> Decimal: ...       # stub p/ A7.2b
   ```
   Tipos retornados são `dataclass(frozen=True)` ou `pydantic.BaseModel` em `pipeline/domain/types/config.py`.
2. `pipeline/adapters/file_config_store.py` — adapter legacy lendo de `PROJECT_DIR / "config"`. **Emite `DeprecationWarning` no construtor** com data de remoção (A7.5).
3. `backend/app/services/db_config_store.py` — adapter DB que delega aos repositórios já existentes (`CategorizationConfigRepository`, `FamilyMemberConfigRepository`, …). Stubs para `get_fiscal_for_period`/`get_market_rate` raise `NotImplementedError` até A7.2b.
4. `pipeline/stage_config.py` — `StageConfig` ganha campo `config_store: ConfigStore` opcional (default `FileConfigStore` para compat).
5. Testes:
   - `tests/test_config_store_protocol.py` — fakes nomeados (`InMemoryConfigStore`) usados em pelo menos 2 testes de domain service.
   - `backend/tests/test_db_config_store.py` — adapter integra com SQLAlchemy fixture.
6. `docs/STATELESS_AUDIT.md` — entrada nova: `FileConfigStore` é singleton lazy idempotente (cumpre R19), removido em A7.5.

**Acceptance gates:**
- `pytest tests -q && pytest backend/tests -q` verdes.
- `make smoke` (E2E pipeline em workspace fixture) verde.
- `dev/check_pipeline_boundaries.py` passa (pipeline não importa SQLAlchemy).
- Zero call-site existente migrado nesta lane (`grep -rn "ConfigStore" pipeline/ scripts/ backend/` retorna apenas o protocol + os 2 adapters + os testes).

**Não-objetivos:** migrar nenhum chamador. `materialize_config` continua intacto. `_init_config` continua lendo disco direto.

**Rollback:** `git revert <merge-commit>` deleta protocol+adapters; nada externo depende.

---

### §5.1 A7.1 — Cutover `materialize_config` → `ConfigStore` ✅ entregue 2026-04-27

**Onda 2 · 1 lane · ~2–3 sessões · paralelo com A7.2a, A7.2b, A7.4.**

**Status:** ✅ **mergeada em `main`** (2026-04-27, commits `7bac3fe`..`5929bb7` + ruff fix `eaed671`). CI verde em `fd0ebd9`.

**Depende de:** A7.0 ✅ mergeada em `main`.

**Objetivo:** todos os leitores user-facing (pipeline E3/E4/E5/E5.N + scripts CLI) consomem `ConfigStore` em vez de `_init_config()` ou `materialize_config()`. `materialize_config` ganha `DeprecationWarning` e log estruturado quando ainda é chamado (intent: detectar leitores legados não migrados).

**Configs afetados:** `categorization`, `family_members`, `report_layout`, `institutions`, `transfer_configs`.

**Como foi entregue (5 commits atômicos):**

1. `feat(backend): pipeline_adapter injects ConfigStore via WorkspaceContext` (`7bac3fe`) — `pipeline/context.py` ganha `workspace_id` + `config_store: Optional[ConfigStore]`; `for_tenant` aceita ambos. `pipeline/stage_config.py` move `ConfigStore` import p/ runtime (Pydantic v2 forward-ref fix). `backend/app/services/pipeline_adapter.build_config_store(db, use_db_artifacts)` — `DBConfigStore` quando flag on, `FileConfigStore` legacy senão. `pipeline_task._setup_run_context` abre sessão long-lived só com flag on, instancia store, injeta. `_close_config_store_session` fecha no try/finally.
2. `feat(backend): worker pre-popula config_overrides do DB` (`5e644ec`) — `build_config_overrides_from_db(workspace_id, db)` pré-serializa configs A7.1 em dict para `WorkspaceContext.config_overrides`. `_setup_run_context` injeta via `for_tenant(config=overrides, …)`. **E3/E4 automaticamente DB-first** (já usavam `ctx.load_config()`).
3. `refactor(scripts): e5_analyze + e5n_narrativas read configs via ctx.load_config` (`13ce459`) — `_init_config(base_dir, *, ctx=None)` aceita ctx; `family_members.json` + `categorization.json` lidos via `ctx.load_config` quando ctx fornecido. `main(root_dir)` legado mantém leitura disco.
4. `chore(backend): materialize_config DeprecationWarning + log; production usa prepare_pipeline_config_dir` (`5ed799a`) — `materialize_config()` emite `DeprecationWarning` + structured log `mathoms.config.materialize.legacy_call` (logger `mathoms.config.materialize`). Novo `prepare_pipeline_config_dir`: copia tree global + materializa apenas configs FORA do escopo A7.1 (pipeline.json, llm_config.json). **Não emite legacy_call.** `_prepare_run_context` + `ensure_tenant_pipeline_config` (upload flow) migrados.
5. `test(a7): split deprecation/legacy_call assertions` (`23a28fe`) + `docs(a7): A7.1 ✅ entregue` (`5929bb7`) — F.I.R.S.T fix (mock spy ao invés de caplog p/ robustez cross-test) + CHANGELOG/BACKLOG.

**Acceptance gates batidos:**
- ✅ `pytest tests -q` 1495 passed (+2 skipped) — pipeline goldens E3/E4/E5/E5.N paridade byte-a-byte preservada.
- ✅ `pytest backend/tests -q` 1350 passed (+4 skipped) — incluindo todos os legacy `materialize_config` tests com DeprecationWarning emitida.
- ✅ Fluxo produtivo (`_prepare_run_context` + `ensure_tenant_pipeline_config`) NÃO chama mais `materialize_config` — zero `mathoms.config.materialize.legacy_call` em smoke E2E. Tests legados emitem warning + log isolados ao escopo de teste.
- ✅ `dev/check_pipeline_boundaries.py` verde (zero SQLAlchemy/FastAPI em `pipeline/`).
- ✅ `dev/check_code_style_regression.py` verde (P7 −2 vs baseline; nenhum P1/P9 novo).
- ✅ CI verde em `main` (`fd0ebd9`).

**Bridges remanescentes (até A7.5):**
- `materialize_config()` continua callable; cada chamada emite `DeprecationWarning` + structured log.
- `FileConfigStore` (Sprint A7.0) continua disponível como fallback quando `MATHOMS_USE_DB_ARTIFACTS=False`.

**Riscos confirmados como mitigados:**
- Rota DB-first → fallback disco determinístico via `ctx.load_config(name)` (overrides → disco). Workspace sem row em `categorization` → overrides não inclui a key → disco prevalece (cópia global de `prepare_pipeline_config_dir`).

**Rollback:** disponível via `git revert` dos 6 commits A7.1 + ruff fix. `materialize_config` permanece como bridge funcional.

---

### §5.2a A7.2a — Decision aggregate (event-sourced) ✅ entregue 2026-04-27

**Onda 2 · 1 lane · ~3–4 sessões · paralelo com A7.1, A7.2b, A7.4.**

**Status:** ✅ **mergeada em `main`** (2026-04-27). 8 commits.

**Depende de:** A7.0 ✅ mergeada (precisa do tipo `DecisionsConfig`). **NÃO** depende de A7.1.

**Objetivo:** introduzir entidade `Decision` com lifecycle event-sourced; migrador one-shot popula o workspace do cliente original com os 15 itens de `config/decisions.md`; tela "Plano de Ação" lê do DB; `decisions.md` deletado **nesta lane** (resolve dívida PII paralelamente à arquitetura).

**Como foi entregue (8 commits):**

1. `docs(a7): A7.2a 🚧 — pickup status` — flip BACKLOG.
2. `feat(backend): Decision + DecisionEvent models + Alembic migration (ADR-136)`
   — `backend/app/models/decision.py` + Alembic `x2y3z4a5b6c7`. Self-FK
   `supersedes_id`, `UNIQUE (workspace_id, code)`, `amount_brl_cents BIGINT`.
3. `feat(backend): DecisionRepository + use cases + DTOs` — append-only event
   log via `repo.add_event`; 6 use cases (create/get/list/update/
   mark_executed/supersede); DTOs com Decimal no wire (ADR-090).
4. `feat(backend): /v1/.../decisions endpoints + router registration` —
   6 endpoints, `response_model` explícito, gated por `require_write_role`.
5. `chore(api): update OpenAPI snapshot + DB schema reference` — 32 → 34
   tabelas; OpenAPI inclui os 6 endpoints de decisions.
6. `test(backend): Decision repository + use cases + API (25 tests)` —
   F.I.R.S.T, valores fictícios (R$1.000, R$50.000).
7. `chore(dev): migrate_decisions_to_db.py one-shot migrator` — parser
   markdown idempotente + 5 specs anti-regressão.
8. `feat(frontend): PlanoDeAcaoSection + useDecisions hook + report_layout
   entry` — tabela, filtro por status, CTA execute, codegen regenerado;
   3 vitest unit specs + 1 e2e `@critical` HTTP API-only.
9. `chore(config): rm config/decisions.md + bloquear re-introdução` —
   `git rm` + entrada em `dev/check_forbidden_paths.py` + `dev/commit.py`.

**Entregáveis:**

1. **Backend models** (`backend/app/models/decision.py`):
   ```python
   class Decision(Base):
       id: UUID
       workspace_id: FK → workspaces
       code: str          # "D01", "D15"…
       title: str
       rationale: text
       amount_brl_cents: BigInt | None
       status: Enum(Pendente|Decidido|Executado|Descartado|Superseded)
       supersedes_id: FK | None
       decided_at: date | None
       executed_at: date | None
       created_at, updated_at: timestamptz

   class DecisionEvent(Base):
       id: UUID
       decision_id: FK
       event_type: Enum(Created|StatusChanged|Superseded|Executed|Updated)
       occurred_at: timestamptz
       actor: str
       payload: jsonb
   ```
2. **Alembic migration** adicionando ambas as tabelas.
3. **Application layer** (`backend/app/application/decisions/`):
   - Use cases: `CreateDecision`, `UpdateDecision`, `MarkDecisionExecuted`, `SupersedeDecision`, `ListDecisions`, `GetDecision`.
   - Cada use case append em `decision_events`; status atual é projeção.
4. **Repositories** (`backend/app/repositories/decision_repository.py`).
5. **API** (`backend/app/api/decisions.py`):
   - `GET    /api/v1/workspaces/{id}/decisions`
   - `POST   /api/v1/workspaces/{id}/decisions`
   - `GET    /api/v1/workspaces/{id}/decisions/{decision_id}`
   - `PATCH  /api/v1/workspaces/{id}/decisions/{decision_id}`
   - `POST   /api/v1/workspaces/{id}/decisions/{decision_id}/execute`
   - Todos com `response_model` explícito; OpenAPI snapshot atualizado.
6. **Frontend** (`frontend/src/components/report/sections/PlanoDeAcao/`):
   - `PlanoDeAcaoSection.tsx` — tabela com status badge, supersede chain.
   - Hook `useDecisions(workspaceId)`.
   - Entrada na taxonomia do `report_layout` (key: `plano_de_acao`).
7. **Migrator one-shot** (`dev/migrate_decisions_to_db.py`):
   - Lê `config/decisions.md`, parseia tabela markdown, cria 15 `Decision` rows + `DecisionEvent` `Created` para o workspace alvo (CLI flag `--workspace-id`).
   - Idempotente: se `code` já existe, skipa.
   - **Não generalizar** — script descartável; não vira service permanente.
8. **Limpeza**: `git rm config/decisions.md` no PR final desta lane (após migrator rodar no workspace do cliente piloto).

**Acceptance gates batidos:**
- ✅ Decision tests novos verdes (29 specs: 5 repo + 11 use cases + 9 API + 5 migrator -1 skip por decisions.md ausente; 4 dummy fora do happy path coberto por outros files).
- ✅ Frontend 649 vitest passed (3 novos PlanoDeAcaoSection + 1 e2e `@critical`).
- ✅ OpenAPI + DB schema reference snapshots regenerados (32 → 34 tabelas).
- ✅ `dev/check_forbidden_paths.py` bloqueia `config/decisions.md` (defense-in-depth).
- ✅ `config/decisions.md` removido do git tree.

**Bridges remanescentes (até A7.5):** nenhum — aggregate é independente
das outras lanes da Sprint A7. `dev/migrate_decisions_to_db.py` permanece
em `dev/` como referência histórica; pode ser removido junto com outras
limpezas em A7.5 se não for mais necessário.

**Riscos confirmados como mitigados:**
- Schema event-sourced é diferente do resto do app (CRUD puro). Documentado
  em ADR-136 §Consequências que `Decision` é caso isolado, não convenção
  a propagar.
- Migrator parser-de-markdown é frágil. Testes do parser garantem que
  decisions.md atual (15 rows) gera entradas válidas; após cutover, o
  teste anti-regressão skipa elegantemente.

**Rollback:** `git revert <merge-commit>`. `config/decisions.md`
recuperável via git history se necessário (commit anterior ao
`git rm`).

---

### §5.2b A7.2b — Tabelas globais fiscal/market versionadas ✅ entregue 2026-04-27

**Onda 2 · 1 lane · ~2–3 sessões · paralelo com A7.1, A7.2a, A7.4.**

**Status:** ✅ **entregue em 6 commits na branch `agent/a7-2b-fiscal-market-tables/20260427-1152`** (aguardando merge em `main`).

**Depende de:** A7.0 ✅ mergeada (estendeu `ConfigStore` com stubs).

**Objetivo:** `parametros_fiscais.json` e `taxas.json` viram tabelas globais versionadas por data. Pipeline (E5, `previdencia_analyzer`, `cenarios_conjuge_analyzer`) lê via `ConfigStore` com escopo de período. Reproducibilidade: relatório de fev/2025 usa parâmetros de 2025 mesmo gerado em 2027.

**Como foi entregue (6 commits):**

1. `feat(backend): fiscal_parameters + market_rates models + Alembic` — `backend/app/models/{fiscal_parameter,market_rate}.py` + migration `x2y3z4a5b6c7`. Money em `BIGINT` cents (PGBL/INSS) ou `DECIMAL` (alíquota, rate). UNIQUE(pair, observed_at).
2. `feat(backend): ConfigStore.get_fiscal_for_period + get_market_rate` — `FiscalParameterRepository.get_for_period` (overlap mid-year → `FiscalParameterAmbiguous`); `MarketRateRepository.get_latest_on_or_before`. Cache Redis `fiscal:y={year}` (TTL 1h fallback) + `market:p={pair}:d={iso}` (TTL 30d immutable). Falha aberta: Redis down → DB direto. `FileConfigStore` bridge implementado.
3. `feat(backend): seed_fiscal_2024_2026` — data migration `y3z4a5b6c7d8` popula 2024/2025/2026 + USD/BRL/EUR/BRL para `today` e bootstrap `2024-01-01`. Idempotente (skip se row já existe). Offline-mode safe (`context.is_offline_mode()` → SQL comment).
4. `refactor(pipeline): E5 analyzers consomem ConfigStore` — `PrevidenciaConfig.from_fiscal_parameters(FiscalParameters)`, `CenariosConjugeConfig.from_configs(cambio_usd_brl: Decimal)`, `E5AnalyzerAdapter.from_configs(fiscal_parameters=, cambio_usd_brl=)`. Scripts `e5_analyze.py` resolvem via `ctx.config_store`. Pipeline domain consome `FiscalParameters` typed; nunca dict ou Path.
5. `test(a72b): 49 specs` — repos (16) + DBConfigStore + cache (14) + parsers (10) + typed analyzers (9).
6. `chore(a72b): code style polish + alembic offline guard + schema snapshot` — encurta docstrings (P7), refatora `legacy_json_to_fiscal` para <20 linhas (P1), adiciona offline-mode guard no seed, regenera `docs/DB_SCHEMA_REFERENCE.md`.

**Acceptance gates batidos:**
- ✅ `pytest tests` 1515 passed (+19 vs A7.1 baseline) — incluindo 19 novos pipeline specs.
- ✅ `pytest backend/tests` 1372 passed (+30 vs A7.1 baseline) — incluindo 30 novos backend specs + alembic offline + schema snapshot.
- ✅ `dev/check_pipeline_boundaries.py` verde.
- ✅ `dev/check_code_style_regression.py` verde (P9 −1; nenhum P1/P7 novo).
- ✅ `pre-commit run --all-files` verde.

**Bridges remanescentes (até A7.5):**
- `config/parametros_fiscais.json` + `config/taxas.json` mantidos no PR — consumidores secundários (`_load_caixa_from_e3`, `e5n_narrativas.py`) ainda lêem dict direto. A7.5 cleanup migra todos os caminhos.
- `FileConfigStore.get_fiscal_for_period`/`get_market_rate` continuam funcionando como fallback legacy.

**ADR:** [ADR-135](DECISIONS.md#adr-135--versionamento-temporal-de-séries-fiscais-e-câmbio) já estava em status Decidido (criado em A7.0); esta lane implementa.

**Entregáveis (originais — referência):**

1. **Backend models**:
   ```python
   class FiscalParameter(Base):
       id: UUID
       year: int                 # 2024, 2025, 2026
       ir_brackets: jsonb        # tabela IRPF progressiva
       pgbl_limit_brl_cents: BigInt
       inss_ceiling_brl_cents: BigInt
       lucro_presumido_aliquota: Decimal
       effective_from: date
       effective_to: date | None # null = vigente
       source: text              # "Receita Federal Lei 14.973/2024" etc.
       created_at: timestamptz

   class MarketRate(Base):
       id: UUID
       pair: str                 # "USD/BRL", "EUR/BRL"
       rate: Decimal
       observed_at: date
       source: text              # "BCB PTAX" etc.
       created_at: timestamptz
       UNIQUE (pair, observed_at)
   ```
2. **Alembic migration** + seed `data_migrations/seed_fiscal_2024_2026.py` que materializa o conteúdo atual de `parametros_fiscais.json` para os anos 2024/2025/2026 + `taxas.json` para a data corrente.
3. **`ConfigStore` extensions** (já estavam stub em A7.0):
   - `get_fiscal_for_period(period: PeriodKey) -> FiscalParameters`
   - `get_market_rate(pair: str, observed_at: date) -> Decimal`
4. **Pipeline migrations**:
   - `pipeline/domain/services/previdencia_analyzer.py`: substitui leitura `parametros_fiscais.json` por `config_store.get_fiscal_for_period(ctx.period)`.
   - `pipeline/domain/services/cenarios_conjuge_analyzer.py`: substitui `taxas.json::cambio_usd_brl` por `config_store.get_market_rate("USD/BRL", ctx.report_date)`.
   - `pipeline/domain/services/patrimonio_types.py`: idem.
5. **API** (`backend/app/api/admin/fiscal_parameters.py` + `market_rates.py`) — apenas leitura pública; criação restrita a internal ops (F7F-Local). **Não exigido para esta lane fechar**; pode ser placeholder GET-only.
6. **Cache Redis**: leituras de `FiscalParameter` cacheadas com chave `fiscal:{year}` invalidada por evento `fiscal_parameter.updated`. Sem `@lru_cache` em processo (ADR-111).
7. **Limpeza**: `git rm config/parametros_fiscais.json config/taxas.json` no PR final desta lane.

**Acceptance gates:**
- Backend tests + pipeline tests verdes (28+ novos).
- Smoke E2E verde com `parametros_fiscais.json` e `taxas.json` ausentes.
- Determinismo: golden de relatório histórico (fixture `tests/fixtures/pipeline_golden/2025-q4`) regenerado e gera output **idêntico** ao baseline pré-cutover.
- CTO sign-off no ADR-135 (versionamento temporal).

**Riscos:**
- Período do relatório vs data de observação de câmbio: documentar em ADR-135 a regra de seleção (último PTAX antes ou em `report_date`).
- Migration backwards-compatible: novas colunas adicionadas com default; nenhum DROP até A7.5.

**Rollback:** revert PR. `parametros_fiscais.json` + `taxas.json` continuam disponíveis no git history para emergência.

---

### §5.3 A7.3 — Catalog + Override resolver

**Onda 3 · 1 lane · ~3 sessões · serial com A7.1.**

**Depende de:** A7.1 ✅ mergeada (leitor é `ConfigStore`).

**Objetivo:** dividir `categorization` em **template global** (taxonomia base do produto, versionada via ADR/seed) + **overrides por workspace** (somente diff). `institutions.json` vira `institution_catalog` global. Resolver no read-path; sem materialização redundante por workspace.

**Entregáveis:**

1. **Schema split**:
   - `category_templates` (global): id, key, parent_key, label, default_keywords, sort_order, version
   - `workspace_category_overrides`: workspace_id, template_key, label_override, keywords_override (array), disabled
   - `institution_catalog` (global): code, name, default_parser, metadata jsonb
2. **Migration**: backfill `category_templates` a partir do conteúdo atual de `categorization.json` (template versão 1); migrar dados existentes em `categories` para `workspace_category_overrides` somente onde diferem do template.
3. **Resolver** (`backend/app/services/category_resolver.py`):
   ```python
   def resolve_categories(workspace_id, db) -> list[ResolvedCategory]:
       template = load_template_v1()  # global, cached Redis
       overrides = repo.list_overrides(workspace_id)
       return [merge(t, overrides.get(t.key)) for t in template]
   ```
4. **`ConfigStore.get_categorization`** delega ao resolver.
5. **API**: endpoints CRUD existentes em `/v1/workspaces/{id}/categories` migram para escrever em `workspace_category_overrides`. Read continua retornando `ResolvedCategory`. Frontend não muda (contrato API estável).
6. **Cache Redis**: `categories:{workspace_id}` invalidado por evento `category_override.changed`. Template global cacheado com chave `category_template:v{N}`.
7. **Institutions**: `institution_catalog` global + helper `resolve_institutions(workspace)` (sem override por workspace nesta lane — fica simples). UI já era read-only; mantém.
8. **Limpeza**: `git rm config/categorization.json config/institutions.json` no PR final.

**Acceptance gates:**
- Tests verdes (40+ novos para resolver + override).
- Migration backwards-compat: workspaces existentes leem categorias idênticas pré e pós cutover.
- Performance: relatório gera com ≤5% diff de tempo (cache Redis hot).
- CTO sign-off no ADR-137 (catalog + override).

**Riscos:**
- Drift quando template ganha categoria nova: workspaces antigos automaticamente herdam (correto). Quando template **renomeia** uma categoria existente: overrides apontam para `template_key` antiga e ficam órfãos. Mitigação: ADR proíbe rename de `template_key`; só add/deprecate.
- Cache de template global: invalidação via evento, não TTL.

**Rollback:** revert. Workspaces continuam funcionando com categories materializados (read-path antigo continua existindo até A7.5).

---

### §5.4 A7.4 — Documentação metodológica → `docs/methodology/`

**✅ Entregue 2026-04-27** — branch `agent/a7-4-methodology-docs/20260427-1151`,
5 commits. `docs/methodology/{definitions,regras_composicao_patrimonial,source_hierarchy,milhas}.md`
+ `README.md` index. `CONFIG_MILHAS` em `scripts/e5_analyze.py` repointado
para o novo path (único arquivo *parseado* em runtime). Cross-doc refs
atualizados em `CLAUDE.md`, `.claude/agents/financial-planner.md`,
`docs/{COPY_GUIDELINES,REPORT_PREMIUM_PLAN,ARCHITECTURE}.md`,
`config/report_spec.md`, `backend/tests/test_config_materializer.py`.
4 paths antigos bloqueados em `dev/{check_forbidden_paths,commit}.py`.

**Paralelo a tudo · 1 lane · ~1 sessão · não depende de nada.**

**Objetivo:** mover documentação humana de produto para `docs/methodology/`, removê-la de `config/`. Atualiza referências de comentário em `scripts/e5_analyze.py`/`e7_review.py` que apontam para `config/<file>.md`.

**Entregáveis:**

1. `git mv config/definitions.md docs/methodology/definitions.md`
2. `git mv config/regras_composicao_patrimonial.md docs/methodology/regras_composicao_patrimonial.md`
3. `git mv config/source_hierarchy.md docs/methodology/source_hierarchy.md`
4. `git mv config/milhas.md docs/methodology/milhas.md`
5. `docs/methodology/README.md` — index com 1 linha por arquivo.
6. Atualizar comentários `# Source: config/X.md` → `# Source: docs/methodology/X.md` nos scripts (puramente comentário, sem efeito runtime).
7. Atualizar `CLAUDE.md` §Fontes de verdade se necessário (apontar para novos paths).

**Acceptance gates:**
- `pytest` verde (zero efeito runtime esperado).
- `grep -rn "config/definitions\|config/regras_composicao\|config/source_hierarchy\|config/milhas" .` retorna zero hits fora de `docs/methodology/`.
- CTO sign-off opcional (lane docs-only, baixo risco).

**Riscos:** mínimos. Lane mais barata da onda; ideal pickup curto.

**Rollback:** revert. `git mv` é reversível.

---

### §5.5 A7.5 — Cleanup final

**Onda 4 · 1 lane · ~1.5–2 sessões · BLOQUEANTE — depende de A7.1 + A7.2a + A7.2b + A7.3 + A7.4.**

**Objetivo:** remover bridges, deletar `config/`, garantir produto rodando puro DB-first.

**Entregáveis:**

1. `pipeline/adapters/file_config_store.py` removido.
2. `backend/app/services/config_materializer.py` removido (todas as funções `serialize_*` + `materialize_config`).
3. `pipeline/stage_config.py` — remove fallback de `FileConfigStore` no default; `config_store: ConfigStore` torna-se obrigatório.
4. `git rm -r config/` — diretório inteiro deletado (todos os 11 arquivos + qualquer auxiliar).
5. `dev/check_forbidden_paths.py` — adiciona `config/` à lista de paths proibidos.
6. CI green: smoke E2E rodando com `config/` ausente.
7. ADR-138 atualizada (status: ✅ entregue) + entrada em CHANGELOG.
8. `docs/CONFIG_CUTOVER_PLAN.md` movido para `docs/archive/CONFIG_CUTOVER_PLAN-YYYY-MM-DD.md` com header "Sprint A7 fechada em <data>".

**Acceptance gates:**
- `pytest tests -q && pytest backend/tests -q && pytest backend/tests/integration -q` verdes.
- `cd frontend && npm test -- --run && npm run test:e2e -- --grep @critical` verdes.
- `make smoke` em workspace fixture verde.
- `make smoke-prod-shadow` (se existir) verde — workspace de cliente piloto sem `config/` no host.
- CTO assina off final + autoriza tag `v-config-free`.

**Riscos:**
- Risco residual de leitor escondido: mitigado pelo grep + smoke. Se aparecer regressão pós-merge, revert puro restaura tudo (bridges em `git history`).

**Rollback:** revert PR. Mas idealmente: testes empíricos pré-merge garantem zero regressão; depois desta lane, voltar atrás é caro.

---

### §5.6 A7.6 — Rules-as-code: dissolver `docs/methodology/`

**Onda 2.5 · 1 lane · ~3-4 sessões · paralelo com A7.2a, A7.3.**

**Status:** ☐ aberta — gate G1 pendente (4 ADRs draft + CTO sign-off antes de codar).

**Depende de:** A7.4 ✅ mergeada (arquivos atualmente em `docs/methodology/`).

**Objetivo:** eliminar o diretório `docs/methodology/` movendo regras universais de produto para docstrings + ADRs no código que enforce, e dados cliente-específicos para DB ou `storage/<workspace_id>/notes/` (gitignored).

**Por que esta lane (retrospectiva A7.4):** A A7.4 fez `git mv` puro (`config/*.md` → `docs/methodology/*.md`) preservando o vício do CLI mono-cliente — cada arquivo mistura **regras universais de produto** (7 categorias, hierarquia de fontes, valuation de milhas) com **instâncias cliente-específicas do workspace piloto** (David, Mariana, Tasso da Silveira, Hashdex, valores BRL reais, contas Itaú/BTG). Auditoria pós-merge confirmou 102 hits cliente-específicos nos 4 arquivos (definitions: 59 · regras_composicao: 19 + valores BRL · source_hierarchy: 19 · milhas: 5). Isso viola CLAUDE.md §Regras críticas ("nunca expor valores monetários reais ... em commits"). A7.6 corrige a arquitetura: rules-as-code em vez de docs paralelos.

**Princípio adotado:** product methodology IS the code. Documentar separadamente cria drift. Eliminar `docs/methodology/` força a referência única (código + ADR para o "porquê").

**ADRs novas (gate G1 — antes de qualquer commit de código):**
- **ADR-139** — `docs/methodology/` é rules-as-code (regra geral)
- **ADR-140** — 7 categorias canonical da composição patrimonial + premissa "titular + cônjuge"
- **ADR-141** — E3 source hierarchy + workspace tier em `BankAccount.source_tier`
- **ADR-142** — Milhas: valuation methodology universal + programs em `storage/<ws>/notes/` (bridge transitório; A8.1 entrega `MileageProgram` DB entity)

**Sub-tasks (1 commit por arquivo, após G1):**

1. **`regras_composicao_patrimonial.md` → docstring no classifier + ADR-140.** Localizar função classificadora em `pipeline/domain/services/cash_flow_builder.py` (ou similar). Migrar 7 categorias + tabela "tipo X → bucket Y" para docstring (sem valores BRL, sem nomes; ref ADR-140). Goldens E4/E5 paridade byte-a-byte preservada.
2. **`source_hierarchy.md` → docstring em `income_origin_resolver` + ADR-141 + schema migration.** Hierarquia universal vai p/ docstring; banco→tier workspace-specific migra p/ DB (`BankAccount.source_tier` — schema review G2 obrigatório). Goldens E3 verde.
3. **`milhas.md` → `storage/<ws>/notes/milhas.md` + ADR-142.** Migrate `parse_milhas_md(workspace_root)` para ler de path workspace-scoped. Migrator one-shot (`dev/migrate_milhas_to_workspace_storage.py`) copia conteúdo atual para workspace piloto. Bridge: fallback p/ path antigo + DeprecationWarning (removido em A7.5). Universal valuation method + ADR-142. **A8.1 modela `MileageProgram` em DB** (débito técnico aceito).
4. **`definitions.md` → DB schema ref + ARCHITECTURE.md glossary.** Mapping por seção:
   - **~190 linhas (38%) — cliente puro:** drop direto (já em DB: `FamilyMember`, `BankAccount`, `BaselinePatrimonial`).
   - **~60 linhas (12%) — decisões de planejamento:** A7.2a Decision aggregate (contratos PJ, estratégia aportes).
   - **~120 linhas (24%) — universal product methodology:** docstrings em route_documents/E0/E1 LLM extractor/calculators + ADRs.
   - **~150 linhas (30%) — híbrido categorização/instituições:** A7.3 catalog/override absorve.
   - **~30 linhas (6%) — duplicação CLAUDE.md:** drop.
   - Resultado: arquivo inteiro desaparece. Sub-task depende soft de A7.3 mergeada (categorias) e A7.2a (decisões).
5. **`README.md` + `git rm -r docs/methodology/` + bloqueio em `dev/check_forbidden_paths.py`.** CLAUDE.md atualizado (Fontes de verdade + Regras críticas).
6. **Documentação Sprint A7:** §1 atualizada (já feito), §5.4 retrospective note, §5.6 ✅, §10 checklist + ADRs 139-142 status Decidido.

**Acceptance gates:**
- ADRs 139-142 status Decidido em `docs/DECISIONS.md`.
- `find docs/methodology/ -type f` → empty.
- `dev/check_forbidden_paths.py` bloqueia `docs/methodology/**`.
- `grep -rn "David\|Mariana\|Tasso\|Benedito\|Hashdex" docs/` → zero hits (fora git history e CHANGELOG retrospectivo).
- `pytest tests -q` 1495+ passed (E3/E4/E5/E5.N goldens paridade preservada).
- `pytest backend/tests -q` 1383+ passed.
- `dev/check_pipeline_boundaries.py` verde.
- CLAUDE.md atualizado.
- Workspace piloto: relatório gera identicamente; card de milhas funciona com path novo.
- CTO G3 ✅ pré-merge.

**Riscos:**
- **`parse_milhas_md` runtime breakage:** mitigação via bridge com fallback warned + migrator roda **antes** do `git rm`.
- **Schema migration `BankAccount.source_tier`:** Alembic backwards-compat (add nullable + populate + flip — nunca DROP no mesmo PR).
- **Coordenação cross-lane:** A7.3 (categorias) e A7.2a (decisões) podem absorver partes de definitions.md — sub-task 4 fica por último.

**Rollback:** `git revert` por sub-task. Bridge transitório em sub-task 3 facilita rollback parcial.

**Track file:** [track_a7_6_rules_as_code.md](agent_prompts/track_a7_6_rules_as_code.md).

---

## §6 Protocolo de supervisão CTO

### §6.1 Quem é o CTO

**Humano (David)** OU **agente `senior-cto`** invocado via `Agent(subagent_type="senior-cto", …)`. As assinaturas valem igual desde que o conteúdo da revisão fique registrado (commit trailer, comentário em PR, ou bullet no CHANGELOG).

### §6.2 Gates obrigatórios

Cada lane passa pelos seguintes pontos de revisão CTO antes de ir para `main`:

| # | Gate | Quando | Quem revisa | Artefato esperado |
|---|---|---|---|---|
| **G1 — ADR draft** | Antes da primeira linha de código da lane | CTO | ADR mergeado em `docs/DECISIONS.md` (rascunho → Decidido) |
| **G2 — Schema review** | Antes da Alembic migration sair do branch | CTO | Comentário "Schema OK" em commit ou track file |
| **G3 — PR review pré-merge** | Quando agente abre PR (ou anuncia "branch pronta para review") | CTO | Aprovação registrada (commit trailer `Reviewed-by:` ou nota em BACKLOG) |
| **G4 — Wave boundary** | Antes da próxima onda começar | CTO | Smoke E2E verde + atualização do diagrama de ondas em BACKLOG |

### §6.3 Como invocar o CTO

Em cada gate, o agente que terminou o trabalho:

1. **Anuncia em CHANGELOG `[Unreleased]`** + linha no BACKLOG: "A7.X aguarda G3 (CTO review)".
2. **Para de mexer em arquivos** — aguarda revisão. Pode pegar outra lane disjunta enquanto espera.
3. **Humano (ou orquestrador)** invoca:
   ```
   Agent(
     subagent_type="senior-cto",
     description="A7.X PR review",
     prompt="Revisar a branch agent/a7-X-<slug>/<ts> antes de merge em main.
             Lane prompt: docs/agent_prompts/track_a7_X_<slug>.md
             ADR de referência: ADR-13Y em docs/DECISIONS.md
             Acceptance gates: §5.X de docs/CONFIG_CUTOVER_PLAN.md
             Tarefa: validar que todos os gates passaram, principio P1
             (produto continua funcionando) está atendido, e que não há
             regressão arquitetural. Reportar APROVADO ou BLOQUEADO + lista
             de comentários acionáveis."
   )
   ```
4. CTO retorna **APROVADO** (com checklist confirmado) ou **BLOQUEADO** (lista de itens). Resultado é resumido pelo orquestrador para o usuário e gravado.

### §6.4 Critérios de aprovação

CTO aprova quando **todos** os itens abaixo são verdade:

- [ ] ADR vinculada está em `Decidido`, não draft.
- [ ] Acceptance gates do §5.X marcados (todos os checkboxes).
- [ ] Smoke E2E na branch verde.
- [ ] Diff respeita §Code style do CLAUDE.md (funções 4-20l, módulos ≤500l, sem `Dict[str, Any]` cross-boundary, sem float em campo monetário).
- [ ] Princípio P1 atendido: rebase em `main` recente + smoke verde demonstram que produto continua funcionando.
- [ ] Princípio P6 atendido: bridges introduzidos têm DeprecationWarning + data de remoção.
- [ ] Não há novidade fora de escopo (refactor casual, "limpeza" tangencial — viola CLAUDE.md §Doing tasks).

### §6.5 Quando o CTO bloqueia

Bloqueio retorna lista de itens. Agente:

1. Endereça cada item em commits adicionais (não amenda anteriores — CLAUDE.md §Git).
2. Re-anuncia "pronto para re-review" em BACKLOG.
3. CTO revisa apenas o delta + confirmação dos itens.

Máximo 2 ciclos de bloqueio antes do humano (David) intervir.

---

## §7 Garantia "produto continua funcionando"

### §7.1 Definição operacional

"Produto continua funcionando" = **smoke E2E** (Playwright `@critical` + `make smoke` pipeline) verde em **todo merge em `main`** durante a sprint.

### §7.2 Bridges obrigatórios

| Lane | Bridge introduzido | Removido em |
|---|---|---|
| A7.0 | `FileConfigStore` (legacy adapter) | A7.5 |
| A7.0 | `materialize_config` mantém-se intacto | A7.5 (deletado) |
| A7.1 | `materialize_config` ganha DeprecationWarning + log | A7.5 |
| A7.2a | `decisions.md` permanece em git history | já em git history (após `git rm` no fim da lane) |
| A7.2b | seed Alembic populado **antes** do delete dos JSONs | parte da lane |
| A7.3 | read-path antigo `categories` table coexiste com `category_templates` + overrides | A7.5 |
| A7.4 | (sem bridge — files docs-only) | n/a |

### §7.3 Critério empírico de cada onda

Antes de declarar uma lane fechada (✅ em BACKLOG):

1. `git fetch origin && git rebase origin/main` na branch.
2. `pytest tests -q && pytest backend/tests -q` verdes.
3. `cd frontend && npm test -- --run` verde se a lane mexeu em frontend.
4. `cd frontend && npm run test:e2e -- --grep @critical` verde se a lane mexeu em UI ou API consumida pela UI.
5. `make smoke` (workspace fixture rodando E0→E5.N→relatório) verde.
6. **CTO G3 aprovado.**
7. `git push origin main` (fast-forward only).
8. CI verde no commit em `origin/main` (ver definição "Concluído" do CLAUDE.md).
9. Smoke shadow em workspace de cliente piloto (se F7 já estiver em prod) — opcional na sprint A7 enquanto F7 está em ramp-up.

---

## §8 Riscos & rollback

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| **Pipeline lê config legado escondido** | Média | Alto | Log estruturado `mathoms.config.materialize.legacy_call` em A7.1; smoke detecta call-site não migrado |
| **Schema fiscal sem vigência produz drift histórico** | Baixa (após A7.2b) | Alto | Golden de relatório histórico em A7.2b; ADR-135 explicita regra de seleção de período |
| **Migrator de `decisions.md` perde dados** | Média | Médio | Migrator idempotente; rodar dry-run; revisão visual antes de `git rm` |
| **Override resolver introduz N+1 query** | Média | Médio | Cache Redis em A7.3; benchmark antes/depois; flame graph se p95 piora |
| **Janela de bridge esticada além de A7.5** | Alta sem governança | Médio | CTO G4 valida cada wave boundary; data de remoção em cada bridge |
| **Conflito entre lanes paralelas (Onda 2)** | Baixa (arquivos disjuntos) | Médio | Mapa de "Toca:" no §4 + protocolo hotspot CLAUDE.md |
| **Múltiplos agentes na mesma lane** | Baixa | Alto | Pickup protocol CLAUDE.md (`git worktree list` + `git for-each-ref`) |

### §8.1 Rollback por lane

Cada lane fecha como **PR atômico em fast-forward**. Rollback = `git revert <merge-commit>` no PR de cutover, **não** força do `main` para trás.

Em caso de regressão silenciosa detectada pós-merge (>24h):
1. Não reverter direto — investigar root cause.
2. Hotfix em nova branch `agent/a7-X-hotfix/<ts>` se trivial (<10min).
3. Revert se demora >30min para hotfix.

---

## §9 ADRs vinculadas

| ADR | Tema | Lane | Status |
|---|---|---|---|
| [ADR-134](DECISIONS.md#adr-134--configstore-protocolo-de-leitura-tipado-pipeline--backend) | ConfigStore protocol + adapters | A7.0 | ☐ aberto |
| [ADR-135](DECISIONS.md#adr-135--versionamento-temporal-de-séries-fiscais-e-câmbio) | Versionamento temporal de séries fiscais e câmbio | A7.2b | ☐ aberto |
| [ADR-136](DECISIONS.md#adr-136--decision-aggregate-event-sourced-com-supersede-chain) | Decision aggregate event-sourced | A7.2a | ✅ Decidido |
| [ADR-137](DECISIONS.md#adr-137--catalog--override-resolver-para-categorization-e-institutions) | Catalog + override resolver | A7.3 | ☐ aberto |
| [ADR-138](DECISIONS.md#adr-138--protocolo-de-supervisão-cto-para-sprint-a7) | Protocolo de supervisão CTO em sprints multi-agente | A7 inteira | ☐ aberto |

---

## §10 Checklist de fechamento da Sprint A7

- [ ] A7.0 ConfigStore protocol mergeada em `main` + ADR-134 ✅
- [ ] A7.1 Cutover materialize_config mergeada + smoke verde
- [x] A7.2a Decision aggregate mergeada + ADR-136 ✅ + `decisions.md` removido
- [ ] A7.2b Tabelas globais fiscal/market mergeadas + ADR-135 ✅ + `parametros_fiscais.json` + `taxas.json` removidos
- [ ] A7.3 Catalog + override mergeada + ADR-137 ✅ + `categorization.json` + `institutions.json` removidos
- [x] A7.4 Metodologia movida para `docs/methodology/` + 4 arquivos removidos de `config/`
- [ ] A7.5 Cleanup mergeada — `config/` deletado, `FileConfigStore` removido, `materialize_config` removido
- [ ] CHANGELOG entrada [Sprint A7 ✅] com data de fechamento
- [ ] `dev/check_forbidden_paths.py` proíbe `config/*`
- [ ] `docs/CONFIG_CUTOVER_PLAN.md` arquivado em `docs/archive/CONFIG_CUTOVER_PLAN-YYYY-MM-DD.md`
- [ ] CTO assina sign-off final em CHANGELOG

---

## §11 Quando tudo isso fecha

Pós A7.5: importação de dados de cliente novo é **operação de produto** (UI no app + endpoints `/v1/workspaces/{id}/...`), não git commit. Cada workspace tem seu conjunto isolado em DB; tabelas globais (fiscal, market, category templates, institution catalog) atualizam-se via seed Alembic + admin UI (F7F-Local internal ops). Próximo passo natural — **fora desta sprint** — é construir UI editor para `report_layout` (decisão de produto: até que ponto cliente final customiza vs. padrão Mathoms).
