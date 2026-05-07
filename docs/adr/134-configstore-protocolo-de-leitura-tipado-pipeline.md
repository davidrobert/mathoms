---
id: ADR-134
type: adr
title: "`ConfigStore`: protocolo de leitura tipado (pipeline + backend)"
status: Decidido
phase: "Sprint A7"
date: "2026-04-26"
relates_to: ["[[ADR-082]]"]
supersedes: []
superseded_by: []
aliases: ["ADR 134"]
tags:
  - area/backend
  - area/persistence
  - area/pipeline
  - status/decidido
  - type/adr
size_lines: 77
---

# ADR-134 — `ConfigStore`: protocolo de leitura tipado (pipeline + backend)

**Status:** Decidido (Sprint A7) • **Data:** 2026-04-26 • **Relaciona**
[ADR-082](#adr-082--pipelineartifact-artefatos-computacionais-no-banco)
(blobs DB-first com materialização para o pipeline),
[ADR-097](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy),
[ADR-101](#adr-101--princípios-r12-r17-dddsolid-no-backend-api-a6e),
[ADR-111](#adr-111--stateless-rigoroso-padrão-e-gate-empírico-a6f6),
[ADR-120](#adr-120--readers-user-facing-consultam-artifactstore-db-first-com-fallback-disco),
[ADR-133](#adr-133--transferencias_internas-modelado-em-transfer_configs-workspace-scoped).

**Contexto:** A versão CLI inicial do produto usava `config/*.json` +
`*.md` como única fonte de verdade. O cutover para multi-tenant
(A6a-A6f) migrou parte dos arquivos para DB (5 blobs:
`pipeline_configs`, `categorization`, `family_members`,
`institution_configs`, `report_layouts`, `transfer_configs`), mas
manteve uma ponte (`backend/app/services/config_materializer.py`) que
**escreve cópia em `config/`** antes do pipeline rodar — porque o
pipeline lê do disco via `_init_config()`. Resultado: dois sources of
truth, janela de race, e `pipeline/**` continua acoplado a `Path`.

Alternativas consideradas:

- **(a) Manter `materialize_config` indefinidamente.** Custo crescente:
  toda nova entidade configurável adiciona dois write paths (DB + disco).
  Não escala para `decisions`, `fiscal_parameters`, `market_rates` etc.
- **(b) Fazer `pipeline/` importar SQLAlchemy.** Quebra
  [ADR-097](#adr-097--extract-then-refactor-estratégia-de-decomposição-de-e3_reconcilepy) e a
  regra do CLAUDE.md (`dev/check_pipeline_boundaries.py`).
- **(c) Protocolo `ConfigStore` definido em `pipeline/ports/`, com
  adapter SQLAlchemy em `backend/app/services/`.** Simétrico ao padrão
  `ArtifactStore`/`DBArtifactStore` que já funciona; pipeline injeta via
  `StageConfig`.

**Decisão:** Adotar (c).

`pipeline/ports/config_store.py` define `ConfigStore` como
`typing.Protocol` read-only. Métodos retornam dataclasses tipadas em
`pipeline/domain/types/config.py` (`CategorizationConfig`,
`FamilyMembersConfig`, `InstitutionsCatalog`, `ReportLayout`,
`TransferConfig`, `FiscalParameters`, `MarketRate`).

Dois adapters concretos:

- `backend/app/services/db_config_store.py` (`DBConfigStore`) — usa os
  repositórios já existentes; é o adapter de produção quando
  `MATHOMS_USE_DB_ARTIFACTS=true`.
- `pipeline/adapters/file_config_store.py` (`FileConfigStore`) — lê de
  `PROJECT_DIR / "config"` para compatibilidade com testes legados +
  invocações CLI fora do produto. **Emite `DeprecationWarning` no
  construtor** com data de remoção (Sprint A7.5).

`StageConfig` ganha campo `config_store: ConfigStore` (default
`FileConfigStore` durante a janela de cutover; obrigatório após A7.5).

`pipeline_adapter` (em `backend/app/services/pipeline_adapter.py`)
instancia `DBConfigStore` ao construir `StageConfig`. Pipeline injetado
via construtor; nenhum `@lru_cache` ou cache em processo (ADR-111).
Cache hot-path vai para Redis com invalidação por evento.

**Consequências:**
- ✅ `pipeline/**` continua sem importar SQLAlchemy/FastAPI.
  `dev/check_pipeline_boundaries.py` permanece verde.
- ✅ Boundary única para qualquer leitura de configuração: novos blobs
  (decisions, fiscal_parameters, market_rates, category_templates,
  institution_catalog) entram pelo mesmo Protocol.
- ✅ Testes domain-pure usam `InMemoryConfigStore` fake — alinhado com
  estratégia de fakes nomeados (`tests/fakes/`).
- ⚠️ Janela de cutover: `materialize_config` continua existindo até
  A7.5; cada chamada legada emite `DeprecationWarning` + log
  `mathoms.config.materialize.legacy_call`. Plano em
  [CONFIG_CUTOVER_PLAN.md §5.0](CONFIG_CUTOVER_PLAN.md#§50-a70--configstore-protocol--adapters).
- ❌ Adicionar campo novo ao `ConfigStore` exige tocar Protocol +
  ambos os adapters + qualquer fake. Aceito como custo simétrico ao
  ganho de tipagem cross-boundary.
